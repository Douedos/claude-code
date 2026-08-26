#!/usr/bin/env python3
"""DAG-guided conditioning audit (declared; ledgered as DAG_audit).

The income-gated-rate pattern (B5: growth rate ~ income | level, +0.017,
p=1e-4) APPEARS only under conditioning on the current adoption level. Under
the causal graph, level is a descendant of income and of the country's own
growth process, so conditioning on it is conditioning on a mediator/collider:
the pattern could in principle be manufactured rather than revealed. Two
calibrated null simulations quantify that risk:

  SIM-A (clean-measurement null): growth rates g_i are iid draws (no income
    link), levels are the OBSERVED levels (which correlate with income as in
    the data), increments are g_i x level_i. If conditioning on level alone
    manufactured an income-rate association, it would appear here.
  SIM-B (measurement-error null): additionally, both period levels are
    observed with independent multiplicative noise (3 and 5 percent),
    g_hat computed from noisy levels. Regression-to-the-mean in the noisy
    denominator can leak into the income coefficient through the
    income-level correlation - the realistic artifact channel.

For each: 2000 simulated worlds; record the income coefficient and its
|t|>2 rate in the g ~ income + log(level) regression; compare the observed
coefficient (+0.0171) against each null distribution.
Seed 20260825.
"""
import csv, json, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NSIM = 2000

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r.get(k) not in ("", "None", None) else None
S = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "q1_2026", "gdp_pc", "pop"))]
h1 = np.array([f(r, "h1_2025") for r in S]); q1 = np.array([f(r, "q1_2026") for r in S])
lgdp = np.log([f(r, "gdp_pc") for r in S])
g_obs = (q1 - h1) / h1
OBS_COEF = 0.0171
gbar, gsd = float(g_obs.mean()), float(g_obs.std())
N = len(h1)

def income_coef(g, lev):
    X = np.column_stack([np.ones(len(g)), lgdp, np.log(lev)])
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ X.T @ g
    e = g - X @ b
    se = np.sqrt(np.diag(XtXi) * (e @ e / (len(g) - 3)))
    return float(b[1]), float(b[1] / se[1])

def run_sim(noise_sd):
    coefs, tstats = [], []
    for _ in range(NSIM):
        g = rng.normal(gbar, gsd, N)              # iid rates: NO income link
        a1_true = h1
        a2_true = a1_true * (1 + g)
        if noise_sd > 0:
            a1o = a1_true * (1 + rng.normal(0, noise_sd, N))
            a2o = a2_true * (1 + rng.normal(0, noise_sd, N))
        else:
            a1o, a2o = a1_true, a2_true
        ghat = (a2o - a1o) / a1o
        b, t = income_coef(ghat, a1o)
        coefs.append(b); tstats.append(t)
    coefs = np.array(coefs); tstats = np.array(tstats)
    return dict(noise_sd=noise_sd,
                mean_income_coef=float(coefs.mean()),
                sd_income_coef=float(coefs.std()),
                q95_abs_coef=float(np.quantile(np.abs(coefs), 0.95)),
                false_positive_rate_t2=float(np.mean(np.abs(tstats) > 2)),
                p_observed_vs_null=float((np.sum(np.abs(coefs) >= abs(OBS_COEF)) + 1) / (NSIM + 1)))

res = dict(observed_income_coef=OBS_COEF,
           calibration=dict(n=N, mean_growth=gbar, sd_growth=gsd,
                            corr_income_loglevel=float(np.corrcoef(lgdp, np.log(h1))[0, 1])),
           SIM_A_clean=run_sim(0.0),
           SIM_B_noise3=run_sim(0.03),
           SIM_B_noise5=run_sim(0.05))
verdict = ("SURVIVES: the observed income-rate coefficient exceeds the 95th percentile of |coef| in every "
           "null world, including 5 percent measurement noise"
           if all(res[k]["q95_abs_coef"] < OBS_COEF for k in ("SIM_A_clean", "SIM_B_noise3", "SIM_B_noise5"))
           else "AT RISK: at least one null world produces coefficients of the observed size")
res["verdict"] = verdict
json.dump(res, open(os.path.join(OUT, "dag_audit_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led = [l for l in led if l.get("spec") != "DAG_audit_sim"]
led.append(dict(spec="DAG_audit_sim", **{k: v for k, v in res.items() if k != "calibration"}))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(res, indent=2))
