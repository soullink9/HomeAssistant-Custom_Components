# Development

For anyone changing the code. [CONTRIBUTING.md](CONTRIBUTING.md) has the rules the code keeps, the file map, how to
check a change and how to release. This page explains how data flows.

## One account, one coordinator

`CarrierCoordinator` (in `coordinator.py`) is created per Carrier account and owns the cloud connection
(`carrier_api.ApiConnectionGraphql`). Its `data` is `{system serial: carrier_api System}`.

- **Full refresh, every 5 minutes** (`FULL_REFRESH`): `api.load_data()` loads every system. If the saved session has
  expired, it signs in again once with the password; a rejected password raises `ConfigEntryAuthFailed`, which stops
  updates and starts the reauth form. Carrier data the library can't parse (`KeyError`, `ValueError`) becomes
  `UpdateFailed`, so entities go unavailable until a refresh parses again.
- **Websocket, in between:** `websocket_loop` runs as a config-entry background task. Carrier pushes changes;
  `WebsocketDataUpdater` patches the loaded `System` objects in place, and the coordinator redraws the entities. A
  dropped socket reconnects after 10 seconds, doubling each time up to 10 minutes, and back to 10 seconds once it has
  stayed up for 5 minutes. While waiting for a new password, it doesn't reconnect.

## Showing just-written values

After Home Assistant changes something, Carrier's cloud keeps reporting (and re-broadcasting) the old value for a few
minutes. So each change records the values it produces with `coordinator.expect(key, value)`, and
`coordinator.shown(key, actual)` returns that value for `EXPECT_SECONDS` (5 minutes) instead of Carrier's. Keys are
`(serial, zone id, field)`, with zone `None` for the system-wide mode.

## Entities

- `entity.py`: `CarrierEntity`, one device per system (identified by serial). Unavailable when Carrier stops listing
  the system or reports it disconnected.
- `climate.py`: `CarrierZone`, one per zone. It reads the zone's **configuration** (activities, setpoints, hold) and
  **status** (temperature, humidity, conditioning). Setpoints come from the configuration of the running activity,
  which Carrier updates sooner than the status. Setting a temperature writes the manual activity and holds it;
  `Resume schedule` works out which activity the schedule resumes on a copy of the zone without its hold, so the
  display is right straight away.
- `sensor.py`: `OutdoorTemperature`, and `Electricity`, the lifetime meter. Its module docstring explains how
  Carrier's yearly figures become one total; its state is saved with `extra_restore_state_data`.

## Tests

```sh
pip install -r tests/carrier_infinity/requirements.txt
python3 tests/carrier_infinity/ha/test_integration.py
python3 tests/carrier_infinity/sim_energy.py
```

- `ha/test_integration.py` runs the whole integration against stand-ins for Home Assistant (`ha/stubs.py`) and
  recorded Carrier data (`fixtures/`, from carrier_api's test suite): the refresh and re-sign-in, reauth, websocket
  messages, every control, the sensors, the setup forms, and that the manifest version matches the newest changelog
  entry. Nothing touches Carrier's cloud.
- `sim_energy.py` plays years of a thermostat hour by hour (restarts, crashes, outages of up to 20 months, bad
  readings, Carrier's New Year quirks) and checks the electricity meter ends within a few kWh of Carrier's figures.
  `python3 tests/carrier_infinity/sim_energy.py 30 6` is the full check before releasing a meter change.

CI runs the integration tests, a 3-year simulation, `ruff` and Home Assistant's `hassfest` on every push.
