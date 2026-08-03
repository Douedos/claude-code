# DICT-21 · Component prices, world trade, product data (namespaces cmdty/trade/product)
The three requested ad-hoc domains as concept sets — the graduation targets for DICT-20 datasets. All start life as `adhoc.*` manifests; concepts here define what they graduate INTO, so the schema exists before the first CSV lands (the B4/estimates principle again: abstraction first, wiring later).

## 1. Component & commodity prices (namespace cmdty; extends the macro.wti/gold family downmarket)
Subject kind: commodity (spec'd instrument: "DRAM DDR5 16Gb spot", not "memory").
| concept_id | definition | notes |
|---|---|---|
| cmdty.spot{code} | Spot/reference price of a spec'd commodity or component | code registry versioned: dram_ddr5_16gb, nand_tlc_512gb, lithium_carbonate_cn, polysilicon_mono, hrc_steel_us, ... spec change = NEW code + link.membership to predecessor, never a splice [KEY: silent spec splices are this domain's classic corruption] |
| cmdty.contract{code} | Front-month futures settle where exchange-traded | KT clean (exchange); preferred over survey spot when both exist |
| cmdty.trend_63d{code} | log(spot / spot 63 sessions back) | the "RAM price trend" concept; window on the series' own calendar |
| cmdty.vol_252d{code} | Realized vol of returns | irregular-cadence guard: min_obs scaled to cadence |
| cmdty.regime{code} | Percentile of spot in trailing 3y | context feature |
| cmdty.basket{basket_id} | Weighted composite (e.g. memory_complex = w·dram + w·nand) | weights versioned; V11 recompute identity |
Sources typical of the domain: exchange feeds (clean), price reporting agencies (survey-based, license-restricted, kt=arrival), scraped retail/spot boards (sandbox forever unless stabilized). Entity impact flows ONLY through link.exposure (DICT-20 §2) — e.g. dram_ddr5 → {memory maker: revenue+}, {server OEM: cost−}; E1/C2 consume the linked, signed series, never raw cmdty in per-entity formulas.

## 2. World trade (namespace trade; subject kinds country, trade_lane, category{hs})
The heavily-revised, heavily-lagged domain — treatment choices ARE the definitions.
| concept_id | definition | notes |
|---|---|---|
| trade.exports_usd{country, hs2?} | Monthly goods exports, USD, by HS-2 chapter when categorized | [PIT] customs data revises for months; each monthly release = vintage; kt = release arrival; first-print vs settled both servable (mode flag) |
| trade.imports_usd{country, hs2?} | Same, imports | |
| trade.balance{country} | exports − imports | computed |
| trade.lane_usd{from, to, hs2?} | Bilateral flow | [KEY] mirror asymmetry: A→B exports ≠ B←A imports (CIF/FOB, routing); we store BOTH sides + trade.mirror_gap as a data-quality-as-signal concept, never average |
| trade.yoy{...} | 12m log change of any flow concept | seasonality handled by yoy, not seasonal adjustment (SA models are vendor black boxes; NSA + yoy is reproducible) |
| trade.concentration{country} | HHI of export partners or categories | fragility context |
| trade.tariff_event | {imposer, target, hs_scope, rate, announced/effective KT split} | event tier; announcement KT is the market-relevant one (DICT-11 lesson) |
| freight.rate{lane_class} | Container/dry-bulk benchmark rates (baltic_dry, container composite, lane-specific) | higher frequency early-warning companion to customs flows |
Entity linkage: revenue-exposure by geography (segment footnotes, DICT-07) × trade.yoy of relevant lanes; link.exposure method=filing_derived carries the evidence passages.

## 3. Product-level data (namespace product; subject kinds product, category)
The most heterogeneous domain — catalog discipline is the whole game.
| concept_id | definition | notes |
|---|---|---|
| product.catalog | {product_id, entity_id (maker, via link), category chain, launch_date, discontinued_date, spec_ref} | subject registry made servable; product_id immutable across renames (interval metadata) |
| product.launch / product.discontinue | Events, KT = announcement | joins news.event_class=product candidates (DICT-17) |
| product.msrp{product} | List price at launch + revisions (each revision an event) | currency + market declared |
| product.street_price{product, market} | Observed selling price (scrape/panel source) | sandbox-heavy; kt=arrival strictly; [KEY] price CUTS mid-cycle are the demand signal (product.price_cut_flag derived) |
| product.rank{product, venue} | Sales/popularity rank on a venue (store, chart) | ordinal, venue-specific — never cross-venue comparable; venue_id is part of identity (the ESG methodology rule again) |
| product.entity_mix{entity} | Share of entity's linked catalog by category / age (freshness of portfolio) | derived from catalog; refresh-cycle features (median product age vs category norm) |
Aggregation to entities: product.* → entity features only through catalog links with declared weights (revenue share where known via segments, count-weighted fallback with flag). Guard: catalog coverage per entity published (like universe.coverage) — an entity with 3 of 40 products tracked serves null+flag on mix concepts, not a confident number from 7% coverage.

## 4. Shared validation additions
V-adhoc1: subject-map audit sampled per refresh (new native keys resolving to existing subjects — drift check). V-adhoc2 (trade): mirror_gap bounds; blowout → source revision probe. V-adhoc3 (cmdty): spec-registry check — a code's spec_ref hash may never change (spec change = new code, enforced). V-adhoc4 (product): rank ordinality (no numeric ops across venues); street_price vs msrp sanity band. Everything else inherits the light baseline + lifecycle caps from DICT-20.

## 5. Worked YAML — cmdty.trend_63d{dram_ddr5_16gb} (the user's "RAM price trend", end to end)
```yaml
concept_id: cmdty.trend_63d
subject: {kind: commodity, code: dram_ddr5_16gb, spec_ref: sha256:..., registry_version: cmdty-2026.08}
tier: market
definition: >
  63-session log return of DRAM DDR5 16Gb spot reference price. Sessions on the series'
  own publication calendar (weekdays, source holidays out). Spec changes create a new
  code; this concept never splices specs.
unit: ratio
period_basis: rolling(63, own_calendar)
formula: log(cmdty.spot[dram_ddr5_16gb] / lag(cmdty.spot[dram_ddr5_16gb], 63))
guards: {min_obs: 50, max_ffill: 1_period}
dataset: adhoc.dram_spot_v1 -> graduated 2026-Q4 (manifest DICT-20 §3; kt: arrival; history kt_reconstructed — asof panels exclude pre-arrival history)
links: [{entity: memory makers, channel: revenue, dir: +, method: curated, version: lk-12},
        {entity: server/device OEMs, channel: cost, dir: -, method: filing_derived, evidence: segment/cogs passages}]
validation: [V1, V2{range: [-2, 2]}, V8{staleness: 10d}, V9, V-adhoc3]
quality_tier: C  # single-source, survey-based; cap per DICT-15 §4 until second PRA or futures series wired
since: "1.3"
```
