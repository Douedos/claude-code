// The hypothesis engine: executes an analysis plan step by step against a
// `DataHub`, accumulating evidence, and produces a `HypothesisReport`.
//
// The engine is deliberately synchronous and deterministic: given the same
// hub contents it always produces the same numbers. Agentic behavior
// (adaptive planning, narrative interpretation) belongs to the harness layer
// that wraps it — see the `Planner` trait and spec/14_hypothesis_engine.md.

use crate::data::{DataHub, FundamentalsSnapshot, Series};
use crate::error::{HypothesisError, Result};
use crate::plan::{Planner, StepKind, TemplatePlanner};
use crate::report::*;
use crate::stats;
use crate::types::{ExpectedEffect, Hypothesis, HypothesisInput, HypothesisKind};
use chrono::NaiveDate;
use serde_json::json;
use std::collections::BTreeMap;
use std::sync::Arc;

/// Thresholds that classify a name as materially exposed / statistically
/// responsive. Tunable per engine instance.
#[derive(Debug, Clone)]
pub struct EngineConfig {
    /// Minimum revenue exposure to count as material (fraction of TTM).
    pub min_exposure: f64,
    /// Minimum |t| for the driver beta to count as significant.
    pub min_t_stat: f64,
    /// Event-study window in trading days.
    pub event_window: usize,
    /// Driver spike threshold in standard deviations.
    pub spike_z: f64,
    /// Maximum lead/lag searched when estimating horizon (days).
    pub max_lag: usize,
}

impl Default for EngineConfig {
    fn default() -> Self {
        Self {
            min_exposure: 0.10,
            min_t_stat: 2.0,
            event_window: 5,
            spike_z: 1.5,
            max_lag: 20,
        }
    }
}

pub struct HypothesisEngine {
    hub: Arc<dyn DataHub>,
    planner: Box<dyn Planner>,
    config: EngineConfig,
}

/// Per-company intermediate state carried between steps.
struct NameState {
    company: crate::data::CompanyRef,
    fundamentals: Option<FundamentalsSnapshot>,
    /// Idiosyncratic (residual) return series, dated.
    residuals: Option<Series>,
    exposure: Option<ExposureEstimate>,
    sensitivity: Option<SensitivityEstimate>,
    /// Which side of a rotation the name sits on: +1 winner, -1 loser, 0 n/a.
    side: i8,
    notes: Vec<String>,
}

impl HypothesisEngine {
    pub fn new(hub: Arc<dyn DataHub>) -> Self {
        Self {
            hub,
            planner: Box::new(TemplatePlanner),
            config: EngineConfig::default(),
        }
    }

    pub fn with_planner(mut self, planner: Box<dyn Planner>) -> Self {
        self.planner = planner;
        self
    }

    pub fn with_config(mut self, config: EngineConfig) -> Self {
        self.config = config;
        self
    }

