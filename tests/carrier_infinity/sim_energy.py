"""Long-run simulation of the lifetime electricity meter (sensor.py), against a model of Carrier's cloud.

Runs the real Electricity sensor hour by hour for years, through Home Assistant restarts, crashes (restoring a
slightly old save), outages from hours to 20 months, Carrier outages and bad readings, and Carrier's quirks
(switchable per scenario). Ground truth is Carrier's own figures, so each run must end within a few kWh of them:

    -(data no meter could have seen) - 3   <=   meter - truth   <=   (kWh Carrier trimmed after the fact) + 3

and the meter must never go down. "Data no meter could have seen": Carrier only keeps one past year, so if Home
Assistant (or Carrier's year2) is away for the whole window in which a year's final total is published, the end of
that year can't be recovered. The simulation works that out from what was actually published.

Run:  python3 tests/carrier_infinity/sim_energy.py [years] [seeds] [scenario ...]
      python3 tests/carrier_infinity/sim_energy.py              (12 years, 6 seeds, every scenario: a few minutes)
      python3 tests/carrier_infinity/sim_energy.py 30 6         (the full check before a release that touches sensor.py)
Prints "N/N runs within bounds" and exits non-zero if any run is not.
"""

from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import random
import sys
import zlib

sys.path.insert(0, str(Path(__file__).parent / "ha"))  # for stubs.py

import stubs  # noqa: I001 - must come first: it installs the Home Assistant stand-ins

from carrier_api import Config, Energy, Profile, Status, System
from carrier_infinity import sensor

TZ = stubs.TZ
RAW = json.loads((stubs.FIXTURES / "systems.json").read_text())["infinitySystems"][0]
SERIAL = RAW["profile"]["serial"]

# Carrier quirks by scenario. Each is tested alone, then all together ("everything").
SCENARIOS = {
    "baseline": {},
    "late_new_year": {"reset_delay_h": (1, 72)},  # Carrier publishes its New Year up to 3 days late
    "stale_year2": {"year2_lag_h": (1, 48)},  # year2 still shows the year before last for up to 2 days
    "year2_gaps": {"year2_gaps": True},  # year2 missing for hours to months, often around New Year
    "year2_revised": {"year2_revisions": True},  # Carrier quietly revises last year's total mid-year
    "daily_updates": {"daily": True},  # Carrier refreshes its energy figures only once a day
    "long_same_year_outage": {"same_year_outage": True, "year2_revisions": True},  # HA off 1-7 months
    "january_install": {"jan_install": True, "year2_gaps": True},  # installed in the first days of a year
    "long_outage": {"long_outage": True},  # HA off for 13-20 months (one or two New Years missed)
    "everything": {
        "reset_delay_h": (1, 72),
        "year2_lag_h": (1, 48),
        "year2_gaps": True,
        "year2_revisions": True,
        "daily": True,
        "same_year_outage": True,
        "long_outage": True,
    },
}


def elec(v):
    """Electricity in one of Carrier's period dicts (gas is reported too, and must be ignored by the meter)."""
    return v["cooling"] + v["fan"]


def period(name, v):
    """One period of Carrier's energy payload, as carrier_api parses it."""
    return {
        "energyPeriodType": name,
        "coolingKwh": v["cooling"],
        "fanKwh": v["fan"],
        "gasKwh": v["gas"],
        "eHeatKwh": 0,
        "fanGasKwh": 0,
        "hPHeatKwh": 0,
        "loopPumpKwh": 0,
        "reheatKwh": 0,
    }


