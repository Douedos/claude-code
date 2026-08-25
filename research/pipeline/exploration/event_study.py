#!/usr/bin/env python3
"""Event-study form of the priority-1 regression (declared v1.3 family).

For each year t in 2016..2025, estimate
    dlp_hw_i,s,t = a_i + d_s + beta_t (AIS_i x Exposed_s) + e
on the year-t cross-section (equivalent to a full panel with country x year
and sector x year fixed effects and year-specific interactions — the frozen
F2 specification). Outcome is the RAW yearly productivity growth rate, so
persistent growth differentials show up as a nonzero pre-period path rather
than being differenced away: the event study is the pre-trend diagnostic.

Inference per year: 2000 country-label permutations -> two-sided p and the
null 2.5/97.5 percentile band. Joint pre-period test: observed mean
beta(2016..2023) against the permutation distribution of the same statistic.
Providers: Microsoft-based AIS (primary) and Anthropic-based AIS (overlay).
Seed 20260825. Grade: EXPLORATORY.
"""
import csv, json, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
REP = os.path.join(BASE, "reports")
rng = np.random.default_rng(20260825)
NPERM = 2000
YEARS = list(range(2016, 2026))
SECT = ["J", "K", "C", "F", "G-I"]
EXPOSED = {"J", "K"}

# ---- AIS per provider (identical construction to eps_analysis.py) ----
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
    return dict(zip(iso, (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))))

ms_sample = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "gdp_pc", "pop"))]
AIS_MS = jackknife_ais(ms_sample, lambda r: np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)))
aei_sample = [r for r in panel if r["iso3"] in aei and aei[r["iso3"]] >= 50
              and all(f(r, k) is not None for k in ("gdp_pc", "pop"))]
AIS_AEI = jackknife_ais(aei_sample, lambda r: np.log(aei[r["iso3"]] / f(r, "pop")))

