import threading
import os

from fastapi import FastAPI

# ============================================================
# CHANGED: scheduler added (replaces manual worker loop)
# ============================================================
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

from main import (
    get_zip_file_path,
    load_pv_settings_from_zip
)

from calcs.SolarPowerPlant import SolarPowerPlant

# ============================================================
# CHANGED: function name update (was forecast_next_24_hours)
# ============================================================
from calcs.forecast import forecast_today_and_tomorrow

app = FastAPI()

LATEST_DATA = {}
LOCK = threading.Lock()

# ============================================================
# REMOVED: manual sleep-based interval (no longer used)
# INTERVAL_SECONDS = 4 * 60 * 60
# ============================================================


# ============================================================
# CORE COMPUTE FUNCTION (reused by API + scheduler)
# ============================================================
def compute_forecast():
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

    # ============================================================
    # CHANGED: forecast now covers today + tomorrow
    # ============================================================
    forecast = forecast_today_and_tomorrow(
        plant=plant,
        city_name=settings['city_name']
    )

    return {
        "plant": settings,
        "forecast": [
            {
                "time": t.isoformat(),
                "wh": wh
            }
            for t, wh in forecast
        ]
    }


# ============================================================
# SCHEDULER FUNCTIONS (replaces worker loop)
# ============================================================
scheduler = BackgroundScheduler()


def refresh_job():
    """
    Runs every 4 hours
    """
    global LATEST_DATA

    try:
        data = compute_forecast()

        with LOCK:
            LATEST_DATA = data

        print("Periodic refresh executed")

    except Exception as e:
        print("Periodic refresh error:", e)


def midnight_job():
    """
    Runs every day at 00:00 (full reset of daily forecast)
    """
    global LATEST_DATA

    try:
        data = compute_forecast()

        with LOCK:
            LATEST_DATA = data

        print("Midnight refresh executed")

    except Exception as e:
        print("Midnight refresh error:", e)


# ============================================================
# STARTUP HOOK (scheduler init)
# ============================================================
@app.on_event("startup")
def startup_event():
    # every 4 hours
    scheduler.add_job(refresh_job, "interval", hours=4)

    # daily reset at midnight
    scheduler.add_job(midnight_job, "cron", hour=0, minute=0)

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
