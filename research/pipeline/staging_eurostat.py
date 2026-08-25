#!/usr/bin/env python3
"""Staging: Eurostat nama_10_lp_a21 -> country x sector x year productivity panel.

Primary outcome per frozen design E1: real labour productivity per hour worked
(RLPR_HW), unit PCH_PRE (% change on previous period). Aggregates (EU/EA) are
dropped; Eurostat 2-letter geo codes mapped to ISO3 (EL->GRC, UK->GBR).
Cross-validated against the independently downloaded default-view spreadsheet.
"""
import csv, gzip, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
GEO = {"AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK",
       "EE":"EST","EL":"GRC","ES":"ESP","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN",
       "IE":"IRL","IT":"ITA","LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT","NL":"NLD",
       "PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE","SI":"SVN","SK":"SVK",
       "NO":"NOR","CH":"CHE","IS":"ISL","UK":"GBR","RS":"SRB","MK":"MKD","BA":"BIH",
       "ME":"MNE","AL":"ALB","TR":"TUR","XK":"XKX","LI":"LIE"}
SECTORS = {"J": "exposed", "K": "exposed", "M": "exposed",
           "C": "control", "F": "control", "G-I": "control"}

# raw file is stored gzip-compressed in git (LFS unavailable on public forks);
# an uncompressed local copy is used when present
rows_out, dropped_geo = [], set()
_plain = os.path.join(BASE, "raw/S08_nama_10_lp_a21_linear.csv")
_opener = (lambda: open(_plain)) if os.path.exists(_plain) else \
          (lambda: gzip.open(_plain + ".gz", "rt"))
with _opener() as f:
    for r in csv.DictReader(f):
        if r["na_item"] != "RLPR_HW" or r["unit"] != "PCH_PRE": continue
        if r["nace_r2"] not in SECTORS: continue
        iso = GEO.get(r["geo"])
        if iso is None:
            dropped_geo.add(r["geo"]); continue
        v = r["OBS_VALUE"].strip()
        if not v: continue
        yr = int(r["TIME_PERIOD"])
        if yr < 2000: continue
        rows_out.append(dict(iso3=iso, nace=r["nace_r2"], exposure=SECTORS[r["nace_r2"]],
                             year=yr, dlp_hw=float(v), flag=r["OBS_FLAG"].strip()))

keys = {(r["iso3"], r["nace"], r["year"]) for r in rows_out}
assert len(keys) == len(rows_out), "duplicate country-sector-year keys"
os.makedirs(os.path.join(BASE, "panel"), exist_ok=True)
with open(os.path.join(BASE, "panel/eurostat_productivity_panel.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["iso3","nace","exposure","year","dlp_hw","flag"])
    w.writeheader()
    for r in sorted(rows_out, key=lambda x: (x["iso3"], x["nace"], x["year"])): w.writerow(r)

cov25 = sorted({r["iso3"] for r in rows_out if r["year"] == 2025})
cov24 = sorted({r["iso3"] for r in rows_out if r["year"] == 2024})
rep = dict(rows=len(rows_out),
           countries=len({r["iso3"] for r in rows_out}),
           dropped_aggregate_geos=sorted(dropped_geo),
           coverage_2025_countries=len(cov25), coverage_2025=cov25,
           coverage_2024_countries=len(cov24),
           sectors={s: sorted({r["iso3"] for r in rows_out if r["nace"] == s and r["year"] == 2025})
                    .__len__() for s in SECTORS})
json.dump(rep, open(os.path.join(BASE, "panel/eurostat_staging_report.json"), "w"), indent=2)
print(json.dumps(rep, indent=2))
