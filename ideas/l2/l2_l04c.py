#!/usr/bin/env python3
"""Idea-funnel L2 follow-up for card I-20261121-l04 (2026-11-21, runner l): at which stage does the codeword matter?
For the 13 failed frames of out2/l04 and the same 8 fresh-noise re-sends of the ORIGINAL codeword, rerun with
(a) the true delays given to round 0 (stageA 'delay' arm) and (b) the fully true round-0 channel (stageA2 'full' arm).
If the same-codeword failures disappear in (a)/(b), the codeword acts through pilot acquisition; if they stay,
it acts in detection/decoding.  Imports l2_batch2 / stageA / stageA2; no new receiver code.
  python l2_l04c.py --out out2/l04c.json
"""
import argparse, json, sys
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch2 as b2  # noqa: E402
from l2_batch2 import setup, SCENARIOS, SEED, CFG, stageA, score_f0, reobserve, failed_frames, f0_true  # noqa: E402


def job(key):
    s_, frame = key
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l04']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, cfg['rho']), cfg['rho'], cfg['snr'])
    sc = float(np.linalg.norm(raw['pilot']) / np.linalg.norm(obs['pilot'])); n = len(obs['y']); d0 = np.asarray(raw['data'], complex) / sc
    reps = []
    for j in range(cfg['repeats']):
        rng = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 40, j])
        noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        o = reobserve(obs, raw, d0, noise)
        dec, arr, syn, _ = stageA.f0(C, o); base = score_f0(C, o, truth, dec, arr, syn, True)
        dec, arr, syn, _ = stageA.f0(C, o, stageA.genie_inject(C, o, truth)); dly = score_f0(C, o, truth, dec, arr, syn, True)
        dec, arr, syn, _ = f0_true(C, o, truth, 'true'); full = score_f0(C, o, truth, dec, arr, syn, True)
        reps.append(dict(j=j, base=base['errors'], delay=dly['errors'], full=full['errors'],
                         base_missing=base['r0']['missing_power'], base_r1_missing=base['r1']['missing_power'],
                         base_r0_dop=base['r0']['doppler_err']))
    return dict(scenario=s_, frame=frame, reps=reps)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    with get_context('spawn').Pool(8) as pool:
        rows = pool.map(job, failed_frames())
    tot = dict(base=0, delay=0, full=0, pairs=0)
    for r in rows:
        r['fail'] = {k: int(sum(x[k] > 0 for x in r['reps'])) for k in ('base', 'delay', 'full')}
        for k in ('base', 'delay', 'full'):
            tot[k] += r['fail'][k]
        tot['pairs'] += len(r['reps'])
    miss_f = [x['base_r1_missing'] for r in rows for x in r['reps'] if x['base'] > 0]; miss_o = [x['base_r1_missing'] for r in rows for x in r['reps'] if x['base'] == 0]
    o = dict(_argv=sys.argv, totals=tot, r1_missing_power_median=dict(base_fail=float(np.median(miss_f)) if miss_f else None, base_ok=float(np.median(miss_o)) if miss_o else None), frames=rows)
    Path(a.out).write_text(json.dumps(o, indent=1))
    print(json.dumps(dict(totals=tot, r1_missing=o['r1_missing_power_median'], per_frame=[(r['scenario'], r['frame'], r['fail']) for r in rows]), indent=1))


if __name__ == '__main__':
    main()
