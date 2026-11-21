#!/usr/bin/env python
"""Gates for the Zheng port (protocol.md I4 + A2), written to out/zport_gates/.  Run on deinlab, single thread (launch_zport_gates.sh).

  g1   ZP-G1 operator: (a) 20 integer-Doppler test channels on the production grid and (b) 20 fractional-Doppler channels (on the .25 grid and off-grid):
       sum_j h_j Xi_j x equals the physical CPP propagation (supplement_pilots.propagate_cpp) and physical_channel_matrix @ x to 1e-10;
       (c) the band (+-4 bins) truncation energy distribution over 200 P1 frames of each scenario.
  g2   ZP-G2 noiseless frames (20 P1 frames per scenario x rho .3 / .5): true path set and gains fed in as h (no estimation), MP + LDPC decodes every frame,
       for both delta readings (Z-adapted structure: fractional atoms, +-4 band); plus the integer-Doppler chain check of the Z-faithful structure.
  g5   ZP-G5 (A3, selection only): noiseless frames (20 per scenario x rho .3 / .5, both delta readings): the full Z-OMP receiver (no genie) selects on average >= 7 of the 8
       true delays (scenario average).  The decode outcome is reported as an informational line.
  g3   ZP-G3 frame identity with P1: for 16 frames the channel parameters, noise hash and codeword (info hash) equal the P1 rows.
  g4cmp ZP-G4 determinism across two processes (8 frames, all variants, bit-identical rows except seconds).
  timing  8 frames per variant at 5.0 and 7.0 dB, rho .3, scenario G; projection of the full port run at 30 shards with x1.5 contention vs the remaining budget.
  merge  out/zport_gates/zport_gates.json + ZPORT_GATES.md
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p1_driver as P  # noqa: E402
import zport_driver as Z  # noqa: E402
from zport_rx import ZPort  # noqa: E402

OUT = HERE / 'out' / 'zport_gates'
P1_ROWS = HERE / 'out' / 'p1'
TIMING_SNR = (500, 700)
CONTENTION = 1.5
NSH = 30
BUDGET_CORE_HOURS = 22.
GRID_SNR = (450, 500, 550, 600, 650, 700, 750, 800)
FRAMES_FULL = 1000
TOL = 1e-10


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
    Z.add_sources(ctx)
    return dict(_argv=list(sys.argv), _config=dict(args={k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}, p1_entropy=P.ENTROPY_HEX,
                                                   p1_domain=P.DOMAIN, source_md5=ctx.source_md5, environment=ctx.environment),
                _code_md5={n: P.md5_file(HERE / f'{n}.py') for n in ('zport_gates', 'zport_driver', 'zport_rx', 'p1_driver', 'gen_fixed')})


def zport(ctx):
    return ZPort(ctx.system.c1, ctx.system.c2, N=int(ctx.system.N_total))


def physical_output(ctx, x, l, nu, g):
    s = ctx.system
    wave = ctx.transform(x, s.c1, s.c2, inverse=True)
    return ctx.transform(ctx.propagate_cpp(wave, s.c1, np.asarray(l, int), np.asarray(nu, float), np.asarray(g, complex), prefix_length=int(s.l_max_cap)), s.c1, s.c2)


# ----------------------------------------------------------------------------- g1
def stage_g1(args, ctx):
    zp = zport(ctx)
    s = ctx.system
    n = int(s.N_total)
    rng = np.random.default_rng(12)
    rows = {}
    for tag in ('integer_grid', 'fractional_on_grid', 'fractional_off_grid'):
        errs, errs_mat = [], []
        for _ in range(args.channels):
            l = rng.choice(zp.l_max + 1, size=8, replace=False)
            if tag == 'integer_grid':
                nu = rng.integers(-2, 3, size=8).astype(float)
            elif tag == 'fractional_on_grid':
                nu = rng.choice([v for v in np.arange(-3., 3. + 1e-9, .25) if v != round(v)], size=8)
            else:
                nu = rng.uniform(-3, 3, size=8)
            g = (rng.standard_normal(8) + 1j * rng.standard_normal(8)) / np.sqrt(16)
            x = rng.standard_normal(n) + 1j * rng.standard_normal(n)
            ref = physical_output(ctx, x, l, nu, g)
            mine = zp.apply(x, l, nu, g)
            errs.append(float(np.abs(mine - ref).max() / np.abs(ref).max()))
            Hm = ctx.physical_channel_matrix(n, s.c1, s.c2, np.asarray(l, int), np.asarray(nu, float), np.asarray(g, complex), prefix_length=int(s.l_max_cap))
            errs_mat.append(float(np.abs(mine - Hm @ x).max() / np.abs(ref).max()))
        rows[tag] = dict(channels=args.channels, max_error_vs_cpp_propagation=max(errs), max_error_vs_physical_matrix=max(errs_mat),
                         passed=bool(max(errs) <= TOL and max(errs_mat) <= TOL))
    # integer-grid atoms are exactly the production grid: the atom operator of the Z-faithful grid is the physical single-path operator
    seed_fn = P.make_seed_fn()
    stats = {}
    for scenario in ('U', 'G'):
        vals = []
        for frame in range(args.frames):
            raw, _ = P.generate(ctx, scenario, .5, 4.5, frame, seed_fn)
            p = raw['params']
            vals.append(zp.truncated_fraction(p['l_i'], p['k_real'], p['g_i'], zp.band_frac))
        v = np.array(vals)
        stats[scenario] = dict(frames=len(v), mean=float(v.mean()), median=float(np.median(v)), p90=float(np.quantile(v, .9)), p99=float(np.quantile(v, .99)),
                               max=float(v.max()), min=float(v.min()))
    payload = provenance(args, ctx)
    payload.update(stage='g1', operator=rows, truncation_energy_fraction_band4=stats, tolerance=TOL, passed=bool(all(r['passed'] for r in rows.values())))
    write_json('g1.json', payload)


# ----------------------------------------------------------------------------- g2
def stage_g2(args, ctx):
    zp = zport(ctx)
    seed_fn = P.make_seed_fn()
    rows = []
    for scenario in ([args.scenario] if args.scenario else ['U', 'G']):
        for rho in (.3, .5):
            for frame in range(args.frames):
                raw, diag = P.generate(ctx, scenario, rho, 4.5, frame, seed_fn)
                x, yn = Z.impulse_frame(ctx, raw, rho)
                p = raw['params']
                for delta in (.1, .9):
                    zp.delta = delta
                    # (i) Z-adapted structure with the true off-grid paths: fractional atoms, +-4 band
                    t0 = time.perf_counter()
                    res = zp.run(yn, rho, 1e-10, 'frac', truth=(p['l_i'], p['k_real'], p['g_i']))
                    sc = Z.score(ctx, Z.decode(ctx, ZPort.llr_from_posterior(res['p_j'])), raw)
                    rows.append(dict(kind='adapted_true_paths', scenario=scenario, rho=rho, frame=frame, delta_new=delta, info_errors=sc['info_errors'],
                                     mp_iterations=res['iterations'], seconds=time.perf_counter() - t0, trunc_est=res['trunc_est']))
                    # (ii) Z-faithful chain on integer-Doppler channels (true integer atoms, no estimation)
                    nu_i = np.rint(p['k_real'])
                    xi_out = physical_output(ctx, x, p['l_i'], nu_i, p['g_i'])
                    res = zp.run(xi_out, rho, 1e-10, 'int', truth=(p['l_i'], nu_i, p['g_i']))
                    sc = Z.score(ctx, Z.decode(ctx, ZPort.llr_from_posterior(res['p_j'])), raw)
                    rows.append(dict(kind='faithful_integer_channel', scenario=scenario, rho=rho, frame=frame, delta_new=delta, info_errors=sc['info_errors'],
                                     mp_iterations=res['iterations'], seconds=0.))
    summary = {}
    for kind in ('adapted_true_paths', 'faithful_integer_channel'):
        for delta in (.1, .9):
            sel = [r for r in rows if r['kind'] == kind and r['delta_new'] == delta]
            summary[f'{kind}/delta{delta}'] = dict(cells=len(sel), decoded=sum(r['info_errors'] == 0 for r in sel), mean_mp_iterations=float(np.mean([r['mp_iterations'] for r in sel])))
    payload = provenance(args, ctx)
    payload.update(stage='g2', scenario=args.scenario, frames_per_scenario_rho=args.frames, receiver_sigma2=1e-10, summary=summary, rows=rows,
                   passed=bool(all(v['decoded'] == v['cells'] for v in summary.values())))
    write_json(f'g2_{args.scenario}.json' if args.scenario else 'g2.json', payload)


# ----------------------------------------------------------------------------- g5
def stage_g5(args, ctx):
    zp = zport(ctx)
    seed_fn = P.make_seed_fn()
    rows = []
    for rho in (.3, .5):
        for frame in range(args.frames):
            raw, diag = P.generate(ctx, args.scenario, rho, 4.5, frame, seed_fn)
            x, yn = Z.impulse_frame(ctx, raw, rho)
            true_l = set(int(l) for l in raw['params']['l_i'])
            for delta in (.1, .9):
                zp.delta = delta
                t0 = time.perf_counter()
                res = zp.run(yn, rho, 1e-10, 'frac', select='omp')
                sc = Z.score(ctx, Z.decode(ctx, ZPort.llr_from_posterior(res['p_j'])), raw)
                rows.append(dict(scenario=args.scenario, rho=rho, frame=frame, delta_new=delta, n_true_delays_hit=len(set(int(l) for l in res['ls']) & true_l),
                                 info_errors=sc['info_errors'], mp_iterations=res['iterations'], seconds=time.perf_counter() - t0))
    summary = {}
    for rho in (.3, .5):
        for delta in (.1, .9):
            sel = [r for r in rows if r['rho'] == rho and r['delta_new'] == delta]
            summary[f'rho{rho}/delta{delta}'] = dict(cells=len(sel), mean_true_delays_hit=float(np.mean([r['n_true_delays_hit'] for r in sel])),
                                                     decoded=sum(r['info_errors'] == 0 for r in sel), mean_mp_iterations=float(np.mean([r['mp_iterations'] for r in sel])))
    per_scenario_mean_hits = float(np.mean([r['n_true_delays_hit'] for r in rows]))
    passed = bool(per_scenario_mean_hits >= 7.)
    failures = [dict(rho=r['rho'], delta_new=r['delta_new'], frame=r['frame'], info_errors=r['info_errors'], mp_iterations=r['mp_iterations'], n_true_delays_hit=r['n_true_delays_hit'])
                for r in rows if r['info_errors'] > 0]
    payload = provenance(args, ctx)
    payload.update(stage='g5', scenario=args.scenario, frames_per_rho=args.frames, receiver_sigma2=1e-10, summary=summary, scenario_mean_true_delays_hit=per_scenario_mean_hits,
                   decoded_total=int(sum(r['info_errors'] == 0 for r in rows)), cells_total=len(rows), decode_failures=failures,
                   criterion='A3: Z-OMP selection recovers >= 7 of the 8 true delays on average over the 20 noiseless frames of the scenario (decode outcome is informational)', rows=rows, passed=passed)
    write_json(f'g5_{args.scenario}.json', payload)


# ----------------------------------------------------------------------------- g3
def p1_row(scenario, rho_pm, snr, frame):
    path = P1_ROWS / f'rows_shard{frame % 30:03d}.jsonl.gz'
    needle = f'"frame": {frame},'
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            if needle in line and f'"scenario": "{scenario}"' in line and f'"rho_permille": {rho_pm},' in line and f'"snr_centi_db": {snr},' in line:
                r = json.loads(line)
                if r['frame'] == frame and r['scenario'] == scenario and r['rho_permille'] == rho_pm and r['snr_centi_db'] == snr:
                    return r
    raise KeyError((scenario, rho_pm, snr, frame))


G3_KEYS = ('channel_seed', 'physical_gains_sha256', 'info_sha256', 'noise_sha256', 'truth_l', 'truth_k', 'truth_g2', 'n_paths', 'n_distinct_delays', 'gen_redraws', 'gen_flags')


def stage_g3(args, ctx):
    seed_fn = P.make_seed_fn()
    rows, bad = [], 0
    zp = zport(ctx)
    for scenario in ('U', 'G'):
        for rho in (.3, .5):
            for frame in range(args.frames):
                raw, diag = P.generate(ctx, scenario, rho, 4.5, frame, seed_fn)
                truth = ctx.hd.truth_from_raw(raw, diag)
                mine = P.truth_fields(ctx, truth, diag)
                ref = p1_row(scenario, int(round(rho * 1000)), 600, frame)
                diffs = [k for k in G3_KEYS if mine[k] != ref[k]]
                x, yn = Z.impulse_frame(ctx, raw, rho)
                data_same = bool(np.array_equal(x[1:], raw['data'][1:]) and abs(x[0] - raw['data'][0] - np.sqrt(rho * 1024)) < 1e-12)
                # the P1 codeword is reproduced by the same encoder from the P1 information bits
                from afdm_sp_joint_unrolled.e1_ldpc import encode
                coded_same = bool(np.array_equal(encode(ctx.code, raw['info']), raw['coded']))
                energy = float(np.vdot(x, x).real)
                rows.append(dict(scenario=scenario, rho=rho, frame=frame, differing_keys=diffs, data_symbols_equal_p1_apart_from_the_pilot=data_same, codeword_matches_encoder=coded_same,
                                 total_energy=energy, expected_energy_range=[1024 * .8, 1024 * 1.2]))
                bad += int(bool(diffs) or not data_same or not coded_same)
    payload = provenance(args, ctx)
    payload.update(stage='g3', frames_per_cell=args.frames, compared_keys=list(G3_KEYS), mismatching_cells=bad, cells=len(rows), rows=rows, passed=bool(bad == 0))
    write_json('g3.json', payload)


# ----------------------------------------------------------------------------- g4 compare
def load_rows_dir(d):
    out = {}
    for f in sorted(Path(d).glob('rows_shard*.jsonl')):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            out[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = r
    return out


def strip_timing(v):
    if isinstance(v, dict):
        return {k: strip_timing(x) for k, x in v.items() if 'seconds' not in k}
    if isinstance(v, list):
        return [strip_timing(x) for x in v]
    return v


def stage_g4cmp(args):
    a, b = load_rows_dir(args.dir_a), load_rows_dir(args.dir_b)
    same_keys = set(a) == set(b)
    diffs = [list(k) for k in sorted(a) if k in b and strip_timing(a[k]) != strip_timing(b[k])]
    variants = sorted(next(iter(a.values()))['variants']) if a else []
    payload = dict(_argv=list(sys.argv), stage='g4cmp', rows_a=len(a), rows_b=len(b), same_keys=bool(same_keys), mismatching_rows=len(diffs), mismatching_keys=diffs, variants=variants,
                   passed=bool(same_keys and not diffs and len(a) >= 8 and 'Zt' in variants and len(variants) == 7),
                   rows_md5={str(p): P.md5_file(p) for p in sorted(Path(args.dir_a).glob('rows_shard*.jsonl')) + sorted(Path(args.dir_b).glob('rows_shard*.jsonl'))})
    write_json('g4.json', payload)


# ----------------------------------------------------------------------------- timing
def stage_timing(args, ctx):
    zp = zport(ctx)
    seed_fn = P.make_seed_fn()
    load0 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    recs, overhead = [], []
    for i in range(args.frames):
        frame = 5000 + i                      # P1 streams, outside the 1000 port frames
        t0 = time.perf_counter()
        raw, diag = P.generate(ctx, 'G', .3, 4.5, frame, seed_fn)
        x, yn = Z.impulse_frame(ctx, raw, .3)
        truth = ctx.hd.truth_from_raw(raw, diag)
        P.truth_fields(ctx, truth, diag)
        overhead.append(time.perf_counter() - t0)
        for snr in TIMING_SNR:
            sigma2 = 10 ** (-snr / 100 / 10)
            y = yn + np.sqrt(sigma2) * raw['noise']
            t1 = time.perf_counter()
            cell = Z.run_cell(ctx, zp, raw, y, .3, sigma2, Z.VARIANTS)
            wall = time.perf_counter() - t1
            recs.append(dict(snr=snr, frame=frame, wall=wall, seconds={k: v['seconds'] for k, v in cell.items()},
                             zt_round2_seconds=cell['Zt']['round2_seconds'], fer={k: v['fer'] for k, v in cell.items()},
                             n_true_delays_hit={k: v['n_true_delays_hit'] for k, v in cell.items()}, mp_iterations={k: v['mp_iterations'] for k, v in cell.items()}))
    load1 = [float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
    summary = {}
    for snr in TIMING_SNR:
        sel = [r for r in recs if r['snr'] == snr]
        summary[str(snr)] = dict(n=len(sel), wall_mean=float(np.mean([r['wall'] for r in sel])),
                                 seconds_mean={k: float(np.mean([r['seconds'][k] for r in sel])) for k in Z.VARIANTS},
                                 zt_round2_seconds_mean=float(np.mean([r['zt_round2_seconds'] for r in sel])),
                                 fer={k: float(np.mean([r['fer'][k] for r in sel])) for k in Z.VARIANTS},
                                 mean_true_delays_hit={k: float(np.mean([r['n_true_delays_hit'][k] for r in sel])) for k in Z.VARIANTS},
                                 mean_mp_iterations={k: float(np.mean([r['mp_iterations'][k] for r in sel])) for k in Z.VARIANTS})
    grid = np.array(GRID_SNR, float)
    ov = float(np.mean(overhead))

    def cost(include_zt):
        # a cell runs Zf01, Zf09, Za01, Za09, Zo01, Zo09 and, if kept, the second Z-turbo round (round 1 = Za09)
        per = []
        for snr in TIMING_SNR:
            s = summary[str(snr)]
            per.append(sum(s['seconds_mean'][k] for k in ('Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09')) + (s['zt_round2_seconds_mean'] if include_zt else 0.))
        c = np.interp(grid, TIMING_SNR, per)
        cells = 2 * 2 * FRAMES_FULL
        quiet = cells * (ov + float(c.sum()))     # one generation per (frame, scenario, rho), one cell cost per SNR
        return quiet
    proj = {}
    for tag, inc in (('all_variants_incl_Zt', True), ('without_Zt', False)):
        q = cost(inc)
        proj[tag] = dict(quiet_core_hours=q / 3600., loaded_core_hours=q * CONTENTION / 3600., wall_hours_at_shards=q * CONTENTION / 3600. / NSH, shards=NSH,
                         contention=CONTENTION, within_budget=bool(q * CONTENTION / 3600. <= BUDGET_CORE_HOURS))
    proj['budget_core_hours'] = BUDGET_CORE_HOURS
    proj['generation_seconds_per_frame_scenario_rho'] = ov
    proj['drop_rule'] = 'I4: if the projection exceeds the remaining budget, drop Z-turbo first and keep the frame count'
    payload = provenance(args, ctx)
    payload.update(stage='timing', frames_per_variant=args.frames, scenario='G', rho=.3, loadavg_before=load0, loadavg_after=load1, summary=summary, projection=proj, records=recs,
                   passed=True)
    write_json('timing.json', payload)
    print('projection', json.dumps(proj), flush=True)


# ----------------------------------------------------------------------------- merge
def stage_merge(args):
    def load(n):
        return json.loads((OUT / n).read_text())
    g1, g3, g4, tm = (load(f'{n}.json') for n in ('g1', 'g3', 'g4', 'timing'))
    g5parts = [load(f'g5_{sc}.json') for sc in ('U', 'G')]
    g5 = dict(passed=all(x['passed'] for x in g5parts), summary={f"{x['scenario']}/{k}": v for x in g5parts for k, v in x['summary'].items()},
              scenario_mean={x['scenario']: x['scenario_mean_true_delays_hit'] for x in g5parts}, criterion=g5parts[0]['criterion'],
              decoded_total=sum(x['decoded_total'] for x in g5parts), cells_total=sum(x['cells_total'] for x in g5parts),
              decode_failures=[dict(f, scenario=x['scenario']) for x in g5parts for f in x['decode_failures']])
    parts = [load(f'g2_{sc}.json') for sc in ('U', 'G')]
    g2 = dict(passed=all(x['passed'] for x in parts), receiver_sigma2=parts[0]['receiver_sigma2'], summary={},
              _code_md5=parts[0]['_code_md5'], _config=parts[0]['_config'])
    for x in parts:
        for k, v in x['summary'].items():
            g2['summary'][f"{x['scenario']}/{k}"] = v
    now = {n: P.md5_file(HERE / f'{n}.py') for n in ('zport_gates', 'zport_driver', 'zport_rx', 'p1_driver', 'gen_fixed')}
    consistent = all(s['_code_md5'] == now for s in (g1, g3, tm, *parts, *g5parts))
    gates = dict(ZP_G1=dict(passed=g1['passed'], operator=g1['operator'], truncation=g1['truncation_energy_fraction_band4']),
                 ZP_G2=dict(passed=g2['passed'], summary=g2['summary'], receiver_sigma2=g2['receiver_sigma2']),
                 ZP_G5=g5,
                 ZP_G3=dict(passed=g3['passed'], cells=g3['cells'], mismatching_cells=g3['mismatching_cells'], compared_keys=g3['compared_keys']),
                 ZP_G4={k: v for k, v in g4.items() if not k.startswith('_') and k != 'mismatching_keys'},
                 timing=dict(loadavg_before=tm['loadavg_before'], loadavg_after=tm['loadavg_after'], summary=tm['summary'], projection=tm['projection']),
                 dropped_variants=dict(variants=['Zt'], reason='I4 budget rule: projection with Z-turbo exceeds the 22 core-hour budget; frame count kept',
                                       run_variants=['Zf01', 'Zf09', 'Za01', 'Za09', 'Zo01', 'Zo09']),
                 stage_code_md5_equals_current=bool(consistent))
    gates['all_pass'] = bool(all(gates[k]['passed'] for k in ('ZP_G1', 'ZP_G2', 'ZP_G3', 'ZP_G4', 'ZP_G5')) and consistent)
    payload = dict(_argv=list(sys.argv), _config=dict(stage_files={p.name: P.md5_file(p) for p in sorted(OUT.glob('*.json')) if p.name != 'zport_gates.json'},
                                                      p1_entropy=P.ENTROPY_HEX, p1_domain=P.DOMAIN, source_md5=g1['_config']['source_md5'], environment=g1['_config']['environment']),
                   _code_md5=now, gates=gates)
    write_json('zport_gates.json', payload)
    (OUT / 'ZPORT_GATES.md').write_text(render_md(gates, now))
    print('all_pass =', gates['all_pass'])


def render_md(g, code):
    flag = lambda ok: 'PASS' if ok else 'FAIL'  # noqa: E731
    g1, g2, g3, g4, tm, g5 = g['ZP_G1'], g['ZP_G2'], g['ZP_G3'], g['ZP_G4'], g['timing'], g['ZP_G5']
    pr = tm['projection']
    op = g1['operator']
    L = ['# Zheng port gates (before the port run)\n', f"Overall: **{flag(g['all_pass'])}**. Code md5: {code}.\n", '| gate | criterion | result |\n|---|---|---|',
         f"| ZP-G1 | sum_j h_j Xi_j x = physical CPP propagation to 1e-10 (integer grid, fractional on/off the .25 grid) | **{flag(g1['passed'])}** max errors vs CPP propagation / physical matrix: "
         + '; '.join(f"{k} {v['max_error_vs_cpp_propagation']:.1e} / {v['max_error_vs_physical_matrix']:.1e}" for k, v in op.items()) + ' |',
         f"| ZP-G2 | noiseless frames, true path set and gains fed in: MP + LDPC decodes every frame, both delta readings | **{flag(g2['passed'])}** "
         + '; '.join(f"{k}: {v['decoded']}/{v['cells']}" for k, v in g2['summary'].items()) + f" (receiver sigma2 {g2['receiver_sigma2']}) |",
         f"| ZP-G5 | {g5['criterion']} | **{flag(g5['passed'])}** scenario mean hits " + ', '.join(f"{k} {v:.2f}" for k, v in g5['scenario_mean'].items()) + '; '
         + '; '.join(f"{k}: hits {v['mean_true_delays_hit']:.2f}" for k, v in g5['summary'].items()) + ' |',
         f"| ZP-G3 | channel parameters, noise hash and codeword equal the P1 rows ({g3['cells']} cells) | **{flag(g3['passed'])}** mismatching {g3['mismatching_cells']} |",
         f"| ZP-G4 | determinism across two processes, all variants | **{flag(g4['passed'])}** {g4['rows_a']} rows, mismatching {g4['mismatching_rows']}, variants {g4['variants']} |\n"]
    L.append(f"Informational (G5 decode, noiseless frames, Z-OMP without genie): {g5['decoded_total']}/{g5['cells_total']} frame decodes succeed; failures: "
             + (', '.join(f"{f['scenario']} rho {f['rho']} delta_new {f['delta_new']} frame {f['frame']} ({f['info_errors']} info errors, MP stopped after {f['mp_iterations']} iterations by the zeta rule, "
                          f"{f['n_true_delays_hit']}/8 delays hit)" for f in g5['decode_failures']) or 'none') + '.\n')
    L.append(f"Budget decision (I4 rule): the projection with Z-turbo is {tm['projection']['all_variants_incl_Zt']['loaded_core_hours']:.1f} loaded core-hours, over the "
             f"{tm['projection']['budget_core_hours']:.0f} core-hour budget; **Z-turbo is dropped from the port run** (frame count unchanged), the run uses Zf01, Zf09, Za01, Za09, Zo01, Zo09 "
             f"({tm['projection']['without_Zt']['loaded_core_hours']:.1f} loaded core-hours, {tm['projection']['without_Zt']['wall_hours_at_shards']:.2f} h wall at {tm['projection']['without_Zt']['shards']} shards).  "
             "Z-turbo was still measured in the timing probe and kept in the G4 determinism check.\n")
    L.append('## Band truncation (+-4 bins) energy fraction of the true channel, P1 frames\n')
    L.append('| scenario | frames | mean | median | p90 | p99 | max |\n|---|---|---|---|---|---|---|')
    for k, v in g1['truncation'].items():
        L.append(f"| {k} | {v['frames']} | {v['mean']:.4f} | {v['median']:.4f} | {v['p90']:.4f} | {v['p99']:.4f} | {v['max']:.4f} |")
    L.append(f"\n## Timing (8 frames per variant, scenario G, rho .3; loadavg {tm['loadavg_before']} -> {tm['loadavg_after']})\n")
    L.append('| SNR | cell wall | ' + ' | '.join(Z.VARIANTS) + ' | Zt round 2 |\n|---|---|' + '---|' * (len(Z.VARIANTS) + 1))
    for snr, v in tm['summary'].items():
        L.append(f"| {int(snr) / 100:g} | {v['wall_mean']:.3f} | " + ' | '.join(f"{v['seconds_mean'][k]:.3f}" for k in Z.VARIANTS) + f" | {v['zt_round2_seconds_mean']:.3f} |")
    L.append('\nMean FER / mean true delays hit (of 8) in the probe: ' + '; '.join(f"{int(snr) / 100:g} dB: " + ', '.join(f"{k} {v['fer'][k]:.2f}/{v['mean_true_delays_hit'][k]:.1f}" for k in Z.VARIANTS)
                                                                         for snr, v in tm['summary'].items()))
    for tag in ('all_variants_incl_Zt', 'without_Zt'):
        p = pr[tag]
        L.append(f"\nProjection {tag}: {p['quiet_core_hours']:.2f} quiet / {p['loaded_core_hours']:.2f} loaded core-hours (x{p['contention']}), {p['wall_hours_at_shards']:.2f} h wall at {p['shards']} shards; "
                 f"within the {pr['budget_core_hours']:.0f} core-hour budget: {p['within_budget']}")
    return '\n'.join(L) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--stage', choices=('g1', 'g2', 'g3', 'g4cmp', 'g5', 'timing', 'merge'), required=True)
    p.add_argument('--frames', type=int, default=0)
    p.add_argument('--channels', type=int, default=20)
    p.add_argument('--scenario', choices=('U', 'G'), default=None)
    p.add_argument('--dir-a', type=Path)
    p.add_argument('--dir-b', type=Path)
    args = p.parse_args()
    if args.stage == 'merge':
        return stage_merge(args)
    if args.stage == 'g4cmp':
        return stage_g4cmp(args)
    ctx = P.load_context()
    {'g1': stage_g1, 'g2': stage_g2, 'g3': stage_g3, 'g5': stage_g5, 'timing': stage_timing}[args.stage](args, ctx)


if __name__ == '__main__':
    main()
