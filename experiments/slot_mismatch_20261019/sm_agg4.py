#!/usr/bin/env python
"""PILOT 4 aggregation (exploratory; predictions P8-P10 in research-assets/prediction-ledger.md).

Units: pilot-2 cap-8 F0_8-triggered keys whose A2 (diag Gamma, 2 edits) final geometry has >= 1 co-delay pair.  A2 failure = A2-prod has information-bit errors
(= pilot-2 A2).  On the SAME A2 final paths: A2-fix = 10-18 K-diag-fullfix (full-Gamma gains held fixed in the detector), A2-merge = co-delay atoms merged
(|gain|^2-weighted Doppler), production joint continuation.
Failures: rescue rate = share with 0 information-bit errors after the arm.  Successes: broken share = share with >= 1 information-bit error after the arm.
Frame-cluster bootstrap (clusters = the pilot-2 frames, sm_agg.boot_weights), percentile 95% CI.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

import sm_agg as sa
import sm_agg3 as a3

FIELDS = ('nfail', 'fix_r', 'merge_r', 'fix_only', 'merge_only', 'both', 'nsucc', 'fix_b', 'merge_b', 'both_b')


def vec(r):
    a = r['arms']
    fail = a['A2-prod']['info_errors'] > 0
    fix_ok, merge_ok = a['A2-fix']['info_errors'] == 0, a['A2-merge']['info_errors'] == 0
    if fail:
        return [1, fix_ok, merge_ok, fix_ok and not merge_ok, merge_ok and not fix_ok, fix_ok and merge_ok, 0, 0, 0, 0]
    return [0, 0, 0, 0, 0, 0, 1, not fix_ok, not merge_ok, (not fix_ok) and (not merge_ok)]


def stats(S):
    S = np.asarray(S, float)
    f = dict(zip(FIELDS, np.moveaxis(S, -1, 0)))
    with np.errstate(invalid='ignore', divide='ignore'):
        out = dict(R_fix=f['fix_r'] / f['nfail'], R_merge=f['merge_r'] / f['nfail'], broken_fix=f['fix_b'] / f['nsucc'], broken_merge=f['merge_b'] / f['nsucc'])
    out['R_merge_minus_fix'] = out['R_merge'] - out['R_fix']
    return out


def aggregate(rows, frames, snrs):
    W = sa.boot_weights(len(frames))
    fi = {f: i for i, f in enumerate(frames)}
    res = {}
    for sg in ['all', *snrs]:
        g = [r for r in rows if sg == 'all' or r['snr_centi_db'] == sg]
        X = np.zeros((len(frames), len(FIELDS)), int)
        for r in g:
            X[fi[r['frame']]] += np.array(vec(r), int)
        tot, boot = np.ones(len(frames)) @ X, W @ X
        point, b = stats(tot), stats(boot)
        e = dict(units=len(g), A2_fail=int(tot[0]), A2_success=int(tot[6]), frames_with_units=len({r['frame'] for r in g}),
                 fail_paired_rescue=dict(fix_only=int(tot[3]), merge_only=int(tot[4]), both=int(tot[5]), neither=int(tot[0] - tot[3] - tot[4] - tot[5])),
                 success_paired_broken=dict(fix_only=int(tot[7] - tot[9]), merge_only=int(tot[8] - tot[9]), both=int(tot[9]), neither=int(tot[6] - tot[7] - tot[8] + tot[9])))
        for k in ('R_fix', 'R_merge', 'R_merge_minus_fix', 'broken_fix', 'broken_merge'):
            e[k] = sa.pt(point[k])
            e[k + '_ci95'] = sa.ci(b[k])
        res[str(sg)] = e
    return res


def table(res):
    f = lambda x: '  n/a' if x is None else f'{x:5.3f}'  # noqa: E731
    c = lambda d: 'n/a' if d['lo'] is None else '[%.3f,%.3f]' % (d['lo'], d['hi'])  # noqa: E731
    lines = [f"{'snr':>5} {'units':>5} {'fail':>5} {'succ':>5} | {'R(fix)':>6} {'CI':>13} {'R(merge)':>8} {'CI':>13} {'m-f':>6} {'CI':>14} | fail pairs fix-only/merge-only/both/neither | "
             f"{'brk fix':>7} {'CI':>13} {'brk mrg':>7} {'CI':>13} | succ pairs fix-only/merge-only/both/neither"]
    for sg, e in res.items():
        p, q = e['fail_paired_rescue'], e['success_paired_broken']
        lines.append(f"{sg:>5} {e['units']:5d} {e['A2_fail']:5d} {e['A2_success']:5d} | {f(e['R_fix'])}  {c(e['R_fix_ci95']):>13} {f(e['R_merge'])}    {c(e['R_merge_ci95']):>13} "
                     f"{f(e['R_merge_minus_fix'])} {c(e['R_merge_minus_fix_ci95']):>14} | {p['fix_only']}/{p['merge_only']}/{p['both']}/{p['neither']} | "
                     f"{f(e['broken_fix'])}   {c(e['broken_fix_ci95']):>13} {f(e['broken_merge'])}   {c(e['broken_merge_ci95']):>13} | {q['fix_only']}/{q['merge_only']}/{q['both']}/{q['neither']}")
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot2', type=Path, required=True)
    p.add_argument('--pilot4', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    p2, p4 = a3.load(a.pilot2), a3.load(a.pilot4)
    rows = list(p4.values())
    bad = [k for k, r in p4.items() if r['arms']['A2-prod']['info_errors'] != p2[k]['s']['8']['arms']['A2']['info_errors']
           or r['arms']['A2-prod']['decoded_sha256'] != p2[k]['s']['8']['arms']['A2']['decoded_sha256']]
    if bad:
        raise ValueError(f'A2-prod differs from pilot-2 A2 at {bad[:3]}')
    expect = {k for k, r in p2.items() if r['s']['8']['triggered'] and len(set(r['s']['8']['arms']['A2']['final_delays'])) < len(r['s']['8']['arms']['A2']['final_delays'])}
    if set(p4) != expect:
        raise ValueError(f'pilot-4 units {len(p4)} != expected {len(expect)}')
    frames, snrs = sorted({k[3] for k in p2}), sorted({k[2] for k in p2})
    res = dict(_label='PILOT 4, exploratory: detector clue on A2 co-delay-pair units (cap 8; frames %d..%d, rho .3, SNR %s dB)' % (frames[0], frames[-1], '/'.join(f'{v / 100:.1f}' for v in snrs)),
               bootstrap=dict(seed=sa.SEED, resamples=sa.N_BOOT, clusters='frames'), n_units=len(rows), by_snr_centi_db=aggregate(rows, frames, snrs),
               merged_slot_count=dict(Counter(r['arms']['A2-merge']['merged_slot_count'] for r in rows)),
               codelay_groups_per_unit=dict(Counter(r['n_codelay_groups'] for r in rows)))
    a.out.write_text(json.dumps(res, indent=1) + '\n')
    print(res['_label'] + f"\nunits {len(rows)}; merged slot count {res['merged_slot_count']}; co-delay groups per unit {res['codelay_groups_per_unit']}\n" + table(res['by_snr_centi_db']))


if __name__ == '__main__':
    main()
