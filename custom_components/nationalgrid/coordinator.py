"""Fetches usage from National Grid and keeps the Energy dashboard statistics up to date.

National Grid offers two kinds of usage data, both through the py-nationalgrid library:

* Real-time reads: 15-minute intervals, available soon after each interval (how soon is up to National Grid),
  but provisional (they can be a little off) and only kept for about a week.
* Settled data: the exact meter readings, published a day or two later and kept for the life of the meter.

Every 15 minutes the coordinator turns these into four hourly long-term statistics per meter (energy imported,
energy exported, cost and export credit), which is the format the Energy dashboard reads. New hours are appended
from real-time reads, and hours are rewritten with settled data once it exists: the whole history on a new
install, the last few days once a day, and a bill period whenever a new bill arrives (so it gets the bill's rate).

Each statistic row carries a running total ("sum"). Whenever hours are rewritten, every row after them is
rewritten too, so the running totals always add up.
"""

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import logging

from aiohttp import ClientError
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfEnergy
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util, slugify
from homeassistant.util.unit_conversion import EnergyConverter
from py_nationalgrid import (
    CannotConnectError,
    InvalidAuthError,
    NationalGridClient,
    NationalGridConfig,
    NationalGridError,
    create_cookie_jar,
)

from .const import (
    DOMAIN,
    EPOCH,
    FILL_GRACE,
    HISTORY_VERSION,
    HOUR,
    QUARTER,
    RATES_EVERY,
    REALTIME_DAYS,
    RETRY_AFTER_EMPTY,
    RETRY_AFTER_ERROR,
    SETTLE,
    STATISTICS,
)

_LOGGER = logging.getLogger(__name__)

# Errors that mean "National Grid couldn't be reached or answered badly": the update is retried next poll.
NET_ERRORS = (CannotConnectError, NationalGridError, ClientError, TimeoutError)


def _local(value):
    """Parse an ISO timestamp (or take a datetime), treating one without an offset as Home Assistant's local time."""
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    return value.replace(tzinfo=dt_util.get_default_time_zone()) if value.tzinfo is None else value


def _hour(value):
    """Return the start of the hour containing `value`, in UTC.

    Hour math is done in UTC on purpose: in local time, adding an hour at the end of daylight saving time skips
    the repeated 1:00 AM hour.
    """
    return _local(value).astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def _split(net_kwh):
    """Split a net reading (positive = taken from the grid, negative = sent to it) into (imported, exported)."""
    return (net_kwh, 0.0) if net_kwh >= 0 else (0.0, -net_kwh)


