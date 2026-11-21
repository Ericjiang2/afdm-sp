#!/usr/bin/env python
"""PILOT aggregation for slot_mismatch (exploratory, not pre-registered; PROTOCOL.md section 4 labels do NOT apply).

Per cap s, pooled over the slice and per SNR: slot-count distribution, triggered keys, rescue rate R(A1_s), R(A2_s) (share of triggered keys with 0
information-bit errors), D_s = R(A1_s) - R(A2_s), doublet (co-delay pair in the final geometry) share of triggered units for A1_s / A2_s, F0_s FER,
B_s FER (A1_s on triggered keys, F0_s otherwise), A3 FER, with frame counts.  Frame-cluster bootstrap (clusters = frames, shared across scenario, SNR and s),
percentile 95% CI.  Ratio D_12/D_8 is computed inside each resample (NaN when D_8 = 0 or a group has no triggered key).
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from pathlib import Path

import numpy as np

FIELDS = ('n', 'trig', 'resc1', 'resc2', 'dbl1', 'dbl2', 'f0fail', 'bfail', 'a3fail')
SEED, N_BOOT = 20261019, 2000


def label(rows, caps):
    snr = '/'.join(f'{v / 100:.1f}' for v in sorted({r['snr_centi_db'] for r in rows}))
    rho = '/'.join(f"{v / 1000:g}" for v in sorted({r['rho_permille'] for r in rows}))
    fr = sorted({r['frame'] for r in rows})
    return f'PILOT, exploratory (frames {fr[0]}..{fr[-1]}, rho {rho}, SNR {snr} dB, s in {set(caps)}); no frozen decision rule applies'


def load_rows(rows_dir):
    rows = []
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        op = gzip.open if path.endswith('.gz') else open
        with op(path, 'rt') as handle:
            rows += [json.loads(x) for x in handle if x.strip()]
    keys = [(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate keys')
    bad = [k for r, k in zip(rows, keys) if r['A3'].get('status') != 'ok'
           or any(a.get('status') != 'ok' for s in r['s'].values() for a in s['arms'].values())]
    if bad:
        raise ValueError(f'{len(bad)} keys with error records, e.g. {bad[:3]}')
    return rows


def doublet(delays):
    return len(set(delays)) < len(delays)


def counts(rows, caps, snrs, frames):
    """C[s]: (n_frames, n_snr, len(FIELDS)) integer counts; frames are the bootstrap clusters."""
    fi, si = {f: i for i, f in enumerate(frames)}, {v: i for i, v in enumerate(snrs)}
    C = {s: np.zeros((len(frames), len(snrs), len(FIELDS)), int) for s in caps}
    for r in rows:
        i, j = fi[r['frame']], si[r['snr_centi_db']]
        a3 = int(r['A3']['info_errors'] > 0)
        for s in caps:
            d = r['s'][str(s)]
            f0fail = int(d['f0']['info_errors'] > 0)
            if d['triggered']:
                a1, a2 = d['arms']['A1'], d['arms']['A2']
                v = (1, 1, a1['info_errors'] == 0, a2['info_errors'] == 0, doublet(a1['final_delays']), doublet(a2['final_delays']), f0fail,
                     a1['info_errors'] > 0, a3)
            else:
                v = (1, 0, 0, 0, 0, 0, f0fail, f0fail, a3)
            C[s][i, j] += np.array(v, int)
    return C


def stats(S):
    """S[..., len(FIELDS)] sums -> rates (NaN where the denominator is 0)."""
    S = np.asarray(S, float)
    f = dict(zip(FIELDS, np.moveaxis(S, -1, 0)))
    with np.errstate(invalid='ignore', divide='ignore'):
        out = dict(R_A1=f['resc1'] / f['trig'], R_A2=f['resc2'] / f['trig'], doublet_A1=f['dbl1'] / f['trig'], doublet_A2=f['dbl2'] / f['trig'],
                   F0_FER=f['f0fail'] / f['n'], B_FER=f['bfail'] / f['n'], A3_FER=f['a3fail'] / f['n'])
    out['D'] = out['R_A1'] - out['R_A2']
    return out


def ci(x):
    x = np.asarray(x)[~np.isnan(x)]
    return dict(lo=float(np.percentile(x, 2.5)), hi=float(np.percentile(x, 97.5)), n_valid=int(x.size)) if x.size else dict(lo=None, hi=None, n_valid=0)


def pt(x):
    return None if np.isnan(x) else float(x)


def boot_weights(n_frames):
    rng = np.random.default_rng(SEED)
    return np.stack([np.bincount(rng.integers(0, n_frames, n_frames), minlength=n_frames) for _ in range(N_BOOT)]).astype(float)


def paired_q1(rows, snrs, frames, W, lo=8, hi=12):
    """Q1 readout paired by key: FER(X_hi) - FER(X_lo) for X = F0 and B (B = A1 on triggered keys, F0 otherwise); frame-cluster bootstrap."""
    fi, si = {f: i for i, f in enumerate(frames)}, {v: i for i, v in enumerate(snrs)}
    Q = np.zeros((len(frames), len(snrs), 5), int)   # n, F0_lo fail, F0_hi fail, B_lo fail, B_hi fail
    for r in rows:
        v = [1]
        for X in ('f0', 'b'):
            for s in (lo, hi):
                d = r['s'][str(s)]
                f0 = int(d['f0']['info_errors'] > 0)
                v.append(f0 if X == 'f0' or not d['triggered'] else int(d['arms']['A1']['info_errors'] > 0))
        Q[fi[r['frame']], si[r['snr_centi_db']]] += np.array(v, int)
    out = {}
    for name, g in {'pooled': None, **{str(v): j for j, v in enumerate(snrs)}}.items():
        X = Q.sum(axis=1) if g is None else Q[:, g, :]
        tot, boot = np.ones(len(frames)) @ X, W @ X
        e = dict(n_keys=int(tot[0]), F0_fail_lo=int(tot[1]), F0_fail_hi=int(tot[2]), B_fail_lo=int(tot[3]), B_fail_hi=int(tot[4]))
        for k, (a, b) in (('dFER_F0', (1, 2)), ('dFER_B', (3, 4))):
            e[k] = float((tot[b] - tot[a]) / tot[0])
            e[k + '_ci95'] = ci((boot[:, b] - boot[:, a]) / boot[:, 0])
        out[name] = e
    return out


def summarize(C, caps, snrs, frames, rows, W):
    ones = np.ones(len(frames))
    groups = {'pooled': None, **{str(v): j for j, v in enumerate(snrs)}}

    res = dict(_label=label(rows, caps), bootstrap=dict(seed=SEED, resamples=N_BOOT, clusters='frames'), n_frames=len(frames), n_keys=len(rows), s={})
    D = {}
    for s in caps:
        res['s'][str(s)] = {}
        for name, g in groups.items():
            X = C[s].sum(axis=1) if g is None else C[s][:, g, :]
            tot = ones @ X
            point, boot = stats(tot), stats(W @ X)
            D[(s, name)] = (float(point['D']), boot['D'])
            e = dict(n_keys=int(tot[0]), n_frames_with_keys=int((X[:, 0] > 0).sum()),
                     triggered=int(tot[1]), rescued_A1=int(tot[2]), rescued_A2=int(tot[3]), doublet_units_A1=int(tot[4]), doublet_units_A2=int(tot[5]))
            for k in ('R_A1', 'R_A2', 'D', 'doublet_A1', 'doublet_A2', 'F0_FER', 'B_FER', 'A3_FER'):
                e[k] = pt(point[k])
                if k in ('R_A1', 'R_A2', 'D'):
                    e[k + '_ci95'] = ci(boot[k])
            sel = [r for r in rows if name == 'pooled' or str(r['snr_centi_db']) == name]
            e['slot_count_counts'] = {str(c): sum(r['s'][str(s)]['f0']['slot_count'] == c for r in sel) for c in sorted({r['s'][str(s)]['f0']['slot_count'] for r in sel})}
            e['n_distinct_nominated_delays'] = dict(min=min(r['n_distinct_nominated_delays'] for r in sel), median=float(np.median([r['n_distinct_nominated_delays'] for r in sel])),
                                                    max=max(r['n_distinct_nominated_delays'] for r in sel))
            res['s'][str(s)][name] = e
    if 8 in caps and 12 in caps:
        res['ratio_D12_over_D8'] = {}
        for name in groups:
            (d8, b8), (d12, b12) = D[(8, name)], D[(12, name)]
            with np.errstate(invalid='ignore', divide='ignore'):
                ratio = np.where(b8 != 0, b12 / b8, np.nan)
            res['ratio_D12_over_D8'][name] = dict(point=pt(d12 / d8) if d8 == d8 and d8 != 0 else None, ci95=ci(ratio),
                                                 resamples_with_D8_undefined_or_zero=int(np.isnan(ratio).sum()))
    return res


def table(res):
    lines = [res['_label'], f"frames {res['n_frames']}, keys {res['n_keys']}, bootstrap {res['bootstrap']['resamples']} frame-cluster resamples"]
    for s, groups in res['s'].items():
        lines.append(f'--- cap s={s}')
        lines.append(f"{'group':>8} {'keys':>5} {'trig':>5} {'R(A1)':>6} {'R(A2)':>6} {'D':>7} {'D 95% CI':>17} {'dbl A1':>7} {'dbl A2':>7} {'F0 FER':>7} {'B FER':>7} {'A3 FER':>7}  slots")
        for name, e in groups.items():
            f = lambda x: '   n/a' if x is None else f'{x:6.3f}'  # noqa: E731
            c = e['D_ci95']
            cis = 'n/a' if c['lo'] is None else f"[{c['lo']:+.3f},{c['hi']:+.3f}]"
            lines.append(f"{name:>8} {e['n_keys']:5d} {e['triggered']:5d} {f(e['R_A1'])} {f(e['R_A2'])} {f(e['D']):>7} {cis:>17} {f(e['doublet_A1'])}  {f(e['doublet_A2'])}  "
                         f"{f(e['F0_FER'])}  {f(e['B_FER'])}  {f(e['A3_FER'])}  {e['slot_count_counts']}")
    for name, e in res.get('q1_paired_12_minus_8', {}).items():
        lines.append(f"Q1 paired 12-8 [{name}] n={e['n_keys']}: dFER(F0) {e['dFER_F0']:+.4f} [{e['dFER_F0_ci95']['lo']:+.4f},{e['dFER_F0_ci95']['hi']:+.4f}] "
                     f"(fail {e['F0_fail_lo']}->{e['F0_fail_hi']}); dFER(B) {e['dFER_B']:+.4f} [{e['dFER_B_ci95']['lo']:+.4f},{e['dFER_B_ci95']['hi']:+.4f}] "
                     f"(fail {e['B_fail_lo']}->{e['B_fail_hi']})")
    if 'ratio_D12_over_D8' in res:
        for name, e in res['ratio_D12_over_D8'].items():
            c = e['ci95']
            lines.append(f"D12/D8 [{name}] point {e['point']} CI {None if c['lo'] is None else (round(c['lo'], 3), round(c['hi'], 3))} valid {c['n_valid']}/{res['bootstrap']['resamples']}")
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rows', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--caps', default='8,12')
    a = p.parse_args()
    rows = load_rows(a.rows)
    caps = [int(x) for x in a.caps.split(',')]
    snrs, frames = sorted({r['snr_centi_db'] for r in rows}), sorted({r['frame'] for r in rows})
    W = boot_weights(len(frames))
    res = summarize(counts(rows, caps, snrs, frames), caps, snrs, frames, rows, W)
    if 8 in caps and 12 in caps:
        res['q1_paired_12_minus_8'] = paired_q1(rows, snrs, frames, W)
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(table(res))


if __name__ == '__main__':
    main()
