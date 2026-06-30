from decimal import Decimal

import pytest

from datetime import date

from src.models.parsed_invoice import ParsedInvoice, SupplierInfo, VATBreakdown


def test_vat_breakdown_accepts_small_adjustment_with_tolerance() -> None:
    breakdown = VATBreakdown.from_values(
        rate=Decimal("0.12"),
        base=Decimal("4360.99"),
        amount=Decimal("523.29"),
        vat_amount_tolerance=Decimal("0.10"),
    )

    assert breakdown.rate == Decimal("0.12")
    assert breakdown.base == Decimal("4360.99")
    assert breakdown.amount == Decimal("523.29")


def test_vat_breakdown_rejects_large_mismatch_by_default() -> None:
    with pytest.raises(ValueError, match="VAT amount 524.00 does not match expected 523.32"):
        VATBreakdown.from_values(
            rate=Decimal("0.12"),
            base=Decimal("4360.99"),
            amount=Decimal("524.00"),
        )


def test_vat_breakdown_normalizes_monetary_values_to_cents() -> None:
    breakdown = VATBreakdown(rate=Decimal("0.21"), base=Decimal("100.004"), amount=Decimal("21.006"))

    assert breakdown.base == Decimal("100.00")
    assert breakdown.amount == Decimal("21.01")


def test_parsed_invoice_accepts_normalized_invoice_identifier() -> None:
    invoice = ParsedInvoice(
        vendor="Phoenix",
        invoice_number="F2250048380",
        received_invoice_number="2250048380",
        issue_date=date(2025, 1, 15),
        due_date=date(2025, 2, 15),
        supply_date=date(2025, 1, 15),
        supplier=SupplierInfo(
            name="Example supplier",
            ic="12345678",
            dic="CZ12345678",
        ),
        vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100"), amount=Decimal("21"))],
        total_amount=Decimal("121.000"),
    )

    assert invoice.total_amount == Decimal("121.00")


def test_parsed_invoice_rejects_mismatched_invoice_identifier() -> None:
    with pytest.raises(ValueError, match="invoice_number and received_invoice_number must refer to the same logical identifier"):
        ParsedInvoice(
            vendor="Phoenix",
            invoice_number="F2250048380",
            received_invoice_number="2250048381",
            issue_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            supply_date=date(2025, 1, 15),
            supplier=SupplierInfo(
                name="Example supplier",
                ic="12345678",
                dic="CZ12345678",
            ),
            vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100"), amount=Decimal("21"))],
            total_amount=Decimal("121.00"),
        )


def test_parsed_invoice_rejects_credit_note_flag_mismatch() -> None:
    with pytest.raises(ValueError, match="invoice_type and is_credit_note must describe the same document type"):
        ParsedInvoice(
            vendor="Phoenix",
            invoice_number="F2250048380",
            received_invoice_number="2250048380",
            issue_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            supply_date=date(2025, 1, 15),
            supplier=SupplierInfo(
                name="Example supplier",
                ic="12345678",
                dic="CZ12345678",
            ),
            vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100"), amount=Decimal("21"))],
            total_amount=Decimal("121.00"),
            invoice_type="credit_note",
            is_credit_note=False,
        )


def test_parsed_invoice_rejects_supply_date_outside_one_week_window() -> None:
    with pytest.raises(ValueError, match="Supply date 2025-01-25 must be within 7 days of issue date 2025-01-15"):
        ParsedInvoice(
            vendor="Phoenix",
            invoice_number="F2250048380",
            received_invoice_number="2250048380",
            issue_date=date(2025, 1, 15),
            due_date=date(2025, 2, 15),
            supply_date=date(2025, 1, 25),
            supplier=SupplierInfo(
                name="Example supplier",
                ic="12345678",
                dic="CZ12345678",
            ),
            vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100"), amount=Decimal("21"))],
            total_amount=Decimal("121.00"),
        )


def test_parsed_invoice_rejects_due_date_before_supply_date() -> None:
    with pytest.raises(ValueError, match="Due date 2025-01-16 must be >= supply date 2025-01-17"):
        ParsedInvoice(
            vendor="Phoenix",
            invoice_number="F2250048380",
            received_invoice_number="2250048380",
            issue_date=date(2025, 1, 15),
            due_date=date(2025, 1, 16),
            supply_date=date(2025, 1, 17),
            supplier=SupplierInfo(
                name="Example supplier",
                ic="12345678",
                dic="CZ12345678",
            ),
            vat_breakdowns=[VATBreakdown(rate=Decimal("0.21"), base=Decimal("100"), amount=Decimal("21"))],
            total_amount=Decimal("121.00"),
        )