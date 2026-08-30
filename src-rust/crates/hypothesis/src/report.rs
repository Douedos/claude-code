// Report model and rendering.
//
// The report is the deliverable of every hypothesis run: a structured JSON
// document (chainable — its open questions can seed new hypotheses) plus a
// markdown rendering in the style of a research note. Every quantitative
// claim in the report is backed by an entry in the evidence ledger.

use crate::data::CompanyRef;
use crate::plan::AnalysisPlan;
use crate::types::Hypothesis;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// One traceable piece of evidence: which step produced it, from which data
/// source, and the value observed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Evidence {
    pub step_id: String,
    pub source: String,
    pub description: String,
    pub value: Value,
    pub recorded_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EvidenceLedger {
    pub entries: Vec<Evidence>,
}

impl EvidenceLedger {
    pub fn record(
        &mut self,
        step_id: &str,
        source: &str,
        description: impl Into<String>,
        value: Value,
    ) {
        self.entries.push(Evidence {
            step_id: step_id.to_string(),
            source: source.to_string(),
            description: description.into(),
            value,
            recorded_at: Utc::now(),
        });
    }
}

/// Revenue exposure of one company to the theme.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExposureEstimate {
    /// Fraction of TTM revenue in theme-tagged segments (0.0-1.0).
    pub revenue_exposure: f64,
    /// Theme-tagged revenue in USD.
    pub exposed_revenue: f64,
    /// Segments that matched, for the report.
    pub matched_segments: Vec<String>,
}

/// Statistical sensitivity of one company's idiosyncratic returns to the
/// driver signal.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SensitivityEstimate {
    /// Coefficient of idiosyncratic return on the (normalized) driver change.
    pub driver_beta: f64,
    pub t_stat: f64,
    /// R² of the driver regression on residual returns.
    pub r_squared: f64,
    /// Mean cumulative abnormal return around driver spikes, if estimable.
    pub event_car: Option<f64>,
    pub event_t_stat: Option<f64>,
    pub n_obs: usize,
}

/// How much the thesis is worth on one name if it plays out.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaterialityEstimate {
    /// Expected price impact for a one-standard-deviation driver move, in
    /// basis points.
    pub bps_per_sigma: f64,
    /// Revenue at stake as a fraction of market cap (fundamental channel).
    pub revenue_at_stake_pct_mcap: f64,
}

/// Where a name lands after synthesis.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NameVerdict {
    /// Material exposure and significant driver response.
    Core,
    /// One of the two, not both.
    Peripheral,
    /// Neither exposure nor response supports inclusion.
    Unsupported,
    /// Data was insufficient to assess.
    Insufficient,
}

/// Complete per-company assessment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompanyAssessment {
    pub company: CompanyRef,
    pub market_cap: f64,
    pub exposure: Option<ExposureEstimate>,
    pub sensitivity: Option<SensitivityEstimate>,
    pub materiality: Option<MaterialityEstimate>,
    pub verdict: NameVerdict,
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ConfidenceLevel {
    High,
    Medium,
    Low,
    Rejected,
}

