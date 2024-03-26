import re
import asyncio
import datetime
from typing import Union, Callable
from datetime import datetime

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import LOGGER, TIMEOUT_SEC
from .utils import generate_digest_header, generate_fcm_token

def parse_device_info(data: dict, key: str) -> Union[str, dict, bool]:
    """Parse gas and vent device information."""
    try:
        if key == "attr":
            return {
                "type": data['type'],
                "reg_date": data['entry'][0]['reg_date'],
                "id": data['entry'][0]['id']
            }
        entry_list = data['entry'][0]['list']
        for entry in entry_list:
            if entry['function'] == key:
                if key == "power":
                    return bool(int(entry['value']))
                else:
                    return entry['value']
        return None
    except KeyError as e:
        LOGGER.error("KeyError while parsing %s: %s", key, e)
    except Exception as e:
        LOGGER.error("An error occurred while parsing %s: %s", key, e)

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
        self.login_data: dict[str] = {}
        self.device_data: dict[str] = {
            "light": {},
            "concent": {},
            "heat": {},  
            "aircon": {}
        }        

    async def set_entry_and_initialize_devices(self, entry) -> None:
        """Set entry data and initialize device states if necessary."""
        self.entry = entry
        self.login_data = self.entry.data.get('pair_info', {})
        if all(not value for value in self.device_data.values()):
            await asyncio.gather(
                self.update_device_state("light"),
                self.update_device_state("concent"),
                self.update_device_state("heat"),
                self.update_device_state("aircon")
            )

    async def update_device_state(self, device: str) -> None:
        """Check and update the state of a device."""
        status = await self.check_device_status(device)
        self.device_data[device].update({
            "data": self.extract_meaningful_data(status),
            "sync_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return self.device_data[device]

    async def fetch_kbranch_token(self) -> None:
        """Gets the authentication token of the kbranch kocom server."""
        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(f'{self.API_SERVER_URL}/api/sphone')

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get('Set-Cookie', ''))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get('WWW-Authenticate', ''))
            self.kbranch_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception as ex:
            LOGGER.error("Request failed to get FCM authentication token from Kocom server, Ex: %s", ex)
    
    async def fetch_apartment_server_token(self) -> None:
        """Gets the authentication token of the apartment server."""
        server_ip = self.login_data['pair_info']['svrip']
        zone_id = self.login_data['zone_id']

        url = self.API_TYPE_URL.format(server_ip, zone_id)

        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(url)

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get('Set-Cookie', ''))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get('WWW-Authenticate', ''))
            self.apartment_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception as ex:
            LOGGER.error("Request failed while retrieving authentication token for apartment server, Ex: %s", ex)

    async def fetch_energy_stdcheck(self, path: str = "/energy/stdcheck/") -> dict:
        server_ip = self.login_data['pair_info']['svrip']
        zone_id = self.login_data['zone_id']

        now = datetime.now()
        year_month = now.strftime("%Y-%m").replace('-', '')

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": generate_digest_header(
                self.login_data['sphone_uuid'], self.login_data['sphone_info']['pwd'],
                f'/api/{self.login_data['zone_id']}{path}{year_month}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        try: 
            response = await session.get(url+path+year_month, headers=headers)
            json_data = await response.json(content_type='text/html')
            LOGGER.debug("fetch_energy_stdcheck - response :: %s", json_data)
            
            return json_data
        except Exception:
            LOGGER.error("Request failed while retrieving energy usage from apartment complex server")

    async def request_sphone_login(self, phone_number: str = None) -> Union[bool, Callable]:
        """First sphone login for wallpad authentication"""
        url = f'{self.API_SERVER_URL}/api/sphone'
        session = async_get_clientsession(self.hass)

        if not self.kbranch_tokens:
            await self.fetch_kbranch_token()
            LOGGER.debug("request_sphone_login - kbranch_tokens :: %s", self.kbranch_tokens)

        headers = {
            "Authorization": generate_digest_header(
                self.DIGEST_IKOD, self.ANDROID_MEMBERSHIP, "/api/sphone", self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }
        data = {"phonenum": phone_number, "type": self.DIGEST_IKOD, "token": generate_fcm_token(phone_number)}

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            self.login_data['sphone_info'] = json_data
            self.login_data['sphone_uuid'] = f'00000{str(json_data['zone'])}00{str(json_data['id'])}'

            LOGGER.debug("request_sphone_login - response :: %s", json_data)

            return await self.request_pairlist_login()    
        except Exception:
            LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/sphone'")
            return False
    
    async def request_pairlist_login(self) -> Union[dict, bool]:
        """Finds the paired device based on the phone number."""
        url = f'{self.API_SERVER_URL}/api/{self.login_data['sphone_uuid']}/pairlist'
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": generate_digest_header(
                self.login_data['sphone_uuid'], self.login_data['sphone_info']['pwd'],
                f'/api/{self.login_data['sphone_uuid']}/pairlist', self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }

        try: 
            response = await session.get(url, headers=headers, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            LOGGER.debug("request_pairlist_login - response :: %s", json_data)
            
            if len(json_data.get('list', 0)) == 1:            
                self.login_data['pair_info'] = json_data['list'][0] # For index-locked multiple registrations, still implemented X

                zone, id = json_data['list'][0]['zone'], json_data['list'][0]['id']
                self.login_data['zone_id'] = f'00{str(zone)}0{str(id)}'

                return self.login_data
            else:
                LOGGER.info("Pairing information not found.")
                return {}
                
        except Exception:
            LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/%s/pairlist'", 
                          {self.login_data['sphone_uuid']}
            )            
            return False

    async def request_pairnum_login(self, wallpad_number: str = None) -> Union[dict[str, str], bool]:
        """If there is no paired device, try pairing through authentication number"""
        url = f'http://kbranch.kocom.co.kr/api/{self.login_data['sphone_uuid']}/pairnum'
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": generate_digest_header(
                self.login_data['sphone_uuid'], self.login_data['sphone_info']['pwd'],
                f'/api/{self.login_data['sphone_uuid']}/pairnum', self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }
        data = {"pairnum": wallpad_number}

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            LOGGER.debug("request_pairnum_login - response :: %s", json_data)

            return json_data
        except Exception:
            LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/%s/pairnum'", 
                          {self.login_data['sphone_uuid']}
            )            
            return False
        
    def is_device_state(self, device: str, id: str, function: str) -> Union[bool, int]:
        """Derive status information from the light, outlet and thermostat list."""
        try:            
            for device_entry in self.device_data[device]['data']['entry']:
                if device_entry['id'] == id:
                    for entry_list in device_entry['list']:
                        if entry_list['function'] == function:
                            return int(entry_list['value'])
        except Exception as ex:
            LOGGER.error("There was a problem in deriving the value of the '%s' list. ex: %s", device, ex)

    async def check_device_status(self, device: str, path: str = "/control/allstatus") -> dict:
        """Check the status of the device's entire item"""
        server_ip = self.login_data['pair_info']['svrip']
        zone_id = self.login_data['zone_id']

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": generate_digest_header(
                self.login_data['sphone_uuid'], self.login_data['sphone_info']['pwd'],
                f'/api/{self.login_data['zone_id']}{path}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        data = {"type": device, "cmd": "status"}

        try:
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            LOGGER.debug("check_device_status - response :: %s", json_data)
            
            return json_data
        except Exception:
            LOGGER.error(
                "Device: '%s' status request to apartment server failed, Path: '/control/allstatus'", device
            )

    async def send_control_request(self, type: str, id: str, function: str, value: str, path: str = "/control") -> dict:
        """Device Control Request"""
        server_ip = self.login_data['pair_info']['svrip']
        zone_id = self.login_data['zone_id']

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)                                     

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": generate_digest_header(
                self.login_data['sphone_uuid'], self.login_data['sphone_info']['pwd'], 
                f'/api/{self.login_data['zone_id']}{path}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        data = {"cmd": "control", "type": type, "id": id, "function": function, "value": value}

        try:
            LOGGER.info("Prepare a device command request to the apartment server. %s, %s, %s, %s",
                        type, id, function, value
            )
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)

            json_data = await response.json(content_type='text/html')
            LOGGER.debug("send_control_request - response :: %s", json_data)

            return json_data
        except Exception:
            LOGGER.error("Device: '%s' command request to apartment server failed, Path: '/control'", type)

    def extract_meaningful_data(self, response: dict[str] = {}) -> dict:
        """Remove meaningless data from lights/consents"""
        room_cnt = self.entry.data['max_room_cnt']
        switch_cnt = self.entry.data['max_switch_cnt']
        try:
            response['entry'] = [entry for entry in response['entry'] if int(entry['id'][2:]) <= room_cnt]
            if response['type'] in ['light', 'concent']:
                for entry in response['entry']:
                    entry['list'] = [item for item in entry['list'] if int(item['function'][3:]) <= switch_cnt]
            return response
        except Exception as ex:
            LOGGER.error(
                "There was an error parsing the status type or there was a problem removing the element. %s, ex: %s",
                response, ex
            )

    def update_device_data(self, control_response: dict[str] = {}) -> None:
        try:
            device_type = control_response['type']
            if device_type and control_response['entry']:
                device_data_to_modify = self.device_data[device_type]['data']
                for device_entry in device_data_to_modify['entry']:
                    if device_entry['id'] == control_response['entry'][0]['id']:
                        device_entry['list'] = control_response['entry'][0]['list'][:len(device_entry['list'])]
                        return device_data_to_modify
        except Exception as ex:
            LOGGER.error("There was a problem updating the device_data element. %s, ex: %s", control_response, ex)

            
