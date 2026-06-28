# Energy Consumption Tracker

Track US electricity consumption (demand) — live and historical — normalized
across data sources, at a granularity fine enough to help isolate datacenter and
large-industrial load growth.

This is the **minimum API**: a clean, extensible backbone you can grow into the
full tracker described in [`DATA_SOURCES.md`](./DATA_SOURCES.md).

## What it does today

- Serves normalized hourly **demand** observations over a small HTTP API.
- Ships two data sources behind one interface:
  - **`fixture`** — deterministic synthetic data; runs offline with no API key.
  - **`eia930`** — live US balancing-authority demand from [EIA API v2](https://www.eia.gov/opendata/)
    (needs a free `EIA_API_KEY`).
- A TTL cache so repeated polls don't hammer upstream feeds.
- Tests run fully offline (the EIA adapter is tested with a mocked transport).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# See output immediately (offline, no key):
energy-tracker --regions PJM,MISO,ERCO,CISO

# Run the API:
uvicorn energy_tracker.api:app --reload
# then open http://127.0.0.1:8000/docs
```

### Example requests

```bash
# Discover sources and their granularity
curl localhost:8000/sources

# Latest demand per region (offline fixture source)
curl "localhost:8000/demand?regions=PJM,CISO,ERCO&latest=true"

# Historical window
curl "localhost:8000/demand?regions=PJM&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z"

# Live data (requires EIA_API_KEY in environment / .env)
curl "localhost:8000/demand?source=eia930&regions=PJM&latest=true"
```

## Configuration

Copy `.env.example` to `.env`. Everything is optional — with no config the app
uses the offline `fixture` source. Set `EIA_API_KEY`
([register free](https://www.eia.gov/opendata/register.php)) to enable live data.

## Architecture

Strict one-directional layering — outer depends on inner, never the reverse:

```
api  →  service  →  registry  →  sources/*  →  models
```

| Layer | File | Responsibility |
|-------|------|----------------|
| Transport | `api.py` | HTTP parsing/validation only; no logic |
| Logic | `service.py` | Caching, `latest`, *(future: multi-source merge, anomaly detection)* |
| Wiring | `registry.py` | Builds a source by name — the one place that knows construction |
| Data access | `sources/*` | One adapter per feed, all returning the same model |
| Domain | `models.py` | Normalized, source-agnostic schema (`DemandObservation`) |

**Why this shape:** the project's real goal — spotting datacenter/industrial
load — needs *many* feeds combined (EIA-930, ISO nodal LMP, interconnection
queues…). Normalizing every source to one model and isolating it behind
`DemandSource` means each new feed is one self-contained class; nothing
downstream changes.

### Adding a new source (the extension path)

1. Create `sources/<name>.py` with a class subclassing `DemandSource`.
2. Implement `info()` and `fetch()`, returning `DemandObservation`s.
3. Register it in `registry.py`.

That's it — it's instantly available via `?source=<name>` and listed at
`/sources`. The roadmap targets (per the research report) are PJM/CAISO/ERCOT
nodal feeds, EPA CEMS, and FERC Form 714.

## Tests

```bash
pytest
```

## Roadmap

- Add ISO nodal LMP sources (finest spatial signal for isolating large loads).
- Add FERC Form 714 + interconnection-queue ingestion (leading indicators).
- Persistent storage for historical series; swap the in-memory cache for Redis.
- Anomaly/step-change detection to flag emerging datacenter/industrial load.
- A dashboard frontend.
