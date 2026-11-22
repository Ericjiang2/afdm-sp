#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 step 2 for card I-20261122-l08 (2026-11-22, runner l, claude-fable-5.2).
Decoding comparison: round 0 of the project receiver started from the true delays plus the per-path Doppler estimated
from two 256-sample end markers (l2_r3_marker.py model), with the superimposed pilot share lowered to .10 / .05,
against the standard receiver at rho = .30.  Same frame index, scenario and SNR for every arm.
Source: ideas/l2/l2_r3_marker.py (estimate imported; the packet synthesis of `one` is copied here because `one` returns
only error statistics, not the estimates) and experiments/data_pilot_fer_20261121/stageA.py (f0 with inject, genie_inject).
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch7.md.
  python l2_r3_marker2.py smoke|run|read --out out_r3b7
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r2_batch1 as r2  # noqa: E402
from l2_r2_batch1 import setup, SEED, stageA  # noqa: E402
import l2_r3_marker as mk  # noqa: E402

WORKERS = 12
CFG = dict(frames=[51000, 51200], scenario='G', snrs=[400, 500, 600], marker=dict(name='L256_guard', L=256, G=102, post=True))
N, CP, LMAX = mk.N, mk.CP, mk.LMAX


def marker_doppler(l, nu, g, snr_db, rng):
    """Per-path Doppler from the two end markers; channel given in the frame convention (phase reference = first data
    sample at receive index t0 = L + G + CP), converted to the packet convention of l2_r3_marker."""
    arm = CFG['marker']; L, G = arm['L'], arm['G']; t0 = L + G + CP
    gs = np.asarray(g, complex) * np.exp(-2j * np.pi * np.asarray(nu, float) * t0 / N)
    m = lambda: np.exp(2j * np.pi * rng.uniform(size=L))
    d = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2); body = np.r_[d[-CP:], d]
    s_mark = np.r_[m(), np.zeros(G + CP + N + G), m()]; s_data = np.r_[np.zeros(L + G), body, np.zeros(G + L)]
    D = L + G + CP + N + G; wins = [np.arange(0, L + LMAX), np.arange(D, D + L + LMAX)]
    T = len(s_mark) + LMAX; t = np.arange(T); tw = np.concatenate(wins)
    sig = np.zeros(T, complex)
    for li, vi, gi in zip(l, nu, gs):
        out = np.zeros(T, complex); out[li:li + len(s_mark)] = s_mark + s_data; sig += gi * out * np.exp(2j * np.pi * vi * t / N)
    s2 = float(np.sum(np.abs(gs) ** 2)) / 10 ** (snr_db / 10)
    y = sig + np.sqrt(s2 / 2) * (rng.standard_normal(T) + 1j * rng.standard_normal(T))
    U = np.zeros((len(l), len(tw)), complex)
    for i, li in enumerate(l):
        rep = np.zeros(T, complex); rep[li:li + len(s_mark)] = s_mark; U[i] = rep[tw]
    nh, _ = mk.estimate(y[tw], U, tw, mk.CFG['grid'], mk.CFG['sage_iters'])
    return nh


def run_arm(C, obs, truth, inject):
    ctx, stage3 = C['ctx'], C['stage3']
    dec, arrays, syn, _ = stageA.f0(C, obs, inject)
    f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth) > 0); cd_err = f0_err
    if syn:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
        cd_err = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth) > 0)
    return dict(F0=f0_err, CD=cd_err)