# ---- outcome panel ----
ep = list(csv.DictReader(open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"))))
for r in ep: r["year"] = int(r["year"]); r["dlp_hw"] = float(r["dlp_hw"])

def year_rows(year, ais):
    return [dict(iso3=r["iso3"], nace=r["nace"],
                 exposed=1.0 if r["nace"] in EXPOSED else 0.0,
                 y=r["dlp_hw"], ais=ais[r["iso3"]])
            for r in ep if r["year"] == year and r["nace"] in SECT and r["iso3"] in ais]

def beta_fe(rows, amap=None):
    isos = sorted({r["iso3"] for r in rows})
    naces = sorted({r["nace"] for r in rows})
    y = np.array([r["y"] for r in rows])
    a = np.array([(amap[r["iso3"]] if amap else r["ais"]) * r["exposed"] for r in rows])
    X = np.column_stack([np.ones(len(y)), a] +
                        [[1.0 if r["iso3"] == i else 0.0 for r in rows] for i in isos[1:]] +
                        [[1.0 if r["nace"] == s else 0.0 for r in rows] for s in naces[1:]])
    return float((np.linalg.pinv(X.T @ X) @ X.T @ y)[1])

def event_study(ais, label):
    out = []
    # one common permutation set of country relabelings reused across years so
    # the joint pre-period statistic has a coherent null
    isos_all = sorted(ais)
    vals = [ais[i] for i in isos_all]
    perms = [dict(zip(isos_all, rng.permutation(vals))) for _ in range(NPERM)]
    null_by_year = {}
    for t in YEARS:
        rows = year_rows(t, ais)
        if len({r["iso3"] for r in rows}) < 10:
            out.append(dict(year=t, beta=None)); continue
        b = beta_fe(rows)
        null = np.array([beta_fe(rows, amap=p) for p in perms])
        null_by_year[t] = null
        out.append(dict(year=t, beta=b,
                        p=float((np.sum(np.abs(null) >= abs(b)) + 1) / (NPERM + 1)),
                        band_lo=float(np.percentile(null, 2.5)),
                        band_hi=float(np.percentile(null, 97.5)),
                        n_countries=len({r["iso3"] for r in rows})))
    pre = [o for o in out if o["beta"] is not None and o["year"] <= 2023]
    obs_pre = float(np.mean([o["beta"] for o in pre]))
    null_pre = np.mean([null_by_year[o["year"]] for o in pre], axis=0)
    pre_p = float((np.sum(np.abs(null_pre) >= abs(obs_pre)) + 1) / (NPERM + 1))
    return dict(label=label, path=out, pre_mean_2016_2023=obs_pre, pre_joint_perm_p=pre_p)

ES_MS = event_study(AIS_MS, "AIS Microsoft (primary)")
ES_AEI = event_study(AIS_AEI, "AIS Anthropic (overlay)")
res = dict(ms=ES_MS, aei=ES_AEI, nperm=NPERM, exposed=sorted(EXPOSED), controls=sorted(set(SECT) - EXPOSED))
json.dump(res, open(os.path.join(OUT, "event_study_results.json"), "w"), indent=2)
ledger = json.load(open(os.path.join(OUT, "search_ledger.json")))
ledger.append(dict(spec="ES_MS_eventstudy", pre_mean=ES_MS["pre_mean_2016_2023"],
                   pre_joint_perm_p=ES_MS["pre_joint_perm_p"],
                   beta_2025=[o["beta"] for o in ES_MS["path"] if o["year"] == 2025][0]))
ledger.append(dict(spec="ES_AEI_eventstudy", pre_mean=ES_AEI["pre_mean_2016_2023"],
                   pre_joint_perm_p=ES_AEI["pre_joint_perm_p"],
                   beta_2025=[o["beta"] for o in ES_AEI["path"] if o["year"] == 2025][0]))
json.dump(ledger, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)

# ---- figure ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 9})
fig, ax = plt.subplots(figsize=(6.8, 4.3))
ms_y = [o["year"] for o in ES_MS["path"] if o["beta"] is not None]
ms_b = [o["beta"] for o in ES_MS["path"] if o["beta"] is not None]
lo = [o["band_lo"] for o in ES_MS["path"] if o["beta"] is not None]
hi = [o["band_hi"] for o in ES_MS["path"] if o["beta"] is not None]
ax.fill_between(ms_y, lo, hi, color="#2c6fbb", alpha=0.15,
                label="95% permutation band (null, Microsoft AIS)")
ax.plot(ms_y, ms_b, "-o", color="#2c6fbb", ms=4, label="Microsoft-based AIS x exposure")
ae_y = [o["year"] for o in ES_AEI["path"] if o["beta"] is not None]
ae_b = [o["beta"] for o in ES_AEI["path"] if o["beta"] is not None]
ax.plot(ae_y, ae_b, "--s", color="#c0392b", ms=4, alpha=0.8, label="Anthropic-based AIS x exposure")
ax.axhline(0, color="#666", lw=0.8)
ax.axvline(2024.5, color="#444", lw=0.9, ls=":")
ax.annotate("adoption first\nmeasured H1 2025", (2024.55, ax.get_ylim()[1] * 0.75), fontsize=7.5)
ax.set_xlabel("outcome year")
ax.set_ylabel("yearly coefficient: AIS x exposed (J,K vs C,F,G-I), pp of productivity growth")
ax.set_title("Event study: differential productivity growth of AI-exposed sectors\nin high-AIS countries, 2016-2025")
ax.legend(frameon=False, fontsize=7.5, loc="lower left")
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig5_event_study.png"), dpi=150)
print(json.dumps(dict(ms_pre=ES_MS["pre_mean_2016_2023"], ms_pre_p=ES_MS["pre_joint_perm_p"],
                      aei_pre=ES_AEI["pre_mean_2016_2023"], aei_pre_p=ES_AEI["pre_joint_perm_p"],
                      ms_path=[(o["year"], round(o["beta"], 2), round(o["p"], 3))
                               for o in ES_MS["path"] if o["beta"] is not None]), indent=2))
