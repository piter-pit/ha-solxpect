"""Config flow for SolXpect PV Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback

DOMAIN = "solxpect"


# ======================================================
# HELPERS
# ======================================================

def parse_36_values(raw: str) -> list[float]:
    """Parse 36 comma-separated float values."""

    parts = [x.strip() for x in raw.split(",") if x.strip()]

    if len(parts) != 36:
        raise ValueError("Expected exactly 36 values")

    return [float(x) for x in parts]


# ======================================================
# CONFIG FLOW
# ======================================================

class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle SolXpect config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):

        errors: dict[str, str] = {}

        if user_input is not None:

            try:
                data = self._clean_input(user_input)

                return self.async_create_entry(
                    title="SolXpect PV Forecast",
                    data=data,
                )

            except Exception:
                errors["base"] = "invalid_input"

        return self.async_show_form(
            step_id="user",
            data_schema=self._build_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Return options flow."""
        return SolxpectOptionsFlow(config_entry)

    def _clean_input(self, user_input: dict[str, Any]):

        cleaned = {}

        float_fields = [
            "latitude",
            "longitude",
            "cells_max_power",
            "cells_area",
            "cells_efficiency",
            "diffuse_efficiency",
            "inverter_power_limit",
            "inverter_efficiency",
            "azimuth_angle",
            "tilt_angle",
            "albedo",
        ]

        for field in float_fields:
            cleaned[field] = float(user_input[field])

        cleaned["is_central_inverter"] = bool(
            user_input.get("is_central_inverter", True)
        )

        cleaned["shading_elevation"] = parse_36_values(
            user_input["shading_elevation"]
        )

        cleaned["shading_opacity"] = parse_36_values(
            user_input["shading_opacity"]
        )

        return cleaned

    def _build_schema(self):

        return vol.Schema(
            {
                vol.Required("latitude", default=0.0): vol.Coerce(float),
                vol.Required("longitude", default=0.0): vol.Coerce(float),

                vol.Required("cells_max_power", default=6000): vol.Coerce(float),
                vol.Required("cells_area", default=25.15): vol.Coerce(float),
                vol.Required("cells_efficiency", default=22.6): vol.Coerce(float),
                vol.Required("diffuse_efficiency", default=97.5): vol.Coerce(float),

                vol.Required("inverter_power_limit", default=6000): vol.Coerce(float),
                vol.Required("inverter_efficiency", default=95.0): vol.Coerce(float),

                vol.Required("azimuth_angle", default=180): vol.Coerce(float),
                vol.Required("tilt_angle", default=40): vol.Coerce(float),

                vol.Required("albedo", default=0.2): vol.Coerce(float),

                vol.Required(
                    "shading_elevation",
                    default=",".join(["0"] * 36),
                ): str,

                vol.Required(
                    "shading_opacity",
                    default=",".join(["0"] * 36),
                ): str,

                vol.Required(
                    "is_central_inverter",
                    default=True,
                ): bool,
            }
        )


# ======================================================
# OPTIONS FLOW
# ======================================================

class SolxpectOptionsFlow(config_entries.OptionsFlow):

    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ):

        errors: dict[str, str] = {}

        if user_input is not None:

            try:
                data = SolxpectConfigFlow()._clean_input(user_input)

                return self.async_create_entry(
                    title="",
                    data=data,
                )

            except Exception:
                errors["base"] = "invalid_input"

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "latitude",
                        default=current.get("latitude", 0.0),
                    ): vol.Coerce(float),

                    vol.Required(
                        "longitude",
                        default=current.get("longitude", 0.0),
                    ): vol.Coerce(float),

                    vol.Required(
                        "cells_max_power",
                        default=current.get("cells_max_power", 6000),
                    ): vol.Coerce(float),

                    vol.Required(
                        "cells_area",
                        default=current.get("cells_area", 25.15),
                    ): vol.Coerce(float),

                    vol.Required(
                        "cells_efficiency",
                        default=current.get("cells_efficiency", 22.6),
                    ): vol.Coerce(float),

                    vol.Required(
                        "diffuse_efficiency",
                        default=current.get("diffuse_efficiency", 97.5),
                    ): vol.Coerce(float),

                    vol.Required(
                        "inverter_power_limit",
                        default=current.get("inverter_power_limit", 6000),
                    ): vol.Coerce(float),

                    vol.Required(
                        "inverter_efficiency",
                        default=current.get("inverter_efficiency", 95.0),
                    ): vol.Coerce(float),

                    vol.Required(
                        "azimuth_angle",
                        default=current.get("azimuth_angle", 180),
                    ): vol.Coerce(float),

                    vol.Required(
                        "tilt_angle",
                        default=current.get("tilt_angle", 40),
                    ): vol.Coerce(float),

                    vol.Required(
                        "albedo",
                        default=current.get("albedo", 0.2),
                    ): vol.Coerce(float),

                    vol.Required(
                        "shading_elevation",
                        default=",".join(
                            map(
                                str,
                                current.get("shading_elevation", [0] * 36),
                            )
                        ),
                    ): str,

                    vol.Required(
                        "shading_opacity",
                        default=",".join(
                            map(
                                str,
                                current.get("shading_opacity", [0] * 36),
                            )
                        ),
                    ): str,

                    vol.Required(
                        "is_central_inverter",
                        default=current.get(
                            "is_central_inverter",
                            True,
                        ),
                    ): bool,
                }
            ),
            errors=errors,
        )
