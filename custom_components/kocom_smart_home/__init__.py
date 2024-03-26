"""
Custom integration to integrate Kocom Smart Home with Home Assistant.
"""
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS, LOGGER
from .api import KocomHomeAPI

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    entry_data: dict[str] = entry.data
    LOGGER.debug("async_setup_entry. entry_data :: %s", entry_data)
    
    api = KocomHomeAPI(hass)
    await api.set_entry_and_initialize_devices(entry)

    hass.data[DOMAIN][entry.entry_id] = api

    for component in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, component))
        
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Handle removal of an entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    return unload_ok

    