    /// Run the full pipeline on a raw hypothesis input.
    pub fn analyze(&self, input: HypothesisInput) -> Result<HypothesisReport> {
        let hypothesis = input.normalize();
        let plan = self.planner.plan(&hypothesis);
        let mut ledger = EvidenceLedger::default();

        let step_id = |kind: StepKind| -> String {
            plan.steps
                .iter()
                .find(|s| s.kind == kind)
                .map(|s| s.id.clone())
                .unwrap_or_else(|| "S?".to_string())
        };

        // -- Screen -------------------------------------------------------
        let sid = step_id(StepKind::ScreenUniverse);
        let universe = self.hub.screen(&hypothesis.criteria)?;
        ledger.record(
            &sid,
            "DataHub::screen",
            format!(
                "Screened universe with keywords {:?}: {} eligible companies ({})",
                hypothesis.criteria.keywords,
                universe.len(),
                universe
                    .iter()
                    .map(|c| c.ticker.as_str())
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            json!({ "tickers": universe.iter().map(|c| &c.ticker).collect::<Vec<_>>() }),
        );
        if universe.is_empty() {
            return Err(HypothesisError::EmptyUniverse(format!(
                "criteria: keywords {:?}, sectors {:?}",
                hypothesis.criteria.keywords, hypothesis.criteria.sectors
            )));
        }

        let mut names: Vec<NameState> = universe
            .into_iter()
            .map(|company| NameState {
                side: rotation_side(&hypothesis, &company),
                company,
                fundamentals: None,
                residuals: None,
                exposure: None,
                sensitivity: None,
                notes: Vec::new(),
            })
            .collect();

        // -- Load data ----------------------------------------------------
        let sid = step_id(StepKind::LoadData);
        let benchmark = self.hub.benchmark()?.simple_returns();
        let factors: Vec<Series> = self
            .hub
            .factors()?
            .into_iter()
            .map(|f| f.simple_returns())
            .collect();
        let driver = self.hub.signal(&hypothesis.driver.signal_id)?;
        ledger.record(
            &sid,
            "DataHub",
            format!(
                "Loaded benchmark ({} obs), {} factor series, driver signal '{}' ({} obs)",
                benchmark.len(),
                factors.len(),
                driver.id,
                driver.len()
            ),
            json!({ "driver_obs": driver.len(), "factors": factors.len() }),
        );
        for state in &mut names {
            match self.hub.fundamentals(&state.company.ticker) {
                Ok(f) => state.fundamentals = Some(f),
                Err(e) => state.notes.push(format!("fundamentals unavailable: {e}")),
            }
        }

        // -- Exposure -----------------------------------------------------
        let sid = step_id(StepKind::EstimateExposure);
        for state in &mut names {
            let Some(f) = &state.fundamentals else { continue };
            let keywords = exposure_keywords(&hypothesis, state.side);
            let mut exposed = 0.0;
            let mut matched = Vec::new();
            for seg in &f.segments {
                let hay = format!(
                    "{} {}",
                    seg.name.to_lowercase(),
                    seg.tags.join(" ").to_lowercase()
                );
                if keywords.iter().any(|k| hay.contains(&k.to_lowercase())) {
                    exposed += seg.revenue;
                    matched.push(seg.name.clone());
                }
            }
            let exposure = if f.revenue_ttm > 0.0 {
                exposed / f.revenue_ttm
            } else {
                0.0
            };
            ledger.record(
                &sid,
                "DataHub::fundamentals",
                format!(
                    "{}: {:.1}% of revenue in theme segments [{}]",
                    state.company.ticker,
                    exposure * 100.0,
                    matched.join(", ")
                ),
                json!({ "ticker": state.company.ticker, "exposure": exposure }),
            );
            state.exposure = Some(ExposureEstimate {
                revenue_exposure: exposure,
                exposed_revenue: exposed,
                matched_segments: matched,
            });
        }

        // -- Idiosyncratic returns ---------------------------------------
        let sid = step_id(StepKind::IdiosyncraticReturns);
        for state in &mut names {
            match self.hub.prices(&state.company.ticker) {
                Ok(prices) => {
                    let rets = prices.simple_returns();
                    match idiosyncratic_returns(&rets, &benchmark, &factors) {
                        Some((residuals, market_beta, r2)) => {
                            ledger.record(
                                &sid,
                                "factor_model",
                                format!(
                                    "{}: market beta {:.2}, factor-model R² {:.2}, {} residual obs",
                                    state.company.ticker,
                                    market_beta,
                                    r2,
                                    residuals.len()
                                ),
                                json!({ "ticker": state.company.ticker, "beta": market_beta, "r2": r2 }),
                            );
                            state.residuals = Some(residuals);
                        }
                        None => state
                            .notes
                            .push("factor regression degenerate; name excluded from stats".into()),
                    }
                }
                Err(e) => state.notes.push(format!("prices unavailable: {e}")),
            }
        }

        // -- Driver sensitivity + event study ----------------------------
        let sid_sens = step_id(StepKind::DriverSensitivity);
        let sid_es = step_id(StepKind::EventStudy);
        let driver_diffs = driver.diffs();
        let dd_std = stats::std_dev(&driver_diffs.values).max(f64::EPSILON);
        let driver_z = Series {
            id: driver_diffs.id.clone(),
            dates: driver_diffs.dates.clone(),
            values: driver_diffs.values.iter().map(|v| v / dd_std).collect(),
        };
        for state in &mut names {
            let Some(res) = &state.residuals else { continue };
            let (r, d) = res.align(&driver_z);
            let Some(fit) = stats::ols(&r, &[d]) else {
                state.notes.push("driver regression degenerate".into());
                continue;
            };
            let driver_beta = fit.coefs[1];
            let t_stat = fit.t_stats[1];
            ledger.record(
                &sid_sens,
                "driver_regression",
                format!(
                    "{}: residual return {:.1} bps per 1σ driver move (t = {:.2}, n = {})",
                    state.company.ticker,
                    driver_beta * 1.0e4,
                    t_stat,
                    fit.n_obs
                ),
                json!({ "ticker": state.company.ticker, "beta": driver_beta, "t": t_stat }),
            );

            // Event study around driver spikes, on the aligned residuals.
            let (res_aligned, drv_aligned) = res.align(&driver);
            let spikes = stats::spike_indices(&drv_aligned, self.config.spike_z);
            let es = stats::event_study(&res_aligned, &spikes, self.config.event_window);
            if let Some(es) = &es {
                ledger.record(
                    &sid_es,
                    "event_study",
                    format!(
                        "{}: mean {:.0} bps CAR over {} days after {} driver spikes (t = {:.2})",
                        state.company.ticker,
                        es.mean_car * 1.0e4,
                        es.window,
                        es.n_events,
                        es.t_stat
                    ),
                    json!({ "ticker": state.company.ticker, "car": es.mean_car, "t": es.t_stat }),
                );
            }
            state.sensitivity = Some(SensitivityEstimate {
                driver_beta,
                t_stat,
                r_squared: fit.r_squared,
                event_car: es.as_ref().map(|e| e.mean_car),
                event_t_stat: es.as_ref().map(|e| e.t_stat),
                n_obs: fit.n_obs,
            });
        }

        // -- Synthesize ---------------------------------------------------
        let sid = step_id(StepKind::Synthesize);
        let mut assessments: Vec<CompanyAssessment> = Vec::new();
        for state in names {
            let market_cap = state
                .fundamentals
                .as_ref()
                .map(|f| f.market_cap)
                .unwrap_or(0.0);
            let expected_sign = expected_sign(&hypothesis.effect, state.side);
            let materiality = state.sensitivity.as_ref().map(|s| MaterialityEstimate {
                bps_per_sigma: s.driver_beta * 1.0e4,
                revenue_at_stake_pct_mcap: state
                    .exposure
                    .as_ref()
                    .map(|e| {
                        if market_cap > 0.0 {
                            e.exposed_revenue / market_cap
                        } else {
                            0.0
                        }
                    })
                    .unwrap_or(0.0),
            });
            let has_exposure = state
                .exposure
                .as_ref()
                .map(|e| e.revenue_exposure >= self.config.min_exposure)
                .unwrap_or(false);
            let has_response = state
                .sensitivity
                .as_ref()
                .map(|s| {
                    s.t_stat.abs() >= self.config.min_t_stat
                        && (expected_sign == 0.0 || s.driver_beta * expected_sign > 0.0)
                })
                .unwrap_or(false);
            let verdict = match (&state.exposure, &state.sensitivity) {
                (None, None) => NameVerdict::Insufficient,
                _ if has_exposure && has_response => NameVerdict::Core,
                _ if has_exposure || has_response => NameVerdict::Peripheral,
                _ => NameVerdict::Unsupported,
            };
            ledger.record(
                &sid,
                "synthesis",
                format!("{}: verdict {:?}", state.company.ticker, verdict),
                json!({ "ticker": state.company.ticker }),
            );
            assessments.push(CompanyAssessment {
                company: state.company,
                market_cap,
                exposure: state.exposure,
                sensitivity: state.sensitivity,
                materiality,
                verdict,
                notes: state.notes,
            });
        }

        let core: Vec<&CompanyAssessment> = assessments
            .iter()
            .filter(|a| a.verdict == NameVerdict::Core)
            .collect();
        let peripheral: Vec<&CompanyAssessment> = assessments
            .iter()
            .filter(|a| a.verdict == NameVerdict::Peripheral)
            .collect();
        let total_cap: f64 = core.iter().map(|a| a.market_cap).sum();
        let aggregate_bps = if total_cap > 0.0 {
            core.iter()
                .map(|a| {
                    a.materiality.as_ref().map(|m| m.bps_per_sigma).unwrap_or(0.0) * a.market_cap
                })
                .sum::<f64>()
                / total_cap
        } else {
            0.0
        };

        let mut key_findings = Vec::new();
        key_findings.push(format!(
            "{} of {} screened names show both material revenue exposure (≥{:.0}%) and a significant driver response (|t| ≥ {:.1}).",
            core.len(),
            assessments.len(),
            self.config.min_exposure * 100.0,
            self.config.min_t_stat
        ));
        if let Some(best) = core.iter().max_by(|a, b| {
            let ma = a.materiality.as_ref().map(|m| m.bps_per_sigma.abs()).unwrap_or(0.0);
            let mb = b.materiality.as_ref().map(|m| m.bps_per_sigma.abs()).unwrap_or(0.0);
            ma.partial_cmp(&mb).unwrap_or(std::cmp::Ordering::Equal)
        }) {
            key_findings.push(format!(
                "Highest-conviction name: {} ({:.0} bps expected move per 1σ driver change).",
                best.company.ticker,
                best.materiality.as_ref().map(|m| m.bps_per_sigma).unwrap_or(0.0)
            ));
        }
        if matches!(hypothesis.effect, ExpectedEffect::Rotation { .. }) {
            let winners: Vec<&&CompanyAssessment> =
                core.iter().filter(|a| rotation_side(&hypothesis, &a.company) > 0).collect();
            let losers: Vec<&&CompanyAssessment> =
                core.iter().filter(|a| rotation_side(&hypothesis, &a.company) < 0).collect();
            key_findings.push(format!(
                "Rotation structure: {} winner-side and {} loser-side names confirmed; the tradable expression is the pair spread, not either leg alone.",
                winners.len(),
                losers.len()
            ));
        }

        // -- Confidence ---------------------------------------------------
        let sid = step_id(StepKind::ConfidenceThresholds);
        let assessed: Vec<&CompanyAssessment> = assessments
            .iter()
            .filter(|a| a.verdict != NameVerdict::Insufficient)
            .collect();
        let n_assessed = assessed.len().max(1) as f64;
        let stat_support = core.len() as f64 / n_assessed;
        let exposure_support = assessed
            .iter()
            .filter(|a| {
                a.exposure
                    .as_ref()
                    .map(|e| e.revenue_exposure >= self.config.min_exposure)
                    .unwrap_or(false)
            })
            .count() as f64
            / n_assessed;
        let min_obs = assessed
            .iter()
            .filter_map(|a| a.sensitivity.as_ref().map(|s| s.n_obs))
            .min()
            .unwrap_or(0);
        let sample_adequacy = (min_obs as f64 / 100.0).min(1.0);
        let score =
            (0.5 * stat_support + 0.3 * exposure_support + 0.2 * sample_adequacy).clamp(0.0, 1.0);
        let level = if score >= 0.70 {
            ConfidenceLevel::High
        } else if score >= 0.45 {
            ConfidenceLevel::Medium
        } else if score >= 0.25 {
            ConfidenceLevel::Low
        } else {
            ConfidenceLevel::Rejected
        };
        let d_mean = stats::mean(&driver.values);
        let d_std = stats::std_dev(&driver.values);
        let thresholds = vec![
            TriggerThreshold {
                signal: driver.id.clone(),
                comparator: ">".into(),
                value: d_mean + d_std,
                meaning: "Driver one σ above its mean: historical regime in which core names repriced; thesis active.".into(),
            },
            TriggerThreshold {
                signal: driver.id.clone(),
                comparator: "<".into(),
                value: d_mean,
                meaning: "Driver back at/below mean: thesis dormant, expected edge decays toward zero.".into(),
            },
            TriggerThreshold {
                signal: format!("{}_zchange", driver.id),
                comparator: ">".into(),
                value: self.config.spike_z,
                meaning: format!(
                    "A daily driver spike above {:.1}σ historically preceded a ~{}-day abnormal-return window (see event study).",
                    self.config.spike_z, self.config.event_window
                ),
            },
        ];
        let mut caveats: Vec<String> = hypothesis
            .sub_claims
            .iter()
            .filter(|sc| !sc.testable)
            .map(|sc| format!("Untested assumption: {}", sc.statement))
            .collect();
        caveats.push(
            "Sensitivities are historical; a structural break in the driver's meaning invalidates them.".into(),
        );
        ledger.record(
            &sid,
            "confidence",
            format!(
                "Composite confidence {:.2}: stat support {:.2}, exposure support {:.2}, sample adequacy {:.2}",
                score, stat_support, exposure_support, sample_adequacy
            ),
            json!({ "score": score }),
        );

        // -- Horizon ------------------------------------------------------
        let sid = step_id(StepKind::EstimateHorizon);
        let horizon = self.estimate_horizon(&sid, &hypothesis, &assessments, &driver, &driver_z, &mut ledger);

        let supported = !core.is_empty();
        let core_names: Vec<String> = core.iter().map(|a| a.company.ticker.clone()).collect();
        let peripheral_names: Vec<String> =
            peripheral.iter().map(|a| a.company.ticker.clone()).collect();
        drop(core);
        drop(peripheral);
        let report = HypothesisReport {
            report_id: uuid::Uuid::new_v4().to_string(),
            plan,
            companies: assessments,
            thesis: ThesisSummary {
                supported,
                core_names,
                peripheral_names,
                aggregate_bps_per_sigma: aggregate_bps,
                key_findings,
            },
            confidence: ConfidenceAssessment {
                score,
                level,
                thresholds,
                caveats,
            },
            horizon,
            evidence: ledger,
            hypothesis,
            generated_at: chrono::Utc::now(),
        };
        Ok(report)
    }

    fn estimate_horizon(
        &self,
        step_id: &str,
        hypothesis: &Hypothesis,
        assessments: &[CompanyAssessment],
        driver: &Series,
        driver_z: &Series,
        ledger: &mut EvidenceLedger,
    ) -> HorizonEstimate {
        // Average residuals of core names into one composite series, then
        // find the lag at which the driver best explains it.
        let core_tickers: Vec<&str> = assessments
            .iter()
            .filter(|a| a.verdict == NameVerdict::Core)
            .map(|a| a.company.ticker.as_str())
            .collect();
        let mut composite: BTreeMap<NaiveDate, (f64, u32)> = BTreeMap::new();
        for t in &core_tickers {
            if let Ok(prices) = self.hub.prices(t) {
                if let Ok(bench) = self.hub.benchmark() {
                    let rets = prices.simple_returns();
                    let bench_rets = bench.simple_returns();
                    if let Some((res, _, _)) = idiosyncratic_returns(&rets, &bench_rets, &[]) {
                        for (d, v) in res.dates.iter().zip(res.values.iter()) {
                            let e = composite.entry(*d).or_insert((0.0, 0));
                            e.0 += v;
                            e.1 += 1;
                        }
                    }
                }
            }
        }
        let composite = Series::new(
            "core_composite_residual",
            composite
                .into_iter()
                .map(|(d, (s, n))| (d, s / n as f64))
                .collect(),
        );

        let price_response_days = if composite.len() > 30 {
            let (d, r) = driver_z.align(&composite);
            stats::best_lag(&d, &r, self.config.max_lag)
                .filter(|(lag, corr)| *lag >= 0 && corr.abs() > 0.05)
                .map(|(lag, _)| (lag as f64).max(1.0))
        } else {
            None
        };
        let driver_half_life_days = stats::half_life(&driver.values);
        let fundamental_realization_quarters = match hypothesis.kind {
            HypothesisKind::Substitution => Some(4),
            HypothesisKind::SentimentCatalyst => Some(2),
            _ => Some(3),
        };
        let basis = format!(
            "Price-response horizon from the lead/lag of the driver against the cap-weighted idiosyncratic return of core names ({}); driver half-life {} from an AR(1) fit measures how long a driver excursion persists (thesis shelf life); fundamental realization assumes {} reporting cycle(s) before the revenue channel is visible in prints.",
            price_response_days
                .map(|d| format!("best lag ~{d:.0} trading days"))
                .unwrap_or_else(|| "not estimable from the sample".into()),
            driver_half_life_days
                .map(|h| format!("~{h:.0} days"))
                .unwrap_or_else(|| "not estimable".into()),
            fundamental_realization_quarters.unwrap_or(0),
        );
        ledger.record(
            step_id,
            "horizon",
            basis.clone(),
            json!({
                "price_response_days": price_response_days,
                "driver_half_life_days": driver_half_life_days,
            }),
        );
        HorizonEstimate {
            price_response_days,
            driver_half_life_days,
            fundamental_realization_quarters,
            basis,
        }
    }
}

/// Which side of a rotation a company sits on, from the effect's keyword
/// lists: +1 winner, -1 loser, 0 not a rotation / unmatched.
fn rotation_side(hypothesis: &Hypothesis, company: &crate::data::CompanyRef) -> i8 {
    let ExpectedEffect::Rotation {
        winner_keywords,
        loser_keywords,
    } = &hypothesis.effect
    else {
        return 0;
    };
    let hay = format!(
        "{} {}",
        company.name.to_lowercase(),
        company.description.to_lowercase()
    );
    let hit = |kws: &[String]| kws.iter().any(|k| hay.contains(&k.to_lowercase()));
    match (hit(winner_keywords), hit(loser_keywords)) {
        (true, false) => 1,
        (false, true) => -1,
        _ => 0,
    }
}

/// Keywords used for segment matching: side-specific for rotations,
/// otherwise the screening keywords.
fn exposure_keywords(hypothesis: &Hypothesis, side: i8) -> Vec<String> {
    if let ExpectedEffect::Rotation {
        winner_keywords,
        loser_keywords,
    } = &hypothesis.effect
    {
        match side {
            1 => return winner_keywords.clone(),
            -1 => return loser_keywords.clone(),
            _ => {}
        }
    }
    hypothesis.criteria.keywords.clone()
}

/// Expected sign of the driver beta for a name, from the hypothesized effect.
fn expected_sign(effect: &ExpectedEffect, side: i8) -> f64 {
    match effect {
        ExpectedEffect::Positive => 1.0,
        ExpectedEffect::Negative => -1.0,
        ExpectedEffect::Rotation { .. } => side as f64,
    }
}

/// Regress a name's returns on benchmark (+ factors); return the dated
/// residual series, the market beta, and the model R².
fn idiosyncratic_returns(
    returns: &Series,
    benchmark_returns: &Series,
    factor_returns: &[Series],
) -> Option<(Series, f64, f64)> {
    // Align all series on common dates.
    let mut dates: Vec<NaiveDate> = returns.dates.clone();
    let keep = |dates: &[NaiveDate], s: &Series| -> Vec<NaiveDate> {
        let set: std::collections::BTreeSet<NaiveDate> = s.dates.iter().cloned().collect();
        dates.iter().filter(|d| set.contains(d)).cloned().collect()
    };
    dates = keep(&dates, benchmark_returns);
    for f in factor_returns {
        dates = keep(&dates, f);
    }
    if dates.len() < 30 {
        return None;
    }
    let extract = |s: &Series| -> Vec<f64> {
        let map: BTreeMap<NaiveDate, f64> = s
            .dates
            .iter()
            .cloned()
            .zip(s.values.iter().cloned())
            .collect();
        dates.iter().map(|d| map[d]).collect()
    };
    let y = extract(returns);
    let mut xs = vec![extract(benchmark_returns)];
    for f in factor_returns {
        xs.push(extract(f));
    }
    let fit = stats::ols(&y, &xs)?;
    let residuals = Series::new(
        format!("{}_idio", returns.id),
        dates.into_iter().zip(fit.residuals.iter().cloned()).collect(),
    );
    Some((residuals, fit.coefs[1], fit.r_squared))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::data::MockDataHub;

    #[test]
    fn pharma_pipeline_end_to_end() {
        let hub = Arc::new(MockDataHub::pharma_demo());
        let mut input = HypothesisInput::new(
            "Pharmaceutical companies that have solutions or would be first responders to today's known epidemic could outperform as sentiment toward the epidemic evolves",
        );
        input.kind = Some(HypothesisKind::SentimentCatalyst);
        input.keywords = vec!["epidemic".into(), "vaccine".into(), "antiviral".into()];
        input.driver_signal_id = Some("epidemic_sentiment".into());

        let report = HypothesisEngine::new(hub).analyze(input).unwrap();

        // The truly exposed names must come out as core, the control must not.
        assert!(report.thesis.core_names.contains(&"VAXA".to_string()));
        assert!(report.thesis.core_names.contains(&"CURX".to_string()));
        assert!(!report.thesis.core_names.contains(&"GENC".to_string()));
        assert!(report.thesis.supported);
        assert!(report.thesis.aggregate_bps_per_sigma > 0.0);
        assert!(!report.confidence.thresholds.is_empty());
        assert!(!report.evidence.entries.is_empty());

        let md = report.to_markdown();
        assert!(md.contains("## Verdict"));
        assert!(md.contains("VAXA"));
        assert!(md.contains("Evidence appendix"));
    }

    #[test]
    fn substitution_pipeline_detects_rotation() {
        let hub = Arc::new(MockDataHub::substitution_demo());
        let mut input = HypothesisInput::new(
            "Apple's new Mac Studio will take a significant amount of Nvidia's consumer GPU sales",
        );
        input.kind = Some(HypothesisKind::Substitution);
        input.keywords = vec!["workstation".into(), "gpu".into()];
        input.effect = Some(ExpectedEffect::Rotation {
            winner_keywords: vec!["workstation".into(), "mac studio".into()],
            loser_keywords: vec!["gpu".into()],
        });
        input.driver_signal_id = Some("mac_studio_adoption".into());

        let report = HypothesisEngine::new(hub).analyze(input).unwrap();

        // Winner has positive beta, loser negative.
        let beta = |t: &str| {
            report
                .companies
                .iter()
                .find(|c| c.company.ticker == t)
                .and_then(|c| c.sensitivity.as_ref())
                .map(|s| s.driver_beta)
                .unwrap()
        };
        assert!(beta("APLW") > 0.0, "winner beta should be positive");
        assert!(beta("NVDL") < 0.0, "loser beta should be negative");
        assert!(report
            .companies
            .iter()
            .all(|c| c.company.ticker != "CTRL" || c.verdict != NameVerdict::Core));
        assert_eq!(
            report.horizon.fundamental_realization_quarters,
            Some(4),
            "substitution theses realize over a product cycle"
        );
    }

    #[test]
    fn empty_universe_is_an_error() {
        let hub = Arc::new(MockDataHub::pharma_demo());
        let mut input = HypothesisInput::new("nothing matches this");
        input.keywords = vec!["zzz_no_such_theme".into()];
        let err = HypothesisEngine::new(hub).analyze(input).unwrap_err();
        assert!(matches!(err, HypothesisError::EmptyUniverse(_)));
    }
}
