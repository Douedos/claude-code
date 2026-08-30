// Data layer for the hypothesis engine: the `DataHub` contract every data
// provider implements, plus two bundled implementations:
//
// * `FileDataHub`  — reads a directory of JSON/CSV files, the integration
//   point for real feeds (a fetcher job materializes files, the engine stays
//   offline and reproducible).
// * `MockDataHub`  — deterministic synthetic data for tests and demos.

use crate::error::{HypothesisError, Result};
use crate::types::ScreenCriteria;
use chrono::NaiveDate;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::PathBuf;

// ---------------------------------------------------------------------------
// Data structures
// ---------------------------------------------------------------------------

/// A company in the screening universe.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CompanyRef {
    pub ticker: String,
    pub name: String,
    pub sector: String,
    /// Free-text business description, used for keyword screening.
    #[serde(default)]
    pub description: String,
}

/// A revenue segment with thematic tags ("oncology", "vaccines", "consumer
/// gpu", ...) used to estimate revenue exposure to a theme.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RevenueSegment {
    pub name: String,
    /// Trailing-twelve-month revenue for the segment, USD.
    pub revenue: f64,
    #[serde(default)]
    pub tags: Vec<String>,
}

/// Point-in-time fundamentals for one company.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FundamentalsSnapshot {
    pub ticker: String,
    pub as_of: NaiveDate,
    /// Market capitalization, USD.
    pub market_cap: f64,
    /// Trailing-twelve-month total revenue, USD.
    pub revenue_ttm: f64,
    #[serde(default)]
    pub segments: Vec<RevenueSegment>,
    /// Gross margin as a fraction (0.62 = 62%), if known.
    pub gross_margin: Option<f64>,
}

/// A dated series (prices, or any driver signal). Dates are strictly
/// increasing; `values` is parallel to `dates`.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Series {
    pub id: String,
    pub dates: Vec<NaiveDate>,
    pub values: Vec<f64>,
}

impl Series {
    pub fn new(id: impl Into<String>, points: Vec<(NaiveDate, f64)>) -> Self {
        let mut points = points;
        points.sort_by_key(|(d, _)| *d);
        Self {
            id: id.into(),
            dates: points.iter().map(|(d, _)| *d).collect(),
            values: points.iter().map(|(_, v)| *v).collect(),
        }
    }

    pub fn len(&self) -> usize {
        self.dates.len()
    }

    pub fn is_empty(&self) -> bool {
        self.dates.is_empty()
    }

    /// Simple period-over-period returns; result is one shorter than the
    /// input and dated at the end of each period.
    pub fn simple_returns(&self) -> Series {
        let mut points = Vec::new();
        for i in 1..self.len() {
            let prev = self.values[i - 1];
            if prev.abs() > f64::EPSILON {
                points.push((self.dates[i], self.values[i] / prev - 1.0));
            }
        }
        Series::new(format!("{}_ret", self.id), points)
    }

    /// Period-over-period differences (for signals where levels, not
    /// returns, are the natural unit).
    pub fn diffs(&self) -> Series {
        let mut points = Vec::new();
        for i in 1..self.len() {
            points.push((self.dates[i], self.values[i] - self.values[i - 1]));
        }
        Series::new(format!("{}_diff", self.id), points)
    }

    /// Inner-join two series on date, returning parallel value vectors.
    pub fn align(&self, other: &Series) -> (Vec<f64>, Vec<f64>) {
        let map: BTreeMap<NaiveDate, f64> = other
            .dates
            .iter()
            .cloned()
            .zip(other.values.iter().cloned())
            .collect();
        let mut a = Vec::new();
        let mut b = Vec::new();
        for (d, v) in self.dates.iter().zip(self.values.iter()) {
            if let Some(o) = map.get(d) {
                a.push(*v);
                b.push(*o);
            }
        }
        (a, b)
    }
}

// ---------------------------------------------------------------------------
// The DataHub contract
// ---------------------------------------------------------------------------

