#!/usr/bin/env python
"""Idea-funnel local round 4, L2 batch 4 (card I-20261122-l36; criteria in PREDICTIONS_r4_batch4.md; runner l, claude-fable-5.2).

Stage A2's 'full' arm injects the true round-0 channel, but the round-0 detector (scalar_joint, gain_mode='joint') rewrites the gains.
Two new arms, the stage A / A2 pipeline imported unchanged (experiments/data_pilot_fer_20261121):
  full_fix0  round 0 = true (l, nu, g) and the round-0 detector runs with gain_mode='fixed'; round 1 and the CODELAY exchange unchanged
  pls_fix0   round 0 = true (l, nu), gains = unbiased pilot LS (time_refine at the true values, data-variance term set to zero), fixed-gain round-0 detector
Archived arms full / ldop (joint detector) are read from out/stageA2 on the same keys.

  python l2_r4_a2_fixed.py gate --out out_r4b4 ; python l2_r4_a2_fixed.py run --out out_r4b4 ; python l2_r4_a2_fixed.py read --out out_r4b4
"""
import argparse, glob, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121'
sys.path.insert(0, str(EXP))
FRAMES = range(41000, 41150)
SCEN, RHOS = ('U', 'G'), (50, 100, 150)
SNRS = (100, 150, 200, 250, 300, 400, 450, 500, 600)
ARMS = ('full_fix0', 'pls_fix0')
WORKERS, BOOT, SEED = 48, 2000, 20261124


def f0_fixed0(C, obs, truth, gains):
    """F0 whose round-0 channel is true (gains 'true') or true (l, nu) + unbiased pilot LS gains ('pls'), with a fixed-gain round-0 detector."""
    native = C['ctx'].native
    o_ref, o_sj = native.time_refine, native.scalar_joint
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    st = dict(ref=0, sj=0)

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw):
        st['ref'] += 1
        if st['ref'] > 1:
            return o_ref(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw)
        if gains == 'true':
            ch, det = o_ref(y, pilot, mu, v, l, nu, g, c1, c2, noise, **dict(kw, rounds=0))
            ch = type(ch)(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers, [g[list(l).index(d)] for d in ch.delays])
        else:
            ch, det = o_ref(y, pilot, np.zeros_like(mu), np.zeros_like(v), l, nu, g, c1, c2, noise, **dict(kw, rounds=0))
        return ch, det

    def sj(*a, **kw):
        st['sj'] += 1
        return o_sj(*a, **(dict(kw, gain_mode='fixed') if st['sj'] == 1 else kw))
    native.time_refine, native.scalar_joint = refine, sj
    try:
        return C['stage3'].e1.f0_state(C['ctx'], obs)
    finally:
        native.time_refine, native.scalar_joint = o_ref, o_sj


def one_arm(C, obs, truth, gains):
    ctx, stage3 = C['ctx'], C['stage3']
    dec, arrays, syndrome, _ = f0_fixed0(C, obs, truth, gains)
    rec = dict(syndrome=int(syndrome), r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)))
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
    else:
        rec['errors'] = rec['f0_errors']
    return rec, arrays


def shard_job(job):
    import stageA
    idx, frames, out = job
    C = stageA.setup(); n = 0
    with open(Path(out) / f'rows_shard{idx:03d}.jsonl', 'w') as fh:
        for frame in frames:
            for s_ in SCEN:
                for rho in RHOS:
                    base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
                    for snr in SNRS:
                        raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
                        print(json.dumps(dict(scenario=s_, rho=rho, snr=snr, frame=frame,
                                              arms={'full_fix0': one_arm(C, obs, truth, 'true')[0], 'pls_fix0': one_arm(C, obs, truth, 'pls')[0]})), file=fh, flush=True); n += 1
    return idx, n


def archived(frames):
    rows = {}
    for p in sorted(glob.glob(str(EXP / 'out' / 'stageA2' / 'rows_shard*.jsonl.gz'))):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                if r['frame'] in frames:
                    rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    return rows


