"""Data coordinator: fetches everything from CWFIS / Open-Meteo once per update and does the maths.

Every entity reads from `coordinator.data` (a plain dict built in `_async_update_data`), so the
servers are queried once per update no matter how many entities exist.

Data flow per update:
  1. Reported fires (required; if this fails the whole update fails and HA retries).
  2. Prescribed burns, hotspots, perimeters, fire danger, last year's numbers and the smoke
     forecast (all optional; if one fails only its own sensors show "unknown").
  3. Distances/bearings from Home and every extra watch zone to each active fire.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from math import cos, radians

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_RADIUS,
    CONF_SMOKE_RADIUS,
    CONF_ZONES,
    CWFIF_WFS,
    DANGER_LEVELS,
    DEFAULT_RADIUS,
    DEFAULT_SMOKE_RADIUS,
    DOMAIN,
    FIRE_FIELDS,
    LAYER_DANGER,
    LAYER_HOTSPOTS,
    LAYER_PERIMETERS,
    LAYER_PRESCRIBED,
    LAYER_REPORTED,
    LEGACY_WFS,
    OPEN_METEO_URL,
    PROVINCES,
    STAGES,
    UPDATE_INTERVAL,
)
from .helpers import bearing, dedupe, fire_size, has_xy, km, pct_change, points

_LOGGER = logging.getLogger(__name__)

# Anything a flaky server or unexpected response can raise while we parse it.
FETCH_ERRORS = (aiohttp.ClientError, TimeoutError, KeyError, ValueError, TypeError, IndexError)


def _utc_stamp(when: datetime) -> str:
    """Format a datetime as the UTC timestamp GeoServer's CQL filters expect."""
    return dt_util.as_utc(when).strftime("%Y-%m-%dT%H:%M:%SZ")