/// The defined set of data capabilities the engine draws from. Implementors
/// wire real feeds (screeners, fundamentals vendors, price feeds, sentiment
/// indices); the engine only ever talks to this trait so every analysis is
/// reproducible against any hub.
pub trait DataHub: Send + Sync {
    /// Screen the universe for companies matching the criteria.
    fn screen(&self, criteria: &ScreenCriteria) -> Result<Vec<CompanyRef>>;

    /// Load fundamentals for one company.
    fn fundamentals(&self, ticker: &str) -> Result<FundamentalsSnapshot>;

    /// Load the price history for one company.
    fn prices(&self, ticker: &str) -> Result<Series>;

    /// The benchmark price series used to strip market beta.
    fn benchmark(&self) -> Result<Series>;

    /// Additional factor return series (sector index, style factors...).
    /// Default: none.
    fn factors(&self) -> Result<Vec<Series>> {
        Ok(Vec::new())
    }

    /// Load a driver signal series by id (sentiment index, adoption proxy,
    /// case counts...).
    fn signal(&self, id: &str) -> Result<Series>;
}

fn matches_criteria(c: &CompanyRef, segments: &[RevenueSegment], criteria: &ScreenCriteria) -> bool {
    if criteria
        .include_tickers
        .iter()
        .any(|t| t.eq_ignore_ascii_case(&c.ticker))
    {
        return true;
    }
    if !criteria.sectors.is_empty()
        && !criteria
            .sectors
            .iter()
            .any(|s| c.sector.eq_ignore_ascii_case(s))
    {
        return false;
    }
    if criteria.keywords.is_empty() {
        return criteria.include_tickers.is_empty();
    }
    let haystack = format!(
        "{} {} {}",
        c.name.to_lowercase(),
        c.description.to_lowercase(),
        segments
            .iter()
            .flat_map(|s| s.tags.iter())
            .map(|t| t.to_lowercase())
            .collect::<Vec<_>>()
            .join(" ")
    );
    criteria
        .keywords
        .iter()
        .any(|k| haystack.contains(&k.to_lowercase()))
}

// ---------------------------------------------------------------------------
// FileDataHub
// ---------------------------------------------------------------------------

/// A hub backed by a directory:
///
/// ```text
/// <root>/universe.json            [CompanyRef, ...]
/// <root>/fundamentals/<T>.json    FundamentalsSnapshot
/// <root>/prices/<T>.csv           date,value rows (header optional)
/// <root>/prices/BENCHMARK.csv     benchmark series
/// <root>/factors/<name>.csv       optional factor series
/// <root>/signals/<id>.csv         driver signals
/// ```
pub struct FileDataHub {
    root: PathBuf,
}

impl FileDataHub {
    pub fn new(root: impl Into<PathBuf>) -> Self {
        Self { root: root.into() }
    }

    fn read_csv_series(&self, path: &PathBuf, id: &str) -> Result<Series> {
        let text = std::fs::read_to_string(path)
            .map_err(|e| HypothesisError::Data(format!("{}: {}", path.display(), e)))?;
        let mut points = Vec::new();
        for line in text.lines() {
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            let mut parts = line.splitn(2, ',');
            let (Some(d), Some(v)) = (parts.next(), parts.next()) else {
                continue;
            };
            let Ok(date) = NaiveDate::parse_from_str(d.trim(), "%Y-%m-%d") else {
                continue; // header or malformed row
            };
            let Ok(value) = v.trim().parse::<f64>() else {
                continue;
            };
            points.push((date, value));
        }
        if points.is_empty() {
            return Err(HypothesisError::Data(format!(
                "no parseable rows in {}",
                path.display()
            )));
        }
        Ok(Series::new(id, points))
    }
}

impl DataHub for FileDataHub {
    fn screen(&self, criteria: &ScreenCriteria) -> Result<Vec<CompanyRef>> {
        let path = self.root.join("universe.json");
        let text = std::fs::read_to_string(&path)
            .map_err(|e| HypothesisError::Data(format!("{}: {}", path.display(), e)))?;
        let universe: Vec<CompanyRef> = serde_json::from_str(&text)
            .map_err(|e| HypothesisError::Data(format!("{}: {}", path.display(), e)))?;
        Ok(universe
            .into_iter()
            .filter(|c| {
                let segments = self
                    .fundamentals(&c.ticker)
                    .map(|f| f.segments)
                    .unwrap_or_default();
                matches_criteria(c, &segments, criteria)
            })
            .collect())
    }

