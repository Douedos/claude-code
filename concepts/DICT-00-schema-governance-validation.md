# DICT-00 · Concept Dictionary: schema, governance, validation taxonomy
The abstract overlay of quantitative quantities. Vendor-agnostic concept definitions that the DAL serves, adapters map into, and validators police. Lives in repo `concepts/` next to `vocab/`, versioned, additive-only, snapshotted to the store like the vocabulary.

## 1. Concept schema (one YAML per concept)
```yaml
concept_id: derived.debt_to_invested_capital      # namespace.tier convention
tier: raw_item | derived | signal | indicator | filing_item | market | macro | event
statement: income_statement|balance_sheet|cash_flow|per_share|market|none
definition: >
  Precise economic definition INCLUDING every treatment choice (minority interest,
  preferred, operating leases, discontinued ops). Ambiguity here becomes silent
  cross-vendor disagreement downstream.
unit: currency | ratio | pct | days | count | zscore | per_share
period_basis: FQ | FY | TTM | balance_pit | rolling(w) | daily
currency_rule: reported | converted(base_ccy)      # conversion at period-end vs average declared
fiscal_alignment: filing_acceptance                # KT rule; concepts inherit B7 corpus rules
formula: null | expr over concept_ids              # derived/signal/indicator tiers
inputs: [concept_ids]                              # dependency graph (validated acyclic)
fallbacks:                                         # ordered strategies when primary is missing
  - compute: <expr>                                # e.g. EBIT = revenue - cogs - sga - dep when not reported
  - proxy: <concept_id> with flag
vendor_map:
  eodhd: {field: ..., transform: ...}
  xbrl:  {tags: [ordered us-gaap fallback chain], dims: ...}
  <future_vendor>: {...}
validation: [V-ids]                                # from §3, with per-concept params
quality_tier: A|B|C                                # A = identity-checked; B = range+quorum; C = best-effort
since: "1.0"
```

## 2. Runtime classes (extends CLASS-03)
```python
class ConceptRegistry:      load / get(concept_id) / dependents / assert_acyclic
class ConceptDef(BaseModel) # the schema above
class VendorMapper:         def resolve(self, concept, vendor) -> FieldBinding   # [KEY] per-vendor per-concept
class FallbackResolver:     def value(self, concept, entity, period, dal) -> (value, provenance_flag)
    # [KEY] fallback order is part of the DEFINITION: computed-EBIT vs reported-EBIT differ; the
    # flag (reported|computed|proxy) travels with the value into panels and claims. Failure mode:
    # mixed provenance in one cross-section without anyone knowing. Test: mixed fixture, flags golden.
class UnitNormalizer:       def normalize(self, raw, binding) -> value           # [KEY] thousands/millions detection (V5)
class CurrencyNormalizer:   def convert(self, value, ccy, rule, fx_asof) -> value  # [PIT] fx at vintage
class FiscalAligner:        def align(self, rows, basis) -> Panel                # FQ->TTM builds, calendarization
    # [KEY][PIT] TTM = sum of last 4 FQ AVAILABLE AT asof (mixed fiscal year-ends across the
    # universe); calendarization documented (no interpolation by default). Off-by-one-quarter here
    # biases every ratio. Test: fiscal-year-end-diversity fixture golden.
class ConceptValidator(ABC): def check(self, panel|row, ctx) -> list[Finding]
```

## 3. Validation taxonomy (V-ids referenced by every concept)
| V | Name | Method | Typical scope |
|---|---|---|---|
| V1 | Schema/unit | type, unit, currency present and legal | all |
| V2 | Sign/range | per-concept bounds (assets>0, margins∈[-5,5], ratios sane) | all |
| V3 | Accounting identities | Assets=Liab+Equity (tol); ΔCash=CFO+CFI+CFF+FX; NI ties IS->CF start; equity roll-forward | raw_items, tier A |
| V4 | Continuity | period-over-period jump z-score net of known corporate actions (B5 join); flags step changes | raw, derived |
| V5 | Scale detection | cross-field sanity (revenue vs market cap, per-share × shares vs total) to catch ×1000 errors | raw |
| V6 | Cross-vendor quorum | X2 hook: value vs k independent sources within tolerance | tier A/B, sampled |
| V7 | Derived cross-check | our formula output vs vendor's precomputed ratio where offered (diff -> mapping bug alert) | derived, signal |
| V8 | Coverage/staleness | universe coverage %, last-report age vs expectation | all, per-vendor |
| V9 | Vintage monotonicity | restatements only via new vintages; KT ordering; no value changes without vintage | all [PIT] |
| V10 | Distributional | cross-sectional percentile drift vs trailing window (mapping breaks show as distribution jumps) | signals |
| V11 | Identity of composites | indicator recomputed from stored inputs equals stored indicator (bit-tol) | indicators |
Findings -> claims `data.quality{concept, entity?, V, severity, detail}` (meta); severity≥error blocks the concept's panel for the day (served with gap, never with the bad value) and files an X2/sign-off ticket per policy.

## 4. Files in this set
01 raw statement items · 02 derived fundamentals · 03 valuation signals · 04 quality/profitability/growth · 05 solvency & credit indicators · 06 market/price-derived · 07 filing & text items (SEC/XBRL) · 08 estimates, events, macro · 09 vendor mapping layer · WORKED-EXAMPLES (8 full YAMLs)
v1.1 additive — the abstraction layer: 10 entity & identity (I1–I6) · 11 corporate actions & AdjustmentChain (A1–A5) · 12 reference data, classification, universes · 13 DAL service contract (S1–S5) · 14 adapter SPI, ingestion, vendor ops · WORKED-EXAMPLES-2 (6 layer artifacts). New tier value `reference` and identifier unit `id_string` join the schema; concept schema itself unchanged.