class Carrier:
    """Carrier's cloud: per-year energy buckets reported in whole kWh, with the quirks of the scenario."""

    def __init__(self, rng, start, quirks):
        """A system installed part-way through a year, with a random history and random usage."""
        self.rng, self.q = rng, quirks
        self.exact = {k: rng.uniform(0, 500) for k in ("cooling", "fan", "gas")}  # this year so far, exact
        self.prev = {k: int(rng.uniform(1000, 4000)) for k in self.exact}  # last year's final (year2)
        self.prev2 = {k: int(rng.uniform(1000, 4000)) for k in self.exact}  # the year before (for stale year2)
        self.year = start.year  # the Carrier year being counted
        self.boundary = self._boundary(self.year + 1)
        self.trims = 0  # kWh Carrier removed from a finished year (the meter may already have counted them)
        self.frozen = None  # what Carrier still publishes while its New Year is late
        self.publish_reset_at = None
        self.year2_stale_until = None
        self.y2_gap_until = None
        self.cache, self.next_refresh = None, start  # once-a-day publishing

    def _boundary(self, year):
        """When Carrier's next year starts: local midnight (plus a little), or UTC midnight (Dec 31 evening)."""
        if self.rng.random() < 1 / 3:
            return datetime(year, 1, 1, tzinfo=UTC).astimezone(TZ)
        return datetime(year, 1, 1, tzinfo=TZ) + timedelta(minutes=self.rng.uniform(0, 120))

    def reported(self):
        """This year so far, in whole kWh."""
        return {k: math.floor(v) for k, v in self.exact.items()}

    def advance(self, now, hours):
        """Move time on. Returns (year, final) when a Carrier year has just ended, else None."""
        ended = None
        if now >= self.boundary:
            if "reset_delay_h" in self.q and self.rng.random() < 0.6:
                self.frozen = (self.reported(), dict(self.prev))
                self.publish_reset_at = now + timedelta(hours=self.rng.uniform(*self.q["reset_delay_h"]))
            final = self.reported()
            if self.rng.random() < 0.35:  # Carrier trims a finished year a little
                trim = min(self.rng.randint(1, 3), final["cooling"])
                final["cooling"] -= trim
                self.trims += trim
            self.prev2, self.prev = self.prev, final
            if "year2_lag_h" in self.q and self.rng.random() < 0.6:
                self.year2_stale_until = now + timedelta(hours=self.rng.uniform(*self.q["year2_lag_h"]))
            self.exact = dict.fromkeys(self.exact, 0.0)
            ended = (self.year, elec(final))
            self.year += 1
            self.boundary = self._boundary(self.year + 1)
        m = now.month
        cool = 2.2 if m in (6, 7, 8) else 0.6 if m in (5, 9) else 0.0
        self.exact["cooling"] += self.rng.uniform(0, cool) * hours
        self.exact["fan"] += self.rng.uniform(0.05, 0.4) * hours
        self.exact["gas"] += (self.rng.uniform(0, 3) if m in (11, 12, 1, 2, 3) else 0) * hours
        if self.q.get("year2_revisions") and 3 <= m <= 11 and self.rng.random() < 0.0004:
            self.prev["fan"] = max(0, self.prev["fan"] + self.rng.choice([-3, -2, -1, 1, 2, 4]))
        if self.q.get("year2_gaps"):
            if self.y2_gap_until and now >= self.y2_gap_until:
                self.y2_gap_until = None
            elif self.y2_gap_until is None:
                new_year_ish = (m == 1 and now.day <= 3) or (m == 12 and now.day == 31)
                if self.rng.random() < (0.02 if new_year_ish else 0.0005):
                    hours_off = self.rng.choice([2, 12, 48, 24 * 30, 24 * 120])
                    self.y2_gap_until = now + timedelta(hours=hours_off)
        return ended

    def view(self, now):
        """What the API returns now: (year1, year2, year1's Carrier year, whether year2 is last year's final)."""
        if self.q.get("daily"):
            if now < self.next_refresh and self.cache is not None:
                return self.cache
            self.next_refresh = now.replace(minute=0) + timedelta(hours=24 + self.rng.randint(-2, 2))
        if self.frozen is not None and self.publish_reset_at and now < self.publish_reset_at:
            y1, y2 = self.frozen
            y1_year, fresh = self.year - 1, False
        else:
            self.frozen = None
            stale = self.year2_stale_until and now < self.year2_stale_until
            y1, y2 = self.reported(), dict(self.prev2 if stale else self.prev)
            y1_year, fresh = self.year, not stale
        if self.y2_gap_until:
            y2, fresh = None, False
        self.cache = (y1, y2, y1_year, fresh)
        return self.cache


class Coord:
    """Just the part of the coordinator the sensor reads: data = {serial: System}."""

    data = {}