class NationalGridCoordinator(DataUpdateCoordinator):
    """One per National Grid login. Polls every 15 minutes; `data` maps each meter to its recent real-time reads."""

    def __init__(self, hass, entry):
        """Set up the National Grid client. Meters are discovered on the first update."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=QUARTER)
        config = NationalGridConfig(username=entry.data[CONF_USERNAME], password=entry.data[CONF_PASSWORD])
        # National Grid's sign-in needs cookies stored unquoted, which create_cookie_jar() sets up.
        self.session = async_create_clientsession(hass, cookie_jar=create_cookie_jar())
        self.api = NationalGridClient(config, session=self.session)
        self.meters: dict[str, dict] = {}  # service point -> meter details plus premise, account and customer numbers
        self.rates: dict[str, tuple[list, float]] = {}  # account -> ([(period start, end, $/kWh)], blended $/kWh)
        self._rewrite: dict[str, datetime] = {}  # service point -> rewrite its statistics from this hour onwards
        self._history_done: set[str] = set()  # meters whose full history import has finished
        self._today = None  # local date of the last update, to spot the first update of each day
        self._rates_checked = self._settled_retry = datetime.min.replace(tzinfo=UTC)

    async def _async_update_data(self):
        """Run one poll: find meters, refresh rates when due, then update every meter's statistics."""
        entry = self.config_entry
        try:
            if not self.meters:
                await self._find_meters()
            if dt_util.utcnow() - self._rates_checked > RATES_EVERY:
                await self._update_rates()
            if self._today != (today := dt_util.now().date()):
                # First update of the day: swap the last few days of real-time estimates for settled data.
                self._today = today
                for service_point in self.meters:
                    self._rewrite_from(service_point, dt_util.start_of_local_day() - SETTLE)
            data = {sp: await self._update_meter(sp, meter) for sp, meter in self.meters.items()}
        except InvalidAuthError as err:
            raise ConfigEntryAuthFailed(err) from err  # makes Home Assistant ask for the password again
        except NET_ERRORS as err:
            raise UpdateFailed(err) from err  # logged, and tried again at the next poll
        # Remember that the full history is in, so restarts don't import it again.
        if entry.data.get("history") != HISTORY_VERSION and self._history_done >= set(self.meters):
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, "history": HISTORY_VERSION})
        return data

    async def _find_meters(self):
        """Collect every electric smart meter on every account linked to this login.

        Gas meters and meters without AMI (smart meter) data are skipped: they have no real-time reads.
        """
        for link in await self.api.get_linked_accounts():
            account_id = link["billingAccountId"]
            account = await self.api.get_billing_account(account_id)
            for meter in account["meter"]["nodes"]:
                if meter.get("hasAmiSmartMeter") and "gas" not in str(meter.get("fuelType")).lower():
                    self.meters[str(meter["servicePointNumber"])] = {
                        **meter,
                        "premise": str(account["premiseNumber"]),
                        "account": account_id,
                        "customer": str(account.get("customerNumber")),
                    }

    def _rewrite_from(self, service_point, since):
        """Schedule a meter's statistics to be rewritten from `since` onwards at its next update."""
        since = _hour(since)
        self._rewrite[service_point] = min(self._rewrite.get(service_point, since), since)

    async def _update_rates(self):
        """Work out each account's cost per kWh from its bill history.

        Each bill's rate is its total charges divided by its kWh, so supply, delivery, taxes and fixed fees are
        all included. Hours not covered by a bill yet use the blended rate of the last three bills.
        """
        for account, customer in {(m["account"], m["customer"]) for m in self.meters.values()}:
            try:
                bills = await self.api.get_electric_bill_history(account, customer)
            except Exception as err:  # noqa: BLE001 - billing being down must never stop usage tracking
                _LOGGER.warning("Could not fetch National Grid bill history: %s", err)
                continue
            bills = [b for b in bills if (b.get("totalKwh") or 0) > 0]  # skip bills with no usage (avoids / 0)
            if not bills:
                continue
            # Bills come newest first.
            periods = [
                (_local(b["readFromDate"]), _local(b["readDate"]), b["totalCharges"] / b["totalKwh"]) for b in bills
            ]
            if periods[:1] != self.rates.get(account, ([], 0))[0][:1]:
                # A new bill (or the first look after a restart): reprice the newest bill period.
                for service_point, meter in self.meters.items():
                    if meter["account"] == account:
                        self._rewrite_from(service_point, periods[0][0])
            recent = bills[:3]
            blended = sum(b["totalCharges"] for b in recent) / sum(b["totalKwh"] for b in recent)
            self.rates[account] = (periods, round(blended, 4))
        self._rates_checked = dt_util.utcnow()

    def rate(self, service_point, hour=None):
        """Return the $/kWh for an hour: its bill period's rate, or the blended rate (also when `hour` is None).

        Returns None until bill history has been fetched once.
        """
        periods, blended = self.rates.get(self.meters[service_point]["account"], ([], None))
        return next((rate for start, end, rate in periods if hour and start <= hour < end), blended)

    async def _recorder(self, func, *args):
        """Run a recorder database query in the recorder's own thread, as Home Assistant requires."""
        return await get_instance(self.hass).async_add_executor_job(func, self.hass, *args)

    async def _update_meter(self, service_point, meter):
        """Bring one meter's four statistics up to date and return its recent real-time reads (for the sensors).

        This is one long method on purpose: the numbered steps below run in order and share their results.
        """
        ids = {key: f"{DOMAIN}:{slugify(service_point)}_{key}" for key in STATISTICS}

        # 1. Where each statistic ends: (start of its last hour, running total), or (EPOCH, 0) when it's empty.
        last = {}
        for key, statistic_id in ids.items():
            rows = (await self._recorder(get_last_statistics, 1, statistic_id, True, {"sum"})).get(statistic_id)
            last[key] = (dt_util.utc_from_timestamp(rows[0]["start"]), rows[0]["sum"]) if rows else (EPOCH, 0.0)
        now = dt_util.utcnow()
        next_new = last["energy"][0] + HOUR  # first hour not stored yet

        # 2. Pick the first hour to write. Normally that's the next new hour, but it's earlier when a full history
        #    import is due, when a rewrite was scheduled, or when hours were stored before any rate was known.
        full = self.config_entry.data.get("history") != HISTORY_VERSION and now >= self._settled_retry
        since = EPOCH if full else min(next_new, self._rewrite.get(service_point, now))
        if self.rates.get(meter["account"]) and last["cost"][0] < last["energy"][0]:
            since = min(since, last["cost"][0] + HOUR if last["cost"][0] > EPOCH else EPOCH)

        # 3. When rewriting stored hours, load them (they're kept unless better data arrives) and find each
        #    running total just before `since`, so the rewritten totals carry on from there.
        stored, base = {}, {key: total for key, (_, total) in last.items()}
        if since < next_new:
            rows = await self._recorder(
                statistics_during_period,
                max(since - timedelta(days=60), EPOCH),
                None,
                set(ids.values()),
                "hour",
                None,
                {"state", "sum"},
            )
            stored = {r["start"]: (r["state"], 0.0) for r in rows.get(ids["energy"], [])}  # ts -> (imported, exported)
            for r in rows.get(ids["return"], []):
                stored[r["start"]] = (stored.get(r["start"], (0.0,))[0], r["state"])
            base = {key: (total if start < since else 0.0) for key, (start, total) in last.items()}
            for key, statistic_id in ids.items():
                if before := [r["sum"] for r in rows.get(statistic_id, []) if r["start"] < since.timestamp()]:
                    base[key] = before[-1]

        # 4. Settled data (exact) for anything older than about a day.
        settled, settled_failed = {}, False
        if since < now - timedelta(days=1) and now >= self._settled_retry:
            try:
                usages = await self.api.get_ami_energy_usages(
                    str(meter["meterNumber"]),
                    meter["premise"],
                    service_point,
                    meter["meterPointNumber"],
                    max(dt_util.as_local(since).date(), date(1970, 1, 1)),
                    dt_util.now().date(),
                    fuel_type=meter.get("fuelType"),
                )
                for usage in usages:
                    if "T" not in str(usage["date"]):
                        continue  # a whole-day total (date only) can't be placed in an hour, so it's not used
                    if (hour := _hour(usage["date"])) >= since:
                        # Records can be hourly or 15-minute: add them up as net kWh, then split the hour.
                        imported, exported = settled.get(hour, (0.0, 0.0))
                        settled[hour] = _split(imported - exported + float(usage["quantity"]))
            except NET_ERRORS as err:
                _LOGGER.warning("National Grid settled usage unavailable, using real-time data: %s", err)
                settled_failed, self._settled_retry = True, now + RETRY_AFTER_ERROR
            if full and not settled:  # nothing settled came back: keep going on real-time data, retry the import later
                full, self._settled_retry = False, max(self._settled_retry, now + RETRY_AFTER_EMPTY)
        if settled_failed and not full:
            # Without settled data a rewrite would only repeat what's stored, so just add new hours this time.
            # The scheduled rewrite stays in place and runs once settled data is back.
            since, stored, base = next_new, {}, {key: total for key, (_, total) in last.items()}

        # 5. Real-time 15-minute reads (always from yesterday's midnight, so the "today" sensors are complete).
        start = max(min(since, dt_util.start_of_local_day() - timedelta(days=1)), now - REALTIME_DAYS)
        reads = await self.api.get_interval_reads(
            meter["premise"],
            service_point,
            dt_util.as_local(start).replace(tzinfo=None),  # the API wants local time
        )
        realtime = defaultdict(lambda: [0.0, 0.0])  # hour -> [imported, exported]
        covered = defaultdict(timedelta)  # hour -> how much of it the reads cover
        for read in reads:
            read["start"], read["end"] = _local(read["startTime"]), _local(read["endTime"])
            if not timedelta(0) < read["end"] - read["start"] <= HOUR:
                # The library mis-dates the read that spans a daylight saving change; every read is 15 minutes.
                read["start"] = read["end"] - QUARTER
            hour = _hour(read["start"])
            realtime[hour][read["value"] < 0] += abs(read["value"])
            covered[hour] += read["end"] - read["start"]
        reads.sort(key=lambda r: r["start"])
        newest = reads[-1]["end"] if reads else now

        # 6. Walk the hours in order, choosing the best data for each, and build the rows with running totals.
        candidates = [h.timestamp() for h in (*settled, *realtime)] + list(stored)
        if not candidates:
            return reads
        hour = max(since, dt_util.utc_from_timestamp(min(candidates)))
        last_hour = dt_util.utc_from_timestamp(max(candidates))
        rows, totals = defaultdict(list), dict(base)
        while hour <= last_hour:
            ts = hour.timestamp()
            if hour in settled:  # exact data wins
                imported, exported = settled[hour]
            elif hour in realtime and covered[hour] >= HOUR:  # a complete real-time hour
                imported, exported = realtime[hour]
            elif hour + HOUR + FILL_GRACE > newest and (hour in realtime or ts not in stored):
                break  # a recent hour still filling in: stop here and try again next poll
            else:
                # An older hour with missing reads (for example a meter outage): use what there is, or what was
                # stored before. Settled data replaces it at the daily rewrite.
                imported, exported = realtime[hour] if hour in realtime else stored.get(ts, (0.0, 0.0))
            rate = self.rate(service_point, hour)  # export is credited at the same rate (net metering)
            values = {"energy": imported, "return": exported}
            if rate is not None:
                values |= {"cost": imported * rate, "compensation": exported * rate}
            for key, value in values.items():
                totals[key] += value
                rows[key].append(StatisticData(start=hour, state=value, sum=totals[key]))
            hour += HOUR

        # 7. Save. Rows for hours already stored are replaced; the recorder writes in the background.
        for key, statistic_rows in rows.items():
            money = key in ("cost", "compensation")
            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                source=DOMAIN,
                statistic_id=ids[key],
                name=f"National Grid {service_point} {STATISTICS[key]}",
                unit_class=None if money else EnergyConverter.UNIT_CLASS,
                unit_of_measurement=self.hass.config.currency if money else UnitOfEnergy.KILO_WATT_HOUR,
            )
            async_add_external_statistics(self.hass, metadata, statistic_rows)
        if not settled_failed:
            self._rewrite.pop(service_point, None)
            if full:
                self._history_done.add(service_point)
        return reads
