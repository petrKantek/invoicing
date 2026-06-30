"""Batch workflow for initializing and processing invoice directories."""

import csv
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.config.config_loader import ConfigLoader
from src.exporters.invoice_to_xml import InvoiceToXMLExporter
from src.models.parsed_invoice import ParsedInvoice
from src.parsers.base_parser import BaseParser, PDFParseError
from src.parsers.vendors.alliance_parser import AllianceParser
from src.parsers.vendors.phoenix_parser import PhoenixParser
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


DEFAULT_PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "alliance": AllianceParser,
    "merck_sharp": PhoenixParser,
    "phoenix": PhoenixParser,
}


@dataclass
class InvoiceReportRow:
    """One report row for a discovered invoice file."""

    vendor: str
    source_file: str
    processed_file: str
    accounting_invoice_id: str
    status: str
    invoice_number: str
    received_invoice_number: str
    issue_date: str
    supply_date: str
    due_date: str
    variable_symbol: str
    total_amount: str
    message: str


@dataclass
class VendorProcessSummary:
    """Processing summary for one vendor directory."""

    vendor: str
    discovered_files: int
    successful_invoices: int
    failed_invoices: int
    status: str
    message: str
    xml_output: Path | None = None


@dataclass
class BatchProcessResult:
    """Files generated while processing one batch directory."""

    batch_dir: Path
    report_csv: Path
    summary_txt: Path
    xml_outputs: list[Path]
    vendor_summaries: list[VendorProcessSummary]


