import tzlocal
import logging

from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .forecast import forecast_today_and_tomorrow
from .SolarPowerPlant import SolarPowerPlant
from collections import defaultdict
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

def build_daily_hours(forecast, tz):
    """
    forecast: list[{time, wh}]
    tz: HA local timezone
    """

    now_local = datetime.now(tz).date()

    today = defaultdict(float)
    tomorrow = defaultdict(float)

    # init 0–23 zawsze (wymaganie UI)
    def init_hours():
        return {f"{h:02d}:00": 0.0 for h in range(24)}

    today_hours = init_hours()
    tomorrow_hours = init_hours()

    for item in forecast:
        dt_local = item["time"].astimezone(tz)
        day = dt_local.date()
        hour = f"{dt_local.hour:02d}:00"

        value = item["wh"] / 1000.0  # Wh → kWh

        if day == now_local:
            today_hours[hour] += value
        elif day == now_local + timedelta(days=1):
            tomorrow_hours[hour] += value

    return today_hours, tomorrow_hours

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

        cfg = {**self.config_entry.data, **self.config_entry.options}
        tz = dt_util.get_default_time_zone()

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
        _LOGGER.debug("CFG: %s", cfg)
        _LOGGER.debug("TZ: %s", tz)
        _LOGGER.debug("PLANT: %s", vars(plant))

        forecast = await self.hass.async_add_executor_job(
            forecast_today_and_tomorrow,
            plant,
            "PV"
        )

        data = [
            {"time": t, "wh": wh}
            for t, wh in forecast
        ]

        today, tomorrow = build_daily_hours(data, tz)

        return {
            "today": today,
            "tomorrow": tomorrow,
        }
