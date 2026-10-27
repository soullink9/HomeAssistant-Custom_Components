# Thermostats and Sensors

Each Carrier system (thermostat) is one device, named as on the thermostat, with its model, serial number and
firmware on the device page.

## A thermostat per zone

Every zone is a thermostat (climate entity), named as on the wall control. It shows the zone's temperature and
humidity, what it's doing (heating, cooling, fan or idle), and the setpoints and fan speed of the activity it's
running.

### Mode

| Home Assistant | Carrier |
|---|---|
| Off | Off |
| Heat | Heat |
| Cool | Cool |
| Heat/Cool | Auto |
| Fan only | Fan only |

Only the modes your equipment supports are offered (no Cool without an air conditioner or heat pump, for example).

**The mode is shared by every zone**, exactly as on the wall control: changing it on one zone changes it on all of
them.

### Temperature

- In **Heat** or **Cool** mode there's one target; in **Heat/Cool** a low (heat) and a high (cool) target.
- **Changing the temperature holds the zone on its Manual activity, indefinitely**, like changing it on the wall
  control. Carrier always stores both setpoints, so the one you didn't change keeps its value.
- Steps are whole degrees in Fahrenheit, half degrees in Celsius. The unit follows what the thermostat is set to
  display; Home Assistant converts if yours differs.

### Presets (activities)

Carrier runs each zone on an **activity**, each with its own heat and cool setpoints and fan speed. They appear as
presets:

| Preset | What choosing it does |
|---|---|
| **Home**, **Away**, **Sleep**, **Wake** | Holds the zone on that activity indefinitely. |
| **Manual** | Holds the zone on its manual setpoints. |
| **Vacation** | Holds the zone on its vacation settings. |
| **Resume schedule** | Drops any hold and returns the zone to its schedule. |

The preset shown is the activity the zone is running now, whether the schedule chose it or a hold did. Only
activities your zone has are offered.

### Fan

**Auto** (Carrier's "off": the fan runs only when heating or cooling), **Low**, **Medium** and **High**. It sets the
fan speed of the activity the zone is running. Offered when the system has a fan.

## Sensors per system

| Sensor | What it shows |
|---|---|
| **Outdoor temperature** | The outdoor air temperature measured by the outdoor unit, in the unit the thermostat displays. |
| **Electricity** | Lifetime electricity used by the whole system, in kWh. Only ever counts up. See [Electricity Meter](Electricity-Meter.md). |

## How quickly things update

- **Changes from Home Assistant show straight away.** Carrier's cloud keeps reporting the old value for a few
  minutes after a change, so for 5 minutes Home Assistant shows the value it sent instead.
- **Changes at the wall or in the Carrier app arrive within seconds**, over Carrier's live connection (websocket).
- **Everything is re-read every 5 minutes** as a safety net. The electricity meter updates then.

## When entities are unavailable

- The thermostat is offline with Carrier (no internet at home, power cut): every entity of that system is
  unavailable until it's back.
- Carrier stops listing a zone (after re-zoning, for example): that zone's thermostat is unavailable. Reload the
  integration to pick up the new zones.
- Carrier's cloud is down, or sends something the library can't read yet: everything is unavailable until a later
  refresh works. See [Troubleshooting](Troubleshooting.md).
