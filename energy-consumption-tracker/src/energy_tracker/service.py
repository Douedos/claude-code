"""Service layer: business logic between the API and the data sources.

Today it does two things: a small TTL cache (so repeated dashboard polls don't
hammer upstream feeds) and a `latest` convenience. It's deliberately the home
for everything that comes next — multi-source merging, unit normalization,
and the datacenter/industrial anomaly detection that is the project's reason
for existing — so that logic never leaks into the transport or source layers.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from energy_tracker.models import DemandObservation, Metric
from energy_tracker.registry import SourceRegistry


class _TTLCache:
    """Minimal in-process time-to-live cache. Swap for Redis later behind the
    same get/set shape without touching callers."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, list[DemandObservation]]] = {}

    def get(self, key: str) -> list[DemandObservation] | None:
        hit = self._store.get(key)
        if hit is None:
            return None
        expires_at, value = hit
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: list[DemandObservation]) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)


class DemandService:
    """Coordinates sources, caching, and higher-level queries."""

    def __init__(self, registry: SourceRegistry, cache_ttl_seconds: int = 300) -> None:
        self._registry = registry
        self._cache = _TTLCache(cache_ttl_seconds)

    def get_demand(
        self,
        source: str,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric = Metric.DEMAND,
    ) -> list[DemandObservation]:
        key = self._cache_key(source, regions, start, end, metric)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        result = self._registry.get(source).fetch(regions, start, end, metric)
        self._cache.set(key, result)
        return result

    def get_latest(
        self,
        source: str,
        regions: Sequence[str],
        metric: Metric = Metric.DEMAND,
        lookback_hours: int = 48,
    ) -> list[DemandObservation]:
        """Most recent observation per region within the lookback window.

        A wide lookback covers feed publication lag (EIA-930 trails ~1-2h).
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=lookback_hours)
        observations = self.get_demand(source, regions, start, end, metric)

        latest: dict[str, DemandObservation] = {}
        for obs in observations:
            current = latest.get(obs.region)
            if current is None or obs.timestamp > current.timestamp:
                latest[obs.region] = obs
        return [latest[r] for r in sorted(latest)]

    @staticmethod
    def _cache_key(
        source: str,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric,
    ) -> str:
        regions_part = ",".join(sorted(r.upper() for r in regions))
        return f"{source}|{regions_part}|{metric.value}|{start.isoformat()}|{end.isoformat()}"
