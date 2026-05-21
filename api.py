import threading
import time
import os

from fastapi import FastAPI

from main import (
    get_zip_file_path,
    load_pv_settings_from_zip
)

from calcs.SolarPowerPlant import SolarPowerPlant
from calcs.forecast import forecast_next_24_hours

app = FastAPI()

LATEST_DATA = {}
LOCK = threading.Lock()

INTERVAL_SECONDS = 4 * 60 * 60


# ============================================================
# CORE COMPUTE FUNCTION (reused by API + background worker)
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

    forecast = forecast_next_24_hours(
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
# BACKGROUND WORKER (updates data every 4h)
# ============================================================
def worker():
    global LATEST_DATA

    while True:
        try:
            data = compute_forecast()

            with LOCK:
                LATEST_DATA = data

            print("Forecast updated")

        except Exception as e:
            print("Worker error:", e)

        time.sleep(INTERVAL_SECONDS)


# ============================================================
# STARTUP HOOK
# ============================================================
@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


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
