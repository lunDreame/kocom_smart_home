"""Constants for Kocom Smart Home."""
import logging
from homeassistant.const import Platform
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfVolume

LOGGER = logging.getLogger(__name__)

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
#VERSION = "1.1.5"

TIMEOUT_SEC = 10

PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
]

DEFAULT_TEMP_RANGE = {
    "heat": {
        "min_temp": 5,
        "max_temp": 40
    },
    "aircon": {
        "min_temp": 18,
        "max_temp": 30
    }
}

ELEMENT_INFO = {
    "elec": [
        "전기 사용량",
        "mdi:flash",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        "total_increasing"
    ],
    "heat": [
        "난방 사용량",
        "mdi:radiator",
        UnitOfVolume.CUBIC_METERS,
        None,
        None
    ],
    "hotwater": [
        "온수 사용량",
        "mdi:hot-tub",
        UnitOfVolume.CUBIC_METERS,
        None,
        None
    ],
    "gas": [
        "가스 사용량",
        "mdi:fire",
        UnitOfVolume.CUBIC_METERS,
        SensorDeviceClass.GAS,
        "total_increasing"
    ],
    "water": [
        "수도 사용량",
        "mdi:water-pump",
        UnitOfVolume.CUBIC_METERS,
        SensorDeviceClass.WATER,
        "total_increasing"
    ]
} 

ELEMENT_UNITNAME = {
    "value": "우리집",
    "avg": "이번달 평균",
    "price": "예상 요금",
    "_previousvalue": "전월 우리집",
    "_previousavg": "전월 평균",
    "_previousprice": "전월 예상 요금",   
}