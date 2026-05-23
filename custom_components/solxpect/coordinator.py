import tzlocal
import logging

from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from .forecast import forecast_today_and_tomorrow
from .SolarPowerPlant import SolarPowerPlant
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)


# ==========================================================
# DAILY HOURS BUILDER (UNCHANGED)
# ==========================================================

def build_daily_hours(forecast, tz):
    now_local = datetime.now(tz).date()

    def init_hours():
        return {f"{h:02d}:00": 0.0 for h in range(24)}

    today_hours = init_hours()
    tomorrow_hours = init_hours()

    for item in forecast:
        dt_local = item["time"].astimezone(tz)
        day = dt_local.date()
        hour = f"{dt_local.hour:02d}:00"

        value = item["wh"] / 1000.0

        if day == now_local:
            today_hours[hour] += value
        elif day == now_local + timedelta(days=1):
            tomorrow_hours[hour] += value

    return today_hours, tomorrow_hours


# ==========================================================
# COORDINATOR
# ==========================================================

class SolxpectCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry):

        self.hass = hass
        self.config_entry = config_entry

        super().__init__(
            hass,
            logger=_LOGGER,
            name="solxpect_coordinator",
            update_interval=timedelta(hours=4),
        )

        self.tz = dt_util.get_default_time_zone()

        self._last_successful_update = None
        self._retain_latest_forecast_when_unavailable = True
        self._max_forecast_age = timedelta(hours=12)

    # ======================================================
    # IMPORTANT: ALWAYS FRESH CONFIG (FIX)
    # ======================================================

    def _cfg(self):
        return {
            **self.config_entry.data,
            **self.config_entry.options,
        }

    # ======================================================
    # MAIN UPDATE
    # ======================================================

    async def _async_update_data(self):

        cfg = self._cfg()  # 🔥 always fresh snapshot per update

        try:
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
                azimuthAngle=cfg["azimuth_angle"],   # <-- WAŻNE: zgodne z const.py
                tiltAngle=cfg["tilt_angle"],         # <-- WAŻNE: zgodne z const.py
                shadingElevation=cfg.get("shading_elevation", [0] * 36),
                shadingOpacity=cfg.get("shading_opacity", [0] * 36),
            )

            forecast = await self.hass.async_add_executor_job(
                forecast_today_and_tomorrow,
                plant,
                "PV",
            )

            data = [{"time": t, "wh": wh} for t, wh in forecast]

            today, tomorrow = build_daily_hours(data, self.tz)

            self._last_successful_update = dt_util.utcnow()

            return {
                "today": today,
                "tomorrow": tomorrow,
            }

        except Exception as err:

            if (
                not self._retain_latest_forecast_when_unavailable
                or self.data is None
            ):
                raise UpdateFailed(str(err)) from err

            if self._last_successful_update:
                age = dt_util.utcnow() - self._last_successful_update

                if age > self._max_forecast_age:
                    raise UpdateFailed("Stale retained data") from err

            _LOGGER.warning(
                "Forecast update failed, using cached data: %s",
                err,
            )

            return self.data
