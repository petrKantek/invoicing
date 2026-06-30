"""Pydantic models for parsed invoice data."""

import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DEFAULT_VAT_AMOUNT_TOLERANCE = Decimal("0.02")
MONEY_QUANTUM = Decimal("0.01")
MAX_ISSUE_SUPPLY_DATE_DELTA_DAYS = 7

# VAT rate literal - currently supported rates across fixture invoices.
VATRate = Literal[
    Decimal("0.21"),
    Decimal("0.15"),
    Decimal("0.12"),
    Decimal("0.10"),
    Decimal("0.00"),
]


class VATBreakdown(BaseModel):
    """VAT breakdown for a single tax rate."""

    rate: Decimal = Field(..., description="VAT rate (0.21, 0.15, 0.12, 0.10, or 0.00)")
    base: Decimal = Field(..., description="Base amount before VAT")
    amount: Decimal = Field(..., description="VAT amount")

    @field_validator("rate")
    @classmethod
    def validate_vat_rate(cls, v: Decimal) -> Decimal:
        """Validate that VAT rate is one of the allowed values."""
        allowed_rates = {
            Decimal("0.21"),
            Decimal("0.15"),
            Decimal("0.12"),
            Decimal("0.10"),
            Decimal("0.00"),
        }
        if v not in allowed_rates:
            raise ValueError(f"VAT rate must be one of {allowed_rates}, got {v}")
        return v

    @field_validator("base", "amount")
    @classmethod
    def normalize_money(cls, v: Decimal) -> Decimal:
        """Normalize VAT monetary values to cents."""
        return v.quantize(MONEY_QUANTUM)

    @field_validator("amount")
    @classmethod
    def validate_vat_calculation(cls, v: Decimal, info) -> Decimal:
        """Validate that VAT amount matches base * rate within a practical tolerance."""
        if "rate" in info.data and "base" in info.data:
            expected = (info.data["base"] * info.data["rate"]).quantize(Decimal("0.01"))
            tolerance = DEFAULT_VAT_AMOUNT_TOLERANCE
            if info.context:
                tolerance = info.context.get("vat_amount_tolerance", tolerance)
            if abs(v - expected) > tolerance:
                raise ValueError(
                    f"VAT amount {v} does not match expected {expected} "
                    f"(base {info.data['base']} * rate {info.data['rate']})"
                )
        return v

    @classmethod
    def from_values(
        cls,
        rate: Decimal,
        base: Decimal,
        amount: Decimal,
        vat_amount_tolerance: Decimal | None = None,
    ) -> "VATBreakdown":
        """Build a VAT breakdown with an optional validation tolerance."""
        context = None
        if vat_amount_tolerance is not None:
            context = {"vat_amount_tolerance": vat_amount_tolerance}

        return cls.model_validate(
            {"rate": rate, "base": base, "amount": amount},
            context=context,
        )


class SupplierInfo(BaseModel):
    """Supplier/vendor information."""

    name: str = Field(..., max_length=255)
    ic: str = Field(..., description="IČ (Company ID)", min_length=8, max_length=8)
    dic: str | None = Field(None, description="DIČ (VAT ID)", max_length=20)
    street: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    zip: str | None = Field(None, max_length=20)
    country: str | None = Field(
        None, max_length=2, description="ISO 3166-1 alpha-2 country code"
    )

    @field_validator("ic")
    @classmethod
    def validate_ic(cls, v: str) -> str:
        """Validate IČ format (must be 8 digits)."""
        if not v.isdigit():
            raise ValueError(f"IČ must contain only digits, got: {v}")
        if len(v) != 8:
            raise ValueError(f"IČ must be exactly 8 digits, got: {v}")
        return v


class LineItem(BaseModel):
    """Invoice line item."""

    description: str = Field(..., max_length=500)
    quantity: Decimal = Field(..., ge=0)
    unit: str = Field(..., max_length=10)
    unit_price: Decimal = Field(..., ge=0)
    vat_rate: Decimal
    total_without_vat: Decimal = Field(..., ge=0)
    total_with_vat: Decimal = Field(..., ge=0)

    @field_validator("vat_rate")
    @classmethod
    def validate_vat_rate(cls, v: Decimal) -> Decimal:
        """Validate that VAT rate is one of the allowed values."""
        allowed_rates = {
            Decimal("0.21"),
            Decimal("0.15"),
            Decimal("0.12"),
            Decimal("0.10"),
            Decimal("0.00"),
        }
        if v not in allowed_rates:
            raise ValueError(f"VAT rate must be one of {allowed_rates}, got {v}")
        return v

    @field_validator("unit_price", "total_without_vat", "total_with_vat")
    @classmethod
    def normalize_money(cls, v: Decimal) -> Decimal:
        """Normalize line-item monetary values to cents."""
        return v.quantize(MONEY_QUANTUM)


