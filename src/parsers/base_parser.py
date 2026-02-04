"""Base parser interface for PDF invoice parsing.

This module defines the abstract base class that all vendor-specific
parsers must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path

import fitz

from src.models.parsed_invoice import ParsedInvoice
from src.models.vendor_config import VendorConfiguration
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFParseError(Exception):
    """Raised when PDF parsing fails."""


class BaseParser(ABC):
    """Abstract base class for vendor-specific invoice parsers."""

    def __init__(self, config: VendorConfiguration):
        """Initialize parser with vendor configuration.

        Args:
            config: Vendor-specific configuration
        """
        self.config = config
        self.logger = setup_logger(self.__class__.__name__)

    @abstractmethod
    def parse(self, pdf_path: Path) -> ParsedInvoice:
        """Parse PDF invoice and extract structured data.

        Args:
            pdf_path: Path to PDF file

        Returns:
            ParsedInvoice instance with extracted data

        Raises:
            PDFParseError: If parsing fails
        """

    def load_pdf(self, pdf_path: Path) -> fitz.Document:
        """Load PDF document.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PyMuPDF Document object

        Raises:
            PDFParseError: If PDF cannot be loaded
        """
        if not pdf_path.exists():
            raise PDFParseError(f"PDF file not found: {pdf_path}")

        try:
            self.logger.info(
                "Loading PDF",
                extra={"pdf_path": str(pdf_path), "vendor": self.config.vendor_name},
            )
            doc = fitz.open(pdf_path)
            self.logger.debug(
                "PDF loaded successfully",
                extra={"pages": len(doc), "pdf_path": str(pdf_path)},
            )
            return doc
        except Exception as e:
            raise PDFParseError(f"Failed to load PDF {pdf_path}: {e}") from e

    def extract_text_blocks(self, page: fitz.Page) -> list[dict]:
        """Extract text blocks with position information from a page.

        Args:
            page: PyMuPDF Page object

        Returns:
            List of text blocks with bbox and text content
        """
        # Use rawdict mode which preserves original encoding better
        text_dict = page.get_text(
            "rawdict",
            flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE,
        )
        blocks = []

        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                bbox = block["bbox"]
                text_parts = []

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span["text"]
                        # Handle potential encoding issues
                        if isinstance(text, bytes):
                            try:
                                text = text.decode("utf-8")
                            except UnicodeDecodeError:
                                try:
                                    text = text.decode(
                                        "cp1250"
                                    )  # Czech Windows encoding
                                except UnicodeDecodeError:
                                    text = text.decode("latin-2", errors="replace")
                        text_parts.append(text)

                full_text = " ".join(text_parts).strip()
                if full_text:
                    blocks.append(
                        {
                            "bbox": bbox,
                            "text": full_text,
                            "x_min": bbox[0],
                            "y_min": bbox[1],
                            "x_max": bbox[2],
                            "y_max": bbox[3],
                        }
                    )

        return blocks

    def get_full_text(self, doc: fitz.Document) -> str:
        """Extract all text from PDF document.

        Args:
            doc: PyMuPDF Document object

        Returns:
            Full text content of the PDF
        """
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Use text mode with ligature preservation for better encoding
            text = page.get_text(
                "text",
                flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE,
            )
            text_parts.append(text)

        return "\n".join(text_parts)
