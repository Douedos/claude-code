# DICT-02 · Derived fundamentals (tier: derived)
Validation baseline [V1,V2,V4,V7,V10] + V11 where composite. period_basis TTM unless noted. Every formula over concept_ids; denominators guarded (see §guards).

## Margins & returns
| concept_id | formula | notes |
|---|---|---|
| derived.gross_margin | gross_profit / revenue | |
| derived.ebit_margin | ebit / revenue | |
| derived.ebitda_margin | ebitda / revenue | |
| derived.net_margin | net_income / revenue | |
| derived.roe | net_income(TTM) / avg(common_equity) | avg = (beg+end)/2; negative-equity -> null + flag (never a "meaningful" huge ROE) |
| derived.roa | net_income(TTM) / avg(total_assets) | |
| derived.nopat | ebit × (1 - effective_tax_rate) | eff rate = tax_expense/pretax_income clamped [0, .5]; clamp flagged |
| derived.invested_capital | total_debt + preferred_equity + minority_interest + common_equity - cash_and_equivalents | financing-side convention (operating-side variant: invested_capital_op = working_capital + net_ppe + intangibles + goodwill) — ONE default, both defined |
| derived.roic | nopat(TTM) / avg(invested_capital) | |
| derived.gpoa | gross_profit(TTM) / total_assets | Novy-Marx quality |
| derived.effective_tax_rate | tax_expense / pretax_income | clamped, flagged |

## Capital structure & obligations
| concept_id | formula | notes |
|---|---|---|
| derived.debt_to_equity | total_debt / common_equity | negative equity -> null+flag |
| derived.debt_to_invested_capital | total_debt / invested_capital | HIS EXAMPLE — worked YAML in WORKED-EXAMPLES |
| derived.net_debt | total_debt - cash_and_equivalents - short_term_investments | |
| derived.net_debt_to_ebitda | net_debt / ebitda(TTM) | ebitda<=0 -> null+flag |
| derived.leverage_assets | total_liabilities / total_assets | Ohlson TL/TA |
| derived.debt_maturity_share_st | short_term_debt / total_debt | refinancing pressure |
| derived.lease_adjusted_leverage | (total_debt + operating_lease_liab) / (invested_capital + operating_lease_liab) | |

## Working capital & cash conversion
| concept_id | formula |
|---|---|
| derived.dso | avg(receivables) / revenue(TTM) × 365 |
| derived.dio | avg(inventory) / cogs(TTM) × 365 |
| derived.dpo | avg(accounts_payable) / cogs(TTM) × 365 |
| derived.ccc | dso + dio - dpo |
| derived.nwc_to_sales | working_capital / revenue(TTM) |
| derived.fcf | cfo - capex |
| derived.fcf_conversion | fcf / net_income (guard NI<=0) |
| derived.capex_intensity | capex / revenue |
| derived.capex_to_dep | capex / dep_amort (reinvestment rate) |

## Accruals & earnings quality inputs
| concept_id | formula | notes |
|---|---|---|
| derived.accruals_cf | (net_income - cfo) / avg(total_assets) | Sloan, cash-flow method (default) |
| derived.accruals_bs | (ΔCA - Δcash) - (ΔCL - ΔSTD) - dep_amort, / avg(total_assets) | balance-sheet method, cross-checked V11-style vs accruals_cf (divergence flagged, acquisitions are the usual cause) |
| derived.noa | (total_assets - cash) - (total_liabilities - total_debt), / total_assets | net operating assets (Hirshleifer) |
| derived.sbc_intensity | sbc / revenue | |

## §guards (all derived)
Denominator rules: |denom| < ε -> null + flag div_guard; sign-sensitive ratios (ROE, D/E) null on economically-meaningless sign, never "large number". Winsor bounds per concept in V10 params. Averages use available endpoints (single endpoint flagged avg_partial).
