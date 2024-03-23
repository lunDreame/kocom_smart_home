import logging
import json
import re
import string
import random
import hashlib
import time
import asyncio
import datetime
from typing import *

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    SPHONE_INFO,
    SPHONE_UUID,
    PAIR_INFO,
    ZONE_ID,
    TIMEOUT_SEC,
)

_LOGGER = logging.getLogger(__name__)


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
                    # gas, vnet = power
                    return bool(int(entry['value']))
                else:
                    # vent = wind ('1', '2', '3')
                    return entry['value']
        return None
    
    except KeyError as e:
        _LOGGER.error("KeyError while parsing %s: %s", key, e)
    except Exception as e:
        _LOGGER.error("An error occurred while parsing %s: %s", key, e)



class KocomHomeManager:
    """Home Manager"""

    """Base API URL"""
    API_SERVER_URL = "http://kbranch.kocom.co.kr"
    API_TYPE_URL = "http://{}/api/{}"

    """Net State Until"""
    ANDROID_MEMBERSHIP = "4990e9e16a532aa9010403b01e0ee52a"
    DIGEST_IKOD = "Android!1000001"

    def __init__(self, hass):
        """Initialize."""
        self.hass = hass
        self.entry = None
        self.kbranch_tokens: dict[str, str] = {}
        self.apartment_tokens: dict[str, str] = {}
        self.login_data: dict[str] = {}
        self.device_data: dict[str] = {
            'light': {}, 'outlet': {}, 'thermostat': {}, 'aircon': {}
        }
        
    async def set_entry(self, entry) -> None:
        """Set entry data."""
        self.entry = entry
        self.login_data = self.entry.data.get(PAIR_INFO, {})
        if all(not value for value in self.device_data.values()):
            await asyncio.gather(
                self.device_state('light'),
                self.device_state('outlet'),
                self.device_state('thermostat'),
                self.device_state('aircon')
            )

    async def device_state(self, device: str):
        async def check_light_state() -> None:
            """Check lighting status"""
            status = await self.check_device_status('light')
            self.device_data['light'] = self.extract_meaningful_data(status)

        async def check_outlet_state():
            """Check outlet status"""
            status = await self.check_device_status('concent')
            self.device_data['outlet'] = self.extract_meaningful_data(status)

        async def check_thermostat_state():
            """Check thermostat status"""
            status = await self.check_device_status('heat')
            self.device_data['thermostat'] = self.extract_meaningful_data(status)

        async def check_aircon_state():
            """Check thermostat status"""
            status = await self.check_device_status('aircon')
            self.device_data['aircon'] = self.extract_meaningful_data(status)

        if device == 'light':
            await check_light_state()
        elif device == 'outlet':
            await check_outlet_state()
        elif device == 'thermostat':
            await check_thermostat_state()
        elif device == 'aircon':
            await check_aircon_state()

    def generate_digest_header(self, username: str, password: str, uri: str, nonce: str) -> str:
        """Authorization header create."""
        username_hash = hashlib.md5(f"{username}:kbranch:{password}".encode()).hexdigest()
        uri_hash = hashlib.md5(f"GET:{uri}".encode()).hexdigest()
        response = hashlib.md5(f"{username_hash}:{nonce}:{uri_hash}".encode()).hexdigest()
        return f'Digest username="{username}", realm="kbranch", nonce="{nonce}", uri="{uri}", response="{response}"'
        
    def generate_fcm_token(self, input_string, length=163) -> str:
        """FCM Token create."""
        random.seed(input_string)
        characters = string.ascii_letters + string.digits
        fcm_token = ''.join(random.choice(characters) for _ in range(length))
        _LOGGER.debug("Generated FCM Token: %s", fcm_token)
        return fcm_token

    async def fetch_kbranch_token(self) -> None:
        """Gets the authentication token of the kbranch kocom server."""
        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(f'{self.API_SERVER_URL}/api/sphone')

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get('Set-Cookie', ''))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get('WWW-Authenticate', ''))
            self.kbranch_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception:
            _LOGGER.error("Request failed to get FCM authentication token from Kocom server")
    
    async def fetch_apartment_server_token(self) -> None:
        """Gets the authentication token of the apartment server."""
        server_ip = self.login_data[PAIR_INFO]['list'][0]['svrip']
        zone_id = self.login_data[ZONE_ID]

        url = self.API_TYPE_URL.format(server_ip, zone_id)

        session = async_get_clientsession(self.hass)
        try: 
            response = await session.get(url)

            session_id = re.search(r'PHPSESSID=[a-zA-Z0-9]+', response.headers.get('Set-Cookie', ''))
            nonce_id = re.search(r'nonce="([^"]+)"', response.headers.get('WWW-Authenticate', ''))
            self.apartment_tokens = {"cookie": session_id.group(), "nonce": nonce_id.group(1)}
        except Exception:
            _LOGGER.error("Request failed while retrieving authentication token for apartment server")

    async def fetch_energy_stdcheck(self, path: str = "/energy/stdcheck/") -> dict:
        server_ip = self.login_data[PAIR_INFO]['list'][0]['svrip']
        zone_id = self.login_data[ZONE_ID]

        now = datetime.datetime.now()
        year_month = now.strftime("%Y-%m").replace('-', '')

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'],
                f'/api/{self.login_data[ZONE_ID]}{path}{year_month}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        try: 
            response = await session.get(url+path+year_month, headers=headers)
            json_data = await response.json(content_type='text/html')
            _LOGGER.debug("fetch_energy_stdcheck - response :: %s", json_data)
            
            return json_data
        except Exception:
            _LOGGER.error("Request failed while retrieving energy usage from apartment complex server")

    async def request_sphone_login(self, phone_number: str = None) -> Union[bool, Callable]:
        """First sphone login for wallpad authentication"""
        url = f'{self.API_SERVER_URL}/api/sphone'
        session = async_get_clientsession(self.hass)

        if not self.kbranch_tokens:
            await self.fetch_kbranch_token()
            _LOGGER.debug("request_sphone_login - kbranch_tokens :: %s", self.kbranch_tokens)

        headers = {
            "Authorization": self.generate_digest_header(
                self.DIGEST_IKOD, self.ANDROID_MEMBERSHIP, "/api/sphone", self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }
        data = {"phonenum": phone_number, "type": self.DIGEST_IKOD, "token": self.generate_fcm_token(phone_number)}

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            self.login_data[SPHONE_INFO] = json_data
            self.login_data[SPHONE_UUID] = f'00000{str(json_data['zone'])}00{str(json_data['id'])}'

            return await self.request_pairlist_login()    
        except Exception:
            _LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/sphone'")
            return False

    """
    async def request_info_login(self) -> Union[bool, Callable]:
        Gets the login return information for the sphone.
        
        zone = self.login_data[SPHONE_INFO]['zone']
        id = self.login_data[SPHONE_INFO]['id']

        self.login_data[SPHONE_UUID] = f'00000{str(zone)}00{str(id)}'

        url = f'{self.API_SERVER_URL}/api/{self.login_data[SPHONE_UUID]}/info'
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'],
                f'/api/{self.login_data[SPHONE_UUID]}/info', self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }
        data = {"version": "1000002", "pushid": ""}

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            _LOGGER.debug("request_info_login - response :: %s", await response.text())

            return await self.request_pairlist_login()    
        except Exception:
            _LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/%s/info'", 
                          {self.login_data[SPHONE_UUID]}
            )
            return False
    """

    async def request_pairlist_login(self) -> Union[dict, bool]:
        """Finds the paired device based on the phone number."""
        url = f'{self.API_SERVER_URL}/api/{self.login_data[SPHONE_UUID]}/pairlist'
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'],
                f'/api/{self.login_data[SPHONE_UUID]}/pairlist', self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }

        try: 
            response = await session.get(url, headers=headers, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            _LOGGER.debug("request_pairlist_login - response :: %s", json_data)
            
            if len(json_data.get('list', 0)) == 1:            
                self.login_data[PAIR_INFO] = json_data

                zone, id = json_data['list'][0]['zone'], json_data['list'][0]['id']
                self.login_data[ZONE_ID] = f'00{str(zone)}0{str(id)}'

                return self.login_data
            else:
                _LOGGER.info("Pairing information not found.")
                return {}
                
        except Exception:
            _LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/%s/pairlist'", 
                          {self.login_data[SPHONE_UUID]}
            )            
            return False

    async def request_pairnum_login(self, wallpad_number: str = None) -> Union[dict[str, str], bool]:
        """If there is no paired device, try pairing through authentication number"""
        url = f'http://kbranch.kocom.co.kr/api/{self.login_data[SPHONE_UUID]}/pairnum'
        session = async_get_clientsession(self.hass)

        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'],
                f'/api/{self.login_data[SPHONE_UUID]}/pairnum', self.kbranch_tokens['nonce']
            ),
            "Cookie": self.kbranch_tokens['cookie'],
        }
        data = {"pairnum": wallpad_number}

        try: 
            response = await session.get(url, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            _LOGGER.debug("request_pairnum_login - response :: %s", json_data)

            return json_data
        except Exception:
            _LOGGER.error("Request failed while attempting a login request to the Kocom server, PATH: '/api/%s/pairnum'", 
                          {self.login_data[SPHONE_UUID]}
            )            
            return False
        
    def is_device_state(self, device: str, id: str, function: str) -> Union[bool, int]:
        """Derive status information from the light, outlet and thermostat list."""
        try:            
            for device_entry in self.device_data[device]['entry']:
                if device_entry['id'] == id:
                    for entry_list in device_entry['list']:
                        if entry_list['function'] == function:
                            return int(entry_list['value'])
        except Exception as ex:
            _LOGGER.error("There was a problem in deriving the value of the '%s' list. ex: %s", device, ex)

    async def check_device_status(self, device: str, path: str = "/control/allstatus") -> dict:
        """Check the status of the device's entire item"""
        server_ip = self.login_data[PAIR_INFO]['list'][0]['svrip']
        zone_id = self.login_data[ZONE_ID]

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)         

        await self.fetch_apartment_server_token()
                                         
        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'],
                f'/api/{self.login_data[ZONE_ID]}{path}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        data = {"type": device, "cmd": "status"}

        try:
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)
            json_data = await response.json(content_type='text/html')
            _LOGGER.debug("check_device_status - response :: %s", json_data)
            
            return json_data
        except Exception:
            _LOGGER.error(
                "Device: '%s' status request to apartment server failed, Path: '/control/allstatus'", device
            )

    async def send_control_request(self, type: str, id: str, function: str, value: str, path: str = "/control") -> dict:
        """Device Control Request"""
        server_ip = self.login_data[PAIR_INFO]['list'][0]['svrip']
        zone_id = self.login_data[ZONE_ID]

        url = self.API_TYPE_URL.format(server_ip, zone_id)
        session = async_get_clientsession(self.hass)                                     

        await self.fetch_apartment_server_token()

        headers = {
            "Authorization": self.generate_digest_header(
                self.login_data[SPHONE_UUID], self.login_data[SPHONE_INFO]['pwd'], 
                f'/api/{self.login_data[ZONE_ID]}{path}', self.apartment_tokens['nonce']
            ),
            "Cookie": self.apartment_tokens['cookie'],
        }
        data = {"cmd": "control", "type": type, "id": id, "function": function, "value": value}

        try:
            _LOGGER.info("Prepare a device command request to the apartment server. %s, %s, %s, %s",
                        type, id, function, value
            )
            response = await session.get(url+path, headers=headers, json=data, timeout=TIMEOUT_SEC)

            json_data = await response.json(content_type='text/html')
            _LOGGER.debug("send_control_request - response :: %s", json_data)

            return json_data
        except Exception:
            _LOGGER.error("Device: '%s' command request to apartment server failed, Path: '/control'", type)

    def extract_meaningful_data(self, response: dict[str] = {}) -> dict:
        """Remove meaningless data from lights/consents"""
        try:
            response['entry'] = [entry for entry in response['entry'] if int(entry['id'][2:]) < 5]
            if response['type'] in ['light', 'concent']:
                for entry in response['entry']:
                    entry['list'] = [item for item in entry['list'] if int(item['function'][3:]) < 3]
            return response
        except Exception as ex:
            _LOGGER.error(
                "There was an error parsing the status type or there was a problem removing the element. %s, ex: %s",
                response, ex
            )

    def update_device_data(self, result: dict[str] = {}) -> None:
        try:
            device_type_mapping = {"concent": "outlet", "heat": "thermostat"}
            device_type = device_type_mapping.get(result['type'], 'light')

            if device_type:
                device_data_to_modify = self.device_data[device_type]
                for device_entry in device_data_to_modify['entry']:
                    if device_entry['id'] == result['entry'][0]['id']:
                        device_entry['list'] = result['entry'][0]['list'][:len(device_entry['list'])]
                        return self.device_data[device_type]
        except Exception as ex:
            _LOGGER.error("There was a problem updating the device_data element. %s, ex: %s", result, ex)
