"""
gen_fyp_fig3_regime_gains.py
FYP Fig. 3 — Regime BER gains: zero-centered forest/dot-whisker plot.

Redesigned from bar chart (gen_fig2_regime_gains.py) to a dot-whisker plot
centered at zero, which is cleaner for showing CI direction vs. the null.

Data source: figures/data/regime_gain_summary.json
"""

import json
import pathlib

import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np

from paper_plot_style import COLORS, save_fig

HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "regime_gain_summary.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

labels = [item["label"] for item in data["regimes"]]
gains  = np.array([item["gain"]    for item in data["regimes"]], dtype=float)
ci_lo  = np.array([item["ci_low"]  for item in data["regimes"]], dtype=float)
ci_hi  = np.array([item["ci_high"] for item in data["regimes"]], dtype=float)

# Colours: green for positive, red for the failure regime
dot_colors = [COLORS["green"] if g >= 0 else COLORS["red"] for g in gains]

y = np.arange(len(labels))

fig, ax = plt.subplots(figsize=(6.8, 3.4))

# Zero reference line
ax.axvline(0.0, color="#111827", linewidth=1.0, zorder=1)

# CI whiskers
for i, (lo, hi, col) in enumerate(zip(ci_lo, ci_hi, dot_colors)):
    ax.plot([lo * 1e3, hi * 1e3], [i, i],
            color=col, linewidth=1.8, solid_capstyle="round", zorder=2)

# Central dots
for i, (g, col) in enumerate(zip(gains, dot_colors)):
    ax.scatter(g * 1e3, i, color=col, s=48, zorder=3)

# Value annotations
for i, (g, hi, lo) in enumerate(zip(gains, ci_hi, ci_lo)):
    sign = "+" if g >= 0 else ""
    ax.text(hi * 1e3 + 0.05, i, f"{sign}{g * 1e3:.2f}",
            va="center", fontsize=8, color="#1F2937")

ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.invert_yaxis()
ax.set_xlabel(r"BER gain ($\times 10^{-3}$)  [positive = improvement]")

# BER gain definition note
ax.text(0.02, -0.14,
        r"BER gain = BER(CurrentJoint) $-$ BER(FrozenCorrector).  "
        r"Error bars: paired-bootstrap 95\,\% CI.",
        ha="left", fontsize=7.5, color="#6B7280", transform=ax.transAxes)

# Shaded positive region
xlim_lo = min(ci_lo) * 1e3 * 1.5
xlim_hi = max(ci_hi) * 1e3 * 1.5
ax.set_xlim(xlim_lo, xlim_hi)
ax.axvspan(0, xlim_hi, alpha=0.04, color=COLORS["green"], zorder=0)
ax.axvspan(xlim_lo, 0, alpha=0.04, color=COLORS["red"], zorder=0)

fig.tight_layout(rect=[0, 0.05, 1, 1])
save_fig(fig, "fyp_fig3_regime_gains")
