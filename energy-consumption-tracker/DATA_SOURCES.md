# US Electricity Consumption Data Sources — Research Report

**Goal:** Identify datasets (live + historical) for tracking US electricity
consumption/demand at a granularity fine enough to **isolate or infer datacenter
and large-industrial load activity**, covering both free/public and
paid/commercial sources, plus energy-market/derivatives data.

**Date:** 2026-06-28

## How to read the confidence markers

This report combines two inputs:

- **✅ Verified** — claim was extracted from a primary source and survived a
  3-vote adversarial fact-check (needed ≥2/3 to be killed). Citation inline.
- **◐ Domain knowledge** — well-established facts about these datasets that
  could **not** be independently re-verified in this run because the source
  host was blocked by the container's network egress policy (EIA, LBNL, and
  several ISO portals were unreachable). Treat as high-confidence-but-unaudited;
  confirm exact numbers against the live source before relying on them.

> ⚠️ Egress note: during the automated research run, `eia.gov`, `lbl.gov`,
> `osti.gov`, and several ISO domains returned policy blocks. The free
> government feeds below are the *backbone* of any real tracker, so their
> details are marked ◐ and flagged for confirmation.

---

## TL;DR — Recommended stack

For a tracker that gives **both a live and a historical view** at the finest
*practical* (and free) granularity for spotting datacenter/industrial growth:

1. **`gridstatus` (open-source Python library)** as the programmatic backbone —
   one consistent API across all 7 US ISOs + EIA, returns raw data in pandas.
   ✅ Free (BSD-3). This unifies most of the live layer.
2. **EIA-930 Hourly Electric Grid Monitor** (via EIA API v2) for nationwide
   balancing-authority hourly demand — the only truly nationwide live demand
   feed, free. ◐
3. **ISO nodal LMP feeds** (PJM, ERCOT, CAISO, MISO, SPP, NYISO, ISO-NE) for
   the **fine spatial signal** — thousands of pricing nodes; persistent local
   congestion is the closest free proxy for a large new load. ◐ / ✅
4. **Leading indicators for datacenter buildout:** ISO **interconnection /
   large-load queues** + **FERC Form 714** planning-area hourly demand. ✅
5. **EPA CEMS** hourly plant-level gross load as a complementary supply-side
   proxy. ◐
6. **Optional paid upgrades** for sub-minute latency / unit-level granularity:
   **Yes Energy Live Power** (60-second data) ✅, or **GridStatus.io** hosted
   API for managed production access ✅.

The honest limit: **no free public dataset reports an individual datacenter's
load directly.** You *infer* it by combining (a) fine-grained nodal prices/
congestion, (b) balancing-authority demand growth, and (c) interconnection-queue
and Form 714 leading indicators.

---

## Comparison table

