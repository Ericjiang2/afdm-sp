#!/usr/bin/env python
"""Aggregate CRB-reference rows (protocol.md section 5, task 10-16-tcom-channel-crb).

Primary (labelled): per (scenario, rho, snr), r = 10 log10(mean NMSE / mean constrained MCRB) over all non-flagged frames,
paired frame bootstrap (2000) 95% CI; pairs F0-pilot vs MCRB and B-final vs MCRB.  Labels BELOW / EFFICIENT / NEAR / GAP.
Everything else is descriptive.  Writes <out>/crb_results.json (_argv, _config) and <out>/CRB_RESULTS.md.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np

LABELLED = (('F0-pilot', 'mcrb'), ('B-final', 'mcrb'))
ESTIMATORS = ('F0-front', 'F0-pilot', 'F0-pilot-LS', 'F0-final', 'F0-final-ce', 'B-final', 'B-final-ce')
BOUNDS = ('mcrb', 'da', 'pi', 'gd')
BOOT = 2000


def db(x):
    return float(10 * np.log10(x))


def load_rows(dirs):
    rows = []
    for d in dirs:
        for p in sorted(Path(d).glob('rows_shard*.jsonl*')):
            opener = gzip.open if p.suffix == '.gz' else open
            with opener(p, 'rt') as handle:
                rows += [json.loads(x) for x in handle if x.strip()]
    return rows


def ratio_ci(num, den, rng, mask=None):
    """10log10(mean num / mean den) with a paired frame bootstrap (same resample for both)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    if mask is not None:
        num, den = num[mask], den[mask]
    m = len(num)
    if m == 0:
        return dict(n=0, r=None, lo=None, hi=None)
    idx = rng.integers(0, m, (BOOT, m))
    boot = 10 * np.log10(num[idx].mean(1) / den[idx].mean(1))
    return dict(n=int(m), r=db(num.mean() / den.mean()), lo=float(np.percentile(boot, 2.5)), hi=float(np.percentile(boot, 97.5)))


def median_ci(x, rng):
    x = np.asarray(x, float)
    if len(x) == 0:
        return dict(n=0, median=None, lo=None, hi=None)
    boot = np.median(x[rng.integers(0, len(x), (BOOT, len(x)))], 1)
    return dict(n=int(len(x)), median=float(np.median(x)), lo=float(np.percentile(boot, 2.5)), hi=float(np.percentile(boot, 97.5)))


def label(ci):
    if ci['hi'] is None:
        return 'NO-DATA'
    if ci['hi'] < 0:
        return 'BELOW'
    if ci['hi'] <= 1:
        return 'EFFICIENT'
    if ci['hi'] <= 3:
        return 'NEAR'
    return 'GAP'


