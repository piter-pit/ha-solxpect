from datetime import datetime, timedelta, timezone
import requests
import pandas as pd
import pvlib
import tzlocal

from .SolarPowerPlant import SolarPowerPlant

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

    response = requests.get(url, params=params)

    if response.status_code != 200:
        response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        return pd.DataFrame()

    df = pd.DataFrame(data["hourly"])

    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)

    return df


def prepare_weather(dt, meteo_df):

    if meteo_df is None or meteo_df.empty:
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
        return None

    row = row.iloc[0]

    if pd.isna(row["temperature_2m"]):
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

    meteo_df = fetch_open_meteo_data(
        plant.latitude,
        plant.longitude,
        start_dt,
        end_dt
    )

    if meteo_df.empty:
        return []

    results = []

    # ============================================================
    # FIX 5 (CRITICAL): iterate over REAL Open-Meteo timestamps
    # instead of synthetic hourly generator
    # ============================================================
    for hour in range(48):
        hour_start = start_dt + timedelta(hours=hour)
        energy_wh = 0.0

        dt_step = hour_start + timedelta(minutes=30) #Immitate solXpect implementataion
        hour_end = hour_start + timedelta(hours=1)
        inputs = prepare_weather(hour_end, meteo_df)

        if inputs is None:
            continue
        
        energy_wh = plant.getPower(
            solarPowerNormal=inputs["solar_power_normal"],
            solarPowerDiffuse=inputs["solar_power_diffuse"],
            shortwaveRadiation=inputs["shortwave_radiation"],
            epochTimeSeconds=int(dt_step.timestamp()),
            ambientTemperature=inputs["ambient_temperature"]
        )
        results.append((hour_start, energy_wh))
        
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
        return factor
    else:
        return 1.0
