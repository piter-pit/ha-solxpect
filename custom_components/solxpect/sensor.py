from homeassistant.helpers.update_coordinator import CoordinatorEntity

DOMAIN = "solxpect"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SolxpectTodaySensor(coordinator),
        SolxpectTomorrowSensor(coordinator),
    ])


class SolxpectTodaySensor(CoordinatorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "SolXpect Today"
        self._attr_unique_id = "solxpect_today"

    @property
    def state(self):
        data = self.coordinator.data
        if not data:
            return 0
        return round(sum(data["today"].values()), 3)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "hours": data["today"]
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()


class SolxpectTomorrowSensor(CoordinatorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "SolXpect Tomorrow"
        self._attr_unique_id = "solxpect_tomorrow"

    @property
    def state(self):
        data = self.coordinator.data
        if not data:
            return 0
        return round(sum(data["tomorrow"].values()), 3)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "hours": data["tomorrow"]
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()
