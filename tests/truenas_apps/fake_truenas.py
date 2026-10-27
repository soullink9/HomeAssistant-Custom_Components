"""A fake TrueNAS and a virtual clock, so months of polling run in seconds.

``Server`` answers the same JSON-RPC calls the integration makes and can be told to misbehave
(drop connections, send garbage, reject the key, hang). ``clock`` is a virtual clock:
``asyncio.sleep`` is replaced so sleeping only moves ``clock.now`` forward.
"""

import asyncio
import collections
import copy
import random

import aiohttp  # the stand-in from tests/truenas_apps/stubs


class Clock:
    """Virtual time in seconds. ``limit`` stops runaway loops."""

    now = 0.0
    limit = float("inf")


clock = Clock()
real_sleep = asyncio.sleep


class StopSim(BaseException):
    """Raised when something sleeps past ``clock.limit``."""


async def virtual_sleep(delay, *args, **kwargs):
    """Replacement for asyncio.sleep: advance the clock, but still let other tasks run."""
    clock.now += delay
    if clock.now > clock.limit:
        raise StopSim()
    await real_sleep(0)


asyncio.sleep = virtual_sleep


def new_app(name, **extra):
    """An app.query record."""
    app = {
        "name": name,
        "state": "RUNNING",
        "version": "1.0.0",
        "latest_version": "1.0.0",
        "upgrade_available": False,
        "metadata": {"icon": f"https://example.invalid/{name}.png"},
    }
    return app | extra


class Server:
    """The fake TrueNAS. Failure knobs are plain attributes the tests set."""

    def __init__(self, seed=1):
        self.rng = random.Random(seed)
        self.key = "KEY"
        self.up = True
        self.apps = {n: new_app(n) for n in ("plex", "sonarr", "radarr")}
        self.pools = {"tank": {"name": "tank", "size": 10**13, "allocated": 4 * 10**12, "free": 6 * 10**12}}
        self.new_version = None  # set to e.g. "25.10.8" to simulate a pending system update
        self.deny = set()  # methods that answer "Not authorized"
        self.drift = None  # function(method, result) -> result, to change the API's shape
        # probabilities (0..1) of misbehaving on any given call
        self.p_conn_fail = self.p_close = self.p_error = self.p_notify = self.p_badjson = self.p_job_fail = 0.0
        self.hang_connect = False  # connections never complete
        self.hang_forever = False  # ...and never even time out by themselves
        self.job_mode = "ok"  # ok | fail | stuck | pruned | fail_if_stopped
        self.job_secs = 20
        self.jobs = {}
        self.next_job = 1
        self.counts = collections.Counter()
        self.open = 0
        self.max_open = 0

    # --- aiohttp-like session ---
    def ws_connect(self, url, **kwargs):
        """What ``session.ws_connect`` does."""
        assert url.startswith("wss://"), url
        return _Connection(self)

    # --- jobs ---
    def _job_state(self, job):
        if self.job_mode == "stuck" or clock.now < job["t0"] + self.job_secs:
            return "RUNNING"
        return "FAILED" if job["fail"] else "SUCCESS"

    def settle(self):
        """Apply the result of every finished job to the app it belonged to."""
        for job in self.jobs.values():
            if job.get("done") or self._job_state(job) == "RUNNING":
                continue
            job["done"] = True
            app = self.apps.get(job["app"])
            if not app:
                continue
            if self._job_state(job) == "FAILED":
                app["state"] = {"app.stop": "STOPPED", "app.upgrade": "RUNNING"}.get(job["method"], "CRASHED")
            elif job["method"] == "app.stop":
                app["state"] = "STOPPED"
            else:
                app["state"] = "RUNNING"
                if job["method"] == "app.upgrade":
                    app["version"], app["upgrade_available"] = app["latest_version"], False

    # --- the API ---
    def handle(self, ws, msg):
        """Answer one JSON-RPC request."""
        method, params, msg_id = msg["method"], msg.get("params", []), msg["id"]

        def ok(result):
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}

        def err(text):
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -1, "message": text}}

        if method == "auth.login_with_api_key":
            ws.authed = bool(params) and params[0] == self.key
            self.counts["login_ok" if ws.authed else "login_fail"] += 1
            return ok(ws.authed)
        if not ws.authed:
            return err("Not authenticated")
        if method in self.deny:
            return err("Not authorized")
        if self.rng.random() < self.p_error:
            return err("Internal error")
        self.settle()
        if method == "app.query":
            result = [dict(a) for a in self.apps.values()]
        elif method == "pool.query":
            result = [dict(p) for p in self.pools.values()]
        elif method == "system.version_short":
            result = "25.10.7"
        elif method == "update.status":
            new = {"version": self.new_version, "manifest": {}} if self.new_version else None
            result = {"code": "NORMAL", "status": {"new_version": new}}
        elif method == "webui.main.dashboard.sys_info":
            result = {"hostname": "thevault", "version": "TrueNAS-25.10.7", "codename": "Goldeye", "license": None}
        elif method == "truenas.is_ix_hardware":
            result = False
        elif method in ("app.start", "app.stop", "app.redeploy", "app.upgrade"):
            app = self.apps.get(params[0])
            if app is None:
                return err("App not found")
            job_id, self.next_job = self.next_job, self.next_job + 1
            fail = (
                self.job_mode == "fail"
                or self.rng.random() < self.p_job_fail
                or (self.job_mode == "fail_if_stopped" and method == "app.stop" and app["state"] == "STOPPED")
            )
            self.jobs[job_id] = {"t0": clock.now, "method": method, "app": params[0], "fail": fail}
            app["state"] = "DEPLOYING"
            self.counts["jobs_started"] += 1
            return ok(job_id)
        elif method == "core.get_jobs":
            job_id = params[0][0][2]
            job = self.jobs.get(job_id)
            self.counts["get_jobs"] += 1
            if job is None or (self.job_mode == "pruned" and self._job_state(job) != "RUNNING"):
                result = []
            else:
                state = self._job_state(job)
                result = [{"id": job_id, "state": state, "error": "boom" if job["fail"] else None}]
        else:
            return err("Method not found")
        if self.drift:
            result = self.drift(method, copy.deepcopy(result))
        return ok(result)


