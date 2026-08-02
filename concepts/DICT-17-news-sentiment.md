# DICT-17 · News & sentiment (tier: text/market hybrid; namespace news)
News enters through dal.text() like filings (DICT-07 discipline: text is evidence, scores are extractions), not as a magic daily number. Vendor sentiment (EODHD polarity/pos/neg/neu) is bootstrap and cross-check; frozen D4 recipes over article text are the promotable scorer. Single-source cap applies (DICT-15 §4).

## 1. The raw item
| concept_id | definition |
|---|---|
| news.item | {doc_ref, published_at, kt=max(published, arrival), title, body_ref, source_domain, vendor_tags[], vendor_symbols[]} |
[KEY] vendor_symbols is a JOIN OPINION, not identity: articles are re-resolved through EntityResolver (DICT-10) — entity mentions in title/body vs vendor tagging; disagreement → tag dropped, resolution logged. Vendor mis-tagging (parent/subsidiary, ticker collision across exchanges) is the #1 quality issue in every news feed.
[PIT] kt = max(published, arrival): vendors backfill articles into history; an article we received Tuesday about Monday is Tuesday knowledge. Arrival log is append-only precisely to make this provable.

## 2. Per-article extractions (recipe-versioned, DICT-07 rules: evidence = the article itself)
| concept_id | definition | notes |
|---|---|---|
| news.polarity_vendor | Vendor sentiment {polarity, pos, neg, neu} as delivered | tier C, frozen as-delivered; recipe_id = vendor_model (opaque, versionless → quarantine-diff monitor below) |
| news.polarity_d4 | Our frozen D4 query battery over title+body | promotable; recipe versioned like filing extractions |
| news.event_class | {earnings, guidance, M&A, litigation, product, management, financing, regulatory, other} frozen classifier | joins event.* concepts as soft candidates (e.g. M&A class → action.merger probe) |
| news.novelty | 1 - max similarity vs entity's trailing 30d articles | reprints/syndication collapse; dedup BEFORE aggregation |

## 3. Entity-day aggregates (market-tier consumables; daily, from deduped, re-resolved articles)
| concept_id | definition | notes |
|---|---|---|
| news.volume_1d / volume_21d | Article count (novelty-weighted) | attention proxy; V10 monitored |
| news.sent_1d | Novelty-weighted mean polarity (scorer per config: vendor or d4; scorer_id in provenance) | [KEY] one scorer per panel — mixing scorers across entities in a cross-section is the mixed-provenance failure |
| news.sent_21d | EWMA, half-life 5d | |
| news.sent_shock | (sent_1d - sent_21d) / trailing std, min 10 articles | the tradable form; sparse-coverage null+flag |
| news.sent_dispersion | Std of polarity across same-day articles | disagreement measure |
| news.coverage_regime | Percentile of volume_21d vs entity's 1y history | neglected-to-spotlight transitions |
| news.tag_exposure{theme} | Share of 21d articles matching theme lexicon (vocab/ theme, versioned) | bridges to theme.exposure / DICT-07 mdna_tone |

## 4. Governance & validation
- Article text retention per entitlement (DICT-14 §5): body may be non-redistributable while derived scores are fine — enforcement at serve/claim time, body_ref access-controlled.
- Vendor-model drift monitor: vendor polarity is an unversioned black box — weekly PSI of polarity distribution on a fixed reference corpus; drift → data.quality claim + freeze reliance (this is the V10 idea applied to an opaque upstream model).
- V-news1: symbols-resolution agreement rate per source_domain (drops → source quarantined). V-news2: dedup effectiveness sampled by X2. V2 bounds on all aggregates; V9 vintages on everything (re-scoring with a new recipe = new vintage, old panels reproducible).
- Promotion path: news.sent_* served from vendor scorer at tier C → D4 scorer runs shadow 60d → X2 comparison → config flips scorer_id (visible seam, DICT-14 §6 pattern).
