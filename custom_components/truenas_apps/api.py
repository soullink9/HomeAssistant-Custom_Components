"""Talking to TrueNAS: a short-lived JSON-RPC 2.0 websocket connection.

TrueNAS exposes its API at wss://<host>/api/current. We open a connection, log in
with the API key, ask what we need, and close it again. Nothing stays connected
between polls, so a TrueNAS reboot or network drop can never leave us half-open.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from aiohttp import ClientError
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CALL_TIMEOUT, POLL_TIMEOUT

# call("app.query", [args]) -> the "result" of the reply
Call = Callable[..., Awaitable[Any]]


@asynccontextmanager
async def connect(hass: HomeAssistant, data: dict) -> AsyncIterator[Call]:
    """Open the websocket, log in, and yield a ``call(method, params)`` coroutine.

    Raises PermissionError for a rejected API key, aiohttp.ClientError for network
    trouble, and RuntimeError when TrueNAS answers a request with an error.
    """
    session = async_get_clientsession(hass, data[CONF_VERIFY_SSL])
    async with session.ws_connect(f"wss://{data[CONF_HOST]}/api/current") as ws:
        msg_id = 0

        async def call(method: str, params: list | None = None) -> Any:
            """Send one request and return its result."""
            nonlocal msg_id
            msg_id += 1
            await ws.send_json({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or []})
            while True:
                try:
                    reply = await ws.receive_json(timeout=CALL_TIMEOUT)
                except (TypeError, ValueError) as err:  # socket closed, or a frame that isn't JSON
                    raise ClientError(f"{method}: connection closed or bad frame") from err
                # TrueNAS may also push notifications; only the reply with our id is the answer.
                if isinstance(reply, dict) and reply.get("id") == msg_id:
                    break
            if "error" in reply:
                raise RuntimeError(reply["error"].get("message", "RPC error"))
            return reply.get("result")

        if await call("auth.login_with_api_key", [data[CONF_API_KEY]]) is not True:
            raise PermissionError("Invalid API key")
        yield call


async def optional(call: Call, method: str) -> Any:
    """Call a method that may be refused (e.g. the API key lacks a role) without failing the poll.

    Returns None when TrueNAS refuses; the matching entities then show as unavailable.
    """
    try:
        return await call(method)
    except RuntimeError:
        return None


async def rpc(hass: HomeAssistant, data: dict, method: str, params: list | None = None) -> Any:
    """Connect, make one call, disconnect. Used by the setup form to test credentials."""
    async with asyncio.timeout(POLL_TIMEOUT), connect(hass, data) as call:
        return await call(method, params)
