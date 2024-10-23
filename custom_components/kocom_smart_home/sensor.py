from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, LOGGER
from .coordinator import KocomSmartHomeCoordinator
from .device import KocomSmartHomeEntity


async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomSmartHomeCoordinator("energy", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomSmartHomeSensor(coordinator, device)
            for device in devices
        )
    
    if entities_to_add:
        async_add_entities(entities_to_add)


class KocomSmartHomeSensor(KocomSmartHomeEntity, SensorEntity):
    def __init__(self, coordinator, device) -> None:
        self._device = device
        self._device_id = device["device_id"]
        self._device_name = device["device_name"]
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
    def icon(self):
        """Return the icon of the sensor."""
        return self._device["device_icon"]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this sensor."""
        return self._device["device_unit"]

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return self._device["device_class"]
    
    @property
    def state_class(self):
        """Type of this sensor state."""
        state_class = self._device["state_class"]
        if state_class and self._device["is_prev_month"]:
            return state_class.split("_")[0]
        else:
            return state_class
        
    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator._energy_usage_state(
            self.unique_id, self._device["reg_date"]
        )

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
