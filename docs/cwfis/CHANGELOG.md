# Changelog

All notable changes to this project are listed here. Versions follow [semantic versioning](https://semver.org/):
`MAJOR` for breaking changes (entity IDs or removed features), `MINOR` for new features, `PATCH` for fixes.

## [1.0.0] - 2026-10-18

First public release.

### Added
- National summary sensors: reported today, active, out, total fires and area burned this season.
- Same-date-last-year comparison sensors for fires and area burned.
- Per-province (agency) breakdown in attributes, plus optional dedicated province sensors.
- Proximity sensors for Home and any extra watch zones: nearest active fire, fires nearby, nearest fire perimeter, satellite hotspots (24 h), prescribed burns and fire danger.
- Binary sensors: Fire within alert radius (per zone), Fire upwind (with a wind sensor) and Wildfire smoke (with a PM2.5 sensor).
- Fire alert event entity: new fire nearby, stage changed, fire grew, fire out.
- 24/48-hour PM2.5 smoke forecast for Home (Open-Meteo / ECMWF CAMS).
- Map markers for active fires (all, nearby only, or none) and optional Canada-wide map images (fire danger today and tomorrow, smoke, hotspots).
- UI-only setup and options. No YAML, API keys or extra packages.
- Built-in integration icon (Home Assistant 2026.3+).
- Offline simulation test suite (`tests/cwfis/simulate.py`) and a GitHub validation workflow.
