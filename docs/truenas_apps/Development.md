# Development

The full contributor guide is [CONTRIBUTING.md](CONTRIBUTING.md).
This page is the quick map.

## Files

```
custom_components/truenas_apps/
  __init__.py        entry setup/unload, deleting an app's device
  const.py           domain, platforms, timing numbers
  api.py             websocket connection and JSON-RPC calls
  coordinator.py     polling + background app actions
  entity.py          base entity classes, adds entities for new apps/pools
  sensor.py switch.py button.py update.py   one entity platform each
  config_flow.py     setup / reconfigure / re-auth form
  translations/en.json   form text
  brand/             icon.png, icon@2x.png
tests/truenas_apps/
  test_integration.py  the test run
  fake_truenas.py      a fake TrueNAS plus a virtual clock
  stubs/               tiny stand-ins for Home Assistant and aiohttp
examples/truenas_apps/
  system_information_card.yaml
```

## How it works

1. `coordinator.py` opens a connection (`api.connect`), logs in with the API key, calls `app.query`, `pool.query`,
   `system.version_short` and (optionally) `update.status`, `webui.main.dashboard.sys_info`, `truenas.is_ix_hardware`,
   and closes it. The result is one dict that every entity reads.
2. Entities never talk to TrueNAS themselves, except through `coordinator.app_action`, which starts a job
   (`app.start`, `app.stop`, `app.redeploy`, `app.upgrade`), waits for it via `core.get_jobs`, shows the outcome and refreshes.
3. `entity.add_per_item` creates entities for every app and pool now and for any that appear later.

## Tests

`python3 tests/truenas_apps/test_integration.py [days]` runs the real integration against a fake TrueNAS on a virtual clock (a
simulated month in a few seconds; use 90 days before a release). It covers normal running, flaky networks, a revoked
key, odd websocket frames, hangs and outages, apps and pools coming and going, API changes, and every control. It
uses stand-ins instead of real Home Assistant, so real-world testing and the CI `hassfest` check still matter.