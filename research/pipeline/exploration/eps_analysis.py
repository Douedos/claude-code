#!/usr/bin/env python3
"""Priority-1 branch: AIS x sector exposure -> productivity surprise (EPS),
plus the WEO growth-surprise branch (H3). All specs pre-declared here and
appended to the search ledger. Grade: EXPLORATORY.

E-branch (Eurostat, country x sector, outcome year 2025; 2019/2023/2024 placebo years)
  EPS_i,s,t = dlp_hw_i,s,t - mean(dlp_hw_i,s,2015..2019)      [pre-AI baseline]
  E1  EPS_i,s,2025 = a_i + d_s + b (AIS_MS_i x Exposed_s) + e   [PRIMARY]
      Exposed: J,K = 1; C,F,G-I = 0. M excluded (6/31 coverage), E1m includes it.
  E2  same, AIS from Anthropic AEI (H4 cross-provider check on b)
  E3  placebo years: 2019 (pre-AI), 2023 (pre-measurement), 2024
  Inference: country-permutation p (10k), wild cluster bootstrap SE (5k,
  Rademacher by country), leave-one-country-out range. Identification is
  within-country cross-sector (country FE absorb AIS main effects).

W-branch (IMF WEO, country level)
  gsurp_i = NGDP_RPCH_2025 [Apr 2026 vintage] - NGDP_RPCH_2025 [Oct 2024 forecast]
  W1  gsurp ~ AIS_MS          W1c  gsurp ~ AIS_MS + log gdp_pc
  W2  gsurp ~ AIS_AEI
  W3  placebo: gsurp_2024 (realized largely before the H1'25 adoption
      measurement) ~ AIS_MS

Headline correction: max-stat permutation across {E1, E2, W1, W1c, W2}.
Seed 20260825 throughout.
"""
import csv, json, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)

# ---------------- AIS (both providers), full-sample jackknife ----------------
panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None
ISO2TO3 = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/X02_country_codes.csv"), encoding="utf-8-sig")):
    a2, a3 = r.get("ISO3166-1-Alpha-2", "").strip(), r.get("ISO3166-1-Alpha-3", "").strip()
    if a2 and a3: ISO2TO3[a2] = a3
aei = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/S04a_aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv"))):
    if r["geography"] == "country" and r["variable"] == "usage_count" and r["geo_id"] != "not_classified":
        i3 = ISO2TO3.get(r["geo_id"])
        if i3: aei[i3] = float(r["value"])

def jackknife_ais(sample, yfun):
    iso = [r["iso3"] for r in sample]
    y = np.array([yfun(r) for r in sample])
    lgdp = np.log([f(r, "gdp_pc") for r in sample])
    lpop = np.log([f(r, "pop") for r in sample])
    region = [r["region"] for r in sample]
    regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
    X = np.column_stack([np.ones(len(y)), lgdp, lpop] +
                        [[1.0 if g == q else 0.0 for g in region] for q in regs])
    XtXi = np.linalg.pinv(X.T @ X)
    H = X @ XtXi @ X.T
    res = (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))
    return dict(zip(iso, res))

ms_sample = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "gdp_pc", "pop"))]
AIS_MS = jackknife_ais(ms_sample, lambda r: np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)))
aei_sample = [r for r in panel if r["iso3"] in aei and aei[r["iso3"]] >= 50
              and all(f(r, k) is not None for k in ("gdp_pc", "pop"))]
AIS_AEI = jackknife_ais(aei_sample, lambda r: np.log(aei[r["iso3"]] / f(r, "pop")))
LGDP = {r["iso3"]: np.log(f(r, "gdp_pc")) for r in panel if f(r, "gdp_pc") is not None}

# adoption-rank persistence (supports using H1'25 as the treatment period)
h1 = np.array([f(r, "h1_2025") for r in ms_sample])
q1 = np.array([f(r, "q1_2026") for r in ms_sample])
persistence_r = float(np.corrcoef(h1, q1)[0, 1])

