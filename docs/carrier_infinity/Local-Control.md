# Local Control

This integration uses **Carrier's cloud**: the same servers the Carrier app uses. That means it needs internet
access, and it stops working if Carrier's cloud is down or Carrier changes its private API (until
[carrier_api](https://github.com/dahlb/carrier_api) catches up).

A local integration, talking straight to the thermostat on your network, would be better. It was the first goal for
this project, and was dropped because nothing local works with current Infinity thermostat firmware without extra
hardware or modified firmware.

## Why not local

- **The thermostat has no local API.** It doesn't accept connections from your network; it only talks out to
  Carrier.
- **Intercepting that traffic doesn't work on current firmware.** Older projects worked by pointing the thermostat
  at a local server instead of Carrier's. Current firmware (including the CESR131755-02.x software this was built on)
  doesn't accept such a stand-in without modification.

## The local options that exist

If local control matters more to you than convenience, these are the routes people use. None of them are part of
this integration.

| Approach | What it takes |
|---|---|
| **A proxy that stands in for Carrier's server** (for example the Infinitude project) | Works only with thermostats on older firmware, or with modified firmware. |
| **Listening on the equipment's communication bus** (the four-wire "ABCD" RS-485 bus) | Extra hardware: an RS-485 adapter wired into the bus, plus software that decodes Carrier's protocol. More involved, and support for each thermostat model varies. |

Both are community efforts, not supported by Carrier. Check each project's own documentation for which models and
firmware it supports before buying hardware.

## Living with the cloud

- Your Carrier password is stored by Home Assistant and kept out of the logs, and only Carrier's servers are
  contacted. See [Privacy and Security](Privacy-and-Security.md).
- When Carrier's cloud is unreachable, the entities show as unavailable, and everything comes back on its own when
  it's reachable again. The thermostat keeps running its own schedule meanwhile.
