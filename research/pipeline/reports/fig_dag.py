#!/usr/bin/env python3
"""Causal graph of the measurement-and-outcome system (fig12)."""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Ellipse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUE, ORANGE, GRAY, GREEN, RED = "#2c6fbb", "#e67e22", "#777", "#1e8449", "#c0392b"
fig, ax = plt.subplots(figsize=(7.4, 4.6))
ax.set_xlim(0, 10); ax.set_ylim(0, 6.4); ax.axis("off")

NODES = {
 "C":  (1.5, 4.9, "C\ndevelopment\ncomplements\n(income, skills)", "obs"),
 "eta":(1.5, 1.2, "η\nnational\ndynamism", "unobs"),
 "V":  (4.6, 6.0, "V\nprovider\navailability", "part"),
 "A":  (4.3, 4.1, "A\ntrue adoption\nlevel", "unobs"),
 "Ast":(6.6, 5.2, "A*\nmeasured\nadoption\n(telemetry + ε)", "meas"),
 "dA": (4.6, 2.0, "ΔA\nadoption\ngrowth", "obs"),
 "E":  (7.3, 1.0, "E\nsector cognitive\nexposure", "obs"),
 "Y":  (8.4, 3.0, "Y\nsector\nproductivity", "obs"),
 "P":  (8.6, 5.6, "P\nAI-producer\nstatus", "obs"),
}
STYLE = {"obs": dict(fc="#eaf1fa", ec=BLUE, ls="-"),
         "unobs": dict(fc="#f2f2f2", ec=GRAY, ls="--"),
         "part": dict(fc="#fdf3e7", ec=ORANGE, ls="-"),
         "meas": dict(fc="#fdeaea", ec=RED, ls="-")}
for k, (x, y, lab, st) in NODES.items():
    s = STYLE[st]
    ax.add_patch(Ellipse((x, y), 1.9, 1.25, facecolor=s["fc"], edgecolor=s["ec"],
                         linestyle=s["ls"], lw=1.4, zorder=2))
    ax.text(x, y, lab, ha="center", va="center", fontsize=6.6, zorder=3)

def edge(a, b, color="#555", lw=1.1, rad=0.0, style="-", z=1):
    xa, ya = NODES[a][0], NODES[a][1]
    xb, yb = NODES[b][0], NODES[b][1]
    ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), connectionstyle=f"arc3,rad={rad}",
                 arrowstyle="-|>", mutation_scale=11, color=color, lw=lw,
                 linestyle=style, shrinkA=24, shrinkB=24, zorder=z))

edge("C", "A")                     # complements -> adoption
edge("C", "dA", rad=0.15)          # complements gate the growth rate (income-gated catch-up)
edge("C", "Y", rad=-0.45)          # development -> productivity dynamics
edge("C", "P", rad=-0.3)           # producers are rich economies
edge("eta", "A", rad=-0.15)        # dynamism -> adoption   (reverse-causality backdoor)
edge("eta", "Y", rad=0.25)         # dynamism -> outcomes
edge("A", "dA")                    # compounding: increments scale with level
edge("A", "Ast", color=RED)        # measurement
edge("V", "Ast", color=RED)        # availability distorts what telemetry sees
edge("A", "Y", color=GREEN, lw=2.2)  # target edge (via E-interaction)
edge("E", "Y", color=GREEN, lw=1.4)
edge("P", "Y")
ax.text(6.5, 3.85, "target:\nA x E -> Y", fontsize=7.2, color=GREEN, ha="center")
ax.text(5.6, 5.75, "measurement\nchannel", fontsize=6.6, color=RED, ha="center")

ax.text(0.15, 0.25,
        "solid blue = observed · dashed gray = unobserved · orange = partially observed · red = measurement node\n"
        "Conditioning moves: {C-proxies} closes the C backdoors (AIS); acknowledging V explains the restricted-market tail;\n"
        "conditioning on A* (level) for the rate question crosses a mediator AND imports ε - the audited, at-risk move.",
        fontsize=6.6, color="#333", va="bottom")
ax.set_title("The causal graph behind the analyses: where each conditioning move acts", fontsize=9.5)
fig.tight_layout()
fig.savefig(os.path.join(BASE, "reports/fig12_dag.png"), dpi=150, bbox_inches="tight")
print("fig12 written")
