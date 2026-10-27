# Disclosure

This project was primarily created for personal use and for my family. While I may provide updates, they are not guaranteed. However, if you've stumbled upon this and find it interesting, feel free to download and use it. I had a great time building this and hope you enjoy it.

Note: Built with the assistance of Claude.ai. I’m putting it here now so you don't have to hunt for it below.

# Home Assistant Custom Components

My custom integrations for Home Assistant, all in one place. Each one is set up entirely in the UI: no YAML and no
helpers to create.

| Integration | What it does | Learn more |
|---|---|---|
| **Carrier Infinity (Cloud)** | Carrier Infinity thermostats through Carrier's cloud: a thermostat per zone, outdoor temperature and a lifetime electricity meter. | [docs/carrier_infinity](docs/carrier_infinity/README.md) |
| **Crafty Controller** | Start and stop your Minecraft servers, and see which ones are running. | [docs/crafty_controller](docs/crafty_controller/README.md) |
| **CWFIS** | Canada's national wildfire data: the fire summary, every active fire on a map, how close fires are, and smoke. | [docs/cwfis](docs/cwfis/README.md) |
| **Life RPG** | A game where your phone's health sensors become daily quests in an RPG built to be played for years. | [docs/life_rpg](docs/life_rpg/README.md) |
| **National Grid** | Your National Grid (US) smart meter's electric usage and cost in 15-minute steps, ready for the Energy dashboard. | [docs/nationalgrid](docs/nationalgrid/README.md) |
| **TrueNAS Apps** | Your TrueNAS Docker apps: status, on/off, restart, and app and system updates. | [docs/truenas_apps](docs/truenas_apps/README.md) |
| **Yardian Local** | Local-only control of Yardian sprinkler controllers, plus a fail-safe watering blueprint. | [docs/yardian_local](docs/yardian_local/README.md) |

## Install

Copy the integration's folder from [`custom_components/`](custom_components) into your Home Assistant
`/config/custom_components/` folder, restart Home Assistant, then add it under **Settings → Devices & services → Add
integration**. Each integration's page above has its requirements and the full setup.

## Repository layout

| Folder | What's in it |
|---|---|
| [`custom_components/`](custom_components) | The integrations, one folder each. |
| [`docs/`](docs) | Each integration's documentation, changelog and contributor guide. |
| [`blueprints/`](blueprints) | The Yardian watering blueprint. |
| [`examples/`](examples) | Dashboards and automations to copy from. |
| [`tests/`](tests) | Each integration's tests. |

Bug reports and pull requests are welcome: [open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose)
and pick the form for the integration. [CONTRIBUTING.md](CONTRIBUTING.md) explains how the repository works.

## Credits and license

Each integration's page lists the work from other people it uses and any trademarks it mentions.

[GNU General Public License v3.0](LICENSE), except **CWFIS**, which is under the
[MIT License](custom_components/cwfis/LICENSE).
