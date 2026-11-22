#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 batch 1 (2026-11-22, runner l, claude-fable-5.2).
  l05   card I-20261122-l05 (also decides the premise of I-20261122-l02 and the loss attribution in I-20261121-l12):
        same frames, data and noise; delay cap 102 / 240 / 400; superimposed pilot ZC root 7 vs random phase.
Source: ideas/l2/l2_r2_batch1.py (with_lmax, distinct_scaled_delays imported; job_l12 Part A is the pattern) and
ideas/l2/l2_20261121.py (pilot_seq imported).  job_l12 cannot be called as is: it fixes the pilot to ZC root 7.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch1.md.  No frozen receiver source file is modified.
  python l2_r3_batch1.py smoke|l05|read --out out_r3b1
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_r2_batch1 as r2  # noqa: E402
from l2_r2_batch1 import setup, SEED, stageA, scale_of, with_lmax, distinct_scaled_delays  # noqa: E402
from l2_20261121 import pilot_seq, support_stats  # noqa: E402

WORKERS = 12
TWIN_OFFSETS = (151, 210, 302, 361)  # delay offsets of the ZC-root-7 pilot twins for ctx.system (2*N*c1 = 5), from the card's table
CFG = dict(l05=dict(frames=[48000, 48200], scenario='G', rho=300, snrs=[500, 600, 700],
                    l_caps=[102, 240, 400], pilots=['zc7', 'rand']),
           # control arm asked for by the l12 gate (astra-gate-l12-20261122.md): paths stay within 102 taps, only the
           # search dictionary is widened to 400.  Same frames as l05 so the arms pair.  Criteria: PREDICTIONS_r3_batch2.md
           l12ctl=dict(frames=[48000, 48200], scenario='G', rho=300, snrs=[500, 600, 700], dict_cap=400, pilots=['zc7', 'rand']))


def eval_three(C, obs, truth, l_cap):
    import stageA2
    ctx, stage3 = C['ctx'], C['stage3']
    with with_lmax(C, l_cap):
        dec_t, _, _, _ = stageA2.f0_true(C, obs, truth, 'true')
        t_err = int(stage3.e1.gd.score(ctx, dec_t['decoded'], truth) > 0)
        dec, arrays, syn, _ = stageA.f0(C, obs)
        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth) > 0)
        cd_err = f0_err
        if syn:
            br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
            cd_err = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], truth) > 0)
    r0 = support_stats(arrays['r0_delays'], arrays['r0_dopplers'], truth, float(obs['sigma2']))
    l_true = set(int(x) for x in truth['l_i']); have = set(int(x) for x in arrays['r0_delays'])
    false_sel = have - l_true
    twin = sum(1 for d in false_sel if any(abs(d - l) in TWIN_OFFSETS for l in l_true))
    return dict(trueH=t_err, F0=f0_err, CD=cd_err, syn=int(syn), r0_right=int(r0['support_right']),
                r0_missing=float(r0['missing_power']), r0_found=len(l_true & have), r0_false=len(false_sel), r0_twin=int(twin))


