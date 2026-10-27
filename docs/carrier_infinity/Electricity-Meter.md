# Electricity Meter

Each Carrier system gets one **Electricity** sensor: the electricity the whole system has used, in kWh, as a lifetime
total that **only ever counts up and never resets**. That's the shape the Energy dashboard needs.

## Why it keeps its own total

Carrier only reports energy per calendar year:

- **This year so far**, which Carrier restarts at New Year.
- **Last year's final total.**

A sensor that just showed "this year so far" would drop to zero every New Year. Instead, the meter keeps a lifetime
total and adds to it:

- **Each reading,** it adds however much "this year so far" grew.
- **At New Year,** it adds the new year's figure from zero.
- **Once Carrier publishes last year's final total,** it adds the last part of the old year it hadn't seen yet
  (from the last reading it took to the year's final figure).

It adds up every electric category Carrier reports (heating, cooling, fan, and so on), and leaves out gas, which is
fuel burned rather than electricity.

## Where it starts

The meter starts at **this year's usage so far** on its first reading, not at the system's lifetime usage (Carrier
doesn't report that). From then on it counts everything. In early January, a first reading may still be last year's
figure, so the meter allows for Carrier's New Year arriving within the next two weeks.

## How accurate it is

- The figures are **Carrier's own**, so the meter is only as accurate as Carrier's energy reporting.
- It updates every **5 minutes**, when Home Assistant re-reads the system. Carrier itself may update its figures less
  often (sometimes once a day), so the meter can move in steps.
- Over years, the meter stays within a few kWh of Carrier's yearly totals. The only usage it can miss is usage no
  meter could have seen (for example, if Carrier never published a final total for a year).

## Carrier's quirks it handles

Carrier's data isn't always tidy. The meter allows for what it does in practice, and every case is tested over
decades of simulated readings:

- **A single bad reading** (zeros, a small dip, a junk "last year" figure) never adds or skips a year: a New Year has
  to show on two readings in a row, and last year's total is only trusted when it's the same on two readings.
- **A late New Year:** Carrier may keep showing last year's numbers for hours or days into January.
- **New Year at UTC midnight,** which is the evening of December 31 in the US.
- **A stale "last year":** Carrier may briefly keep showing the year before last.
- **Home Assistant off across New Year,** even for over a year: the calendar says when a New Year must have passed,
  even if "this year so far" has already grown back. If two or more New Years were missed, only the most recent full
  year can still be recovered.
- **Dips:** a figure that goes down without a New Year is ignored.

## Its state

The total (and what the meter needs to carry on counting) is saved by Home Assistant and restored after restarts and
updates. Removing the integration removes the sensor and its saved total; the Energy dashboard keeps the history it
already recorded.

## Energy dashboard

Open **Settings → Dashboards → Energy** and add the **Electricity** sensor under **Individual devices**. It shows
how much of your home's electricity went to heating and cooling.

Don't add it as grid consumption: it's one appliance, not your whole home's electricity.
