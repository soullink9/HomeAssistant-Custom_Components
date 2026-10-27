"""The coordinator: polls TrueNAS once a minute and runs app actions in the background."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from aiohttp import ClientError
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import connect, optional
from .const import DOMAIN, JOB_CHECK_INTERVAL, JOB_TIMEOUT, POLL_INTERVAL, POLL_TIMEOUT

_LOGGER = logging.getLogger(__name__)

# The config entry carries its coordinator in ``entry.runtime_data``.
type TrueNASConfigEntry = ConfigEntry[TrueNASCoordinator]


class TrueNASCoordinator(DataUpdateCoordinator[dict]):
    """Holds the latest TrueNAS data that every entity reads from.

    ``data`` is a dict with these keys:
      apps     {app name: app.query record}
      pools    {pool name: pool.query record}
      version  short TrueNAS version, e.g. "25.10.7"
      update   update.status result, or None if the API key may not read it
      info     dashboard system info (hostname, codename, license), or None
      ix       True on iXsystems hardware, or None if unknown
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up polling. ``busy`` lists apps with an action still running."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=POLL_INTERVAL)
        )
        self.busy: set[str] = set()

    async def _async_update_data(self) -> dict:
        """Fetch everything in one short connection (called by Home Assistant every minute)."""
        try:
            async with asyncio.timeout(POLL_TIMEOUT), connect(self.hass, self.config_entry.data) as call:
                # These three are required: if they fail, the poll fails.
                apps = await call("app.query")
                pools = await call("pool.query")
                version = await call("system.version_short")
                # These are nice-to-have: a limited API key just loses the matching entities.
                update = await optional(call, "update.status")
                info = await optional(call, "webui.main.dashboard.sys_info")
                ix = await optional(call, "truenas.is_ix_hardware")
        except PermissionError as err:  # bad or revoked key: stop polling and ask the user for a new one
            raise ConfigEntryAuthFailed(err) from err
        except (ClientError, TimeoutError, RuntimeError) as err:  # unreachable, slow or erroring: retry next poll
            raise UpdateFailed(err) from err
        return {
            "apps": {a["name"]: a for a in apps},
            "pools": {p["name"]: p for p in pools},
            "version": version,
            "update": update,
            "info": info,
            "ix": ix,
        }

    @callback
    def app_action(self, app: str, *methods: str) -> None:
        """Start ``app.<method>`` jobs one after another in the background (one action per app at a time)."""
        if app in self.busy:
            raise HomeAssistantError(f"{app}: another action is still running")
        self.busy.add(app)
        self.async_update_listeners()  # entities show "in progress" straight away
        self.config_entry.async_create_background_task(self.hass, self._run(app, methods), f"{DOMAIN}_{app}")

    async def _run(self, app: str, methods: tuple[str, ...]) -> None:
        """Run each job and keep the connection open until TrueNAS reports it finished."""
        error = None
        try:
            async with asyncio.timeout(JOB_TIMEOUT), connect(self.hass, self.config_entry.data) as call:
                for method in methods:
                    # app.upgrade takes an options dict ({} = latest version, default settings).
                    job = await call(f"app.{method}", [app, {}] if method == "upgrade" else [app])
                    await self.async_refresh()  # show the in-progress state
                    while True:
                        # A job record that was already pruned counts as finished.
                        (j,) = await call("core.get_jobs", [[["id", "=", job]]]) or [{"state": "SUCCESS"}]
                        if j["state"] not in ("WAITING", "RUNNING"):
                            break
                        await asyncio.sleep(JOB_CHECK_INTERVAL)
                    if j["state"] != "SUCCESS":
                        raise RuntimeError(f"{j['state']} {j.get('error')}")
        except (ClientError, TimeoutError, RuntimeError, PermissionError) as err:
            error = f"app.{'+'.join(methods)} on {app} failed: {err or type(err).__name__}"
            _LOGGER.error(error)
        finally:
            self.busy.discard(app)  # always release the app, whatever happened
        # Background work can't raise to the user, so report through a notification instead.
        notification_id = f"{DOMAIN}_{app}"
        if error:
            persistent_notification.async_create(
                self.hass, error, title="TrueNAS Apps", notification_id=notification_id
            )
        else:
            persistent_notification.async_dismiss(self.hass, notification_id)
        await self.async_refresh()
