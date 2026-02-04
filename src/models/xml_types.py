"""XML type mappings for Pohoda accounting system.

This module defines Pydantic models that map to Pohoda XML schema types
defined in __Faktura.xsd. These models ensure data exported to XML
matches the expected Pohoda format.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PohodaFirma(BaseModel):
    """Supplier/customer company information for Pohoda XML (firmaType)."""

    Nazev: str = Field(max_length=255, description="Company name")
    IC: str = Field(max_length=15, description="Company registration number (IČ)")
    DIC: str | None = Field(default=None, max_length=18, description="VAT number (DIČ)")
    Ulice: str | None = Field(default=None, max_length=64, description="Street")
    Misto: str | None = Field(default=None, max_length=45, description="City")
    PSC: str | None = Field(default=None, max_length=15, description="Postal code")
    Stat: str | None = Field(
        default=None, max_length=2, description="Country code (ISO 3166-1 alpha-2)"
    )


class PohodaSouhrnDPH(BaseModel):
    """VAT breakdown summary for Pohoda XML (souhrnDPHType)."""

    Zaklad1: Decimal | None = Field(
        default=None, ge=0, description="Base amount for reduced VAT rate (12%)"
    )
    DPH1: Decimal | None = Field(
        default=None, ge=0, description="VAT amount for reduced rate (12%)"
    )
    Zaklad2: Decimal | None = Field(
        default=None, ge=0, description="Base amount for standard VAT rate (21%)"
    )
    DPH2: Decimal | None = Field(
        default=None, ge=0, description="VAT amount for standard rate (21%)"
    )
    Zaklad3: Decimal | None = Field(
        default=None, ge=0, description="Base amount for 0% VAT rate"
    )
    DPH3: Decimal | None = Field(default=None, ge=0, description="VAT amount (0)")
    ZakladSniz: Decimal | None = Field(
        default=None, ge=0, description="Total base for reduced rates"
    )
    DPHSniz: Decimal | None = Field(
        default=None, ge=0, description="Total VAT for reduced rates"
    )
    ZakladZakl: Decimal | None = Field(
        default=None, ge=0, description="Total base for standard rate"
    )
    DPHZakl: Decimal | None = Field(
        default=None, ge=0, description="Total VAT for standard rate"
    )

    @field_validator("DPH1", "DPH2", "DPH3", "DPHSniz", "DPHZakl")
    @classmethod
    def round_to_two_decimals(cls, v: Decimal | None) -> Decimal | None:
        """Round VAT amounts to 2 decimal places."""
        if v is None:
            return None
        return round(v, 2)


class PohodaPolozka(BaseModel):
    """Invoice line item for Pohoda XML (polFakturyType)."""

    Popis: str = Field(max_length=90, description="Item description")
    PocetMJ: Decimal = Field(ge=0, description="Quantity")
    SazbaDPH: Decimal = Field(description="VAT rate as percentage (e.g., 21.0)")
    Cena: Decimal = Field(description="Unit price")
    CenaTyp: int = Field(
        default=0, ge=0, le=3, description="Price type: 0=without VAT, 1=with VAT"
    )
    Katalog: str | None = Field(
        default=None, max_length=60, description="Catalog number"
    )
    MJ: str | None = Field(default=None, max_length=10, description="Unit of measure")

    @field_validator("SazbaDPH")
    @classmethod
    def validate_vat_rate(cls, v: Decimal) -> Decimal:
        """Validate that VAT rate is one of the allowed values."""
        allowed_rates = {Decimal("0"), Decimal("12"), Decimal("21")}
        if v not in allowed_rates:
            raise ValueError(f"VAT rate must be one of {allowed_rates}, got {v}")
        return v


class PohodaFaktura(BaseModel):
    """Pohoda invoice document (fakturaType)."""

    Doklad: str | None = Field(
        default=None, max_length=10, description="Invoice number"
    )
    Rada: str | None = Field(
        default=None, max_length=5, description="Document series code"
    )
    Popis: str | None = Field(
        default=None, max_length=50, description="Invoice description"
    )
    Vystaveno: date = Field(description="Issue date")
    PlnenoDPH: date = Field(description="Tax point date (supply date)")
    Splatno: date = Field(description="Due date")
    VarSymbol: str | None = Field(
        default=None, max_length=20, description="Variable symbol"
    )
    KonstSym: str | None = Field(
        default=None, max_length=4, description="Constant symbol"
    )
    PrijatDokl: str | None = Field(
        default=None, max_length=50, description="Received invoice number"
    )
    Druh: str | None = Field(
        default="N",
        max_length=1,
        description="Invoice type: N=normal, Z=advance, P=proforma, D=tax document",
    )
    Ucet: str | None = Field(
        default=None, max_length=10, description="Bank account/cash register code"
    )
    SouhrnDPH: PohodaSouhrnDPH = Field(description="VAT breakdown")
    DodOdb: PohodaFirma = Field(description="Supplier information")
    SeznamPolozek: list[PohodaPolozka] | None = Field(
        default=None, description="List of invoice line items"
    )

    @field_validator("Druh")
    @classmethod
    def validate_invoice_type(cls, v: str | None) -> str | None:
        """Validate invoice type code."""
        if v is None:
            return None
        allowed_types = {"N", "Z", "P", "L", "F", "D"}
        if v not in allowed_types:
            raise ValueError(f"Invoice type must be one of {allowed_types}, got '{v}'")
        return v
