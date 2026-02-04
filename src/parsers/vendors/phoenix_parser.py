"""Phoenix vendor-specific invoice parser.

This module implements the parser for Phoenix Lékárenský Velkoobchod invoices.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.models.parsed_invoice import ParsedInvoice, SupplierInfo, VATBreakdown
from src.models.vendor_config import VendorConfiguration
from src.parsers.base_parser import BaseParser, PDFParseError
from src.parsers.extractors.keyword_extractor import KeywordExtractor
from src.parsers.extractors.regex_extractor import RegexExtractor


class PhoenixParser(BaseParser):
    """Parser for Phoenix Lékárenský Velkoobchod invoices."""

    def parse(self, pdf_path: Path) -> ParsedInvoice:
        """Parse Phoenix invoice PDF.

        Args:
            pdf_path: Path to Phoenix PDF invoice

        Returns:
            ParsedInvoice with extracted data

        Raises:
            PDFParseError: If parsing fails
        """
        doc = self.load_pdf(pdf_path)
        full_text = self.get_full_text(doc)

        self.logger.info("Parsing Phoenix invoice", extra={"pdf_path": str(pdf_path)})

        try:
            # Extract header information
            invoice_number = self._extract_invoice_number(full_text)
            issue_date = self._extract_issue_date(full_text)
            due_date = self._extract_due_date(full_text)
            supply_date = self._extract_supply_date(full_text)
            variable_symbol = self._extract_variable_symbol(full_text)

            # Extract supplier information
            supplier = self._extract_supplier_info(full_text)

            # Extract VAT breakdown
            vat_breakdowns = self._extract_vat_breakdown(full_text)

            # Extract total amount
            total_amount = self._extract_total_amount(full_text)

            # Create ParsedInvoice instance
            invoice = ParsedInvoice(
                vendor="Phoenix",
                invoice_number=invoice_number,
                issue_date=issue_date,
                due_date=due_date,
                supply_date=supply_date,
                supplier=supplier,
                vat_breakdowns=vat_breakdowns,
                total_amount=total_amount,
                variable_symbol=variable_symbol,
                received_invoice_number=invoice_number,  # Phoenix uses same number
            )

            self.logger.info(
                "Successfully parsed Phoenix invoice",
                extra={"invoice_number": invoice_number},
            )

            return invoice

        except Exception as e:
            raise PDFParseError(
                f"Failed to parse Phoenix invoice {pdf_path}: {e}"
            ) from e
        finally:
            doc.close()

    def _extract_invoice_number(self, text: str) -> str:
        """Extract invoice number from text."""
        # Pattern: "č. 2250048380"
        value = KeywordExtractor.find_text_after_keyword(
            text, "DAŇOVÝ DOKLAD", r"č\.\s*(\d+)"
        )
        if not value:
            raise PDFParseError("Invoice number not found")

        # Extract just the number from the match
        match = RegexExtractor.extract_first_match(value, r"(\d+)", group=1)
        if not match:
            raise PDFParseError(f"Could not extract invoice number from: {value}")

        return match

    def _extract_issue_date(self, text: str) -> datetime:
        """Extract issue date from text."""
        # Look for date after "Datum vystavení:" - may be on next line
        date_str = RegexExtractor.extract_czech_date(text)
        if not date_str:
            raise PDFParseError("Issue date not found")

        # Find the first date after "Datum vystavení:"
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "Datum vystavení" in line or "vystavený" in line.lower():
                # Check same line and next few lines for date
                for j in range(i, min(i + 3, len(lines))):
                    date_match = RegexExtractor.extract_czech_date(lines[j])
                    if date_match:
                        return self._parse_czech_date(date_match)

        raise PDFParseError("Issue date not found")

    def _extract_due_date(self, text: str) -> datetime:
        """Extract due date from text."""
        value = KeywordExtractor.find_text_after_keyword(
            text, "DATUM SPLATNOSTI:", r"(\d{2}\.\d{2}\.\d{4})"
        )
        if not value:
            raise PDFParseError("Due date not found")

        return self._parse_czech_date(value)

    def _extract_supply_date(self, text: str) -> datetime:
        """Extract supply date (tax point date) from text."""
        # Look for date after "Datum usk. zdanit. plnění:"
        # The dates appear as:
        # Datum vystavení:
        # Datum usk. zdanit. plnění:
        # 22.11.2025  <- issue date (first)
        # 24.11.2025  <- supply date (second)
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "zdanit" in line.lower() and "plnění" in line.lower():
                # Check next few lines and collect all dates
                dates_found = []
                for j in range(i, min(i + 5, len(lines))):
                    date_match = RegexExtractor.extract_czech_date(lines[j])
                    if date_match:
                        dates_found.append(date_match)

                # Supply date is the second date found (first is issue date)
                if len(dates_found) >= 2:
                    return self._parse_czech_date(dates_found[1])
                elif len(dates_found) == 1:
                    # Fallback to first date if only one found
                    return self._parse_czech_date(dates_found[0])

        raise PDFParseError("Supply date not found")

    def _extract_variable_symbol(self, text: str) -> str | None:
        """Extract variable symbol from text."""
        # Use invoice number as variable symbol (mentioned in parentheses)
        value = KeywordExtractor.find_text_after_keyword(
            text, "variabilní symbol", r"(\d+)"
        )
        return value

    def _extract_supplier_info(self, text: str) -> SupplierInfo:
        """Extract supplier information from text."""
        # Extract name
        name_value = KeywordExtractor.find_text_after_keyword(text, "Dodavatel:", None)
        if not name_value:
            raise PDFParseError("Supplier name not found")

        # Clean up the name (first line after "Dodavatel:")
        name = name_value.split("\n")[0].strip()

        # Extract IČO
        ic = RegexExtractor.extract_ic(text)
        if not ic:
            raise PDFParseError("Supplier IČO not found")

        # Extract DIČ
        dic = RegexExtractor.extract_dic(text)
        if not dic:
            raise PDFParseError("Supplier DIČ not found")

        return SupplierInfo(name=name, ic=ic, dic=dic)

    def _extract_vat_breakdown(self, text: str) -> list[VATBreakdown]:
        """Extract VAT breakdown from text.

        Phoenix invoices typically have VAT summary on page 2.
        """
        vat_breakdowns = []

        # Try to extract 21% VAT (most common)
        base_21 = self._extract_vat_base(text, "21")
        vat_21 = self._extract_vat_amount(text, "21")

        if base_21 and vat_21:
            vat_breakdowns.append(
                VATBreakdown(rate=Decimal("0.21"), base=base_21, amount=vat_21)
            )

        # Try to extract 12% VAT
        base_12 = self._extract_vat_base(text, "12")
        vat_12 = self._extract_vat_amount(text, "12")

        if base_12 and vat_12:
            vat_breakdowns.append(
                VATBreakdown(rate=Decimal("0.12"), base=base_12, amount=vat_12)
            )

        # Try to extract 0% VAT
        base_0 = self._extract_vat_base(text, "0")

        if base_0:
            vat_breakdowns.append(
                VATBreakdown(rate=Decimal("0.00"), base=base_0, amount=Decimal("0.00"))
            )

        if not vat_breakdowns:
            raise PDFParseError("No VAT breakdown found")

        return vat_breakdowns

    def _extract_vat_base(self, text: str, rate: str) -> Decimal | None:
        """Extract VAT base amount for a specific rate."""
        # Find all matches and take the last one (final recap on page 2)
        pattern = rf"{rate}%[\s\S]{{0,100}}?([\d\s]+,\d{{2}})"
        matches = RegexExtractor.extract_all_matches(text, pattern, group=1)
        if matches:
            # Take last match
            cleaned = RegexExtractor.clean_czech_number(matches[-1])
            return Decimal(cleaned)
        return None

    def _extract_vat_amount(self, text: str, rate: str) -> Decimal | None:
        """Extract VAT amount for a specific rate."""
        # Find all pairs and take the last pair's second number
        pattern = (
            rf"{rate}%[\s\S]{{0,100}}?[\d\s]+,\d{{2}}[\s\S]{{0,50}}?([\d\s]+,\d{{2}})"
        )
        matches = RegexExtractor.extract_all_matches(text, pattern, group=1)
        if matches:
            # Take last match
            cleaned = RegexExtractor.clean_czech_number(matches[-1])
            return Decimal(cleaned)
        return None

    def _extract_total_amount(self, text: str) -> Decimal:
        """Extract total amount with VAT."""
        value = KeywordExtractor.find_text_after_keyword(
            text, "ČÁSTKA K ÚHRADĚ:", r"([\d\s]+,\d{2})"
        )
        if not value:
            raise PDFParseError("Total amount not found")

        cleaned = RegexExtractor.clean_czech_number(value)
        return Decimal(cleaned)

    def _parse_czech_date(self, date_str: str) -> datetime:
        """Parse Czech date format (DD.MM.YYYY) to datetime.

        Args:
            date_str: Date string in DD.MM.YYYY format

        Returns:
            datetime object

        Raises:
            PDFParseError: If date format is invalid
        """
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError as e:
            raise PDFParseError(f"Invalid date format '{date_str}': {e}") from e
