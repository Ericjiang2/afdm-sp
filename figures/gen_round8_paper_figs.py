"""Generate the four paper figures for the Round-8 / classical-baseline narrative.

Inputs:
  - afdm_sp_joint_unrolled/outputs_classical_baselines_python/classical_baselines_python_results.json
  - afdm_sp_joint_unrolled/outputs_teacher_margin_gate_fullsnr/teacher_margin_gate_results.json
  - afdm_sp_joint_unrolled/outputs_teacher_margin_learned_fusion_lr/teacher_margin_learned_fusion_results.json

Outputs (PDF, in paper/figures/):
  - fig_py_ber_family.pdf         BER vs SNR, classical family
  - fig_py_nmse.pdf               NMSE vs SNR (LS / OMP / Joint)
  - fig_py_iter_conv.pdf          Joint OMP-MP iteration convergence
  - fig_fusion_ber_snr.pdf        Round-8 fusion vs baselines, BER vs SNR
  - fig_fusion_bar.pdf            Round-8 per-SNR BER gain bar chart
"""
from __future__ import annotations

import json
import pathlib
import sys
import numpy as np
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]  # .../AFDM-channel-estimation
DATA_CLASSICAL = ROOT / "afdm_sp_joint_unrolled/outputs_classical_baselines_python/classical_baselines_python_results.json"
DATA_GATE = ROOT / "afdm_sp_joint_unrolled/outputs_teacher_margin_gate_fullsnr/teacher_margin_gate_results.json"
DATA_LR = ROOT / "afdm_sp_joint_unrolled/outputs_teacher_margin_learned_fusion_lr/teacher_margin_learned_fusion_results.json"
OUT = pathlib.Path(__file__).resolve().parent


def _load(path: pathlib.Path):
    if not path.exists():
        print(f"  [warn] missing {path}")
        return None
    return json.loads(path.read_text())


def _savefig(fig, name):
    out = OUT / name
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out}")


def _set_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 11,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "lines.linewidth": 1.6,
        "lines.markersize": 5,
        "grid.linestyle": ":",
        "grid.linewidth": 0.5,
    })


def fig_py_ber_family(data_cls):
    if data_cls is None:
        return
    methods = [
        ("perfect_csi_mmse", "Perfect CSI + MMSE", "o", "black"),
        ("ls_mmse",          "LS + MMSE",          "v", "tab:purple"),
        ("omp_mmse",         "OMP + MMSE",         "^", "tab:red"),
        ("omp_mp",           "OMP + MP",           "D", "tab:orange"),
        ("joint_omp_mp",     "Joint OMP-MP",       "p", "tab:green"),
    ]
    snr_list = sorted(int(s) for s in data_cls["per_snr_ber"]["joint_omp_mp"].keys())
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for key, label, mk, color in methods:
        ys = [data_cls["per_snr_ber"][key][str(s)]["mean"] for s in snr_list]
        ax.semilogy(snr_list, np.maximum(ys, 1e-5), marker=mk, color=color, label=label)
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("BER")
    ax.set_title(r"Classical baseline family (Python UWA, $P{=}10$, SP pilot, $K{=}10$)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left")
    _savefig(fig, "fig_py_ber_family.pdf")


def fig_py_nmse(data_cls):
    if data_cls is None:
        return
    methods = [
        ("ls",    "LS",             "v", "tab:purple"),
        ("omp",   "OMP",            "^", "tab:red"),
        ("joint", "Joint OMP-MP",   "p", "tab:green"),
    ]
    snr_list = sorted(int(s) for s in data_cls["per_snr_nmse"]["joint"].keys())
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    for key, label, mk, color in methods:
        ys_lin = np.array([data_cls["per_snr_nmse"][key][str(s)]["mean"] for s in snr_list])
        ys_db = 10.0 * np.log10(ys_lin + 1e-30)
        ax.plot(snr_list, ys_db, marker=mk, color=color, label=label)
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Channel estimation NMSE (dB)")
    ax.set_title("AFDM channel-estimation NMSE vs SNR")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right")
    _savefig(fig, "fig_py_nmse.pdf")


def fig_py_iter_conv(data_cls):
    if data_cls is None:
        return
    snr_list = sorted(int(s) for s in data_cls["per_snr_joint_iter_ber"].keys())
    targets = [s for s in (10, 15, 20) if s in snr_list]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    colors = {"10": "tab:orange", "15": "tab:green", "20": "tab:blue"}
    for snr in targets:
        row = data_cls["per_snr_joint_iter_ber"][str(snr)]
        y = row["iter_mean"]
        x = list(range(1, len(y) + 1))
        ax.semilogy(x, np.maximum(y, 1e-6), marker="o",
                    label=f"SNR = {snr} dB", color=colors.get(str(snr)))
    ax.set_xlabel("Outer iteration index")
    ax.set_ylabel("BER")
    ax.set_title("Joint OMP-MP iteration convergence")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper right")
    _savefig(fig, "fig_py_iter_conv.pdf")


