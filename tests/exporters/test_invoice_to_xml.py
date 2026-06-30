"""Tests for InvoiceToXMLExporter."""

from datetime import date
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytest

from src.config.config_loader import ConfigLoader
from src.exporters.invoice_to_xml import InvoiceToXMLExporter
from src.models.parsed_invoice import LineItem, ParsedInvoice, SupplierInfo, VATBreakdown
from src.models.vendor_config import TargetXMLConfig
from src.models.xml_types import PohodaFaktura, PohodaFirma, PohodaPolozka, PohodaSouhrnDPH


@pytest.fixture
def sample_supplier() -> SupplierInfo:
    """Create a sample supplier for testing."""
    return SupplierInfo(
        name="Phoenix Lékárenský Velkoobchod a.s.",
        ic="12345678",
        dic="CZ12345678",
        street="Hájkova 1",
        city="Praha",
        zip="15000",
        country="CZ",
    )


@pytest.fixture
def sample_invoice(sample_supplier: SupplierInfo) -> ParsedInvoice:
    """Create a sample invoice with all fields populated."""
    return ParsedInvoice(
        vendor="phoenix",
        invoice_number="F2250048380",
        received_invoice_number="2250048380",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[
            VATBreakdown(rate=Decimal("0.21"), base=Decimal("10000.00"), amount=Decimal("2100.00")),
            VATBreakdown(rate=Decimal("0.12"), base=Decimal("5000.00"), amount=Decimal("600.00")),
        ],
        total_amount=Decimal("17700.00"),
        variable_symbol="2250048380",
        constant_symbol="0308",
        description="Invoice for medical supplies",
        invoice_type="normal",
        is_credit_note=False,
    )


@pytest.fixture
def invoice_with_line_items(sample_supplier: SupplierInfo) -> ParsedInvoice:
    """Create an invoice with line items."""
    return ParsedInvoice(
        vendor="phoenix",
        invoice_number="F2250048380",
        received_invoice_number="2250048380",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[
            VATBreakdown(rate=Decimal("0.21"), base=Decimal("1000.00"), amount=Decimal("210.00"))
        ],
        total_amount=Decimal("1210.00"),
        variable_symbol="2250048380",
        line_items=[
            LineItem(
                description="Aspirin 100mg",
                quantity=Decimal("10"),
                unit="KS",
                unit_price=Decimal("50.00"),
                vat_rate=Decimal("0.21"),
                total_without_vat=Decimal("500.00"),
                total_with_vat=Decimal("605.00"),
            ),
            LineItem(
                description="Ibuprofen 400mg",
                quantity=Decimal("5"),
                unit="KS",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.21"),
                total_without_vat=Decimal("500.00"),
                total_with_vat=Decimal("605.00"),
            ),
        ],
    )


@pytest.fixture
def target_xml_config() -> TargetXMLConfig:
    """Create a minimal target XML config for serializer tests."""
    return TargetXMLConfig.model_validate(
        {
            "root_tag": "MoneyData",
            "root_attributes": {
                "ICAgendy": "71004378",
                "JazykVerze": "CZ",
            },
            "body": [
                {
                    "tag": "SeznamFaktPrij",
                    "children": [
                        {
                            "tag": "FaktPrij",
                            "repeat_for_each_invoice": True,
                            "children": [
                                {"tag": "Rada", "text": "2rr"},
                                {"tag": "Vystaveno", "dynamic_field": "Vystaveno"},
                                {"tag": "PlnenoDPH", "dynamic_field": "PlnenoDPH"},
                                {"tag": "Doruceno", "dynamic_field": "Doruceno"},
                                {"tag": "Splatno", "dynamic_field": "Splatno"},
                                {"tag": "VarSymbol", "dynamic_field": "VarSymbol"},
                                {"tag": "PrijatDokl", "dynamic_field": "PrijatDokl"},
                                {"tag": "Proplatit", "dynamic_field": "Proplatit"},
                                {
                                    "tag": "SouhrnDPH",
                                    "children": [
                                        {"tag": "Zaklad0", "dynamic_field": "Zaklad0"},
                                        {"tag": "Zaklad5", "dynamic_field": "Zaklad5"},
                                        {"tag": "Zaklad22", "dynamic_field": "Zaklad22"},
                                        {"tag": "DPH5", "dynamic_field": "DPH5"},
                                        {"tag": "DPH22", "dynamic_field": "DPH22"},
                                    ],
                                },
                                {"tag": "Celkem", "dynamic_field": "Celkem"},
                                {
                                    "tag": "DodOdb",
                                    "children": [
                                        {"tag": "ObchNazev", "text": "Fixed Supplier"}
                                    ],
                                },
                            ],
                        }
                    ],
                },
                {"tag": "SeznamFaktPrij_DPP"},
            ],
        }
    )


