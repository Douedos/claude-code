#!/usr/bin/env python3
"""Bayesian layer over the executed results (the skeleton's section-3 framing,
now computed rather than narrated).

Method: for each headline estimate b with standard error se, compare
  H0: beta = 0                      (point null)
  H1: beta ~ N(0, tau^2)            (zero-centered effect-size prior)
via the Gaussian marginal likelihood ratio
  BF01 = N(b; 0, se^2) / N(b; 0, se^2 + tau^2)
(Kass & Raftery 1995; equivalent to Savage-Dickey for this conjugate case).
BF01 > 1 favors the null; BF01 ~ 1 means the data are UNINFORMATIVE at that
prior scale - the Bayesian statement of "underpowered at this horizon".

Three declared prior scales per family (skeptical / moderate / optimistic),
anchored before computation:
- E1 (EPS on AIS x exposure, units: pp productivity growth per logit-AIS):
  tau = 0.5 (J-curve prior: near-zero contemporaneous effects),
  1.5 (moderate), 3.0 (large immediate effect ~ scaled from the
  St. Louis Fed 3.2pp cumulative US-Europe differential).
- W1 (GDP growth surprise per logit-AIS): tau = 0.25 / 0.75 / 1.5.
- B1 (diffusion divergence, pp-gained per pp-initial): tau = 0.05 / 0.15 / 0.30.
- D2 (cross-provider AIS correlation, Fisher-z scale): tau_z = 0.1 / 0.3 / 0.6.

Posterior worked examples use Ioannidis-style pre-study odds: prior
P(effect) = 0.25 for outcome families (mechanism plausible, literature
mixed), 0.5 for the diffusion-dynamics family (S-curve theory predicts it).
Seed-free: all inputs are point statistics from prior pipeline stages.
"""
import csv, json, math, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")

eps = json.load(open(os.path.join(OUT, "eps_results.json")))
cp = json.load(open(os.path.join(OUT, "crossprovider_results.json")))
res_main = json.load(open(os.path.join(OUT, "results.json")))

def norm_pdf(x, s):
    return math.exp(-0.5 * (x / s) ** 2) / (s * math.sqrt(2 * math.pi))

def bf01(b, se, tau):
    return norm_pdf(b, se) / norm_pdf(b, math.sqrt(se * se + tau * tau))

def posterior_p_effect(bf01_val, prior_p):
    """P(effect | data) from prior P(effect) and BF01 (null over effect)."""
    prior_odds = prior_p / (1 - prior_p)
    post_odds = prior_odds / bf01_val
    return post_odds / (1 + post_odds)

# ---- standard errors ----
# E1: wild-cluster bootstrap SE from eps_analysis
E1_b, E1_se = eps["E"]["E1"]["beta"], eps["E"]["E1"]["wild_boot_se"]
# W1 and B1: recompute analytic HC1 quickly
panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None

def hc1(y, x):
    X = np.column_stack([np.ones(len(y)), x])
    XtXi = np.linalg.pinv(X.T @ X)
    beta = XtXi @ X.T @ y
    e = y - X @ beta
    u = X * e[:, None]
    meat = u.T @ u * len(y) / (len(y) - 2)
    return float(beta[1]), float(np.sqrt(np.diag(XtXi @ meat @ XtXi))[1])

# W1 inputs (reuse WEO parses via eps ledger values; recompute from raw)
oct24, apr26 = {}, {}
with open(os.path.join(BASE, "raw/S12_WEOOct2024all.tsv"), encoding="utf-16-le", errors="replace") as fh:
    rdr = csv.reader(fh, delimiter="\t")
    hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        if len(row) > 10 and row[2] == "NGDP_RPCH" and row[1]:
            v = row[yi["2025"]].replace(",", "").strip()
            if v and v not in ("n/a", "--"):
                try: oct24[row[1]] = float(v)
                except ValueError: pass
with open(os.path.join(BASE, "raw/S11_WEO_Apr2026_portal.csv"), encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        p = row[1].split(".")
        if len(p) == 3 and p[1] == "NGDP_RPCH" and len(p[0]) == 3 and row[yi["2025"]].strip():
            try: apr26[p[0]] = float(row[yi["2025"]])
            except ValueError: pass

ISO_AIS = {}
ms_sample = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "gdp_pc", "pop"))]
y = np.array([np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)) for r in ms_sample])
lgdp = np.log([f(r, "gdp_pc") for r in ms_sample]); lpop = np.log([f(r, "pop") for r in ms_sample])
region = [r["region"] for r in ms_sample]
regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
X = np.column_stack([np.ones(len(y)), lgdp, lpop] + [[1.0 if g == q else 0.0 for g in region] for q in regs])
XtXi = np.linalg.pinv(X.T @ X); H = X @ XtXi @ X.T
ISO_AIS = dict(zip([r["iso3"] for r in ms_sample], (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))))

