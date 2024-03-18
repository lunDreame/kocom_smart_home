"""Adds config flow for Kocom Smart Home"""
import re
import logging
import voluptuous as vol
from typing import *

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import KocomHomeManager
from .const import (
    DOMAIN,
    CONF_PHONE_NUMBER,
    CONF_WALLPAD_NUMBER,
    PAIR_INFO,
    CONF_ROOM_INTERVAL,
    CONF_GAS_INTERVAL,
    CONF_VENT_INTERVAL,
    CONF_ENERGY_INTERVAL
)

_LOGGER = logging.getLogger(__name__)

class KocomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Kocom Smart home."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize."""
        self._errors: dict[str, str] = {}
        self._userdata: dict[str] = {}
        self._manager = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {} 

        if user_input is not None:
            phone_number = user_input.get(CONF_PHONE_NUMBER, '')
            already_sphone: bool = False

            if not re.search(r'^010\d{8}$', phone_number):
                errors['base'] = "invalid_phone"
                
            else:
                self._userdata[CONF_PHONE_NUMBER] = phone_number
                self._manager = KocomHomeManager(self.hass)
                sphone_login = await self._manager.request_sphone_login(phone_number)

                if isinstance(sphone_login, bool) and not sphone_login:
                    errors['base'] = "network_error"
                elif sphone_login:
                    self._userdata[PAIR_INFO] = sphone_login
                    already_sphone = True

                _LOGGER.debug("async_step_user. sphone_login :: %s", sphone_login)
            if not (errors or already_sphone):
                return await self.async_step_wallpad()
            elif already_sphone:
                return self.async_create_entry(title=phone_number, data=self._userdata)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required(CONF_PHONE_NUMBER): cv.string,}), errors=errors or {}
        )
    
    @callback
    async def async_step_wallpad(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
    
        if user_input is not None:
            wallpad_number = user_input.get(CONF_WALLPAD_NUMBER, "")

            if not re.search(r'^\d{8}$', wallpad_number):
                errors['base'] = "invalid_auth"
                
            else:
                self._userdata[CONF_WALLPAD_NUMBER] = wallpad_number
                pairnum_login = await self._manager.request_pairnum_login(wallpad_number)

                if pairnum_login.get('error-msg') == "PairNum Fail":
                    errors['base'] = "auth_failure"
            
            if not errors:
                pairlist_login = await self._manager.request_pairlist_login()
                self._userdata[PAIR_INFO] = pairlist_login

                if isinstance(pairlist_login, bool) and not pairlist_login:
                    return self.async_abort(reason="registration_failed")
                else:
                    return self.async_create_entry(
                        title=self._userdata.get(CONF_PHONE_NUMBER, ''), data=self._userdata
                    )
               
        return self.async_show_form(
            step_id="wallpad", data_schema=vol.Schema({
                vol.Required(CONF_WALLPAD_NUMBER): cv.string,}), errors=errors or {}
        )
   
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Handle a option flow."""
        return KocomOptionsFlowHandler(config_entry)

class KocomOptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry) -> None:
        self._config_entry = config_entry
        self._user_data: dict[str] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}

        if user_input is not None:
            if not errors:
                self._user_data[CONF_ROOM_INTERVAL] = user_input.get(CONF_ROOM_INTERVAL)
                self._user_data[CONF_GAS_INTERVAL] = user_input.get(CONF_GAS_INTERVAL)
                self._user_data[CONF_VENT_INTERVAL] = user_input.get(CONF_VENT_INTERVAL)
                self._user_data[CONF_ENERGY_INTERVAL] = user_input.get(CONF_ENERGY_INTERVAL)

                return self.async_create_entry(title=self._config_entry[CONF_PHONE_NUMBER], data=self._user_data)

        schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_INTERVAL, default=300): cv.positive_int,
                vol.Required(CONF_GAS_INTERVAL, default=300): cv.positive_int,
                vol.Required(CONF_VENT_INTERVAL, default=300): cv.positive_int,
                vol.Required(CONF_ENERGY_INTERVAL, default=600): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
