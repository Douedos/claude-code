"""EIA-930 adapter tests with a mocked HTTP transport — no network required."""

from datetime import datetime, timezone

import httpx
import pytest

from energy_tracker.models import Metric, RegionType
from energy_tracker.sources.base import SourceError
from energy_tracker.sources.eia930 import EIA930Source

_SAMPLE = {
    "response": {
        "data": [
            {"period": "2024-01-01T05", "respondent": "PJM",
             "type": "D", "value": "91234", "value-units": "megawatthours"},
            {"period": "2024-01-01T04", "respondent": "PJM",
             "type": "D", "value": "89000", "value-units": "megawatthours"},
        ]
    }
}


def _client_returning(payload, capture=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def test_parses_rows_into_normalized_observations():
    src = EIA930Source("KEY", client=_client_returning(_SAMPLE))
    obs = src.fetch(["PJM"], _utc(2024, 1, 1, 4), _utc(2024, 1, 1, 6))
    assert len(obs) == 2
    first = obs[0]
    assert first.source == "eia930"
    assert first.region == "PJM"
    assert first.region_type is RegionType.BALANCING_AUTHORITY
    assert first.value == 89000.0  # sorted ascending by time
    assert first.timestamp == _utc(2024, 1, 1, 4)


def test_sends_expected_query_params():
    captured: list[httpx.Request] = []
    src = EIA930Source("SECRET", client=_client_returning(_SAMPLE, captured))
    src.fetch(["PJM", "ciso"], _utc(2024, 1, 1), _utc(2024, 1, 2), Metric.DEMAND)
    url = captured[0].url
    assert url.params.get("api_key") == "SECRET"
    assert url.params.get("frequency") == "hourly"
    assert url.params.get("facets[type][]") == "D"
    # both regions, uppercased
    respondents = url.params.get_list("facets[respondent][]")
    assert respondents == ["PJM", "CISO"]


def test_missing_api_key_raises():
    src = EIA930Source(None, client=_client_returning(_SAMPLE))
    with pytest.raises(SourceError, match="EIA_API_KEY"):
        src.fetch(["PJM"], _utc(2024, 1, 1), _utc(2024, 1, 2))


def test_http_error_becomes_source_error():
    def boom(request):
        return httpx.Response(500, text="server error")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    src = EIA930Source("KEY", client=client)
    with pytest.raises(SourceError, match="EIA request failed"):
        src.fetch(["PJM"], _utc(2024, 1, 1), _utc(2024, 1, 2))


def test_malformed_row_becomes_source_error():
    bad = {"response": {"data": [{"period": "2024-01-01T05", "respondent": "PJM"}]}}
    src = EIA930Source("KEY", client=_client_returning(bad))
    with pytest.raises(SourceError, match="unexpected EIA row"):
        src.fetch(["PJM"], _utc(2024, 1, 1), _utc(2024, 1, 2))
