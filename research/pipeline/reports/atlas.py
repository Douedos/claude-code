#!/usr/bin/env python3
"""Descriptive data atlas: one figure per dataset family.
Palette: categorical order [blue #2c6fbb, orange #e67e22, purple #7d3c98,
teal #148f77]; gray #888 context; red reserved for flags; sequential = blues.
"""
import csv, gzip, json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(BASE, "reports")
BLUE, ORANGE, PURPLE, TEAL, GRAY = "#2c6fbb", "#e67e22", "#7d3c98", "#148f77", "#888888"
plt.rcParams.update({"font.size": 8.6, "axes.edgecolor": "#999", "axes.linewidth": 0.7,
                     "xtick.color": "#444", "ytick.color": "#444"})

panel = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r.get(k) not in ("", "None", None) else None

# ---------- fig7: coverage matrix ----------
rows = [
 ("Microsoft AI Diffusion (S02)", 147, "H1'25 - Q1'26 (3 periods)"),
 ("Anthropic AEI v3 (S04)", 171, "one week, Aug 2025"),
 ("IMF WEO Apr'26 (S11)", 210, "1980 - 2031"),
 ("IMF WEO Oct'24 baseline (S12)", 196, "1980 - 2029 (forecasts)"),
 ("ILOSTAT ISCO-08 (S14)", 118, "latest 2015 - 2025"),
 ("World Bank GDP/pop mirrors", 142, "2023 / 2024"),
 ("Eurostat productivity (S08)", 31, "1996 - 2025, 11 NACE groups"),
 ("Joint EPS estimation sample", 25, "outcome 2016 - 2025"),
]
fig, ax = plt.subplots(figsize=(6.9, 3.1))
names = [r[0] for r in rows][::-1]; vals = [r[1] for r in rows][::-1]; spans = [r[2] for r in rows][::-1]
bars = ax.barh(range(len(rows)), vals, color=BLUE, height=0.62)
for i, (v, s) in enumerate(zip(vals, spans)):
    ax.text(v + 2, i, f"{v}  ·  {s}", va="center", fontsize=7.6, color="#333")
ax.set_yticks(range(len(rows))); ax.set_yticklabels(names, fontsize=8)
ax.set_xlim(0, 305); ax.set_xlabel("economies covered")
ax.set_title("Coverage by dataset: economies and time span")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig7_coverage.png"), dpi=150); plt.close(fig)

# ---------- fig8: adoption ----------
q1 = np.array([f(r, "q1_2026") for r in panel if f(r, "q1_2026") is not None])
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
ax = axes[0]
ax.hist(q1, bins=24, color=BLUE, edgecolor="white", linewidth=0.6)
ax.axvline(17.8, color="#333", lw=1.0, ls="--")
ax.text(18.6, ax.get_ylim()[1] * 0.92, "world mean 17.8", fontsize=7.4, color="#333")
ax.set_xlabel("AI user share Q1 2026 (%)"); ax.set_ylabel("economies")
ax.set_title("Distribution of adoption, 147 economies")
ax.spines[["top", "right"]].set_visible(False)
ax = axes[1]
HL = {"ARE": (BLUE, "UAE"), "USA": (ORANGE, "USA"), "KOR": (PURPLE, "Korea"), "NGA": (TEAL, "Nigeria")}
xs = [0, 1, 2]
for r in panel:
    v = [f(r, "h1_2025"), f(r, "h2_2025"), f(r, "q1_2026")]
    if None in v: continue
    if r["iso3"] in HL:
        c, lab = HL[r["iso3"]]
        ax.plot(xs, v, color=c, lw=1.8, marker="o", ms=3.5, label=lab, zorder=3)
    else:
        ax.plot(xs, v, color=GRAY, lw=0.5, alpha=0.28, zorder=1)
ax.set_xticks(xs); ax.set_xticklabels(["H1 2025", "H2 2025", "Q1 2026"])
ax.set_ylabel("AI user share (%)"); ax.set_title("Trajectories (all economies; four highlighted)")
ax.legend(frameon=False, fontsize=7.4, loc="upper left")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig8_adoption.png"), dpi=150); plt.close(fig)

# ---------- fig9: outcomes ----------
G2I = {"AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK","EE":"EST","EL":"GRC",
       "ES":"ESP","FI":"FIN","FR":"FRA","HR":"HRV","HU":"HUN","IE":"IRL","IT":"ITA","LT":"LTU","LU":"LUX",
       "LV":"LVA","MT":"MLT","NL":"NLD","PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE","SI":"SVN","SK":"SVK",
       "NO":"NOR","CH":"CHE","IS":"ISL","RS":"SRB"}
