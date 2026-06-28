from datetime import datetime, timezone

import pytest

from energy_tracker.models import Metric, RegionType
from energy_tracker.sources.base import SourceError
from energy_tracker.sources.fixture import FixtureSource


def _utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def test_fetch_returns_one_observation_per_hour_per_region():
    src = FixtureSource()
    obs = src.fetch(["PJM", "CISO"], _utc(2024, 1, 1), _utc(2024, 1, 1, 6))
    # 6 hours x 2 regions
    assert len(obs) == 12
    assert {o.region for o in obs} == {"PJM", "CISO"}
    assert all(o.metric is Metric.DEMAND for o in obs)
    assert all(o.region_type is RegionType.SYNTHETIC for o in obs)


def test_output_is_deterministic():
    src = FixtureSource()
    a = src.fetch(["PJM"], _utc(2024, 6, 1), _utc(2024, 6, 2))
    b = src.fetch(["PJM"], _utc(2024, 6, 1), _utc(2024, 6, 2))
    assert [o.value for o in a] == [o.value for o in b]


def test_results_sorted_by_region_then_time():
    src = FixtureSource()
    obs = src.fetch(["CISO", "PJM"], _utc(2024, 1, 1), _utc(2024, 1, 1, 3))
    keys = [(o.region, o.timestamp) for o in obs]
    assert keys == sorted(keys)


def test_demand_stays_within_expected_band():
    src = FixtureSource()
    obs = src.fetch(["PJM"], _utc(2024, 1, 1), _utc(2024, 1, 3))
    values = [o.value for o in obs]
    # +/-20% around PJM base load of 95,000 MW, minus weekend dip.
    assert min(values) > 95_000 * 0.7
    assert max(values) < 95_000 * 1.25


def test_invalid_window_raises():
    src = FixtureSource()
    with pytest.raises(SourceError):
        src.fetch(["PJM"], _utc(2024, 1, 2), _utc(2024, 1, 1))
