"""Stage A2 (STAGEA2_PROTOCOL.md): does a fully true round-0 channel (delays, Doppler, gains) beat the true-delay
ceiling of stage A?  Copies stageA.one_arm/f0 with one change: the round-0 call of ctx.native.time_refine is replaced
(stageA.f0 can only override pilot_front, whose Doppler/gains time_refine re-estimates from the pilot alone).

Arms per key (same observation as stage A):
  full = round 0 uses the true (l_i, k_real, g_i); round 1 and the CODELAY exchange unchanged.
  ldop = round 0 uses the true (l_i, k_real); gains are the LS solution of time_refine at those values (no search).
base / delay rows come from stage A (out/stageA, same frames, rho, SNR grid >= 3 dB, same observations).

  python stageA2.py gate --out out/stageA2_gate.json
  python stageA2.py run  --out out/stageA2
  python stageA2.py read --out out/stageA2      (needs out/stageA rows next to it)
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import stageA
from stageA import FRAMES, SCENARIOS, setup, support_stats

RHOS = (50, 100, 150, 200)
SNRS = (200, 250) + stageA.SNRS
ARMS = ('full', 'ldop')
FRAMES_PER_SHARD, WORKERS = 5, 32
BOOT, SEED, KILL_DB = 2000, 20261121, 0.15


def f0_true(C, obs, truth, gains):
    """F0 whose round-0 time_refine returns the true channel; gains='true' or 'ls'. Restores time_refine afterwards."""
    native = C['ctx'].native
    orig = native.time_refine
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
    state = dict(calls=0)

    def refine(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw):
        state['calls'] += 1
        if state['calls'] > 1:
            return orig(y, pilot, mu, v, ls, ks, gs, c1, c2, noise, **kw)
        ch, det = orig(y, pilot, mu, v, l, nu, g, c1, c2, noise, **dict(kw, rounds=0))
        if gains == 'true':
            ch = type(ch)(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers, [g[list(l).index(d)] for d in ch.delays])
        return ch, det
    native.time_refine = refine
    try:
        return C['stage3'].e1.f0_state(C['ctx'], obs)
    finally:
        native.time_refine = orig


def one_arm(C, obs, truth, gains):
    ctx, stage3 = C['ctx'], C['stage3']
    dec, arrays, syndrome, _ = f0_true(C, obs, truth, gains)
    s2 = float(obs['sigma2'])
    rec = dict(syndrome=int(syndrome),
               r0_errors=int(stage3.e1.gd.score(ctx, arrays['r0_decoded'], truth)),
               f0_errors=int(stage3.e1.gd.score(ctx, dec['decoded'], truth)),
               r0=support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, s2),
               r1=support_stats(arrays['r1_delays'], arrays['r1_dopplers'], truth, s2))
    if syndrome:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        rec['errors'] = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth))
        rec['final'] = support_stats([p.delay for p in br['result'].paths], [p.doppler for p in br['result'].paths], truth, s2)
    else:
        rec['errors'] = rec['f0_errors']; rec['final'] = rec['r1']
    return rec


def run_key(C, base, s_, rho, snr, frame):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
                arms=dict(full=one_arm(C, obs, truth, 'true'), ldop=one_arm(C, obs, truth, 'ls')))


def shard_job(job):
    idx, frames, out = job
    C = setup(); path = Path(out) / f'rows_shard{idx:03d}.jsonl'; n = 0
    with open(path, 'x') as fh:
        for frame in frames:
            for s_ in SCENARIOS:
                for rho in RHOS:
                    base = C['stage3'].inputs(C['ctx'], frame, s_, rho)
                    for snr in SNRS:
                        print(json.dumps(run_key(C, base, s_, rho, snr, frame)), file=fh); n += 1
    os.system(f'gzip -n {path}')
    return idx, n


def gate(out):
    """G1: identity time_refine wrapper is bitwise the baseline, and the base arm reproduces stage A rows.
    G2: round 0 of 'full' carries exactly the true delays, Doppler and gains.
    G3: gain convention: noiseless, true data known, LS gains at the true (l, nu) align with truth g_i (cosine >= .999)."""
    C = setup(); stage3, ctx, native = C['stage3'], C['ctx'], C['ctx'].native
    rows = {}
    with gzip.open(Path(out).parent / 'stageA' / 'rows_shard000.jsonl.gz', 'rt') as fh:
        for line in fh:
            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    keys = [k for k in rows if k[1] in (100, 200) and k[2] in (500, 800)][:8]
    res = []
    for s_, rho, snr, frame in keys:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        rec = stageA.one_arm(C, obs, truth, None); a = rows[(s_, rho, snr, frame)]['arms']['base']
        reproduce = all(rec[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
        dec0, arr0, _, _ = stageA.f0(C, obs)
        orig = native.time_refine
        native.time_refine = lambda *p, **kw: orig(*p, **kw)
        try:
            dec1, arr1, _, _ = stage3.e1.f0_state(ctx, obs)
        finally:
            native.time_refine = orig
        ident = all(np.array_equal(arr0[k], arr1[k]) for k in ('r0_delays', 'r0_dopplers', 'r1_delays', 'r1_dopplers')) \
            and np.array_equal(dec0['decoded'], dec1['decoded'])
        _, arr2, _, _ = f0_true(C, obs, truth, 'true')
        l = np.asarray(truth['l_i'], int); order = [list(l).index(d) for d in arr2['r0_delays']]
        g2 = (sorted(arr2['r0_delays'].tolist()) == sorted(l.tolist())
              and np.allclose(arr2['r0_dopplers'], np.asarray(truth['k_real'])[order])
              and np.allclose(arr2['r0_ce_gains'], np.asarray(truth['g_i'])[order]))
        res.append(dict(key=[s_, rho, snr, frame], reproduce=bool(reproduce), identity=bool(ident), full_r0_true=bool(g2)))
    cos = []
    for frame in (41000, 41001, 41002, 41003):
        base = stage3.inputs(ctx, frame, 'U', 300)
        raw, obs, truth = stage3.observed(ctx, base, 300, 1200)
        l = np.asarray(truth['l_i'], int); g = np.asarray(truth['g_i'], complex); y0 = np.asarray(raw['noiseless'])
        # noiseless observation with the true data known: LS gains at the true (l, nu) must equal truth g_i
        ch, _ = native.time_refine(y0, obs['pilot'], np.asarray(raw['data']), np.zeros(len(y0)), l,
                                   np.asarray(truth['k_real'], float), g, ctx.system.c1, ctx.system.c2, 1e-12,
                                   mode='mean', max_paths=8, rounds=0)
        gt = np.array([g[list(l).index(d)] for d in ch.delays])
        cos.append(float(abs(np.vdot(ch.gains, gt)) / np.linalg.norm(ch.gains) / np.linalg.norm(gt)))
    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
    for snr in (500, 800):
        run_key(C, base, 'G', 100, snr, 41399)
    per_key = (time.process_time() - t) / 2
    out_ = dict(cpu_seconds_per_key=per_key,
                projected_core_hours=per_key * len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS) / 3600 * 1.3,
                G1=all(x['reproduce'] and x['identity'] for x in res), G2=all(x['full_r0_true'] for x in res),
                G3=min(cos) >= .999, cosines=cos, keys=res)
    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    frames = list(FRAMES)
    jobs = [(i, frames[k:k + FRAMES_PER_SHARD], str(out)) for i, k in enumerate(range(0, len(frames), FRAMES_PER_SHARD))]
    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
    t0 = time.time(); done = 0
    with get_context('spawn').Pool(WORKERS) as pool:
        for idx, n in pool.imap_unordered(shard_job, jobs):
            done += n > 0
    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
    (out / 'STATUS').write_text((f'DONE {done} {hours:.4f}' if done == len(jobs) else f'STOPPED incomplete {hours:.4f}') + '\n')
    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))


def crossing(fer, snrs):
    """stageA.crossing on an arbitrary SNR grid (dB)."""
    x = np.asarray(snrs) / 100; lf = np.log10(np.maximum(fer, 1e-4))
    if fer[0] <= .01:
        return -np.inf
    for i in range(1, len(x)):
        if fer[i] <= .01:
            t = (lf[i - 1] + 2) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
            return x[i - 1] + t * (x[i] - x[i - 1])
    return np.inf


def load(out, arms, rhos, snrs):
    fi = {f: i for i, f in enumerate(FRAMES)}
    fail = np.zeros((len(FRAMES), len(arms), len(SCENARIOS), len(rhos), len(snrs)), bool); seen = np.zeros_like(fail)
    diag = []
    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                if r['rho'] not in rhos or r['snr'] not in snrs:
                    continue
                for a, arm in enumerate(arms):
                    j = (fi[r['frame']], a, SCENARIOS.index(r['scenario']), rhos.index(r['rho']), snrs.index(r['snr']))
                    fail[j] = r['arms'][arm]['errors'] > 0; seen[j] = True
                if 'full' in arms and r['arms']['full']['errors'] > 0:
                    f = r['arms']['full']['final']
                    diag.append(dict(support_right=f['support_right'], doppler_err=f['doppler_err'] or 0.,
                                     r0_fail=r['arms']['full']['r0_errors'] > 0))
    if not seen.all():
        raise ValueError(f'incomplete grid in {out}')
    return fail, diag


def read(out):
    out = Path(out); status = (out / 'STATUS').read_text().split()
    if status[0] != 'DONE':
        raise ValueError(status)
    fa, _ = load(out.parent / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)       # base, delay
    fb, diag = load(out, ARMS, RHOS, SNRS)                                            # full, ldop
    lo_idx = [stageA.RHOS.index(r) for r in RHOS]

    def table(w):
        def m(fail, snrs):
            fer = np.tensordot(w, fail, axes=(0, 0)) / w.sum()
            return np.apply_along_axis(crossing, -1, fer, snrs)                  # arms x scen x rho
        ca, cb = m(fa, stageA.SNRS), m(fb, SNRS)
        return ca, cb, ca.mean(axis=1), cb.mean(axis=1)

    def stats(ma, mb):
        delay_best = np.min(ma[1][lo_idx]); full_best = np.min(mb[0]); base_best = np.min(ma[0])
        return delay_best - full_best, base_best - full_best, delay_best, full_best, base_best

    w = np.ones(len(FRAMES)); ca, cb, ma, mb = table(w); g = stats(ma, mb)
    rng = np.random.default_rng(SEED); boots = []
    for _ in range(BOOT):
        wb = np.bincount(rng.integers(0, len(FRAMES), len(FRAMES)), minlength=len(FRAMES)).astype(float)
        boots.append(stats(*table(wb)[2:])[:2])
    boots = np.array(boots)

    def ci(x):
        return [float(v) for v in np.percentile(x, [2.5, 97.5])] if np.isfinite(x).all() else [float('nan')] * 2
    lo, hi = ci(boots[:, 0])
    verdict = 'CONTINUE' if lo > KILL_DB else 'STOP' if hi < KILL_DB else 'INCONCLUSIVE'
    n = len(diag)
    split = dict(n=n, support_missing=float(np.mean([not d['support_right'] for d in diag])) if n else None,
                 support_right_doppler_gt_0p1=float(np.mean([d['support_right'] and d['doppler_err'] > .1 for d in diag])) if n else None,
                 support_right_doppler_ok=float(np.mean([d['support_right'] and d['doppler_err'] <= .1 for d in diag])) if n else None,
                 r0_decode_failed=float(np.mean([d['r0_fail'] for d in diag])) if n else None)
    res = dict(_argv=sys.argv, protocol='STAGEA2_PROTOCOL.md',
               mean_crossing=dict({arm: {str(r): float(ma[i, j]) for j, r in enumerate(stageA.RHOS)} for i, arm in enumerate(stageA.ARMS)},
                                  **{arm: {str(r): float(mb[i, j]) for j, r in enumerate(RHOS)} for i, arm in enumerate(ARMS)}),
               crossings={arm: {s_: {str(r): float(cb[i, k, j]) for j, r in enumerate(RHOS)} for k, s_ in enumerate(SCENARIOS)}
                          for i, arm in enumerate(ARMS)},
               delay_best_low_rho=float(g[2]), full_best=float(g[3]), base_best=float(g[4]),
               gain_vs_delay=float(g[0]), gain_vs_delay_ci=[lo, hi], gain_vs_base=float(g[1]), gain_vs_base_ci=ci(boots[:, 1]),
               verdict=verdict, full_failure_split=split, status=status)
    (out / 'results.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'run', 'read')); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(gate=gate, run=run, read=read)[a.mode](a.out)
