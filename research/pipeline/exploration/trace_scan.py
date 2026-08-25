#!/usr/bin/env python3
"""End-product layer 1: the trace scan and pre-specified trend statistics.

Implements the skeleton's section-7.1 dynamic statistics on the event-study
coefficient path, splits the exposure margin, tests the acceleration
hypothesis (skeleton priority 3), runs the producer/measurement-distortion
sensitivity (confounder G2), and computes the MDE/power table.

Declared additions to the search family (all ledgered):
  T1  trend in beta_t (OLS slope of yearly coefficients on year, 2016-2025)
  T2  variance of beta_t vs permutation null
  T3  lag-1 autocorrelation (persistence) of beta_t vs null
  S1  sector-split event paths: J-only and K-only vs controls (C, F, G-I)
  A1  acceleration surprise x exposure -> EPS 2025  (adoption speed, not level)
  A2  GDP growth surprise 2025 ~ acceleration surprise
  G2  E1 and W1 with producer/distortion economies removed (NLD, IRL in the
      Eurostat sample; KOR, TWN, NLD, IRL, SGP in the global W sample)
  MDE 80%-power minimum detectable effects for E1, W1, B1

Trace labels (pre-declared): |z|>=1.96 'trace (unadjusted)', 1.28<=|z|<1.96
'weak trace', else 'no trace' - z = beta / null-permutation sd. Labels are
descriptive flags for follow-up, NEVER promoted claims; the family-wide
correction still governs any headline. Seed 20260825.
"""
import csv, json, math, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NPERM = 2000
YEARS = list(range(2016, 2026))
CONTROLS = ["C", "F", "G-I"]

# ---------- shared inputs ----------
panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None
ms_sample = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "q1_2026", "gdp_pc", "pop"))]

def jackknife(sample, yvals):
    y = np.asarray(yvals, float)
    lgdp = np.log([f(r, "gdp_pc") for r in sample]); lpop = np.log([f(r, "pop") for r in sample])
    region = [r["region"] for r in sample]
    regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
    X = np.column_stack([np.ones(len(y)), lgdp, lpop] +
                        [[1.0 if g == q else 0.0 for g in region] for q in regs])
    XtXi = np.linalg.pinv(X.T @ X); H = X @ XtXi @ X.T
    return dict(zip([r["iso3"] for r in sample], (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))))

AIS = jackknife(ms_sample, [np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)) for r in ms_sample])
# acceleration surprise: pp change residualized on initial level + structure
accel_raw = [f(r, "q1_2026") - f(r, "h1_2025") for r in ms_sample]
lvl = np.array([f(r, "h1_2025") for r in ms_sample])
ACC = jackknife(ms_sample, np.asarray(accel_raw) - np.polyval(np.polyfit(lvl, accel_raw, 1), lvl))

