import tzlocal
import logging

from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
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

    # init 0–23 always (UI requirement)
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

        # --- CONFIG (from config_flow + options) ---
        cfg = {**config_entry.data, **config_entry.options}

        # retain switch (on/off)
        self._retain_latest_forecast_when_unavailable = cfg.get(
            "retain_enabled",
            True,
        )

        # retain max age (hours)
        self._max_forecast_age = timedelta(
            hours=cfg.get("retain_hours", 12)
        )

        # timestamp of last successful update
        self._last_successful_update = None

        # timezone (constant per instance)
        self.tz = dt_util.get_default_time_zone()

        # --- SHADING FROM CONFIG ---
        shading_elevation = cfg.get("shading_elevation", [0] * 36)
        shading_opacity = cfg.get("shading_opacity", [0] * 36)

        self.plant = SolarPowerPlant(
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
            shadingElevation=shading_elevation,
            shadingOpacity=shading_opacity,
        )

    async def _async_update_data(self):

        try:
            forecast = await self.hass.async_add_executor_job(
                forecast_today_and_tomorrow,
                self.plant,
                "PV"
            )

            data = [
                {"time": t, "wh": wh}
                for t, wh in forecast
            ]

            today, tomorrow = build_daily_hours(data, self.tz)

            result = {
                "today": today,
                "tomorrow": tomorrow,
            }

            # update timestamp on success
            self._last_successful_update = dt_util.utcnow()

            return result

        except Exception as err:

            # no retain OR no previous data → fail hard
            if (
                not self._retain_latest_forecast_when_unavailable
                or self.data is None
            ):
                raise UpdateFailed(
                    f"Error communicating with API: {err}"
                ) from err

            # validate age of retained data
            if self._max_forecast_age is not None:

                if self._last_successful_update is None:
                    raise UpdateFailed(
                        "No successful forecast update timestamp available"
                    ) from err

                forecast_age = dt_util.utcnow() - self._last_successful_update

                if forecast_age > self._max_forecast_age:
                    raise UpdateFailed(
                        f"Retained forecast exceeded max age "
                        f"({forecast_age.total_seconds()/3600:.1f}h > "
                        f"{self._max_forecast_age.total_seconds()/3600:.1f}h)"
                    ) from err

            _LOGGER.warning(
                "Unable to refresh forecast data, using retained forecast: %s",
                err,
            )

            return self.data
