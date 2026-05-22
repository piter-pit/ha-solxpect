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

            # -----------------------------
            # FLOAT PARAMETERS
            # -----------------------------
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

            # -----------------------------
            # BOOLEAN
            # -----------------------------
            cleaned["is_central_inverter"] = bool(
                user_input.get("is_central_inverter", True)
            )

            # -----------------------------
            # SHADING (CRITICAL)
            # -----------------------------
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
                schema = self._get_schema()
                return self.async_show_form(
                    step_id="user",
                    data_schema=schema,
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

    def _get_schema(self):
        """UI schema definition."""

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