def test_export_basic_invoice(sample_invoice: ParsedInvoice) -> None:
    """Test exporting a basic invoice without line items."""
    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert isinstance(result, PohodaFaktura)
    assert result.Doklad is None  # Auto-generated by Pohoda
    assert result.PrijatDokl == "2250048380"
    assert result.Vystaveno == date(2025, 1, 15)
    assert result.PlnenoDPH == date(2025, 1, 15)
    assert result.Splatno == date(2025, 2, 15)
    assert result.VarSymbol == "2250048380"
    assert result.KonstSym == "0308"
    assert result.Popis == "Invoice for medical supplies"
    assert result.Druh == "N"


def test_export_supplier_info(sample_invoice: ParsedInvoice) -> None:
    """Test that supplier information is correctly converted."""
    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    supplier = result.DodOdb
    assert isinstance(supplier, PohodaFirma)
    assert supplier.Nazev == "Phoenix Lékárenský Velkoobchod a.s."
    assert supplier.IC == "12345678"
    assert supplier.DIC == "CZ12345678"
    assert supplier.Ulice == "Hájkova 1"
    assert supplier.Misto == "Praha"
    assert supplier.PSC == "15000"
    assert supplier.Stat == "CZ"


def test_export_uses_override_supplier_for_phoenix_invoice_with_variable_symbol_starting_with_8(
    sample_supplier: SupplierInfo,
) -> None:
    """Test that Phoenix invoices with variable symbols starting with 8 use the requested supplier data."""
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100.00"), amount=Decimal("21.00"))],
        total_amount=Decimal("121.00"),
        variable_symbol="82084805",
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    supplier = result.DodOdb
    assert supplier.Nazev == "Merck Sharp & Dohme s.r.o."
    assert supplier.IC == "28462564"
    assert supplier.DIC == "CZ28462564"
    assert supplier.Ulice == "Na Valentince 3336/4"
    assert supplier.Misto == "Praha"
    assert supplier.PSC == "15000"
    assert supplier.Stat == "CZ"


def test_export_vat_breakdown_multiple_rates(sample_invoice: ParsedInvoice) -> None:
    """Test VAT breakdown with multiple rates."""
    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    vat = result.SouhrnDPH
    assert isinstance(vat, PohodaSouhrnDPH)
    # 21% rate
    assert vat.Zaklad2 == Decimal("10000.00")
    assert vat.DPH2 == Decimal("2100.00")
    assert vat.ZakladZakl == Decimal("10000.00")
    assert vat.DPHZakl == Decimal("2100.00")
    # 12% rate
    assert vat.Zaklad1 == Decimal("5000.00")
    assert vat.DPH1 == Decimal("600.00")
    assert vat.ZakladSniz == Decimal("5000.00")
    assert vat.DPHSniz == Decimal("600.00")
    # 0% rate should be None
    assert vat.Zaklad3 is None
    assert vat.DPH3 is None


def test_export_vat_breakdown_zero_rate(sample_supplier: SupplierInfo) -> None:
    """Test VAT breakdown with 0% rate."""
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.00"), base=Decimal("1000.00"), amount=Decimal("0.00"))],
        total_amount=Decimal("1000.00"),
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    vat = result.SouhrnDPH
    assert vat.Zaklad3 == Decimal("1000.00")
    assert vat.DPH3 == Decimal("0.00")
    assert vat.Zaklad1 is None
    assert vat.Zaklad2 is None


