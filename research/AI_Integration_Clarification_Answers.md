# AI Integration Clarification — Answered Design Checklist

**Status:** Proposed answers (v0.1) — a proposal, not a substitute for approval, per the checklist's own rule.
**Provenance rule:** Every answer is grounded in the research skeleton ("AI Integration and Economic Effects", v0.1, Aug 2026) or in the handover assessment of it. Answers that go beyond the skeleton are tagged **[PROPOSED CHANGE]** and correspond to the numbered critique points in the handover review. Any changed answer must create a versioned design decision, not silently alter an analysis.

---

## A. Research objective and claim boundaries

### A1 — What is the primary scientific question?
**Response:** Does unexpected AI adoption at time t — the AI Integration Surprise (AIS), i.e., adoption residualized on structural predictors — predict unexpected economic performance (Economic Productivity Surprise, EPS) in cognitively AI-exposed activities at horizon t+h?
**Rationale:** This is the skeleton's core question (§1.1) and its highest-priority hypothesis H7. The emphasis on "unexpected" on both sides is deliberate: raw adoption and raw growth are each dominated by structure (income, digitalization, occupational mix; development stage, demographics, sector mix).

### A2 — What counts as success: correlation, prediction, mechanism evidence, or causal evidence?
**Response:** For v1: **out-of-sample prediction plus mechanism-consistent evidence** — a "Provisional" grade on the skeleton's ladder (consistent across independent providers, search-adjusted significance, correct negative-control behavior), upgradable to "Strong" only via the prospective 2027–2028 holdout. Correlation alone is explicitly insufficient; causal evidence is explicitly out of reach for this design.
**Rationale:** The evidence-grading table (§10) caps the panel framework below "Causal", which requires a quasi-experimental/instrumental design beyond v1. **[PROPOSED CHANGE]** A null is also a publishable success *if* the pre-computed MDE shows the design had power to detect plausible effect sizes — otherwise it is only "underpowered", and the honest deliverable is the pre-registered instrument for 2027–2030.

### A3 — What claims are explicitly out of scope for the first version?
**Response:** (1) Any causal claim; (2) any numeric result inherited from the exploratory chat (correlations, p-values, rankings, sample sizes); (3) the earlier finance-productivity claim, already killed by the robustness audit; (4) stock-return causation; (5) treating monthly services production as labor productivity; (6) treating OpenRouter billing geography as end-user geography; (7) countries without provider coverage (e.g., China); (8) firm-level or within-firm claims — the unit is national/sectoral; (9) policy recommendations.
**Rationale:** Items 1–6 are the skeleton's §13 "what should not be inherited" plus the grading cap; 7–9 follow from the data sources and design scope.

### A4 — Should stock-market returns remain a primary outcome or only downstream validation?
**Response:** **Downstream validation only.**
**Rationale:** Skeleton is unambiguous: market outcomes are "most downstream / most confounded" (Axis B), H1's next action is "keep only as downstream validation", and priority 5 gates equity returns behind mechanism-level evidence. S17 (CountryETFTracker) is exploratory-only and must be replaced by primary market data even for that role.

## B. Unit of analysis and geography

### B1 — Canonical observational unit?
**Response:** **Hybrid, two linked panels:** primary inference on **country × sector × year** (Eurostat real GVA per hour, nama_10_lp_a21); a fast-moving intermediate panel on **country × sector × month** (services production, sts_sepr_m), labeled output, never productivity.
**Rationale:** The skeleton's Axis B puts annual sectoral productivity "closest" to the mechanism and monthly services output as "intermediate" (H5's role); §8 requires one canonical country × month × sector table with unique keys, from which the annual panel aggregates deterministically.

