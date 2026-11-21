"""Stage A (STAGEA_PROTOCOL.md): does a true-delay round-0 support let low pilot fractions beat the best baseline?

Arms per key (same observation): base = F0 + CODELAY exchange (rho-sweep pipeline); delay = the same with the round-0
support replaced by the 8 true delays (Doppler centers observable: best pilot-MF integer column at each delay).
Injection replaces ctx.native.pilot_front only for the 'delay' F0 call; everything downstream is unchanged.
Reuses unified_cov_prospective_20261119/cstate.py (context, stage3 inputs/observed/e1.f0_state/e1.run_branch).

  python stageA.py gate  --out out/stageA_gate.json
  python stageA.py run   --out out/stageA                 (rows + STATUS)
  python stageA.py read  --out out/stageA                 (frozen readout -> results.json)
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / 'unified_cov_prospective_20261119'))
sys.path.insert(0, str(EXP / 'sp_afdm_frozen_20260920' / 'src'))

FRAMES = range(41000, 41400)
SCENARIOS = ('U', 'G')
RHOS = (50, 100, 150, 200, 250, 300)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
ARMS = ('base', 'delay')
FRAMES_PER_SHARD = 5
WORKERS = 32
TAU = 0.2
BOOT, SEED, GATE_DB = 2000, 20261121, 0.3
_C = None


def setup():
    global _C
    if _C is None:
        import cstate
        from physical import regressors
        ctx, full, cd, _ = cstate.context()
        s = ctx.system; lmax = int(s.l_max_cap)
        dl = np.repeat(np.arange(lmax + 1), 5); dk = np.tile(np.arange(-2, 3), lmax + 1)
        U = regressors(np.asarray(s._zc_seq), dl, dk.astype(float), s.c1, s.c2)
        _C = dict(stage3=cstate.stage3, ctx=ctx, cd=cd, U=U / np.linalg.norm(U, axis=0, keepdims=True),
                  lmax=lmax, orig_front=ctx.native.pilot_front)
    return _C


def f0(C, obs, inject=None):
    """F0 with an optional round-0 support override; the native module's pilot_front is restored afterwards."""
    ctx, orig = C['ctx'], C['orig_front']
    if inject is None:
        return C['stage3'].e1.f0_state(ctx, obs)

    def front(observed, system, code):
        s = orig(observed, system, code)
        ls, ks, gs = inject
        gs = np.ones(len(ls), complex) if gs is None else np.asarray(gs, complex)
        return dict(s, delays=np.asarray(ls, int), dopplers=np.asarray(ks, float), gains=gs)
    ctx.native.pilot_front = front
    try:
        return C['stage3'].e1.f0_state(ctx, obs)
    finally:
        ctx.native.pilot_front = orig


def support_stats(delays, dopplers, truth, sigma2):
    l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.abs(np.asarray(truth['g_i'])) ** 2
    rel = g >= TAU * sigma2
    have = set(int(d) for d in delays)
    miss = float(sum(g[i] for i in range(len(l)) if rel[i] and l[i] not in have))
    err, wsum = 0.0, 0.0
    for i in range(len(l)):
        if l[i] in have:
            cand = [float(dopplers[k]) for k, d in enumerate(delays) if int(d) == l[i]]
            err += g[i] * min(abs(c - nu[i]) for c in cand); wsum += g[i]
    return dict(missing_power=miss, doppler_err=err / wsum if wsum else None,
                support_right=bool(all(l[i] in have for i in range(len(l)) if rel[i])))


def one_arm(C, obs, truth, inject):
    ctx, stage3 = C['ctx'], C['stage3']
    dec, arrays, syndrome, _ = f0(C, obs, inject)
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


def genie_inject(C, obs, truth):
    z5 = (np.abs(C['U'].conj().T @ obs['y']) ** 2).reshape(C['lmax'] + 1, 5)
    ls = [int(d) for d in truth['l_i']]
    return ls, [int(np.argmax(z5[d])) - 2 for d in ls], None


