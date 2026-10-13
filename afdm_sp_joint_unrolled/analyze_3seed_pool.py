"""analyze_3seed_pool.py — pool 3-seed results across train seeds at iter=5 and iter=10.

Reads outputs_3seed_s{20260507,20260508,20260509}_iter{5,10}/results.json,
emits per-iter pooled headlines:
  * mean BER ± std across 3 seeds
  * pooled n10/n01 counts → pooled McNemar p
  * paired-frame statistics

Output: outputs_3seed_pool_summary.md
"""
from __future__ import annotations

import json
import math
import pathlib
from typing import Dict


SEEDS = [20260507, 20260508, 20260509]
ITERS = [5, 10]
SNRS = [15, 20, 25]
ROOT = pathlib.Path(__file__).resolve().parent


def _mcnemar_one_sided_p(n10: int, n01: int) -> float:
    """One-sided p-value: probability of >=n10 successes in n10+n01 Bernoulli(0.5).
    Use normal approximation with continuity correction for large n.
    """
    n = n10 + n01
    if n == 0:
        return 1.0
    # Use normal approximation: Z = (n10 - n/2 - 0.5) / sqrt(n/4)
    import math as _math
    z = (n10 - n/2.0 - 0.5) / (n/4.0) ** 0.5
    # one-sided p = P(Z >= z) = 0.5 * erfc(z/sqrt(2))
    return 0.5 * _math.erfc(z / _math.sqrt(2.0))


def main():
    pooled = {it: {snr: dict(cls_errs=0, lrn_errs=0, n10=0, n01=0,
                              n_frames=0, cls_bers=[], lrn_bers=[],
                              cls_nmse=[], lrn_nmse=[]) for snr in SNRS}
              for it in ITERS}

    for seed in SEEDS:
        for it in ITERS:
            f = ROOT / f'outputs_3seed_s{seed}_iter{it}/results.json'
            if not f.exists():
                print(f'MISSING: {f}')
                continue
            d = json.loads(f.read_text())
            for snr in SNRS:
                e = d[str(snr)]
                p = pooled[it][snr]
                p['cls_errs'] += int(e['classical_errs'])
                p['lrn_errs'] += int(e['learned_errs'])
                p['n10'] += int(e.get('mcnemar_n10', 0))
                p['n01'] += int(e.get('mcnemar_n01', 0))
                p['n_frames'] += int(e['frames'])
                p['cls_bers'].append(float(e['classical_ber']))
                p['lrn_bers'].append(float(e['learned_ber']))
                p['cls_nmse'].append(float(e['classical_nmse_db']))
                p['lrn_nmse'].append(float(e['learned_nmse_db']))

    lines = ['# 3-seed pool summary',
             '',
             f'Train seeds: {SEEDS}',
             f'Iters: {ITERS}',
             f'SNRs: {SNRS}',
             f'Eval seed: 20260423 (canonical paired_learned_eval)',
             f'Frames per (seed, iter, snr): 200',
             '',
             ]

    for it in ITERS:
        lines.append(f'## iter={it}')
        lines.append('')
        lines.append('| SNR | mean cls BER | mean lrn BER | rel Δ (mean) | std (cls / lrn) | n10 | n01 | pooled p (1-sided) | mean NMSE cls | mean NMSE lrn |')
        lines.append('|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|')
        for snr in SNRS:
            p = pooled[it][snr]
            if p['n_frames'] == 0:
                lines.append(f'| {snr} | (no data) |  |  |  |  |  |  |  |  |')
                continue
            cls_mean = sum(p['cls_bers']) / len(p['cls_bers'])
            lrn_mean = sum(p['lrn_bers']) / len(p['lrn_bers'])
            cls_std = (sum((x - cls_mean) ** 2 for x in p['cls_bers']) / max(len(p['cls_bers']) - 1, 1)) ** 0.5
            lrn_std = (sum((x - lrn_mean) ** 2 for x in p['lrn_bers']) / max(len(p['lrn_bers']) - 1, 1)) ** 0.5
            rel = (lrn_mean - cls_mean) / max(cls_mean, 1e-30) * 100
            mc_p = _mcnemar_one_sided_p(p['n10'], p['n01'])
            cls_n_mean = sum(p['cls_nmse']) / len(p['cls_nmse'])
            lrn_n_mean = sum(p['lrn_nmse']) / len(p['lrn_nmse'])
            lines.append(f'| {snr} | {cls_mean:.3e} | {lrn_mean:.3e} | {rel:+.2f}% | {cls_std:.2e} / {lrn_std:.2e} | {p["n10"]} | {p["n01"]} | {mc_p:.2e} | {cls_n_mean:+.2f} | {lrn_n_mean:+.2f} |')
        lines.append('')

    out = ROOT / 'outputs_3seed_pool_summary.md'
    out.write_text('\n'.join(lines))
    print(f'wrote {out}')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
