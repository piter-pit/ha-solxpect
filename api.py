import threading
import os
import time
import tzlocal
import json

from requests import Request
from calcs.forecast import fetch_open_meteo_data
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from calcs.SolarPowerPlant import SolarPowerPlant
from calcs.forecast import forecast_today_and_tomorrow

app = FastAPI()

LATEST_DATA = {}
LOCK = threading.Lock()

def load_pv_settings():
    path = os.getenv("CONFIG_PATH", "/app/config/config.json")
    with open(path, "r") as f:
        return json.load(f)

def compute_forecast():
    settings = load_pv_settings()
    SYSTEM_TZ = tzlocal.get_localzone()

    plant = SolarPowerPlant(
        albedo=float(settings['albedo']),
        latitude=float(settings['latitude']),
        longitude=float(settings['longitude']),
        cellsMaxPower=float(settings['cells_max_power']),
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
        city_name="PV"
    )

    payload = {
        "plant": settings,
        "forecast": [
            {"time": t.astimezone(SYSTEM_TZ).isoformat(), "wh": wh}
            for t, wh in forecast
        ]
    }

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
