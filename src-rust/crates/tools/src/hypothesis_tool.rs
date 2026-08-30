// HypothesisAnalyze tool: exposes the cc-hypothesis engine to the agent
// loop, so the model can turn a textual investment hypothesis (claim,
// prediction, observation) into a quantitative report — universe, revenue
// exposure, idiosyncratic driver sensitivity, materiality, confidence
// thresholds and horizon.
//
// The agentic workflow this tool anchors (spec/14_hypothesis_engine.md):
// the model normalizes the hypothesis from its source (news, report, a
// previous analysis), chooses kind/keywords/driver, calls this tool, then
// interprets and narrates the returned report — chaining follow-up
// hypotheses from the report's open questions if warranted.

use crate::{PermissionLevel, Tool, ToolContext, ToolResult};
use async_trait::async_trait;
use cc_hypothesis::{
    DataHub, ExpectedEffect, FileDataHub, HypothesisEngine, HypothesisInput, HypothesisKind,
    MockDataHub,
};
use serde::Deserialize;
use serde_json::{json, Value};
use std::sync::Arc;

pub struct HypothesisAnalyzeTool;

#[derive(Debug, Deserialize)]
struct Input {
    hypothesis: String,
    #[serde(default)]
    kind: Option<String>,
    #[serde(default)]
    keywords: Vec<String>,
    #[serde(default)]
    sectors: Vec<String>,
    #[serde(default)]
    include_tickers: Vec<String>,
    #[serde(default)]
    driver_signal: Option<String>,
    #[serde(default)]
    winner_keywords: Vec<String>,
    #[serde(default)]
    loser_keywords: Vec<String>,
    /// Directory of a FileDataHub (universe.json, fundamentals/, prices/,
    /// signals/). When omitted, the bundled deterministic demo hub is used.
    #[serde(default)]
    data_dir: Option<String>,
    /// Also return the full report JSON alongside the markdown.
    #[serde(default)]
    include_json: bool,
}

fn parse_kind(s: &str) -> Option<HypothesisKind> {
    match s.to_lowercase().replace(['-', ' '], "_").as_str() {
        "sentiment_catalyst" | "sentiment" => Some(HypothesisKind::SentimentCatalyst),
        "substitution" | "share_shift" => Some(HypothesisKind::Substitution),
        "supply_chain" => Some(HypothesisKind::SupplyChain),
        "regulatory" => Some(HypothesisKind::Regulatory),
        "macro_thematic" | "macro" => Some(HypothesisKind::MacroThematic),
        "custom" => Some(HypothesisKind::Custom),
        _ => None,
    }
}

#[async_trait]
impl Tool for HypothesisAnalyzeTool {
    fn name(&self) -> &str {
        "HypothesisAnalyze"
    }

    fn description(&self) -> &str {
        "Run a quantitative analysis of a textual investment hypothesis: screen the eligible universe, estimate revenue exposure, regress idiosyncratic returns on the driver signal, and report materiality, confidence thresholds and horizon."
    }

    fn permission_level(&self) -> PermissionLevel {
        PermissionLevel::ReadOnly
    }

