import re
from datetime import datetime
from datetime import timedelta

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, VERSION, LOGGER
from .api import parse_device_info

ENERGY_INFO = {
    "elec": ["전기 사용량", "mdi:flash", "kWh", SensorDeviceClass.ENERGY, "total_increasing"],
    "heat": ["난방 사용량", "mdi:radiator", "m³", None, None],
    "hotwater": ["온수 사용량", "mdi:hot-tub", "m³", None, None],
    "gas": ["가스 사용량", "mdi:fire", "m³", SensorDeviceClass.GAS, "total_increasing"],
    "water": ["수도 사용량", "mdi:water-pump", "m³", SensorDeviceClass.WATER, "total_increasing"]
}

ENERGY_UNIT = {
    "value": "우리집",
    "avg": "이번달 평균",
    "price": "예상 요금",
    "_previousvalue": "전월 우리집",
    "_previousavg": "전월 평균",
    "_previousprice": "전월 예상 요금",   
}

class KocomCoordinator(DataUpdateCoordinator):
    """Kocom update coordinator."""
    irdev = False

    def __init__(self, name, api, hass, entry) -> None:
        self.name = name
        self.api = api
        self.hass = hass
        self.n_interval = f"{name}_interval"
        
        update_interval = entry.data[self.n_interval]
        if name in ["light", "concent", "heat", "aircon"]:
            self.irdev = True
            self._data = api.device_settings[name]
        else:
            self._data = {"data": {}, "sync_date": ""}
        super().__init__(
            hass, LOGGER, name=name, update_interval=timedelta(seconds=update_interval)
        )
    
    async def get_energy_usage(self) -> dict:
        energy_usage = await self.api.fetch_energy_stdcheck()
        self._data.update({
            "data": energy_usage,
            "sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self._data

    async def get_single_device(self, control_response: dict = None) -> dict:
        if control_response is None:
            device_state = await self.api.check_device_status(self.name)
        else:
            if control_response["type"] == "totalcontrol":
                control_response["entry"][0]["list"][0]["value"] = ~(int(control_response["entry"][0]["list"][0]["value"]))
            device_state = control_response

        self._data["data"].update({
            "attr": parse_device_info(device_state, "attr"),
            "power": parse_device_info(
                device_state, "totallight" if self.name == "totalcontrol" else "power"
            ),
        })
        if self.name == "vent":
            self._data["data"].update({"wind": parse_device_info(device_state, "wind")})

        self._update_sync_date()
        return self._data
    
    def _energy_usage_state(self, unique_id: str, target_date: str) -> dict:
        pattern = r"(elec|gas|water|hotwater|heat).*?(value|avg|price)"
        match = re.search(pattern, unique_id)
        if match:
            energy_type, data_type = match.group(1), match.group(2)
            for data_entry in self._data["data"]["list"]:
                if data_entry["energy"] == energy_type and data_entry["date"] == target_date:
                    return data_entry[data_type]
        else:
            LOGGER.warning("Unable to update energy usage information.")
    
    def _is_device_state(self, unique_id: str, function: str = "power") -> bool:
        if self.irdev:
            id_parts = unique_id.split("_")
            id = id_parts[0].title()
            if id_parts[1] == "00":
                id_parts[1] = function
            return self.api.is_device_state(self.name, id, id_parts[1])
        return self._data["data"]["power"]
        
    def _interpret_command(
        self, unique_id: str, command_name: str, command_value: int
    ) -> tuple:
        id_parts = unique_id.split("_")
        id = id_parts[0].title()

        if unique_id.startswith(("vent", "gas", "totalcontrol")):
            if unique_id.startswith("totalcontrol"):
                command_name = "totallight"
        elif unique_id.startswith(("lt", "ct")):
            command_value *= 255
            command_name = id_parts[1]

        if command_name != "power":
            command_name = command_name

        return id, command_name, command_value

    def _is_previous_month(self, date_str: str) -> bool:
        try:
            previous_month = int(date_str.split()[0].replace("-", "")) // 100
            current_year_month = int(datetime.now().strftime("%Y%m"))
            return current_year_month > previous_month
        except Exception:
            return False
        
    def _update_sync_date(self):
        self._data.update({"sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    async def _async_update_data(self):
        n_interval = self.config_entry.options.get(self.n_interval)

        if n_interval is not None:
            self.update_interval = timedelta(seconds=n_interval)
            LOGGER.info("Changing update %s to %s", self.n_interval, n_interval)

        if self.name in ["gas", "vent", "totalcontrol"]:
            return await self.update_single_device()
        elif self.name == "energy":
            return await self.update_energy_usage()
        else:
            return await self.update_room_device()
    
    async def set_device_command(
        self, unique_id: str, kwargs**
    ) -> None:
        id, name, value = self._interpret_command(unique_id, name, value for name, value in kwargs.items())

        control_response = await self.api.send_control_request(
            self.name, id, name, value
        )
        if self.irdev:
            self.api.update_device_data(control_response)
        else:
            await self.get_single_device(control_response)
        
    async def specify_elements(self) -> list:
        energy_usage = await self.get_energy_usage()
        devices = []

        for usage_data in energy_usage["data"]["list"]:
            is_prev_month = self._is_previous_month(usage_data["date"])
            prev_suffix = "_previous" if is_prev_month else ""
            for key, value in usage_data.items():
                if key in ["energy", "date"]:
                    continue
                if key == "price":
                    device_id = f"{usage_data["energy"]}{prev_suffix}_expect_price"
                    device_name = f"{ENERGY_INFO[usage_data["energy"]][0]} {ENERGY_UNIT[prev_suffix+"price"]}"
                else:
                    device_id = f"{usage_data["energy"]}{prev_suffix}_{key}_usage"
                    device_name = f"{ENERGY_UNIT[prev_suffix+key]} {ENERGY_INFO[usage_data["energy"]][0]}"

                entry_data = {
                    "device_id": device_id,
                    "device_name": device_name,
                    "device_room": usage_data["energy"],
                    "device_type": key,
                    "is_prev_month": is_prev_month,
                    "reg_date": usage_data["date"]
                }       
                devices.append(entry_data)

        return devices         

    async def get_devices(self) -> list:
        devices = []
        if self.name == "energy":
            devices = await self.specify_elements()
        elif self.name in ["gas", "vent", "totalcontrol"]:
            single_device = await self.get_single_device()
            entry_data = {
                "device_id": f"{self.name}_{single_device["data"]["attr"]["id"].lower()}",
                "device_name": {"gas": "가스", "vent": "환기", "totalcontrol": "일괄소등"}[self.name],
                "device_room": "00",
                "device_type": single_device["data"]["attr"]["type"],
                "reg_date": single_device["data"]["attr"]["reg_date"]
            }
            devices.append(entry_data)
        else:
            for entry in self._data["data"]["entry"]:
                for entry_list in entry["list"]:
                    if self._data["data"]["type"] in ["heat", "aircon"]:
                        entry_data = {
                            "device_id": f"{entry["id"].lower()}_00",
                            "device_name": f"{entry["id"]} 00",
                            "device_room": "00",
                            "device_type": self._data["data"]["type"],
                            "reg_date": entry["reg_date"],
                        }
                        temperature_range = {
                            "heat": {"min_temp": 5, "max_temp": 40},
                            "aircon": {"min_temp": 18, "max_temp": 30},
                        }
                        entry_data.update(temperature_range[self._data["data"]["type"]])
                    else:
                        entry_data = {
                            "device_id": f"{entry["id"].lower()}_{entry_list["function"]}",
                            "device_name": f"{entry["id"]} {entry_list["function"]}",
                            "device_room": entry["id"][-2:],
                            "device_type": self._data["data"]["type"],
                            "reg_date": entry["reg_date"],
                        }
                    devices.append(entry_data)
        
        LOGGER.debug("Get devices: %s", devices)
        return devices         

    async def update_single_device(self) -> dict:
        return await self.get_single_device()
    
    async def update_energy_usage(self) -> dict:
        return await self.get_energy_usage()
        
    async def update_room_device(self) -> dict:
        return await self.api.update_device_state(self.name)

    def get_device_info(self) -> DeviceInfo:
        is_specific_name = self.name in ["gas", "vent", "totalcontrol", "room"]
        return DeviceInfo(
            identifiers={(DOMAIN, "kocom" if is_specific_name else self.name)},
            name="KOCOM" if is_specific_name else f"KOCOM {self.name.title()}",
            manufacturer="Kocom Co, Ltd.",
            model=self.api.user_credentials["pairing_info"]["alias"],
            sw_version=VERSION,
        )
    
