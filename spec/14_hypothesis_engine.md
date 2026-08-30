# Quantitative Hypothesis Analysis Engine

> **Crate:** `src-rust/crates/hypothesis` (`cc-hypothesis`)
> **Tool:** `HypothesisAnalyze` in `cc-tools` (`hypothesis_tool.rs`)
> **Status:** implemented — deterministic core + agentic integration points

---

## 1. Purpose

Turn a **textual hypothesis** — a claimed fact, prediction, or observation —
into a **quantitative analysis** with precise, monitorable estimates:

- the **eligible universe** of companies the claim touches,
- each name's **revenue exposure** to the theme,
- the **idiosyncratic return response** to the theme's driver signal,
- **materiality** (bps of expected price impact per unit of driver move),
- a **confidence score with explicit trigger thresholds**, and
- a **horizon** (price-response days + fundamental realization quarters).

Hypotheses can come from news media, research reports, or **the output of a
previous analysis** — the report is structured JSON as well as markdown, so
one report's open questions can seed the next hypothesis (auto-research
chaining).

Two motivating examples, both bundled as deterministic demos:

1. *"Pharmaceutical companies that have solutions or would be first
   responders to today's known epidemic could outperform as sentiment toward
   the epidemic evolves."* (an "ebola-style" sentiment-catalyst report)
2. *"Apple's new Mac Studio will take a significant amount of Nvidia's
   consumer GPU sales."* (a substitution / share-shift report)

---

## 2. Position in the harness

```
                     agent loop (cc-query)
                            |
                    HypothesisAnalyze tool          <- cc-tools/hypothesis_tool.rs
                            |
   HypothesisInput ──normalize──> Hypothesis
                            |
                        Planner ──> AnalysisPlan    <- TemplatePlanner (deterministic)
                            |                          or an LLM-backed Planner
                    HypothesisEngine::analyze
                            |
        ┌──────────── DataHub trait ────────────┐   <- the "defined set of tools"
        |  screen | fundamentals | prices |     |
        |  benchmark | factors | signal         |
        └───────────────────────────────────────┘
             FileDataHub          MockDataHub
        (real feeds, offline)   (tests & demos)
                            |
                    HypothesisReport
              (markdown note + JSON + evidence ledger)
```

Division of labor:

- **`cc-hypothesis` is deterministic.** Same hub contents → same numbers.
  All statistics, screening, and report assembly live here.
- **The harness supplies the agentic layer.** The model (via the
  `HypothesisAnalyze` tool schema) normalizes the raw text into structured
  inputs — kind, keywords, driver signal, rotation sides — then interprets
  and narrates the returned report, and may chain follow-up runs.
- **`Planner` is the adaptivity hook.** `TemplatePlanner` maps hypothesis
  kind → step template; an LLM-backed implementation can reorder, drop, or
  parameterize steps per hypothesis without touching the engine.

---

## 3. Domain model (`types.rs`)

| Type | Role |
|---|---|
| `HypothesisInput` | Raw entry point: text + optional structure. Everything optional is filled by `normalize()` (keyword extraction fallback; an LLM should pre-fill in agentic use). |
| `Hypothesis` | Structured claim: kind, source, expected effect, driver spec, screening criteria, decomposed sub-claims. |
| `HypothesisSource` | `NewsMedia`, `Report`, `AnalysisOutput { report_id }` (chaining), `Manual`. |
| `HypothesisKind` | `SentimentCatalyst`, `Substitution`, `SupplyChain`, `Regulatory`, `MacroThematic`, `Custom`. Selects the plan template. |
| `ExpectedEffect` | `Positive`, `Negative`, or `Rotation { winner_keywords, loser_keywords }` for share-shift theses. |
| `DriverSpec` | The observable time series the thesis rides on (sentiment index, adoption proxy, case counts) — resolvable by the data hub via `signal_id`. |
| `ScreenCriteria` | Sectors, thematic keywords, force-included tickers, min market cap. |
| `SubClaim` | Individually testable decomposition; untestable claims flow into report caveats instead of silently disappearing. |

Design rule: **every hypothesis must name a driver signal**. A thesis without
an observable driver cannot produce sensitivities, thresholds, or a horizon —
it is narrative, not analysis. The driver is what makes the report monitorable.

---

## 4. The analysis pipeline (`plan.rs`, `engine.rs`)

### 4.1 Step vocabulary

`ScreenUniverse → LoadData → EstimateExposure → IdiosyncraticReturns →
DriverSensitivity → EventStudy → Synthesize → ConfidenceThresholds →
EstimateHorizon → RenderReport`

