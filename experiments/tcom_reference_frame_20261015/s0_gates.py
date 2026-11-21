#!/usr/bin/env python
"""S0 gates for gen_fixed.py (task 10-15-tcom-reference-frame, protocol.md section 2).

Run on deinlab, single thread (launch_s0.sh).  Stages (each writes out/s0/<stage>*.json):
  numax  estimate nu_max = 99% quantile of |k_real| under the frozen UWA law (draws of the frozen
         generate_uwa_channel); the value is then frozen as gen_fixed.UWA_NU_MAX_99.
  a      G-S0a  flags off: frames 0..999 bit-identical to the frozen headroom driver.generate_base  (sharded).
  b      G-S0b  D1+D2: same-delay stacking vs natural rate (MC), delay-span KS vs direct rejection sampler,
                truncation rate; geometric-law report.
  c      G-S0c  20 frames x 5 configurations (off, D1+D2, D1+D2+geo, +fix_energy U / G): observation vs direct CPP
                propagation, prefix >= max delay.
  d      G-S0d  (amendment A1) fix_energy on, U and G: per-frame physical energy ||H||_F^2/N = 1 to 1e-9 (200 frames each).
  smoke  frozen F0+CSTATE receiver (headroom driver.run_a0) on 8 frames x 5 configurations at 7 dB, rho .5.
  merge  collect everything into out/s0/gates.json + GATES.md.
Nothing frozen is edited; the frozen headroom driver is imported as a module.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
HEADROOM = PROJECT / 'experiments' / 'headroom_ladder_20261008'
OUT = HERE / 'out' / 's0'
# any 256-bit test entropy; generated 2026-10-15 with secrets.token_hex(32); used for S0 only (never for P1)
TEST_ENTROPY = '6f264a9a7ac4efe09a742cd9e632450d198774183a087833e07a2b8816db5fe2'
STATED_LAW = dict(P_paths=8, tau_mean=0.8e-3, fs=16000.0, tau_spread=10e-3, v_mean=2.0, v_std=0.5, N_total=1024)
CONFIGS = ('off', 'd12', 'd12geo', 'd12e', 'd12egeo')

sys.path.insert(0, str(HERE))
import gen_fixed  # noqa: E402
from gen_fixed import Flags  # noqa: E402


def config_flags(name):
    return {'off': Flags(), 'd1': Flags(fix_delay_cap=True), 'd2': Flags(fix_delay_grid=True),
            'd12': Flags(True, True), 'd12geo': Flags(True, True, 'geometric'),
            'd12e': Flags(True, True, 'uwa', True), 'd12egeo': Flags(True, True, 'geometric', True)}[name]


# ----------------------------------------------------------------------------- helpers
def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def to_jsonable(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value))


def load_headroom():
    spec = importlib.util.spec_from_file_location('headroom_driver', HEADROOM / 'driver.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def get_context():
    hd = load_headroom()
    args = hd.parse_args(['--mode', 'generate', '--out', str(OUT), '--project', str(PROJECT)])
    ctx = hd.load_context(args)
    return hd, ctx


def provenance(args, ctx):
    import scipy
    return dict(_argv=list(sys.argv), _config=dict(
        args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        test_entropy=TEST_ENTROPY, stated_law=STATED_LAW, nu_max_99_constant=gen_fixed.UWA_NU_MAX_99,
        receiver_bank_max_delay=gen_fixed.RECEIVER_BANK_MAX_DELAY,
        versions=dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__),
        frozen_source_sha256=ctx.sources, environment=ctx.environment),
        _code_md5=dict(gen_fixed=md5_file(HERE / 'gen_fixed.py'), s0_gates=md5_file(HERE / 's0_gates.py')))


def write_json(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=1, sort_keys=True, default=to_jsonable, allow_nan=False) + '\n')
    print('wrote', path, flush=True)


def check_system_matches_stated_law(system):
    got = dict(P_paths=system.P_paths, tau_mean=system.tau_mean, fs=system.fs, tau_spread=system.tau_spread,
               v_mean=system.v_mean, v_std=system.v_std, N_total=system.N_total)
    if got != STATED_LAW:
        raise AssertionError(f'system differs from the stated law: {got} vs {STATED_LAW}')


# ----------------------------------------------------------------------------- numax
def stage_numax(args, hd, ctx):
    from scipy import optimize, stats
    s = ctx.system
    n = int(s.N_total)
    k_clip = min(s.k_max_cap, int(np.floor(n / 2) - s.k_guard - 1))
    blocks, per = 20, args.frames // 20
    np.random.seed(20261015)  # numax stage only; the frozen method draws from the global generator
    block_q, pooled = [], []
    t0 = time.time()
    for _ in range(blocks):
        ks = []
        for _ in range(per):
            _bar, _g, _idx, _pv, doppler_a, _vel, _att = s.generate_uwa_channel()
            k = np.clip((doppler_a * s.fc / s.fs) * n, -float(k_clip), float(k_clip))
            ks.append(np.abs(k))
        ks = np.concatenate(ks)
        block_q.append(float(np.quantile(ks, .99)))
        pooled.append(ks)
    pooled = np.concatenate(pooled)
    q = float(np.quantile(pooled, .99))
    se_blocks = float(np.std(block_q, ddof=1) / np.sqrt(blocks))
    factor = s.fc / (s.c_sound * s.fs) * n
    folded = lambda v: stats.norm.cdf((v - s.v_mean) / s.v_std) - stats.norm.cdf((-v - s.v_mean) / s.v_std) - .99  # noqa: E731
    v99 = float(optimize.brentq(folded, 0.5, 10.))
    payload = provenance(args, ctx)
    payload.update(stage='numax', n_frames=blocks * per, n_paths=int(pooled.size), seconds=time.time() - t0,
                   nu_max_99_pooled=q, nu_max_99_rounded3=round(q, 3), mc_se_block_quantiles=se_blocks,
                   block_quantiles=block_q, analytic_folded_normal_99=float(v99 * factor), k_per_ms=float(factor),
                   k_clip=int(k_clip), fraction_clipped=float(np.mean(pooled >= k_clip - 1e-12)),
                   mean_abs_k=float(pooled.mean()), sd_abs_k=float(pooled.std()))
    write_json('numax.json', payload)
    print(f'nu_max_99 pooled={q:.5f} +- {se_blocks:.5f} (blocks), analytic={v99 * factor:.5f}', flush=True)


# ----------------------------------------------------------------------------- G-S0a
A_KEYS = ('l_i', 'k_real', 'g_i')


def equal(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return bool(a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a, b))


def compare_frames(raw_f, diag_f, raw_n, diag_n):
    res = {}
    for key in A_KEYS:
        res[key] = equal(raw_f['params'][key], raw_n['params'][key])
    ref_f, ref_n = raw_f['g0_reference']['params'], raw_n['g0_reference']['params']
    if set(ref_f) != set(ref_n):
        raise AssertionError('params key sets differ')
    for key in sorted(ref_f):
        res['g0.' + key] = equal(ref_f[key], ref_n[key])
    res['physical_gains_sha256'] = diag_f['physical_gains_sha256'] == diag_n['physical_gains_sha256']
    for key in ('H', 'noiseless', 'y', 'info', 'coded', 'data', 'noise', 'pilot', 'sigma2', 'channel_seed'):
        res['raw.' + key] = equal(raw_f[key], raw_n[key])
    res['raw.g0_H'] = equal(raw_f['g0_reference']['H'], raw_n['g0_reference']['H'])
    return res


def triple_sha(params):
    h = hashlib.sha256()
    for key in A_KEYS:
        a = np.ascontiguousarray(params[key])
        h.update(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes())
    return h.hexdigest()


def stage_a(args, hd, ctx):
    seed_fn = lambda frame, component: hd.seed_words(TEST_ENTROPY, frame, component)  # noqa: E731
    cells = [(f, .5) for f in range(args.frames)] + [(f, .3) for f in range(args.rho3_frames)]
    mine = cells[args.shard::args.nshard]
    rows = []
    t0 = time.time()
    for frame, rho in mine:
        t = time.perf_counter()
        raw_f, diag_f = hd.generate_base(ctx, rho, 7.0, frame, seed_fn)
        t_f = time.perf_counter() - t
        t = time.perf_counter()
        raw_n, diag_n = gen_fixed.generate_base(ctx, rho, 7.0, frame, seed_fn, gen_fixed.FLAGS_OFF)
        t_n = time.perf_counter() - t
        cmp = compare_frames(raw_f, diag_f, raw_n, diag_n)
        sha_f, sha_n = triple_sha(raw_f['params']), triple_sha(raw_n['params'])
        rows.append(dict(frame=frame, rho=rho, all_equal=bool(all(cmp.values())),
                         triple_equal=bool(all(cmp[k] for k in A_KEYS)), triple_sha256_frozen=sha_f,
                         triple_sha256_fixed=sha_n, failed=[k for k, v in cmp.items() if not v],
                         resample_attempts=int(raw_f['g0_reference']['params']['resample_attempts']),
                         max_l=int(raw_f['params']['l_i'].max()), seconds_frozen=t_f, seconds_fixed=t_n))
        print(f'[{time.time() - t0:7.1f}s] frame={frame} rho={rho} equal={rows[-1]["all_equal"]}', flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='a', shard=args.shard, nshard=args.nshard, rows=rows)
    write_json(f'a_shard{args.shard:03d}.json', payload)


# ----------------------------------------------------------------------------- G-S0b
def mc_draw(system, flags, n, seed, *, natural=False):
    """n frames of path draws (no channel matrix).  natural=True: a single attempt, no cap, no clip."""
    P = int(system.P_paths)
    rs = np.random.RandomState(seed)
    geo = np.random.default_rng(seed + 1)
    flags_u, flags_g = Flags(doppler_law='uwa'), Flags(doppler_law='geometric')
    L = np.empty((n, P), int)
    Ku, Kg = np.empty((n, P)), np.empty((n, P))
    attempts = np.ones(n, int)
    fallback = np.zeros(n, bool)
    for i in range(n):
        if natural:
            d = gen_fixed.one_attempt(system, rs, flags)
        else:
            d = gen_fixed.draw_paths(system, rs, flags)
            attempts[i], fallback[i] = d['attempts'], d['fallback']
        L[i] = gen_fixed.delay_bins(system, d['delay_idx_bar'], flags, clip=not natural)
        Ku[i] = gen_fixed.doppler_k_real(system, d['doppler_a'], flags_u, None)
        Kg[i] = gen_fixed.doppler_k_real(system, d['doppler_a'], flags_g, geo)
    return dict(L=L, Ku=Ku, Kg=Kg, attempts=attempts, fallback=fallback)


def stacking(L):
    return (np.diff(np.sort(L, axis=1), axis=1) == 0).any(axis=1)


def rate_row(mask):
    n = int(mask.size)
    p = float(mask.mean())
    return dict(n=n, k=int(mask.sum()), rate=p, se=float(np.sqrt(p * (1 - p) / n)))


def compare_rates(a, b):
    """Difference of two stacking rates against 3 pooled standard errors (equal rates pass trivially)."""
    p = (a['k'] + b['k']) / (a['n'] + b['n'])
    se = float(np.sqrt(p * (1 - p) * (1 / a['n'] + 1 / b['n'])))
    diff = a['rate'] - b['rate']
    return dict(diff=diff, se_pooled=se, z=(diff / se if se > 0 else 0.0),
                within_3se=bool(diff == 0 or abs(diff) <= 3 * se))


def direct_sampler(n_accept, seed, cap_l):
    """Independent rejection sampler of the stated delay law (D2 grid: bin = sample index - 1)."""
    law = STATED_LAW
    ts = 1.0 / law['fs']
    rng = np.random.default_rng(seed)
    spans, maxes, tried = [], [], 0
    got = 0
    while got < n_accept:
        m = 200000
        inc = np.maximum(1, np.ceil(rng.exponential(law['tau_mean'], size=(m, law['P_paths'])) / ts).astype(np.int64))
        l = np.cumsum(inc, axis=1) - 1
        ok = l.max(axis=1) <= cap_l
        tried += m
        spans.append((l.max(axis=1) - l.min(axis=1))[ok])
        maxes.append(l.max(axis=1)[ok])
        got += int(ok.sum())
    spans, maxes = np.concatenate(spans), np.concatenate(maxes)
    return spans[:n_accept], maxes[:n_accept], tried, int(len(spans))


def pair_stats(L, K):
    """Within-frame pair statistics: P(|dk| <= 1) over all pairs and over same-delay pairs."""
    P = L.shape[1]
    all_close, same_close, n_all, n_same = 0, 0, 0, 0
    for i in range(P):
        for j in range(i + 1, P):
            close = np.abs(K[:, i] - K[:, j]) <= 1.0
            same = L[:, i] == L[:, j]
            all_close += int(close.sum())
            n_all += close.size
            same_close += int((close & same).sum())
            n_same += int(same.sum())
    return dict(pairs_all=n_all, frac_within_1bin_all_pairs=all_close / n_all, pairs_same_delay=n_same,
                frac_within_1bin_same_delay=(same_close / n_same if n_same else None))


def doppler_summary(K):
    a = np.abs(K).ravel()
    return dict(n_paths=int(K.size), frac_positive=float((K > 0).mean()), mean=float(K.mean()), sd=float(K.std()),
                abs_quantiles={str(q): float(np.quantile(a, q)) for q in (.1, .5, .9, .99, 1.0)},
                min=float(K.min()), max=float(K.max()))


def stage_b(args, hd, ctx):
    from scipy import stats
    s = ctx.system
    check_system_matches_stated_law(s)
    n, n_slow = args.mc_frames, args.mc_frames_frozen
    t0 = time.time()
    runs = {}
    plan = [('natural_d1grid', Flags(), n, True), ('natural_d2grid', Flags(fix_delay_grid=True), n, True),
            ('off', Flags(), n_slow, False), ('d2', Flags(fix_delay_grid=True), n_slow, False),
            ('d1', Flags(fix_delay_cap=True), n, False), ('d12', Flags(True, True), n, False)]
    for i, (name, flags, count, natural) in enumerate(plan):
        runs[name] = mc_draw(s, flags, count, args.seed + 10 * i, natural=natural)
        print(f'[{time.time() - t0:7.1f}s] mc {name} done', flush=True)
    stack = {k: rate_row(stacking(v['L'])) for k, v in runs.items()}
    # (i) stacking rate: D1+D2 vs the natural rate of the same grid with no cap at all (gate), D1 alone informational
    cmp_d12 = compare_rates(stack['d12'], stack['natural_d2grid'])
    cmp_d1 = compare_rates(stack['d1'], stack['natural_d1grid'])
    gate_i = bool(cmp_d12['within_3se'])
    # strictly increasing delay indices => no stacking is structural under the D2 grid
    structural = {k: bool((np.diff(runs[k]['L'], axis=1) > 0).all()) for k in ('natural_d2grid', 'd12')}
    # (ii) delay span / max-delay law vs direct rejection sampler
    L = runs['d12']['L']
    span_g, max_g = L.max(1) - L.min(1), L.max(1)
    span_d, max_d, tried, accepted_direct = direct_sampler(len(L), args.seed + 999, gen_fixed.RECEIVER_BANK_MAX_DELAY)
    ks_span = stats.ks_2samp(span_g, span_d)
    ks_max = stats.ks_2samp(max_g, max_d)
    gate_ii = bool(ks_span.pvalue > .01)
    # (iii) truncation rate
    att = runs['d12']['attempts']
    att1 = runs['d1']['attempts']
    off = runs['off']
    accept_direct = accepted_direct / tried
    accept_gen = len(att) / att.sum()
    se_acc = float(np.sqrt(accept_direct * (1 - accept_direct) / tried + accept_gen * (1 - accept_gen) / att.sum()))
    trunc = dict(d12=dict(first_try_acceptance=accept_gen, redraws_per_frame=float(att.mean() - 1),
                          redraw_rate_truncation=1 - accept_gen, max_attempts=int(att.max()),
                          direct_sampler_acceptance=accept_direct, z_vs_direct=(accept_gen - accept_direct) / se_acc),
                 d1_only=dict(first_try_acceptance=len(att1) / att1.sum(), redraws_per_frame=float(att1.mean() - 1)),
                 frozen=dict(first_try_acceptance=float((off['attempts'] == 1).mean()),
                             mean_attempts=float(off['attempts'].mean()),
                             clip_fallback_fraction=float(off['fallback'].mean())),
                 cap_idx=dict(frozen=gen_fixed.effective_grid(s, Flags())['cap_idx_frozen'],
                              d1_grid_frozen=gen_fixed.effective_grid(s, Flags(fix_delay_cap=True))['cap_idx_fixed'],
                              d1_d2_grid=gen_fixed.effective_grid(s, Flags(True, True))['cap_idx_fixed']))
    # equivalence of the cap formula and the explicit l-bin truncation
    cap_equiv = {}
    for name, flags in (('d1', Flags(fix_delay_cap=True)), ('d12', Flags(True, True))):
        cap = gen_fixed.effective_grid(s, flags)['cap_idx_fixed']
        idx = np.arange(1, 400)
        by_idx = idx <= cap
        by_bin = gen_fixed.delay_bins(s, idx, flags, clip=False) <= gen_fixed.RECEIVER_BANK_MAX_DELAY
        cap_equiv[name] = bool(np.array_equal(by_idx, by_bin))
    # Doppler laws
    dop = {}
    for tag, K, Lx in (('uwa_d12', runs['d12']['Ku'], runs['d12']['L']), ('geometric_d12', runs['d12']['Kg'], runs['d12']['L']),
                       ('uwa_d1only', runs['d1']['Ku'], runs['d1']['L']), ('geometric_d1only', runs['d1']['Kg'], runs['d1']['L'])):
        dop[tag] = dict(doppler_summary(K), **pair_stats(Lx, K))
    q_fresh = float(np.quantile(np.abs(runs['d12']['Ku']), .99))
    se_fresh = float(np.sqrt(.99 * .01 / runs['d12']['Ku'].size) / max(1e-9, _density(np.abs(runs['d12']['Ku']), q_fresh)))
    nu_const = gen_fixed.UWA_NU_MAX_99
    numax = dict(constant=nu_const, fresh_uwa_quantile_in_d12_mc=q_fresh, fresh_se=se_fresh,
                 z=(None if nu_const is None else (nu_const - q_fresh) / se_fresh),
                 consistent_within_4se=(None if nu_const is None else bool(abs(nu_const - q_fresh) <= 4 * se_fresh + 5e-4)))
    payload = provenance(args, ctx)
    payload.update(stage='b', seconds=time.time() - t0, mc_frames=n, mc_frames_slow=n_slow, seed=args.seed,
                   stacking=stack, stacking_compare_d12_vs_natural_d2grid=cmp_d12,
                   stacking_compare_d1_vs_natural_d1grid=cmp_d1, structural_strictly_increasing=structural,
                   gate_i_pass=gate_i, ks_span=dict(statistic=float(ks_span.statistic), pvalue=float(ks_span.pvalue),
                                                    n_gen=len(span_g), n_direct=len(span_d)),
                   ks_max_delay=dict(statistic=float(ks_max.statistic), pvalue=float(ks_max.pvalue)),
                   span_summary=dict(gen_mean=float(span_g.mean()), direct_mean=float(span_d.mean()),
                                     gen_max_mean=float(max_g.mean()), direct_max_mean=float(max_d.mean())),
                   gate_ii_pass=gate_ii, truncation=trunc, cap_formula_equals_bin_truncation=cap_equiv,
                   doppler=dop, numax_check=numax, gate_b_pass=bool(gate_i and gate_ii))
    write_json('b.json', payload)
    print('gate b: stacking', cmp_d12, 'KS span p=', ks_span.pvalue, flush=True)


def _density(a, q, h=.02):
    return float(((a > q - h) & (a <= q + h)).mean() / (2 * h))


# ----------------------------------------------------------------------------- G-S0c
def stage_c(args, hd, ctx):
    seed_fn = lambda frame, component: hd.seed_words(TEST_ENTROPY, frame, component)  # noqa: E731
    s = ctx.system
    out = {}
    for name in CONFIGS:
        flags = config_flags(name)
        rows = []
        for frame in range(args.frames):
            raw, diag = gen_fixed.generate_base(ctx, .5, 7.0, frame, seed_fn, flags)
            p = raw['params']
            l, nu, g = p['l_i'], p['k_real'], p['g_i']
            prefix = int(diag['gen_fixed']['prefix_length'])
            x = raw['pilot'] + raw['data']
            wave = ctx.transform(x, s.c1, s.c2, inverse=True)
            phys = ctx.transform(ctx.propagate_cpp(wave, s.c1, l, nu, g, prefix_length=prefix), s.c1, s.c2)
            scale = max(1., float(np.linalg.norm(phys)))
            hm = ctx.physical_channel_matrix(int(s.N_total), s.c1, s.c2, l, nu, g, prefix_length=prefix)
            rows.append(dict(
                frame=frame, prefix=prefix, max_delay=int(l.max()), n_distinct_delays=int(len(np.unique(l))),
                k_min=float(nu.min()), k_max=float(nu.max()), redraws=int(diag['gen_fixed']['redraws']),
                err_noiseless_vs_cpp=float(np.linalg.norm(raw['noiseless'] - phys) / scale),
                err_matrix_vs_cpp=float(np.linalg.norm(hm @ x - phys) / scale),
                err_H_vs_physical_matrix=float(np.linalg.norm(raw['H'] - hm) / max(1., np.linalg.norm(hm))),
                err_y_vs_cpp_plus_noise=float(np.linalg.norm(raw['y'] - (phys + np.sqrt(raw['sigma2']) * raw['noise'])) / scale),
                prefix_ge_max_delay=bool(prefix >= int(l.max())),
                matrix_cpp_relative_error_diag=float(diag['matrix_cpp_relative_error'])))
        errs = ('err_noiseless_vs_cpp', 'err_matrix_vs_cpp', 'err_H_vs_physical_matrix', 'err_y_vs_cpp_plus_noise')
        ok = all(r[e] <= 1e-10 for r in rows for e in errs) and all(r['prefix_ge_max_delay'] for r in rows)
        if flags.fix_delay_cap:
            ok = ok and all(r['max_delay'] <= gen_fixed.RECEIVER_BANK_MAX_DELAY for r in rows)
        out[name] = dict(pass_=bool(ok), max_err=float(max(r[e] for r in rows for e in errs)),
                         prefix_values=sorted({r['prefix'] for r in rows}), rows=rows)
        print('config', name, 'pass', ok, 'max err', out[name]['max_err'], flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='c', frames_per_config=args.frames, configs=out, gate_c_pass=bool(all(v['pass_'] for v in out.values())))
    write_json('c.json', payload)


# ----------------------------------------------------------------------------- G-S0d (amendment A1)
def stage_d(args, hd, ctx):
    seed_fn = lambda frame, component: hd.seed_words(TEST_ENTROPY, frame, component)  # noqa: E731
    s = ctx.system
    n = int(s.N_total)
    out = {}
    for name, ref in (('d12e', 'd12'), ('d12egeo', 'd12geo')):
        rows = []
        for frame in range(args.frames):
            raw, diag = gen_fixed.generate_base(ctx, .5, 7.0, frame, seed_fn, config_flags(name))
            _, diag_ref = gen_fixed.generate_base(ctx, .5, 7.0, frame, seed_fn, config_flags(ref))
            p = raw['params']
            energy_diag = float(diag['channel_energy_per_dimension'])
            energy_h = float(np.vdot(raw['H'], raw['H']).real / n)
            hm = ctx.physical_channel_matrix(n, s.c1, s.c2, p['l_i'], p['k_real'], p['g_i'], prefix_length=int(diag['gen_fixed']['prefix_length']))
            energy_op = float(np.vdot(hm, hm).real / n)
            rows.append(dict(frame=frame, energy_diag=energy_diag, energy_raw_H=energy_h, energy_cpp_operator=energy_op,
                             path_power=float(np.sum(np.abs(p['g_i']) ** 2)), fro_scale=float(raw['g0_reference']['params']['fro_scale']),
                             energy_without_fix=float(diag_ref['channel_energy_per_dimension']),
                             n_distinct_delays=int(len(np.unique(p['l_i'])))))
        e = np.array([[r['energy_diag'], r['energy_raw_H'], r['energy_cpp_operator']] for r in rows])
        pp = np.array([r['path_power'] for r in rows])
        ref_e = np.array([r['energy_without_fix'] for r in rows])
        max_dev = float(np.abs(e - 1.0).max())
        ok = bool(max_dev <= 1e-9 and np.abs(pp - 1.0).max() <= 1e-9 and all(r['fro_scale'] == 1.0 for r in rows))
        out[name] = dict(pass_=ok, frames=len(rows), max_abs_energy_deviation=max_dev, max_abs_path_power_deviation=float(np.abs(pp - 1.0).max()),
                         energy_min=float(e.min()), energy_max=float(e.max()),
                         energy_without_fix_mean=float(ref_e.mean()), energy_without_fix_min=float(ref_e.min()),
                         energy_without_fix_max=float(ref_e.max()), all_delays_distinct=bool(all(r['n_distinct_delays'] == s.P_paths for r in rows)),
                         rows=rows)
        print('G-S0d', name, 'pass', ok, 'max dev', max_dev, flush=True)
    payload = provenance(args, ctx)
    payload.update(stage='d', frames_per_config=args.frames, configs=out, gate_d_pass=bool(all(v['pass_'] for v in out.values())))
    write_json('d.json', payload)


# ----------------------------------------------------------------------------- smoke
def stage_smoke(args, hd, ctx):
    seed_fn = lambda frame, component: hd.seed_words(TEST_ENTROPY, frame, component)  # noqa: E731
    out = {}
    for name in CONFIGS:
        flags = config_flags(name)
        rows, errors = [], []
        for frame in range(args.frames):
            t = time.perf_counter()
            try:
                raw_base, diag_base = gen_fixed.generate_base(ctx, .5, 7.0, frame, seed_fn, flags)
                raw, diag = ctx.reuse_at_snr(raw_base, diag_base, 7.0)
                obs = hd.observe(raw, .5, 7.0)
                truth = hd.truth_from_raw(raw, diag)
                gen_s = time.perf_counter() - t
                results = hd.run_a0(ctx, obs)
                for res in results:
                    sc = hd.score(ctx, res, truth)
                    rows.append(dict(frame=frame, arm=res['arm'], info_errors=sc['info_errors'], decode_ok=sc['decode_ok'],
                                     seconds=sc['seconds'], triggered=sc['triggered'], generate_seconds=gen_s,
                                     n_paths=int(len(truth['l_i'])), max_l=int(np.max(truth['l_i']))))
            except Exception as error:  # recorded, never silently dropped
                import traceback
                errors.append(dict(frame=frame, error=repr(error), trace=traceback.format_exc()[-1500:]))
            print('smoke', name, frame, [(r['arm'], r['info_errors']) for r in rows if r['frame'] == frame], flush=True)
        a0 = [r for r in rows if r['arm'] == 'A0']
        out[name] = dict(rows=rows, errors=errors, n_frames=args.frames, n_ok=len(a0),
                         mean_seconds_A0=float(np.mean([r['seconds'] for r in a0])) if a0 else None,
                         mean_seconds_F0=float(np.mean([r['seconds'] for r in rows if r['arm'] == 'F0'])) if a0 else None,
                         mean_generate_seconds=float(np.mean([r['generate_seconds'] for r in a0])) if a0 else None,
                         info_errors_A0=[r['info_errors'] for r in a0], info_errors_F0=[r['info_errors'] for r in rows if r['arm'] == 'F0'])
    payload = provenance(args, ctx)
    payload.update(stage='smoke', configs=out, smoke_pass=bool(all(not v['errors'] and v['n_ok'] == v['n_frames'] for v in out.values())))
    write_json('smoke.json', payload)


# ----------------------------------------------------------------------------- merge
def stage_merge(args):
    def load(name):
        return json.loads((OUT / name).read_text())
    numax = load('numax.json')
    shards = [load(p.name) for p in sorted(OUT.glob('a_shard*.json'))]
    rows = [r for s in shards for r in s['rows']]
    n5 = [r for r in rows if r['rho'] == .5]
    n3 = [r for r in rows if r['rho'] == .3]
    a = {}
    a['n_shards'] = len(shards)
    a['n_frames_rho05'] = len(n5)
    a['n_frames_rho03'] = len(n3)
    a['triple_identical_rho05'] = int(sum(r['triple_equal'] for r in n5))
    a['all_fields_identical_rho05'] = int(sum(r['all_equal'] for r in n5))
    a['triple_identical_rho03'] = int(sum(r['triple_equal'] for r in n3))
    a['all_fields_identical_rho03'] = int(sum(r['all_equal'] for r in n3))
    a['frames_with_fallback_clip_frozen'] = int(sum(r['resample_attempts'] == 32 for r in n5))
    a['failed'] = sorted({k for r in rows for k in r['failed']})
    a['shard_frame_coverage_ok'] = sorted(r['frame'] for r in n5) == list(range(len(n5)))
    a['pass'] = bool(len(n5) >= 1000 and a['triple_identical_rho05'] == len(n5) and a['all_fields_identical_rho05'] == len(n5)
                     and a['triple_identical_rho03'] == len(n3) and a['all_fields_identical_rho03'] == len(n3)
                     and a['shard_frame_coverage_ok'])
    a['seconds_frozen_mean'] = float(np.mean([r['seconds_frozen'] for r in rows]))
    a['seconds_fixed_mean'] = float(np.mean([r['seconds_fixed'] for r in rows]))
    b, c, sm, dd = load('b.json'), load('c.json'), load('smoke.json'), load('d.json')
    now = dict(gen_fixed=md5_file(HERE / 'gen_fixed.py'), s0_gates=md5_file(HERE / 's0_gates.py'))
    code_ok = ({s['_code_md5']['gen_fixed'] for s in shards + [b, c, sm, dd]} == {now['gen_fixed']}
               and {s['_code_md5']['s0_gates'] for s in shards + [b, c, sm, dd, numax]} == {now['s0_gates']})
    constant_ok = gen_fixed.UWA_NU_MAX_99 is not None and abs(gen_fixed.UWA_NU_MAX_99 - numax['nu_max_99_rounded3']) < 1e-12
    gates = dict(
        G_S0a=a, G_S0b=dict(pass_=bool(b['gate_b_pass']), i_stacking_pass=b['gate_i_pass'], ii_ks_span_pass=b['gate_ii_pass'],
                            stacking=b['stacking'], compare_d12=b['stacking_compare_d12_vs_natural_d2grid'],
                            compare_d1=b['stacking_compare_d1_vs_natural_d1grid'], ks_span=b['ks_span'],
                            ks_max_delay=b['ks_max_delay'], truncation=b['truncation'],
                            cap_formula_equals_bin_truncation=b['cap_formula_equals_bin_truncation'],
                            structural_strictly_increasing=b['structural_strictly_increasing']),
        G_S0d=dict(pass_=bool(dd['gate_d_pass']), per_config={k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in dd['configs'].items()}),
        G_S0c=dict(pass_=bool(c['gate_c_pass']), per_config={k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in c['configs'].items()}),
        geometric_law=dict(nu_max=numax['nu_max_99_rounded3'], nu_max_pooled=numax['nu_max_99_pooled'], mc_se=numax['mc_se_block_quantiles'],
                           analytic=numax['analytic_folded_normal_99'], n_paths=numax['n_paths'], doppler=b['doppler'], numax_check=b['numax_check']),
        smoke=dict(pass_=bool(sm['smoke_pass']), per_config={k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in sm['configs'].items()}),
        constants=dict(nu_max_99_in_gen_fixed=gen_fixed.UWA_NU_MAX_99, constant_matches_numax_json=constant_ok,
                       stage_code_md5_equals_current_files=code_ok))
    gates['all_pass'] = bool(a['pass'] and gates['G_S0b']['pass_'] and gates['G_S0c']['pass_'] and gates['G_S0d']['pass_'] and sm['smoke_pass'] and constant_ok and code_ok)
    payload = dict(_argv=list(sys.argv), _config=dict(test_entropy=TEST_ENTROPY, stage_files={p.name: md5_file(p) for p in sorted(OUT.glob('*.json'))
                                                                                                if p.name != 'gates.json'},
                                                      stage_argv={p.name: load(p.name)['_argv'] for p in sorted(OUT.glob('*.json'))
                                                                  if p.name != 'gates.json'},
                                                      frozen_source_sha256=b['_config']['frozen_source_sha256'],
                                                      environment=b['_config']['environment'], versions=b['_config']['versions']),
                   _code_md5=dict(gen_fixed=md5_file(HERE / 'gen_fixed.py'), s0_gates=md5_file(HERE / 's0_gates.py')), gates=gates)
    write_json('gates.json', payload)
    (OUT / 'GATES.md').write_text(render_md(gates, payload))
    print('wrote', OUT / 'GATES.md', 'all_pass =', gates['all_pass'], flush=True)


def pct(x):
    return f'{100 * x:.3f}%'


def render_md(g, payload):
    a, b, c, geo, sm, d = g['G_S0a'], g['G_S0b'], g['G_S0c'], g['geometric_law'], g['smoke'], g['G_S0d']
    st = b['stacking']
    tr = b['truncation']
    flag = lambda ok: 'PASS' if ok else 'FAIL'  # noqa: E731
    L = []
    L.append('# S0 gates (generator fix D1-D3)\n')
    L.append(f"Overall: **{flag(g['all_pass'])}**.  Test entropy `{TEST_ENTROPY}` (S0 only).  "
             f"Code md5: gen_fixed `{payload['_code_md5']['gen_fixed']}`, s0_gates `{payload['_code_md5']['s0_gates']}`.  "
             f"`_argv` / `_config` are in gates.json.\n")
    L.append('| gate | criterion | result |\n|---|---|---|')
    L.append(f"| G-S0a | flags off, frames 0..999: l_i, k_real, g_i (+ every other field) bit-identical to frozen driver.generate_base | "
             f"**{flag(a['pass'])}** {a['triple_identical_rho05']}/{a['n_frames_rho05']} (l,k,g), all fields {a['all_fields_identical_rho05']}/{a['n_frames_rho05']}; "
             f"rho .3 extra {a['triple_identical_rho03']}/{a['n_frames_rho03']} |")
    L.append(f"| G-S0b(i) | D1+D2 same-delay stacking rate within 3 SE of the natural (uncapped) rate | **{flag(b['i_stacking_pass'])}** "
             f"{pct(st['d12']['rate'])} vs {pct(st['natural_d2grid']['rate'])} (z = {b['compare_d12']['z']:.2f}, n = {st['d12']['n']}/{st['natural_d2grid']['n']}) |")
    L.append(f"| G-S0b(ii) | delay-span two-sample KS p > .01 vs direct rejection sampler | **{flag(b['ii_ks_span_pass'])}** "
             f"p = {b['ks_span']['pvalue']:.3f} (D = {b['ks_span']['statistic']:.4f}); max-delay p = {b['ks_max_delay']['pvalue']:.3f} |")
    L.append(f"| G-S0b(iii) | truncation (redraw) rate reported | first-try acceptance {pct(tr['d12']['first_try_acceptance'])}, "
             f"{tr['d12']['redraws_per_frame']:.3f} redraws/frame, max attempts {tr['d12']['max_attempts']} |")
    L.append(f"| G-S0c | observation = CPP propagation to 1e-10, prefix >= max delay, 20 frames x 5 configs | **{flag(c['pass_'])}** "
             f"max err {max(v['max_err'] for v in c['per_config'].values()):.2e} |")
    L.append(f"| G-S0d (A1) | fix_energy on, U and G: per-frame ||H||_F^2/N = 1 to 1e-9 (CPP operator), 200 frames each | **{flag(d['pass_'])}** "
             f"max |dev| U {d['per_config']['d12e']['max_abs_energy_deviation']:.2e}, G {d['per_config']['d12egeo']['max_abs_energy_deviation']:.2e} |")
    L.append(f"| smoke | frozen F0+CSTATE (run_a0) runs on 8 frames x 5 configs at 7 dB, rho .5 | **{flag(sm['pass_'])}** |\n")
    L.append('## G-S0a detail\n')
    L.append(f"- Frames rho .5: {a['n_frames_rho05']} (shards {a['n_shards']}); failed fields: {a['failed'] or 'none'}.")
    L.append(f"- Frozen draw: {a['frames_with_fallback_clip_frozen']} frames hit the 32-attempt clip fallback; mean seconds per frame frozen/fixed "
             f"{a['seconds_frozen_mean']:.2f}/{a['seconds_fixed_mean']:.2f} (fixed copy skips H_time).\n")
    L.append('## G-S0b detail\n')
    L.append('Same-delay stacking (frames with >= 2 paths in one delay bin), MC:\n')
    L.append('| draw | n | rate | SE |\n|---|---|---|---|')
    for k in ('off', 'd2', 'd1', 'd12', 'natural_d1grid', 'natural_d2grid'):
        L.append(f"| {k} | {st[k]['n']} | {pct(st[k]['rate'])} | {pct(st[k]['se'])} |")
    L.append(f"\nOff = frozen law (stale cap 54, 32 redraws, clip). d1 = explicit truncation at 102 on the frozen 65.1 us grid; d2 = new grid, stale cap; "
             f"d12 = both. natural_* = single draw, no cap, no clip. D1-only vs its natural rate: diff {pct(b['compare_d1']['diff'])}, "
             f"z = {b['compare_d1']['z']:.2f} (informational: truncation biases the span and, on the 0.96 grid, the stacking rate). "
             f"Under D2 the sample delays are strictly increasing in every drawn frame (checked: {b['structural_strictly_increasing']}), "
             f"so the natural stacking rate is structurally 0 and equality is the pass condition.\n")
    L.append(f"Cap formula (computed from the final fs/Ts) vs explicit bin truncation agree for all indices: {b['cap_formula_equals_bin_truncation']}; "
             f"cap values {tr['cap_idx']}.\n")
    L.append(f"Truncation: D1+D2 first-try acceptance {pct(tr['d12']['first_try_acceptance'])} vs direct sampler "
             f"{pct(tr['d12']['direct_sampler_acceptance'])} (z = {tr['d12']['z_vs_direct']:.2f}); D1 on the old grid "
             f"{pct(tr['d1_only']['first_try_acceptance'])}; frozen law first-try acceptance {pct(tr['frozen']['first_try_acceptance'])}, "
             f"clip fallback in {pct(tr['frozen']['clip_fallback_fraction'])} of frames.\n")
    L.append('## G-S0c detail\n')
    for k, v in c['per_config'].items():
        L.append(f"- {k}: {flag(v['pass_'])}, max rel. error {v['max_err']:.2e}, prefix values {v['prefix_values']}")
    L.append('\n## G-S0d detail (amendment A1: fix_energy)\n')
    for k, v in d['per_config'].items():
        L.append(f"- {k}: {flag(v['pass_'])}, {v['frames']} frames, energy in [{v['energy_min']:.12f}, {v['energy_max']:.12f}] "
                 f"(max |dev| {v['max_abs_energy_deviation']:.2e}, path power dev {v['max_abs_path_power_deviation']:.2e}); "
                 f"same frames without fix_energy: mean {v['energy_without_fix_mean']:.4f}, min {v['energy_without_fix_min']:.4f}, "
                 f"max {v['energy_without_fix_max']:.4f}")
    L.append('\n## Geometric law\n')
    L.append(f"- nu_max = {geo['nu_max']} (pooled estimate {geo['nu_max_pooled']:.5f}, MC SE {geo['mc_se']:.5f} over 20 blocks, "
             f"{geo['n_paths']} path draws; analytic folded-normal value {geo['analytic']:.5f}); frozen in gen_fixed.UWA_NU_MAX_99.")
    nc = geo['numax_check']
    L.append(f"- Fresh UWA quantile in the D1+D2 MC: {nc['fresh_uwa_quantile_in_d12_mc']:.4f} (SE {nc['fresh_se']:.4f}), consistent: {nc['consistent_within_4se']}.\n")
    L.append('| law (D1+D2 draws) | frac k>0 | |k| q50 | q90 | q99 | max | P(|dk|<=1) all pairs |\n|---|---|---|---|---|---|---|')
    for tag in ('uwa_d12', 'geometric_d12'):
        d = geo['doppler'][tag]
        q = d['abs_quantiles']
        L.append(f"| {tag} | {d['frac_positive']:.3f} | {q['0.5']:.3f} | {q['0.9']:.3f} | {q['0.99']:.3f} | {q['1.0']:.3f} | {d['frac_within_1bin_all_pairs']:.4f} |")
    L.append('\nSame-delay pairs exist only without D2 (D1-only draws); fraction within one Doppler bin:\n')
    L.append('| law | same-delay pairs | P(|dk|<=1) |\n|---|---|---|')
    for tag in ('uwa_d1only', 'geometric_d1only'):
        d = geo['doppler'][tag]
        L.append(f"| {tag} | {d['pairs_same_delay']} | {d['frac_within_1bin_same_delay']:.4f} |")
    L.append('\n## Smoke (not a performance result)\n')
    for k, v in sm['per_config'].items():
        L.append(f"- {k}: {v['n_ok']}/{v['n_frames']} frames ok, errors {len(v['errors'])}, A0 {v['mean_seconds_A0']:.3f} s/frame, "
                 f"F0 {v['mean_seconds_F0']:.3f} s/frame, generation {v['mean_generate_seconds']:.2f} s/frame; "
                 f"info errors A0 {v['info_errors_A0']}, F0 {v['info_errors_F0']}")
    return '\n'.join(L) + '\n'


# ----------------------------------------------------------------------------- main
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('numax', 'a', 'b', 'c', 'd', 'smoke', 'merge'), required=True)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--rho3-frames', type=int, default=0)
    p.add_argument('--mc-frames', type=int, default=100000)
    p.add_argument('--mc-frames-frozen', type=int, default=40000)
    p.add_argument('--seed', type=int, default=20261015)
    args = p.parse_args()
    if args.stage == 'merge':
        return stage_merge(args)
    hd, ctx = get_context()
    check_system_matches_stated_law(ctx.system)
    {'numax': stage_numax, 'a': stage_a, 'b': stage_b, 'c': stage_c, 'd': stage_d, 'smoke': stage_smoke}[args.stage](args, hd, ctx)


if __name__ == '__main__':
    main()
