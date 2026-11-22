#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l13 (2026-11-22, runner l, claude-fable-5.2); also the
"delays from the markers" item owed by I-20261122-l08 / -l12.  Delays are no longer given: they are found from the two
end markers (batch pick or path-by-path CLEAN), then Doppler per found delay from markers + superimposed pilot.
Source: l2_r3_marker.py (estimate imported; packet synthesis of one_hybrid copied here because it returns no samples)
and l2_r3_marker2.py (setup, run_arm imported).  Criteria: ideas/l2/PREDICTIONS_r3_batch13.md.
  python l2_r3_marker3.py smoke|run|read --out out_r3b13
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r3_marker as mk  # noqa: E402
from l2_r3_marker2 import setup, SEED, run_arm  # noqa: E402

WORKERS = 12
N, CP, LMAX = mk.N, mk.CP, mk.LMAX
CFG = dict(frames=[55000, 55200], scenario='G', snrs=[350, 400, 450, 500], rho=0.10, max_paths=8, thr=10.0,
           arms=[('genie_hyb128', 128, 'bpsk', 'genie'), ('clean_bpsk_hyb128', 128, 'bpsk', 'clean'), ('batch_bpsk_hyb128', 128, 'bpsk', 'batch'),
                 ('clean_bpsk_m256', 256, 'bpsk', 'clean'), ('clean_lfm_m256', 256, 'lfm', 'clean')])


def marker(kind, L, rng):                 # 'bpsk': random +-1 (stands in for distinct m-sequences); 'lfm': full-band up-chirp
    if kind == 'lfm':
        n = np.arange(L); return np.exp(1j * np.pi * n * n / L)
    return rng.choice([-1.0, 1.0], L).astype(complex)


def synth(l, nu, g, snr_db, L, rho, kind, rng):
    mA, mB = marker(kind, L, rng), marker(kind, L, rng)
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2); sp = np.exp(2j * np.pi * rng.uniform(size=N))
    known = np.r_[mA, np.sqrt(rho) * np.r_[sp[-CP:], sp], mB]; data = np.r_[np.zeros(L), np.sqrt(1 - rho) * np.r_[d[-CP:], d], np.zeros(L)]
    T = len(known) + LMAX; t = np.arange(T); sig = np.zeros(T, complex)
    for li, vi, gi in zip(l, nu, g):
        out = np.zeros(T, complex); out[li:li + len(known)] = known + data; sig += gi * out * np.exp(2j * np.pi * vi * t / N)
    ptot = float(np.sum(np.abs(g) ** 2)); s2 = ptot / 10 ** (snr_db / 10)
    y = sig + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T))
    nv = np.full(T, s2); nv[L:L + CP + N + LMAX] = s2 + (1 - rho) * ptot
    return y, known, t, 1 / np.sqrt(nv), s2


def replicas(known, delays, T):
    U = np.zeros((len(delays), T), complex)
    for i, li in enumerate(delays):
        U[i, int(li):int(li) + len(known)] = known
    return U


def metric(r, known, L):                  # non-coherent sum of the two marker correlations, per candidate delay
    mA, mB = known[:L], known[-L:]; off = len(known) - L
    return np.array([abs(np.vdot(mA, r[c:c + L])) ** 2 + abs(np.vdot(mB, r[c + off:c + off + L])) ** 2 for c in range(LMAX + 1)])


def est_delays(y, known, t, wgt, L, s2, mode):
    T = len(y); kmax = CFG['max_paths']
    if mode == 'batch':
        ls = np.sort(np.argsort(-metric(y, known, L))[:kmax])
    else:
        r = y.copy(); ls = []
        for _ in range(kmax):
            m = metric(r, known, L)
            if ls:
                m[np.array(ls)] = 0
            c = int(np.argmax(m))
            if m[c] < CFG['thr'] * 2 * L * s2:                 # noise-only mean of the metric is 2 L s2
                break
            U1 = replicas(known, [c], T); nu1, g1 = mk.estimate(r * wgt, U1 * wgt[None, :], t, mk.CFG['grid'], 1)
            r = r - g1[0] * U1[0] * np.exp(2j * np.pi * nu1[0] * t / N); ls.append(c)
        ls = np.array(sorted(ls), int)
    if len(ls) == 0:
        ls = np.array([int(np.argmax(metric(y, known, L)))])
    U = replicas(known, ls, T); nh, _ = mk.estimate(y * wgt, U * wgt[None, :], t, mk.CFG['grid'], mk.CFG['sage_iters'])
    return ls, nh


