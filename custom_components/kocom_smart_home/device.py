"""Base entity class for Kocom Smart Home devices."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import LOGGER
from .coordinator import KocomSmartHomeCoordinator

class KocomSmartHomeEntity(CoordinatorEntity[KocomSmartHomeCoordinator]):
    """Base Kocom Smart Home entity class."""
    
    @property
    def device_info(self) -> DeviceInfo:
        """Get device info for this Kocom device."""
        return self.coordinator.get_device_info()