    fn input_schema(&self) -> Value {
        json!({
            "type": "object",
            "properties": {
                "hypothesis": {
                    "type": "string",
                    "description": "The textual claim / prediction / observation to analyze, verbatim from its source."
                },
                "kind": {
                    "type": "string",
                    "enum": ["sentiment_catalyst", "substitution", "supply_chain", "regulatory", "macro_thematic", "custom"],
                    "description": "Structural family of the hypothesis; selects the analysis plan template. Defaults to sentiment_catalyst."
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Thematic keywords for screening and segment matching. Extracted from the text when omitted."
                },
                "sectors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional sector filter for the screen."
                },
                "include_tickers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tickers to force-include in the universe."
                },
                "driver_signal": {
                    "type": "string",
                    "description": "Id of the driver signal series in the data hub (e.g. a sentiment index or adoption proxy)."
                },
                "winner_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "For substitution theses: keywords identifying the winning side."
                },
                "loser_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "For substitution theses: keywords identifying the losing side."
                },
                "data_dir": {
                    "type": "string",
                    "description": "Directory of a file-backed data hub (universe.json, fundamentals/, prices/, signals/). Uses the bundled demo hub when omitted."
                },
                "include_json": {
                    "type": "boolean",
                    "description": "Also return the structured report JSON (for chaining into further analyses)."
                }
            },
            "required": ["hypothesis"]
        })
    }

    async fn execute(&self, input: Value, ctx: &ToolContext) -> ToolResult {
        let parsed: Input = match serde_json::from_value(input) {
            Ok(p) => p,
            Err(e) => return ToolResult::error(format!("Invalid input: {e}")),
        };

        let hub: Arc<dyn DataHub> = match &parsed.data_dir {
            Some(dir) => Arc::new(FileDataHub::new(ctx.resolve_path(dir))),
            None => {
                if matches!(parse_kind(parsed.kind.as_deref().unwrap_or("")), Some(HypothesisKind::Substitution)) {
                    Arc::new(MockDataHub::substitution_demo())
                } else {
                    Arc::new(MockDataHub::pharma_demo())
                }
            }
        };

        let mut hi = HypothesisInput::new(parsed.hypothesis);
        hi.kind = parsed.kind.as_deref().and_then(parse_kind);
        hi.keywords = parsed.keywords;
        hi.sectors = parsed.sectors;
        hi.include_tickers = parsed.include_tickers;
        hi.driver_signal_id = parsed.driver_signal;
        if !parsed.winner_keywords.is_empty() || !parsed.loser_keywords.is_empty() {
            hi.effect = Some(ExpectedEffect::Rotation {
                winner_keywords: parsed.winner_keywords,
                loser_keywords: parsed.loser_keywords,
            });
        }

        // The engine is synchronous CPU/file work; keep the runtime free.
        let include_json = parsed.include_json;
        let result = tokio::task::spawn_blocking(move || {
            HypothesisEngine::new(hub).analyze(hi)
        })
        .await;

        match result {
            Ok(Ok(report)) => {
                let mut content = report.to_markdown();
                if include_json {
                    match serde_json::to_string_pretty(&report) {
                        Ok(js) => {
                            content.push_str("\n## Structured report (JSON)\n\n```json\n");
                            content.push_str(&js);
                            content.push_str("\n```\n");
                        }
                        Err(e) => content.push_str(&format!("\n(JSON serialization failed: {e})\n")),
                    }
                }
                ToolResult::success(content).with_metadata(json!({
                    "report_id": report.report_id,
                    "supported": report.thesis.supported,
                    "confidence": report.confidence.score,
                    "core_names": report.thesis.core_names,
                }))
            }
            Ok(Err(e)) => ToolResult::error(format!("Hypothesis analysis failed: {e}")),
            Err(e) => ToolResult::error(format!("Analysis task panicked: {e}")),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use cc_core::config::{Config, PermissionMode};
    use cc_core::cost::CostTracker;
    use cc_core::permissions::{PermissionDecision, PermissionHandler, PermissionRequest};

    struct AllowAll;
    impl PermissionHandler for AllowAll {
        fn check_permission(&self, _req: &PermissionRequest) -> PermissionDecision {
            PermissionDecision::Allow
        }
        fn request_permission(&self, _req: &PermissionRequest) -> PermissionDecision {
            PermissionDecision::Allow
        }
    }

    fn test_ctx() -> ToolContext {
        ToolContext {
            working_dir: std::env::temp_dir(),
            permission_mode: PermissionMode::Default,
            permission_handler: Arc::new(AllowAll),
            cost_tracker: CostTracker::new(),
            session_id: "test".into(),
            non_interactive: true,
            mcp_manager: None,
            config: Config::default(),
        }
    }

    #[tokio::test]
    async fn analyzes_demo_hypothesis() {
        let tool = HypothesisAnalyzeTool;
        let result = tool
            .execute(
                json!({
                    "hypothesis": "Epidemic-exposed pharma outperforms as sentiment evolves",
                    "keywords": ["epidemic", "vaccine", "antiviral"],
                    "driver_signal": "epidemic_sentiment"
                }),
                &test_ctx(),
            )
            .await;
        assert!(!result.is_error, "{}", result.content);
        assert!(result.content.contains("## Verdict"));
        assert!(result.metadata.is_some());
    }

    #[tokio::test]
    async fn rejects_missing_hypothesis() {
        let tool = HypothesisAnalyzeTool;
        let result = tool.execute(json!({}), &test_ctx()).await;
        assert!(result.is_error);
    }
}
