#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 3 (card I-20261122-l34; criteria in PREDICTIONS_r4_batch3.md; runner l, claude-fable-5.2).

After the detector is matched (joint gain in both rounds, see l2_r4_sbl_joint.py), how far is CODELAY still ahead of the SBL ports near
its own 1% crossing?  SBL joint arms are run on fresh frames 4060..4119; CODELAY and F0 come from the archived stage-3 rows on the same keys.

  python l2_r4_sbl_joint_b3.py run  --out out_r4b3
  python l2_r4_sbl_joint_b3.py read --out out_r4b3
"""
import argparse, glob, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r4_sbl_joint as b2          # joint_detector, slim, e3 (unchanged)

VARIANTS = b2.VARIANTS
FRAMES = range(4060, 4120)
GRID = {'U_300': [5.0, 5.5, 6.0], 'G_300': [5.0, 5.5, 6.0], 'U_500': [6.0, 6.5, 7.0], 'G_500': [6.0, 6.5, 7.0]}
MAIN_ARM = 'L-cov'
STAGE3 = HERE.parents[1] / 'experiments' / 'cstate_codelay_sbl_stage3_20261118' / 'out'
WORKERS, BOOT, SEED = 48, 2000, 20261123


def shard_job(job):
    idx, frames, out = job
    e3d = b2.e3(); ctx = e3d.p1ctx.load()
    cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap)); n = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for frame in frames:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, GRID, None):
                calls = []
                with mock.patch.object(e3d, 'detect_decode', b2.joint_detector(calls)):
                    row = e3d.process_key(ctx, cache, grid, obs, data_af, truth, meta, VARIANTS)
                if len(calls) != 1 + len(VARIANTS):
                    raise AssertionError('detector call count')
                print(json.dumps(b2.slim(row, calls)), file=fh, flush=True); n += 1
    return idx, n


def run(out):
    frames = list(FRAMES); jobs = [(i, frames[i::WORKERS], str(out)) for i in range(min(WORKERS, len(frames)))]
    t0 = time.time()
    with get_context('spawn').Pool(len(jobs)) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[FRAMES.start, FRAMES.stop - 1], grid=GRID, variants=VARIANTS, workers=WORKERS, main_arm=MAIN_ARM,
                                                 detector='scalar_joint gain_mode=joint, iterations 20, damping .3, both rounds'),
                   keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, 'keys', round((ch.ru_utime + ch.ru_stime) / 3600, 3), 'core-hours', round(time.time() - t0), 's wall')


def read(out):
    J = {}
    for p in sorted(out.glob('rows_shard*.jsonl')):
        for line in open(p):
            r = json.loads(line); J[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    C = {}
    for p in sorted(glob.glob(str(STAGE3 / 'main-*.jsonl'))):
        for line in open(p):
            r = json.loads(line); k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
            if k in J:
                C[k] = dict(CODELAY=int(r['arms']['CODELAY']['errors'] > 0), F0=int(r['arms']['F0']['errors'] > 0))
    if set(C) != set(J):
        raise ValueError(f'archived CODELAY rows missing for {len(set(J) - set(C))} keys')
    frames = sorted({k[3] for k in J}); rng = np.random.default_rng(SEED)

    def jfer(k, v):
        r = J[k]; e = r['detector_errors']
        return 1 if (e[0] is not None or e[1 + VARIANTS.index(v)] is not None) else r['variants'][v]['fer']

    res = dict(keys=len(J), frames=len(frames), detector_errors=int(sum(any(x is not None for x in r['detector_errors']) for r in J.values())), table={}, pooled={}, lowest_snr_fer_le_2_of_120={})
    for rho in (300, 500):
        snrs = sorted({k[2] for k in J if k[1] == rho}); low = {}
        for snr in snrs:
            ks = [k for k in J if k[1] == rho and k[2] == snr]
            row = dict(n=len(ks), CODELAY=float(np.mean([C[k]['CODELAY'] for k in ks])), F0=float(np.mean([C[k]['F0'] for k in ks])),
                       round1_zero_syndrome_joint=float(np.mean([J[k]['round1']['syndrome'] == 0 for k in ks])),
                       **{f'{v}/joint': float(np.mean([jfer(k, v) for k in ks])) for v in VARIANTS})
            res['table'][f'{rho}_{snr}'] = row
            for a in ('CODELAY', 'F0') + tuple(f'{v}/joint' for v in VARIANTS):
                if a not in low and row[a] * len(ks) <= 2 * len(ks) / 120 + 1e-9:
                    low[a] = snr / 100
        res['lowest_snr_fer_le_2_of_120'][str(rho)] = low
        ks = [k for k in J if k[1] == rho]
        fi = {f: [i for i, k in enumerate(ks) if k[3] == f] for f in frames}; B = rng.integers(0, len(frames), (BOOT, len(frames)))
        cd = np.array([C[k]['CODELAY'] for k in ks], float)

        def boot(d):
            per = np.array([[d[fi[f]].sum(), len(fi[f])] for f in frames]); s = per[B]
            return np.percentile(s[:, :, 0].sum(1) / s[:, :, 1].sum(1), [2.5, 97.5]).tolist()
        pooled = dict(CODELAY=float(cd.mean()))
        for v in VARIANTS:
            x = np.array([jfer(k, v) for k in ks], float)
            pooled[f'{v}/joint'] = dict(fer=float(x.mean()), diff_vs_CODELAY=float((x - cd).mean()), ci95=boot(x - cd),
                                        sbl_only_fail=int(((x == 1) & (cd == 0)).sum()), codelay_only_fail=int(((x == 0) & (cd == 1)).sum()))
        res['pooled'][str(rho)] = pooled
    json.dump(res, open(out / 'summary.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('run', 'read')); ap.add_argument('--out', default='out_r4b3'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True)
    {'run': run, 'read': read}[a.cmd](out)