def test_export_vat_breakdown_ten_percent_uses_reduced_bucket(
    sample_supplier: SupplierInfo,
) -> None:
    """Test that 10% VAT is exported through the reduced-rate bucket."""
    invoice = ParsedInvoice(
        vendor="alliance",
        invoice_number="A001",
        received_invoice_number="A001",
        issue_date=date(2021, 10, 15),
        supply_date=date(2021, 10, 13),
        due_date=date(2021, 11, 14),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.10"), base=Decimal("1095.92"), amount=Decimal("109.59"))],
        total_amount=Decimal("1205.51"),
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    assert result.SouhrnDPH.Zaklad1 == Decimal("1095.92")
    assert result.SouhrnDPH.DPH1 == Decimal("109.59")
    assert result.SouhrnDPH.Zaklad2 is None


def test_export_line_items(invoice_with_line_items: ParsedInvoice) -> None:
    """Test exporting invoice with line items."""
    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice_with_line_items)

    items = result.SeznamPolozek
    assert items is not None
    assert len(items) == 2

    item1 = items[0]
    assert isinstance(item1, PohodaPolozka)
    assert item1.Popis == "Aspirin 100mg"
    assert item1.PocetMJ == Decimal("10")
    assert item1.Cena == Decimal("50.00")
    assert item1.SazbaDPH == Decimal("21")
    assert item1.CenaTyp == 0
    assert item1.MJ == "KS"

    item2 = items[1]
    assert item2.Popis == "Ibuprofen 400mg"
    assert item2.PocetMJ == Decimal("5")
    assert item2.Cena == Decimal("100.00")


def test_export_invoice_without_line_items(sample_invoice: ParsedInvoice) -> None:
    """Test that invoices without line items have None for SeznamPolozek."""
    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert result.SeznamPolozek is None


def test_export_invoice_type_normal(sample_invoice: ParsedInvoice) -> None:
    """Test that normal invoice type is converted to 'N'."""
    sample_invoice.invoice_type = "normal"
    sample_invoice.is_credit_note = False

    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert result.Druh == "N"


def test_export_invoice_type_proforma(sample_invoice: ParsedInvoice) -> None:
    """Test that proforma invoice type is converted to 'P'."""
    sample_invoice.invoice_type = "proforma"
    sample_invoice.is_credit_note = False

    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert result.Druh == "P"


def test_export_invoice_type_credit_note(sample_invoice: ParsedInvoice) -> None:
    """Test that credit note is converted to 'D'."""
    sample_invoice.invoice_type = "credit_note"
    sample_invoice.is_credit_note = True

    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert result.Druh == "D"


def test_export_credit_note_flag_overrides_type(sample_invoice: ParsedInvoice) -> None:
    """Test that is_credit_note flag overrides invoice_type."""
    sample_invoice.invoice_type = "normal"
    sample_invoice.is_credit_note = True

    exporter = InvoiceToXMLExporter()
    result = exporter.export(sample_invoice)

    assert result.Druh == "D"


def test_export_truncates_long_line_item_descriptions(sample_supplier: SupplierInfo) -> None:
    """Test that line item descriptions longer than 90 chars are truncated."""
    long_description = "A" * 100
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100.00"), amount=Decimal("21.00"))],
        total_amount=Decimal("121.00"),
        line_items=[
            LineItem(
                description=long_description,
                quantity=Decimal("1"),
                unit="KS",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.21"),
                total_without_vat=Decimal("100.00"),
                total_with_vat=Decimal("121.00"),
            )
        ],
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    items = result.SeznamPolozek
    assert items is not None
    assert len(items[0].Popis) == 90
    assert items[0].Popis == "A" * 90


def test_export_optional_fields_none(sample_supplier: SupplierInfo) -> None:
    """Test exporting invoice with optional fields set to None."""
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100.00"), amount=Decimal("21.00"))],
        total_amount=Decimal("121.00"),
        variable_symbol=None,
        constant_symbol=None,
        description=None,
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    assert result.VarSymbol == "001"
    assert result.KonstSym is None
    assert result.Popis is None


