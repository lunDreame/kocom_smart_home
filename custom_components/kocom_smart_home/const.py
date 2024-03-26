"""Constants for Kocom Smart Home."""
import logging
from homeassistant.const import Platform
from homeassistant.components.sensor import SensorDeviceClass

LOGGER = logging.getLogger(__name__)

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
VERSION = "1.1.0"

TIMEOUT_SEC = 10

BIT_OFF = 0
BIT_ON = 1

ENERGY_INFO = {
    "elec": ["전기 사용량", "mdi:flash", "kWh", SensorDeviceClass.ENERGY, "total_increasing"],
    "heat": ["난방 사용량", "mdi:radiator", "㎥", None, None],
    "hotwater": ["온수 사용량", "mdi:hot-tub", "㎥", None, None],
    "gas": ["가스 사용량", "mdi:fire", "㎥", SensorDeviceClass.GAS, "total_increasing"],
    "water": ["수도 사용량", "mdi:water-pump", "㎥", SensorDeviceClass.WATER, "total_increasing"]
}

ENERGY_UNIT = {
    "value": "우리집",
    "avg": "이번달 평균",
    "price": "예상 요금",
    "_previousvalue": "전월 우리집",
    "_previousavg": "전월 평균",
    "_previousprice": "전월 예상 요금",   
}

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
]

