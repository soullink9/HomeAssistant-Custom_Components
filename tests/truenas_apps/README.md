# Tests

Run everything with `python3 tests/truenas_apps/test_integration.py` (add a number to change how many simulated days the
long-run checks cover, default 30; the full check before a release is 90).

The tests use a **fake TrueNAS** (`fake_truenas.py`) and tiny stand-ins for Home Assistant and aiohttp
(`stubs/`), so they need no installs and no real server, and months of polling take seconds.

What this does and does not prove:

- It exercises the integration's own code paths: polling, failure handling, app actions, entity values,
  device removal.
- It does **not** run real Home Assistant, so it can't catch a mismatch with Home Assistant's own API.
  That is what the `hassfest` job in CI and trying the integration in a real Home Assistant are for.
