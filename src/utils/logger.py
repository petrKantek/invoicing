"""Logging configuration for the invoice parser."""

import logging
import sys
from pathlib import Path
from typing import Any


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Path | None = None,
) -> logging.Logger:
    """Set up a logger with console and optional file handlers.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs only to console.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    console_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


def log_invoice_processing(
    logger: logging.Logger, invoice_number: str, **kwargs: Any
) -> None:
    """Log invoice processing with structured context.

    Args:
        logger: Logger instance
        invoice_number: Invoice number being processed
        **kwargs: Additional context (vendor, status, etc.)
    """
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Invoice: {invoice_number} | {context}")


def log_validation_result(
    logger: logging.Logger,
    invoice_number: str,
    is_valid: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    """Log validation results in structured format."""
    status = "PASS" if is_valid else "FAIL"
    logger.info(f"Validation {status} | Invoice: {invoice_number}")

    if errors:
        logger.error(f"Validation errors for {invoice_number}:")
        for error in errors:
            logger.error(f"  - {error}")

    if warnings:
        logger.warning(f"Validation warnings for {invoice_number}:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
