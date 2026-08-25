#!/usr/bin/env python3
"""Staging: ILOSTAT employment by ISCO-08 occupation -> white-collar denominators.

Frozen D3: white-collar = ISCO-08 major groups 1-4 (managers, professionals,
technicians, clerical); sensitivity = groups 1-3. Share of total employment,
both sexes (SEX_T), latest available year in 2015-2025 per country (the share
is slow-moving; the chosen year is recorded). Values are thousands employed.
Appends columns to panel/country_panel.csv (idempotent: recomputes columns).
"""
import csv, json, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
NEED = {"OCU_ISCO08_1", "OCU_ISCO08_2", "OCU_ISCO08_3", "OCU_ISCO08_4", "OCU_ISCO08_TOTAL"}

by_ct = defaultdict(dict)  # (iso3, year) -> {class: value}
with open(os.path.join(BASE, "raw/S14_ilostat_emp_by_occupation.csv"), encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["sex"] != "SEX_T" or r["classif1"] not in NEED: continue
        try:
            yr = int(r["time"]); v = float(r["obs_value"])
        except ValueError:
            continue
        if not (2015 <= yr <= 2025): continue
        by_ct[(r["ref_area"], yr)][r["classif1"]] = v

best = {}  # iso3 -> (year, wc14_share, wc13_share, wc14_thousands, total_thousands)
for (iso, yr), d in by_ct.items():
    if not NEED <= set(d): continue
    tot = d["OCU_ISCO08_TOTAL"]
    if tot <= 0: continue
    wc14 = sum(d[f"OCU_ISCO08_{i}"] for i in (1, 2, 3, 4))
    wc13 = sum(d[f"OCU_ISCO08_{i}"] for i in (1, 2, 3))
    cur = best.get(iso)
    if cur is None or yr > cur[0]:
        best[iso] = (yr, wc14 / tot, wc13 / tot, wc14, tot)

panel_path = os.path.join(BASE, "panel/country_panel.csv")
rows = list(csv.DictReader(open(panel_path)))
matched = 0
for r in rows:
    b = best.get(r["iso3"])
    if b:
        matched += 1
        r["wc_year"], r["wc14_share"], r["wc13_share"] = b[0], f"{b[1]:.6f}", f"{b[2]:.6f}"
        r["wc14_thousands"], r["emp_total_thousands"] = f"{b[3]:.3f}", f"{b[4]:.3f}"
    else:
        r["wc_year"] = r["wc14_share"] = r["wc13_share"] = r["wc14_thousands"] = r["emp_total_thousands"] = ""
fields = list(rows[0].keys())
with open(panel_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in rows: w.writerow(r)

missing = sorted(r["iso3"] for r in rows if not r["wc14_share"])
rep = dict(ilostat_countries_with_full_isco=len(best), panel_matched=matched,
           panel_total=len(rows), missing_in_panel=missing,
           year_distribution={str(y): sum(1 for b in best.values() if b[0] == y)
                              for y in sorted({b[0] for b in best.values()})})
json.dump(rep, open(os.path.join(BASE, "panel/ilostat_staging_report.json"), "w"), indent=2)
print(json.dumps(rep, indent=2)[:1200])
