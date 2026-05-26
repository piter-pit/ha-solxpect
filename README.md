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
9. Settings → Devices & Services → Add Integration → solXpect PV Forecast

---

# Configuration

The configuration UI is still being refined and may require some additional polishing.  
For now, please note the following important details:

- All configuration fields must currently be filled in.
- `Cells Max Power` is currently **not used directly** in calculations.  
  Since `Cells Efficiency` and `Cells Area` were introduced, the panel power is calculated automatically from these values.

## Geographic Coordinates

Latitude and longitude should be entered in decimal format, for example:

```text
13.92873
```

Coordinate conventions follow the Open-Meteo API standard:

- Positive latitude values = Northern Hemisphere
- Negative latitude values = Southern Hemisphere
- Positive longitude values = Eastern Hemisphere
- Negative longitude values = Western Hemisphere

Examples:

```text
Latitude: 52.2297
Longitude: 21.0122
```

## Central Inverter Mode

If `Is Central Inverter` is enabled, the total generated PV power will be limited by the configured `Inverter Power Limit`.

## Shading Configuration

Each shading cell must contain exactly **36 comma-separated values** representing obstacles for azimuth sectors in 10° increments:

```text
0°–10°, 10°–20°, 20°–30°, ...
```

### Shading Elevation

`Shading Elevation` defines the maximum obstacle height angle for each sector:

- Range: `0°–90°`

### Shading Opacity

`Shading Opacity` defines the attenuation strength of the obstacle:

- Range: `0%–100%`

## Important Notes About Shading

Shading affects only the **direct beam irradiation** component.

If forecast values still appear too high after configuring shading, it is recommended to reduce the `Diffuse Efficiency` parameter to better match real-world conditions.

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

SolXpect is a photovoltaic forecasting model for Android based on physical solar calculations:
- solar position
- irradiance models
- temperature correction
- inverter constraints
- shading

## solXpect_meets_python
https://github.com/blablubbbb/solXpect_meets_python

Python adaptation of solXpect.

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
