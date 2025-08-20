# ☀️ solXpect_meets_python

This Python library reproduces the energy output calculations of the original `SolarPowerPlant.java` class from [solXpect](https://github.com/woheller69/solxpect), with one minor difference: it uses a different package (`pvlib`) to calculate the sun's position.

The goal is to provide a transparent, reproducible, and physically aligned implementation of solXpect's solar energy model — useful for validation, experimentation, and integration into larger forecasting workflows.

---

## 📦 Features

- ✅ Reproduces solXpect's energy output logic hour-by-hour
- ✅ Uses Open-Meteo API for weather data (irradiance, temperature)
- ✅ Supports shading logic, temperature derating, and inverter clipping
- ✅ Reads plant configuration from a ZIP file (Backup database file from solXpect)
- ✅ Outputs hourly energy forecasts in Wh, adjusted to local time zone

---

## 🔧 Requirements

- Python 3.9+
- Internet connection (for Open-Meteo API)
- Backup database file from solXpect (ZIP containing `SQLITE.db`)

### 📚 Dependencies

| Library         | Purpose                                      |
|----------------|----------------------------------------------|
| `pvlib`         | Solar position calculation                  |
| `requests`      | API calls to Open-Meteo                     |
| `sqlite3`       | Reading plant configuration from ZIP        |
| `pandas`        | Data handling and time series manipulation  |

---

## 🚀 Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/solar-forecast-repro.git
   cd solar-forecast-repro
