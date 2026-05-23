from .coordinator import SolxpectCoordinator

DOMAIN = "solxpect"


# ==========================================================
# SETUP ENTRY
# ==========================================================

async def async_setup_entry(hass, entry):
    coordinator = SolxpectCoordinator(hass, entry)

    # initial fetch
    await coordinator.async_config_entry_first_refresh()

    # store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # forward platforms (sensors etc.)
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # 🔥 IMPORTANT: react to options changes
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


# ==========================================================
# UPDATE LISTENER (CRITICAL MISSING PIECE)
# ==========================================================

async def _async_update_listener(hass, entry):
    """Called when config entry is updated (OptionsFlow)."""

    coordinator = hass.data[DOMAIN][entry.entry_id]

    # refresh config reference inside coordinator
    coordinator.config_entry = entry

    # force refresh data after option change
    await coordinator.async_request_refresh()


# ==========================================================
# UNLOAD ENTRY
# ==========================================================

async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor"]
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
