"""Configuration loader for vendor-specific invoice parsing.

This module loads and validates vendor configurations from YAML files,
providing a cached interface for accessing vendor parsing settings.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.models.vendor_config import VendorConfiguration
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""


class ConfigLoader:
    """Loads and manages vendor configurations."""

    def __init__(self, config_dir: Path | str = "config/vendors"):
        """Initialize the config loader.

        Args:
            config_dir: Directory containing vendor YAML configuration files
        """
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise ConfigurationError(
                f"Configuration directory not found: {self.config_dir}"
            )

    @lru_cache(maxsize=10)
    def load_vendor_config(self, vendor_code: str) -> VendorConfiguration:
        """Load and validate vendor configuration from YAML file."""
        config_file = self.config_dir / f"{vendor_code}_config.yaml"

        if not config_file.exists():
            raise ConfigurationError(
                f"Configuration file not found for vendor '{vendor_code}': {config_file}"
            )

        logger.info(
            "Loading vendor configuration",
            extra={"vendor": vendor_code, "config_file": str(config_file)},
        )

        try:
            with config_file.open("r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            vendor_config = VendorConfiguration.model_validate(config_data)
            logger.info(
                "Successfully loaded vendor configuration",
                extra={"vendor": vendor_config.vendor_name},
            )
            return vendor_config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse YAML configuration for '{vendor_code}': {e}"
            ) from e
        except ValidationError as e:
            raise ConfigurationError(
                f"Invalid configuration for '{vendor_code}': {e}"
            ) from e
        except Exception as e:
            raise ConfigurationError(
                f"Unexpected error loading configuration for '{vendor_code}': {e}"
            ) from e

    def list_available_vendors(self) -> list[str]:
        """List all available vendor configurations.

        Returns:
            List of vendor codes (e.g., ['phoenix', 'alliance'])
        """
        vendor_codes = []
        for config_file in self.config_dir.glob("*_config.yaml"):
            vendor_code = config_file.stem.replace("_config", "")
            vendor_codes.append(vendor_code)

        logger.debug("Available vendor configurations", extra={"vendors": vendor_codes})
        return sorted(vendor_codes)

    def clear_cache(self) -> None:
        self.load_vendor_config.cache_clear()
        logger.info("Configuration cache cleared")


_default_loader = ConfigLoader()
