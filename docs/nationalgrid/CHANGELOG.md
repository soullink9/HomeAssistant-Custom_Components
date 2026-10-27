# Changelog

## 1.0.0 (2026-10-18)

The first public release.

- Near-real-time electric usage from National Grid (US) smart meters, in 15-minute steps, polled every 15 minutes.
- Everything the Energy dashboard's grid entry asks for: energy imported, energy exported, cost, export credit
  and a grid power sensor.
- Imports all the history National Grid still has for your meter on the first run.
- Real-time estimates are replaced with National Grid's settled meter data once a day, so past hours end up exact.
- Cost from your own bills (total charges ÷ kWh for each bill period), repriced when a new bill arrives.
- Handles the daylight saving time changes, National Grid outages and Home Assistant restarts without gaps
  or double counting.
- Setup in the UI, with re-authentication when your password changes.
