"""
gen_fyp_fig2_traditional_ber.py
FYP Fig. 2 — BER vs SNR: traditional receiver family comparison.

Data source: figures/data/traditional_ber_snr.json
"""

import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig

HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "traditional_ber_snr.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

snr = data["snr_db"]
methods = data["methods"]

# Method display config: label -> (color_key, linestyle, marker)
METHOD_STYLE = {
    "JointOMP-MP":            (COLORS["gray"],   "--",  "s"),
    "TRADPARAM Fixed":        (COLORS["blue"],   "-",   "o"),
    "TRADPARAM Classical Full":(COLORS["purple"], "-.",  "^"),
    "Stage6 Param Joint":     (COLORS["green"],  ":",   "D"),
}
# Display labels
METHOD_LABEL = {
    "JointOMP-MP":             "JointOMP-MP (classical)",
    "TRADPARAM Fixed":         "TRADPARAM Fixed (strongest traditional)",
    "TRADPARAM Classical Full":"TRADPARAM Classical Full",
    "Stage6 Param Joint":      "Stage-6 Param Joint",
}

fig, ax = plt.subplots(figsize=(6.0, 4.0))

for name, ber_vals in methods.items():
    color, ls, mk = METHOD_STYLE.get(name, (COLORS["gray"], "-", "o"))
    label = METHOD_LABEL.get(name, name)
    ax.semilogy(
        snr, ber_vals,
        color=color, linestyle=ls, marker=mk,
        markersize=5, linewidth=1.5, label=label,
    )

ax.set_xlabel("SNR (dB)")
ax.set_ylabel("Bit Error Rate (BER)")
ax.set_xticks(snr)
ax.legend(frameon=False, fontsize=9)
ax.grid(True, which="both", linestyle=":", linewidth=0.5, color="#D1D5DB")
ax.text(
    0.02, -0.14,
    "Python-aligned evaluation protocol. 100 frames per SNR, seed=42.",
    ha="left", fontsize=7.5, color="#6B7280", transform=ax.transAxes,
)

fig.tight_layout(rect=[0, 0.05, 1, 1])
save_fig(fig, "fyp_fig2_traditional_ber")