| Source | What it measures | Spatial granularity | Temporal res. | History | Latency | Access | Cost |
|---|---|---|---|---|---|---|---|
| **EIA-930 / Hourly Electric Grid Monitor** ◐ | Demand, net generation, interchange | ~60+ balancing authorities (+ some sub-regions) | Hourly | ~mid-2015→ | ~1–2 h | EIA API v2 (key), CSV/JSON | Free |
| **EIA API v2 (923/860 etc.)** ◐ | Generation, capacity, fuel | Plant / state / national | Monthly–annual | Decades | Monthly | REST API (key) | Free |
| **PJM Data Miner 2** ◐ | LMP, load | Nodal (1000s) + zones | 5-min / hourly | Years | Near-real-time | REST API (free reg.) | Free |
| **ERCOT** ◐ | LMP, system/zonal load, SCED | Settlement points / nodes | 5–15 min | Years | Near-real-time | Public API / reports | Free |
| **CAISO OASIS** ◐ | LMP, area load | Nodal (1000s) | 5/15-min, hourly | Years | Near-real-time | REST API | Free |
| **MISO / SPP / NYISO / ISO-NE** ◐ | LMP, zonal load | Nodal + zones | 5-min / hourly | Years | Near-real-time | Portals / web-service APIs | Free |
| **Nodal LMP (any ISO)** ◐ | Locational price (congestion signal) | Thousands of nodes | 5-min / hourly | Years | Near-real-time | ISO APIs | Free |
| **FERC Form 714** ✅ | Planning-area **actual hourly demand** (8,760 values/yr) | Planning area / utility | Hourly | 2006→ (2006-2020 DB = 56 MB, 13 CSVs; 2011→ on e-Forms/XBRL) | Annual filing | Bulk CSV download | Free |
| **Interconnection / large-load queues** ✅ | Planned generation & large-load requests (leading indicator) | Project / node | Event-based | Multi-year | Periodic | ISO queue reports | Free |
| **EPA CEMS (CAMPD)** ◐ | Plant **gross load (MW)** + emissions | Unit / plant | Hourly | 1995→ | ~quarterly (hourly granularity) | API / bulk | Free |
| **LBNL data-center energy reports** ◐ | Estimated US datacenter consumption | National / sector | Periodic study | 2007→ | Report cadence | PDF | Free |
| **Nodal Exchange** ✅ | Nodal power **futures & options** | Hundreds of nodes (1,000+ contracts) | Daily/monthly contracts | Market history | Market | Exchange / brokers | Paid (market data) |
| **CME/NYMEX, ICE** ◐ | Power futures/options (hub-level) | Hubs/zones | Daily/monthly | Market history | Market | Exchange / vendors | Paid |
| **Yes Energy — Live Power** ✅ | Generation & transmission flows | Unit / line, 7 ISOs | **60-second** | — | Near-real-time | Subscription | Paid |
| **GridStatus.io (hosted API)** ✅ | ISO fuel mix, LMP (hubs/zones), net load | ISO / zone / hub | 5-min / hourly | Years | Near-real-time | REST API (key) + Python client | Freemium → Paid |
| **`gridstatus` (OSS library)** ✅ | Supply, demand, pricing across ISOs+EIA | ISO-wide (raw) | Per-source | Per-source | Per-source | Python (BSD-3) | Free |
| **Wood Mackenzie (Genscape), S&P Platts, LSEG/Refinitiv, Bloomberg/BNEF, Velocity Suite** ◐ | Proprietary power/load analytics | Varies (often asset-level) | Varies | Deep | Varies | Enterprise subscription | Paid ($$$) |

---

## 1. Live / near-real-time consumption

### EIA-930 Hourly Electric Grid Monitor ◐
The single most important **free, nationwide** live demand feed. Reports hourly
**demand**, net generation, and interchange for ~60+ US balancing authorities
(some large BAs are broken into sub-regions). History from ~mid-2015. Served
through **EIA API v2** (free API key; JSON/CSV; per-request row caps, generous
but throttled). Latency on the order of an hour or two. *Confirm current
coverage/latency at eia.gov — host was blocked during this run.*

### ISO/RTO real-time feeds ◐
All seven US ISOs publish load and price data **for free**, typically with a
free registration/API key:

- **PJM Data Miner 2** — REST API; nodal LMP (thousands of nodes), zonal load,
  5-min and hourly.
- **ERCOT** — public API/reports; settlement-point LMP, system & zonal load,
  SCED at 5–15 min.
- **CAISO OASIS** — REST API; nodal LMP, area load, 5/15-min and hourly.
- **MISO, SPP, NYISO, ISO-NE** — portals + web-service APIs; nodal/zonal LMP and
  zonal load at 5-min/hourly.

`gridstatus` (below) wraps most of these behind one interface. ✅

---

## 2. High spatial granularity — isolating datacenters / industrial centers

This is the hard part. **No free feed reports a single datacenter's draw.** The
practical proxies:

