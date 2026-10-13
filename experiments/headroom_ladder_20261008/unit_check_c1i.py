#!/usr/bin/env python
"""Validation of driver_c1i.py from a smoke run (reads rows only; pure numpy/json, no frozen import).  Run on deinlab or locally:
    python -B unit_check_c1i.py <c1i_smoke_dir> <c1_map_dir> <out.json>
 D  determinism: FULL_R4 rounds 1-2 == stored c1_map SPg_flat row (same L, frame, rho .3, 6.5 dB): eps_ce1/det1/ce2/det2, round-1
    (r1_cerr, r1_syn, r1_ll_in) and round-2 (info_errors, coded_errors, syndrome, logloss) decision counts; and == the REF arm
    (driver_c1.run_sp re-run): dsha2 (decision hash), all eps.  Exact max abs diffs are reported.
 W0 WARM_0.0 == FULL_R4 on every numeric field except timings and every decision hash (all rounds)
 W1 WARM_1.0: eps_init == eps_proj; WARM_l: eps_init(l) = eps_proj + (1 - l)^2 (eps_pilot1 - eps_proj) (LS projection => Pythagoras)
 F  FROZEN: eps_ce2 == eps_det1 == eps_det2 == eps_ce1 and frozen_gain_drift == 0; eps_ce1 == FULL_R4 eps_ce1 (same pilot-only refit)
 T  mean seconds per arm per L (the full-grid CPU estimate is done by the caller)
"""
import glob
import json
from pathlib import Path
import sys

import numpy as np

smoke, cmap, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
rows = [json.loads(x) for f in sorted(glob.glob(str(smoke / 'rows_shard*.jsonl'))) for x in open(f) if x.strip()]
bad = [r for r in rows if r['status'] != 'ok']
cell = {}
for r in rows:
    cell.setdefault((r['L'], r['frame'], r['snr_centi_db']), {})[r['arm']] = r
res, fails = {}, []


def check(name, ok, **info):
    res[name] = dict(ok=bool(ok), **info)
    if not ok:
        fails.append(name)
    print(('PASS ' if ok else 'FAIL ') + name, json.dumps(info), flush=True)


def stored(L, frame, snr):
    f = cmap / f'rows_shard{frame % 56:03d}.jsonl'  # c1_map: 56 shards, frames[shard::56]
    for x in open(f):
        r = json.loads(x)
        if r['arm'] == 'SPg_flat' and r['L'] == L and r['frame'] == frame and r['snr_centi_db'] == snr:
            return r
    raise KeyError((L, frame, snr))