async def run(seed, quirks, years):
    """One simulated installation. Returns the numbers the bounds are checked against."""
    rng = random.Random(seed * 7919 + zlib.crc32(json.dumps(quirks, sort_keys=True).encode()))
    if quirks.get("jan_install"):
        start = datetime(2026, 1, 1, 2, tzinfo=TZ) + timedelta(hours=rng.randint(0, 24 * 20))
    else:
        start = datetime(2026, 1, 1, tzinfo=TZ) + timedelta(hours=rng.randint(0, 24 * 360))
    stubs.NOW[0] = start
    carrier = Carrier(rng, start, quirks)
    if quirks.get("jan_install"):
        carrier.y2_gap_until = start + timedelta(days=rng.randint(1, 25))  # year2 missing when installed
    coord = Coord()
    system = System(
        Profile(RAW["profile"]), Status(RAW["status"]), Config(RAW["config"]), Energy({"energyPeriods": []})
    )
    coord.data = {SERIAL: system}

    # What the meter could know: per Carrier year, the highest year1 it read, and whether last year's final total
    # was ever readable on two readings in a row (what the meter needs to trust it).
    seen = {"max": {}, "streak": 0, "readable": set(), "finals": {}}

    def publish(glitch=None):
        """Put Carrier's current answer (possibly a bad reading) into the system the sensor reads."""
        y1, y2, y1_year, fresh = carrier.view(stubs.NOW[0])
        if glitch == "empty":
            y1 = y2 = None
        elif glitch == "zeros":
            y1 = y2 = {"cooling": 0, "fan": 0, "gas": 0}
        elif glitch == "dip" and y1:
            y1 = dict(y1, fan=max(0, y1["fan"] - rng.randint(1, 3)))
        elif glitch == "y2junk":
            y2 = {"cooling": rng.randint(0, 5000), "fan": 0, "gas": 0}
        periods = ([period("year1", y1)] if y1 else []) + ([period("year2", y2)] if y2 else [])
        system.energy = Energy({"energyPeriods": periods})
        if glitch in (None, "dip") and y1:
            seen["max"][y1_year] = max(seen["max"].get(y1_year, 0), elec(y1))
        if glitch != "empty":  # an empty reading is skipped by the meter entirely
            seen["streak"] = seen["streak"] + 1 if fresh and glitch in (None, "dip") else 0
            if seen["streak"] >= 2:
                seen["readable"].add(carrier.year - 1)

    def close_year(year):
        """Year's final-total window has closed: anything the meter could never see of it is unrecoverable."""
        if year in seen["finals"] and year not in seen["readable"]:
            return max(seen["finals"][year] - seen["max"].get(year, 0), 0)
        return 0

    async def new_meter():
        """Home Assistant (re)starts: a fresh entity loads the saved state and reads the current data."""
        seen["streak"] = 0
        publish()
        e = sensor.Electricity(coord, SERIAL)
        await e.async_added_to_hass()
        return e

    publish()
    stubs.SAVED.clear()
    meter = await new_meter()
    while meter.native_value is None:  # Carrier sent nothing usable on the very first read
        stubs.NOW[0] += timedelta(hours=1)
        carrier.advance(stubs.NOW[0], 1)
        publish()
        meter._handle_coordinator_update()

    completed = 0  # finals of the Carrier years that ended since install
    truth0 = elec(carrier.reported()) - meter.native_value  # the meter starts at this year so far
    snapshot = meter.extra_restore_state_data.as_dict()  # Home Assistant's periodic save (used after a crash)

    planned = []  # long Home Assistant outages
    if quirks.get("long_outage"):
        s = start + timedelta(days=rng.randint(365 * 2, 365 * max(years - 3, 2)))
        planned.append((s, s + timedelta(days=rng.randint(395, 610))))
    if quirks.get("same_year_outage"):
        s = datetime(start.year + rng.randint(2, max(years - 3, 2)), 2, 1, tzinfo=TZ) + timedelta(
            days=rng.randint(0, 120)
        )
        planned.append((s, s + timedelta(days=rng.randint(31, 200))))  # ends before December

    ha_down_until = cloud_down_until = None
    prev_value, decreases, unrecoverable = meter.native_value, 0, 0
    end = datetime(start.year + years, 6, 15, tzinfo=TZ)
    while stubs.NOW[0] < end:
        stubs.NOW[0] += timedelta(hours=1)
        now = stubs.NOW[0]
        if (ended := carrier.advance(now, 1)) is not None:
            year, final = ended
            completed += final
            seen["finals"][year] = final
            unrecoverable += close_year(year - 1)

        # Home Assistant: planned outages, random ones (hours to weeks), restarts and crashes.
        if ha_down_until is None:
            ha_down_until = next((e for s, e in planned if s <= now < e), None)
            if ha_down_until is None:
                r = rng.random()
                if r < 0.0018:
                    ha_down_until = now + timedelta(hours=rng.randint(1, 12))
                elif r < 0.0020:
                    ha_down_until = now + timedelta(days=rng.randint(1, 10))
                elif r < 0.00203:
                    ha_down_until = now + timedelta(weeks=rng.randint(2, 8))
            if ha_down_until is not None:  # half the time it stops uncleanly and restores the periodic save
                saved = snapshot if rng.random() < 0.5 else meter.extra_restore_state_data.as_dict()
                stubs.SAVED[meter._attr_unique_id] = dict(saved)
        if ha_down_until is not None:
            if now < ha_down_until:
                continue
            ha_down_until = None
            meter = await new_meter()
        elif rng.random() < 0.006:  # a restart (~weekly); 30% are crashes
            crash = rng.random() < 0.3
            stubs.SAVED[meter._attr_unique_id] = dict(snapshot if crash else meter.extra_restore_state_data.as_dict())
            meter = await new_meter()

        # Carrier's cloud: occasional outages (no reading at all), and bad readings.
        if cloud_down_until is not None and now < cloud_down_until:
            continue
        cloud_down_until = None
        if rng.random() < 0.001:
            cloud_down_until = now + timedelta(hours=rng.randint(1, 24))
            continue
        g = rng.random()
        glitch = (
            "empty" if g < 0.002 else "zeros" if g < 0.004 else "dip" if g < 0.006 else "y2junk" if g < 0.007 else None
        )
        publish(glitch)
        meter._handle_coordinator_update()

        value = meter.native_value
        if value is not None and prev_value is not None and value < prev_value - 1e-9:
            decreases += 1
        prev_value = value if value is not None else prev_value
        snapshot = meter.extra_restore_state_data.as_dict()

    # End: two fresh readings (as after a refresh), then compare with Carrier's totals.
    carrier.cache, carrier.next_refresh = None, stubs.NOW[0]
    for _ in range(2):
        publish()
        meter._handle_coordinator_update()
    unrecoverable += close_year(carrier.year - 1)  # the latest finished year, if its total was never readable
    truth = completed + elec(carrier.reported()) - truth0
    error = meter.native_value - truth
    ok = decreases == 0 and -unrecoverable - 3 <= error <= carrier.trims + 3
    return {
        "ok": ok,
        "error": error,
        "trims": carrier.trims,
        "unrecoverable": unrecoverable,
        "decreases": decreases,
        "lifetime": truth,
    }


