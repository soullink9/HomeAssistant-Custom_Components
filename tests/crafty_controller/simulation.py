"""Simulation test for the Crafty Controller integration.

Run:  python3 tests/crafty_controller/simulation.py      (Python 3.12+, no other dependencies)

The real integration files are loaded and run against a mock Crafty server that
returns messy data: missing fields, 403s, HTML pages, hangs, servers that are
removed or added, and failing start/stop actions. It prints PASS/FAIL per check
and exits non-zero if any check fails.

aiohttp, voluptuous and the Home Assistant base classes are thin stand-ins
defined below, so this checks the integration's own logic only. It does NOT test
real Home Assistant, real HTTP/TLS or a real Crafty. Keep the stand-ins in sync
if the integration starts using more of the Home Assistant API.
"""
import asyncio, importlib, json, os, sys, types

sys.dont_write_bytecode = True  # keep __pycache__ out of the repository
from enum import Enum
from typing import Generic, TypeVar
from urllib.parse import urlparse

# Locate the integration relative to this file so the script runs from anywhere.
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "custom_components")
PKG = os.path.join(ROOT, "crafty_controller")
sys.path.insert(0, ROOT)
T = TypeVar("T")

# ───────────────────────── aiohttp stand-in ─────────────────────────
class ClientError(Exception): pass
class ClientResponseError(ClientError):
    def __init__(self, status): super().__init__(status); self.status = status
class ClientTimeout:
    def __init__(self, total=None): self.total = total
class _Resp:
    def __init__(self, status, body): self.status, self.body = status, body
    def raise_for_status(self):
        if self.status >= 400: raise ClientResponseError(self.status)
    async def json(self, content_type=None): return json.loads(self.body)  # bad JSON -> ValueError, as real
async def _fetch(method, url, headers):
    u = urlparse(url)
    if u.scheme != "http": raise ClientError("ssl/handshake failure (stand-in)")
    try: r, w = await asyncio.open_connection(u.hostname, u.port)
    except OSError as e: raise ClientError(str(e)) from e
    hdr = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
    w.write(f"{method} {u.path} HTTP/1.1\r\nHost: x\r\n{hdr}Connection: close\r\n\r\n".encode())
    raw = await r.read(); w.close()
    head, _, body = raw.partition(b"\r\n\r\n")
    return _Resp(int(head.split(b" ", 2)[1]), body)
class _Req:
    def __init__(self, m, u, h, t): self.a = (m, u, h); self.t = t
    async def __aenter__(self):
        return await asyncio.wait_for(_fetch(*self.a), self.t.total if self.t else None)
    async def __aexit__(self, *x): return False
class ClientSession:
    def request(self, method, url, headers=None, timeout=None): return _Req(method, url, headers or {}, timeout)
    def get(self, url, **kw): return self.request("GET", url, **kw)
def mod(name, **kw):
    m = types.ModuleType(name); m.__dict__.update(kw); sys.modules[name] = m; return m
mod("aiohttp", ClientError=ClientError, ClientResponseError=ClientResponseError,
    ClientTimeout=ClientTimeout, ClientSession=ClientSession)
class _Required:
    def __init__(self, k, default=None): self.schema, self.default = k, default
class _Schema:
    def __init__(self, s): self.schema = s
mod("voluptuous", Required=_Required, Schema=_Schema)

# ───────────────────────── Home Assistant stand-ins ─────────────────────────
class Platform(str, Enum): SWITCH = "switch"; BINARY_SENSOR = "binary_sensor"
class HomeAssistantError(Exception): pass
class UpdateFailed(Exception): pass
class ConfigEntryNotReady(Exception): pass
class ConfigEntry(Generic[T]):
    def __init__(self, data): self.data, self.runtime_data, self._un = data, None, []
    def async_on_unload(self, fn): self._un.append(fn)
class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kw): cls.domain = domain
    def _async_abort_entries_match(self, m): pass
    def async_show_form(self, step_id, data_schema, errors=None): return {"type": "form", "errors": errors or {}}
    def async_create_entry(self, title, data): return {"type": "create_entry", "data": data}
class DataUpdateCoordinator(Generic[T]):
    def __init__(self, hass, logger, *, name, config_entry=None, update_interval=None):
        self.data, self.last_update_success, self._l, self.unexpected = None, True, [], []
    async def async_refresh(self):
        try: self.data = await self._async_update_data(); self.last_update_success = True
        except UpdateFailed: self.last_update_success = False
        except Exception as e: self.unexpected.append(e); self.last_update_success = False  # real HA logs these as bugs
        for cb in list(self._l): cb()
    async def async_config_entry_first_refresh(self):
        await self.async_refresh()
        if not self.last_update_success: raise ConfigEntryNotReady()
    def async_add_listener(self, cb):
        self._l.append(cb); return lambda: self._l.remove(cb)
