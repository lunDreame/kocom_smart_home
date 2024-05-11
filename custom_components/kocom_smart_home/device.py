"""Device class."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import LOGGER
from .coordinator import KocomCoordinator

class KocomEntity(CoordinatorEntity[KocomCoordinator]):
    """Defines a base Kocom entity."""
    
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Kocom device."""
        return self.coordinator.get_device_info()
    