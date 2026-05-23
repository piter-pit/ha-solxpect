from .coordinator import SolxpectCoordinator

DOMAIN = "solxpect"


# ==========================================================
# SETUP ENTRY
# ==========================================================

async def async_setup_entry(hass, entry):
    """Set up SolXpect config entry."""

    coordinator = SolxpectCoordinator(hass, entry)

    # initial fetch
    await coordinator.async_config_entry_first_refresh()

    # store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # ======================================================
    # IMPORTANT: register update listener safely
    # ======================================================
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


# ==========================================================
# UPDATE LISTENER (FIXED - NO RACE / NO STALE STATE)
# ==========================================================

async def _async_update_listener(hass, entry):
    """
    Called when config entry options are updated.

    FIXES:
    - prevents stale coordinator config
    - avoids partial refresh race conditions
    """

    coordinator = hass.data[DOMAIN].get(entry.entry_id)

    if coordinator is None:
        return

    # ------------------------------------------------------
    # IMPORTANT: update config reference FIRST
    # ------------------------------------------------------
    coordinator.config_entry = entry

    # ------------------------------------------------------
    # CRITICAL FIX: full reload instead of only refresh
    # (prevents alternating old/new results)
    # ------------------------------------------------------
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