def job_l05(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l05']
    from physical import Channel
    s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    rec = dict(frame=frame, cells={})
    base = stage3.inputs(ctx, frame, cfg['scenario'], cfg['rho'])
    for snr in cfg['snrs']:
        raw, obs, truth = stage3.observed(ctx, base, cfg['rho'], snr)
        n = len(obs['y']); sc = scale_of(raw, obs)
        p_zc = np.asarray(obs['pilot'], complex)
        d = np.asarray(raw['data'], complex) / sc
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'], complex)
        l0 = np.asarray(truth['l_i'], int); k0 = np.asarray(truth['k_real'], float); g0 = np.asarray(truth['g_i'], complex)
        for pname in cfg['pilots']:
            seq = pilot_seq(pname, n)
            p = p_zc if seq is None else np.sqrt(np.vdot(p_zc, p_zc).real / np.vdot(seq, seq).real) * seq
            for l_cap in cfg['l_caps']:
                l_sc = distinct_scaled_delays(l0, 102, l_cap)
                y = Channel(n, c1, c2, l_sc, k0, g0).apply(p + d) + w
                if pname == 'zc7' and l_cap == 102 and snr == cfg['snrs'][0]:
                    rec['gate_y102'] = float(np.linalg.norm(y - obs['y']) / np.linalg.norm(obs['y']))
                rec['cells'][f'{snr}|{pname}|{l_cap}'] = eval_three(C, dict(obs, y=y, pilot=p), dict(truth, l_i=l_sc), l_cap)
    return [rec]


def job_l12ctl(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l12ctl']
    from physical import Channel
    s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    rec = dict(frame=frame, cells={})
    base = stage3.inputs(ctx, frame, cfg['scenario'], cfg['rho'])
    for snr in cfg['snrs']:
        raw, obs, truth = stage3.observed(ctx, base, cfg['rho'], snr)
        n = len(obs['y']); sc = scale_of(raw, obs)
        p_zc = np.asarray(obs['pilot'], complex)
        d = np.asarray(raw['data'], complex) / sc
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'], complex)
        l0 = np.asarray(truth['l_i'], int); k0 = np.asarray(truth['k_real'], float); g0 = np.asarray(truth['g_i'], complex)
        for pname in cfg['pilots']:
            seq = pilot_seq(pname, n)
            p = p_zc if seq is None else np.sqrt(np.vdot(p_zc, p_zc).real / np.vdot(seq, seq).real) * seq
            y = Channel(n, c1, c2, l0, k0, g0).apply(p + d) + w        # delays NOT stretched
            if pname == 'zc7' and snr == cfg['snrs'][0]:
                rec['gate_y102'] = float(np.linalg.norm(y - obs['y']) / np.linalg.norm(obs['y']))
            rec['cells'][f'{snr}|{pname}|short_wide'] = eval_three(C, dict(obs, y=y, pilot=p), truth, cfg['dict_cap'])
    return [rec]


def job_genie(frame):
    """Long paths (stretched to cap 400), wide re-search bank, but round 0 is handed the true delays (what a preamble
    would give, card c14); Doppler start = best integer bin per true delay from the pilot.  Criteria: PREDICTIONS_r3_batch5.md"""
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l05']; import stageA2
    from physical import Channel, regressors
    s = ctx.system; c1, c2 = float(s.c1), float(s.c2); l_cap = 400
    rec = dict(frame=frame, cells={})
    base = stage3.inputs(ctx, frame, cfg['scenario'], cfg['rho'])
    for snr in cfg['snrs']:
        raw, obs, truth = stage3.observed(ctx, base, cfg['rho'], snr)
        n = len(obs['y']); sc = scale_of(raw, obs)
        p_zc = np.asarray(obs['pilot'], complex)
        d = np.asarray(raw['data'], complex) / sc
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'], complex)
        l0 = np.asarray(truth['l_i'], int); k0 = np.asarray(truth['k_real'], float); g0 = np.asarray(truth['g_i'], complex)
        l_sc = distinct_scaled_delays(l0, 102, l_cap)
        for pname in cfg['pilots']:
            seq = pilot_seq(pname, n)
            p = p_zc if seq is None else np.sqrt(np.vdot(p_zc, p_zc).real / np.vdot(seq, seq).real) * seq
            y = Channel(n, c1, c2, l_sc, k0, g0).apply(p + d) + w
            o = dict(obs, y=y, pilot=p); t = dict(truth, l_i=l_sc)
            ls = [int(x) for x in l_sc]
            U = regressors(p, np.repeat(ls, 5), np.tile(np.arange(-2, 3), len(ls)).astype(float), c1, c2)
            z5 = (np.abs(U.conj().T @ y) ** 2).reshape(len(ls), 5)
            inject = (ls, [int(np.argmax(z5[i])) - 2 for i in range(len(ls))], None)
            with with_lmax(C, l_cap):
                ext = ctx.native.pilot_front          # the widened front; stageA.f0(inject=...) would call the frozen 515-column one

                def front(observed, system, code, ext=ext, inject=inject):
                    s0 = ext(observed, system, code)
                    return dict(s0, delays=np.asarray(inject[0], int), dopplers=np.asarray(inject[1], float),
                                gains=np.ones(len(inject[0]), complex))
                ctx.native.pilot_front = front
                try:
                    dec, arrays, syn, _ = stage3.e1.f0_state(ctx, o)
                finally:
                    ctx.native.pilot_front = ext
                f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], t) > 0); cd_err = f0_err
                if syn:
                    br = stage3.e1.run_branch(ctx, C['cd'], o, arrays, 'A1')
                    cd_err = int(stage3.e1.gd.score(ctx, br['decoder']['decoded'], t) > 0)
            have = set(int(x) for x in arrays['r0_delays'])
            rec['cells'][f'{snr}|{pname}|long_genie'] = dict(F0=f0_err, CD=cd_err, syn=int(syn), r0_found=len(set(ls) & have), r0_n=len(have))
    return [rec]


