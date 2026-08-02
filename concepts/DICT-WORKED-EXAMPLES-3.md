# DICT-WORKED-EXAMPLES-3 · EODHD-expansion examples (DICT-15..19 instantiated)
Four artifacts showing the new domains under full template discipline — including the two places the abstraction visibly refuses to overreach (estimates KT, ESG quorum).

## 1. insider.net_buy_ratio_6m (the KT-vs-event-date trap, solved in schema)
```yaml
concept_id: insider.net_buy_ratio_6m
tier: signal
definition: >
  Net open-market insider buying: (buy value - sell value) / (buy + sell value) over
  trailing 126 trading days. Open-market purchases/sales only (Form 4 codes P, S);
  option exercises, gifts, 10b5-1 plan sales excluded. Windowing on KNOWLEDGE time
  (Form-4 filing date), never transaction date.
unit: ratio
period_basis: rolling(126)
formula: (sum(insider.txn.value | code=P) - sum(value | code=S)) / (sum(P)+sum(S))
inputs: [insider.txn]
guards: {min_total_value: 50000, else: null+flag}
vendor_map:
  eodhd: {endpoint: insider-transactions, kt: form4_filing_date, event: transactionDate,
          quirks: ["10b5-1 flag inferred from footnote text where present; inference flagged"]}
validation: [V1, V2{range: [-1, 1]}, V9{kt: form4_filing_date mandatory}]
quality_tier: B          # single-source cap (DICT-15 §4); EDGAR Form-4 adapter is the quorum partner
since: "1.2"
```

## 2. opt.iv_atm_30d (surface concept with construction as part of identity)
```yaml
concept_id: opt.iv_atm_30d
tier: market
definition: >
  At-the-money implied volatility at constant 30-calendar-day maturity. ATM = 50-delta
  interpolated; maturity interpolation linear in total variance between bracketing listed
  expiries; standard contracts only (adjusted contracts excluded per DICT-18 §1); no
  extrapolation — missing bracket -> null+flag.
unit: ratio          # annualized vol
period_basis: daily
inputs: [options chain (eodhd/unicornbay), event join: action.* exclusion windows]
construction: {atm: delta_50_interp, maturity: variance_linear, min_oi: 10, expiry_bracket: required}
vendor_map:
  eodhd_unicornbay: {endpoint: mp/unicornbay/options/eod, kt: arrival_daily, entitlement: ent.unicornbay_2026}
validation: [V1, V2{range: [0.03, 4.0]}, V-opt1{parity_band}, V-opt3{action_seam_null}, V10]
quality_tier: B      # single-source; own-solver shadow is the promotion path
since: "1.2"
```

## 3. est.surprise_last wired — and est.eps_revision_3m NOT wired (the refusal, explicit)
```yaml
concept_id: est.surprise_last
vendor_map:
  eodhd: {endpoint: fundamentals.Earnings.History, fields: [epsActual, epsEstimate, surprisePercent],
          kt: arrival_snapshot, quirks: ["estimate is last-pre-print snapshot; adequate for surprise"]}
quality_tier: C -> B after 60d V6 vs a second calendar source
# ---
concept_id: est.eps_revision_3m
vendor_map: {}       # STAYS EMPTY. EODHD Earnings.Trend is a current snapshot without revision
                     # timestamps; serving revision concepts from snapshot diffs manufactures KT.
                     # DICT-15 §3 row "earnings estimates" is the binding refusal; the concept keeps
                     # waiting for revision-level data. This empty map is load-bearing governance.
```

## 4. esg.score_env (methodology-as-identity — the no-quorum exception in action)
```yaml
concept_id: esg.score_env
tier: raw_item
definition: >
  Environmental pillar score under a NAMED provider methodology. The served value is
  (score, methodology_id, methodology_version). Scores under different methodologies are
  different quantities: no V6 cross-vendor quorum, no averaging, no cross-methodology deltas.
unit: score{provider_scale}
period_basis: snapshot, kt: arrival
vendor_map:
  eodhd_investverte: {endpoint: mp/investverte/esg, methodology_id: investverte_v?, scale: [0,100]}
  eodhd_native:      {endpoint: fundamentals.ESGScores, methodology_id: eodhd_esg, scale: declared}
  # both retained as SEPARATE series if both ingested; class.crosswalk-style mapping never applied to scores
validation: [V1, V-esg1{scale+version registered}, V8, V9]
quality_tier: C
since: "1.2"
```
