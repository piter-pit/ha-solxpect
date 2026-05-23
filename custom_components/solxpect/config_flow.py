"""Config flow for SolXpect PV Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

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
    CONF_CELLS_TEMP_COEFF,
)


# ======================================================
# HELPERS
# ======================================================

def parse_36_values(raw: str, name: str) -> list[float]:
    """Validate and parse 36-value CSV strings."""

    parts = [x.strip() for x in raw.split(",") if x.strip()]

    if len(parts) != 36:
        raise ValueError(f"{name} must contain exactly 36 values")

    try:
        return [float(x) for x in parts]
    except ValueError as err:
        raise ValueError(f"Invalid float in {name}") from err


def csv_from_list(values: list[Any]) -> str:
    """Convert list to CSV string."""

    return ",".join(map(str, values))


def build_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build form schema."""

    return vol.Schema(
        {
            vol.Required(
                CONF_LONGITUDE,
                default=defaults.get(CONF_LONGITUDE, 0.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_LATITUDE,
                default=defaults.get(CONF_LATITUDE, 0.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_CELLS_MAX_POWER,
                default=defaults.get(CONF_CELLS_MAX_POWER, 6000.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_CELLS_AREA,
                default=defaults.get(CONF_CELLS_AREA, 25.15),
            ): vol.Coerce(float),

            vol.Required(
                CONF_CELLS_EFFICIENCY,
                default=defaults.get(CONF_CELLS_EFFICIENCY, 22.6),
            ): vol.Coerce(float),

            vol.Required(
                CONF_DIFFUSE_EFFICIENCY,
                default=defaults.get(CONF_DIFFUSE_EFFICIENCY, 97.5),
            ): vol.Coerce(float),

            vol.Required(
                CONF_INVERTER_POWER_LIMIT,
                default=defaults.get(CONF_INVERTER_POWER_LIMIT, 15000.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_INVERTER_EFFICIENCY,
                default=defaults.get(CONF_INVERTER_EFFICIENCY, 95.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_AZIMUTH,
                default=defaults.get(CONF_AZIMUTH, 180.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_TILT,
                default=defaults.get(CONF_TILT, 40.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_CELLS_TEMP_COEFF,
                default=defaults.get(CONF_CELLS_TEMP_COEFF, -0.26),
            ): vol.Coerce(float),

            vol.Required(
                CONF_ALBEDO,
                default=defaults.get(CONF_ALBEDO, 0.0),
            ): vol.Coerce(float),

            vol.Required(
                CONF_SHADING_ELEVATION,
                default=csv_from_list(
                    defaults.get(CONF_SHADING_ELEVATION, [0] * 36)
                ),
            ): str,

            vol.Required(
                CONF_SHADING_OPACITY,
                default=csv_from_list(
                    defaults.get(CONF_SHADING_OPACITY, [0] * 36)
                ),
            ): str,

            vol.Required(
                CONF_IS_CENTRAL_INVERTER,
                default=bool(
                    defaults.get(CONF_IS_CENTRAL_INVERTER, True)
                ),
            ): bool,
        }
    )


def parse_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate input."""

    cleaned: dict[str, Any] = {}

    float_keys = [
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

    for key in float_keys:
        cleaned[key] = float(user_input[key])

    cleaned[CONF_IS_CENTRAL_INVERTER] = bool(
        user_input.get(CONF_IS_CENTRAL_INVERTER, True)
    )

    cleaned[CONF_SHADING_ELEVATION] = parse_36_values(
        user_input[CONF_SHADING_ELEVATION],
        CONF_SHADING_ELEVATION,
    )

    cleaned[CONF_SHADING_OPACITY] = parse_36_values(
        user_input[CONF_SHADING_OPACITY],
        CONF_SHADING_OPACITY,
    )

    return cleaned


# ======================================================
# CONFIG FLOW
# ======================================================

class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return options flow."""

        return SolxpectOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle user config step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                parsed = parse_input(user_input)

                return self.async_create_entry(
                    title="SolXpect PV Forecast",
                    data=parsed,
                )

            except ValueError:
                errors["base"] = "invalid_input"

            except Exception as err:
                errors["base"] = "unknown"
                print(f"SolXpect config flow error: {err}")

        return self.async_show_form(
            step_id="user",
            data_schema=build_schema({}),
            errors=errors,
        )


# ======================================================
# OPTIONS FLOW
# ======================================================

class SolxpectOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""

        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage options."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                parsed = parse_input(user_input)

                return self.async_create_entry(
                    title="",
                    data=parsed,
                )

            except ValueError:
                errors["base"] = "invalid_input"

            except Exception as err:
                errors["base"] = "unknown"
                print(f"SolXpect options flow error: {err}")

        current_data = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=build_schema(current_data),
            errors=errors,
        )
