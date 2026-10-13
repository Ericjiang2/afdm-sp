"""Loop-13 combined plot: pooled classical BP / learned + OMP+MP-serial +
PCSI+MMSE at SNR {0, 5, 10, 15, 20, 25}.

IEEE / comms-journal style (via _plot_style.apply_ieee_style()):
  - Serif font, thin lines (1.2 pt), hollow-face markers, tight grid.
  - Classical BP + learned pooled across Loop-12 R3 + matched + seed-2 AND
    topped up with Loop-13 2B @ SNR {0, 5}.
  - OMP+MP-serial and PCSI+MMSE from Loop-13 2B sweep (SNR 0..25).
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
    return json.loads(Path(path).read_text())


def pool_legacy(snr_key, runs):
    err_c = err_l = err_p = bits = 0
    frames_total = 0
    nmse_c_lin_sum = nmse_l_lin_sum = 0.0
    run_count = 0
    for _, d in runs:
        if snr_key not in d:
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
        frames=frames_total, bits=bits,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--r3', default='/tmp/loop12_r3.json')
    ap.add_argument('--matched', default='/tmp/loop12_matched.json')
    ap.add_argument('--seed2', default='/tmp/loop12_seed2.json')
    ap.add_argument('--lowsnr',
                    default='afdm_sp_joint_unrolled/outputs_loop13_2B_snr0_5_results.json',
                    help='Loop-13 paired eval at SNR 0,5 (2B).')
    ap.add_argument('--loop13',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_500f_results.json')
    ap.add_argument('--out', default='figures/loop13/loop13_combined_ber_mse.png')
    args = ap.parse_args()

    legacy_runs = [('R3', load(args.r3)),
                   ('matched', load(args.matched)),
                   ('seed-2', load(args.seed2))]
    # Optional SNR 0/5 top-up
    low = None
    if Path(args.lowsnr).exists():
        low = load(args.lowsnr)
        legacy_runs.append(('lowSNR', low))
    loop13 = load(args.loop13)
    snrs_plot = [0, 5, 10, 15, 20, 25]

    legacy_pool = {s: pool_legacy(str(s), legacy_runs) for s in snrs_plot}
    legacy_snrs = [s for s in snrs_plot if legacy_pool[s] is not None]

    # Print summary
    print('# Combined (2B) pooled table')
    print('| SNR | cls BER | learned BER | Δ% | OMP+MP-serial | PCSI+MMSE |')
    print('|---:|---:|---:|---:|---:|---:|')
    for s in snrs_plot:
        leg = legacy_pool.get(s)
        new = loop13.get(str(s))
        cls_ber = f"{leg['ber_c']:.3e}" if leg else '—'
        lrn_ber = f"{leg['ber_l']:.3e}" if leg else '—'
        delta = (f"{100*(leg['ber_l']-leg['ber_c'])/max(leg['ber_c'],1e-12):+.1f}%"
                 if leg else '—')
        omp_ber = f"{new['omp_serial_ber']:.3e}" if new else '—'
        pcsi_ber = f"{new['pcsi_mmse_ber']:.3e}" if new else '—'
        print(f"| {s} | {cls_ber} | {lrn_ber} | {delta} | {omp_ber} | {pcsi_ber} |")

    # === Figure ===
    apply_ieee_style()
    eps = 1e-6
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))

    ax = axes[0]
    xs = snrs_plot
    ys_omp = [max(loop13[str(s)]['omp_serial_ber'], eps) for s in xs]
    ax.semilogy(xs, ys_omp, label='OMP + MP (serial, 2B)',
                **BER_STYLES['omp_serial'])

    if legacy_snrs:
        ys_cls = [max(legacy_pool[s]['ber_c'], eps) for s in legacy_snrs]
        ax.semilogy(legacy_snrs, ys_cls,
                    label='Classical BP (joint, pooled 2B)',
                    **BER_STYLES['classical'])
        ys_lrn = [max(legacy_pool[s]['ber_l'], eps) for s in legacy_snrs]
        ax.semilogy(legacy_snrs, ys_lrn,
                    label='Learned C2-rel F2-P (pooled 2B)',
                    **BER_STYLES['learned'])

    ys_pcsi = [max(loop13[str(s)]['pcsi_mmse_ber'], eps) for s in xs]
    ax.semilogy(xs, ys_pcsi, label='PCSI + MMSE (lower bound, 2B)',
                **BER_STYLES['pcsi_mmse'])

    ax.set_xticks(snrs_plot)
    ax.set_ylim(1e-6, 1.0)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='BER',
                   title='(a) BER waterfall — 2B (fs = 2B, Nyquist)',
                   grid='log', legend_loc='lower left')

    # NMSE
    ax = axes[1]
    xs_omp = [s for s in xs if loop13[str(s)]['omp_serial_nmse_db'] is not None]
    ys_omp_n = [loop13[str(s)]['omp_serial_nmse_db'] for s in xs_omp]
    ax.plot(xs_omp, ys_omp_n, label='OMP + MP (serial)',
            **BER_STYLES['omp_serial'])
    if legacy_snrs:
        ax.plot(legacy_snrs, [legacy_pool[s]['nmse_c'] for s in legacy_snrs],
                label='Classical BP (pooled)', **BER_STYLES['classical'])
        ax.plot(legacy_snrs, [legacy_pool[s]['nmse_l'] for s in legacy_snrs],
                label='Learned F2-P (pooled)', **BER_STYLES['learned'])
    ax.set_xticks(snrs_plot)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='Channel NMSE (dB)',
                   title='(b) Channel NMSE — 2B',
                   grid='linear', legend_loc='upper right')

    fig.tight_layout()
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=300, bbox_inches='tight')
    fig.savefig(outp.with_suffix('.pdf'))
    print(f'\n[saved] {outp}')
    print(f'[saved] {outp.with_suffix(".pdf")}')


if __name__ == '__main__':
    main()
