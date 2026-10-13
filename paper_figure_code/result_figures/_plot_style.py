"""Shared matplotlib styling for Loop-13 figures.

Target look-and-feel: IEEE / Elsevier Comms journal waterfall plots.

Design principles baked in:
  - Serif font (Times New Roman / DejaVu Serif fallback)
  - Thin lines (1.1 pt), larger hollow-face markers for distinguishability
  - Narrow log-grid without the matplotlib default grey fill
  - Tight tick labels with mathtext fractions for dB
  - Compact legend box with rounded corners, white face

Use:
    from _plot_style import (
        apply_ieee_style, BER_STYLES, NMSE_STYLES, finalize_axes,
    )
    apply_ieee_style()
    fig, ax = plt.subplots(figsize=(3.7, 3.1))
    ax.semilogy(snrs, ber, **BER_STYLES['classical'], label='Classical BP')
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='BER', grid='log')
"""
from __future__ import annotations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


# Per-curve styles shared across all waterfall figures for consistency.
# Markers use a hollow face (markerfacecolor='white') so they do not obscure
# the line or each other when curves cross.
_BASE = dict(linewidth=1.2, markersize=5.5, markeredgewidth=1.2,
             markerfacecolor='white')

BER_STYLES = {
    'pcsi_mmse':    dict(color='#2ca02c', linestyle=(0, (3, 1)),
                         marker='o', **_BASE),        # green, dashed
    'classical':    dict(color='#1f77b4', linestyle='-',
                         marker='s', **_BASE),        # blue, solid, square
    'learned':      dict(color='#d62728', linestyle='-',
                         marker='^', **_BASE),        # red, solid, triangle
    'omp_serial':   dict(color='#7f7f7f', linestyle=(0, (5, 2)),
                         marker='v', **_BASE),        # grey, loose dash
    # 4B variants — same colour, dotted line, diamond marker.
    'pcsi_mmse_4B':  dict(color='#2ca02c', linestyle=(0, (1, 1.5)),
                          marker='D', **_BASE),
    'classical_4B':  dict(color='#1f77b4', linestyle=(0, (1, 1.5)),
                          marker='D', **_BASE),
    'learned_4B':    dict(color='#d62728', linestyle=(0, (1, 1.5)),
                          marker='D', **_BASE),
    'omp_serial_4B': dict(color='#7f7f7f', linestyle=(0, (1, 1.5)),
                          marker='D', **_BASE),
}

NMSE_STYLES = {k: v for k, v in BER_STYLES.items()}


_RCPARAMS = {
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif', 'Nimbus Roman',
                   'Liberation Serif'],
    'mathtext.fontset': 'stix',
    'font.size': 10,
    'axes.labelsize': 10.5,
    'axes.titlesize': 11,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 8.8,
    'legend.frameon': True,
    'legend.framealpha': 0.95,
    'legend.edgecolor': '#555555',
    'legend.fancybox': True,
    'axes.grid': False,
    'axes.linewidth': 0.85,
    'xtick.major.width': 0.85,
    'ytick.major.width': 0.85,
    'xtick.minor.width': 0.6,
    'ytick.minor.width': 0.6,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
}


def apply_ieee_style():
    """Update rcParams — idempotent, safe to call multiple times."""
    plt.rcParams.update(_RCPARAMS)


def finalize_axes(ax, xlabel=None, ylabel=None, title=None, grid='log',
                   legend_loc='best', ncol_legend=1):
    """Standard axis finish: grid, labels, legend, tick ends.

    grid: 'log' for a semilogy BER panel, 'linear' for NMSE.
    """
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)
    if grid == 'log':
        ax.grid(True, which='major', linestyle='-', linewidth=0.45,
                color='#bbbbbb')
        ax.grid(True, which='minor', linestyle=':', linewidth=0.35,
                color='#dddddd')
    else:
        ax.grid(True, which='major', linestyle='-', linewidth=0.45,
                color='#bbbbbb')
    ax.legend(loc=legend_loc, ncol=ncol_legend)


def ber_legend_label(kind, pooled=False, onB='2B'):
    """Consistent labels across figures."""
    base = {
        'pcsi_mmse':  'PCSI + MMSE',
        'classical':  'Classical BP (joint)',
        'learned':    'Learned C2-rel F2-P',
        'omp_serial': 'OMP + MP (serial)',
    }[kind]
    if pooled:
        base += ' (pooled)'
    return f'{base} — {onB}' if onB else base
