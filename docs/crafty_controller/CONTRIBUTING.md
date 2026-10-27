# Contributing / maintaining

Thanks for helping out. This file is the map for anyone taking over the code.

## Project layout

```
custom_components/crafty_controller/
├── __init__.py       Set-up/unload: creates the coordinator, forwards to the platforms
├── const.py          DOMAIN, PLATFORMS, poll interval, request timeout, the ERRORS tuple
├── api.py            The one function that calls Crafty (auth, timeout, response checks)
├── coordinator.py    Polls Crafty every 30 s and holds the data for all servers
├── entity.py         Base entity (device, unique ID, availability) + entity creation helper
├── switch.py         On/off switch per server (start_server / stop_server)
├── binary_sensor.py  Online/offline status sensor per server
├── config_flow.py    Set-up form: URL, API token, SSL check
├── manifest.json     Integration metadata (bump "version" on every release)
├── translations/     UI strings for the config flow (en.json)
└── brand/            Icons (icon.png 256 px, icon@2x.png 512 px)
tests/crafty_controller/simulation.py   Dependency-free simulation against a mock Crafty server
```

## How data flows

1. `CraftyCoordinator` calls `GET /servers`, then `GET /servers/{id}/stats` for each server in parallel.
2. `_parse_server()` boils each reply down to `{name, port, running, online}`, stored in `coordinator.data[server_id]`.
3. Entities only read `coordinator.data`. A server missing from `data` is shown as unavailable.
4. Turning the switch on or off calls `POST /servers/{id}/action/start_server` or `stop_server`, then updates the state optimistically; the next poll confirms it.

Crafty API endpoints used (API v2, [spec](https://docs.craftycontrol.com/pages/developer-guide/api-reference/v2/)):

| Call | Used for |
| --- | --- |
| `GET /api/v2/servers` | List servers (name, port); also validates the token in the config flow |
| `GET /api/v2/servers/{id}/stats` | `running` and `int_ping_results` |
| `POST /api/v2/servers/{id}/action/{start_server\|stop_server}` | The switch |

## Conventions

- **Unique IDs are permanent.** `_key` on each entity class (`power`, `status`) feeds the unique ID. Changing it orphans users' existing entities.
- **One error path.** Network and API problems all surface as the `ERRORS` tuple in `const.py`. Catch that tuple, not individual exceptions.
- **Keep it minimal.** The goal is a small integration: on/off, status, port, name. Think twice before adding more.
- Keep comments and docstrings current; the code is meant to be readable by someone new.

## Running the simulation

```
python3 tests/crafty_controller/simulation.py
```

Needs Python 3.12+ and nothing else. It loads the real integration files against stand-ins for Home Assistant, aiohttp and voluptuous, and a mock Crafty server that returns messy data (missing fields, 403s, HTML pages, hangs, removed and added servers, failed actions) and checks the entities and config flow behave. It exits non-zero if any check fails.

It does **not** test real Home Assistant, real HTTP/TLS, or a real Crafty. Always try changes on a real instance too.

## Releasing

1. Update `CHANGELOG.md` and bump `version` in `manifest.json`.
2. Run the simulation and make sure the GitHub *CI* workflow is green.
3. Commit and push. To publish a GitHub release, tag it `crafty_controller-vX.Y.Z` (this folder's name, then the version) so
   each integration's releases stay apart, and attach a zip of the integration's folder.

## Known limitations / ideas

- No reconfigure or re-auth flow: to change the URL or token, remove and re-add the integration.
- A server renamed in Crafty keeps its old device name in Home Assistant until the device is renamed there.
- The smallest set of Crafty API-key permissions that works has not been pinned down; see the [Configuration](Configuration.md) page.
