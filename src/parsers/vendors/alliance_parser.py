"""Alliance vendor-specific invoice parser."""

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.models.parsed_invoice import ParsedInvoice, SupplierInfo, VATBreakdown
from src.models.vendor_config import VendorConfiguration
from src.parsers.base_parser import BaseParser, PDFParseError


class AllianceParser(BaseParser):
    """Parser for Alliance Healthcare invoices."""

    def parse(self, pdf_path: Path) -> ParsedInvoice:
        """Parse Alliance invoice PDF."""
        doc = self.load_pdf(pdf_path)
        full_text = self.get_full_text(doc)

        self.logger.info("Parsing Alliance invoice", extra={"pdf_path": str(pdf_path)})

        try:
            invoice_number = self._extract_invoice_number(full_text)
            issue_date = self._extract_date(
                full_text,
                "Datum vystavení faktury",
                "Issue date not found",
            )
            due_date = self._extract_date(
                full_text,
                "Datum splatnosti",
                "Due date not found",
            )
            supply_date = self._extract_date(
                full_text,
                "Datum uskutečnění zdanitelného plnění",
                "Supply date not found",
            )
            supplier = self._extract_supplier_info(full_text)
            vat_breakdowns = self._extract_vat_breakdown(full_text)
            total_amount = self._extract_total_amount(full_text)

            invoice = ParsedInvoice(
                vendor="Alliance",
                invoice_number=invoice_number,
                received_invoice_number=invoice_number,
                issue_date=issue_date,
                due_date=due_date,
                supply_date=supply_date,
                supplier=supplier,
                vat_breakdowns=vat_breakdowns,
                total_amount=total_amount,
            )

            self.logger.info(
                "Successfully parsed Alliance invoice",
                extra={"invoice_number": invoice_number},
            )
            return invoice
        except Exception as e:
            raise PDFParseError(
                f"Failed to parse Alliance invoice {pdf_path}: {e}"
            ) from e
        finally:
            doc.close()

    def _extract_invoice_number(self, text: str) -> str:
        match = re.search(r"DAŇOVÝ DOKLAD\s*-\s*FAKTURA\s*(\d+)", text)
        if match is None:
            raise PDFParseError("Invoice number not found")
        return match.group(1)

    def _extract_date(self, text: str, label: str, error_message: str) -> datetime:
        pattern = rf"{re.escape(label)}:\s*(\d{{2}}\.\d{{2}}\.\d{{4}})"
        match = re.search(pattern, text)
        if match is None:
            raise PDFParseError(error_message)
        return self._parse_czech_date(match.group(1))

    def _extract_supplier_info(self, text: str) -> SupplierInfo:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        try:
            customer_label_index = lines.index("Odběratel:")
        except ValueError as error:
            raise PDFParseError("Supplier information not found")

        supplier_block = lines[customer_label_index + 1 : customer_label_index + 6]
        if len(supplier_block) < 5:
            raise PDFParseError("Supplier information not found")

        city_line = supplier_block[2]
        city_match = re.match(r"(?P<zip>\d{3}\s\d{2})\s+(?P<city>.+)", city_line)
        if city_match is None:
            raise PDFParseError("Supplier city information not found")

        ic_match = re.search(r"IČ:\s*(\d{8})", supplier_block[3])
        dic_match = re.search(r"DIČ:\s*(CZ\d{8,10})", supplier_block[4])
        if ic_match is None or dic_match is None:
            raise PDFParseError("Supplier tax identifiers not found")

        return SupplierInfo(
            name=supplier_block[0],
            street=supplier_block[1],
            zip=city_match.group("zip"),
            city=city_match.group("city"),
            ic=ic_match.group(1),
            dic=dic_match.group(1),
            country="CZ",
        )

    def _extract_vat_breakdown(self, text: str) -> list[VATBreakdown]:
        lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
        vat_breakdowns: list[VATBreakdown] = []

        for index, line in enumerate(lines):
            if "z toho pro" not in line.lower():
                continue

            rate_match = re.search(r"(\d+)\s*%", line)
            if rate_match is None:
                continue

            amount_values: list[str] = []
            for candidate_line in lines[index + 1 : index + 4]:
                candidate_match = re.search(r"([\d,]+\.\d{2})", candidate_line)
                if candidate_match is not None:
                    amount_values.append(candidate_match.group(1))

            if len(amount_values) < 2:
                continue

            rate = Decimal(rate_match.group(1)) / Decimal("100")
            base = self._parse_alliance_amount(amount_values[0])
            amount = self._parse_alliance_amount(amount_values[1])
            vat_breakdowns.append(
                VATBreakdown.from_values(
                    rate=rate,
                    base=base,
                    amount=amount,
                    vat_amount_tolerance=Decimal("0.10"),
                )
            )

        if not vat_breakdowns:
            raise PDFParseError("VAT breakdown not found")

        return vat_breakdowns

    def _extract_total_amount(self, text: str) -> Decimal:
        match = re.search(r"Celkem\s*k\s*úhradě\s*CZK:\s*([\d,]+\.\d{2})", text)
        if match is None:
            raise PDFParseError("Total amount not found")
        return self._parse_alliance_amount(match.group(1))

    def _parse_alliance_amount(self, value: str) -> Decimal:
        return Decimal(value.replace(",", ""))

    def _parse_czech_date(self, date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError as e:
            raise PDFParseError(f"Invalid date format '{date_str}': {e}") from e