class CoordinatorEntity(Generic[T]):
    def __init__(self, coordinator): self.coordinator = coordinator
    @property
    def available(self): return self.coordinator.last_update_success
    def async_write_ha_state(self): render(self)
def render(e):
    attrs = e.extra_state_attributes            # HA evaluates attributes even when unavailable
    if not e.available: return "unavailable", attrs
    return ("on" if e.is_on else "off"), attrs
mod("homeassistant"); mod("homeassistant.components"); mod("homeassistant.helpers")
mod("homeassistant.config_entries", ConfigEntry=ConfigEntry, ConfigFlow=ConfigFlow)
mod("homeassistant.const", CONF_TOKEN="token", CONF_URL="url", CONF_VERIFY_SSL="verify_ssl", Platform=Platform)
mod("homeassistant.core", HomeAssistant=object, callback=lambda f: f)
mod("homeassistant.exceptions", HomeAssistantError=HomeAssistantError)
mod("homeassistant.helpers.aiohttp_client", async_get_clientsession=lambda hass, v=True: ClientSession())
mod("homeassistant.helpers.device_registry", DeviceInfo=dict)
mod("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity,
    DataUpdateCoordinator=DataUpdateCoordinator, UpdateFailed=UpdateFailed)
mod("homeassistant.components.switch", SwitchEntity=type("SwitchEntity", (), {}))
mod("homeassistant.components.binary_sensor", BinarySensorEntity=type("BinarySensorEntity", (), {}),
    BinarySensorDeviceClass=type("BSDC", (), {"CONNECTIVITY": "connectivity"}))

# ───────────────────────── mock Crafty ─────────────────────────
W = {"servers": {}, "list_mode": "ok", "stats_mode": {}, "action_mode": "ok", "delay": 0.3, "calls": []}
def J(o, status=200): return status, "application/json", json.dumps(o).encode()
def sobj(sid, s):
    o = {"server_id": sid, "type": "minecraft-java"}
    if s["name"] is not None: o["server_name"] = s["name"]
    if s["port"] is not None: o["server_port"] = s["port"]
    return o
async def route(method, path, hdr):
    if hdr.get("authorization") != "Bearer GOOD": return J({"status": "error", "error": "NOT_AUTHORIZED"}, 403)
    if path == "/api/v2/servers":
        m = W["list_mode"]
        if m == "html": return 200, "text/html", b"<html>login</html>"
        if m == "error_status": return J({"status": "error", "error": "X"})
        if m == "500": return J({"status": "error"}, 500)
        if m == "wrong_shape": return J([])
        if m == "hang": await asyncio.sleep(2)
        return J({"status": "ok", "data": [sobj(k, v) for k, v in W["servers"].items()]})
    p = path.split("/"); sid = p[4]
    if sid not in W["servers"]: return J({"status": "error", "error": "SERVER_NOT_FOUND"}, 404)
    s = W["servers"][sid]
    if p[5] == "stats":
        m = W["stats_mode"].get(sid, "top")
        if m == "403": return J({"status": "error"}, 403)
        if m == "html": return 200, "text/html", b"<html/>"
        if m == "nulls": return J({"status": "ok", "data": None, "running": None, "int_ping_results": None})
        ping = s["ping"]
        if m == "nested": return J({"status": "ok", "data": {"running": s["running"], "int_ping_results": ping, "server_port": s["port"]}})
        return J({"status": "ok", "data": {"server_id": sobj(sid, s)}, "running": s["running"],
                  "int_ping_results": "True" if ping else "False", "server_port": s["port"]})
    if p[5] == "action":
        m = W["action_mode"]
        if m == "403": return J({"status": "error"}, 403)
        if m == "error_status": return J({"status": "error", "error": "NOPE"})
        run = p[6] == "start_server"
        asyncio.get_running_loop().call_later(W["delay"], lambda: s.update(running=run, ping=run))
        return J({"status": "ok"})
async def handle(r, w):
    try:
        head = (await r.readuntil(b"\r\n\r\n")).decode().split("\r\n")
        method, path, _ = head[0].split(" ")
        hdr = {l.split(":", 1)[0].lower(): l.split(":", 1)[1].strip() for l in head[1:] if ":" in l}
        W["calls"].append((method, path))
        st, ct, body = await route(method, path, hdr)
        w.write(f"HTTP/1.1 {st} X\r\nContent-Type: {ct}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
        await w.drain(); w.close()
    except Exception: pass

# ───────────────────────── harness ─────────────────────────
res = []
def check(name, cond, detail=""):
    res.append(cond); print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"   <- {detail}"))
