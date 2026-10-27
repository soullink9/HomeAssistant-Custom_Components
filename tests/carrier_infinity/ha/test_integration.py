"""Integration test: the whole Home Assistant side (coordinator, climate, sensors, config flow, log filter) against
Home Assistant stand-ins (stubs.py) and recorded Carrier data (tests/carrier_infinity/fixtures). Nothing touches Carrier's cloud: the
coordinator is given a fake API that records what would have been sent.

Run: python3 tests/carrier_infinity/ha/test_integration.py      (needs carrier-api: pip install -r tests/carrier_infinity/requirements.txt)
"""

import asyncio
import copy
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import re
import sys
import types

sys.path.insert(0, str(Path(__file__).parent))  # for stubs.py

import stubs  # noqa: I001 - must come first: it installs the Home Assistant stand-ins
from stubs import NOW, REPO, SAVED, TZ, ConfigEntry, ConfigEntryAuthFailed, HVACAction, HVACMode
from stubs import HomeAssistantError, UpdateFailed, load_systems, message

from carrier_api import ActivityTypes, CarrierApiAuthError, CarrierApiGraphqlError, EnergyPeriod

import carrier_infinity  # noqa: F401 - the integration's own modules load cleanly
from carrier_infinity import climate, config_flow, coordinator as coord_mod, sensor
from carrier_infinity.const import DOMAIN, EXPECT_SECONDS

RESULTS = {"pass": 0, "fail": 0}


def check(name, ok, detail=""):
    """Record one check and print it."""
    RESULTS["pass" if ok else "fail"] += 1
    print(f"  {'ok  ' if ok else 'FAIL'} {name}{'' if ok else f'  ({detail})'}")


class FakeApi:
    """Stands in for carrier_api's ApiConnectionGraphql: serves the fixtures and records every change sent."""

    def __init__(self):
        """Start with a valid session, no recorded calls and no failures queued."""
        self.calls, self.refresh_token, self.fail_with = [], "token", []
        self.api_websocket = types.SimpleNamespace(callback_add=lambda cb: None)

    async def load_data(self):
        """The fixture systems, or the next queued failure."""
        if self.fail_with:
            raise self.fail_with.pop(0)
        return load_systems()

    async def cleanup(self):
        """Nothing to close."""

    def __getattr__(self, name):
        """Any change (set_config_mode, update_fan, set_config_hold, ...): record it, or raise a queued failure."""

        async def call(*args, **kwargs):
            if self.fail_with:
                raise self.fail_with.pop(0)
            self.calls.append((name, [a.value if hasattr(a, "value") else a for a in args]))

        return call


async def new_coordinator():
    """A coordinator with the fake API and the fixture data loaded."""
    entry = ConfigEntry({"username": "me@example.com", "password": "pw"}, unique_id="me@example.com")
    coordinator = coord_mod.CarrierCoordinator(object(), entry)
    coordinator.api = FakeApi()
    coordinator.data = await coordinator._async_update_data()
    return coordinator


async def test_coordinator():
    """Full refresh, the one-time silent sign-in retry, wrong passwords, cloud errors and websocket messages."""
    print("coordinator")
    c = await new_coordinator()
    serial = next(iter(c.data))
    check("loads every system, keyed by serial", list(c.data) == ["SERIALXXX"], list(c.data))
    check("full refresh every 5 minutes", c.update_interval == timedelta(minutes=5), c.update_interval)

    c.api.fail_with = [CarrierApiAuthError("expired")]
    data = await c._async_update_data()
    check("expired session: signs in again once and carries on", serial in data and c.api.refresh_token is None)

    c.api.refresh_token, c.api.fail_with = "token", [CarrierApiAuthError("a"), CarrierApiAuthError("b")]
    try:
        await c._async_update_data()
        check("wrong password: asks the user (reauth)", False, "no error")
    except ConfigEntryAuthFailed:
        check("wrong password: asks the user (reauth)", True)

    c.api.fail_with = [CarrierApiGraphqlError("down")]
    try:
        await c._async_update_data()
        check("cloud error: entities go unavailable until the next refresh", False, "no error")
    except UpdateFailed:
        check("cloud error: entities go unavailable until the next refresh", True)

    c.data = await c._async_update_data()
    before = c.listener_updates
    await c._on_message(message("status_zone_rh", serial))
    zone = c.data[serial].status.zones[0]
    check(
        "websocket message updates the data and the entities", zone.humidity == 34 and c.listener_updates == before + 1
    )
    for bad in ("not json", '{"messageType":"InfinityStatus","deviceId":"OTHER"}'):
        await c._on_message(bad)
    check("bad or unknown websocket messages are ignored", c.listener_updates == before + 1)
    await c._on_message(message("heartbeat_with_no_device_id", serial))
    check("keep-alive messages change nothing", c.data[serial].status.zones[0].humidity == 34)


