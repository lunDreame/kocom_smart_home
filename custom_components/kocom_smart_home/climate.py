from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.components.climate.const import PRESET_NONE, PRESET_AWAY
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode

from .const import DOMAIN, LOGGER
from .coordinator import KocomSmartHomeCoordinator
from .device import KocomSmartHomeEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomSmartHomeCoordinator("heat", api, hass, config_entry),
        KocomSmartHomeCoordinator("aircon", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomSmartHomeClimate(coordinator, device)
            for device in devices
        )
    
    if entities_to_add:
        async_add_entities(entities_to_add)


class KocomSmartHomeClimate(KocomSmartHomeEntity, ClimateEntity):
    
    _enable_turn_on_off_backwards_compatibility = False
    
    def __init__(self, coordinator, device) -> None:
        self._device = device
        self._device_id = device["device_id"]
        self._device_name = device["device_name"]
        self._device_type = device["device_type"]

        self._hvac_modes = [HVACMode.OFF, HVACMode.HEAT] # Default
        self._supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._supported_features |= ClimateEntityFeature.TURN_ON
        self._supported_features |= ClimateEntityFeature.TURN_OFF
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return the entity ID."""
        return self._device_id
    
    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._device_name

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        status = self.coordinator.get_device_status(self.unique_id, "nowtemp")
        return status

    @property
    def target_temperature(self) -> float:
        """Return the target temperature."""
        status = self.coordinator.get_device_status(self.unique_id, "settemp")
        return status

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    @property
    def target_temperature_step(self):
        """Step tempreature."""
        return 1

    @property
    def min_temp(self):
        """Min tempreature."""
        return self._device["min_temp"]

    @property
    def max_temp(self):
        """Max tempreature."""
        return self._device["max_temp"]

    @property
    def hvac_modes(self) -> list:
        """Return the list of available hvac operation modes."""
        if self._device_type == "aircon":
            self._hvac_modes[1] = HVACMode.COOL
        return self._hvac_modes
    
    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        status = self.coordinator.get_device_status(self.unique_id)
        return self._hvac_modes[1] if status else HVACMode.OFF
    
    @property
    def preset_modes(self) -> list:
        """Return the list of available preset modes."""
        if self._device_type == "heat":
            return [PRESET_AWAY, PRESET_NONE]
    
    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires ClimateEntityFeature.PRESET_MODE.
        """
        status = self.coordinator.get_device_status(self.unique_id, "mode")
        return PRESET_AWAY if status else PRESET_NONE

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self._device_type == "heat":
            self._supported_features |= ClimateEntityFeature.PRESET_MODE
        return self._supported_features

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "Unique ID": self._device["device_id"],
            "Device room": self._device["device_room"],
            "Device type": self._device["device_type"],
            "Registration Date": self._device["reg_date"],
            "Sync date": self.coordinator._device_info["sync_date"]
        }
    
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == self._hvac_modes[1]:
            await self.coordinator.set_device_command(self.unique_id, 1)
        elif hvac_mode == HVACMode.OFF:
            await self.coordinator.set_device_command(self.unique_id, 0)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.coordinator.set_device_command(self.unique_id, 1)
            await self.coordinator.set_device_command(self.unique_id, 1, "mode")
        elif preset_mode == PRESET_NONE:
            await self.coordinator.set_device_command(self.unique_id, 0, "mode")

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        await self.coordinator.set_device_command(self.unique_id, 1)
        await self.coordinator.set_device_command(
            self.unique_id, kwargs.get(ATTR_TEMPERATURE, 20), "settemp"
        )
