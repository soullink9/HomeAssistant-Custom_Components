import asyncio
from typing import Generic, TypeVar

T = TypeVar("T")


class ConfigEntry(Generic[T]):
    def __init__(self, entry_id="E1", data=None):
        self.entry_id, self.data = entry_id, data or {}
        self._unload, self.bg, self.bg_errors = [], [], []

    def async_on_unload(self, cb):
        self._unload.append(cb)

    def async_create_background_task(self, hass, coro, name):
        t = asyncio.get_running_loop().create_task(coro, name=name)
        self.bg.append(t)

        def done(t):
            if not t.cancelled() and t.exception() is not None:
                self.bg_errors.append(type(t.exception()).__name__)

        t.add_done_callback(done)
        return t


ConfigFlowResult = dict


class ConfigFlow:
    def __init_subclass__(cls, domain=None, **kw):
        cls.domain = domain
