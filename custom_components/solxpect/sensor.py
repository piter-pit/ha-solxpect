from homeassistant.helpers.entity import Entity


class SolxpectSensor(Entity):

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def name(self):
        return "Solxpect Forecast"

    @property
    def state(self):
        if not self.coordinator.data:
            return 0

        return sum(x[1] for x in self.coordinator.data[:24])
