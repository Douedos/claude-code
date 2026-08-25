#!/usr/bin/env python3
"""Freeze the confirmatory protocol for the prospective 2026-2027 test.

Writes, and hashes, two artifacts:
  frozen_ais_treatment.csv  - the treatment values (AIS per provider, jackknife
                              residuals as estimated 2026-08-25) that the
                              prospective test MUST use unchanged
  frozen_protocol.json      - the full pre-registered specification: outcomes,
                              vintages, estimators, confirmatory family,
                              adjustment, and decision rules

After outcome data for 2026 is accessed, nothing in this directory may change
(the skeleton's read-only rule). External registration of the two SHA-256
hashes (OSF or equivalent) is the recommended next user action.
"""
import csv, hashlib, json, os
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))

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

def jackknife(sample, yvals):
    y = np.asarray(yvals, float)
    lgdp = np.log([f(r, "gdp_pc") for r in sample]); lpop = np.log([f(r, "pop") for r in sample])
    region = [r["region"] for r in sample]
    regs = sorted({g for g in region if sum(1 for x in region if x == g) >= 2})[1:]
    X = np.column_stack([np.ones(len(y)), lgdp, lpop] +
                        [[1.0 if g == q else 0.0 for g in region] for q in regs])
    XtXi = np.linalg.pinv(X.T @ X); H = X @ XtXi @ X.T
    return dict(zip([r["iso3"] for r in sample], (y - X @ (XtXi @ X.T @ y)) / (1 - np.diag(H))))

ms_sample = [r for r in panel if all(f(r, k) is not None for k in ("h1_2025", "gdp_pc", "pop"))]
AIS_MS = jackknife(ms_sample, [np.log((f(r, "h1_2025") / 100) / (1 - f(r, "h1_2025") / 100)) for r in ms_sample])
aei_sample = [r for r in panel if r["iso3"] in aei and aei[r["iso3"]] >= 50
              and all(f(r, k) is not None for k in ("gdp_pc", "pop"))]
AIS_AEI = jackknife(aei_sample, [np.log(aei[r["iso3"]] / f(r, "pop")) for r in aei_sample])

tpath = os.path.join(HERE, "frozen_ais_treatment.csv")
with open(tpath, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["iso3", "ais_ms_h1_2025", "ais_aei_aug2025"])
    for i in sorted(set(AIS_MS) | set(AIS_AEI)):
        w.writerow([i, f"{AIS_MS[i]:.6f}" if i in AIS_MS else "",
                    f"{AIS_AEI[i]:.6f}" if i in AIS_AEI else ""])

protocol = dict(
  version="1.0", frozen_utc="2026-08-25", status="FROZEN - read-only after any 2026 outcome access",
  treatment=dict(
    primary="ais_ms_h1_2025 from frozen_ais_treatment.csv (jackknife residual of logit Microsoft H1-2025 "
            "diffusion on log GDP pc, log population, M49 region FE; estimated 2026-08-25)",
    consistency_requirement="ais_aei_aug2025 (same construction on Anthropic AEI v3 usage per capita)",
    rule="values may NOT be re-estimated with newer covariates or adoption data"),
  outcomes=[
    dict(id="P1", name="Eurostat nama_10_lp_a21, RLPR_HW, PCH_PRE, years 2026 and 2027",
         vintage_rule="first Eurostat release covering each year; retrieval manifested with hash"),
    dict(id="P2", name="IMF WEO real GDP growth surprise for 2026",
         construction="actual (first spring vintage covering 2026, expected April 2027) minus the "
                      "October 2024 forecast for 2026 (S12, sha256 in manifest)")],
  design=dict(
    estimator="year-specific cross-section with country FE + sector FE; coefficient on AIS x Exposed",
    exposed=["J", "K"], controls=["C", "F", "G-I"], m_variant="sensitivity only",
    primary_statistic="beta_post = mean(beta_2026, beta_2027); if only 2026 available, beta_2026",
    co_primary_robustness="detrended beta_post: beta_post minus the 2016-2023 linear pre-trend "
                          "prediction (T1 showed a declining path; sign consistency with the raw "
                          "beta_post is required)",
    inference="10,000 country-label permutations, seed 20270101 (declared now, unused so far); "
              "wild cluster bootstrap (5,000, Rademacher, by country) secondary; LOCO mandatory"),
  confirmatory_family=dict(
    members=["beta_post with ais_ms", "beta_post with ais_aei", "W: 2026 growth surprise on ais_ms"],
    adjustment="max-statistic permutation across the three members",
    alpha=0.05),
  decision_rules=dict(
    promote_to_provisional=[
      "search-adjusted p < 0.05 within the confirmatory family",
      "sign-consistent between ais_ms and ais_aei treatments",
      "sign unchanged under leave-one-country-out",
      "negative-control sectors show no comparable effect",
      "sign consistent between raw and detrended beta_post"],
    informative_null="if |beta_post| CI excludes the MDE-scaled plausible band (0.3-1.0 pp per sd AIS), "
                     "report as evidence against short-horizon effects of that size",
    otherwise="report as still-underpowered; continue to 2028 vintage"),
  power_note="pooling 2026+2027 approximately halves the single-year MDE of 2.4 pp per sd(AIS)",
  code="exploration/eps_analysis.py and exploration/event_study.py at the git commit recorded alongside "
       "this file; any re-implementation must reproduce the frozen 2025 betas before running 2026+")

ppath = os.path.join(HERE, "frozen_protocol.json")
json.dump(protocol, open(ppath, "w"), indent=2)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""): h.update(c)
    return h.hexdigest()
hashes = {os.path.basename(tpath): sha(tpath), os.path.basename(ppath): sha(ppath)}
json.dump(hashes, open(os.path.join(HERE, "freeze_hashes.json"), "w"), indent=2)
print(json.dumps(hashes, indent=2))
print("treatment rows:", len(set(AIS_MS) | set(AIS_AEI)))
