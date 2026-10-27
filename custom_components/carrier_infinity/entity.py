"""The base class every entity shares: one Home Assistant device per Carrier system (thermostat)."""

from __future__ import annotations

from carrier_api import System
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CarrierCoordinator


class CarrierEntity(CoordinatorEntity[CarrierCoordinator]):
    """An entity that belongs to one Carrier system, identified by the system's serial number."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CarrierCoordinator, serial: str) -> None:
        """Attach to the system with this serial and describe its device."""
        super().__init__(coordinator)
        self._serial = serial
        self._last_system = coordinator.data[serial]
        profile = self._system.profile
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=profile.name or "Carrier",
            manufacturer=profile.brand or "Carrier",
            model=profile.model,
            serial_number=serial,
            sw_version=profile.firmware,
        )

    @property
    def _system(self) -> System:
        """The latest data for this system, or the last known copy if Carrier briefly stops listing it."""
        if (system := self.coordinator.data.get(self._serial)) is not None:
            self._last_system = system
        return self._last_system

    @property
    def available(self) -> bool:
        """Available while Carrier lists the system and the thermostat is online with Carrier."""
        return super().available and self._serial in self.coordinator.data and not self._system.status.is_disconnected