def cell_stats(rows, rng):
    flagged = np.array([r['bounds']['mcrb']['flagged'] for r in rows])
    ok = ~flagged
    rows_ok = [r for r, f in zip(rows, ok) if f]
    nm = {e: np.array([r['nmse'][e] for r in rows_ok]) for e in ESTIMATORS}
    bd = {b: np.array([r['bounds'][b]['c'] if b in r['bounds'] else np.nan for r in rows_ok]) for b in BOUNDS}
    bu = {b: np.array([r['bounds'][b]['u'] if b in r['bounds'] else np.nan for r in rows_ok]) for b in BOUNDS}
    f0_ok = np.array([r['F0']['fer'] == 0 for r in rows_ok])
    b_ok = np.array([r['B']['fer'] == 0 for r in rows_ok])
    trig = np.array([r['B']['triggered'] for r in rows_ok])
    gd_mask = ~np.isnan(bd['gd'])
    out = dict(frames=len(rows), flagged=int(flagged.sum()), f0_fer=float(1 - f0_ok.mean()), b_fer=float(1 - b_ok.mean()),
               triggered=int(trig.sum()), gd_frames=int(gd_mask.sum()))
    out['curve_db'] = {**{f'nmse_{e}': db(nm[e].mean()) for e in ESTIMATORS},
                       **{f'bound_{b}': db(np.nanmean(bd[b])) for b in BOUNDS if np.isfinite(bd[b]).any()},
                       **{f'bound_{b}_unconstrained': db(np.nanmean(bu[b])) for b in BOUNDS if np.isfinite(bu[b]).any()}}
    out['gross_fraction'] = {e: float(np.mean(nm[e] > 10 ** -.5)) for e in ESTIMATORS}
    out['missed_energy_mean'] = {e: float(np.mean([r['missed_energy'][e] for r in rows_ok])) for e in ESTIMATORS}  # I1
    out['labelled'] = {}
    for e, b in LABELLED:
        ci = ratio_ci(nm[e], bd[b], rng)
        out['labelled'][f'{e}|{b}'] = dict(ci, label=label(ci))
    desc = {}
    desc['B-final|mcrb|B-decoded'] = ratio_ci(nm['B-final'], bd['mcrb'], rng, b_ok)
    desc['B-final|mcrb|B-failed'] = ratio_ci(nm['B-final'], bd['mcrb'], rng, ~b_ok)
    desc['F0-final|mcrb|all'] = ratio_ci(nm['F0-final'], bd['mcrb'], rng)
    desc['F0-final|mcrb|F0-decoded'] = ratio_ci(nm['F0-final'], bd['mcrb'], rng, f0_ok)
    desc['F0-final|da|F0-decoded'] = ratio_ci(nm['F0-final'], bd['da'], rng, f0_ok)
    desc['B-final|da|B-decoded'] = ratio_ci(nm['B-final'], bd['da'], rng, b_ok)
    desc['F0-pilot|pi|all'] = ratio_ci(nm['F0-pilot'], bd['pi'], rng)
    desc['F0-front|pi|all'] = ratio_ci(nm['F0-front'], bd['pi'], rng)
    desc['F0-pilot-LS|pi|all'] = ratio_ci(nm['F0-pilot-LS'], bd['pi'], rng)  # I1
    desc['F0-pilot-LS|mcrb|all'] = ratio_ci(nm['F0-pilot-LS'], bd['mcrb'], rng)  # I1
    desc['F0-pilot|gd|gd-subset'] = ratio_ci(nm['F0-pilot'], bd['gd'], rng, gd_mask)
    desc['pi|gd|gd-subset'] = ratio_ci(bd['pi'], bd['gd'], rng, gd_mask)
    desc['da|mcrb|all'] = ratio_ci(bd['da'], bd['mcrb'], rng)
    desc['pi|mcrb|all'] = ratio_ci(bd['pi'], bd['mcrb'], rng)
    desc['mcrb_c|mcrb_u|all'] = ratio_ci(bd['mcrb'], bu['mcrb'], rng)
    desc['median_frame_ratio_db'] = {f'{e}|mcrb': median_ci(10 * np.log10(nm[e] / bd['mcrb']), rng) for e in ('F0-pilot', 'B-final')}
    if trig.any():
        diff = 10 * np.log10(nm['B-final'][trig]) - 10 * np.log10(nm['F0-final'][trig])
        desc['rescue_db_B_minus_F0_on_triggered'] = dict(median_ci(diff, rng), improved_fraction=float(np.mean(diff < 0)))
    out['descriptive'] = desc
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seed', type=int, default=20261016)
    args = p.parse_args(argv)
    rows = load_rows(args.rows)
    rng = np.random.default_rng(args.seed)
    cells = {}
    for r in rows:
        cells.setdefault((r['scenario'], r['rho_permille'], r['snr_centi_db']), []).append(r)
    res = {}
    for key in sorted(cells):
        res['%s|%d|%d' % key] = cell_stats(sorted(cells[key], key=lambda r: r['frame']), rng)
    # wording rule: SNR points per (scenario, rho) where hi <= 1 / <= 3
    wording = {}
    for (scen, rho) in sorted({k[:2] for k in cells}):
        for pair in ('%s|%s' % x for x in LABELLED):
            pts = [(k[2] / 100, res['%s|%d|%d' % k]['labelled'][pair]) for k in sorted(cells) if k[:2] == (scen, rho)]
            wording[f'{scen}|{rho}|{pair}'] = dict(
                within_1db=[s for s, c in pts if c['label'] == 'EFFICIENT'],
                within_3db=[s for s, c in pts if c['label'] in ('EFFICIENT', 'NEAR')],
                labels={str(s): c['label'] for s, c in pts})
    flagged_max = max(c['flagged'] / c['frames'] for c in res.values())
    doc = dict(_argv=sys.argv, _config=dict(rows=[str(x) for x in args.rows], seed=args.seed, bootstrap=BOOT,
                                            labelled=LABELLED, primary_bound='constrained MCRB'),
               n_rows=len(rows), flagged_max_fraction=flagged_max, cells=res, wording=wording)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'crb_results.json').write_text(json.dumps(doc, indent=1) + '\n')
    lines = ['# CRB reference results (protocol 10-16-tcom-channel-crb, section 5)', '',
             f'rows {len(rows)}; max flagged fraction per cell {flagged_max:.4f}; primary bound = constrained MCRB.', '',
             '| scen | rho | SNR | F0 FER | B FER | MCRB dB | F0-pilot dB | r(F0-pilot) [CI] | label | B-final dB | r(B-final) [CI] | label | '
             'r(B-final), decoded | PI dB | DA−MCRB dB |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    fmt = lambda c: '%.2f [%.2f, %.2f]' % (c['r'], c['lo'], c['hi']) if c['r'] is not None else 'n/a'  # noqa: E731
    for key in sorted(cells):
        c = res['%s|%d|%d' % key]
        lp, lb = c['labelled']['F0-pilot|mcrb'], c['labelled']['B-final|mcrb']
        lines.append('| %s | %.1f | %.1f | %.4f | %.4f | %.2f | %.2f | %s | %s | %.2f | %s | %s | %s | %.2f | %.2f |' % (
            key[0], key[1] / 1000, key[2] / 100, c['f0_fer'], c['b_fer'], c['curve_db']['bound_mcrb'], c['curve_db']['nmse_F0-pilot'],
            fmt(lp), lp['label'], c['curve_db']['nmse_B-final'], fmt(lb), lb['label'],
            fmt(c['descriptive']['B-final|mcrb|B-decoded']), c['curve_db']['bound_pi'], c['descriptive']['da|mcrb|all']['r']))
    (args.out / 'CRB_RESULTS.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
