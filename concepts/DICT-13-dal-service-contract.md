# DICT-13 · DAL service contract (the abstract layer's API)
What "DAL fundamentals()/macro()/text() serve concept_ids" (DICT-INDEX) means precisely. One request shape, one response envelope, for every tier and every vendor behind it. Consumers (E1 features, C2 recipes, D11 factors, DICT-05 indicators) see ONLY this contract; a vendor swap, fallback, or quarantine changes provenance metadata, never the shape. Adding a vendor = DICT-09 map + DICT-14 adapter; the contract here never changes (B4 principle).

## 1. Request
```yaml
request:
  concepts: [concept_id, ...]            # any tier; the DAL resolves the dependency graph itself
  scope:    universe_id | [entity_id|listing_id, ...]
  asof:     datetime                     # [PIT] knowledge time; NEVER defaults to now() silently — callers state it
  span:     period | window              # what to return; distinct from asof (what was knowable)
  basis:    concept default | override(FQ|FY|TTM|daily)   # override only where concept declares it legal
  options:
    max_staleness: per-concept default | override        # older than this -> gap, not value
    include_provisional: false           # confirmed_provisional actions, computed fallbacks beyond depth 1, etc.
    quality_floor: A|B|C                 # drop cells below tier
    ccy: reported | base
```
Two query modes, never mixed in one call: `asof` (what was knowable at t — backtests, replays) and `latest_vintage` (current best history — research display). [KEY] Every response is stamped with its mode; a panel without a mode stamp is unservable by definition.

## 2. Response: the Panel envelope
```yaml
panel:
  mode: asof(t) | latest_vintage
  index: (entity|listing, period) × concept
  cells:
    value: number | text_ref | null
    status: ok | gap{reason} | blocked{V-finding ref}     # [KEY] gap-not-garbage: a blocked cell is a gap WITH a reason, never a value
    provenance:                                           # travels with the value, always (DICT-00 FallbackResolver contract)
      source: {vendor, binding_version} | computed{formula_version} | proxy{concept_id}
      flag: reported | computed | proxy | provisional
      vintage_id: ...
      chain_version: ...        # market concepts: AdjustmentChain version (DICT-11)
      recipe_version: ...       # filing_item extractions (DICT-07)
  meta:
    coverage: per concept, vs scope        # served/gap/blocked counts
    mixed_provenance: per concept, share non-primary   # [KEY] the DICT-00 failure mode, surfaced per response so consumers can refuse
    dict_version, map_version, config_version
```
Text tier: `dal.text()` returns span refs + servable text with the same envelope (doc_ref, span, recipe_version as provenance). Estimates/macro identical shape; only the index granularity differs.

## 3. Serving rules
| rule | statement |
|---|---|
| S1 gap-not-garbage | severity≥error V/I-finding blocks the (concept, entity) cell; the panel serves, the cell gaps with the finding ref (DICT-00 §3 policy, enforced here) |
| S2 no silent substitution | fallback/proxy/secondary-vendor values always carry the flag; `quality_floor` and `include_provisional` let callers refuse them |
| S3 determinism | same (request, dict_version, map_version, vintage set) -> bit-identical panel; this is what makes X2 replay and V11 possible |
| S4 dependency resolution | requesting a derived/signal/indicator concept pulls its input subtree at the SAME asof; partial-input policy per concept (null+flag, DICT-02 §guards) |
| S5 no future leak | any cell whose provenance KT > asof is a hard serve error (belt-and-braces over V9), tested with poisoned-fixture goldens |

## 4. Lineage & explain
```python
class DAL:
    def panel(self, request) -> Panel
    def explain(self, concept_id, entity, asof) -> Lineage
    # Lineage = full derivation tree: concept -> formula -> input cells -> vendor bindings -> raw payload refs
    # -> vintages -> validations run (pass/fail) -> fallback decisions taken. [KEY] Every number the
    # solution acts on is explainable to a raw vendor payload in one call; claims can embed lineage refs.
    def coverage(self, universe_id, concepts, asof) -> CoverageReport      # pre-flight for consumers
```

## 5. Materialization (behavior, not contract)
Raw/vendor-bound cells stored at ingest; derived/signal/indicator computed at read by default, memoized keyed on (inputs' vintage set, formula_version) — a new input vintage invalidates exactly its dependents (ConceptRegistry.dependents). Precompute schedules are an ops concern (DICT-14); [KEY] consumers cannot tell (and must not be able to tell) cached from freshly computed — S3 guarantees it.

## 6. Layer SLOs (meta-concepts, monitored like data)
meta.dal_latency{tier} · meta.dal_availability · meta.panel_block_rate{concept} · meta.mixed_provenance_share{concept} — alerts route with vendor-health signals (DICT-14); persistent block-rate elevation on a concept is a mapping/vendor incident, not a consumer problem.
