import math
import pvlib
from datetime import datetime, timezone

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
        self.isCentralInverter = isCentralInverter  # boolean
        self.azimuthAngle = azimuthAngle  # degrees, 0 = North, 90 = East
        self.tiltAngle = tiltAngle  # degrees  from horizontal
        self.shadingElevation = shadingElevation  # array of elevation threshold angles per azimuth bin
        self.shadingOpacity = shadingOpacity  # list of 36 opacity values (0–100) one per azimuth bin

    def getPower(self, solarPowerNormal, solarPowerDiffuse, shortwaveRadiation, epochTimeSeconds, ambientTemperature):
	    # Inputs:
        # solarPowerNormal: W/m², direct irradiance normal to sun
        # solarPowerDiffuse: W/m², diffuse irradiance
        # shortwaveRadiation: W/m², total shortwave (used for albedo)
        # epochTimeSeconds: Unix timestamp, When you want to calculate the Energy between 9am and 10am you should give the function 9:30am
        # ambientTemperature: °C
        # Convert timestamp to UTC datetime

		logger.debug(
    		f"getPower START | epoch={epochTimeSeconds} | "
    		f"DNI={solarPowerNormal} | diffuse={solarPowerDiffuse} | "
    		f"sw={shortwaveRadiation} | temp={ambientTemperature}"
		)
		
        i = datetime.fromtimestamp(epochTimeSeconds, tz=timezone.utc)

        # Use pvlib to calculate solar position
        solarPosition = pvlib.solarposition.get_solarposition(i, self.latitude, self.longitude)

		logger.debug(f"pvlib output rows={len(solarPosition)}")

        solarAzimuth = solarPosition['azimuth'].iloc[0]  # degrees
        solarElevation = solarPosition['elevation'].iloc[0]  # degrees

		logger.debug(f"sun pos | az={solarAzimuth} | el={solarElevation}")

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
            efficiency = max(0.0, efficiency)  # set to 0 if sun is behind panel

            if efficiency > 0:
                shFactor = 0.0

                # Calculate shading in 6 intervals per hour -> 10min steps xx:05 / xx:15 / xx:25 / xx:35 / xx:45 / xx:55
                numSteps = 6
                interval = 3600 // numSteps  # seconds

                for j in range(numSteps):
                    shEpoch = epochTimeSeconds - ((numSteps - 1) * interval // 2) + j * interval
                    shDateTime = datetime.fromtimestamp(shEpoch, tz=timezone.utc)

                    shPosition = pvlib.solarposition.get_solarposition(shDateTime, self.latitude, self.longitude)
                    shSolarAzimuth = shPosition['azimuth'].iloc[0]
                    shSolarElevation = shPosition['elevation'].iloc[0]

                    # Shading values are provided in 10 degree ranges -> total of 36 ranges
                    shadingIndex = ((((int(round((shSolarAzimuth + 5) / 10))) - 1) % 36 + 36) % 36)

                    if self.shadingElevation[shadingIndex] > shSolarElevation:
                        shFactor += (100 - self.shadingOpacity[shadingIndex]) / (numSteps * 100.0)
                    else:
                        shFactor += 100 / (numSteps * 100.0) #numSteps iterations with no shading give 100%

                efficiency *= shFactor  # apply shading factor

        # Calculate reflected radiation — flat plate equivalent
        tiltRad = math.radians(self.tiltAngle)
        reflected = shortwaveRadiation * (0.5 - 0.5 * math.cos(tiltRad)) * self.albedo

        # Total irradiance on cell (W/m²)
        totalIrradianceOnCell = (
            solarPowerNormal * efficiency +
            solarPowerDiffuse * self.diffuseEfficiency +
            reflected
        )

        # Estimate cell temperature using Ross modelhttps://www.researchgate.net/publication/275438802_Thermal_effects_of_the_extended_holographic_regions_for_holographic_planar_concentrator
        #implementation matches solXpect
        cellTemperature = ambientTemperature + 0.0342 * totalIrradianceOnCell

        # Calculate DC power (W)
        if self.cellsEfficiency != 0 and self.cellsArea != 0:
            dcPower = totalIrradianceOnCell * (1 + (cellTemperature - 25) * self.cellsTempCoeff) * self.cellsEfficiency * self.cellsArea
        else: #assume cellMaxPower is defined at 1000W/sqm
            dcPower = totalIrradianceOnCell / 1000 * (1 + (cellTemperature - 25) * self.cellsTempCoeff) * self.cellsMaxPower

        # Convert to AC power (W)
        if not self.isCentralInverter:
            acPower = min(dcPower * self.inverterEfficiency, self.inverterPowerLimit)
        else:
            acPower = dcPower * self.inverterEfficiency  # no clipping for central inverter

		logger.debug(f"getPower RESULT | acPower={acPower}")

        return float(acPower)

    @staticmethod
    def calcDiffuseEfficiency(tilt):
        # Returns % efficiency for diffuse light based on tilt angle
        return int(50 + 50 * math.cos(math.radians(tilt)))

    @staticmethod
    def calcCellTemperature(ambientTemperature, totalIrradiance):
        #Ross model: https://www.researchgate.net/publication/275438802_Thermal_effects_of_the_extended_holographic_regions_for_holographic_planar_concentrator
        #assuming "not so well cooled" : 0.0342
        return ambientTemperature + 0.0342 * totalIrradiance
