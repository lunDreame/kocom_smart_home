from homeassistant.components.light import LightEntity, ColorMode

from .const import DOMAIN, LOGGER
from .coordinator import KocomSmartHomeCoordinator
from .device import KocomSmartHomeEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomSmartHomeCoordinator("light", api, hass, config_entry),
        KocomSmartHomeCoordinator("totalcontrol", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomSmartHomeLight(coordinator, device)
            for device in devices
        )
    
    if entities_to_add:
        async_add_entities(entities_to_add)


class KocomSmartHomeLight(KocomSmartHomeEntity, LightEntity):
    def __init__(self, coordinator, device) -> None:
        self._device = device
        self._device_id = device["device_id"]
        self._device_name = device["device_name"]
        self._device_type = device["device_type"]
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
    def is_on(self) -> bool:
        """Return true if fan is on."""
        status = self.coordinator.get_device_status(self.unique_id)
        return status

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        return ColorMode.ONOFF
        
    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Return the list of supported color mode."""
        return ColorMode.ONOFF

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
        
    async def async_turn_on(self, **kwargs):
        """Turn on light."""
        await self.coordinator.set_device_command(self.unique_id, 1)
        
    async def async_turn_off(self, **kwargs):
        """Turn off light."""
        await self.coordinator.set_device_command(self.unique_id, 0)
