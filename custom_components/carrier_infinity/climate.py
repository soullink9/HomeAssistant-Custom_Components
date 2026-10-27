"""One climate entity per Carrier zone.

How Carrier's model maps onto Home Assistant's:
- The system mode (heat, cool, auto, fan only, off) is shared by every zone: changing it on one zone
  changes it on all of them, exactly as on the wall control.
- Each zone runs an "activity" (home, away, sleep, wake, manual, vacation), each with its own heat and
  cool setpoints and fan speed. Home Assistant shows the activity as the preset.
- Setting a temperature writes the zone's "manual" activity and holds it indefinitely, like changing
  the temperature on the wall control. The "Resume schedule" preset drops the hold.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import copy
from functools import partial
from typing import Any

from carrier_api import (
    ActivityTypes,
    CarrierApiError,
    ConfigZone,
    ConfigZoneActivity,
    FanModes,
    StatusZone,
    SystemModes,
    TemperatureUnits,
)
from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CarrierConfigEntry, CarrierCoordinator
from .entity import CarrierEntity

# Carrier system mode -> Home Assistant HVAC mode.
MODES = {
    SystemModes.OFF: HVACMode.OFF,
    SystemModes.HEAT: HVACMode.HEAT,
    SystemModes.COOL: HVACMode.COOL,
    SystemModes.AUTO: HVACMode.HEAT_COOL,
    SystemModes.FAN_ONLY: HVACMode.FAN_ONLY,
}
# Carrier fan speed -> Home Assistant fan mode. Carrier's "off" means the fan runs only when needed.
FANS = {FanModes.OFF: "auto", FanModes.LOW: "low", FanModes.MED: "medium", FanModes.HIGH: "high"}
# Extra preset (not a Carrier activity) that drops any hold and returns the zone to its schedule.
RESUME = "resume"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarrierConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a climate entity for every enabled zone of every system on the account."""
    coordinator = entry.runtime_data
    async_add_entities(
        CarrierZone(coordinator, serial, zone.api_id)
        for serial, system in coordinator.data.items()
        for zone in system.config.zones
    )


