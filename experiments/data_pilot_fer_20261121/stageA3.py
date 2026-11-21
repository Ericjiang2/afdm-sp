"""Stage A3 (STAGEA3_PROTOCOL.md): Doppler-error tolerance of the round-0 channel.  Round 0 gets the true delays and
true Doppler plus Gaussian error sigma * z (z ~ N(0,1) per path, fixed per frame and scenario, shared across sigma,
rho and SNR); gains are the pilot LS solution of time_refine at those values (stage A2 'ldop' with perturbed Doppler).
one_arm is stageA2.one_arm with the truth passed to f0_true replaced by the perturbed one (stageA2.one_arm scores
against the truth it injects, so it cannot be called directly).

  python stageA3.py gate --out out/stageA3_gate.json   (needs out/stageA2 rows)
  python stageA3.py run  --out out/stageA3
  python stageA3.py read --out out/stageA3             (needs out/stageA and out/stageA2 rows)
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

import stageA, stageA2
from stageA import FRAMES, SCENARIOS, setup, support_stats
from stageA2 import f0_true, crossing, load

RHOS = (100, 150, 200)
SNRS = stageA2.SNRS
SIGMAS = (25, 50, 100, 200)                      # Doppler error std in 1/1000 bin
ARMS = tuple(f's{s:03d}' for s in SIGMAS)
FRAMES_PER_SHARD, WORKERS = 5, 32
BOOT, SEED = 2000, 20261121


def z_paths(frame, s_, n):
    return np.random.default_rng([SEED, frame, SCENARIOS.index(s_)]).standard_normal(n)


def one_arm(C, obs, truth, sigma, z):
    ctx, stage3 = C['ctx'], C['stage3']
    pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + sigma / 1000 * z).tolist())
    dec, arrays, syndrome, _ = f0_true(C, obs, pert, 'ls')
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


def run_key(C, base, s_, rho, snr, frame, sigmas=SIGMAS):
    raw, obs, truth = C['stage3'].observed(C['ctx'], base, rho, snr)
    z = z_paths(frame, s_, len(truth['l_i']))
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
                arms={f's{s:03d}': one_arm(C, obs, truth, s, z) for s in sigmas})


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
    """G1: sigma = 0 reproduces the stage A2 'ldop' rows (syndrome, F0 errors, final errors).
    G2: for sigma = .05 bin, round 0 carries the true delays and exactly k_real + .05 z, with z fixed across rho/SNR."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']
    rows = {}
    with gzip.open(Path(out).parent / 'stageA2' / 'rows_shard000.jsonl.gz', 'rt') as fh:
        for line in fh:
            r = json.loads(line); rows[(r['scenario'], r['rho'], r['snr'], r['frame'])] = r
    keys = [k for k in rows if k[1] in (100, 200) and k[2] in (400, 600)][:8]
    res = []
    for s_, rho, snr, frame in keys:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        z = z_paths(frame, s_, len(truth['l_i']))
        rec = one_arm(C, obs, truth, 0, z); a = rows[(s_, rho, snr, frame)]['arms']['ldop']
        reproduce = all(rec[k] == a[k] for k in ('syndrome', 'f0_errors', 'errors'))
        pert = dict(truth, k_real=(np.asarray(truth['k_real'], float) + .05 * z).tolist())
        _, arr, _, _ = f0_true(C, obs, pert, 'ls')
        l = list(np.asarray(truth['l_i'], int)); order = [l.index(d) for d in arr['r0_delays']]
        exact = (sorted(arr['r0_delays'].tolist()) == sorted(l)
                 and np.allclose(arr['r0_dopplers'], (np.asarray(truth['k_real']) + .05 * z)[order]))
        res.append(dict(key=[s_, rho, snr, frame], reproduce=bool(reproduce), r0_exact=bool(exact)))
    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
    for snr in (400, 600):
        run_key(C, base, 'G', 100, snr, 41399)
    per_key = (time.process_time() - t) / 2
    out_ = dict(cpu_seconds_per_key=per_key,
                projected_core_hours=per_key * len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS) / 3600 * 1.3,
                G1=all(x['reproduce'] for x in res), G2=all(x['r0_exact'] for x in res), keys=res)
    Path(out).write_text(json.dumps(out_, indent=1)); print(json.dumps(out_, indent=1))


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    frames = list(FRAMES)
    jobs = [(i, frames[k:k + FRAMES_PER_SHARD], str(out)) for i, k in enumerate(range(0, len(frames), FRAMES_PER_SHARD))]
    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, sigmas_millibin=SIGMAS, arms=ARMS, workers=WORKERS), indent=1))
    t0 = time.time(); done = 0
    with get_context('spawn').Pool(WORKERS) as pool:
        for idx, n in pool.imap_unordered(shard_job, jobs):
            done += n > 0
    ch = resource.getrusage(resource.RUSAGE_CHILDREN); hours = (ch.ru_utime + ch.ru_stime) / 3600
    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
    (out / 'STATUS').write_text((f'DONE {done} {hours:.4f}' if done == len(jobs) else f'STOPPED incomplete {hours:.4f}') + '\n')
    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))


