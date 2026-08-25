#!/usr/bin/env python3
"""Coverage-extension family (declared, ledgered):

  CV1  E1-2025 with WIDENED CONTROL SET: exposed {J,K} unchanged; controls
       extended from {C,F,G-I} to {C,D,F,G-I,S} using sectors already present
       in the retrieved Eurostat file. Raises within-country contrast
       (observations per country 5 -> 7) at zero data cost.
  CV2  Unemployment-rate surprise 2025 (WEO LUR: Apr-2026 actual minus
       Oct-2024 forecast) ~ AIS. A second macro outcome from files already
       ingested; labor-market margin of H3.
  CV3  Event-study window extended back to 2010 (JK vs widened controls) for
       longer pre-trend context - descriptive, no new claim.

Seed 20260825. Grade: EXPLORATORY. These are design changes relative to the
frozen protocol and do NOT modify it; the confirmatory test runs as frozen.
"""
import csv, json, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)
NPERM = 5000

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r.get(k) not in ("", "None", None) else None
ms = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "gdp_pc", "pop"))]
y = np.array([np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)) for r in ms])
lgdp = np.log([f(r, "gdp_pc") for r in ms]); lpop = np.log([f(r, "pop") for r in ms])
region = [r["region"] for r in ms]
regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
X = np.column_stack([np.ones(len(y)), lgdp, lpop] + [[1.0 if g == q else 0.0 for g in region] for q in regs])
XtXi = np.linalg.pinv(X.T @ X); H = X @ XtXi @ X.T
AIS = dict(zip([r["iso3"] for r in ms], (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))))

# staging kept only the 6 declared sectors; re-stage the wider set here from raw
import gzip
GEO = json.loads(open(os.path.join(BASE, "panel/eurostat_staging_report.json")).read())  # noqa (vintage only)
G2I = {"AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK","EE":"EST","EL":"GRC",
       "ES":"ESP","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN","IE":"IRL","IT":"ITA","LT":"LTU","LU":"LUX",
       "LV":"LVA","MT":"MLT","NL":"NLD","PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE","SI":"SVN","SK":"SVK",
       "NO":"NOR","CH":"CHE","IS":"ISL","RS":"SRB","MK":"MKD","BA":"BIH","ME":"MNE","AL":"ALB","TR":"TUR"}
WANT = {"J", "K", "C", "D", "F", "G-I", "S"}
_plain = os.path.join(BASE, "raw/S08_nama_10_lp_a21_linear.csv")
opener = (lambda: open(_plain)) if os.path.exists(_plain) else (lambda: gzip.open(_plain + ".gz", "rt"))
ep = []
with opener() as fh:
    for r in csv.DictReader(fh):
        if r["na_item"] != "RLPR_HW" or r["unit"] != "PCH_PRE" or r["nace_r2"] not in WANT: continue
        iso = G2I.get(r["geo"]); v = r["OBS_VALUE"].strip()
        if not iso or not v: continue
        yr = int(r["TIME_PERIOD"])
        if yr < 2005: continue
        ep.append(dict(iso3=iso, nace=r["nace_r2"], year=yr, dlp=float(v)))

def beta_fe(rows, amap=None):
    isos = sorted({r["iso3"] for r in rows}); naces = sorted({r["nace"] for r in rows})
    yv = np.array([r["y"] for r in rows])
    a = np.array([(amap[r["iso3"]] if amap else r["ais"]) * r["exposed"] for r in rows])
    Xd = np.column_stack([np.ones(len(yv)), a] +
                         [[1.0 if r["iso3"] == i else 0.0 for r in rows] for i in isos[1:]] +
                         [[1.0 if r["nace"] == s else 0.0 for r in rows] for s in naces[1:]])
    return float((np.linalg.pinv(Xd.T @ Xd) @ Xd.T @ yv)[1])