/// A concrete, monitorable trigger: "if <signal> <comparator> <value>, then
/// <meaning>". These make the report actionable instead of narrative.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerThreshold {
    pub signal: String,
    pub comparator: String,
    pub value: f64,
    pub meaning: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceAssessment {
    /// 0.0-1.0 composite score.
    pub score: f64,
    pub level: ConfidenceLevel,
    pub thresholds: Vec<TriggerThreshold>,
    pub caveats: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HorizonEstimate {
    /// Expected trading days from a driver move to the bulk of the price
    /// response, from lead/lag analysis.
    pub price_response_days: Option<f64>,
    /// Days for a driver excursion to decay by half (thesis shelf life).
    pub driver_half_life_days: Option<f64>,
    /// Quarters until the fundamental (revenue) channel would show up.
    pub fundamental_realization_quarters: Option<u32>,
    pub basis: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThesisSummary {
    /// Whether the data supports the hypothesized direction.
    pub supported: bool,
    /// Names in each verdict bucket.
    pub core_names: Vec<String>,
    pub peripheral_names: Vec<String>,
    /// Aggregate expected impact across core names for a 1-sigma driver
    /// move, capitalization-weighted, in bps.
    pub aggregate_bps_per_sigma: f64,
    pub key_findings: Vec<String>,
}

/// The full deliverable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HypothesisReport {
    pub report_id: String,
    pub hypothesis: Hypothesis,
    pub plan: AnalysisPlan,
    pub companies: Vec<CompanyAssessment>,
    pub thesis: ThesisSummary,
    pub confidence: ConfidenceAssessment,
    pub horizon: HorizonEstimate,
    pub evidence: EvidenceLedger,
    pub generated_at: DateTime<Utc>,
}

fn fmt_pct(x: f64) -> String {
    format!("{:.1}%", x * 100.0)
}

fn fmt_usd_b(x: f64) -> String {
    format!("${:.1}B", x / 1.0e9)
}

impl HypothesisReport {
    /// Render the research-note style markdown report.
    pub fn to_markdown(&self) -> String {
        let mut md = String::new();
        let h = &self.hypothesis;
        md.push_str(&format!("# Hypothesis Analysis: {}\n\n", h.text));
        md.push_str(&format!(
            "*Report `{}` — generated {} — kind: `{:?}` — driver: **{}***\n\n",
            self.report_id,
            self.generated_at.format("%Y-%m-%d %H:%M UTC"),
            h.kind,
            h.driver.name,
        ));

        // Verdict box.
        md.push_str("## Verdict\n\n");
        md.push_str(&format!(
            "- **Thesis supported by the data:** {}\n- **Confidence:** {:?} ({:.2})\n- **Aggregate materiality (core names):** {:.0} bps per 1σ driver move\n",
            if self.thesis.supported { "YES" } else { "NO" },
            self.confidence.level,
            self.confidence.score,
            self.thesis.aggregate_bps_per_sigma,
        ));
        if let Some(d) = self.horizon.price_response_days {
            md.push_str(&format!("- **Price-response horizon:** ~{d:.0} trading days\n"));
        }
        if let Some(q) = self.horizon.fundamental_realization_quarters {
            md.push_str(&format!("- **Fundamental realization:** ~{q} quarters\n"));
        }
        md.push('\n');

        // Methodology from the plan.
        md.push_str("## Methodology\n\n");
        for step in &self.plan.steps {
            md.push_str(&format!("{}. **{}** — {}\n", step.id.trim_start_matches('S'), step.title, step.rationale));
        }
        md.push('\n');

        // Universe table.
        md.push_str("## Universe assessment\n\n");
        md.push_str("| Ticker | Mkt cap | Rev. exposure | Driver β | t-stat | bps/1σ | Verdict |\n");
        md.push_str("|---|---|---|---|---|---|---|\n");
        for c in &self.companies {
            let exp = c
                .exposure
                .as_ref()
                .map(|e| fmt_pct(e.revenue_exposure))
                .unwrap_or_else(|| "—".into());
            let (beta, t) = c
                .sensitivity
                .as_ref()
                .map(|s| (format!("{:.2}", s.driver_beta), format!("{:.1}", s.t_stat)))
                .unwrap_or_else(|| ("—".into(), "—".into()));
            let bps = c
                .materiality
                .as_ref()
                .map(|m| format!("{:.0}", m.bps_per_sigma))
                .unwrap_or_else(|| "—".into());
            md.push_str(&format!(
                "| {} | {} | {} | {} | {} | {} | {:?} |\n",
                c.company.ticker,
                fmt_usd_b(c.market_cap),
                exp,
                beta,
                t,
                bps,
                c.verdict,
            ));
        }
        md.push('\n');

        // Per-name notes.
        for c in &self.companies {
            if c.notes.is_empty() && c.exposure.is_none() {
                continue;
            }
            md.push_str(&format!("### {} ({})\n\n", c.company.name, c.company.ticker));
            if let Some(e) = &c.exposure {
                md.push_str(&format!(
                    "- Revenue exposure: {} of TTM revenue ({}) via segments: {}\n",
                    fmt_pct(e.revenue_exposure),
                    fmt_usd_b(e.exposed_revenue),
                    if e.matched_segments.is_empty() {
                        "none".to_string()
                    } else {
                        e.matched_segments.join(", ")
                    },
                ));
            }
            if let Some(s) = &c.sensitivity {
                md.push_str(&format!(
                    "- Idiosyncratic driver beta {:.3} (t = {:.2}, R² = {:.2}, n = {})\n",
                    s.driver_beta, s.t_stat, s.r_squared, s.n_obs
                ));
                if let (Some(car), Some(t)) = (s.event_car, s.event_t_stat) {
                    md.push_str(&format!(
                        "- Event study: mean CAR {} around driver spikes (t = {:.2})\n",
                        fmt_pct(car),
                        t
                    ));
                }
            }
            for n in &c.notes {
                md.push_str(&format!("- {n}\n"));
            }
            md.push('\n');
        }

        // Findings.
        md.push_str("## Key findings\n\n");
        for f in &self.thesis.key_findings {
            md.push_str(&format!("- {f}\n"));
        }
        md.push('\n');

        // Confidence & triggers.
        md.push_str("## Confidence & monitoring triggers\n\n");
        md.push_str(&format!(
            "Composite confidence **{:.2}** ({:?}).\n\n",
            self.confidence.score, self.confidence.level
        ));
        if !self.confidence.thresholds.is_empty() {
            md.push_str("| Signal | Condition | Meaning |\n|---|---|---|\n");
            for t in &self.confidence.thresholds {
                md.push_str(&format!(
                    "| {} | {} {:.2} | {} |\n",
                    t.signal, t.comparator, t.value, t.meaning
                ));
            }
            md.push('\n');
        }
        if !self.confidence.caveats.is_empty() {
            md.push_str("**Caveats:**\n\n");
            for c in &self.confidence.caveats {
                md.push_str(&format!("- {c}\n"));
            }
            md.push('\n');
        }

        // Horizon.
        md.push_str("## Horizon\n\n");
        md.push_str(&format!("{}\n\n", self.horizon.basis));

        // Sub-claims.
        if !h.sub_claims.is_empty() {
            md.push_str("## Sub-claims\n\n");
            for sc in &h.sub_claims {
                md.push_str(&format!(
                    "- `{}` {} — {}\n",
                    sc.id,
                    sc.statement,
                    if sc.testable {
                        "tested quantitatively above"
                    } else {
                        "NOT quantitatively testable; carried as an assumption"
                    }
                ));
            }
            md.push('\n');
        }

        // Evidence appendix.
        md.push_str(&format!(
            "## Evidence appendix\n\n{} ledger entries. Each quantitative claim above traces to a step/source pair.\n\n",
            self.evidence.entries.len()
        ));
        md.push_str("| Step | Source | Observation |\n|---|---|---|\n");
        for e in &self.evidence.entries {
            md.push_str(&format!("| {} | {} | {} |\n", e.step_id, e.source, e.description));
        }
        md.push('\n');
        md
    }
}
