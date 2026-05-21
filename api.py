import threading
import os
import logging

from requests import Request
from calcs.forecast import fetch_open_meteo_data
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI

# ============================================================
# CHANGED: scheduler added (keeps control over timing)
# ============================================================
from apscheduler.schedulers.background import BackgroundScheduler

from main import (
    get_zip_file_path,
    load_pv_settings_from_zip
)

from calcs.SolarPowerPlant import SolarPowerPlant

# ============================================================
# CHANGED: updated forecast function (today + tomorrow range)
# ============================================================
from calcs.forecast import forecast_today_and_tomorrow

app = FastAPI()

# ============================================================
# NEW: enable DEBUG logging globally
# ============================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

LATEST_DATA = {}
LOCK = threading.Lock()

# ============================================================
# REMOVED: manual sleep loop (replaced by scheduler)
# ============================================================


# ============================================================
# CORE COMPUTE FUNCTION (reused by API + scheduler)
# ============================================================
def compute_forecast():
    logger.debug("COMPUTE START")
    zip_path = get_zip_file_path()
    settings = load_pv_settings_from_zip(zip_path)

    plant = SolarPowerPlant(
        albedo=float(settings['albedo']),
        latitude=float(settings['latitude']),
        longitude=float(settings['longitude']),
        cellsMaxPower=float(settings['cells_max_pPower']),
        cellsArea=float(settings['cells_area']),
        cellsEfficiency=float(settings['cells_efficiency']),
        cellsTempCoeff=float(settings['cells_temp_coeff']),
        diffuseEfficiency=float(settings['diffuse_efficiency']),
        inverterPowerLimit=float(settings['inverter_power_limit']),
        inverterEfficiency=float(settings['inverter_efficiency']),
        isCentralInverter=bool(int(settings['is_central_inverter'])),
        azimuthAngle=float(settings['azimuth_angle']),
        tiltAngle=float(settings['tilt_angle']),
        shadingElevation=[int(x) for x in settings['shading_elevation'].split(',')],
        shadingOpacity=[int(x) for x in settings['shading_opacity'].split(',')]
    )

    forecast = forecast_today_and_tomorrow(
        plant=plant,
        city_name=settings['city_name']
    )
    logger.debug(f"COMPUTE FORECAST LEN = {len(forecast)}")

    payload = {
        "plant": settings,
        "forecast": [
            {"time": t.isoformat(), "wh": wh}
            for t, wh in forecast
        ]
    }

    logger.debug(f"COMPUTE RETURN KEYS = {payload.keys()}")
    logger.debug(f"COMPUTE FORECAST ITEMS = {len(payload['forecast'])}")
    logger.debug(f"COMPUTE RETURN FINAL SAMPLE = {payload['forecast'][:2]}")

    return payload


# ============================================================
# SCHEDULER
# ============================================================
scheduler = BackgroundScheduler()


def refresh_job():
    global LATEST_DATA

    try:
        data = compute_forecast()

        with LOCK:
            LATEST_DATA = data

        print("Periodic refresh executed")

    except Exception as e:
        print("Periodic refresh error:", e)


def midnight_job():
    global LATEST_DATA

    try:
        data = compute_forecast()

        with LOCK:
            LATEST_DATA = data

        print("Midnight refresh executed")

    except Exception as e:
        print("Midnight refresh error:", e)


# ============================================================
# STARTUP HOOK
# ============================================================
@app.on_event("startup")
def startup_event():
    # ============================================================
    # CHANGED: scheduler jobs
    # ============================================================

    scheduler.add_job(refresh_job, "interval", hours=4)

    scheduler.add_job(midnight_job, "cron", hour=0, minute=0)

    # ============================================================
    # CHANGED: warmup run (important!)
    # ensures API is populated immediately after container start
    # ============================================================
    try:
        data = compute_forecast()
        with LOCK:
            LATEST_DATA = data
        print("Warmup forecast executed")
    except Exception as e:
        print("Warmup error:", e)

    scheduler.start()


# ============================================================
# API ENDPOINTS
# ============================================================
@app.get("/forecast")
def get_forecast():
    with LOCK:
        return LATEST_DATA


@app.get("/health")
def health():
    return {"status": "ok"}


# optional: manual refresh trigger
@app.post("/refresh")
def refresh():
    global LATEST_DATA

    data = compute_forecast()

    with LOCK:
        LATEST_DATA = data

    return {"status": "updated"}

@app.get("/debug/open-meteo")
def debug_open_meteo():
    """
    Raw Open-Meteo response inspector
    """
    zip_path = get_zip_file_path()
    settings = load_pv_settings_from_zip(zip_path)

    start_dt = datetime.now(timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0
    )

    end_dt = start_dt + timedelta(hours=24)

    # ============================================================
    # NEW: build exact Open-Meteo request URL for debugging
    # ============================================================
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": settings["latitude"],
        "longitude": settings["longitude"],
        "hourly": "direct_normal_irradiance,diffuse_radiation,shortwave_radiation,temperature_2m",
        "start": start_dt.strftime("%Y-%m-%dT%H:%M"),
        "end": end_dt.strftime("%Y-%m-%dT%H:%M"),
        "timezone": "UTC"
    }

    full_url = Request(
        "GET",
        url,
        params=params
    ).prepare().url

    df = fetch_open_meteo_data(
        settings["latitude"],
        settings["longitude"],
        start_dt,
        end_dt
    )

    if df is None or df.empty:
        return {
            "status": "empty",
            "message": "No data from Open-Meteo",
            "request_url": full_url
        }

    return {
        "status": "ok",

        # ============================================================
        # NEW: expose full Open-Meteo request
        # ============================================================
        "request_url": full_url,

        "columns": list(df.columns),

        # ============================================================
        # OPTIONAL: useful debug info
        # ============================================================
        "rows": len(df),
        "first_time": str(df.iloc[0]["time"]),
        "last_time": str(df.iloc[-1]["time"]),

        "sample": df.head(10).to_dict(orient="records")
    }