class ParsedInvoice(BaseModel):
    """Complete parsed invoice data."""

    # Metadata
    vendor: str = Field(..., description="Vendor identifier (phoenix, alliance, etc.)")

    # Invoice identification
    invoice_number: str = Field(
        ..., max_length=50, description="Invoice number from PDF"
    )
    received_invoice_number: str = Field(
        ..., max_length=50, description="PrijatDokl - for received invoices"
    )

    # Dates
    issue_date: date = Field(..., description="Date of issue (Vystaveno)")
    due_date: date = Field(..., description="Due date (Splatno)")
    supply_date: date = Field(..., description="Tax point date (PlnenoDPH)")

    # Supplier information
    supplier: SupplierInfo

    # Customer information (optional - may not be needed for received invoices)
    customer: SupplierInfo | None = None

    # Amounts and VAT
    vat_breakdowns: list[VATBreakdown] = Field(
        ..., min_length=1, description="VAT breakdown by rate"
    )
    total_amount: Decimal = Field(..., description="Total amount including VAT")

    # Payment details
    variable_symbol: str | None = Field(None, max_length=20)
    constant_symbol: str | None = Field(None, max_length=4)
    specific_symbol: str | None = Field(None, max_length=20)

    # Optional fields
    description: str | None = Field(
        None, max_length=500, description="Invoice description"
    )
    note: str | None = Field(None, description="Additional notes")

    # Invoice type
    invoice_type: Literal["normal", "credit_note", "proforma"] = Field(default="normal")
    is_credit_note: bool = Field(default=False)

    # Line items (optional)
    line_items: list[LineItem] | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: date, info) -> date:
        """Validate that due date is not before issue or supply date."""
        if "issue_date" in info.data and v < info.data["issue_date"]:
            raise ValueError(
                f"Due date {v} must be >= issue date {info.data['issue_date']}"
            )
        if "supply_date" in info.data and v < info.data["supply_date"]:
            raise ValueError(
                f"Due date {v} must be >= supply date {info.data['supply_date']}"
            )
        return v

    @field_validator("supply_date")
    @classmethod
    def validate_supply_date(cls, v: date, info) -> date:
        """Validate that supply date is close to the issue date."""
        if "issue_date" in info.data:
            days_diff = (v - info.data["issue_date"]).days
            if abs(days_diff) > MAX_ISSUE_SUPPLY_DATE_DELTA_DAYS:
                raise ValueError(
                    f"Supply date {v} must be within {MAX_ISSUE_SUPPLY_DATE_DELTA_DAYS} days of "
                    f"issue date {info.data['issue_date']} ({days_diff} days difference)"
                )
        return v

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: Decimal, info) -> Decimal:
        """Validate that total amount matches VAT breakdown sum."""
        v = v.quantize(MONEY_QUANTUM)
        if "vat_breakdowns" in info.data:
            vat_sum = sum(vat.base + vat.amount for vat in info.data["vat_breakdowns"])
            # Allow small rounding differences (0.01)
            if abs(vat_sum - v) > MONEY_QUANTUM:
                raise ValueError(
                    f"VAT breakdown sum ({vat_sum}) does not match total amount ({v}). "
                    f"Difference: {abs(vat_sum - v)}"
                )
        return v

    def model_post_init(self, __context) -> None:
        """Validate cross-field consistency after model construction."""
        if self.due_date < self.supply_date:
            raise ValueError(
                f"Due date {self.due_date} must be >= supply date {self.supply_date}"
            )

        issue_supply_days_diff = (self.supply_date - self.issue_date).days
        if abs(issue_supply_days_diff) > MAX_ISSUE_SUPPLY_DATE_DELTA_DAYS:
            raise ValueError(
                f"Supply date {self.supply_date} must be within {MAX_ISSUE_SUPPLY_DATE_DELTA_DAYS} days of "
                f"issue date {self.issue_date} ({issue_supply_days_diff} days difference)"
            )

        normalized_invoice_number = self._normalize_invoice_identifier(self.invoice_number)
        normalized_received_invoice_number = self._normalize_invoice_identifier(
            self.received_invoice_number
        )

        if normalized_invoice_number != normalized_received_invoice_number:
            raise ValueError(
                "invoice_number and received_invoice_number must refer to the same "
                f"logical identifier (got {self.invoice_number!r} and {self.received_invoice_number!r})"
            )

        if (self.invoice_type == "credit_note") != self.is_credit_note:
            raise ValueError(
                "invoice_type and is_credit_note must describe the same document type"
            )

    @staticmethod
    def _normalize_invoice_identifier(value: str) -> str:
        """Normalize invoice identifiers for cross-field comparison."""
        stripped_value = value.strip().upper()
        match = re.fullmatch(r"[A-Z]+(\d+)", stripped_value)
        if match is not None:
            return match.group(1)
        return stripped_value

    model_config = {"frozen": False, "validate_assignment": True}
