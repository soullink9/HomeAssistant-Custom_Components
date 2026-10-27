"""Carrier Infinity (cloud) for Home Assistant.

Connects to the same Carrier cloud account as the Carrier app (through the carrier_api library) and
creates one climate entity per zone, plus outdoor temperature and lifetime electricity sensors.

File map:
- const.py        shared constants (domain, timings)
- coordinator.py  the cloud connection, the 5-minute refresh and the websocket
- entity.py       the base class (one device per Carrier system)
- climate.py      the zone thermostats
- sensor.py       outdoor temperature and the lifetime electricity meter
- config_flow.py  the sign-in form and the "password changed" form
- translations/   the text shown in the UI (forms, errors, entity and preset names)
- brand/          the icon and logo Home Assistant shows for the integration
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import CarrierConfigEntry, CarrierCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: CarrierConfigEntry) -> bool:
    """Set up one Carrier account: sign in, load the systems, start the websocket, add the entities."""
    coordinator = CarrierCoordinator(hass, entry)
    entry.async_on_unload(coordinator.api.cleanup)  # close the cloud session on unload (or failed setup)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # A background task tied to the entry: Home Assistant cancels it when the entry unloads.
    entry.async_create_background_task(hass, coordinator.websocket_loop(), "carrier_websocket")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CarrierConfigEntry) -> bool:
    """Unload the entities; the websocket task and cloud session are closed by the hooks above."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
