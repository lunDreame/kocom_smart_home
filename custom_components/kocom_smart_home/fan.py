import logging
from datetime import timedelta
from typing import *
from homeassistant.components.fan import FanEntity
from homeassistant.components.fan import FanEntityFeature
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ranged_value,
)

from .const import (
    DOMAIN,
    VERSION, 
    CONF_PHONE_NUMBER,
    CONF_VENT_INTERVAL,
    PAIR_INFO,
    FAN_ICONS,
    SPEED_LIST
)
from .api import parse_device_info

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=300)

async def async_setup_entry(hass, config_entry, async_add_entities):
    hass_data = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    vent_state = await hass_data.check_device_status('vent')

    if isinstance(vent_state, dict):
        entities.append(KocomFan(vent_state, hass_data))

    async_add_entities(entities)


class KocomFan(FanEntity):
    def __init__(self, state_data, hass_data):
        self._state_data = state_data
        self._hass_data = hass_data
        self._device_type = "환기"
        self._state_attr = parse_device_info(state_data, 'attr')
        self._state_power = parse_device_info(state_data, 'power')
        self._state_wind = parse_device_info(state_data, 'wind')
        self._result = {}

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'switch.ventilation_{self._state_attr['id'].lower()}_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'
    
    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return self._device_type

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        if self._state_power:
            return FAN_ICONS[self._state_wind]
        else:
            return FAN_ICONS['off']

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._state_power

    @property
    def supported_features(self) -> int: 
        """Flag supported features."""
        return FanEntityFeature.SET_SPEED
    
    @property
    def percentage(self):
        """Return the current percentage based speed."""
        return ordered_list_item_to_percentage(SPEED_LIST, self._state_wind)
    
    @property
    def preset_mode(self):
        """Return the preset mode."""
        return self._state_wind 

    @property
    def preset_modes(self) -> list:
        """Return the list of available preset modes."""
        return SPEED_LIST

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(SPEED_LIST)

    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Device type": self._state_attr['id'],
            "Device state": self._state_power,
            "Registration date": self._state_attr['reg_date']
        }
        return attributes
    
    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return
        
        vent_state = await self._hass_data.check_device_status('vent')
        self._state_power = parse_device_info(vent_state, 'power')
        self._state_wind = parse_device_info(vent_state, 'wind')

    async def async_turn_on(self, speed: Optional[str] = None, percentage: Optional[int] = None, preset_mode: Optional[str] = None, **kwargs: Any) -> None:
        """Turn on the fan."""
        self._result = await self._hass_data.send_control_request('vent', self._state_attr['id'], 'power', '1')

        self._state_power = parse_device_info(self._result, 'power') 

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self._result = await self._hass_data.send_control_request('vent', self._state_attr['id'], 'power', '0')

        self._state_power = parse_device_info(self._result, 'power') 

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        return percentage_to_ranged_value((1, len(SPEED_LIST)), percentage)
        
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if not self._state_power:
            self._result = await self._hass_data.send_control_request('vent', self._state_attr['id'], 'power', '1')
            self._state_power = parse_device_info(self._result, 'power')

        self._result = await self._hass_data.send_control_request('vent', self._state_attr['id'], 'wind', preset_mode)
        self._state_wind = parse_device_info(self._result, 'wind')

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'kocom')},
             "name": "KOCOM",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }
