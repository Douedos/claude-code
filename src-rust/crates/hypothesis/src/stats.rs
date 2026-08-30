// Statistical building blocks for the hypothesis engine.
//
// Everything here is dependency-free (hand-rolled OLS via normal equations
// with Gaussian elimination) because the factor counts involved are tiny
// (market + a handful of factors + the driver).

use serde::{Deserialize, Serialize};

/// Result of an ordinary-least-squares fit `y = a + b1*x1 + ... + bk*xk`.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OlsFit {
    /// Coefficients, intercept first.
    pub coefs: Vec<f64>,
    /// t-statistics parallel to `coefs`.
    pub t_stats: Vec<f64>,
    pub r_squared: f64,
    pub residuals: Vec<f64>,
    pub n_obs: usize,
}

/// Fit OLS with intercept. `xs` is a list of regressor columns, each the
/// same length as `y`. Returns None when the system is degenerate or the
/// sample is too small for inference.
pub fn ols(y: &[f64], xs: &[Vec<f64>]) -> Option<OlsFit> {
    let n = y.len();
    let k = xs.len() + 1; // + intercept
    if n < k + 2 || xs.iter().any(|x| x.len() != n) {
        return None;
    }

    // Design matrix row i: [1, x1[i], ..., xk[i]]
    let row = |i: usize| -> Vec<f64> {
        let mut r = Vec::with_capacity(k);
        r.push(1.0);
        for x in xs {
            r.push(x[i]);
        }
        r
    };

    // Normal equations: (X'X) b = X'y
    let mut xtx = vec![vec![0.0; k]; k];
    let mut xty = vec![0.0; k];
    for i in 0..n {
        let r = row(i);
        for a in 0..k {
            xty[a] += r[a] * y[i];
            for b in 0..k {
                xtx[a][b] += r[a] * r[b];
            }
        }
    }

    let xtx_inv = invert(&xtx)?;
    let mut coefs = vec![0.0; k];
    for a in 0..k {
        for b in 0..k {
            coefs[a] += xtx_inv[a][b] * xty[b];
        }
    }

    // Residuals and fit statistics.
    let y_mean = y.iter().sum::<f64>() / n as f64;
    let mut ss_res = 0.0;
    let mut ss_tot = 0.0;
    let mut residuals = Vec::with_capacity(n);
    for i in 0..n {
        let r = row(i);
        let fitted: f64 = r.iter().zip(coefs.iter()).map(|(a, b)| a * b).sum();
        let e = y[i] - fitted;
        residuals.push(e);
        ss_res += e * e;
        ss_tot += (y[i] - y_mean).powi(2);
    }
    let dof = (n - k) as f64;
    let sigma2 = ss_res / dof;
    let t_stats = (0..k)
        .map(|a| {
            let se = (sigma2 * xtx_inv[a][a]).sqrt();
            if se > f64::EPSILON {
                coefs[a] / se
            } else {
                0.0
            }
        })
        .collect();
    let r_squared = if ss_tot > f64::EPSILON {
        1.0 - ss_res / ss_tot
    } else {
        0.0
    };

    Some(OlsFit {
        coefs,
        t_stats,
        r_squared,
        residuals,
        n_obs: n,
    })
}

/// Invert a small symmetric positive-definite matrix via Gauss-Jordan.
fn invert(m: &[Vec<f64>]) -> Option<Vec<Vec<f64>>> {
    let n = m.len();
    let mut a: Vec<Vec<f64>> = m.iter().cloned().collect();
    let mut inv = vec![vec![0.0; n]; n];
    for (i, r) in inv.iter_mut().enumerate() {
        r[i] = 1.0;
    }
    for col in 0..n {
        // Partial pivot.
        let mut pivot = col;
        for r in (col + 1)..n {
            if a[r][col].abs() > a[pivot][col].abs() {
                pivot = r;
            }
        }
        if a[pivot][col].abs() < 1e-12 {
            return None;
        }
        a.swap(col, pivot);
        inv.swap(col, pivot);
        let p = a[col][col];
        for j in 0..n {
            a[col][j] /= p;
            inv[col][j] /= p;
        }
        for r in 0..n {
            if r != col {
                let f = a[r][col];
                for j in 0..n {
                    a[r][j] -= f * a[col][j];
                    inv[r][j] -= f * inv[col][j];
                }
            }
        }
    }
    Some(inv)
}

pub fn mean(xs: &[f64]) -> f64 {
    if xs.is_empty() {
        return 0.0;
    }
    xs.iter().sum::<f64>() / xs.len() as f64
}

pub fn std_dev(xs: &[f64]) -> f64 {
    if xs.len() < 2 {
        return 0.0;
    }
    let m = mean(xs);
    (xs.iter().map(|x| (x - m).powi(2)).sum::<f64>() / (xs.len() - 1) as f64).sqrt()
}

/// Pearson correlation.
pub fn correlation(x: &[f64], y: &[f64]) -> f64 {
    if x.len() != y.len() || x.len() < 2 {
        return 0.0;
    }
    let (mx, my) = (mean(x), mean(y));
    let mut num = 0.0;
    let mut dx = 0.0;
    let mut dy = 0.0;
    for i in 0..x.len() {
        num += (x[i] - mx) * (y[i] - my);
        dx += (x[i] - mx).powi(2);
        dy += (y[i] - my).powi(2);
    }
    let den = (dx * dy).sqrt();
    if den > f64::EPSILON {
        num / den
    } else {
        0.0
    }
}

/// Correlation of `y` against `x` shifted by each lag in `[-max_lag, max_lag]`.
/// A positive best lag means x leads y by that many periods — the basis of
/// the price-response horizon estimate.
pub fn lead_lag_correlations(x: &[f64], y: &[f64], max_lag: usize) -> Vec<(i64, f64)> {
    let n = x.len().min(y.len());
    let mut out = Vec::new();
    for lag in -(max_lag as i64)..=(max_lag as i64) {
        let mut xv = Vec::new();
        let mut yv = Vec::new();
        for i in 0..n as i64 {
            let j = i + lag;
            if j >= 0 && (j as usize) < n {
                xv.push(x[i as usize]);
                yv.push(y[j as usize]);
            }
        }
        if xv.len() > 10 {
            out.push((lag, correlation(&xv, &yv)));
        }
    }
    out
}

/// The lag with the largest absolute correlation.
pub fn best_lag(x: &[f64], y: &[f64], max_lag: usize) -> Option<(i64, f64)> {
    lead_lag_correlations(x, y, max_lag)
        .into_iter()
        .max_by(|a, b| a.1.abs().partial_cmp(&b.1.abs()).unwrap_or(std::cmp::Ordering::Equal))
}

/// Half-life (in periods) of deviations of a series from its mean, from an
/// AR(1) fit. None when the series is non-mean-reverting (rho >= 1) or the
/// fit is degenerate.
pub fn half_life(series: &[f64]) -> Option<f64> {
    if series.len() < 20 {
        return None;
    }
    let m = mean(series);
    let dev: Vec<f64> = series.iter().map(|v| v - m).collect();
    let y: Vec<f64> = dev[1..].to_vec();
    let x: Vec<f64> = dev[..dev.len() - 1].to_vec();
    let fit = ols(&y, &[x])?;
    let rho = fit.coefs[1];
    if rho <= 0.0 || rho >= 1.0 {
        return None;
    }
    Some((0.5f64).ln() / rho.ln())
}

/// Cumulative-abnormal-return event study. `abnormal_returns` is the
/// residual return series; `event_indices` marks the event dates; the CAR is
/// accumulated over `window` periods after each event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventStudy {
    pub mean_car: f64,
    pub t_stat: f64,
    pub n_events: usize,
    pub window: usize,
}