    fn fundamentals(&self, ticker: &str) -> Result<FundamentalsSnapshot> {
        let path = self.root.join("fundamentals").join(format!("{ticker}.json"));
        let text = std::fs::read_to_string(&path)
            .map_err(|e| HypothesisError::Data(format!("{}: {}", path.display(), e)))?;
        serde_json::from_str(&text)
            .map_err(|e| HypothesisError::Data(format!("{}: {}", path.display(), e)))
    }

    fn prices(&self, ticker: &str) -> Result<Series> {
        let path = self.root.join("prices").join(format!("{ticker}.csv"));
        self.read_csv_series(&path, ticker)
    }

    fn benchmark(&self) -> Result<Series> {
        let path = self.root.join("prices").join("BENCHMARK.csv");
        self.read_csv_series(&path, "BENCHMARK")
    }

    fn factors(&self) -> Result<Vec<Series>> {
        let dir = self.root.join("factors");
        let mut out = Vec::new();
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("csv") {
                    let id = path
                        .file_stem()
                        .and_then(|s| s.to_str())
                        .unwrap_or("factor")
                        .to_string();
                    out.push(self.read_csv_series(&path, &id)?);
                }
            }
        }
        out.sort_by(|a, b| a.id.cmp(&b.id));
        Ok(out)
    }

    fn signal(&self, id: &str) -> Result<Series> {
        let path = self.root.join("signals").join(format!("{id}.csv"));
        self.read_csv_series(&path, id)
    }
}

// ---------------------------------------------------------------------------
// MockDataHub
// ---------------------------------------------------------------------------

/// Deterministic synthetic hub for tests and demos. The universe contains
/// names with varying true exposure to the driver signal, so end-to-end runs
/// produce differentiated, reproducible reports.
pub struct MockDataHub {
    universe: Vec<(CompanyRef, FundamentalsSnapshot, f64)>, // (company, fundamentals, true driver beta)
    days: usize,
    seed: u64,
}

/// Minimal deterministic PRNG (xorshift64*), avoids a rand dependency.
struct Prng(u64);

impl Prng {
    fn next_f64(&mut self) -> f64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        // Map to (-0.5, 0.5)
        (self.0 as f64 / u64::MAX as f64) - 0.5
    }
}

impl MockDataHub {
    /// A small pharma-flavoured universe: two exposed names, one partially
    /// exposed, one unexposed control.
    pub fn pharma_demo() -> Self {
        let mk = |ticker: &str, name: &str, desc: &str, mcap: f64, rev: f64, segments: Vec<RevenueSegment>, beta: f64| {
            (
                CompanyRef {
                    ticker: ticker.into(),
                    name: name.into(),
                    sector: "Healthcare".into(),
                    description: desc.into(),
                },
                FundamentalsSnapshot {
                    ticker: ticker.into(),
                    as_of: NaiveDate::from_ymd_opt(2026, 6, 30).unwrap(),
                    market_cap: mcap,
                    revenue_ttm: rev,
                    segments,
                    gross_margin: Some(0.65),
                },
                beta,
            )
        };
        let seg = |name: &str, rev: f64, tags: &[&str]| RevenueSegment {
            name: name.into(),
            revenue: rev,
            tags: tags.iter().map(|s| s.to_string()).collect(),
        };
        Self {
            universe: vec![
                mk(
                    "VAXA",
                    "Vaxa Therapeutics",
                    "vaccine developer with epidemic antiviral pipeline",
                    8.0e9,
                    1.2e9,
                    vec![
                        seg("Vaccines", 0.7e9, &["vaccine", "epidemic"]),
                        seg("Other", 0.5e9, &[]),
                    ],
                    0.9,
                ),
                mk(
                    "CURX",
                    "CureX Biosciences",
                    "antiviral therapeutics first responder epidemic treatments",
                    4.0e9,
                    0.8e9,
                    vec![
                        seg("Antivirals", 0.6e9, &["antiviral", "epidemic"]),
                        seg("Diagnostics", 0.2e9, &["diagnostics"]),
                    ],
                    1.2,
                ),
                mk(
                    "MEDI",
                    "Medix Health",
                    "diversified pharma with small vaccine unit",
                    50.0e9,
                    20.0e9,
                    vec![
                        seg("Oncology", 14.0e9, &["oncology"]),
                        seg("Vaccines", 2.0e9, &["vaccine"]),
                        seg("Consumer", 4.0e9, &[]),
                    ],
                    0.25,
                ),
                mk(
                    "GENC",
                    "Generic Consumer Co",
                    "consumer staples unrelated to healthcare themes",
                    30.0e9,
                    15.0e9,
                    vec![seg("Staples", 15.0e9, &[])],
                    0.0,
                ),
            ],
            days: 260,
            seed: 42,
        }
    }

