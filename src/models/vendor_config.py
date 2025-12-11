"""Vendor configuration models for PDF invoice parsing.

This module defines Pydantic models for vendor-specific configuration
loaded from YAML files. These configurations specify where to find
specific fields in vendor PDFs.
"""

from pydantic import BaseModel, Field


class FieldPosition(BaseModel):
    """Position specification for a field in a PDF."""

    page: int = Field(ge=1, description="Page number (1-indexed)")
    x_min: float = Field(ge=0, description="Minimum X coordinate")
    x_max: float = Field(ge=0, description="Maximum X coordinate")
    y_min: float = Field(ge=0, description="Minimum Y coordinate")
    y_max: float = Field(ge=0, description="Maximum Y coordinate")
    pattern: str | None = Field(
        default=None, description="Regex pattern to extract value from text"
    )


class FieldConfig(BaseModel):
    """Configuration for extracting a specific field from PDF."""

    position: FieldPosition | None = Field(
        default=None, description="Position-based extraction config"
    )
    keyword_search: str | None = Field(
        default=None, description="Keyword to search for, then extract nearby value"
    )
    extraction_strategy: str = Field(
        default="position",
        description="Extraction strategy: 'position', 'keyword', 'pattern'",
    )
    required: bool = Field(default=True, description="Whether this field is required")
    validation_pattern: str | None = Field(
        default=None, description="Regex pattern for validating extracted value"
    )


class VATBreakdownConfig(BaseModel):
    """Configuration for extracting VAT breakdown information."""

    rate_21_base: FieldConfig
    rate_21_vat: FieldConfig
    rate_12_base: FieldConfig
    rate_12_vat: FieldConfig 
    rate_0_base: FieldConfig 


class SupplierConfig(BaseModel):
    """Configuration for extracting supplier information."""

    name: FieldConfig
    address: FieldConfig
    ic: FieldConfig
    dic: FieldConfig


class InvoiceHeaderConfig(BaseModel):
    """Configuration for extracting invoice header information."""

    invoice_number: FieldConfig
    issue_date: FieldConfig
    due_date: FieldConfig
    supply_date: FieldConfig
    variable_symbol: FieldConfig | None = None


class VendorConfiguration(BaseModel):
    """Complete configuration for a specific vendor's invoice format."""

    vendor_name: str = Field(description="Vendor name (e.g., 'Phoenix')")
    vendor_code: str = Field(
        description="Short vendor code for file naming (e.g., 'PHX')"
    )
    header: InvoiceHeaderConfig
    supplier: SupplierConfig
    vat_breakdown: VATBreakdownConfig
    total_amount: FieldConfig = Field(description="Total amount with VAT")

