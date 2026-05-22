import voluptuous as vol
from homeassistant import config_entries

DOMAIN = "solxpect"

class SolxpectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="SolXpect PV Forecast",
                data=user_input
            )

        schema = vol.Schema({
            vol.Required("latitude"): float,
            vol.Required("longitude"): float,
            vol.Required("cells_max_power", default=6000): float,
            vol.Required("cells_area", default=25.15): float,
            vol.Required("cells_efficiency", default=22.6): float,
            vol.Required("diffuse_efficiency", default=97.5): float,
            vol.Required("inverter_power_limit", default=15000): float,
            vol.Required("inverter_efficiency", default=95.0): float,
            vol.Required("azimuth_angle", default=201): float,
            vol.Required("tilt_angle", default=40): float,
            vol.Required("albedo", default=0.0): float,
            vol.Required("is_central_inverter", default=True): bool,
        })

        return self.async_show_form(step_id="user", data_schema=schema)
