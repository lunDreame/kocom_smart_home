"""Adds config flow for kocom_smart_home"""
import re
import voluptuous as vol
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)

from .api import KocomSmartHomeAPI
from .const import DOMAIN, LOGGER

def int_between(min_int, max_int):
    """Return an integer between 'min_int' and 'max_int'."""
    return vol.All(vol.Coerce(int), vol.Range(min=min_int, max=max_int))


class KocomSmartHomeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    _api: KocomSmartHomeAPI
    _data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return KocomSmartHomeOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}
        already_sphone = False

        if user_input is not None:
            self._data.update(user_input)

            if not re.match(r"^010\d{8}$", user_input["phone_number"]):
                errors["base"] = "invalid_phone_number"
            else:
                self._api = KocomSmartHomeAPI()
                sphone_login = await self._api.request_sphone_login(
                    user_input["phone_number"]
                )

                if isinstance(sphone_login, bool) and not sphone_login:
                    errors["base"] = "network_error"
                elif sphone_login:
                    self._data["pairing_data"] = sphone_login
                    already_sphone = True

            if not (errors or already_sphone):
                return await self.async_step_wallpad()
            elif already_sphone:
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({
                vol.Required("phone_number"): cv.string}), errors=errors,
        )
    
    async def async_step_wallpad(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Request information entered through the user to the wallpad."""
        errors = {}

        if user_input is not None:
            #self._data.update(user_input)

            if not re.match(r"^\d{8}$", user_input["wallpad_number"]):
                errors["base"] = "invalid_auth_number"
            else:
                pairnum_login = await self._api.request_pairnum_login(
                    user_input["wallpad_number"]
                )
                if pairnum_login.get("error-msg") == "PairNum Fail":
                    errors["base"] = "wallpad_auth_failure"
            
            if not errors:
                pairlist_login = await self._api.request_pairlist_login()
                self._data["pairing_data"] = pairlist_login

                if isinstance(pairlist_login, bool) and not pairlist_login:
                    return self.async_abort(reason="registration_failed")
                else:
                    return await self.async_step_options()

        return self.async_show_form(
            step_id="wallpad", data_schema=vol.Schema({
                vol.Required("wallpad_number"): cv.string}), errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Defines the Kocom options."""
        if user_input is not None:
            self._data.update(user_input)

            return self.async_create_entry(
                title=self._data["phone_number"], data=self._data
            )

        data_schema = vol.Schema(
            {
                vol.Required("room_count", default=4): int_between(1, 6),
                vol.Required("switch_count", default=2): int_between(1, 8),
                vol.Required("light_interval", default=120): cv.positive_int,
                vol.Required("concent_interval", default=300): cv.positive_int,
                vol.Required("heat_interval", default=300): cv.positive_int,
                vol.Required("aircon_interval", default=300): cv.positive_int,
                vol.Required("gas_interval", default=600): cv.positive_int,
                vol.Required("vent_interval", default=600): cv.positive_int,
                vol.Required("energy_interval", default=1200): cv.positive_int,
                vol.Required("totalcontrol_interval", default=900): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="options", data_schema=data_schema, errors={},
        )


class KocomSmartHomeOptionsFlowHandler(OptionsFlow):
    """Handle a option flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        data_schema = vol.Schema({
            vol.Required(
                "light_interval",
                default=self.config_entry.options.get(
                    "light_interval", self.config_entry.data["light_interval"])
                ): cv.positive_int,
            vol.Required(
                "concent_interval",
                default=self.config_entry.options.get(
                    "concent_interval", self.config_entry.data["concent_interval"])
                ): cv.positive_int,
            vol.Required(
                "heat_interval",
                default=self.config_entry.options.get(
                    "heat_interval", self.config_entry.data["heat_interval"])
                ): cv.positive_int,
            vol.Required(
                "aircon_interval",
                default=self.config_entry.options.get(
                    "aircon_interval", self.config_entry.data["aircon_interval"])
                ): cv.positive_int,
            vol.Required(
                "gas_interval",
                default=self.config_entry.options.get(
                    "gas_interval", self.config_entry.data["gas_interval"])
                ): cv.positive_int,
            vol.Required(
                "vent_interval",
                default=self.config_entry.options.get(
                    "vent_interval", self.config_entry.data["vent_interval"])
                ): cv.positive_int,
            vol.Required(
                "energy_interval",
                default=self.config_entry.options.get(
                    "energy_interval", self.config_entry.data["energy_interval"])
                ): cv.positive_int,
            vol.Required(
                "totalcontrol_interval",
                default=self.config_entry.options.get(
                    "totalcontrol_interval", self.config_entry.data["totalcontrol_interval"])
                ): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors={},
        )
