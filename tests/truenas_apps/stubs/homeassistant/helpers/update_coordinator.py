import collections
from typing import Generic, TypeVar
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

T = TypeVar("T")


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator(Generic[T]):
    """Mirrors HA semantics: UpdateFailed -> unavailable; other exceptions -> logged + unavailable;
    ConfigEntryAuthFailed -> reauth started and polling stops."""

    def __init__(self, hass, logger, *, config_entry=None, name=None, update_interval=None):
        self.hass, self.config_entry, self.update_interval = hass, config_entry, update_interval
        self.data, self.last_update_success, self.auth_failed = None, True, False
        self.listeners, self.failed, self.unexpected = [], collections.Counter(), collections.Counter()

    def async_add_listener(self, cb, context=None):
        self.listeners.append(cb)
        return lambda: self.listeners.remove(cb)

    async def async_refresh(self):
        try:
            self.data = await self._async_update_data()
            self.last_update_success = True
        except UpdateFailed as e:
            self.last_update_success = False
            self.failed[type(e.__cause__).__name__] += 1
        except ConfigEntryAuthFailed:
            self.last_update_success = False
            self.auth_failed = True
        except Exception as e:  # HA logs "Unexpected error fetching ..." with a traceback each time
            self.last_update_success = False
            self.unexpected[type(e).__name__] += 1
        for cb in list(self.listeners):
            cb()

    def async_update_listeners(self):
        for cb in list(self.listeners):
            cb()

    async_request_refresh = async_refresh

    async def async_config_entry_first_refresh(self):
        await self.async_refresh()
        if not self.last_update_success:
            raise ConfigEntryNotReady


class CoordinatorEntity(Generic[T]):
    def __init__(self, coordinator, context=None):
        self.coordinator = coordinator

    @property
    def available(self):
        return self.coordinator.last_update_success