def _agg_per_snr_ber(data):
    """Return dict method → {snr → BER mean}. 'data' is teacher_margin_gate_results.json."""
    agg = data.get("aggregated", {})
    out = {}
    for m, row in agg.items():
        if m == "gains_vs_pred":
            continue
        per_snr = row.get("per_snr_ber_mean", {})
        out[m] = {int(k): float(v) for k, v in per_snr.items()}
    return out


def _agg_lr_per_snr(data_lr):
    """Return dict method → {snr → BER mean} for learned_fusion results."""
    agg = data_lr.get("aggregated", {})
    out = {}
    for m in ("pred", "teacher", "fixed_tau_gate", "learned_fusion"):
        if m in agg:
            per_snr = agg[m].get("per_snr_mean", {})
            out[m] = {int(k): float(v) for k, v in per_snr.items()}
    return out


def fig_fusion_ber_snr(data_gate, data_lr):
    if data_lr is None:
        return
    snr_map_lr = _agg_lr_per_snr(data_lr)  # has pred/teacher/fixed_tau_gate/learned_fusion
    snr_map_gate = _agg_per_snr_ber(data_gate) if data_gate is not None else {}

    methods = [
        ("pred",            "CurrentJoint (learned)",     "o", "tab:blue",   "-"),
        ("teacher",         "Joint OMP-MP teacher",       "s", "tab:red",    "--"),
        ("fixed_tau_gate",  r"Fixed $\tau^*=0.1$ gate",   "^", "tab:orange", "-."),
        ("learned_fusion",  "Learned fusion (4-param)",   "p", "tab:green",  "-"),
    ]
    random_curve = snr_map_gate.get("random_rate_matched", {})

    snr_list = sorted(snr_map_lr.get("pred", {}).keys())
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for key, label, mk, color, ls in methods:
        if key not in snr_map_lr:
            continue
        y = [snr_map_lr[key][s] for s in snr_list]
        ax.semilogy(snr_list, np.maximum(y, 1e-5), marker=mk, color=color, linestyle=ls, label=label)
    if random_curve:
        y = [random_curve[s] for s in snr_list if s in random_curve]
        ax.semilogy(snr_list, np.maximum(y, 1e-5), marker="x", color="gray", linestyle=":",
                    label="Rate-matched random")
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("BER")
    ax.set_title(r"Learned-classical fusion on 3 untouched test caches")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left")
    _savefig(fig, "fig_fusion_ber_snr.pdf")


def fig_fusion_bar(data_gate, data_lr):
    if data_lr is None or data_gate is None:
        return
    snr_map_lr = _agg_lr_per_snr(data_lr)
    snr_map_gate = _agg_per_snr_ber(data_gate)
    snr_list = sorted(snr_map_lr.get("pred", {}).keys())

    pred = np.array([snr_map_lr["pred"][s] for s in snr_list])
    teacher = np.array([snr_map_lr["teacher"][s] for s in snr_list])
    gate = np.array([snr_map_lr["fixed_tau_gate"][s] for s in snr_list])
    learned = np.array([snr_map_lr["learned_fusion"][s] for s in snr_list])
    random = np.array([snr_map_gate["random_rate_matched"][s] for s in snr_list])

    gains = {
        "Joint OMP-MP\nteacher": pred - teacher,
        r"Fixed $\tau^*=0.1$"  "\ngate":  pred - gate,
        "Learned fusion\n(4-param)":     pred - learned,
        "Rate-matched\nrandom":           pred - random,
    }

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    n_methods = len(gains)
    width = 0.2
    x = np.arange(len(snr_list))
    colors = ["tab:red", "tab:orange", "tab:green", "gray"]
    for i, (label, values) in enumerate(gains.items()):
        ax.bar(x + (i - (n_methods - 1) / 2) * width, values, width=width, label=label,
               color=colors[i], edgecolor="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s} dB" for s in snr_list])
    ax.set_ylabel(r"BER gain vs CurrentJoint ($\Delta$BER)")
    ax.set_title("Per-SNR BER gain, 3-seed untouched test")
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.legend(loc="upper right", ncol=2, fontsize=8)
    _savefig(fig, "fig_fusion_bar.pdf")


def main():
    _set_style()
    data_cls = _load(DATA_CLASSICAL)
    data_gate = _load(DATA_GATE)
    data_lr = _load(DATA_LR)
    print("Generating classical-family figures...")
    fig_py_ber_family(data_cls)
    fig_py_nmse(data_cls)
    fig_py_iter_conv(data_cls)
    print("Generating fusion figures...")
    fig_fusion_ber_snr(data_gate, data_lr)
    fig_fusion_bar(data_gate, data_lr)
    print("Done.")


if __name__ == "__main__":
    main()
