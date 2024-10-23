import re
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import LOGGER, REQUEST_TIMEOUT
from .utils import generate_digest_header, generate_fcm_token


def parse_device_info(data: dict, key: str) -> bool | str | None:
    """Parse device gas/vent info from data"""
    try:
        if key == "attr":
            return {
                "type": data.get("type"),
                "reg_date": data.get("entry", [{}])[0].get("reg_date"),
                "id": data.get("entry", [{}])[0].get("id")
            }
        
        entry_list = data.get("entry", [{}])[0].get("list", [])
        for entry in entry_list:
            if entry.get("function") == key:
                if key == "power":
                    return bool(int(entry.get("value", 0)))
                else:
                    return entry.get("value")
                
        return None
    except Exception as ex:
        LOGGER.error("Failed to parse device info - Key: %s, Error: %s", key, str(ex))
        return None


class KocomSmartHomeAPI:
    """KOCOM Samrt Home API client"""

    """API endpoints"""
    API_SERVER_URL = "http://kbranch.kocom.co.kr"
    API_TYPE_URL = "http://{}/api/{}"

    """Authentication constants"""
    ANDROID_MEMBERSHIP = "4990e9e16a532aa9010403b01e0ee52a"
    DIGEST_IKOD = "Android!1000001"

    def __init__(self) -> None:
        """Initialize API client"""
        self.entry = None
        self.session = aiohttp.ClientSession()
        self.kbranch_tokens: dict[str, str] = {}
        self.apartment_tokens: dict[str, str] = {}
        self.user_credentials: dict[str, Any] = {}
        self.device_settings: dict[str, Any] = {
            "light": {},
            "concent": {},
            "heat": {},  
            "aircon": {}
        }

    async def initialize_devices(self, entry: ConfigEntry):
        """Initialize devices and credentials"""
        self.entry = entry
        self.user_credentials = self.entry.data.get("pairing_data", {})
        #self.session = aiohttp.ClientSession()
        
        if not any(self.device_settings.values()):
            await asyncio.gather(
                self.update_device_state("light"),
                self.update_device_state("concent"),
                self.update_device_state("heat"),
                self.update_device_state("aircon")
            )

    async def close(self):
        """Close API session"""
        if self.session:
            await self.session.close()

    def set_user_credentials(self, data: dict):
        """Set user auth credentials"""
        try:
            if len(data.keys()) == 3:
                self.user_credentials["password"] = data["pwd"]
                self.user_credentials["user_id"] = f"00000{str(data['zone'])}00{str(data['id'])}"
            else:
                pairing_info = data["list"][0]
                pairing_zone, pairing_id = pairing_info["zone"], pairing_info["id"]

                self.user_credentials["pairing_info"] = pairing_info
                self.user_credentials["zone_id"] = f"00{pairing_zone}0{pairing_id}"
        except Exception as ex:
            LOGGER.error(f"Failed to set user credentials: {ex}")

    async def update_device_state(self, device: str) -> dict[str, Any]:
        """Update device state data"""
        status = await self.check_device_status(device)
        self.device_settings[device].update({
            "data": self.extract_meaningful_data(status),
            "sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self.device_settings[device]

    async def fetch_kbranch_token(self):
        """Get Kbranch auth token"""
        try: 
            async with self.session.get(f"{self.API_SERVER_URL}/api/sphone") as response:
                session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get("Set-Cookie"))
                nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get("WWW-Authenticate"))

                if session_id and nonce_id:
                    self.kbranch_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
                else:
                    raise ValueError("Failed to extract Kbranch session or nonce.")
        except Exception as ex:
            LOGGER.error("Failed to fetch Kbranch authentication token: %s", str(ex))
    
    async def fetch_apartment_server_token(self):
        """Get apartment server auth token"""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]
        url = self.API_TYPE_URL.format(server_ip, zone_id)

        try: 
            async with self.session.get(url) as response:
                session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get("Set-Cookie"))
                nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get("WWW-Authenticate"))

                if session_id and nonce_id:
                    self.apartment_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
                else:
                    raise ValueError("Failed to extract apartment server session or nonce.")
        except Exception as ex:
            LOGGER.error("Failed to fetch apartment server authentication token: %s", str(ex))

    async def fetch_energy_stdcheck(self, path: str = "/energy/stdcheck/") -> dict:
        """Get energy usage data"""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]
        year_month = datetime.now().strftime("%Y%m")
        url = self.API_TYPE_URL.format(server_ip, zone_id)

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials['zone_id']}{path}{year_month}",
                self.apartment_tokens["nonce"]
            ),
            "Cookie": self.apartment_tokens["cookie"],
        }

        try: 
            async with self.session.get(url+path+year_month, headers=headers) as response:
                json_data = await response.json(content_type="text/html")
                LOGGER.debug("Energy usage data fetched: %s", json_data)
                return json_data
        except Exception as ex:
            LOGGER.error("Failed to fetch energy usage data: %s", str(ex))

    async def request_sphone_login(self, phone_number: str) -> bool:
        """Login with phone number"""
        url = f"{self.API_SERVER_URL}/api/sphone"

        if not self.kbranch_tokens:
            await self.fetch_kbranch_token()
            LOGGER.debug("Kbranch tokens initialized: %s", self.kbranch_tokens)

        headers = {
            "Authorization": generate_digest_header(
                self.DIGEST_IKOD,
                self.ANDROID_MEMBERSHIP,
                "/api/sphone",
                self.kbranch_tokens["nonce"]
            ),
            "User-Agent": "SmartHome/1.0.1 (com.kocom.SmartHome2; build:46; iOS 18.1.0) Alamofire/5.6.2",
            "Cookie": self.kbranch_tokens["cookie"],
        }
        data = {
            "phonenum": phone_number,
            "type": self.DIGEST_IKOD,
            "token": generate_fcm_token()
        }

        try: 
            async with self.session.get(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT) as response:
                json_data = await response.json(content_type="text/html")
                self.set_user_credentials(json_data)
                LOGGER.debug("Sphone login successful: %s", json_data)
                return await self.request_pairlist_login()    
        except Exception as ex:
            LOGGER.error("Sphone login failed: %s", str(ex))
            return False
    
    async def request_pairlist_login(self) -> dict | bool:
        """Get paired device list"""
        url = f"{self.API_SERVER_URL}/api/{self.user_credentials['user_id']}/pairlist"

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials['user_id']}/pairlist",
                self.kbranch_tokens["nonce"]
            ),
            "User-Agent": "SmartHome/1.0.1 (com.kocom.SmartHome2; build:46; iOS 18.1.0) Alamofire/5.6.2",
            "Cookie": self.kbranch_tokens["cookie"],
        }

        try: 
            async with self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as response:
                json_data = await response.json(content_type="text/html")
                LOGGER.debug("Pairlist login response: %s", json_data)
                
                if len(json_data.get("list", [])) == 1:        
                    self.set_user_credentials(json_data)    
                    LOGGER.info("Device pairing found: %s", self.user_credentials["pairing_info"])
                    return self.user_credentials
                else:
                    LOGGER.info("No paired devices found")
                    return {}
                    
        except Exception as ex:
            LOGGER.error("Failed to fetch pair list: %s", str(ex))
            return False

    async def request_pairnum_login(self, wallpad_number: str) -> dict | bool:
        """Login with wallpad number"""
        url = f"http://kbranch.kocom.co.kr/api/{self.user_credentials['user_id']}/pairnum"

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials['user_id']}/pairnum",
                self.kbranch_tokens["nonce"]
            ),
            "User-Agent": "SmartHome/1.0.1 (com.kocom.SmartHome2; build:46; iOS 18.1.0) Alamofire/5.6.2",
            "Cookie": self.kbranch_tokens["cookie"],
        }
        data = {
            "pairnum": wallpad_number
        }

        try: 
            async with self.session.get(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT) as response:
                json_data = await response.json(content_type="text/html")
                LOGGER.debug("Pairnum login successful: %s", json_data)
                return json_data
        except Exception as ex:
            LOGGER.error("Pairnum login failed: %s", str(ex))
            return False
        
    def current_device_state(self, device: str, id: str, function: str) -> bool | int:
        """Get current device state"""
        try:            
            device_data = self.device_settings.get(device, {}).get("data", {}).get("entry", [])
            for device_entry in device_data:
                if device_entry.get("id") == id:
                    for entry_list in device_entry.get("list", []):
                        if entry_list.get("function") == function:
                            return int(entry_list.get("value", 0))
        except Exception as ex:
            LOGGER.error("Failed to get %s state - ID: %s, Function: %s, Error: %s", device, id, function, str(ex))
            return 0  

    async def check_device_status(self, device: str, path: str = "/control/allstatus") -> dict:
        """Check device status"""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]
        url = self.API_TYPE_URL.format(server_ip, zone_id)

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials['zone_id']}{path}",
                self.apartment_tokens["nonce"]
            ),
            "User-Agent": "SmartHome/1.0.1 (com.kocom.SmartHome2; build:46; iOS 18.1.0) Alamofire/5.6.2",
            "Cookie": self.apartment_tokens["cookie"],
        }
        data = {
            "type": device,
            "cmd": "status"
        }

        try:
            async with self.session.get(url+path, headers=headers, json=data, timeout=REQUEST_TIMEOUT) as response:
                json_data = await response.json(content_type="text/html")
                LOGGER.debug("%s status fetched: %s", device, json_data)
                return json_data
        except Exception as ex:
            LOGGER.error("Failed to fetch %s status: %s", device, str(ex))

    async def send_control_request(self, type: str, id: str, function: str, value: str, path: str = "/control") -> dict:
        """Send device control command"""
        LOGGER.info(
            "Sending device control - Type: %s, ID: %s, Function: %s, Value: %s",
            type, id, function, value
        )
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]
        url = self.API_TYPE_URL.format(server_ip, zone_id)

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"], 
                f"/api/{self.user_credentials['zone_id']}{path}",
                self.apartment_tokens["nonce"]
            ),
            "User-Agent": "SmartHome/1.0.1 (com.kocom.SmartHome2; build:46; iOS 18.1.0) Alamofire/5.6.2",
            "Cookie": self.apartment_tokens["cookie"],
        }
        data = {
            "cmd": "control",
            "type": type,
            "id": id,
            "function": function,
            "value": value
        }

        try:
            async with self.session.get(url+path, headers=headers, json=data, timeout=REQUEST_TIMEOUT) as response:
                json_data = await response.json(content_type="text/html")
                LOGGER.debug("Control request successful: %s", json_data)
                return json_data
        except Exception as ex:
            LOGGER.error("Control request failed - Type: %s, Error: %s", type, str(ex))

    def extract_meaningful_data(self, response: dict) -> dict:
        """Filter and clean device data"""
        try:
            room_count = self.entry.data.get("room_count")
            switch_count = self.entry.data.get("switch_count")
        
            entry_list = response.get("entry", [])
            response["entry"] = [
                entry for entry in entry_list
                if int(entry.get("id", "")[2:]) <= room_count
            ]
        
            if response.get("type") in ["light", "concent"]:
                for entry in entry_list:
                    entry["list"] = [
                        item for item in entry.get("list", [])
                        if int(item.get("function", "")[3:]) <= switch_count
                    ]
        
            return response
        except Exception as ex:
            LOGGER.error("Failed to filter device data: %s", str(ex))
            return {}

    def update_device_data(self, control_response: dict):
        """Updates device entry list data from control response."""
        try:
            device_type = control_response.get("type")
            entries = control_response.get("entry", [])
            
            if not (device_type and entries):
                LOGGER.error(f"Device {device_type}: Missing required data in control response")
            
            device_entries = self.device_settings.get(device_type, {}).get("data", {}).get("entry", [])
            target_entry = next((e for e in device_entries if e.get("id") == entries[0].get("id")), None)

            if target_entry:
                target_entry["list"] = entries[0].get("list", [])[:len(target_entry.get("list", []))]
                #LOGGER.info(f"Device {device_type}: Successfully updated entry {entries[0].get('id')}")
            else:
                LOGGER.error(f"Device {device_type}: Entry {entries[0].get('id')} not found")
        except Exception as ex:
            LOGGER.error(f"Device {device_type}: Update failed - {str(ex)}")
