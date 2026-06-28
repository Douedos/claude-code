"""Normalized domain models.

Every data source — no matter how different its raw API — converts its output
into these types. That normalization is the whole point: once PJM, CAISO, EIA,
etc. all emit ``DemandObservation`` objects, the rest of the system (service,
API, future anomaly detection) never has to care where a number came from.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Metric(str, Enum):
    """What a single observation measures."""

    DEMAND = "demand"  # electricity consumption (load), MW-averaged over the hour
    NET_GENERATION = "net_generation"
    INTERCHANGE = "interchange"
    DAY_AHEAD_DEMAND_FORECAST = "day_ahead_demand_forecast"


class RegionType(str, Enum):
    """Spatial granularity of a region. New levels slot in as finer sources
    are added (e.g. PRICING_NODE for nodal LMP — the key to isolating
    individual large loads)."""

    BALANCING_AUTHORITY = "balancing_authority"
    PLANNING_AREA = "planning_area"
    ZONE = "zone"
    PRICING_NODE = "pricing_node"
    SYNTHETIC = "synthetic"  # fixture / test data


class DemandObservation(BaseModel):
    """A single measurement of electricity demand at one place and time.

    Immutable, source-tagged, and timezone-aware (always UTC) so observations
    from different feeds can be merged and compared without ambiguity.
    """

    source: str = Field(description="Adapter that produced this, e.g. 'eia930'")
    region: str = Field(description="Region code, e.g. 'PJM', 'CISO'")
    region_type: RegionType
    metric: Metric
    timestamp: datetime = Field(description="Start of the hour, UTC")
    value: float = Field(description="Measured value")
    unit: str = Field(default="MWh", description="Unit of `value`")

    model_config = {"frozen": True}


class SourceInfo(BaseModel):
    """Lightweight description of a data source for discovery endpoints."""

    name: str
    description: str
    region_type: RegionType
    requires_api_key: bool
    live: bool = Field(description="True if it reaches a real upstream feed")
