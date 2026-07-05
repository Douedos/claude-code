"""HTTP API (FastAPI).

Thin transport layer: parse/validate the request, call the service, return JSON.
No business logic lives here. Endpoints are plain ``def`` functions — FastAPI
runs them in a threadpool, which keeps the synchronous source adapters simple to
read while staying non-blocking.

Run locally:
    uvicorn energy_tracker.api:app --reload
Interactive docs at /docs once running.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query

from energy_tracker.config import Settings, load_settings
from energy_tracker.models import DemandObservation, Metric, SourceInfo
from energy_tracker.registry import SourceRegistry
from energy_tracker.service import DemandService
from energy_tracker.sources.base import SourceError


@lru_cache
def _settings() -> Settings:
    return load_settings()


@lru_cache
def _service() -> DemandService:
    settings = _settings()
    return DemandService(
        SourceRegistry(settings),
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )


def get_service() -> DemandService:
    """Dependency seam: override in tests to inject a stub service."""
    return _service()


app = FastAPI(
    title="Energy Consumption Tracker API",
    version="0.1.0",
    summary="Live + historical US electricity demand, normalized across sources.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sources", response_model=list[SourceInfo])
def list_sources(service: DemandService = Depends(get_service)) -> list[SourceInfo]:
    """Discover available data sources and their granularity / requirements."""
    registry = SourceRegistry(_settings())
    return [registry.get(name).info() for name in registry.names()]


@app.get("/demand", response_model=list[DemandObservation])
def get_demand(
    regions: str = Query(description="Comma-separated region codes, e.g. PJM,CISO"),
    source: str | None = Query(default=None, description="Source name; defaults to config"),
    start: datetime | None = Query(default=None, description="UTC ISO8601 start (inclusive)"),
    end: datetime | None = Query(default=None, description="UTC ISO8601 end (exclusive)"),
    metric: Metric = Query(default=Metric.DEMAND),
    latest: bool = Query(default=False, description="Return only the most recent point per region"),
    service: DemandService = Depends(get_service),
) -> list[DemandObservation]:
    """Demand observations for one or more regions.

    With ``latest=true`` returns a single most-recent point per region (ignores
    start/end). Otherwise requires a ``[start, end)`` UTC window.
    """
    region_list = [r.strip() for r in regions.split(",") if r.strip()]
    if not region_list:
        raise HTTPException(status_code=422, detail="at least one region is required")

    source_name = source or _settings().default_source

    try:
        if latest:
            return service.get_latest(source_name, region_list, metric)
        if start is None or end is None:
            raise HTTPException(
                status_code=422,
                detail="start and end are required unless latest=true",
            )
        return service.get_demand(
            source_name, region_list, _as_utc(start), _as_utc(end), metric
        )
    except SourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC; convert aware ones to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
