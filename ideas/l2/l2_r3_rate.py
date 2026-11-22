#!/usr/bin/env python3
"""Idea-funnel local round 3, L2 check for card I-20261122-l16 (2026-11-22, runner l, claude-fable-5.2): the paper fixes the
code rate at 1/2; rerun the frozen receiver with (3,4), (3,6), (3,12) regular LDPC codes of the same length (rates 1/4, 1/2,
3/4) and read pilot-ratio optimum and "more rounds vs re-search" per rate.  Existing code only: the code object in the
context is replaced (ctx.code, ctx.H); generator, receiver and CODELAY branch are called unchanged.
Pattern of l2_r3_batch1.job_l05 (F0 then CD on failure); that job has no code swap and no extra-round arms.
Pre-registered criteria: ideas/l2/PREDICTIONS_r3_batch17.md.
  python l2_r3_rate.py gate|probe|run|read --out out_r3b17
"""
import argparse, gzip, json, os, resource, sys, time
from multiprocessing import get_context
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from l2_batch3 import setup, SEED, stageA  # noqa: E402

WORKERS = 12
CODE_SEED = 20260726
CFG = dict(frames=[58000, 58120], scenario='G', dcs=[4, 6, 12], rhos=[200, 250, 300, 400], true_rhos=[200, 300],
           snrs={'4': [50, 100, 150, 200], '6': [400, 450, 500, 550], '12': [800, 875, 950, 1050]})   # placed from the probe on frames 57992-57999
_CODES = {}


def code_for(C, dc, cache):
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    if dc not in _CODES:
        _CODES[dc] = build_code(2048, d_v=3, d_c=dc, seed=CODE_SEED, cache_dir=cache)
    ctx = C['ctx']; ctx.code = _CODES[dc]; ctx.H = np.asarray(ctx.code['H']).astype(np.int32)
    return ctx.code


def arms(C, obs, truth, with_true):
    import stageA2
    stage3, ctx = C['stage3'], C['ctx']; sc = lambda dec: int(stage3.e1.gd.score(ctx, dec, truth) > 0)
    dec, arrays, syn, _ = stageA.f0(C, obs); f0 = sc(dec['decoded']); out = dict(F0=f0, CD=f0, R3=f0, R5=f0, syn=int(syn > 0))
    if syn:
        br = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1'); out['CD'] = sc(br['decoder']['decoded'])
        d3, _, s3, _ = stage3.e1.receive_state(ctx, obs, 3); out['R3'] = sc(d3['decoded']); out['R5'] = out['R3']
        if s3:
            d5, _, _, _ = stage3.e1.receive_state(ctx, obs, 5); out['R5'] = sc(d5['decoded'])
    if with_true:
        dt, _, _, _ = stageA2.f0_true(C, obs, truth, 'true'); out['TH'] = sc(dt['decoded'])
    return out


def job(args):
    frame, cache, snrs, rhos = args
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; rec = dict(frame=frame, cells={}, chan={})
    for dc in CFG['dcs']:
        code = code_for(C, dc, cache); rec.setdefault('k', {})[str(dc)] = int(code['k'])
        for rho in rhos:
            base = stage3.inputs(ctx, frame, CFG['scenario'], rho)
            for snr in snrs[str(dc)]:
                raw, obs, truth = stage3.observed(ctx, base, rho, snr)
                rec['chan'].setdefault(str(rho), {})[str(dc)] = [float(np.sum(np.asarray(truth['l_i']))), float(np.sum(np.asarray(truth['k_real'])))]
                rec['cells'][f'{dc}|{rho}|{snr}'] = arms(C, obs, truth, rho in CFG['true_rhos'])
    return [rec]


LAD = dict(frames=[59000, 59120], rhos={'6': [250, 300], '12': [300, 400]},
           snrs={'6': [350, 400, 450, 500, 550], '12': [650, 725, 800, 875, 950, 1025]})   # criteria: PREDICTIONS_r3_batch19.md


