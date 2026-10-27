# Troubleshooting

Start with the log: **Settings → System → Logs**, search for `carrier_infinity` (and `carrier_api` for the library).

## Setup says "Invalid username or password"

Use the username and password you sign in with in the Carrier app. Check you can sign in there first.

## Setup says "Could not reach the Carrier cloud"

Home Assistant couldn't get through to Carrier: no internet, or Carrier's cloud is down. Try again later.

## "This Carrier account is already set up"

That account is already added. One entry covers every thermostat on the account.

## "Reconfiguration required" / "Carrier password changed"

Carrier stopped accepting the saved password (you changed it in the Carrier app, for example). Open the notice and
enter the current password. Updates stop until you do, so a wrong password can't lock the account.

## Changes from the wall or the app are slow to show

They normally arrive within seconds over Carrier's live connection. If that connection drops, the integration
reconnects (waiting longer each time it fails, up to 10 minutes), and the 5-minute refresh keeps things up to date
meanwhile. Turn on debug logging (below) to see "Carrier websocket dropped" messages.

## A change from Home Assistant seems to undo itself

For 5 minutes after a change, Home Assistant shows the value it sent, because Carrier's cloud keeps reporting the old
one for a while. If the cloud still reports the old value after that, Carrier didn't apply the change: check the
thermostat, and the log for **Carrier cloud rejected the change**.

## Everything is unavailable

- **The thermostat is offline with Carrier.** Check it's connected (the Carrier app shows the same).
- **Carrier's cloud is down.** The log shows **Carrier cloud error**. It recovers on its own.
- **Carrier started sending something new** (a new preset or fan speed, for example) that the library can't read yet.
  The log shows **Carrier cloud error** with a `KeyError` or `ValueError`. This needs a newer
  [carrier_api](https://github.com/dahlb/carrier_api); please [open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose).

## One zone is unavailable, or a zone is missing

Carrier no longer reports that zone, or you added zones. Reload the integration (**Settings → Devices & services →
Carrier Infinity (Cloud) → ⋮ → Reload**). Zones are read when the integration starts.

## A mode is missing

Only the modes your equipment supports are offered. Heat/Cool needs both heating and cooling; Fan only needs a fan.

## The electricity meter looks wrong

- Right after setup it starts at this year's usage so far, not your system's lifetime usage.
- It updates in steps, as Carrier updates its own figures.
- Around New Year it may wait a few days for Carrier to publish last year's final total.

[Electricity Meter](Electricity-Meter.md) explains all three.

## Debug logging

On the integration's page choose **Enable debug logging**, reproduce the problem, then **Disable debug logging** to
download the log. The password and Carrier's tokens are kept out of it, but it contains your thermostat's serial
number, so check it before posting.

## Still stuck

[Open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose) with the Carrier form:
your versions, the thermostat's model and software version, and the log.
