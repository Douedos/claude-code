#!/usr/bin/env python3
"""Specification-curve figure for the normalization multiverse."""
import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mv = json.load(open(os.path.join(BASE, "exploration/multiverse_results.json")))
BLUE, ORANGE, GRAY = "#2c6fbb", "#e67e22", "#888"
plt.rcParams.update({"font.size": 8.6, "axes.edgecolor": "#999", "axes.linewidth": 0.7})

names = mv["metrics"]
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
for ax, key, title in ((axes[0], "divergence", "Outcome: diffusion divergence\n(pp gained H1'25-Q1'26, per sd of metric)"),
                       (axes[1], "growth_surprise", "Outcome: 2025 GDP growth surprise\n(pp vs Oct-24 forecast, per sd of metric)")):
    ys = np.arange(len(names))[::-1]
    for y, n in zip(ys, names):
        d = mv["spec_curve"][n][key]
        b, p = d["beta_per_sd"], d["perm_p"]
        sig = p < 0.05
        col = BLUE if b >= 0 else ORANGE
        ax.plot([0, b], [y, y], color=col, lw=1.4, alpha=0.55)
        ax.plot([b], [y], "o", ms=7 if sig else 5, color=col,
                markerfacecolor=col if sig else "white", markeredgecolor=col, markeredgewidth=1.2)
        ax.annotate(f"{b:+.2f}  p={p:.3f}", (b, y), fontsize=6.8,
                    xytext=(6 if b >= 0 else -6, -2), textcoords="offset points",
                    ha="left" if b >= 0 else "right", color="#333")
    ax.axvline(0, color="#555", lw=0.9)
    ax.set_yticks(ys); ax.set_yticklabels(names, fontsize=8)
    ax.set_title(title, fontsize=8.6)
    ax.set_xlim(-1.9, 2.3)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_xlabel("standardized association"); axes[1].set_xlabel("standardized association")
fig.suptitle("The normalization multiverse: the same data, seven adoption metrics\n"
             "filled marker = permutation p < 0.05 · blue = positive, orange = negative", fontsize=9, y=1.04)
fig.tight_layout()
fig.savefig(os.path.join(BASE, "reports/fig11_multiverse.png"), dpi=150, bbox_inches="tight")
print("fig11 written")
