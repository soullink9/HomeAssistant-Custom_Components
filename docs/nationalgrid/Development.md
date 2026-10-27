# Development

For anyone changing the code. [CONTRIBUTING.md](CONTRIBUTING.md) has the rules the code keeps, how to check a change
and how to release.

## Files

```
custom_components/nationalgrid/
  __init__.py        sets up and unloads a login (a config entry); statistics stay when it's removed
  const.py           the domain, the statistic keys, and every timing (poll, settle window, retries)
  coordinator.py     everything that talks to National Grid and writes the statistics
  sensor.py          the four sensors per meter
  config_flow.py     the sign-in form, also used for re-authentication
  manifest.json      metadata, version and the pinned py-nationalgrid
  translations/en.json   form text
  brand/             icon.png, icon@2x.png
tests/nationalgrid/
  stubs.py           stand-ins for the parts of Home Assistant the integration uses
  test_simulation.py nine days against a fake National Grid
docs/nationalgrid/   these pages
```

## How data flows

`NationalGridCoordinator._async_update_data` runs every 15 minutes:

1. On the first poll it finds the meters (`_find_meters`): every electric smart meter on every linked account.
2. Every 12 hours it reads bill history and works out each bill period's rate and the blended rate
   (`_update_rates`). A new bill schedules its period to be rewritten.
3. On the first poll of each day it schedules the last four days to be rewritten (`SETTLE` in `const.py`).
4. For each meter, `_update_meter` runs seven numbered steps: find where each statistic ends, pick the first hour to
   write, load stored hours and the running totals before it, fetch settled data, fetch real-time reads, walk the
   hours choosing the best data for each, and save.

The coordinator's `data` is each meter's recent real-time reads, which the sensors read. The Energy dashboard reads
the statistics, written with `async_add_external_statistics`.

**Choosing data for an hour:** settled data wins; then a complete real-time hour; a recent incomplete hour stops the
walk until the next poll; an older incomplete hour uses what there is (or what was stored) until settled data
replaces it.

**Re-importing everyone's history:** bump `HISTORY_VERSION` in `const.py`. The version that's been imported is kept in
the config entry's data under `history`.

## Tests

```sh
python3 tests/nationalgrid/test_simulation.py
```

Plain Python 3.13, nothing to install. It polls every 15 minutes from a fresh install through nine days that include
the end of daylight saving time, a meter outage only settled data knows about, outages of the settled service and of
everything, Home Assistant off for 36 hours and restarted from scratch, a new bill mid-month, and solar export. At the
end every statistic must be continuous, running totals must add up, settled hours must match the truth exactly, and
every cost must equal energy × that hour's rate. It prints `all checks passed` when all is well.

The stand-ins can't prove the integration works with real Home Assistant or real National Grid data; try changes
on a real installation too. CI also runs `ruff` and Home Assistant's `hassfest`.
