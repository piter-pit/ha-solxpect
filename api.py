import threading
import os

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

LATEST_DATA = {}
LOCK = threading.Lock()

# ============================================================
# REMOVED: manual sleep loop (replaced by scheduler)
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

    start_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end_dt = start_dt + timedelta(hours=24)

    df = fetch_open_meteo_data(
        settings["latitude"],
        settings["longitude"],
        start_dt,
        end_dt
    )

    if df is None or df.empty:
        return {
            "status": "empty",
            "message": "No data from Open-Meteo"
        }

    return {
        "status": "ok",
        "columns": list(df.columns),
        "sample": df.head(10).to_dict(orient="records")
    }
