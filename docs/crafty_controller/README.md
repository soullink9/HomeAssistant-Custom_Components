# Crafty Controller for Home Assistant

> Start and stop your Minecraft servers from Home Assistant, and see at a glance which ones are running.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=crafty_controller)

A small custom integration for [Crafty Controller](https://craftycontrol.com/). It is deliberately minimal: it does the few things needed to turn a server on and know what is already running, and nothing else.

## What you get

Every Minecraft server in Crafty becomes a Home Assistant device with:

- **A switch**: on while the server is running. Turn it on to start the server, off to stop it.
- **A status sensor**: online when the server is answering and players can connect. It stays off while a server is still starting up.
- **The server's name and port**: the name is the device name, and the port is a `port` attribute on both entities.

Servers added in Crafty later appear on their own. If one server can't be read, only that server goes `unavailable`. Crafty is polled locally every 30 seconds.

## Requirements

- Home Assistant 2026.9 or newer
- Crafty Controller 4 (API v2), reachable from Home Assistant
- A Crafty API token (see [Configuration](Configuration.md))

## Install

Copy the [`custom_components/crafty_controller`](../../custom_components/crafty_controller) folder from this repository into `/config/custom_components/`, then restart Home Assistant.

Then go to **Settings → Devices & services → Add integration → Crafty Controller** and enter your Crafty URL (for example `https://192.168.1.10:8443`) and API token. Full steps are in the [Installation](Installation.md) page.

## Documentation

Details live in the other pages here:

| Page | What's in it |
| --- | --- |
| [Installation](Installation.md) | Installing, adding the integration |
| [Configuration](Configuration.md) | Crafty URL, API token and permissions, SSL |
| [Entities](Entities.md) | The switch, the status sensor, attributes and states |
| [Troubleshooting](Troubleshooting.md) | No devices, can't connect, unavailable entities |
| [Development](Development.md) | Pointers for maintainers |

## Privacy

The integration only talks to the Crafty address you enter. There is no cloud service and no telemetry. Your API token is stored by Home Assistant in the integration's config entry, like any other integration credential.

## Contributing

Bug reports and pull requests are welcome, although replies are not guaranteed (see the Disclosure on the [main page](../../README.md)). [CONTRIBUTING.md](CONTRIBUTING.md) explains the code layout, how to run the simulation test, and the release steps.

## Credits

- **[Crafty Controller](https://craftycontrol.com/)** by Arcadia Technology. This integration is a client for Crafty's [v2 API](https://docs.craftycontrol.com/pages/developer-guide/api-reference/v2/), and Crafty does all of the actual server management.
- **[Home Assistant developer documentation](https://developers.home-assistant.io/)**. The integration follows its documented patterns (config flow, `DataUpdateCoordinator`, `runtime_data`).
- **[Claude](https://claude.ai)** by Anthropic, which assisted in building this project.

No code was copied or adapted from other projects. The icon is original artwork made for this project; it is not Crafty's or Minecraft's artwork.

## Disclaimer

This is an unofficial community project. It is not affiliated with or endorsed by Arcadia Technology (Crafty Controller), Mojang or Microsoft. Minecraft is a trademark of its respective owners.

## License

[GNU General Public License v3.0](../../LICENSE) (GPL-3.0).
