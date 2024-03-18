import logging
import asyncio
from datetime import datetime
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity

from .const import (
    DOMAIN,
    VERSION, 
    CONF_PHONE_NUMBER,
    PAIR_INFO,
    ROOM_ICONS,
    ENERGY_NAME,
    ENERGY_UNIT_NAME
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=600)

async def async_setup_entry(hass, config_entry, async_add_entities):
    hass_data = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    for device, id in hass_data.device_data.items():
        entities.append(KocomRoom(device, id, hass_data))

    try: 
        energy_stdcheck = await hass_data.fetch_energy_stdcheck()

        for item_list in energy_stdcheck['list']:
            elements = [key for key in item_list if key not in ['energy', 'date']]
            entities.extend(KocomEnergy(item_list, period, hass_data) for period in elements)

    except Exception as ex:
        _LOGGER.error("async_setup_entry Failed to upload KocomEnergy: %s", ex)

    if hass_data.login_data.get(PAIR_INFO, False):
        entities.append(KocomLoginInfo(hass_data.login_data[PAIR_INFO], hass_data))

    async_add_entities(entities)



class KocomRoom(Entity):
    def __init__(self, device_type, device_id, hass_data) -> None:
        self._device_type = device_type
        self._device_id = device_id
        self._hass_data = hass_data
        self._sync_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._attributes = {
            "Device type": device_type,
            "Device room": ", ".join([f'{i:02d}' for i in range(len(device_id['entry']))])
        }

    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'sensor.{self._device_type}_room_sensor_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'
    
    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{self._device_type.title()} Room Sensor'

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ROOM_ICONS[self._device_type]

    @property
    def state(self):
        return self._sync_date
    
    @property
    def extra_state_attributes(self):
        """Attributes."""
        return {**self._attributes, "Sync date": self._sync_date}

    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return

        await asyncio.gather(
            self._hass_data.device_state('light'),
            self._hass_data.device_state('outlet'),
            self._hass_data.device_state('thermostat')
        )

        self._sync_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'kocom')},
            "name": "KOCOM",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }
    
    

class KocomLoginInfo(Entity):
    def __init__(self, pair_info, hass_data) -> None:
        self._pair_info = pair_info
        self._hass_data = hass_data
        self._sync_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
   
    @property
    def unique_id(self):
        """Return the entity ID."""
        return f'{self._pair_info['list'][0]['alias'].lower()}_login_info_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        return f'{self._pair_info['list'][0]['alias']} Login Info'

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return "mdi:login"

    @property
    def state(self):
        return self._sync_date

    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Index": self._pair_info['list'][0]['idx'],
            "Zone": self._pair_info['list'][0]['zone'],
            "ID": self._pair_info['list'][0]['id'],
            "Alias": self._pair_info['list'][0]['alias'],
            "Server IP": self._pair_info['list'][0]['svrip'],
            "Server port": self._pair_info['list'][0]['svrport'],
        }
        return attributes

    async def async_update(self):
        """Get the latest state of the sensor."""
    
    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'kocom')},
            "name": "KOCOM",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }
    


class KocomEnergy(SensorEntity):
    def __init__(self, item_list, item_period, hass_data) -> None:
        self._item_list = item_list
        self._item_period = item_period
        self._hass_data = hass_data
        self._previous_month = self._extract_previous_month(self._item_list['date'])
        self._period_suffix = "_previous" if self._previous_month else ""

    def _extract_previous_month(self, date_str: str) -> bool:
        try:
            previous_month = int(date_str.split()[0].replace('-', '')) // 100
            current_year_month = int(datetime.now().strftime("%Y%m"))
            return current_year_month > previous_month
        except Exception:
            return False
    
    @property
    def unique_id(self):
        """Return the entity ID."""
        if self._item_period == "price":
            return f'{self._item_list['energy']}{self._period_suffix}_expect_price_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'
        else:
            return f'{self._item_list['energy']}{self._period_suffix}_{self._item_period}_usage_{self._hass_data.entry.data[CONF_PHONE_NUMBER][7:]}'

    @property
    def name(self):
        """Return the name of the sensor, if any."""
        if self._item_period == "price":
            return f'{ENERGY_NAME[self._item_list['energy']][0]} {ENERGY_UNIT_NAME[self._period_suffix+'price']}'
        else:
            return f'{ENERGY_UNIT_NAME[self._period_suffix+self._item_period]} {ENERGY_NAME[self._item_list['energy']][0]}'

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ENERGY_NAME[self._item_list['energy']][1]

    @property
    def unit_of_measurement(self):
        if self._item_period == "price":
            return "krw"
        else:
            return ENERGY_NAME[self._item_list['energy']][2]

    @property
    def device_class(self):
        return ENERGY_NAME[self._item_list['energy']][3]
        
    @property
    def state_class(self):
        name = self._item_list['energy']
        state_class = ENERGY_NAME[name][4]
    
        if state_class is not None and self._previous_month:
            return state_class.split('_')[0]
        else:
            return state_class
        
    @property
    def state(self):
        return self._item_list[self._item_period]
    
    @property
    def extra_state_attributes(self):
        """Attributes."""
        attributes = {
            "Device room": self._item_list['energy'],
            "Device type": self._item_period,
            "Device state": self._item_list[self._item_period],
            "Sync date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return attributes

    async def async_update(self):
        """Get the latest state of the sensor."""
        if self._hass_data is None: 
            return

        energy_stdcheck = await self._hass_data.fetch_energy_stdcheck()
        
        for item_list in energy_stdcheck['list']:
            if item_list['energy'] == self._item_list['energy'] and item_list['date'] == self._item_list['date']:
                self._item_list = item_list

    @property
    def device_info(self):
        """Return information about the device."""
        return {
            "identifiers": {(DOMAIN, 'energy')},
            "name": "KOCOM Energy",
            "manufacturer": "Kocom Co, Ltd.",
            "model": self._hass_data.login_data[PAIR_INFO]['list'][0]['alias'],
            "sw_version": VERSION
        }
