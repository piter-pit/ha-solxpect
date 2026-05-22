import tzlocal
import logging

from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .forecast import forecast_today_and_tomorrow
from .SolarPowerPlant import SolarPowerPlant

_LOGGER = logging.getLogger(__name__)

class SolxpectCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry):
        super().__init__(
            hass,
            logger=_LOGGER,
            name="solxpect_coordinator",
            update_interval=timedelta(hours=4),
        )
        self.config_entry = config_entry

    async def _async_update_data(self):

        cfg = self.config_entry.data
        SYSTEM_TZ = tzlocal.get_localzone()

        plant = SolarPowerPlant(
            albedo=cfg["albedo"],
            latitude=cfg["latitude"],
            longitude=cfg["longitude"],
            cellsMaxPower=cfg["cells_max_power"],
            cellsArea=cfg["cells_area"],
            cellsEfficiency=cfg["cells_efficiency"],
            cellsTempCoeff=cfg.get("cells_temp_coeff", -0.26),
            diffuseEfficiency=cfg["diffuse_efficiency"],
            inverterPowerLimit=cfg["inverter_power_limit"],
            inverterEfficiency=cfg["inverter_efficiency"],
            isCentralInverter=int(cfg["is_central_inverter"]),
            azimuthAngle=cfg["azimuth_angle"],
            tiltAngle=cfg["tilt_angle"],
            shadingElevation=[0]*36,
            shadingOpacity=[0]*36,
        )

        forecast = await self.hass.async_add_executor_job(
            forecast_today_and_tomorrow,
            plant,
            "PV"
        )

        return {
            "forecast": [
                {"time": t.astimezone(SYSTEM_TZ), "wh": wh}
                for t, wh in forecast
            ]
        }
