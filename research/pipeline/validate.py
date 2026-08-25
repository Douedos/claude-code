#!/usr/bin/env python3
"""Validation layer (protocol section 12.1 of the research skeleton).

Checks: unique keys, schema, value ranges, denominator sanity, and
reproduction of values visibly published in the Microsoft Q1 2026 report
(extracted to staging/report_text_Q1_2026.txt from the S01 PDF).
A failure exits nonzero and blocks downstream analysis.
"""
import csv, json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
checks = []

def check(name, ok, detail=""):
    checks.append(dict(check=name, passed=bool(ok), detail=str(detail)))
    print(("PASS " if ok else "FAIL ") + name + ("  | " + str(detail) if detail else ""))

# 1. unique keys
isos = [r["iso3"] for r in rows]
check("unique_iso3_keys", len(isos) == len(set(isos)), f"n={len(isos)}")

# 2. schema and ranges
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None
bad_range = [r["iso3"] for r in rows for k in ("h1_2025","h2_2025","q1_2026")
             if f(r, k) is not None and not (0 < f(r, k) < 100)]
check("adoption_shares_in_(0,100)", not bad_range, bad_range or "all in range")
mono_note = sum(1 for r in rows if None not in (f(r,"h1_2025"), f(r,"q1_2026"))
                and f(r,"q1_2026") < f(r,"h1_2025"))
check("adoption_mostly_nondecreasing", True, f"{mono_note} economies declined H1'25->Q1'26 (informational)")

# 3. denominator sanity
bad_pop = [r["iso3"] for r in rows if f(r, "pop") is not None and f(r, "pop") <= 0]
check("population_positive", not bad_pop, bad_pop or "ok")

# 4. published-value reproduction (>=2 required by protocol)
val = {r["iso3"]: r for r in rows}
targets = [  # (iso3, column, published value in Q1 2026 report)
    ("ARE", "q1_2026", 70.1), ("SGP", "q1_2026", 63.4), ("NOR", "q1_2026", 48.6),
    ("IRL", "q1_2026", 48.4), ("USA", "q1_2026", 31.3), ("CHN", "q1_2026", 16.4),
    ("ARE", "h2_2025", 64.0), ("SGP", "h2_2025", 60.9),
]
for iso, col, pub in targets:
    got = f(val[iso], col)
    check(f"published_value_{iso}_{col}", got is not None and abs(got - pub) < 1e-9,
          f"published={pub} retrieved={got}")

# 5. US rank 21 in Q1 2026 (report: "from 24th to 21st ... 31.3%")
ranked = sorted((r for r in rows if f(r, "q1_2026") is not None),
                key=lambda r: -f(r, "q1_2026"))
us_rank = next(i + 1 for i, r in enumerate(ranked) if r["iso3"] == "USA")
check("published_us_rank_21_q1_2026", us_rank == 21, f"computed rank={us_rank}")

# 6. world weighted mean ~= 17.8% (report; report weights by 15-64 population,
#    we only have total population -> tolerance band, informational-strict)
num = sum(f(r,"q1_2026") * f(r,"pop") for r in rows
          if f(r,"q1_2026") is not None and f(r,"pop") is not None)
den = sum(f(r,"pop") for r in rows if f(r,"q1_2026") is not None and f(r,"pop") is not None)
wmean = num / den
check("world_weighted_mean_near_17.8", abs(wmean - 17.8) < 2.0,
      f"total-pop-weighted={wmean:.2f} (report 17.8 uses ages 15-64; deviation expected)")

# 7. explicit missingness report
missing_gdp = [r["iso3"] for r in rows if f(r, "gdp_pc") is None]
check("missingness_reported", True, f"missing gdp_pc: {missing_gdp}")

json.dump(checks, open(os.path.join(BASE, "manifest/validation.json"), "w"), indent=2)
fails = [c for c in checks if not c["passed"]]
print(f"\n{len(checks)} checks, {len(fails)} failures")
sys.exit(1 if fails else 0)
