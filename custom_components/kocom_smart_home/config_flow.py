"""Adds config flow for Kocom Smart Home"""
import re
import voluptuous as vol
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    OptionsFlow,
)

from .api import KocomHomeAPI
from .const import (
    DOMAIN,
    LOGGER,
    CONF_PHONE_NUMBER,
    CONF_WALLPAD_NUMBER,
    MAX_ROOM_CNT,
    MAX_SWITCH_CNT,
    LIGHT_INTERVAL,
    CONCENT_INTERVAL,
    HEAT_INTERVAL,
    AIRCON_INTERVAL,
    GAS_INTERVAL,
    VENT_INTERVAL,
    ENERGY_INTERVAL,
    TOTALCTRL_INTERVAL
)

def int_between(min_int, max_int):
    """Return an integer between 'min_int' and 'max_int'."""
    return vol.All(vol.Coerce(int), vol.Range(min=min_int, max=max_int))


class KocomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    api: KocomHomeAPI = None
    data: dict[str, Any]

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return KocomOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, 
        user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle a flow initiated by the user."""
        errors = {}
        already_sphone = False

        if user_input is not None:
            self.data = user_input

            if not re.match(r"^010\d{8}$", self.data[CONF_PHONE_NUMBER]):
                errors["base"] = "invalid_phone_number"
            else:
                self.api = KocomHomeAPI(self.hass)
                sphone_login = await self.api.request_sphone_login(self.data[CONF_PHONE_NUMBER])

                if isinstance(sphone_login, bool) and not sphone_login:
                    errors["base"] = "network_error"
                elif sphone_login:
                    self.data["pairing_data"] = sphone_login
                    already_sphone = True

            if not (errors or already_sphone):
                return await self.async_step_wallpad()
            elif already_sphone:
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({vol.Required(CONF_PHONE_NUMBER): cv.string}),
            errors=errors,
            last_step=False,
        )
    
    async def async_step_wallpad(
        self, 
        user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Request information entered through the user to the wallpad."""
        errors = {}

        if user_input is not None:
            self.data = user_input

            if not re.match(r"^\d{8}$", self.data[CONF_WALLPAD_NUMBER]):
                errors["base"] = "invalid_auth_number"
            else:
                pairnum_login = await self.api.request_pairnum_login(self.data[CONF_WALLPAD_NUMBER])
                if pairnum_login.get("error-msg") == "PairNum Fail":
                    errors["base"] = "wallpad_auth_failure"
            
            if not errors:
                pairlist_login = await self.api.request_pairlist_login()
                self.data["pairing_data"] = pairlist_login

                if isinstance(pairlist_login, bool) and not pairlist_login:
                    return self.async_abort(reason="registration_failed")
                else:
                    return await self.async_step_options()

        return self.async_show_form(
            step_id="wallpad",
            data_schema=vol.Schema({vol.Required(CONF_WALLPAD_NUMBER): cv.string}),
            errors=errors,
            last_step=False,
        )
   
    async def async_step_options(
        self, 
        user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Defines the Kocom options."""
        if user_input is not None:
            return self.async_create_entry(
                title=self.data[CONF_PHONE_NUMBER],
                data={**self.data, **user_input}
            )

        data_schema = vol.Schema(
            {
                vol.Required(MAX_ROOM_CNT, default=4): int_between(1, 6),
                vol.Required(MAX_SWITCH_CNT, default=2): int_between(1, 8),
                vol.Required(LIGHT_INTERVAL, default=120): cv.positive_int,
                vol.Required(CONCENT_INTERVAL, default=300): cv.positive_int,
                vol.Required(HEAT_INTERVAL, default=300): cv.positive_int,
                vol.Required(AIRCON_INTERVAL, default=300): cv.positive_int,
                vol.Required(GAS_INTERVAL, default=600): cv.positive_int,
                vol.Required(VENT_INTERVAL, default=600): cv.positive_int,
                vol.Required(ENERGY_INTERVAL, default=1200): cv.positive_int,
                vol.Required(TOTALCTRL_INTERVAL, default=900): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="options",
            data_schema=data_schema,
            errors={},
        )


class KocomOptionsFlowHandler(OptionsFlow):
    """Handle a option flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
    
    async def async_step_init(
        self, 
        user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        data_schema = vol.Schema({
                vol.Required(
                    LIGHT_INTERVAL,
                    default=self.config_entry.options.get(
                        LIGHT_INTERVAL, self.config_entry.data[LIGHT_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    CONCENT_INTERVAL,
                    default=self.config_entry.options.get(
                        CONCENT_INTERVAL, self.config_entry.data[CONCENT_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    HEAT_INTERVAL,
                    default=self.config_entry.options.get(
                        HEAT_INTERVAL, self.config_entry.data[HEAT_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    AIRCON_INTERVAL,
                    default=self.config_entry.options.get(
                        AIRCON_INTERVAL, self.config_entry.data[AIRCON_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    GAS_INTERVAL,
                    default=self.config_entry.options.get(
                        GAS_INTERVAL, self.config_entry.data[GAS_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    VENT_INTERVAL,
                    default=self.config_entry.options.get(
                        VENT_INTERVAL, self.config_entry.data[VENT_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    ENERGY_INTERVAL,
                    default=self.config_entry.options.get(
                        ENERGY_INTERVAL, self.config_entry.data[ENERGY_INTERVAL])
                    ): cv.positive_int,
                vol.Required(
                    TOTALCTRL_INTERVAL,
                    default=self.config_entry.options.get(
                        TOTALCTRL_INTERVAL, self.config_entry.data[TOTALCTRL_INTERVAL])
                    ): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors={},
        )