### 4.2 Sentiment-catalyst template (the canonical 7-step research plan)

Matches the original epidemic-pharma workflow one-to-one:

| User's step | Engine step(s) |
|---|---|
| 1. Find eligible companies | `ScreenUniverse` — keyword/sector screen over descriptions + segment tags |
| 2. Load fundamentals and returns | `LoadData` |
| 3. Estimate revenue exposure | `EstimateExposure` — theme-tagged segment revenue / TTM revenue |
| 4. Idiosyncratic returns | `IdiosyncraticReturns` — OLS residuals vs benchmark + factors |
| 5. Build the analysis | `DriverSensitivity` + `EventStudy` + `Synthesize` |
| 6. Confidence thresholds | `ConfidenceThresholds` |
| 7. Horizon | `EstimateHorizon` |

### 4.3 Substitution template (Apple Mac Studio vs. Nvidia consumer GPUs)

The steps the sentiment plan doesn't cover:

1. **Identify both sides** — the analysis is *relative*; winner and loser
   cohorts are screened separately via `Rotation` keyword lists.
2. **Revenue at risk / addressable gain** — for the loser, the substituted
   segment's share of revenue (e.g. Consumer GPU / total); for the winner,
   the same pool treated as an addressable gain.
3. **Relative idiosyncratic response** — a credible substitution shows
   *opposite-signed* driver betas: winner positive, loser negative. Same-signed
   betas mean the driver is proxying a common factor, and the thesis fails.
4. **Event study around milestones** — launches/adoption spikes are discrete;
   CAR around them separates narrative from actual repricing.
5. **Scenario the share shift** — materiality = segment revenue × assumed
   share loss × margin, mapped to bps of market cap *on each side*; the
   tradable expression is the pair spread, not either leg.
6. **Horizon** — price response from lead/lag; fundamental realization set to
   a product cycle (~4 quarters) rather than a sentiment cycle (~2).

### 4.4 Execution semantics

- Steps run in order; per-name data failures **degrade, not abort**: the name
  is carried with `Insufficient` verdict and a note, and the run continues.
- An empty screen is a hard error (`EmptyUniverse`) — the agent should widen
  criteria rather than receive an empty report.
- Every step writes to the **evidence ledger**: `(step_id, source,
  description, value)`. Every number in the rendered report traces to a ledger
  entry — the report is auditable by construction.

---

## 5. The data layer (`data.rs`) — the "defined set of tools"

The engine only ever talks to the `DataHub` trait:

```rust
trait DataHub {
    fn screen(&self, criteria: &ScreenCriteria) -> Result<Vec<CompanyRef>>;
    fn fundamentals(&self, ticker: &str) -> Result<FundamentalsSnapshot>;
    fn prices(&self, ticker: &str) -> Result<Series>;
    fn benchmark(&self) -> Result<Series>;
    fn factors(&self) -> Result<Vec<Series>>;      // optional style/sector factors
    fn signal(&self, id: &str) -> Result<Series>;  // driver series
}
```

Bundled implementations:

- **`FileDataHub`** — a directory the engine treats as ground truth:

  ```
  <root>/universe.json            [CompanyRef, ...]
  <root>/fundamentals/<T>.json    FundamentalsSnapshot (with tagged segments)
  <root>/prices/<T>.csv           date,value
  <root>/prices/BENCHMARK.csv
  <root>/factors/<name>.csv       optional
  <root>/signals/<id>.csv         driver series (sentiment, adoption, cases…)
  ```

  This is the integration point for real feeds: fetcher jobs (market data
  APIs, sentiment pipelines, web scrapes) *materialize files*; the engine
  stays offline and every run is reproducible from a data-directory snapshot.

- **`MockDataHub`** — deterministic synthetic universes (`pharma_demo`,
  `substitution_demo`) whose names have *known* true driver betas, so
  end-to-end tests assert the pipeline recovers ground truth (winner positive,
  loser negative, control excluded).

---

## 6. Statistical methodology (`stats.rs`)

All dependency-free (hand-rolled OLS via normal equations; factor counts are
tiny).