def r0_err(out, arms, rhos, snr_lo=400, snr_hi=500):
    """Mean power-weighted round-0 |Doppler error| per arm and rho over SNR in [snr_lo, snr_hi] (descriptive)."""
    acc = {(a, r): [] for a in arms for r in rhos}
    for p in sorted(Path(out).glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                if r['rho'] in rhos and snr_lo <= r['snr'] <= snr_hi:
                    for a in arms:
                        e = r['arms'][a]['r0']['doppler_err']
                        if e is not None:
                            acc[(a, r['rho'])].append(e)
    return {a: {str(r): float(np.mean(acc[(a, r)])) for r in rhos} for a in arms}


def read(out):
    out = Path(out); status = (out / 'STATUS').read_text().split()
    if status[0] != 'DONE':
        raise ValueError(status)
    fa, _ = load(out.parent / 'stageA', stageA.ARMS, stageA.RHOS, stageA.SNRS)      # base, delay
    fb, _ = load(out.parent / 'stageA2', stageA2.ARMS, stageA2.RHOS, SNRS)           # full, ldop
    fc, _ = load(out, ARMS, RHOS, SNRS)                                               # sigma arms
    ia = [stageA.RHOS.index(r) for r in RHOS]; ib = [stageA2.RHOS.index(r) for r in RHOS]

    def means(w):
        def m(fail, snrs):
            fer = np.tensordot(w, fail, axes=(0, 0)) / w.sum()
            return np.apply_along_axis(crossing, -1, fer, snrs).mean(axis=1)         # arms x rho
        return m(fa, stageA.SNRS)[:, ia], m(fb, SNRS)[:, ib], m(fc, SNRS)

    def stats(ma, mb, mc):
        delay_best, ldop_best = ma[1].min(), mb[1].min()
        best = mc.min(axis=1)
        return np.concatenate([(delay_best - best) / (delay_best - ldop_best), best, [delay_best, ldop_best]])

    w = np.ones(len(FRAMES)); ma, mb, mc = means(w); g = stats(ma, mb, mc)
    rng = np.random.default_rng(SEED); boots = []
    for _ in range(BOOT):
        wb = np.bincount(rng.integers(0, len(FRAMES), len(FRAMES)), minlength=len(FRAMES)).astype(float)
        boots.append(stats(*means(wb)))
    boots = np.array(boots); k = len(SIGMAS)

    def ci(x):
        return [float(v) for v in np.percentile(x, [2.5, 97.5])] if np.isfinite(x).all() else [float('nan')] * 2
    R = {a: dict(point=float(g[i]), ci=ci(boots[:, i])) for i, a in enumerate(ARMS)}
    lo_100, hi_050 = R['s100']['ci'][0], R['s050']['ci'][1]
    verdict = 'EASY' if lo_100 >= .5 else 'HARD' if hi_050 < .5 else 'MIDDLE'
    res = dict(_argv=sys.argv, protocol='STAGEA3_PROTOCOL.md',
               mean_crossing=dict(delay={str(r): float(ma[1, j]) for j, r in enumerate(RHOS)},
                                  ldop={str(r): float(mb[1, j]) for j, r in enumerate(RHOS)},
                                  **{a: {str(r): float(mc[i, j]) for j, r in enumerate(RHOS)} for i, a in enumerate(ARMS)}),
               best=dict(delay=float(g[2 * k]), ldop=float(g[2 * k + 1]), **{a: float(g[k + i]) for i, a in enumerate(ARMS)}),
               retained_fraction=R, verdict=verdict,
               r0_doppler_err_snr4_5=dict(delay=r0_err(out.parent / 'stageA', ('delay',), RHOS)['delay'],
                                          **r0_err(out, ARMS, RHOS)),
               status=status)
    (out / 'results.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'run', 'read')); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(gate=gate, run=run, read=read)[a.mode](a.out)
