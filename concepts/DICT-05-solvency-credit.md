# DICT-05 · Solvency and credit indicators (tier: indicator)
His "indicator of solvability" family. Validation [V1,V2,V11] + V6 sampling; every composite publishes its inputs as concepts (auditability) and its recompute identity.

## Liquidity & coverage
| concept_id | formula | notes |
|---|---|---|
| indicator.current_ratio | current_assets / current_liabilities | |
| indicator.quick_ratio | (current_assets - inventory) / current_liabilities | |
| indicator.cash_ratio | (cash + short_term_investments) / current_liabilities | |
| indicator.interest_coverage | ebit(TTM) / interest_expense(TTM) | interest≈0 -> capped +flag, not inf |
| indicator.cash_coverage | (ebitda - capex)(TTM) / interest_expense(TTM) | |
| indicator.fixed_charge_coverage | (ebit + lease_expense) / (interest + lease_expense) | lease data tier B |
| indicator.debt_service_years | net_debt / fcf(TTM) | fcf<=0 -> null+flag |
| indicator.cash_burn_runway | cash / -fcf(TTM) when fcf<0 else null | months; distress screen |

## Altman Z (manufacturing, public)
indicator.altman_z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5
X1 working_capital/total_assets · X2 retained_earnings/total_assets · X3 ebit(TTM)/total_assets · X4 market_cap/total_liabilities · X5 revenue(TTM)/total_assets.
Zones: distress <1.81, grey 1.81–2.99, safe >2.99 (published as indicator.altman_zone).
Variant indicator.altman_z2 (non-manufacturers, Z''): 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4' with X4' = common_equity/total_liabilities (book, no X5). Applicability rule: sector map decides which variant is primary; both computed.

## Ohlson O-score
indicator.ohlson_o = -1.32 - 0.407·log(total_assets/price_deflator) + 6.03·(TL/TA) - 1.43·(WC/TA) + 0.0757·(CL/CA) - 1.72·NEG_EQ - 2.37·(NI/TA) - 1.83·(FFO/TL) + 0.285·TWO_LOSS - 0.521·ΔNI_norm
NEG_EQ = 1 if total_liabilities>total_assets; TWO_LOSS = 1 if NI<0 last two FY; ΔNI_norm = (NI_t - NI_{t-1})/(|NI_t|+|NI_{t-1}|); price_deflator = GNP/GDP deflator series (macro concept, vintage). Probability form indicator.ohlson_p = logistic(o). All 9 terms published as concepts.

## Merton distance-to-default (structural)
indicator.merton_dd: solve V_A, σ_A from equity value/vol (market_cap, signal.vol_252d) with face value F = short_term_debt + 0.5·long_term_debt, horizon 1y, riskfree from macro; DD = (ln(V_A/F) + (μ - σ_A²/2)) / σ_A; indicator.merton_pd = N(-DD).
[NUM] iterative solver: convergence guard + bounds; failures -> null+flag (tier B). μ convention: riskfree (KMV-style practical default).

## Other credit posture
| concept_id | formula/def |
|---|---|
| indicator.solvency_composite | rank-avg{altman primary, -ohlson_p, merton_dd, interest_coverage} (C2 recipe) |
| indicator.going_concern_flag | filing_item.going_concern (DICT-07) |
| indicator.covenant_pressure | net_debt_to_ebitda vs sector p90 (relative screen, tier C) |
| indicator.dividend_sustainability | dividends_paid / fcf (TTM), >1 flagged |