### B2 — Primary geography?
**Response:** **EU/EFTA as the primary inference sample** (dictated by Eurostat outcome coverage), with a **global descriptive layer** for adoption (Microsoft/OpenAI/Anthropic cover far more countries) used for the AIS residual model and for context, not for core outcome regressions.
**Rationale:** The core outcome sources (S08–S10) are Eurostat; the adoption sources are global. Fitting the AIS model on the wider global cross-section improves the residualization while inference stays where outcomes exist. **[PROPOSED CHANGE]** This makes the effective inference N ≈ 27–31 countries — the binding constraint driving the power analysis (see H4/K3).

### B3 — How are China and provider-restricted countries handled?
**Response:** **Excluded from telemetry-based inference** — provider data cannot measure adoption where the providers are unavailable — and recorded as explicit geography exclusions in the staging concordance, with the exclusion list versioned and reported.
**Rationale:** Follows from the availability confounder (§5: language/product availability) and the mandatory "country-code concordance and geography exclusions" check (§8.1). Their absence must be stated, not silent.

### B4 — Minimum country coverage before a cross-sectional result is discussed?
**Response:** Pre-specified floor: **N ≥ 20 countries** with non-missing AIS and outcome for any headline cross-sectional statistic; below the floor a result may only appear labeled "Exploratory". Every headline statistic additionally requires the automatic leave-one-country-out sweep.
**Rationale:** The skeleton demands outlier defenses for "small cross-sections" (§5: Estonia/Korea-type dominance) but sets no number; a fixed floor converts that into an enforceable gate. **[PROPOSED CHANGE]** The floor is complemented by the MDE computation: coverage alone does not confer power.

## C. AI measures and timing

### C1 — Primary source for broad adoption?
**Response:** **Microsoft AI Diffusion (S01 report + S02 repository)**, with S02's machine-readable files as the ingestion path and version anchor.
**Rationale:** It is the only broad, **cardinal** user-share by country and period (skeleton S01 "Use" field); OpenAI Signals is rank-based and plan-restricted, Anthropic is one provider's usage, OpenRouter is API traffic.

### C2 — How are Anthropic, OpenAI and OpenRouter used relative to Microsoft?
**Response:** Anthropic (S03/S04): independent provider-specific adoption/depth measure and replication check. OpenAI Signals (S05/S06): ordinal cross-check (messages-per-person ranks; excludes Enterprise/Codex). OpenRouter (S07): **API/developer depth only, robustness class, never broad adoption**. Provider-specific AIS measures are computed **before** any reconciliation. **[PROPOSED CHANGE]** Promote reconciliation from "robustness layer" (skeleton priority 4) into core AIS construction: extract a latent adoption factor, or instrument one provider's measure with another's — provider measurement error is non-classical (correlated with language/availability, which are also AIS predictors), and multi-provider designs correct it rather than merely decorate it.
**Rationale:** Skeleton §4.1, §5 (language/availability, billing location), §13 ("do not mix in raw units"); the promotion is critique point 5 of the handover review.

### C3 — Should provider measures ever be averaged in raw units?
**Response:** **No, never.** User-shares (Microsoft), usage shares (Anthropic), ranks (OpenAI) and token volumes (OpenRouter) are incommensurable. Combination happens only after per-provider standardization/residualization, via rank aggregation or a latent factor.
**Rationale:** Explicit skeleton rule (§13) and the "avoid raw averaging" mitigation for billing-location bias (§5).

### C4 — Definitions of breadth, depth, professional intensity?
**Response:** **Breadth** = AI users per working-age person (Microsoft user share). **Depth** = usage intensity conditional on adoption: tokens/messages per user, API/agentic activity (Anthropic per-capita index, OpenRouter tokens). **Professional intensity** = AI users per white-collar worker, ISCO-08 major groups 1–4 (ILOSTAT denominators), sensitivity on groups 1–3. **Acceleration** = change in adoption over the period. **AIS** = the residual of adoption after structural predictors — the inferential object.
**Rationale:** Direct transcription of Axis A (§3.1) with D3's denominator definition.