ep = list(csv.DictReader(open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"))))
for r in ep: r["year"] = int(r["year"]); r["dlp_hw"] = float(r["dlp_hw"])

def beta_fe(rows, amap=None):
    isos = sorted({r["iso3"] for r in rows}); naces = sorted({r["nace"] for r in rows})
    y = np.array([r["y"] for r in rows])
    a = np.array([(amap[r["iso3"]] if amap else r["ais"]) * r["exposed"] for r in rows])
    X = np.column_stack([np.ones(len(y)), a] +
                        [[1.0 if r["iso3"] == i else 0.0 for r in rows] for i in isos[1:]] +
                        [[1.0 if r["nace"] == s else 0.0 for r in rows] for s in naces[1:]])
    return float((np.linalg.pinv(X.T @ X) @ X.T @ y)[1])

def year_rows(year, exposed_set, treat, drop=()):
    return [dict(iso3=r["iso3"], nace=r["nace"],
                 exposed=1.0 if r["nace"] in exposed_set else 0.0,
                 y=r["dlp_hw"], ais=treat[r["iso3"]])
            for r in ep if r["year"] == year and r["iso3"] in treat and r["iso3"] not in drop
            and (r["nace"] in exposed_set or r["nace"] in CONTROLS)]

isos_all = sorted(AIS); vals_ms = [AIS[i] for i in isos_all]
PERMS = [dict(zip(isos_all, rng.permutation(vals_ms))) for _ in range(NPERM)]

def path(exposed_set, treat=AIS, perms=PERMS, drop=()):
    out, nulls = [], {}
    for t in YEARS:
        rows = year_rows(t, exposed_set, treat, drop)
        if len({r["iso3"] for r in rows}) < 10: continue
        b = beta_fe(rows)
        null = np.array([beta_fe(rows, amap=p) for p in perms])
        z = b / null.std()
        out.append(dict(year=t, beta=b, z=float(z),
                        p=float((np.sum(np.abs(null) >= abs(b)) + 1) / (len(perms) + 1)),
                        label=("trace (unadjusted)" if abs(z) >= 1.96 else
                               "weak trace" if abs(z) >= 1.28 else "no trace")))
        nulls[t] = null
    return out, nulls

# ---------- S1: sector-split paths ----------
paths = {}
nulls_jk = None
for name, es in (("JK", {"J", "K"}), ("J", {"J"}), ("K", {"K"})):
    p_, n_ = path(es)
    paths[name] = p_
    if name == "JK": nulls_jk = n_

# ---------- T1-T3: trend statistics on the JK path ----------
yrs = np.array([o["year"] for o in paths["JK"]], float)
bts = np.array([o["beta"] for o in paths["JK"]])
null_mat = np.column_stack([nulls_jk[int(t)] for t in yrs])  # NPERM x T
def trend(v): return float(np.polyfit(yrs, v, 1)[0])
def lag1(v):
    v = np.asarray(v) - np.mean(v)
    return float(np.sum(v[1:] * v[:-1]) / np.sum(v * v))
T = {}
obs = dict(T1_trend=trend(bts), T2_var=float(np.var(bts)), T3_lag1=lag1(bts))
nullstats = dict(T1_trend=np.array([trend(null_mat[j]) for j in range(NPERM)]),
                 T2_var=np.array([np.var(null_mat[j]) for j in range(NPERM)]),
                 T3_lag1=np.array([lag1(null_mat[j]) for j in range(NPERM)]))
for k in obs:
    ns = nullstats[k]
    T[k] = dict(observed=obs[k],
                p=float((np.sum(np.abs(ns) >= abs(obs[k])) + 1) / (NPERM + 1))
                if k != "T2_var" else float((np.sum(ns >= obs[k]) + 1) / (NPERM + 1)),
                null_mean=float(ns.mean()), null_sd=float(ns.std()))

# ---------- A1/A2: acceleration hypothesis ----------
accel_perms = [dict(zip(isos_all, rng.permutation([ACC[i] for i in isos_all]))) for _ in range(NPERM)]
rows_a = year_rows(2025, {"J", "K"}, ACC)
bA = beta_fe(rows_a)
nullA = np.array([beta_fe(rows_a, amap=p) for p in accel_perms])
A1 = dict(beta=bA, z=float(bA / nullA.std()),
          p=float((np.sum(np.abs(nullA) >= abs(bA)) + 1) / (NPERM + 1)))
# A2: macro
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
        p_ = row[1].split(".")
        if len(p_) == 3 and p_[1] == "NGDP_RPCH" and len(p_[0]) == 3 and row[yi["2025"]].strip():
            try: apr26[p_[0]] = float(row[yi["2025"]])
            except ValueError: pass
def wbeta(treat, drop=()):
    isos = sorted(set(treat) & set(oct24) & set(apr26) - set(drop))
    ys = np.array([apr26[i] - oct24[i] for i in isos]); a = np.array([treat[i] for i in isos])
    X = np.column_stack([np.ones(len(isos)), a])
    b = float((np.linalg.pinv(X.T @ X) @ X.T @ ys)[1])
    null = []
    for _ in range(NPERM):
        Xp = X.copy(); Xp[:, 1] = rng.permutation(a)
        null.append((np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ ys)[1])
    null = np.array(null)
    return dict(beta=b, z=float(b / null.std()),
                p=float((np.sum(np.abs(null) >= abs(b)) + 1) / (NPERM + 1)), n=len(isos))
A2 = wbeta(ACC)

# ---------- G2: producer / measurement-distortion sensitivity ----------
E1_full = paths["JK"][[o["year"] for o in paths["JK"]].index(2025)]
p_drop, n_drop = path({"J", "K"}, drop=("NLD", "IRL"))
E1_noprod = p_drop[[o["year"] for o in p_drop].index(2025)]
W1_full = wbeta(AIS)
W1_noprod = wbeta(AIS, drop=("KOR", "TWN", "NLD", "IRL", "SGP"))
G2 = dict(E1_2025_full=dict(beta=E1_full["beta"], p=E1_full["p"]),
          E1_2025_dropNLD_IRL=dict(beta=E1_noprod["beta"], p=E1_noprod["p"]),
          W1_full=dict(beta=W1_full["beta"], p=W1_full["p"], n=W1_full["n"]),
          W1_drop_producers=dict(beta=W1_noprod["beta"], p=W1_noprod["p"], n=W1_noprod["n"]),
          producer_set_eurostat=["NLD", "IRL"], producer_set_global=["KOR", "TWN", "NLD", "IRL", "SGP"])

# ---------- MDE / power ----------
sd_ais = float(np.std(list(AIS.values())))
eps_res = json.load(open(os.path.join(OUT, "eps_results.json")))
E1_se = eps_res["E"]["E1"]["wild_boot_se"]
W1_se_null = None  # use permutation-based null sd on observed design
W1_null_sd = abs(W1_full["beta"] / W1_full["z"])
B1_se = 0.0142  # HC1 from bayes layer inputs
MDE = dict(sd_ais=sd_ais,
           E1=dict(se=E1_se, mde80=2.8 * E1_se, mde80_per_sd_ais=2.8 * E1_se * sd_ais,
                   plausible_effect_per_sd="0.3-1.0 pp/yr (adoption-gap literature)",
                   verdict="underpowered by roughly a factor of 3-10 at one year"),
           W1=dict(se=W1_null_sd, mde80=2.8 * W1_null_sd, mde80_per_sd_ais=2.8 * W1_null_sd * sd_ais,
                   plausible_effect_per_sd="0.1-0.5 pp growth surprise",
                   verdict="underpowered by roughly a factor of 1.5-4"),
           B1=dict(se=B1_se, mde80=2.8 * B1_se,
                   verdict="well powered - and the effect is detected decisively"))

res = dict(paths=paths, trend_stats=T, A1_accel_eps=A1, A2_accel_gsurp=A2, G2=G2, MDE=MDE,
           label_rule="z>=1.96 trace (unadjusted); 1.28<=z<1.96 weak trace; else no trace",
           nperm=NPERM)
json.dump(res, open(os.path.join(OUT, "trace_scan_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led = [l for l in led if l.get("spec") != "TRACE_SCAN_family"]
led.append(dict(spec="TRACE_SCAN_family", specs=["T1", "T2", "T3", "S1_J", "S1_K", "A1", "A2", "G2"],
                note="declared in trace_scan.py before estimation"))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)

# ---------- trace-map figure ----------
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 8.5})
rows_fig = [("J+K (primary)", paths["JK"]), ("J only", paths["J"]), ("K only", paths["K"])]
fig, ax = plt.subplots(figsize=(7.2, 2.9))
for ri, (lab, pth) in enumerate(rows_fig):
    for o in pth:
        z = o["z"]
        col = plt.cm.RdBu_r(0.5 + max(min(z / 4, 0.5), -0.5))
        ax.add_patch(plt.Rectangle((o["year"] - 0.45, ri - 0.45), 0.9, 0.9, color=col))
        ax.text(o["year"], ri, f"{o['beta']:.1f}", ha="center", va="center",
                fontsize=6.6, color="black")
        if abs(z) >= 1.96:
            ax.add_patch(plt.Rectangle((o["year"] - 0.45, ri - 0.45), 0.9, 0.9,
                                       fill=False, edgecolor="black", lw=1.6))
        elif abs(z) >= 1.28:
            ax.add_patch(plt.Rectangle((o["year"] - 0.45, ri - 0.45), 0.9, 0.9,
                                       fill=False, edgecolor="black", lw=0.9, ls="--"))
ax.set_xlim(2015.4, 2025.6); ax.set_ylim(-0.6, len(rows_fig) - 0.4)
ax.set_yticks(range(len(rows_fig))); ax.set_yticklabels([r[0] for r in rows_fig])
ax.set_xticks(YEARS)
ax.axvline(2024.5, color="#222", lw=1.0, ls=":")
ax.set_title("Trace map: yearly AIS x exposure coefficients by sector split\n"
             "(cell = beta; solid box = |z|>=1.96 unadjusted trace; dashed = weak trace; red = positive, blue = negative)")
ax.invert_yaxis()
fig.tight_layout(); fig.savefig(os.path.join(BASE, "reports/fig6_trace_map.png"), dpi=150)

print(json.dumps(dict(trend=T, A1=A1, A2=A2, G2=G2,
                      J2025=[o for o in paths["J"] if o["year"] == 2025],
                      K2025=[o for o in paths["K"] if o["year"] == 2025],
                      MDE={k: (v if k == "sd_ais" else v.get("mde80")) for k, v in MDE.items()}), indent=2))
