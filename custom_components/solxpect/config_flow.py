"""Config flow for SolXpect PV Forecast."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_LONGITUDE,
    CONF_LATITUDE,
    CONF_CELLS_MAX_POWER,
    CONF_CELLS_AREA,
    CONF_CELLS_EFFICIENCY,
    CONF_DIFFUSE_EFFICIENCY,
    CONF_INVERTER_POWER_LIMIT,
    CONF_INVERTER_EFFICIENCY,
    CONF_AZIMUTH,
    CONF_TILT,
    CONF_CELLS_TEMP_COEFF,
    CONF_ALBEDO,
    CONF_SHADING_ELEVATION,
    CONF_SHADING_OPACITY,
    CONF_IS_CENTRAL_INVERTER,
    CONF_RETAIN_ENABLED,
    CONF_RETAIN_HOURS,
    CONF_FORECAST_UPDATE_HOURS,
)

_LOGGER = logging.getLogger(__name__)


# ==========================================================
# HELPERS
# ==========================================================

def parse_36_values(value: str, field_name: str) -> list[float]:
    parts = [x.strip() for x in value.split(",")]

    if len(parts) != 36:
        raise ValueError(f"{field_name} must contain exactly 36 values")

    try:
        return [float(x) for x in parts]
    except Exception as err:
        raise ValueError(f"Invalid numeric value in {field_name}") from err


def list_to_csv(values: list[Any]) -> str:
    return ",".join(str(x) for x in values)


def get_default(defaults: dict[str, Any], key: str, fallback: Any) -> Any:
    return defaults.get(key, fallback)


# ==========================================================
# SCHEMA
# ==========================================================

def build_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LONGITUDE, default=get_default(defaults, CONF_LONGITUDE, 0.0)): vol.Coerce(float),
            vol.Required(CONF_LATITUDE, default=get_default(defaults, CONF_LATITUDE, 0.0)): vol.Coerce(float),

            vol.Required(CONF_CELLS_MAX_POWER, default=get_default(defaults, CONF_CELLS_MAX_POWER, 6000.0)): vol.Coerce(float),
            vol.Required(CONF_CELLS_AREA, default=get_default(defaults, CONF_CELLS_AREA, 25.15)): vol.Coerce(float),
            vol.Required(CONF_CELLS_EFFICIENCY, default=get_default(defaults, CONF_CELLS_EFFICIENCY, 22.6)): vol.Coerce(float),

            vol.Required(CONF_DIFFUSE_EFFICIENCY, default=get_default(defaults, CONF_DIFFUSE_EFFICIENCY, 97.5)): vol.Coerce(float),

            vol.Required(CONF_INVERTER_POWER_LIMIT, default=get_default(defaults, CONF_INVERTER_POWER_LIMIT, 15000.0)): vol.Coerce(float),
            vol.Required(CONF_INVERTER_EFFICIENCY, default=get_default(defaults, CONF_INVERTER_EFFICIENCY, 95.0)): vol.Coerce(float),

            vol.Required(CONF_AZIMUTH, default=get_default(defaults, CONF_AZIMUTH, 180.0)): vol.Coerce(float),
            vol.Required(CONF_TILT, default=get_default(defaults, CONF_TILT, 40.0)): vol.Coerce(float),

            vol.Required(CONF_CELLS_TEMP_COEFF, default=get_default(defaults, CONF_CELLS_TEMP_COEFF, -0.26)): vol.Coerce(float),
            vol.Required(CONF_ALBEDO, default=get_default(defaults, CONF_ALBEDO, 0.0)): vol.Coerce(float),

            vol.Required(CONF_RETAIN_ENABLED, default=get_default(defaults, CONF_RETAIN_ENABLED, True)): bool,
            vol.Required(CONF_RETAIN_HOURS, default=12): vol.Coerce(int),

            vol.Required(CONF_FORECAST_UPDATE_HOURS, default=4): vol.Coerce(int),

            vol.Required(
                CONF_SHADING_ELEVATION,
                default=list_to_csv(get_default(defaults, CONF_SHADING_ELEVATION, [0] * 36)),
            ): str,

            vol.Required(
                CONF_SHADING_OPACITY,
                default=list_to_csv(get_default(defaults, CONF_SHADING_OPACITY, [0] * 36)),
            ): str,

            vol.Required(CONF_IS_CENTRAL_INVERTER, default=get_default(defaults, CONF_IS_CENTRAL_INVERTER, True)): bool,
        }
    )


# ==========================================================
# PARSE INPUT
# ==========================================================

def parse_user_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {}

    float_fields = [
        CONF_LONGITUDE,
        CONF_LATITUDE,
        CONF_CELLS_MAX_POWER,
        CONF_CELLS_AREA,
        CONF_CELLS_EFFICIENCY,
        CONF_DIFFUSE_EFFICIENCY,
        CONF_INVERTER_POWER_LIMIT,
        CONF_INVERTER_EFFICIENCY,
        CONF_AZIMUTH,
        CONF_TILT,
        CONF_CELLS_TEMP_COEFF,
        CONF_ALBEDO,
    ]

    for field in float_fields:
        data[field] = float(user_input[field])

    data[CONF_RETAIN_ENABLED] = bool(user_input[CONF_RETAIN_ENABLED])
    data[CONF_RETAIN_HOURS] = int(user_input[CONF_RETAIN_HOURS])
    data[CONF_FORECAST_UPDATE_HOURS] = int(user_input[CONF_FORECAST_UPDATE_HOURS])

    data[CONF_SHADING_ELEVATION] = parse_36_values(
        user_input[CONF_SHADING_ELEVATION],
        CONF_SHADING_ELEVATION,
    )

    data[CONF_SHADING_OPACITY] = parse_36_values(
        user_input[CONF_SHADING_OPACITY],
        CONF_SHADING_OPACITY,
    )

    data[CONF_IS_CENTRAL_INVERTER] = bool(
        user_input.get(CONF_IS_CENTRAL_INVERTER, True)
    )

    return data


# ==========================================================
# CONFIG FLOW
# ==========================================================

class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SolxpectOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                parsed = parse_user_input(user_input)

                return self.async_create_entry(
                    title="SolXpect PV Forecast",
                    data=parsed,
                    options={},  # REQUIRED for OptionsFlow support
                )

            except Exception:
                _LOGGER.exception("Config flow error")
                errors["base"] = "invalid_input"

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema({}),
            errors=errors,
        )


# ==========================================================
# OPTIONS FLOW
# ==========================================================

class SolxpectOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}

        if user_input is not None:
            try:
                parsed = parse_user_input(user_input)

                # ✔ CORRECT: OptionsFlow writes into entry.options automatically
                return self.async_create_entry(
                    title="",
                    data=parsed,
                )

            except Exception:
                _LOGGER.exception("Options flow error")
                errors["base"] = "invalid_input"

        current = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(current),
            errors=errors,
        )
