# DICT-WORKED-EXAMPLES · Eight full concept YAMLs
The template instantiated end to end, including his two named examples.

## 1. signal.earnings_yield (earnings to price)
```yaml
concept_id: signal.earnings_yield
tier: signal
definition: >
  Trailing earnings yield: TTM net income attributable to parent divided by current
  market capitalization. Yield form (not P/E) for cross-sectional behavior through zero.
  Excludes discontinued operations. Diluted per-share variant defined separately.
unit: ratio
period_basis: TTM over balance_pit market_cap
formula: raw.net_income[TTM] / raw.market_cap
inputs: [raw.net_income, raw.market_cap]
fallbacks:
  - compute: raw.eps_diluted[TTM] * raw.shares_diluted_wavg / raw.market_cap   # flag: eps_path
vendor_map: {}            # pure derived; vendors' own "PE" used only as V7 crosscheck (inverted)
validation:
  - V1; V2 {range: [-2.0, 1.0], winsor: [0.005, 0.995]}
  - V7 {vs: eodhd.Valuation.TrailingPE, transform: inverse, tol_rel: 0.05}
  - V10 {drift_z_max: 4}
quality_tier: A
since: "1.0"
```

## 2. derived.debt_to_invested_capital
```yaml
concept_id: derived.debt_to_invested_capital
tier: derived
definition: >
  Total debt as a share of invested capital, financing-side convention. Total debt =
  short-term + long-term debt incl. finance leases, excl. operating leases (variant
  _lease_adj includes them). Invested capital = total debt + preferred equity +
  minority interest + common equity - cash and equivalents. Negative invested capital -> null+flag.
unit: ratio
period_basis: balance_pit
formula: raw.total_debt / derived.invested_capital
inputs: [raw.total_debt, derived.invested_capital]
fallbacks:
  - compute: raw.total_debt / (raw.total_debt + raw.total_equity - raw.cash_and_equivalents)   # flag: equity_incl_nci
validation:
  - V1; V2 {range: [0, 1.5]}; V4 {jump_z: 4, net_of_actions: true}
  - V7 {vs: vendor debt_to_capital where offered, tol_rel: 0.03}
  - V11 {recompute_from_inputs: true}
quality_tier: A
since: "1.0"
```

## 3. raw.ebit
```yaml
concept_id: raw.ebit
tier: raw_item
statement: income_statement
definition: >
  Operating income as reported: revenue minus operating costs, before non-operating
  income/expense, interest and taxes. Impairments inside operating income stay (flagged
  via raw.special_items when separable). NOT "adjusted EBIT".
unit: currency
period_basis: FQ
currency_rule: reported
vendor_map:
  eodhd: {path: Financials.Income_Statement.quarterly.*.operatingIncome, kt: filing_date}
  xbrl:  {tags: [OperatingIncomeLoss], facts: duration}
fallbacks:
  - compute: raw.revenue - raw.cogs - raw.sga - raw.rnd - raw.other_opex   # flag: computed
validation: [V1, V2{sign: any}, V3{ties: pretax_income = ebit - interest_expense + interest_income + nonop, tol_rel: 0.02}, V4, V5, V7{vs: computed fallback, tol_rel: 0.02}, V9]
quality_tier: A
```

## 4. indicator.altman_z (solvency composite)
```yaml
concept_id: indicator.altman_z
tier: indicator
definition: Altman (1968) Z-score, public manufacturers; zones distress<1.81, grey, safe>2.99.
unit: zscore
period_basis: TTM flows over balance_pit stocks, market_cap current
formula: 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
inputs: [indicator.altman_x1..x5]      # each its own published concept
applicability: sector_map.manufacturing; else primary = indicator.altman_z2
validation: [V1, V2{range: [-10, 20]}, V11{recompute: bit_tol}, V10]
quality_tier: A
```

## 5. filing_item.going_concern
```yaml
concept_id: filing_item.going_concern
tier: filing_item
definition: >
  True when the auditor's opinion or the notes assert substantial doubt about the entity's
  ability to continue as a going concern for ~12 months. Rule-first ("substantial doubt"
  + "going concern" proximity in opinion/notes), LLM confirmation pass; passage mandatory.
unit: bool
period_basis: per filing (KT = acceptance)
extraction: {recipe: gc_rule_llm_v1, corpus: [10-K opinion, notes]}
evidence: passage_refs required (claims invalid without)
validation: [V1, V8{coverage vs 10-K count}, X2 evidence-fidelity heavy sampling (new-source stratum)]
quality_tier: B
```

## 6. market.amihud_illiq
```yaml
concept_id: market.amihud_illiq
tier: market
definition: Amihud (2002) illiquidity, mean(|daily return| / dollar volume) over 252d, ×1e6.
unit: ratio
period_basis: rolling(252)
formula: mean(abs(ret_d) / (raw.price_close * raw.volume)) * 1e6
inputs: [returns(adjusted), raw.price_close, raw.volume]
guards: {min_obs: 150, zero_volume_days: excluded, flag_if_excluded_gt: 0.2}
validation: [V1, V2{range: [0, 1e4]}, V10]
quality_tier: A
```

## 7. est.eps_revision_3m (schema-first, vendor later)
```yaml
concept_id: est.eps_revision_3m
tier: signal
definition: Change in mean NTM EPS estimate over 63 trading days, scaled by |mean|.
unit: ratio
period_basis: rolling(63)
formula: (est.eps_ntm_mean - lag(est.eps_ntm_mean, 63)) / abs(lag(est.eps_ntm_mean, 63))
inputs: [est.eps_ntm_mean]
vendor_map: {}      # deliberately empty; [PIT] binding rule documented: revision-timestamp data only
validation: [V1, V2, V9{revision_kt: mandatory}]
quality_tier: C     # promotes to B when a mapped vendor passes V6 for 60 days
```

## 8. macro.credit_spread_hy_oas
```yaml
concept_id: macro.hy_oas
tier: macro
definition: US high-yield option-adjusted spread, percentage points, vintage-correct.
unit: pct
period_basis: daily
vendor_map: {fred: {series: BAMLH0A0HYM2, vintages: alfred}}
validation: [V1, V2{range: [1, 25]}, V9]
quality_tier: A
```
