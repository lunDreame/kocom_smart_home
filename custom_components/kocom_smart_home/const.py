"""Constants for Kocom Smart Home."""
from homeassistant.const import Platform
from homeassistant.components.sensor import SensorDeviceClass

NAME = "Kocom Smart Home"
DOMAIN = "kocom_smart_home"
VERSION = "1.0.3"
PLATFORMS = [
    Platform.FAN,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.CLIMATE,
]

CONF_PHONE_NUMBER  = "phone_number"
CONF_WALLPAD_NUMBER = "wallpad_number"
CONF_ROOM_INTERVAL = "room_interval"
CONF_GAS_INTERVAL = "gas_interval"
CONF_VENT_INTERVAL = "vent_interval"
CONF_ENERGY_INTERVAL = "energy_interval"

TIMEOUT_SEC = 30

SPHONE_INFO = "sphone_info"
SPHONE_UUID = "sphone_uuid"
PAIR_INFO = "pair_info"
ZONE_ID = "zone_id"

SPEED_LOW = "1"
SPEED_MID = "2" 
SPEED_HIGH = "3" 
SPEED_LIST = [SPEED_LOW, SPEED_MID, SPEED_HIGH]

FAN_ICONS = {
    "off": "mdi:fan-off",
    "1": "mdi:fan-speed-1",
    "2": "mdi:fan-speed-2",
    "3": "mdi:fan-speed-3"
}

ROOM_ICONS = {
    "light": "mdi:lightbulb",
    "outlet": "mdi:power-socket-eu",
    "thermostat": "mdi:thermostat",
    "aircon": "mdi:air-conditioner"
}

ENERGY_NAME = {
    "elec": ["전기 사용량", "mdi:flash", "kWh", SensorDeviceClass.ENERGY, "total_increasing"],
    "heat": ["난방 사용량", "mdi:radiator", "㎥", None, None],
    "hotwater": ["온수 사용량", "mdi:hot-tub", "㎥", None, None],
    "gas": ["가스 사용량", "mdi:fire", "㎥", SensorDeviceClass.GAS, "total_increasing"],
    "water": ["수도 사용량", "mdi:water-pump", "㎥", SensorDeviceClass.WATER, "total_increasing"]
}

ENERGY_UNIT_NAME = {
    "value": "우리집",
    "avg": "이번달 평균",
    "price": "예상 요금",
    "_previousvalue": "전월 우리집",
    "_previousavg": "전월 평균",
    "_previousprice": "전월 예상 요금",   
}