def job(frame):
    import stageA2
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; scen = CFG['scenario']; rec = dict(frame=frame, cells={})
    for snr in CFG['snrs']:
        ref = None
        for rho in (300, 100, 50):
            raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, rho), rho, snr)
            l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
            if ref is None:
                ref = (l.copy(), nu.copy(), g.copy())
                rng = np.random.default_rng([SEED, frame, snr, 77]); nh = marker_doppler(l, nu, g, snr / 100.0, rng)
                p = np.abs(g) ** 2; rec.setdefault('marker_mae_w', {})[str(snr)] = float(np.sum(p * np.abs(nh - nu)) / p.sum())
            else:
                rec['same_channel'] = bool(rec.get('same_channel', True) and np.array_equal(l, ref[0]) and np.allclose(nu, ref[1]) and np.allclose(g, ref[2]))
            ls = [int(x) for x in l]
            arms = {'std': None}
            if rho != 300:
                arms['delay'] = stageA.genie_inject(C, obs, truth)                 # true delays, integer Doppler from the pilot (card c14)
                arms['marker'] = (ls, [float(x) for x in nh], None)                # true delays + marker Doppler (this card)
            else:
                arms['marker'] = (ls, [float(x) for x in nh], None)
            for name, inj in arms.items():
                rec['cells'][f'{snr}|{rho}|{name}'] = run_arm(C, obs, truth, inj)
            if rho != 300:
                dec_t, _, _, _ = stageA2.f0_true(C, obs, truth, 'true')
                rec['cells'][f'{snr}|{rho}|trueH'] = dict(F0=int(stage3.e1.gd.score(ctx, dec_t['decoded'], truth) > 0))
    return [rec]


CFG3 = dict(frames=[53000, 53200], scenario='G', snrs=[300, 350, 400, 500], hybrid=dict(name='L128_sp10', L=128, G=0, rho=0.10))


