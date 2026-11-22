#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 2 (card I-20261122-l34; criteria in PREDICTIONS_r4_batch2.md; runner l, claude-fable-5.2).

Does the fixed-gain detector of the archived SBL arms (tf_e3_sbl_20261017/e3_driver.detect_decode, gain_mode='fixed') account for their
gap to CODELAY?  The E-3 pipeline (e3_driver.process_key) is imported unchanged; the only change is detect_decode -> gain_mode='joint'
(iterations 20, damping .3 as before) in BOTH rounds.  The fixed arm is read from the archived E-3 rows on the same keys.
Pattern follows sbl_joint_detector_20261019/sj_driver.py (which teed round 2 only).  Nothing frozen is edited.

  python l2_r4_sbl_joint.py gate --out out_r4b2          (8 archived keys reproduce bit for bit without the patch)
  python l2_r4_sbl_joint.py run  --out out_r4b2          (960 keys, joint detector)
  python l2_r4_sbl_joint.py read --out out_r4b2          (paired readout against the archived fixed rows -> summary.json)
"""
import argparse, glob, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
from unittest import mock

os.environ.setdefault('OMP_NUM_THREADS', '1'); os.environ.setdefault('OPENBLAS_NUM_THREADS', '1'); os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np

HERE = Path(__file__).resolve().parent
E3_DIR = HERE.parents[1] / 'experiments' / 'tf_e3_sbl_20261017'
VARIANTS = ('L-hard', 'L-diag', 'L-cov')
FRAMES = range(4000, 4060)
GRID = {c: [6.0, 7.0, 8.0, 9.0] for c in ('U_300', 'G_300', 'U_500', 'G_500')}
WORKERS, BOOT, SEED = 48, 2000, 20261122


def e3():
    sys.path.insert(0, str(E3_DIR))
    import e3_driver
    return e3_driver


def joint_detector(calls):
    """detect_decode with gain_mode='joint'; a numerical failure is recorded and the fixed-gain output keeps the pipeline going."""
    def detect_decode(ctx, obs, channel, prior):
        t0 = time.perf_counter()
        try:
            det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - ctx.system.rho, prior=prior, iterations=20,
                                          damping=.3, gain_mode='joint')
            calls.append(None)
        except (FloatingPointError, np.linalg.LinAlgError) as exc:
            calls.append(repr(exc))
            det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - ctx.system.rho, prior=prior, iterations=20,
                                          damping=.3, gain_mode='fixed')
        t1 = time.perf_counter()
        dec = ctx.native.decoder_messages(ctx.code, np.clip(det['extrinsic'], -20, 20), maxiter=50)
        return det, dec, t1 - t0, time.perf_counter() - t1
    return detect_decode


def slim(row, calls=None):
    r = dict(scenario=row['scenario'], rho_permille=row['rho_permille'], snr_centi_db=row['snr_centi_db'], frame=row['frame'],
             round1=dict(info_errors=row['round1']['info_errors'], syndrome=row['round1']['syndrome']),
             variants={v: {k: row['variants'][v][k] for k in ('fer', 'info_errors', 'syndrome', 'n_atoms', 'n_pair', 'decoded_sha256')} for v in VARIANTS})
    if calls is not None:
        r['detector_errors'] = calls
    return r


def shard_job(job):
    idx, frames, out = job
    e3d = e3(); ctx = e3d.p1ctx.load()
    cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap)); n = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for frame in frames:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, GRID, None):
                calls = []
                with mock.patch.object(e3d, 'detect_decode', joint_detector(calls)):
                    row = e3d.process_key(ctx, cache, grid, obs, data_af, truth, meta, VARIANTS)
                if len(calls) != 1 + len(VARIANTS):
                    raise AssertionError(f'expected {1 + len(VARIANTS)} detector calls, got {len(calls)}')
                print(json.dumps(slim(row, calls)), file=fh, flush=True); n += 1
    return idx, n


def archived(keys=None):
    rows = {}
    for path in sorted(glob.glob(str(E3_DIR / 'out' / 'main' / 'rows_shard*.jsonl.gz'))):
        with gzip.open(path, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                if r.get('status') == 'error':
                    continue
                k = (r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])
                if keys is None or k in keys:
                    rows[k] = r
    return rows


def gate(out):
    e3d = e3(); ctx = e3d.p1ctx.load(); p1ctx = e3d.p1ctx
    cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap))
    keys = [(s, rho, 700, f) for s in 'UG' for rho in (300, 500) for f in (4000, 4001)]
    old = archived(set(keys)); recs = []
    for k in keys:
        sc, rho_pm, snr, frame = k
        raw_base, diag_base = p1ctx.base(ctx, sc, rho_pm / 1000, frame)
        meta, obs, data_af, truth = e3d.observe_key(ctx, raw_base, diag_base, sc, rho_pm, snr, frame)
        row = e3d.process_key(ctx, cache, grid, obs, data_af, truth, meta, VARIANTS)
        recs.append(dict(key=list(k), match={v: row['variants'][v]['decoded_sha256'] == old[k]['variants'][v]['decoded_sha256'] for v in VARIANTS},
                         round1=row['round1']['decoded_sha256'] == old[k]['round1']['decoded_sha256']))
        print(recs[-1], flush=True)
    ok = len(recs) == 8 and all(all(r['match'].values()) and r['round1'] for r in recs)
    json.dump(dict(pass_=ok, records=recs, frozen_md5_check=e3d.check_frozen_md5(ctx)), open(out / 'gate.json', 'w'), indent=1, default=str)
    print('GATE', 'PASS' if ok else 'FAIL')


def run(out):
    frames = list(FRAMES); jobs = [(i, frames[i::WORKERS], str(out)) for i in range(min(WORKERS, len(frames)))]
    t0 = time.time()
    with get_context('spawn').Pool(len(jobs)) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[FRAMES.start, FRAMES.stop - 1], grid=GRID, variants=VARIANTS, workers=WORKERS,
                                                 detector='scalar_joint gain_mode=joint, iterations 20, damping .3, both rounds'),
                   keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, 'keys', round((ch.ru_utime + ch.ru_stime) / 3600, 3), 'core-hours', round(time.time() - t0), 's wall')


def read(out):
    J = {}
    for p in sorted(out.glob('rows_shard*.jsonl')):
        for line in open(p):
            r = json.loads(line); J[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    F = archived(set(J))
    if set(F) != set(J):
        raise ValueError(f'archived rows missing for {len(set(J) - set(F))} keys')
    frames = sorted({k[3] for k in J}); rng = np.random.default_rng(SEED)

    def jfer(k, v):
        r = J[k]; e = r['detector_errors']
        return 1 if (e[0] is not None or e[1 + VARIANTS.index(v)] is not None) else r['variants'][v]['fer']

    res = dict(keys=len(J), frames=len(frames), detector_errors=dict(round1=sum(r['detector_errors'][0] is not None for r in J.values()),
               **{v: sum(r['detector_errors'][1 + i] is not None for r in J.values()) for i, v in enumerate(VARIANTS)}), table={}, pooled={}, round1_zero_syndrome={})
    for rho in (300, 500):
        for snr in (600, 700, 800, 900):
            ks = [k for k in J if k[1] == rho and k[2] == snr]
            res['table'][f'{rho}_{snr}'] = {v: dict(fixed=float(np.mean([F[k]['variants'][v]['fer'] for k in ks])), joint=float(np.mean([jfer(k, v) for k in ks]))) for v in VARIANTS}
            res['round1_zero_syndrome'][f'{rho}_{snr}'] = dict(fixed=float(np.mean([F[k]['round1']['syndrome'] == 0 for k in ks])),
                                                              joint=float(np.mean([J[k]['round1']['syndrome'] == 0 and J[k]['detector_errors'][0] is None for k in ks])))
        ks = [k for k in J if k[1] == rho and k[2] in (700, 800)]
        fi = {f: [i for i, k in enumerate(ks) if k[3] == f] for f in frames}
        B = rng.integers(0, len(frames), (BOOT, len(frames)))
        cfg = {}
        for v in VARIANTS:
            cfg[f'{v}/fixed'] = np.array([F[k]['variants'][v]['fer'] for k in ks], float); cfg[f'{v}/joint'] = np.array([jfer(k, v) for k in ks], float)

        def boot(d):
            per = np.array([[d[fi[f]].sum(), len(fi[f])] for f in frames])
            s = per[B]; return np.percentile(s[:, :, 0].sum(1) / s[:, :, 1].sum(1), [2.5, 97.5]).tolist()
        pooled = {name: float(x.mean()) for name, x in cfg.items()}
        pooled['paired'] = {v: dict(diff=float((cfg[f'{v}/fixed'] - cfg[f'{v}/joint']).mean()), ci95=boot(cfg[f'{v}/fixed'] - cfg[f'{v}/joint']),
                                    rescue=int(((cfg[f'{v}/fixed'] == 1) & (cfg[f'{v}/joint'] == 0)).sum()), harm=int(((cfg[f'{v}/fixed'] == 0) & (cfg[f'{v}/joint'] == 1)).sum()))
                            for v in VARIANTS}
        best = min((n for n in cfg), key=lambda n: cfg[n].mean()); ref = cfg['L-diag/fixed']
        pooled['best'] = dict(name=best, fer=float(cfg[best].mean()), vs_Ldiag_fixed_diff=float((ref - cfg[best]).mean()), ci95=boot(ref - cfg[best]))
        res['pooled'][str(rho)] = pooled
    json.dump(res, open(out / 'summary.json', 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('gate', 'run', 'read')); ap.add_argument('--out', default='out_r4b2'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True)
    {'gate': gate, 'run': run, 'read': read}[a.cmd](out)
