# Changelog

## 1.0.0 (2026-10-18)

The first public release.

- Every Docker app on TrueNAS becomes a Home Assistant device with:
  - a **status** sensor (running, stopped, crashed, deploying, stopping),
  - an on/off **switch**,
  - **Restart** and **Force recreate** buttons,
  - an **update** entity that shows in Settings → Updates and can install the app update.
- A **TrueNAS** device with a usage-percent sensor per storage pool and a system **update** entity. The system update
  entity shows that an update exists but deliberately cannot install it. Its attributes (hostname, platform, edition,
  version name) feed the example System Information card.
- Setup, **reconfigure** (host, API key, SSL check) and **re-authentication** when TrueNAS rejects the API key.
- Apps removed from TrueNAS can be deleted from Home Assistant's device page.
- Actions run in the background with one action per app at a time; a failure leaves a persistent notification.
- Built to survive long unattended runs: every poll has a time limit, odd or dropped websocket frames are handled,
  and a rejected API key stops polling instead of retrying forever.
