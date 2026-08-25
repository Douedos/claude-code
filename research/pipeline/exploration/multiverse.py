#!/usr/bin/env python3
"""The normalization multiverse (R-family), thresholds (N-family) and the
resilience variant of H6 (X-family). Reproduces, from raw versioned data, the
skeleton's H0/H1 qualitative lesson: the choice of denominator changes country
rankings and can change the apparent relationship - which is why inference
uses residualized surprises and ratios stay descriptive (frozen answers D1/D2).

Declared metrics (adoption, per country):
  R1  raw share            Microsoft H1'25 AI user share (% of working-age)
  R2  logit share          logit(R1/100)  - functional form for a bounded share
  R3  users per $ GDP      R1 x population / GDP           [log]
  R4  users per white-collar worker  R1 x population / WC14 [log]
  R5  Claude usage per capita        AEI count / population [log]
  R6  Claude usage per $ GDP         AEI count / GDP        [log]
  R7  AIS (primary)        jackknife residual of R2 on log GDPpc + log pop + region

Declared tests:
  R-corr   Spearman correlation matrix across metrics
  R-rank   top-5 economies per metric (ranking instability exhibit)
  R-spec   specification curve: for each metric (z-scored), association with
           (a) diffusion divergence (d_pp on metric) and (b) 2025 growth
           surprise; 2000 permutations each
  N1       divergence nonlinearity: quadratic term in initial level
  N2       EPS-2025 effect split by AIS median (threshold-style)
  X1       |growth surprise| ~ AIS + log gdp (resilience: do integrated
           economies deviate less from forecast?)
  X2       variance ratio of growth surprises, high- vs low-AIS halves
Seed 20260825. Grade: EXPLORATORY. All results ledgered.
"""
import csv, json, os
import numpy as np
from scipy.stats import spearmanr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NP = 2000

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r.get(k) not in ("", "None", None) else None
ISO2TO3 = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/X02_country_codes.csv"), encoding="utf-8-sig")):
    a2, a3 = r.get("ISO3166-1-Alpha-2", "").strip(), r.get("ISO3166-1-Alpha-3", "").strip()
    if a2 and a3: ISO2TO3[a2] = a3
aei = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/S04a_aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv"))):
    if r["geography"] == "country" and r["variable"] == "usage_count" and r["geo_id"] != "not_classified":
        i3 = ISO2TO3.get(r["geo_id"])
        if i3: aei[i3] = float(r["value"])

# base sample: countries with MS + covariates
S = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "q1_2026", "gdp_pc", "pop"))]
iso = [r["iso3"] for r in S]
h1 = np.array([f(r, "h1_2025") for r in S]); q1 = np.array([f(r, "q1_2026") for r in S])
pop = np.array([f(r, "pop") for r in S]); gdp = np.array([f(r, "gdp_usd") for r in S])
lgdpc = np.log(np.array([f(r, "gdp_pc") for r in S])); lpop = np.log(pop)
region = [r["region"] for r in S]
regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
X = np.column_stack([np.ones(len(h1)), lgdpc, lpop] + [[1.0 if g == q else 0.0 for g in region] for q in regs])
XtXi = np.linalg.pinv(X.T @ X); H = X @ XtXi @ X.T
ylog = np.log((h1 / 100) / (1 - h1 / 100))
ais = (ylog - X @ (XtXi @ X.T @ ylog)) / (1 - np.diag(H))
wc = np.array([f(r, "wc14_thousands") if f(r, "wc14_thousands") else np.nan for r in S])
aei_v = np.array([aei.get(i, np.nan) for i in iso])
aei_v[aei_v < 50] = np.nan  # min-usage floor as in crossprovider

METRICS = {
 "R1 raw share": h1,
 "R2 logit share": ylog,
 "R3 users per $GDP": np.log(h1 * pop / gdp),
 "R4 users per white-collar": np.log(h1 * pop / (wc * 1000)),
 "R5 Claude per capita": np.log(aei_v / pop),
 "R6 Claude per $GDP": np.log(aei_v / gdp),
 "R7 AIS (primary)": ais,
}

