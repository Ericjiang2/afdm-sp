#!/usr/bin/env python
"""P2b gates before any test-frame run (task 10-15-tcom-reference-frame, protocol I2).  All gate frames come from the DEV entropy set.

  g0   (a) the P1 scenarios U and G are bit-identical between the P1-era gen_fixed.py (out/p2b_gates/ref/gen_fixed_p1.py, md5 recorded)
           and the current file, 100 frames each; (b) scenario S law: redraw / truncation rate and delay-span KS vs an independent
           rejection sampler, max delay <= 25, distinct delays.
  g1   P2b-G1: EP-genie on noiseless frames (sigma2 -> 1e-10, 20 frames): all decoded, first-round detector output == transmitted symbols.
  g2   P2b-G2: estimator on noiseless pilot-only frames, 50 frames of scenario S: delays exact, Doppler within 0.05 bin; plus the closed-form
           pilot response vs the physical operator, and informational recall statistics with data present at 4.5 and 8.0 dB.
  g3cmp P2b-G3: two separate processes of p2b_driver on the same 16 frames give bit-identical rows (all arms except SPG, all fields except
        seconds), and the EP / EP-genie / SP rows equal the rows stored before the shared LMMSE core was factored out (ref/g3_prev).
  g4   P2b-G4: LDPC n = 1530 encoder/decoder round trip on 100 random messages, noiseless; actual k recorded.
  g5   P2b-G5 (protocol I3): the report-only SP-genie-LMMSE arm decodes every noiseless SP frame (20 dev frames at rho .3 and .5).
  g6cmp P2b-G6: G3-style determinism including the SPG arm (all 10 arms, two processes, 16 frames).
  timing_spg  timing of the SPG arm only (16 frames at 5.0 and 7.0 dB) and the updated test-run projection.
  timing  16 frames per arm at 5.0 and 7.0 dB, single quiet process; core-hour projection of the test run at 30 shards (x1.5 contention).
  merge  out/p2b_gates/p2b_gates.json + P2B_GATES.md
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_rx as E  # noqa: E402
import gen_fixed  # noqa: E402
import p1_driver as P  # noqa: E402
import p2b_driver as D  # noqa: E402

OUT = HERE / 'out' / 'p2b_gates'
REF = OUT / 'ref' / 'gen_fixed_p1.py'
G_RHO_EP = 0.1          # gate pilot fraction (independent of the frozen RHO_EP)
FRAME = dict(g0=0, g1=1000, g2=2000, g3=3000, timing=4000, g5=7000, timing_spg=8000)
TIMING_SNR = (500, 700)
CONTENTION = 1.5
NSH = 30
GRID_SNR = (450, 500, 550, 600, 650, 700, 750, 800)


def _jsonable(value):
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


def write_json(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=1, sort_keys=True, default=_jsonable, allow_nan=False) + '\n')
    print('wrote', OUT / name, flush=True)


def provenance(args, ctx):
    D.add_sources(ctx)
    return dict(_argv=list(sys.argv), _config=dict(
        args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}, entropy_dev=D.ENTROPY_DEV, domain_dev=D.DOMAIN_DEV,
        entropy_test=D.ENTROPY_TEST, domain_test=D.DOMAIN_TEST, gate_rho_ep=G_RHO_EP, flags_S=D.FLAGS_S.tag(),
        source_md5=ctx.source_md5, environment=ctx.environment),
        _code_md5={n: P.md5_file(HERE / f'{n}.py') for n in ('p2b_gates', 'p2b_driver', 'ep_rx', 'gen_fixed', 'p1_driver')})


def dev_seed():
    return P.make_seed_fn(D.ENTROPY_DEV, D.DOMAIN_DEV)


def frame_inputs(ctx, ep, frame, seed_fn):
    raw, diag = P.generate(ctx, D.FLAGS_S, .5, 6.0, frame, seed_fn)
    p = raw['params']
    rf = gen_fixed.make_rng_factory(seed_fn, frame)
    info = rf(0, frame, 2, split=2).integers(0, 2, size=ep.k).astype(np.uint8)
    H = E.channel_matrix(ep, p['l_i'], p['k_real'], p['g_i'])
    return dict(params=p, noise=raw['noise'], info=info, H=H)


# ----------------------------------------------------------------------------- g0
def load_ref():
    spec = importlib.util.spec_from_file_location('gen_fixed_p1', REF)
    module = importlib.util.module_from_spec(spec)
    sys.modules['gen_fixed_p1'] = module  # dataclasses resolves cls.__module__ through sys.modules
    spec.loader.exec_module(module)
    return module


def stage_g0(args, ctx):
    from scipy import stats
    import s0_gates as S0
    ref = load_ref()
    seed_fn = dev_seed()
    rows, bad = [], 0
    for name, new_flags, ref_flags in (('U', P.SCENARIOS['U'], ref.Flags(True, True, 'uwa', True)),
                                       ('G', P.SCENARIOS['G'], ref.Flags(True, True, 'geometric', True))):
        for frame in range(FRAME['g0'], FRAME['g0'] + args.frames):
            a, da = ref.generate_base(ctx, .5, 6.0, frame, seed_fn, ref_flags)
            b, db = gen_fixed.generate_base(ctx, .5, 6.0, frame, seed_fn, new_flags)
            same = all(np.array_equal(a['params'][k], b['params'][k]) for k in ('l_i', 'k_real', 'g_i', 'g_i_raw'))
            same = same and all(np.array_equal(a[k], b[k]) for k in ('H', 'y', 'noiseless', 'info', 'coded', 'noise'))
            same = same and da['physical_gains_sha256'] == db['physical_gains_sha256']
            rows.append(dict(scenario=name, frame=frame, identical=bool(same)))
            bad += int(not same)
    # scenario S law
    system = ctx.system
    n = args.mc_frames
    run = S0.mc_draw(system, D.FLAGS_S, n, 20261016)
    L = run['L']
    att = run['attempts']
    ts = 1.0 / system.fs
    tau = system.tau_mean * 25. / 102.
    rng = np.random.default_rng(20261017)
    spans, maxes, tried, accepted = [], [], 0, 0
    while accepted < n:
        m = 200000
        inc = np.maximum(1, np.ceil(rng.exponential(tau, size=(m, system.P_paths)) / ts).astype(np.int64))
        lx = np.cumsum(inc, axis=1) - 1
        ok = lx.max(axis=1) <= 25
        tried += m
        spans.append((lx.max(axis=1) - lx.min(axis=1))[ok])
        accepted += int(ok.sum())
    span_d = np.concatenate(spans)
    accept_direct = accepted / tried
    accept_gen = n / att.sum()
    se = float(np.sqrt(accept_direct * (1 - accept_direct) / tried + accept_gen * (1 - accept_gen) / att.sum()))
    ks = stats.ks_2samp(L.max(1) - L.min(1), span_d[:n])
    law = dict(frames=n, first_try_acceptance=float(accept_gen), redraw_rate=float(1 - accept_gen), redraws_per_frame=float(att.mean() - 1),
               max_attempts=int(att.max()), direct_sampler_acceptance=float(accept_direct), z_vs_direct=float((accept_gen - accept_direct) / se),
               ks_span_p=float(ks.pvalue), ks_span_D=float(ks.statistic), max_delay=int(L.max()), min_delay=int(L.min()),
               all_delays_distinct=bool((np.diff(np.sort(L, axis=1), axis=1) > 0).all()),
               delay_mean_increment_samples=float(tau / ts), n_paths=int(system.P_paths))
    law['passed'] = bool(law['max_delay'] <= 25 and law['all_delays_distinct'] and abs(law['z_vs_direct']) < 3 and law['ks_span_p'] > .01)
    payload = provenance(args, ctx)
    payload.update(stage='g0', p1_scenarios_identical=bad == 0, p1_scenarios_checked=len(rows), p1_mismatches=bad,
                   ref_md5=P.md5_file(REF), scenario_s_law=law, passed=bool(bad == 0 and law['passed']))
    write_json('g0.json', payload)


# ----------------------------------------------------------------------------- g1
def stage_g1(args, ctx):
    ep = D.build_ep(ctx)
    seed_fn = dev_seed()
    rows = []
    for i in range(args.frames):
        fr = FRAME['g1'] + i
        fi = frame_inputs(ctx, ep, fr, seed_fn)
        x, sym, _ = E.make_frame(ep, fi['info'], G_RHO_EP)
        y = fi['H'] @ x  # noiseless
        t = time.perf_counter()
        det = E.detect(ep, y, fi['H'], 1e-10, G_RHO_EP)
        m = det['first_round_mean']
        hard_ok = bool(np.array_equal(m.real > 0, sym.real > 0) and np.array_equal(m.imag > 0, sym.imag > 0))
        rows.append(dict(frame=fr, info_errors=int(np.count_nonzero(det['info_hat'] != fi['info'])), decode_ok=bool(det['ok']),
                         max_symbol_error=float(np.abs(m - sym).max()), hard_decisions_match=hard_ok,
                         rms_symbol_error=float(np.sqrt(np.mean(np.abs(m - sym) ** 2))), seconds=time.perf_counter() - t,
                         bp_iterations=det['iterations']))
    tol = 1e-3
    passed = all(r['info_errors'] == 0 and r['decode_ok'] and r['hard_decisions_match'] and r['max_symbol_error'] <= tol for r in rows)
    payload = provenance(args, ctx)
    payload.update(stage='g1', frames=len(rows), sigma2=1e-10, rho_ep=G_RHO_EP, symbol_tolerance=tol, rows=rows, passed=bool(passed),
                   max_symbol_error=max(r['max_symbol_error'] for r in rows))
    write_json('g1.json', payload)


# ----------------------------------------------------------------------------- g2
def stage_g2(args, ctx):
    ep = D.build_ep(ctx)
    seed_fn = dev_seed()
    # closed-form pilot response vs the frozen physical operator
    from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
    rng = np.random.default_rng(7)
    resp_err = 0.
    for _ in range(8):
        l, nu = int(rng.integers(0, 26)), float(rng.uniform(-2, 2))
        Hs = physical_channel_matrix(E.N, ep.c1, ep.c2, np.array([l]), np.array([nu]), np.array([1 + 0j]), prefix_length=ep.prefix)
        resp_err = max(resp_err, float(np.abs(Hs[ep.rows, E.PILOT] - E.pilot_response(ep, l, nu)).max()))
        full = np.arange(E.N)
        resp_err = max(resp_err, float(np.abs(Hs[:, E.PILOT] - E.pilot_response(ep, l, nu, rows=full)).max()))
    rows = []
    xp = np.zeros(E.N, complex)
    xp[E.PILOT] = E.pilot_amplitude(G_RHO_EP)
    for i in range(args.frames):
        fr = FRAME['g2'] + i
        fi = frame_inputs(ctx, ep, fr, seed_fn)
        est = E.estimate_paths(ep, fi['H'] @ xp, 1e-6, G_RHO_EP)
        rows.append(dict(frame=fr, **E.path_match(est, fi['params']['l_i'], fi['params']['k_real'])))
    passed_main = all(r['delays_exact'] and r['max_doppler_error'] is not None and r['max_doppler_error'] <= 0.05 for r in rows) and resp_err < 1e-10
    # informational: data present, operating SNRs
    info_rows = {}
    for snr in (450, 800):
        sigma2 = 10 ** (-snr / 100 / 10)
        rec, fa, perr, captured, total = 0, 0, [], 0., 0.
        for i in range(args.frames):
            fr = FRAME['g2'] + 500 + i
            fi = frame_inputs(ctx, ep, fr, seed_fn)
            x, _, _ = E.make_frame(ep, fi['info'], G_RHO_EP)
            y = E.observe(ep, fi['H'], x, fi['noise'], sigma2)
            est = E.estimate_paths(ep, y, sigma2, G_RHO_EP)
            tl, tn, tg = fi['params']['l_i'], fi['params']['k_real'], fi['params']['g_i']
            found = {int(l): (nu, g) for l, nu, g in zip(est['delays'], est['dopplers'], est['gains'])}
            for l, nu, g in zip(tl, tn, tg):
                total += abs(g) ** 2
                if int(l) in found:
                    rec += 1
                    captured += abs(g) ** 2
                    perr.append(abs(found[int(l)][0] - nu))
            fa += len(set(found) - set(int(l) for l in tl))
        n_true = args.frames * ctx.system.P_paths
        info_rows[str(snr)] = dict(path_recall=rec / n_true, energy_recall=captured / total, false_paths_per_frame=fa / args.frames,
                                   median_doppler_error=float(np.median(perr)), p90_doppler_error=float(np.quantile(perr, .9)))
    payload = provenance(args, ctx)
    payload.update(stage='g2', frames=len(rows), sigma2_input=1e-6, rho_ep=G_RHO_EP, pilot_response_max_error=resp_err, rows=rows,
                   passed=bool(passed_main), informational_with_data=info_rows,
                   max_doppler_error=max(r['max_doppler_error'] for r in rows))
    write_json('g2.json', payload)


# ----------------------------------------------------------------------------- g5
def stage_g5(args, ctx):
    """Pass criterion (protocol I3): the arm decodes every noiseless SP frame.  The first-round symbol error is informational: the square SP
    operator has (near-)null singular values, so a data-only-prior LMMSE cannot reproduce every symbol before the decoder helps."""
    seed_fn = dev_seed()
    rows = []
    for i in range(args.frames):
        fr = FRAME['g5'] + i
        for rho in D.SP_RHOS:
            raw, diag = P.generate(ctx, D.FLAGS_S, rho, 6.0, fr, seed_fn)
            sv = np.linalg.svd(raw['H'], compute_uv=False)
            t = time.perf_counter()
            det = E.detect_sp(ctx.code, raw['H'], raw['noiseless'], raw['pilot'], 1e-10, rho)
            sym, m = raw['data'], det['first_round_mean']
            rows.append(dict(frame=fr, rho=rho, info_errors=int(np.count_nonzero(det['info_hat'] != raw['info'])), decode_ok=bool(det['ok']),
                             first_round_max_symbol_error=float(np.abs(m - sym).max()), first_round_rms_symbol_error=float(np.sqrt(np.mean(np.abs(m - sym) ** 2))),
                             first_round_hard_bit_errors=int(np.sum((m.real > 0) != (sym.real > 0)) + np.sum((m.imag > 0) != (sym.imag > 0))),
                             operator_sv_min=float(sv.min()), operator_sv_below_noise_prior=int(np.sum(sv < np.sqrt(1e-10 / (1. - rho)))),
                             seconds=time.perf_counter() - t, bp_iterations=det['iterations']))
    passed = all(r['info_errors'] == 0 and r['decode_ok'] for r in rows)
    payload = provenance(args, ctx)
    payload.update(stage='g5', frames=args.frames, rhos=list(D.SP_RHOS), cells=len(rows), sigma2=1e-10, rows=rows, passed=bool(passed),
                   decoded=sum(r['decode_ok'] and r['info_errors'] == 0 for r in rows),
                   max_first_round_symbol_error=max(r['first_round_max_symbol_error'] for r in rows),
                   first_round_hard_bit_errors=sum(r['first_round_hard_bit_errors'] for r in rows),
                   cells_with_null_directions=sum(r['operator_sv_below_noise_prior'] > 0 for r in rows),
                   min_operator_sv=min(r['operator_sv_min'] for r in rows))
    write_json('g5.json', payload)


# ----------------------------------------------------------------------------- g3 compare
def load_rows_dir(d):
    out = {}
    for f in sorted(Path(d).glob('rows_shard*.jsonl')):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            out[(r['snr_centi_db'], r['frame'])] = r
    return out


def strip_timing(value):
    if isinstance(value, dict):
        return {k: strip_timing(v) for k, v in value.items() if 'seconds' not in k}
    if isinstance(value, list):
        return [strip_timing(v) for v in value]
    return value


def _arm_filter(rows, keep):
    out = {}
    for k, r in rows.items():
        r2 = dict(r)
        r2['arms'] = {a: v for a, v in r['arms'].items() if keep(a)}
        out[k] = r2
    return out


def stage_g3cmp(args):
    """P2b-G3: determinism of the original 8 arms across two processes + equality with the rows stored before the LMMSE-core refactor."""
    not_spg = lambda a: not a.startswith('SPG')  # noqa: E731
    a, b = _arm_filter(load_rows_dir(args.dir_a), not_spg), _arm_filter(load_rows_dir(args.dir_b), not_spg)
    ref = load_rows_dir(args.dir_ref)
    same_keys = set(a) == set(b)
    diffs = [k for k in sorted(a) if k in b and strip_timing(a[k]) != strip_timing(b[k])]
    # regression: only the arms and fields that exist in the reference rows are compared
    reg = []
    for k in sorted(ref):
        if k not in a:
            reg.append(list(k))
            continue
        ra, rr = strip_timing(a[k]['arms']), strip_timing(ref[k]['arms'])
        if any(ra.get(arm) != val for arm, val in rr.items()):
            reg.append(list(k))
    arms = sorted(next(iter(a.values()))['arms']) if a else []
    payload = dict(_argv=list(sys.argv), stage='g3cmp', rows_a=len(a), rows_b=len(b), rows_ref=len(ref), same_keys=bool(same_keys),
                   mismatching_rows=len(diffs), mismatching_keys=[list(k) for k in diffs], regression_mismatching_rows=len(reg), arms=arms,
                   passed=bool(same_keys and not diffs and not reg and len(a) >= 16 and len(ref) >= 16),
                   rows_md5={str(p): P.md5_file(p) for p in sorted(Path(args.dir_a).glob('rows_shard*.jsonl')) + sorted(Path(args.dir_b).glob('rows_shard*.jsonl'))
                             + sorted(Path(args.dir_ref).glob('rows_shard*.jsonl'))})
    write_json('g3.json', payload)


def stage_g6cmp(args):
    """P2b-G6: G3-style determinism including the SPG arm: two processes, all arms, all fields except seconds."""
    a, b = load_rows_dir(args.dir_a), load_rows_dir(args.dir_b)
    same_keys = set(a) == set(b)
    diffs = [k for k in sorted(a) if k in b and strip_timing(a[k]) != strip_timing(b[k])]
    arms = sorted(next(iter(a.values()))['arms']) if a else []
    spg_ok = bool(a) and all(all(f'SPG_r{r}' in row['arms'] and row['arms'][f'SPG_r{r}'].get('status') == 'ok' for r in (300, 500)) for row in a.values())
    payload = dict(_argv=list(sys.argv), stage='g6cmp', rows_a=len(a), rows_b=len(b), same_keys=bool(same_keys), mismatching_rows=len(diffs),
                   mismatching_keys=[list(k) for k in diffs], arms=arms, spg_present_and_ok=spg_ok,
                   passed=bool(same_keys and not diffs and len(a) >= 16 and spg_ok),
                   rows_md5={str(p): P.md5_file(p) for p in sorted(Path(args.dir_a).glob('rows_shard*.jsonl')) + sorted(Path(args.dir_b).glob('rows_shard*.jsonl'))})
    write_json('g6.json', payload)


# ----------------------------------------------------------------------------- g4
def stage_g4(args, ctx):
    from afdm_sp_joint_unrolled.e1_ldpc import encode, extract_info
    from afdm_sp_joint_unrolled.supplement_messages import decoder_messages
    ep = D.build_ep(ctx)
    code = ep.code
    rng = np.random.default_rng(11)
    ok_dec, ok_map, syn_ok, iters = 0, 0, 0, []
    for _ in range(args.frames):
        info = rng.integers(0, 2, size=code['k']).astype(np.uint8)
        coded = encode(code, info)
        syn_ok += int(not ((code['H'].astype(np.int32) @ coded.astype(np.int32)) % 2).any())
        llr = 8. * (1 - 2 * coded.astype(float))
        dec = decoder_messages(code, llr, maxiter=50)
        ok_dec += int(np.array_equal(extract_info(code, dec['decoded']), info) and dec['decode_ok'])
        x, sym, _ = E.make_frame(ep, info, G_RHO_EP)
        bits = np.concatenate([(sym.real < 0), (sym.imag < 0)]).astype(np.uint8)
        ok_map += int(np.array_equal(bits, coded))
        iters.append(int(dec['iterations']))
    payload = provenance(args, ctx)
    payload.update(stage='g4', messages=args.frames, decode_roundtrip_ok=ok_dec, codeword_syndrome_zero=syn_ok, mapping_roundtrip_ok=ok_map,
                   n=int(code['n']), k=int(code['k']), rate=float(code['k'] / code['n']), H_shape=list(code['H'].shape),
                   rank=int(code['n'] - code['k']), cache_path=code['cache_path'], construction='build_code(1530, d_v=3, d_c=6, seed=20260726), Gallager blocks; '
                   'rank 763 = 765 rows - 2 dependent block sums, so k = 767 (the n = 2048 code has k = 1024)',
                   goodput_info_bits=int(code['k']),
                   passed=bool(ok_dec == args.frames and syn_ok == args.frames and ok_map == args.frames and code['n'] == 1530))
    write_json('g4.json', payload)


# ----------------------------------------------------------------------------- timing
def stage_timing(args, ctx):
    ep = D.build_ep(ctx)
    seed_fn = dev_seed()
    load0 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    arms = ('F0', 'B', 'A3', 'EP', 'EPG')
    recs, shared = [], []
    for i in range(args.frames):
        fr = FRAME['timing'] + i
        res = D.frame_cells(ctx, ep, fr, list(TIMING_SNR), D.SP_RHOS, arms, [G_RHO_EP], seed_fn)
        shared.append(res['shared_seconds'])
        for snr in TIMING_SNR:
            recs.append(dict(snr=snr, frame=fr, snr_seconds=res['snr_seconds'][snr],
                             arm_seconds={k: v['seconds'] for k, v in res['cells'][snr].items() if v.get('status') == 'ok'},
                             statuses={k: v.get('status') for k, v in res['cells'][snr].items()},
                             fer={k: v.get('fer') for k, v in res['cells'][snr].items()}))
    load1 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    summary = {}
    for snr in TIMING_SNR:
        sel = [r for r in recs if r['snr'] == snr]
        keys = sorted(sel[0]['arm_seconds'])
        summary[str(snr)] = dict(n=len(sel), snr_seconds_mean=float(np.mean([r['snr_seconds'] for r in sel])),
                                 arm_seconds_mean={k: float(np.mean([r['arm_seconds'][k] for r in sel])) for k in keys},
                                 all_ok=bool(all(s == 'ok' for r in sel for s in r['statuses'].values())))
    shared_mean = float(np.mean(shared))
    grid = np.array(GRID_SNR, float)
    cost = np.interp(grid, TIMING_SNR, [summary[str(s)]['snr_seconds_mean'] for s in TIMING_SNR])
    frames = 2000
    quiet = frames * (shared_mean + float(cost.sum()))
    proj = dict(cells=frames * len(grid), frames_per_snr=frames, shared_seconds_per_frame=shared_mean, per_snr_cost=[float(x) for x in cost],
                quiet_core_hours=quiet / 3600., contention=CONTENTION, loaded_core_hours=quiet * CONTENTION / 3600., shards=NSH,
                wall_hours_at_shards=quiet * CONTENTION / 3600. / NSH)
    payload = provenance(args, ctx)
    payload.update(stage='timing', frames_per_arm=args.frames, rho_ep=G_RHO_EP, loadavg_before=load0, loadavg_after=load1, summary=summary,
                   projection=proj, passed=bool(all(v['all_ok'] for v in summary.values())), records=recs)
    write_json('timing.json', payload)
    print('projected loaded core-hours', proj['loaded_core_hours'], 'wall h at 30 shards', proj['wall_hours_at_shards'], flush=True)


def stage_timing_spg(args, ctx):
    """Timing of the SPG arm only: per-arm seconds (both rho) and the per-frame Gram; increment of the test-run projection."""
    ep = D.build_ep(ctx)
    seed_fn = dev_seed()
    load0 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    recs, grams = [], []
    for i in range(args.frames):
        fr = FRAME['timing_spg'] + i
        res = D.frame_cells(ctx, ep, fr, list(TIMING_SNR), D.SP_RHOS, ('SPG',), [G_RHO_EP], seed_fn)
        grams.append(res['spg_gram_seconds'])
        for snr in TIMING_SNR:
            cell = res['cells'][snr]
            recs.append(dict(snr=snr, frame=fr, seconds={k: v['seconds'] for k, v in cell.items() if v.get('status') == 'ok'},
                             statuses={k: v.get('status') for k, v in cell.items()}, fer={k: v.get('fer') for k, v in cell.items()}))
    load1 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    summary = {}
    for snr in TIMING_SNR:
        sel = [r for r in recs if r['snr'] == snr]
        keys = sorted(sel[0]['seconds'])
        summary[str(snr)] = dict(n=len(sel), arm_seconds_mean={k: float(np.mean([r['seconds'][k] for r in sel])) for k in keys},
                                 spg_both_rho_seconds_mean=float(np.mean([sum(r['seconds'].values()) for r in sel])),
                                 all_ok=bool(all(s == 'ok' for r in sel for s in r['statuses'].values())))
    gram_mean = float(np.mean(grams))
    grid = np.array(GRID_SNR, float)
    cost = np.interp(grid, TIMING_SNR, [summary[str(s)]['spg_both_rho_seconds_mean'] for s in TIMING_SNR])
    frames = 2000
    increment = frames * (gram_mean + float(cost.sum()))
    payload = provenance(args, ctx)
    payload.update(stage='timing_spg', frames_per_arm=args.frames, loadavg_before=load0, loadavg_after=load1, summary=summary,
                   gram_seconds_per_frame=gram_mean, per_snr_cost_both_rho=[float(x) for x in cost],
                   increment_quiet_core_hours=increment / 3600., passed=bool(all(v['all_ok'] for v in summary.values())), records=recs)
    write_json('timing_spg.json', payload)
    print('SPG increment quiet core-hours', increment / 3600., flush=True)


# ----------------------------------------------------------------------------- merge
def stage_merge(args):
    def load(n):
        return json.loads((OUT / n).read_text())
    g0, g1, g2, g3, g4, tm = (load(f'{n}.json') for n in ('g0', 'g1', 'g2', 'g3', 'g4', 'timing'))
    g5, g6, ts = load('g5.json'), load('g6.json'), load('timing_spg.json')
    now = {n: P.md5_file(HERE / f'{n}.py') for n in ('p2b_gates', 'p2b_driver', 'ep_rx', 'gen_fixed', 'p1_driver')}
    consistent = all(s['_code_md5'] == now for s in (g0, g1, g2, g4, g5, tm, ts))
    pr = tm['projection']
    inc = ts['increment_quiet_core_hours']
    quiet = pr['quiet_core_hours'] + inc
    with_spg = dict(spg_increment_quiet_core_hours=inc, quiet_core_hours=quiet, contention=pr['contention'], loaded_core_hours=quiet * pr['contention'],
                    shards=pr['shards'], wall_hours_at_shards=quiet * pr['contention'] / pr['shards'])
    gates = dict(P2B_G0=dict(passed=g0['passed'], p1_scenarios_identical=g0['p1_scenarios_identical'], checked=g0['p1_scenarios_checked'],
                             scenario_s_law=g0['scenario_s_law']),
                 P2B_G1=dict(passed=g1['passed'], frames=g1['frames'], max_symbol_error=g1['max_symbol_error'],
                             decoded=sum(r['decode_ok'] and r['info_errors'] == 0 for r in g1['rows'])),
                 P2B_G2=dict(passed=g2['passed'], frames=g2['frames'], max_doppler_error=g2['max_doppler_error'],
                             pilot_response_max_error=g2['pilot_response_max_error'], informational_with_data=g2['informational_with_data'],
                             delays_exact=sum(r['delays_exact'] for r in g2['rows'])),
                 P2B_G3=dict({k: v for k, v in g3.items() if not k.startswith('_')}),
                 P2B_G4={k: v for k, v in g4.items() if not k.startswith('_') and k not in ('construction',)},
                 P2B_G5={k: g5[k] for k in ('passed', 'frames', 'cells', 'decoded', 'max_first_round_symbol_error', 'first_round_hard_bit_errors',
                                            'cells_with_null_directions', 'min_operator_sv')},
                 P2B_G6={k: v for k, v in g6.items() if not k.startswith('_')},
                 timing=dict(passed=bool(tm['passed'] and ts['passed']), loadavg_before=tm['loadavg_before'], loadavg_after=tm['loadavg_after'],
                             summary=tm['summary'], projection=pr, spg_timing=dict(summary=ts['summary'], gram_seconds_per_frame=ts['gram_seconds_per_frame'],
                                                                                   loadavg_before=ts['loadavg_before'], loadavg_after=ts['loadavg_after']),
                             projection_with_spg=with_spg),
                 stage_code_md5_equals_current=bool(consistent))
    gates['all_pass'] = bool(all(gates[k]['passed'] for k in ('P2B_G0', 'P2B_G1', 'P2B_G2', 'P2B_G3', 'P2B_G4', 'P2B_G5', 'P2B_G6', 'timing')) and consistent)
    payload = dict(_argv=list(sys.argv), _config=dict(stage_files={p.name: P.md5_file(p) for p in sorted(OUT.glob('*.json')) if p.name != 'p2b_gates.json'},
                                                      entropy_dev=D.ENTROPY_DEV, domain_dev=D.DOMAIN_DEV, entropy_test=D.ENTROPY_TEST,
                                                      domain_test=D.DOMAIN_TEST, source_md5=g0['_config']['source_md5'],
                                                      environment=g0['_config']['environment']), _code_md5=now, gates=gates)
    write_json('p2b_gates.json', payload)
    (OUT / 'P2B_GATES.md').write_text(render_md(gates, now))
    print('all_pass =', gates['all_pass'])


def render_md(g, code):
    flag = lambda ok: 'PASS' if ok else 'FAIL'  # noqa: E731
    g0, g1, g2, g3, g4, tm = g['P2B_G0'], g['P2B_G1'], g['P2B_G2'], g['P2B_G3'], g['P2B_G4'], g['timing']
    g5, g6 = g['P2B_G5'], g['P2B_G6']
    law, pr = g0['scenario_s_law'], tm['projection_with_spg']
    L = ['# P2b gates (before any test-frame run)\n',
         f"Overall: **{flag(g['all_pass'])}**. Code md5: {code}. Dev entropy `{D.ENTROPY_DEV}` (domain 0x{D.DOMAIN_DEV:08X}); test entropy `{D.ENTROPY_TEST}` "
         f"(domain 0x{D.DOMAIN_TEST:08X}) is untouched.\n",
         '| gate | criterion | result |\n|---|---|---|',
         f"| P2b-G0 | P1 scenarios U, G bit-identical to the P1-era gen_fixed ({g0['checked']} frames); scenario S law: max delay <= 25, distinct delays, acceptance vs direct sampler | **{flag(g0['passed'])}** "
         f"identical: {g0['p1_scenarios_identical']}; S redraw rate {100 * law['redraw_rate']:.1f}% ({law['redraws_per_frame']:.3f} redraws/frame, first-try acceptance {100 * law['first_try_acceptance']:.2f}% vs direct {100 * law['direct_sampler_acceptance']:.2f}%, z = {law['z_vs_direct']:.2f}, KS p = {law['ks_span_p']:.3f}), max delay {law['max_delay']} |",
         f"| P2b-G1 | EP-genie, noiseless (sigma2 1e-10): all decoded, detector output = transmitted symbols | **{flag(g1['passed'])}** {g1['decoded']}/{g1['frames']} decoded, max |x_hat - x| {g1['max_symbol_error']:.1e} |",
         f"| P2b-G2 | estimator, noiseless pilot-only, {g2['frames']} frames: delays exact, Doppler within 0.05 | **{flag(g2['passed'])}** delays exact {g2['delays_exact']}/{g2['frames']}, max Doppler error {g2['max_doppler_error']:.4f}, closed-form response vs operator {g2['pilot_response_max_error']:.1e} |",
         f"| P2b-G3 | SP + EP arms reproduce themselves (two processes, 16 frames) and equal the rows stored before the shared LMMSE core | **{flag(g3['passed'])}** {g3['rows_a']} rows, mismatching {g3['mismatching_rows']}, regression mismatches {g3['regression_mismatching_rows']}/{g3['rows_ref']}, arms {g3['arms']} |",
         f"| P2b-G4 | LDPC n = 1530 round trip, 100 messages | **{flag(g4['passed'])}** decode {g4['decode_roundtrip_ok']}/{g4['messages']}, mapping {g4['mapping_roundtrip_ok']}/{g4['messages']}, k = {g4['k']} (rate {g4['rate']:.4f}) |",
         f"| P2b-G5 | SP-genie-LMMSE (report-only arm) on noiseless SP frames, {g5['frames']} frames x rho {{.3, .5}} | **{flag(g5['passed'])}** {g5['decoded']}/{g5['cells']} decoded (informational: first-round max |x_hat - x| {g5['max_first_round_symbol_error']:.2f}, first-round hard bit errors {g5['first_round_hard_bit_errors']}, "
         f"{g5['cells_with_null_directions']}/{g5['cells']} cells have operator singular values below the noise prior, min {g5['min_operator_sv']:.1e}) |",
         f"| P2b-G6 | determinism including the SPG arm (two processes, 16 frames, all arms) | **{flag(g6['passed'])}** {g6['rows_a']} rows, mismatching {g6['mismatching_rows']}, arms {g6['arms']} |",
         f"| timing | 16 frames per arm, 5.0 and 7.0 dB, loadavg {tm['loadavg_before']} -> {tm['loadavg_after']} (SPG probe {tm['spg_timing']['loadavg_before']} -> {tm['spg_timing']['loadavg_after']}) | **{flag(tm['passed'])}** "
         f"{pr['quiet_core_hours']:.1f} quiet / {pr['loaded_core_hours']:.1f} loaded core-hours (x{pr['contention']}; SPG adds {pr['spg_increment_quiet_core_hours']:.2f} quiet), {pr['wall_hours_at_shards']:.2f} h wall at {pr['shards']} shards |\n"]
    L.append('## Estimator with data present (informational, rho_EP = 0.1)\n')
    L.append('| SNR | path recall | energy recall | false paths / frame | median / p90 Doppler error |\n|---|---|---|---|---|')
    for snr, v in g2['informational_with_data'].items():
        L.append(f"| {int(snr) / 100:g} dB | {v['path_recall']:.3f} | {v['energy_recall']:.3f} | {v['false_paths_per_frame']:.3f} | {v['median_doppler_error']:.4f} / {v['p90_doppler_error']:.4f} |")
    L.append('\n## Timing (mean seconds per arm and per (frame, SNR) wall)\n')
    L.append('| SNR | n | wall | ' + ' | '.join(sorted(next(iter(tm['summary'].values()))['arm_seconds_mean'])) + ' |\n|---|---|---|' + '---|' * len(next(iter(tm['summary'].values()))['arm_seconds_mean']))
    for snr, v in tm['summary'].items():
        keys = sorted(v['arm_seconds_mean'])
        L.append(f"| {int(snr) / 100:g} | {v['n']} | {v['snr_seconds_mean']:.3f} | " + ' | '.join(f"{v['arm_seconds_mean'][k]:.3f}" for k in keys) + ' |')
    p0 = tm['projection']
    L.append(f"\nProjection before the SPG arm: {p0['cells']} cells; shared per-frame cost {p0['shared_seconds_per_frame']:.3f} s (SP bases, true operator, genie Gram); per-SNR cost interpolated between the probe SNRs: "
             f"{p0['quiet_core_hours']:.2f} quiet core-hours.")
    st = tm['spg_timing']
    L.append('\nSPG arm only (mean seconds per cell and rho; the per-frame Gram H^H H is counted in the shared cost): ' +
             '; '.join(f"{int(k) / 100:g} dB: " + ', '.join(f"{a} {t:.3f}" for a, t in v['arm_seconds_mean'].items()) for k, v in st['summary'].items()) +
             f"; Gram {st['gram_seconds_per_frame']:.3f} s per frame. Updated projection: {pr['quiet_core_hours']:.2f} quiet = {p0['quiet_core_hours']:.2f} + {pr['spg_increment_quiet_core_hours']:.2f} (SPG).\n")
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('g0', 'g1', 'g2', 'g3cmp', 'g4', 'g5', 'g6cmp', 'timing', 'timing_spg', 'merge'), required=True)
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--mc-frames', type=int, default=100000)
    p.add_argument('--dir-a', type=Path)
    p.add_argument('--dir-b', type=Path)
    p.add_argument('--dir-ref', type=Path)
    args = p.parse_args()
    if args.stage == 'merge':
        return stage_merge(args)
    if args.stage == 'g3cmp':
        return stage_g3cmp(args)
    if args.stage == 'g6cmp':
        return stage_g6cmp(args)
    ctx = P.load_context()
    {'g0': stage_g0, 'g1': stage_g1, 'g2': stage_g2, 'g4': stage_g4, 'g5': stage_g5, 'timing': stage_timing,
     'timing_spg': stage_timing_spg}[args.stage](args, ctx)


if __name__ == '__main__':
    main()
