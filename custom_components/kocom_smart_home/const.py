"""Constants for Kocom Smart Home."""
import logging
from homeassistant.const import Platform
from homeassistant.components.sensor import SensorDeviceClass

LOGGER = logging.getLogger(__name__)

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
VERSION = "1.2.0-bata"

TIMEOUT_SEC = 10

BIT_OFF = 0
BIT_ON = 1

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
]

