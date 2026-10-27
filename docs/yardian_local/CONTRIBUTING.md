# Contributing to Yardian Local

Thanks for helping. This page is for anyone changing the code: where things live, the rules the code keeps,
how to check a change, and how to release one.

## Ground rules

- **Local only.** The integration talks to the controller's address the user enters, and nothing else. No cloud
  calls, update checks or analytics.
- **Every start has a duration.** Nothing may start a zone without a run time. That's what lets the controller stop
  a zone on its own when Home Assistant is down; it is the project's main safety promise.
- **Never water twice in a day.** The blueprint decides a day is handled from the automation's `last_triggered` and
  the integration's **Last watering** sensor. `async_mark_start` saves that time immediately (not with the usual
  delay) so it survives a power cut. Keep both when changing either side.
- **No helpers.** Users set everything in the UI; settings the integration needs (run times, flow rates) are its own
  number entities.
- **Saved data must keep loading.** `.storage/yardian_local.<entry_id>.water` holds `{"water": {zone: total},
  "last_start": iso}`; `async_load` in `coordinator.py` also reads the older `{zone: total}` form. Entity unique IDs
  (`<yid>_<key>`) must never change, or users lose their entities and Energy history.
- **One dependency.** `pyyardian`, pinned in `manifest.json` to the version Home Assistant Core's own Yardian
  integration uses. Bump it only when Core does.

## Where things live

The [Development](Development.md) page has the full file map. The usual places to make a change:

| To change | Look in |
|---|---|
| Poll interval, save timing, defaults | `custom_components/yardian_local/const.py` |
| Polling, the water estimate, saved data, last watering | `coordinator.py` |
| What a kind of entity shows | the platform file: `switch.py`, `number.py`, `sensor.py`, `binary_sensor.py`, `button.py` |
| Actions | `services.py` (`notify`), `switch.py` (`start_irrigation`); describe them in `services.yaml` and `translations/en.json` |
| Setup form | `config_flow.py`, labels in `translations/en.json` |
| The schedule, skips, recovery and notifications | `blueprints/automation/yardian/yardian_lawn_schedule.yaml` (its header comment maps the flow) |

**Adding an entity:** add the class to the matching platform file with a new, permanent `key`, read its value from
`coordinator.data` (or a coordinator attribute for Home Assistant-side values), and list it on the
[Entities and Actions](Entities-and-Actions.md) page.

**Changing the start time calculation:** it exists twice in the blueprint (the `schedule` trigger and the `start_ts`
variable). Change both the same way; `tests/yardian_local/check_blueprint.py` fails if they differ.

## Checking a change

You need Python 3.13.

```sh
pip install ruff pyyaml jinja2
```

| Command | Time | When |
|---|---|---|
| `ruff check custom_components tests` and `ruff format custom_components tests` | seconds | every change |
| `python3 tests/yardian_local/check_blueprint.py` | seconds | any blueprint change |
| Install on a test Home Assistant and run one zone for a minute | a few minutes | before every release |

GitHub Actions runs ruff, the blueprint check, `hassfest` on every push. There are no automated
tests against a real or simulated controller yet; a pull request adding them is welcome.

Code style: `ruff` settles formatting and import order (see `pyproject.toml`). Every module, class and function has a
docstring, and comments say why, not what.

## Documentation

This integration's pages live in [`docs/yardian_local/`](.): [README.md](README.md) is its front page, and every other page sits
next to it. When a change alters something a page describes, update that page in the same commit.

## Releasing

1. Change `version` in `custom_components/yardian_local/manifest.json`.
2. Add the release to `CHANGELOG.md`.
3. Run the checks above, and try the release on a real controller.
4. Commit and push. To publish a GitHub release, tag it `yardian_local-vX.Y.Z` (this folder's name, then the version) so each
   integration's releases stay apart, and attach a zip of the integration's folder.

## Reporting bugs

Open an issue with your Home Assistant version, the Yardian Local version, your controller model, what you did and
what you expected. Two things help most: the log (**Settings → System → Logs**, search for `yardian_local`) and, for
anything the controller reports, the diagnostics file (**Settings → Devices & services → Yardian Local → ⋮ →
Download diagnostics**; identifiers are removed). For a schedule problem, add the automation's trace
(**Settings → Automations**, open it, ⋮ → **Traces**).
