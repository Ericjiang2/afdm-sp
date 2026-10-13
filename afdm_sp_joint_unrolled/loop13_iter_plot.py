"""Loop-13 BER vs outer-iteration count — IEEE style.

Reads `outputs_loop13_iter_convergence_v2/results.json` (produced by
`loop13_iter_convergence_probe.py`) and emits a clean figure.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from _plot_style import apply_ieee_style, finalize_axes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--results',
                    default='afdm_sp_joint_unrolled/outputs_loop13_iter_convergence_v2_results.json')
    ap.add_argument('--out', default='figures/loop13/loop13_iter_convergence.png')
    args = ap.parse_args()

    d = json.loads(Path(args.results).read_text())
    snrs = sorted(int(s) for s in d['classical'].keys())

    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(5.0, 3.8))

    snr_palette = {15: '#1f77b4', 20: '#d62728'}
    line_props = dict(linewidth=1.2, markersize=5.5, markeredgewidth=1.2,
                      markerfacecolor='white')
    for snr in snrs:
        c = snr_palette.get(snr, 'black')
        cls = d['classical'][str(snr)]
        xs = sorted(int(it) for it in cls)
        ys = [cls[str(it)]['ber'] for it in xs]
        ax.semilogy(xs, ys, color=c, linestyle='-', marker='s',
                    label=f'Classical BP (SNR = {snr} dB)', **line_props)
        lrn = d['learned'][str(snr)]
        xs_l = sorted(int(it) for it in lrn)
        ys_l = [lrn[str(it)]['ber'] for it in xs_l]
        ax.semilogy(xs_l, ys_l, color=c, linestyle=(0, (3, 1)),
                    marker='^', label=f'Learned C2-rel F2-P (SNR = {snr} dB)',
                    **line_props)

    ax.set_xticks(sorted(set(int(it) for s in snrs
                              for it in d['classical'][str(s)])))
    finalize_axes(ax, xlabel='Outer-iteration count',
                   ylabel='BER',
                   title='BER vs outer-iteration count (2B)',
                   grid='log', legend_loc='upper right')

    fig.tight_layout()
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=300, bbox_inches='tight')
    fig.savefig(outp.with_suffix('.pdf'))
    print(f'[saved] {outp}')


if __name__ == '__main__':
    main()