    /// A substitution-flavoured universe: a winner (workstation vendor), a
    /// loser with a consumer GPU segment, and a control.
    pub fn substitution_demo() -> Self {
        let mut hub = Self::pharma_demo();
        hub.universe = vec![
            (
                CompanyRef {
                    ticker: "APLW".into(),
                    name: "Apple-like Workstations".into(),
                    sector: "Technology".into(),
                    description: "integrated workstation vendor mac studio desktop compute".into(),
                },
                FundamentalsSnapshot {
                    ticker: "APLW".into(),
                    as_of: NaiveDate::from_ymd_opt(2026, 6, 30).unwrap(),
                    market_cap: 3000.0e9,
                    revenue_ttm: 400.0e9,
                    segments: vec![RevenueSegment {
                        name: "Desktops".into(),
                        revenue: 30.0e9,
                        tags: vec!["workstation".into(), "desktop".into()],
                    }],
                    gross_margin: Some(0.45),
                },
                0.6,
            ),
            (
                CompanyRef {
                    ticker: "NVDL".into(),
                    name: "Nvidia-like GPUs".into(),
                    sector: "Technology".into(),
                    description: "gpu designer consumer gaming and datacenter accelerators".into(),
                },
                FundamentalsSnapshot {
                    ticker: "NVDL".into(),
                    as_of: NaiveDate::from_ymd_opt(2026, 6, 30).unwrap(),
                    market_cap: 2000.0e9,
                    revenue_ttm: 100.0e9,
                    segments: vec![
                        RevenueSegment {
                            name: "Consumer GPU".into(),
                            revenue: 12.0e9,
                            tags: vec!["consumer".into(), "gpu".into(), "gaming".into()],
                        },
                        RevenueSegment {
                            name: "Datacenter".into(),
                            revenue: 85.0e9,
                            tags: vec!["datacenter".into(), "ai".into()],
                        },
                    ],
                    gross_margin: Some(0.7),
                },
                -0.8,
            ),
            (
                CompanyRef {
                    ticker: "CTRL".into(),
                    name: "Control Industrials".into(),
                    sector: "Industrials".into(),
                    description: "industrial conglomerate".into(),
                },
                FundamentalsSnapshot {
                    ticker: "CTRL".into(),
                    as_of: NaiveDate::from_ymd_opt(2026, 6, 30).unwrap(),
                    market_cap: 80.0e9,
                    revenue_ttm: 60.0e9,
                    segments: vec![RevenueSegment {
                        name: "Industrial".into(),
                        revenue: 60.0e9,
                        tags: vec![],
                    }],
                    gross_margin: Some(0.3),
                },
                0.0,
            ),
        ];
        hub.seed = 7;
        hub
    }

    fn dates(&self) -> Vec<NaiveDate> {
        let start = NaiveDate::from_ymd_opt(2025, 7, 1).unwrap();
        (0..self.days as i64)
            .map(|i| start + chrono::Duration::days(i))
            .collect()
    }

    /// The driver signal: a slow sinusoid plus noise, in "sentiment index"
    /// units. Deterministic per seed.
    fn driver_values(&self) -> Vec<f64> {
        let mut rng = Prng(self.seed.wrapping_mul(0x9E3779B97F4A7C15) | 1);
        (0..self.days)
            .map(|i| {
                let t = i as f64;
                50.0 + 20.0 * (t / 40.0).sin() + 6.0 * rng.next_f64()
            })
            .collect()
    }

