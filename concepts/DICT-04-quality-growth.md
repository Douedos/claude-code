# DICT-04 · Quality, profitability, growth (tier: signal/indicator)
Validation [V1,V2,V10] + V11 for composites.

## Profitability/quality signals
| concept_id | formula | notes |
|---|---|---|
| signal.gpoa | derived.gpoa | |
| signal.roe_stability | -std(roe, 5y FY) | higher = better; min 3 obs |
| signal.margin_trend | slope(ebit_margin, 12 FQ) | |
| signal.asset_growth | -Δ total_assets / lag(total_assets, 1y) | inverted (growth anomaly) |
| signal.noa_level | -derived.noa | inverted |
| signal.accruals | -derived.accruals_cf | inverted (low accruals = quality) |
| signal.sbc_drag | -derived.sbc_intensity | |
| signal.earnings_persistence | AR(1) coef of NI/TA over 8 FY | min 5 obs, tier C |

## Growth
| concept_id | formula |
|---|---|
| signal.revenue_growth_ttm | revenue(TTM)/revenue(TTM,-1y) - 1 |
| signal.revenue_growth_3y | CAGR(revenue FY, 3y) |
| signal.eps_growth_ttm | eps_diluted(TTM) vs -1y (sign-guarded: null when base<=0) |
| signal.fcf_growth_3y | CAGR guarded |
| signal.reinvestment_rate | capex_to_dep composite with rnd/revenue |

## Piotroski F-score (indicator, 0-9)
indicator.f_score = Σ of 9 binaries, each its own concept for auditability:
f1 roa>0 · f2 cfo>0 · f3 Δroa>0 · f4 accruals: cfo>net_income · f5 Δleverage_lt<0 (LTD/avg assets) · f6 Δcurrent_ratio>0 · f7 no share_issuance (Δshares_outstanding<=ε) · f8 Δgross_margin>0 · f9 Δasset_turnover>0 (revenue/avg assets).
Validation V11: stored score equals recompute from stored components; components published individually (indicator.f1..f9).