isos = sorted(set(ISO_AIS) & set(oct24) & set(apr26))
W1_b, W1_se = hc1(np.array([apr26[i] - oct24[i] for i in isos]),
                  np.array([ISO_AIS[i] for i in isos]))

# B1 divergence
h1 = np.array([f(r, "h1_2025") for r in ms_sample])
q1 = np.array([f(r, "q1_2026") for r in ms_sample])
B1_b, B1_se = hc1(q1 - h1, h1)

# D2 cross-provider correlation on Fisher z scale
r_d2, n_d2 = cp["D2"]["pearson_ais"], cp["n_joint"]
D2_z, D2_se = math.atanh(r_d2), 1 / math.sqrt(n_d2 - 3)

PRIORS = dict(E1=[0.5, 1.5, 3.0], W1=[0.25, 0.75, 1.5],
              B1=[0.05, 0.15, 0.30], D2=[0.1, 0.3, 0.6])
EST = dict(E1=(E1_b, E1_se), W1=(W1_b, W1_se), B1=(B1_b, B1_se), D2=(D2_z, D2_se))
PRIOR_P = dict(E1=0.25, W1=0.25, B1=0.50, D2=0.50)
LABELS = dict(E1="EPS 2025 ~ AIS x exposure (pp per logit-AIS)",
              W1="GDP growth surprise 2025 ~ AIS (pp per logit-AIS)",
              B1="Diffusion divergence (pp gained per pp initial)",
              D2="Cross-provider AIS agreement (Fisher z)")

bayes = {}
for k, (b, se) in EST.items():
    entry = dict(label=LABELS[k], estimate=b, se=se, prior_p_effect=PRIOR_P[k], scales={})
    for tau in PRIORS[k]:
        v = bf01(b, se, tau)
        entry["scales"][str(tau)] = dict(
            bf01=v, bf10=1 / v,
            posterior_p_effect=posterior_p_effect(v, PRIOR_P[k]))
    bayes[k] = entry

# hypothesis-ledger posterior directions (H0-H7), grounded in executed evidence
ledger_update = [
 dict(h="H0/H1 (AI -> stock returns, raw or normalized)", prior="low (demoted by skeleton)",
      evidence="not executed (market data unavailable)", posterior="unchanged (low)"),
 dict(h="H2 (AI level -> absolute GDP growth)", prior="low",
      evidence="W-branch null at h=0 consistent with it", posterior="slightly lower"),
 dict(h="H3 (AI -> GDP growth surprise)", prior="medium-low",
      evidence=f"W1: BF01={bayes['W1']['scales']['0.75']['bf01']:.1f} at moderate scale - mildly favors null at h=0",
      posterior="slightly lower at short horizons; untested at h>=1"),
 dict(h="H4 (AI -> knowledge-sector productivity)", prior="medium (priority 1 as H7 form)",
      evidence=f"E1: BF01={bayes['E1']['scales']['0.5']['bf01']:.2f} vs J-curve prior, "
               f"{bayes['E1']['scales']['3.0']['bf01']:.2f} vs large-immediate prior - BF ~ 1 at every scale",
      posterior="essentially unchanged: the h=0 test carried almost no information "
                "either way (SE too large even to rule out large immediate effects)"),
 dict(h="H5 (frozen exposure -> monthly services output)", prior="medium-low",
      evidence="not executed (sts_sepr_m not retrieved)", posterior="unchanged"),
 dict(h="H6 (shock-interaction / temporal rotation)", prior="medium",
      evidence="not executed (no identified-shock series yet)", posterior="unchanged"),
 dict(h="H7 (AIS -> productivity surprise; priority 1)", prior="medium",
      evidence="h=0 test uninformative by design (BF ~ 1 at J-curve scale); "
               "event study shows single-year noise floor; AEI variant carries pre-ChatGPT selection",
      posterior="essentially unchanged - the informative test is 2026-27 vintages"),
 dict(h="NEW: absolute diffusion divergence (levels)", prior="medium (S-curve predicts it)",
      evidence=f"B1: BF10={bayes['B1']['scales']['0.15']['bf10']:.0f} at moderate scale",
      posterior=f"~{bayes['B1']['scales']['0.15']['posterior_p_effect']:.3f} (near-certain at this scale)"),
 dict(h="NEW: single-provider AIS = national AI integration", prior="implicit high (v1.0 assumption)",
      evidence=f"D2: BF01={bayes['D2']['scales']['0.3']['bf01']:.2f} on agreement; "
               "AEI pre-trend p=0.007 shows provider-specific selection",
      posterior="demoted - reconciliation now core (C2)"),
]

out = dict(bayes_factors=bayes, hypothesis_ledger_update=ledger_update,
           method="Gaussian marginal likelihood BF (Kass-Raftery); "
                  "posteriors via pre-study odds (Ioannidis-style)")
json.dump(out, open(os.path.join(OUT, "bayes_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led.append(dict(spec="BAYES_layer", inputs={k: EST[k] for k in EST},
                priors=PRIORS, note="declared before computation; see bayes_layer.py"))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(out["bayes_factors"], indent=2))
