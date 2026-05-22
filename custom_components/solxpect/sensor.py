from homeassistant.helpers.entity import Entity

DOMAIN = "solxpect"

async def async_setup_entry(hass, entry, async_add_entities):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SolxpectSensor(coordinator)
    ])


class SolxpectSensor(Entity):

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def name(self):
        return "SolXpect Forecast"

    @property
    def state(self):
        data = self.coordinator.data
        if not data:
            return None
        return round(data["forecast"][0]["wh"], 2)

    @property
    def extra_state_attributes(self):
        return {
            "forecast": self.coordinator.data["forecast"]
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
