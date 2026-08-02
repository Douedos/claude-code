# DICT-07 · Filing and text items (tier: filing_item)
"Just items from SEC filings" made first-class. Two kinds: STRUCTURAL (a located span of a filing, servable as text) and EXTRACTED (a typed value/flag pulled from the span, with the passage as evidence). Extracted items are produced by frozen extraction recipes (D4-style or rule-based), never freeform; every extracted value carries doc_ref + span.

## Structural items (dal.text sections; KT = filing acceptance)
| concept_id | definition |
|---|---|
| filing.10k.item1_business | Item 1 |
| filing.10k.item1a_risk_factors | Item 1A (also served diffed: filing.10k.risk_factors_delta vs prior year — change is the signal) |
| filing.10k.item3_legal | Legal proceedings |
| filing.10k.item7_mdna | MD&A |
| filing.10k.item7a_market_risk | Quantitative/qualitative market risk |
| filing.10k.item8_financials | Statements + footnotes block |
| filing.10q.part1 / filing.10q.mdna | Quarterly analogues |
| filing.8k.item_code | 8-K item taxonomy as event concepts: 1.01 material agreement, 1.03 bankruptcy, 2.01 acquisition/disposition completed, 2.02 results, 2.05 exit/restructuring costs, 2.06 material impairments, 3.01 delisting notice, 4.01 auditor change, 4.02 non-reliance (restatement!), 5.02 officer/director changes, 7.01 Reg FD, 8.01 other |
| filing.proxy.compensation | DEF 14A comp section |
| filing.footnote.debt_schedule | Debt footnote (maturity ladder source) |
| filing.footnote.segments | Segment reporting |
| filing.footnote.leases | Lease commitments |
| filing.footnote.pension | |
| filing.footnote.contingencies | Litigation/commitments |

## Extracted flags and values (validation [V1,V2] + evidence-passage required)
| concept_id | type | extraction definition |
|---|---|---|
| filing_item.going_concern | bool | "substantial doubt ... going concern" in auditor opinion or notes; rule-first, LLM-confirm; passage attached |
| filing_item.auditor_opinion | enum{unqualified, qualified, adverse, disclaimer} + auditor name | opinion page parse |
| filing_item.auditor_change | event | from 8-K 4.01 |
| filing_item.restatement_flag | bool + scope | 8-K 4.02 or amended filings (10-K/A with restated financials) |
| filing_item.material_weakness | bool | ICFR section: "material weakness" assertion |
| filing_item.late_filing | bool | NT 10-K / NT 10-Q presence |
| filing_item.debt_maturity_ladder | vector{<1y,1-3y,3-5y,>5y} | debt footnote table extraction (tier B; table parser + reconcile to raw.total_debt within tol -> V11-style check) |
| filing_item.offbs_commitments | currency | contingencies/commitments totals (tier C) |
| filing_item.customer_concentration | pct | "customer(s) accounted for X% of revenue" extraction |
| filing_item.segment_revenue | table | segments footnote -> per-segment revenue concepts |
| filing_item.risk_factor_count / risk_factor_novelty | count / score | 1A structure; novelty = 1 - max similarity of each factor vs prior year's set |
| filing_item.mdna_tone | score | frozen D4 query battery over MD&A (guidance tone, demand language) — bridges to theme.exposure |
| filing_item.insider_ownership | pct | proxy extraction (tier C) |
| filing_item.buyback_authorization | currency + date | 8-K/press extraction, KT = announcement |
| filing_item.guidance_revision | enum{raise, maintain, cut, withdraw} | 8-K 2.02 / release parsing; joins D8 |

[KEY] Every extracted item: (a) passage evidence mandatory (claims fail validation without span refs); (b) extraction recipe versioned — a recipe change re-extracts forward only, history keeps its recipe version (PIT of the extractor itself); (c) X2's evidence-fidelity dimension samples these heavily at first (new-source stratum).
