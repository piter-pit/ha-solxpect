from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SolxpectTodaySensor(coordinator),
        SolxpectTomorrowSensor(coordinator),
    ])


class SolxpectTodaySensor(CoordinatorEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        entry = coordinator.config_entry
        # per-entry name and unique ID, so several plants can coexist
        self._attr_name = f"{entry.title} Today"
        self._attr_unique_id = f"{entry.entry_id}_today"
        self._attr_device_class = "energy"
        self._attr_state_class = "total"
        self._attr_native_unit_of_measurement = "kWh"
        

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
        entry = coordinator.config_entry
        # per-entry name and unique ID, so several plants can coexist
        self._attr_name = f"{entry.title} Tomorrow"
        self._attr_unique_id = f"{entry.entry_id}_tomorrow"
        self._attr_device_class = "energy"
        self._attr_state_class = "total"
        self._attr_native_unit_of_measurement = "kWh"

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
