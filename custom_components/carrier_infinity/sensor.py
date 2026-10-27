"""Sensors for each Carrier system: the outdoor temperature, and a lifetime electricity meter.

The electricity meter is the only part of the integration that keeps its own state, because Carrier only
reports energy per calendar year:

- year1: electricity used so far this year. Carrier restarts it at New Year.
- year2: last year's final total.

The meter keeps a running lifetime total that only ever goes up. Each reading it adds whatever year1 grew by.
When Carrier starts a new year it adds the new year1, and once Carrier publishes year2 it adds the last part of
the old year it had not seen yet (the "tail": from the last year1 it read to the year's final total).

Carrier's data is not always tidy, and the New Year handling allows for what it does in practice (all checked by
tests/sim_energy.py over many simulated years):
- A single bad reading (zeros, a small dip, a junk year2) must never add or skip a year, so every New Year signal
  has to show up on two readings in a row, and year2 is only trusted when it is the same on two readings.
- Carrier may publish its New Year late (hours or days), may start it at UTC midnight (Dec 31 evening here),
  and may briefly keep showing the year before last as year2. So the meter tracks which Carrier year it is
  counting, and waits for a year2 that has actually changed before finishing the old year.
- Home Assistant may be off across New Year (even for over a year), so the calendar says when a New Year must
  have passed even if year1 has already grown back.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from carrier_api import EnergyPeriod, EnergyUsageMetric, TemperatureUnits
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoredExtraData, RestoreEntity
from homeassistant.util import dt as dt_util

from .coordinator import CarrierConfigEntry, CarrierCoordinator
from .entity import CarrierEntity

# Every Carrier energy category except gas (gas is fuel burned, not electricity).
ELECTRIC = [m for m in EnergyUsageMetric if m is not EnergyUsageMetric.GAS]

# An outage longer than this (seconds) may have hidden a whole New Year from the meter.
WEEK = 7 * 86400


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the outdoor temperature and electricity sensors for every system on the account."""
    coordinator = entry.runtime_data
    for serial in coordinator.data:
        async_add_entities([OutdoorTemperature(coordinator, serial), Electricity(coordinator, serial)])


