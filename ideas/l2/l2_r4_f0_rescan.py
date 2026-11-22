#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 8 (child card I-20261122-l41 of l37; criteria in PREDICTIONS_r4_batch8.md; runner l, claude-fable-5.2).
Blind receiver (stage A 'base' arm = F0 + CODELAY on failure) with a round-1 Doppler coarse rescan: the second refit call of F0 is replaced by
headroom arms.refine_fixed_delays on the delays time_refine itself would keep, with an empty acquired list (rescan=True) or passed through (gate).
  python l2_r4_f0_rescan.py gate|run|read --out out_r4b8
"""
import argparse, glob, gzip, json, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / 'experiments'
sys.path.insert(0, str(EXP / 'data_pilot_fer_20261121')); sys.path.insert(0, str(EXP / 'headroom_ladder_20261008'))
FRAMES, SCEN, RHOS, SNRS = range(41000, 41200), ('U', 'G'), (250, 300), (400, 450, 500, 550, 600)
WORKERS, BOOT, SEED = 48, 2000, 20261127


def arm(C, obs, truth, rescan):
    import arms
    native = C['ctx'].native; orig = native.time_refine; st = dict(n=0)

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw):
        st['n'] += 1
        if st['n'] != 2:
            return orig(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw)
        ls_, gs_ = np.asarray(ls, int), np.asarray(gs, complex); u = np.unique(ls_)
        e = np.array([np.sum(abs(gs_[ls_ == d]) ** 2) for d in u]); l = u[np.argsort(-e)[:kw.get('max_paths', 8)]]
        acq = (np.zeros(0, int), np.zeros(0), np.zeros(0, complex)) if rescan else (ls, ks, gs)
        return arms.refine_fixed_delays(y, pilot, mu, v, *acq, c1, c2, noise, delays=l, mode=kw.get('mode', 'soft'), rounds=kw.get('rounds', 2))
    native.time_refine = refine
    try:
        import stageA
        return stageA.one_arm(C, obs, truth, None)
    finally:
        native.time_refine = orig


def shard_job(job):
    import stageA
    idx, frames, out = job; C = stageA.setup(); n = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for f in frames:
            for s in SCEN:
                for rho in RHOS:
                    base = C['stage3'].inputs(C['ctx'], f, s, rho)
                    for snr in SNRS:
                        raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr); r = arm(C, obs, truth, True)
                        print(json.dumps(dict(scenario=s, rho=rho, snr=snr, frame=f, errors=r['errors'], f0_errors=r['f0_errors'], syndrome=r['syndrome'])), file=fh, flush=True); n += 1
    return idx, n


def archived(keys):
    out = {}
    for p in sorted(glob.glob(str(EXP / 'data_pilot_fer_20261121' / 'out' / 'stageA' / 'rows_shard*.jsonl.gz'))):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line); k = (r['scenario'], r['rho'], r['snr'], r['frame'])
                if k in keys:
                    out[k] = r['arms']['base']
    return out


def gate(out):
    import stageA
    C = stageA.setup(); keys = [(s, rho, snr, 41000) for s in SCEN for rho in RHOS for snr in (450, 550)]; old = archived(set(keys)); recs = []
    for s, rho, snr, f in keys:
        base = C['stage3'].inputs(C['ctx'], f, s, rho); raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
        r = arm(C, obs, truth, False); a = old[(s, rho, snr, f)]; r2 = arm(C, obs, truth, True)
        recs.append(dict(key=[s, rho, snr, f], match=all(r[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors')), base=a['errors'], rescan=r2['errors'])); print(recs[-1], flush=True)
    ok = all(r['match'] for r in recs); json.dump(dict(pass_=ok, records=recs), open(out / 'gate.json', 'w'), indent=1); print('GATE', 'PASS' if ok else 'FAIL')


def run(out):
    fr = list(FRAMES); jobs = [(i, fr[i::WORKERS], str(out)) for i in range(WORKERS)]; t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[41000, 41199], scenarios=SCEN, rhos=RHOS, snrs=SNRS, arm='base with round-1 coarse rescan'), keys=done,
                   core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, round((ch.ru_utime + ch.ru_stime) / 3600, 2), 'core-hours')


def read(out):
    N = {}
    for p in sorted(out.glob('rows_shard*.jsonl')):
        for line in open(p):
            r = json.loads(line); N[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    A = archived(set(N)); fr = sorted({k[3] for k in N}); rng = np.random.default_rng(SEED); res = dict(keys=len(N), table={}, pooled={})
    for rho in RHOS:
        for snr in SNRS:
            ks = [k for k in N if k[1] == rho and k[2] == snr]
            res['table'][f'{rho}_{snr}'] = dict(base=float(np.mean([A[k]['errors'] > 0 for k in ks])), rescan=float(np.mean([N[k]['errors'] > 0 for k in ks])),
                                                f0_base=float(np.mean([A[k]['f0_errors'] > 0 for k in ks])), f0_rescan=float(np.mean([N[k]['f0_errors'] > 0 for k in ks])))
        ks = [k for k in N if k[1] == rho and k[2] in (450, 500, 550)]
        a = np.array([A[k]['errors'] > 0 for k in ks], float); b = np.array([N[k]['errors'] > 0 for k in ks], float)
        fi = {f: [i for i, k in enumerate(ks) if k[3] == f] for f in fr}; Bx = rng.integers(0, len(fr), (BOOT, len(fr)))
        per = np.array([[(a - b)[fi[f]].sum(), len(fi[f])] for f in fr]); s = per[Bx]
        res['pooled'][str(rho)] = dict(base=float(a.mean()), rescan=float(b.mean()), diff=float((a - b).mean()), ci95=np.percentile(s[:, :, 0].sum(1) / s[:, :, 1].sum(1), [2.5, 97.5]).tolist(),
                                       rescue=int(((a == 1) & (b == 0)).sum()), harm=int(((a == 0) & (b == 1)).sum()))
    json.dump(res, open(out / 'summary.json', 'w'), indent=1); print(json.dumps(res))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('gate', 'run', 'read')); ap.add_argument('--out', default='out_r4b8'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True); {'gate': gate, 'run': run, 'read': read}[a.cmd](out)
