#!/usr/bin/env python
"""pick_best_tau.py — read all tau_* sweep results.json and pick best per-SNR tau.

Outputs:
    outputs_threshold_sweep/sweep_summary.md   — table of (tau, SNR, classical, learned)
    outputs_threshold_sweep/best_tau.json      — recommended per-SNR tau picks
"""
from __future__ import annotations

import argparse
import json
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='afdm_sp_joint_unrolled/outputs_threshold_sweep')
    args = ap.parse_args()

    root = pathlib.Path(args.root)
    rows = []
    for sub in sorted(root.glob('tau_*')):
        rj = sub / 'results.json'
        if not rj.exists():
            continue
        tau_str = sub.name.split('_', 1)[1]
        try:
            tau = float(tau_str)
        except ValueError:
            continue
        data = json.loads(rj.read_text())
        for snr_str, snr_row in data.items():
            if snr_str.startswith('_'):
                continue
            try:
                snr_db = int(snr_str)
            except ValueError:
                continue
            rows.append({
                'tau': tau,
                'snr_db': snr_db,
                'frames': int(snr_row['frames']),
                'classical_ber': float(snr_row['classical_ber']),
                'learned_ber': float(snr_row['learned_ber']),
                'classical_errs': int(snr_row.get('classical_errs', -1)),
                'learned_errs': int(snr_row.get('learned_errs', -1)),
                'mcnemar_n10': snr_row.get('mcnemar_n10'),
                'mcnemar_n01': snr_row.get('mcnemar_n01'),
                'mcnemar_p_one_sided': snr_row.get('mcnemar_p_one_sided'),
            })

    if not rows:
        raise SystemExit('no sweep cells found under ' + str(root))

    rows.sort(key=lambda r: (r['snr_db'], r['tau']))

    # Per-SNR minimum learned_ber
    by_snr = {}
    for r in rows:
        s = r['snr_db']
        cur = by_snr.get(s)
        if cur is None or r['learned_ber'] < cur['learned_ber']:
            by_snr[s] = r

    md = ['# Tau sweep summary',
          '',
          '## Per-(tau, SNR) BER table',
          '',
          '| tau | SNR | classical errs | learned errs | classical BER | learned BER | n10 | n01 | p (learned better) |',
          '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        p = r['mcnemar_p_one_sided']
        p_str = f'{p:.3f}' if isinstance(p, (int, float)) else '—'
        md.append(f"| {r['tau']:.0f} | {r['snr_db']} | {r['classical_errs']} | "
                  f"{r['learned_errs']} | {r['classical_ber']:.3e} | "
                  f"{r['learned_ber']:.3e} | {r['mcnemar_n10']} | "
                  f"{r['mcnemar_n01']} | {p_str} |")

    md += ['', '## Best per-SNR tau (lowest learned BER)', '',
           '| SNR | best tau | classical errs | learned errs | classical BER | learned BER |',
           '|---:|---:|---:|---:|---:|---:|']
    for snr in sorted(by_snr):
        r = by_snr[snr]
        md.append(f"| {snr} | {r['tau']:.0f} | {r['classical_errs']} | "
                  f"{r['learned_errs']} | {r['classical_ber']:.3e} | {r['learned_ber']:.3e} |")
    out_md = root / 'sweep_summary.md'
    out_md.write_text('\n'.join(md) + '\n')

    best = {str(s): {'tau': by_snr[s]['tau'],
                     'classical_ber': by_snr[s]['classical_ber'],
                     'learned_ber': by_snr[s]['learned_ber']}
            for s in sorted(by_snr)}
    (root / 'best_tau.json').write_text(json.dumps(best, indent=2))
    print(f'wrote {out_md} + best_tau.json')


if __name__ == '__main__':
    main()
