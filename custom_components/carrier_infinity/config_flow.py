"""The setup forms: sign in with the Carrier app account, and re-enter the password if Carrier stops accepting it.

One config entry is one Carrier account; every thermostat (system) on the account is added under it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from carrier_api import ApiConnectionGraphql, CarrierApiAuthError, CarrierApiError
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
import voluptuous as vol

from .const import DOMAIN

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))  # a masked password box
SCHEMA = vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): PASSWORD})
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD})


async def _check_login(username: str, password: str) -> dict[str, str]:
    """Try to sign in to Carrier. Returns the form errors: none if it worked (labels in translations/en.json)."""
    api = ApiConnectionGraphql(username, password)
    try:
        await api.login()
    except CarrierApiAuthError:
        return {"base": "invalid_auth"}
    except CarrierApiError:
        return {"base": "cannot_connect"}
    finally:
        await api.cleanup()  # this was only a test sign-in: close its connection
    return {}


class CarrierConfigFlow(ConfigFlow, domain=DOMAIN):
    """Adds a Carrier account to Home Assistant."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the Carrier app username and password, and check them before saving."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # The username (case-insensitive) identifies the account, so it can only be added once.
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            errors = await _check_login(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
            if not errors:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Started by Home Assistant when the coordinator reports that Carrier rejected the saved password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the new password, check it, save it and reload the integration."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _check_login(entry.data[CONF_USERNAME], user_input[CONF_PASSWORD])
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
        )