    fn market_returns(&self) -> Vec<f64> {
        let mut rng = Prng(self.seed.wrapping_mul(0xD1B54A32D192ED03) | 1);
        (0..self.days).map(|_| 0.0003 + 0.02 * rng.next_f64()).collect()
    }
}

impl DataHub for MockDataHub {
    fn screen(&self, criteria: &ScreenCriteria) -> Result<Vec<CompanyRef>> {
        Ok(self
            .universe
            .iter()
            .filter(|(c, f, _)| matches_criteria(c, &f.segments, criteria))
            .map(|(c, _, _)| c.clone())
            .collect())
    }

    fn fundamentals(&self, ticker: &str) -> Result<FundamentalsSnapshot> {
        self.universe
            .iter()
            .find(|(c, _, _)| c.ticker == ticker)
            .map(|(_, f, _)| f.clone())
            .ok_or_else(|| HypothesisError::Data(format!("unknown ticker {ticker}")))
    }

    fn prices(&self, ticker: &str) -> Result<Series> {
        let (_, _, beta) = self
            .universe
            .iter()
            .find(|(c, _, _)| c.ticker == ticker)
            .ok_or_else(|| HypothesisError::Data(format!("unknown ticker {ticker}")))?;
        let dates = self.dates();
        let market = self.market_returns();
        let driver = self.driver_values();
        // Per-ticker idiosyncratic noise, deterministic.
        let mut rng = Prng(
            ticker
                .bytes()
                .fold(self.seed | 1, |acc, b| acc.wrapping_mul(131).wrapping_add(b as u64)),
        );
        let mut price = 100.0;
        let mut points = vec![(dates[0], price)];
        for i in 1..self.days {
            // Return = market beta 1.0 + driver sensitivity on driver change + noise.
            let driver_chg = (driver[i] - driver[i - 1]) / 100.0;
            let r = market[i] + beta * driver_chg + 0.01 * rng.next_f64();
            price *= 1.0 + r;
            points.push((dates[i], price));
        }
        Ok(Series::new(ticker, points))
    }

    fn benchmark(&self) -> Result<Series> {
        let dates = self.dates();
        let market = self.market_returns();
        let mut price = 1000.0;
        let mut points = vec![(dates[0], price)];
        for i in 1..self.days {
            price *= 1.0 + market[i];
            points.push((dates[i], price));
        }
        Ok(Series::new("BENCHMARK", points))
    }

    fn signal(&self, id: &str) -> Result<Series> {
        let dates = self.dates();
        Ok(Series::new(
            id,
            dates.into_iter().zip(self.driver_values()).collect(),
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mock_hub_screens_by_keyword() {
        let hub = MockDataHub::pharma_demo();
        let crit = ScreenCriteria {
            keywords: vec!["epidemic".into()],
            ..Default::default()
        };
        let hits = hub.screen(&crit).unwrap();
        let tickers: Vec<_> = hits.iter().map(|c| c.ticker.as_str()).collect();
        assert!(tickers.contains(&"VAXA"));
        assert!(tickers.contains(&"CURX"));
        assert!(!tickers.contains(&"GENC"));
    }

    #[test]
    fn series_align_inner_joins_on_date() {
        let d = |day: u32| NaiveDate::from_ymd_opt(2026, 1, day).unwrap();
        let a = Series::new("a", vec![(d(1), 1.0), (d(2), 2.0), (d(3), 3.0)]);
        let b = Series::new("b", vec![(d(2), 20.0), (d(3), 30.0), (d(4), 40.0)]);
        let (x, y) = a.align(&b);
        assert_eq!(x, vec![2.0, 3.0]);
        assert_eq!(y, vec![20.0, 30.0]);
    }

    #[test]
    fn mock_prices_are_deterministic() {
        let hub = MockDataHub::pharma_demo();
        let p1 = hub.prices("VAXA").unwrap();
        let p2 = hub.prices("VAXA").unwrap();
        assert_eq!(p1, p2);
        assert_eq!(p1.len(), 260);
    }
}
