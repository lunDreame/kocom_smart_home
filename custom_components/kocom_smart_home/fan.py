from typing import Any, Optional

from homeassistant.components.fan import FanEntity
from homeassistant.components.fan import FanEntityFeature
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ranged_value,
)

from .const import DOMAIN, LOGGER, BIT_OFF, BIT_ON
from .coordinator import KocomCoordinator
from .device import KocomEntity

SPEED_LOW = "1"
SPEED_MID = "2" 
SPEED_HIGH = "3" 
SPEED_LIST = [SPEED_LOW, SPEED_MID, SPEED_HIGH]

ICON = {
    "off": "mdi:fan-off",
    "1": "mdi:fan-speed-1",
    "2": "mdi:fan-speed-2",
    "3": "mdi:fan-speed-3",
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = KocomCoordinator("vent", api, hass, config_entry)
    devices = await coordinator.get_devices()

    entities_to_add: list = [
        KocomFan(coordinator, devices[0])
    ]

    async_add_entities(entities_to_add)
    
class KocomFan(KocomEntity, FanEntity): 
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
    def icon(self) -> str:
        """Icon to use in the frontend, if any."""
        if self.coordinator._data['data']['power']:
            return ICON.get(self.coordinator._data['data']['wind'])
        return ICON['off']

    @property
    def is_on(self) -> bool:
        """If the switch is currently on or off."""
        return self.coordinator._data['data']['power']

    @property
    def supported_features(self) -> int: 
        """Flag supported features."""
        return FanEntityFeature.SET_SPEED
    
    @property
    def percentage(self):
        """Return the current percentage based speed."""
        return ordered_list_item_to_percentage(
            SPEED_LIST, self.coordinator._data['data']['wind']
        )
    
    @property
    def preset_mode(self):
        """Return the preset mode."""
        return self.coordinator._data['data']['wind']

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
            "Device room": self.device['device_room'],
            "Device type": self.device['device_type'],
            "Registration Date": self.device['reg_date'],
            "Sync date": self.coordinator._data['sync_date']
        }
        return attributes

    async def async_turn_on(
        self, 
        speed: Optional[str] = None, 
        percentage: Optional[int] = None, 
        preset_mode: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """Turn on the fan."""
        await self.coordinator.set_device_command(self.device_id, BIT_ON)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self.coordinator.set_device_command(self.device_id, BIT_OFF)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        return percentage_to_ranged_value((1, len(SPEED_LIST)), percentage)
        
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if not self.coordinator._data['data']['power']:
            await self.coordinator.set_device_command(self.device_id, BIT_ON)

        await self.coordinator.set_device_command(self.device_id, preset_mode, "wind")
        await self.coordinator.async_request_refresh()
