# DICT-10 · Entity & identity layer (tier: reference)
The layer everything else silently assumes. Every vendor keys data its own way (ticker, ISIN, vendor-internal id, CIK); the DAL keys everything by an internal, immutable `entity_id` / `listing_id` pair. Identity mapping is data — versioned, point-in-time, quorum-checked — exactly like DICT-09 field maps. [KEY] A wrong join here corrupts every concept downstream and no V-check catches it (values are individually plausible); identity gets its own validation family (I1–I6 below).

## 1. Identity model
Three levels, never conflated:
| level | id | definition |
|---|---|---|
| entity | entity_id | The economic/legal issuer (survives renames, ticker changes, redomiciles). Internal, immutable, never recycled. |
| security | security_id | An instrument issued by an entity (common class A/B, preferred, ADR). |
| listing | listing_id | A security on an exchange in a currency (AAPL on NASDAQ ≠ APC on XETRA — same security, different listing, different prices/calendar/currency). |

Fundamentals and filings bind at **entity** level; prices/volume/market concepts at **listing** level; shares outstanding at **security** level. `raw.market_cap` = security-level shares × primary-listing price — the join is declared, not incidental. Primary-listing election is itself PIT data (`ident.primary_listing`, changes are events).

## 2. Identifier concepts (all interval-valid, PIT)
| concept_id | definition | notes |
|---|---|---|
| ident.ticker | Exchange ticker with validity interval [from, to) | [KEY] tickers are RECYCLED (dead company's ticker reassigned); a ticker is never a key, only (ticker, exchange, date) resolves |
| ident.exchange_mic | ISO 10383 MIC of listing | |
| ident.isin / ident.cusip / ident.sedol | Security-level identifiers, interval-valid | reused after corporate events; licensing: CUSIP/SEDOL redistribution restricted (entitlement flag from DICT-14) |
| ident.figi | OpenFIGI, listing-level; preferred public join key | free redistribution |
| ident.cik | SEC registrant id, entity-level | stable, never recycled — anchor for filings join |
| ident.lei | Legal Entity Identifier, entity-level | coverage partial (tier B) |
| ident.vendor_key{vendor} | Vendor's native primary key (e.g. EODHD symbol) | one per vendor, interval-valid; the ONLY place vendor keys exist |
| ident.primary_listing | Elected primary listing_id per security | election rule: home exchange, then largest 63d dollar volume; changes are events |
| ident.entity_name | Legal name with validity interval | renames are events, not overwrites |
| ident.country_domicile / ident.country_listing | ISO 3166 | redomicile = event |

## 3. Resolution (runtime class, extends CLASS-03)
```python
class EntityResolver:
    def resolve(self, vendor, native_key, asof) -> ResolvedId   # (entity_id, security_id, listing_id, confidence)
    # [KEY] resolution is PIT: same vendor key resolves differently across time (ticker recycling).
    # Match cascade (first hit wins, choice recorded as provenance):
    #   1. ident.vendor_key exact (curated map)
    #   2. FIGI exact -> 3. ISIN+MIC -> 4. CUSIP -> 5. CIK (entity level only)
    #   6. (ticker, exchange, asof) interval lookup
    #   7. name-fuzzy -> NEVER auto-binds: emits candidate for review queue (I5)
    # confidence < threshold -> data quarantined (DICT-14), not served under a guessed id.
class IdentityLedger:  # append-only intervals; corrections close an interval and open a new one [PIT]
    def intervals(self, id_kind, value) -> list[Interval]
    def survivor(self, entity_id, asof) -> entity_id   # merger chains: acquired entity forwards to survivor AFTER effective date only
```

## 4. Identity validation (I-family, referenced like V-ids)
| I | Name | Method |
|---|---|---|
| I1 | Uniqueness | at any asof: one live primary interval per (id_kind, value); overlaps are hard errors |
| I2 | Cross-id consistency | FIGI↔ISIN↔ticker triangle agrees per asof; disagreement -> quarantine + ticket |
| I3 | Vendor-key drift | vendor key resolving to a different entity than yesterday without an identity event -> block (this is how silent ticker recycling is caught) |
| I4 | Continuity-of-entity | fundamentals jump (V4) coinciding with an identity interval boundary -> suspect bad join before suspecting restatement |
| I5 | Fuzzy-match review | name-based candidates human/X2-confirmed before entering the ledger |
| I6 | Survivorship audit | resolved universe vs known delistings: dead entities must stay resolvable (asof in their life) — [KEY] survivorship bias enters through the ID layer, not the data layer |

Findings -> `data.quality{scope: identity, I, ...}` claims, same policy as V-findings (block on severity≥error).

[KEY] Delisted/dead entities are never purged: `EntityResolver.resolve(asof=historical)` must work forever, or every backtest inherits survivorship bias silently.
