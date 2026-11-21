#!/usr/bin/env python3
"""Idea-funnel L2 checks, batch 3 (2026-11-21, runner l), for cards I-20261121-l01, -l03 and -l04.
Source: ideas/l2/l2_batch2.py and l2_20261121.py (imported).  New arms only:
  l01  round-0 decoder input re-decoded with the per-symbol reliabilities moved to other positions (truth-relabelled)
  l03  a random 10% / 20% of the data symbols handed to the channel estimator only, as known symbols
  l04b the l04 re-send comparison at more (rho, SNR) points
  python l2_batch3.py smoke|l01|l03|l04b|read --out out4
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch2 as b2  # noqa: E402
from l2_batch2 import setup, SCENARIOS, SEED, WORKERS, stageA, score_f0, reobserve  # noqa: E402

CFG = dict(
    l01=dict(frames=[41000, 41150], cells=[[200, 500], [200, 600], [250, 500]]),
    l03=dict(frames=[41000, 41100], rhos=[100, 150], snrs=[400, 500, 600, 800], alphas=[0.1, 0.2]),
    l04b=dict(cells=[[100, 800], [100, 600], [150, 600], [200, 500]], max_frames=30, repeats=4, frame_offset=5000),
)


def scale_of(raw, obs):
    return float(np.linalg.norm(raw['pilot']) / np.linalg.norm(obs['pilot']))


def job_l01(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; out = []
    decoder_messages = ctx.native.decoder_messages      # the copy the frozen context loaded (importing 'receiver' first breaks its md5 gate)
    for s_ in SCENARIOS:
        for rho, snr in CFG['l01']['cells']:
            raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, rho), rho, snr)
            dec, arrays, syn, _ = stageA.f0(C, obs)
            L = np.asarray(arrays['r0_input_llr'], float); b = np.asarray(raw['coded']).astype(int); n = len(L) // 2
            z = (1 - 2 * b) * L
            rng = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 51])
            perms = dict(orig=np.arange(n), shift=(np.arange(n) + n // 2) % n, rand=rng.permutation(n))
            rec = dict(scenario=s_, rho=rho, snr=snr, frame=frame, sign_agree=float(np.mean(z > 0)),
                       r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)))
            for name, p in perms.items():
                idx = np.r_[p, p + n]
                d = decoder_messages(ctx.code, np.clip((1 - 2 * b) * z[idx], -20, 20), maxiter=50)
                rec[name] = int(stage3.e1.gd.score(ctx, d['decoded'], truth))
            out.append(rec)
    return out


def f0_anchor(C, obs, data, idx):
    native = C['ctx'].native; orig = native.time_refine
    def refine(y, pilot, mu, v, *a, **kw):
        mu = np.array(mu, complex); v = np.array(v, float); mu[idx] = data[idx]; v[idx] = 0.0
        return orig(y, pilot, mu, v, *a, **kw)
    native.time_refine = refine
    try:
        return C['stage3'].e1.f0_state(C['ctx'], obs)
    finally:
        native.time_refine = orig


def job_l03(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l03']; out = []
    for s_ in SCENARIOS:
        for rho in cfg['rhos']:
            base = stage3.inputs(ctx, frame, s_, rho)
            for snr in cfg['snrs']:
                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
                d = np.asarray(raw['data'], complex) / scale_of(raw, obs); n = len(d)
                order = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 52]).permutation(n)
                arms = {}
                dec, arrays, syn, _ = stageA.f0(C, obs); arms['base'] = score_f0(C, obs, truth, dec, arrays, syn, True)
                for a in cfg['alphas']:
                    dec, arrays, syn, _ = f0_anchor(C, obs, d, order[:int(a * n)])
                    arms[f'anc{int(a * 100):02d}'] = score_f0(C, obs, truth, dec, arrays, syn, True)
                out.append(dict(scenario=s_, rho=rho, snr=snr, frame=frame,
                                arms={k: dict(r0_errors=v['r0_errors'], f0_errors=v['f0_errors'], errors=v['errors'],
                                              r0_dop=v['r0']['doppler_err'], r0_right=v['r0']['support_right']) for k, v in arms.items()}))
    return out


def job_l04b(job):
    s_, frame, rho, snr = job
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l04b']
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, s_, rho), rho, snr)
    sc = scale_of(raw, obs); n = len(obs['y']); d0 = np.asarray(raw['data'], complex) / sc
    def run(o, t):
        dec, arrays, syn, _ = stageA.f0(C, o)
        return score_f0(C, o, t, dec, arrays, syn, True)['errors']
    reps = []
    for j in range(cfg['repeats']):
        rng = np.random.default_rng([SEED, frame, SCENARIOS.index(s_), 40, j])
        noise = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
        raw2, _, truth2 = stage3.observed(ctx, stage3.inputs(ctx, frame + cfg['frame_offset'] * (j + 1), s_, rho), rho, snr)
        reps.append([int(run(reobserve(obs, raw, d0, noise), truth) > 0),
                     int(run(reobserve(obs, raw, np.asarray(raw2['data'], complex) / sc, noise), dict(truth, info=truth2['info'])) > 0)])
    return [dict(scenario=s_, frame=frame, rho=rho, snr=snr, reps=reps)]


def l04b_jobs():
    cfg = CFG['l04b']; cells = {tuple(c): [] for c in cfg['cells']}
    d = HERE.parents[1] / 'experiments' / 'data_pilot_fer_20261121' / 'out' / 'stageA'
    for p in sorted(d.glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line); k = (r['rho'], r['snr'])
                if k in cells and r['arms']['base']['errors'] > 0:
                    cells[k].append((r['scenario'], r['frame'], r['rho'], r['snr']))
    return [j for k in cells for j in sorted(cells[k])[:cfg['max_frames']]], {f'{k[0]}_{k[1]}': len(v) for k, v in cells.items()}


JOBS = dict(l01=(job_l01, lambda: list(range(*CFG['l01']['frames']))), l03=(job_l03, lambda: list(range(*CFG['l03']['frames']))),
            l04b=(job_l04b, lambda: l04b_jobs()[0]))


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
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0,
        stageA_failed_counts=l04b_jobs()[1] if mode == 'l04b' else None), indent=1))
    os.system(f'gzip -n {path}'); print(mode, 'rows', n, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def smoke(out):
    """G1 l01: identity order reproduces the round-0 decode outcome, LLR sign convention agrees with the coded bits.
    G2 l03: alpha = 0 is the baseline.  Costs."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    t = time.process_time(); r1 = job_l01(41000); c1 = (time.process_time() - t) / len(r1)
    g1 = all((x['orig'] > 0) == (x['r0_errors'] > 0) for x in r1) and min(x['sign_agree'] for x in r1) > 0.6
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, 41000, 'U', 150), 150, 500)
    d0, a0, s0, _ = stageA.f0(C, obs); d1, a1, s1, _ = f0_anchor(C, obs, np.asarray(raw['data'], complex), np.array([], int))
    g2 = bool(np.array_equal(d0['decoded'], d1['decoded']) and np.array_equal(a0['r0_dopplers'], a1['r0_dopplers']))
    t = time.process_time(); job_l03(41001); c3 = (time.process_time() - t) / 16
    jobs, counts = l04b_jobs(); t = time.process_time(); job_l04b(jobs[0]); c4 = time.process_time() - t
    o = dict(_argv=sys.argv, G1=bool(g1), l01_rows=r1[:2], G2=g2, l04b_failed_counts=counts, l04b_jobs=len(jobs),
             projected_core_hours=dict(l01=c1 * 150 * 6 / 3600, l03=c3 * 1600 / 3600, l04b=c4 * len(jobs) / 3600))
    Path(out).mkdir(parents=True, exist_ok=True); (Path(out) / 'smoke.json').write_text(json.dumps(o, indent=1)); print(json.dumps(o, indent=1))


