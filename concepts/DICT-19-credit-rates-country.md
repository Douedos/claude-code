# DICT-19 · Credit, rates, sovereign & country extension (tiers: macro/event; namespaces sov/credit/rates/country)
Extends DICT-08 macro with domains EODHD serves natively (DICT-15): sovereign credit, corporate credit aggregates, global policy/reference rates, macro release events, and a country fundamentals panel. FRED remains primary for vintaged US series; these concepts fill what FRED lacks or add a V6 second leg.

## 1. Sovereign credit (daily/weekly; per country ISO-3166)
| concept_id | definition | notes |
|---|---|---|
| sov.cds_5y{country} | 5y sovereign CDS spread, bps | V2 [0, 10000]; V4 jump-monitored |
| sov.rating{country} | Composite agency rating on a 21-notch ordinal scale (AAA=1); per-agency variants sov.rating_{agency} | [KEY] ratings are EVENTS not series: KT = rating action date; served as step function; outlook separate: sov.outlook ∈ {pos, stable, neg, watch} |
| sov.default_spread{country} | Vendor default-spread estimate | tier C (methodology opaque; Damodaran-style) |
| sov.risk_premium{country} | Equity risk premium add-on per country | tier C, same caveat; used as context feature only, never in indicator formulas without methodology pin |

## 2. Corporate credit aggregates (market-level context; daily)
| concept_id | definition | notes |
|---|---|---|
| credit.cmdi | Corporate credit market distress indicator | secondary to macro.hy_oas family as regime input; correlated but distinct construction |
| credit.hqm_yield{maturity} | High-quality corporate bond spot yield curve (Treasury HQM) | pension discounting context; maturities as params |
| credit.cds_agg{bucket} | CDS market aggregate spreads {IG, HY} | V6 pair vs macro.ig_oas/hy_oas — different instruments (CDS vs cash), tolerance wide, disagreement is INFORMATION (basis), so paired as basis concept: credit.cds_cash_basis |
| macro.funding_stress | Funding stress spread composite (e.g. FRA-OIS style) | joins macro.fin_conditions_nfci as regime feature |

## 3. Global rates (daily; generalizes the US-only v1 set)
| concept_id | definition | notes |
|---|---|---|
| rates.policy{country} | Central bank policy rate, step function, KT = decision announcement | macro.policy_rate becomes rates.policy{US} alias (additive: alias, not rename) |
| rates.reference{code} | Reference rates {SOFR, ESTR, SONIA, TONA, ...} | ref.riskfree_map (DICT-12) extends per-ccy to these |
| rates.ust_bill{tenor} / rates.ust_real{tenor} | Treasury bill & real (TIPS) yields | EODHD /ust/* as V6 second leg vs FRED primary; promotion per DICT-14 §6 |

## 4. Macro release events (the economic-events calendar as first-class events)
| concept_id | definition | notes |
|---|---|---|
| event.macro_release | {series_ref, country, release_time, actual, consensus, previous, revision_of?} | KT: consensus knowable pre-release; actual at release_time (or our arrival if later) [PIT] |
| macro.surprise{series} | (actual - consensus) / trailing std(actual - consensus, 24 releases) | standardized surprise; min 8 obs |
| macro.surprise_index{country} | Decayed sum of macro.surprise over trailing 91d (CESI-style construction, weights versioned) | regime feature for E1 |
[KEY] the calendar's consensus is a snapshot (no revision trail) — macro.surprise uses last-pre-release snapshot; DICT-15 §3 arrival rules apply.

## 5. Country fundamentals panel (annual, WB-style; per country)
country.gdp_growth · country.gdp_per_capita · country.inflation_yoy · country.debt_to_gdp · country.unemployment · country.current_account_gdp (net_trades proxy) · country.gross_capital_formation_gdp · country.market_cap_to_gdp · country.trade_openness (exports+imports %GDP)
Uniform treatment: unit declared per concept; period = calendar year; **no vintages at vendor** → kt = arrival, history kt_reconstructed: true, tier C; restatement-in-place at vendor detected by value-hash diff on refresh → new vintage on our side with supersession note (V9 preserved even over a non-PIT source — the abstraction's job).
Use: country risk context, ADR/exposure joins, sov.* companions. Never inputs to per-entity indicators without explicit lag policy (annual data joins with publication-realistic lag ≥ 6m).

## 6. Validation
Baseline [V1,V2,V8,V9] all; V4 on cds/rates (jump vs event join: rating actions, CB decisions explain jumps — unexplained jump → probe); V10 on surprise indices; sov.rating I-style interval integrity (one live rating per (country, agency)). Findings → data.quality, standard policy.
