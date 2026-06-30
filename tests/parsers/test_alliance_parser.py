from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from src.config.config_loader import ConfigLoader
from src.parsers.vendors.alliance_parser import AllianceParser


def load_alliance_fixtures() -> list[tuple[Path, Path]]:
    fixtures_dir = Path("tests/fixtures")
    pdf_dir = fixtures_dir / "pdfs" / "alliance"
    expected_dir = fixtures_dir / "expected" / "alliance"

    fixtures = []
    for yaml_file in expected_dir.glob("*.yaml"):
        pdf_candidates = list(pdf_dir.glob(f"*{yaml_file.stem}*.pdf"))
        if pdf_candidates:
            fixtures.append((pdf_candidates[0], yaml_file))

    return fixtures


def test_alliance_parser_handles_batch_invoice_vat_format() -> None:
    config = ConfigLoader().load_vendor_config("alliance")
    parser = AllianceParser(config)

    parsed = parser.parse(Path("runs/2026-05-01_2026-05-10/alliance/invoices/FAVU2026242611852.pdf"))

    assert parsed.invoice_number == "242611852"
    assert parsed.received_invoice_number == "242611852"
    assert parsed.total_amount == Decimal("5826.65")
    assert parsed.supplier.name == "Alliance Healthcare s.r.o."
    assert any(
        vat.rate == Decimal("0.12")
        and vat.base == Decimal("5202.36")
        and vat.amount == Decimal("624.29")
        for vat in parsed.vat_breakdowns
    )


def test_alliance_parser_accepts_vat_rounding_mismatch() -> None:
    config = ConfigLoader().load_vendor_config("alliance")
    parser = AllianceParser(config)

    parsed = parser.parse(Path("runs/2026-05-11_2026-05-31/alliance/invoices/FAVU2026242612480.pdf"))

    assert parsed.invoice_number == "242612480"
    assert parsed.total_amount == Decimal("2311.78")
    assert any(
        vat.rate == Decimal("0.12") and vat.base == Decimal("1900.49")
        for vat in parsed.vat_breakdowns
    )


@pytest.mark.parametrize(
    "pdf_path,expected_yaml_path", load_alliance_fixtures(), ids=lambda x: x.stem
)
def test_alliance_parser_against_fixtures(pdf_path: Path, expected_yaml_path: Path) -> None:
    config = ConfigLoader().load_vendor_config("alliance")
    parser = AllianceParser(config)

    with expected_yaml_path.open(encoding="utf-8") as f:
        expected = yaml.safe_load(f)

    parsed = parser.parse(pdf_path)

    assert config.target_xml is not None
    assert parsed.vendor == expected["vendor"]
    assert parsed.invoice_number == expected["invoice_number"]
    assert parsed.received_invoice_number == expected["received_invoice_number"]
    assert parsed.issue_date.strftime("%Y-%m-%d") == expected["issue_date"]
    assert parsed.due_date.strftime("%Y-%m-%d") == expected["due_date"]
    assert parsed.supply_date.strftime("%Y-%m-%d") == expected["supply_date"]
    assert parsed.supplier.name == expected["supplier"]["name"]
    assert parsed.supplier.ic == expected["supplier"]["ic"]
    assert parsed.supplier.dic == expected["supplier"]["dic"]
    assert parsed.supplier.street == expected["supplier"]["street"]
    assert parsed.supplier.city == expected["supplier"]["city"]
    assert parsed.supplier.zip == expected["supplier"]["zip"]
    assert parsed.total_amount == Decimal(expected["total_amount"])
    assert parsed.variable_symbol is None
    assert len(parsed.vat_breakdowns) == len(expected["vat_breakdowns"])

    parsed_vat_sorted = sorted(parsed.vat_breakdowns, key=lambda vat: vat.rate)
    expected_vat_sorted = sorted(expected["vat_breakdowns"], key=lambda vat: Decimal(vat["rate"]))

    for parsed_vat, expected_vat in zip(parsed_vat_sorted, expected_vat_sorted):
        assert parsed_vat.rate == Decimal(expected_vat["rate"])
        assert parsed_vat.base == Decimal(expected_vat["base"])
        assert parsed_vat.amount == Decimal(expected_vat["amount"])

    seznam_fakt_prij = config.target_xml.body[0]
    fakt_prij = seznam_fakt_prij.children[0]
    sazba_dph1 = next(child for child in fakt_prij.children if child.tag == "SazbaDPH1")
    assert sazba_dph1.text == "10"