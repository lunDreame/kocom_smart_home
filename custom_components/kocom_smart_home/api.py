import re
import asyncio
import datetime
from typing import Any
from datetime import datetime

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import LOGGER, TIMEOUT_SEC, MAX_ROOM_CNT, MAX_SWITCH_CNT
from .utils import generate_digest_header, generate_fcm_token


def parse_device_info(data: dict, key: str) -> bool | str | None:
    """Parse gas and vent device information."""
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
    except Exception:
        return None


class KocomHomeAPI:
    """KOCOM API"""

    """Base API URL"""
    API_SERVER_URL = "http://kbranch.kocom.co.kr"
    API_TYPE_URL = "http://{}/api/{}"

    """Net State Until"""
    ANDROID_MEMBERSHIP = "4990e9e16a532aa9010403b01e0ee52a"
    DIGEST_IKOD = "Android!1000001"

    def __init__(self, hass) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = None
        self.kbranch_tokens: dict[str, str] = {}
        self.apartment_tokens: dict[str, str] = {}
        self.user_credentials: dict[str, Any] = {}
        self.device_settings: dict[str, Any] = {
            "light": {},
            "concent": {},
            "heat": {},  
            "aircon": {}
        }

    async def set_entry_and_initialize_devices(self, entry):
        """Set entry data and initialize device states if necessary."""
        self.entry = entry
        self.user_credentials = self.entry.data.get("pairing_data", {})
        if all(not value for value in self.device_settings.values()):
            await asyncio.gather(
                self.update_device_state("light"),
                self.update_device_state("concent"),
                self.update_device_state("heat"),
                self.update_device_state("aircon")
            )

    def set_user_credentials(self, data: dict):
        if len(data.keys()) == 3:
            self.user_credentials["password"] = data["pwd"]
            self.user_credentials["user_id"] = f"00000{str(data["zone"])}00{str(data["id"])}"
        else:
            pairing_info = data["list"][0] 
            pairing_zone, pairing_id = pairing_info["zone"], pairing_info["id"]

            self.user_credentials["pairing_info"] = pairing_info
            self.user_credentials["zone_id"] = f"00{pairing_zone}0{pairing_id}"

    async def update_device_state(self, device: str) -> dict[str, Any]:
        """Check and update the state of a device."""
        status = await self.check_device_status(device)
        self.device_settings[device].update({
            "data": self.extract_meaningful_data(status),
            "sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self.device_settings[device]

    async def fetch_kbranch_token(self):
        """Gets the authentication token of the kbranch kocom server."""
        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(f"{self.API_SERVER_URL}/api/sphone")

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get("Set-Cookie", ""))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get("WWW-Authenticate", ""))
            self.kbranch_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception as ex:
            LOGGER.error("Request failed to get FCM authentication token from Kocom server, %s", ex)
    
    async def fetch_apartment_server_token(self):
        """Gets the authentication token of the apartment server."""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]

        url = self.API_TYPE_URL.format(server_ip, zone_id)

        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(url)

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get("Set-Cookie", ""))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get("WWW-Authenticate", ""))
            self.apartment_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception as ex:
            LOGGER.error("Request failed while retrieving authentication token for apartment server, %s", ex)

    async def fetch_energy_stdcheck(self, path: str = "/energy/stdcheck/") -> dict:
        """Obtain energy usage information from the apartment server."""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]

        now = datetime.now()
        year_month = now.strftime("%Y-%m").replace("-", "")

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials["zone_id"]}{path}{year_month}",
                self.apartment_tokens["nonce"]
            ),
            "Cookie": self.apartment_tokens["cookie"],
        }
        try: 
            response = await session.get(url+path+year_month, headers=headers)
            json_data = await response.json(content_type="text/html")
            LOGGER.debug("Fetch energy stdcheck: %s", json_data)
            
            return json_data
        except Exception:
            LOGGER.error("Request failed while retrieving energy usage from apartment complex server")

    async def request_sphone_login(self, phone_number: str) -> bool:
        """First sphone login for wallpad authentication"""
        url = f"{self.API_SERVER_URL}/api/sphone"
        session = async_get_clientsession(self.hass)

        if not self.kbranch_tokens:
            await self.fetch_kbranch_token()
            LOGGER.debug("Request sphone login  KBRANCH_TOKENS: %s", self.kbranch_tokens)

        headers = {
            "Authorization": generate_digest_header(
                self.DIGEST_IKOD,
                self.ANDROID_MEMBERSHIP,
                "/api/sphone",
                self.kbranch_tokens["nonce"]
            ),
            "Cookie": self.kbranch_tokens["cookie"],
        }
        data = {
            "phonenum": phone_number,
            "type": self.DIGEST_IKOD,
            "token": generate_fcm_token(phone_number)
        }

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type="text/html")

            self.set_user_credentials(json_data)
            LOGGER.debug("Request sphone login: %s", json_data)

            return await self.request_pairlist_login()    
        except Exception:
            LOGGER.error("Request failed while attempting a login request to the Kocom server, Path: '/api/sphone'")
            return False
    
    async def request_pairlist_login(self) -> dict | bool:
        """Finds the paired device based on the phone number."""
        url = f"{self.API_SERVER_URL}/api/{self.user_credentials["user_id"]}/pairlist"
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials["user_id"]}/pairlist",
                self.kbranch_tokens["nonce"]
            ),
            "Cookie": self.kbranch_tokens["cookie"],
        }

        try: 
            response = await session.get(url, headers=headers, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type="text/html")
            LOGGER.debug("Request pairlist login: %s", json_data)
            
            if len(json_data.get("list", 0)) == 1:        
                self.set_user_credentials(json_data)    
                LOGGER.info("Pairing Information Found: %s", self.user_credentials["pairing_info"])
                return self.user_credentials
            else:
                LOGGER.info("Pairing information not found.")
                return {}
                
        except Exception:
            LOGGER.error(
                "Request failed while attempting a login request to the Kocom server, Path: '/api/%s/pairlist'", 
                {self.user_credentials["user_id"]}
            )            
            return False

    async def request_pairnum_login(self, wallpad_number: str) -> dict | bool:
        """If there is no paired device, try pairing through authentication number"""
        url = f"http://kbranch.kocom.co.kr/api/{self.user_credentials["user_id"]}/pairnum"
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials["user_id"]}/pairnum",
                self.kbranch_tokens["nonce"]
            ),
            "Cookie": self.kbranch_tokens["cookie"],
        }
        data = {
            "pairnum": wallpad_number
        }

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type="text/html")
            LOGGER.debug("Request pairnum login: %s", json_data)

            return json_data
        except Exception:
            LOGGER.error(
                "Request failed while attempting a login request to the Kocom server, Path: '/api/%s/pairnum'", 
                {self.user_credentials["user_id"]}
            )            
            return False
        
    def is_device_state(self, device: str, id: str, function: str) -> bool | int:
        """Derive status information from the list of lights, outlets, thermostats, and air conditioners."""
        try:            
            device_data = self.device_settings.get(device, {}).get("data", {}).get("entry", [])
            for device_entry in device_data:
                if device_entry.get("id") == id:
                    for entry_list in device_entry.get("list", []):
                        if entry_list.get("function") == function:
                            return int(entry_list.get("value", 0))
        except Exception as ex:
            LOGGER.error("There was a problem in deriving the value of the '%s' list. %s", device, ex)
            return 0  

    async def check_device_status(self, device: str, path: str = "/control/allstatus") -> dict:
        """Check the status of the device"s entire item"""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"],
                f"/api/{self.user_credentials["zone_id"]}{path}",
                self.apartment_tokens["nonce"]
            ),
            "Cookie": self.apartment_tokens["cookie"],
        }
        data = {
            "type": device,
            "cmd": "status"
        }

        try:
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type="text/html")
            LOGGER.debug("Check device status: %s", json_data)
            
            return json_data
        except Exception:
            LOGGER.error("Device '%s' status request to apartment server failed, Path: '/control/allstatus'", device)

    async def send_control_request(self, type: str, id: str, function: str, value: str, path: str = "/control") -> dict:
        """Device Control Request"""
        server_ip = self.user_credentials["pairing_info"]["svrip"]
        zone_id = self.user_credentials["zone_id"]

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)                                     

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": generate_digest_header(
                self.user_credentials["user_id"],
                self.user_credentials["password"], 
                f"/api/{self.user_credentials["zone_id"]}{path}",
                self.apartment_tokens["nonce"]
            ),
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
            LOGGER.info(
                "Prepare a device command request to the apartment server. %s, %s, %s, %s",
                type, id, function, value
            )
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)

            json_data = await response.json(content_type="text/html")
            LOGGER.debug("send_control_request  %s", json_data)

            return json_data
        except Exception:
            LOGGER.error("Device '%s' command request to apartment server failed, Path: '/control'", type)

    def extract_meaningful_data(self, response: dict) -> dict:
        """Remove meaningless data from lights/concents"""
        try:
            max_room_cnt = self.entry.data.get(MAX_ROOM_CNT)
            max_switch_cnt = self.entry.data.get(MAX_SWITCH_CNT)
        
            entry_list = response.get("entry", [])
            response["entry"] = [entry for entry in entry_list if int(entry.get("id", "")[2:]) <= max_room_cnt]
        
            if response.get("type") in ["light", "concent"]:
                for entry in entry_list:
                    entry["list"] = [item for item in entry.get("list", []) if int(item.get("function", "")[3:]) <= max_switch_cnt]
        
            return response
        except Exception as ex:
            LOGGER.error("There was an error parsing the status type or there was a problem removing the element. %s", ex)
            return {}

    def update_device_data(self, control_response: dict):
        """Update device data"""
        try:
            device_type = control_response.get("type")
            entry_list = control_response.get("entry", [])
        
            if device_type and entry_list:
                device_settings = self.device_settings.get(device_type, {})
                device_data_to_modify = device_settings.get("data", {})
                device_entries = device_data_to_modify.get("entry", [])
            
                for device_entry in device_entries:
                    entry_id = device_entry.get("id")
                    if entry_id == entry_list[0].get("id"):
                        device_entry["list"] = entry_list[0].get("list", [])[:len(device_entry.get("list", []))]
                        LOGGER.info("%s device data update successful.", device_type.title())
                        break
        except Exception as ex:
            LOGGER.error("Failed to update the device settings: %s", ex)

