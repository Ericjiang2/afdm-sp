#!/usr/bin/env python
"""Aggregate amendment A1 (post hoc, descriptive only): GS+C against B, A3 and GS-set.  Run on deinlab.

FER (frames 0..1999): crossing differences at 1e-2 with p2b_agg.crossing_calibration (20000 weights), as protocol section 3 H-S3.
NMSE (frames 0..499, CRB rows): r = 10 log10(m_GS+C / m_MCRB) and f = (m_B - m_GS+C) / (m_B - m_MCRB), paired bootstrap 2000.
Writes <out>/a1_results.json (_argv, _config) and <out>/A1_RESULTS.md.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gs_agg as g  # noqa: E402

ARM = 'GS+C'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, default=HERE / 'out' / 'a1')
    p.add_argument('--main-rows', type=Path, default=HERE / 'out' / 'main')
    p.add_argument('--crb-rows', type=Path, default=g.PROJECT / 'experiments' / 'tcom_channel_crb_20261016' / 'out' / 'main')
    p.add_argument('--p1-rows', type=Path, default=g.PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p1')
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'analysis')
    args = p.parse_args(argv)
    a1 = g.load(args.rows, slim=lambda r: r[ARM])
    gs = g.load(args.main_rows, slim=lambda r: dict(fer=r['arms']['GS-set']['fer'], sha=r['arms']['GS-set']['decoded_sha256']))
    crb_rows = g.load(args.crb_rows, lambda r: r['frame'] < g.NMSE_FRAMES,
                      lambda r: dict(nmse_B=r['nmse']['B-final'], mcrb=r['bounds']['mcrb']['c'], flagged=bool(r['bounds']['mcrb']['flagged'])))
    p1 = g.load(args.p1_rows, lambda r: r['frame'] < g.FER_FRAMES, lambda r: dict(B=r['arms']['B']['fer'], A3=r['arms']['A3']['fer']))
    bad = [k for k, r in a1.items() if r['gs_sha256'] != gs[k]['sha']]
    if bad or len(a1) != len(gs):
        raise ValueError(f'A1-G1 failed or rows missing: {len(bad)} mismatches, {len(a1)} vs {len(gs)} rows')
    rng = np.random.default_rng(g.SEED + 1)
    snr = [s / 100 for s in g.SNR]
    cells = {}
    for sc in ('G', 'U'):
        for rho in (300, 500):
            fr = range(g.FER_FRAMES)
            data = {ARM: dict(fer=np.array([[a1[(sc, rho, s, f)]['fer'] for s in g.SNR] for f in fr], float)),
                    'GS-set': dict(fer=np.array([[gs[(sc, rho, s, f)]['fer'] for s in g.SNR] for f in fr], float))}
            for a in ('B', 'A3'):
                data[a] = dict(fer=np.array([[p1[(sc, rho, s, f)][a] for s in g.SNR] for f in fr], float))
            fer = {f'{a}-{b}': g.crossing_calibration(data, a, b, snr, g.BOOT_FER, rng)
                   for a, b in (('B', ARM), (ARM, 'A3'), ('GS-set', ARM), ('B', 'A3'))}
            trig = {s: float(np.mean([a1[(sc, rho, s, f)]['triggered'] for f in fr])) for s in g.SNR}
            kept = {s: (float(np.mean([a1[(sc, rho, s, f)]['true_set_kept'] for f in fr if a1[(sc, rho, s, f)]['triggered']]))
                        if trig[s] > 0 else None) for s in g.SNR}
            nm = {}
            for s in g.SNR:
                keys = [(sc, rho, s, f) for f in range(g.NMSE_FRAMES) if not crb_rows[(sc, rho, s, f)]['flagged']]
                x = np.array([a1[k]['nmse'] for k in keys])
                nb = np.array([crb_rows[k]['nmse_B'] for k in keys])
                m = np.array([crb_rows[k]['mcrb'] for k in keys])
                idx = rng.integers(0, len(keys), (g.BOOT_NMSE, len(keys)))
                mx, mb, mm = x[idx].mean(1), nb[idx].mean(1), m[idx].mean(1)
                nm[s] = dict(r=g.ci(10 * np.log10(mx / mm), g.db(x.mean() / m.mean())),
                             f=g.ci((mb - mx) / (mb - mm), (nb.mean() - x.mean()) / (nb.mean() - m.mean())))
            cells[f'{sc}, rho .{rho // 100}'] = dict(fer=fer, fer_curves={a: [float(v) for v in d['fer'].mean(0)] for a, d in data.items()},
                                                     triggered=trig, true_set_kept_when_triggered=kept, nmse=nm)
    res = dict(_argv=sys.argv, _config=dict(amendment='A1 post hoc, descriptive only', boot_fer=g.BOOT_FER, boot_nmse=g.BOOT_NMSE,
                                            seed=g.SEED + 1, rows=str(args.rows), n_rows=len(a1)), cells=cells)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'a1_results.json').write_text(g.json.dumps(res, indent=1, default=float) + '\n')
    L = ['# Amendment A1 (post hoc, descriptive): GS+C = GS-set + CSTATE20 iff syndrome != 0', '']
    for cell, c in cells.items():
        L += [f'## {cell}', '', '| crossing difference @1e-2 (dB) | point [CI] | a / b |', '|---|---|---|']
        for k, d in c['fer'].items():
            L.append(f"| x({d['arm_a']}) - x({d['arm_b']}) | {d['difference_db']:.2f} [{d['ci_lo']:.2f}, {d['ci_hi']:.2f}] | "
                     f"{d['crossing_a_db']:.2f} {d['status_a']} / {d['crossing_b_db']:.2f} {d['status_b']} |")
        L += ['', '| SNR | FER GS+C | FER B | FER GS-set | triggered | true set kept (trig.) | r GS+C (dB) | f GS+C |',
              '|---|---|---|---|---|---|---|---|']
        for i, s in enumerate(g.SNR):
            kp = c['true_set_kept_when_triggered'][s]
            L.append(f"| {s / 100:.1f} | {c['fer_curves'][ARM][i]:.4f} | {c['fer_curves']['B'][i]:.4f} | {c['fer_curves']['GS-set'][i]:.4f} | "
                     f"{c['triggered'][s]:.4f} | {'-' if kp is None else f'{kp:.3f}'} | {g.fmt(c['nmse'][s]['r'])} | {g.fmt(c['nmse'][s]['f'])} |")
        L.append('')
    (args.out / 'A1_RESULTS.md').write_text('\n'.join(L) + '\n')
    print((args.out / 'A1_RESULTS.md').read_text())


if __name__ == '__main__':
    main()
