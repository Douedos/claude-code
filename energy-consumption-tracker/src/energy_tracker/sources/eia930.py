"""EIA-930 Hourly Electric Grid Monitor adapter.

The only free, nationwide live demand feed: hourly demand / net generation /
interchange for ~60+ US balancing authorities, via EIA API v2.

  Docs:   https://www.eia.gov/opendata/
  Route:  /v2/electricity/rto/region-data/data/
  Auth:   free API key (EIA_API_KEY)

NOTE: the build environment blocks api.eia.gov, so this adapter is exercised by
unit tests with a mocked HTTP client rather than live calls. It runs for real
anywhere outbound HTTPS to api.eia.gov is permitted.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

import httpx

from energy_tracker.models import (
    DemandObservation,
    Metric,
    RegionType,
    SourceInfo,
)
from energy_tracker.sources.base import DemandSource, SourceError

_BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"

# Map our normalized Metric onto EIA's `type` facet codes.
_METRIC_TO_EIA_TYPE: dict[Metric, str] = {
    Metric.DEMAND: "D",
    Metric.NET_GENERATION: "NG",
    Metric.INTERCHANGE: "TI",
    Metric.DAY_AHEAD_DEMAND_FORECAST: "DF",
}


class EIA930Source(DemandSource):
    """Live US balancing-authority hourly demand from EIA API v2."""

    name = "eia930"

    def __init__(
        self,
        api_key: str | None,
        *,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
        page_length: int = 5000,
    ) -> None:
        self._api_key = api_key
        # Injectable client makes the adapter unit-testable without network.
        self._client = client or httpx.Client(timeout=timeout)
        self._page_length = page_length

    def info(self) -> SourceInfo:
        return SourceInfo(
            name=self.name,
            description="EIA-930 hourly demand for US balancing authorities",
            region_type=RegionType.BALANCING_AUTHORITY,
            requires_api_key=True,
            live=True,
        )

    def fetch(
        self,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric = Metric.DEMAND,
    ) -> list[DemandObservation]:
        if not self._api_key:
            raise SourceError("EIA_API_KEY is not configured")
        if start >= end:
            raise SourceError("start must be before end")

        params = self._build_params(regions, start, end, metric)
        try:
            resp = self._client.get(_BASE_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            raise SourceError(f"EIA request failed: {exc}") from exc

        rows = payload.get("response", {}).get("data", [])
        observations = [self._parse_row(row, metric) for row in rows]
        observations.sort(key=lambda o: (o.region, o.timestamp))
        return observations

    def health(self) -> bool:
        return bool(self._api_key)

    # -- internals ---------------------------------------------------------

    def _build_params(
        self,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
        metric: Metric,
    ) -> list[tuple[str, str]]:
        # EIA expects repeated keys for array params, so we use a list of pairs.
        params: list[tuple[str, str]] = [
            ("api_key", self._api_key or ""),
            ("frequency", "hourly"),
            ("data[]", "value"),
            ("facets[type][]", _METRIC_TO_EIA_TYPE[metric]),
            ("start", start.strftime("%Y-%m-%dT%H")),
            ("end", end.strftime("%Y-%m-%dT%H")),
            ("sort[0][column]", "period"),
            ("sort[0][direction]", "desc"),
            ("length", str(self._page_length)),
        ]
        params += [("facets[respondent][]", r.upper()) for r in regions]
        return params

    def _parse_row(self, row: dict, metric: Metric) -> DemandObservation:
        try:
            return DemandObservation(
                source=self.name,
                region=row["respondent"],
                region_type=RegionType.BALANCING_AUTHORITY,
                metric=metric,
                timestamp=self._parse_period(row["period"]),
                value=float(row["value"]),
                unit=row.get("value-units", "MWh"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SourceError(f"unexpected EIA row shape: {row!r}") from exc

    @staticmethod
    def _parse_period(period: str) -> datetime:
        # EIA hourly periods look like "2024-01-01T05" (UTC). Be lenient about
        # an optional ":00" suffix some routes include.
        fmt = "%Y-%m-%dT%H:%M" if len(period) > 13 else "%Y-%m-%dT%H"
        return datetime.strptime(period, fmt).replace(tzinfo=timezone.utc)