### Nodal LMP (locational marginal pricing) ◐
ISOs price energy at **thousands of nodes**. A large new load creates local
congestion that shows up as persistent price separation at nearby nodes — a
spatial fingerprint of demand growth. Free from every ISO.

### FERC Form 714 — planning-area hourly demand ✅
A **mandatory annual filing** (Federal Power Act, 18 CFR § 141.51). Respondents
report the planning area's **actual hourly demand in MW for every hour of the
year — 8,760 values per planning area per year.**
[ferc.gov](https://www.ferc.gov/industries-data/electric/general-information/electric-industry-forms/form-no-714-annual-electric/data)
- Historical **2006–2010** ships as the *2006-2020 Form 714 Database* (56 MB
  archive, 13 CSV tables). ✅
- **2011 onward** is on FERC's **e-Forms portal** after an Oct-2021 XBRL
  taxonomy upgrade. ✅

This gives **utility/planning-area-level** hourly demand — finer than BA, and a
good way to localize where load is concentrating.

### Interconnection & large-load queues — the leading indicator ✅
Large-load interconnection requests precede actual consumption, making queues
the best *forward* signal of datacenter buildout:
- US interconnection queues hold **~2.6 TW** of generation capacity — roughly
  **2× current installed capacity.** [RMI](https://rmi.org/interconnection-reform-ai-data-centers-generator-queues/) ✅
- In **ERCOT, 198 GW of large load applied for interconnection in Q1 2026
  alone.** [RMI](https://rmi.org/interconnection-reform-ai-data-centers-generator-queues/) ✅
- **Data centers alone could add ~100 GW of new US demand by 2035**, and pairing
  data centers with existing interconnection points could unlock **~50 GW
  quickly.** [RMI](https://rmi.org/interconnection-reform-ai-data-centers-generator-queues/) ✅

### Datacenter-specific estimates ◐
**LBNL's** periodic *US Data Center Energy Usage* reports are the standard
reference for national datacenter consumption estimates. (Host blocked this run —
fetch directly from lbl.gov.)

> ❗ One claim was **rejected** by verification: that "Live Power" data measures
> *individual units* directly — the granularity claim was overstated; treat
> unit-level attribution cautiously.

---

## 3. Supply-side / complementary

- **EPA CEMS (CAMPD)** ◐ — hourly **gross load (MW)** and emissions for fossil
  units, 1995→. A strong near-real-time **generation** proxy; free API/bulk.
- **EIA-923 / EIA-860** ◐ — monthly/annual generation and capacity by plant.
  Free via EIA API v2. Supply-side context, not live.

---

## 4. Energy-market / derivatives data

Markets price *expected* regional demand, so they're a complementary signal.

### Nodal Exchange ✅
The most location-granular power derivatives venue:
- **1,000+ power futures & options contracts on hundreds of unique nodal
  locations** — the largest set of nodal power futures/options in the world.
  [nodalexchange.com](https://www.nodalexchange.com/products-services/power/) ✅
- Contracts **settle to LMP or its components** (Energy + Congestion, or Energy
  only) as published by the RTOs/ISOs — so you can hedge nodal congestion
  directly. ✅
- Covers **seven US ISOs/RTOs + Mid-C** (ISO-NE, NYISO, PJM, MISO, ERCOT, SPP,
  CAISO). ✅

### CME/NYMEX & ICE ◐
Hub-level power futures and options (e.g., PJM Western Hub). Coarser than Nodal
Exchange spatially, deep liquidity. Paid market data.

### Day-ahead / real-time prices as demand proxies ✅/◐
Free from ISOs; rising prices at specific nodes corroborate load growth.

---

## 5. Commercial / paid providers

| Provider | Offering | Granularity | Tier |
|---|---|---|---|
| **Yes Energy — Live Power** ✅ | Proprietary generation & transmission, 7 US ISOs | **60-second** intervals, near-real-time | Paid |
| **GridStatus.io** ✅ | Hosted REST API: fuel mix, LMP (hubs/zones), net load | ISO/zone/hub, 5-min | Freemium → Paid |
| **Wood Mackenzie (Genscape)** ◐ | Power flows, plant monitoring | Asset-level | $$$ |
| **S&P Global / Platts, LSEG/Refinitiv, Bloomberg/BNEF, Velocity Suite (Hitachi)** ◐ | Power analytics, fundamentals, forecasts | Varies | $$$ |

**Yes Energy Live Power** ✅ — proprietary **60-second-interval** generation and
transmission data across CAISO, ERCOT, MISO, SPP, PJM, NYISO, ISO-NE —
far finer latency than aggregated ISO summaries.
[yesenergy.com](https://www.yesenergy.com/products/live-power)

---

## 6. Practical integration — building the tracker

### `gridstatus` (open-source) — the free backbone ✅
- Open-source **Python library, BSD-3**, consistent API across electricity
  **supply, demand, and pricing**. [github.com/gridstatus/gridstatus](https://github.com/gridstatus/gridstatus)
- Covers **CAISO, SPP, ISO-NE, MISO, ERCOT, NYISO, PJM** + Canadian IESO/AESO
  + **EIA** — one tool for nationwide demand/pricing. ✅
- Returns **raw / minimally-processed** data (fidelity to original ISO/EIA
  values — important when isolating load signals). ✅

### GridStatus.io (hosted API) — managed production option ✅
- Hosted **REST API + API key**; official Python client `gridstatusio`
  (Python 3.10+), `client.get_dataset()` with start/end/limit.
  [gridstatus.io/products/api](https://www.gridstatus.io/products/api) ✅
- Returns **pandas** by default (also polars / list-of-dicts) — easy pipeline
  integration. ✅
- Datasets like `ercot_fuel_mix`; fuel mix, locational pricing (hubs/zones),
  net load for multiple ISOs. ✅
- **Rate limits** per-second/minute/hour (HTTP 429); client does
  exponential-backoff retries; limits depend on tier. ✅
- Free plan caps usage (≈500k rows/month per the site; PyPI text says 1M — figure
  is inconsistent across their own docs, so verify before depending on it). ✅(1/3)

### EIA API v2 ◐
Free key; JSON/CSV; the canonical source for EIA-930 hourly demand and
EIA-923/860. The nationwide demand layer `gridstatus` also taps.

### Suggested architecture
```
            ┌─ EIA-930 (nationwide BA hourly demand)  ── live demand layer
gridstatus ─┼─ ISO nodal LMP + zonal load            ── fine spatial signal
   /EIA API └─ EPA CEMS hourly gross load             ── generation proxy
                         │
   FERC Form 714 (annual planning-area hourly) ───────── localized history
   ISO interconnection / large-load queues ──────────── leading indicator
                         │
   (optional) Yes Energy 60s / Nodal Exchange ───────── premium latency/markets
```
Combine: nodal congestion + BA/planning-area demand growth + queue activity →
the strongest *free* composite signal for emerging datacenter/industrial load.

---

## Caveats & what to confirm

1. **EIA / LBNL / some ISO specifics are ◐** — host egress was blocked during
   automated research. Confirm exact latency, history depth, and API row caps
   on the live sites before coding against them.
2. **No direct per-datacenter feed exists publicly** — all datacenter isolation
   is *inference* from the proxies above.
3. **GridStatus.io free-tier row cap is internally inconsistent** (500k vs 1M)
   across their own docs — verify current limits.
4. **Rejected claims** (failed adversarial verification, do **not** rely on):
   a specific PJM "~258 GW queue" figure, and the assertion that Live Power
   resolves *individual units* directly.

---

*Method: automated multi-agent deep-research run — 5 search angles, ~23 source
extractions, 25 candidate claims each adversarially verified by a 3-vote panel
(23 survived, 2 killed). Synthesis assembled here after the workflow's final
auto-synthesis step failed on an output-schema error; verified claims were
recovered directly from agent transcripts.*
