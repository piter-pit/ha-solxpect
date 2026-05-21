import logging
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
import pvlib

from .SolarPowerPlant import SolarPowerPlant

logger = logging.getLogger(__name__)


def fetch_open_meteo_data(latitude, longitude, start_dt, end_dt):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "direct_normal_irradiance,"
            "diffuse_radiation,"
            "shortwave_radiation,"
            "temperature_2m"
        ),
        "start": start_dt.strftime("%Y-%m-%dT%H:%M"),
        "end": end_dt.strftime("%Y-%m-%dT%H:%M"),
        "timezone": "UTC"
    }

    full_url = requests.Request('GET', url, params=params).prepare().url
    logger.debug(f"API Request: {full_url}")

    response = requests.get(url, params=params)

    # ============================================================
    # CHANGED: better visibility when API fails (prevents silent empty forecast)
    # ============================================================
    if response.status_code != 200:
        logger.error(f"Open-Meteo error {response.status_code}: {response.text}")
        response.raise_for_status()

    data = response.json()

    logger.debug(f"API Response Keys: {list(data.keys())}")

    if "hourly" in data:
        logger.debug(f"Hourly Data Keys: {list(data['hourly'].keys())}")
        logger.debug(f"Sample Times: {data['hourly']['time'][:3]} ...")
    else:
        logger.warning("No 'hourly' field in API response")
        return pd.DataFrame()

    df = pd.DataFrame(data["hourly"])

    # ============================================================
    # CHANGED: ensure strict UTC datetime alignment
    # ============================================================
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)

    return df


def prepare_weather(dt, meteo_df):

    if meteo_df is None or meteo_df.empty:
        logger.warning("Empty meteo dataframe")
        return None

    # ============================================================
    # CHANGED: FIX critical bug (exact match replaced with nearest hour)
    # ============================================================
    dt = pd.Timestamp(dt, tz="UTC")

    idx = (meteo_df["time"] - dt).abs().idxmin()
    row = meteo_df.loc[idx]

    if row is None or pd.isna(row["temperature_2m"]):
        logger.warning(f"No valid weather data for hour {dt}")
        return None

    return {
        "solar_power_normal": row["direct_normal_irradiance"],
        "solar_power_diffuse": row["diffuse_radiation"],
        "shortwave_radiation": row["shortwave_radiation"],
        "ambient_temperature": row["temperature_2m"]
    }


# ============================================================
# CHANGED FUNCTION NAME (was: forecast_next_24_hours)
# ============================================================
def forecast_today_and_tomorrow(plant: SolarPowerPlant, city_name: str):

    start_dt = datetime.now(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )

    end_dt = start_dt + timedelta(hours=48)

    latitude = plant.latitude
    longitude = plant.longitude

    meteo_df = fetch_open_meteo_data(latitude, longitude, start_dt, end_dt)

    logger.debug(f"Forecasting for {city_name} ({latitude}, {longitude})")

    # ============================================================
    # CHANGED: debug guard (prevents silent empty forecast)
    # ============================================================
    if meteo_df.empty:
        logger.error("Meteo dataframe is empty - Open-Meteo returned no data")
        return []

    results = []

    for hour in range(48):

        hour_start = start_dt + timedelta(hours=hour)

        logger.info(f"Hour: {hour_start.strftime('%Y-%m-%d %H:%M')}")

        dt_step = hour_start + timedelta(minutes=30)
        hour_end = hour_start + timedelta(hours=1)

        inputs = prepare_weather(hour_end, meteo_df)

        if inputs is None:
            logger.warning(f"{dt_step.strftime('%Y-%m-%d %H:%M')} – No data available")
            continue

        energy_wh = plant.getPower(
            solarPowerNormal=inputs["solar_power_normal"],
            solarPowerDiffuse=inputs["solar_power_diffuse"],
            shortwaveRadiation=inputs["shortwave_radiation"],
            epochTimeSeconds=int(dt_step.timestamp()),
            ambientTemperature=inputs["ambient_temperature"]
        )

        results.append((hour_end, energy_wh))

    return results


def get_shading_factor(elevation_deg, azimuth_deg, thresholds, opacities):

    bin_index = int(azimuth_deg // 10) % 36
    threshold = thresholds[bin_index]
    opacity = opacities[bin_index]

    if elevation_deg < threshold:
        factor = 1.0 - opacity
        logger.debug(
            f"Shading applied: azimuth={azimuth_deg:.1f}°, "
            f"bin={bin_index}, elevation={elevation_deg:.1f}°, "
            f"threshold={threshold:.1f}°, opacity={opacity:.1f}, factor={factor:.2f}"
        )
        return factor
    else:
        logger.debug(
            f"No shading: azimuth={azimuth_deg:.1f}°, "
            f"bin={bin_index}, elevation={elevation_deg:.1f}°, "
            f"threshold={threshold:.1f}°"
        )
        return 1.0
