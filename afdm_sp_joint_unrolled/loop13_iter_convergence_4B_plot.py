#!/usr/bin/env python
"""Loop-13 4B outer-iteration convergence plot.

Reads ``outputs_loop13_iter_convergence_4B/results.json`` produced by
``loop13_iter_convergence_probe.py --fs-factor 2.0`` and produces an
IEEE-styled log-y plot of BER vs outer-iteration count for classical BP and
learned C2-rel F2-P, at SNR ∈ {15, 20} dB.

Usage::

    python afdm_sp_joint_unrolled/loop13_iter_convergence_4B_plot.py \
        --in afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_4B/results.json \
        --out figures/loop13/loop13_iter_convergence_4B.png
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _plot_style import apply_ieee_style, finalize_axes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', type=str, required=True,
                    help='Path to results.json from loop13_iter_convergence_probe.py.')
    ap.add_argument('--out', type=str, required=True,
                    help='Output figure path (.png). .pdf sibling also written.')
    args = ap.parse_args()

    res = json.loads(pathlib.Path(args.inp).read_text())
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(4.6, 3.3))

    # Colour scheme: SNR=15 blue, SNR=20 red; classical solid, learned dashed.
    snr_colours = {'15': '#1f77b4', '20': '#d62728'}
    snr_labels = {'15': 'SNR = 15 dB', '20': 'SNR = 20 dB'}

    for snr_str in sorted(res['classical'].keys()):
        cls = res['classical'][snr_str]
        lrn = res['learned'][snr_str]
        if not cls or not lrn:
            continue
        iters_cls = sorted(int(k) for k in cls)
        iters_lrn = sorted(int(k) for k in lrn)
        colour = snr_colours.get(snr_str, '#7f7f7f')
        ax.plot(iters_cls, [cls[str(k)]['ber'] for k in iters_cls],
                marker='s', markerfacecolor='white', markersize=5,
                linestyle='-', linewidth=1.15, color=colour,
                label=f'Classical, {snr_labels[snr_str]}')
        ax.plot(iters_lrn, [lrn[str(k)]['ber'] for k in iters_lrn],
                marker='^', markerfacecolor='white', markersize=5,
                linestyle='--', linewidth=1.15, color=colour,
                label=f'Learned C2-rel F2-P, {snr_labels[snr_str]}')

    ax.set_yscale('log')
    ax.set_xlabel('Outer iteration $t$')
    ax.set_ylabel('BER')
    ax.set_xticks(sorted({int(k) for s in res['classical'].values() for k in s}))
    finalize_axes(ax, grid='log', legend_loc='upper right')

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=300, bbox_inches='tight')
    fig.savefig(out.with_suffix('.pdf'), bbox_inches='tight')
    print(f'[saved] {out}  (+ .pdf)')


if __name__ == '__main__':
    main()
