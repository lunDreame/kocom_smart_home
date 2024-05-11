import re
from datetime import datetime
from datetime import timedelta

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, VERSION, LOGGER
from .api import parse_device_info


class KocomCoordinator(DataUpdateCoordinator):
    """Kocom update coordinator."""
    _irdev = False

    def __init__(self, name, api, hass, entry) -> None:
        self.name = name
        self.api = api
        self.hass = hass
        self.name_interval = f"{name}_interval"
        
        update_interval = entry.data[self.name_interval]
        if name in ["light", "concent", "heat", "aircon"]:
            self._irdev = True
            self._device_info = api.device_settings[name]
        else:
            self._device_info = {"data": {}, "sync_date": ""}
        super().__init__(
            hass, LOGGER, name=name, update_interval=timedelta(seconds=update_interval)
        )
    
    async def get_energy_usage(self) -> dict:
        energy_usage = await self.api.fetch_energy_stdcheck()
        self._device_info.update({
            "data": energy_usage,
            "sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self._device_info

    async def get_single_device(self, control_response: dict = None) -> dict:
        if control_response:
            device_state = control_response
        else:
            device_state = await self.api.check_device_status(self.name)
        
        if device_state["type"] == "totalcontrol" and device_state["entry"]:         
            # 0: totallight / 1: totalelevator
            entry_to_list = device_state["entry"][0]["list"][0]
            entry_to_list["value"] = ~int(entry_to_list["value"]) & 1

        power_key = "totallight" if self.name == "totalcontrol" else "power"
        data_updates = {
            "attr": parse_device_info(device_state, "attr"),
            "power": parse_device_info(device_state, power_key),
        }

        if self.name == "vent":
            data_updates["wind"] = parse_device_info(device_state, "wind")

        self._device_info["data"].update(data_updates)
        self._update_sync_date()

        return self._device_info
    
    def _energy_usage_state(self, unique_id: str, target_date: str) -> dict:
        pattern = r"(elec|gas|water|hotwater|heat).*?(value|avg|price)"
        match = re.search(pattern, unique_id)
        if match:
            energy_type, data_type = match.group(1), match.group(2)
            for data_entry in self._device_info["data"]["list"]:
                if data_entry["energy"] == energy_type and data_entry["date"] == target_date:
                    return data_entry[data_type]
        else:
            LOGGER.warning("Unable to update energy usage information.")
    
    def get_device_status(self, unique_id: str, function: str = "power") -> bool:
        if self._irdev and unique_id:
            id_parts = unique_id.split("_")
            id = id_parts[0].title()
            if id_parts[1] == "00":
                id_parts[1] = function
            return self.api.is_device_state(self.name, id, id_parts[1])
        else:
            return self._device_info.get("data", {}).get(function)
        
    def _interpret_command(self, unique_id: str, value: int, function: str) -> tuple:
        id_parts = unique_id.split("_")
        id = id_parts[0].title()

        if unique_id.startswith(("vent", "gas", "totalcontrol")):
            if unique_id.startswith("totalcontrol"):
                value = ~value & 1 
                function = "totallight"
        elif unique_id.startswith(("lt", "ct")):
            value *= 255
            function = id_parts[1]

        if function != "power":
            function = function

        return id, function, value

    def _is_previous_month(self, date_str: str) -> bool:
        try:
            previous_month = int(date_str.split()[0].replace("-", "")) // 100
            current_year_month = int(datetime.now().strftime("%Y%m"))
            return current_year_month > previous_month
        except Exception:
            return False
        
    def _update_sync_date(self):
        self._device_info.update({"sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    async def _async_update_data(self):
        update_interval = self.config_entry.options.get(self.name_interval)
        if update_interval:
            self.update_interval = timedelta(seconds=update_interval)
        
        if self.name in ["gas", "vent", "totalcontrol"]:
            return await self.update_single_device()
        elif self.name == "energy":
            return await self.update_energy_usage()
        else:
            return await self.update_room_device()
    
    async def set_device_command(self, unique_id: str, value: int, function: str = "power") -> None:
        id, function, value = self._interpret_command(unique_id, value, function)
        control_response = await self.api.send_control_request(self.name, id, function, value)

        if self._irdev:
            self.api.update_device_data(control_response)
        else:
            await self.get_single_device(control_response)
        
        await self.async_request_refresh()

    async def specify_elements(self) -> list:
        energy_usage = await self.get_energy_usage()
        devices = []

        energy_element_info = {
            "elec": ["전기 사용량", "mdi:flash", "kWh", SensorDeviceClass.ENERGY, "total_increasing"],
            "heat": ["난방 사용량", "mdi:radiator", "m³", None, None],
            "hotwater": ["온수 사용량", "mdi:hot-tub", "m³", None, None],
            "gas": ["가스 사용량", "mdi:fire", "m³", SensorDeviceClass.GAS, "total_increasing"],
            "water": ["수도 사용량", "mdi:water-pump", "m³", SensorDeviceClass.WATER, "total_increasing"]
        } 
        energy_unit_name = {
            "value": "우리집",
            "avg": "이번달 평균",
            "price": "예상 요금",
            "_previousvalue": "전월 우리집",
            "_previousavg": "전월 평균",
            "_previousprice": "전월 예상 요금",   
        }

        for usage_device_info in energy_usage["data"]["list"]:
            is_prev_month = self._is_previous_month(usage_device_info["date"])
            prev_suffix = "_previous" if is_prev_month else ""
            energy_type = usage_device_info["energy"]
            for key, value in usage_device_info.items():
                if key in ["energy", "date"]:
                    continue
                entry_device_info = {
                    "device_id": f"{energy_type}{prev_suffix}_{key}_usage" 
                    if key != "price" else f"{energy_type}{prev_suffix}_expect_price",
                    "device_name": f"{energy_unit_name[f"{prev_suffix}{key}"]} {energy_element_info[energy_type][0]}" 
                    if key != "price" else f"{energy_element_info[energy_type][0]} {energy_unit_name[f"{prev_suffix}price"]}",
                    "device_icon": energy_element_info[energy_type][1],
                    "device_unit": energy_element_info[energy_type][2] if key != "price" else "KRW/kWh",
                    "device_class": energy_element_info[energy_type][3],
                    "state_class": energy_element_info[energy_type][4],
                    "device_room": usage_device_info["energy"],
                    "device_type": key,
                    "is_prev_month": is_prev_month,
                    "reg_date": usage_device_info["date"]
                }       
                devices.append(entry_device_info)

        LOGGER.debug("Get specify elements: %s", devices)
        return devices

    async def get_devices(self) -> list:
        devices = []
        if self.name == "energy":
            devices = await self.specify_elements()
        elif self.name in ["gas", "vent", "totalcontrol"]:
            single_device = await self.get_single_device()
            entry_device_info = {
                "device_id": f"{self.name}_{single_device["data"]["attr"]["id"].lower()}",
                "device_name": {"gas": "가스", "vent": "환기", "totalcontrol": "일괄소등"}[self.name],
                "device_room": "00",
                "device_type": single_device["data"]["attr"]["type"],
                "reg_date": single_device["data"]["attr"]["reg_date"]
            }
            devices.append(entry_device_info)
        else:
            for entry in self._device_info["data"]["entry"]:
                for entry_list in entry["list"]:
                    device_id = entry.get("id", "").lower()
                    function = entry_list.get("function", "")
                    device_name = f"{entry.get("id", "")} {function}" if function else f"{entry.get("id", "")} 00"
                    device_room = entry.get("id", "")[-2:] if function else "00"
                    device_type = self._device_info["data"]["type"]
                    reg_date = entry.get("reg_date", "")

                    if device_type in ["heat", "aircon"]:
                        temperature_range = {"heat": {"min_temp": 5, "max_temp": 40}, "aircon": {"min_temp": 18, "max_temp": 30}}
                        devices.append({
                            "device_id": f"{device_id}_00",
                            "device_name": device_name,
                            "device_room": device_room,
                            "device_type": device_type,
                            "reg_date": reg_date,
                            **temperature_range.get(device_type, {})
                        })
                    else:
                        devices.append({
                            "device_id": f"{device_id}_{function}",
                            "device_name": device_name,
                            "device_room": device_room,
                            "device_type": device_type,
                            "reg_date": reg_date
                        })
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
    