from typing import Any, Optional

from homeassistant.components.fan import FanEntity
from homeassistant.components.fan import FanEntityFeature
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN, LOGGER
from .coordinator import KocomSmartHomeCoordinator
from .device import KocomSmartHomeEntity

SPEED_LOW = "1"
SPEED_MID = "2" 
SPEED_HIGH = "3" 
SPEED_LIST = [SPEED_LOW, SPEED_MID, SPEED_HIGH]


async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = KocomSmartHomeCoordinator("vent", api, hass, config_entry)
    devices = await coordinator.get_devices()

    entities_to_add: list = [
        KocomSmartHomeFan(coordinator, device)
        for device in devices
    ]
    
    if entities_to_add:
        async_add_entities(entities_to_add)


class KocomSmartHomeFan(KocomSmartHomeEntity, FanEntity): 
    def __init__(self, coordinator, device) -> None:
        self._device = device
        self._device_id = device["device_id"]
        self._device_name = device["device_name"]

        self._supported_features = FanEntityFeature.SET_SPEED
        self._supported_features |= FanEntityFeature.TURN_ON
        self._supported_features |= FanEntityFeature.TURN_OFF
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
        status = self.coordinator.get_device_status()
        return status

    @property
    def supported_features(self) -> int: 
        """Flag supported features."""
        return self._supported_features
    
    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        status = self.coordinator.get_device_status(function="wind")
        if status == "0":
            return 0
        return ordered_list_item_to_percentage(SPEED_LIST, status)
    
    @property
    def preset_mode(self):
        """Return the preset mode."""
        status = self.coordinator.get_device_status(function="wind")
        return status

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
        """Return the state attributes of the sensor."""
        return {
            "Unique ID": self._device["device_id"],
            "Device room": self._device["device_room"],
            "Device type": self._device["device_type"],
            "Registration Date": self._device["reg_date"],
            "Sync date": self.coordinator._device_info["sync_date"]
        }

    async def async_turn_on(
        self,
        speed: Optional[str] = None,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on fan."""
        await self.coordinator.set_device_command(self.unique_id, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off fan."""
        await self.coordinator.set_device_command(self.unique_id, 0)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.coordinator.set_device_command(self.unique_id, 0)
        else:
            await self.coordinator.set_device_command(
                self.unique_id, 
                percentage_to_ordered_list_item(SPEED_LIST, percentage),
                "wind"
            )
        
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
