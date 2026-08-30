// Core domain types for the quantitative hypothesis analysis engine.
//
// A `Hypothesis` is a textual claim / prediction / observation about markets
// ("pharma companies exposed to the current epidemic will outperform as
// sentiment evolves", "Apple's new Mac Studio will take a significant share
// of Nvidia's consumer GPU sales") that the engine turns into a quantitative
// analysis: universe, exposures, sensitivities, materiality, confidence
// thresholds and horizon.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Where a hypothesis came from. Hypotheses can be fed from news media,
/// research reports, or the output of a previous analysis (auto-research
/// chaining).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum HypothesisSource {
    /// A news/media item (article, tweet, broadcast).
    NewsMedia { outlet: String, reference: String },
    /// A research or corporate report.
    Report { publisher: String, reference: String },
    /// The output of another analysis run (report id), enabling chained
    /// auto-research: one report's open question becomes the next hypothesis.
    AnalysisOutput { report_id: String },
    /// Entered manually by the user.
    Manual,
}

impl Default for HypothesisSource {
    fn default() -> Self {
        HypothesisSource::Manual
    }
}

/// The structural family a hypothesis belongs to. The family selects the
/// analysis plan template (which steps to run and how to interpret them).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HypothesisKind {
    /// A theme/event whose public salience (sentiment, news volume) reprices
    /// exposed names. Example: epidemic sentiment vs. first-responder pharma.
    SentimentCatalyst,
    /// Product/vendor A takes demand share from product/vendor B.
    /// Example: Apple Mac Studio vs. Nvidia consumer GPU sales.
    Substitution,
    /// A disruption or shift propagating through suppliers/customers.
    SupplyChain,
    /// A regulatory or policy change re-rating a set of names.
    Regulatory,
    /// A broad macro theme (rates, commodity, FX) hitting a cohort.
    MacroThematic,
    /// Anything else; falls back to the generic plan template.
    Custom,
}

/// Which way the hypothesis says exposed names should move.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ExpectedEffect {
    /// Exposed names outperform.
    Positive,
    /// Exposed names underperform.
    Negative,
    /// Demand rotates from `loser_keywords`-matched names to
    /// `winner_keywords`-matched names (substitution theses).
    Rotation {
        winner_keywords: Vec<String>,
        loser_keywords: Vec<String>,
    },
}

/// The observable driver of the thesis: a time series the engine can load
/// from a `DataHub` (a sentiment index, news-volume index, adoption proxy,
/// epidemic case counts...). Sensitivity and horizon are estimated against
/// this series.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DriverSpec {
    /// Signal id resolvable by the data hub (e.g. "epidemic_sentiment").
    pub signal_id: String,
    /// Human-readable name for the report.
    pub name: String,
    /// What the series measures and where it comes from.
    pub description: String,
}

/// Screening criteria describing which companies are eligible under the
/// hypothesis ("companies that have a solution or would be first responders").
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct ScreenCriteria {
    /// Sector / industry filters (matched case-insensitively).
    pub sectors: Vec<String>,
    /// Keywords matched against company descriptions and segment tags.
    pub keywords: Vec<String>,
    /// Explicit tickers to force-include (bypasses keyword matching).
    pub include_tickers: Vec<String>,
    /// Minimum market cap in USD, if any.
    pub min_market_cap: Option<f64>,
}

/// A decomposed, individually testable sub-claim of the hypothesis.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SubClaim {
    pub id: String,
    pub statement: String,
    /// Whether the engine can test it quantitatively with the available
    /// data hub (untestable claims are carried into the report as caveats).
    pub testable: bool,
}

/// A fully structured hypothesis, ready for planning and execution.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Hypothesis {
    pub id: String,
    /// The original textual claim, verbatim.
    pub text: String,
    pub kind: HypothesisKind,
    pub source: HypothesisSource,
    pub effect: ExpectedEffect,
    pub driver: DriverSpec,
    pub criteria: ScreenCriteria,
    pub sub_claims: Vec<SubClaim>,
    pub created_at: DateTime<Utc>,
}

/// The raw input handed to the engine. Everything except `text` is optional:
/// missing fields are filled by normalization (keyword extraction today, an
/// LLM planner when wired into the harness — see spec/14_hypothesis_engine.md).
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct HypothesisInput {
    pub text: String,
    pub kind: Option<HypothesisKind>,
    #[serde(default)]
    pub source: HypothesisSource,
    pub effect: Option<ExpectedEffect>,
    pub driver_signal_id: Option<String>,
    #[serde(default)]
    pub keywords: Vec<String>,
    #[serde(default)]
    pub sectors: Vec<String>,
    #[serde(default)]
    pub include_tickers: Vec<String>,
    pub min_market_cap: Option<f64>,
}

