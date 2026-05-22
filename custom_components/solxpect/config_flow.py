"""Config flow for SolXpect PV Forecast."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

DOMAIN = "solxpect"


# ======================================================
# 🔧 UTIL: 36-value CSV parser
# ======================================================
def parse_36_values(raw: str, name: str) -> list[float]:
    """Validate and parse 36-value CSV strings."""
    try:
        parts = [x.strip() for x in raw.split(",") if x.strip() != ""]

        if len(parts) != 36:
            raise ValueError(f"{name} must contain exactly 36 values")

        return [float(x) for x in parts]

    except Exception as err:
        raise ValueError(f"Invalid {name}") from err


# ======================================================
# 🔵 CONFIG FLOW (first install)
# ======================================================
class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            try:
                cleaned = self._parse_input(user_input)
            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_input"},
                )

            return self.async_create_entry(
                title="SolXpect PV Forecast",
                data=cleaned,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
        )

    # -----------------------------
    # INPUT PARSING
    # -----------------------------
    def _parse_input(self, user_input: dict):
        cleaned = {}

        float_keys = [
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

        for key in float_keys:
            try:
                cleaned[key] = float(user_input.get(key, 0.0))
            except Exception:
                cleaned[key] = 0.0

        cleaned["is_central_inverter"] = bool(
            user_input.get("is_central_inverter", True)
        )

        cleaned["shading_elevation"] = parse_36_values(
            user_input.get("shading_elevation", ",".join(["0"] * 36)),
            "shading_elevation",
        )

        cleaned["shading_opacity"] = parse_36_values(
            user_input.get("shading_opacity", ",".join(["0"] * 36)),
            "shading_opacity",
        )

        return cleaned

    # -----------------------------
    # UI SCHEMA
    # -----------------------------
    def _get_schema(self):
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

                vol.Required("is_central_inverter", default=True): bool,
            }
        )

    # ======================================================
    # 🔗 ENABLE OPTIONS FLOW (EDIT IN UI)
    # ======================================================
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolxpectOptionsFlow(config_entry)


# ======================================================
# 🔵 OPTIONS FLOW (EDIT AFTER INSTALL)
# ======================================================
class SolxpectOptionsFlow(config_entries.OptionsFlow):
    """Handle integration options editing."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            try:
                cleaned = self._parse_input(user_input)
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_input"},
                )

            return self.async_create_entry(title="", data=cleaned)

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_schema(),
        )

    # reuse parser logic safely
    def _parse_input(self, user_input: dict):
        return SolxpectConfigFlow()._parse_input(user_input)

    # merge existing config + options
    def _get_schema(self):
        data = {**self.config_entry.data, **self.config_entry.options}

        return vol.Schema(
            {
                vol.Required("latitude", default=data.get("latitude", 0.0)): vol.Coerce(float),
                vol.Required("longitude", default=data.get("longitude", 0.0)): vol.Coerce(float),

                vol.Required("cells_max_power", default=data.get("cells_max_power", 6000)): vol.Coerce(float),
                vol.Required("cells_area", default=data.get("cells_area", 25.15)): vol.Coerce(float),
                vol.Required("cells_efficiency", default=data.get("cells_efficiency", 22.6)): vol.Coerce(float),
                vol.Required("diffuse_efficiency", default=data.get("diffuse_efficiency", 97.5)): vol.Coerce(float),

                vol.Required("inverter_power_limit", default=data.get("inverter_power_limit", 6000)): vol.Coerce(float),
                vol.Required("inverter_efficiency", default=data.get("inverter_efficiency", 95.0)): vol.Coerce(float),

                vol.Required("azimuth_angle", default=data.get("azimuth_angle", 180)): vol.Coerce(float),
                vol.Required("tilt_angle", default=data.get("tilt_angle", 40)): vol.Coerce(float),

                vol.Required("albedo", default=data.get("albedo", 0.2)): vol.Coerce(float),

                vol.Required(
                    "shading_elevation",
                    default=",".join(map(str, data.get("shading_elevation", [0] * 36))),
                ): str,

                vol.Required(
                    "shading_opacity",
                    default=",".join(map(str, data.get("shading_opacity", [0] * 36))),
                ): str,

                vol.Required(
                    "is_central_inverter",
                    default=data.get("is_central_inverter", True),
                ): bool,
            }
        )
