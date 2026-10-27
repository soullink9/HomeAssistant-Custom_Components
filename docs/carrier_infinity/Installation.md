# Installation

**Needs:** Home Assistant 2026.9 or newer, internet access, and a Carrier account that works in the Carrier app (the
same username and password). Built and tested with an Infinity Touch (SYSTXCCITC01-C); other thermostats that work in
the Carrier app should work too.

## 1. Download

Copy the [`custom_components/carrier_infinity`](../../custom_components/carrier_infinity) folder from this repository
into `/config/custom_components/` (so you end up with `/config/custom_components/carrier_infinity/manifest.json`),
then restart Home Assistant.

Home Assistant installs the one library it needs, [carrier_api](https://github.com/dahlb/carrier_api), by itself on the
first start.

## 2. Sign in

Go to **Settings → Devices & services → Add integration → Carrier Infinity (Cloud)**, and enter the username and
password you use in the Carrier app. Home Assistant checks them with Carrier before saving.

One entry is one Carrier account. Every thermostat (Carrier calls each one a system) on the account is added, each as
a device with:

- a **thermostat** for every zone,
- an **Outdoor temperature** sensor,
- an **Electricity** meter for the whole system.

[Thermostats and Sensors](Thermostats-and-Sensors.md) explains each one. Adding the same account twice is refused.

If you also use another Carrier integration (such as `ha_carrier`), remove it, so the two don't both control the
thermostat.

## 3. The Energy dashboard (optional)

To track the system's electricity, open **Settings → Dashboards → Energy** and add the **Electricity** sensor under
**Individual devices**. [Electricity Meter](Electricity-Meter.md) explains how it counts and how accurate it is.

## When your Carrier password changes

When Carrier stops accepting the saved password, Home Assistant shows a **Reconfiguration required** notice ("Carrier
password changed"). Open it and enter the current password from the Carrier app; the integration reconnects.

It doesn't keep retrying a rejected password, so a wrong password can't lock your Carrier account.

## Updating

Replace the `carrier_infinity` folder with the new version from this repository and restart. The
[changelog](CHANGELOG.md) lists what changed. Your entities and the electricity meter's total carry over.

## Removing

1. **Settings → Devices & services → Carrier Infinity (Cloud) → ⋮ → Delete**.
2. Delete the `/config/custom_components/carrier_infinity` folder and restart.

Removing it doesn't change anything on the thermostat: schedules, holds and settings stay as they are.
