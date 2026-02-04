"""Keyword-based text extraction from PDF documents.

This module provides utilities for finding and extracting text values
based on keyword searches in PDF content.
"""

import re
from typing import Pattern

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class KeywordExtractor:
    """Extract text values based on keyword proximity searches."""

    @staticmethod
    def find_text_after_keyword(
        full_text: str, keyword: str, pattern: str | Pattern | None = None
    ) -> str | None:
        """Find and extract text that appears after a keyword.

        Args:
            full_text: Full text content to search
            keyword: Keyword to search for
            pattern: Optional regex pattern to extract specific value after keyword

        Returns:
            Extracted text value or None if not found
        """
        # Escape special regex characters in keyword
        keyword_escaped = re.escape(keyword)

        if pattern:
            # Compile pattern if it's a string
            if isinstance(pattern, str):
                pattern = re.compile(pattern)

            # Search for keyword followed by the pattern
            search_pattern = f"{keyword_escaped}[\\s:]*{pattern.pattern}"
            match = re.search(search_pattern, full_text, re.IGNORECASE | re.MULTILINE)

            if match:
                # Try to extract the first capturing group or the whole match
                if match.groups():
                    value = match.group(1).strip()
                else:
                    value = match.group(0).replace(keyword, "").strip()

                logger.debug(
                    "Keyword extraction successful",
                    extra={"keyword": keyword, "value": value},
                )
                return value

        else:
            # Simple keyword search - extract next line or nearby text
            keyword_pattern = f"{keyword_escaped}[\\s:]*([^\\n]+)"
            match = re.search(keyword_pattern, full_text, re.IGNORECASE)

            if match:
                value = match.group(1).strip()
                logger.debug(
                    "Keyword extraction successful",
                    extra={"keyword": keyword, "value": value},
                )
                return value

        logger.warning(
            "Keyword extraction failed",
            extra={"keyword": keyword, "pattern": str(pattern)},
        )
        return None

    @staticmethod
    def find_all_matches(full_text: str, pattern: str | Pattern) -> list[str]:
        """Find all matches of a pattern in text.

        Args:
            full_text: Full text content to search
            pattern: Regex pattern to match

        Returns:
            List of matched values
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)

        matches = pattern.findall(full_text)
        logger.debug(
            "Pattern matching complete",
            extra={"pattern": pattern.pattern, "matches": len(matches)},
        )
        return matches

    @staticmethod
    def extract_with_context(
        text_blocks: list[dict], keyword: str, pattern: str | None = None
    ) -> str | None:
        """Extract value from text blocks based on keyword proximity.

        This method searches through positioned text blocks to find the keyword
        and extract nearby values with positional awareness.

        Args:
            text_blocks: List of text blocks with bbox information
            keyword: Keyword to search for
            pattern: Optional regex pattern for value extraction

        Returns:
            Extracted value or None if not found
        """
        for i, block in enumerate(text_blocks):
            if keyword.lower() in block["text"].lower():
                # Found keyword block
                target_text = block["text"]

                # Also check next few blocks (on same line or nearby)
                for j in range(i + 1, min(i + 5, len(text_blocks))):
                    next_block = text_blocks[j]
                    # Check if block is nearby (within 100 points vertically)
                    if abs(next_block["y_min"] - block["y_min"]) < 100:
                        target_text += " " + next_block["text"]

                # Extract using pattern if provided
                if pattern:
                    if isinstance(pattern, str):
                        pattern = re.compile(pattern)
                    match = pattern.search(target_text)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
                else:
                    # Return text after keyword
                    parts = target_text.split(keyword, 1)
                    if len(parts) > 1:
                        return parts[1].strip()

        return None