def run_year(year, controls, nperm=NPERM):
    rows = [dict(iso3=r["iso3"], nace=r["nace"], exposed=1.0 if r["nace"] in ("J", "K") else 0.0,
                 y=r["dlp"], ais=AIS[r["iso3"]])
            for r in ep if r["year"] == year and r["iso3"] in AIS and r["nace"] in ({"J", "K"} | controls)]
    b = beta_fe(rows)
    isos = sorted({r["iso3"] for r in rows}); vals = [AIS[i] for i in isos]
    null = np.array([beta_fe(rows, amap=dict(zip(isos, rng.permutation(vals)))) for _ in range(nperm)])
    return dict(beta=b, z=float(b / null.std()),
                p=float((np.sum(np.abs(null) >= abs(b)) + 1) / (nperm + 1)),
                n_obs=len(rows), n_countries=len(isos))

CV1 = run_year(2025, {"C", "D", "F", "G-I", "S"})
CV1_narrow = run_year(2025, {"C", "F", "G-I"}, nperm=2000)  # consistency check vs eps_analysis

# CV2: unemployment surprise
def weo_read_oct(subject, col):
    out = {}
    with open(os.path.join(BASE, "raw/S12_WEOOct2024all.tsv"), encoding="utf-16-le", errors="replace") as fh:
        rdr = csv.reader(fh, delimiter="\t"); hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
        for row in rdr:
            if len(row) > 10 and row[2] == subject and row[1]:
                v = row[yi[col]].replace(",", "").strip()
                if v and v not in ("n/a", "--"):
                    try: out[row[1]] = float(v)
                    except ValueError: pass
    return out
def weo_read_apr(subject, col):
    out = {}
    with open(os.path.join(BASE, "raw/S11_WEO_Apr2026_portal.csv"), encoding="utf-8-sig") as fh:
        rdr = csv.reader(fh); hdr = next(rdr); yi = {h: i for i, h in enumerate(hdr)}
        for row in rdr:
            p = row[1].split(".")
            if len(p) == 3 and p[1] == subject and len(p[0]) == 3 and row[yi[col]].strip():
                try: out[p[0]] = float(row[yi[col]])
                except ValueError: pass
    return out
lur_f = weo_read_oct("LUR", "2025"); lur_a = weo_read_apr("LUR", "2025")
isosW = sorted(set(AIS) & set(lur_f) & set(lur_a))
ysur = np.array([lur_a[i] - lur_f[i] for i in isosW]); a = np.array([AIS[i] for i in isosW])
Xw = np.column_stack([np.ones(len(isosW)), a])
bW = float((np.linalg.pinv(Xw.T @ Xw) @ Xw.T @ ysur)[1])
nullW = []
for _ in range(NPERM):
    Xp = Xw.copy(); Xp[:, 1] = rng.permutation(a)
    nullW.append((np.linalg.pinv(Xp.T @ Xp) @ Xp.T @ ysur)[1])
nullW = np.array(nullW)
CV2 = dict(beta=bW, z=float(bW / nullW.std()),
           p=float((np.sum(np.abs(nullW) >= abs(bW)) + 1) / (NPERM + 1)),
           n=len(isosW), mean_surprise=float(ysur.mean()),
           note="unemployment-rate surprise 2025, pp; positive = worse than forecast")

# CV3: extended event path 2010-2025 (widened controls), lighter perms
CV3 = [dict(year=t, **run_year(t, {"C", "D", "F", "G-I", "S"}, nperm=500)) for t in range(2010, 2026)]

res = dict(CV1_widened_controls=CV1, CV1_narrow_consistency=CV1_narrow, CV2_unemployment=CV2,
           CV3_extended_path=CV3)
json.dump(res, open(os.path.join(OUT, "coverage_ext_results.json"), "w"), indent=2)
led = json.load(open(os.path.join(OUT, "search_ledger.json")))
led = [l for l in led if l.get("spec") != "CV_family"]
led.append(dict(spec="CV_family", CV1=CV1, CV2={k: v for k, v in CV2.items() if k != "note"}))
json.dump(led, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(dict(CV1=CV1, CV1_narrow=CV1_narrow, CV2=CV2), indent=2))
