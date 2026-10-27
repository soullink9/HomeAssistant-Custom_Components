# Changelog

## 1.0.0 (2026-10-18)

The first public release.

- A thermostat (climate entity) for every zone: heat, cool, heat/cool, fan only and off; setpoints; fan speed;
  Carrier's activities (home, away, sleep, wake, manual, vacation) as presets, plus "Resume schedule".
- Changing the temperature holds the zone on its manual activity, like the wall control.
- Changes appear in Home Assistant straight away, even while Carrier's cloud is still catching up.
- Changes made on the wall control or in the Carrier app arrive within seconds over Carrier's live connection.
- An outdoor temperature sensor, and one lifetime electricity meter for the whole system that never resets
  (ready for the Energy dashboard).
- Setup and password changes are all in the UI.