# ---------------- E-branch ----------------
ep = list(csv.DictReader(open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"))))
for r in ep: r["year"] = int(r["year"]); r["dlp_hw"] = float(r["dlp_hw"])
base = {}
for r in ep:
    if 2015 <= r["year"] <= 2019:
        base.setdefault((r["iso3"], r["nace"]), []).append(r["dlp_hw"])
BASELINE = {k: float(np.mean(v)) for k, v in base.items() if len(v) >= 3}

def eps_rows(year, sectors, ais):
    rows = []
    for r in ep:
        if r["year"] != year or r["nace"] not in sectors: continue
        b = BASELINE.get((r["iso3"], r["nace"]))
        a = ais.get(r["iso3"])
        if b is None or a is None: continue
        rows.append(dict(iso3=r["iso3"], nace=r["nace"],
                         exposed=1.0 if r["nace"] in ("J", "K", "M") else 0.0,
                         eps=r["dlp_hw"] - b, ais=a))
    return rows

def interaction_beta(rows, ais_override=None):
    isos = sorted({r["iso3"] for r in rows})
    naces = sorted({r["nace"] for r in rows})
    amap = ais_override or {}
    y = np.array([r["eps"] for r in rows])
    inter = np.array([(amap.get(r["iso3"], r["ais"])) * r["exposed"] for r in rows])
    Xc = [[1.0 if r["iso3"] == i else 0.0 for r in rows] for i in isos[1:]]
    Xs = [[1.0 if r["nace"] == s else 0.0 for r in rows] for s in naces[1:]]
    X = np.column_stack([np.ones(len(y)), inter] + Xc + Xs)
    XtXi = np.linalg.pinv(X.T @ X)
    beta = XtXi @ X.T @ y
    e = y - X @ beta
    return float(beta[1]), y, X, e, XtXi, isos

def analyze(rows, label, nperm=10000, nboot=5000):
    b, y, X, e, XtXi, isos = interaction_beta(rows)
    # permutation: reshuffle AIS across countries
    vals = {r["iso3"]: r["ais"] for r in rows}
    ivals = [vals[i] for i in sorted(vals)]
    cnt = 0
    for _ in range(nperm):
        shuf = dict(zip(sorted(vals), rng.permutation(ivals)))
        bp, *_ = interaction_beta(rows, ais_override=shuf)
        if abs(bp) >= abs(b): cnt += 1
    perm_p = (cnt + 1) / (nperm + 1)
    # wild cluster bootstrap (null-imposed on beta): Rademacher by country
    Xr = X.copy(); Xr[:, 1] = 0  # restricted model w/o interaction
    br = np.linalg.pinv(Xr.T @ Xr) @ Xr.T @ y
    er = y - Xr @ br
    yr0 = Xr @ br
    cid = np.array([sorted(set(r["iso3"] for r in rows)).index(r["iso3"]) for r in rows])
    tb = []
    for _ in range(nboot):
        w = rng.choice([-1.0, 1.0], size=len(isos))
        yb = yr0 + er * w[cid]
        bb = (XtXi @ X.T @ yb)[1]
        tb.append(bb)
    boot_p = float(np.mean(np.abs(tb) >= abs(b)))
    boot_se = float(np.std(tb))
    # LOCO
    lo = []
    for i in isos:
        sub = [r for r in rows if r["iso3"] != i]
        lo.append(interaction_beta(sub)[0])
    return dict(spec=label, beta=b, perm_p=float(perm_p), wild_boot_p=boot_p,
                wild_boot_se=boot_se, n_obs=len(rows), n_countries=len(isos),
                loco_min=float(min(lo)), loco_max=float(max(lo)))

SECT = ["J", "K", "C", "F", "G-I"]
E = {}
E["E1"] = analyze(eps_rows(2025, SECT, AIS_MS), "E1_primary_2025_MS")
E["E1m"] = analyze(eps_rows(2025, SECT + ["M"], AIS_MS), "E1m_withM_2025_MS")
E["E2"] = analyze(eps_rows(2025, SECT, AIS_AEI), "E2_2025_AEI")
E["E3_2019"] = analyze(eps_rows(2019, SECT, AIS_MS), "E3_placebo_2019_MS")
E["E3_2023"] = analyze(eps_rows(2023, SECT, AIS_MS), "E3_placebo_2023_MS")
E["E4_2024"] = analyze(eps_rows(2024, SECT, AIS_MS), "E4_2024_MS")

# descriptive: mean EPS by exposure x AIS-half (readable diff-in-diff)
r25 = eps_rows(2025, SECT, AIS_MS)
med = float(np.median([v for v in {r["iso3"]: r["ais"] for r in r25}.values()]))
def cellmean(hi, ex):
    xs = [r["eps"] for r in r25 if (r["ais"] > med) == hi and r["exposed"] == ex]
    return float(np.mean(xs)) if xs else None
did = dict(hiAIS_exposed=cellmean(True, 1), hiAIS_control=cellmean(True, 0),
           loAIS_exposed=cellmean(False, 1), loAIS_control=cellmean(False, 0))
did["diff_in_diff"] = (did["hiAIS_exposed"] - did["hiAIS_control"]) - \
                      (did["loAIS_exposed"] - did["loAIS_control"])

# ---------------- W-branch ----------------
oct24_f25, oct24_f24 = {}, {}
with open(os.path.join(BASE, "raw/S12_WEOOct2024all.tsv"), encoding="utf-16-le", errors="replace") as fh:
    rdr = csv.reader(fh, delimiter="\t")
    hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        if len(row) > 10 and row[2] == "NGDP_RPCH" and row[1]:
            for tgt, col in ((oct24_f25, "2025"), (oct24_f24, "2024")):
                v = row[yi[col]].replace(",", "").strip()
                if v and v not in ("n/a", "--"):
                    try: tgt[row[1]] = float(v)
                    except ValueError: pass
apr26_a25, apr26_a24 = {}, {}
with open(os.path.join(BASE, "raw/S11_WEO_Apr2026_portal.csv"), encoding="utf-8-sig") as fh:
    rdr = csv.reader(fh)
    hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
    for row in rdr:
        parts = row[1].split(".")
        if len(parts) == 3 and parts[1] == "NGDP_RPCH" and len(parts[0]) == 3:
            for tgt, col in ((apr26_a25, "2025"), (apr26_a24, "2024")):
                v = row[yi[col]].strip()
                if v:
                    try: tgt[parts[0]] = float(v)
                    except ValueError: pass

def wspec(label, ais, target_actual, target_fcst, income_control=False):
    isos = sorted(set(ais) & set(target_actual) & set(target_fcst) &
                  (set(LGDP) if income_control else set(ais)))
    ysur = np.array([target_actual[i] - target_fcst[i] for i in isos])
    a = np.array([ais[i] for i in isos])
    cols = [a] + ([np.array([LGDP[i] for i in isos])] if income_control else [])
    X = np.column_stack([np.ones(len(isos))] + cols)
    XtXi = np.linalg.pinv(X.T @ X)
    beta = XtXi @ X.T @ ysur
    b = float(beta[1])
    cnt = 0
    for _ in range(10000):
        Xp = X.copy(); Xp[:, 1] = rng.permutation(a)
        bp = (np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ ysur)[1]
        if abs(bp) >= abs(b): cnt += 1
    lo = []
    for j in range(len(isos)):
        m = np.ones(len(isos), bool); m[j] = False
        lo.append(float((np.linalg.pinv(X[m].T @ X[m]) @ X[m].T @ ysur[m])[1]))
    return dict(spec=label, beta=b, perm_p=(cnt + 1) / 10001, n=len(isos),
                loco_min=min(lo), loco_max=max(lo),
                mean_surprise=float(ysur.mean()))

W = {}
W["W1"] = wspec("W1_gsurp2025_MS", AIS_MS, apr26_a25, oct24_f25)
W["W1c"] = wspec("W1c_gsurp2025_MS_income", AIS_MS, apr26_a25, oct24_f25, income_control=True)
W["W2"] = wspec("W2_gsurp2025_AEI", AIS_AEI, apr26_a25, oct24_f25)
W["W3"] = wspec("W3_placebo_gsurp2024_MS", AIS_MS, apr26_a24, oct24_f24)

# ---------------- family max-stat for the headline ----------------
# family: E1, E2, W1, W1c, W2 (placebos excluded by design). Null: permute AIS
# labels once per draw, recompute all five, take max |beta/se_proxy| via
# rank-scale: use |beta|/loco-range-free scale -> use permutation max of |beta|
# standardized by each spec's own permutation sd.
def perm_family(ndraw=1000):
    r25s = eps_rows(2025, SECT, AIS_MS)
    r25a = eps_rows(2025, SECT, AIS_AEI)
    vals_ms = {r["iso3"]: r["ais"] for r in r25s}
    obs = {}
    sds = {}
    draws = {k: [] for k in ("E1", "E2", "W1", "W1c", "W2")}
    for _ in range(ndraw):
        shuf_ms = dict(zip(sorted(AIS_MS), rng.permutation(list(AIS_MS.values()))))
        shuf_ae = dict(zip(sorted(AIS_AEI), rng.permutation(list(AIS_AEI.values()))))
        draws["E1"].append(interaction_beta(r25s, ais_override=shuf_ms)[0])
        draws["E2"].append(interaction_beta(r25a, ais_override=shuf_ae)[0])
        for key, ais_s in (("W1", shuf_ms), ("W1c", shuf_ms), ("W2", shuf_ae)):
            isos = sorted(set(ais_s) & set(apr26_a25) & set(oct24_f25) & set(LGDP))
            ysur = np.array([apr26_a25[i] - oct24_f25[i] for i in isos])
            a = np.array([ais_s[i] for i in isos])
            cols = [a] + ([np.array([LGDP[i] for i in isos])] if key == "W1c" else [])
            X = np.column_stack([np.ones(len(isos))] + cols)
            draws[key].append(float((np.linalg.pinv(X.T @ X) @ X.T @ ysur)[1]))
    obs = dict(E1=E["E1"]["beta"], E2=E["E2"]["beta"], W1=W["W1"]["beta"],
               W1c=W["W1c"]["beta"], W2=W["W2"]["beta"])
    sds = {k: float(np.std(v)) or 1.0 for k, v in draws.items()}
    obs_max = max(abs(obs[k]) / sds[k] for k in obs)
    null_max = [max(abs(draws[k][j]) / sds[k] for k in draws) for j in range(ndraw)]
    return dict(observed_max_std_beta=float(obs_max),
                p_search=float((sum(1 for m in null_max if m >= obs_max) + 1) / (ndraw + 1)),
                family=["E1", "E2", "W1", "W1c", "W2"], ndraw=ndraw,
                per_spec_std_beta={k: abs(obs[k]) / sds[k] for k in obs})

MS_FAM = perm_family()

res = dict(persistence_h1_q1=persistence_r, E=E, did_2025=did, W=W, family=MS_FAM,
           n_ais_ms=len(AIS_MS), n_ais_aei=len(AIS_AEI))
json.dump(res, open(os.path.join(OUT, "eps_results.json"), "w"), indent=2)
ledger = json.load(open(os.path.join(OUT, "search_ledger.json")))
for k, v in {**E, **W}.items():
    ledger.append(dict(v))
ledger.append(dict(spec="EW_family_maxstat", **{k: v for k, v in MS_FAM.items() if k != "per_spec_std_beta"}))
json.dump(ledger, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(res, indent=2))
