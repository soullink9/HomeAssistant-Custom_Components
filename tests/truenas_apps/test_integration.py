"""Integration tests: the real integration code against a fake TrueNAS on a virtual clock.

Run: ``python3 tests/truenas_apps/test_integration.py [days]`` (see tests/truenas_apps/README.md). Exits non-zero if any check fails.
"""

import asyncio
import collections
import gc
import importlib
import logging
import os
import sys
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [
    os.path.join(HERE, "stubs"),
    os.path.dirname(os.path.dirname(HERE)),
    HERE,
]  # stand-ins first, then the repo
sys.dont_write_bytecode = True
logging.disable(logging.CRITICAL)

from fake_truenas import Server, Session, clock, new_app  # noqa: E402
from homeassistant.config_entries import ConfigEntry  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.helpers.device_registry import DeviceEntry  # noqa: E402

PKG = "custom_components.truenas_apps"
integration = importlib.import_module(PKG)
coordinator_mod = importlib.import_module(f"{PKG}.coordinator")
platforms = [importlib.import_module(f"{PKG}.{n}") for n in ("sensor", "switch", "button", "update")]
importlib.import_module(f"{PKG}.config_flow")  # must at least import

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 30
POLLS_PER_DAY = 1440  # one poll a minute
PROPERTIES = (
    "native_value",
    "is_on",
    "installed_version",
    "latest_version",
    "entity_picture",
    "extra_state_attributes",
    "release_url",
    "in_progress",
)


def reset(seed=1):
    """Fresh clock and fake server."""
    clock.now, clock.limit = 0.0, float("inf")
    return Server(seed)


async def setup(server):
    """Build coordinator + entities like Home Assistant would. Returns (hass, entry, coordinator, entities)."""
    hass = HomeAssistant()
    hass.session = Session(server)
    entry = ConfigEntry(data={"host": "nas", "api_key": server.key, "verify_ssl": False})
    coord = coordinator_mod.TrueNASCoordinator(hass, entry)
    entry.runtime_data = coord
    await coord.async_config_entry_first_refresh()
    entities = []
    for platform in platforms:
        await platform.async_setup_entry(hass, entry, entities.extend)
    for e in entities:
        e.hass = hass
    return hass, entry, coord, entities


def read_all(entities, errors):
    """Read every property of every available entity, counting any that raise."""
    for e in entities:
        try:
            if not e.available:
                continue
        except Exception as ex:
            errors[f"{type(e).__name__}.available:{type(ex).__name__}"] += 1
            continue
        for prop in PROPERTIES:
            if hasattr(type(e), prop):
                try:
                    getattr(e, prop)
                except Exception as ex:
                    errors[f"{type(e).__name__}.{prop}:{type(ex).__name__}"] += 1


async def poll(coord, entities, errors, count=1, hook=None):
    """Advance one minute per poll, refresh, and read all entities."""
    for _ in range(count):
        if coord.auth_failed:
            return
        clock.now += 60
        await coord.async_refresh()
        if coord.data is not None:
            read_all(entities, errors)
        if hook:
            hook()


def entity(entities, cls, app, name=None):
    """Find an entity by class name, app and (for buttons) display name."""
    for e in entities:
        if type(e).__name__ == cls and getattr(e, "_app", None) == app and (name is None or e._attr_name == name):
            return e
    raise LookupError((cls, app, name))


async def finish(entry, coord, entities):
    """Wait for background jobs, then poll once so entities see the result."""
    await asyncio.gather(*entry.bg, return_exceptions=True)
    await poll(coord, entities, collections.Counter(), 1)


# --------------------------------------------------------------------------------------------------
# Each test returns nothing and asserts. They run in order; a failure is reported and the run continues.
# --------------------------------------------------------------------------------------------------


async def test_healthy_long_run():
    """Months of normal polling: no errors, no leaked sockets/tasks/listeners, memory stays flat."""
    srv = reset()
    _, _, coord, ents = await setup(srv)
    errors = collections.Counter()
    listeners_at_start = len(coord.listeners)
    tracemalloc.start()
    await poll(coord, ents, errors, POLLS_PER_DAY * 2)
    gc.collect()
    base = tracemalloc.get_traced_memory()[0]
    await poll(coord, ents, errors, POLLS_PER_DAY * (DAYS - 2))
    gc.collect()
    growth_kb = (tracemalloc.get_traced_memory()[0] - base) / 1024
    tracemalloc.stop()
    assert not coord.failed and not coord.unexpected, (dict(coord.failed), dict(coord.unexpected))
    assert not errors, dict(errors)
    assert srv.open == 0 and srv.max_open == 1, (srv.open, srv.max_open)
    assert len(coord.listeners) == listeners_at_start, "listeners piled up"
    assert len(asyncio.all_tasks()) == 1, "background tasks leaked"
    assert srv.counts["login_ok"] >= POLLS_PER_DAY * DAYS  # one short connection per poll
    assert growth_kb < 512, f"memory grew {growth_kb:.0f} KB"