### C5 — What time lag between adoption and outcome should be tested?
**Response:** A **pre-specified, closed lag family**, fully logged and included in the permutation correction: h ∈ {0, 6, 12, 24} months for the monthly output panel; h ∈ {0, 1, 2} years for annual productivity. Prior mass on lagged rather than contemporaneous effects. Leads (future AI "predicting" past outcomes) run automatically as placebos, never as candidate results.
**Rationale:** The skeleton demands lags (Axis C, H7 "requires careful residual models and lags") but leaves them open — an open lag menu is exactly the search flexibility §7 penalizes, so the family must be closed in advance. The lag prior follows the productivity-J-curve reading of why H2–H5 were near-neutral (handover review). With adoption data starting ~2023, long lags are barely observable pre-holdout — an argued limitation, not a fixable one.

## D. Normalization and orthogonalization

### D1 — Preferred normalization for inference?
**Response:** **Residualized surprises (AIS and EPS), not ratios.** Ratios stay descriptive.
**Rationale:** Skeleton §4: "the main inferential objects should be residualized 'surprises' so the denominator does not mechanically create the relationship." The whole H0→H7 path is the argument.

### D2 — Which ratios remain descriptive only?
**Response:** AI/GDP, AI/population, AI/working-age population, AI/white-collar (as a raw ratio), AI/software-spending (S16 — exploratory only, definition excludes internal development), and every H0–H1 object.
**Rationale:** Skeleton H1 lesson ("ratio artifacts"), §5 (specification search), S16's use class. Ratios may motivate; they may not testify.

### D3 — Definition of white-collar employment?
**Response:** **ISCO-08 major groups 1–4** (managers, professionals, technicians, clerical support) from ILOSTAT tables; **groups 1–3 as the sensitivity** variant. Sources S13/S14.
**Rationale:** Verbatim from S13's use field and the occupational-mix mitigation (§5).

### D4 — Covariates in the AI-adoption residual model?
**Response:** GDP per capita, internet access/penetration, education, white-collar share, digital readiness, language, region, and provider availability — per skeleton §4.1. **[PROPOSED CHANGE]** Keep this set frozen and parsimonious: with a global fitting sample but only ~30 inference countries, every added covariate consumes scarce degrees of freedom and the residual becomes noise; the covariate list is itself a searched object and belongs in the ledger.
**Rationale:** Skeleton §4.1 and §5 (income/digital maturity mitigation); the parsimony warning is critique point 3 (generated-regressor / overfit risk at small N).

### D5 — AIS estimated linearly, by ranks, or flexibly?
**Response:** **Transparent linear and rank models first**; a flexible model only with **cross-fitting** (no observation used to fit and evaluate its own residual). **[PROPOSED CHANGE]** Additionally: (a) run the one-step equivalent — controls entered directly in the outcome regression (Frisch–Waugh–Lovell logic) — so two-step residualization never silently drives inference; (b) bootstrap the *entire* two-step pipeline, because AIS is a generated regressor and naive second-stage standard errors are wrong (Pagan 1984).
**Rationale:** Skeleton §4.1 sets (linear/rank first, cross-fitting required); the additions are critique point 3.

## E. Economic outcomes and sector exposure

### E1 — Primary economic outcome?
**Response:** **EPS built on real GVA per hour worked**, annual, by country and industry — Eurostat nama_10_lp_a21 (S08) — for the cognitively exposed sectors; residualized on history, cycle, capital, employment, sector and country effects per §4.2.
**Rationale:** Axis B ranks per-hour sectoral productivity "closest" to the mechanism; H7 is the priority hypothesis; the skeleton fixes real GVA as numerator and hours as labor input.

### E2 — How are services output and labor productivity distinguished?
**Response:** By an **enforced naming rule in the codebase**: any monthly sts_sepr_m series is `output`/`production`; the word `productivity` is reserved for series with an explicit labor-input denominator. The S09 metadata (Services Production Index definition) is the reference; a lint-style check on variable names backs the rule.
**Rationale:** Skeleton §4.2 and §13 ("do not treat monthly services production as labor productivity"); H5's lesson was precisely "output is not productivity".

