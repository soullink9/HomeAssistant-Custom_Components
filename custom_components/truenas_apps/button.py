"""Buttons: restart an app, or force-recreate it."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrueNASConfigEntry, TrueNASCoordinator
from .entity import AppEntity, add_per_item

# key: (display name, device class, the TrueNAS app.* methods to run, in order)
BUTTONS = {
    "restart": ("Restart", ButtonDeviceClass.RESTART, ("stop", "start")),
    "recreate": ("Force recreate", None, ("redeploy",)),  # redeploy rebuilds the containers
}


async def async_setup_entry(
    hass: HomeAssistant, entry: TrueNASConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add every button in ``BUTTONS`` for every app."""
    for key in BUTTONS:
        add_per_item(entry, async_add_entities, lambda coordinator, app, key=key: AppButton(coordinator, app, key))


class AppButton(AppEntity, ButtonEntity):
    """One action button for one app."""

    def __init__(self, coordinator: TrueNASCoordinator, app: str, key: str) -> None:
        """Create the ``key`` button (see ``BUTTONS``) for ``app``."""
        super().__init__(coordinator, app, key)
        self._attr_name, self._attr_device_class, self._methods = BUTTONS[key]

    async def async_press(self) -> None:
        """Run the button's job(s) in the background."""
        methods = self._methods
        if methods[0] == "stop" and self.app.get("state") == "STOPPED":
            methods = methods[1:]  # "restarting" a stopped app is just a start
        self.coordinator.app_action(self._app, *methods)
