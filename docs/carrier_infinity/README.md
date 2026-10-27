# Carrier Infinity (Cloud)

A slim Home Assistant integration for Carrier Infinity thermostats, through the same cloud account as the Carrier app.

[![Open your Home Assistant instance and start setting up Carrier Infinity (Cloud).](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=carrier_infinity)

- a thermostat for every zone: mode, temperatures, fan speed, and Carrier's activities (home, away, sleep, wake,
  manual, vacation) as presets, plus **Resume schedule**
- changes made in Home Assistant show straight away; changes made at the wall or in the Carrier app arrive within
  seconds
- outdoor temperature
- **one electricity meter for the whole system** that only counts up and never resets, ready for the Energy dashboard
- setup and password changes all in the UI: no YAML, no helpers

This is a **cloud** integration: it needs internet access and a Carrier account. Newer Infinity thermostat firmware
has no local option that works without extra hardware or modified firmware; the
[Local Control](Local-Control.md) page covers what exists.

## Install

**Needs:** Home Assistant 2026.9 or newer, and a Carrier account that works in the Carrier app (the same username and
password). Built and tested with an Infinity Touch (SYSTXCCITC01-C); other thermostats that work in the Carrier app
should work too.

1. **Download.** Copy the [`custom_components/carrier_infinity`](../../custom_components/carrier_infinity) folder from this repository into `/config/custom_components/` and restart Home Assistant.
2. **Sign in.** Press the button above, or go to **Settings → Devices & services → Add integration → Carrier
   Infinity (Cloud)**, and enter your Carrier app username and password.
3. **Use it.** Each thermostat appears as a device with a thermostat entity per zone, an outdoor temperature sensor
   and an electricity meter. To track the system's electricity, add the meter under **Individual devices** in the
   Energy dashboard's settings.

## Documentation

The other pages here cover everything else:

| Page | What's in it |
|---|---|
| [Installation](Installation.md) | Download, sign-in, password changes, updating and removing. |
| [Thermostats and Sensors](Thermostats-and-Sensors.md) | Every entity, and what each control does on your system. |
| [Electricity Meter](Electricity-Meter.md) | How the lifetime total is counted, how accurate it is, and the Energy dashboard. |
| [Local Control](Local-Control.md) | Why this uses Carrier's cloud, and the local options that exist. |
| [Troubleshooting](Troubleshooting.md) | Slow updates, unavailable entities, debug logs. |
| [Privacy and Security](Privacy-and-Security.md) | What is sent where, and how your password is kept. |
| [Development](Development.md) | How data flows, the file map and the tests. |

## Privacy

The only outside connections are to Carrier's own cloud, the same servers the Carrier app uses. Your password is
stored by Home Assistant like any other integration's, and is kept out of the logs. See
[Privacy and Security](Privacy-and-Security.md).

## Contributing

Bug reports and pull requests are welcome: [open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose).
[CONTRIBUTING.md](CONTRIBUTING.md) covers how the code is laid out, how to run the checks and how to release a new
version.

## Credits

Code from other people in this project:
- [carrier_api](https://github.com/dahlb/carrier_api) by [dahlb](https://github.com/dahlb) (MIT): every exchange with
  Carrier's cloud (sign-in, data, changes and the live connection) goes through this library, which Home Assistant
  installs as a requirement. The recorded Carrier responses in `tests/carrier_infinity/fixtures` come from its test suite.
- [ha_carrier](https://github.com/dahlb/ha_carrier) by [dahlb](https://github.com/dahlb) (MIT): the thermostat
  follows its design for how Carrier's modes, activities and fan speeds map onto Home Assistant, setting temperatures
  as a hold on the manual activity, the Resume preset, and showing a just-written value for a few minutes while
  Carrier's cloud catches up.

Everything else was written for this project, with help from Claude, Anthropic's AI model.

Carrier, Infinity and the Carrier logo are trademarks of Carrier. This project is not affiliated with or endorsed by
Carrier.

## License
[GNU General Public License v3.0](../../LICENSE). You may use, study, share and change this integration; if you share a
changed version, share its source under the same licence.