def job(frame, snrs=None):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; rec = dict(frame=frame, cells={}, sup={})
    for snr in (snrs or CFG['snrs']):
        raw3, obs3, truth3 = stage3.observed(ctx, stage3.inputs(ctx, frame, CFG['scenario'], 300), 300, snr)
        rec['cells'][f'{snr}|std_sp30'] = run_arm(C, obs3, truth3, None)
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, CFG['scenario'], 100), 100, snr)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex); p = np.abs(g) ** 2
        for ai, (name, L, kind, mode) in enumerate(CFG['arms']):
            rng = np.random.default_rng([SEED, frame, snr, 200 + ai])
            y, known, t, wgt, s2 = synth(l, nu, g, snr / 100.0, L, CFG['rho'], kind, rng)
            if mode == 'genie':
                U = replicas(known, l, len(y)); nh, _ = mk.estimate(y * wgt, U * wgt[None, :], t, mk.CFG['grid'], mk.CFG['sage_iters']); ls = l
            else:
                ls, nh = est_delays(y, known, t, wgt, L, s2, mode)
            found = set(int(x) for x in ls) & set(int(x) for x in l)
            rec['sup'][f'{snr}|{name}'] = dict(n=int(len(ls)), found=len(found), missed_power=float(sum(p[i] for i in range(len(l)) if int(l[i]) not in found) / p.sum()))
            rec['cells'][f'{snr}|{name}'] = run_arm(C, obs, truth, ([int(x) for x in ls], [float(x) for x in nh], None))
    return [rec]


def run(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'marker13_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'marker13_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'marker13_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); rng = np.random.default_rng(SEED + 13); snrs = CFG['snrs']; names = ['std_sp30'] + [a[0] for a in CFG['arms']]
    col = lambda key, f='CD': np.array([r['cells'][key][f] for r in rows], float)
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    pool3 = lambda name: sum(col(f'{s}|{name}') for s in (350, 400, 450)); pool2 = lambda name: sum(col(f'{s}|{name}') for s in (400, 450))
    res = dict(frames=n, table={nm: {str(s): dict(F0=int(col(f'{s}|{nm}', 'F0').sum()), CD=int(col(f'{s}|{nm}').sum())) for s in snrs} for nm in names},
               support={nm: {str(s): dict(found_mean=float(np.mean([r['sup'][f'{s}|{nm}']['found'] for r in rows])), n_mean=float(np.mean([r['sup'][f'{s}|{nm}']['n'] for r in rows])),
                                         missed_power=float(np.mean([r['sup'][f'{s}|{nm}']['missed_power'] for r in rows]))) for s in snrs} for nm in names[1:]},
               v1_batch_minus_clean=boot(lambda ii: (pool3('batch_bpsk_hyb128')[ii] - pool3('clean_bpsk_hyb128')[ii]).sum()),
               v1_lfm_minus_bpsk_m256=boot(lambda ii: (pool3('clean_lfm_m256')[ii] - pool3('clean_bpsk_m256')[ii]).sum()),
               v2_clean_at4_minus_std_at5_pp=boot(lambda ii: 100 * (col('400|clean_bpsk_hyb128')[ii] - col('500|std_sp30')[ii]).mean()),
               v2_clean_minus_genie=boot(lambda ii: (pool2('clean_bpsk_hyb128')[ii] - pool2('genie_hyb128')[ii]).sum()))
    a, b, c, d = res['v1_batch_minus_clean'], res['v1_lfm_minus_bpsk_m256'], res['v2_clean_at4_minus_std_at5_pp'], res['v2_clean_minus_genie']
    res['veto1_ordinary_sync'] = bool((a['point'] < 12 or a['ci95'][0] <= 0) and b['point'] < 6)
    res['veto2_unknown_delay_eats_margin'] = bool(c['ci95'][1] > 5.0 or d['point'] > 12)
    (out / 'marker13_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read')); ap.add_argument('--out', default='out_r3b13'); a = ap.parse_args()
    if a.mode == 'smoke':
        t0 = time.process_time(); r = job(55000, snrs=[400])[0]; print(json.dumps(r)); print('cpu', time.process_time() - t0)
    else:
        dict(run=run, read=read)[a.mode](HERE / a.out)