# ---- R-corr: Spearman matrix ----
names = list(METRICS)
corr = np.full((len(names), len(names)), np.nan)
for i, a in enumerate(names):
    for j, b in enumerate(names):
        m = ~np.isnan(METRICS[a]) & ~np.isnan(METRICS[b])
        if m.sum() > 10:
            corr[i, j] = spearmanr(METRICS[a][m], METRICS[b][m])[0]

# ---- R-rank: top-5 per metric ----
top5 = {}
for a in names:
    v = METRICS[a]
    order = np.argsort(np.where(np.isnan(v), -np.inf, v))[::-1][:5]
    top5[a] = [iso[k] for k in order]

# ---- outcomes ----
dpp = q1 - h1
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
gsur = np.array([apr26.get(i, np.nan) - oct24.get(i, np.nan)
                 if i in apr26 and i in oct24 else np.nan for i in iso])

def assoc(metric, outcome):
    m = ~np.isnan(metric) & ~np.isnan(outcome)
    x = metric[m]; y = outcome[m]
    z = (x - x.mean()) / x.std()
    b = float(np.polyfit(z, y, 1)[0])
    cnt = 0
    for _ in range(NP):
        bp = np.polyfit(rng.permutation(z), y, 1)[0]
        if abs(bp) >= abs(b): cnt += 1
    return dict(beta_per_sd=b, perm_p=(cnt + 1) / (NP + 1), n=int(m.sum()))

spec_curve = {}
for a in names:
    spec_curve[a] = dict(divergence=assoc(METRICS[a], dpp),
                         growth_surprise=assoc(METRICS[a], gsur))

# ---- N1: divergence nonlinearity (quadratic in initial level) ----
z = (h1 - h1.mean()) / h1.std()
Xq = np.column_stack([np.ones(len(z)), z, z ** 2])
bq = np.linalg.pinv(Xq.T @ Xq) @ Xq.T @ dpp
cnt = 0
for _ in range(NP):
    perm = rng.permutation(len(z))
    Xp = np.column_stack([np.ones(len(z)), z[perm], z[perm] ** 2])
    bp = (np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ dpp)[2]
    if abs(bp) >= abs(bq[2]): cnt += 1
N1 = dict(quad_coef=float(bq[2]), lin_coef=float(bq[1]), perm_p_quad=(cnt + 1) / (NP + 1))
# quartile means (descriptive)
qcut = np.quantile(h1, [0.25, 0.5, 0.75])
N1["quartile_mean_gain_pp"] = [float(dpp[(h1 <= qcut[0])].mean()),
                               float(dpp[(h1 > qcut[0]) & (h1 <= qcut[1])].mean()),
                               float(dpp[(h1 > qcut[1]) & (h1 <= qcut[2])].mean()),
                               float(dpp[h1 > qcut[2]].mean())]