| Estimate | Method |
|---|---|
| Idiosyncratic returns | OLS of daily returns on benchmark (+ factor) returns; residual series keeps its dates for later alignment. |
| Driver sensitivity | OLS of residuals on the **z-scored day-over-day driver change** → β is *return per 1σ driver move*; t-stat gates significance (default \|t\| ≥ 2). |
| Event study | Driver spike days (Δ > 1.5σ) → mean cumulative abnormal return over a 5-day window, with a t-stat across events. Validates the regression on discrete episodes. |
| Materiality | `bps_per_sigma = β × 10⁴`; fundamental channel = exposed revenue / market cap. |
| Confidence | Composite: 0.5 × (share of assessed names that are Core) + 0.3 × (share with material exposure) + 0.2 × sample adequacy (min n/100). Levels: ≥0.70 High, ≥0.45 Medium, ≥0.25 Low, else Rejected. |
| Trigger thresholds | Driver mean/σ define regime lines: `driver > μ+σ` (thesis active), `driver < μ` (dormant), `daily Δ > 1.5σ` (event window opens). These make the report *monitorable*: a cron/routine can watch the signal and re-fire the analysis. |
| Price-response horizon | Lead/lag scan (±20d) of driver changes vs the composite idiosyncratic return of Core names; best positive lag = days from driver move to price response. |
| Thesis shelf life | AR(1) half-life of the driver series — how long an excursion persists. |
| Fundamental horizon | Kind-based prior: ~2 quarters (sentiment), ~4 (substitution / product cycle), ~3 otherwise — until real guidance/estimate data is wired in. |

### Name verdicts

|  | Significant driver response (sign-correct) | Not significant |
|---|---|---|
| **Material exposure (≥10 % rev)** | `Core` | `Peripheral` |
| **Immaterial** | `Peripheral` | `Unsupported` |

Missing data → `Insufficient`. Thesis `supported` ⇔ at least one Core name.
Aggregate materiality = cap-weighted `bps_per_sigma` over Core names.

---

## 7. The report (`report.rs`)

`HypothesisReport` is both the deliverable and a chainable artifact:

- **Markdown** (`to_markdown()`): verdict box, methodology (from the plan's
  rationales), universe table, per-name detail, key findings, confidence &
  trigger table, horizon, sub-claim status, evidence appendix.
- **JSON** (serde): the full structure — feed `report_id` back as
  `HypothesisSource::AnalysisOutput` to chain follow-up hypotheses; feed
  `confidence.thresholds` to a monitoring routine.

Non-testable sub-claims are carried as explicit caveats ("Untested
assumption: …") — the report never silently absorbs narrative claims.

---

## 8. Agentic workflow (how the harness uses it)

1. **Intake** — a hypothesis arrives from a news item, a report, a user, or a
   previous run's open question.
2. **Normalize (LLM)** — the model chooses `kind`, screening keywords, the
   driver `signal_id`, and, for substitutions, winner/loser keyword lists;
   it may first use Web/search tools to ground the entity set.
3. **Analyze (deterministic)** — call `HypothesisAnalyze`; the engine runs
   the plan against the configured data hub (`data_dir` for real data).
4. **Interpret (LLM)** — narrate the report, flag weak links (low-t names,
   untested sub-claims), decide whether to widen the screen or refine the
   driver and re-run.
5. **Monitor** — register the report's trigger thresholds with the harness's
   cron/routine system; when the driver crosses a line, re-fire the analysis
   and diff against the prior report.
6. **Chain** — open questions become new `HypothesisInput`s with
   `source = AnalysisOutput { report_id }`.

Failure modes the tool surfaces for the agent: `EmptyUniverse` → widen
criteria; missing signal file → fetch/derive the driver series first; low
confidence with material exposure → the thesis is fundamental-only; low
exposure with strong response → the driver is proxying something else.

---

## 9. Extension roadmap

- **Real feeds**: fetcher jobs writing the `FileDataHub` layout (prices,
  segment fundamentals, sentiment series from news embedding pipelines).
- **LLM planner**: implement `Planner` against `cc-api` to specialize plans
  per hypothesis (e.g. add peer-relative screens, skip event study on short
  samples).
- **Backtesting**: walk-forward re-estimation of sensitivities to produce
  out-of-sample confidence instead of in-sample t-stats.
- **Sizing**: map `bps_per_sigma` and confidence into position sizing /
  Kelly-fraction suggestions.
- **Estimate data**: replace the kind-based fundamental horizon prior with
  consensus-revision lead times.

---

## 10. Verification

```
cargo test -p cc-hypothesis      # 15 tests: stats, data, plan, 2 e2e pipelines
cargo test -p cc-tools           # tool registration + execution tests
cargo run -p cc-hypothesis --example demo                  # epidemic-pharma report
cargo run -p cc-hypothesis --example demo -- substitution  # Mac Studio vs GPU report
```

The e2e tests assert ground-truth recovery on the mock hubs: exposed names
come out `Core`, controls are excluded, and substitution betas come out
opposite-signed (winner +, loser −).
