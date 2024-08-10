"""
Custom integration to integrate Kocom Smart Home with Home Assistant.
"""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS, LOGGER
from .api import KocomHomeAPI

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Integration setup."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    api = KocomHomeAPI(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = api

    await api.initialize_devices(entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    LOGGER.debug(f"Update Options: {entry.options}")
    await hass.config_entries.async_reload(entry.entry_id)