async def test_entities_and_values():
    """Every expected entity exists, with the right values."""
    srv = reset()
    srv.new_version = "25.10.8"
    srv.apps["plex"].update(upgrade_available=True, latest_version="2.0.0", state="STOPPED")
    _, _, coord, ents = await setup(srv)
    await poll(coord, ents, collections.Counter())
    names = collections.Counter(type(e).__name__ for e in ents)
    assert names == {
        "AppStatus": 3,
        "AppSwitch": 3,
        "AppButton": 6,
        "AppUpdate": 3,
        "PoolUsage": 1,
        "SystemUpdate": 1,
    }, names
    assert len({e._attr_unique_id for e in ents}) == len(ents)
    assert entity(ents, "AppStatus", "plex").native_value == "stopped"
    assert entity(ents, "AppSwitch", "plex").is_on is False and entity(ents, "AppSwitch", "sonarr").is_on is True
    upd = entity(ents, "AppUpdate", "plex")
    assert (upd.installed_version, upd.latest_version) == ("1.0.0", "2.0.0")
    assert entity(ents, "AppUpdate", "sonarr").latest_version == "1.0.0"
    assert upd.entity_picture.endswith("plex.png")
    pool = [e for e in ents if type(e).__name__ == "PoolUsage"][0]
    assert pool.native_value == 40.0
    system = [e for e in ents if type(e).__name__ == "SystemUpdate"][0]
    assert (system.installed_version, system.latest_version) == ("25.10.7", "25.10.8")
    assert system.extra_state_attributes == {
        "hostname": "thevault",
        "platform": "Generic",
        "edition": "Community",
        "version_name": "Goldeye",
    }


async def test_system_update_never_installs():
    """The TrueNAS update entity refuses to install and starts no job."""
    srv = reset()
    _, _, coord, ents = await setup(srv)
    system = [e for e in ents if type(e).__name__ == "SystemUpdate"][0]
    try:
        await system.async_install(None, False)
    except Exception as ex:
        assert type(ex).__name__ == "HomeAssistantError"
    else:
        raise AssertionError("install was allowed")
    assert srv.counts["jobs_started"] == 0


async def test_flaky_network():
    """2% connect failures, 1% mid-reply closes, 0.2% RPC errors: all handled, nothing leaks."""
    srv = reset(2)
    srv.p_conn_fail, srv.p_close, srv.p_error = 0.02, 0.01, 0.002
    _, _, coord, ents = await setup(srv)
    errors = collections.Counter()
    await poll(coord, ents, errors, POLLS_PER_DAY * min(DAYS, 30))
    assert not coord.unexpected, dict(coord.unexpected)
    assert coord.failed, "expected some handled failures"
    assert srv.open == 0 and not errors, (srv.open, dict(errors))


async def test_revoked_key_asks_for_reauth_and_stops():
    """A rejected key triggers re-authentication and stops hammering TrueNAS."""
    srv = reset(3)
    _, _, coord, ents = await setup(srv)
    errors = collections.Counter()
    await poll(coord, ents, errors, POLLS_PER_DAY)
    srv.key = "ROTATED"
    before = srv.counts["connect"]
    await poll(coord, ents, errors, POLLS_PER_DAY * 5)
    assert coord.auth_failed
    assert srv.counts["connect"] - before == 1, "kept retrying with a rejected key"
    assert srv.counts["login_fail"] == 1


async def test_apps_and_pools_come_and_go():
    """Removed things become unavailable, can be deleted, and come back; live devices can't be deleted."""
    srv = reset(4)
    hass, entry, coord, ents = await setup(srv)
    errors = collections.Counter()
    await poll(coord, ents, errors, 5)
    start = len(ents)
    del srv.apps["radarr"]
    await poll(coord, ents, errors, 3)
    gone = [e for e in ents if getattr(e, "_app", None) == "radarr"]
    assert gone and all(not e.available for e in gone)
    ident = lambda suffix: DeviceEntry({("truenas_apps", f"E1{suffix}")})  # noqa: E731
    remove = integration.async_remove_config_entry_device
    assert await remove(hass, entry, ident("_radarr")) is True
    assert hass.config_entries.reloads == ["E1"]
    assert await remove(hass, entry, ident("_plex")) is False
    assert await remove(hass, entry, ident("")) is False
    srv.apps["radarr"] = new_app("radarr", version="2.0")
    await poll(coord, ents, errors, 3)
    assert all(e.available for e in gone)
    srv.pools["fast"] = {"name": "fast", "size": 10**12, "allocated": 10**11, "free": 9 * 10**11}
    await poll(coord, ents, errors, 2)
    assert len(ents) == start + 1, "new pool should get one sensor"
    del srv.pools["tank"]
    await poll(coord, ents, errors, 2)
    assert not [e for e in ents if getattr(e, "_pool", None) == "tank"][0].available

    class Unloaded:
        entry_id = "E1"

    assert await remove(hass, Unloaded(), ident("_radarr")) is False
    assert not errors and not coord.unexpected