check('error_rows', not bad, n=len(bad), first=bad[0].get('error') if bad else None)
EPS = ('eps_ce1', 'eps_det1', 'eps_ce2', 'eps_det2')
for (L, frame, snr), arms in sorted(cell.items()):
    tag = f'L{L}_f{frame}'
    full, ref, st = arms['FULL_R4'], arms.get('REF'), stored(L, frame, snr)  # REF / WARM_0.0 are smoke-only arms (optional)
    d_eps = {k: abs(full[k] - st[k]) for k in EPS}
    d_cnt = dict(r1_cerr=full['cerr1'] - st['r1_cerr'], r1_syn=full['syn1'] - st['r1_syn'],
                 info_errors=full['ierr2'] - st['info_errors'], coded_errors=full['cerr2'] - st['coded_errors'],
                 syndrome=full['syn2'] - st['syndrome'], r1_ll_in=abs(full['ll_in1'] - st['r1_ll_in']),
                 logloss2=abs(full['ll_in2'] - st['logloss_bits']))
    check(f'D_stored_{tag}', max(d_eps.values()) < 1e-10 and all(abs(v) < 1e-10 for v in d_cnt.values()),
          eps_diff=d_eps, count_diff=d_cnt, stored=dict(info_errors=st['info_errors'], coded_errors=st['coded_errors'],
                                                       syndrome=st['syndrome']))
    if ref is not None:
        d_ref = {k: abs(full[k] - ref[k]) for k in EPS}
        check(f'D_ref_{tag}', max(d_ref.values()) < 1e-10 and full['dsha2'] == ref['dsha2'] and full['syn2'] == ref['syndrome']
              and full['ierr2'] == ref['info_errors'], eps_diff=d_ref, dsha2_equal=full['dsha2'] == ref['dsha2'])
        d_st_ref = {k: abs(ref[k] - st[k]) for k in EPS}
        check(f'D_ref_vs_stored_{tag}', max(d_st_ref.values()) < 1e-10 and ref['info_errors'] == st['info_errors'],
              eps_diff=d_st_ref)

    if 'WARM_0.0' in arms:
        w0 = arms['WARM_0.0']
        skip = {'seconds', 'sec_pilot', 'sec_ce', 'sec_inference', 'arm', 'lam'}
        diffs = {k: abs(full[k] - w0[k]) for k in full if k not in skip and isinstance(full[k], (int, float))
                 and not isinstance(full[k], bool) and k in w0}
        sha_eq = all(full[f'dsha{r}'] == w0[f'dsha{r}'] for r in range(1, 5))
        check(f'W0_{tag}', max(diffs.values()) == 0. and sha_eq, max_abs_diff=max(diffs.values()), all_dsha_equal=sha_eq)
    w1 = arms['WARM_1.0']
    pyth = {}
    for lam in (0.25, 0.5, 0.75, 1.0):
        w = arms[f'WARM_{lam}']
        pyth[lam] = abs(w['eps_init'] - (w['eps_proj'] + (1 - lam) ** 2 * (w['eps_pilot1'] - w['eps_proj'])))
    check(f'W1_{tag}', w1['eps_init'] == w1['eps_proj'] and max(pyth.values()) < 1e-10 and full['eps_pilot1'] == full['eps_ce1'],
          eps_init=w1['eps_init'], eps_proj=w1['eps_proj'], diff=abs(w1['eps_init'] - w1['eps_proj']), pythagoras_max_diff=max(pyth.values()),
          eps_pilot1=full['eps_pilot1'], eps_init_by_lambda={str(l): arms[f'WARM_{l}']['eps_init'] for l in (0.25, 0.5, 0.75, 1.0)})
    fz = arms['FROZEN']
    check(f'F_{tag}', fz['eps_ce2'] == fz['eps_ce1'] == fz['eps_det1'] == fz['eps_det2'] and fz['frozen_gain_drift'] == 0.
          and fz['eps_ce1'] == full['eps_ce1'], eps_ce1=fz['eps_ce1'], eps_ce2=fz['eps_ce2'], eps_det1=fz['eps_det1'],
          eps_det2=fz['eps_det2'], frozen_gain_drift=fz['frozen_gain_drift'])
    check(f'rounds_{tag}', all(f'eps_ce{r}' in full and f'eps_ce{r}' in arms['WARM_0.5'] for r in range(1, 5))
          and 'eps_ce3' not in fz, rounds=dict(full=full['rounds'], frozen=fz['rounds']))

# ------------------------------------------------------------------------------------------ outcomes + timing (informational)
timing = {}
for r in rows:
    timing.setdefault((r['L'], r['arm']), []).append(r['seconds'])
res['timing_mean_seconds'] = {f'L{L}_{arm}': float(np.mean(v)) for (L, arm), v in sorted(timing.items())}
res['outcomes'] = {f'L{L}_f{frame}_{arm}': dict(ierr=a['info_errors'], cerr=[a.get(f'cerr{k}') for k in range(1, 5)],
                                                eps_ce=[a.get(f'eps_ce{k}') for k in range(1, 5)])
                   for (L, frame, snr), arms in sorted(cell.items()) for arm, a in arms.items()}
res['fails'] = fails
outp.write_text(json.dumps(res, indent=1) + '\n')
print('FAILS:', fails)
print(json.dumps(res['timing_mean_seconds'], indent=1))
