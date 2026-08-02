# DICT-15 · EODHD full-surface capability audit (extends DICT-09 EODHD section)
Audit of the entire EODHD API surface (~90 endpoints, OpenAPI spec) against the dictionary: what each endpoint is FOR in our architecture. Every endpoint gets a disposition — nothing is "we'll see". Dispositions: **primary** (serves concepts), **secondary** (V6/V7 check material), **candidate-feed** (DICT-11 action candidates), **identity-feed** (DICT-10 ledger input), **ops** (DICT-14 machinery), **not-adopted** (with reason, revisitable).

## 1. Endpoint disposition table
| endpoint(s) | disposition | binds to |
|---|---|---|
| /eod/{t}, /eod-bulk-last-day/{ex} | **primary** | raw.price_close, raw.volume (unadjusted; adjusted_close ignored except A1 check) |
| /fundamentals/{t} → Financials.{IS,BS,CF} | **primary** | DICT-01 raw items (map in DICT-09); KT = filing_date field |
| /fundamentals → General | **identity-feed** | ident.isin/cusip/cik/lei? no-lei; name, country, ipo date; Sector/Industry → class.membership{eodhd_scheme} |
| /fundamentals → outstandingShares, SharesStats | **primary** | raw.shares_outstanding; raw.free_float (SharesFloat); raw.short_interest (SharesShort, tier C) |
| /fundamentals → Highlights, Valuation, Technicals | **secondary** | V7 material only (vendor-precomputed PE/EV/beta/margins vs our derived.*/signal.*) — [KEY] never served |
| /fundamentals → SplitsDividends | **candidate-feed** | action.split / action.dividend_cash candidates (source 1 of quorum) |
| /fundamentals → Earnings (History/Trend/Annual) | **primary, tier C** | est.surprise_last, event.earnings_date; [PIT] snapshot-level, no revision timestamps — see §3 |
| /fundamentals → AnalystRatings | **primary, tier C** | analyst.* (DICT-16); US-only, snapshot — kt_policy arrival |
| /fundamentals → Holders, InsiderTransactions; /insider-transactions | **primary** | own.* / insider.* (DICT-16); insider KT = Form-4 filing link where present |
| /fundamentals → ESGScores; /mp/investverte/* | **primary, tier C** | esg.* (DICT-16); methodology-versioned vendor opinion |
| /fundamentals (ETF_Data, MutualFund_Data, Index General) | **not-adopted v1.2** | fund/ETF holdings & exposures — adopt with a fund-tier dictionary when universe needs it |
| /div/{t}, /splits/{t}, /calendar/splits, /calendar/dividends | **candidate-feed** | action.dividend_cash, action.split (announcement vs ex dates both captured) |
| /calendar/earnings, /calendar/ipos | **primary** | event.earnings_date_estimated/confirmed, action.ipo candidates |
| /calendar/trends | **not-adopted** | vendor-curated "trending" — editorial, no stable definition |
| /symbol-change-history | **identity-feed** | ident.ticker interval closes; action.ticker_change events |
| /id-mapping, /search/{q} | **identity-feed / ops** | EntityResolver cascade steps 2–6 support; search = resolution QA tooling only |
| /exchanges-list, /v2/exchange-details, tradinghours mp | **primary** | ref.trading_calendar{mic}, ref.session{mic} (DICT-12) — second source vs curated calendar |
| /historical-market-cap/{t} | **secondary** | V7 vs raw.market_cap = price × shares |
| /macro-indicator/{country} | **primary, tier C** | country.* panel (DICT-19) — annual WB-style; no vintages → kt_reconstructed |
| /economic-events | **primary** | event.macro_release{actual, consensus, previous} → macro surprise concepts (DICT-19) |
| /ust/* (bill, yield, long-term, real) | **secondary** | vs FRED-backed macro.ust_* (V6); promotable per DICT-14 §6 |
| /rates/policy-rates, /rates/reference-rates, /spreads/funding-stress | **primary** | rates.policy{country}, rates.reference{code:SOFR,ESTR,...}, macro.funding_stress (DICT-19) |
| /credit-risk/sovereign/* (cds, ratings, default/risk premium) | **primary** | sov.* (DICT-19) |
| /credit-risk/corporate/{cmdi, hqm-yields}, /credit-risk/cds-market/aggregates | **primary** | credit.cmdi, credit.hqm_yield{mat}, credit.cds_agg (DICT-19) |
| /cboe/indices, /cboe/index | **secondary** | vs macro.vix/move family; primary where FRED lacks the index |
| /commodities/historical/{code} | **secondary** | vs macro.wti/gold sources; primary for codes FRED lacks |
| /real-estate/* | **not-adopted v1.2** | country HPI context; adopt as country.hpi if macro regime work wants it |
| /mp/unicornbay/options/* | **primary** | opt.* (DICT-18); sub-vendor provenance eodhd/unicornbay, own entitlement |
| /news, /sentiments, /news-word-weights | **primary, tier C** | news.* (DICT-17); vendor polarity is bootstrap/check, D4 recipes are the real scorer |
| /screener, /technical/{t} | **not-adopted** | derived data we compute from concepts — accepting vendor versions would bypass V11/lineage |
| /mp/praams/*, /mp/unicornbay/spglobal/* | **not-adopted** | third-party analytics/scores; conflicts with explainability rule (no black-box inputs to claims) |
| /sanctions/* | **not-adopted v1.2** | compliance domain; revisit as compliance.sanctioned_flag if universe goes global/EM |
| /intraday, /real-time, /ticks, /us-quote-delayed, websockets | **not-adopted v1.2** | solution is EOD-frequency; descriptor lists the capability (latency tier) for future intraday work |
| /logo* | **ops** | display only |
| /user, /internal-user, /bulk-* | **ops** | quota monitoring (meta.vendor_cost); bulk = backfill fetch strategy (DICT-14 §3) |

## 2. Coverage scoreboard (EODHD alone vs dictionary v1.2)
| dictionary domain | EODHD as primary | notes |
|---|---|---|
| DICT-01 raw items (~70) | ~65 servable | gaps: operating_lease_liab granularity, ffo_reit, borrow_fee; KT honest via filing_date |
| DICT-02..05 derived/signals/indicators | 100% computed | EODHD contributes only V7 cross-checks by design |
| DICT-06 market | all inputs | prices/volume/splits/divs primary; single action source → quorum partner required (EDGAR/8-K feed) |
| DICT-07 filing items | ~0 | needs EDGAR adapter; EODHD has no filing text |
| DICT-08 estimates | partial, tier C cap | snapshot consensus only — est.revision_* concepts CANNOT be honestly served (§3); calendar + surprise yes |
| DICT-08 macro | secondary + gaps filled | FRED stays primary for vintaged US series; EODHD primary for policy/reference rates, sovereign credit, economic-events calendar |
| DICT-10 identity | strong feed | General + id-mapping + symbol-change + exchange lists — 4 of 7 cascade steps supported |
| DICT-11 actions | 1 of 2 quorum sources | plus announcement KT from calendars |
| DICT-16 ownership/insider/analyst/ESG | primary (sole source v1.2) | tier B/C caps until second source exists |
| DICT-17 news/sentiment | primary (sole source v1.2) | tier C; D4 promotes |
| DICT-18 options | primary (sole source v1.2) | US, ~6k underlyings, EOD granularity |
| DICT-19 credit/rates/country | primary for most | single-source caps apply |

## 3. KT honesty table ([PIT] — what the adapter must declare per DICT-14 kt_policy)
| data | KT available? | policy |
|---|---|---|
| statements | filing_date field (mostly) | kt = filing_date; missing → filings-adapter join, else arrival |
| prices/volume | session close | kt = arrival at post-close fetch |
| splits/dividends | announcement in calendars; ex-dates in history | both KTs stored (DICT-11) |
| earnings estimates/ratings/holders/ESG | **none** — snapshots, UpdatedAt only | kt = arrival_time; forbids serving revision-based concepts; history backfill flagged kt_reconstructed — [KEY] this single row is why est.* stays schema-first until a revision-level vendor is wired (DICT-08 trap, enforced) |
| insider transactions | Form-4 filing date/link | kt = filing date (transactionDate is the EVENT date, never KT) |
| macro-indicator country panel | none (restated in place) | kt = arrival; history kt_reconstructed |
| economic-events | event datetime + our poll | kt = arrival; consensus values before event are estimates (fine), actuals after |
| news | published timestamp + arrival | kt = max(published, arrival) — vendor backfills articles; arrival wins on conflict |
| options EOD | trade date, daily file | kt = arrival at daily fetch |

## 4. Single-source rule (governance)
Every domain where EODHD is the sole wired source carries a quality-tier cap (≤B) and a standing DICT-14 §6 exit-test failure — by construction, no vendor is removable while sole-source. The scoreboard above is therefore also the second-vendor shopping list, priority: (1) actions quorum partner, (2) revision-level estimates, (3) options cross-check.
