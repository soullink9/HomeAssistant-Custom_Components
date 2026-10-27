"""The coordinator: one per Carrier account. It owns the cloud connection and all the data.

Data flow:
- Every FULL_REFRESH (5 minutes) it loads every system on the account from Carrier's cloud.
- In between, Carrier's websocket pushes changes; carrier_api patches the loaded System objects in
  place and the coordinator tells the entities to redraw.
- When Home Assistant changes a setting, the entity records the value it wrote with `expect()`, and
  `shown()` serves that value for EXPECT_SECONDS, because the cloud keeps replaying the old one for a
  while after a change.
"""

from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from carrier_api import ApiConnectionGraphql, CarrierApiAuthError, CarrierApiError, System, WebsocketDataUpdater
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, EXPECT_SECONDS, FULL_REFRESH, RECONNECT_FIRST, RECONNECT_MAX

_LOGGER = logging.getLogger(__name__)

# A config entry whose runtime_data is our coordinator (set in __init__.async_setup_entry).
type CarrierConfigEntry = ConfigEntry[CarrierCoordinator]


class _HideSecrets(logging.Filter):
    """Keep the Carrier password and access tokens out of the log.

    The gql library (used by carrier_api) logs whole request and response bodies at debug level. The
    sign-in request contains the password and its reply the tokens, so those lines are dropped.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False (drop the line) when it carries a secret."""
        text = str(record.args)
        return not any(secret in text for secret in ("password", "access_token", "refresh_token"))


logging.getLogger("gql.transport.aiohttp").addFilter(_HideSecrets())


class CarrierCoordinator(DataUpdateCoordinator[dict[str, System]]):
    """Loads every Carrier system on the account; data is {system serial: carrier_api System}."""

    def __init__(self, hass: HomeAssistant, entry: CarrierConfigEntry) -> None:
        """Create the cloud connection for this account (nothing is sent until the first refresh)."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=FULL_REFRESH)
        self.api = ApiConnectionGraphql(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
        # Applies websocket messages to the System objects; given the systems after each full load.
        self.updater = WebsocketDataUpdater([])
        # (serial, zone id or None, field) -> (value we wrote, monotonic time it stops overriding).
        self._expected: dict[tuple, tuple[Any, float]] = {}

    # --- values just written by Home Assistant ----------------------------------------------------

    def expect(self, key: tuple, value: Any) -> None:
        """Remember a value Home Assistant just wrote, so it is shown instead of the cloud's stale one."""
        self._expected[key] = (value, monotonic() + EXPECT_SECONDS)

    def shown(self, key: tuple, actual: Any) -> Any:
        """Return the value to display: a recent write if there is one, otherwise what Carrier reports."""
        hit = self._expected.get(key)
        if hit is None or monotonic() > hit[1]:
            self._expected.pop(key, None)  # expired (or never set): the cloud is authoritative again
            return actual
        return hit[0]

    # --- full refresh ------------------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, System]:
        """Load everything from Carrier, signing in again (once) if the saved session has expired."""
        try:
            if self.api.refresh_token is not None:
                try:
                    return await self._fetch()
                except CarrierApiAuthError:
                    # The saved session expired or was revoked: sign in again with the password, once.
                    self.api.refresh_token = None
            return await self._fetch()
        except CarrierApiAuthError as err:
            # The password itself is wrong now. Stop here (repeated sign-ins could lock the Carrier
            # account) and let Home Assistant ask for the new password (config_flow reauth step).
            raise ConfigEntryAuthFailed("Carrier rejected the saved password") from err
        except (CarrierApiError, TimeoutError, KeyError, ValueError) as err:
            # KeyError/ValueError: Carrier sent data carrier_api could not parse (for example a new
            # preset name). Entities go unavailable until a later refresh parses again.
            raise UpdateFailed(f"Carrier cloud error: {err}") from err

    async def _fetch(self) -> dict[str, System]:
        """One full load of every system (signs in first if needed; carrier_api handles that)."""
        systems = await self.api.load_data()
        self.updater.systems = systems
        return {system.profile.serial: system for system in systems}

    # --- websocket (pushed changes) ----------------------------------------------------------------

    async def _on_message(self, message: str) -> None:
        """Apply one websocket message to the loaded systems, then redraw the entities."""
        try:
            await self.updater.message_handler(message)  # patches the System objects in place
        except Exception:  # noqa: BLE001 - one bad message must never take down the socket
            _LOGGER.debug("Ignored websocket message: %s", message, exc_info=True)
            return
        self.async_update_listeners()

    async def websocket_loop(self) -> None:
        """Keep Carrier's websocket open for as long as the integration is loaded.

        Runs as a config-entry background task, so Home Assistant cancels it on unload. While the
        socket keeps failing it backs off from RECONNECT_FIRST up to RECONNECT_MAX seconds.
        """
        socket = self.api.api_websocket  # created by carrier_api when it signed in (first refresh)
        socket.callback_add(self._on_message)
        delay = RECONNECT_FIRST
        while True:
            if isinstance(self.last_exception, ConfigEntryAuthFailed):
                await asyncio.sleep(RECONNECT_MAX)  # waiting for the user to enter the new password
                continue
            started = monotonic()
            try:
                await socket.listener()  # returns (or raises) when the connection closes
            except Exception as err:  # noqa: BLE001
                # Message only: a full traceback can contain the access token (it is in the URL).
                _LOGGER.debug("Carrier websocket dropped: %s: %s", type(err).__name__, err)
            if monotonic() - started > 300:
                delay = RECONNECT_FIRST  # it had been connected a while: reconnect promptly
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX)
