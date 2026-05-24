import math
import pvlib
import logging

from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)

class SolarPowerPlant: 
        #Class should reproduce the java class by the same name in solXpect:
        #https://github.com/woheller69/solxpect/blob/main/app/src/main/java/org/woheller69/weather/SolarPowerPlant.java
        #Only significant difference is the library which is used to calculate the solar position
    def __init__(self, albedo, latitude, longitude, cellsMaxPower, cellsArea, cellsEfficiency,
                 cellsTempCoeff, diffuseEfficiency, inverterPowerLimit, inverterEfficiency,
                 isCentralInverter, azimuthAngle, tiltAngle, shadingElevation, shadingOpacity):
        self.albedo = albedo  # fraction (e.g. 0.18), ground reflectivity
        self.latitude = latitude  # degrees
        self.longitude = longitude  # degrees
        self.cellsMaxPower = cellsMaxPower  # W
        self.cellsArea = cellsArea  # m²
        self.cellsEfficiency = cellsEfficiency / 100.0  # fraction (e.g. 0.85)
        self.cellsTempCoeff = cellsTempCoeff / 100.0  # fraction per °C (e.g. -0.004)
        self.diffuseEfficiency = diffuseEfficiency / 100.0  # fraction (e.g. 0.85)
        self.inverterPowerLimit = inverterPowerLimit  # W
        self.inverterEfficiency = inverterEfficiency / 100.0  # fraction (e.g. 0.96)
        self.isCentralInverter = bool(isCentralInverter)
        self.azimuthAngle = azimuthAngle  # degrees, 0 = North, 90 = East
        self.tiltAngle = tiltAngle  # degrees  from horizontal
        self.shadingElevation = shadingElevation  # array of elevation threshold angles per azimuth bin
        self.shadingOpacity = shadingOpacity  # list of 36 opacity values (0–100) one per azimuth bin

    def getPower(self, solarPowerNormal, solarPowerDiffuse, shortwaveRadiation, epochTimeSeconds, ambientTemperature):
        # Inputs:
        # solarPowerNormal: W/m², direct irradiance normal to sun
        # solarPowerDiffuse: W/m², diffuse irradiance
        # shortwaveRadiation: W/m², total shortwave (used for albedo)
        # epochTimeSeconds: Unix timestamp
        # ambientTemperature: °C

        _LOGGER.debug(
            "GETPOWER SELF STATE: %s",
            self.__dict__
        )

        i = datetime.fromtimestamp(epochTimeSeconds, tz=timezone.utc)

        # Use pvlib to calculate solar position
        solarPosition = pvlib.solarposition.get_solarposition(i, self.latitude, self.longitude)

        solarAzimuth = solarPosition['azimuth'].iloc[0]  # degrees
        solarElevation = solarPosition['elevation'].iloc[0]  # degrees

        # Calculate sun direction vector
        directionSun = [
            math.sin(math.radians(solarAzimuth)) * math.cos(math.radians(solarElevation)),
            math.cos(math.radians(solarAzimuth)) * math.cos(math.radians(solarElevation)),
            math.sin(math.radians(solarElevation))
        ]

        # Calculate panel normal vector
        normalPanel = [
            math.sin(math.radians(self.azimuthAngle)) * math.cos(math.radians(90 - self.tiltAngle)),
            math.cos(math.radians(self.azimuthAngle)) * math.cos(math.radians(90 - self.tiltAngle)),
            math.sin(math.radians(90 - self.tiltAngle))
        ]

        # Calculate scalar product of sun direction and panel normal
        efficiency = 0.0
        if solarPowerNormal > 0:
            efficiency = sum(directionSun[j] * normalPanel[j] for j in range(3))
            efficiency = max(0.0, efficiency)

            if efficiency > 0:
                shFactor = 0.0

                numSteps = 6
                interval = 3600 // numSteps

                for j in range(numSteps):
                    shEpoch = epochTimeSeconds - ((numSteps - 1) * interval // 2) + j * interval
                    shDateTime = datetime.fromtimestamp(shEpoch, tz=timezone.utc)

                    shPosition = pvlib.solarposition.get_solarposition(shDateTime, self.latitude, self.longitude)
                    shSolarAzimuth = shPosition['azimuth'].iloc[0]
                    shSolarElevation = shPosition['elevation'].iloc[0]

                    shadingIndex = ((((int(round((shSolarAzimuth + 5) / 10))) - 1) % 36 + 36) % 36)

                    if self.shadingElevation[shadingIndex] > shSolarElevation:
                        shFactor += (100 - self.shadingOpacity[shadingIndex]) / (numSteps * 100.0)
                    else:
                        shFactor += 100 / (numSteps * 100.0)

                efficiency *= shFactor

        # Calculate reflected radiation
        tiltRad = math.radians(self.tiltAngle)
        reflected = shortwaveRadiation * (0.5 - 0.5 * math.cos(tiltRad)) * self.albedo

        # Total irradiance on cell
        totalIrradianceOnCell = (
            solarPowerNormal * efficiency +
            solarPowerDiffuse * self.diffuseEfficiency +
            reflected
        )

        cellTemperature = ambientTemperature + 0.0342 * totalIrradianceOnCell

        if self.cellsEfficiency != 0 and self.cellsArea != 0:
            dcPower = totalIrradianceOnCell * (1 + (cellTemperature - 25) * self.cellsTempCoeff) * self.cellsEfficiency * self.cellsArea
        else:
            dcPower = totalIrradianceOnCell / 1000 * (1 + (cellTemperature - 25) * self.cellsTempCoeff) * self.cellsMaxPower
        
        if not self.isCentralInverter:
            acPower = min(dcPower * self.inverterEfficiency, self.inverterPowerLimit)
                
            _LOGGER.debug(
                "BRANCH: NON-CENTRAL inverter → CLAMP applied → acPower=%s",
            acPower,
            )
                
        else:
            acPower = dcPower * self.inverterEfficiency
                
            _LOGGER.debug(
                "BRANCH: CENTRAL inverter → NO CLAMP → acPower=%s",
            acPower,
            )

        _LOGGER.debug(
            "CentralInv= %s DC=%s AC_before_limit=%s LIMIT=%s FINAL=%s",
            self.isCentralInverter,
            dcPower,
            dcPower * self.inverterEfficiency,
            self.inverterPowerLimit,
            acPower,
        )

        return float(acPower)

    @staticmethod
    def calcDiffuseEfficiency(tilt):
        return int(50 + 50 * math.cos(math.radians(tilt)))

    @staticmethod
    def calcCellTemperature(ambientTemperature, totalIrradiance):
        return ambientTemperature + 0.0342 * totalIrradiance
