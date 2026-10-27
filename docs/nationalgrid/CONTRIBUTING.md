# Contributing to the National Grid integration

Thanks for helping. This page is for anyone changing the code: where things live, the rules the code keeps,
how to check a change, and how to release one.

## Ground rules

- **Keep it slim.** The whole integration is a few hundred lines. Prefer a small, clear change over a new layer.
- **Only National Grid is contacted, and only through [py-nationalgrid](https://github.com/virtitnerd/py-nationalgrid).**
  No other services, analytics or update checks. If National Grid changes its API, the fix belongs in the library;
  here we only bump the pinned version in `manifest.json`.
- **Never rename an ID people depend on.** The statistic IDs (`nationalgrid:<service point>_energy`, `_return`,
  `_cost`, `_compensation`) are what users pick in their Energy dashboard, and the sensors' unique IDs
  (`<service point>_power` and so on) keep their entity IDs and history. Renaming either silently breaks
  existing setups.
- **Running totals must always add up.** Every statistic row carries a running total. Any change that rewrites
  past hours must rewrite every row after them too (`_update_meter` in `coordinator.py` already does this).
- **Do hour math in UTC.** Adding an hour in local time skips the repeated hour when daylight saving time ends.
  Use `_hour()` in `coordinator.py`.

## Where things live

The [Development](Development.md) page has the full file map. The usual places to make a change:

| To change | Look in |
|---|---|
| Timings: poll interval, how far back the daily correction reaches, retry delays | `const.py` |
| How usage is fetched and written to the Energy dashboard statistics | `coordinator.py`, `_update_meter` (numbered steps) |
| How cost rates are worked out from bills | `coordinator.py`, `_update_rates` and `rate` |
| Which meters are included | `coordinator.py`, `_find_meters` |
| The sensors | `sensor.py` |
| The setup and re-authentication form | `config_flow.py`, with its text in `translations/en.json` |
| The icon | `brand/icon.png` (256×256) and `brand/icon@2x.png` (512×512) |

**Rebuilding everyone's history:** if a change means stored hours are wrong (not just future ones), bump
`HISTORY_VERSION` in `const.py`. Every installation then re-imports its full history once after updating.

## Checking a change

You need Python 3.13. Nothing else is needed for the simulation; `ruff` is the only tool to install.

| Command | When |
|---|---|
| `ruff check custom_components tests` and `ruff format custom_components tests` | every change |
| `python3 tests/nationalgrid/test_simulation.py` | every change (takes a few seconds) |

The simulation runs the real integration code against stand-ins for Home Assistant (`tests/nationalgrid/stubs.py`) and a fake
National Grid, polling every 15 minutes for nine days through a daylight saving change, outages, a Home Assistant
restart and a new bill. It checks every stored hour against the true usage and prints `all checks passed` when
all is well. When you fix a bug, add the situation that caused it to the scenario so it stays fixed.

GitHub Actions runs `ruff`, the simulation, Home Assistant's `hassfest` on every push.

Code style: `ruff` settles formatting and import order (see `pyproject.toml`). Every function and class has a
docstring, and comments say why, not what.

## Documentation

This integration's pages live in [`docs/nationalgrid/`](.): [README.md](README.md) is its front page, and every other page sits
next to it. When a change alters something a page describes, update that page in the same commit.

## Releasing

1. Change `version` in `custom_components/nationalgrid/manifest.json`.
2. Add the release to `CHANGELOG.md`.
3. Run the checks above.
4. Commit and push. To publish a GitHub release, tag it `nationalgrid-vX.Y.Z` (this folder's name, then the version) so each
   integration's releases stay apart, and attach a zip of the integration's folder.

## Reporting bugs

Open an issue with your Home Assistant version, the integration's version, what you did and what you expected.
The log helps: **Settings → System → Logs**, search for `nationalgrid`. Remove your email, account and meter
numbers before posting.
