"""Pydantic models for parsed invoice data."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# VAT rate literal - only these values allowed: 21%, 12%, 0%
VATRate = Literal[Decimal("0.21"), Decimal("0.12"), Decimal("0.00")]


class VATBreakdown(BaseModel):
    """VAT breakdown for a single tax rate."""

    rate: Decimal = Field(..., description="VAT rate (0.21, 0.12, or 0.00)")
    base: Decimal = Field(..., description="Base amount before VAT", ge=0)
    amount: Decimal = Field(..., description="VAT amount", ge=0)

    @field_validator("rate")
    @classmethod
    def validate_vat_rate(cls, v: Decimal) -> Decimal:
        """Validate that VAT rate is one of the allowed values."""
        allowed_rates = {Decimal("0.21"), Decimal("0.12"), Decimal("0.00")}
        if v not in allowed_rates:
            raise ValueError(f"VAT rate must be one of {allowed_rates}, got {v}")
        return v

    @field_validator("amount")
    @classmethod
    def validate_vat_calculation(cls, v: Decimal, info) -> Decimal:
        """Validate that VAT amount matches base * rate."""
        if "rate" in info.data and "base" in info.data:
            expected = (info.data["base"] * info.data["rate"]).quantize(Decimal("0.01"))
            # Allow small rounding differences (0.01)
            if abs(v - expected) > Decimal("0.01"):
                raise ValueError(
                    f"VAT amount {v} does not match expected {expected} "
                    f"(base {info.data['base']} * rate {info.data['rate']})"
                )
        return v


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
        allowed_rates = {Decimal("0.21"), Decimal("0.12"), Decimal("0.00")}
        if v not in allowed_rates:
            raise ValueError(f"VAT rate must be one of {allowed_rates}, got {v}")
        return v


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
    total_amount: Decimal = Field(..., ge=0, description="Total amount including VAT")

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
        """Validate that due date is not before issue date."""
        if "issue_date" in info.data and v < info.data["issue_date"]:
            raise ValueError(
                f"Due date {v} must be >= issue date {info.data['issue_date']}"
            )
        return v

    @field_validator("supply_date")
    @classmethod
    def validate_supply_date(cls, v: date, info) -> date:
        """Validate that supply date is reasonable."""
        if "issue_date" in info.data:
            # Supply date should generally be close to issue date
            # Allow up to 90 days before or 30 days after issue date
            days_diff = (v - info.data["issue_date"]).days
            if days_diff < -90 or days_diff > 30:
                raise ValueError(
                    f"Supply date {v} is unusually far from issue date {info.data['issue_date']} "
                    f"({days_diff} days difference)"
                )
        return v

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: Decimal, info) -> Decimal:
        """Validate that total amount matches VAT breakdown sum."""
        if "vat_breakdowns" in info.data:
            vat_sum = sum(vat.base + vat.amount for vat in info.data["vat_breakdowns"])
            # Allow small rounding differences (0.01)
            if abs(vat_sum - v) > Decimal("0.01"):
                raise ValueError(
                    f"VAT breakdown sum ({vat_sum}) does not match total amount ({v}). "
                    f"Difference: {abs(vat_sum - v)}"
                )
        return v

    model_config = {"frozen": False, "validate_assignment": True}
