"""Adds config flow for Kocom Smart Home"""
import re
import voluptuous as vol
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import KocomHomeAPI
from .const import DOMAIN, LOGGER

class KocomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Kocom Smart home."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize."""
        self.api = None
        self.errors: dict[str, str] = {}
        self.user_data: dict[str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {} 

        if user_input is not None:
            phone_number = user_input.get('phone_number', '')
            already_sphone: bool = False

            if not re.search(r'^010\d{8}$', phone_number):
                errors['base'] = "invalid_phone"
                
            else:
                self.user_data['phone_number'] = phone_number
                self.api = KocomHomeAPI(self.hass)
                sphone_login = await self.api.request_sphone_login(phone_number)

                if isinstance(sphone_login, bool) and not sphone_login:
                    errors['base'] = "network_error"
                elif sphone_login:
                    self.user_data['pair_info'] = sphone_login
                    already_sphone = True

                LOGGER.debug("async_step_user. sphone_login :: %s", sphone_login)
            if not (errors or already_sphone):
                return await self.async_step_wallpad()
            elif already_sphone:
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required('phone_number'): cv.string,}), errors=errors or {}
        )
    
    @callback
    async def async_step_wallpad(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
    
        if user_input is not None:
            wallpad_number = user_input.get('wallpad_number', "")

            if not re.search(r'^\d{8}$', wallpad_number):
                errors['base'] = "invalid_auth"
                
            else:
                self.user_data['wallpad_number'] = wallpad_number
                pairnum_login = await self.api.request_pairnum_login(wallpad_number)

                if pairnum_login.get('error-msg') == "PairNum Fail":
                    errors['base'] = "auth_failure"
            
            if not errors:
                pairlist_login = await self.api.request_pairlist_login()
                self.user_data['pair_info'] = pairlist_login

                if isinstance(pairlist_login, bool) and not pairlist_login:
                    return self.async_abort(reason="registration_failed")
                else:
                    return await self.async_step_options()
               
        return self.async_show_form(
            step_id="wallpad", data_schema=vol.Schema({
                vol.Required('wallpad_number'): cv.string,}), errors=errors or {}
        )
   
    @callback
    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}

        if user_input is not None:
            if not errors:
                self.user_data = {**self.user_data, **user_input}
                return self.async_create_entry(
                    title=self.user_data.get('phone_number', ''), data=self.user_data
                )

        schema = vol.Schema(
            {
                vol.Required('max_room_cnt', default=4): 
                vol.All(vol.Coerce(int), vol.Range(min=1, max=6)),
                vol.Required('max_switch_cnt', default=2):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
                vol.Required('light_interval', default=120): cv.positive_int,
                vol.Required('concent_interval', default=300): cv.positive_int,
                vol.Required('heat_interval', default=300): cv.positive_int,
                vol.Required('aircon_interval', default=300): cv.positive_int,
                vol.Required('gas_interval', default=600): cv.positive_int,
                vol.Required('vent_interval', default=600): cv.positive_int,
                vol.Required('energy_interval', default=1200): cv.positive_int,
                vol.Required('totalcontrol_interval', default=900): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=schema, errors=errors
        )

    #@staticmethod
    #@callback
    #def async_get_options_flow(config_entry):
    #    """Handle a option flow."""
    #    return KocomOptionsFlowHandler(config_entry)

class KocomOptionsFlowHandler(config_entries.OptionsFlow):
    """Handles options flow for the component."""

    def __init__(self, config_entry) -> None:
        """Initialize Options"""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}
