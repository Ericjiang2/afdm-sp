"""
gen_fyp_fig2b_corrector_ber_snr.py
FYP Fig. 2b — BER vs SNR: CurrentJoint baseline vs frozen corrector (nominal + P_paths=15).

Data source: figures/data/corrector_ber_snr.json
"""

import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig

HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "corrector_ber_snr.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

nom = data["nominal"]
p15 = data["failure_ppaths15"]

fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), sharey=False)

for ax, regime, title in [
    (axes[0], nom, "Nominal"),
    (axes[1], p15, r"Severe Path Shift ($P_\mathrm{paths}=15$)"),
]:
    snr = regime["snr_db"]
    cj = regime["CurrentJoint"]
    fc = regime["FrozenCorrector"]
    ax.semilogy(snr, cj, color=COLORS["orange"], linestyle="--",
                marker="s", markersize=4, linewidth=1.5, label="CurrentJoint (baseline)")
    ax.semilogy(snr, fc, color=COLORS["green"], linestyle="-",
                marker="o", markersize=4, linewidth=1.5, label="Frozen corrector")
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Bit Error Rate (BER)")
    ax.set_xticks(snr)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(True, which="both", linestyle=":", linewidth=0.5, color="#D1D5DB")
    ax.set_title(title, fontsize=10)

axes[0].text(
    0.02, -0.18,
    r"BER gain = BER(CurrentJoint) $-$ BER(FrozenCorrector). Positive = improvement.",
    ha="left", fontsize=7.5, color="#6B7280", transform=axes[0].transAxes,
)

fig.tight_layout(rect=[0, 0.05, 1, 1])
save_fig(fig, "fyp_fig2b_corrector_ber_snr")
