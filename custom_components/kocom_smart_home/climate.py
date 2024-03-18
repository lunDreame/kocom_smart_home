import logging
from datetime import timedelta
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_NONE
)
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_TEMPERATURE
)

from .const import (
    DOMAIN,
    VERSION, 
    CONF_PHONE_NUMBER,
    PAIR_INFO,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=300)

async def async_setup_entry(hass, config_entry, async_add_entities):
    hass_data = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    thermostat_data = hass_data.device_data.get('thermostat')

    for device_type in thermostat_data['entry']:
        entities.append(KocomHeating(device_type, hass_data))

    aircon_data = hass_data.device_data.get('aircon')

    for device_type in aircon_data['entry']:
        entities.append(KocomAircon(device_type, hass_data)) 

    async_add_entities(entities)


class KocomHeating(ClimateEntity):
    def __init__(self, device_type, hass_data) -> None:
        self._device_type = device_type
        self._hass_data = hass_data
        self._device_id = "00"
        self._result = {}
        self._features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | 
            ClimateEntityFeature.PRESET_MODE
        )

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'climate.{self._device_type['id'].lower()}_{self._device_id}_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{self._device_type['id']} {self._device_id}'

    @property
    def current_temperature(self):
        return self._hass_data.is_device_state('thermostat', self._device_type['id'], 'nowtemp')

    @property
    def target_temperature(self):
        return self._hass_data.is_device_state('thermostat', self._device_type['id'], 'settemp')
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 5

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 40

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVACMode.OFF, HVACMode.HEAT]
    
    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        return HVACMode.HEAT if self._hass_data.is_device_state('thermostat', self._device_type['id'], 'power') else HVACMode.OFF
    
    @property
    def preset_modes(self):
        return [PRESET_AWAY, PRESET_NONE]
    
    @property
    def preset_mode(self):
        return PRESET_AWAY if self._hass_data.is_device_state('thermostat', self._device_type['id'], 'mode') else PRESET_NONE

    @property
    def supported_features(self):
        return self._features

    @property
    def extra_state_attributes(self):
        attributes = {
            "Device room": self._device_type['id'],
            "Device type": self._device_id,
        }
        return attributes
    
    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return

        await self._hass_data.device_state('thermostat')
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'power', '1')

        elif hvac_mode == HVACMode.OFF:
            self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'power', '0')

        self._hass_data.update_device_data(self._result)

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode == PRESET_AWAY:
            self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'power', '1')

            self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'mode', '1')
        elif preset_mode == PRESET_NONE:
            self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'mode', '0')

        self._hass_data.update_device_data(self._result)    

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._result = await self._hass_data.send_control_request('heat', self._device_type['id'], 'power', '1')

        self._result = await self._hass_data.send_control_request(
            'heat', self._device_type['id'], 'settemp', kwargs.get(ATTR_TEMPERATURE, 20)
        )

        self._hass_data.update_device_data(self._result)    

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'thermostat')},
            "name": "KOCOM Thermostat",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }



class KocomAircon(ClimateEntity):
    def __init__(self, device_type, hass_data) -> None:
        self._device_type = device_type
        self._hass_data = hass_data
        self._device_id = "00"
        self._result = {}
        self._features = (ClimateEntityFeature.TARGET_TEMPERATURE)

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'climate.{self._device_type['id'].lower()}_{self._device_id}_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{self._device_type['id']} {self._device_id}'
    
    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:air-conditioner"

    @property
    def current_temperature(self):
        return self._hass_data.is_device_state('aircon', self._device_type['id'], 'nowtemp')

    @property
    def target_temperature(self):
        return self._hass_data.is_device_state('aircon', self._device_type['id'], 'settemp')
    
    @property
    def temperature_unit(self):
        """Return the unit of measurement which this thermostat uses."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 18

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 30

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVACMode.OFF, HVACMode.COOL]
    
    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        return HVACMode.COOL if self._hass_data.is_device_state('aircon', self._device_type['id'], 'power') else HVACMode.OFF

    @property
    def supported_features(self):
        return self._features

    @property
    def extra_state_attributes(self):
        attributes = {
            "Device room": self._device_type['id'],
            "Device type": self._device_id,
        }
        return attributes
    
    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return
        
        await self._hass_data.device_state('aircon')
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.COOL:
            self._result = await self._hass_data.send_control_request('aircon', self._device_type['id'], 'power', '1')

        elif hvac_mode == HVACMode.OFF:
            self._result = await self._hass_data.send_control_request('aircon', self._device_type['id'], 'power', '0')

        self._hass_data.update_device_data(self._result)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        self._result = await self._hass_data.send_control_request('aircon', self._device_type['id'], 'power', '1')

        self._result = await self._hass_data.send_control_request(
            'aircon', self._device_type['id'], 'settemp', kwargs.get(ATTR_TEMPERATURE, 20)
        )

        self._hass_data.update_device_data(self._result)    

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'aircon')},
            "name": "KOCOM Aircon",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }


