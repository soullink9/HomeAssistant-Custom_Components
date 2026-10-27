# Contributing to TrueNAS Apps

Thanks for helping. This page is for anyone changing the code: where things live, the rules the code keeps, how
to check a change, and how to release one.

## Ground rules

- **Stay slim.** The integration deliberately exposes only Docker apps, their status and updates, controls, pool
  usage and the TrueNAS system update. Please open an issue before adding a new kind of entity.
- **No dependencies.** `manifest.json` has no `requirements`. The websocket client is the `aiohttp` that ships
  with Home Assistant, and the API is plain JSON-RPC.
- **No JavaScript, no custom cards.** Dashboards use Home Assistant's built-in cards (see `examples/truenas_apps/`).
- **Never install a TrueNAS system update from Home Assistant.** That should stay a deliberate action in the
  TrueNAS UI, after a backup. `SystemUpdate.async_install` refuses on purpose.
- **Never let a failure escape unseen.** Polling failures become `UpdateFailed` (entities go unavailable and retry);
  background actions end in a persistent notification; everything has a timeout.
- **Keep unique ids stable.** Changing them orphans every user's entities.

## Where things live

| File | What it does |
|---|---|
| `const.py` | The domain, the platform list and every timing number. |
| `api.py` | The websocket connection: connect, log in, `call(method, params)`. |
| `coordinator.py` | Polls TrueNAS once a minute and runs start/stop/restart/upgrade jobs in the background. |
| `entity.py` | Base classes (`AppEntity`, `SystemEntity`) and `add_per_item`, which adds entities for new apps and pools. |
| `sensor.py`, `switch.py`, `button.py`, `update.py` | One entity platform each. |
| `config_flow.py` | Setup, reconfigure and re-authentication share one form. |
| `__init__.py` | Entry setup/unload and deleting an app's device. |
| `translations/en.json` | Text for the setup form. |
| `brand/` | The integration's icon (used by Home Assistant 2026.3 and newer, no brands repository needed). |

**Adding a button:** add a line to `BUTTONS` in `button.py` (name, device class, the `app.*` methods to run).

**Asking TrueNAS for something new:** add the call to `_async_update_data` in `coordinator.py` (use `optional()` if a
limited API key might not be allowed), add its result to the returned dict, and document the key in the class
docstring.

## Checking a change

You need Python 3.13 and [ruff](https://docs.astral.sh/ruff/) (`pip install ruff`).

| Command | When |
|---|---|
| `ruff check custom_components tests` and `ruff format custom_components tests` | every change |
| `python3 tests/truenas_apps/test_integration.py` | every change (seconds) |
| `python3 tests/truenas_apps/test_integration.py 90` | before a release (90 simulated days) |

The tests use a fake TrueNAS and small stand-ins for Home Assistant, so they can't prove the integration works
with real Home Assistant. Try a change on a real instance too. CI also runs `hassfest`.
See [tests/truenas_apps/README.md](../../tests/truenas_apps/README.md).

Code style: `ruff` settles formatting and import order (see `pyproject.toml`). Every function and class has a
docstring, and comments say why, not what.

## Documentation

This integration's pages live in [`docs/truenas_apps/`](.): [README.md](README.md) is its front page, and every other page sits
next to it. When a change alters something a page describes, update that page in the same commit.

## Releasing

1. Change `version` in `custom_components/truenas_apps/manifest.json`.
2. Add the release to `CHANGELOG.md`.
3. Run the checks above.
4. Commit and push. To publish a GitHub release, tag it `truenas_apps-vX.Y.Z` (this folder's name, then the version) so each
   integration's releases stay apart, and attach a zip of the integration's folder.

## Reporting bugs

Open an issue with your Home Assistant, TrueNAS and integration versions, what you did and what you expected.
The log helps: **Settings → System → Logs**, search for `truenas_apps`. Remove API keys and hostnames you don't
want public before posting.
