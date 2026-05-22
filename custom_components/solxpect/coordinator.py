from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .forecast import forecast_today_and_tomorrow
from .SolarPowerPlant import SolarPowerPlant


class SolxpectCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config):
        super().__init__(
            hass,
            name="solxpect",
            update_interval=timedelta(hours=4),
        )
        self.config = config

    async def _async_update_data(self):

        plant = SolarPowerPlant(**self.config)

        return forecast_today_and_tomorrow(plant, "PV")