def gate(out):
    import stageA, stageA2
    C = stageA.setup()
    keys = [(s, rho, snr, f) for s in SCEN for rho in (100, 150) for snr in (300, 450) for f in (41000,)]
    old = archived({41000}); recs = []
    for s_, rho, snr, frame in keys:
        base = C['stage3'].inputs(C['ctx'], frame, s_, rho); raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
        ref = stageA2.one_arm(C, obs, truth, 'true'); a = old[(s_, rho, snr, frame)]['arms']['full']
        g1 = all(ref[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
        rec, arr = one_arm(C, obs, truth, 'true')
        l = np.asarray(truth['l_i'], int); order = [list(l).index(d) for d in arr['r0_delays']]
        g2 = bool(np.allclose(arr['r0_gains'], np.asarray(truth['g_i'])[order]) and np.allclose(arr['r0_dopplers'], np.asarray(truth['k_real'])[order]))
        rec2, arr2 = one_arm(C, obs, truth, 'pls')
        cos = float(abs(np.vdot(np.asarray(truth['g_i'])[[list(l).index(d) for d in arr2['r0_delays']]], arr2['r0_gains'])) /
                    (np.linalg.norm(truth['g_i']) * np.linalg.norm(arr2['r0_gains'])))
        ratio = float(np.linalg.norm(arr2['r0_gains']) / np.linalg.norm(truth['g_i']))
        recs.append(dict(key=[s_, rho, snr, frame], g1_reproduce=bool(g1), g2_true_gains_kept=g2, pls_cosine=cos, pls_norm_ratio=ratio,
                         errors=dict(archived_full=a['errors'], full_fix0=rec['errors'], pls_fix0=rec2['errors'])))
        print(recs[-1], flush=True)
    ok = all(r['g1_reproduce'] and r['g2_true_gains_kept'] for r in recs)
    json.dump(dict(pass_=ok, records=recs), open(out / 'gate.json', 'w'), indent=1)
    print('GATE', 'PASS' if ok else 'FAIL')


def run(out):
    frames = list(FRAMES); jobs = [(i, frames[i::WORKERS], str(out)) for i in range(WORKERS)]
    t0 = time.time()
    with get_context('spawn').Pool(WORKERS) as pool:
        done = sum(n for _, n in pool.imap_unordered(shard_job, jobs))
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    json.dump(dict(_argv=sys.argv, _config=dict(frames=[FRAMES.start, FRAMES.stop - 1], scenarios=SCEN, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS),
                   keys=done, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), open(out / 'run.json', 'w'), indent=1)
    print('DONE', done, 'keys', round((ch.ru_utime + ch.ru_stime) / 3600, 3), 'core-hours', round(time.time() - t0), 's wall')


def crossing(x, fer, t=.01):
    """1% crossing by log10 interpolation; clipped to x[0] - .5 (already below) or x[-1] + .5 (never reached)."""
    lf = np.log10(np.maximum(fer, 1e-4))
    if fer[0] <= t:
        return x[0] - .5
    for i in range(1, len(x)):
        if fer[i] <= t:
            a = (lf[i - 1] + 2) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.
            return x[i - 1] + a * (x[i] - x[i - 1])
    return x[-1] + .5


def read(out):
    N = {}
    for p in sorted(out.glob('rows_shard*.jsonl')):
        for line in open(p):
            r = json.loads(line); N[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    frames = sorted({k[3] for k in N}); A = archived(set(frames)); fi = {f: i for i, f in enumerate(frames)}
    asnr = sorted({k[2] for k in A}); nsnr = sorted({k[2] for k in N})
    fail = {a: np.zeros((len(frames), 2, len(RHOS), len(nsnr))) for a in ARMS}
    fail.update({a: np.zeros((len(frames), 2, len(RHOS), len(asnr))) for a in ('full', 'ldop')})
    for (s, rho, snr, f), r in N.items():
        for a in ARMS:
            fail[a][fi[f], SCEN.index(s), RHOS.index(rho), nsnr.index(snr)] = r['arms'][a]['errors'] > 0
    for (s, rho, snr, f), r in A.items():
        if rho in RHOS:
            for a in ('full', 'ldop'):
                fail[a][fi[f], SCEN.index(s), RHOS.index(rho), asnr.index(snr)] = r['arms'][a]['errors'] > 0
    grid = {a: np.array(nsnr) / 100. for a in ARMS}; grid.update({a: np.array(asnr) / 100. for a in ('full', 'ldop')})

    def stats(idx):
        cr = {a: np.array([[crossing(grid[a], fail[a][idx, s, r].mean(0)) for r in range(len(RHOS))] for s in range(2)]).mean(0) for a in fail}
        return dict(cross={a: cr[a].tolist() for a in cr}, d1=float(cr['full'].min() - cr['full_fix0'].min()),
                    d2=float(cr['pls_fix0'][RHOS.index(100)] - cr['full_fix0'][RHOS.index(100)]),
                    d2_15=float(cr['pls_fix0'][RHOS.index(150)] - cr['full_fix0'][RHOS.index(150)]))
    pt = stats(np.arange(len(frames))); rng = np.random.default_rng(SEED)
    B = [stats(rng.integers(0, len(frames), len(frames))) for _ in range(BOOT)]
    res = dict(keys=len(N), frames=len(frames), rhos=RHOS, new_snr_grid=grid['full_fix0'].tolist(), archived_snr_grid=grid['full'].tolist(),
               crossings_by_rho=pt['cross'], d1=pt['d1'], d1_ci95=np.percentile([b['d1'] for b in B], [2.5, 97.5]).tolist(),
               d2_rho10=pt['d2'], d2_ci95=np.percentile([b['d2'] for b in B], [2.5, 97.5]).tolist(),
               d2_rho15=pt['d2_15'], d2_rho15_ci95=np.percentile([b['d2_15'] for b in B], [2.5, 97.5]).tolist(),
               fer={a: {str(rho): {str(int(s * 100)): float(fail[a][:, :, r, i].mean()) for i, s in enumerate(grid[a])} for r, rho in enumerate(RHOS)} for a in fail})
    json.dump(res, open(out / 'summary.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'fer'}, indent=1))
    for a in fail:
        for r, rho in enumerate(RHOS):
            print(a, rho, {int(s * 100): round(float(fail[a][:, :, r, i].mean()), 4) for i, s in enumerate(grid[a]) if s <= 6.5})


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=('gate', 'run', 'read')); ap.add_argument('--out', default='out_r4b4'); a = ap.parse_args()
    out = HERE / a.out; out.mkdir(exist_ok=True)
    {'gate': gate, 'run': run, 'read': read}[a.cmd](out)