class CarrierZone(CarrierEntity, ClimateEntity):
    """A single Carrier zone as a Home Assistant thermostat."""

    _attr_translation_key = "zone"  # for the preset names in translations/en.json
    _attr_fan_modes = list(FANS.values())

    def __init__(self, coordinator: CarrierCoordinator, serial: str, zone_id: str) -> None:
        """Build the entity, offering only the modes this system's equipment supports."""
        self._zone_id = zone_id
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_{zone_id}"
        self._attr_name = self._config_zone.name  # the zone's name from the thermostat
        caps = self._system.supported_hvac_capabilities()  # from carrier_api: heat / cool / fan
        features = (
            ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.PRESET_MODE
        )
        modes = [HVACMode.OFF]
        if caps["heat"]:
            modes.append(HVACMode.HEAT)
        if caps["cool"]:
            modes.append(HVACMode.COOL)
        if caps["heat"] and caps["cool"]:
            modes.append(HVACMode.HEAT_COOL)
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if caps["fan"]:
            modes.append(HVACMode.FAN_ONLY)
            features |= ClimateEntityFeature.FAN_MODE
        self._attr_hvac_modes = modes
        self._attr_supported_features = features
        self._attr_preset_modes = [a.type.value for a in self._config_zone.activities] + [RESUME]

    # --- where the data comes from -----------------------------------------------------------------
    # Carrier splits a zone in two: its configuration (activities, setpoints, schedule, hold) and its
    # status (temperature, humidity, what it is doing right now).

    @property
    def _config_zone(self) -> ConfigZone | None:
        """This zone's configuration."""
        return next((z for z in self._system.config.zones if z.api_id == self._zone_id), None)

    @property
    def _status_zone(self) -> StatusZone | None:
        """This zone's live status."""
        return next((z for z in self._system.status.zones if z.api_id == self._zone_id), None)

    def _shown(self, name: str, actual: Any, zone: bool = True) -> Any:
        """The value to display for a field: a value Home Assistant just wrote, else Carrier's."""
        key = (self._serial, self._zone_id if zone else None, name)  # the mode is system-wide: no zone
        return self.coordinator.shown(key, actual)

    @property
    def _activity(self) -> ConfigZoneActivity | StatusZone:
        """The activity the zone is running. Its setpoints come from the configuration, which Carrier
        updates sooner than the status after a change; the status is the fallback."""
        activity = self._config_zone.find_activity(ActivityTypes(self.preset_mode))
        return activity or self._status_zone

    @property
    def available(self) -> bool:
        """Unavailable if Carrier stops reporting this zone (for example after re-zoning)."""
        return super().available and self._config_zone is not None and self._status_zone is not None

    # --- state shown in Home Assistant -------------------------------------------------------------

    @property
    def temperature_unit(self) -> str:
        """The unit the thermostat is set to display; Home Assistant converts if yours differs."""
        if self._system.status.temperature_unit == TemperatureUnits.CELSIUS:
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def target_temperature_step(self) -> float:
        """Carrier accepts whole degrees Fahrenheit, or half degrees Celsius."""
        return 0.5 if self.temperature_unit == UnitOfTemperature.CELSIUS else 1.0

    @property
    def current_temperature(self) -> float | None:
        """Room temperature measured by the zone's sensor."""
        return self._status_zone.temperature

    @property
    def current_humidity(self) -> float | None:
        """Room humidity measured by the zone's sensor."""
        return self._status_zone.humidity

    @property
    def hvac_mode(self) -> HVACMode | None:
        """The system mode (shared by all zones); None if Carrier reports one we don't know."""
        try:
            actual = MODES[SystemModes(self._system.config.mode)]
        except KeyError, ValueError:
            actual = None
        return self._shown("mode", actual, zone=False)

    @property
    def hvac_action(self) -> HVACAction | None:
        """What the zone is doing right now, from Carrier's zone conditioning status."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        conditioning = self._status_zone.conditioning or ""  # e.g. "active_heat", "idle"
        if conditioning.startswith("active_heat"):
            return HVACAction.HEATING
        if conditioning.startswith("active_cool"):
            return HVACAction.COOLING
        return HVACAction.IDLE if self.fan_mode == "auto" else HVACAction.FAN

    @property
    def _heat(self) -> float | None:
        """Heat setpoint of the running activity."""
        return self._shown("heat", self._activity.heat_set_point)

    @property
    def _cool(self) -> float | None:
        """Cool setpoint of the running activity."""
        return self._shown("cool", self._activity.cool_set_point)

    @property
    def target_temperature(self) -> float | None:
        """Single target in heat or cool mode (heat_cool uses the low/high pair below)."""
        if self.hvac_mode == HVACMode.HEAT:
            return self._heat
        if self.hvac_mode == HVACMode.COOL:
            return self._cool
        return None

    @property
    def target_temperature_low(self) -> float | None:
        """Heat setpoint, in heat_cool (auto) mode."""
        return self._heat if self.hvac_mode == HVACMode.HEAT_COOL else None

    @property
    def target_temperature_high(self) -> float | None:
        """Cool setpoint, in heat_cool (auto) mode."""
        return self._cool if self.hvac_mode == HVACMode.HEAT_COOL else None

    @property
    def fan_mode(self) -> str | None:
        """Fan speed of the running activity."""
        return self._shown("fan", FANS.get(self._activity.fan))

    @property
    def preset_mode(self) -> str | None:
        """The running activity (home, away, sleep, wake, manual or vacation)."""
        return self._shown("preset", self._status_zone.current_status_activity_type.value)

    # --- changes from Home Assistant ---------------------------------------------------------------

    async def _run(self, expect: dict[str, Any], *calls: Callable[[], Awaitable[Any]]) -> None:
        """Send one or more changes to Carrier, then show the result straight away.

        `expect` holds the values the change produces (field name -> value). They are shown for a few
        minutes instead of re-reading the cloud, which keeps serving the old values for a while.
        """
        try:
            for call in calls:
                await call()
        except CarrierApiError as err:
            raise HomeAssistantError(f"Carrier cloud rejected the change: {err}") from err
        for name, value in expect.items():
            zone = None if name == "mode" else self._zone_id
            self.coordinator.expect((self._serial, zone, name), value)
        self.coordinator.async_update_listeners()

    @staticmethod
    def _expect_activity(activity: ConfigZoneActivity) -> dict[str, Any]:
        """The values a zone shows once it switches to this activity."""
        return {
            "preset": activity.type.value,
            "heat": activity.heat_set_point,
            "cool": activity.cool_set_point,
            "fan": FANS.get(activity.fan),
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Change the system mode (applies to every zone)."""
        mode = next(k for k, v in MODES.items() if v == hvac_mode)
        await self._run({"mode": hvac_mode}, partial(self.coordinator.api.set_config_mode, self._serial, mode))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Change the fan speed of the activity the zone is running."""
        fan = next(k for k, v in FANS.items() if v == fan_mode)
        activity = self._config_zone.find_activity(ActivityTypes(self.preset_mode))
        if activity is None:
            raise HomeAssistantError("Current activity unknown, try again shortly")
        await self._run(
            {"fan": fan_mode},
            partial(self.coordinator.api.update_fan, self._serial, self._zone_id, activity.type, fan),
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Hold the zone on an activity indefinitely, or (RESUME) return it to its schedule."""
        api, zone = self.coordinator.api, self._config_zone
        if preset_mode == RESUME:
            # Work out which activity the schedule resumes, on a copy without the hold (the live data
            # stays as Carrier reported it until Carrier confirms the change).
            unheld = copy.copy(zone)
            unheld.hold = False
            activity = unheld.current_scheduled_activity()
            expect = self._expect_activity(activity) if activity else {}
            await self._run(expect, partial(api.resume_schedule, self._serial, self._zone_id))
            return
        activity = zone.find_activity(ActivityTypes(preset_mode))
        expect = self._expect_activity(activity) if activity else {"preset": preset_mode}
        await self._run(
            expect,
            partial(api.set_config_hold, self._serial, self._zone_id, ActivityTypes(preset_mode)),
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write the setpoints to the zone's manual activity and hold it indefinitely, like the wall unit.

        Carrier always stores both setpoints, so the one not being changed keeps its current value.
        """
        manual = self._config_zone.find_activity(ActivityTypes.MANUAL)
        if manual is None:
            raise HomeAssistantError("This zone has no manual activity")
        heat = kwargs.get(ATTR_TARGET_TEMP_LOW, self._heat)
        cool = kwargs.get(ATTR_TARGET_TEMP_HIGH, self._cool)
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            if self.hvac_mode == HVACMode.COOL:
                cool = temp
            else:
                heat = temp
        api = self.coordinator.api
        await self._run(
            {"preset": ActivityTypes.MANUAL.value, "heat": heat, "cool": cool},
            partial(api.set_config_manual_activity, self._serial, self._zone_id, str(heat), str(cool), manual.fan),
            partial(api.set_config_hold, self._serial, self._zone_id, ActivityTypes.MANUAL),
        )
