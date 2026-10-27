# Contributing

Thanks for helping. Each integration has its own guide with the rules its code keeps, where things live and how to
check a change:

| Integration | Guide |
|---|---|
| Carrier Infinity (Cloud) | [docs/carrier_infinity/CONTRIBUTING.md](docs/carrier_infinity/CONTRIBUTING.md) |
| Crafty Controller | [docs/crafty_controller/CONTRIBUTING.md](docs/crafty_controller/CONTRIBUTING.md) |
| CWFIS | [docs/cwfis/Development.md](docs/cwfis/Development.md) |
| Life RPG | [docs/life_rpg/CONTRIBUTING.md](docs/life_rpg/CONTRIBUTING.md) |
| National Grid | [docs/nationalgrid/CONTRIBUTING.md](docs/nationalgrid/CONTRIBUTING.md) |
| TrueNAS Apps | [docs/truenas_apps/CONTRIBUTING.md](docs/truenas_apps/CONTRIBUTING.md) |
| Yardian Local | [docs/yardian_local/CONTRIBUTING.md](docs/yardian_local/CONTRIBUTING.md) |

## How the repository is laid out

Every integration uses its folder name (its Home Assistant domain) in the same four places:

```
custom_components/<domain>/   the integration itself: what gets copied into Home Assistant
docs/<domain>/                its pages: README.md (front page), CHANGELOG.md, CONTRIBUTING.md and the rest
tests/<domain>/               its tests; run them from the repository root
examples/<domain>/            copy-and-paste dashboards and automations, where it has any
```

Yardian's watering blueprint lives in `blueprints/automation/yardian/`, the path Home Assistant expects.

Run everything from the repository root. `ruff check` and `ruff format` cover the whole repository with the settings
in `pyproject.toml`; each integration's guide lists its own tests. GitHub Actions runs the lint, every integration's
tests and Home Assistant's `hassfest` on every push and once a week.

## Releasing

1. Change `version` in the integration's `manifest.json` (Life RPG has three more places; see its guide).
2. Add the release to the integration's `CHANGELOG.md` under `docs/<domain>/`.
3. Run its checks.
4. Commit and push. To publish a GitHub release, tag it `<domain>-vX.Y.Z` (for example `truenas_apps-v1.1.0`) so
   each integration's releases stay apart, and attach a zip of its `custom_components/<domain>` folder.

## Reporting bugs

[Open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose) and pick the form for
the integration. Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
