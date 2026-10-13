import pathlib

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = pathlib.Path(__file__).resolve().parent
OUT_PATH = HERE / "ai_generated" / "fig1_hero_pipeline.png"


def add_box(ax, x, y, w, h, text, fc, ec="#1F2937", fontsize=13, weight="bold"):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=2.0,
        facecolor=fc,
        edgecolor=ec
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, weight=weight)
    return patch


def add_arrow(ax, start, end, color="#111827", lw=2.5):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=18,
        linewidth=lw,
        color=color,
        shrinkA=2,
        shrinkB=2
    )
    ax.add_patch(arrow)


fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

# Core flow
add_box(ax, 0.03, 0.42, 0.14, 0.16, "AFDM\nInput Frame", "#D1FAE5")
add_box(ax, 0.22, 0.38, 0.18, 0.24, "CurrentJoint\nReceiver", "#DBEAFE", fontsize=15)
add_box(ax, 0.23, 0.18, 0.16, 0.11, "Observable\nTrajectory Features", "#E5E7EB", fontsize=11)

add_arrow(ax, (0.17, 0.50), (0.22, 0.50))
add_arrow(ax, (0.31, 0.38), (0.31, 0.29))

# Failed path
add_box(ax, 0.48, 0.63, 0.17, 0.13, "Mean-Residual\nDistillation", "#FEE2E2", fontsize=12)
add_box(ax, 0.72, 0.63, 0.21, 0.13, "Fails to move\nhard decisions", "#FCA5A5", fontsize=12)
add_arrow(ax, (0.40, 0.58), (0.48, 0.69), color="#B91C1C")
add_arrow(ax, (0.65, 0.69), (0.72, 0.69), color="#B91C1C")

# Successful path
add_box(ax, 0.46, 0.21, 0.19, 0.13, "Frozen\nDirect-Bit Corrector", "#DCFCE7", fontsize=12)
add_box(ax, 0.72, 0.21, 0.21, 0.13, "Train once,\ntest on many", "#86EFAC", fontsize=12)
add_arrow(ax, (0.40, 0.29), (0.46, 0.27), color="#047857")
add_arrow(ax, (0.65, 0.27), (0.72, 0.27), color="#047857")

# Positive regime group
pos_patch = FancyBboxPatch(
    (0.70, 0.42),
    0.23,
    0.16,
    boxstyle="round,pad=0.02,rounding_size=0.03",
    linewidth=2.0,
    facecolor="#ECFDF5",
    edgecolor="#047857"
)
ax.add_patch(pos_patch)
ax.text(0.815, 0.55, "Positive Regimes", ha="center", va="center", fontsize=13, weight="bold")
ax.text(
    0.815,
    0.47,
    "Nominal\nHigher Doppler\nInteger-Doppler\nLower Pilot Power",
    ha="center",
    va="center",
    fontsize=10
)
add_arrow(ax, (0.93, 0.27), (0.81, 0.42), color="#047857")

# Failure boundary
fail_patch = FancyBboxPatch(
    (0.70, 0.79),
    0.23,
    0.11,
    boxstyle="round,pad=0.02,rounding_size=0.03",
    linewidth=2.0,
    facecolor="#FEE2E2",
    edgecolor="#B91C1C"
)
ax.add_patch(fail_patch)
ax.text(0.815, 0.865, "Failure Boundary", ha="center", va="center", fontsize=13, weight="bold")
ax.text(0.815, 0.815, "Severe Path Shift\n(P_paths=15)", ha="center", va="center", fontsize=10)
add_arrow(ax, (0.93, 0.69), (0.81, 0.79), color="#B91C1C")

# Packet utility strip
strip = FancyBboxPatch(
    (0.08, 0.03),
    0.84,
    0.08,
    boxstyle="round,pad=0.02,rounding_size=0.02",
    linewidth=2.0,
    facecolor="#FFEDD5",
    edgecolor="#C2410C"
)
ax.add_patch(strip)
ax.text(0.19, 0.07, "Packet-Level Utility", ha="center", va="center", fontsize=12, weight="bold")
ax.text(0.52, 0.07, "64-bit: +3.6% to +5.7%", ha="center", va="center", fontsize=11)
ax.text(0.78, 0.07, "256-bit: +5.0% to +11.3%", ha="center", va="center", fontsize=11)

ax.text(
    0.5,
    0.96,
    "From Failed Mean Residuals to Frozen Decision-Level Correction in AFDM",
    ha="center",
    va="center",
    fontsize=18,
    weight="bold"
)

fig.savefig(OUT_PATH, dpi=300, bbox_inches="tight", pad_inches=0.05)
print(f"Saved fallback hero figure: {OUT_PATH}")
