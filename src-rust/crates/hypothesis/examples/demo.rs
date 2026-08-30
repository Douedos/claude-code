// Run both bundled demo analyses and print their markdown reports.
//
//   cargo run -p cc-hypothesis --example demo
//   cargo run -p cc-hypothesis --example demo -- substitution

use cc_hypothesis::{
    ExpectedEffect, HypothesisEngine, HypothesisInput, HypothesisKind, MockDataHub,
};
use std::sync::Arc;

fn main() {
    let which = std::env::args().nth(1).unwrap_or_else(|| "pharma".into());
    let report = match which.as_str() {
        "substitution" => {
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
            HypothesisEngine::new(Arc::new(MockDataHub::substitution_demo()))
                .analyze(input)
                .expect("analysis failed")
        }
        _ => {
            let mut input = HypothesisInput::new(
                "Pharmaceutical companies that have solutions or would be first responders to today's known epidemic could outperform as sentiment toward the epidemic evolves",
            );
            input.kind = Some(HypothesisKind::SentimentCatalyst);
            input.keywords = vec!["epidemic".into(), "vaccine".into(), "antiviral".into()];
            input.driver_signal_id = Some("epidemic_sentiment".into());
            HypothesisEngine::new(Arc::new(MockDataHub::pharma_demo()))
                .analyze(input)
                .expect("analysis failed")
        }
    };
    println!("{}", report.to_markdown());
}