async def test_climate():
    """The thermostat entity: what it shows, every control, and showing writes before the cloud catches up."""
    print("climate")
    c = await new_coordinator()
    serial = next(iter(c.data))
    zones = [climate.CarrierZone(c, serial, z.api_id) for z in c.data[serial].config.zones]
    z = zones[0]
    check("one entity per enabled zone, named after the zone", [e._attr_name for e in zones] == ["ZONE 1"])
    check("unique id is serial + zone", z._attr_unique_id == f"{serial}_1", z._attr_unique_id)
    check(
        "modes follow the equipment",
        z._attr_hvac_modes == [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL, HVACMode.FAN_ONLY],
        z._attr_hvac_modes,
    )
    check(
        "presets are the zone's activities plus resume",
        z._attr_preset_modes[-1] == "resume" and "manual" in z._attr_preset_modes,
    )
    check("fan modes", z._attr_fan_modes == ["auto", "low", "medium", "high"], z._attr_fan_modes)
    check("device info from the profile", z._attr_device_info["model"] == "SYSTXCCWIC01-B", z._attr_device_info)
    check(
        "state from the fixture",
        (z.hvac_mode, z.current_temperature, z.current_humidity, z.preset_mode, z.target_temperature, z.fan_mode)
        == (HVACMode.HEAT, 74.0, 32, "wake", 74.0, "medium"),
        (z.hvac_mode, z.current_temperature, z.current_humidity, z.preset_mode, z.target_temperature, z.fan_mode),
    )
    check("heating while the zone is actively heating", z.hvac_action == HVACAction.HEATING, z.hvac_action)
    check("whole degrees in Fahrenheit", (z.temperature_unit, z.target_temperature_step) == ("°F", 1.0))

    await z.async_set_hvac_mode(HVACMode.COOL)
    await z.async_set_temperature(temperature=71.0)
    check(
        "set cool 71: sent as manual setpoints plus an indefinite hold",
        [n for n, _ in c.api.calls] == ["set_config_mode", "set_config_manual_activity", "set_config_hold"],
        c.api.calls,
    )
    check("set cool 71: the heat setpoint is kept", c.api.calls[1][1][2:4] == ["74.0", "71.0"], c.api.calls[1])
    check(
        "set cool 71: shown straight away",
        (z.hvac_mode, z.target_temperature, z.preset_mode) == (HVACMode.COOL, 71.0, "manual"),
    )

    c.data = await c._async_update_data()  # the cloud still serves the pre-change values for a while
    await c._on_message(message("status_zone_htsp", serial))
    check("stale cloud data does not undo the change", (z.hvac_mode, z.target_temperature) == (HVACMode.COOL, 71.0))

    await z.async_set_temperature(target_temp_low=66.0, target_temp_high=77.0)
    check("range in heat_cool form: both setpoints sent", c.api.calls[-2][1][2:4] == ["66.0", "77.0"], c.api.calls[-2])

    await z.async_set_preset_mode("away")
    away = c.data[serial].config.zones[0].find_activity(ActivityTypes.AWAY)
    check(
        "preset away: hold sent and away's setpoints shown",
        c.api.calls[-1] == ("set_config_hold", [serial, "1", "away"]) and z.target_temperature == away.cool_set_point,
    )

    await z.async_set_fan_mode("high")
    check(
        "fan high: sent for the running activity",
        c.api.calls[-1] == ("update_fan", [serial, "1", "away", "high"]),
        c.api.calls[-1],
    )

    live_zone = c.data[serial].config.zones[0]
    live_zone.hold, hold_before = True, True
    await z.async_set_preset_mode("resume")
    check("resume: schedule resumed", c.api.calls[-1] == ("resume_schedule", [serial, "1"]), c.api.calls[-1])
    check("resume: Carrier's own data is not changed locally", live_zone.hold == hold_before)

    c.api.fail_with = [CarrierApiGraphqlError("nope")]
    try:
        await z.async_set_hvac_mode(HVACMode.OFF)
        check("a rejected change is reported", False, "no error")
    except HomeAssistantError:
        check("a rejected change is reported", True)
    check("a rejected change is not shown", z.hvac_mode == HVACMode.COOL, z.hvac_mode)

    real = coord_mod.monotonic
    coord_mod.monotonic = lambda: real() + EXPECT_SECONDS + 1
    check("after the override window, Carrier's values are shown again", z.hvac_mode == HVACMode.HEAT, z.hvac_mode)
    coord_mod.monotonic = real

    c.data[serial].status.is_disconnected = True
    check("unavailable while the thermostat is offline with Carrier", not z.available)


