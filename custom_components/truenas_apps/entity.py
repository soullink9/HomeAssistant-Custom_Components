"""Base classes shared by the entity platforms."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TrueNASConfigEntry, TrueNASCoordinator


class SystemEntity(CoordinatorEntity[TrueNASCoordinator]):
    """An entity on the main "TrueNAS" device (pool usage, the system update)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TrueNASCoordinator, suffix: str) -> None:
        """``suffix`` keeps the unique id different for each kind of entity."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)}, name="TrueNAS", manufacturer="TrueNAS")


class AppEntity(CoordinatorEntity[TrueNASCoordinator]):
    """An entity belonging to one app. Each app becomes its own Home Assistant device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TrueNASCoordinator, app: str, suffix: str) -> None:
        """``app`` is the TrueNAS app name; ``suffix`` keeps unique ids apart per entity kind."""
        super().__init__(coordinator)
        self._app = app
        device_id = f"{coordinator.config_entry.entry_id}_{app}"
        self._attr_unique_id = f"{device_id}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_id)}, name=app, manufacturer="TrueNAS")

    @property
    def app(self) -> dict:
        """The latest app.query record for this app."""
        return self.coordinator.data["apps"][self._app]

    @property
    def available(self) -> bool:
        """Unavailable while the poll is failing or after the app was removed from TrueNAS."""
        return super().available and self._app in self.coordinator.data["apps"]


def add_per_item(
    entry: TrueNASConfigEntry,
    async_add_entities: AddEntitiesCallback,
    factory: Callable[[TrueNASCoordinator, str], CoordinatorEntity],
    kind: str = "apps",
) -> None:
    """Create ``factory(coordinator, name)`` for every app (or pool) now and for any that show up later.

    ``kind`` is the key in the coordinator data to follow: "apps" or "pools".
    """
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = set(coordinator.data[kind]) - known
        known.update(new)
        async_add_entities([factory(coordinator, name) for name in new])

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))  # re-check after every poll
