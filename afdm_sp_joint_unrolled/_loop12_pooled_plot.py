"""Loop-12 3-seed pooled BER + NMSE waterfall.

Pools R3 (seed 20260423, 5 SNRs) + matched-F2P (seed 20260423 subset, SNRs 20/25/30)
+ seed-2 (seed 20260424, SNRs 20/25/30). At each SNR, combines raw error counts
and bit totals across runs → single pooled BER per arm. NMSE averaged in linear
MSE domain then back to dB (weighted by frame count).

Output: `figures/loop12/loop12_pooled_ber_mse.png`.
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


def pool_snr(snr_key, runs):
    """Pool per-SNR stats across available runs."""
    err_c = err_t = err_l = err_p = bits = 0
    frames_total = 0
    nmse_c_lin_sum = nmse_t_lin_sum = nmse_l_lin_sum = 0.0
    run_count = 0
    contrib = []
    for name, d in runs:
        if snr_key not in d:
            continue
        pl = d[snr_key]
        fr = int(pl['frames'])
        err_c += int(pl['classical_errs'])
        err_t += int(pl['torch_ref_errs'])
        err_l += int(pl['learned_errs'])
        err_p += int(pl.get('pcsi_errs', 0)) if 'pcsi_errs' in pl else 0
        bits += int(pl['cum_bits'])
        nmse_c_lin_sum += fr * 10 ** (float(pl['classical_nmse_db']) / 10.0)
        nmse_t_lin_sum += fr * 10 ** (float(pl['torch_ref_nmse_db']) / 10.0)
        nmse_l_lin_sum += fr * 10 ** (float(pl['learned_nmse_db']) / 10.0)
        frames_total += fr
        contrib.append((name, fr))
        run_count += 1
    if run_count == 0:
        return None
    ber_c = err_c / max(bits, 1)
    ber_t = err_t / max(bits, 1)
    ber_l = err_l / max(bits, 1)
    ber_p = err_p / max(bits, 1)
    nmse_c = 10.0 * np.log10(nmse_c_lin_sum / frames_total + 1e-30)
    nmse_t = 10.0 * np.log10(nmse_t_lin_sum / frames_total + 1e-30)
    nmse_l = 10.0 * np.log10(nmse_l_lin_sum / frames_total + 1e-30)
    return dict(ber_c=ber_c, ber_t=ber_t, ber_l=ber_l, ber_p=ber_p,
                nmse_c=nmse_c, nmse_t=nmse_t, nmse_l=nmse_l,
                frames=frames_total, bits=bits,
                contrib=contrib)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--r3',
                    default='afdm_sp_joint_unrolled/outputs_loop12_r3_official/results.json')
    ap.add_argument('--matched',
                    default='afdm_sp_joint_unrolled/outputs_loop12_matched_f2p_s20_30/results.json')
    ap.add_argument('--seed2',
                    default='afdm_sp_joint_unrolled/outputs_loop12_seed2_s20_s25_s30/results.json')
    ap.add_argument('--out', default='figures/loop12/loop12_pooled_ber_mse.png')
    args = ap.parse_args()

    runs = [
        ('R3 (500f seed=20260423, 5-SNR)', load(args.r3)),
        ('matched (300f seed=20260423, 3-SNR)', load(args.matched)),
        ('seed-2 (500f seed=20260424, 3-SNR)', load(args.seed2)),
    ]

    # Gather union of SNRs
    snr_set = set()
    for _, d in runs:
        for k in d:
            if k != '_config':
                try:
                    snr_set.add(int(k))
                except ValueError:
                    pass
    snrs = sorted(snr_set)

    pooled = {}
    for s in snrs:
        pooled[s] = pool_snr(str(s), runs)

    # Print pooled table
    print('# Loop-12 3-seed pooled table')
    print('| SNR | n_runs | total frames | total bits | cls BER | tref BER | learned BER | PCSI | Δ vs cls | visible dB | cls / learned NMSE (dB) |')
    print('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
    for s in snrs:
        r = pooled[s]
        delta = 100 * (r['ber_l'] - r['ber_c']) / max(r['ber_c'], 1e-12)
        vis_db = (np.log10(max(r['ber_c'], 1e-12)) - np.log10(max(r['ber_l'], 1e-12))) * 10 / 1  # decades*10
        pcsi_str = f"{r['ber_p']:.3e}" if r['ber_p'] > 0 else "0"
        print(f"| {s} | {len(r['contrib'])} | {r['frames']} | {r['bits']} | "
              f"{r['ber_c']:.3e} | {r['ber_t']:.3e} | {r['ber_l']:.3e} | {pcsi_str} | "
              f"{delta:+.2f} % | {vis_db:.2f} | {r['nmse_c']:.2f} / {r['nmse_l']:.2f} |")

    # Plot
    eps = 1e-6
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    ax = axes[0]
    x = snrs
    cls = [max(pooled[s]['ber_c'], eps) for s in snrs]
    tref = [max(pooled[s]['ber_t'], eps) for s in snrs]
    lrn = [max(pooled[s]['ber_l'], eps) for s in snrs]
    pcsi = [max(pooled[s]['ber_p'], eps) if pooled[s]['ber_p'] > 0 else None for s in snrs]

    ax.semilogy(x, cls, 's-', color='tab:blue', lw=2, ms=9, label='Classical BP-joint (pooled, torch)')
    ax.semilogy(x, tref, 'd--', color='tab:cyan', lw=1.2, ms=7, alpha=0.7, label='Torch-ref (pooled)')
    ax.semilogy(x, lrn, '^-', color='tab:red', lw=2.4, ms=10, label='Learned C2-rel F2-P (pooled)')
    # PCSI upper bound shading
    x_pcsi = [xi for xi, pi in zip(x, pcsi) if pi is not None]
    y_pcsi = [pi for pi in pcsi if pi is not None]
    if x_pcsi:
        ax.semilogy(x_pcsi, y_pcsi, 'o-.', color='tab:green', lw=1.5, ms=7,
                    alpha=0.9, label='PCSI-BP upper bound')

    # Individual-run faint overlays for context
    markers = ['o', 's', '^']
    for (name, d), m in zip(runs, markers):
        xs = sorted(int(k) for k in d if k != '_config' and k.lstrip('-').isdigit())
        ys = [max(d[str(s)]['learned_ber'], eps) for s in xs]
        ax.semilogy(xs, ys, m, color='tab:red', ms=5, mfc='white', alpha=0.45,
                    label=f'  learned — {name}' if m == 'o' else None)

    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('BER (log scale, floor=1e-6)')
    ax.set_title('Loop-12 pooled BER waterfall (3 runs: R3 + matched + seed-2)')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(fontsize=7.8, loc='lower left')
    ax.set_ylim(1e-6, 1)

    # NMSE panel
    ax = axes[1]
    ax.plot(x, [pooled[s]['nmse_c'] for s in snrs], 's-', color='tab:blue', lw=2, ms=9,
            label='Classical (pooled)')
    ax.plot(x, [pooled[s]['nmse_t'] for s in snrs], 'd--', color='tab:cyan', lw=1.2, ms=7,
            alpha=0.7, label='Torch-ref (pooled)')
    ax.plot(x, [pooled[s]['nmse_l'] for s in snrs], '^-', color='tab:red', lw=2.4, ms=10,
            label='Learned F2-P (pooled)')
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('Channel NMSE (dB)')
    ax.set_title('Loop-12 pooled channel-NMSE')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc='upper right')

    fig.tight_layout()
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outp, dpi=150, bbox_inches='tight')
    print(f'\n[saved] {outp}')


if __name__ == '__main__':
    main()