def test_export_vat_rate_conversion_12_percent(sample_supplier: SupplierInfo) -> None:
    """Test that VAT rate 0.12 is converted to 12 for line items."""
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.12"), base=Decimal("100.00"), amount=Decimal("12.00"))],
        total_amount=Decimal("112.00"),
        line_items=[
            LineItem(
                description="Item with 12% VAT",
                quantity=Decimal("1"),
                unit="KS",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.12"),
                total_without_vat=Decimal("100.00"),
                total_with_vat=Decimal("112.00"),
            )
        ],
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    items = result.SeznamPolozek
    assert items is not None
    assert items[0].SazbaDPH == Decimal("12")


def test_export_vat_rate_conversion_0_percent(sample_supplier: SupplierInfo) -> None:
    """Test that VAT rate 0.00 is converted to 0 for line items."""
    invoice = ParsedInvoice(
        vendor="phoenix",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=sample_supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.00"), base=Decimal("100.00"), amount=Decimal("0.00"))],
        total_amount=Decimal("100.00"),
        line_items=[
            LineItem(
                description="Item with 0% VAT",
                quantity=Decimal("1"),
                unit="KS",
                unit_price=Decimal("100.00"),
                vat_rate=Decimal("0.00"),
                total_without_vat=Decimal("100.00"),
                total_with_vat=Decimal("100.00"),
            )
        ],
    )

    exporter = InvoiceToXMLExporter()
    result = exporter.export(invoice)

    items = result.SeznamPolozek
    assert items is not None
    assert items[0].SazbaDPH == Decimal("0")


def test_export_static_method() -> None:
    """Test that export can be called as static method."""
    supplier = SupplierInfo(
        name="Test Company", ic="12345678", dic="CZ12345678", street="Street 1", city="City", zip="12345", country="CZ"
    )
    invoice = ParsedInvoice(
        vendor="test",
        invoice_number="F001",
        received_invoice_number="001",
        issue_date=date(2025, 1, 15),
        supply_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supplier=supplier,
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100.00"), amount=Decimal("21.00"))],
        total_amount=Decimal("121.00"),
    )

    result = InvoiceToXMLExporter.export(invoice)
    assert isinstance(result, PohodaFaktura)
    assert result.Doklad is None  # Auto-generated by Pohoda


def test_export_target_xml_single_invoice(
    sample_invoice: ParsedInvoice,
    target_xml_config: TargetXMLConfig,
) -> None:
    """Test serializing one invoice into the configured target XML."""
    sample_invoice.supply_date = date(2025, 1, 16)

    pohoda_invoice = InvoiceToXMLExporter.export(sample_invoice)
    xml_output = InvoiceToXMLExporter.export_target_xml(
        pohoda_invoice,
        target_xml_config,
    )

    root = ET.fromstring(xml_output)
    faktura = root.find("./SeznamFaktPrij/FaktPrij")

    assert root.tag == "MoneyData"
    assert root.attrib["ICAgendy"] == "71004378"
    assert faktura is not None
    assert faktura.findtext("Rada") == "2rr"
    assert faktura.findtext("Vystaveno") == "2025-01-15"
    assert faktura.findtext("PlnenoDPH") == "2025-01-16"
    assert faktura.findtext("Doruceno") == "2025-01-16"
    assert faktura.findtext("Splatno") == "2025-02-15"
    assert faktura.findtext("VarSymbol") == "2250048380"
    assert faktura.findtext("PrijatDokl") == "2250048380"
    assert faktura.findtext("Proplatit") == "17700"
    assert faktura.find("SouhrnDPH") is not None
    assert faktura.findtext("./SouhrnDPH/Zaklad0") == "0"
    assert faktura.findtext("./SouhrnDPH/Zaklad5") == "5000"
    assert faktura.findtext("./SouhrnDPH/Zaklad22") == "10000"
    assert faktura.findtext("./SouhrnDPH/DPH5") == "600"
    assert faktura.findtext("./SouhrnDPH/DPH22") == "2100"
    assert faktura.findtext("Celkem") == "17700"
    assert faktura.findtext("./DodOdb/ObchNazev") == "Fixed Supplier"


