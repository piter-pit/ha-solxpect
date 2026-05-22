import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "solxpect"


class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SolXpect PV Forecast config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # HA UI sends strings → normalize safely
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
                    cleaned[key] = float(user_input[key])
                except (ValueError, TypeError, KeyError):
                    cleaned[key] = 0.0

            cleaned["is_central_inverter"] = bool(user_input.get("is_central_inverter", True))

            return self.async_create_entry(
                title="SolXpect PV Forecast",
                data=cleaned,
            )

        schema = vol.Schema({
            vol.Required("latitude", default=0.0): vol.Coerce(float),
            vol.Required("longitude", default=0.0): vol.Coerce(float),

            vol.Required("cells_max_power", default=6000): vol.Coerce(float),
            vol.Required("cells_area", default=25.15): vol.Coerce(float),
            vol.Required("cells_efficiency", default=22.6): vol.Coerce(float),
            vol.Required("diffuse_efficiency", default=97.5): vol.Coerce(float),

            vol.Required("inverter_power_limit", default=15000): vol.Coerce(float),
            vol.Required("inverter_efficiency", default=95.0): vol.Coerce(float),

            vol.Required("azimuth_angle", default=201): vol.Coerce(float),
            vol.Required("tilt_angle", default=40): vol.Coerce(float),

            vol.Required("albedo", default=0.0): vol.Coerce(float),

            vol.Required("is_central_inverter", default=True): bool,
        })

        return self.async_show_form(step_id="user", data_schema=schema)