async def test_restart_pressed_repeatedly():
    """Pressing Restart three times runs once; the extra presses are refused with a message."""
    srv = reset(5)
    _, entry, coord, ents = await setup(srv)
    button = entity(ents, "AppButton", "plex", "Restart")
    refused = 0
    for _ in range(3):
        try:
            await button.async_press()
        except Exception:
            refused += 1
    await finish(entry, coord, ents)
    assert refused == 2 and len(entry.bg) == 1
    assert (srv.counts["app.stop"], srv.counts["app.start"]) == (1, 1)
    assert srv.apps["plex"]["state"] == "RUNNING" and coord.busy == set()


async def test_stuck_job_gives_up():
    """A job that never finishes is abandoned after JOB_TIMEOUT and the app is released."""
    srv = reset(6)
    srv.job_mode = "stuck"
    _, entry, coord, ents = await setup(srv)
    clock.limit = 86400
    old = coordinator_mod.JOB_TIMEOUT
    coordinator_mod.JOB_TIMEOUT = 0.3  # virtual-clock seconds
    try:
        coord.app_action("plex", "start")
        await asyncio.wait_for(asyncio.gather(*entry.bg, return_exceptions=True), 30)
    finally:
        coordinator_mod.JOB_TIMEOUT = old
    assert coord.busy == set() and srv.open == 0
    assert "plex" in " ".join(coord.hass.notifications.values()), "no notification for the abandoned job"


async def test_pruned_job_counts_as_done():
    """If TrueNAS already forgot the job when we look, treat it as finished instead of crashing."""
    srv = reset(7)
    srv.job_mode = "pruned"
    _, entry, coord, ents = await setup(srv)
    coord.app_action("plex", "stop")
    await asyncio.gather(*entry.bg, return_exceptions=True)
    assert not entry.bg_errors and coord.busy == set()


async def test_restart_of_stopped_app_only_starts():
    """Restart on a stopped app skips the stop (which TrueNAS would reject)."""
    srv = reset(8)
    srv.job_mode = "fail_if_stopped"
    srv.apps["plex"]["state"] = "STOPPED"
    _, entry, coord, ents = await setup(srv)
    await entity(ents, "AppButton", "plex", "Restart").async_press()
    await asyncio.gather(*entry.bg, return_exceptions=True)
    assert srv.counts["app.stop"] == 0 and srv.counts["app.start"] == 1
    assert not entry.bg_errors


async def test_api_drift():
    """Missing or null fields after a TrueNAS upgrade never raise out of the coordinator or an entity."""

    def drop(method, key):
        return lambda m, r: [{k: v for k, v in a.items() if k != key} for a in r] if m == method else r

    def replace(method, **kw):
        return lambda m, r: [dict(a, **kw) for a in r] if m == method else r

    cases = {
        "app missing state": drop("app.query", "state"),
        "app version null": replace("app.query", version=None),
        "app metadata null": replace("app.query", metadata=None),
        "update flagged but no latest_version": replace("app.query", upgrade_available=True, latest_version=None),
        "pool size 0": replace("pool.query", size=0),
        "pool missing allocated": drop("pool.query", "allocated"),
        "update.status error": lambda m, r: {"code": "ERROR", "status": None} if m == "update.status" else r,
        "sys_info null": lambda m, r: None if m == "webui.main.dashboard.sys_info" else r,
        "sys_info missing hostname": lambda m, r: (
            {k: v for k, v in r.items() if k != "hostname"} if m == "webui.main.dashboard.sys_info" else r
        ),
    }
    for name, fn in cases.items():
        srv = reset(9)
        _, _, coord, ents = await setup(srv)
        errors = collections.Counter()
        srv.drift = fn
        await poll(coord, ents, errors, 3)
        assert not coord.unexpected and not errors, (name, dict(coord.unexpected), dict(errors))


async def test_restricted_api_key():
    """A key that can't read the optional methods still works; only those entities go unavailable."""
    srv = reset(9)
    srv.deny = {"update.status", "webui.main.dashboard.sys_info", "truenas.is_ix_hardware"}
    _, _, coord, ents = await setup(srv)
    errors = collections.Counter()
    await poll(coord, ents, errors, 3)
    system = [e for e in ents if type(e).__name__ == "SystemUpdate"][0]
    assert not system.available and system.extra_state_attributes == {}
    assert entity(ents, "AppStatus", "plex").available and not errors and not coord.unexpected