WANT = ["J", "K", "M", "C", "D", "F", "G-I", "S"]
_plain = os.path.join(BASE, "raw/S08_nama_10_lp_a21_linear.csv")
opener = (lambda: open(_plain)) if os.path.exists(_plain) else (lambda: gzip.open(_plain + ".gz", "rt"))
by_sect = {s: [] for s in WANT}
with opener() as fh:
    for r in csv.DictReader(fh):
        if r["na_item"] != "RLPR_HW" or r["unit"] != "PCH_PRE" or r["nace_r2"] not in by_sect: continue
        if r["geo"] not in G2I or not r["OBS_VALUE"].strip(): continue
        if not (2016 <= int(r["TIME_PERIOD"]) <= 2025): continue
        by_sect[r["nace_r2"]].append(float(r["OBS_VALUE"]))
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.1))
ax = axes[0]
data = [by_sect[s] for s in WANT]
bp = ax.boxplot(data, tick_labels=WANT, showfliers=False, widths=0.55, patch_artist=True,
                medianprops=dict(color="#222", lw=1.1))
for patch, s in zip(bp["boxes"], WANT):
    patch.set_facecolor(ORANGE if s in ("J", "K", "M") else BLUE); patch.set_alpha(0.75)
    patch.set_edgecolor("white")
ax.axhline(0, color="#999", lw=0.7)
ax.set_ylabel("yearly productivity growth per hour (%)")
ax.set_title("Eurostat outcome by sector, 2016-2025\n(orange = AI-exposed, blue = controls)")
ax.spines[["top", "right"]].set_visible(False)
ax = axes[1]
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
common = sorted(set(oct24) & set(apr26))
fx = np.array([oct24[i] for i in common]); ay = np.array([apr26[i] for i in common])
m = (np.abs(fx) < 12) & (np.abs(ay) < 12)
ax.scatter(fx[m], ay[m], s=10, color=BLUE, alpha=0.6)
lim = [-6, 10]
ax.plot(lim, lim, color="#999", lw=0.9)
for tag in ("DEU", "USA", "CHN", "ARG", "IRL"):
    if tag in common:
        ax.annotate(tag, (oct24[tag], apr26[tag]), fontsize=6.8, xytext=(3, 3), textcoords="offset points")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("forecast 2025 growth (Oct 2024 vintage, %)")
ax.set_ylabel("actual/estimate (Apr 2026 vintage, %)")
ax.set_title("WEO growth-surprise construction\n(N=%d; 45-degree line = forecast met)" % int(m.sum()))
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig9_outcomes.png"), dpi=150); plt.close(fig)

# ---------- fig10: structure ----------
fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0))
ax = axes[0]
xs, ys = [], []
for r in panel:
    if f(r, "wc14_share") is not None and f(r, "gdp_pc") is not None:
        xs.append(np.log(f(r, "gdp_pc"))); ys.append(100 * f(r, "wc14_share"))
xs, ys = np.array(xs), np.array(ys)
ax.scatter(xs, ys, s=10, color=BLUE, alpha=0.65)
b = np.polyfit(xs, ys, 1)
xr = np.linspace(xs.min(), xs.max(), 40)
ax.plot(xr, np.polyval(b, xr), color="#333", lw=1.0)
ax.set_xlabel("log GDP per capita"); ax.set_ylabel("white-collar share of employment (%)")
ax.set_title("ILOSTAT: occupational structure vs income\n(the collinearity behind the WC1 anticlimax)")
ax.spines[["top", "right"]].set_visible(False)
ax = axes[1]
ISO2TO3 = {}
for r in csv.DictReader(open(os.path.join(BASE, "raw/X02_country_codes.csv"), encoding="utf-8-sig")):
    a2, a3 = r.get("ISO3166-1-Alpha-2", "").strip(), r.get("ISO3166-1-Alpha-3", "").strip()
    if a2 and a3: ISO2TO3[a2] = a3
usage = []
for r in csv.DictReader(open(os.path.join(BASE, "raw/S04a_aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv"))):
    if r["geography"] == "country" and r["variable"] == "usage_count" and r["geo_id"] != "not_classified":
        usage.append(float(r["value"]))
usage = np.sort(np.array(usage))[::-1]
share = np.cumsum(usage) / usage.sum()
ax.plot(np.arange(1, len(usage) + 1), 100 * share, color=BLUE, lw=1.8)
for k in (1, 5, 10, 20):
    ax.plot([k], [100 * share[k - 1]], "o", ms=4, color=ORANGE)
    ax.annotate(f"top {k}: {100*share[k-1]:.0f}%", (k, 100 * share[k - 1]),
                fontsize=6.9, xytext=(6, -9), textcoords="offset points")
ax.set_xscale("log")
ax.set_xlabel("countries, ranked by usage (log scale)"); ax.set_ylabel("cumulative share of Claude usage (%)")
ax.set_title("AEI: geographic concentration of usage\n(171 countries, one-week window)")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig10_structure.png"), dpi=150); plt.close(fig)
print("atlas figures written: fig7-fig10")
