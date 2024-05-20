"""Constants for Kocom Smart Home."""
import logging
from homeassistant.const import Platform

LOGGER = logging.getLogger(__name__)

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
VERSION = "1.1.4"

TIMEOUT_SEC = 10

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
]
