"""Update entities: one per app, plus one for TrueNAS itself.

Home Assistant lists these under Settings > Updates, so pending updates are easy to spot.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrueNASConfigEntry, TrueNASCoordinator
from .entity import AppEntity, SystemEntity, add_per_item


async def async_setup_entry(
    hass: HomeAssistant, entry: TrueNASConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add an update entity per app and one for the TrueNAS system."""
    add_per_item(entry, async_add_entities, AppUpdate)
    async_add_entities([SystemUpdate(entry.runtime_data)])


class AppUpdate(AppEntity, UpdateEntity):
    """An app's update. The Install button upgrades the app through TrueNAS."""

    _attr_name = None  # named after the device (the app)
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, coordinator: TrueNASCoordinator, app: str) -> None:
        """Create the update entity for ``app``."""
        super().__init__(coordinator, app, "update")
        self._attr_title = app

    @property
    def entity_picture(self) -> str | None:
        """The app's own icon from TrueNAS (None if it has none)."""
        return (self.app.get("metadata") or {}).get("icon")

    @property
    def installed_version(self) -> str | None:
        """The version running now."""
        return self.app.get("version")

    @property
    def latest_version(self) -> str | None:
        """The newest version; equal to the installed one when there is no update.

        Home Assistant shows "update available" whenever the two differ, so when TrueNAS
        flags an update but names no version we still return a different placeholder.
        """
        app = self.app
        if not app.get("upgrade_available"):
            return app.get("version")
        return app.get("latest_version") or app.get("latest_app_version") or "update available"

    @property
    def in_progress(self) -> bool:
        """True while any action (including this upgrade) is running for the app."""
        return self._app in self.coordinator.busy

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Upgrade the app. Runs in the background until TrueNAS finishes the job."""
        self.coordinator.app_action(self._app, "upgrade")


class SystemUpdate(SystemEntity, UpdateEntity):
    """The TrueNAS operating system. Shows when an update exists but never installs one."""

    _attr_name = None  # named after the device ("TrueNAS")
    _attr_title = "TrueNAS"
    _attr_supported_features = UpdateEntityFeature.INSTALL  # kept only so the button can explain itself

    def __init__(self, coordinator: TrueNASCoordinator) -> None:
        """Create the system update entity."""
        super().__init__(coordinator, "system_update")

    @property
    def _new(self) -> dict:
        """The 'new_version' part of update.status (empty when up to date)."""
        status = (self.coordinator.data["update"] or {}).get("status") or {}
        return status.get("new_version") or {}

    @property
    def available(self) -> bool:
        """Unavailable if the API key may not read update.status."""
        return super().available and self.coordinator.data["update"] is not None

    @property
    def installed_version(self) -> str:
        """The running TrueNAS version, e.g. 25.10.7."""
        return self.coordinator.data["version"]

    @property
    def latest_version(self) -> str:
        """The newer version if there is one, otherwise the installed version."""
        return self._new.get("version") or self.installed_version

    @property
    def release_url(self) -> str | None:
        """Link to the release notes of the new version."""
        return self._new.get("release_notes_url")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """System details (same as TrueNAS's System Information card) for dashboards to read."""
        data = self.coordinator.data
        info = data["info"]
        if not info:  # the API key can't read system info
            return {}
        return {
            "hostname": info.get("hostname"),
            "platform": "TrueNAS hardware" if data["ix"] else "Generic",
            "edition": "Enterprise" if info.get("license") else "Community",
            "version_name": info.get("codename"),
        }

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Deliberately refuse: a system update should be run from TrueNAS after a backup."""
        raise HomeAssistantError(
            "TrueNAS can't be updated from Home Assistant. Save your configuration and "
            "take a backup, then run the update from the TrueNAS web UI (System > Update)."
        )
