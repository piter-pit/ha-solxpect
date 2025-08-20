import os
import zipfile
import sqlite3
import tempfile
import logging
from datetime import datetime, timezone, timedelta

from calcs.SolarPowerPlant import SolarPowerPlant
from calcs.forecast import forecast_next_24_hours

def prompt_for_zip_file():
    path = input("Enter path to ZIP file containing SQLITE.db: ").strip()
    #For now just use fixed path
    #path = r"C:\Users\userId\Downloads\solXpect.zip"
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")
    return path

def load_pv_settings_from_zip(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        db_candidates = [f for f in zip_ref.namelist() if f.endswith('SQLITE.db') and 'databases/' in f]
        if not db_candidates:
            raise FileNotFoundError("No SQLITE.db found in 'databases/' folder inside ZIP.")
        
        db_path_in_zip = db_candidates[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            extracted_db_path = zip_ref.extract(db_path_in_zip, path=temp_dir)
            conn = sqlite3.connect(extracted_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT CITIES_TO_WATCH.*, GENERAL_DATA.timezone_seconds FROM CITIES_TO_WATCH JOIN GENERAL_DATA ON CITIES_TO_WATCH.city_id = GENERAL_DATA.city_id")

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            conn.close()

            if not rows:
                raise ValueError("No data found in CITIES_TO_WATCH table.")

            if len(rows) == 1:
                selected_row = rows[0]
            else:
                print("Multiple PV plant configurations found:")
                for i, row in enumerate(rows):
                    print(f"[{i}] city_name: {row[3]}, rank: {row[2]}")
                index = int(input("Select row index to use: "))
                selected_row = rows[index]

            return dict(zip(columns, selected_row))

# 🔁 Run the full workflow
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,  # 👈 This enables DEBUG messages
        format="%(levelname)s:%(name)s:%(message)s"
    )
    logger = logging.getLogger(__name__)

    zip_path = prompt_for_zip_file()
    settings = load_pv_settings_from_zip(zip_path)
    print("🔍 Settings loaded from ZIP:")
    for key, value in settings.items():
        print(f"  {key}: {value}")
    plant_timezone = timezone(timedelta(seconds=int(settings["timezone_seconds"])))
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

    forecast24 = forecast_next_24_hours(
        plant=plant,
        city_name=settings['city_name']
    )
    for hour_end_utc, energy_wh in forecast24:
        hour_end_local = hour_end_utc.astimezone(plant_timezone)
        print(f"{hour_end_local.strftime('%Y-%m-%d %H:%M')} → {energy_wh:.2f} Wh")
