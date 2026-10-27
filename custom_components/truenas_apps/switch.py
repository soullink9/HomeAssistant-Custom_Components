"""The on/off switch for each app."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrueNASConfigEntry, TrueNASCoordinator
from .entity import AppEntity, add_per_item


async def async_setup_entry(
    hass: HomeAssistant, entry: TrueNASConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add one switch per app."""
    add_per_item(entry, async_add_entities, AppSwitch)


class AppSwitch(AppEntity, SwitchEntity):
    """On while the app is running (or starting up); turning it off stops the app."""

    _attr_name = None  # no extra name: the entity is named after the device (the app)

    def __init__(self, coordinator: TrueNASCoordinator, app: str) -> None:
        """Create the switch for ``app``."""
        super().__init__(coordinator, app, "switch")

    @property
    def is_on(self) -> bool:
        """DEPLOYING counts as on so the switch doesn't flicker while an app starts."""
        return self.app.get("state") in ("RUNNING", "DEPLOYING")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the app (runs in the background; raises if another action is still running)."""
        self.coordinator.app_action(self._app, "start")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the app (runs in the background)."""
        self.coordinator.app_action(self._app, "stop")
