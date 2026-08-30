// cc-hypothesis: quantitative analysis of textual investment hypotheses.
//
// Turns a claimed fact / prediction / observation ("pharma names exposed to
// the current epidemic outperform as sentiment evolves", "Apple's Mac Studio
// takes share from Nvidia's consumer GPUs") into a reproducible quantitative
// report: eligible universe, revenue exposure, idiosyncratic driver
// sensitivity, materiality, confidence thresholds and horizon.
//
// Architecture (see spec/14_hypothesis_engine.md for the full design):
//
//   HypothesisInput --normalize--> Hypothesis --Planner--> AnalysisPlan
//        |                                                     |
//        v                                                     v
//   HypothesisEngine::analyze --- executes steps against a DataHub ---
//        |
//        v
//   HypothesisReport (JSON + markdown, evidence-backed, chainable)
//
// The engine is deterministic; agentic behavior (LLM normalization,
// adaptive planning, narrative sections) is layered on by the harness via
// the `Planner` trait and the HypothesisAnalyze tool in cc-tools.

pub mod data;
pub mod engine;
pub mod error;
pub mod plan;
pub mod report;
pub mod stats;
pub mod types;

pub use data::{CompanyRef, DataHub, FileDataHub, FundamentalsSnapshot, MockDataHub, Series};
pub use engine::{EngineConfig, HypothesisEngine};
pub use error::{HypothesisError, Result};
pub use plan::{AnalysisPlan, PlanStep, Planner, StepKind, TemplatePlanner};
pub use report::{
    CompanyAssessment, ConfidenceAssessment, ConfidenceLevel, EvidenceLedger, HorizonEstimate,
    HypothesisReport, NameVerdict, TriggerThreshold,
};
pub use types::{
    ExpectedEffect, Hypothesis, HypothesisInput, HypothesisKind, HypothesisSource, ScreenCriteria,
};
