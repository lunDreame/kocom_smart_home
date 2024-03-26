from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.components.climate.const import PRESET_NONE, PRESET_AWAY
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode

from .const import DOMAIN, LOGGER, BIT_OFF, BIT_ON
from .coordinator import KocomCoordinator
from .device import KocomEntity

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomCoordinator("heat", api, hass, config_entry),
        KocomCoordinator("aircon", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomClimate(coordinator, device) for device in devices
        )

    async_add_entities(entities_to_add)

class KocomClimate(KocomEntity, ClimateEntity):
    def __init__(self, coordinator, device) -> None:
        self.device = device
        self.device_id = device.get('device_id')
        self.device_name = device.get('device_name')
        if self.device['device_type'] == "heat":
            self.mode = HVACMode.HEAT 
        else:
            self.mode = HVACMode.COOL
        self.features = (ClimateEntityFeature.TARGET_TEMPERATURE)
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return the entity ID."""
        return self.device_id
    
    @property
    def name(self) -> str:
        """Return the name of the sensor, if any."""
        return self.device_name

    @property
    def current_temperature(self):
        return self.coordinator._is_device_state(self.device_id, "nowtemp")

    @property
    def target_temperature(self):
        return self.coordinator._is_device_state(self.device_id, "settemp")
    
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
        return self.device["min_temp"]

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self.device["max_temp"]

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.
        Need to be a subset of HVAC_MODES.
        """
        return [HVACMode.OFF, self.mode]
    
    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode.
        Need to be one of HVAC_MODE_*.
        """
        if self.coordinator._is_device_state(self.device_id):
            return self.mode
        return HVACMode.OFF
    
    @property
    def preset_modes(self):
        if self.device['device_type'] == "heat":
            return [PRESET_AWAY, PRESET_NONE]
        return None
    
    @property
    def preset_mode(self):
        if self.coordinator._is_device_state(self.device_id, "mode"):
            return PRESET_AWAY
        return PRESET_NONE

    @property
    def supported_features(self):
        if self.device['device_type'] == "heat":
            self.features |= ClimateEntityFeature.PRESET_MODE
        return self.features

    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Device room": self.device['device_room'],
            "Device type": self.device['device_type'],
            "Registration Date": self.device['reg_date'],
            "Sync date": self.coordinator._data['sync_date']
        }
        return attributes
    
    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == self.mode:
            await self.coordinator.set_device_command(self.device_id, BIT_ON)
        elif hvac_mode == HVACMode.OFF:
            await self.coordinator.set_device_command(self.device_id, BIT_OFF)

        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set new target preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.coordinator.set_device_command(self.device_id, BIT_ON)

            await self.coordinator.set_device_command(self.device_id, BIT_ON, "mode")
        elif preset_mode == PRESET_NONE:
            await self.coordinator.set_device_command(self.device_id, BIT_OFF, "mode")

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        await self.coordinator.set_device_command(self.device_id, BIT_ON)
        await self.coordinator.set_device_command(
            self.device_id, kwargs.get(ATTR_TEMPERATURE, 20), "settemp"
        )

        await self.coordinator.async_request_refresh()

        
