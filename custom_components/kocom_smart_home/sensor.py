from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN, LOGGER, ENERGY_INFO
from .coordinator import KocomCoordinator
from .device import KocomEntity

ICON = {
    "light": "mdi:lightbulb",
    "concent": "mdi:power-socket-eu",
    "heat": "mdi:thermostat",
    "aircon": "mdi:thermostat",
}

async def async_setup_entry(hass, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities_to_add: list = []

    coordinators = [
        KocomCoordinator("energy", api, hass, config_entry)
    ]

    for coordinator in coordinators:
        devices = await coordinator.get_devices()
        entities_to_add.extend(
            KocomSensor(coordinator, device) for device in devices
        )

    async_add_entities(entities_to_add)

class KocomSensor(KocomEntity, SensorEntity):
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
    def icon(self):
        """Return the icon of the sensor."""
        return ENERGY_INFO[self.device["device_room"]][1]

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this sensor."""
        if self.device["device_type"] == "price":
            return "KRW/kWh"
        return ENERGY_INFO[self.device["device_room"]][2]

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return ENERGY_INFO[self.device["device_room"]][3]
    
    @property
    def state_class(self):
        """Type of this sensor state."""
        _state_class = ENERGY_INFO[self.device["device_room"]][4]    
        if _state_class is not None and self.device["is_prev_month"]:
            return _state_class.split("_")[0]
        return _state_class
        
    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator._energy_usage_state(
            self.device_id, self.device["reg_date"]
        )
    
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        return {
            "Device room": self.device["device_room"],
            "Device type": self.device["device_type"],
            "Registration Date": self.device["reg_date"],
            "Sync date": self.coordinator._data["sync_date"]
        }

