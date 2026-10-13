import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig


HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "regime_gain_summary.json"


with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

labels = [item["label"] for item in data["regimes"]]
gains = np.array([item["gain"] for item in data["regimes"]], dtype=float)
lower = np.array([item["gain"] - item["ci_low"] for item in data["regimes"]], dtype=float)
upper = np.array([item["ci_high"] - item["gain"] for item in data["regimes"]], dtype=float)
colors = [COLORS["green"] if g >= 0 else COLORS["red"] for g in gains]

fig, ax = plt.subplots(figsize=(6.8, 3.3))
x = np.arange(len(labels))
bars = ax.bar(x, gains * 1e3, color=colors, width=0.72)
ax.errorbar(
    x,
    gains * 1e3,
    yerr=np.vstack([lower, upper]) * 1e3,
    fmt="none",
    ecolor="#111827",
    elinewidth=1.2,
    capsize=4
)
ax.axhline(0.0, color="#111827", linewidth=1.0)
ax.set_ylabel("BER gain (x$10^{-3}$)")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=18, ha="right")

for bar, gain in zip(bars, gains):
    y = bar.get_height()
    va = "bottom" if y >= 0 else "top"
    offset = 0.05 if y >= 0 else -0.10
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        y + offset,
        f"{gain * 1e3:.2f}",
        ha="center",
        va=va
    )

save_fig(fig, "fig2_regime_gains")
