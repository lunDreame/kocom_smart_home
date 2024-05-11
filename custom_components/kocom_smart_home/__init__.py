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
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api: KocomHomeAPI = KocomHomeAPI(hass)
    await api.set_entry_and_initialize_devices(entry)

    hass.data[DOMAIN][entry.entry_id] = api
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    hass.data[DOMAIN].pop(entry.entry_id)

    return True
