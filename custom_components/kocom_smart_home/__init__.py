"""
Custom integration to integrate Kocom Smart Home with Home Assistant.
"""
import logging
import asyncio
from typing import *

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    PLATFORMS,
)
from .api import KocomHomeManager

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    entry_data: dict[str] = entry.data
    _LOGGER.debug("async_setup_entry. entry_data :: %s", entry_data)
    
    manager = KocomHomeManager(hass)
    await manager.set_entry(entry)

    hass.data[DOMAIN][entry.entry_id] = manager

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
