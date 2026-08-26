#!/usr/bin/env python3
"""Post-hoc test C (ledger-flagged) + figures for the research note.

Spec C was NOT in the pre-declared family. It was suggested by inspecting the
AIS bottom ranks (search ledger records this provenance): economies where the
major Western AI providers are unavailable or restricted dominate the negative
tail. C tests whether mean AIS differs for a provider-restricted group defined
from public provider supported-country policies (OpenAI/Microsoft consumer
service availability as of 2025): CHN, RUS, BLR, IRN, CUB, SYR, AFG.
This is the skeleton's G3 confounder (language/availability) made visible.
"""
import csv, json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "exploration")
REP = os.path.join(BASE, "reports")
os.makedirs(REP, exist_ok=True)
rng = np.random.default_rng(20260825)

rows = list(csv.DictReader(open(os.path.join(BASE, "panel/country_panel.csv"))))
def f(r, k): return float(r[k]) if r[k] not in ("", "None") else None
data = [r for r in rows if all(f(r, k) is not None for k in ("h1_2025","q1_2026","gdp_pc","pop"))]
iso = [r["iso3"] for r in data]; econ = [r["economy"] for r in data]
q1 = np.array([f(r,"q1_2026") for r in data]); h1 = np.array([f(r,"h1_2025") for r in data])
lgdp = np.log(np.array([f(r,"gdp_pc") for r in data]))
lpop = np.log(np.array([f(r,"pop") for r in data]))
region = [r["region"] for r in data]; regions = sorted(set(region))
y = np.log((q1/100)/(1-q1/100))

Xd = np.column_stack([np.ones(len(y)), lgdp, lpop] +
                     [[1.0 if r==g else 0.0 for r in region] for g in regions[1:]])
beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
H = Xd @ np.linalg.inv(Xd.T @ Xd) @ Xd.T
ais = (y - Xd @ beta) / (1 - np.diag(H))

RESTRICTED = {"CHN","RUS","BLR","IRN","CUB","SYR","AFG"}
mask = np.array([i in RESTRICTED for i in iso])
diff = ais[mask].mean() - ais[~mask].mean()
cnt = 0
for _ in range(10000):
    p = rng.permutation(len(ais))
    m = np.zeros(len(ais), bool); m[p[:mask.sum()]] = True
    if abs(ais[m].mean() - ais[~m].mean()) >= abs(diff): cnt += 1
resC = dict(spec="C_posthoc_provider_restricted",
            provenance="post-hoc; suggested by AIS bottom-rank inspection",
            group=sorted(RESTRICTED & set(iso)),
            mean_ais_restricted=float(ais[mask].mean()),
            mean_ais_rest=float(ais[~mask].mean()),
            diff=float(diff), perm_p=float((cnt+1)/10001),
            china_ais=float(ais[iso.index("CHN")]))
ledger = json.load(open(os.path.join(OUT, "search_ledger.json")))
ledger.append(resC)
json.dump(ledger, open(os.path.join(OUT, "search_ledger.json"), "w"), indent=2)
print(json.dumps(resC, indent=2))

# ---------------- figures ----------------
plt.rcParams.update({"font.size": 9, "figure.dpi": 150})

fig, ax = plt.subplots(figsize=(6.5, 4.2))
ax.scatter(lgdp[~mask], y[~mask], s=14, alpha=0.65, color="#2c6fbb", label="Open-access economies")
ax.scatter(lgdp[mask], y[mask], s=22, alpha=0.9, color="#c0392b", marker="s", label="Provider-restricted")
xs = np.linspace(lgdp.min(), lgdp.max(), 50)
b2, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(y)), lgdp]), y, rcond=None)
ax.plot(xs, b2[0] + b2[1]*xs, color="black", lw=1.2, label=f"fit: slope={b2[1]:.2f} (logit per log $)")
for tag in ("ARE","SGP","USA","CHN","RUS","VNM","JOR","IND","FRA","NGA","TKM","CUB"):
    if tag in iso:
        i = iso.index(tag)
        ax.annotate(tag, (lgdp[i], y[i]), fontsize=7, xytext=(3,3), textcoords="offset points")
ax.set_xlabel("log GDP per capita (2023, current US$; World Bank mirror)")
ax.set_ylabel("logit AI user share, Q1 2026 (Microsoft AI Diffusion)")
ax.set_title("AI adoption vs income across 142 economies")
ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig1_adoption_income.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 4.2))
d = q1 - h1
gbar = float(np.mean(d / h1))
ax.scatter(h1, d, s=14, alpha=0.65, color="#2c6fbb")
b1, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(d)), h1]), d, rcond=None)
xs = np.linspace(h1.min(), h1.max(), 50)
ax.plot(xs, b1[0] + b1[1]*xs, color="black", lw=1.2,
        label=f"observed fit: slope={b1[1]:.3f} pp per pp")
ax.plot(xs, gbar * xs, color="#e67e22", lw=1.2, ls="--",
        label=f"common-rate compounding benchmark: slope={gbar:.3f}")
for tag in ("ARE","SGP","KOR","JPN","THA","USA","IND","NGA","FRA","ESP"):
    if tag in iso:
        i = iso.index(tag)
        ax.annotate(tag, (h1[i], d[i]), fontsize=7, xytext=(3,3), textcoords="offset points")
ax.set_xlabel("AI user share, H1 2025 (%)")
ax.set_ylabel("Change in AI user share, H1 2025 to Q1 2026 (pp)")
ax.set_title("Level-increment relation in diffusion: consistent with compounding\n"
             "observed slope below the exponential benchmark; catch-up is income-gated", fontsize=9.5)
ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig2_divergence.png")); plt.close(fig)

# AIS bar figure
order = np.argsort(-ais)
sel = list(order[:12]) + list(order[-12:])
fig, ax = plt.subplots(figsize=(6.5, 5.2))
names = [econ[i] for i in sel][::-1]; vals = [ais[i] for i in sel][::-1]
cols = ["#c0392b" if iso[i] in RESTRICTED else ("#2c6fbb" if ais[i] < 0 else "#1e8449") for i in sel][::-1]
ax.barh(range(len(sel)), vals, color=cols)
ax.set_yticks(range(len(sel))); ax.set_yticklabels(names, fontsize=7.5)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("AI Integration Surprise (jackknife logit residual, income/size/region adjusted)")
ax.set_title("Top and bottom 12 AI Integration Surprise, Q1 2026\n(red = provider-restricted economies)")
fig.tight_layout(); fig.savefig(os.path.join(REP, "fig3_ais_ranking.png")); plt.close(fig)
print("figures written")
