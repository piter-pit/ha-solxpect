import os
import zipfile
import sqlite3
import tempfile
import logging
import time  # ============================================================
# NEW: scheduler sleep
# ============================================================

from datetime import datetime, timezone, timedelta

from calcs.SolarPowerPlant import SolarPowerPlant
from calcs.forecast import forecast_next_24_hours


# ============================================================
# REMOVED INTERACTIVE INPUT (Docker incompatible)
# ============================================================
# def prompt_for_zip_file():
#     path = input("Enter path to ZIP file containing SQLITE.db: ").strip()
#     #For now just use fixed path
#     #path = r"C:\Users\userId\Downloads\solXpect.zip"
#     if not os.path.isfile(path):
#         raise FileNotFoundError(f"File not found: {path}")
#     return path


# ============================================================
# NEW: Docker-friendly file resolution
# ============================================================
def get_zip_file_path():
    """
    Priority:
    1. ENV variable (best for Docker flexibility)
    2. default mounted path (/app/data)
    """
    return os.getenv("ZIP_PATH", "/app/data/solXpect.zip")


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
                print("Multiple PV plant configurations found:", flush=True)
                for i, row in enumerate(rows):
                    print(f"[{i}] city_name: {row[3]}, rank: {row[2]}", flush=True)

                index = int(input("Select row index to use: "))  # WARNING: still interactive fallback
                selected_row = rows[index]

            return dict(zip(columns, selected_row))

        print(f"Sleeping for {INTERVAL_SECONDS / 3600} hours", flush=True)
        time.sleep(INTERVAL_SECONDS)
