# Privacy and Security

## What leaves your Home Assistant

Nothing goes to the internet. The integration connects only to the TrueNAS host you entered, over an encrypted
websocket (`wss://`). There's no analytics, update check or third-party service.

## The API key

- It's stored in Home Assistant's own configuration storage, like any integration's credentials.
- It is sent only to your TrueNAS, once per connection, to log in.
- It's never written to the log by this integration. Check logs and screenshots for it anyway before sharing them.
- Delete the key in TrueNAS if you stop using the integration, and use a key from an account you're happy to give this access.

## Verify SSL certificate

It's **off** by default because TrueNAS ships with a self-signed certificate. With it off, the connection is still
encrypted, but Home Assistant can't tell whether the server is really your TrueNAS. On a home network that risk is
small; if you have a trusted certificate on TrueNAS, turn verification on (Reconfigure).

## What the integration can do to your TrueNAS

With a key that can change apps, it can start, stop, restart, redeploy and upgrade your apps, and nothing else.
It deliberately **cannot** install a TrueNAS system update, change storage, delete data or touch containers directly.
Anyone who can use buttons and switches in your Home Assistant can use those controls, so think about who has
access to them (for example, hide them from dashboards shared with guests).

## Hardening already in the code

- The host field accepts only a name or IP (and port), so the connection URL can't be redirected somewhere else.
- Every network operation has a time limit, so a hung server can't freeze Home Assistant.
- A rejected API key stops polling instead of retrying forever.