def smoke(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    C = setup(); ctx = C['ctx']; s = ctx.system
    t0 = time.process_time(); r = job_l05(CFG['l05']['frames'][0])[0]; t = time.process_time() - t0
    res = dict(c1_times_2048=float(2048 * s.c1), l_max_cap=int(s.l_max_cap),
               gate_y102=r['gate_y102'], cpu_per_frame=t, est_core_hours=t * 200 / 3600, sample=r['cells'])
    if not r['gate_y102'] < 1e-11:
        raise AssertionError(f'smoke gate failed: {res}')
    (out / 'smoke.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def run_task(mode, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    path = out / f'{mode}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    frames = list(range(*CFG['l05' if mode == 'genie' else mode]['frames']))
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(dict(l05=job_l05, l12ctl=job_l12ctl, genie=job_genie)[mode], frames):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv, mode=mode, _config=CFG['l05' if mode == 'genie' else mode], seed=SEED, workers=WORKERS, twin_offsets=TWIN_OFFSETS,
                rows=nrow, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0)
    (out / f'{mode}_run.json').write_text(json.dumps(meta, indent=1))
    os.system(f'gzip -n {path}')
    print(mode, 'rows', nrow, 'core-hours', round(meta['core_hours'], 3), 'wall', round(meta['wall_seconds'], 1))


def read_all(out):
    out = Path(out); rng = np.random.default_rng(SEED); cfg = CFG['l05']
    rows = sorted([json.loads(x) for x in gzip.open(out / 'l05_rows.jsonl.gz', 'rt')], key=lambda r: r['frame'])
    n = len(rows); snrs, caps, pilots = cfg['snrs'], cfg['l_caps'], cfg['pilots']
    arr = lambda key, snr, p, cap: np.array([r['cells'][f'{snr}|{p}|{cap}'][key] for r in rows], float)
    table = {}
    for p in pilots:
        for cap in caps:
            table[f'{p}|{cap}'] = {str(snr): dict(
                trueH=int(arr('trueH', snr, p, cap).sum()), F0=int(arr('F0', snr, p, cap).sum()), CD=int(arr('CD', snr, p, cap).sum()),
                r0_right=float(arr('r0_right', snr, p, cap).mean()), r0_found_mean=float(arr('r0_found', snr, p, cap).mean()),
                frames_with_twin=float((arr('r0_twin', snr, p, cap) > 0).mean()), r0_false_mean=float(arr('r0_false', snr, p, cap).mean()))
                for snr in snrs}
    pooled = lambda key, p, cap: sum(arr(key, snr, p, cap) for snr in snrs)          # per-frame count over the three SNRs
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    base = pooled('CD', 'zc7', 102)
    res = dict(frames=n, gate_y102_max=max(r['gate_y102'] for r in rows), table=table, paired={})
    for cap in (240, 400):
        zc, rd = pooled('CD', 'zc7', cap), pooled('CD', 'rand', cap)
        res['paired'][str(cap)] = dict(
            cd_errors_zc_minus_rand=boot(lambda ii: (zc[ii] - rd[ii]).sum()),
            excess_zc=boot(lambda ii: (zc[ii] - base[ii]).sum()), excess_rand=boot(lambda ii: (rd[ii] - base[ii]).sum()),
            recovered_fraction=boot(lambda ii: 1 - (rd[ii] - base[ii]).sum() / max((zc[ii] - base[ii]).sum(), 1e-9)),
            f0_errors_zc_minus_rand=boot(lambda ii: (pooled('F0', 'zc7', cap)[ii] - pooled('F0', 'rand', cap)[ii]).sum()))
    a, b = arr('CD', 600, 'rand', 400), arr('CD', 500, 'zc7', 102)
    res['db_reading_rand400_at6_minus_zc102_at5_pp'] = boot(lambda ii: 100 * (a[ii] - b[ii]).mean())
    a7, b6 = arr('CD', 700, 'rand', 400), arr('CD', 600, 'zc7', 102)
    res['db_reading_rand400_at7_minus_zc102_at6_pp'] = boot(lambda ii: 100 * (a7[ii] - b6[ii]).mean())
    res['parity_cap102_cd_rand_minus_zc'] = boot(lambda ii: (pooled('CD', 'rand', 102)[ii] - base[ii]).sum())
    res['trueH_rand_minus_zc_total'] = {str(cap): int((pooled('trueH', 'rand', cap) - pooled('trueH', 'zc7', cap)).sum()) for cap in caps}
    rf = res['paired']['400']['recovered_fraction']
    res['verdict'] = ('PASS' if rf['point'] >= 0.5 and rf['ci95'][0] > 0.25 and res['db_reading_rand400_at6_minus_zc102_at5_pp']['ci95'][1] <= 3.0
                      else 'KILL' if rf['point'] < 0.25 or rf['ci95'][1] < 0.5 else 'UNDETERMINED')
    (out / 'summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def read_ctl(out):
    out = Path(out); rng = np.random.default_rng(SEED + 1); snrs = CFG['l05']['snrs']
    a = {r['frame']: r for r in (json.loads(x) for x in gzip.open(out / 'l05_rows.jsonl.gz', 'rt'))}
    b = {r['frame']: r for r in (json.loads(x) for x in gzip.open(out / 'l12ctl_rows.jsonl.gz', 'rt'))}
    frames = sorted(set(a) & set(b)); n = len(frames)
    def pooled(rows, key, tag):
        return np.array([sum(rows[f]['cells'][f'{snr}|{tag}'][key] for snr in snrs) for f in frames], float)
    arms = {'zc_short_narrow': pooled(a, 'CD', 'zc7|102'), 'rand_short_narrow': pooled(a, 'CD', 'rand|102'),
            'zc_long_wide': pooled(a, 'CD', 'zc7|400'), 'rand_long_wide': pooled(a, 'CD', 'rand|400'),
            'zc_short_wide': pooled(b, 'CD', 'zc7|short_wide'), 'rand_short_wide': pooled(b, 'CD', 'rand|short_wide')}
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    E = lambda k: (lambda ii: arms[k][ii].sum())
    res = dict(frames=n, gate_y102_max=max(b[f]['gate_y102'] for f in frames),
               cd_errors={k: int(v.sum()) for k, v in arms.items()},
               per_snr={tag: {str(snr): dict(trueH=int(sum(b[f]['cells'][f'{snr}|{tag}|short_wide']['trueH'] for f in frames)),
                                              F0=int(sum(b[f]['cells'][f'{snr}|{tag}|short_wide']['F0'] for f in frames)),
                                              CD=int(sum(b[f]['cells'][f'{snr}|{tag}|short_wide']['CD'] for f in frames)),
                                              frames_with_twin=float(np.mean([b[f]['cells'][f'{snr}|{tag}|short_wide']['r0_twin'] > 0 for f in frames])),
                                              r0_found_mean=float(np.mean([b[f]['cells'][f'{snr}|{tag}|short_wide']['r0_found'] for f in frames])))
                              for snr in snrs} for tag in ('zc7', 'rand')},
               dict_only_rand=boot(lambda ii: (arms['rand_short_wide'][ii] - arms['zc_short_narrow'][ii]).sum()),
               dict_plus_twin_zc=boot(lambda ii: (arms['zc_short_wide'][ii] - arms['zc_short_narrow'][ii]).sum()),
               twin_at_short=boot(lambda ii: (arms['zc_short_wide'][ii] - arms['rand_short_wide'][ii]).sum()),
               stretch_rand=boot(lambda ii: (arms['rand_long_wide'][ii] - arms['rand_short_wide'][ii]).sum()),
               stretch_zc=boot(lambda ii: (arms['zc_long_wide'][ii] - arms['zc_short_wide'][ii]).sum()),
               dict_share_of_rand_residual=boot(lambda ii: (arms['rand_short_wide'][ii] - arms['zc_short_narrow'][ii]).sum()
                                                / max((arms['rand_long_wide'][ii] - arms['zc_short_narrow'][ii]).sum(), 1e-9)))
    (out / 'summary_l12ctl.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def read_genie(out):
    out = Path(out); rng = np.random.default_rng(SEED + 2); snrs = CFG['l05']['snrs']
    a = {r['frame']: r for r in (json.loads(x) for x in gzip.open(out / 'l05_rows.jsonl.gz', 'rt'))}
    g = {r['frame']: r for r in (json.loads(x) for x in gzip.open(out / 'genie_rows.jsonl.gz', 'rt'))}
    frames = sorted(set(a) & set(g)); n = len(frames)
    pooled = lambda rows, key, tag: np.array([sum(rows[f]['cells'][f'{snr}|{tag}'][key] for snr in snrs) for f in frames], float)
    arms = {'zc_short_narrow': pooled(a, 'CD', 'zc7|102'), 'zc_long_wide': pooled(a, 'CD', 'zc7|400'), 'rand_long_wide': pooled(a, 'CD', 'rand|400'),
            'zc_long_genie': pooled(g, 'CD', 'zc7|long_genie'), 'rand_long_genie': pooled(g, 'CD', 'rand|long_genie')}
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    res = dict(frames=n, cd_errors={k: int(v.sum()) for k, v in arms.items()},
               per_snr={tag: {str(snr): dict(F0=int(sum(g[f]['cells'][f'{snr}|{tag}|long_genie']['F0'] for f in frames)),
                                              CD=int(sum(g[f]['cells'][f'{snr}|{tag}|long_genie']['CD'] for f in frames)),
                                              r0_found_mean=float(np.mean([g[f]['cells'][f'{snr}|{tag}|long_genie']['r0_found'] for f in frames])))
                              for snr in snrs} for tag in ('zc7', 'rand')},
               genie_zc_minus_baseline=boot(lambda ii: (arms['zc_long_genie'][ii] - arms['zc_short_narrow'][ii]).sum()),
               genie_rand_minus_baseline=boot(lambda ii: (arms['rand_long_genie'][ii] - arms['zc_short_narrow'][ii]).sum()),
               zc_wide_minus_genie=boot(lambda ii: (arms['zc_long_wide'][ii] - arms['zc_long_genie'][ii]).sum()),
               rand_wide_minus_genie=boot(lambda ii: (arms['rand_long_wide'][ii] - arms['rand_long_genie'][ii]).sum()))
    (out / 'summary_genie.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['smoke', 'l05', 'read', 'l12ctl', 'readctl', 'genie', 'readgenie']); ap.add_argument('--out', default='out_r3b1')
    a = ap.parse_args()
    for v in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ.setdefault(v, '1')
    {'smoke': smoke, 'l05': lambda o: run_task('l05', o), 'read': read_all, 'l12ctl': lambda o: run_task('l12ctl', o), 'readctl': read_ctl, 'genie': lambda o: run_task('genie', o), 'readgenie': read_genie}[a.mode](HERE / a.out)
