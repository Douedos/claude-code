#!/usr/bin/env python3
"""Cross-provider analysis: Microsoft AI Diffusion vs Anthropic Economic Index.

This is the skeleton's priority-4 branch (provider reconciliation) and the
H4 promotion criterion ("consistent across at least two independent AI
measures"), which was untestable until the AEI v3 raw release was retrieved.

Timing: the AEI window (2025-08-04..11) falls inside Microsoft's H2 2025
period, so H2 2025 diffusion is the comparison period.

Declared specs (appended to the search ledger):
  D1  log AEI usage per capita  vs  logit MS H2'25 diffusion  (Pearson+Spearman)
  D2  AIS agreement: jackknife residuals from the SAME A4-form model
      (log/logit outcome ~ log gdp_pc + log pop + region FE) computed per
      provider; Pearson+Spearman correlation, permutation p (10k, seeded)
  D3  Coverage audit: registry restricted-market set vs AEI presence
Grade: EXPLORATORY.
"""
import csv, json, os
import numpy as np
from scipy.stats import spearmanr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
rng = np.random.default_rng(20260825)

# --- AEI country usage ---
ISO2TO3 = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/X02_country_codes.csv"), encoding="utf-8-sig")):
    a2, a3 = r.get("ISO3166-1-Alpha-2", "").strip(), r.get("ISO3166-1-Alpha-3", "").strip()
    if a2 and a3: ISO2TO3[a2] = a3
aei = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/S04a_aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv"))):
    if r["geography"] == "country" and r["variable"] == "usage_count" and r["geo_id"] != "not_classified":
        iso3 = ISO2TO3.get(r["geo_id"])
        if iso3: aei[iso3] = float(r["value"])

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None

# joint sample: both providers + covariates
J = [r for r in panel if r["iso3"] in aei and aei[r["iso3"]] >= 50  # min-usage floor to
     and all(f(r, k) is not None for k in ("h2_2025", "gdp_pc", "pop"))]  # avoid log(1-count) noise
iso = [r["iso3"] for r in J]
ms = np.array([f(r, "h2_2025") for r in J])
aei_pc = np.array([aei[r["iso3"]] / f(r, "pop") for r in J])
lgdp = np.log(np.array([f(r, "gdp_pc") for r in J]))
lpop = np.log(np.array([f(r, "pop") for r in J]))
region = [r["region"] for r in J]
regions = sorted(set(region))
y_ms = np.log((ms / 100) / (1 - ms / 100))
y_aei = np.log(aei_pc)
N = len(J)

def jackknife_resid(y):
    X = np.column_stack([np.ones(N), lgdp, lpop] +
                        [[1.0 if r == g else 0.0 for r in region] for g in regions[1:]])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    H = X @ np.linalg.inv(X.T @ X) @ X.T
    return (y - X @ beta) / (1 - np.diag(H))

ais_ms = jackknife_resid(y_ms)
ais_aei = jackknife_resid(y_aei)

# D1: raw association
pear_raw = float(np.corrcoef(y_aei, y_ms)[0, 1])
rho_raw, _ = spearmanr(y_aei, y_ms)

# D2: AIS agreement + permutation p
pear_ais = float(np.corrcoef(ais_ms, ais_aei)[0, 1])
rho_ais, _ = spearmanr(ais_ms, ais_aei)
cnt = 0
for _ in range(10000):
    if abs(np.corrcoef(ais_ms, rng.permutation(ais_aei))[0, 1]) >= abs(pear_ais):
        cnt += 1
perm_p = (cnt + 1) / 10001

# agreement on tails
k = 15
top_ms = set(np.array(iso)[np.argsort(-ais_ms)[:k]])
top_aei = set(np.array(iso)[np.argsort(-ais_aei)[:k]])
bot_ms = set(np.array(iso)[np.argsort(ais_ms)[:k]])
bot_aei = set(np.array(iso)[np.argsort(ais_aei)[:k]])

# D3: restricted coverage audit
RESTRICTED = ["CHN", "RUS", "BLR", "IRN", "CUB", "SYR", "AFG"]
coverage = {c: (c in aei) for c in RESTRICTED}

res = dict(
    n_joint=N, aei_countries_total=len(aei),
    D1=dict(pearson_log_vs_logit=pear_raw, spearman=float(rho_raw)),
    D2=dict(pearson_ais=pear_ais, spearman_ais=float(rho_ais), perm_p=float(perm_p),
            top15_overlap=len(top_ms & top_aei), top15_common=sorted(top_ms & top_aei),
            bottom15_overlap=len(bot_ms & bot_aei), bottom15_common=sorted(bot_ms & bot_aei)),
    D3=dict(restricted_present_in_aei=coverage,
            note="absence = provider does not serve the market; telemetry cannot "
                 "distinguish zero access from zero demand"),
    min_usage_floor=50,
    excluded_below_floor=sorted(set(aei) & {r["iso3"] for r in panel} -
                                {r["iso3"] for r in J} -
                                {r["iso3"] for r in panel if f(r, "gdp_pc") is None}),
)
json.dump(res, open(os.path.join(OUT, "crossprovider_results.json"), "w"), indent=2)
ledger = json.load(open(os.path.join(OUT, "search_ledger.json")))
for spec, d in (("D1_raw_association", res["D1"]), ("D2_ais_agreement", res["D2"]),
                ("D3_coverage_audit", res["D3"])):
    ledger.append(dict(spec=spec, **{k: v for k, v in d.items() if not isinstance(v, list)}))
json.dump(ledger, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(res, indent=2))