async def test_sensors():
    """Outdoor temperature, and the electricity meter's start, growth, glitches, New Year and saved state."""
    print("sensors")
    c = await new_coordinator()
    serial = next(iter(c.data))
    out = sensor.OutdoorTemperature(c, serial)
    check("outdoor temperature", (out.native_value, out.native_unit_of_measurement) == (30.0, "°F"))

    def set_energy(y1, y2=None):
        """Replace year1 (and year2) in the fixture: cooling carries the number, gas must be ignored."""
        for period, value in ((EnergyPeriod.YEAR_1, y1), (EnergyPeriod.YEAR_2, y2)):
            m = c.data[serial].energy.measurement_for_period(period)
            for metric in sensor.ELECTRIC:
                setattr(m, metric.value, 0)
            m.cooling, m.gas = value, 99999

    async def meter():
        e = sensor.Electricity(c, serial)
        await e.async_added_to_hass()
        return e

    def read(e, when, y1, y2):
        NOW[0] = when
        set_energy(y1, y2)
        e._handle_coordinator_update()
        return e.native_value

    SAVED.clear()
    NOW[0] = datetime(2026, 10, 18, 12, tzinfo=TZ)
    set_energy(2400, 4100)
    e = await meter()
    check("starts at this year so far (gas excluded)", e.native_value == 2400, e.native_value)
    t = NOW[0]
    check("adds growth", read(e, t + timedelta(hours=1), 2410, 4100) == 2410)
    check("ignores a dip", read(e, t + timedelta(hours=2), 2405, 4100) == 2410)
    check("ignores a single zero reading", read(e, t + timedelta(hours=3), 0, 0) == 2410)
    check("no double count when it recovers", read(e, t + timedelta(hours=4), 2420, 4100) == 2420)

    SAVED[e._attr_unique_id] = e.extra_restore_state_data.as_dict()
    set_energy(2500, 4100)
    e = await meter()
    check("restart: total carried over and the missed growth added", e.native_value == 2500, e.native_value)

    ny = datetime(2027, 1, 1, 1, tzinfo=TZ)
    steps = [(ny - timedelta(hours=2), 2520, 4100), (ny, 3, 4100), (ny + timedelta(hours=1), 3, 4100),
             (ny + timedelta(hours=2), 5, 2530), (ny + timedelta(hours=3), 5, 2530)]  # fmt: skip
    values = [read(e, *s) for s in steps]
    check(
        "New Year: reset confirmed on a second reading, then last year finished from its final total",
        values == [2520, 2520, 2523, 2525, 2535],
        values,
    )
    check("never goes down", all(b >= a for a, b in zip(values, values[1:], strict=False)))

    # State saved by the pre-release version (no "year" key): a reading in October 2026, before New Year.
    SAVED.clear()
    SAVED[f"{serial}_electricity"] = {"total": 1520.0, "last": 1520, "prior": 4100,
                                     "seen": datetime(2026, 10, 17, 14, tzinfo=TZ).timestamp(), "rolled": None}  # fmt: skip
    NOW[0] = datetime(2026, 10, 18, 12, tzinfo=TZ)
    set_energy(1523, 4100)
    e = await meter()
    check(
        "upgrade from the pre-release saved state", (e.native_value, e._year) == (1523, 2026), (e.native_value, e._year)
    )


