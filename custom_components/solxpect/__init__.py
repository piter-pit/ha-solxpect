from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, DEFAULT_NAME, LEGACY_TITLE
from .coordinator import SolxpectCoordinator

# sensor keys, used in the per-entry unique IDs ("<entry_id>_today")
SENSOR_KEYS = ("today", "tomorrow")


# ==========================================================
# SETUP ENTRY
# ==========================================================

async def async_setup_entry(hass, entry):
    """Set up SolXpect config entry."""

    await _async_migrate_unique_ids(hass, entry)

    coordinator = SolxpectCoordinator(hass, entry)

    # initial fetch
    await coordinator.async_config_entry_first_refresh()

    # store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # reload the entry whenever its options change
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


# ==========================================================
# UNIQUE ID MIGRATION (single plant -> multiple plants)
# ==========================================================

async def _async_migrate_unique_ids(hass, entry):
    """
    Older versions used the fixed unique IDs "solxpect_today" and
    "solxpect_tomorrow", so only one plant could exist. Rewrite them to
    "<entry_id>_today" / "<entry_id>_tomorrow".

    Only the unique ID changes; the entity keeps its entity ID
    (e.g. sensor.solxpect_today), history, dashboards and automations.
    """

    migrated = False

    @callback
    def _migrate(entity_entry):
        nonlocal migrated
        for key in SENSOR_KEYS:
            if entity_entry.unique_id == f"solxpect_{key}":
                migrated = True
                return {"new_unique_id": f"{entry.entry_id}_{key}"}
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)

    # Old entries all got the fixed title "SolXpect PV Forecast". The
    # sensor names are now "<title> Today", so switch that fixed title to
    # the default name to keep the familiar "SolXpect Today" names.
    if migrated and entry.title == LEGACY_TITLE:
        hass.config_entries.async_update_entry(entry, title=DEFAULT_NAME)


# ==========================================================
# UPDATE LISTENER
# ==========================================================

async def _async_update_listener(hass, entry):
    """Called when config entry options are updated: reload once."""

    await hass.config_entries.async_reload(entry.entry_id)


# ==========================================================
# UNLOAD ENTRY
# ==========================================================

async def async_unload_entry(hass, entry):
    """Unload config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor"]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
