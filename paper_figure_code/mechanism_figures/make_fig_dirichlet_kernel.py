"""Generate Fig 5b: Dirichlet kernel cross-section.

Plots |D(delta)| = |sin(pi*delta) / (N * sin(pi*delta/N))| over delta in [-3, 3]
Doppler-bin units, with N = N_sub = 1024.  Two curves overlaid:
  - Integer-aligned case (k_real - k = 0): main lobe at delta=0, deep nulls at
    integer offsets — what an integer-Doppler dictionary would see.
  - Worst-case fractional residual (|k_real - k| = 0.5): main lobe shifted, the
    integer side-lobes at delta = +/-1, +/-2 carry non-trivial energy — the
    physical mechanism that the learned head exploits.

The k_leak = 2 truncation boundary is marked with a dashed vertical line; the
energy outside this boundary (the sum of squared coefficients at |delta| > 2)
is what is dropped by the Dirichlet expansion in Section 2.2.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Reuse the existing IEEE plot style from afdm_sp_joint_unrolled/_plot_style.py
_THIS = pathlib.Path(__file__).resolve()
_REPO = _THIS.parent.parent.parent  # paper/figures_mechanism/.. /.. = repo root
sys.path.insert(0, str(_REPO / 'afdm_sp_joint_unrolled'))
from _plot_style import apply_ieee_style  # noqa: E402


def dirichlet(delta: np.ndarray, N: int) -> np.ndarray:
    """|D(delta)| = |sin(pi*delta) / (N * sin(pi*delta/N))|."""
    eps = 1e-12
    num = np.abs(np.sin(np.pi * delta))
    den = N * np.abs(np.sin(np.pi * delta / N))
    return num / np.maximum(den, eps)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--N', type=int, default=1024, help='Number of sub-carriers')
    p.add_argument('--k-leak', type=int, default=2, help='Dirichlet truncation half-width')
    p.add_argument('--out', type=str,
                   default=str(_REPO / 'paper' / 'system_block' / 'fig_dirichlet_kernel.pdf'))
    args = p.parse_args()

    apply_ieee_style()

    delta = np.linspace(-3.0, 3.0, 6001)

    # Integer-aligned case: kappa = k_real - k = 0 (no fractional residual)
    D_aligned = dirichlet(delta, args.N)

    # Worst-case fractional residual: |kappa| = 0.5, so the kernel is shifted
    # by +0.5 in delta and the integer dictionary bins sample at delta - 0.5.
    D_worst = dirichlet(delta - 0.5, args.N)

    fig, ax = plt.subplots(figsize=(3.7, 3.0))
    ax.plot(delta, D_aligned, color='#1f77b4', linestyle='-', linewidth=1.4,
            label=r'Integer-aligned ($\kappa = 0$)')
    ax.plot(delta, D_worst, color='#d62728', linestyle='-', linewidth=1.4,
            label=r'Worst-case fractional ($\kappa = 0.5$)')

    # Mark integer Doppler-bin sample positions for the worst-case curve.
    int_offsets = np.array([-2, -1, 0, 1, 2])
    int_samples = dirichlet(int_offsets - 0.5, args.N)
    ax.scatter(int_offsets, int_samples, marker='o', s=28, facecolor='white',
               edgecolor='#d62728', linewidths=1.2, zorder=5,
               label=r'Integer-bin samples (worst case)')

    # k_leak = 2 truncation boundaries.
    for x in (-args.k_leak, args.k_leak):
        ax.axvline(x, color='gray', linestyle=(0, (3, 2)), linewidth=0.9, alpha=0.7)
    ax.text(args.k_leak + 0.05, 0.85, r'$k_{\mathrm{leak}}=2$',
            fontsize=8, color='gray', va='top')

    ax.set_xlabel(r'Doppler-bin offset $\delta$')
    ax.set_ylabel(r'$|D(\delta)|$')
    ax.set_xlim([-3.0, 3.0])
    ax.set_ylim([0, 1.05])
    ax.set_xticks([-3, -2, -1, 0, 1, 2, 3])
    ax.grid(True, alpha=0.3, linewidth=0.6)
    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.95,
              borderpad=0.4, handlelength=1.6, handletextpad=0.5)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.3)
    fig.savefig(out, format='pdf', bbox_inches='tight')
    print(f'wrote {out} ({out.stat().st_size} bytes)')


if __name__ == '__main__':
    main()
