import json
import pathlib

import matplotlib.pyplot as plt
import numpy as np

from paper_plot_style import COLORS, save_fig


HERE = pathlib.Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "feature_ablation_summary.json"


with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

labels = [item["label"] for item in data["variants"]]
gains = np.array([item["gain"] for item in data["variants"]], dtype=float)
colors = []
for item in data["variants"]:
    if item["id"] == "full":
        colors.append(COLORS["green"])
    elif item["id"] == "llr_only":
        colors.append(COLORS["red"])
    else:
        colors.append(COLORS["purple"])

fig, ax = plt.subplots(figsize=(6.8, 3.3))
y = np.arange(len(labels))
bars = ax.barh(y, gains * 1e3, color=colors, height=0.66)
ax.set_xlabel("BER gain (x$10^{-3}$)")
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.invert_yaxis()

for bar, gain in zip(bars, gains):
    ax.text(
        bar.get_width() + 0.02,
        bar.get_y() + bar.get_height() / 2,
        f"{gain * 1e3:.2f}",
        va="center",
        fontsize=8
    )

save_fig(fig, "fig4_feature_ablation")
