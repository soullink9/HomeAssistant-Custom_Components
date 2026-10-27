# TrueNAS Apps

Your TrueNAS Docker apps in Home Assistant: see which are running, start, stop and restart them, and get app and system updates in the Updates list. Nothing else is exposed, by design.

[![Open your Home Assistant instance and start setting up TrueNAS Apps.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=truenas_apps)

- one Home Assistant device per **app** (not per container), with the app's own icon on its update entity
- a **status** sensor: running, stopped, crashed, deploying or stopping
- an **on/off switch**, plus **Restart** and **Force recreate** buttons
- an **update** entity per app, shown in Settings → Updates, with an Install button that upgrades the app
- a **TrueNAS** device with a **usage %** sensor for every storage pool
- a **TrueNAS system update** entity that tells you when an update exists. It cannot install it: updating the operating system should be done in TrueNAS, after a backup
- apps you remove from TrueNAS can be deleted from Home Assistant's device page
- setup, reconfigure and re-authentication are all in the UI: no YAML, no helpers, no custom cards, no dependencies

## Install

**Needs:** Home Assistant 2026.9 or newer, and TrueNAS 25.10 (Goldeye) or newer, which has the Docker-based Apps. It was built and tested on 25.10.7.

1. **Download.** Copy the [`custom_components/truenas_apps`](../../custom_components/truenas_apps) folder from this repository into `/config/custom_components/` and restart Home Assistant.
2. **Make an API key** in TrueNAS (user menu in the top right → **API Keys** → **Add**). Copy it when it's shown; TrueNAS won't show it again.
3. **Add the integration.** Press the button above, or go to **Settings → Devices & services → Add integration → TrueNAS Apps**. Enter the TrueNAS hostname or IP, the API key, and whether to verify the SSL certificate (leave it off if TrueNAS uses its default self-signed certificate).

The [Installation](Installation.md) page has the details, including reconfiguring later and what to do if the API key changes.

## Documentation

The other pages here cover everything else:

| Page | What's in it |
|---|---|
| [Installation](Installation.md) | Download, API key, setup, reconfigure, updating and removing. |
| [Entities and Controls](Entities-and-Controls.md) | Every entity, what each button does, and how updates behave. |
| [System Information Card](System-Information-Card.md) | A built-in Markdown card that looks like TrueNAS's System Information panel. |
| [Troubleshooting](Troubleshooting.md) | Common problems and what the log messages mean. |
| [Privacy and Security](Privacy-and-Security.md) | What leaves your Home Assistant and how the API key is used. |
| [Development](Development.md) | The file map and the tests. |

## Privacy

Nothing calls out to the internet. The only connection is from Home Assistant to the TrueNAS address you enter. See [Privacy and Security](Privacy-and-Security.md).

## Contributing

Bug reports and pull requests are welcome: [open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose). [CONTRIBUTING.md](CONTRIBUTING.md) covers how the code is laid out, how to run the checks and how to release a new version.

## Credits
Code from other people in this project: none. No code was copied or adapted from other TrueNAS or Home Assistant projects.

What it was built from:
- The protocol (JSON-RPC 2.0 over a websocket, API-key login, and the `app.*`, `pool.query`, `update.status` and `core.get_jobs` calls) follows the official [TrueNAS API documentation](https://www.truenas.com/docs/scale/25.10/api/).
- The integration structure (coordinator, config flow with reconfigure and re-authentication, update entities, the `brand` folder) follows the [Home Assistant developer documentation](https://developers.home-assistant.io/).
- The icon is an original drawing made for this project. It is not the TrueNAS logo.

Everything else was written for this project, with help from Claude, Anthropic's AI model.

TrueNAS is a trademark of iXsystems, Inc. This project is not made by, affiliated with or endorsed by iXsystems or Home Assistant.

## License
[GNU General Public License v3.0](../../LICENSE). You may use, study, share and change TrueNAS Apps; if you share a changed version, share its source under the same licence.
