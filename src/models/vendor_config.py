"""Vendor configuration models for invoice parsing and export.

This module defines Pydantic models for vendor-specific configuration
loaded from YAML files. These configurations specify how to parse fields
from vendor PDFs and how to render target XML payloads.
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

    rate_21_base: FieldConfig | None = None
    rate_21_vat: FieldConfig | None = None
    rate_15_base: FieldConfig | None = None
    rate_15_vat: FieldConfig | None = None
    rate_12_base: FieldConfig | None = None
    rate_12_vat: FieldConfig | None = None
    rate_10_base: FieldConfig | None = None
    rate_10_vat: FieldConfig | None = None
    rate_0_base: FieldConfig | None = None


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


class TargetXMLElement(BaseModel):
    """Declarative XML element template for config-driven serialization."""

    tag: str = Field(min_length=1, description="XML tag name")
    text: str | None = Field(default=None, description="Static text content")
    dynamic_field: str | None = Field(
        default=None,
        description="Dynamic invoice field name resolved during serialization",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Element attributes",
    )
    children: list["TargetXMLElement"] = Field(
        default_factory=list,
        description="Nested child elements in output order",
    )
    repeat_for_each_invoice: bool = Field(
        default=False,
        description="Repeat this element once for each invoice in the export",
    )


class TargetXMLConfig(BaseModel):
    """Configuration for target XML serialization."""

    root_tag: str = Field(default="MoneyData", min_length=1)
    root_attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Attributes applied to the root XML element",
    )
    body: list[TargetXMLElement] = Field(
        default_factory=list,
        description="Ordered XML template below the root element",
    )


class VendorExportOverrides(BaseModel):
    """Vendor-specific overrides layered on top of the shared export config."""

    root_attributes: dict[str, str] = Field(default_factory=dict)
    invoice_defaults: dict[str, str] = Field(default_factory=dict)


class SharedExportConfig(BaseModel):
    """Reusable export configuration shared by multiple vendors."""

    root_tag: str = Field(default="MoneyData", min_length=1)
    root_attributes: dict[str, str] = Field(default_factory=dict)
    invoice_defaults: dict[str, str] = Field(default_factory=dict)
    my_company: TargetXMLElement


TargetXMLElement.model_rebuild()


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
    export_supplier: TargetXMLElement | None = Field(
        default=None,
        description="Vendor-specific supplier XML block for export",
    )
    export_overrides: VendorExportOverrides | None = Field(
        default=None,
        description="Vendor-specific overrides on top of the shared export config",
    )
    target_xml: TargetXMLConfig | None = Field(
        default=None,
        description="Optional target XML template for invoice export",
    )

