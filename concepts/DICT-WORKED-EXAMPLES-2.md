# DICT-WORKED-EXAMPLES-2 · Layer-side examples (DICT-10..14 instantiated)
Six worked artifacts for the abstraction layer itself, same template discipline as WORKED-EXAMPLES v1.

## 1. Identity ledger entry — a ticker recycling case (DICT-10)
```yaml
# Entity A dies, its ticker is reassigned to entity B eight months later.
- {id_kind: ticker_exchange, value: "XYZ:XNAS", entity: ent_000123, security: sec_000123a,
   listing: lst_000123a1, interval: ["2014-03-11", "2021-06-30"), closed_by: action.delisting}
- {id_kind: ticker_exchange, value: "XYZ:XNAS", entity: ent_009911, security: sec_009911a,
   listing: lst_009911a1, interval: ["2022-02-14", null)}
# resolve(eodhd, "XYZ.US", asof=2020-05-01) -> ent_000123 (interval hit)
# resolve(eodhd, "XYZ.US", asof=2023-05-01) -> ent_009911
# I3 catches the vendor feed that keeps posting to the dead entity after 2022-02-14.
```

## 2. ident.figi (identifier as a full concept YAML)
```yaml
concept_id: ident.figi
tier: reference
definition: >
  OpenFIGI identifier at listing level. Preferred public join key: free redistribution,
  never recycled, one per (security, exchange). Composite/share-class FIGIs stored as
  separate id_kinds (ident.figi_composite) — never conflated with listing-level.
unit: id_string
period_basis: interval_valid
vendor_map:
  openfigi: {endpoint: mapping, keys_in: [isin+mic, cusip, ticker+mic]}
validation: [I1, I2{triangle: [figi, isin, ticker_exchange]}]
quality_tier: A
since: "1.1"
```

## 3. AdjustmentChain — late-discovered split (DICT-11, the [PIT] case)
```yaml
listing: lst_000777a1
chain_v1:                       # built 2025-08-01; the 2025-07-15 split not yet confirmed (single source)
  - {ex_date: 2023-04-03, factor: 0.25, source: action.split cnf_2023_881}
chain_v2:                       # built 2025-08-06 after quorum confirmed the July split
  - {ex_date: 2023-04-03, factor: 0.25, source: cnf_2023_881}
  - {ex_date: 2025-07-15, factor: 0.5,  source: cnf_2025_142, kt_confirmed: 2025-08-06T14:02Z}
# panel(asof=2025-08-04) MUST use chain_v1 (the split wasn't knowable) -> momentum shows the raw gap,
# A2 return-spike audit has an open probe. panel(asof=2025-08-07) uses chain_v2. Both are correct;
# serving v2 for the 08-04 asof is look-ahead. Golden fixture: both panels pinned.
```

## 4. universe.investable_v1 (universe as a concept YAML, DICT-12)
```yaml
concept_id: universe.investable_v1
tier: reference
definition: >
  Rule-based investable universe, US primary listings: primary listing only; price >= 1 USD;
  market.dollar_volume_63d >= cross-sectional p10; no pending delisting action; coverage of
  {raw.revenue, raw.total_assets, raw.price_close} >= 90% trailing 4 FQ. Rule frozen; any change
  ships as universe.investable_v2 with its own history — v1 keeps serving [PIT].
unit: membership
period_basis: daily
inputs: [ident.primary_listing, raw.price_close, market.dollar_volume_63d, event.action_pending, universe.coverage]
validation: [interval_integrity, churn_monitor{turnover_z_max: 4}, reconstruction_golden]
quality_tier: A
since: "1.1"
```

## 5. DAL request/response — mixed provenance surfaced (DICT-13)
```yaml
request: {concepts: [derived.roic], scope: universe.investable_v1, asof: 2026-07-31T21:00Z,
          span: latest_TTM, options: {quality_floor: B}}
panel:
  mode: asof(2026-07-31T21:00Z)
  cells_sample:
    - {entity: ent_000123, value: 0.184, status: ok,
       provenance: {source: computed{roic_f_v3}, flag: reported, vintage_id: v_88121,
                    inputs: {raw.ebit: {vendor: eodhd, flag: reported}, raw.tax_expense: {vendor: eodhd},
                             derived.invested_capital: {flag: computed}}}}
    - {entity: ent_004410, value: null, status: blocked,
       provenance: {finding: "V3 identity fail: assets != liab+equity, tol 2% (vintage v_88093)"}}
    - {entity: ent_007702, value: 0.121, status: ok,
       provenance: {source: computed, flag: proxy, note: "ebit via revenue-cogs-sga fallback"}}
  meta: {coverage: {derived.roic: {ok: 2811, gap: 74, blocked: 12}},
         mixed_provenance: {derived.roic: 0.031},        # 3.1% of cells on fallback path — visible, refusable
         dict_version: "1.1", map_version: "eodhd-2026.07", config_version: "cfg-119"}
```

## 6. AdapterDescriptor + failover seam (DICT-14)
```yaml
adapter: newvendor_fundamentals_v1
capabilities:
  - {tier: raw_item, concepts: map_ref: dict9/newvendor.yaml, granularity: FQ, history_from: 2005}
rate_limits: {rps: 4, daily_quota: 20k}
kt_policy: {fundamentals: vendor_revision_timestamp}     # honest KT — the estimates-trap rule applied to fundamentals
entitlement_ref: ent.newvendor_2026
# Promotion path (DICT-14 §6): ingest warm 60d as V6 secondary vs eodhd primary ->
# meta.vendor_drift stable & coverage >= primary-5pp -> config event cfg-120 flips primary for
# concept-group raw_item.balance_sheet on 2026-10-01 -> V10 straddles the seam date on purpose.
```
