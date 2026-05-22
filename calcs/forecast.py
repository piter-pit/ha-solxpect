import logging
from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
import pvlib
import tzlocal

from .SolarPowerPlant import SolarPowerPlant

logger = logging.getLogger(__name__)

def fetch_open_meteo_data(latitude, longitude, start_dt, end_dt):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "direct_normal_irradiance,diffuse_radiation,shortwave_radiation,temperature_2m",
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

    row = meteo_df.loc[meteo_df["time"] == dt]

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

    SYSTEM_TZ = tzlocal.get_localzone()

    now_local = datetime.now(SYSTEM_TZ)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(hours=48)

    start_dt = start_local.astimezone(timezone.utc)
    end_dt = end_local.astimezone(timezone.utc)

    SYSTEM_TZ = tzlocal.get_localzone()
    
    logger.debug(f"SYSTEM_TZ = {SYSTEM_TZ}")
    logger.debug(f"now_local = {now_local} | tz={now_local.tzinfo}")
    logger.debug(f"start_local = {start_local} | tz={start_local.tzinfo}")
    logger.debug(f"end_local = {end_local} | tz={end_local.tzinfo}")
    logger.debug(f"start_dt (UTC) = {start_dt} | tz={start_dt.tzinfo}")
    logger.debug(f"end_dt (UTC) = {end_dt} | tz={end_dt.tzinfo}")
    logger.debug(f"offset_hours = {(start_local - start_dt).total_seconds() / 3600}")

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
    for hour in range(48):
        hour_start = start_dt + timedelta(hours=hour)
        energy_wh = 0.0

        logger.info(f"⏱️ Hour: {hour_start.strftime('%Y-%m-%d %H:%M')}")

        dt_step = hour_start + timedelta(minutes=30) #Immitate solXpect implementataion
        hour_end = hour_start + timedelta(hours=1)
        inputs = prepare_weather(hour_end, meteo_df)

        if inputs is None:
            logger.warning(f"{dt_step.strftime('%Y-%m-%d %H:%M')} – No data available")
            continue

        logger.info(
            f"DEBUG getPower INPUT | "
            f"time={hour_start.isoformat()} | "
            f"epoch={int(dt_step.timestamp())} | "
            f"DNI={inputs['solar_power_normal']} | "
            f"diffuse={inputs['solar_power_diffuse']} | "
            f"sw={inputs['shortwave_radiation']} | "
            f"temp={inputs['ambient_temperature']}"
        )
        
        energy_wh = plant.getPower(
            solarPowerNormal=inputs["solar_power_normal"],
            solarPowerDiffuse=inputs["solar_power_diffuse"],
            shortwaveRadiation=inputs["shortwave_radiation"],
            epochTimeSeconds=int(dt_step.timestamp()),
            ambientTemperature=inputs["ambient_temperature"]
        )
        results.append((hour_start, energy_wh))
        logger.debug(f"APPEND | hour_end={hour_end} | energy={energy_wh}")
        
    logger.info(f"FORECAST DONE | results_count={len(results)}")
    return results

def get_shading_factor(elevation_deg, azimuth_deg, thresholds, opacities):
    """
    Applies azimuth-dependent shading logic.

    thresholds: list of elevation thresholds per azimuth bin
    opacities: list of shading percentages per azimuth bin
    Assumes 36 bins covering 0–360° in 10° increments.
    """
    bin_index = int(azimuth_deg // 10) % 36
    threshold = thresholds[bin_index]
    opacity = opacities[bin_index]

    if elevation_deg < threshold:
        factor = 1.0 - opacity
        logger.debug(
            f"⛅ Shading applied: azimuth={azimuth_deg:.1f}° → bin={bin_index}, "
            f"elevation={elevation_deg:.1f}° < threshold={threshold:.1f}°, "
            f"opacity={opacity:.1f}%, factor={factor:.2f}"
        )
        return factor
    else:
        logger.debug(
            f"☀️ No shading: azimuth={azimuth_deg:.1f}° → bin={bin_index}, "
            f"elevation={elevation_deg:.1f}° ≥ threshold={threshold:.1f}°"
        )
        return 1.0
