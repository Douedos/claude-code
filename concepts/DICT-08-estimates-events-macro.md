# DICT-08 · Estimates, events, macro (tiers: event/macro; estimates tier C until vendor wired)

## Earnings/event concepts (D8/E3 alignment)
| concept_id | definition |
|---|---|
| event.earnings_date_confirmed / estimated | With revision trail (supersessions) |
| event.earnings_time | BMO/AMC/unspecified |
| event.dividend_declaration / ex_date / pay_date | KT = declaration |
| event.guidance_event | From filing_item.guidance_revision |
| event.split_announced / merger_announced / spinoff_announced | From B5 candidates (announcement KT, distinct from effective) |
| event.index_add / index_drop | Reconstitution events |
| event.pm_contract | Polymarket contract linkage: {event entity, resolution_spec, market_price ref} |

## Estimates (schema now, adapter later — the abstraction is the point)
| concept_id | definition |
|---|---|
| est.eps_ntm_mean / median / std / count | Consensus NTM EPS distribution |
| est.revenue_ntm_mean | |
| est.eps_fy1 / fy2 | Fiscal-year anchored |
| est.revision_breadth_3m | (#up - #down)/#total revisions 63d |
| est.eps_revision_3m | Δ mean estimate / |mean| 63d |
| est.surprise_last | (actual - consensus)/|consensus| at last print |
Vendor_map empty except schema; wiring an estimates feed later = adapter + map fill, zero concept change (B4 principle). Estimates KT = revision timestamps (vendor-provided) — [PIT] the classic estimates trap is file-date vs revision-date; the map must bind revision-level data.

## Macro concepts (FRED-backed, vintage)
| concept_id | series intent (mapping to FRED ids in DICT-09) |
|---|---|
| macro.policy_rate / macro.ust_3m / ust_2y / ust_10y / ust_30y | Rates curve |
| macro.term_spread_10y_3m / 10y_2y | Computed |
| macro.credit_spread_baa_aaa / hy_oas / ig_oas | Credit |
| macro.cpi_yoy / core_pce_yoy / breakeven_5y5y | Inflation |
| macro.unemployment / payrolls_mom / claims_4wk | Labor |
| macro.indpro_yoy / gdp_now / retail_sales_yoy | Activity |
| macro.ism_pmi | tier B (licensing varies; FRED proxy) |
| macro.vix / move | Vol regime (market source) |
| macro.dxy / wti / gold | FX/commodities context |
| macro.gdp_deflator | Ohlson deflator input |
| macro.fin_conditions_nfci | Chicago Fed NFCI |
E1's regime features draw exclusively from these concepts (never raw FRED ids in module code).
