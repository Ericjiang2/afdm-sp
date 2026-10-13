"""Loop-13 4B combined plot — 4 lines, all at fs = 4B.

  1. OMP + MP (serial)            — from outputs_loop13_new_baselines_4B
  2. Classical BP (joint)         — from outputs_loop13_4B_full (paired arm)
  3. Learned C2-rel F2-P          — from outputs_loop13_4B_retrain27k_snr25_eval
                                    (4B retrained + SNR=25 regularisation)
  4. PCSI + MMSE (lower bound)    — from outputs_loop13_new_baselines_4B

IEEE / comms-journal style (serif font, thin lines, hollow markers,
tight grid).
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baselines-4b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_4B_results.json',
                    help='OMP+MP-serial + PCSI+MMSE at 4B.')
    ap.add_argument('--paired-4b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_4B_full_results.json',
                    help='Paired eval at 4B (classical arm used here).')
    ap.add_argument('--learned-4b',
                    default='afdm_sp_joint_unrolled/outputs_loop13_4B_retrain27k_snr25_eval_results.json',
                    help='4B retrained + SNR=25 ckpt eval (learned arm).')
    ap.add_argument('--out', default='figures/loop13/loop13_combined_4B_ber_mse.png')
    args = ap.parse_args()

    base = load(args.baselines_4b)
    paired = load(args.paired_4b)
    learned = load(args.learned_4b)
    snrs_plot = [0, 5, 10, 15, 20, 25]

    def _get(d, s, key, eps=1e-6):
        if str(s) not in d:
            return None
        v = d[str(s)].get(key)
        if v is None:
            return None
        return max(float(v), eps)

    # Print table
    print('# Loop-13 combined @ 4B')
    print('| SNR | OMP+MP-serial | Classical BP | Learned F2-P (4B retrain+SNR25) | PCSI+MMSE | cls NMSE | lrn NMSE | OMP NMSE |')
    print('|---:|---:|---:|---:|---:|---:|---:|---:|')
    for s in snrs_plot:
        omp_ber = _get(base, s, 'omp_serial_ber')
        cls_ber = _get(paired, s, 'classical_ber')
        lrn_ber = _get(learned, s, 'learned_ber')
        pcsi_ber = _get(base, s, 'pcsi_mmse_ber')
        cls_nm = (paired[str(s)].get('classical_nmse_db')
                  if str(s) in paired else None)
        lrn_nm = (learned[str(s)].get('learned_nmse_db')
                  if str(s) in learned else None)
        omp_nm = (base[str(s)].get('omp_serial_nmse_db')
                  if str(s) in base else None)
        row = [f"{s}"]
        for v in [omp_ber, cls_ber, lrn_ber, pcsi_ber]:
            row.append(f"{v:.3e}" if v is not None else "—")
        for v in [cls_nm, lrn_nm, omp_nm]:
            row.append(f"{v:+.2f}" if v is not None else "—")
        print("| " + " | ".join(row) + " |")

    # === Figure ===
    apply_ieee_style()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8))

    # BER panel
    ax = axes[0]
    xs = snrs_plot
    ys_omp = [_get(base, s, 'omp_serial_ber') for s in xs]
    ys_cls = [_get(paired, s, 'classical_ber') for s in xs]
    ys_lrn = [_get(learned, s, 'learned_ber') for s in xs]
    ys_pcsi = [_get(base, s, 'pcsi_mmse_ber') for s in xs]
    ax.semilogy(xs, ys_omp,
                label='OMP + MP (serial)', **BER_STYLES['omp_serial'])
    ax.semilogy(xs, ys_cls,
                label='Classical BP (joint)', **BER_STYLES['classical'])
    ax.semilogy(xs, ys_lrn,
                label='Learned C2-rel F2-P', **BER_STYLES['learned'])
    ax.semilogy(xs, ys_pcsi,
                label='PCSI + MMSE (lower bound)', **BER_STYLES['pcsi_mmse'])
    ax.set_xticks(snrs_plot)
    ax.set_ylim(1e-6, 1.0)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='BER',
                   title='(a) BER waterfall — fs = 4 · B',
                   grid='log', legend_loc='lower left')

    # NMSE panel
    ax = axes[1]
    xs_cls = [s for s in xs if str(s) in paired and paired[str(s)].get('classical_nmse_db') is not None]
    xs_lrn = [s for s in xs if str(s) in learned and learned[str(s)].get('learned_nmse_db') is not None]
    xs_omp = [s for s in xs if str(s) in base and base[str(s)].get('omp_serial_nmse_db') is not None]
    ax.plot(xs_omp, [base[str(s)]['omp_serial_nmse_db'] for s in xs_omp],
            label='OMP + MP (serial)', **BER_STYLES['omp_serial'])
    ax.plot(xs_cls, [paired[str(s)]['classical_nmse_db'] for s in xs_cls],
            label='Classical BP (joint)', **BER_STYLES['classical'])
    ax.plot(xs_lrn, [learned[str(s)]['learned_nmse_db'] for s in xs_lrn],
            label='Learned F2-P', **BER_STYLES['learned'])
    ax.set_xticks(snrs_plot)
    finalize_axes(ax, xlabel='SNR (dB)', ylabel='Channel NMSE (dB)',
                   title='(b) Channel NMSE — fs = 4 · B',
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
