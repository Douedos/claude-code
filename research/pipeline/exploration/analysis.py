#!/usr/bin/env python3
"""Exploration-grade analysis on the validated country panel.

Pre-declared specification family (all runs logged to search_ledger.json;
the headline permutation p is max-stat corrected across the family):

  A. AI Integration Surprise (AIS) residual models, outcome = Q1 2026 diffusion
     A1  level  ~ log gdp_pc
     A2  logit  ~ log gdp_pc                      (primary functional form)
     A3  logit  ~ log gdp_pc + log pop
     A4  logit  ~ log gdp_pc + log pop + region FE  (PRIMARY; skeleton D4 subset)
     A5  Spearman rank correlation (robustness)
     AIS is the JACKKNIFE (leave-one-out) residual of A4 — no observation
     scores its own fit (cross-fitting requirement of skeleton 4.1).

  B. Diffusion dynamics H1 2025 -> Q1 2026 (three quarters)
     B1  d_pp   ~ initial level                    (pp divergence test)
     B2  d_pp   ~ log gdp_pc
     B3  d_pp   ~ initial + log gdp_pc
     B4  log growth ratio ~ log initial            (proportional convergence)

  Inference: permutation p (10k label shuffles, seed=20260825) per spec,
  plus family-wide max-stat p for the headline dynamic claim; leave-one-
  country-out ranges for every headline coefficient.

Grade: EXPLORATORY under the project's evidence ladder. No causal claims.
"""
import csv, json, math, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NPERM = 10000

rows = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k):
    return float(r[k]) if r[k] not in ("", "None") else None

data = [r for r in rows if all(f(r, k) is not None for k in
        ("h1_2025", "q1_2026", "gdp_pc", "pop"))]
iso = [r["iso3"] for r in data]
econ = [r["economy"] for r in data]
q1 = np.array([f(r, "q1_2026") for r in data])
h1 = np.array([f(r, "h1_2025") for r in data])
lgdp = np.log(np.array([f(r, "gdp_pc") for r in data]))
lpop = np.log(np.array([f(r, "pop") for r in data]))
region = [r["region"] for r in data]
regions = sorted(set(region))
N = len(data)
logit = lambda p: np.log(p / (1 - p))
y_logit = logit(q1 / 100.0)
d_pp = q1 - h1
g_log = np.log(q1 / h1)

ledger = []

def ols(y, X, names):
    Xd = np.column_stack([np.ones(len(y))] + list(X))
    beta, res, rank, sv = np.linalg.lstsq(Xd, y, rcond=None)
    yhat = Xd @ beta
    e = y - yhat
    dof = len(y) - Xd.shape[1]
    s2 = e @ e / dof
    XtXinv = np.linalg.inv(Xd.T @ Xd)
    se = np.sqrt(np.diag(XtXinv) * s2)
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    # HC1 robust SE
    u = Xd * e[:, None]
    meat = u.T @ u * len(y) / dof
    hc1 = np.sqrt(np.diag(XtXinv @ meat @ XtXinv))
    return dict(beta=beta, se=se, hc1=hc1, r2=r2, resid=e, X=Xd, names=["const"] + names)

def perm_p(y, X, names, focal, nperm=NPERM):
    """Permutation p for the focal regressor's coefficient (shuffle focal column)."""
    m = ols(y, X, names)
    j = m["names"].index(focal)
    obs = m["beta"][j]
    cnt = 0
    Xl = [np.array(x, dtype=float) for x in X]
    fi = names.index(focal)
    for _ in range(nperm):
        Xp = list(Xl)
        Xp[fi] = rng.permutation(Xl[fi])
        b = ols(y, Xp, names)["beta"][j]
        if abs(b) >= abs(obs): cnt += 1
    return obs, (cnt + 1) / (nperm + 1), m

def loco(y, X, names, focal):
    j = names.index(focal) + 1
    coefs = []
    for i in range(len(y)):
        mask = np.ones(len(y), bool); mask[i] = False
        m = ols(y[mask], [x[mask] for x in X], names)
        coefs.append(m["beta"][j])
    return dict(min=float(np.min(coefs)), max=float(np.max(coefs)),
                argmin=iso[int(np.argmin(coefs))], argmax=iso[int(np.argmax(coefs))])

def region_dummies():
    return [np.array([1.0 if r == g else 0.0 for r in region]) for g in regions[1:]], \
           [f"reg_{g}" for g in regions[1:]]

# ---------- A. AIS models ----------
res = {}
m1 = ols(q1, [lgdp], ["lgdp"]);            ledger.append(dict(spec="A1", dep="level", coef_lgdp=float(m1["beta"][1]), r2=float(m1["r2"])))
m2 = ols(y_logit, [lgdp], ["lgdp"]);       ledger.append(dict(spec="A2", dep="logit", coef_lgdp=float(m2["beta"][1]), r2=float(m2["r2"])))
m3 = ols(y_logit, [lgdp, lpop], ["lgdp", "lpop"])
ledger.append(dict(spec="A3", dep="logit", coef_lgdp=float(m3["beta"][1]), coef_lpop=float(m3["beta"][2]), r2=float(m3["r2"])))
rd, rn = region_dummies()
m4 = ols(y_logit, [lgdp, lpop] + rd, ["lgdp", "lpop"] + rn)
ledger.append(dict(spec="A4_PRIMARY", dep="logit", coef_lgdp=float(m4["beta"][1]),
                   coef_lpop=float(m4["beta"][2]), r2=float(m4["r2"])))
