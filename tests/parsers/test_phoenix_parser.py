from decimal import Decimal
from pathlib import Path
from types import MethodType

import pytest
import yaml

from src.config.config_loader import ConfigLoader
from src.models.parsed_invoice import ParsedInvoice, SupplierInfo, VATBreakdown
from src.parsers.base_parser import PDFParseError
from src.parsers.vendors.phoenix_parser import PhoenixParser


def load_phoenix_fixtures() -> list[tuple[Path, Path]]:
    fixtures_dir = Path("tests/fixtures")
    pdf_dir = fixtures_dir / "pdfs" / "phoenix"
    expected_dir = fixtures_dir / "expected" / "phoenix"

    fixtures = []
    for yaml_file in expected_dir.glob("*.yaml"):
        invoice_id = yaml_file.stem.replace("invoice_", "")

        # Find corresponding PDF
        pdf_candidates = list(pdf_dir.glob(f"*{invoice_id}*.pdf"))
        if pdf_candidates:
            fixtures.append((pdf_candidates[0], yaml_file))

    return fixtures


def load_merck_sharp_fixtures() -> list[tuple[Path, Path]]:
    fixtures_dir = Path("tests/fixtures")
    pdf_dir = fixtures_dir / "pdfs" / "merck_sharp"
    expected_dir = fixtures_dir / "expected" / "merck_sharp"

    fixtures = []
    for yaml_file in expected_dir.glob("*.yaml"):
        invoice_id = yaml_file.stem

        pdf_candidates = list(pdf_dir.glob(f"*{invoice_id}*.pdf"))
        if pdf_candidates:
            fixtures.append((pdf_candidates[0], yaml_file))

    return fixtures


@pytest.fixture
def phoenix_parser():
    config_loader = ConfigLoader()
    config = config_loader.load_vendor_config("phoenix")
    return PhoenixParser(config)


@pytest.mark.parametrize(
    "pdf_path,expected_yaml_path", load_phoenix_fixtures(), ids=lambda x: x.stem
)
def test_phoenix_parser_against_fixtures(phoenix_parser, pdf_path, expected_yaml_path):
    """Test Phoenix parser output matches expected YAML fixtures.

    Args:
        phoenix_parser: PhoenixParser instance
        pdf_path: Path to test PDF
        expected_yaml_path: Path to expected values YAML
    """
    # Load expected data from YAML
    with open(expected_yaml_path, encoding="utf-8") as f:
        expected = yaml.safe_load(f)

    # Parse PDF
    parsed = phoenix_parser.parse(pdf_path)

    # Compare basic fields
    assert parsed.vendor == expected["vendor"], "Vendor mismatch"
    assert parsed.invoice_number == expected["invoice_number"], (
        "Invoice number mismatch"
    )
    assert parsed.received_invoice_number == expected["received_invoice_number"], (
        "Received invoice number mismatch"
    )

    # Compare dates
    assert parsed.issue_date.strftime("%Y-%m-%d") == expected["issue_date"], (
        "Issue date mismatch"
    )
    assert parsed.due_date.strftime("%Y-%m-%d") == expected["due_date"], (
        "Due date mismatch"
    )
    assert parsed.supply_date.strftime("%Y-%m-%d") == expected["supply_date"], (
        "Supply date mismatch"
    )

    # Compare supplier info
    expected_supplier = expected["supplier"]
    assert parsed.supplier.name == expected_supplier["name"], "Supplier name mismatch"
    # assert parsed.supplier.ic == expected_supplier["ic"], "Supplier IČO mismatch"
    # assert parsed.supplier.dic == expected_supplier["dic"], "Supplier DIČ mismatch"

    # Compare VAT breakdowns
    assert len(parsed.vat_breakdowns) == len(expected["vat_breakdowns"]), (
        "VAT breakdown count mismatch"
    )

    # Sort both lists by rate for comparison
    parsed_vat_sorted = sorted(parsed.vat_breakdowns, key=lambda x: x.rate)
    expected_vat_sorted = sorted(
        expected["vat_breakdowns"], key=lambda x: Decimal(x["rate"])
    )

    for parsed_vat, expected_vat in zip(parsed_vat_sorted, expected_vat_sorted):
        expected_rate = Decimal(expected_vat["rate"])
        expected_base = Decimal(expected_vat["base"])
        expected_amount = Decimal(expected_vat["amount"])

        assert parsed_vat.rate == expected_rate, (
            f"VAT rate mismatch: {parsed_vat.rate} != {expected_rate}"
        )
        assert abs(parsed_vat.base - expected_base) < Decimal("0.01"), (
            f"VAT base amount mismatch: {parsed_vat.base} != {expected_base}"
        )
        assert abs(parsed_vat.amount - expected_amount) < Decimal("0.01"), (
            f"VAT amount mismatch: {parsed_vat.amount} != {expected_amount}"
        )

    # Compare total amount
    expected_total = Decimal(expected["total_amount"])
    assert abs(parsed.total_amount - expected_total) < Decimal("0.01"), (
        f"Total amount mismatch: {parsed.total_amount} != {expected_total}"
    )

    # Compare variable symbol (can be None)
    expected_vs = expected.get("variable_symbol")
    if expected_vs is not None:
        assert parsed.variable_symbol == expected_vs, "Variable symbol mismatch"


@pytest.fixture
def merck_sharp_parser() -> PhoenixParser:
    config_loader = ConfigLoader()
    config = config_loader.load_vendor_config("merck_sharp")
    return PhoenixParser(config)