async def test_config_flow():
    """Sign-in form: success, wrong password, cloud down, duplicate account; and the password-changed form."""
    print("config flow")

    class FakeLogin:
        """Stands in for carrier_api's sign-in: succeeds, or raises whatever `outcome` is set to."""

        outcome = None

        def __init__(self, username, password):
            self.password = password

        async def login(self):
            if FakeLogin.outcome:
                raise FakeLogin.outcome

        async def cleanup(self):
            pass

    config_flow.ApiConnectionGraphql = FakeLogin
    user = {"username": "Me@Example.com", "password": "pw"}
    flow = config_flow.CarrierConfigFlow()
    result = await flow.async_step_user(user)
    check("good sign-in creates the entry", result["type"] == "create_entry" and flow.unique_id == "me@example.com")
    for error, expected in (
        (CarrierApiAuthError("x"), "invalid_auth"),
        (CarrierApiGraphqlError("x"), "cannot_connect"),
    ):
        FakeLogin.outcome = error
        result = await config_flow.CarrierConfigFlow().async_step_user(user)
        check(f"{expected} shown on the form", result["errors"] == {"base": expected}, result)
    FakeLogin.outcome = None
    config_flow.CarrierConfigFlow.existing_unique_ids = {"me@example.com"}
    try:
        await config_flow.CarrierConfigFlow().async_step_user(user)
        check("the same account can't be added twice", False, "no abort")
    except stubs.AbortFlow as abort:
        check("the same account can't be added twice", abort.reason == "already_configured")

    flow = config_flow.CarrierConfigFlow()
    flow.reauth_entry = ConfigEntry({"username": "me@example.com", "password": "old"})
    form = await flow.async_step_reauth({})
    check("password-changed form names the account", form["placeholders"] == {"username": "me@example.com"}, form)
    result = await flow.async_step_reauth_confirm({"password": "new"})
    check(
        "new password saved and the integration reloaded",
        flow.reauth_entry.data["password"] == "new" and result["reason"] == "reauth_successful",
    )


def test_files():
    """The log filter, translations covering every key the code uses, and the version in one place per file."""
    print("files")
    hide = coord_mod._HideSecrets()
    leak = logging.LogRecord("gql", logging.DEBUG, "", 0, "%s", ({"password": "pw"},), None)
    fine = logging.LogRecord("gql", logging.DEBUG, "", 0, "%s", ({"zones": []},), None)
    check("secrets kept out of the log", not hide.filter(leak) and hide.filter(fine))

    base = REPO / "custom_components" / DOMAIN
    tr = json.loads((base / "translations" / "en.json").read_text())
    presets = set(tr["entity"]["climate"]["zone"]["state_attributes"]["preset_mode"]["state"])
    check("every preset has a name", presets == {a.value for a in ActivityTypes} | {climate.RESUME}, presets)
    needed = {("config", "step", "user"), ("config", "step", "reauth_confirm"), ("config", "error", "invalid_auth"),
              ("config", "error", "cannot_connect"), ("config", "abort", "already_configured"),
              ("config", "abort", "reauth_successful"), ("entity", "sensor", "outdoor_temperature"),
              ("entity", "sensor", "electricity")}  # fmt: skip
    missing = [k for k in needed if k[2] not in tr[k[0]][k[1]]]
    check("every form, error and sensor has its text", not missing, missing)

    manifest = json.loads((base / "manifest.json").read_text())
    changelog = re.search(r"^## (\S+)", (REPO / "docs" / DOMAIN / "CHANGELOG.md").read_text(), re.M)
    check(
        "manifest version matches the newest CHANGELOG entry",
        changelog and changelog.group(1) == manifest["version"],
        (manifest["version"], changelog and changelog.group(1)),
    )
    check(
        "manifest keys in Home Assistant's order",
        list(manifest)[:2] == ["domain", "name"] and list(manifest)[2:] == sorted(list(manifest)[2:]),
    )


async def main():
    """Run every test and exit non-zero if any check failed."""
    snapshot = copy.deepcopy(SAVED)
    await test_coordinator()
    await test_climate()
    await test_sensors()
    await test_config_flow()
    test_files()
    SAVED.clear()
    SAVED.update(snapshot)
    print(f"\n{RESULTS['pass']} passed, {RESULTS['fail']} failed")
    sys.exit(1 if RESULTS["fail"] else 0)


if __name__ == "__main__":
    asyncio.run(main())
