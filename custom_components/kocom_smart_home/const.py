"""Constants for Kocom Smart Home."""
import logging
from homeassistant.const import Platform
from homeassistant.components.sensor import SensorDeviceClass

LOGGER = logging.getLogger(__name__)

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
VERSION = "1.1.1"

CONF_PHONE_NUMBER = "phone_number"
CONF_WALLPAD_NUMBER = "wallpad_number"

MAX_ROOM_CNT = "max_room_cnt"
MAX_SWITCH_CNT = "max_switch_cnt"

LIGHT_INTERVAL = "light_interval"
CONCENT_INTERVAL = "concent_interval"
HEAT_INTERVAL = "heat_interval"
AIRCON_INTERVAL = "aircon_interval"
GAS_INTERVAL = "gas_interval"
VENT_INTERVAL = "vent_interval"
ENERGY_INTERVAL = "energy_interval"
TOTALCTRL_INTERVAL = "totalcontrol_interval"

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