class CwfisCoordinator(DataUpdateCoordinator[dict]):
    """Fetches and combines all CWFIS data for the integration."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Read the options once; the integration reloads whenever they change."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.session = async_get_clientsession(hass)
        self.radius = entry.options.get(CONF_RADIUS, DEFAULT_RADIUS)
        self.smoke_radius = entry.options.get(CONF_SMOKE_RADIUS, DEFAULT_SMOKE_RADIUS)
        self.zone_ids = entry.options.get(CONF_ZONES, [])
        self._last_year_cache: dict = {}  # last year's totals only change once a day

    # ------------------------------------------------------------------
    # Low-level requests
    # ------------------------------------------------------------------
    async def _wfs(self, url: str, params: dict) -> list[dict]:
        """Run a WFS GetFeature request and return the GeoJSON features."""
        params = {"SERVICE": "WFS", "REQUEST": "GetFeature", "OUTPUTFORMAT": "application/json", **params}
        async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            resp.raise_for_status()
            return (await resp.json(content_type=None))["features"]

    async def _cwfif(self, layer: str, fields: str, cql: str) -> list[dict]:
        """Query a CWFIF fire layer with a CQL filter; returns each feature's properties."""
        params = {"VERSION": "2.0.0", "TYPENAMES": layer, "PROPERTYNAME": fields, "CQL_FILTER": cql}
        return [feature["properties"] for feature in await self._wfs(CWFIF_WFS, params)]

    async def _around(self, layer: str, fields: str, lat: float, lon: float, reach_km: float) -> list[dict]:
        """Query a legacy CWFIS layer for features inside a box of ±reach_km around a point.

        WFS 1.0.0 is used on purpose: it keeps the BBOX in plain lon/lat order.
        """
        dlat = reach_km / 111  # ~111 km per degree of latitude
        dlon = reach_km / (111 * max(cos(radians(lat)), 0.01))  # degrees of longitude shrink towards the poles
        return await self._wfs(LEGACY_WFS, {
            "VERSION": "1.0.0", "TYPENAME": layer, "PROPERTYNAME": fields, "SRSNAME": "EPSG:4326",
            "BBOX": f"{lon - dlon},{lat - dlat},{lon + dlon},{lat + dlat},EPSG:4326",
        })

    async def _optional(self, coro):
        """Await an optional request; on any failure log at debug level and return None."""
        try:
            return await coro
        except FETCH_ERRORS as err:
            _LOGGER.debug("Optional CWFIS request failed: %s", err)
            return None

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------
    async def _async_update_data(self) -> dict:
        """Build the data dict every entity reads from."""
        year = dt_util.now().year
        midnight = _utc_stamp(dt_util.start_of_local_day())
        now_cql = "now()>=record_start AND now()<=record_end"  # each fire's current record only

        try:
            # This season's fires PLUS any earlier-season fire still burning, so fires that carry
            # over New Year don't vanish (and don't trigger false "fire out" alerts) at midnight.
            fires = dedupe(await self._cwfif(
                LAYER_REPORTED, FIRE_FIELDS, f"(fire_year={year} OR stage_of_control_status<>'EX') AND {now_cql}"))
            # Fires that already existed at local midnight; anything else was reported today.
            known = {f.get("national_fire_id") for f in await self._cwfif(
                LAYER_REPORTED, "national_fire_id",
                f"fire_year={year} AND record_start BEFORE {midnight} AND record_end AFTER {midnight}",
            )}
        except FETCH_ERRORS as err:
            raise UpdateFailed(f"CWFIS request failed: {err}") from err

        burns = await self._optional(self._cwfif(
            LAYER_PRESCRIBED, "national_fire_id,stage_of_control_status,latitude,longitude", now_cql))
        if burns is not None:
            burns = [b for b in burns
                     if b.get("stage_of_control_status") != "EX" and has_xy(b.get("latitude"), b.get("longitude"))]

        for fire in fires:
            fire["agency_code"] = fire.get("agency_code") or "Unknown"
        season = [f for f in fires if f.get("fire_year") == year]  # year-to-date numbers
        burning = [f for f in fires if f.get("stage_of_control_status") != "EX"]
        # Fires we can place on a map and track over time need an ID and valid coordinates.
        trackable = [f for f in burning if f.get("national_fire_id") and has_xy(f.get("latitude"), f.get("longitude"))]

        zones = self._zones()
        results = await asyncio.gather(*(self._zone_data(*zone, trackable, burns) for zone in zones.values()))
        by_zone = dict(zip(zones, results))

        total, area = len(season), round(sum(fire_size(f) for f in season))
        prev, smoke = await asyncio.gather(self._last_year(year), self._optional(self._smoke_forecast()))
        provinces = {
            code: {
                "active": sum(f["agency_code"] == code for f in burning),
                "area": round(sum(fire_size(f) for f in season if f["agency_code"] == code)),
            }
            for code in sorted({f["agency_code"] for f in fires})
        }
        home_fires = by_zone["home"]["all"]

        # Keys ending in "_attrs" are picked up automatically as that sensor's attributes.
        return {
            "zones": by_zone,
            "fires": {f["national_fire_id"]: f for f in home_fires},  # map markers, measured from Home
            "provinces": provinces,
            "reported_today": sum(f.get("national_fire_id") not in known for f in season),
            "active": len(burning),
            "active_attrs": {
                **{name.lower().replace(" ", "_"): sum(f.get("stage_of_control_status") == code for f in burning)
                   for code, name in STAGES.items()},
                "by_province": {PROVINCES.get(c, c): p["active"] for c, p in provinces.items() if p["active"]},
            },
            "out": sum(f.get("stage_of_control_status") == "EX" for f in season),
            "total": total,
            "area": area,
            "area_attrs": {"by_province_ha": {PROVINCES.get(c, c): p["area"] for c, p in provinces.items()}},
            "fires_vs_last_year": pct_change(total, prev and prev["total"]),
            "fires_vs_last_year_attrs": {"this_year": total, "same_date_last_year": prev and prev["total"]},
            "area_vs_last_year": pct_change(area, prev and prev["area"]),
            "area_vs_last_year_attrs": {"this_year_ha": area, "same_date_last_year_ha": prev and prev["area"]},
            "smoke_forecast": smoke and smoke["max_24h"],
            "smoke_forecast_attrs": smoke and {k: v for k, v in smoke.items() if k != "max_24h"},
            # Candidate smoke sources for the Fire upwind / Wildfire smoke binary sensors.
            "smoke_pool": [f for f in home_fires if f["distance"] <= self.smoke_radius],
        }

    # ------------------------------------------------------------------
    # Per-zone proximity
    # ------------------------------------------------------------------
    def _zones(self) -> dict:
        """Home plus every configured extra zone that still exists: id -> (name, lat, lon)."""
        found = {"home": ("Home", self.hass.config.latitude, self.hass.config.longitude)}
        for zone_id in self.zone_ids:
            state = self.hass.states.get(zone_id)
            if zone_id != "zone.home" and state and "latitude" in state.attributes:
                found[zone_id] = (state.name, state.attributes["latitude"], state.attributes["longitude"])
        return found

    async def _zone_data(self, name: str, lat: float, lon: float, fires: list[dict], burns: list | None) -> dict:
        """Everything measured relative to one zone."""
        radius = self.radius
        spots, perims, danger = await asyncio.gather(
            self._optional(self._around(LAYER_HOTSPOTS, "lat,lon", lat, lon, radius)),
            self._optional(self._around(LAYER_PERIMETERS, "geometry", lat, lon, radius)),
            # A tiny box (0.5 km) is enough to find the danger polygon covering the zone itself.
            self._optional(self._around(LAYER_DANGER, "GRIDCODE", lat, lon, 0.5)),
        )

        # Every trackable fire with distance/bearing from this zone, nearest first.
        here = sorted(
            ({**f, "distance": round(km(lat, lon, f["latitude"], f["longitude"]), 1),
              "bearing": bearing(lat, lon, f["latitude"], f["longitude"])} for f in fires),
            key=lambda f: f["distance"],
        )
        # Distance to every perimeter vertex; the closest one approximates the nearest fire edge.
        edges = [km(lat, lon, y, x)
                 for p in perims or [] for x, y, *_ in points((p.get("geometry") or {}).get("coordinates"))]
        # Valid danger codes only (0-4); anything else is "no data".
        codes = [int(code) for p in danger or []
                 if isinstance(code := (p.get("properties") or {}).get("GRIDCODE"), (int, float))
                 and 0 <= code < len(DANGER_LEVELS)]
        if spots is not None:
            spots = [s["properties"] for s in spots
                     if has_xy((s.get("properties") or {}).get("lat"), (s.get("properties") or {}).get("lon"))]

        return {
            "name": name,
            "all": here,
            "nearby": [f for f in here if f["distance"] <= radius],
            "nearest": here[0] if here else None,
            "hotspots": None if spots is None else sum(km(lat, lon, s["lat"], s["lon"]) <= radius for s in spots),
            "perimeter": round(min(edges), 1) if edges else None,
            "danger": DANGER_LEVELS[max(codes)] if codes else None,
            "prescribed": None if burns is None else sum(
                km(lat, lon, b["latitude"], b["longitude"]) <= radius for b in burns),
        }

    # ------------------------------------------------------------------
    # Optional extras
    # ------------------------------------------------------------------
    async def _last_year(self, year: int) -> dict | None:
        """Season totals exactly as they stood at this moment last year (fetched once a day)."""
        cache = self._last_year_cache
        today = dt_util.now().date()
        if cache.get("date") != today:
            now = dt_util.utcnow()
            try:
                then = now.replace(year=now.year - 1)
            except ValueError:  # today is Feb 29 and last year had none
                then = now.replace(year=now.year - 1, day=28)
            stamp = _utc_stamp(then)
            prev = await self._optional(self._cwfif(
                LAYER_REPORTED, "stage_of_control_status,fire_size",
                f"fire_year={year - 1} AND record_start BEFORE {stamp} AND record_end AFTER {stamp}",
            ))
            if prev is None:  # request failed: keep yesterday's value rather than going blank
                return cache.get("value")
            cache.update(date=today, value={"total": len(prev), "area": round(sum(fire_size(f) for f in prev))})
        return cache["value"]

    async def _smoke_forecast(self) -> dict | None:
        """Highest forecast PM2.5 at Home over the next 24 h and 48 h (Open-Meteo / ECMWF CAMS)."""
        params = {"latitude": self.hass.config.latitude, "longitude": self.hass.config.longitude,
                  "hourly": "pm2_5", "forecast_days": 3, "timezone": "UTC"}
        async with self.session.get(OPEN_METEO_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            hourly = (await resp.json(content_type=None))["hourly"]

        now = dt_util.utcnow()
        series = [(datetime.fromisoformat(t).replace(tzinfo=timezone.utc), value)
                  for t, value in zip(hourly["time"], hourly["pm2_5"]) if value is not None]

        def peak(hours: int):
            """(time, value) of the highest reading from an hour ago until `hours` ahead."""
            window = [p for p in series if now - timedelta(hours=1) <= p[0] <= now + timedelta(hours=hours)]
            return max(window, key=lambda p: p[1], default=(None, None))

        (t24, v24), (t48, v48) = peak(24), peak(48)
        if v24 is None:  # no usable forecast values
            return None
        return {
            "max_24h": round(v24, 1),
            "peak_time_24h": dt_util.as_local(t24).isoformat(),
            "max_48h": round(v48, 1),
            "peak_time_48h": dt_util.as_local(t48).isoformat(),
            "source": "Open-Meteo / ECMWF CAMS",
        }