/// Words too generic to act as screening keywords when extracting from text.
const STOPWORDS: &[&str] = &[
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "that", "this", "will", "would", "could", "should", "have", "has", "is",
    "are", "be", "been", "when", "who", "which", "their", "its", "new",
    "significant", "amount", "toward", "towards", "today", "known", "know",
    "under", "those", "these", "from", "take", "sales", "companies", "company",
];

impl HypothesisInput {
    pub fn new(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            ..Default::default()
        }
    }

    /// Normalize the raw input into a structured `Hypothesis`.
    ///
    /// This is the deterministic fallback: keywords are extracted naively
    /// from the text when none are supplied, kind defaults to
    /// `SentimentCatalyst`, and the driver defaults to a generic
    /// "thesis_driver" signal. An agentic harness should pre-fill these
    /// fields via an LLM pass before calling the engine.
    pub fn normalize(self) -> Hypothesis {
        let keywords = if self.keywords.is_empty() {
            extract_keywords(&self.text)
        } else {
            self.keywords
        };
        let kind = self.kind.unwrap_or(HypothesisKind::SentimentCatalyst);
        let effect = self.effect.unwrap_or(ExpectedEffect::Positive);
        let driver_id = self
            .driver_signal_id
            .unwrap_or_else(|| "thesis_driver".to_string());
        Hypothesis {
            id: uuid::Uuid::new_v4().to_string(),
            sub_claims: default_sub_claims(kind),
            text: self.text,
            kind,
            source: self.source,
            effect,
            driver: DriverSpec {
                signal_id: driver_id.clone(),
                name: driver_id,
                description: "Driver signal supplied by the data hub".to_string(),
            },
            criteria: ScreenCriteria {
                sectors: self.sectors,
                keywords,
                include_tickers: self.include_tickers,
                min_market_cap: self.min_market_cap,
            },
            created_at: Utc::now(),
        }
    }
}

/// Naive keyword extraction: lowercase alphanumeric tokens minus stopwords,
/// deduplicated, longest-first, capped at 8.
fn extract_keywords(text: &str) -> Vec<String> {
    let mut seen = std::collections::HashSet::new();
    let mut words: Vec<String> = text
        .split(|c: char| !c.is_alphanumeric())
        .map(|w| w.to_lowercase())
        .filter(|w| w.len() > 3 && !STOPWORDS.contains(&w.as_str()))
        .filter(|w| seen.insert(w.clone()))
        .collect();
    words.sort_by_key(|w| std::cmp::Reverse(w.len()));
    words.truncate(8);
    words
}

/// Every hypothesis family decomposes into the same skeleton of testable
/// sub-claims; templates specialize the wording.
fn default_sub_claims(kind: HypothesisKind) -> Vec<SubClaim> {
    let claims: &[(&str, bool)] = match kind {
        HypothesisKind::Substitution => &[
            ("An identifiable set of names sits on each side of the substitution", true),
            ("The losing side has material revenue in the substituted product line", true),
            ("Idiosyncratic returns of both sides respond to the driver signal", true),
            ("The substitution is technically/commercially credible", false),
        ],
        _ => &[
            ("An identifiable universe of exposed companies exists", true),
            ("Those companies have material revenue exposure to the theme", true),
            ("Their idiosyncratic returns respond to the driver signal", true),
            ("The driver signal will continue to evolve as claimed", false),
        ],
    };
    claims
        .iter()
        .enumerate()
        .map(|(i, (s, t))| SubClaim {
            id: format!("SC{}", i + 1),
            statement: s.to_string(),
            testable: *t,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_extracts_keywords_and_defaults() {
        let h = HypothesisInput::new(
            "Pharmaceutical companies with epidemic solutions could outperform",
        )
        .normalize();
        assert_eq!(h.kind, HypothesisKind::SentimentCatalyst);
        assert!(h.criteria.keywords.iter().any(|k| k == "pharmaceutical"));
        assert!(h.criteria.keywords.iter().any(|k| k == "epidemic"));
        assert!(!h.sub_claims.is_empty());
    }

    #[test]
    fn explicit_fields_survive_normalization() {
        let mut input = HypothesisInput::new("Mac Studio takes Nvidia consumer share");
        input.kind = Some(HypothesisKind::Substitution);
        input.keywords = vec!["gpu".into()];
        input.driver_signal_id = Some("mac_studio_adoption".into());
        let h = input.normalize();
        assert_eq!(h.kind, HypothesisKind::Substitution);
        assert_eq!(h.criteria.keywords, vec!["gpu".to_string()]);
        assert_eq!(h.driver.signal_id, "mac_studio_adoption");
    }
}