async def test_odd_frames():
    """Push notifications, bad JSON and dropped sockets mid-reply are survived."""
    for knob in ("p_notify", "p_badjson", "p_close"):
        srv = reset(10)
        setattr(srv, knob, 0.01)
        _, _, coord, ents = await setup(srv)
        await poll(coord, ents, collections.Counter(), POLLS_PER_DAY * 3)
        assert not coord.unexpected, (knob, dict(coord.unexpected))
        assert srv.open == 0


async def test_outage_and_recovery():
    """A six-hour outage marks everything unavailable; the first poll after it recovers."""
    srv = reset(11)
    _, _, coord, ents = await setup(srv)
    errors = collections.Counter()
    await poll(coord, ents, errors, 100)
    srv.up = False
    await poll(coord, ents, errors, 360)
    assert not coord.last_update_success and not entity(ents, "AppStatus", "plex").available
    srv.up = True
    await poll(coord, ents, errors, 1)
    assert coord.last_update_success and entity(ents, "AppStatus", "plex").available
    assert not coord.unexpected and srv.open == 0


async def test_connect_hang_is_capped():
    """A TrueNAS that accepts connections but never answers can't block a poll beyond POLL_TIMEOUT."""
    srv = reset(12)
    _, _, coord, _ = await setup(srv)
    srv.hang_connect = srv.hang_forever = True
    old = coordinator_mod.POLL_TIMEOUT
    coordinator_mod.POLL_TIMEOUT = 0.05
    start = time.time()
    try:
        await coord.async_refresh()
    finally:
        coordinator_mod.POLL_TIMEOUT = old
    assert time.time() - start < 5 and not coord.last_update_success and not coord.unexpected


async def test_install_button():
    """Install runs once, shows progress, reports failures, and is refused while busy."""

    def arm(s):
        s.apps["plex"].update(version="1.0.0", latest_version="2.0.0", upgrade_available=True, state="RUNNING")

    # happy path, with a double press
    srv = reset(20)
    arm(srv)
    hass, entry, coord, ents = await setup(srv)
    upd = entity(ents, "AppUpdate", "plex")
    await upd.async_install(None, False)
    assert upd.in_progress
    try:
        await upd.async_install(None, False)
    except Exception as ex:
        assert type(ex).__name__ == "HomeAssistantError"
    else:
        raise AssertionError("second press was accepted")
    await finish(entry, coord, ents)
    assert srv.counts["app.upgrade"] == 1
    assert srv.apps["plex"]["version"] == "2.0.0" and not upd.in_progress and not hass.notifications

    # the job fails on TrueNAS: the user gets a persistent notification
    srv = reset(21)
    arm(srv)
    srv.job_mode = "fail"
    hass, entry, coord, ents = await setup(srv)
    await entity(ents, "AppUpdate", "plex").async_install(None, False)
    await finish(entry, coord, ents)
    assert "plex" in " ".join(hass.notifications.values())

    # pressed while a restart runs: refused
    srv = reset(22)
    arm(srv)
    hass, entry, coord, ents = await setup(srv)
    coord.app_action("plex", "stop", "start")
    try:
        await entity(ents, "AppUpdate", "plex").async_install(None, False)
    except Exception as ex:
        assert type(ex).__name__ == "HomeAssistantError"
    else:
        raise AssertionError("install overlapped a restart")
    await finish(entry, coord, ents)

    # 60 presses on a flaky setup: every press ends in an upgrade or a visible notification, never silence
    srv = reset(24)
    srv.p_conn_fail, srv.p_close, srv.p_job_fail = 0.10, 0.03, 0.10
    hass, entry, coord, ents = await setup(srv)
    upd = entity(ents, "AppUpdate", "plex")
    for _ in range(60):
        srv.up = True
        arm(srv)
        hass.notifications.clear()
        entry.bg.clear()
        try:
            await upd.async_install(None, False)
        except Exception:
            pass  # refused before it started: Home Assistant shows the error itself
        await asyncio.gather(*entry.bg, return_exceptions=True)
        clock.now += 60
        srv.settle()
        if srv.apps["plex"]["version"] != "2.0.0" and entry.bg:
            assert hass.notifications, "an install failed silently"


async def main():
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and asyncio.iscoroutinefunction(f)]
    failed = []
    for name, fn in tests:
        started = time.time()
        try:
            await fn()
            print(f"PASS {name} ({time.time() - started:.1f}s)")
        except AssertionError as ex:
            failed.append(name)
            print(f"FAIL {name}: {ex!r}")
        except Exception as ex:
            failed.append(name)
            print(f"ERROR {name}: {type(ex).__name__}: {ex}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed ({DAYS} simulated days)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