# ---- N2: EPS-2025 effect by AIS half ----
ep = list(csv.DictReader(open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"))))
for r in ep: r["year"] = int(r["year"]); r["dlp_hw"] = float(r["dlp_hw"])
base = {}
for r in ep:
    if 2015 <= r["year"] <= 2019: base.setdefault((r["iso3"], r["nace"]), []).append(r["dlp_hw"])
B = {k: float(np.mean(v)) for k, v in base.items() if len(v) >= 3}
AIS_D = dict(zip(iso, ais))
SECT = {"J": 1, "K": 1, "C": 0, "F": 0, "G-I": 0}
rows25 = [dict(iso3=r["iso3"], nace=r["nace"], exposed=float(SECT[r["nace"]]),
               eps=r["dlp_hw"] - B[(r["iso3"], r["nace"])], ais=AIS_D[r["iso3"]])
          for r in ep if r["year"] == 2025 and r["nace"] in SECT
          and (r["iso3"], r["nace"]) in B and r["iso3"] in AIS_D]
med = float(np.median([AIS_D[i] for i in {r["iso3"] for r in rows25}]))
def did_half(hi):
    e = [r["eps"] for r in rows25 if (r["ais"] > med) == hi and r["exposed"] == 1]
    c = [r["eps"] for r in rows25 if (r["ais"] > med) == hi and r["exposed"] == 0]
    return float(np.mean(e) - np.mean(c))
obs_n2 = did_half(True) - did_half(False)
isoset = sorted({r["iso3"] for r in rows25}); avals = [AIS_D[i] for i in isoset]
cnt = 0
for _ in range(NP):
    shuf = dict(zip(isoset, rng.permutation(avals)))
    m2 = float(np.median(list(shuf.values())))
    def dh(hi):
        e = [r["eps"] for r in rows25 if (shuf[r["iso3"]] > m2) == hi and r["exposed"] == 1]
        c = [r["eps"] for r in rows25 if (shuf[r["iso3"]] > m2) == hi and r["exposed"] == 0]
        return np.mean(e) - np.mean(c)
    if abs(dh(True) - dh(False)) >= abs(obs_n2): cnt += 1
N2 = dict(did_high_minus_low=obs_n2, perm_p=(cnt + 1) / (NP + 1),
          did_high=did_half(True), did_low=did_half(False))

# ---- X: resilience ----
m = ~np.isnan(gsur)
absg = np.abs(gsur[m]); a_m = ais[m]; lg = lgdpc[m]
Xr = np.column_stack([np.ones(m.sum()), a_m, lg])
br = np.linalg.pinv(Xr.T @ Xr) @ Xr.T @ absg
cnt = 0
for _ in range(NP):
    Xp = Xr.copy(); Xp[:, 1] = rng.permutation(a_m)
    bp = (np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ absg)[1]
    if abs(bp) >= abs(br[1]): cnt += 1
X1 = dict(beta_ais=float(br[1]), perm_p=(cnt + 1) / (NP + 1), n=int(m.sum()))
medA = np.median(a_m)
vr = float(np.var(gsur[m][a_m > medA]) / np.var(gsur[m][a_m <= medA]))
cnt = 0
for _ in range(NP):
    pm = rng.permutation(a_m)
    v2 = np.var(gsur[m][pm > medA]) / np.var(gsur[m][pm <= medA])
    if abs(np.log(v2)) >= abs(np.log(vr)): cnt += 1
X2 = dict(variance_ratio_high_over_low=vr, perm_p=(cnt + 1) / (NP + 1))

res = dict(metrics=names,
           spearman_matrix={a: {b: (None if np.isnan(corr[i, j]) else round(float(corr[i, j]), 3))
                                for j, b in enumerate(names)} for i, a in enumerate(names)},
           top5=top5, spec_curve=spec_curve, N1=N1, N2=N2, X1=X1, X2=X2)
json.dump(res, open(os.path.join(OUT, "multiverse_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led = [l for l in led if l.get("spec") not in ("R_family", "N_family", "X_family")]
led.append(dict(spec="R_family", note="normalization multiverse; reproduces skeleton step 6 H0/H1 lesson",
                metrics=names))
led.append(dict(spec="N_family", N1=N1["quad_coef"], N2=N2["did_high_minus_low"]))
led.append(dict(spec="X_family", X1=X1["beta_ais"], X2=X2["variance_ratio_high_over_low"]))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(dict(top5=top5, N1=N1, N2=N2, X1=X1, X2=X2), indent=2))
print("\nSPEC CURVE:")
for a in names:
    d, g = spec_curve[a]["divergence"], spec_curve[a]["growth_surprise"]
    print(f"  {a:<28} div: {d['beta_per_sd']:+.2f} (p={d['perm_p']:.3f}, n={d['n']})   "
          f"gsurp: {g['beta_per_sd']:+.2f} (p={g['perm_p']:.3f}, n={g['n']})")
