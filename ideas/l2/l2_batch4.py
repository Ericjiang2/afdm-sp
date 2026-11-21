#!/usr/bin/env python3
"""Idea-funnel L2 checks, batch 4 (2026-11-21, runner l).  Imports l2_batch2 / l2_batch3 / stageA; new arms only.
  c01s  one path's round-0 Doppler perturbed (strongest or weakest relevant path), all else true: does round 1 pull it back?
        (asked by the cross-model gate on card c01)
  l05   re-send after a failure: round-0 capture from the average of the two receptions (same pilot), then decode reception 2
        (child of card l04)
  python l2_batch4.py c01s|l05|read --out out5
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SCENARIOS, SEED, WORKERS, stageA, score_f0, reobserve, scale_of  # noqa: E402
from l2_batch2 import f0_true, failed_frames  # noqa: E402

CFG = dict(c01s=dict(frames=[41000, 41060], rho=100, snr=500, errs=[0.10, 0.20, 0.24, 0.26, 0.30, 0.40]),
           l05=dict(cells=[[100, 1200, 8], [100, 800, 4], [150, 600, 4]], max_frames=30, frame_offset=5000))


def job_c01s(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['c01s']; out = []
    for s_ in SCENARIOS:
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, cfg['rho']), cfg['rho'], cfg['snr'])
        l = [int(x) for x in np.asarray(truth['l_i'])]; nu = np.asarray(truth['k_real'], float)
        g = np.abs(np.asarray(truth['g_i'])) ** 2; rel = np.flatnonzero(g >= stageA.TAU * float(obs['sigma2']))
        picks = dict(strong=int(np.argmax(g)), weak=int(rel[np.argmin(g[rel])]))
        for which, i in picks.items():
            for e in cfg['errs']:
                k = nu.copy(); k[i] += e
                dec, arr, syn, _ = f0_true(C, obs, dict(truth, k_real=k), 'ls')
                d1 = [int(x) for x in arr['r1_delays']]
                res = float(abs(np.asarray(arr['r1_dopplers'], float)[d1.index(l[i])] - nu[i])) if l[i] in d1 else None
                out.append(dict(scenario=s_, frame=frame, which=which, e=e, share=float(g[i] / g.sum()), r1_res=res,
                                r0_fail=int(stage3.e1.gd.score(ctx, arr['r0_decoded'], truth) > 0),
                                f0_fail=int(stage3.e1.gd.score(ctx, dec['decoded'], truth) > 0)))
    return out


def l05_jobs():
    cfg = CFG['l05']; jobs = []
    d = HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121' / 'out' / 'stageA'
    cells = {(c[0], c[1]): [] for c in cfg['cells']}
    for p in sorted(d.glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line); k = (r['rho'], r['snr'])
                if k in cells and r['arms']['base']['errors'] > 0:
                    cells[k].append((r['scenario'], r['frame']))
    for rho, snr, reps in cfg['cells']:
        jobs += [(s_, f, rho, snr, reps) for s_, f in sorted(cells[(rho, snr)])[:cfg['max_frames']]]
    return jobs


def job_l05(job):
    s_, frame, rho, snr, nrep = job
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l05']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, rho), rho, snr)
    sc = scale_of(raw, obs); n = len(obs['y']); d0 = np.asarray(raw['data'], complex) / sc; reps = []

    def run(o, t, y1=None):
        inj = None
        if y1 is not None:      # capture from the average of both receptions: pilot kept, independent data and noise halved
            s = C['orig_front'](dict(o, y=(np.asarray(y1) + np.asarray(o['y'])) / 2, sigma2=float(o['sigma2']) / 2), ctx.system, ctx.code)
            inj = (s['delays'], s['dopplers'], s['gains'])
        dec, arr, syn, _ = stageA.f0(C, o, inj)
        r = score_f0(C, o, t, dec, arr, syn, True)
        return [int(r['errors'] > 0), int(r['r0']['support_right'])]
    for j in range(nrep):
        rng = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 40, j])
        noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        raw2, _, truth2 = stage3.observed(ctx, stage3.inputs(ctx, frame + cfg['frame_offset'] * (j + 1), s_, rho), rho, snr)
        oa = reobserve(obs, raw, d0, noise); ob = reobserve(obs, raw, np.asarray(raw2['data'], complex) / sc, noise)
        tb = dict(truth, info=truth2['info'])
        reps.append(dict(A=run(oa, truth), B=run(ob, tb), AJ=run(oa, truth, obs['y']), BJ=run(ob, tb, obs['y'])))
    return [dict(scenario=s_, frame=frame, rho=rho, snr=snr, reps=reps)]


JOBS = dict(c01s=(job_c01s, lambda: list(range(*CFG['c01s']['frames']))), l05=(job_l05, l05_jobs))


def run(mode, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); path = out / f'{mode}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    fn, jobs = JOBS[mode]; t0 = time.time(); n = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(fn, jobs()):
            for r in rows:
                print(json.dumps(r), file=fh); n += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / f'{mode}_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG[mode], seed=SEED, workers=WORKERS), rows=n,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print(mode, 'rows', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def read(out):
    L = lambda m: [json.loads(l) for l in gzip.open(Path(out) / f'{m}_rows.jsonl.gz', 'rt')]
    res = dict(_argv=sys.argv, _config=CFG)
    if (Path(out) / 'c01s_rows.jsonl.gz').exists():
        rows = L('c01s'); tab = {}
        for which in ('strong', 'weak'):
            for e in CFG['c01s']['errs']:
                s = [r for r in rows if r['which'] == which and r['e'] == e]; rr = [r['r1_res'] for r in s if r['r1_res'] is not None]
                tab[f'{which}_{e:.2f}'] = dict(n=len(s), pulled_back=int(sum(x <= 0.05 for x in rr)), stuck=int(sum(x >= 0.8 * e for x in rr)),
                    dropped=len(s) - len(rr), r1_res_median=float(np.median(rr)) if rr else None, r0_fail=sum(r['r0_fail'] for r in s),
                    f0_fail=sum(r['f0_fail'] for r in s), power_share_median=float(np.median([r['share'] for r in s])))
        res['c01s'] = tab
    if (Path(out) / 'l05_rows.jsonl.gz').exists():
        rows = L('l05'); tab = {}
        for rho, snr, _ in CFG['l05']['cells']:
            reps = [x for r in rows if r['rho'] == rho and r['snr'] == snr for x in r['reps']]
            tab[f'rho{rho}_snr{snr}'] = dict(frames=sum(r['rho'] == rho and r['snr'] == snr for r in rows), pairs=len(reps),
                fail={a: int(sum(x[a][0] for x in reps)) for a in ('A', 'B', 'AJ', 'BJ')},
                r0_support_right={a: int(sum(x[a][1] for x in reps)) for a in ('A', 'B', 'AJ', 'BJ')},
                BJ_only_fail_vs_B=int(sum(x['BJ'][0] and not x['B'][0] for x in reps)), B_only_fail_vs_BJ=int(sum(x['B'][0] and not x['BJ'][0] for x in reps)))
        res['l05'] = tab
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('c01s', 'l05', 'read')); ap.add_argument('--out', required=True); a = ap.parse_args()
    read(a.out) if a.mode == 'read' else run(a.mode, a.out)
