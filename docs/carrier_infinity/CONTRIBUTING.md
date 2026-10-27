# Contributing to Carrier Infinity (Cloud)

Thanks for helping. This page is for anyone changing the code: where things live, the rules the code keeps, how to
check a change, and how to release one.

## Ground rules

- **Keep it slim.** The integration does one job: a thermostat per zone, outdoor temperature and one electricity
  meter. New entities or options need a good reason.
- **All cloud traffic goes through carrier_api.** The integration never builds its own requests to Carrier.
  [carrier_api](https://github.com/dahlb/carrier_api) knows Carrier's private API and is updated when Carrier changes
  it; the version is pinned in `manifest.json` (see [Updating carrier_api](#updating-carrier_api)).
- **Secrets stay out of the log.** The password and Carrier's tokens must never be logged. `coordinator.py` filters
  the gql library's debug output, and websocket errors are logged as a message only (a traceback can include the
  token, which is part of the websocket address).
- **Never sign in over and over.** A rejected password stops the integration and asks the user (reauth), so a
  wrong password can't lock the Carrier account.
- **The electricity meter only goes up, and its saves keep loading.** Its state is saved by Home Assistant (see
  `extra_restore_state_data` in `sensor.py`). Adding a key is safe; renaming or reshaping one needs a conversion in
  `Electricity.async_added_to_hass` so existing totals carry over. Any change to the meter gets the full 30-year
  simulation before it ships (see below).
- **Entity unique ids never change.** They are `<serial>_<zone id>`, `<serial>_outdoor_temperature` and
  `<serial>_electricity`. Changing one would orphan people's entities, history and Energy dashboard settings.

## Where things live

```
custom_components/carrier_infinity/
  __init__.py      setup and unload of a Carrier account (a config entry)
  const.py         shared constants: domain, refresh interval, timings
  coordinator.py   the cloud connection: 5-minute refresh, websocket, sign-in retry, showing just-written values
  entity.py        the base class: one Home Assistant device per Carrier system
  climate.py       the thermostat for each zone
  sensor.py        outdoor temperature and the lifetime electricity meter
  config_flow.py   the sign-in form and the password-changed form
  translations/    the text shown in the UI
  brand/           the icon and logo
tests/carrier_infinity/
  ha/stubs.py             small stand-ins for Home Assistant (and for carrier_api's network layer)
  ha/test_integration.py  the whole integration against recorded Carrier data
  sim_energy.py           years-long simulation of the electricity meter
  fixtures/               recorded Carrier responses (from carrier_api's tests; see fixtures/README.md)
```

The usual places to make a change:

| To change | Look in |
|---|---|
| How a Carrier mode, activity or fan speed shows in Home Assistant | `MODES`, `FANS` and the properties in `climate.py` |
| What happens when a setting is changed from Home Assistant | the `async_set_*` methods in `climate.py` |
| How long a just-written value wins over the cloud, refresh and reconnect timings | `const.py` |
| Sign-in, refresh, websocket handling | `coordinator.py` |
| The forms and their messages | `config_flow.py` and `translations/en.json` |
| The electricity meter | `Electricity` in `sensor.py` (its module docstring explains the approach) |

The [Development](Development.md) page explains how
data flows from Carrier to the entities.

## Checking a change

You need Python 3.14 (what Home Assistant 2026.9 uses). Then:

```sh
pip install -r tests/carrier_infinity/requirements.txt
```

| Command | Time | When |
|---|---|---|
| `ruff check custom_components tests` and `ruff format custom_components tests` | seconds | every change |
| `python3 tests/carrier_infinity/ha/test_integration.py` | seconds | every change |
| `python3 tests/carrier_infinity/sim_energy.py` | a few minutes (12 years, 6 seeds, all scenarios, on all cores) | any change to `sensor.py` or `coordinator.py` |
| `python3 tests/carrier_infinity/sim_energy.py 30 6` | longer | before releasing a change to the electricity meter |

The simulation plays years of a thermostat hour by hour: restarts, crashes, outages of up to 20 months, bad
readings, and Carrier's quirks (a late New Year, a stale or missing "last year" figure, once-a-day updates). It ends
with `N/N runs within bounds`; each run must finish within a few kWh of Carrier's own figures, allowing only for
data that no meter could have seen.

The tests use stand-ins for Home Assistant (`tests/carrier_infinity/ha/stubs.py`), written to match Home Assistant 2026.9. If Home
Assistant changes an API the integration uses, update the stand-in to match. GitHub Actions runs the lint, the
tests, a 3-year simulation, `hassfest` on every push.

Code style: `ruff` settles formatting and import order (see `pyproject.toml`). Every function and class has a
docstring, and comments say why, not what.

## Documentation

This integration's pages live in [`docs/carrier_infinity/`](.): [README.md](README.md) is its front page, and every other page sits
next to it. When a change alters something a page describes, update that page in the same commit.

## Updating carrier_api

Carrier's API is private and can change. When it does, [carrier_api](https://github.com/dahlb/carrier_api) usually
gets a fix first. A new value Carrier starts sending (a new preset or fan speed, say) also needs a newer carrier_api:
until then the update fails to parse and the entities show unavailable.

1. Change the version in `manifest.json` (`requirements`) and in `tests/carrier_infinity/requirements.txt`.
2. Read carrier_api's changes for anything the integration uses (the `System`, `Status`, `Config` and `Energy`
   models, the `set_*`/`update_*` methods, the websocket).
3. Run the checks above, including `python3 tests/carrier_infinity/sim_energy.py`.

## Releasing

1. Change `version` in `custom_components/carrier_infinity/manifest.json`.
2. Add the release to the top of `CHANGELOG.md` (the tests fail if the two disagree).
3. Run the checks above.
4. Commit and push. To publish a GitHub release, tag it `carrier_infinity-vX.Y.Z` (this folder's name, then the version) so each
   integration's releases stay apart, and attach a zip of the integration's folder.

## Reporting bugs

[Open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose) with your Home Assistant
version, the integration's version, your thermostat's model and software version, what you did and what you expected.
A debug log helps: on the integration's page choose **Enable debug logging**, reproduce the problem, then **Disable
debug logging** to download it. It contains your thermostat's serial number, so check it before posting.
