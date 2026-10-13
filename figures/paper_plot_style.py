import pathlib

import matplotlib
import matplotlib.pyplot as plt


FIG_DIR = pathlib.Path(__file__).resolve().parent
FONT_SIZE = 10

matplotlib.rcParams.update(
    {
        "font.size": FONT_SIZE,
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "axes.labelsize": FONT_SIZE,
        "axes.titlesize": FONT_SIZE + 1,
        "xtick.labelsize": FONT_SIZE - 1,
        "ytick.labelsize": FONT_SIZE - 1,
        "legend.fontsize": FONT_SIZE - 1,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.usetex": False,
        "mathtext.fontset": "stix"
    }
)

COLORS = {
    "blue": "#2563EB",
    "green": "#10B981",
    "orange": "#EA580C",
    "purple": "#7C3AED",
    "red": "#DC2626",
    "gray": "#6B7280"
}


def save_fig(fig, stem):
    path = FIG_DIR / f"{stem}.pdf"
    fig.savefig(path)
    print(f"Saved: {path}")