def job_ladder(args):
    """Genie ladder per rate: standard (F0 then CD) / true delays given (F0 then CD) / true delays and Dopplers, gains by
    least squares (F0) / true channel start (F0).  Card draft: child of I-20261122-l16."""
    import stageA2
    frame, cache = args
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; rec = dict(frame=frame, cells={}); sc = lambda dec, truth: int(stage3.e1.gd.score(ctx, dec, truth) > 0)
    for dc in (6, 12):
        code_for(C, dc, cache)
        for rho in LAD['rhos'][str(dc)]:
            base = stage3.inputs(ctx, frame, CFG['scenario'], rho)
            for snr in LAD['snrs'][str(dc)]:
                raw, obs, truth = stage3.observed(ctx, base, rho, snr); out = {}
                for name, inj in (('STD', None), ('DEL', stageA.genie_inject(C, obs, truth))):
                    dec, arrays, syn, _ = stageA.f0(C, obs, inj); e = sc(dec['decoded'], truth); out[name + '_F0'] = e
                    if syn:
                        e = sc(stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')['decoder']['decoded'], truth)
                    out[name] = e
                out['DOP'] = sc(stageA2.f0_true(C, obs, truth, 'ls')[0]['decoded'], truth)
                out['TH'] = sc(stageA2.f0_true(C, obs, truth, 'true')[0]['decoded'], truth)
                rec['cells'][f'{dc}|{rho}|{snr}'] = out
    return [rec]


def run_ladder(out):
    cache = out / 'code-cache'; path = out / 'ladder_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job_ladder, [(f, str(cache)) for f in range(*LAD['frames'])]):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / 'ladder_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(LAD, scenario=CFG['scenario'], seed=SEED, code_seed=CODE_SEED, workers=WORKERS), rows=nrow,
        core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def crossing(snrs, errs, n, fer=0.10):
    """(value, censored): linear interpolation of log10(FER) between bracketing points; 0 errors -> 0.5 / n."""
    f = np.log10(np.maximum(np.asarray(errs, float), 0.5) / n); x = np.asarray(snrs, float) / 100; t = np.log10(fer)
    if f[0] < t:
        return float(x[0]), 'below'
    for i in range(len(x) - 1):
        if f[i] >= t >= f[i + 1]:
            return float(x[i] + (f[i] - t) / (f[i] - f[i + 1]) * (x[i + 1] - x[i])), None
    return float(x[-1]), 'above'


def read_ladder(out):
    rows = sorted([json.loads(x) for x in gzip.open(out / 'ladder_rows.jsonl.gz', 'rt')], key=lambda r: r['frame']); n = len(rows); rng = np.random.default_rng(SEED + 19)
    arms = ('STD', 'DEL', 'DOP', 'TH')
    E = {(dc, rho, a): np.array([[r['cells'][f'{dc}|{rho}|{s}'][a] for s in LAD['snrs'][dc]] for r in rows], float) for dc in ('6', '12') for rho in LAD['rhos'][dc] for a in arms}
    def cr(dc, rho, a, ii):
        return crossing(LAD['snrs'][dc], E[(dc, rho, a)][ii].sum(axis=0), len(ii))
    def loss(dc, ii):                       # best-rho standard receiver against the true-channel start with its pilot power removed
        std = min(cr(dc, rho, 'STD', ii)[0] for rho in LAD['rhos'][dc]); th = cr(dc, 300, 'TH', ii)[0] + 10 * np.log10(0.7)
        return std - th
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(2000)]
        return dict(point=float(pt), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    all_ = np.arange(n)
    res = dict(frames=n, errors={f'{dc}|{rho}|{a}': [int(x) for x in E[(dc, rho, a)].sum(axis=0)] for (dc, rho, a) in E},
               crossings={f'{dc}|{rho}|{a}': dict(zip(('db', 'censored'), cr(dc, rho, a, all_))) for (dc, rho, a) in E},
               loss_db={dc: boot(lambda ii, dc=dc: loss(dc, ii)) for dc in ('6', '12')}, loss_12_minus_6=boot(lambda ii: loss('12', ii) - loss('6', ii)))
    lad = {}
    for dc in ('6', '12'):
        c = {a: cr(dc, 300, a, all_) for a in arms}; tot = c['STD'][0] - c['TH'][0]
        lad[dc] = dict(std=c['STD'][0], delays=c['DEL'][0], delays_doppler=c['DOP'][0], true=c['TH'][0], total_db=tot, any_censored=bool(any(v[1] for v in c.values())),
                       share_support=(c['STD'][0] - c['DEL'][0]) / tot if tot > 0 else None, share_doppler=(c['DEL'][0] - c['DOP'][0]) / tot if tot > 0 else None,
                       share_gain=(c['DOP'][0] - c['TH'][0]) / tot if tot > 0 else None)
    res['ladder_rho30'] = lad
    d = res['loss_12_minus_6']; cens = any(res['crossings'][k]['censored'] for k in res['crossings'] if k.endswith('STD') or k in ('6|300|TH', '12|300|TH'))
    res['verdict'] = 'UNDETERMINED_CENSORED' if cens else 'PASS' if d['point'] >= 1.0 and d['ci95'][0] > 0.5 else 'KILL' if d['point'] < 0.5 else 'UNDETERMINED'
    (out / 'ladder_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def gate(out):
    """(a) rebuilt (3,6) code equals the context's code; (b) with it, F0 / CD decisions on one frame are bit-identical;
    (c) each rate decodes without error from the true channel at high SNR; (d) same channel across rates."""
    out.mkdir(parents=True, exist_ok=True); cache = out / 'code-cache'; cache.mkdir(exist_ok=True)
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; orig = ctx.code; res = {}
    base = stage3.inputs(ctx, 57990, 'G', 250); raw, obs, truth = stage3.observed(ctx, base, 250, 500)
    d0, a0, s0, _ = stageA.f0(C, obs); b0 = stage3.e1.run_branch(ctx, C['cd'], obs, a0, 'A1') if s0 else None
    new = code_for(C, 6, cache); res['H_equal'] = bool(np.array_equal(np.asarray(orig['H']), np.asarray(new['H']))); res['G_equal'] = bool(np.array_equal(np.asarray(orig['G']), np.asarray(new['G'])))
    base1 = stage3.inputs(ctx, 57990, 'G', 250); raw1, obs1, truth1 = stage3.observed(ctx, base1, 250, 500)
    d1, a1, s1, _ = stageA.f0(C, obs1); res['y_equal'] = bool(np.array_equal(obs['y'], obs1['y'])); res['f0_equal'] = bool(np.array_equal(d0['decoded'], d1['decoded']) and s0 == s1)
    if s0:
        b1 = stage3.e1.run_branch(ctx, C['cd'], obs1, a1, 'A1'); res['cd_equal'] = bool(np.array_equal(b0['decoder']['decoded'], b1['decoder']['decoded']))
    for dc, snr in ((4, 1500), (6, 1500), (12, 2500)):
        code = code_for(C, dc, cache); b = stage3.inputs(ctx, 57991, 'G', 300); r, o, t = stage3.observed(ctx, b, 300, snr)
        res[f'dc{dc}'] = dict(k=int(code['k']), rate=float(code['k'] / code['n']), **arms(C, o, t, True), l_sum=int(np.sum(t['l_i'])), k_sum=float(np.sum(t['k_real'])))
    (out / 'rate_gate.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def run_pool(out, frames, snrs, rhos, tag):
    out.mkdir(parents=True, exist_ok=True); cache = out / 'code-cache'; cache.mkdir(exist_ok=True)
    missing = [dc for dc in CFG['dcs'] if not (cache / f'e1_ldpc_code_n2048_dv3_dc{dc}_seed{CODE_SEED}.npz').exists()]
    if missing:                                   # the gate builds the three codes; workers only load them
        raise FileNotFoundError(f'run the gate first; codes missing for d_c = {missing}')
    path = out / f'{tag}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(job, [(f, str(cache), snrs, rhos) for f in frames]):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / f'{tag}_run.json').write_text(json.dumps(dict(_argv=sys.argv, _config=dict(CFG, seed=SEED, code_seed=CODE_SEED, workers=WORKERS, snrs_used=snrs, rhos_used=rhos, frames_used=[frames[0], frames[-1] + 1]),
        rows=nrow, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0), indent=1))
    os.system(f'gzip -n {path}'); print('rows', nrow, 'core-hours', round((ch.ru_utime + ch.ru_stime) / 3600, 3))