class InvoiceBatchProcessor:
    """Initialize batch folders and process vendor invoices."""

    def __init__(
        self,
        config_loader: ConfigLoader | None = None,
        parser_registry: dict[str, type[BaseParser]] | None = None,
    ) -> None:
        """Initialize the batch processor."""
        self.config_loader = config_loader or ConfigLoader()
        self.parser_registry = parser_registry or DEFAULT_PARSER_REGISTRY.copy()
        self.logger = setup_logger(self.__class__.__name__)

    def build_batch_dir(
        self,
        start_date: date,
        end_date: date,
        destination_root: Path,
    ) -> Path:
        """Build the batch directory path for a date interval."""
        return destination_root / f"{start_date.isoformat()}_{end_date.isoformat()}"

    def initialize_batch_directories(
        self,
        start_date: date,
        end_date: date,
        destination_root: Path,
    ) -> Path:
        """Create the vendor folder structure for a date interval."""
        if end_date < start_date:
            raise ValueError("End date must be greater than or equal to start date")

        destination_root.mkdir(parents=True, exist_ok=True)
        batch_dir = self.build_batch_dir(start_date, end_date, destination_root)
        batch_dir.mkdir(parents=True, exist_ok=True)

        vendor_codes = self.config_loader.list_available_vendors()
        for vendor in vendor_codes:
            (batch_dir / vendor / "invoices").mkdir(parents=True, exist_ok=True)
            (batch_dir / vendor / "output").mkdir(parents=True, exist_ok=True)

            if vendor == "phoenix":
                for subfolder in ("prusanky", "bojanovice"):
                    (batch_dir / vendor / "invoices" / subfolder).mkdir(parents=True, exist_ok=True)
                    (batch_dir / vendor / "output" / subfolder).mkdir(parents=True, exist_ok=True)

        readme_path = batch_dir / "README.txt"
        readme_path.write_text(
            self._build_readme(start_date, end_date, vendor_codes),
            encoding="utf-8",
        )

        self.logger.info(
            "Initialized batch directory",
            extra={"batch_dir": str(batch_dir), "vendor_count": len(vendor_codes)},
        )
        return batch_dir

    def process_batch(
        self,
        batch_dir: Path,
        starting_invoice_id: int,
    ) -> BatchProcessResult:
        """Process vendor invoice folders and export XML plus reports."""
        if not batch_dir.exists():
            raise PDFParseError(f"Batch directory not found: {batch_dir}")
        if not batch_dir.is_dir():
            raise PDFParseError(f"Batch path is not a directory: {batch_dir}")
        if starting_invoice_id < 0:
            raise PDFParseError("Starting invoice id must be zero or greater")

        report_rows: list[InvoiceReportRow] = []
        vendor_summaries: list[VendorProcessSummary] = []
        xml_outputs: list[Path] = []
        next_invoice_id = starting_invoice_id

        for vendor in self.config_loader.list_available_vendors():
            vendor_summary, vendor_rows, xml_output, next_invoice_id = self._process_vendor(
                batch_dir,
                vendor,
                next_invoice_id,
            )
            vendor_summaries.append(vendor_summary)
            report_rows.extend(vendor_rows)
            if xml_output is not None:
                xml_outputs.append(xml_output)

        report_csv = batch_dir / "extraction_report.csv"
        summary_txt = batch_dir / "processing_summary.txt"
        self._write_report_csv(report_csv, report_rows)
        self._write_summary_txt(summary_txt, batch_dir, vendor_summaries)

        self.logger.info(
            "Processed batch directory",
            extra={
                "batch_dir": str(batch_dir),
                "vendor_count": len(vendor_summaries),
                "xml_outputs": len(xml_outputs),
            },
        )
        return BatchProcessResult(
            batch_dir=batch_dir,
            report_csv=report_csv,
            summary_txt=summary_txt,
            xml_outputs=xml_outputs,
            vendor_summaries=vendor_summaries,
        )

    def _process_vendor(
        self,
        batch_dir: Path,
        vendor: str,
        starting_invoice_id: int,
    ) -> tuple[VendorProcessSummary, list[InvoiceReportRow], Path | None, int]:
        """Process one vendor directory within a batch."""
        invoices_dir = batch_dir / vendor / "invoices"
        output_dir = batch_dir / vendor / "output"
        pdf_paths = sorted(invoices_dir.rglob("*.pdf")) if invoices_dir.exists() else []

        invoice_id = starting_invoice_id

        if not pdf_paths:
            return (
                VendorProcessSummary(
                    vendor=vendor,
                    discovered_files=0,
                    successful_invoices=0,
                    failed_invoices=0,
                    status="no_files",
                    message="No PDF invoices found",
                ),
                [],
                None,
                invoice_id,
            )

        parser_class = self.parser_registry.get(vendor)
        if parser_class is None:
            rows = [
                InvoiceReportRow(
                    vendor=vendor,
                    source_file=pdf_path.name,
                    processed_file="",
                    accounting_invoice_id="",
                    status="unsupported_parser",
                    invoice_number="",
                    received_invoice_number="",
                    issue_date="",
                    supply_date="",
                    due_date="",
                    variable_symbol="",
                    total_amount="",
                    message=f"Parser not implemented for vendor '{vendor}'",
                )
                for pdf_path in pdf_paths
            ]
            return (
                VendorProcessSummary(
                    vendor=vendor,
                    discovered_files=len(pdf_paths),
                    successful_invoices=0,
                    failed_invoices=len(pdf_paths),
                    status="unsupported_parser",
                    message=f"Parser not implemented for vendor '{vendor}'",
                ),
                rows,
                None,
                invoice_id,
            )

        config = self.config_loader.load_vendor_config(vendor)
        parser = parser_class(config)
        exporter = InvoiceToXMLExporter()
        output_dir.mkdir(parents=True, exist_ok=True)

        successful_invoices: list[ParsedInvoice] = []
        report_rows: list[InvoiceReportRow] = []
        invoice_id = starting_invoice_id

        for pdf_path in pdf_paths:
            try:
                invoice = parser.parse(pdf_path)
            except Exception as error:
                report_rows.append(
                    InvoiceReportRow(
                        vendor=vendor,
                        source_file=pdf_path.name,
                        processed_file="",
                        accounting_invoice_id="",
                        status="parse_error",
                        invoice_number="",
                        received_invoice_number="",
                        issue_date="",
                        supply_date="",
                        due_date="",
                        variable_symbol="",
                        total_amount="",
                        message=str(error),
                    )
                )
                continue

            accounting_invoice_id = str(invoice_id)
            processed_file = self._build_processed_file_name(pdf_path, invoice_id)
            processed_path = self._build_processed_output_path(pdf_path, invoices_dir, output_dir, processed_file)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, processed_path)
            invoice_id += 1
            successful_invoices.append(invoice)
            report_rows.append(
                self._build_success_row(
                    vendor,
                    pdf_path,
                    processed_file,
                    accounting_invoice_id,
                    invoice,
                )
            )

        xml_output: Path | None = None
        export_message = ""
        status = "processed"
        if successful_invoices and config.target_xml is not None:
            try:
                pohoda_invoices = [exporter.export(invoice) for invoice in successful_invoices]
                xml_output = output_dir / f"{vendor}_{batch_dir.name}.xml"
                xml_output.write_text(
                    exporter.export_target_xml(pohoda_invoices, config.target_xml),
                    encoding="utf-8",
                )
                export_message = f"Exported XML to {xml_output}"
            except Exception as error:
                status = "export_failed"
                export_message = f"XML export failed: {error}"
        elif successful_invoices:
            status = "missing_target_xml"
            export_message = "No target XML configuration defined"
        else:
            status = "parse_failed"
            export_message = "No invoices were parsed successfully"

        if successful_invoices and len(successful_invoices) != len(pdf_paths) and status == "processed":
            status = "processed_with_errors"

        summary = VendorProcessSummary(
            vendor=vendor,
            discovered_files=len(pdf_paths),
            successful_invoices=len(successful_invoices),
            failed_invoices=len(pdf_paths) - len(successful_invoices),
            status=status,
            message=export_message,
            xml_output=xml_output,
        )
        return summary, report_rows, xml_output, invoice_id

    def _build_processed_file_name(
        self,
        pdf_path: Path,
        assigned_invoice_id: int,
    ) -> str:
        """Build the copied invoice filename using the accounting invoice id suffix."""
        return f"{pdf_path.stem}_{assigned_invoice_id}{pdf_path.suffix}"

    def _build_processed_output_path(
        self,
        pdf_path: Path,
        invoices_dir: Path,
        output_dir: Path,
        processed_file: str,
    ) -> Path:
        """Build the output path that mirrors the input folder structure."""
        relative_parent = pdf_path.relative_to(invoices_dir).parent
        if relative_parent == Path("."):
            return output_dir / processed_file
        return output_dir / relative_parent / processed_file

    def _build_success_row(
        self,
        vendor: str,
        pdf_path: Path,
        processed_file: str,
        accounting_invoice_id: str,
        invoice: ParsedInvoice,
    ) -> InvoiceReportRow:
        """Build a report row for a successfully parsed invoice."""
        return InvoiceReportRow(
            vendor=vendor,
            source_file=pdf_path.name,
            processed_file=processed_file,
            accounting_invoice_id=accounting_invoice_id,
            status="parsed",
            invoice_number=invoice.invoice_number,
            received_invoice_number=invoice.received_invoice_number,
            issue_date=invoice.issue_date.isoformat(),
            supply_date=invoice.supply_date.isoformat(),
            due_date=invoice.due_date.isoformat(),
            variable_symbol=invoice.variable_symbol or invoice.received_invoice_number,
            total_amount=str(invoice.total_amount),
            message="",
        )

    def _write_report_csv(
        self,
        report_csv: Path,
        report_rows: list[InvoiceReportRow],
    ) -> None:
        """Write the per-invoice report as CSV."""
        field_names = [
            "vendor",
            "source_file",
            "processed_file",
            "accounting_invoice_id",
            "status",
            "invoice_number",
            "received_invoice_number",
            "issue_date",
            "supply_date",
            "due_date",
            "variable_symbol",
            "total_amount",
            "message",
        ]
        with report_csv.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()
            for row in report_rows:
                writer.writerow(row.__dict__)

    def _write_summary_txt(
        self,
        summary_txt: Path,
        batch_dir: Path,
        vendor_summaries: list[VendorProcessSummary],
    ) -> None:
        """Write a user-friendly processing summary."""
        lines = [
            "INVOICE BATCH PROCESSING SUMMARY",
            "=" * 80,
            f"Batch directory: {batch_dir}",
            "",
        ]

        for summary in vendor_summaries:
            lines.extend(
                [
                    f"Vendor: {summary.vendor}",
                    f"Status: {summary.status}",
                    f"Files found: {summary.discovered_files}",
                    f"Successful invoices: {summary.successful_invoices}",
                    f"Failed invoices: {summary.failed_invoices}",
                    f"XML output: {summary.xml_output or 'N/A'}",
                    f"Message: {summary.message or 'N/A'}",
                    "",
                ]
            )

        summary_txt.write_text("\n".join(lines), encoding="utf-8")

    def _build_readme(
        self,
        start_date: date,
        end_date: date,
        vendor_codes: list[str],
    ) -> str:
        """Build the README shown in a new batch directory."""
        lines = [
            "INVOICE BATCH DIRECTORY",
            "=" * 80,
            f"Date interval: {start_date.isoformat()} to {end_date.isoformat()}",
            "",
            "Put PDF invoices into each vendor's invoices directory.",
            "Processed XML files will be written into each vendor's output directory.",
            "",
            "Configured vendors:",
        ]
        lines.extend(f"- {vendor}" for vendor in vendor_codes)
        lines.extend(
            [
                "",
                "Supported parsers:",
            ]
        )
        lines.extend(f"- {vendor}" for vendor in sorted(self.parser_registry))
        return "\n".join(lines)