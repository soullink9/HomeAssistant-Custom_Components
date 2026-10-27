"""TrueNAS Apps: Docker apps from TrueNAS in Home Assistant (status, updates and controls).

File map: ``api.py`` talks to TrueNAS, ``coordinator.py`` polls it and runs actions,
``entity.py`` has the shared entity bases, and ``sensor.py``/``switch.py``/``button.py``/
``update.py`` are the entity platforms. ``config_flow.py`` is the setup form.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import TrueNASConfigEntry, TrueNASCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: TrueNASConfigEntry) -> bool:
    """Create the coordinator, do the first poll, then load the entity platforms."""
    entry.runtime_data = TrueNASCoordinator(hass, entry)
    await entry.runtime_data.async_config_entry_first_refresh()  # raises (and retries later) if TrueNAS is down
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TrueNASConfigEntry) -> bool:
    """Unload the platforms (the coordinator goes away with the entry)."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(hass: HomeAssistant, entry: TrueNASConfigEntry, device: DeviceEntry) -> bool:
    """Let the user delete an app's device from the UI, but only once the app is gone from TrueNAS."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None or coordinator.data is None:  # not loaded, so we can't tell what still exists
        return False
    live = {entry.entry_id} | {f"{entry.entry_id}_{app}" for app in coordinator.data["apps"]}
    if any(ident in live for domain, ident in device.identifiers if domain == DOMAIN):
        return False  # the TrueNAS device itself, or an app that still exists
    # Reload afterwards so an app that is reinstalled later gets fresh entities.
    hass.config_entries.async_schedule_reload(entry.entry_id)
    return True
