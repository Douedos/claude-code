# DICT-14 · Adapter contract, ingestion lifecycle, vendor operations
The other side of the abstraction: what a vendor integration must implement, how bytes become vintages, and how vendors are watched, ranked and swapped. Adding a vendor touches exactly three artifacts — adapter (this contract), mapping file (DICT-09), entitlement record (§5) — and zero concepts, zero consumers (B4).

## 1. Adapter SPI (extends CLASS-03)
```python
class VendorAdapter(ABC):
    descriptor: AdapterDescriptor        # static capabilities, see §2
    def fetch(self, capability, scope, span) -> RawBatch          # vendor-native payloads + native keys, UNTOUCHED
    def kt_of(self, raw_record) -> datetime                       # [PIT][KEY] the adapter's hardest job: where
        # knowledge-time truly lives per record (filing_date, revision timestamp, acceptance, feed-arrival).
        # An adapter that can't produce honest KT for a capability must declare kt_policy: arrival_time
        # (conservative: KT = when WE received it) — pessimistic but never look-ahead.
    def healthcheck(self) -> ProbeResult
# Adapters do NOT: map fields (VendorMapper), normalize units (UnitNormalizer), resolve identity
# (EntityResolver), validate (ConceptValidator). One job: honest bytes with honest timestamps.
```

## 2. AdapterDescriptor (capabilities as data — what the router reads)
```yaml
adapter: eodhd_v2
capabilities:
  - {tier: raw_item, concepts: dict9_map_ref, granularity: FQ, history_from: 1990, universe: us_primary}
  - {tier: market, concepts: [raw.price_close, raw.volume], granularity: daily, latency: T+0 18:00 ET}
rate_limits: {rps: 10, daily_quota: 100k, burst: 50}
cost_model: {per_call | flat_month, params}
kt_policy: {fundamentals: filing_date, prices: session_close_arrival}
entitlement_ref: ent.eodhd_2026    # §5
```

## 3. Ingestion pipeline (every batch, every vendor, same stages)
```
fetch -> land (raw payload archived immutable, hash-addressed; replayable forever)
      -> resolve identity (EntityResolver; sub-threshold confidence -> QUARANTINE, not best-guess)
      -> bind (VendorMapper per DICT-09; unmapped fields logged, never dropped silently)
      -> normalize (UnitNormalizer V5, CurrencyNormalizer)
      -> validate (V1..V5 inline "B cells"; V6+ async/sampled per DICT-00)
      -> vintage-write (append-only; value change without new vintage is impossible by construction, V9)
      -> publish (cells become servable; blocked cells enter served-with-gap state, DICT-13 S1)
```
Quarantine & dead-letter: records failing identity or schema go to a replayable queue with reason codes; quarantine ages into `meta.vendor_error_rate`. [KEY] Re-running the pipeline over landed payloads after a map/recipe fix is the ONLY correction path — vintages layer, nothing edits.
Backfill: history loads reconstruct KT from record-level evidence (filing dates, revision stamps); where impossible, `kt_reconstructed: true` flags the vintage and PIT-sensitive consumers (backtests) can exclude or haircut. Never assign KT = period date (the DICT-09 [KEY] rule, enforced at write).

## 4. Vendor health (meta-concepts, monitored like market data)
| concept_id | definition |
|---|---|
| meta.vendor_coverage{vendor, concept} | % of expected universe served (drives V8) |
| meta.vendor_staleness{vendor, concept} | age of newest KT vs expectation (earnings season aware) |
| meta.vendor_error_rate{vendor} | validation-failure + quarantine share, trailing |
| meta.vendor_latency{vendor, capability} | arrival lag distribution vs descriptor's declared latency |
| meta.vendor_drift{vendor, concept} | V6/V7 disagreement rate trend — the early-warning that a vendor changed methodology without telling anyone |
| meta.vendor_cost{vendor} | Spend vs quota; degradation decisions are cost-aware, not just quality-aware |

## 5. Entitlement & licensing (as data, enforced at serve time)
```yaml
entitlement:
  id: ent.eodhd_2026
  scope: {concepts | tiers}, display: internal_only | redistributable, derived_ok: true|false,
  retention: ..., attribution: ...
```
[KEY] Enforcement lives in the DAL serve path (a claim/export carrying a non-redistributable value gets blocked with reason), not in adapter docs nobody reads. CUSIP/SEDOL-style identifier licensing (DICT-10) uses the same mechanism.

## 6. Failover & primacy policy (extends DICT-09 cross-vendor policy)
- Primary vendor per concept-group in config (versioned). Secondaries ingest continuously (warm), serve as V6/V7 checks.
- Switch = explicit config event, never automatic mid-day drift: an incident (health breach, hard outage) triggers a PROPOSED switch ticket; auto-switch only for full outage beyond SLO, and then the panel's `mixed_provenance` meta surfaces it immediately (DICT-13).
- After a switch, the seam is data: provenance changes vendor at date d; V10 distribution checks straddle the seam on purpose (vendor changes masquerade as regime changes — the seam date makes them separable).
- Exit tests: a vendor is removable iff (a) all its concept-groups have a warm secondary passing V6 ≥ 60d (the DICT-08 promotion rule generalized), (b) landed payloads retained per entitlement, (c) replay of last 4 quarters from secondary reproduces panels within tolerance.

## 7. Ops validation
Descriptor-vs-reality audit (declared latency/coverage vs measured, quarterly); chaos drill: replay a day with primary muted, diff panels vs production (the failover fixture); cost regression alerts on per-concept unit cost.
