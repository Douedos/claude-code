from fastapi.testclient import TestClient

from energy_tracker.api import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_sources_includes_fixture_and_eia930():
    r = client.get("/sources")
    assert r.status_code == 200
    names = {s["name"] for s in r.json()}
    assert {"fixture", "eia930"} <= names


def test_demand_window_against_fixture():
    r = client.get(
        "/demand",
        params={
            "regions": "PJM,CISO",
            "source": "fixture",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-01T03:00:00Z",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 6  # 3 hours x 2 regions
    assert data[0]["source"] == "fixture"


def test_demand_latest():
    r = client.get("/demand", params={"regions": "PJM", "source": "fixture", "latest": "true"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["region"] == "PJM"


def test_demand_requires_window_when_not_latest():
    r = client.get("/demand", params={"regions": "PJM", "source": "fixture"})
    assert r.status_code == 422


def test_unknown_source_is_502():
    r = client.get("/demand", params={"regions": "PJM", "source": "nope", "latest": "true"})
    assert r.status_code == 502
