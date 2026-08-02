# DICT-12 · Reference data, classification, universes (tier: reference)
The static-looking data that is never static. Calendars, currencies, classification and universe membership are all interval-valid and vintage-stored like everything else [PIT]. These concepts are what DICT-05's `sector_map`, DICT-06's `benchmark map per exchange`, and every backtest universe silently depend on.

## 1. Calendars & sessions
| concept_id | definition |
|---|---|
| ref.trading_calendar{mic} | Trading days per exchange, incl. ad-hoc closures (versioned: a hurricane closure is a calendar VINTAGE, not an edit) |
| ref.session{mic} | Open/close times, half-days, timezone (tz database id, not offset) |
| ref.halt | Per-listing trading halts with reason where sourced (tier B) — feeds zero-volume-day exclusion in DICT-06 guards |
| ref.settlement_cycle{mic} | T+1/T+2 by interval (changed 2024-05 in US — interval data, not a constant) |
[KEY] "Daily" concepts are defined over the LISTING's calendar; cross-exchange panels align via calendar union with explicit forward-fill limits (max_ffill per concept, default 0 — gap, not stale value).

## 2. Currency & FX
| concept_id | definition |
|---|---|
| ref.currency{listing} | Trading currency, interval-valid (redenominations happen) |
| fx.rate{ccy_pair} | Daily reference rate, source + fixing time declared (WM/R 4pm London default); vintage-stored |
| fx.rate_pit | The rate the CurrencyNormalizer (DICT-00) is allowed to use: last fixing with KT <= asof [PIT] |
Conversion rule per concept comes from `currency_rule` in the concept schema; flows convert at period-average, stocks at period-end — declared once, in DICT-00, applied by the normalizer, never ad hoc in modules.

## 3. Classification (sector/industry)
| concept_id | definition |
|---|---|
| class.scheme | A classification scheme as data: {scheme_id, levels, taxonomy version} — GICS-like licensed schemes and open schemes (e.g. SIC from EDGAR, vendor sectors) are all instances |
| class.membership{scheme} | (entity_id, node, interval) — reclassifications are interval closes, not overwrites [PIT] |
| class.crosswalk{a,b} | Mapping between schemes with fidelity flag {exact, approx, manual} |
| class.primary_scheme | Config: which scheme downstream concepts mean by "sector" (DICT-05 Altman applicability, sector-neutralization in C2) — one default, switchable only by config version bump |
[KEY] Backtests must resolve membership at asof: today's sector map applied to 2015 data is look-ahead (reclassifications correlate with performance).

## 4. Benchmarks
| concept_id | definition |
|---|---|
| ref.benchmark_map | listing/exchange -> benchmark listing_id (DICT-06 beta/idio_vol input); versioned config |
| ref.riskfree_map | ccy -> macro rate concept (USD -> macro.ust_3m); Merton/Sharpe inputs cite this, never hardcode |

## 5. Universes (first-class, PIT)
A universe is a stored, versioned membership series — never a filter re-derived ad hoc in module code.
| concept_id | definition |
|---|---|
| universe.membership{universe_id} | (entity/listing, interval, add/drop events) — index universes from event.index_add/drop (DICT-08); rule-based universes from frozen screens |
| universe.investable_v1 | Rule-based example: primary listing ∧ price ≥ 1 ∧ market.dollar_volume_63d ≥ p10 ∧ not event.action_pending(delisting) ∧ coverage(core concepts) ≥ threshold — rule frozen & versioned; rule change = new universe_id, old one keeps serving [PIT] |
| universe.coverage{universe_id, concept} | % members with servable value at asof — the denominator for V8 and the first thing checked when a signal degrades |
[KEY] Universe construction uses only KT<=asof information, including the DICT-10 survivor logic — a universe that can't reproduce its historical membership is a silent backtest killer. Test: reconstruction at random historical asof equals stored membership (golden).

## 6. Runtime
```python
class CalendarService:   trading_days(mic, span) / align(panel, policy)     # policy: union|intersect|primary, max_ffill per concept
class ClassificationSvc: node(entity, scheme, asof) / neutralize_groups(panel, scheme, level)
class UniverseService:   members(universe_id, asof) / events(universe_id, span)
```
Validation: interval integrity (I1-style, no overlaps), crosswalk round-trip sampling, calendar-vs-actual-prints check (prices on a "closed" day -> calendar bug alert), universe churn monitor (turnover z-score vs history -> rule or data break).
