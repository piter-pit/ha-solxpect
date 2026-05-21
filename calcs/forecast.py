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

    if response.status_code != 200:
        logger.error(f"Open-Meteo error {response.status_code}: {response.text}")
        response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        logger.warning("No hourly field in response")
        return pd.DataFrame()

    df = pd.DataFrame(data["hourly"])

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)

    return df


def prepare_weather(dt, meteo_df):

    if meteo_df is None or meteo_df.empty:
        logger.warning("Empty meteo dataframe")
        return None

    # FIX 1: unified timestamp normalization (UTC consistency)
    dt = pd.Timestamp(dt)
    if dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    else:
        dt = dt.tz_convert("UTC")

    # ============================================================
    # FIX 2 (CRITICAL): remove nearest-match logic
    # Reason: it caused wrong hour mapping and silent data loss
    # ============================================================

    row = meteo_df[meteo_df["time"] == dt]

    if row.empty:
        logger.warning(f"No exact match for {dt}")
        return None

    row = row.iloc[0]

    if pd.isna(row["temperature_2m"]):
        logger.warning(f"No valid weather for {dt}")
        return None

    return {
        "solar_power_normal": row["direct_normal_irradiance"],
        "solar_power_diffuse": row["diffuse_radiation"],
        "shortwave_radiation": row["shortwave_radiation"],
        "ambient_temperature": row["temperature_2m"]
    }


def forecast_today_and_tomorrow(plant: SolarPowerPlant, city_name: str):

    now = datetime.now(timezone.utc)

    # FIX 3: correct day alignment (stable full-day window)
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # FIX 4: keep 3 days window (OK)
    end_dt = start_dt + timedelta(days=3)

    meteo_df = fetch_open_meteo_data(
        plant.latitude,
        plant.longitude,
        start_dt,
        end_dt
    )

    if meteo_df.empty:
        logger.error("Empty meteo dataframe")
        return []

    results = []

    # ============================================================
    # FIX 5 (CRITICAL): iterate over REAL Open-Meteo timestamps
    # instead of synthetic hourly generator
    # ============================================================
    for dt in meteo_df["time"]:

        logger.info(f"Hour: {dt.strftime('%Y-%m-%d %H:%M')}")

        inputs = prepare_weather(dt, meteo_df)

        if inputs is None:
            logger.warning(f"No data for {dt}")
            continue

        energy_wh = plant.getPower(
            solarPowerNormal=inputs["solar_power_normal"],
            solarPowerDiffuse=inputs["solar_power_diffuse"],
            shortwaveRadiation=inputs["shortwave_radiation"],
            epochTimeSeconds=int(dt.timestamp()),
            ambientTemperature=inputs["ambient_temperature"]
        )

        results.append((dt, energy_wh))

    return results


def get_shading_factor(elevation_deg, azimuth_deg, thresholds, opacities):

    bin_index = int(azimuth_deg // 10) % 36
    threshold = thresholds[bin_index]
    opacity = opacities[bin_index]

    if elevation_deg < threshold:
        return 1.0 - opacity
    else:
        return 1.0
