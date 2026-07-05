"""Offline synthetic source.

Produces deterministic, realistic-looking hourly demand so the whole system is
runnable and testable with **no network and no API key**. This matters here for
two reasons:

  * the build/CI environment blocks outbound data endpoints, and
  * deterministic data makes tests and AI-harness runs reproducible.

The shape mimics real load: a diurnal curve (overnight trough, afternoon/evening
peak) scaled by a per-region base load, with a mild weekday/weekend difference.
No randomness — same inputs always yield the same output.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta

from energy_tracker.models import (
    DemandObservation,
    Metric,
    RegionType,
    SourceInfo,
)
from energy_tracker.sources.base import DemandSource, SourceError

# Approximate average load (MW) per region, used to scale the synthetic curve.
# Values are illustrative, not authoritative — this is fixture data.
_BASE_LOAD_MW: dict[str, float] = {
    "PJM": 95_000,
    "MISO": 75_000,
    "ERCO": 55_000,   # ERCOT
    "CISO": 30_000,   # CAISO
    "SWPP": 30_000,   # SPP
    "NYIS": 18_000,   # NYISO
    "ISNE": 14_000,   # ISO-NE
}


class FixtureSource(DemandSource):
    """Deterministic synthetic demand for development and testing."""

    name = "fixture"

    def info(self) -> SourceInfo:
        return SourceInfo(
            name=self.name,
            description="Deterministic synthetic hourly demand (offline, no key)",
            region_type=RegionType.SYNTHETIC,
            requires_api_key=False,
            live=False,
        )

    def fetch(
        self,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric = Metric.DEMAND,
    ) -> list[DemandObservation]:
        if start >= end:
            raise SourceError("start must be before end")

        out: list[DemandObservation] = []
        for region in regions:
            base = _BASE_LOAD_MW.get(region.upper(), 20_000)
            cursor = start.replace(minute=0, second=0, microsecond=0)
            while cursor < end:
                out.append(
                    DemandObservation(
                        source=self.name,
                        region=region.upper(),
                        region_type=RegionType.SYNTHETIC,
                        metric=metric,
                        timestamp=cursor,
                        value=round(self._load_at(cursor, base), 1),
                        unit="MWh",
                    )
                )
                cursor += timedelta(hours=1)
        out.sort(key=lambda o: (o.region, o.timestamp))
        return out

    @staticmethod
    def _load_at(ts: datetime, base: float) -> float:
        # Diurnal curve: trough ~04:00, peak ~18:00. +/-20% of base.
        diurnal = math.sin((ts.hour - 10) / 24 * 2 * math.pi)
        weekend = 0.92 if ts.weekday() >= 5 else 1.0
        return base * weekend * (1 + 0.20 * diurnal)
