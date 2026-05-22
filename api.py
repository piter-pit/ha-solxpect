import threading
import os
import logging
import time

from requests import Request
from calcs.forecast import fetch_open_meteo_data
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from main import (
    get_zip_file_path,
    load_pv_settings_from_zip
)
from calcs.SolarPowerPlant import SolarPowerPlant
from calcs.forecast import forecast_today_and_tomorrow

logger = logging.getLogger(__name__)
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
    global LATEST_DATA

    logger.debug(f"BEFORE SCHEDULER | LATEST_DATA id={id(LATEST_DATA)}")
    scheduler.add_job(refresh_job, "interval", hours=4)

    scheduler.add_job(midnight_job, "cron", hour=0, minute=0)

    # ============================================================
    # CHANGED: warmup run (important!)
    # ensures API is populated immediately after container start
    # ============================================================
    try:
        data = compute_forecast()
        logger.warning(f"STARTUP: forecast_len={len(data.get('forecast', []))}")
        
        with LOCK:
            LATEST_DATA = data
        logger.warning(f"STARTUP: LATEST_DATA SET id={id(LATEST_DATA)}")
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
        logger.warning(f"API CALLED | LATEST_DATA id={id(LATEST_DATA)}")

        if isinstance(LATEST_DATA, dict):
            logger.warning(f"API forecast len={len(LATEST_DATA.get('forecast', []))}")
        else:
            logger.warning("API LATEST_DATA IS EMPTY OR INVALID")
            
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
