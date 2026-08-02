# DICT-01 · Raw statement items (tier: raw_item)
Conventions: currency unit, period_basis FQ/FY (balance items balance_pit), validation baseline [V1,V2,V4,V5,V8,V9]; tier-A items add V3. Definitions state the treatment choices; XBRL chains in DICT-09.

## Income statement (period_basis FQ, flow)
| concept_id | definition (treatment choices in parentheses) |
|---|---|
| raw.revenue | Total revenue from contracts, net of returns/allowances (excludes other income; excise-tax-net where reported) |
| raw.cogs | Cost of revenue incl. D&A when not separable (flag: da_in_cogs) |
| raw.gross_profit | revenue - cogs; fallback compute |
| raw.sga | Selling, general & administrative (R&D excluded when reported separately) |
| raw.rnd | Research & development expense |
| raw.ebit | Operating income (excludes non-operating items, impairments flagged separately); fallback: revenue - cogs - sga - rnd - other_opex |
| raw.ebitda | ebit + dep_amort; fallback compute (never vendor "adjusted EBITDA") |
| raw.dep_amort | D&A (IS or CF source; source flagged — CF preferred for completeness) |
| raw.interest_expense | Gross interest expense (not netted vs interest income) |
| raw.interest_income | |
| raw.pretax_income | |
| raw.tax_expense | Current + deferred |
| raw.net_income | NI attributable to parent (minority interest excluded; flag if only consolidated available) |
| raw.net_income_consolidated | Incl. NCI |
| raw.eps_basic / raw.eps_diluted | As reported (per_share) |
| raw.special_items | Impairments, restructuring, one-offs (sign: expense negative) |
| raw.discontinued_ops | Income from discontinued operations |

## Balance sheet (balance_pit)
| concept_id | definition |
|---|---|
| raw.total_assets | |
| raw.current_assets | |
| raw.cash_and_equivalents | Cash + equivalents (excl. restricted; restricted flagged separately) |
| raw.short_term_investments | |
| raw.receivables | Trade receivables, net |
| raw.inventory | |
| raw.net_ppe | Property, plant & equipment net of accumulated depreciation |
| raw.gross_ppe / raw.accum_depreciation | |
| raw.goodwill | |
| raw.intangibles | Excl. goodwill |
| raw.total_liabilities | |
| raw.current_liabilities | |
| raw.accounts_payable | |
| raw.short_term_debt | Debt due <1y incl. current portion of LTD |
| raw.long_term_debt | Excl. current portion; incl. finance-lease liabilities (operating leases flagged: post-ASC842 on-BS) |
| raw.total_debt | short_term_debt + long_term_debt; fallback compute |
| raw.operating_lease_liab | Separately when reported |
| raw.deferred_revenue | |
| raw.deferred_tax_liab / raw.deferred_tax_assets | |
| raw.pension_liability | Net funded status where disclosed |
| raw.preferred_equity | Preferred stock at carrying value |
| raw.minority_interest | Noncontrolling interests |
| raw.common_equity | Total stockholders' equity attributable to parent (excl. NCI, excl. preferred); fallback: total_equity - preferred - minority |
| raw.total_equity | Incl. NCI |
| raw.retained_earnings | |
| raw.treasury_stock | |
| raw.working_capital | current_assets - current_liabilities; fallback compute |

## Cash flow (flow)
| concept_id | definition |
|---|---|
| raw.cfo | Net cash from operating activities |
| raw.cfi | Investing |
| raw.cff | Financing |
| raw.capex | Purchases of PP&E (gross; disposals separate: raw.asset_sales) |
| raw.acquisitions | Cash paid for acquisitions net of cash acquired |
| raw.dividends_paid | Common + preferred (split when disclosed) |
| raw.share_repurchases | Gross buybacks |
| raw.share_issuance | |
| raw.debt_issued / raw.debt_repaid | |
| raw.fx_effect_cash | |
| raw.sbc | Stock-based compensation (CF add-back) |
| raw.ffo | Funds from operations proxy: net_income + dep_amort + deferred taxes (used by Ohlson; REIT definition separate: raw.ffo_reit) |

## Shares and market (daily unless noted)
| concept_id | definition |
|---|---|
| raw.shares_basic_wavg / raw.shares_diluted_wavg | Weighted average (FQ) |
| raw.shares_outstanding | Point-in-time from cover page / latest (balance_pit) |
| raw.free_float | When available (tier C) |
| raw.price_close | Official close, listing currency, unadjusted (adjustments via AdjustmentChain only) |
| raw.volume | Shares traded |
| raw.market_cap | price_close × shares_outstanding (aligned KT); fallback vendor field with V7 cross-check |
| raw.enterprise_value | market_cap + total_debt + preferred_equity + minority_interest - cash_and_equivalents (declared: excl. operating leases by default, variant ev_incl_leases) |
| raw.dividend_per_share | Declared per share (KT = declaration) |
| raw.borrow_fee / raw.short_interest | Tier C where sourced |
