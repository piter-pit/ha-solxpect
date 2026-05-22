import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "solxpect"


def parse_36_values(raw: str, name: str) -> list[float]:
    """Validate and parse 36-value CSV strings."""
    try:
        parts = [x.strip() for x in raw.split(",") if x.strip() != ""]
        if len(parts) != 36:
            raise ValueError(f"{name} must contain exactly 36 values")

        return [float(x) for x in parts]

    except Exception:
        raise ValueError(f"Invalid {name}")


class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SolXpect PV Forecast config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:

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
                except (ValueError, TypeError):
                    cleaned[key] = 0.0

            cleaned["is_central_inverter"] = bool(
                user_input.get("is_central_inverter", True)
            )

            try:
                cleaned["shading_elevation"] = parse_36_values(
                    user_input.get("shading_elevation", "0," * 35 + "0"),
                    "shading_elevation",
                )

                cleaned["shading_opacity"] = parse_36_values(
                    user_input.get("shading_opacity", "0," * 35 + "0"),
                    "shading_opacity",
                )

            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_schema(),
                    errors={"base": "invalid_shading_format"},
                )

            return self.async_create_entry(
                title="SolXpect PV Forecast",
                data=cleaned,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_schema(),
        )

    # =========================================================
    # EDIT MODE (ZĘBATKA W HOME ASSISTANT)
    # =========================================================
    async def async_step_init(self, user_input=None):
        """Edit existing config entry."""

        if user_input is not None:

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
                except (ValueError, TypeError):
                    cleaned[key] = 0.0

            cleaned["is_central_inverter"] = bool(
                user_input.get("is_central_inverter", True)
            )

            try:
                cleaned["shading_elevation"] = parse_36_values(
                    user_input.get("shading_elevation", "0," * 35 + "0"),
                    "shading_elevation",
                )

                cleaned["shading_opacity"] = parse_36_values(
                    user_input.get("shading_opacity", "0," * 35 + "0"),
                    "shading_opacity",
                )

            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_schema(current=True),
                    errors={"base": "invalid_shading_format"},
                )

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=cleaned,
            )

            return self.async_create_entry(title="", data=cleaned)

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_schema(current=True),
        )

    # =========================================================
    # FIXED SCHEMA (KLUCZ DO WYSWIETLANIA ZAPISANYCH WARTOSCI)
    # =========================================================
    def _get_schema(self, current=False):
        """UI schema definition with optional loaded config."""

        data = self.config_entry.data if current and self.config_entry else {}

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
