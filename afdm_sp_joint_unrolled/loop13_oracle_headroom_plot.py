#!/usr/bin/env python
"""Loop-13 oracle-support headroom plot.

Reads ``outputs_loop13_headroom_{2B,4B}/headroom_results.json`` produced by
``classical_joint_headroom_probe.py`` and plots a grouped horizontal bar chart
showing, at SNR ∈ {15, 20, 25} dB × fs ∈ {2B, 4B}, the BER of:

    - Classical joint (baseline)
    - Oracle-support (OMP replaced by ground-truth top-K)
    - Learned C2-rel F2-P (from the main BER waterfalls)
    - PCSI + MMSE (reference)

Per-(SNR, fs) cell also annotates the fraction of the classical-to-oracle gap
closed by the learned head.

Usage::

    python afdm_sp_joint_unrolled/loop13_oracle_headroom_plot.py \
        --headroom-2b afdm_sp_joint_unrolled/outputs_loop13_headroom_2B/headroom_results.json \
        --headroom-4b afdm_sp_joint_unrolled/outputs_loop13_headroom_4B/headroom_results.json \
        --out figures/loop13/loop13_oracle_headroom.png
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _plot_style import apply_ieee_style


# Hard-coded reference numbers for the learned head and PCSI+MMSE arms at the
# headline SNRs (pulled from the main BER waterfalls already in the narrative:
# Table 2 for 2B, Table 3 for 4B). These can be overridden via --ref-json.
_DEFAULT_REF = {
    '2B': {
        15: dict(learned=2.91e-2, pcsi_mmse=8.79e-3),
        20: dict(learned=1.87e-3, pcsi_mmse=3.49e-4),
        25: dict(learned=8.35e-4, pcsi_mmse=6.84e-6),
    },
    '4B': {
        15: dict(learned=1.51e-2, pcsi_mmse=7.42e-3),
        20: dict(learned=7.39e-5, pcsi_mmse=1.17e-4),
        25: dict(learned=5.58e-6, pcsi_mmse=4.5e-6),  # PCSI censored, Clopper upper
    },
}


def _load_headroom(path: pathlib.Path):
    """Extract per-SNR baseline and oracle_support mean BERs.

    Reads the headroom_results.json structure produced by
    classical_joint_headroom_probe.py, which is
    ``{str(snr): {cname: {ber_mean, ber_std, ...}, ...}, '_config': {...}}``.
    """
    d = json.loads(path.read_text())
    out = {}
    for snr_key, cfg_map in d.items():
        if snr_key.startswith('_') or not isinstance(cfg_map, dict):
            continue
        try:
            snr = int(snr_key)
        except ValueError:
            continue
        base = cfg_map.get('baseline', {}) or {}
        osup = cfg_map.get('oracle_support', {}) or {}
        ophy = cfg_map.get('oracle_physical', {}) or {}
        out[snr] = dict(
            baseline=float(base.get('ber_mean', np.nan)),
            oracle_support=float(osup.get('ber_mean', np.nan)),
            oracle_physical=float(ophy.get('ber_mean', np.nan)) if ophy else np.nan,
        )
    return out


def _plot(panels, out_path: pathlib.Path, drop_clean_pilot: bool = False):
    apply_ieee_style()
    fs_keys = [k for k in ('2B', '4B') if panels.get(k)]
    snrs = sorted({s for k in fs_keys for s in panels[k]})
    fig, axes = plt.subplots(1, len(snrs), figsize=(3.3 * len(snrs), 3.4),
                              sharey=True)
    if len(snrs) == 1:
        axes = [axes]

    # Check whether any cell has an oracle_physical row → add the 5th bar.
    has_phys = any(
        np.isfinite(panels[fk][s].get('oracle_physical', np.nan))
        for fk in fs_keys for s in panels[fk]
    )
    # When the physical-support oracle is present and the user requested it,
    # drop the (negative-finding) clean-pilot oracle bar entirely so the figure
    # shows only Classical / Oracle physical / Learned / PCSI+MMSE.
    show_clean_pilot = has_phys and not drop_clean_pilot
    if has_phys and drop_clean_pilot:
        arms = ['Classical', 'Oracle\nphysical', 'Learned', 'PCSI+MMSE']
        colours = {
            'Classical': '#1f77b4',
            'Oracle\nphysical': '#9467bd',
            'Learned': '#d62728',
            'PCSI+MMSE': '#2ca02c',
        }
    elif has_phys:
        arms = ['Classical', 'Oracle\nclean-pilot', 'Oracle\nphysical',
                'Learned', 'PCSI+MMSE']
        colours = {
            'Classical': '#1f77b4',
            'Oracle\nclean-pilot': '#ff7f0e',
            'Oracle\nphysical': '#9467bd',  # distinct purple for the valid ceiling
            'Learned': '#d62728',
            'PCSI+MMSE': '#2ca02c',
        }
    else:
        arms = ['Classical', 'Oracle\nsupport', 'Learned', 'PCSI+MMSE']
        colours = dict(
            Classical='#1f77b4',
            **{'Oracle\nsupport': '#ff7f0e'},
            Learned='#d62728',
            **{'PCSI+MMSE': '#2ca02c'},
        )
    y_pos = np.arange(len(arms))
    fs_hatch = {'2B': None, '4B': '///'}
    single_fs_mode = (len(fs_keys) == 1)

    for ai, snr in enumerate(snrs):
        ax = axes[ai]
        width = 0.65 if single_fs_mode else 0.4
        for fi, fs in enumerate(fs_keys):
            if snr not in panels[fs]:
                continue
            row = panels[fs][snr]
            if has_phys:
                # Censored-zero physical oracle → plot at 5e-7 so the log axis
                # shows something (truly zero would be off-scale).
                ophy_raw = row.get('oracle_physical', np.nan)
                ophy = (5e-7 if (np.isfinite(ophy_raw) and ophy_raw == 0)
                        else ophy_raw)
                if show_clean_pilot:
                    vals = [row['classical'], row['oracle_support'], ophy,
                            row['learned'], row['pcsi_mmse']]
                else:
                    vals = [row['classical'], ophy,
                            row['learned'], row['pcsi_mmse']]
            else:
                vals = [row['classical'], row['oracle_support'],
                        row['learned'], row['pcsi_mmse']]
            if single_fs_mode:
                ypos_shifted = y_pos
            else:
                ypos_shifted = y_pos + (fi - 0.5) * width
            ax.barh(ypos_shifted, vals, height=width,
                    hatch=(None if single_fs_mode else fs_hatch[fs]),
                    color=[colours[a] for a in arms],
                    edgecolor='black', linewidth=0.6, alpha=0.85)
            cls = row['classical']; osup = row['oracle_support']
            ophy_raw = row.get('oracle_physical', np.nan)
            lrn = row['learned']
            # Index of the Learned bar inside the current arms list.
            lrn_idx = arms.index('Learned')
            # Prefer gap_closed vs PHYSICAL oracle (the valid ceiling).
            # Fall back to clean-pilot oracle only if physical is missing.
            if has_phys and np.isfinite(ophy_raw) and cls > 0 and lrn > 0:
                # Treat censored 0 as 0 (best-case ceiling, so denominator = cls - 0 = cls).
                denom = cls - max(ophy_raw, 0.0)
                if denom > 0:
                    gap_closed = 100.0 * (cls - lrn) / denom
                    if 0 < gap_closed <= 110:
                        lrn_y = ypos_shifted[lrn_idx]
                        ax.annotate(f'{gap_closed:.0f}% closed',
                                     xy=(max(lrn, 1e-6) * 1.2, lrn_y),
                                     fontsize=7.5, color='#333333')
            elif cls > osup > 0 and lrn > 0:
                gap_closed = 100.0 * (cls - lrn) / (cls - osup)
                if 0 < gap_closed <= 150:
                    ax.annotate(f'{gap_closed:.0f}% closed',
                                 xy=(max(lrn, osup * 1.2), ypos_shifted[2]),
                                 fontsize=7.5, color='#333333')
        ax.set_xscale('log')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(arms, fontsize=9)
        ax.set_xlabel('BER')
        ax.set_title(f'SNR = {snr} dB', fontsize=10)
        ax.grid(True, which='major', axis='x', linestyle=':',
                 linewidth=0.45, color='#bbbbbb')

    if not single_fs_mode:
        from matplotlib.patches import Patch
        legend_handles = [
            Patch(facecolor='white', edgecolor='black', label='fs = 2B'),
            Patch(facecolor='white', edgecolor='black', hatch='///',
                  label='fs = 4B'),
        ]
        fig.legend(handles=legend_handles, loc='lower center', ncol=2,
                    bbox_to_anchor=(0.5, -0.02), frameon=True, fontsize=8.5)
    title_suffix = (f' at $\\mathrm{{fs}} = {fs_keys[0]}$'
                    if single_fs_mode else '')
    if has_phys and show_clean_pilot:
        title_main = 'Top-$P$ support-oracle headroom (two oracle variants)'
    elif has_phys:
        title_main = ('Top-$P$ physical-support-oracle headroom '
                      '(classical-joint BER with OMP replaced by '
                      'simulator-truth top-$P$ atoms)')
    else:
        title_main = ('Oracle-support headroom (classical-joint BER with OMP '
                      'replaced by ground-truth top-$K$)')
    fig.suptitle(title_main + title_suffix, fontsize=10.5, y=1.02)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    fig.savefig(out_path.with_suffix('.pdf'), bbox_inches='tight')
    print(f'[saved] {out_path} (+ .pdf)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--headroom-2b', type=str, default=None,
                    help='Path to 2B headroom_results.json. Omit for 4B-only plot.')
    ap.add_argument('--headroom-4b', type=str, required=True)
    ap.add_argument('--ref-json', type=str, default=None,
                    help='Optional JSON overriding the default learned/PCSI '
                         'reference numbers.')
    ap.add_argument('--out', type=str, required=True)
    ap.add_argument('--snr-list', nargs='+', type=int, default=None,
                    help='Restrict plotted SNR cells (e.g. "15 20"); default '
                         'plots every SNR present in the headroom JSONs.')
    ap.add_argument('--drop-clean-pilot', action='store_true',
                    help='When the physical-support oracle is present, drop '
                         'the (negative-finding) clean-pilot oracle bar. '
                         'The figure then shows 4 bars: Classical, Oracle '
                         'physical, Learned, PCSI+MMSE.')
    args = ap.parse_args()

    ref = _DEFAULT_REF
    if args.ref_json:
        ref = json.loads(pathlib.Path(args.ref_json).read_text())

    h_4b = _load_headroom(pathlib.Path(args.headroom_4b))
    h_2b = (_load_headroom(pathlib.Path(args.headroom_2b))
            if args.headroom_2b else {})

    panels = {}
    snr_filter = set(args.snr_list) if args.snr_list else None
    sources = [('4B', h_4b)]
    if args.headroom_2b:
        sources.insert(0, ('2B', h_2b))
    for fs_key, headroom_per_snr in sources:
        panels[fs_key] = {}
        for snr, row in headroom_per_snr.items():
            if snr_filter is not None and snr not in snr_filter:
                continue
            ref_row = ref[fs_key].get(snr, {})
            panels[fs_key][snr] = dict(
                classical=row['baseline'],
                oracle_support=row['oracle_support'],
                oracle_physical=row.get('oracle_physical', np.nan),
                learned=float(ref_row.get('learned', np.nan)),
                pcsi_mmse=float(ref_row.get('pcsi_mmse', np.nan)),
            )

    _plot(panels, pathlib.Path(args.out),
          drop_clean_pilot=args.drop_clean_pilot)


if __name__ == '__main__':
    main()
