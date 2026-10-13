"""Loop-13 2B vs 4B learned+classical comparison plot.

Overlays, at SNR 0..25:
  - Classical BP 2B (pooled) vs classical BP 4B (Loop-13 full)
  - Learned C2-rel F2-P 2B (pooled) vs learned 4B (same ckpt, OOD eval;
    if a 4B-retrained ckpt is provided, overlay that as a third curve)
  - PCSI + MMSE 2B vs 4B (lower bounds)
  - OMP + MP-serial 2B vs 4B (estimation-floor reference)

Uses IEEE/Comms journal style (serif, thin lines, hollow markers).
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from _plot_style import apply_ieee_style, BER_STYLES, finalize_axes


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


def pool_legacy(snr_key, runs):
    err_c = err_l = err_p = bits = 0
    frames_total = 0
    nmse_c_lin_sum = nmse_l_lin_sum = 0.0
    run_count = 0
    for _, d in runs:
        if d is None or snr_key not in d:
            continue
        pl = d[snr_key]
        fr = int(pl['frames'])
        err_c += int(pl['classical_errs'])
        err_l += int(pl['learned_errs'])
        err_p += int(pl.get('pcsi_errs') or 0)
        bits += int(pl['cum_bits'])
        nmse_c_lin_sum += fr * 10 ** (float(pl['classical_nmse_db']) / 10.0)
        nmse_l_lin_sum += fr * 10 ** (float(pl['learned_nmse_db']) / 10.0)
        frames_total += fr
        run_count += 1
    if run_count == 0:
        return None
    return dict(
        ber_c=err_c / max(bits, 1),
        ber_l=err_l / max(bits, 1),
        ber_p=err_p / max(bits, 1) if err_p else 0.0,
        nmse_c=10 * np.log10(nmse_c_lin_sum / frames_total + 1e-30),
        nmse_l=10 * np.log10(nmse_l_lin_sum / frames_total + 1e-30),
    )


def main():
    ap = argparse.ArgumentParser()
    # Legacy 2B pooled sources
    ap.add_argument('--r3',      default='/tmp/loop12_r3.json')
    ap.add_argument('--matched', default='/tmp/loop12_matched.json')
    ap.add_argument('--seed2',   default='/tmp/loop12_seed2.json')
    ap.add_argument('--lowsnr',
                    default='afdm_sp_joint_unrolled/outputs_loop13_2B_snr0_5_results.json')
    # Loop-13 2B/4B results
    ap.add_argument('--baseline-2b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_500f_results.json')
    ap.add_argument('--baseline-4b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_4B_results.json')
    ap.add_argument('--paired-4b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_4B_full_results.json',
                    help='paired_learned_eval --fs-factor 4 output (2B ckpt @ 4B).')
    ap.add_argument('--paired-4b-retrained', default=None,
                    help='Optional: 4B-retrained ckpt evaluated at 4B.')
    ap.add_argument('--out', default='figures/loop13/loop13_2B_vs_4B.png')
    args = ap.parse_args()

    legacy_runs = [('R3', load(args.r3)),
                   ('matched', load(args.matched)),
                   ('seed-2', load(args.seed2))]
    low = load(args.lowsnr)
    if low is not None:
        legacy_runs.append(('lowSNR', low))
    base2 = load(args.baseline_2b)
    base4 = load(args.baseline_4b)
    paired4 = load(args.paired_4b)
    paired4_retrained = load(args.paired_4b_retrained) if args.paired_4b_retrained else None

    snrs = [0, 5, 10, 15, 20, 25]
    pool2 = {s: pool_legacy(str(s), legacy_runs) for s in snrs}
    snrs_legacy = [s for s in snrs if pool2[s] is not None]

    def _arr(d, key, eps=1e-6):
        return [max(d[str(s)][key], eps) if d and str(s) in d else None for s in snrs]

    # Print table
    print('# 2B vs 4B comparison')
    print('| SNR | cls 2B | cls 4B | lrn 2B (pool) | lrn 4B (same ckpt) | lrn 4B (retrained) | PCSI 2B | PCSI 4B |')
    print('|---:|---:|---:|---:|---:|---:|---:|---:|')
    for s in snrs:
        p2 = pool2.get(s)
        cls_2b = f"{p2['ber_c']:.3e}" if p2 else '—'
        lrn_2b = f"{p2['ber_l']:.3e}" if p2 else '—'
        cls_4b = (f"{paired4[str(s)]['classical_ber']:.3e}"
                   if paired4 and str(s) in paired4 else '—')
        lrn_4b = (f"{paired4[str(s)]['learned_ber']:.3e}"
                   if paired4 and str(s) in paired4 else '—')
        lrn_4b_rt = (f"{paired4_retrained[str(s)]['learned_ber']:.3e}"
                      if paired4_retrained and str(s) in paired4_retrained else '—')
        pcsi_2b = f"{base2[str(s)]['pcsi_mmse_ber']:.3e}" if base2 and str(s) in base2 else '—'
        pcsi_4b = f"{base4[str(s)]['pcsi_mmse_ber']:.3e}" if base4 and str(s) in base4 else '—'
        print(f"| {s} | {cls_2b} | {cls_4b} | {lrn_2b} | {lrn_4b} | {lrn_4b_rt} | {pcsi_2b} | {pcsi_4b} |")

    # === Figure ===
    apply_ieee_style()
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9))

    ax = axes[0]
    # 2B curves (solid lines)
    if snrs_legacy:
        ax.semilogy(snrs_legacy, [pool2[s]['ber_c'] for s in snrs_legacy],
                    label='Classical BP — 2B', **BER_STYLES['classical'])
        ax.semilogy(snrs_legacy, [pool2[s]['ber_l'] for s in snrs_legacy],
                    label='Learned F2-P — 2B', **BER_STYLES['learned'])
    # 4B classical+learned from paired eval (dotted)
    if paired4:
        xs4 = [s for s in snrs if str(s) in paired4]
        ax.semilogy(xs4,
                    [max(paired4[str(s)]['classical_ber'], 1e-6) for s in xs4],
                    label='Classical BP — 4B', **BER_STYLES['classical_4B'])
        ax.semilogy(xs4,
                    [max(paired4[str(s)]['learned_ber'], 1e-6) for s in xs4],
                    label='Learned F2-P (2B ckpt @ 4B)',
                    **BER_STYLES['learned_4B'])
    if paired4_retrained:
        xs4r = [s for s in snrs if str(s) in paired4_retrained]
        style = {**BER_STYLES['learned'], 'linestyle': (0, (3, 1, 1, 1)),
                 'marker': '*', 'markersize': 7}
        ax.semilogy(xs4r,
                    [max(paired4_retrained[str(s)]['learned_ber'], 1e-6) for s in xs4r],
                    label='Learned F2-P (4B retrained @ 4B)', **style)
    # PCSI lower bounds
    if base2:
        ax.semilogy(snrs, [max(base2[str(s)]['pcsi_mmse_ber'], 1e-6) for s in snrs],
                    label='PCSI + MMSE — 2B', **BER_STYLES['pcsi_mmse'])
    if base4:
        ax.semilogy(snrs, [max(base4[str(s)]['pcsi_mmse_ber'], 1e-6) for s in snrs],
                    label='PCSI + MMSE — 4B', **BER_STYLES['pcsi_mmse_4B'])

    ax.set_xticks(snrs)
    ax.set_ylim(1e-6, 1.0)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='BER',
                   title='(a) BER: 2B vs 4B',
                   grid='log', legend_loc='lower left')

    # NMSE panel
    ax = axes[1]
    if snrs_legacy:
        ax.plot(snrs_legacy, [pool2[s]['nmse_c'] for s in snrs_legacy],
                label='Classical BP — 2B', **BER_STYLES['classical'])
        ax.plot(snrs_legacy, [pool2[s]['nmse_l'] for s in snrs_legacy],
                label='Learned F2-P — 2B', **BER_STYLES['learned'])
    if paired4:
        xs4n = [s for s in snrs if str(s) in paired4 and paired4[str(s)].get('classical_nmse_db') is not None]
        ax.plot(xs4n, [paired4[str(s)]['classical_nmse_db'] for s in xs4n],
                label='Classical BP — 4B', **BER_STYLES['classical_4B'])
        ax.plot(xs4n, [paired4[str(s)]['learned_nmse_db'] for s in xs4n],
                label='Learned F2-P — 4B (2B ckpt)', **BER_STYLES['learned_4B'])
    if paired4_retrained:
        xs4rn = [s for s in snrs if str(s) in paired4_retrained
                 and paired4_retrained[str(s)].get('learned_nmse_db') is not None]
        style = {**BER_STYLES['learned'], 'linestyle': (0, (3, 1, 1, 1)),
                 'marker': '*', 'markersize': 7}
        ax.plot(xs4rn, [paired4_retrained[str(s)]['learned_nmse_db'] for s in xs4rn],
                label='Learned F2-P — 4B (retrained)', **style)
    ax.set_xticks(snrs)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='Channel NMSE (dB)',
                   title='(b) NMSE: 2B vs 4B',
                   grid='linear', legend_loc='upper right')

    fig.tight_layout()
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=300, bbox_inches='tight')
    fig.savefig(outp.with_suffix('.pdf'))
    print(f'\n[saved] {outp}')


if __name__ == '__main__':
    main()