pub fn event_study(abnormal_returns: &[f64], event_indices: &[usize], window: usize) -> Option<EventStudy> {
    let mut cars = Vec::new();
    for &e in event_indices {
        let end = e + window;
        if end < abnormal_returns.len() {
            cars.push(abnormal_returns[e..end].iter().sum::<f64>());
        }
    }
    if cars.len() < 2 {
        return None;
    }
    let m = mean(&cars);
    let s = std_dev(&cars);
    let t = if s > f64::EPSILON {
        m / (s / (cars.len() as f64).sqrt())
    } else {
        0.0
    };
    Some(EventStudy {
        mean_car: m,
        t_stat: t,
        n_events: cars.len(),
        window,
    })
}

/// Indices where a series spikes above `z` standard deviations of its
/// period-over-period change — used to locate driver "events".
pub fn spike_indices(values: &[f64], z: f64) -> Vec<usize> {
    if values.len() < 3 {
        return Vec::new();
    }
    let diffs: Vec<f64> = values.windows(2).map(|w| w[1] - w[0]).collect();
    let s = std_dev(&diffs);
    if s < f64::EPSILON {
        return Vec::new();
    }
    let m = mean(&diffs);
    diffs
        .iter()
        .enumerate()
        .filter(|(_, d)| (**d - m) / s > z)
        .map(|(i, _)| i + 1)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ols_recovers_known_coefficients() {
        // y = 2 + 3x, exactly.
        let x: Vec<f64> = (0..50).map(|i| i as f64).collect();
        let y: Vec<f64> = x.iter().map(|v| 2.0 + 3.0 * v).collect();
        let fit = ols(&y, &[x]).unwrap();
        assert!((fit.coefs[0] - 2.0).abs() < 1e-8);
        assert!((fit.coefs[1] - 3.0).abs() < 1e-8);
        assert!(fit.r_squared > 0.9999);
    }

    #[test]
    fn ols_two_regressors() {
        let x1: Vec<f64> = (0..100).map(|i| (i as f64 * 0.7).sin()).collect();
        let x2: Vec<f64> = (0..100).map(|i| (i as f64 * 0.13).cos()).collect();
        let y: Vec<f64> = (0..100).map(|i| 1.0 + 2.0 * x1[i] - 4.0 * x2[i]).collect();
        let fit = ols(&y, &[x1, x2]).unwrap();
        assert!((fit.coefs[1] - 2.0).abs() < 1e-6);
        assert!((fit.coefs[2] + 4.0).abs() < 1e-6);
    }

    #[test]
    fn ols_rejects_degenerate_input() {
        let x = vec![1.0; 30];
        let y = vec![2.0; 30];
        // Constant column collinear with intercept.
        assert!(ols(&y, &[x]).is_none());
    }

    #[test]
    fn half_life_of_ar1_process() {
        // x_t = 0.9 x_{t-1} + deterministic small shock
        let mut x = vec![10.0];
        for i in 1..300 {
            let shock = ((i as f64) * 1.7).sin() * 0.5;
            x.push(0.9 * x[i - 1] + shock);
        }
        let hl = half_life(&x).unwrap();
        // Theoretical: ln(0.5)/ln(0.9) ~ 6.58
        assert!((hl - 6.58).abs() < 2.0, "half-life {hl} not near 6.58");
    }

    #[test]
    fn lead_lag_finds_shift() {
        let x: Vec<f64> = (0..200).map(|i| (i as f64 / 10.0).sin()).collect();
        // y lags x by 5 periods: y[i] = x[i-5]
        let y: Vec<f64> = (0..200)
            .map(|i| if i >= 5 { x[i - 5] } else { 0.0 })
            .collect();
        let (lag, corr) = best_lag(&x, &y, 10).unwrap();
        assert_eq!(lag, 5);
        assert!(corr > 0.95);
    }

    #[test]
    fn spike_indices_finds_jumps() {
        let mut v = vec![0.0; 50];
        v[20] = 10.0; // jump at index 20
        for i in 21..50 {
            v[i] = 10.0;
        }
        let spikes = spike_indices(&v, 2.0);
        assert_eq!(spikes, vec![20]);
    }
}
