# Privacy and Security

## What is sent where

The only outside connections are to **Carrier's cloud**, the same servers the Carrier app uses, through the
[carrier_api](https://github.com/dahlb/carrier_api) library. There's no analytics, update check or other service.

| What | When |
|---|---|
| Sign-in with your username and password | at the start, and when Carrier's session expires |
| Every system's profile, status, configuration and energy figures | every 5 minutes |
| A live connection (websocket) that receives changes | kept open while the integration runs |
| Your changes (mode, setpoints, fan, holds, resume schedule) | when you make them |

## Your password

- It's stored in Home Assistant's own configuration storage, like any other integration's sign-in, and sent only to
  Carrier.
- **It's kept out of the logs.** The library underneath logs whole requests and replies at debug level; the integration
  drops any of those lines that contain the password or Carrier's access and refresh tokens. When the live connection
  drops, only the error message is logged, not a full traceback, because the connection's address contains the
  access token.
- **It's never retried blindly.** If Carrier rejects it, the integration stops and asks you for the new one, so a
  wrong password can't lock your Carrier account. An expired session is renewed once with the saved password before
  it gives up.

## What the integration can change

Only what the Carrier app can: the mode, setpoints, fan speed, holds and resuming the schedule. Anyone who can use
the thermostats in your Home Assistant can make those changes, so think about who has access (for example, hide them
from dashboards shared with guests).

## Before you share a log

Debug logs contain your thermostat's serial number and your home's settings. Check them before posting anywhere.
