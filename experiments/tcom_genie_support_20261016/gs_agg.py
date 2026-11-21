#!/usr/bin/env python
"""Aggregate genie-support rows (protocol.md section 3, task 10-16-tcom-genie-support).  Run on deinlab (needs CRB and P1 rows).

NMSE part (frames 0..499, joined with the CRB rows; frames flagged in the CRB rows are dropped from every arm and the bound):
  f_X = (m_B - m_X) / (m_B - m_M) and r_X = 10 log10(m_X / m_M), m = mean over frames, M = constrained MCRB;
  one paired frame bootstrap (2000, nearest rank) per (scenario, rho, snr) shared by every statistic.
  H-S1 on f_set, H-S2 on r_multi over the judgment points 6.5-8.0 dB (protocol section 3).
FER part (frames 0..1999, joined with the P1 ledger B and A3): crossing differences at FER 1e-2 via p2b_agg.crossing_calibration
(20000 multinomial frame weights).  Stop rule: x(GS-multi) - x(B) with CI lo > 0 in any cell.
Writes <out>/gs_results.json (_argv, _config) and <out>/GS_RESULTS.md.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / 'experiments' / 'tcom_reference_frame_20261015'))
from p2b_agg import crossing_calibration, nearest_rank  # noqa: E402

ARMS = ('GS-set', 'GS-multi')
JUDGE = (650, 700, 750, 800)
SNR = (450, 500, 550, 600, 650, 700, 750, 800)
NMSE_FRAMES = 500
FER_FRAMES = 2000
BOOT_NMSE = 2000
BOOT_FER = 20000
SEED = 20261016
ALPHA = .05


def key(r):
    return (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])


def load(d, keep=lambda r: True, slim=None):
    out = {}
    for p in sorted(Path(d).glob('rows_shard*.jsonl*')):
        opener = gzip.open if p.suffix == '.gz' else open
        with opener(p, 'rt') as handle:
            for line in handle:
                if line.strip():
                    r = json.loads(line)
                    if keep(r):
                        k = key(r)
                        if k in out:
                            raise ValueError(f'duplicate row {k}')
                        out[k] = slim(r) if slim else r
    return out


def db(x):
    return float(10 * np.log10(x))


def label(lo, hi):
    if hi < 0:
        return 'BELOW'
    if hi <= 1:
        return 'EFFICIENT'
    if hi <= 3:
        return 'NEAR'
    return 'GAP'


def ci(boot, point):
    return dict(point=float(point), lo=nearest_rank(boot, ALPHA / 2), hi=nearest_rank(boot, 1 - ALPHA / 2))


def nmse_point(gs, crb_rows, cell, snr, rng):
    sc, rho = cell
    keys = [(sc, rho, snr, f) for f in range(NMSE_FRAMES)]
    miss = [k for k in keys if k not in gs or k not in crb_rows]
    if miss:
        raise ValueError(f'missing rows for {cell} {snr}: {miss[:3]}')
    keys = [k for k in keys if not crb_rows[k]['flagged']]
    nb = np.array([crb_rows[k]['nmse_B'] for k in keys])
    m = np.array([crb_rows[k]['mcrb'] for k in keys])
    n = {a: np.array([gs[k]['arms'][a]['nmse'] for k in keys]) for a in ARMS}
    nce = {a: np.array([gs[k]['arms'][a]['nmse_ce'] for k in keys]) for a in ARMS}
    b_ok = np.array([crb_rows[k]['B_fer'] == 0 for k in keys])
    idx = rng.integers(0, len(keys), (BOOT_NMSE, len(keys)))
    mean = lambda x: x[idx].mean(1)  # noqa: E731
    mb, mm = mean(nb), mean(m)
    out = dict(frames=len(keys), flagged=NMSE_FRAMES - len(keys), mcrb_db=db(m.mean()))
    out['r_B'] = ci(10 * np.log10(mb / mm), db(nb.mean() / m.mean()))
    for a in ARMS:
        mx = mean(n[a])
        out[f'r_{a}'] = ci(10 * np.log10(mx / mm), db(n[a].mean() / m.mean()))
        out[f'r_{a}']['label'] = label(out[f'r_{a}']['lo'], out[f'r_{a}']['hi'])
        out[f'f_{a}'] = ci((mb - mx) / (mb - mm), (nb.mean() - n[a].mean()) / (nb.mean() - m.mean()))
        out[f'r_{a}_ce'] = db(nce[a].mean() / m.mean())
        out[f'nmse_db_{a}'] = db(n[a].mean())
        out[f'frac_above_m5dB_{a}'] = float(np.mean(n[a] > 10 ** -.5))
        for tag, mask in (('B_ok', b_ok), ('B_fail', ~b_ok)):
            out[f'r_{a}_{tag}'] = db(n[a][mask].mean() / m[mask].mean()) if mask.any() else None
    out['d_acq_db'] = ci(10 * np.log10(mb / mean(n['GS-set'])), db(nb.mean() / n['GS-set'].mean()))
    out['d_mult_db'] = ci(10 * np.log10(mean(n['GS-set']) / mean(n['GS-multi'])), db(n['GS-set'].mean() / n['GS-multi'].mean()))
    out['nmse_db_B'] = db(nb.mean())
    out['frac_above_m5dB_B'] = float(np.mean(nb > 10 ** -.5))
    return out


def verdict(points, stat, rule):
    los = [points[s][stat]['lo'] for s in JUDGE]
    his = [points[s][stat]['hi'] for s in JUDGE]
    if rule == 'H-S1':
        return 'SUPPORTED' if min(los) >= .5 else 'REFUTED' if max(his) < .5 else 'INCONCLUSIVE'
    return 'SUPPORTED' if max(his) <= 3 else 'REFUTED' if min(los) > 3 else 'INCONCLUSIVE'


def fer_cell(gs, p1, cell, rng):
    sc, rho = cell
    frames = range(FER_FRAMES)
    data = {}
    for a in ARMS:
        data[a] = dict(fer=np.array([[gs[(sc, rho, s, f)]['arms'][a]['fer'] for s in SNR] for f in frames], float))
    for a in ('B', 'A3'):
        data[a] = dict(fer=np.array([[p1[(sc, rho, s, f)][a] for s in SNR] for f in frames], float))
    snr = [s / 100 for s in SNR]
    pairs = (('B', 'GS-set'), ('GS-set', 'GS-multi'), ('GS-multi', 'A3'), ('B', 'GS-multi'), ('GS-multi', 'B'), ('B', 'A3'))
    out = {f'{a}-{b}': crossing_calibration(data, a, b, snr, BOOT_FER, rng) for a, b in pairs}
    out['fer'] = {a: [float(x) for x in d['fer'].mean(0)] for a, d in data.items()}
    out['syndrome_nonzero'] = {a: [float(np.mean([gs[(sc, rho, s, f)]['arms'][a]['syndrome'] != 0 for f in frames])) for s in SNR]
                               for a in ARMS}
    out['stop_rule'] = bool(out['GS-multi-B']['ci_lo'] > 0)
    return out


def fmt(c):
    return f"{c['point']:.2f} [{c['lo']:.2f}, {c['hi']:.2f}]"


def write_md(res, path):
    L = ['# Genie-support audit results (protocol.md section 3)', '',
         f"H-S1 overall: **{res['H-S1_overall']}**; H-S2 overall: **{res['H-S2_overall']}**; stop rule triggered: "
         f"**{res['stop_rule_any']}**", '']
    for cell, c in res['cells'].items():
        L += [f'## {cell}', '', f"H-S1 (f_set, 6.5-8 dB): **{c['H-S1']}**; H-S2 (r_multi <= 3 dB): **{c['H-S2']}**", '',
              '| SNR | MCRB dB | r_B | r_set [label] | r_multi [label] | f_set | f_multi | acq dB | mult dB |',
              '|---|---|---|---|---|---|---|---|---|']
        for s, p in c['nmse'].items():
            L.append(f"| {int(s) / 100:.1f} | {p['mcrb_db']:.1f} | {fmt(p['r_B'])} | {fmt(p['r_GS-set'])} {p['r_GS-set']['label']} | "
                     f"{fmt(p['r_GS-multi'])} {p['r_GS-multi']['label']} | {fmt(p['f_GS-set'])} | {fmt(p['f_GS-multi'])} | "
                     f"{fmt(p['d_acq_db'])} | {fmt(p['d_mult_db'])} |")
        f = c['fer']
        L += ['', '| crossing difference @1e-2 (dB) | point [CI] | a / b status |', '|---|---|---|']
        for k in ('B-GS-set', 'GS-set-GS-multi', 'GS-multi-A3', 'B-GS-multi', 'B-A3'):
            d = f[k]
            L.append(f"| x({d['arm_a']}) - x({d['arm_b']}) | {d['difference_db']:.2f} [{d['ci_lo']:.2f}, {d['ci_hi']:.2f}] | "
                     f"{d['crossing_a_db']:.2f} {d['status_a']} / {d['crossing_b_db']:.2f} {d['status_b']} |")
        L += ['', 'FER by SNR: ' + '; '.join(f"{a} " + ' '.join(f'{x:.4f}' for x in v) for a, v in f['fer'].items()), '']
    path.write_text('\n'.join(L) + '\n')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--rows', type=Path, default=HERE / 'out' / 'main')
    p.add_argument('--crb-rows', type=Path, default=PROJECT / 'experiments' / 'tcom_channel_crb_20261016' / 'out' / 'main')
    p.add_argument('--p1-rows', type=Path, default=PROJECT / 'experiments' / 'tcom_reference_frame_20261015' / 'out' / 'p1')
    p.add_argument('--out', type=Path, default=HERE / 'out' / 'analysis')
    args = p.parse_args(argv)
    gs = load(args.rows, lambda r: r['frame'] < FER_FRAMES)
    crb_rows = load(args.crb_rows, lambda r: r['frame'] < NMSE_FRAMES,
                    lambda r: dict(nmse_B=r['nmse']['B-final'], mcrb=r['bounds']['mcrb']['c'], flagged=bool(r['bounds']['mcrb']['flagged']),
                                   B_fer=r['B']['fer'], sigma2=r['sigma2'], frob=r['frob']))
    p1 = load(args.p1_rows, lambda r: r['frame'] < FER_FRAMES, lambda r: dict(B=r['arms']['B']['fer'], A3=r['arms']['A3']['fer']))
    join_bad = [k for k, c in crb_rows.items() if k in gs and (gs[k]['sigma2'] != c['sigma2'] or abs(gs[k]['frob'] - c['frob']) > 1e-12 * c['frob'])]
    if join_bad:
        raise ValueError(f'S5 join mismatch: {join_bad[:5]}')
    rng = np.random.default_rng(SEED)
    cells = {}
    for sc in ('G', 'U'):
        for rho in (300, 500):
            nm = {s: nmse_point(gs, crb_rows, (sc, rho), s, rng) for s in SNR}
            cells[f'{sc}, rho .{rho // 100}'] = dict(nmse=nm, **{'H-S1': verdict(nm, 'f_GS-set', 'H-S1'),
                                                                 'H-S2': verdict(nm, 'r_GS-multi', 'H-S2')},
                                                    fer=fer_cell(gs, p1, (sc, rho), rng))
    overall = lambda h: 'SUPPORTED' if all(c[h] == 'SUPPORTED' for c in cells.values()) else 'per-cell: ' + ', '.join(  # noqa: E731
        f'{k} {c[h]}' for k, c in cells.items())
    res = dict(_argv=sys.argv, _config=dict(judge_snr=JUDGE, nmse_frames=NMSE_FRAMES, fer_frames=FER_FRAMES, boot_nmse=BOOT_NMSE,
                                            boot_fer=BOOT_FER, seed=SEED, rows=str(args.rows), crb_rows=str(args.crb_rows),
                                            p1_rows=str(args.p1_rows), n_gs_rows=len(gs)),
               cells=cells, **{'H-S1_overall': overall('H-S1'), 'H-S2_overall': overall('H-S2')},
               stop_rule_any=any(c['fer']['stop_rule'] for c in cells.values()))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'gs_results.json').write_text(json.dumps(res, indent=1, default=float) + '\n')
    write_md(res, args.out / 'GS_RESULTS.md')
    print((args.out / 'GS_RESULTS.md').read_text())


if __name__ == '__main__':
    main()
