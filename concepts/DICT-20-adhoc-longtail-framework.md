# DICT-20 · Ad-hoc & long-tail data framework (tier: any; the sandbox track)
For data that arrives as a file, a scrape, a niche API, or a one-off research download — RAM spot prices, trade flows, product catalogs, anything. Design ruling: **separate onboarding track, separate catalog section, SAME serving contract.** Ad-hoc data enters through a lighter gate but flows through the identical DAL/panel/provenance/vintage machinery (DICT-13/14). The alternative — side-channel CSVs joined in module code — is the single most common way quant stacks rot: unversioned inputs, invented KT, silent revisions. This track exists so the lazy path IS the governed path.

## 1. Subject model extension (generalizes DICT-10)
Concepts so far key on entity/listing/country. Ad-hoc data keys on anything:
```yaml
subject_kind: entity | listing | country | commodity | product | category{scheme} |
              trade_lane{from,to} | region | series      # `series` = self-keyed (an index is its own subject)
subject_id:   namespaced, immutable, interval-metadata like entity_ids (DICT-10 rules apply:
              never recycled, dead subjects stay resolvable)
```
```python
class SubjectRegistry(extends EntityResolver ideas):
    def resolve(self, manifest, native_key, asof) -> subject_id   # per-dataset key map; fuzzy -> review queue, never auto
```
[KEY] A product renamed, a commodity spec change (DDR4→DDR5), an HS-code revision — all interval events, not overwrites. Subject identity is where ad-hoc datasets silently break; it gets DICT-10 discipline from day one.

## 2. Linkage concepts (how non-entity subjects reach the solution)
Ad-hoc data is useless to a per-entity solution until linked. Linkage is data, never inline code:
| concept_id | definition |
|---|---|
| link.exposure{subject → entity} | {entity_id, subject_id, direction: +/-, channel: revenue|cost|competition|supply, weight ∈ [0,1], method: curated|filing_derived|D4_extracted, evidence_ref?, version} |
| link.membership{subject → subject} | Hierarchies: product → category, HS6 → HS2, commodity → complex |
[KEY] direction+channel matter more than weight: DRAM spot ↑ is revenue+ for memory makers, cost− for device OEMs — one series, opposite exposures. Filing-derived links (supplier/customer mentions, segment text via DICT-07 machinery) carry evidence passages like any extraction; curated links carry an author + review date. Links are versioned; a panel cites link_version in provenance like everything else.

## 3. Dataset manifest (the onboarding unit — one YAML, replaces "just load the CSV")
```yaml
dataset_id: adhoc.dram_spot_v1
origin: {kind: file_drop|scrape|api_lite|manual_entry, ref: ..., owner: person}
subjects: {kind: commodity, key_map: {column: part_no -> subject_id via curated map}}
schema: {columns, units, currency, scale}          # UnitNormalizer rules declared, not inferred
cadence: daily|weekly|monthly|irregular
kt_policy: arrival                                  # [KEY] the honest default; a manifest claiming better
                                                    # than arrival must prove where KT lives (DICT-14 kt_of rule)
history: {loaded: true, kt_reconstructed: true}     # backtest usability declared UP FRONT, not discovered
license: {redistributable: false, derived_ok: true, source_attribution: ...}
refresh: {expected: weekly, staleness_alert: 21d}   # V8 wiring
status: sandbox                                     # lifecycle §4
```
`GenericTableAdapter` implements the DICT-14 SPI from a manifest alone: land (hash-addressed) → resolve subjects → normalize → validate light baseline [V1,V2,V8,V9] → vintage-write → publish. A vendor restating a file in place is detected by hash diff → new vintage with supersession note (same trick as the DICT-19 country panel). Manual-entry datasets get an entry log (who, when, source doc) as their landed payload.

## 4. Lifecycle: sandbox → probation → graduated | retired
| stage | rules |
|---|---|
| sandbox | Served ONLY via explicit dataset_id request; never in universe-wide panels; tier none; free schema iteration (manifest versions) |
| probation | Enters the catalog under `adhoc.*`; tier C hard cap; panels flag adhoc provenance; composites/indicators may NOT consume it (S2-style refusal is automatic); ≥ 60d of refreshes + stable schema + V8 clean required to advance |
| graduated | Promoted into a real namespace (cmdty.*, trade.*, product.* — DICT-21) via additive rename-alias; tier per normal rules; second-source and KT caps still apply (DICT-15 §4) |
| retired | Refresh stopped or source dead: dataset frozen read-only, history stays servable forever (PIT), status prevents new dependencies |
[KEY] Graduation is a governance event with a review (subject map audit, license check, V-history), not a config flip. The `adhoc.` prefix is the quarantine — the moment it disappears, the data has earned the same trust as vendor feeds.

## 5. Honesty rules specific to this track
- kt = arrival unless proven otherwise; scraped "historical" data is context, not backtest fuel — panels built in asof mode simply won't include pre-arrival history (kt_reconstructed cells excluded by default, opt-in via include_provisional).
- Irregular cadence: no forward-fill beyond declared max_ffill (default: one cadence period); gaps serve as gaps.
- One-off snapshots (a consultant table, a paper's dataset) are legal: cadence irregular, refresh none — they age into staleness naturally instead of living forever in a notebook.
- Attribution/redistribution from license block enforced at serve/claim time (DICT-14 §5 mechanism, unchanged).
