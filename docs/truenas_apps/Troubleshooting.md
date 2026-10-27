# Troubleshooting

Start with the log: **Settings → System → Logs**, search for `truenas_apps`.

## Setup says "Cannot connect to TrueNAS"

- Check the host. Use just the name or IP (`truenas.local`, `192.168.1.10`), with `:port` if needed. No `https://`.
- Home Assistant connects with `wss://` (secure websocket), so TrueNAS's HTTPS must be reachable from Home Assistant.
- If you turned **Verify SSL certificate** on and TrueNAS uses a self-signed certificate, the connection is refused.
  Turn it off, or install a certificate Home Assistant trusts.
- The API key must be allowed to read apps (setup tests this).

## Setup says "Invalid API key"

The key was typed wrong, deleted, or belongs to a user that can't use the API. Make a new one in TrueNAS.

## "Reconfiguration required" appeared later

TrueNAS stopped accepting the key. Open the notice (or ⋮ → **Reconfigure**) and enter a new key.

## Everything is unavailable

TrueNAS is down, rebooting or unreachable. Entities recover on their own at the next poll after it's back
(within a minute).

## One app's entities are unavailable

The app was removed from TrueNAS. Delete its device in Home Assistant (see [Installation](Installation.md)).

## A button or switch does nothing / "another action is still running"

Only one action per app runs at a time. Wait for the first to finish. A very slow job is abandoned after 30 minutes.

## "app.… on <app> failed: …" notification

TrueNAS ran the job and it failed (or the connection dropped while waiting). The text after the colon is TrueNAS's own
error. Check the app in the TrueNAS UI (**Apps**) and its job list.

## Update shows "update available" with no version number

TrueNAS flagged an update without saying which version. The Install button still upgrades to the latest.

## The TrueNAS update entity is unavailable, or the card shows —

The API key isn't allowed to read update status or system information. Those parts are optional; use a key with
more rights if you want them.

## Still stuck

[Open an issue](https://github.com/soullink9/HomeAssistant-Custom_Components/issues/new/choose) with your versions and the log
lines. Remove your API key and anything private first.