class _Connection:
    """Async context manager returned by ``ws_connect``."""

    def __init__(self, server):
        self.server = server

    async def __aenter__(self):
        await real_sleep(0)
        s = self.server
        s.counts["connect"] += 1
        if not s.up or s.rng.random() < s.p_conn_fail:
            raise aiohttp.ClientConnectorError("down")
        if s.hang_connect:
            if s.hang_forever:
                await asyncio.Event().wait()
            await virtual_sleep(300)  # aiohttp's default total timeout is 5 minutes
            raise TimeoutError
        s.open += 1
        s.max_open = max(s.max_open, s.open)
        self.ws = _Socket(s)
        return self.ws

    async def __aexit__(self, *exc):
        self.server.open -= 1
        self.ws.closed = True


class _Socket:
    """The websocket. Replies are queued by ``send_json`` and handed out by ``receive_json``."""

    def __init__(self, server):
        self.server = server
        self.queue = collections.deque()
        self.authed = False
        self.closed = False

    async def send_json(self, msg):
        s = self.server
        s.counts["rpc"] += 1
        s.counts[msg["method"]] += 1
        if s.rng.random() < s.p_notify:  # a push notification that isn't the answer
            self.queue.append({"jsonrpc": "2.0", "method": "collection_update", "params": {}})
        if s.rng.random() < s.p_close:
            self.queue.append("CLOSE")
            return
        if s.rng.random() < s.p_badjson:
            self.queue.append("BADJSON")
            return
        self.queue.append(s.handle(self, msg))

    async def receive_json(self, timeout=None):
        await real_sleep(0)  # real sockets yield to the event loop
        item = self.queue.popleft()
        if item == "CLOSE":
            raise TypeError("Received message 257:None is not WSMsgType.TEXT")
        if item == "BADJSON":
            raise ValueError("Expecting value")
        return item


class Session:
    """Stands in for the aiohttp client session Home Assistant hands out."""

    def __init__(self, server):
        self.server = server

    def ws_connect(self, url, **kwargs):
        return self.server.ws_connect(url, **kwargs)