def table(rows, snrs, rhos):
    tab = {}
    for dc in CFG['dcs']:
        for rho in rhos:
            for snr in snrs[str(dc)]:
                c = [r['cells'][f'{dc}|{rho}|{snr}'] for r in rows]
                tab[f'{dc}|{rho}|{snr}'] = {a: int(sum(x[a] for x in c)) for a in ('F0', 'CD', 'R3', 'R5', 'TH') if a in c[0]}
    return tab


def read(out, tag='rate'):
    rows = sorted([json.loads(x) for x in gzip.open(out / f'{tag}_rows.jsonl.gz', 'rt')], key=lambda r: r['frame']); meta = json.loads((out / f'{tag}_run.json').read_text())
    snrs, rhos = meta['_config']['snrs_used'], meta['_config']['rhos_used']; n = len(rows); rng = np.random.default_rng(SEED + 17)
    res = dict(frames=n, k=rows[0]['k'], same_channel=bool(all(len({tuple(v) for v in r['chan'][str(rho)].values()}) == 1 for r in rows for rho in rhos)), table=table(rows, snrs, rhos))
    if tag != 'rate':
        (out / f'{tag}_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1)); return
    col = lambda dc, rho, snr, a: np.array([r['cells'][f'{dc}|{rho}|{snr}'][a] for r in rows], float)
    pooled = lambda dc, rho, a: sum(col(dc, rho, s, a) for s in snrs[str(dc)])
    def boot(fn):
        pt = fn(np.arange(n)); bs = [fn(rng.integers(0, n, n)) for _ in range(4000)]
        return dict(point=float(pt), ci95=[float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))])
    res['pooled'] = {f'{dc}|{rho}': {a: int(pooled(dc, rho, a).sum()) for a in ('F0', 'CD', 'R3', 'R5')} for dc in CFG['dcs'] for rho in rhos}
    # direction 1: advantage of re-search over equal-time extra rounds, as a share of the frames F0 fails, at rho in {.25, .30}
    def adv(dc):
        def f(ii):
            f0 = sum(pooled(dc, rho, 'F0')[ii].sum() for rho in (250, 300)); r3 = sum(pooled(dc, rho, 'R3')[ii].sum() for rho in (250, 300)); cd = sum(pooled(dc, rho, 'CD')[ii].sum() for rho in (250, 300))
            return (r3 - cd) / f0 if f0 > 0 else np.nan
        return f
    res['research_advantage'] = {str(dc): boot(adv(dc)) for dc in CFG['dcs']}
    res['adv_12_minus_6'] = boot(lambda ii: adv(12)(ii) - adv(6)(ii)); res['adv_6_minus_4'] = boot(lambda ii: adv(6)(ii) - adv(4)(ii))
    # direction 2: CD at rho = .25 against the better of rho = .30 / .40, pooled errors per frame-SNR, rate 3/4 against rate 1/2
    def pen(dc):
        return lambda ii: (pooled(dc, 250, 'CD')[ii].sum() - min(pooled(dc, 300, 'CD')[ii].sum(), pooled(dc, 400, 'CD')[ii].sum())) / (len(ii) * len(snrs[str(dc)]))
    res['rho25_penalty'] = {str(dc): boot(pen(dc)) for dc in CFG['dcs']}; res['rho25_penalty_12_minus_6'] = boot(lambda ii: pen(12)(ii) - pen(6)(ii))
    res['best_rho_cd'] = {str(dc): min(rhos, key=lambda rho: pooled(dc, rho, 'CD').sum()) for dc in CFG['dcs']}
    res['r5_floor_at_top_snr'] = {str(dc): {str(rho): int(col(dc, rho, snrs[str(dc)][-1], 'R5').sum()) for rho in rhos} for dc in CFG['dcs']}
    a1, a2, p = res['adv_12_minus_6'], res['adv_6_minus_4'], res['rho25_penalty_12_minus_6']
    d1 = a1['ci95'][0] > 0 and a2['point'] > 0; d2 = p['ci95'][0] > 0
    res['direction_1_research_advantage_grows_with_rate'] = bool(d1); res['direction_2_low_pilot_cliff_moves_right_at_high_rate'] = bool(d2)
    res['verdict'] = 'DIRECTION_PASS' if d1 and d2 else 'KILL'          # the card: either direction failing kills it
    (out / 'rate_summary.json').write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=('gate', 'probe', 'readprobe', 'run', 'read', 'ladder', 'readladder')); ap.add_argument('--out', default='out_r3b17'); a = ap.parse_args(); o = HERE / a.out
    if a.mode == 'gate':
        gate(o)
    elif a.mode == 'probe':        # frames outside the evaluation set, wide SNR grids, to place the four SNR points per rate
        run_pool(o, list(range(57992, 58000)), {'4': [-100, 0, 100, 200, 300, 450], '6': [450, 550], '12': [750, 900, 1050, 1200, 1350, 1500]}, [250, 300], 'probe')
    elif a.mode == 'readprobe':
        read(o, 'probe')
    elif a.mode == 'run':
        run_pool(o, list(range(*CFG['frames'])), CFG['snrs'], CFG['rhos'], 'rate')
    elif a.mode == 'ladder':
        run_ladder(o)
    elif a.mode == 'readladder':
        read_ladder(o)
    else:
        read(o)
