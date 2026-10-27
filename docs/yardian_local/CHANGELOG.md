# Changelog

## 1.0.0 (2026-10-18)

The first public release.

- Yardian Local integration: local-only control of a Yardian controller (host and access token, set up in the UI).
- Zone switches that always send a run time, so the controller stops each zone on its own; a Stop all button.
- Run times and flow rates kept in Home Assistant (no helpers to create), restored after restarts.
- Estimated water use per zone and in total, ready for the Energy dashboard; the unit is fixed at setup so
  changing Home Assistant's unit system later can't corrupt the history.
- Last watering, Active zone, Watering, Standby and Rain delay sensors; firmware on the device page when the
  controller reports it; a diagnostics download.
- `yardian_local.start_irrigation` and `yardian_local.notify` (a notification that skips missing phones instead of
  stopping the automation).
- Brand images for the integration (Home Assistant 2026.3 and newer show them).
- The fail-safe lawn watering blueprint: fixed-time or finish-before-sunrise schedules, a watering season with
  reminders, watering days and odd/even dates, town rules, weather and forecast skips, recovery after Home
  Assistant or the controller comes back, never watering twice in a day, a safety watchdog and notifications.
