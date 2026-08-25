#!/usr/bin/env python3
"""White-collar denominator layer (closes the occupational-mix confounder, D3/D4).

Declared specs (ledgered before estimation):
  WC1  Does white-collar share (ISCO 1-4) predict adoption beyond income/size/
       region? Coefficient + R2 gain in the AIS residual model; ISCO 1-3
       sensitivity.
  WC2  AIS stability: corr(AIS v1, AIS v2 with wc-share covariate); league-
       table movement (max |rank change|).
  WC3  E1 2025 re-run with AIS v2 (does the occupational control change the
       priority-1 null?)
  WC4  W1 growth-surprise re-run with AIS v2.
  WC5  Professional-intensity margin (Axis A): PI = adoption share of
       working-age population / white-collar share of employment (approx.,
       employment-based share; declared). PI-surprise = jackknife residual of
       log PI on structure; W-branch test with PI-surprise.
Seed 20260825. Grade: EXPLORATORY.
"""
import csv, json, os
import numpy as np
from scipy.stats import spearmanr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NPERM = 10000

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r.get(k) not in ("", "None", None) else None

S = [r for r in panel if all(f(r, k) is not None for k in
     ("h1_2025", "gdp_pc", "pop", "wc14_share"))]
iso = [r["iso3"] for r in S]; N = len(S)
y_ms = np.array([np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)) for r in S])
lgdp = np.log([f(r, "gdp_pc") for r in S]); lpop = np.log([f(r, "pop") for r in S])
wc14 = np.array([f(r, "wc14_share") for r in S])
wc13 = np.array([f(r, "wc13_share") for r in S])
region = [r["region"] for r in S]
regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
RD = [[1.0 if g == q else 0.0 for g in region] for q in regs]

def fit(y, cols):
    X = np.column_stack([np.ones(len(y))] + cols)
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ X.T @ y
    e = y - X @ b
    r2 = 1 - e @ e / ((y - y.mean()) @ (y - y.mean()))
    u = X * e[:, None]
    hc1 = np.sqrt(np.diag(XtXi @ (u.T @ u * len(y) / (len(y) - X.shape[1])) @ XtXi))
    H = X @ XtXi @ X.T
    return b, hc1, float(r2), e / (1 - np.diag(H))

b0, se0, r2_0, ais_v1 = fit(y_ms, [lgdp, lpop] + RD)
b1, se1, r2_1, ais_v2 = fit(y_ms, [lgdp, lpop, wc14] + RD)
b13, se13, r2_13, _ = fit(y_ms, [lgdp, lpop, wc13] + RD)
j = 3  # index of wc coefficient (const, lgdp, lpop, wc)
WC1 = dict(coef_wc14=float(b1[j]), hc1=float(se1[j]), r2_without=r2_0, r2_with=r2_1,
           r2_gain=r2_1 - r2_0, coef_wc13=float(b13[j]), hc1_wc13=float(se13[j]),
           n=N, note="wc coef = logit-adoption per unit white-collar share")

rank1 = np.argsort(np.argsort(-ais_v1)); rank2 = np.argsort(np.argsort(-ais_v2))
moves = {iso[i]: int(rank1[i] - rank2[i]) for i in range(N)}
big = sorted(moves.items(), key=lambda kv: -abs(kv[1]))[:5]
WC2 = dict(corr_ais_v1_v2=float(np.corrcoef(ais_v1, ais_v2)[0, 1]),
           spearman=float(spearmanr(ais_v1, ais_v2)[0]),
           largest_rank_moves=big)

AIS_V2 = dict(zip(iso, ais_v2))

