#!/usr/bin/env python
"""PILOT 5 aggregation (exploratory; predictions P11-P13).  Frame-cluster bootstrap (clusters = frames 9100..9299; sm_agg.boot_weights, 2000 resamples), percentile 95% CI.

Per group (pooled, per SNR, per scenario, per cell): FER of the four combinations (variant L-diag / L-cov  x  detector fixed / joint) on the SAME SBL output;
  A_fixed     = FER(cov, fixed) - FER(diag, fixed)
  A_joint     = FER(cov, joint) - FER(diag, joint)
  interaction = [FER(diag, joint) - FER(diag, fixed)] - [FER(cov, joint) - FER(cov, fixed)]
  P12 helper  = A_joint - .5 A_fixed  (<= 0 is the P12 predicate)
all computed inside each resample (paired by frame).  A joint-detector numerical failure counts as a failed frame and is counted separately.
Transitions (fixed -> joint) per variant: [ok->ok, ok->fail, fail->ok, fail->fail].  Mean n_pair (co-delay pairs) and atoms per variant (the shared SBL output).
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'slot_mismatch_20261019'))
import sm_agg as sa  # noqa: E402  (boot_weights, ci, pt, SEED, N_BOOT)

V = {'d': 'L-diag', 'c': 'L-cov'}
FIELDS = ('n', 'd00', 'd01', 'd10', 'd11', 'c00', 'c01', 'c10', 'c11', 'd_pair', 'c_pair', 'd_atoms', 'c_atoms', 'd_err', 'c_err')
IDX = {f: i for i, f in enumerate(FIELDS)}


def load(rows_dir):
    rows = []
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        with (gzip.open if path.endswith('.gz') else open)(path, 'rt') as handle:
            rows += [json.loads(x) for x in handle if x.strip()]
    keys = [(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']) for r in rows]
    if len(keys) != len(set(keys)) or any('status' in r for r in rows):
        raise ValueError('duplicate keys or error rows')
    return rows


def vec(r):
    v = dict.fromkeys(FIELDS, 0)
    v['n'] = 1
    for k, name in V.items():
        fixed = int(r['variants'][name]['info_errors'] > 0)
        j = r['joint'][name]
        joint = 1 if j['status'] == 'error' else int(j['info_errors'] > 0)
        v[f'{k}{fixed}{joint}'] += 1
        v[f'{k}_pair'] += r['variants'][name]['n_pair']
        v[f'{k}_atoms'] += r['variants'][name]['n_atoms']
        v[f'{k}_err'] += int(j['status'] == 'error')
    return [v[f] for f in FIELDS]


def stats(S):
    S = np.asarray(S, float)
    g = lambda f: S[..., IDX[f]]  # noqa: E731
    n = g('n')
    with np.errstate(invalid='ignore', divide='ignore'):
        fer = {'diag_fixed': (g('d10') + g('d11')) / n, 'diag_joint': (g('d01') + g('d11')) / n,
               'cov_fixed': (g('c10') + g('c11')) / n, 'cov_joint': (g('c01') + g('c11')) / n}
        out = dict(fer)
        out['A_fixed'] = fer['cov_fixed'] - fer['diag_fixed']
        out['A_joint'] = fer['cov_joint'] - fer['diag_joint']
        out['interaction'] = (fer['diag_joint'] - fer['diag_fixed']) - (fer['cov_joint'] - fer['cov_fixed'])
        out['A_joint_minus_half_A_fixed'] = out['A_joint'] - .5 * out['A_fixed']
        out['A_joint_over_A_fixed'] = np.where(out['A_fixed'] != 0, out['A_joint'] / out['A_fixed'], np.nan)
    return out


def aggregate(rows, frames):
    W = sa.boot_weights(len(frames))
    fi = {f: i for i, f in enumerate(frames)}
    group_of = {'pooled': lambda r: True, **{f'snr={s}': (lambda r, s=s: r['snr_centi_db'] == s) for s in sorted({r['snr_centi_db'] for r in rows})},
                **{f'scenario={sc}': (lambda r, sc=sc: r['scenario'] == sc) for sc in sorted({r['scenario'] for r in rows})},
                **{f'cell={sc}_{s}': (lambda r, sc=sc, s=s: r['scenario'] == sc and r['snr_centi_db'] == s)
                   for sc in sorted({r['scenario'] for r in rows}) for s in sorted({r['snr_centi_db'] for r in rows})}}
    res = {}
    for name, pred in group_of.items():
        g = [r for r in rows if pred(r)]
        X = np.zeros((len(frames), len(FIELDS)), int)
        for r in g:
            X[fi[r['frame']]] += np.array(vec(r), int)
        tot = np.ones(len(frames)) @ X
        point, boot = stats(tot), stats(W @ X)
        e = dict(keys=len(g), frames=len({r['frame'] for r in g}), joint_detector_errors={k: int(tot[IDX[f'{k}_err']]) for k in V})
        for k in point:
            e[k] = sa.pt(point[k])
            e[k + '_ci95'] = sa.ci(boot[k])
        n = max(tot[IDX['n']], 1)
        for k, nm in V.items():
            e[f'transitions_{nm}_fixed_to_joint'] = {'ok->ok': int(tot[IDX[f'{k}00']]), 'ok->fail': int(tot[IDX[f'{k}01']]), 'fail->ok': int(tot[IDX[f'{k}10']]),
                                                     'fail->fail': int(tot[IDX[f'{k}11']])}
            e[f'mean_n_pair_{nm}'], e[f'mean_atoms_{nm}'] = float(tot[IDX[f'{k}_pair']] / n), float(tot[IDX[f'{k}_atoms']] / n)
        res[name] = e
    return res


def table(res):
    f = lambda e, k: ('%.4f [%.4f,%.4f]' % (e[k], e[k + '_ci95']['lo'], e[k + '_ci95']['hi'])) if e[k] is not None and e[k + '_ci95']['lo'] is not None else 'n/a'  # noqa: E731
    lines = []
    for name, e in res.items():
        lines.append(f"== {name}: keys {e['keys']}, frames {e['frames']}, joint-detector errors {e['joint_detector_errors']}")
        for k in ('diag_fixed', 'diag_joint', 'cov_fixed', 'cov_joint'):
            lines.append(f"   FER {k:<11} {f(e, k)}")
        for k in ('A_fixed', 'A_joint', 'interaction', 'A_joint_minus_half_A_fixed', 'A_joint_over_A_fixed'):
            lines.append(f"   {k:<27} {f(e, k)}")
        lines.append('   transitions fixed->joint (ok->ok / ok->fail / fail->ok / fail->fail): ' + '; '.join(
            f"{nm} " + '/'.join(str(v) for v in e[f'transitions_{nm}_fixed_to_joint'].values()) for nm in V.values())
            + f"; mean n_pair diag {e['mean_n_pair_L-diag']:.2f} cov {e['mean_n_pair_L-cov']:.2f}; mean atoms diag {e['mean_atoms_L-diag']:.2f} cov {e['mean_atoms_L-cov']:.2f}")
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    rows = load(a.rows)
    frames = sorted({r['frame'] for r in rows})
    res = dict(_label='PILOT 5, exploratory: SBL on-grid E-3 pipeline, fixed vs joint detector on the same SBL output (rho .3, SNR 7/8 dB, frames %d..%d)' % (frames[0], frames[-1]),
               bootstrap=dict(seed=sa.SEED, resamples=sa.N_BOOT, clusters='frames'), n_keys=len(rows), n_frames=len(frames), groups=aggregate(rows, frames))
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(res['_label'] + f"\nkeys {len(rows)}, frames {len(frames)}\n" + table(res['groups']))


if __name__ == '__main__':
    main()