from scipy.stats import spearmanr, rankdata
rho, rho_p = spearmanr(q1, lgdp)
ledger.append(dict(spec="A5_rank", spearman_rho=float(rho), p=float(rho_p)))

# jackknife AIS from A4 (leave-one-out residual, standard hat-matrix identity)
X4 = m4["X"]; H = X4 @ np.linalg.inv(X4.T @ X4) @ X4.T
ais = m4["resid"] / (1 - np.diag(H))
order = np.argsort(-ais)
league = [dict(iso3=iso[i], economy=econ[i], ais_logit=float(ais[i]),
               q1_2026=float(q1[i]), gdp_pc=float(math.exp(lgdp[i])))
          for i in order]
res["ais_top15"] = league[:15]
res["ais_bottom15"] = league[-15:]
res["A4"] = dict(coef_lgdp=float(m4["beta"][1]), hc1_lgdp=float(m4["hc1"][1]),
                 coef_lpop=float(m4["beta"][2]), hc1_lpop=float(m4["hc1"][2]),
                 r2=float(m4["r2"]), n=N)
res["A2_elasticity"] = dict(coef_lgdp=float(m2["beta"][1]), hc1=float(m2["hc1"][1]), r2=float(m2["r2"]))
res["A5_rank"] = dict(rho=float(rho), p=float(rho_p))
res["loco_A4_lgdp"] = loco(y_logit, [lgdp, lpop] + rd, ["lgdp", "lpop"] + rn, "lgdp")

# ---------- B. dynamics ----------
b_res = {}
obs1, p1, mb1 = perm_p(d_pp, [h1], ["init"], "init")
b_res["B1"] = dict(coef_init=float(obs1), perm_p=float(p1), r2=float(mb1["r2"]),
                   loco=loco(d_pp, [h1], ["init"], "init"))
ledger.append(dict(spec="B1", coef_init=float(obs1), perm_p=float(p1)))
obs2, p2, mb2 = perm_p(d_pp, [lgdp], ["lgdp"], "lgdp")
b_res["B2"] = dict(coef_lgdp=float(obs2), perm_p=float(p2), r2=float(mb2["r2"]),
                   loco=loco(d_pp, [lgdp], ["lgdp"], "lgdp"))
ledger.append(dict(spec="B2", coef_lgdp=float(obs2), perm_p=float(p2)))
obs3, p3, mb3 = perm_p(d_pp, [h1, lgdp], ["init", "lgdp"], "init")
b_res["B3"] = dict(coef_init=float(obs3), coef_lgdp=float(mb3["beta"][2]),
                   perm_p_init=float(p3), r2=float(mb3["r2"]),
                   loco=loco(d_pp, [h1, lgdp], ["init", "lgdp"], "init"))
ledger.append(dict(spec="B3", coef_init=float(obs3), perm_p=float(p3)))
obs4, p4, mb4 = perm_p(g_log, [np.log(h1)], ["linit"], "linit")
b_res["B4"] = dict(coef_linit=float(obs4), perm_p=float(p4), r2=float(mb4["r2"]),
                   loco=loco(g_log, [np.log(h1)], ["linit"], "linit"))
ledger.append(dict(spec="B4", coef_linit=float(obs4), perm_p=float(p4)))

# ---------- family-wide max-stat correction for the headline dynamic claim ----
# The headline is B1 (pp divergence). Null: reshuffle country labels of the
# initial-level/gdp regressors jointly; recompute all four dynamic t-stats;
# compare the max |t| to the observed max |t| across the family.
def tstat(y, X, names, focal):
    m = ols(y, X, names); j = m["names"].index(focal)
    return m["beta"][j] / m["hc1"][j]
specs = [(d_pp, [h1], ["init"], "init"),
         (d_pp, [lgdp], ["lgdp"], "lgdp"),
         (d_pp, [h1, lgdp], ["init", "lgdp"], "init"),
         (g_log, [np.log(h1)], ["linit"], "linit")]
obs_ts = [abs(tstat(*s)) for s in specs]
obs_max = max(obs_ts)
cnt = 0
for _ in range(2000):
    perm = rng.permutation(N)
    mx = 0.0
    for y, X, names, focal in specs:
        Xp = [x[perm] for x in X]
        mx = max(mx, abs(tstat(y, Xp, names, focal)))
    if mx >= obs_max: cnt += 1
res["max_stat"] = dict(observed_max_abs_t=float(obs_max),
                       per_spec_abs_t=[float(t) for t in obs_ts],
                       p_search=float((cnt + 1) / 2001),
                       family_size=len(specs), nperm=2000)
res["B"] = b_res
res["n"] = N
res["dropped_for_missing_covariates"] = [r["iso3"] for r in rows if r not in data]

json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=2)
json.dump(ledger, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps({k: v for k, v in res.items() if k not in ("ais_top15", "ais_bottom15")}, indent=2))
print("\nAIS TOP 10 (over-adopters given income/size/region):")
for r in res["ais_top15"][:10]:
    print(f"  {r['economy']:<22} AIS={r['ais_logit']:+.3f}  adoption={r['q1_2026']:.1f}%  gdp_pc=${r['gdp_pc']:,.0f}")
print("AIS BOTTOM 10 (under-adopters):")
for r in res["ais_bottom15"][-10:]:
    print(f"  {r['economy']:<22} AIS={r['ais_logit']:+.3f}  adoption={r['q1_2026']:.1f}%  gdp_pc=${r['gdp_pc']:,.0f}")