def test_export_target_xml_multiple_invoices_repeats_invoice_nodes(
    sample_invoice: ParsedInvoice,
    target_xml_config: TargetXMLConfig,
) -> None:
    """Test serializing multiple invoices into repeated FaktPrij nodes."""
    second_invoice = sample_invoice.model_copy(deep=True)
    second_invoice.received_invoice_number = "2250048381"
    second_invoice.variable_symbol = "2250048381"

    first_pohoda_invoice = InvoiceToXMLExporter.export(sample_invoice)
    second_pohoda_invoice = InvoiceToXMLExporter.export(second_invoice)

    xml_output = InvoiceToXMLExporter.export_target_xml(
        [first_pohoda_invoice, second_pohoda_invoice],
        target_xml_config,
    )

    root = ET.fromstring(xml_output)
    faktury = root.findall("./SeznamFaktPrij/FaktPrij")

    assert len(faktury) == 2
    assert faktury[0].findtext("PrijatDokl") == "2250048380"
    assert faktury[1].findtext("PrijatDokl") == "2250048381"
    assert faktury[1].findtext("Doruceno") == "2025-01-15"


def test_phoenix_config_contains_target_xml() -> None:
    """Test that the Phoenix vendor config exposes target XML settings."""
    vendor_config = ConfigLoader().load_vendor_config("phoenix")

    assert vendor_config.target_xml is not None
    assert vendor_config.target_xml.root_tag == "MoneyData"
    assert vendor_config.target_xml.body[0].tag == "SeznamFaktPrij"


def test_merck_sharp_config_uses_alternative_supplier_xml() -> None:
    """Test that the Merck Sharp config reuses Phoenix parsing with a different supplier XML block."""
    vendor_config = ConfigLoader().load_vendor_config("merck_sharp")

    assert vendor_config.vendor_name == "Merck Sharp & Dohme s.r.o."
    assert vendor_config.vendor_code == "merck_sharp"
    assert vendor_config.export_supplier is not None
    assert vendor_config.export_supplier.tag == "DodOdb"
    assert vendor_config.export_supplier.children[0].text == "Merck Sharp & Dohme s.r.o."
    assert vendor_config.export_supplier.children[1].tag == "ObchAdresa"
    assert vendor_config.export_supplier.children[1].children[0].text == "Na Valentince 3336/4"
    assert vendor_config.export_supplier.children[1].children[1].text == "Praha"
    assert vendor_config.export_supplier.children[1].children[2].text == "15000"
    assert vendor_config.export_supplier.children[1].children[3].text == "Česká republika"
    assert vendor_config.export_supplier.children[1].children[4].text == "CZ"
    assert vendor_config.export_supplier.children[2].text == "Merck Sharp & Dohme s.r.o."
    assert vendor_config.export_supplier.children[3].text == "28462564"
    assert vendor_config.export_supplier.children[4].text == "CZ28462564"
    assert vendor_config.export_supplier.children[5].tag == "FaktAdresa"
    assert vendor_config.export_supplier.children[5].children[0].text == "Na Valentince 3336/4"
    assert vendor_config.export_supplier.children[5].children[1].text == "Praha"
    assert vendor_config.export_supplier.children[5].children[2].text == "15000"
    assert vendor_config.export_supplier.children[5].children[3].text == "Česká republika"
    assert vendor_config.export_supplier.children[5].children[4].text == "CZ"
    assert vendor_config.export_supplier.children[6].text == "{E18BD06C-7F11-4BCD-BF24-5AF57CCC8735}"
    assert vendor_config.export_supplier.children[7].text == "1"
    assert vendor_config.export_supplier.children[8].text == "0"
    assert vendor_config.export_supplier.children[9].text == "Citibank Europe plc"
    assert vendor_config.export_supplier.children[10].text == "2051460102"
    assert vendor_config.export_supplier.children[11].text == "2600"
    assert vendor_config.export_supplier.children[12].tag == "SeznamBankSpojeni"
    assert vendor_config.export_supplier.children[12].children[0].tag == "BankSpojeni"
    assert vendor_config.export_supplier.children[12].children[0].children[0].text == "2051460508"
    assert vendor_config.export_supplier.children[12].children[0].children[1].text == "2600"
