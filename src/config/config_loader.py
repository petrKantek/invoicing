"""Configuration loader for vendor-specific invoice parsing.

This module loads and validates vendor configurations from YAML files,
providing a cached interface for accessing vendor parsing settings.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from src.models.vendor_config import (
    SharedExportConfig,
    TargetXMLElement,
    TargetXMLConfig,
    VendorConfiguration,
)
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

            config_data = self._inject_shared_target_xml(config_data)

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

    @lru_cache(maxsize=1)
    def load_shared_export_config(self) -> SharedExportConfig:
        """Load the reusable export configuration shared by vendors."""
        shared_config_file = self.config_dir.parent / "shared" / "export_shared.yaml"
        if not shared_config_file.exists():
            raise ConfigurationError(
                f"Shared export configuration not found: {shared_config_file}"
            )

        try:
            with shared_config_file.open("r", encoding="utf-8") as f:
                shared_config_data = yaml.safe_load(f)

            return SharedExportConfig.model_validate(shared_config_data)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Failed to parse shared export configuration: {e}"
            ) from e
        except ValidationError as e:
            raise ConfigurationError(
                f"Invalid shared export configuration: {e}"
            ) from e

    def _inject_shared_target_xml(self, config_data: dict) -> dict:
        """Build target XML from shared export defaults when configured."""
        if config_data.get("target_xml") is not None:
            return config_data

        export_supplier = config_data.get("export_supplier")
        if export_supplier is None:
            return config_data

        shared_export_config = self.load_shared_export_config()
        export_overrides = config_data.get("export_overrides") or {}
        root_attributes = {
            **shared_export_config.root_attributes,
            **export_overrides.get("root_attributes", {}),
        }
        invoice_defaults = {
            **shared_export_config.invoice_defaults,
            **export_overrides.get("invoice_defaults", {}),
        }

        config_data = dict(config_data)
        config_data["target_xml"] = self._build_target_xml_config(
            shared_export_config,
            root_attributes,
            invoice_defaults,
            export_supplier,
        ).model_dump(mode="python")
        return config_data

    def _build_target_xml_config(
        self,
        shared_export_config: SharedExportConfig,
        root_attributes: dict[str, str],
        invoice_defaults: dict[str, str],
        export_supplier: dict,
    ) -> TargetXMLConfig:
        """Compose a vendor target XML config from shared and vendor-specific parts."""
        static_field_order = [
            "Rada",
            "CisRada",
            "Popis",
        ]
        fakt_prij_children = [
            self._static_element(tag, invoice_defaults[tag]) for tag in static_field_order
        ]
        fakt_prij_children.extend(
            [
                self._dynamic_element("Vystaveno"),
                self._dynamic_element("PlnenoDPH"),
                self._dynamic_element("Doruceno"),
                self._dynamic_element("Splatno"),
                self._static_element("KodDPH", invoice_defaults["KodDPH"]),
                self._dynamic_element("VarSymbol"),
                self._dynamic_element("PrijatDokl"),
                self._static_element("Ucet", invoice_defaults["Ucet"]),
                self._static_element("Druh", invoice_defaults["Druh"]),
                self._static_element("Dobropis", invoice_defaults["Dobropis"]),
                self._static_element("Uhrada", invoice_defaults["Uhrada"]),
                self._static_element("PredKontac", invoice_defaults["PredKontac"]),
                self._static_element("ZpVypDPH", invoice_defaults["ZpVypDPH"]),
                self._static_element("SazbaDPH1", invoice_defaults["SazbaDPH1"]),
                self._static_element("SazbaDPH2", invoice_defaults["SazbaDPH2"]),
                self._dynamic_element("Proplatit"),
                self._static_element("Vyuctovano", invoice_defaults["Vyuctovano"]),
                TargetXMLElement(
                    tag="SouhrnDPH",
                    children=[
                        self._dynamic_element("Zaklad0"),
                        self._dynamic_element("Zaklad5"),
                        self._dynamic_element("Zaklad22"),
                        self._dynamic_element("DPH5"),
                        self._dynamic_element("DPH22"),
                    ],
                ),
                self._dynamic_element("Celkem"),
                self._static_element("Typ", invoice_defaults["Typ"]),
                self._static_element("PriUhrZbyv", invoice_defaults["PriUhrZbyv"]),
                self._static_element("ValutyProp", invoice_defaults["ValutyProp"]),
                self._static_element("SumZaloha", invoice_defaults["SumZaloha"]),
                self._static_element("SumZalohaC", invoice_defaults["SumZalohaC"]),
                TargetXMLElement.model_validate(export_supplier),
                self._static_element("DopravTuz", invoice_defaults["DopravTuz"]),
                self._static_element("DopravZahr", invoice_defaults["DopravZahr"]),
                self._static_element("Sleva", invoice_defaults["Sleva"]),
                TargetXMLElement(tag="SeznamPolozek"),
                shared_export_config.my_company.model_copy(deep=True),
            ]
        )

        return TargetXMLConfig(
            root_tag=shared_export_config.root_tag,
            root_attributes=root_attributes,
            body=[
                TargetXMLElement(
                    tag="SeznamFaktPrij",
                    children=[
                        TargetXMLElement(
                            tag="FaktPrij",
                            repeat_for_each_invoice=True,
                            children=fakt_prij_children,
                        )
                    ],
                ),
                TargetXMLElement(tag="SeznamFaktPrij_DPP"),
            ],
        )

    def _static_element(self, tag: str, text: str) -> TargetXMLElement:
        """Create a static XML element."""
        return TargetXMLElement(tag=tag, text=text)

    def _dynamic_element(self, field_name: str) -> TargetXMLElement:
        """Create a dynamic XML element bound to an invoice field."""
        return TargetXMLElement(tag=field_name, dynamic_field=field_name)

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
        self.load_shared_export_config.cache_clear()
        logger.info("Configuration cache cleared")


_default_loader = ConfigLoader()