def _one(args):
    """Worker: run one (scenario, seed) in its own process."""
    import asyncio

    name, seed, years = args
    return name, seed, asyncio.run(run(seed, SCENARIOS[name], years))


def main():
    """Run the chosen scenarios on all cores and print one line per scenario."""
    years = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    names = sys.argv[3:] or list(SCENARIOS)
    jobs = [(n, s, years) for n in names for s in range(seeds)]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(_one, jobs))
    print(f"{'scenario':24}{'runs':>5}  {'meter - Carrier (kWh)':>22}  {'unrecoverable':>13}  never down")
    for n in names:
        rows = [r for name, _, r in results if name == n]
        errors = [r["error"] for r in rows]
        print(
            f"{n:24}{len(rows):5}  {min(errors):+10.0f} .. {max(errors):+8.0f}  {sum(r['unrecoverable'] for r in rows):13.0f}"
            f"  {'yes' if all(r['decreases'] == 0 for r in rows) else 'NO'}"
        )
        for name, seed, r in results:
            if name == n and not r["ok"]:
                print(f"    OUT OF BOUNDS seed {seed}: {r}")
    good = sum(r["ok"] for _, _, r in results)
    print(f"\n{good}/{len(results)} runs within bounds ({years} years each)")
    sys.exit(0 if good == len(results) else 1)


if __name__ == "__main__":
    main()
