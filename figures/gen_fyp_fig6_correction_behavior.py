"""
gen_fyp_fig6_correction_behavior.py
FYP Fig. 6 — Correction-behavior analysis (two-panel).

Left panel: Decision oracle headroom (nominal) — how much oracle-beneficial vs oracle-harmful
            opportunity exists in the backbone receiver output.
Right panel: Frozen corrector flip breakdown — nominal vs P_paths=15,
             showing why the method succeeds in nominal and fails at P_paths=15.

Data source: figures/data/correction_behavior.json
"""

import json
import pathlib

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig

HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "correction_behavior.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

oracle = data["oracle_analysis"]
flip_nom = data["corrector_flip_analysis"]["nominal"]
flip_p15 = data["corrector_flip_analysis"]["failure_ppaths15"]

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))

# ── Left panel: Oracle headroom (nominal) ────────────────────────────────────
ax_left = axes[0]
oracle_ben  = oracle["oracle_beneficial_flip_rate"]
oracle_harm = oracle["oracle_harmful_flip_rate"]

y = np.array([0])
ax_left.barh(y, oracle_ben * 100, height=0.55, color=COLORS["green"])
ax_left.barh(y, oracle_harm * 100, height=0.55, left=oracle_ben * 100,
             color=COLORS["red"])
ax_left.text(oracle_ben * 100 / 2, 0,
             f"{oracle_ben * 100:.2f}%", ha="center", va="center",
             fontsize=8.5, color="white", fontweight="bold")
ax_left.text(oracle_ben * 100 + oracle_harm * 100 / 2, 0,
             f"{oracle_harm * 100:.2f}%", ha="center", va="center",
             fontsize=8.5, color="white", fontweight="bold")

ax_left.set_yticks([0])
ax_left.set_yticklabels(["Decision Oracle\n(Nominal)"])
ax_left.set_xlabel("Fraction of all bits (%)")
ax_left.set_xlim(0, 9)
ax_left.text(0.5, -0.26,
             f"Teacher disagreement: {oracle['teacher_different_rate'] * 100:.2f}% of bits",
             ha="center", transform=ax_left.transAxes, fontsize=8, color="#6B7280")

# ── Right panel: Frozen corrector flip breakdown (nominal vs P_paths=15) ─────
ax_right = axes[1]
row_labels = ["Nominal", r"$P_\mathrm{paths}=15$"]
ben_vals  = [flip_nom["beneficial_correction_rate"], flip_p15["beneficial_correction_rate"]]
harm_vals = [flip_nom["harmful_correction_rate"],    flip_p15["harmful_correction_rate"]]

y = np.arange(2)
ax_right.barh(y, [v * 100 for v in ben_vals], height=0.55,
              color=COLORS["green"])
ax_right.barh(y, [v * 100 for v in harm_vals], height=0.55,
              left=[v * 100 for v in ben_vals], color=COLORS["red"])

# Annotate values
for i, (b, h) in enumerate(zip(ben_vals, harm_vals)):
    ax_right.text(b * 100 / 2, i,
                  f"{b * 100:.2f}%", ha="center", va="center",
                  fontsize=8, color="white", fontweight="bold")
    ax_right.text(b * 100 + h * 100 / 2, i,
                  f"{h * 100:.2f}%", ha="center", va="center",
                  fontsize=8, color="white", fontweight="bold")

ax_right.set_yticks(y)
ax_right.set_yticklabels(row_labels)
ax_right.set_xlabel("Fraction of all bits (%)")
ax_right.invert_yaxis()
xlim = max([(b + h) * 100 for b, h in zip(ben_vals, harm_vals)]) * 1.6
ax_right.set_xlim(0, max(xlim, 5))

ax_right.text(0.5, -0.26,
              "Harmful > Beneficial at $P_\\mathrm{paths}=15$ explains BER regression",
              ha="center", transform=ax_right.transAxes, fontsize=8, color="#6B7280")

# Shared legend
ben_patch  = mpatches.Patch(color=COLORS["green"], label="Beneficial flips")
harm_patch = mpatches.Patch(color=COLORS["red"],   label="Harmful flips")
fig.legend(handles=[ben_patch, harm_patch], frameon=False,
           loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.10))

fig.tight_layout(rect=[0, 0.08, 1, 1])
save_fig(fig, "fyp_fig6_correction_behavior")