@pytest.mark.parametrize(
    "pdf_path,expected_yaml_path", load_merck_sharp_fixtures(), ids=lambda x: x.stem
)
def test_merck_sharp_parser_against_fixtures(
    merck_sharp_parser: PhoenixParser,
    pdf_path: Path,
    expected_yaml_path: Path,
) -> None:
    """Test Merck Sharp PDFs parse to the expected invoice data."""
    with open(expected_yaml_path, encoding="utf-8") as f:
        expected = yaml.safe_load(f)

    parsed = merck_sharp_parser.parse(pdf_path)

    assert parsed.vendor == expected["vendor"], "Vendor mismatch"
    assert parsed.invoice_number == expected["invoice_number"], "Invoice number mismatch"
    assert parsed.received_invoice_number == expected["received_invoice_number"], (
        "Received invoice number mismatch"
    )
    assert parsed.issue_date.strftime("%Y-%m-%d") == expected["issue_date"], (
        "Issue date mismatch"
    )
    assert parsed.due_date.strftime("%Y-%m-%d") == expected["due_date"], (
        "Due date mismatch"
    )
    assert parsed.supply_date.strftime("%Y-%m-%d") == expected["supply_date"], (
        "Supply date mismatch"
    )

    expected_supplier = expected["supplier"]
    assert parsed.supplier.name == expected_supplier["name"], "Supplier name mismatch"
    assert parsed.supplier.street == expected_supplier["street"], "Supplier street mismatch"
    assert parsed.supplier.city == expected_supplier["city"], "Supplier city mismatch"
    assert parsed.supplier.zip == expected_supplier["zip"], "Supplier zip mismatch"
    assert parsed.supplier.ic == expected_supplier["ic"], "Supplier IČO mismatch"
    assert parsed.supplier.dic == expected_supplier["dic"], "Supplier DIČ mismatch"

    assert len(parsed.vat_breakdowns) == len(expected["vat_breakdowns"]), (
        "VAT breakdown count mismatch"
    )

    parsed_vat_sorted = sorted(parsed.vat_breakdowns, key=lambda x: x.rate)
    expected_vat_sorted = sorted(
        expected["vat_breakdowns"], key=lambda x: Decimal(x["rate"])
    )

    for parsed_vat, expected_vat in zip(parsed_vat_sorted, expected_vat_sorted):
        expected_rate = Decimal(expected_vat["rate"])
        expected_base = Decimal(expected_vat["base"])
        expected_amount = Decimal(expected_vat["amount"])

        assert parsed_vat.rate == expected_rate, (
            f"VAT rate mismatch: {parsed_vat.rate} != {expected_rate}"
        )
        assert abs(parsed_vat.base - expected_base) < Decimal("0.01"), (
            f"VAT base amount mismatch: {parsed_vat.base} != {expected_base}"
        )
        assert abs(parsed_vat.amount - expected_amount) < Decimal("0.01"), (
            f"VAT amount mismatch: {parsed_vat.amount} != {expected_amount}"
        )

    expected_total = Decimal(expected["total_amount"])
    assert abs(parsed.total_amount - expected_total) < Decimal("0.01"), (
        f"Total amount mismatch: {parsed.total_amount} != {expected_total}"
    )


def test_parse_directory_parses_all_pdfs_in_filename_order(
    phoenix_parser: PhoenixParser,
    tmp_path: Path,
) -> None:
    """Test parsing all PDFs from a directory in deterministic order."""
    pdf_b = tmp_path / "b_invoice.pdf"
    pdf_a = tmp_path / "a_invoice.pdf"
    ignored = tmp_path / "notes.txt"
    pdf_b.write_text("", encoding="utf-8")
    pdf_a.write_text("", encoding="utf-8")
    ignored.write_text("ignore", encoding="utf-8")

    def fake_parse(self: PhoenixParser, pdf_path: Path) -> ParsedInvoice:
        invoice_number = pdf_path.stem
        return ParsedInvoice(
            vendor="Phoenix",
            invoice_number=invoice_number,
            received_invoice_number=invoice_number,
            issue_date=parsed_date,
            due_date=parsed_date,
            supply_date=parsed_date,
            supplier=SupplierInfo(name="Supplier", ic="12345678", dic="CZ12345678"),
            vat_breakdowns=[
                VATBreakdown(
                    rate=Decimal("0.21"),
                    base=Decimal("100.00"),
                    amount=Decimal("21.00"),
                )
            ],
            total_amount=Decimal("121.00"),
        )

    parsed_date = pytest.importorskip("datetime").date(2025, 1, 1)
    phoenix_parser.parse = MethodType(fake_parse, phoenix_parser)

    invoices = phoenix_parser.parse_directory(tmp_path)

    assert [invoice.invoice_number for invoice in invoices] == [
        "a_invoice",
        "b_invoice",
    ]


def test_parse_directory_raises_for_missing_directory(
    phoenix_parser: PhoenixParser,
    tmp_path: Path,
) -> None:
    """Test directory parsing fails fast for a missing directory."""
    missing_dir = tmp_path / "missing"

    with pytest.raises(PDFParseError, match="Invoice directory not found"):
        phoenix_parser.parse_directory(missing_dir)


def test_parse_directory_raises_for_file_path(
    phoenix_parser: PhoenixParser,
    tmp_path: Path,
) -> None:
    """Test directory parsing fails when given a file path."""
    file_path = tmp_path / "invoice.pdf"
    file_path.write_text("", encoding="utf-8")

    with pytest.raises(PDFParseError, match="Invoice path is not a directory"):
        phoenix_parser.parse_directory(file_path)
