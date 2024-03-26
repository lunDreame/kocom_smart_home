from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN, LOGGER, BIT_OFF, BIT_ON
from .coordinator import KocomCoordinator
from .device import KocomEntity

ICON = {
    "gas": "mdi:gas-cylinder",
    "concent": "mdi:power-socket-eu"
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomCoordinator("gas", api, hass, config_entry),
        KocomCoordinator("concent", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomSwitch(coordinator, device) for device in devices
        )

    async_add_entities(entities_to_add)

class KocomSwitch(KocomEntity, SwitchEntity):
    def __init__(self, coordinator, device) -> None:
        self.device = device
        self.device_id = device.get('device_id')
        self.device_name = device.get('device_name')
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
    def icon(self) -> str | None:
        """Icon to use in the frontend, if any."""
        return ICON[self.device['device_type']]

    @property
    def is_on(self) -> bool:
        """If the switch is currently on or off."""
        return self.coordinator._is_device_state(self.device_id)

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
    
    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.coordinator.set_device_command(self.device_id, BIT_ON)
        await self.coordinator.async_request_refresh()
        
    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.coordinator.set_device_command(self.device_id, BIT_OFF)
        await self.coordinator.async_request_refresh()