def run_key(C, base, s_, rho, snr, frame):
    stage3 = C['stage3']
    raw, obs, truth = stage3.observed(C['ctx'], base, rho, snr)
    return dict(scenario=s_, rho=rho, snr=snr, frame=frame, sigma2=float(obs['sigma2']),
                arms=dict(base=one_arm(C, obs, truth, None), delay=one_arm(C, obs, truth, genie_inject(C, obs, truth))))


def shard_job(job):
    idx, frames, out = job
    C = setup()
    path = Path(out) / f'rows_shard{idx:03d}.jsonl'
    n = 0
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
    """G1: base arm reproduces archived rho-sweep F0/CD errors on 8 keys. G2: identity injection is bitwise baseline.
    G3: genie injection puts exactly the true delays in round 0."""
    C = setup(); stage3 = C['stage3']; ctx = C['ctx']
    arch = {}
    with open(EXP / 'rho_sweep_20261119' / 'out' / 'main_20261119' / 'rows_shard000.jsonl') as fh:
        for line in fh:
            r = json.loads(line); arch[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
            if len(arch) >= 400:
                break
    keys = [k for k in arch if k[1] in (150, 300) and k[2] in (500, 800)][:8]
    g1 = []
    for s_, rho, snr, frame in keys:
        base = stage3.inputs(ctx, frame, s_, rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        rec = one_arm(C, obs, truth, None); a = arch[(s_, rho, snr, frame)]
        g1.append(dict(key=[s_, rho, snr, frame], ok=bool(rec['syndrome'] == a['syndrome']
                       and rec['f0_errors'] == a['arms']['F0']['errors'] and rec['errors'] == a['arms']['CD']['errors'])))
        dec0, arr0, _, _ = f0(C, obs)
        s0 = C['orig_front'](obs, ctx.system, ctx.code)
        dec1, arr1, _, _ = f0(C, obs, (s0['delays'], s0['dopplers'], s0['gains']))
        same = all(np.array_equal(arr0[k], arr1[k]) for k in ('r0_delays', 'r1_delays', 'r1_dopplers')) and \
            np.array_equal(dec0['decoded'], dec1['decoded'])
        g1[-1]['identity_bitwise'] = bool(same)
        inj = genie_inject(C, obs, truth)
        _, arr2, _, _ = f0(C, obs, inj)
        g1[-1]['genie_r0_true'] = sorted(int(d) for d in arr2['r0_delays']) == sorted(inj[0])
    t = time.process_time(); base = stage3.inputs(ctx, 41399, 'G', 100)
    for snr in (500, 800):
        run_key(C, base, 'G', 100, snr, 41399)
    per_key = (time.process_time() - t) / 2
    res = dict(cpu_seconds_per_key=per_key, projected_core_hours=per_key * len(FRAMES) * 2 * len(RHOS) * len(SNRS) / 3600 * 1.3,
               G1=all(x['ok'] for x in g1), G2=all(x['identity_bitwise'] for x in g1), G3=all(x['genie_r0_true'] for x in g1), keys=g1)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def run(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    frames = list(FRAMES)
    jobs = [(i, frames[k:k + FRAMES_PER_SHARD], str(out)) for i, k in enumerate(range(0, len(frames), FRAMES_PER_SHARD))]
    (out / 'RUN_CONFIG.json').write_text(json.dumps(dict(_argv=sys.argv, frames=[FRAMES.start, FRAMES.stop - 1],
        scenarios=SCENARIOS, rhos=RHOS, snrs=SNRS, arms=ARMS, workers=WORKERS), indent=1))
    t0 = time.time(); done = 0; reason = None
    with get_context('spawn').Pool(WORKERS) as pool:
        for idx, n in pool.imap_unordered(shard_job, jobs):  # no in-run cost stop: cost is projected by the gate
            done += n > 0
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    hours = (ch.ru_utime + ch.ru_stime) / 3600
    if reason is None and done != len(jobs):
        reason = 'incomplete'
    os.system(f'cd {out} && md5sum rows_shard*.jsonl.gz > REMOTE_ROWS_MD5.txt')
    (out / 'STATUS').write_text((f'STOPPED {reason} {hours:.4f}' if reason else f'DONE {done} {hours:.4f}') + '\n')
    print((out / 'STATUS').read_text(), 'wall', round(time.time() - t0))


def crossing(fer):
    """First SNR where FER <= .01 by log10 interpolation; -inf if already below at the first SNR, +inf if never."""
    x = np.array(SNRS) / 100; lf = np.log10(np.maximum(fer, 1e-4))
    if fer[0] <= .01:
        return -np.inf
    for i in range(1, len(x)):
        if fer[i] <= .01:
            t = (lf[i - 1] + 2) / (lf[i - 1] - lf[i]) if lf[i - 1] != lf[i] else 1.0
            return x[i - 1] + t * (x[i] - x[i - 1])
    return np.inf


def read(out):
    out = Path(out)
    status = (out / 'STATUS').read_text().split()
    if status[0] != 'DONE':
        raise ValueError(status)
    fi = {f: i for i, f in enumerate(FRAMES)}
    fail = np.zeros((len(FRAMES), len(ARMS), len(SCENARIOS), len(RHOS), len(SNRS)), bool)
    seen = np.zeros_like(fail)
    diag = []
    for p in sorted(out.glob('rows_shard*.jsonl.gz')):
        with gzip.open(p, 'rt') as fh:
            for line in fh:
                r = json.loads(line)
                ix = (fi[r['frame']], slice(None), SCENARIOS.index(r['scenario']), RHOS.index(r['rho']), SNRS.index(r['snr']))
                for a, arm in enumerate(ARMS):
                    j = (ix[0], a) + ix[2:]
                    fail[j] = r['arms'][arm]['errors'] > 0; seen[j] = True
                d = r['arms']['delay']
                if r['rho'] <= 200 and d['errors'] > 0:
                    diag.append(dict(rho=r['rho'], snr=r['snr'], support_right=d['final']['support_right'],
                                     doppler_err=d['final']['doppler_err'], r0_err=d['r0_errors'] > 0))
    if not seen.all():
        raise ValueError('incomplete grid')

    def table(w):
        fer = np.tensordot(w, fail, axes=(0, 0)) / w.sum()          # arms x scen x rho x snr
        cr = np.apply_along_axis(crossing, -1, fer)                  # arms x scen x rho
        m = cr.mean(axis=1)                                          # U/G average, arms x rho
        return cr, m

    def gain(m):
        b = np.min(m[0]); a = np.min(m[1][[RHOS.index(r) for r in RHOS if r <= 200]])
        return b - a, b, a

    w = np.ones(len(FRAMES)); cr, m = table(w); g, b, a = gain(m)
    rng = np.random.default_rng(SEED); gs = []
    for _ in range(BOOT):
        wb = np.bincount(rng.integers(0, len(FRAMES), len(FRAMES)), minlength=len(FRAMES)).astype(float)
        gs.append(gain(table(wb)[1])[0])
    gs = np.array(gs); finite = gs[np.isfinite(gs)]
    lo, hi = (np.percentile(finite, [2.5, 97.5]) if len(finite) == len(gs) else (np.nan, np.nan))
    verdict = 'CONTINUE' if lo > GATE_DB else 'STOP' if hi < GATE_DB else 'INCONCLUSIVE'
    near = [x for x in diag]
    split = dict(n=len(near), support_missing=float(np.mean([not x['support_right'] for x in near])) if near else None,
                 support_right_doppler_gt_0p1=float(np.mean([x['support_right'] and (x['doppler_err'] or 0) > .1 for x in near])) if near else None,
                 support_right_doppler_ok=float(np.mean([x['support_right'] and (x['doppler_err'] or 0) <= .1 for x in near])) if near else None)
    res = dict(crossings={arm: {s_: {str(r): float(cr[ai, si, ri]) for ri, r in enumerate(RHOS)}
                                for si, s_ in enumerate(SCENARIOS)} for ai, arm in enumerate(ARMS)},
               mean_crossing={arm: {str(r): float(m[ai, ri]) for ri, r in enumerate(RHOS)} for ai, arm in enumerate(ARMS)},
               base_best=float(b), delay_best_low_rho=float(a), gain=float(g), gain_ci=[float(lo), float(hi)],
               verdict=verdict, delay_failure_split_rho_le_200=split, status=status)
    (out / 'results.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'run', 'read')); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    dict(gate=gate, run=run, read=read)[a.mode](a.out)
