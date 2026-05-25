# Home Assistant solXpect Integration

A custom Home Assistant integration for photovoltaic (PV) production forecasting based on:

- https://github.com/blablubbbb/solXpect_meets_python  
- https://github.com/woheller69/solxpect  

This integration brings solar production forecasting directly into Home Assistant using solXpect-based calculation logic.

---

# Overview

The integration adapts the solXpect PV forecasting model into Home Assistant sensors.

The original solXpect model calculates PV production using:

- solar geometry
- direct and diffuse radiation
- weather forecast data (Open-Meteo)
- panel orientation (azimuth & tilt)
- temperature influence
- inverter limits
- optional shading effects

This Home Assistant integration exposes these calculations as sensors for automation and dashboards.

---

# Features

- PV production forecast:
  - Today
  - Tomorrow
- Native Home Assistant sensors
- HACS compatible installation
- Based on solXpect physics model
- Uses Open-Meteo weather forecasts
- Lightweight calculation layer

---

# Installation (HACS)

## Add custom repository

In HACS:

1. Go to **HACS → Integrations**
2. Open menu (⋮)
3. Select **Custom repositories**
4. Add: https://github.com/piter-pit/ha-solxpect
5. Category: **Integration**
6. Click **Add**
7. Search for **SolXpect PV Forecast**
8. Install in HACS
13. Restart Home Assistant

---

# Configuration

After installation:

Settings → Devices & Services → Add Integration → solXpect

---

# Current limitations

- Only **one PV string / panel group** is supported - No multiple orientations

---

# Sensors

The integration creates the following sensors:

| Sensor | Description |
|------|-------------|
| `sensor.solxpect_today` | PV forecast for today |
| `sensor.solxpect_tomorrow` | PV forecast for tomorrow |

Units: kWh

## Detailed hourly data

Each sensor also provides detailed hourly PV production values in its attributes under `hours`.

---

# Use cases

- Battery charge planning
- EV charging optimization
- Smart home energy scheduling
- Forecast-based automations
- Energy dashboards

---

# Based on

## solXpect
https://github.com/woheller69/solxpect

SolXpect is a photovoltaic forecasting model based on physical solar calculations:
- solar position
- irradiance models
- temperature correction
- inverter constraints
- shading

It provides hourly and daily PV forecasts.

---

## solXpect_meets_python
https://github.com/blablubbbb/solXpect_meets_python

Python adaptation of solXpect designed for integration into automation systems like Home Assistant.

---

# Credits

Thanks to:
- solXpect authors
- solXpect_meets_python contributors
- Open-Meteo weather API

---

# Development Status

This integration is currently in active development.

Some features may change, break, or be refactored without notice.

It is intended for testing and early adoption purposes.

---

# Disclaimer

This integration is provided "as is", without any warranties.

Use it at your own risk.

The authors are not responsible for:
- incorrect PV forecasts
- data inaccuracies
- Home Assistant instability
- issues caused by external weather data (Open-Meteo)
- incorrect automation decisions based on forecasts

Always verify critical automations with additional safeguards.
