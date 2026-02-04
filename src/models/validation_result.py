"""Validation result models for invoice data validation.

This module defines models for capturing validation results,
including errors, warnings, and overall validation status.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity levels for validation messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationMessage(BaseModel):
    """A single validation message."""

    severity: ValidationSeverity
    field: str | None = Field(
        default=None, description="Field name that failed validation"
    )
    message: str = Field(description="Human-readable validation message")
    code: str | None = Field(
        default=None, description="Machine-readable error code (e.g., 'VAT_MISMATCH')"
    )
    context: dict[str, str | int | float | bool] | None = Field(
        default=None, description="Additional context about the validation failure"
    )


class ValidationResult(BaseModel):
    """Result of invoice validation."""

    is_valid: bool = Field(description="True if validation passed with no errors")
    errors: list[ValidationMessage] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: list[ValidationMessage] = Field(
        default_factory=list, description="List of validation warnings"
    )
    info: list[ValidationMessage] = Field(
        default_factory=list, description="List of informational messages"
    )

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def message_count(self) -> int:
        """Total count of all validation messages."""
        return len(self.errors) + len(self.warnings) + len(self.info)

    def add_error(
        self,
        message: str,
        field: str | None = None,
        code: str | None = None,
        context: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        """Add an error message and mark validation as failed."""
        self.errors.append(
            ValidationMessage(
                severity=ValidationSeverity.ERROR,
                field=field,
                message=message,
                code=code,
                context=context,
            )
        )
        self.is_valid = False

    def add_warning(
        self,
        message: str,
        field: str | None = None,
        code: str | None = None,
        context: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        """Add a warning message."""
        self.warnings.append(
            ValidationMessage(
                severity=ValidationSeverity.WARNING,
                field=field,
                message=message,
                code=code,
                context=context,
            )
        )

    def add_info(
        self,
        message: str,
        field: str | None = None,
        code: str | None = None,
        context: dict[str, str | int | float | bool] | None = None,
    ) -> None:
        """Add an informational message."""
        self.info.append(
            ValidationMessage(
                severity=ValidationSeverity.INFO,
                field=field,
                message=message,
                code=code,
                context=context,
            )
        )