class OutdoorTemperature(CarrierEntity, SensorEntity):
    """Outdoor air temperature, as measured by the outdoor unit and reported by the thermostat."""

    _attr_translation_key = "outdoor_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: CarrierCoordinator, serial: str) -> None:
        """Create the sensor for the system with this serial."""
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_outdoor_temperature"

    @property
    def native_value(self) -> float | None:
        """The latest outdoor temperature."""
        return self._system.status.outdoor_temperature

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit the thermostat is set to display; Home Assistant converts if yours differs."""
        if self._system.status.temperature_unit == TemperatureUnits.CELSIUS:
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT


class Electricity(CarrierEntity, RestoreEntity, SensorEntity):
    """Lifetime electricity used by the whole system (kWh). Only ever counts up; never resets.

    Its state is saved by Home Assistant (restore state) and carried over restarts. See the module docstring for
    how Carrier's yearly figures are turned into one lifetime total.
    """

    _attr_translation_key = "electricity"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING  # never decreases, so HA's statistics stay simple
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    def __init__(self, coordinator: CarrierCoordinator, serial: str) -> None:
        """Create the meter for the system with this serial (its saved state is loaded when it is added)."""
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_electricity"
        # Saved across restarts (see extra_restore_state_data):
        self._total: float | None = None  # lifetime kWh shown in Home Assistant
        self._last: float | None = None  # highest year1 counted for Carrier year _year
        self._year: int | None = None  # the Carrier year that _last belongs to
        self._prior: float | None = None  # year2 as confirmed during that year
        self._tail_from: float | None = None  # the old year's year1 at New Year, while waiting for its year2
        self._seen: float | None = None  # when a reading was last counted (Unix timestamp)
        # Not saved (they only bridge two readings in a row):
        self._drop: float | None = None  # a New Year reading waiting for its confirming second reading
        self._y2_prev: float | None = None  # year2 on the previous reading

    @property
    def native_value(self) -> float | None:
        """The lifetime total, or unknown until the first reading."""
        return None if self._total is None else round(self._total, 3)

    @property
    def extra_restore_state_data(self) -> RestoredExtraData:
        """What Home Assistant saves for this sensor. Add new keys freely; never rename one (see CONTRIBUTING)."""
        keys = ("total", "last", "year", "prior", "tail_from", "seen")
        return RestoredExtraData({k: getattr(self, f"_{k}") for k in keys})

    async def async_added_to_hass(self) -> None:
        """Load the saved state (if any), then count the current reading."""
        await super().async_added_to_hass()
        if (saved := await self.async_get_last_extra_data()) is not None:
            data = saved.as_dict()
            self._total, self._last, self._prior = data.get("total"), data.get("last"), data.get("prior")
            self._seen, self._tail_from = data.get("seen"), data.get("tail_from")
            if (year := data.get("year")) is None:
                # Saved by a pre-release version that did not store the year: work it out from when the last
                # reading was taken ("rolled" was that version's record of the last New Year it counted).
                seen = dt_util.as_local(dt_util.utc_from_timestamp(self._seen or dt_util.now().timestamp()))
                year = _carrier_year(seen)
                if data.get("rolled") != year and _early_january(seen, year):
                    year -= 1  # that New Year had not been counted yet
            self._year = year
        self._accumulate()

    def _handle_coordinator_update(self) -> None:
        """Count each new reading before the state is written (called by the coordinator on every update)."""
        self._accumulate()
        super()._handle_coordinator_update()

    def _kwh(self, period: EnergyPeriod) -> float | None:
        """Total electricity (kWh) Carrier reports for one period (year1 or year2), or None if it sent none."""
        if self._serial not in self.coordinator.data:
            return None
        measurement = self._system.energy.measurement_for_period(period)
        if measurement is None:
            return None
        values = [v for m in ELECTRIC if (v := measurement.value_for_metric(m)) is not None]
        return sum(values) if values else None

    def _accumulate(self) -> None:
        """Add whatever Carrier's figures say was used since the last reading."""
        ytd, y2 = self._kwh(EnergyPeriod.YEAR_1), self._kwh(EnergyPeriod.YEAR_2)
        if ytd is None:
            return  # nothing usable this time: wait for the next reading
        now = dt_util.now()
        ts, year = now.timestamp(), _carrier_year(now)
        y2_sure = y2 is not None and y2 == self._y2_prev  # the same on two readings: not a glitch
        self._y2_prev = y2

        if self._total is None or self._last is None or self._year is None:
            # The very first reading: the meter starts at this year's usage so far. In early January it may still
            # be last year's figure (Carrier publishes its New Year late), so a reset in the next two weeks still
            # counts as this New Year.
            self._total, self._last, self._prior, self._seen = ytd, ytd, y2, ts
            self._year = year - 1 if _early_january(now, year) else year
            return

        new_year = year > self._year and self._is_new_year(now, ts, year, ytd, y2)
        if new_year and (self._drop is None or ytd < self._drop):
            self._drop = ytd  # looks like a New Year: wait for a second reading to confirm it
            return
        if new_year:
            # Confirmed: count all of the new year1. The old year is finished off below once Carrier publishes its
            # final total. If 2+ New Years were missed, only the latest full year is still known (from year2).
            self._tail_from = self._last if year - self._year == 1 else 0.0
            self._total += ytd
            self._last, self._year = ytd, year
        elif ytd > self._last:
            self._total += ytd - self._last  # normal growth
            self._last = ytd
            if self._year < year and not _early_january(now, year):
                self._year = year  # Carrier never reset this year: just keep counting
        # Anything else is a dip or a bad reading from Carrier: ignore it (the high-water mark stays).
        self._drop, self._seen = None, ts

        # Finish the old year once Carrier publishes its final total: a confirmed year2 that is at least about what
        # year1 had reached and, in early January (when Carrier may still show the year before), different from the
        # year2 seen during the old year.
        if not y2_sure:
            return
        if self._tail_from is None:
            self._prior = y2  # no New Year pending: just follow Carrier's revisions of last year's total
        elif (y2 != self._prior or not _early_january(now, year)) and y2 >= 0.9 * self._tail_from:
            self._total += max(y2 - self._tail_from, 0)  # never negative if Carrier trimmed the year slightly
            self._tail_from, self._prior = None, y2

    def _is_new_year(self, now: datetime, ts: float, year: int, ytd: float, y2: float | None) -> bool:
        """Is this reading from a Carrier year after the one counted so far? (The calendar already says it can be.)"""
        if ytd < self._last / 2:
            return True  # year1 restarted
        if ts - (self._seen or ts) < WEEK:
            return False  # still last year's numbers: Carrier publishes its New Year late
        # Home Assistant (or Carrier) was away across New Year, so year1 may have grown back already.
        if y2 is not None and y2 != self._prior:
            return True  # Carrier has moved last year into year2
        return not _early_january(now, year)  # by mid-January Carrier has always reset


def _carrier_year(now: datetime) -> int:
    """The calendar year, allowing for Carrier starting its year at UTC midnight (the evening of Dec 31 in the US)."""
    return (now + timedelta(hours=6)).year


def _early_january(now: datetime, year: int) -> bool:
    """Before Jan 15: Carrier may not have published its New Year yet, so a reset may still be on its way."""
    return now < datetime(year, 1, 15, tzinfo=now.tzinfo)