def read(out):
    L = lambda m: [json.loads(l) for l in gzip.open(Path(out) / f'{m}_rows.jsonl.gz', 'rt')]
    res = dict(_argv=sys.argv, _config=CFG)
    if (Path(out) / 'l01_rows.jsonl.gz').exists():
        rows = L('l01'); tab = {}
        for rho, snr in CFG['l01']['cells']:
            s = [r for r in rows if r['rho'] == rho and r['snr'] == snr]
            f = {k: np.array([r[k] > 0 for r in s]) for k in ('orig', 'shift', 'rand')}
            tab[f'rho{rho}_snr{snr}'] = dict(n=len(s), **{k: int(v.sum()) for k, v in f.items()},
                orig_only_fail_vs_rand=int((f['orig'] & ~f['rand']).sum()), rand_only_fail_vs_orig=int((f['rand'] & ~f['orig']).sum()))
        allr = np.array([[r['orig'] > 0, r['rand'] > 0, r['shift'] > 0, r['frame']] for r in rows])
        d = allr[:, 0].astype(float) - allr[:, 1].astype(float); fr = allr[:, 3]; rng = np.random.default_rng(SEED); u = np.unique(fr)
        per = np.array([d[fr == x].sum() for x in u]); cnt = np.array([(fr == x).sum() for x in u])
        bs = [per[i].sum() / cnt[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(4000))]
        tab['pooled'] = dict(orig_minus_rand_fer=float(d.mean()), ci90=[float(np.percentile(bs, 5)), float(np.percentile(bs, 95))],
                             orig_minus_shift_fer=float((allr[:, 0].astype(float) - allr[:, 2].astype(float)).mean()))
        res['l01'] = tab
    if (Path(out) / 'l03_rows.jsonl.gz').exists():
        rows = L('l03'); tab = {}
        for rho in CFG['l03']['rhos']:
            for snr in CFG['l03']['snrs']:
                s = [r['arms'] for r in rows if r['rho'] == rho and r['snr'] == snr]
                tab[f'rho{rho}_snr{snr}'] = {a: dict(final_fail=sum(x[a]['errors'] > 0 for x in s), f0_fail=sum(x[a]['f0_errors'] > 0 for x in s),
                    r0_fail=sum(x[a]['r0_errors'] > 0 for x in s), r0_dop_mean=float(np.mean([x[a]['r0_dop'] for x in s if x[a]['r0_dop'] is not None])),
                    n=len(s)) for a in s[0]}
        res['l03'] = tab
    if (Path(out) / 'l04b_rows.jsonl.gz').exists():
        rows = L('l04b'); tab = {}
        for rho, snr in CFG['l04b']['cells']:
            s = [r for r in rows if r['rho'] == rho and r['snr'] == snr]; reps = [x for r in s for x in r['reps']]
            tab[f'rho{rho}_snr{snr}'] = dict(frames=len(s), pairs=len(reps), A_fail=sum(a for a, b in reps), B_fail=sum(b for a, b in reps),
                n_plus=sum(a and not b for a, b in reps), n_minus=sum(b and not a for a, b in reps),
                frames_A_majority_fail=sum(sum(a for a, b in r['reps']) * 2 > len(r['reps']) for r in s))
        res['l04b'] = tab
    (Path(out) / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'l01', 'l03', 'l04b', 'read'))
    ap.add_argument('--out', required=True); a = ap.parse_args()
    dict(smoke=smoke, read=read).get(a.mode, lambda o: run(a.mode, o))(a.out)
