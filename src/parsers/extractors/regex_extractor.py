"""Regex-based text extraction utilities.

This module provides utilities for extracting structured data using
regular expressions.
"""

import re
from typing import Pattern

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RegexExtractor:
    """Extract text values using regular expressions."""

    @staticmethod
    def extract_first_match(
        text: str, pattern: str | Pattern, group: int = 0
    ) -> str | None:
        """Extract first match of a regex pattern.

        Args:
            text: Text to search
            pattern: Regex pattern (string or compiled Pattern)
            group: Capture group to extract (0 = full match, 1+ = capturing groups)

        Returns:
            Matched text or None if not found
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        match = pattern.search(text)
        if match:
            try:
                value = match.group(group)
                logger.debug(
                    "Regex extraction successful",
                    extra={"pattern": pattern.pattern, "value": value},
                )
                return value
            except IndexError:
                logger.warning(
                    "Invalid group index",
                    extra={"pattern": pattern.pattern, "group": group},
                )
                return None

        logger.debug("Regex extraction failed", extra={"pattern": pattern.pattern})
        return None

    @staticmethod
    def extract_all_matches(
        text: str, pattern: str | Pattern, group: int = 0
    ) -> list[str]:
        """Extract all matches of a regex pattern.

        Args:
            text: Text to search
            pattern: Regex pattern (string or compiled Pattern)
            group: Capture group to extract

        Returns:
            List of matched values
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        matches = []
        for match in pattern.finditer(text):
            try:
                matches.append(match.group(group))
            except IndexError:
                continue

        logger.debug(
            "Regex extraction complete",
            extra={"pattern": pattern.pattern, "count": len(matches)},
        )
        return matches

    @staticmethod
    def clean_czech_number(value: str) -> str:
        """Clean Czech number format (spaces and comma decimal separator).

        Args:
            value: Number string in Czech format (e.g., '1 234,56')

        Returns:
            Cleaned number string (e.g., '1234.56')
        """
        # Remove spaces (thousands separator)
        cleaned = value.replace(" ", "")
        # Replace comma with dot (decimal separator)
        cleaned = cleaned.replace(",", ".")
        return cleaned

    @staticmethod
    def extract_czech_date(text: str) -> str | None:
        """Extract date in Czech format (DD.MM.YYYY).

        Args:
            text: Text containing date

        Returns:
            Date string in DD.MM.YYYY format or None
        """
        pattern = r"(\d{2}\.\d{2}\.\d{4})"
        return RegexExtractor.extract_first_match(text, pattern, group=1)

    @staticmethod
    def extract_ic(text: str) -> str | None:
        """Extract IČO (Czech company registration number).

        Args:
            text: Text containing IČO

        Returns:
            8-digit IČO or None
        """
        pattern = r"IČO[:\s]*(\d{8})"
        return RegexExtractor.extract_first_match(text, pattern, group=1)

    @staticmethod
    def extract_dic(text: str) -> str | None:
        """Extract DIČ (Czech VAT number).

        Args:
            text: Text containing DIČ

        Returns:
            DIČ in format CZ followed by 8-10 digits, or None
        """
        pattern = r"DIČ[:\s]*(CZ\d{8,10})"
        return RegexExtractor.extract_first_match(text, pattern, group=1)