### E3 — Which sectors are AI-exposed?
**Response:** Information & communication (NACE J), professional/scientific/technical (M), and finance/insurance (K) — the skeleton's named trio. **[PROPOSED CHANGE]** The exposure weighting must come from **established occupational-exposure indices** (Felten et al. AIOE, Eloundou et al., or the Anthropic Economic Index task mapping) rather than a bespoke score, and the choice of index is logged as a searched specification.
**Rationale:** Skeleton Axis B and §4.3 (CognitiveExposure_s); the index rule is critique point 4 — a hand-built exposure measure re-opens the researcher degree of freedom this design exists to close.

### E4 — Which sectors are negative controls?
**Response:** Low-cognitive-exposure services and industry: accommodation & food (I), transportation & storage (H), construction (F), and mining/utilities where covered — chosen as the bottom of the same published exposure index used for E3, fixed before estimation.
**Rationale:** The skeleton requires negative-control sectors (Axis C sector interaction; §7 placebos "test low-exposure sectors") without naming them; deriving both tails from one pre-specified index keeps the choice non-discretionary.

### E5 — How is GDP growth surprise constructed; which forecast vintage is baseline?
**Response:** Actual real GDP growth (WEO April 2026 vintage, S11) minus the forecast from the **pre-AI-vintage WEO October 2024 database (S12)** — the designated baseline — computed per country and horizon. Secondary macro outcome only (H3's role).
**Rationale:** S12's use field says exactly this ("pre-AI-vintage forecast baseline for GDP-growth surprise"). The Oct-2024 vintage largely predates country-specific AI-adoption effects entering IMF forecasts, which is what makes the surprise informative.

### E6 — Employment, hours, wages, margins, firm creation as additional channels?
**Response:** **Yes, as secondary/operational channels** — employment, hours (already the productivity denominator), wages and business formation from the skeleton's operational layer — hypothesis-generating and mechanism-consistency checks only. Margins/earnings sit in the market layer: downstream validation only (see A4).
**Rationale:** Axis B's operational layer; the grading ladder's "mechanism outcomes align" criterion for a Strong grade is what these channels serve.

## F. Dynamic structure

### F1 — Main dynamic hypothesis?
**Response:** **Lagged effect with sector interaction** — AIS × cognitive exposure → future productivity surprise (priority 1 / H7) — with the **shock-interaction family** (AIS × identified shock → response) as the pre-specified second family (priority 2 / H6). Level, acceleration and threshold forms remain in the searched family, corrected for.
**Rationale:** Skeleton §11 priorities and §4.3's two regression families; §11 states the prior has shifted away from level effects toward mechanism-close, lagged, heterogeneous effects.

### F2 — How are month and country effects controlled?
**Response:** Baseline per skeleton: country FE, time (month/year) FE, sector FE, region×time where needed. **[PROPOSED CHANGE]** Because identification runs through the AIS × exposure interaction, absorb **country×time and sector×time fixed effects** (Rajan–Zingales design): identification then comes purely from within-country, cross-sector variation, and country-level macro shocks — which the confounder map worries about — drop out entirely. Inference by **wild-cluster bootstrap** clustered on country (~30 clusters is too few for asymptotic clustered SEs).
**Rationale:** Skeleton §4.3/§5 for the baseline; the upgrade is critique point 2 of the handover review — a strictly stronger specification the interaction design permits for free.

### F3 — How to test whether a neutral average hides time-varying structure?
**Response:** The pre-specified dynamic statistics of §7.1: variance of the monthly coefficient vs. the permutation null; trend in the coefficient (are AI-intensive countries progressively pulling ahead?); regime autocorrelation; shock-conditional response. Each compared against nulls that preserve the time-path structure (see H1).
**Rationale:** This is Axis C's variance/persistence effect and H6's formalization — the skeleton's answer to "a near-zero average can hide lagged, threshold, sector-specific or shock-dependent effects".

### F4 — What constitutes persistence rather than random sign-flipping?
**Response:** Coefficient-path autocorrelation (and regime-duration statistics) **exceeding the permutation distribution** generated by reassigning AI labels across countries with each country's full time path preserved, with block resampling for time dependence. Persistence is a rejected null, not an eyeballed run of same-sign months.
**Rationale:** Direct combination of §7.1 ("positive/negative AI regimes persistent rather than random sign flips") with §7's resampling rules.

## G. Confounders and placebos

### G1 — Confounders that must be controlled before any economic interpretation?
**Response:** All ten rows of the skeleton's confounder map: country scale; income & digital maturity; occupational mix; AI-producer exposure; language & product availability; billing/cloud location; reverse causality; common macro shocks; persistent structural country differences; measurement revision — plus the two meta-confounders, specification search and outliers. Each transformation must state which row it mitigates; post-hoc ratios with no mechanism are rejected.
**Rationale:** Skeleton §5, including its governing rule ("every transformation should have a stated causal/statistical purpose").

### G2 — Isolating AI-use benefits from AI-production/semiconductor exposure?
**Response:** Producer-vs-user decomposition: technology/semiconductor sector weights as covariates; sensitivity analyses excluding or flagging producer economies (Korea, Taiwan, Netherlands); and checking outcomes in **non-AI-producing sectors** of producer countries — if gains appear only in producer sectors, the story is hardware exports, not AI-use productivity.
**Rationale:** Skeleton §5 AI-producer row, verbatim mitigations; H0's original lesson (Korea/Taiwan) motivated it.

### G3 — Language, availability and billing-location bias?
**Response:** Language and availability enter the AIS residual model as covariates (§4.1); provider-specific estimates are computed before reconciliation so provider-specific telemetry bias stays visible; OpenRouter is depth-only; billing-hub sensitivity re-runs exclude hub economies (Singapore, Netherlands, Ireland-type). Raw cross-provider averaging is banned (C3).
**Rationale:** Skeleton §5 language/availability and billing rows. **[PROPOSED CHANGE]** The multi-provider latent-factor/IV construction (C2) is the systematic correction; the exclusions are its diagnostics.

### G4 — Placebo tests that run automatically?
**Response:** Four, on every headline result: (1) **lead placebo** — future AI "predicting" past outcomes; (2) **substitution placebo** — replace AI with broadband penetration or GDP per capita; (3) **negative-control sectors** — the E4 set must show no effect; (4) **permutation placebo** — AI labels reassigned across countries, full time paths preserved. Failures block promotion past Exploratory.
**Rationale:** Skeleton §7 placebo list; the blocking rule implements the grading ladder's "negative controls behave correctly" requirement.

## H. Resampling and search correction

### H1 — Resampling scheme preserving dependence?
**Response:** (a) Cross-section: permute AI exposure labels across countries **keeping each country's entire time path intact**; (b) time: block bootstrap, never independent month resampling; (c) sectors: max-stat across exposed and negative-control sectors jointly. Deterministic seeds throughout.
**Rationale:** Skeleton §7 bullets and the §8.1 seed rule — the null must "repeat as much of the search procedure as feasible".

### H2 — How is specification search penalized?
**Response:** The **max-statistic permutation p-value** over the genuinely searched family: p_search = P(max over the family of permuted statistics ≥ best observed statistic). The machine-readable search ledger defines the family (ratios, residualizations, lags, providers, sectors actually tried — including the H0–H6 chat history, which is why it was preserved). p_search is reported beside every nominal p. **[PROPOSED CHANGE]** Implement via the standard **Romano–Wolf stepdown / White reality-check** machinery and report a specification curve (Simonsohn et al.) rather than reinventing the correction.
**Rationale:** Skeleton §7 formula and §13 ("preserve the research path… because those define the multiple-search burden"); named implementations are the handover review's literature point.

### H3 — Mandatory leave-one-out and influence diagnostics?
**Response:** For **every headline statistic**, automatically: leave-one-country-out re-estimation (full sweep, results stored); influence diagnostics (Cook's distance / DFBETA-class); robust-regression and rank-statistic cross-checks. A result that dies under LOCO is reclassified, not footnoted.
**Rationale:** Skeleton §7 ("compute leave-one-country-out results automatically for every headline statistic") and §5 outlier row; H4's finance signal died exactly this way.

### H4 — Evidence threshold from exploratory to provisional?
**Response:** All of, per the grading table: reproducible from immutable raw data; survives LOCO and influence checks; **consistent in sign and rough magnitude across ≥2 independent provider measures**; acceptable search-adjusted significance (p_search, not nominal p); negative controls and placebos behave correctly; not attributable to a ratio artifact. **[PROPOSED CHANGE]** Plus: the design's pre-computed MDE must show the effect size is one the sample could plausibly detect — a "significant" estimate far above the MDE-implied plausible range is a red flag, not a promotion.
**Rationale:** Skeleton §10 Provisional row; the MDE gate is critique point 1.

## I. Source governance and validation

### I1 — Admissible sources for core regressions?
**Response:** **S01–S14 only, first-party retrieval only** (Microsoft, Anthropic, OpenAI, OpenRouter-as-robustness, Eurostat, IMF, ILO/ILOSTAT). S15 (World Bank GDP) is a supporting cross-check; S16 (WIPO software spending) and S17 (CountryETFTracker) are exploratory-only and can never enter a core regression.
**Rationale:** Skeleton §9 step 2 ("first-party sources only") and the source registry's use classes.

### I2 — Mandatory source metadata per downloaded file?
**Response:** The minimum retrieval record: official URL + source ID; retrieval UTC timestamp; publication/vintage date; local immutable filename; byte size; SHA-256; license; expected vs. observed title/fingerprint; expected vs. observed schema; the two reproduced published values; validation pass/fail and reviewer.
**Rationale:** Checklist page 10 and skeleton §8 manifest layer, merged verbatim.

### I3 — How is correct retrieval validated?
**Response:** Three gates, all blocking: (1) title + short fingerprint match (<25 quoted words; mismatch **blocks ingestion**); (2) schema/columns/units check; (3) reproduction of ≥2 values visibly published by the source (e.g., Microsoft Canada/Korea user shares; Eurostat EU sector growth). Results land in the manifest; a failed check stops downstream analysis.
**Rationale:** Skeleton §12.1 retrieval-validation protocol, unchanged.

### I4 — What happens on methodology change or historical revision?
**Response:** The new vintage is downloaded as a **new immutable raw file alongside the old** (never overwritten); the hash/vintage comparison flags the change; the pipeline re-runs on the new vintage; results are reported per vintage with a vintage-sensitivity note. Frozen confirmatory specs are evaluated on the vintage named at freeze time; a methodology break that invalidates a frozen spec is a versioned design decision, not a silent patch.
**Rationale:** Skeleton §5 measurement-revision row ("vintage every download; hashes; immutable raw; rerun on vintage updates") and §8's immutability rule.

## J. Reproducibility and confirmation

### J1 — How are exploration and confirmation separated in the repository?
**Response:** Physically and procedurally: `exploration/` (every run auto-logged to the search ledger) vs. `confirmatory/` (frozen, read-only specifications after outcome access; no model edits after seeing outcomes). Nothing found in exploration may be re-presented as out-of-sample confirmation on the same observations. **[PROPOSED CHANGE]** The freeze is additionally **registered externally** (OSF-style, timestamped spec hash) before 2027 data access — a read-only directory is self-attestation; registration is verifiable.
**Rationale:** Skeleton §6 and §8; the registration is critique point 6.

### J2 — What data is reserved as a genuine holdout?
**Response:** **Future data: the 2027–2028 releases** of the adoption and outcome sources. No re-splitting of historical data is ever labeled confirmation.
**Rationale:** Skeleton §6 "prospective advantage": formalizing in 2026 makes future vintages a true holdout, "much stronger than repeatedly re-splitting historical data". This is the project's single biggest credibility asset.

### J3 — How is every tested hypothesis recorded?
**Response:** In the **machine-readable search ledger**, one entry per run: specification ID, transformation/normalization, outcome, lag, sample, provider, result summary, date, and the confounder or lesson it produced — extending the H0–H7 five-column ledger (hypothesis, exploratory result, confounder/issue, next action). The ledger **is** the permutation family for H2.
**Rationale:** Skeleton §2 (canonical ledger), §8 exploration layer rule, §9 step 1.

### J4 — Automated tests that must pass before any regression runs?
**Response:** The §8.1 battery: unique country/date/sector keys; country-code concordance and geography exclusions; unit/scale checks; date alignment and **no-look-ahead assertions**; ≥2 published values reproduced per source; all dropped/missing observations reported with reasons; deterministic seeds; denominator sanity/nonzero constraints; source hash/vintage comparison on refresh. Any failure stops the pipeline.
**Rationale:** Skeleton §8.1, adopted as a blocking CI gate (§9 step 3's validation-first ordering).

## K. Interpretation and deliverables

### K1 — Preferred final output?
**Response:** **All three, fully generated:** an academic-style paper as the primary deliverable, the reproducible research notebook/pipeline as its substrate, and a dashboard as an optional view — under the `reports/` rule that **no numeric result is manually typed**; every table and figure regenerates from immutable raw data + code.
**Rationale:** Skeleton §8 reports layer and the end-state description (every result carries source lineage, spec ID, search context, validation status).

### K2 — How are null results reported?
**Response:** **With the same prominence as positive results** (skeleton §9 step 10), each null accompanied by its search-adjusted inference and — **[PROPOSED CHANGE]** — by the MDE/power context that says what the null does and does not rule out. "We found nothing" and "we could not have found anything this small" are different sentences; both get printed.
**Rationale:** Skeleton §9; the power context is critique point 1 and is what makes a null informative rather than merely honest.

### K3 — What result would cause abandoning the AI-productivity hypothesis?
**Response:** Pre-specified abandonment criteria, all holding jointly: (1) search-adjusted nulls across **both** core families (AIS × exposure; AIS × shock) at **every** pre-specified lag, on a design whose MDE covers the benchmark effect sizes from the adoption-gap literature; (2) exposed sectors indistinguishable from negative-control sectors; (3) no cross-provider consistency in any surviving sub-result; and finally (4) failure of the frozen hypotheses on the 2027–2028 prospective holdout. Short of (4), the verdict is "no detectable effect at this horizon and power", not "no effect".
**Rationale:** Composed from the skeleton's grading logic, dynamic statistics, and prospective design; the power qualifier is critique point 1. The skeleton's own priors (§11) already accept that simple level stories are likely dead — abandonment targets the mechanism-close forms.

### K4 — What result justifies the prospective 2027–2028 confirmation study?
**Response:** Any result reaching the **Provisional grade under the full H4 battery**: search-adjusted significance, LOCO-robust, consistent across ≥2 independent providers, correct placebo/negative-control behavior, mechanism-proximal outcome, and an economically meaningful magnitude when benchmarked against the external adoption-gap estimates (e.g., the ~3.2pp cumulative US–Europe differential scale from the industry-level literature). At most a **small number of frozen hypotheses** (skeleton: "a few") proceed; the freeze + external registration happens before any 2027 data is touched.
**Rationale:** Skeleton §9 steps 9–10, §10 Provisional→Strong transition; the external benchmark anchor is the handover review's calibration point. Note the asymmetry: the prospective study is also justified by a *well-powered near-miss*, since the holdout is the design's only path to a Strong grade either way.

---

## Sign-off gate

Per the checklist: the confirmatory specification must not freeze until A1–A4, C1–C5, D1–D5, E1–E5, H1–H4 and J1–J4 above are explicitly **approved** (this document is the proposal). Every future change to an answer becomes a versioned design decision in the ledger.
