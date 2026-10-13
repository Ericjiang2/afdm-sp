#!/usr/bin/env python
"""Loop-13 support-recall probe (Probe a).

Post-process cached feature files produced by `loop9_cache_features.py` to
compute the OMP-once recall against the Dirichlet-weighted oracle support.

The cache stores, per frame:
  - ``cand_cols``  : (M,)  off-support candidate column indices.
  - ``y``          : (M,)  binary label; y_i = 1 iff cand_cols[i] is an oracle
                           atom that OMP missed. (sum(y) ≈ number of missed
                           oracle atoms; exact when M is large enough that all
                           missed atoms survive the top-M residual-ranking,
                           which is the regime of our caches since M=48 or 96
                           and |missed| ≤ sparsity = 8.)
  - ``p_real``     : ()    OMP support size (= sparsity = P_paths).

Both the OMP support and the oracle support have size = sparsity, so
``precision == recall`` in this setting; we report a single "recall" number.

Outputs a JSON summary (one entry per SNR) and a line plot of mean recall vs
SNR.  No Monte-Carlo; reads only the cached tensors.

Usage::

    python afdm_sp_joint_unrolled/loop13_support_recall_probe.py \
        --cache-dir afdm_sp_joint_unrolled/outputs_loop13_4B_cache \
        --snr-list 10 15 20 25 \
        --out afdm_sp_joint_unrolled/outputs_loop13_support_recall
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import torch


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

try:
    from afdm_sp_joint_unrolled._plot_style import apply_ieee_style
except Exception:  # pragma: no cover - optional
    def apply_ieee_style():
        import matplotlib.pyplot as plt
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['axes.linewidth'] = 0.8


def _load_cache(cache_path: pathlib.Path) -> dict:
    """Load a cache_snr{SNR}.pt file produced by loop9_cache_features.py."""
    d = torch.load(cache_path, map_location='cpu', weights_only=False)
    y = d['y'].numpy()                      # (N, M)
    p_real = d['p_real'].numpy()            # (N,)
    snr = int(d['snr'])
    return dict(y=y, p_real=p_real, snr=snr, n=int(d.get('n', y.shape[0])))


def _per_frame_recall(y: np.ndarray, p_real: np.ndarray) -> dict:
    """Return per-frame recall array and summary stats.

    recall_i = (p_real_i - missed_i) / p_real_i
    missed_i = sum over candidates j of (y_ij == 1)
    """
    missed_per_frame = (y == 1).sum(axis=1)                     # (N,)
    p_real_f = p_real.astype(np.float64)
    hits = np.maximum(p_real_f - missed_per_frame, 0.0)
    recall = hits / np.maximum(p_real_f, 1.0)
    frac_bad_frames = float(np.mean(missed_per_frame >= 1))
    return dict(
        recall=recall,
        missed=missed_per_frame.astype(np.int64),
        mean_recall=float(np.mean(recall)),
        std_recall=float(np.std(recall)),
        median_recall=float(np.median(recall)),
        mean_missed=float(np.mean(missed_per_frame)),
        std_missed=float(np.std(missed_per_frame)),
        frac_frames_with_missed=frac_bad_frames,
        frames=int(recall.size),
    )


def _plot_recall_vs_snr(per_snr, out_png: pathlib.Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    apply_ieee_style()
    snrs = sorted(per_snr.keys())
    means = [per_snr[s]['mean_recall'] for s in snrs]
    bad_fracs = [per_snr[s]['frac_frames_with_missed'] for s in snrs]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.5, 3.4))
    ax1.plot(snrs, means, marker='o', markersize=5,
              markerfacecolor='white', linewidth=1.2, color='tab:blue')
    ax1.set_xlabel('SNR (dB)')
    ax1.set_ylabel('Mean OMP-once recall')
    ax1.set_ylim([max(min(means) - 0.05, 0.0), 1.01])
    ax1.grid(True, which='both', alpha=0.3, linewidth=0.6)
    ax1.set_title('Recall vs SNR (OMP-once vs oracle)', fontsize=10)
    ax2.plot(snrs, bad_fracs, marker='s', markersize=5,
              markerfacecolor='white', linewidth=1.2, color='tab:red')
    ax2.set_xlabel('SNR (dB)')
    ax2.set_ylabel('Fraction of frames with $\\geq 1$ missed atom')
    ax2.set_ylim([0.0, max(max(bad_fracs) * 1.1, 0.1)])
    ax2.grid(True, which='both', alpha=0.3, linewidth=0.6)
    ax2.set_title('Mechanism prevalence: head is useful on\nthis fraction of frames',
                  fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200, bbox_inches='tight')
    fig.savefig(out_png.with_suffix('.pdf'), bbox_inches='tight')
    print(f'[saved] {out_png} (+ .pdf)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache-dir', type=str, required=True,
                    help='Directory containing cache_snr{SNR}.pt files.')
    ap.add_argument('--snr-list', nargs='+', type=int,
                    default=[10, 15, 20, 25])
    ap.add_argument('--out', type=str, required=True,
                    help='Output directory for recall_by_snr.json + log.')
    ap.add_argument('--fig-out', type=str,
                    default='figures/loop13/loop13_support_recall.png')
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = pathlib.Path(args.cache_dir)
    if not cache_dir.is_dir():
        raise SystemExit(f'cache-dir not found: {cache_dir}')

    per_snr = {}
    for snr in args.snr_list:
        cache_path = cache_dir / f'cache_snr{snr}.pt'
        if not cache_path.exists():
            print(f'[warn] {cache_path} missing; skipping.')
            continue
        print(f'[snr={snr}] loading {cache_path}...')
        d = _load_cache(cache_path)
        stats = _per_frame_recall(d['y'], d['p_real'])
        # Drop the raw arrays before JSON dump.
        dump = {k: v for k, v in stats.items() if k not in ('recall', 'missed')}
        dump['snr'] = d['snr']
        per_snr[int(snr)] = dump
        print(f'  mean_recall={stats["mean_recall"]:.4f} '
              f'median={stats["median_recall"]:.4f} '
              f'mean_missed={stats["mean_missed"]:.3f} '
              f'frac_bad={stats["frac_frames_with_missed"]:.4f} '
              f'frames={stats["frames"]}')

    # JSON output
    (out_dir / 'recall_by_snr.json').write_text(
        json.dumps({
            '_meta': {'cache_dir': str(cache_dir),
                       'snr_list': args.snr_list,
                       'note': 'recall = (p_real - missed) / p_real; '
                               'precision == recall because |OMP|=|oracle|=sparsity'},
            'per_snr': per_snr,
        }, indent=2))
    print(f'[saved] {out_dir}/recall_by_snr.json')

    # Plot
    fig_path = pathlib.Path(args.fig_out)
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    _plot_recall_vs_snr(per_snr, fig_path)
    print('[done]')


if __name__ == '__main__':
    main()
