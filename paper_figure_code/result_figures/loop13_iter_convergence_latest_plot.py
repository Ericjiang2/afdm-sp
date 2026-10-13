#!/usr/bin/env python
"""Latest outer-iteration convergence plot for the TCOM draft.

The FYP-era figure was generated from the April 24 mixed 80/300-frame JSON
and stopped at five outer iterations.  The May 8 records supersede it with
the ablation-H sweep over t in {1,2,3,5,7,10,15,20}.  This script reads the
Markdown record directly so the figure stays tied to the experiment log.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _plot_style import apply_ieee_style, finalize_axes


NUM_RE = re.compile(r'(?:\d+\.\d+|\d+)e[+-]?\d+|(?<![\d.])0(?![\d.])')


def _clean_cell(cell: str) -> str:
    return (cell.replace('**', '')
                .replace('←', '')
                .replace('IDENTICAL to iter=15', '')
                .strip())


def _parse_summary_table(path: pathlib.Path) -> dict[int, dict[int, tuple[float, float]]]:
    """Return {snr: {outer_iter: (classical_ber, learned_ber)}}."""
    rows: dict[int, dict[int, tuple[float, float]]] = {15: {}, 20: {}, 25: {}}
    in_table = False
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if line.startswith('| iter | SNR=15'):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith('|'):
            if rows[15]:
                break
            continue
        if line.startswith('|:') or line.startswith('|---'):
            continue
        parts = [p.strip() for p in line.strip('|').split('|')]
        if len(parts) < 4:
            continue
        m_iter = re.search(r'\d+', parts[0])
        if not m_iter:
            continue
        outer_iter = int(m_iter.group(0))
        for snr, cell in zip((15, 20, 25), parts[1:4]):
            nums = NUM_RE.findall(_clean_cell(cell))
            if len(nums) >= 2:
                rows[snr][outer_iter] = (float(nums[0]), float(nums[1]))
    if not rows[15] or not rows[20]:
        raise RuntimeError(f'No outer-iteration table parsed from {path}')
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--summary-md', required=True,
                    help='outputs_ablation_H_outer_iter_20/CEILING_TEST_SUMMARY.md')
    ap.add_argument('--out', required=True,
                    help='Output figure path (.png); .pdf sibling also written.')
    args = ap.parse_args()

    rows = _parse_summary_table(pathlib.Path(args.summary_md))
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(4.7, 3.2))

    colours = {15: '#1f77b4', 20: '#d62728'}
    for snr in (15, 20):
        iters = sorted(rows[snr])
        cls = [rows[snr][t][0] for t in iters]
        lrn = [rows[snr][t][1] for t in iters]
        ax.plot(iters, cls, marker='s', markerfacecolor='white',
                markersize=4.8, linewidth=1.15, color=colours[snr],
                label=f'Classical, SNR = {snr} dB')
        # Matplotlib cannot render log(0), but zeros occur only for the
        # learned SNR=20 curve after t=15; plot at 5e-7 and label as censored.
        lrn_plot = [5e-7 if v == 0 else v for v in lrn]
        ax.plot(iters, lrn_plot, marker='^', markerfacecolor='white',
                markersize=4.8, linewidth=1.15, linestyle='--',
                color=colours[snr], label=f'Learned, SNR = {snr} dB')

    ax.axvline(5, color='#777777', linestyle=':', linewidth=0.8)
    ax.axvline(10, color='#555555', linestyle='-.', linewidth=0.8)

    ax.set_yscale('log')
    ax.set_xlabel('Outer iteration count $T_\\mathrm{out}$')
    ax.set_ylabel('BER')
    ax.set_xticks([1, 2, 3, 5, 7, 10, 15, 20])
    ax.set_ylim(4e-7, 1.4e-1)
    finalize_axes(ax, grid='log', legend_loc='lower left')

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=300, bbox_inches='tight')
    fig.savefig(out.with_suffix('.pdf'), bbox_inches='tight')
    print(f'[saved] {out} (+ .pdf)')


if __name__ == '__main__':
    main()
