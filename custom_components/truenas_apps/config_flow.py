"""The setup form: first-time setup, reconfigure, and re-authentication share one form."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_VERIFY_SSL
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType
import voluptuous as vol

from .api import rpc
from .const import DOMAIN

SCHEMA = vol.Schema(
    {
        # Bare hostname or IP (optionally :port) only. No scheme, path, "?" or "user@",
        # so the websocket URL we build from it can't be bent to point somewhere else.
        vol.Required(CONF_HOST): vol.All(str, vol.Strip, vol.Match(r"^[A-Za-z0-9.\-:\[\]]+$")),
        vol.Required(CONF_API_KEY): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
        # Off by default because TrueNAS ships with a self-signed certificate.
        vol.Required(CONF_VERIFY_SSL, default=False): bool,
    }
)


class TrueNASConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for host, API key and SSL choice, and check that they work before saving."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First-time setup (Settings > Devices & services > Add integration)."""
        return await self._async_form("user", user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change host, API key or SSL verification of an existing entry."""
        return await self._async_form("reconfigure", user_input, self._get_reconfigure_entry())

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Home Assistant starts this when TrueNAS rejects the stored API key."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the new key."""
        return await self._async_form("reauth_confirm", user_input, self._get_reauth_entry())

    async def _async_form(
        self, step_id: str, user_input: dict[str, Any] | None, entry: ConfigEntry | None = None
    ) -> ConfigFlowResult:
        """Show the form; when submitted, test the login and then create or update the entry."""
        errors = {}
        if user_input:
            if entry is None:  # new setup: refuse a TrueNAS that is already added
                self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            try:
                await rpc(self.hass, user_input, "app.query")  # needs a key allowed to read apps
            except PermissionError:
                errors["base"] = "invalid_auth"
            except (ClientError, TimeoutError, RuntimeError):
                errors["base"] = "cannot_connect"
            else:
                if entry:
                    return self.async_update_reload_and_abort(entry, data_updates=user_input)
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)
        # Pre-fill with what was just typed, or with the saved settings when editing.
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or (entry.data if entry else None)),
            errors=errors,
        )
