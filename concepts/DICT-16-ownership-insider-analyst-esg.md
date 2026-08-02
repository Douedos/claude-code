# DICT-16 · Ownership, insiders, analyst coverage, ESG (tiers: raw_item/signal; new namespaces own/insider/analyst/esg)
Domains EODHD can feed today (DICT-15) that v1 had no concepts for. Schema-first as always: concepts defined vendor-agnostically; EODHD is merely the first map entry. Single-source caps per DICT-15 §4. Validation baseline [V1,V2,V8,V9] unless noted.

## Ownership structure (source: 13F-derived holder data; balance_pit, quarterly refresh)
| concept_id | definition | notes |
|---|---|---|
| own.inst_pct | % shares outstanding held by institutions | vendor PercentInstitutions; V2 [0, 1.2] (>1 = stale shares denom, flag) |
| own.inst_holder_count | # reporting institutions | coverage proxy |
| own.top10_share | Σ top-10 holders' shares / shares_outstanding | concentration; computed from holder list |
| own.fund_pct | % held by mutual funds | |
| own.insider_pct | % held by insiders | cross-ref filing_item.insider_ownership (proxy-extracted) — V6 pair when both present |
| own.float_share | free_float / shares_outstanding | joins raw.free_float |
[KEY] 13F data is quarterly with ~45d lag; KT = our arrival of the refreshed snapshot, NEVER the quarter-end (classic 13F look-ahead). period = quarter-end, KT ≥ quarter-end + lag.

## Insider transactions (source: Form 4 stream; event-granular)
| concept_id | definition | notes |
|---|---|---|
| insider.txn | Event: {role, code(P/S/A/D/G/F/M...), shares, price, value, event_date, kt=form4_filing_date} | raw event stream; open-market P/S are the signal-bearing codes — plan sales (10b5-1, code flag) separated |
| insider.net_buy_ratio_6m | (buy_value - sell_value) / (buy_value + sell_value), open-market only, 126d | worked YAML in EXAMPLES-3; null when denom < min_value |
| insider.buyer_breadth_6m | # distinct open-market buyers, 126d | cluster buying (breadth > 2) is the documented alpha carrier, not volume |
| insider.officer_buy_flag | Any CEO/CFO open-market buy trailing 63d | role from reporter title |
| insider.sell_pressure | sell_value(126d) / (own.insider_pct × market_cap) | scaled disposals; guards on tiny insider stakes |
[PIT] event_date (transactionDate) is when the trade happened; the market learns at Form-4 filing — signals window on KT, event_date is payload. Backtest joining on event_date is look-ahead by up to 2 business days.

## Analyst coverage (distinct from est.* — opinions, not forecast values; snapshot-KT per DICT-15 §3)
| concept_id | definition | notes |
|---|---|---|
| analyst.rating_mean | Mean recommendation, 1 (strong buy) – 5 (strong sell), declared scale | vendor scales normalized in map, scale_id in provenance |
| analyst.rating_count | # contributing analysts | coverage; also a neglect signal input |
| analyst.rating_delta_3m | rating_mean vs 63d prior snapshot | tier C until revision-KT source exists (snapshot diffs are lag-blurred — flag snapshot_diff) |
| analyst.target_upside | target_price_mean / price_close - 1 | V2 [-0.9, 3]; stale-target guard: targets older than 6m excluded where age known |
| analyst.coverage_gap | -log(1 + rating_count) | neglect factor form |

## ESG (vendor-opinion tier; methodology is part of identity)
| concept_id | definition | notes |
|---|---|---|
| esg.score_env / score_social / score_gov / score_total | Provider scores under a NAMED methodology: concept serves (value, methodology_id, version) | [KEY] ESG scores from different providers correlate ~0.5 — they are different quantities. NEVER cross-vendor quorum (V6 exempt); switching provider = new methodology_id, both series retained; composites cite methodology_id in lineage |
| esg.controversy_flag | Provider controversy/severity flag | tier C |
| esg.score_delta_1y | Change under SAME methodology version only | cross-version delta is undefined (null+flag) |

## Validation additions
V-own1: Σ holder categories ≤ 105% shares outstanding (double-count guard). V-ins1: insider.txn price within ±20% of session range on event_date (bad-parse catch). V-esg1: score within provider's declared scale, version registered. All findings → data.quality claims, standard policy.
