#!/usr/bin/env python
"""PILOT 3 aggregation (exploratory; plan: POSTHOC_CHECKS.md "Pilot 3 plan"): edit budget 2 -> 4 on the pilot-2 keys, caps 8 and 12.

Units = F0_s-triggered keys (identical for 2 and 4 edits: pilot3_mode asserts the F0_s sha against pilot 2).  R = share with 0 information-bit errors.
D_2 = R(A1) - R(A2) at 2 edits (pilot-2 rows), D_4 = R(A1e4) - R(A2e4); ratio D_4/D_2 computed inside each frame-cluster resample (shared with sm_agg.boot_weights).
Edit classes (replayed on the F0_s r1 geometry in step order): phantom = the new delay is already held by another slot; true_add = not a phantom and the
new delay is a true delay; other = neither.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from collections import Counter
from pathlib import Path

import numpy as np

import sm_agg as sa

FIELDS = ('trig', 'a1_2', 'a2_2', 'a1_4', 'a2_4')
CAP_GROUPS = {'8': ('8',), '12': ('12',), 'both': ('8', '12')}


def load(rows_dir):
    rows = {}
    for path in sorted(glob.glob(str(Path(rows_dir) / 'rows_shard*.jsonl*'))):
        with (gzip.open if path.endswith('.gz') else open)(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                rows[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    return rows


def classify(r1, edits, truth):
    geo, out = list(r1), []
    for e in sorted(edits, key=lambda x: x['step']):
        slot, new = e['slot'], e['new']['delay']
        if geo[slot] != e['old']['delay']:
            raise ValueError('edit replay mismatch')
        geo[slot] = new
        out.append((e['step'], 'phantom' if new in [d for j, d in enumerate(geo) if j != slot] else 'true_add' if new in truth else 'other'))
    return out


def units(p2, p3):
    """One record per (key, cap) with F0_s triggered; joins the 2-edit arms (pilot 2) with the 4-edit arms (pilot 3)."""
    if set(p2) != set(p3):
        raise ValueError('pilot 2 and pilot 3 key sets differ')
    out = []
    for k in sorted(p2):
        a, b = p2[k], p3[k]
        for s in ('8', '12'):
            x, y = a['s'][s], b['s'][s]
            if x['f0']['decoded_sha256'] != y['f0_sha256'] or x['triggered'] != y['triggered']:
                raise ValueError(f'F0 differs at {k} cap {s}')
            if not x['triggered']:
                continue
            arms = {n: (x['arms'][n] if n in ('A1', 'A2') else y['arms'][n]) for n in ('A1', 'A2', 'A1e4', 'A2e4')}
            bad = [n for n, r in arms.items() if r.get('status') != 'ok']
            if bad:
                raise ValueError(f'error records {bad} at {k} cap {s}')
            out.append(dict(key=k, cap=s, frame=k[3], snr=k[2], arms=arms, r1=x['f0']['r1_delays'], truth=set(a['truth']['delays'])))
    return out


def rescued(u, arm):
    return int(u['arms'][arm]['info_errors'] == 0)


def aggregate(us, frames, snrs):
    W = sa.boot_weights(len(frames))
    fi = {f: i for i, f in enumerate(frames)}
    groups = {(cg, sg): [] for cg in CAP_GROUPS for sg in ['all', *snrs]}
    for u in us:
        for cg, caps in CAP_GROUPS.items():
            if u['cap'] in caps:
                groups[(cg, 'all')].append(u)
                groups[(cg, u['snr'])].append(u)
    res = {}
    for (cg, sg), g in groups.items():
        X = np.zeros((len(frames), len(FIELDS)), int)
        for u in g:
            X[fi[u['frame']]] += np.array([1, rescued(u, 'A1'), rescued(u, 'A2'), rescued(u, 'A1e4'), rescued(u, 'A2e4')])
        tot, boot = np.ones(len(frames)) @ X, W @ X

        def stat(S):
            S = np.asarray(S, float)
            with np.errstate(invalid='ignore', divide='ignore'):
                R = {k: S[..., i] / S[..., 0] for i, k in enumerate(FIELDS) if i}
                D2, D4 = R['a1_2'] - R['a2_2'], R['a1_4'] - R['a2_4']
                return R, D2, D4, np.where(D2 != 0, D4 / D2, np.nan)
        R, D2, D4, ratio = stat(tot)
        _, bD2, bD4, bratio = stat(boot)
        e = dict(triggered=int(tot[0]), R_A1_2=sa.pt(R['a1_2']), R_A2_2=sa.pt(R['a2_2']), R_A1_4=sa.pt(R['a1_4']), R_A2_4=sa.pt(R['a2_4']),
                 D_2=sa.pt(D2), D_2_ci95=sa.ci(bD2), D_4=sa.pt(D4), D_4_ci95=sa.ci(bD4), ratio_D4_over_D2=sa.pt(ratio), ratio_ci95=sa.ci(bratio),
                 resamples_with_D2_undefined_or_zero=int(np.isnan(bratio).sum()))
        for arm, (a2, a4) in (('A1', ('A1', 'A1e4')), ('A2', ('A2', 'A2e4'))):
            t = Counter(f'{rescued(u, a2)}{rescued(u, a4)}' for u in g)
            e[f'transitions_{arm}_rescued_at2_at4'] = {k: t[k] for k in ('11', '10', '01', '00')}
        n = max(len(g), 1)
        for name in ('A1', 'A2', 'A1e4', 'A2e4'):
            cls = [[c for _, c in classify(u['r1'], u['arms'][name]['edits'], u['truth'])] for u in g]
            e[f'edits_{name}'] = dict(mean_accepted=sum(len(c) for c in cls) / n, mean_phantom=sum(c.count('phantom') for c in cls) / n,
                                      units_with_ge3_edits=sum(len(c) >= 3 for c in cls))
            if name.endswith('e4'):
                late = [c for u in g for st, c in classify(u['r1'], u['arms'][name]['edits'], u['truth']) if st >= 2]
                e[f'edits_{name}']['edits_3_4'] = dict(n=len(late), **{k: late.count(k) for k in ('phantom', 'true_add', 'other')},
                                                       **{f'share_{k}': (late.count(k) / len(late) if late else None) for k in ('phantom', 'true_add', 'other')})
        same = sum([(ed['slot'], ed['new']['delay'], ed['new']['doppler']) for ed in sorted(u['arms'][a4]['edits'], key=lambda z: z['step'])[:2]]
                   == [(ed['slot'], ed['new']['delay'], ed['new']['doppler']) for ed in sorted(u['arms'][a2]['edits'], key=lambda z: z['step'])[:2]]
                   for u in g for a2, a4 in (('A1', 'A1e4'), ('A2', 'A2e4')))
        e['first_two_edits_equal_2edit_run'] = dict(arm_units=2 * len(g), equal=int(same))
        res[f'cap={cg}|snr={sg}'] = e
    return res


def table(res):
    f = lambda x: '  n/a' if x is None else f'{x:5.3f}'  # noqa: E731
    lines = [f"{'group':>16} {'trig':>5} {'R1@2':>6} {'R2@2':>6} {'R1@4':>6} {'R2@4':>6} {'D2':>6} {'D4':>6} {'D4 CI':>16} {'D4/D2':>6} {'ratio CI':>15}  A1 2->4 (11/10/01/00)  A2 2->4"]
    for name, e in res.items():
        c, rc = e['D_4_ci95'], e['ratio_ci95']
        lines.append(f"{name:>16} {e['triggered']:5d} {f(e['R_A1_2'])} {f(e['R_A2_2'])} {f(e['R_A1_4'])} {f(e['R_A2_4'])} {f(e['D_2'])} {f(e['D_4'])} "
                     f"{('[%+.3f,%+.3f]' % (c['lo'], c['hi'])) if c['lo'] is not None else 'n/a':>16} {f(e['ratio_D4_over_D2'])} "
                     f"{('[%.2f,%.2f]' % (rc['lo'], rc['hi'])) if rc['lo'] is not None else 'n/a':>15}  "
                     f"{'/'.join(str(v) for v in e['transitions_A1_rescued_at2_at4'].values())}  {'/'.join(str(v) for v in e['transitions_A2_rescued_at2_at4'].values())}")
    lines.append('--- mean accepted / mean phantom edits per unit; edits 3-4 classes (n; phantom/true_add/other)')
    for name, e in res.items():
        if name.endswith('snr=all'):
            lines.append(name + ': ' + '; '.join(
                f"{a}: {e['edits_' + a]['mean_accepted']:.2f}/{e['edits_' + a]['mean_phantom']:.2f}"
                + (f" late n={e['edits_' + a]['edits_3_4']['n']} {e['edits_' + a]['edits_3_4']['phantom']}/{e['edits_' + a]['edits_3_4']['true_add']}/{e['edits_' + a]['edits_3_4']['other']}"
                   if a.endswith('e4') else '') for a in ('A1', 'A2', 'A1e4', 'A2e4')))
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot2', type=Path, required=True)
    p.add_argument('--pilot3', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    p2, p3 = load(a.pilot2), load(a.pilot3)
    us = units(p2, p3)
    frames, snrs = sorted({k[3] for k in p2}), sorted({k[2] for k in p2})
    res = dict(_label='PILOT 3, exploratory: edit budget 2 -> 4, pilot-2 keys (frames %d..%d, rho .3, SNR %s dB, caps 8 and 12); agreed bands in POSTHOC_CHECKS.md, not frozen'
               % (frames[0], frames[-1], '/'.join(f'{v / 100:.1f}' for v in snrs)), bootstrap=dict(seed=sa.SEED, resamples=sa.N_BOOT, clusters='frames'),
               n_keys=len(p2), n_frames=len(frames), n_units=len(us), groups=aggregate(us, frames, snrs))
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(res['_label'] + f"\nkeys {len(p2)}, frames {len(frames)}, triggered units {len(us)}\n" + table(res['groups']))


if __name__ == '__main__':
    main()
