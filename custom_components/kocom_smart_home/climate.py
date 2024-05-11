from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.components.climate.const import PRESET_NONE, PRESET_AWAY
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode

from .const import DOMAIN, LOGGER
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
    
    if entities_to_add:
        async_add_entities(entities_to_add)


class KocomClimate(KocomEntity, ClimateEntity):
    def __init__(self, coordinator, device) -> None:
        self._device = device
        self._device_id = device["device_id"]
        self._device_name = device["device_name"]
        self._device_type = device["device_type"]
        self._hvac_mode = [HVACMode.OFF]
        if self._device_type == "heat":
            self._hvac_mode.append(HVACMode.HEAT)
        else:
            self._hvac_mode.append(HVACMode.COOL)
        self._features = (
            ClimateEntityFeature.TARGET_TEMPERATURE|
            ClimateEntityFeature.TURN_ON|
            ClimateEntityFeature.TURN_OFF
        )
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
        status = self.coordinator.get_device_status(self._device_id, "nowtemp")
        return status

    @property
    def target_temperature(self) -> float:
        """Return the target temperature."""
        status = self.coordinator.get_device_status(self._device_id, "settemp")
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
        return self._hvac_mode
    
    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        status = self.coordinator.get_device_status(self._device_id)
        if status:
            return self._hvac_mode[1]
        else:
            return self._hvac_mode[0]
    
    @property
    def preset_modes(self) -> list:
        """Return the list of available preset modes."""
        if self._device_type == "heat":
            return [PRESET_AWAY, PRESET_NONE]
        else:
            return []
    
    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.
        Requires ClimateEntityFeature.PRESET_MODE.
        """
        status = self.coordinator.get_device_status(self._device_id, "mode")
        if status:
            return PRESET_AWAY
        else:
            return PRESET_NONE

    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self._device_type == "heat":
            self._features |= ClimateEntityFeature.PRESET_MODE

        return self._features

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "Device room": self._device["device_room"],
            "Device type": self._device["device_type"],
            "Registration Date": self._device["reg_date"],
            "Sync date": self.coordinator._device_info["sync_date"]
        }
    
    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == self._hvac_mode[1]:
            await self.coordinator.set_device_command(self._device_id, 1)
        elif hvac_mode == self._hvac_mode[0]:
            await self.coordinator.set_device_command(self._device_id, 0)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new target preset mode."""
        if preset_mode == PRESET_AWAY:
            await self.coordinator.set_device_command(self._device_id, 1)
            await self.coordinator.set_device_command(self._device_id, 1, "mode")
        elif preset_mode == PRESET_NONE:
            await self.coordinator.set_device_command(self._device_id, 0, "mode")

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        await self.coordinator.set_device_command(self._device_id, 1)
        await self.coordinator.set_device_command(
            self._device_id, kwargs.get(ATTR_TEMPERATURE, 20), "settemp"
        )