# ---- WC3: E1 2025 with AIS v2 ----
ep = list(csv.DictReader(open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"))))
for r in ep: r["year"] = int(r["year"]); r["dlp_hw"] = float(r["dlp_hw"])
base = {}
for r in ep:
    if 2015 <= r["year"] <= 2019: base.setdefault((r["iso3"], r["nace"]), []).append(r["dlp_hw"])
B = {k: float(np.mean(v)) for k, v in base.items() if len(v) >= 3}
SECT = {"J": 1, "K": 1, "C": 0, "F": 0, "G-I": 0}
rows25 = [dict(iso3=r["iso3"], nace=r["nace"], exposed=float(SECT[r["nace"]]),
               eps=r["dlp_hw"] - B[(r["iso3"], r["nace"])], ais=AIS_V2[r["iso3"]])
          for r in ep if r["year"] == 2025 and r["nace"] in SECT
          and (r["iso3"], r["nace"]) in B and r["iso3"] in AIS_V2]

def ibeta(rows, amap=None):
    isos = sorted({r["iso3"] for r in rows}); naces = sorted({r["nace"] for r in rows})
    y = np.array([r["eps"] for r in rows])
    a = np.array([(amap[r["iso3"]] if amap else r["ais"]) * r["exposed"] for r in rows])
    X = np.column_stack([np.ones(len(y)), a] +
                        [[1.0 if r["iso3"] == i else 0.0 for r in rows] for i in isos[1:]] +
                        [[1.0 if r["nace"] == s else 0.0 for r in rows] for s in naces[1:]])
    return float((np.linalg.pinv(X.T @ X) @ X.T @ y)[1])

bE = ibeta(rows25)
vals = sorted({r["iso3"] for r in rows25})
avals = [AIS_V2[i] for i in vals]
cnt = 0
for _ in range(NPERM):
    if abs(ibeta(rows25, amap=dict(zip(vals, rng.permutation(avals))))) >= abs(bE): cnt += 1
WC3 = dict(beta=bE, perm_p=(cnt + 1) / (NPERM + 1),
           n_countries=len(vals), comparison_v1_beta=-2.636)

# ---- WC4 / WC5: W-branch ----
oct24, apr26 = {}, {}
with open(os.path.join(BASE, "raw/S12_WEOOct2024all.tsv"), encoding="utf-16-le", errors="replace") as fh:
    rdr = csv.reader(fh, delimiter="\t"); hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        if len(row) > 10 and row[2] == "NGDP_RPCH" and row[1]:
            v = row[yi["2025"]].replace(",", "").strip()
            if v and v not in ("n/a", "--"):
                try: oct24[row[1]] = float(v)
                except ValueError: pass
with open(os.path.join(BASE, "raw/S11_WEO_Apr2026_portal.csv"), encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh); hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        p = row[1].split(".")
        if len(p) == 3 and p[1] == "NGDP_RPCH" and len(p[0]) == 3 and row[yi["2025"]].strip():
            try: apr26[p[0]] = float(row[yi["2025"]])
            except ValueError: pass

def wtest(treat):
    isos = sorted(set(treat) & set(oct24) & set(apr26))
    ys = np.array([apr26[i] - oct24[i] for i in isos]); a = np.array([treat[i] for i in isos])
    X = np.column_stack([np.ones(len(isos)), a])
    b = float((np.linalg.pinv(X.T @ X) @ X.T @ ys)[1])
    cnt = 0
    for _ in range(NPERM):
        Xp = X.copy(); Xp[:, 1] = rng.permutation(a)
        if abs((np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ ys)[1]) >= abs(b): cnt += 1
    return dict(beta=b, perm_p=(cnt + 1) / (NPERM + 1), n=len(isos))

WC4 = wtest(AIS_V2); WC4["comparison_v1"] = dict(beta=-0.273, perm_p=0.50)

# WC5: professional intensity
pi = np.array([f(r, "h1_2025") for r in S]) / wc14  # adoption per unit wc-share (approx PI)
_, _, _, pi_resid = fit(np.log(pi), [lgdp, lpop] + RD)
PI_S = dict(zip(iso, pi_resid))
WC5 = dict(w_test=wtest(PI_S),
           top5_pi=[iso[i] for i in np.argsort(-pi)[:5]],
           corr_pi_surprise_vs_ais=float(np.corrcoef(pi_resid, ais_v1)[0, 1]),
           note="PI = working-age adoption share / white-collar employment share (approx)")

res = dict(WC1=WC1, WC2=WC2, WC3=WC3, WC4=WC4, WC5=WC5, n_sample=N)
json.dump(res, open(os.path.join(OUT, "wc_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led = [l for l in led if l.get("spec") != "WC_family"]
led.append(dict(spec="WC_family", specs=["WC1", "WC2", "WC3", "WC4", "WC5"],
                results=dict(WC1_coef=WC1["coef_wc14"], WC2_corr=WC2["corr_ais_v1_v2"],
                             WC3_beta=WC3["beta"], WC4_beta=WC4["beta"],
                             WC5_beta=WC5["w_test"]["beta"])))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(res, indent=2))
