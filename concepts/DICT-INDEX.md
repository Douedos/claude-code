# Concept Dictionary v1.2 · Index
~360 concepts across 19 files + 18 worked artifacts. DICT-00 is the contract (schema, classes, validation taxonomy V1–V11); 01–08 are content; 09–14 are the abstraction layer itself — everything between a vendor's bytes and a served concept; 15–19 are the EODHD full-surface expansion (capability audit + four new concept domains it can feed). Additive throughout: no prior concept changed.

| File | Contents | ~n |
|---|---|---|
| 00 | Schema, governance, ConceptRegistry/VendorMapper/FallbackResolver/FiscalAligner classes, V1–V11 | — |
| 01 | Raw statement items (IS/BS/CF, shares, market) | 70 |
| 02 | Derived fundamentals (margins, ROIC family, capital structure, working capital, accruals) | 35 |
| 03 | Valuation signals (yield family, EV multiples, shareholder yield) | 14 |
| 04 | Quality/profitability/growth + Piotroski F components | 25 |
| 05 | Solvency & credit (liquidity, coverage, Altman Z/Z'', Ohlson O, Merton DD, composites) | 30 |
| 06 | Market/price-derived (momentum, vol, beta, illiquidity, lottery) | 16 |
| 07 | Filing & text items (10-K/10-Q/8-K structure, extracted flags: going concern, restatement, material weakness, debt ladder, guidance) | 35 |
| 08 | Estimates (schema-first), events, macro (FRED-backed, vintage) | 40 |
| 09 | Vendor mapping layer (EODHD map, XBRL tag chains, cross-vendor policy) | — |
| 10 | Entity & identity (entity/security/listing model, PIT symbology, EntityResolver, I1–I6) | 12 |
| 11 | Corporate actions & AdjustmentChain (candidate→confirmed lifecycle, PIT chains, delisting conventions, A1–A5) | 14 |
| 12 | Reference & universes (calendars, FX, classification-as-data, PIT universe membership) | 18 |
| 13 | DAL service contract (request/Panel envelope, serving rules S1–S5, explain/lineage, materialization, SLOs) | — |
| 14 | Adapter SPI, ingestion lifecycle, vendor health meta-concepts, entitlements, failover policy | 8 |
| 15 | EODHD full-surface audit: ~90 endpoints dispositioned (primary/secondary/candidate/identity/ops/not-adopted), coverage scoreboard, KT honesty table | — |
| 16 | Ownership, insiders, analyst coverage, ESG (own/insider/analyst/esg namespaces; 13F lag & Form-4 KT rules) | 22 |
| 17 | News & sentiment (news namespace; re-resolution of vendor tags, dedup/novelty, scorer promotion path) | 12 |
| 18 | Options-implied (opt namespace; chain hygiene, surface construction, parity/action-seam checks) | 12 |
| 19 | Credit, rates, sovereign & country (sov/credit/rates/country; macro release events & surprise indices) | 25 |

Integration: DAL fundamentals()/macro()/text() serve concept_ids under the DICT-13 contract; adapters bind via DICT-09 maps under the DICT-14 SPI; identity joins via DICT-10; adjusted returns only via DICT-11 chains; universes/calendars/classification via DICT-12; validators run at ingest (B cells) with V6 delegated to X2 sampling; E1 features, C2 recipe inputs, D11 compiled factors and DICT-05 indicators all reference concepts, never vendor fields.
Governance: additive-only like the vocabulary; quirks ledger versioned with the map; primary-vendor per concept in config; disagreement -> data.quality claim, never silent averaging.
Layer invariants (the one-line versions): keys are internal ids, never tickers (10) · prices raw forever, adjustment computed per-asof (11) · nothing static is static — intervals + vintages everywhere (12) · gap-not-garbage, provenance travels, panels deterministic (13) · adapters produce honest bytes with honest KT, corrections replay from landed payloads, vendor swaps are config events with visible seams (14).
