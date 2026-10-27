"""Sensors: the status of each app and how full each storage pool is."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import TrueNASConfigEntry, TrueNASCoordinator
from .entity import AppEntity, SystemEntity, add_per_item


async def async_setup_entry(
    hass: HomeAssistant, entry: TrueNASConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add a status sensor per app and a usage sensor per pool."""
    add_per_item(entry, async_add_entities, AppStatus)
    add_per_item(entry, async_add_entities, PoolUsage, "pools")


class AppStatus(AppEntity, SensorEntity):
    """The app's state as text: running, stopped, crashed, deploying or stopping."""

    _attr_name = "Status"

    def __init__(self, coordinator: TrueNASCoordinator, app: str) -> None:
        """Create the status sensor for ``app``."""
        super().__init__(coordinator, app, "status")

    @property
    def native_value(self) -> str:
        """TrueNAS reports e.g. "RUNNING"; Home Assistant states are lower case."""
        return self.app.get("state", "unknown").lower()


class PoolUsage(SystemEntity, SensorEntity):
    """Percent of a storage pool that is used."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: TrueNASCoordinator, pool: str) -> None:
        """Create the usage sensor for ``pool``."""
        super().__init__(coordinator, f"pool_{pool}")
        self._pool = pool
        self._attr_name = f"{pool} usage"

    @property
    def available(self) -> bool:
        """Unavailable while polling fails or after the pool was removed."""
        return super().available and self._pool in self.coordinator.data["pools"]

    @property
    def native_value(self) -> float | None:
        """Allocated space as a percentage of the pool size (None if TrueNAS gave no numbers)."""
        pool = self.coordinator.data["pools"][self._pool]
        size, used = pool.get("size"), pool.get("allocated")
        return round(used / size * 100, 1) if size and used is not None else None