class Hass:
    def __init__(self):
        self.entities = []
        self.config_entries = types.SimpleNamespace(
            async_forward_entry_setups=self._fwd, async_unload_platforms=self._unl)
    async def _fwd(self, entry, platforms):
        for p in platforms:
            await importlib.import_module(f"crafty_controller.{p.value}").async_setup_entry(
                self, entry, lambda ents: self.entities.extend(ents))
    async def _unl(self, entry, platforms): return True
def E(h, cls, sid): return next(e for e in h.entities if type(e).__name__ == cls and e.server_id == sid)
def S(h, cls, sid): return render(E(h, cls, sid))

async def main():
    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]; URL = f"http://127.0.0.1:{port}"

    # --- file layout / metadata ---
    need = ["__init__.py", "const.py", "api.py", "coordinator.py", "entity.py", "config_flow.py",
            "switch.py", "binary_sensor.py", "manifest.json", "translations/en.json",
            "brand/icon.png", "brand/icon@2x.png"]
    miss = [f for f in need if not os.path.isfile(f"{PKG}/{f}")]
    check("layout: all required files present with exact names", not miss, miss)
    try:
        for f in need:
            if f.endswith(".py"): compile(open(f"{PKG}/{f}").read(), f, "exec")  # syntax check only
        man = json.load(open(f"{PKG}/manifest.json")); tr = json.load(open(f"{PKG}/translations/en.json"))
        ok = man["domain"] == "crafty_controller" and man["config_flow"] is True and "version" in man
        ok2 = set(tr["config"]["step"]["user"]["data"]) == {"url", "token", "verify_ssl"} and {"cannot_connect", "invalid_auth"} <= set(tr["config"]["error"])
        check("layout: py compiles, manifest + translations valid and match flow keys", ok and ok2)
    except Exception as e: check("layout: compile/json", False, repr(e))

    cc = importlib.import_module("crafty_controller")
    importlib.import_module("crafty_controller.api").TIMEOUT = ClientTimeout(total=0.5)  # make hang scenarios fast
    from crafty_controller.config_flow import CraftyFlow

    W["servers"] = {
        "s1": {"name": "Survival", "port": 25565, "running": True, "ping": True},
        "s2": {"name": "Creative", "port": 25566, "running": False, "ping": False},
        "s3": {"name": None, "port": None, "running": False, "ping": False},   # sparse data
    }
    W["stats_mode"] = {"s2": "nested", "s3": "nulls"}
    h = Hass(); entry = ConfigEntry({"url": URL, "token": "GOOD", "verify_ssl": False})
    await cc.async_setup_entry(h, entry); c = entry.runtime_data
    sw, st = "CraftySwitch", "CraftyStatus"

    # --- S1 baseline + both response shapes + null/missing fields ---
    check("S1 six entities created (3 servers x switch+status)", len(h.entities) == 6, len(h.entities))
    check("S1 s1 running+online, port attr", S(h, sw, "s1") == ("on", {"port": 25565}) and S(h, st, "s1")[0] == "on", (S(h, sw, "s1"), S(h, st, "s1")))
    check("S1 s2 (nested shape, bool ping) off/off, port 25566", S(h, sw, "s2") == ("off", {"port": 25566}) and S(h, st, "s2")[0] == "off")
    check("S1 s3 (no name/port, null stats) survives: off/off, port None", S(h, sw, "s3") == ("off", {"port": None}) and S(h, st, "s3")[0] == "off")
    check("S1 s3 device name falls back to server_id", E(h, sw, "s3")._attr_device_info["name"] == "s3")
    check("S1 unique_ids unique", len({e._attr_unique_id for e in h.entities}) == 6)

    # --- S2 one server's stats fail -> only that server unavailable ---
    W["stats_mode"]["s2"] = "403"; await c.async_refresh()
    check("S2 s2 403 -> s2 unavailable, no crash", S(h, sw, "s2") == ("unavailable", {"port": None}) and S(h, st, "s2")[0] == "unavailable")
    check("S2 s1/s3 unaffected", S(h, sw, "s1")[0] == "on" and S(h, sw, "s3")[0] == "off" and c.last_update_success)
    W["stats_mode"]["s2"] = "html"; await c.async_refresh()
    check("S2 s2 HTML body -> unavailable, still no crash", S(h, sw, "s2")[0] == "unavailable" and S(h, sw, "s1")[0] == "on")
    W["stats_mode"]["s2"] = "nested"; await c.async_refresh()
    check("S2 s2 recovers", S(h, sw, "s2")[0] == "off")

    # --- S3 server removed in Crafty, then returns ---
    gone = W["servers"].pop("s3"); await c.async_refresh()
    check("S3 removed server -> unavailable, no KeyError", S(h, sw, "s3")[0] == "unavailable" and S(h, st, "s3")[0] == "unavailable")
    W["servers"]["s3"] = gone; await c.async_refresh()
    check("S3 returns -> available again, no duplicate entities", S(h, sw, "s3")[0] == "off" and len(h.entities) == 6, len(h.entities))

    # --- S4 server added later ---
    W["servers"]["s4"] = {"name": "Modded", "port": 25570, "running": True, "ping": True}; await c.async_refresh()
    check("S4 new server gets entities without reload", len(h.entities) == 8 and S(h, sw, "s4") == ("on", {"port": 25570}), len(h.entities))
    check("S4 unique_ids still unique", len({e._attr_unique_id for e in h.entities}) == 8)

    # --- S5 whole-API failure modes, then recovery ---
    for m in ("html", "error_status", "500", "wrong_shape", "hang"):
        W["list_mode"] = m; await c.async_refresh()
        allun = all(render(e)[0] == "unavailable" for e in h.entities)
        check(f"S5 list={m}: UpdateFailed, all unavailable, no unexpected exception", (not c.last_update_success) and allun and not c.unexpected, (c.unexpected[-1:] if c.unexpected else ""))
    W["list_mode"] = "ok"; await c.async_refresh()
    check("S5 recovers after outage", c.last_update_success and all(render(e)[0] != "unavailable" for e in h.entities))
    c._token = "BAD"; await c.async_refresh()
    check("S5 revoked token -> unavailable (no crash)", (not c.last_update_success) and not c.unexpected)
    c._token = "GOOD"; await c.async_refresh()

    # --- S6 switch actions ---
    W["calls"].clear(); sw2 = E(h, sw, "s2")
    await sw2.async_turn_on()
    check("S6 turn_on: POST start_server sent", ("POST", "/api/v2/servers/s2/action/start_server") in W["calls"])
    check("S6 turn_on: switch shows ON immediately (no flicker)", S(h, sw, "s2")[0] == "on")
    await asyncio.sleep(0.5); await c.async_refresh()
    check("S6 after server actually starts, poll confirms ON + status online", S(h, sw, "s2")[0] == "on" and S(h, st, "s2")[0] == "on")
    await sw2.async_turn_off(); check("S6 turn_off: OFF immediately", S(h, sw, "s2")[0] == "off")
    await asyncio.sleep(0.5); await c.async_refresh()
    check("S6 poll confirms OFF", S(h, sw, "s2")[0] == "off" and S(h, st, "s2")[0] == "off")
    for m in ("403", "error_status"):
        W["action_mode"] = m
        try: await sw2.async_turn_on(); raised = False
        except HomeAssistantError: raised = True
        check(f"S6 action {m}: HomeAssistantError raised, state NOT flipped", raised and S(h, sw, "s2")[0] == "off")
    W["action_mode"] = "ok"

    # --- S7 config flow ---
    async def flow(url, token, verify=False):
        f = CraftyFlow(); f.hass = None
        return await f.async_step_user({"url": url, "token": token, "verify_ssl": verify})
    r = await flow(f"  {URL}/  ", " GOOD ")
    check("S7 flow ok: entry created, URL + token normalised", r["type"] == "create_entry" and r["data"]["url"] == URL and r["data"]["token"] == "GOOD", r)
    r = await flow(URL, "BAD"); check("S7 flow bad token -> invalid_auth", r["errors"] == {"base": "invalid_auth"}, r)
    r = await flow("http://127.0.0.1:1", "GOOD"); check("S7 flow unreachable -> cannot_connect", r["errors"] == {"base": "cannot_connect"}, r)
    r = await flow(f"127.0.0.1:{port}", "GOOD"); check("S7 flow no-scheme/TLS mismatch -> cannot_connect, no crash", r["errors"] == {"base": "cannot_connect"}, r)
    for m in ("html", "500", "wrong_shape", "hang"):
        W["list_mode"] = m; r = await flow(URL, "GOOD")
        check(f"S7 flow list={m} -> cannot_connect (not a false 'success')", r["errors"] == {"base": "cannot_connect"}, r)
    W["list_mode"] = "ok"

    # --- S8 unload ---
    for fn in entry._un: fn()
    check("S8 unload removes coordinator listeners (no leak)", len(c._l) == 0, len(c._l))
    check("overall: no unexpected (non-UpdateFailed) exceptions anywhere", not c.unexpected, c.unexpected)
    server.close()

asyncio.run(asyncio.wait_for(main(), 90))
print(f"\n{sum(res)}/{len(res)} checks passed"); sys.exit(0 if all(res) else 1)
