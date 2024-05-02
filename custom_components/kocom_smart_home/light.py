from homeassistant.components.light import LightEntity, ColorMode

from .const import DOMAIN, LOGGER, BIT_OFF, BIT_ON
from .coordinator import KocomCoordinator
from .device import KocomEntity

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomCoordinator("light", api, hass, config_entry),
        KocomCoordinator("totalcontrol", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomLight(coordinator, device) for device in devices
        )

    async_add_entities(entities_to_add)

class KocomLight(KocomEntity, LightEntity):
    def __init__(self, coordinator, device) -> None:
        self.device = device
        self.device_id = device.get("device_id")
        self.device_name = device.get("device_name")
        super().__init__(coordinator)

    @property
    def unique_id(self) -> str:
        """Return the entity ID."""
        return self.device_id
    
    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.device_name
    
    @property
    def is_on(self) -> bool:
        """Return true if fan is on."""
        return self.coordinator._is_device_state(self.device_id)

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
            "Device room": self.device["device_room"],
            "Device type": self.device["device_type"],
            "Registration Date": self.device["reg_date"],
            "Sync date": self.coordinator._data["sync_date"]
        }
        
    async def async_turn_on(self, **kwargs):
        """Turn on light."""
        await self.coordinator.set_device_command(self.device_id, power=BIT_ON)
        await self.coordinator.async_request_refresh()
        
    async def async_turn_off(self, **kwargs):
        """Turn off light."""
        await self.coordinator.set_device_command(self.device_id, power=BIT_OFF)
        await self.coordinator.async_request_refresh()

