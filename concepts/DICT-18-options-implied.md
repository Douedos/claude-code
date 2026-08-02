# DICT-18 · Options-implied concepts (tier: market; namespace opt)
Forward-looking market beliefs extracted from option chains. Contracts are raw material; concepts are surface summaries with declared construction rules — consumers never touch chains. Source v1.2: EODHD/Unicornbay marketplace (US, ~6k underlyings, EOD, full greeks/IV/OI per contract); sub-vendor provenance + own entitlement (DICT-14 §5), single-source cap (DICT-15 §4).

## 1. Chain hygiene (before any concept computes)
- Contract identity: OCC symbol = (underlying listing, expiry, strike, C/P); OCC symbols mutate on corporate actions — [KEY] adjusted contracts (non-standard multipliers/deliverables after splits/spinoffs, ".1" style suffixes) are EXCLUDED from surface construction (they price the old deliverable; including them is the classic IV-surface corruption around actions). DICT-11 event join drives the exclusion window.
- Underlying join via EntityResolver on the vendor's underlying key, never ticker string match.
- Quote sanity per contract: bid ≤ ask, IV present & in [0.01, 5], DTE > 0, arbitrage-gross violations (C < intrinsic) dropped with count logged.
- Min-liquidity for surface points: OI ≥ 10 or volume ≥ 5 (params versioned per concept).

## 2. Surface summary concepts (daily, per underlying entity; interpolation policy: linear in variance across the two bracketing expiries, delta-space for skew; NO extrapolation — insufficient wings → null+flag)
| concept_id | definition | notes |
|---|---|---|
| opt.iv_atm_30d | ATM (50Δ interp) implied vol at constant 30d maturity | worked YAML in EXAMPLES-3 |
| opt.iv_atm_91d | Same, 91d | |
| opt.iv_term_slope | iv_atm_91d - iv_atm_30d | inversion = event/stress pricing |
| opt.skew_25d | IV(25Δ put) - IV(25Δ call), 30d constant | crash-risk pricing |
| opt.rv_iv_spread | market.vol_252d - iv_atm_30d | variance-risk-premium form; both legs' windows declared |
| opt.iv_rank_252d | Percentile of iv_atm_30d in own 1y history | min 150 obs |
| opt.pcr_oi / opt.pcr_volume | Put/call ratio on OI / on volume, all listed expiries ≤ 91d | V2 (0, 20] |
| opt.oi_dollar | Σ OI × mid × multiplier, ≤ 91d | positioning size; standard contracts only |
| opt.earnings_iv_ratio | iv of expiry straddling next event.earnings_date / first expiry after | event-premium isolation; needs DICT-08 join; null when no confirmed date |
| opt.iv_dlt_1d | Δ iv_atm_30d day-over-day | V4-monitored; jump w/o news/action → data probe |

## 3. Validation & governance
- V-opt1 (parity): put-call parity residual at ATM within band per underlying-day; systematic residual → dividend-forecast or rate input bug in VENDOR's IV — reliance on vendor greeks flagged per DICT-15 (they're convenience; our own IV solver is the promotion path if V-opt1 fails persistently).
- V-opt2 (coherence): iv_atm_30d vs realized vol ratio within [0.3, 5] cross-sectionally winsorized; V10 distribution drift on all surface concepts.
- V-opt3 (action seam): surface concepts null inside ±3d of confirmed split/spinoff ex-date unless chain-adjusted contracts verified (the hygiene rule made a check).
- Coverage: opt.* universe is options-listed ∩ liquidity floor — universe.optionable published (DICT-12 pattern) so consumers don't silently mix optionable/non-optionable cross-sections.
- Greeks (delta/gamma/theta/vega/rho) are per-contract vendor inputs used in construction, not served concepts — dealer-positioning composites (GEX-style) deferred until a second source or own solver exists (tier would be C and unverifiable single-source).
