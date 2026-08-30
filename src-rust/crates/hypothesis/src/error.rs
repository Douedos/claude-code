use thiserror::Error;

#[derive(Error, Debug)]
pub enum HypothesisError {
    #[error("data error: {0}")]
    Data(String),

    #[error("screening produced no eligible companies: {0}")]
    EmptyUniverse(String),

    #[error("analysis error: {0}")]
    Analysis(String),
}

pub type Result<T> = std::result::Result<T, HypothesisError>;
