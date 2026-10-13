"""Loop-13 4B (fs=4B) vs 2B (fs=2B) sensitivity plot.

Overlays OMP+MP-serial and PCSI+MMSE BER curves for the default 2B sampling
config (fs = 2·B, Nyquist) vs the 4B over-sampled config (fs = 4·B). This is
the single-shot bandwidth sensitivity check requested by the user.

Delay resolution is tied to 1/(N·Δf) so it is unchanged; fs only re-scales
the physical Doppler to integer bins, shrinking k_max when fs doubles.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def load(path):
    return json.loads(Path(path).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--twoB',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_500f/results.json')
    ap.add_argument('--fourB',
                    default='afdm_sp_joint_unrolled/outputs_loop13_new_baselines_4B/results.json')
    ap.add_argument('--out', default='figures/loop13/loop13_4B_vs_2B.png')
    args = ap.parse_args()

    d2 = load(args.twoB)
    d4 = load(args.fourB)
    snrs = sorted(
        set(int(k) for k in d2 if k != '_config' and k.lstrip('-').isdigit())
        & set(int(k) for k in d4 if k != '_config' and k.lstrip('-').isdigit())
    )

    # Print pretty table
    print('# 4B vs 2B comparison (OMP+MP-serial, PCSI+MMSE)')
    print(f"_config[2B] = {d2.get('_config')}")
    print(f"_config[4B] = {d4.get('_config')}")
    print('| SNR | OMP BER 2B | OMP BER 4B | Δ% | PCSI BER 2B | PCSI BER 4B | OMP NMSE 2B | OMP NMSE 4B |')
    print('|---:|---:|---:|---:|---:|---:|---:|---:|')
    for s in snrs:
        r2 = d2[str(s)]
        r4 = d4[str(s)]
        delta = 100 * (r4['omp_serial_ber'] - r2['omp_serial_ber']) / max(r2['omp_serial_ber'], 1e-12)
        nmse2 = f"{r2['omp_serial_nmse_db']:+.2f}" if r2['omp_serial_nmse_db'] is not None else '—'
        nmse4 = f"{r4['omp_serial_nmse_db']:+.2f}" if r4['omp_serial_nmse_db'] is not None else '—'
        print(f"| {s} | {r2['omp_serial_ber']:.3e} | {r4['omp_serial_ber']:.3e} | "
              f"{delta:+.2f}% | {r2['pcsi_mmse_ber']:.3e} | {r4['pcsi_mmse_ber']:.3e} | "
              f"{nmse2} | {nmse4} |")

    eps = 1e-6
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.0))
    ax = axes[0]
    omp2 = [max(d2[str(s)]['omp_serial_ber'], eps) for s in snrs]
    omp4 = [max(d4[str(s)]['omp_serial_ber'], eps) for s in snrs]
    pcsi2 = [max(d2[str(s)]['pcsi_mmse_ber'], eps) for s in snrs]
    pcsi4 = [max(d4[str(s)]['pcsi_mmse_ber'], eps) for s in snrs]
    ax.semilogy(snrs, omp2, '-', color='tab:gray', linewidth=1.4,
                label='OMP+MP serial — 2B (fs=2·B)')
    ax.semilogy(snrs, omp4, '--', color='tab:gray', linewidth=1.4,
                label='OMP+MP serial — 4B (fs=4·B)')
    ax.semilogy(snrs, pcsi2, '-', color='tab:green', linewidth=1.4,
                label='PCSI+MMSE — 2B (fs=2·B)')
    ax.semilogy(snrs, pcsi4, '--', color='tab:green', linewidth=1.4,
                label='PCSI+MMSE — 4B (fs=4·B)')
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('BER (log scale, floor=1e-6)')
    ax.set_title('BER waterfall: 4B oversampling vs 2B (Nyquist)')
    ax.set_xticks(snrs)
    ax.set_ylim(1e-6, 1.0)
    ax.grid(True, which='both', alpha=0.3, linewidth=0.6)
    ax.legend(fontsize=8.5, loc='lower left')

    ax = axes[1]
    n2 = [d2[str(s)]['omp_serial_nmse_db'] for s in snrs
          if d2[str(s)]['omp_serial_nmse_db'] is not None]
    s2 = [s for s in snrs if d2[str(s)]['omp_serial_nmse_db'] is not None]
    n4 = [d4[str(s)]['omp_serial_nmse_db'] for s in snrs
          if d4[str(s)]['omp_serial_nmse_db'] is not None]
    s4 = [s for s in snrs if d4[str(s)]['omp_serial_nmse_db'] is not None]
    ax.plot(s2, n2, '-', color='tab:gray', linewidth=1.4, label='OMP — 2B')
    ax.plot(s4, n4, '--', color='tab:gray', linewidth=1.4, label='OMP — 4B')
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('Channel NMSE (dB)')
    ax.set_title('OMP channel NMSE: 4B vs 2B')
    ax.set_xticks(snrs)
    ax.grid(True, alpha=0.3, linewidth=0.6)
    ax.legend(fontsize=8.5, loc='upper right')

    fig.tight_layout()
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=150, bbox_inches='tight')
    print(f'\n[saved] {outp}')


if __name__ == '__main__':
    main()