def job3(frame):
    """Step 3 (cards 22-l08 and 22-l12): lower SNR points, and the hybrid start (128-sample end markers + the rho = .10
    superimposed pilot, joint estimate) next to the 256-sample marker start.  Criteria: PREDICTIONS_r3_batch10.md."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; scen = CFG3['scenario']; rec = dict(frame=frame, cells={}, mae={})
    for snr in CFG3['snrs']:
        raw3, obs3, truth3 = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 300), 300, snr)
        rec['cells'][f'{snr}|300|std'] = run_arm(C, obs3, truth3, None)
        raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 100), 100, snr)
        l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
        rec['same_channel'] = bool(rec.get('same_channel', True) and np.array_equal(l, np.asarray(truth3['l_i'], int)) and np.allclose(nu, truth3['k_real']))
        ls = [int(x) for x in l]; p = np.abs(g) ** 2
        nh_m = marker_doppler(l, nu, g, snr / 100.0, np.random.default_rng([SEED, frame, snr, 77]))
        nh_h = mk.one_hybrid(l, nu, g, snr / 100.0, CFG3['hybrid'], np.random.default_rng([SEED, frame, snr, 78]), return_estimate=True)
        rec['mae'][str(snr)] = dict(marker256=float(np.sum(p * np.abs(nh_m - nu)) / p.sum()), hybrid128=float(np.sum(p * np.abs(nh_h - nu)) / p.sum()))
        rec['cells'][f'{snr}|100|marker256'] = run_arm(C, obs, truth, (ls, [float(x) for x in nh_m], None))
        rec['cells'][f'{snr}|100|hybrid128'] = run_arm(C, obs, truth, (ls, [float(x) for x in nh_h], None))
        rec['cells'][f'{snr}|100|delay'] = run_arm(C, obs, truth, stageA.genie_inject(C, obs, truth))
    return [rec]


def run3(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'marker3_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job3, list(range(*CFG3['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'marker3_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG3, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read3(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'marker3_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); rng = np.random.default_rng(SEED + 10); snrs = CFG3['snrs']
    col = lambda key, f='CD': np.array([r['cells'][key][f] for r in rows], float)
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    arms = [(300, 'std'), (100, 'marker256'), (100, 'hybrid128'), (100, 'delay')]
    table = {f'{rho}|{name}': {str(s): dict(F0=int(col(f'{s}|{rho}|{name}', 'F0').sum()), CD=int(col(f'{s}|{rho}|{name}').sum())) for s in snrs} for rho, name in arms}
    pooled = lambda rho, name: sum(col(f'{s}|{rho}|{name}') for s in snrs)
    res = dict(frames=n, same_channel_all=bool(all(r.get('same_channel', False) for r in rows)),
               mae_w={str(s): {k: float(np.mean([r['mae'][str(s)][k] for r in rows])) for k in ('marker256', 'hybrid128')} for s in snrs}, table=table,
               pooled_cd={f'{rho}|{name}': int(pooled(rho, name).sum()) for rho, name in arms},
               hybrid_minus_marker256=boot(lambda ii: (pooled(100, 'hybrid128')[ii] - pooled(100, 'marker256')[ii]).sum()),
               hybrid_at4_minus_std_at5_pp=boot(lambda ii: 100 * (col('400|100|hybrid128')[ii] - col('500|300|std')[ii]).mean()),
               marker_at4_minus_std_at5_pp=boot(lambda ii: 100 * (col('400|100|marker256')[ii] - col('500|300|std')[ii]).mean()),
               hybrid_at35_minus_std_at5_pp=boot(lambda ii: 100 * (col('350|100|hybrid128')[ii] - col('500|300|std')[ii]).mean()),
               marker_at35_minus_std_at5_pp=boot(lambda ii: 100 * (col('350|100|marker256')[ii] - col('500|300|std')[ii]).mean()),
               marker_at3_minus_std_at5_pp=boot(lambda ii: 100 * (col('300|100|marker256')[ii] - col('500|300|std')[ii]).mean()))
    h = res['hybrid_minus_marker256']; one = res['hybrid_at4_minus_std_at5_pp']
    res['verdict_22l12'] = 'KILL' if h['point'] > 10 else 'PASS' if one['ci95'][1] <= 3.0 else 'UNDETERMINED'
    (out / 'marker3_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


CFG4 = dict(frames=[54000, 54200], scenario='G', gammas=[450, 500, 550], loss_hybrid128=89, loss_marker256=163,
            hybrid=dict(name='L128_sp10', L=128, G=0, rho=0.10))


def job4(frame):
    """Equal total transmit energy (gate request for 22-l08): the standard packet (prefix + data, rho = .25, the best
    standard point) at gamma, against packets with added end markers whose per-sample SNR is lowered by the energy the
    markers take: 128 + 128 samples -> 10 log10(1382 / 1126) = 0.89 dB, 256 + 256 -> 1.63 dB.  True delays still given.
    Criteria: PREDICTIONS_r3_batch12.md."""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; scen = CFG4['scenario']; rec = dict(frame=frame, cells={})
    for gam in CFG4['gammas']:
        raw0, obs0, truth0 = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 250), 250, gam)
        rec['cells'][f'{gam}|std25'] = run_arm(C, obs0, truth0, None)
        for name, loss in (('hybrid128', CFG4['loss_hybrid128']), ('marker256', CFG4['loss_marker256'])):
            snr = gam - loss
            raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, scen, 100), 100, snr)
            l = np.asarray(truth['l_i'], int); nu = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
            rec['same_channel'] = bool(rec.get('same_channel', True) and np.array_equal(l, np.asarray(truth0['l_i'], int)) and np.allclose(nu, truth0['k_real']))
            if name == 'hybrid128':
                nh = mk.one_hybrid(l, nu, g, snr / 100.0, CFG4['hybrid'], np.random.default_rng([SEED, frame, gam, 81]), return_estimate=True)
            else:
                nh = marker_doppler(l, nu, g, snr / 100.0, np.random.default_rng([SEED, frame, gam, 82]))
            rec['cells'][f'{gam}|{name}'] = run_arm(C, obs, truth, ([int(x) for x in l], [float(x) for x in nh], None))
    return [rec]


def run4(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'marker4_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job4, list(range(*CFG4['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'marker4_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG4, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read4(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'marker4_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); rng = np.random.default_rng(SEED + 12); gams = CFG4['gammas']
    col = lambda key, f='CD': np.array([r['cells'][key][f] for r in rows], float)
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    table = {name: {str(g): dict(F0=int(col(f'{g}|{name}', 'F0').sum()), CD=int(col(f'{g}|{name}').sum())) for g in gams} for name in ('std25', 'hybrid128', 'marker256')}
    pooled = lambda name: sum(col(f'{g}|{name}') for g in gams)
    res = dict(frames=n, same_channel_all=bool(all(r.get('same_channel', False) for r in rows)), table=table,
               pooled_cd={k: int(pooled(k).sum()) for k in ('std25', 'hybrid128', 'marker256')},
               hybrid128_minus_std25=boot(lambda ii: (pooled('hybrid128')[ii] - pooled('std25')[ii]).sum()),
               marker256_minus_std25=boot(lambda ii: (pooled('marker256')[ii] - pooled('std25')[ii]).sum()))
    h = res['hybrid128_minus_std25']
    res['verdict_equal_energy_hybrid128'] = 'NET_GAIN' if h['ci95'][1] < 0 else 'NET_LOSS' if h['ci95'][0] > 0 else 'NO_DIFFERENCE'
    (out / 'marker4_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def run(out):
    out.mkdir(parents=True, exist_ok=True); path = out / 'marker2_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, list(range(*CFG['frames']))):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    chd = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'marker2_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, workers=WORKERS), rows=nrow,
        core_hours=(chd.ru_utime + chd.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((chd.ru_utime + chd.ru_stime) / 3600, 3))


def read(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'marker2_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); rng = np.random.default_rng(SEED + 7); snrs = CFG['snrs']
    col = lambda key, f='CD': np.array([r['cells'][key][f] for r in rows], float)
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    table = {}
    for rho, names in ((300, ('std', 'marker')), (100, ('std', 'delay', 'marker')), (50, ('std', 'delay', 'marker'))):
        for name in names:
            table[f'{rho}|{name}'] = {str(s): dict(F0=int(col(f'{s}|{rho}|{name}', 'F0').sum()), CD=int(col(f'{s}|{rho}|{name}').sum())) for s in snrs}
        if rho != 300:
            table[f'{rho}|trueH'] = {str(s): dict(F0=int(col(f'{s}|{rho}|trueH', 'F0').sum())) for s in snrs}
    pooled = lambda rho, name: sum(col(f'{s}|{rho}|{name}') for s in snrs)
    A = pooled(300, 'std')
    res = dict(frames=n, same_channel_all=bool(all(r.get('same_channel', False) for r in rows)),
               marker_mae_w={str(s): float(np.mean([r['marker_mae_w'][str(s)] for r in rows])) for s in snrs}, table=table,
               pooled_cd={f'{rho}|{name}': int(pooled(rho, name).sum()) for rho, name in ((300, 'std'), (300, 'marker'), (100, 'std'), (100, 'delay'), (100, 'marker'), (50, 'std'), (50, 'delay'), (50, 'marker'))},
               same_snr_marker10_minus_std30=boot(lambda ii: (pooled(100, 'marker')[ii] - A[ii]).sum()),
               same_snr_marker05_minus_std30=boot(lambda ii: (pooled(50, 'marker')[ii] - A[ii]).sum()),
               same_snr_marker30_minus_std30=boot(lambda ii: (pooled(300, 'marker')[ii] - A[ii]).sum()),
               marker10_minus_delay10=boot(lambda ii: (pooled(100, 'marker')[ii] - pooled(100, 'delay')[ii]).sum()),
               one_db_marker10_at5_minus_std30_at6_pp=boot(lambda ii: 100 * (col('500|100|marker')[ii] - col('600|300|std')[ii]).mean()),
               one_db_marker10_at4_minus_std30_at5_pp=boot(lambda ii: 100 * (col('400|100|marker')[ii] - col('500|300|std')[ii]).mean()))
    a = res['same_snr_marker10_minus_std30']; b5 = res['one_db_marker10_at5_minus_std30_at6_pp']; b4 = res['one_db_marker10_at4_minus_std30_at5_pp']
    res['verdict'] = ('PASS_1DB' if b5['ci95'][1] <= 3.0 and b4['ci95'][1] <= 3.0 else 'PASS_GAIN' if a['ci95'][1] < 0 else 'KILL' if a['ci95'][0] >= 0 else 'UNDETERMINED')
    (out / 'marker2_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('smoke', 'run', 'read', 'run3', 'read3', 'run4', 'read4')); ap.add_argument('--out', default='out_r3b7'); a = ap.parse_args()
    if a.mode == 'smoke':
        t0 = time.process_time(); r = job(51000)[0]; print(json.dumps(r, indent=None)); print('cpu per frame', time.process_time() - t0)
    else:
        dict(run=run, read=read, run3=run3, read3=read3, run4=run4, read4=read4)[a.mode](HERE / a.out)
