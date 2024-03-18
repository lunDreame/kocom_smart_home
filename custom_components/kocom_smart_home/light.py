import logging
from datetime import timedelta
from homeassistant.components.light import (
    LightEntity,
    LightEntityFeature,
)

from .const import (
    DOMAIN,
    VERSION, 
    CONF_PHONE_NUMBER,
    PAIR_INFO
)
from .api import parse_device_info

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=120)

async def async_setup_entry(hass, config_entry, async_add_entities):
    hass_data = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    light_data = hass_data.device_data.get('light')

    for device in light_data['entry']:
        for id in device['list']:
            entities.append(KocomLight(device, id, hass_data))

    totalcontrol_state = await hass_data.check_device_status('totalcontrol')

    if isinstance(totalcontrol_state, dict):
        entities.append(KocomBatchLight(totalcontrol_state, hass_data))

    async_add_entities(entities)


class KocomLight(LightEntity):
    def __init__(self, device_type, device_id, hass_data) -> None:
        self._device_type = device_type
        self._device_id = device_id
        self._hass_data = hass_data
        self._result = {}
        self._features = 0

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'light.{self._device_type['id'].lower()}_{self._device_id['function'].lower()}_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{self._device_type['id']} {self._device_id['function']}'

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._hass_data.is_device_state('light', self._device_type['id'], self._device_id['function'])

    @property
    def supported_features(self):
        return LightEntityFeature(self._features)

    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Device room": self._device_type['id'],
            "Device type": self._device_id['function'],
            "Device state": self._hass_data.is_device_state(
                'light', self._device_type['id'], self._device_id['function']
            ),
        }
        return attributes
    
    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return
        
        await self._hass_data.device_state('light')

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._result = await self._hass_data.send_control_request('light', self._device_type['id'], self._device_id['function'], '255')

        self._hass_data.update_device_data(self._result)

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._result = await self._hass_data.send_control_request('light', self._device_type['id'], self._device_id['function'], '0')

        self._hass_data.update_device_data(self._result)

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'light')},
            "name": "KOCOM Light",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }
    


class KocomBatchLight(LightEntity):
    def __init__(self, state_data, hass_data) -> None:
        self._state_data = state_data
        self._hass_data = hass_data
        self._device_type = "일괄소등"
        self._state_attr = parse_device_info(state_data, 'attr')
        self._state_power = parse_device_info(state_data, 'totallight')
        self._result = {}
        self._features = 0

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'light.cutoff_switch_{self._state_attr['id'].lower()}_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return self._device_type

    @property
    def is_on(self):
        """If the switch is currently on or off."""
        return self._state_power
    
    @property
    def supported_features(self):
        return LightEntityFeature(self._features)

    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Device type": self._state_attr['id'],
            "Device state": self._state_power,
            "Registration date": self._state_attr['reg_date']
        }
        return attributes
    
    def update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        self._result = await self._hass_data.send_control_request('totalcontrol', self._state_attr['id'], 'totallight', '1')
        
        self._state_power = parse_device_info(self._result, 'totallight')

    async def aync_turn_off(self, **kwargs):
        """Turn the switch off."""
        self._result = await self._hass_data.send_control_request('totalcontrol', self._state_attr['id'], 'totallight', '0')
        
        self._state_power = parse_device_info(self._result, 'totallight')

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
