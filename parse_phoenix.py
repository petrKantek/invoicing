"""Parse Phoenix invoice and output results to text file.

Simple CLI script to parse a Phoenix PDF invoice and save the extracted
data to a text file for review.
"""

from pathlib import Path

from src.config.config_loader import _default_loader
from src.parsers.vendors.phoenix_parser import PhoenixParser
from src.exporters.invoice_to_xml import InvoiceToXMLExporter


def main():
    """Parse Phoenix invoice and save to text file."""
    # Input PDF
    invoice = "f7021241452"
    pdf_path = Path(f"tests/fixtures/pdfs/phoenix/{invoice}.pdf")

    invoice = "7021283883"
    invoice = "2260015575"
    pdf_path = Path(f"data/phoenix/{invoice}.pdf")

    # Output text file
    output_path = Path(f"data/output/phoenix_parsed_{invoice}.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load Phoenix configuration
    phoenix_config = _default_loader.load_vendor_config("phoenix")

    # Create parser and parse invoice
    parser = PhoenixParser(phoenix_config)
    invoice = parser.parse(pdf_path)
    print(invoice)
    # Format output
    output_lines = [
        "=" * 80,
        "PHOENIX INVOICE PARSING RESULTS",
        "=" * 80,
        "",
        "INVOICE HEADER",
        "-" * 80,
        f"Invoice Number:         {invoice.invoice_number}",
        f"Received Invoice No:    {invoice.received_invoice_number}",
        f"Issue Date:             {invoice.issue_date.strftime('%d.%m.%Y')}",
        f"Due Date:               {invoice.due_date.strftime('%d.%m.%Y')}",
        f"Supply Date:            {invoice.supply_date.strftime('%d.%m.%Y')}",
        f"Variable Symbol:        {invoice.variable_symbol or 'N/A'}",
        "",
        "SUPPLIER INFORMATION",
        "-" * 80,
        f"Name:                   {invoice.supplier.name}",
        f"IČO:                    {invoice.supplier.ic}",
        f"DIČ:                    {invoice.supplier.dic}",
        "",
        "VAT BREAKDOWN",
        "-" * 80,
    ]

    for vat in invoice.vat_breakdowns:
        rate_percent = float(vat.rate) * 100
        output_lines.extend(
            [
                f"Rate {rate_percent:.0f}%:",
                f"  Base Amount:          {vat.base:,.2f} Kč",
                f"  VAT Amount:           {vat.amount:,.2f} Kč",
                f"  Total:                {vat.base + vat.amount:,.2f} Kč",
                "",
            ]
        )

    output_lines.extend(
        [
            "TOTALS",
            "-" * 80,
            f"Total Amount (incl. VAT): {invoice.total_amount:,.2f} Kč",
            "",
            "VALIDATION STATUS",
            "-" * 80,
            f"VAT Sum Check:          {sum(v.base + v.amount for v in invoice.vat_breakdowns):,.2f} Kč",
            f"Matches Total:          {'✓ YES' if abs(sum(v.base + v.amount for v in invoice.vat_breakdowns) - invoice.total_amount) < 0.01 else '✗ NO'}",
            "",
            "=" * 80,
        ]
    )

    xml_exp = InvoiceToXMLExporter()
    if phoenix_config.target_xml is None:
        raise ValueError("Phoenix config does not define target XML export settings")

    pohoda_invoice = xml_exp.export(invoice)
    xml = xml_exp.export_target_xml(pohoda_invoice, phoenix_config.target_xml)


    # Write to file (XML)
    with output_path.with_suffix(".xml").open("w", encoding="utf-8") as f:
        f.write(xml)

    # Write to file
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print("✓ Parsing successful!")
    print(f"✓ Results saved to: {output_path}")
    print(f"\nInvoice: {invoice.invoice_number}")
    print(f"Supplier: {invoice.supplier.name}")
    print(f"Total: {invoice.total_amount:,.2f} Kč")


if __name__ == "__main__":
    main()
