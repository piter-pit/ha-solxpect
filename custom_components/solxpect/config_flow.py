"""Config flow for SolXpect PV Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_CELLS_MAX_POWER,
    CONF_CELLS_AREA,
    CONF_CELLS_EFFICIENCY,
    CONF_DIFFUSE_EFFICIENCY,
    CONF_INVERTER_POWER_LIMIT,
    CONF_INVERTER_EFFICIENCY,
    CONF_AZIMUTH,
    CONF_TILT,
    CONF_ALBEDO,
    CONF_IS_CENTRAL_INVERTER,
    CONF_SHADING_ELEVATION,
    CONF_SHADING_OPACITY,
)

# ======================================================
# 🔧 SHADING VALIDATOR (36 VALUES)
# ======================================================
def parse_36_values(raw: str, name: str) -> list[float]:
    parts = [x.strip() for x in raw.split(",") if x.strip()]

    if len(parts) != 36:
        raise ValueError(f"{name} must contain exactly 36 values")

    return [float(x) for x in parts]


# ======================================================
# 🔵 CONFIG FLOW (INITIAL SETUP)
# ======================================================
class SolxpectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial setup flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):

        if user_input is not None:
            try:
                return self.async_create_entry(
                    title="SolXpect PV Forecast",
                    data=self._parse_input(user_input),
                )
            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_input"},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
        )

    # -----------------------------
    # PARSER
    # -----------------------------
    def _parse_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}

        float_keys = [
            CONF_LATITUDE,
            CONF_LONGITUDE,
            CONF_CELLS_MAX_POWER,
            CONF_CELLS_AREA,
            CONF_CELLS_EFFICIENCY,
            CONF_DIFFUSE_EFFICIENCY,
            CONF_INVERTER_POWER_LIMIT,
            CONF_INVERTER_EFFICIENCY,
            CONF_AZIMUTH,
            CONF_TILT,
            CONF_ALBEDO,
        ]

        for key in float_keys:
            try:
                cleaned[key] = float(user_input.get(key, 0.0))
            except Exception:
                cleaned[key] = 0.0

        cleaned[CONF_IS_CENTRAL_INVERTER] = bool(
            user_input.get(CONF_IS_CENTRAL_INVERTER, True)
        )

        cleaned[CONF_SHADING_ELEVATION] = parse_36_values(
            user_input.get(CONF_SHADING_ELEVATION, ",".join(["0"] * 36)),
            "shading_elevation",
        )

        cleaned[CONF_SHADING_OPACITY] = parse_36_values(
            user_input.get(CONF_SHADING_OPACITY, ",".join(["0"] * 36)),
            "shading_opacity",
        )

        return cleaned

    # -----------------------------
    # UI SCHEMA
    # -----------------------------
    def _get_schema(self):
        return vol.Schema(
            {
                vol.Required(CONF_LATITUDE, default=0.0): vol.Coerce(float),
                vol.Required(CONF_LONGITUDE, default=0.0): vol.Coerce(float),

                vol.Required(CONF_CELLS_MAX_POWER, default=6000): vol.Coerce(float),
                vol.Required(CONF_CELLS_AREA, default=25.15): vol.Coerce(float),
                vol.Required(CONF_CELLS_EFFICIENCY, default=22.6): vol.Coerce(float),
                vol.Required(CONF_DIFFUSE_EFFICIENCY, default=97.5): vol.Coerce(float),

                vol.Required(CONF_INVERTER_POWER_LIMIT, default=6000): vol.Coerce(float),
                vol.Required(CONF_INVERTER_EFFICIENCY, default=95.0): vol.Coerce(float),

                vol.Required(CONF_AZIMUTH, default=180): vol.Coerce(float),
                vol.Required(CONF_TILT, default=40): vol.Coerce(float),

                vol.Required(CONF_ALBEDO, default=0.2): vol.Coerce(float),

                vol.Required(
                    CONF_SHADING_ELEVATION,
                    default=",".join(["0"] * 36),
                ): str,

                vol.Required(
                    CONF_SHADING_OPACITY,
                    default=",".join(["0"] * 36),
                ): str,

                vol.Required(CONF_IS_CENTRAL_INVERTER, default=True): bool,
            }
        )

    # ======================================================
    # 🔗 OPTIONS FLOW HOOK (ENABLE EDIT BUTTON)
    # ======================================================
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        return SolxpectOptionsFlow(config_entry)


# ======================================================
# 🔵 OPTIONS FLOW (EDIT AFTER INSTALL)
# ======================================================
class SolxpectOptionsFlow(OptionsFlow):
    """Handle integration options editing."""

    def __init__(self, config_entry: ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):

        if user_input is not None:
            try:
                return self.async_create_entry(
                    title="",
                    data=self._parse_input(user_input),
                )
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_input"},
                )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_schema(),
        )

    # reuse same parser
    def _parse_input(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return SolxpectConfigFlow()._parse_input(user_input)

    # merge config + options safely
    def _get_schema(self):

        data = {
            **self.config_entry.data,
            **(self.config_entry.options or {}),
        }

        return vol.Schema(
            {
                vol.Required(CONF_LATITUDE, default=data.get(CONF_LATITUDE, 0.0)): vol.Coerce(float),
                vol.Required(CONF_LONGITUDE, default=data.get(CONF_LONGITUDE, 0.0)): vol.Coerce(float),

                vol.Required(CONF_CELLS_MAX_POWER, default=data.get(CONF_CELLS_MAX_POWER, 6000)): vol.Coerce(float),
                vol.Required(CONF_CELLS_AREA, default=data.get(CONF_CELLS_AREA, 25.15)): vol.Coerce(float),
                vol.Required(CONF_CELLS_EFFICIENCY, default=data.get(CONF_CELLS_EFFICIENCY, 22.6)): vol.Coerce(float),
                vol.Required(CONF_DIFFUSE_EFFICIENCY, default=data.get(CONF_DIFFUSE_EFFICIENCY, 97.5)): vol.Coerce(float),

                vol.Required(CONF_INVERTER_POWER_LIMIT, default=data.get(CONF_INVERTER_POWER_LIMIT, 6000)): vol.Coerce(float),
                vol.Required(CONF_INVERTER_EFFICIENCY, default=data.get(CONF_INVERTER_EFFICIENCY, 95.0)): vol.Coerce(float),

                vol.Required(CONF_AZIMUTH, default=data.get(CONF_AZIMUTH, 180)): vol.Coerce(float),
                vol.Required(CONF_TILT, default=data.get(CONF_TILT, 40)): vol.Coerce(float),

                vol.Required(CONF_ALBEDO, default=data.get(CONF_ALBEDO, 0.2)): vol.Coerce(float),

                vol.Required(
                    CONF_SHADING_ELEVATION,
                    default=",".join(map(str, data.get(CONF_SHADING_ELEVATION, [0] * 36))),
                ): str,

                vol.Required(
                    CONF_SHADING_OPACITY,
                    default=",".join(map(str, data.get(CONF_SHADING_OPACITY, [0] * 36))),
                ): str,

                vol.Required(
                    CONF_IS_CENTRAL_INVERTER,
                    default=data.get(CONF_IS_CENTRAL_INVERTER, True),
                ): bool,
            }
        )
