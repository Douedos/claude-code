// Analysis planning: how a structured hypothesis becomes an ordered list of
// executable steps.
//
// The `Planner` trait is the agentic integration point: the bundled
// `TemplatePlanner` is deterministic (kind -> step template), while a
// harness can supply an LLM-backed planner that proposes/refines plans from
// the hypothesis text and available data hub capabilities.

use crate::types::{Hypothesis, HypothesisKind};
use serde::{Deserialize, Serialize};

/// The vocabulary of executable analysis steps.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StepKind {
    /// Screen the universe for eligible companies.
    ScreenUniverse,
    /// Load fundamentals and price/return history for the universe.
    LoadData,
    /// Estimate each company's revenue exposure to the theme.
    EstimateExposure,
    /// Strip market/factor betas to get idiosyncratic return series.
    IdiosyncraticReturns,
    /// Regress idiosyncratic returns on the driver signal.
    DriverSensitivity,
    /// Event study of abnormal returns around driver spikes.
    EventStudy,
    /// Combine exposure and sensitivity into per-name and thesis-level
    /// materiality estimates.
    Synthesize,
    /// Derive the confidence score and actionable signal thresholds.
    ConfidenceThresholds,
    /// Estimate price-response and fundamental-realization horizons.
    EstimateHorizon,
    /// Render the final report.
    RenderReport,
}

/// One planned step with its rationale (rationales flow into the report's
/// methodology section).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanStep {
    pub id: String,
    pub kind: StepKind,
    pub title: String,
    pub rationale: String,
}

/// An ordered analysis plan for one hypothesis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalysisPlan {
    pub hypothesis_id: String,
    pub steps: Vec<PlanStep>,
}

/// Planning strategy. Implement this against an LLM (via the harness's API
/// crate) to make planning adaptive; `TemplatePlanner` is the deterministic
/// default.
pub trait Planner: Send + Sync {
    fn plan(&self, hypothesis: &Hypothesis) -> AnalysisPlan;
}

/// Deterministic planner: each hypothesis kind maps to a step template.
#[derive(Debug, Default)]
pub struct TemplatePlanner;

impl Planner for TemplatePlanner {
    fn plan(&self, hypothesis: &Hypothesis) -> AnalysisPlan {
        let steps: Vec<(StepKind, &str, &str)> = match hypothesis.kind {
            HypothesisKind::Substitution => vec![
                (
                    StepKind::ScreenUniverse,
                    "Identify both sides of the substitution",
                    "Winner and loser cohorts are screened from the criteria keywords; the analysis is relative, so both sides are needed.",
                ),
                (
                    StepKind::LoadData,
                    "Load fundamentals and returns",
                    "Segment-level revenue locates the substituted product line; return history feeds the factor model.",
                ),
                (
                    StepKind::EstimateExposure,
                    "Estimate revenue at risk / addressable gain",
                    "For the loser, the substituted segment's share of revenue; for the winner, the same pool as an addressable gain.",
                ),
                (
                    StepKind::IdiosyncraticReturns,
                    "Compute idiosyncratic returns",
                    "Both names share market/sector beta; the substitution effect must show up in residuals to be attributable.",
                ),
                (
                    StepKind::DriverSensitivity,
                    "Regress residuals on the adoption driver",
                    "A credible substitution shows opposite-signed sensitivities: winner positive, loser negative.",
                ),
                (
                    StepKind::EventStudy,
                    "Event study around driver milestones",
                    "Product launches / adoption spikes are discrete events; CAR around them separates narrative from repricing.",
                ),
                (
                    StepKind::Synthesize,
                    "Scenario the share shift",
                    "Materiality = segment revenue x assumed share loss x margin, mapped to bps of market cap on each side.",
                ),
                (
                    StepKind::ConfidenceThresholds,
                    "Score confidence and set driver thresholds",
                    "Confidence needs both statistical response and material exposure; thresholds define what driver reading would confirm the thesis.",
                ),
                (
                    StepKind::EstimateHorizon,
                    "Estimate horizon",
                    "Price response horizon from lead/lag of residuals vs driver; fundamental horizon from product-cycle length.",
                ),
                (StepKind::RenderReport, "Render report", "Deliverable."),
            ],
            // SentimentCatalyst and the remaining kinds share the canonical
            // 7-step research plan (screen -> load -> exposure -> idio ->
            // analysis -> confidence -> horizon), plus the report step.
            _ => vec![
                (
                    StepKind::ScreenUniverse,
                    "Find eligible companies",
                    "Screen for names matching the thesis criteria (sector, thematic keywords, explicit tickers).",
                ),
                (
                    StepKind::LoadData,
                    "Load fundamentals and returns",
                    "Fundamentals ground the exposure estimate; return history feeds the factor model.",
                ),
                (
                    StepKind::EstimateExposure,
                    "Estimate revenue exposure",
                    "Share of each company's revenue in segments tagged to the theme: the fundamental channel of the thesis.",
                ),
                (
                    StepKind::IdiosyncraticReturns,
                    "Compute idiosyncratic returns",
                    "Strip market/factor beta so the driver response is not confounded by general market moves.",
                ),
                (
                    StepKind::DriverSensitivity,
                    "Regress residuals on the driver signal",
                    "Quantifies how sentiment/theme evolution has historically repriced each name.",
                ),
                (
                    StepKind::EventStudy,
                    "Event study around driver spikes",
                    "Validates the sensitivity estimate on discrete episodes rather than the full sample.",
                ),
                (
                    StepKind::Synthesize,
                    "Build the analysis",
                    "Combine exposure and sensitivity into per-name expected impact; classify names as core/peripheral/unsupported.",
                ),
                (
                    StepKind::ConfidenceThresholds,
                    "Estimate confidence thresholds",
                    "Score the thesis and state the driver readings at which it becomes actionable or falsified.",
                ),
                (
                    StepKind::EstimateHorizon,
                    "Estimate horizon",
                    "Lead/lag and signal half-life give the expected time from driver move to price response.",
                ),
                (StepKind::RenderReport, "Render report", "Deliverable."),
            ],
        };

        AnalysisPlan {
            hypothesis_id: hypothesis.id.clone(),
            steps: steps
                .into_iter()
                .enumerate()
                .map(|(i, (kind, title, rationale))| PlanStep {
                    id: format!("S{}", i + 1),
                    kind,
                    title: title.to_string(),
                    rationale: rationale.to_string(),
                })
                .collect(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::HypothesisInput;

    #[test]
    fn template_plans_cover_all_kinds() {
        for kind in [
            HypothesisKind::SentimentCatalyst,
            HypothesisKind::Substitution,
            HypothesisKind::SupplyChain,
            HypothesisKind::Custom,
        ] {
            let mut input = HypothesisInput::new("test");
            input.kind = Some(kind);
            let plan = TemplatePlanner.plan(&input.normalize());
            assert!(plan.steps.len() >= 8);
            assert_eq!(plan.steps.first().unwrap().kind, StepKind::ScreenUniverse);
            assert_eq!(plan.steps.last().unwrap().kind, StepKind::RenderReport);
        }
    }
}
