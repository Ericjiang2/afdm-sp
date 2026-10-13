import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig


HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "system_impact_summary.json"


with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

labels = [item["label"] for item in data["regimes"]]
gain64 = np.array([item["gain_64"] for item in data["regimes"]], dtype=float)
gain256 = np.array([item["gain_256"] for item in data["regimes"]], dtype=float)

x = np.arange(len(labels))
width = 0.36

fig, ax = plt.subplots(figsize=(7.0, 3.4))
b1 = ax.bar(x - width / 2, gain64, width=width, color=COLORS["blue"], label="64-bit")
b2 = ax.bar(x + width / 2, gain256, width=width, color=COLORS["orange"], label="256-bit")

ax.axhline(0.0, color="#111827", linewidth=1.0)
ax.set_ylabel("Relative goodput gain (%)")
ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=18, ha="right")
ax.legend(frameon=False, ncol=2, loc="upper left")

for bars in (b1, b2):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.15,
            f"{height:.1f}",
            ha="center",
            va="bottom",
            fontsize=8
        )

save_fig(fig, "fig3_system_impact")
