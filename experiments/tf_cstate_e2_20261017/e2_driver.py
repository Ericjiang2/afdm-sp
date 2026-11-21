#!/usr/bin/env python
"""E-2 driver (task 10-17-codelay-guard-e2; PROTOCOL.md = design.md + execution facts).

Arms (all start from the SAME captured F0 state; triggered units = F0 final syndrome != 0):
  A1   full Gamma  edits 2 passes 2 guard off      production CSTATE20
  A2   diag Gamma  edits 2 passes 2 guard off      E-1 control
  A3   full Gamma  edits 0 passes 2 guard off      no swaps
  A1g  full Gamma  edits 2 passes 2 guard all      co-delay atoms forbidden
  A2g  diag Gamma  edits 2 passes 2 guard all
  A2n  diag Gamma  edits 2 passes 2 guard neardup  only |D_N(dnu)| >= .5 co-delay atoms forbidden (report arm)
  A5   no geometry call: detector + LDPC rerun on r1 geometry/gains
  A7   literal third F0 round (receive(rounds=3)); G5: its round-0/1 state equals the captured one, every unit
Families: R = P1 generator on frames 3000..3999 (all keys get F0, no ledger); C = Jakes-4 same-delay Doppler clusters (e2_channels.py),
E2CJ domain, main frames 0..999, calibration frames 5000..5099 (F0 only), SNR grid from GRID.json.

Modes: gate / gate-merge (real P1 states, frames 0..19: G1 G2 G3 G4 G5) | cgate (CG1 CG2 CG3 with the receiver context) |
       calibrate / calibrate-merge (C family, F0 only -> GRID.json) | run (--family R|C; --smoke for smoke runs on other frames).
Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(HERE))
import e2_lib  # noqa: E402

e2_lib.prepare_paths()
import codelay_guard as cg  # noqa: E402
import e1_driver as e1d  # noqa: E402  (frozen E-1 driver: F0 state, A7/G5, arm records, ledger loader)
import e2_calib  # noqa: E402
import e2_channels as ch  # noqa: E402
import gs_driver as gd  # noqa: E402
from gs_driver import p1ctx  # noqa: E402

P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
E1_ROWS = EXPERIMENTS / 'tf_cstate_e1_20261017' / 'out' / 'main'
ALL_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
R_FRAMES = (3000, 4000)
C_FRAMES = ch.MAIN_FRAMES
CAL_FRAMES = ch.CALIBRATION_FRAMES
CAL_SNRS = e2_calib.CAL_SNRS
CAL_RHOS = (0.3, 0.5)
ARMS = ('A1', 'A2', 'A3', 'A1g', 'A2g', 'A2n', 'A5', 'A7')
ARM_SPECS = {
    'A1': dict(gamma_mode='full', max_edits=2, local_passes=2, guard='off'),
    'A2': dict(gamma_mode='diag', max_edits=2, local_passes=2, guard='off'),
    'A3': dict(gamma_mode='full', max_edits=0, local_passes=2, guard='off'),
    'A1g': dict(gamma_mode='full', max_edits=2, local_passes=2, guard='all'),
    'A2g': dict(gamma_mode='diag', max_edits=2, local_passes=2, guard='all'),
    'A2n': dict(gamma_mode='diag', max_edits=2, local_passes=2, guard='neardup'),
    'A5': None,
    'A7': None,
}
GUARDED = {'A1g': 'all', 'A2g': 'all', 'A2n': 'neardup'}
GEOMETRY_STAGES = e1d.GEOMETRY_STAGES
CHECKED_ARMS_G1 = ('A1', 'A2', 'A3')  # arms that exist, with the same parameters, in E-1


# ----------------------------------------------------------------------------- provenance
def load_kernels():
    e2_lib.prepare_paths()
    import geometry_validation_guard as k2
    import geometry_validation_variant as k1
    return k1, k2


def check_frozen_md5(ctx):
    """Every file listed in SOURCE_MD5.txt must have the recorded md5 (loaded module of the same stem preferred, else the file on disk)."""
    results, bad = {}, []
    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        digest, rel = line.split()
        path = EXPERIMENTS / rel
        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
        if loaded is not None:
            actual, how = loaded, 'loaded-module'
        elif path.exists():
            actual, how = e2_lib.md5_file(path), 'file'
        else:
            actual, how = None, 'absent'
        results[rel] = dict(expected=digest, actual=actual, via=how)
        if actual is None:
            results[rel]['status'] = 'unchecked'
        elif actual != digest:
            results[rel]['status'] = 'MISMATCH'
            bad.append(rel)
        else:
            results[rel]['status'] = 'ok'
    if bad:
        raise RuntimeError(f'frozen source md5 mismatch: {bad}')
    return results


def own_md5():
    names = ('e2_driver.py', 'e2_lib.py', 'e2_channels.py', 'codelay_guard.py', 'geometry_validation_guard.py', 'e2_agg.py', 'PROTOCOL.md',
             'SOURCE_MD5.txt')
    return {n: e2_lib.md5_file(HERE / n) for n in names if (HERE / n).exists()}


def write_config(out, shard, argv, args, ctx, extra=None):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    cfg = dict(vars(args), out=str(args.out), arm_specs=ARM_SPECS, arms=ARMS, guards=GUARDED,
               neardup_threshold=cg.NEARDUP_THRESHOLD, family_R=dict(entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN),
               family_C=dict(entropy=ch.E2CJ_ENTROPY, domain=ch.E2CJ_DOMAIN, config='J4 (lambda 4, per-ray uniform theta)'),
               schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; branch as E-1 (scalar_joint iterations=20 damping=.3 '
                        'joint, prior=r1_check; decoder maxiter=50; reopen strategy=compact grid_step=.25 chunk_size=64 local_halfwidth=.75 '
                        'local_max_evals=16 duplicate_tolerance=1e-6 top_k=20 ridge=sigma2 max_delay=system.l_max_cap doppler=[-3,3])',
               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment, **(extra or {}))
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- the E-2 branch (E-1 run_branch + the guard keyword)
def run_branch(ctx, kvar, obs, arrays, arm):
    """e1_driver.run_branch with the per-arm guard.  A5 skips geometry entirely."""
    from messages import moments
    from physical import Channel, daft

    spec, system, native = ARM_SPECS[arm], ctx.system, ctx.native
    stamp = time.perf_counter()
    app = np.clip(arrays['r1_app'], -20, 20)
    check = np.clip(arrays['r1_check'], -20, 20)
    if spec is None:
        if len(arrays['r1_delays']) != len(arrays['r1_gains']):
            raise ValueError('native physical slot count differs')
        message_end = time.perf_counter()
        channel = Channel(len(obs['y']), system.c1, system.c2, arrays['r1_delays'], arrays['r1_dopplers'], arrays['r1_gains'])
        channel_end = time.perf_counter()
        result, initial = None, None
        stages = dict(message_handling=message_end - stamp, y_transform=0., **{k: 0. for k in GEOMETRY_STAGES},
                      geometry_wrapper_overhead=0., wrapper_validation=0., channel_construction=channel_end - message_end)
        mu = v = None
    else:
        mu, v, _ = moments(app, 1 - system.rho)
        initial = [kvar.Path(int(delay), float(nu)) for delay, nu in zip(arrays['r1_delays'], arrays['r1_dopplers'])]
        if len(initial) != len(arrays['r1_gains']):
            raise ValueError('native physical slot count differs')
        message_end = time.perf_counter()
        Y = daft(obs['y'], system.c1, system.c2, True)
        transform_end = time.perf_counter()
        result = kvar.reopen_geometry(
            Y, obs['pilot'] + mu, v, initial, c1=system.c1, c2=system.c2, ridge=float(obs['sigma2']),
            max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3., grid_step=.25, max_edits=spec['max_edits'], chunk_size=64,
            local_passes=spec['local_passes'], local_halfwidth=.75, local_max_evals=16, duplicate_tolerance=1e-6, top_k=20,
            strategy='compact', gamma_mode=spec['gamma_mode'], codelay_guard=spec['guard'])
        geometry_end = time.perf_counter()
        if len(result.paths) != len(initial):
            raise ValueError('geometry changed physical slot count')
        stage = result.diagnostics['stage_timing']
        exclusive = stage['exclusive_seconds']
        if set(exclusive) != set(GEOMETRY_STAGES) or any(not np.isfinite(x) or x < 0 for x in exclusive.values()):
            raise ValueError('kernel exclusive-stage classification differs')
        if not np.isclose(sum(exclusive.values()), stage['total_seconds'], rtol=0, atol=1e-6):
            raise ValueError('kernel exclusive stages do not sum to geometry total')
        overhead = geometry_end - transform_end - stage['total_seconds']
        if overhead < 0:
            raise ValueError('kernel stage total exceeds wrapper geometry wall time')
        validation_end = time.perf_counter()
        channel = Channel(len(obs['y']), system.c1, system.c2, [p.delay for p in result.paths], [p.doppler for p in result.paths],
                          result.gains)
        channel_end = time.perf_counter()
        stages = dict(message_handling=message_end - stamp, y_transform=transform_end - message_end, **exclusive,
                      geometry_wrapper_overhead=overhead, wrapper_validation=validation_end - geometry_end,
                      channel_construction=channel_end - validation_end)
    detector = native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'], pd=1 - system.rho, prior=check,
                                   iterations=20, damping=.3, gain_mode='joint')
    tf_end = time.perf_counter()
    decoder = native.decoder_messages(ctx.code, np.clip(detector['extrinsic'], -20, 20), maxiter=50)
    decision_end = time.perf_counter()
    stages.update(tf=tf_end - channel_end, ldpc=decision_end - tf_end)
    decision = decision_end - stamp
    if not np.isclose(sum(stages.values()), decision, rtol=0, atol=1e-7):
        raise ValueError('decision-ready exclusive stage sum differs')
    return dict(result=result, detector=detector, decoder=decoder, app_input=app, check_prior=check, ce_mu=mu, ce_variance=v,
                initial_paths=initial, exclusive_stages=stages, branch_decision_seconds=decision)


def run_arm(ctx, kvar, obs, arrays, arm):
    return e1d.run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)


def guard_holds(delays, dopplers, n, mode):
    """Final-geometry guard invariant (G2): 'all' -> unique delays; 'neardup' -> no co-delay pair with |D_N| >= .5."""
    if mode == 'off':
        return True
    pairs = [(i, j) for i in range(len(delays)) for j in range(i + 1, len(delays)) if delays[i] == delays[j]]
    if mode == 'all':
        return not pairs
    return all(float(cg.abs_dn(np.array([dopplers[i] - dopplers[j]]), n)[0]) < cg.NEARDUP_THRESHOLD for i, j in pairs)


# ----------------------------------------------------------------------------- one unit (shared by run / gate / smoke)
def process_key(ctx, kvar, obs, truth, meta, f0_pack, arms=ARMS, cluster=None):
    """Row for one key: F0 fields always; the arms (from the SAME captured F0 state) only when F0 is triggered."""
    dec0, arrays, syn, f0_seconds = f0_pack
    f0_info = gd.score(ctx, dec0['decoded'], truth)
    row = dict(meta, f0=dict(syndrome=int(syn), info_errors=int(f0_info), decoded_sha256=gd.bits_sha(dec0['decoded']),
                             ldpc_iters=int(dec0['iterations']), seconds=float(f0_seconds)), triggered=bool(syn != 0), arms={})
    if syn == 0:
        return row
    row['r1'] = dict(delays=[int(x) for x in np.asarray(arrays['r1_delays'])], dopplers=[float(x) for x in np.asarray(arrays['r1_dopplers'])])
    row['truth'] = dict(delays=[int(x) for x in np.asarray(truth['l_i'])], dopplers=[float(x) for x in np.asarray(truth['k_real'])],
                        gains=[[float(g.real), float(g.imag)] for g in np.asarray(truth['g_i'], complex)])
    if cluster is not None:
        row['truth'].update(rays_per_tap=[int(x) for x in cluster['rays_per_tap']], tap_delays=[int(x) for x in cluster['tap_delays']])
    row['g5_ok'] = False
    n = len(obs['y'])
    for arm in arms:
        try:
            br = run_arm(ctx, kvar, obs, arrays, arm)
            if arm == 'A7':
                rec = e1d.a7_record(ctx, truth, br, arrays, f0_seconds)
                row['g5_ok'], row['g5_mismatch'], row['g5_keys'] = bool(not br['g5_diff']), br['g5_diff'][:3], len(br['g5_keys'])
            else:
                rec = e1d.arm_record(ctx, truth, br, arrays)
                if arm in GUARDED:
                    rec['guard_ok'] = bool(guard_holds(rec['final_delays'], rec['final_dopplers'], n, GUARDED[arm]))
            row['arms'][arm] = rec
        except Exception as error:  # recorded, never silently dropped
            row['arms'][arm] = e1d.err_record(error)
    row['guard_ok'] = all(row['arms'].get(a, {}).get('guard_ok', False) for a in GUARDED)
    return row


def write_row(handle, row):
    handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def key_of(row):
    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])


# ----------------------------------------------------------------------------- key generators for the two families
def r_cells(ctx, frame, snr_cells):
    """All (scenario, rho) cells of one P1 frame: yields (meta, obs, truth, gen_seconds, cluster)."""
    for scenario in gd.SCENARIOS:
        for rho in (0.3, 0.5):
            g0 = time.perf_counter()
            raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
            gen_seconds = time.perf_counter() - g0
            for k, snr in enumerate(snr_cells):
                raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                meta = dict(family='R', scenario=scenario, rho=float(rho), rho_permille=int(round(rho * 1000)), snr_centi_db=int(snr),
                            snr_db=snr / 100, frame=int(frame), sigma2=float(raw['sigma2']), gen_seconds=gen_seconds if k == 0 else 0.)
                yield meta, obs, truth, None


def c_cells(ctx, frame, grid):
    """All (rho, snr) cells of one cluster frame; ``grid`` maps rho -> list of SNR (dB, ints/floats)."""
    g0 = time.perf_counter()
    fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, frame)
    geometry_seconds = time.perf_counter() - g0
    seed_fn = ch.make_seed_fn()
    first = True
    for rho in (0.3, 0.5):
        snrs = grid.get(rho) or []
        if not snrs:
            continue
        g1 = time.perf_counter()
        msg = ch.cluster_message(ctx, seed_fn, rho, frame)
        raw_base, diag = ch.cluster_base(ctx, fg, msg)
        gen_seconds = time.perf_counter() - g1 + (geometry_seconds if first else 0.)
        first = False
        for k, snr_db in enumerate(snrs):
            raw = ch.at_snr(raw_base, float(snr_db))
            obs = ctx.hd.observe(raw, rho, float(snr_db))
            truth = ctx.hd.truth_from_raw(raw, diag)
            meta = dict(family='C', scenario='J4', rho=float(rho), rho_permille=int(round(rho * 1000)), snr_centi_db=int(round(snr_db * 100)),
                        snr_db=float(snr_db), frame=int(frame), sigma2=float(raw['sigma2']), gen_seconds=gen_seconds if k == 0 else 0.)
            yield meta, obs, truth, raw['cluster']


# ----------------------------------------------------------------------------- run mode
def parse_grid(args):
    if args.smoke_snr:
        return {0.3: [float(x) for x in args.smoke_snr.split(',')], 0.5: [float(x) for x in args.smoke_snr.split(',')]}, None
    grid = json.loads(Path(args.grid).read_text())
    out = {}
    for rho in (0.3, 0.5):
        e = grid['rho'][str(rho)]
        out[rho] = [] if e['status'] != 'OK' else [float(x) for x in e['grid_db']]
    return out, grid


def run_mode(args, argv):
    lo, hi = R_FRAMES if args.family == 'R' else C_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not args.smoke and not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'family {args.family} main run frames must lie in [{lo}, {hi}); use --smoke for other frames')
    if args.smoke and args.family == 'C' and (f_lo < 9000 and not args.smoke_any_frames):
        raise ValueError('C smoke frames must be >= 9000 (disjoint from calibration 5000..5099 and main 0..999)')
    ctx = p1ctx.load()
    _, kvar = load_kernels()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    grid_by_rho, grid_doc = (None, None)
    if args.family == 'C':
        grid_by_rho, grid_doc = parse_grid(args)
        if not any(grid_by_rho.values()):
            raise SystemExit('C family: no informative rho in GRID.json; nothing to run (D3 = UNINFORMATIVE)')
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    write_config(out, args.shard, argv, args, ctx, extra=dict(smoke_only=bool(args.smoke), grid_by_rho={str(k): v for k, v in (grid_by_rho or {}).items()},
                                                              grid_md5=None if not args.grid or args.smoke else e2_lib.md5_file(args.grid)))
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    frames = list(range(f_lo, f_hi))[args.shard::args.nshard]
    started = time.perf_counter()
    n_rows = n_trig = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            if args.max_triggered and n_trig >= args.max_triggered:
                break
            gen = r_cells(ctx, frame, snr_cells) if args.family == 'R' else c_cells(ctx, frame, grid_by_rho)
            for meta, obs, truth, cluster in gen:
                k = key_of(meta)
                if k in done:
                    continue
                if args.max_triggered and n_trig >= args.max_triggered:
                    break
                if args.smoke:
                    meta['smoke'] = True
                row = process_key(ctx, kvar, obs, truth, meta, e1d.f0_state(ctx, obs), cluster=cluster)
                write_row(handle, row)
                n_rows += 1
                n_trig += int(row['triggered'])
                print(f"[{time.perf_counter() - started:8.1f}s] {k} trig={row['triggered']} f0_err={row['f0']['info_errors']} "
                      + ' '.join(f"{a}:{r.get('info_errors', 'ERR')}" for a, r in row['arms'].items()), flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_rows} keys ({n_trig} triggered) in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- calibrate (C family, F0 only)
def calibrate_mode(args, argv):
    lo, hi = CAL_FRAMES
    f_lo, f_hi = args.frame_offset, args.frame_offset + args.frames
    if not (lo <= f_lo and f_hi <= hi):
        raise ValueError(f'calibration frames must lie in [{lo}, {hi})')
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx, extra=dict(candidate_snr_db=list(CAL_SNRS), rule='PROTOCOL.md section 3 (design 3)'))
    jsonl = out / f'cal_rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    frames = list(range(f_lo, f_hi))[args.shard::args.nshard]
    started = time.perf_counter()
    with jsonl.open('a') as handle:
        for frame in frames:
            grid = {0.3: list(CAL_SNRS), 0.5: list(CAL_SNRS)}
            for meta, obs, truth, cluster in c_cells(ctx, frame, grid):
                if key_of(meta) in done:
                    continue
                dec0, arrays, syn, secs = e1d.f0_state(ctx, obs)
                info = gd.score(ctx, dec0['decoded'], truth)
                row = dict(meta, f0=dict(syndrome=int(syn), info_errors=int(info), seconds=float(secs)), fer=int(info > 0))
                write_row(handle, row)
                print(f"[{time.perf_counter() - started:8.1f}s] {key_of(meta)} fer={row['fer']}", flush=True)
    print(f'calibration shard {args.shard}/{args.nshard} done in {time.perf_counter() - started:.1f}s', flush=True)


def calibrate_merge(args):
    rows = []
    for p in sorted(glob.glob(str(args.out / 'cal_rows_shard*.jsonl'))):
        rows += [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
    lo, hi = CAL_FRAMES
    want = {(0.3, s, f) for s in CAL_SNRS for f in range(lo, hi)} | {(0.5, s, f) for s in CAL_SNRS for f in range(lo, hi)}
    got = [(r['rho'], int(round(r['snr_db'])), r['frame']) for r in rows]
    if len(got) != len(set(got)) or set(got) != want:
        raise SystemExit(f'calibration incomplete or duplicated: {len(set(got))} of {len(want)} cells')
    doc = dict(rule='smallest candidate SNR with F0 FER <= .95 -> s0; grid {s0, s0+2, s0+4, s0+6} capped at 20 dB; F0 FER(20 dB) > .95 -> UNINFORMATIVE',
               fer_metric='fraction of calibration frames with >= 1 information-bit error after F0 (rounds=2)', frames=[lo, hi], rho={},
               n_rows=len(rows), rows_md5={Path(p).name: e2_lib.md5_file(p) for p in sorted(glob.glob(str(args.out / 'cal_rows_shard*.jsonl')))})
    for rho in CAL_RHOS:
        fer = {s: float(np.mean([r['fer'] for r in rows if r['rho'] == rho and int(round(r['snr_db'])) == s])) for s in CAL_SNRS}
        doc['rho'][str(rho)] = dict(fer_by_snr={str(s): v for s, v in fer.items()}, **e2_calib.decide_grid(fer))
    (args.out / 'GRID.json').write_text(json.dumps(doc, indent=1) + '\n')
    print(json.dumps(doc['rho'], indent=1))


# ----------------------------------------------------------------------------- gate mode (real P1 states, frames 0..19)
def load_e1_rows(e1_dir, frames):
    out = {}
    for p in sorted(glob.glob(str(Path(e1_dir) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if r['frame'] in frames:
                    out[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = {a: x['decoded_sha256'] for a, x in r['arms'].items()}
    return out


def top1(res):
    t = res.global_trace[0]['selected'] if res is not None and res.global_trace else None
    return None if t is None else (t['slot'], t['replacement']['delay'], t['replacement']['doppler'])


def decision_differs(a, b):
    ra, rb = a['result'], b['result']
    return bool(sorted(p.delay for p in ra.paths) != sorted(p.delay for p in rb.paths) or [e['new'] for e in ra.edits] != [e['new'] for e in rb.edits]
                or top1(ra) != top1(rb) or gd.bits_sha(a['decoder']['decoded']) != gd.bits_sha(b['decoder']['decoded']))


def gate_mode(args, argv):
    ctx = p1ctx.load()
    k1, k2 = load_kernels()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    ledger = e1d.load_ledger(args.p1_rows, set(frames), set(snr_cells))
    e1rows = load_e1_rows(args.e1_rows, set(frames))
    records, g3_done, started = [], 0, time.perf_counter()
    for frame in frames:
        for meta, obs, truth, _ in r_cells(ctx, frame, snr_cells):
            k = key_of(meta)
            led = ledger[k]
            pack = e1d.f0_state(ctx, obs)
            dec0, arrays, syn, _ = pack
            trig = syn != 0
            rec = dict(key=list(k), triggered=bool(trig), ledger_triggered=led['triggered'], f0_syndrome=int(syn), trigger_match=bool(trig == led['triggered']),
                       f0_sha_match=bool(gd.bits_sha(dec0['decoded']) == led['f0_sha']))
            # G1 (every state, triggered and not): guard 'off' == E-1 variant for A1/A2/A3 (E-1 itself == production, E-1 G1)
            g1 = {}
            for arm in CHECKED_ARMS_G1:
                x = e1d.run_branch(ctx, k1, obs, arrays, arm)
                y = run_branch(ctx, k2, obs, arrays, arm)
                g1[arm] = not e2_lib.deep_equal(e1d.branch_core(x), e1d.branch_core(y))
                if arm == 'A1':
                    a1 = y
            rec['g1'] = g1
            # G4: R pipeline vs ledger / E-1 rows
            rec['ledger_sha_match'] = bool(gd.bits_sha(a1['decoder']['decoded'] if trig else dec0['decoded']) == led['b_sha'])
            if trig:
                a2 = run_branch(ctx, k2, obs, arrays, 'A2')
                e1r = e1rows.get(k, {})
                rec['a1_vs_e1_row'] = bool(gd.bits_sha(a1['decoder']['decoded']) == e1r.get('A1'))
                rec['a2_vs_e1_row'] = bool(gd.bits_sha(a2['decoder']['decoded']) == e1r.get('A2'))
                # G2: guard invariants + decision change
                n = len(obs['y'])
                g2 = {}
                brs = {a: run_branch(ctx, k2, obs, arrays, a) for a in GUARDED}
                for arm, mode in GUARDED.items():
                    res = brs[arm]['result']
                    g2[f'{arm}_guard_ok'] = bool(guard_holds([p.delay for p in res.paths], [p.doppler for p in res.paths], n, mode))
                g2['a2g_differs_from_a2'] = decision_differs(brs['A2g'], a2)
                g2['a1g_differs_from_a1'] = decision_differs(brs['A1g'], a1)
                g2['a2n_differs_from_a2'] = decision_differs(brs['A2n'], a2)
                g2['a2n_differs_from_a2g'] = decision_differs(brs['A2n'], brs['A2g'])
                rec['g2'] = g2
                # G3 / G5: all 8 arms twice, bitwise
                if g3_done < args.g3_max:
                    g3 = {}
                    for arm in ARMS:
                        x, y = run_arm(ctx, k2, obs, arrays, arm), run_arm(ctx, k2, obs, arrays, arm)
                        g3[arm] = not e2_lib.deep_equal(e1d.branch_core(x), e1d.branch_core(y))
                        if arm == 'A7':
                            rec['g5_ok'] = bool(not x['g5_diff'] and not y['g5_diff'])
                            rec['g5_keys'] = len(x['g5_keys'])
                    rec['g3'] = g3
                    g3_done += 1
            records.append(rec)
        print(f'[{time.perf_counter() - started:8.1f}s] frame {frame} gate records {len(records)}', flush=True)
    (out / f'gate_shard{args.shard:03d}.json').write_text(json.dumps(records) + '\n')
    print(f'gate shard {args.shard}: {len(records)} states, {sum(r["triggered"] for r in records)} triggered', flush=True)


def gate_merge(args):
    recs = []
    for p in sorted(args.out.glob('gate_shard*.json')):
        recs += json.loads(p.read_text())
    trig = [r for r in recs if r['triggered']]
    g2 = [r['g2'] for r in trig]
    g3 = [r['g3'] for r in trig if 'g3' in r]
    g5 = [r['g5_ok'] for r in trig if 'g5_ok' in r]
    gates = dict(n_states=len(recs), n_triggered=len(trig), n_untriggered=len(recs) - len(trig))
    gates['G1'] = dict(states=len(recs), per_arm_identical={a: sum(r['g1'][a] for r in recs) for a in CHECKED_ARMS_G1},
                       note='guard off == E-1 variant (A1, A2, A3), all states incl. untriggered; E-1 variant == production (E-1 G1)')
    gates['G1']['pass_'] = bool(len(recs) >= 640 and len(trig) >= 1 and len(recs) > len(trig)
                                and all(v == len(recs) for v in gates['G1']['per_arm_identical'].values()))
    gates['G2'] = dict(triggered_states=len(g2), A1g_guard_ok=sum(x['A1g_guard_ok'] for x in g2), A2g_guard_ok=sum(x['A2g_guard_ok'] for x in g2),
                       A2n_guard_ok=sum(x['A2n_guard_ok'] for x in g2), a2g_differs_from_a2=sum(x['a2g_differs_from_a2'] for x in g2),
                       a1g_differs_from_a1=sum(x['a1g_differs_from_a1'] for x in g2), a2n_differs_from_a2=sum(x['a2n_differs_from_a2'] for x in g2),
                       a2n_differs_from_a2g=sum(x['a2n_differs_from_a2g'] for x in g2))
    G2 = gates['G2']
    G2['pass_'] = bool(G2['triggered_states'] >= 8 and G2['A1g_guard_ok'] == G2['A2g_guard_ok'] == G2['A2n_guard_ok'] == G2['triggered_states']
                       and G2['a2g_differs_from_a2'] >= 8)
    gates['G3'] = dict(states=len(g3), per_arm_identical={a: sum(x[a] for x in g3) for a in ARMS})
    gates['G3']['pass_'] = bool(len(g3) >= 1 and all(v == len(g3) for v in gates['G3']['per_arm_identical'].values()))
    gates['G4'] = dict(states=len(recs), trigger_match=sum(r['trigger_match'] for r in recs), f0_sha_match=sum(r['f0_sha_match'] for r in recs),
                       ledger_sha_match=sum(r['ledger_sha_match'] for r in recs), triggered=len(trig),
                       a1_vs_e1_row=sum(r['a1_vs_e1_row'] for r in trig), a2_vs_e1_row=sum(r['a2_vs_e1_row'] for r in trig))
    G4 = gates['G4']
    G4['pass_'] = bool(G4['states'] >= 1 and G4['trigger_match'] == G4['f0_sha_match'] == G4['ledger_sha_match'] == G4['states']
                       and G4['a1_vs_e1_row'] == G4['a2_vs_e1_row'] == G4['triggered'])
    gates['G5'] = dict(states=len(g5), identical=sum(g5), pass_=bool(len(g5) >= 1 and all(g5)))
    gates['all_pass'] = all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4', 'G5'))
    (args.out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


# ----------------------------------------------------------------------------- cgate (CG1-CG3 with the receiver context)
def cgate_mode(args, argv):
    ctx = p1ctx.load()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    s = ctx.system
    n = int(s.N_total)
    from physical import Channel
    seed_fn = ch.make_seed_fn()
    res = dict(label='CG1-CG3 with the receiver context', entropy=ch.E2CJ_ENTROPY, domain=ch.E2CJ_DOMAIN, source_md5=ctx.source_md5)
    # CG1: ||H||_F^2/N = 1 within 1e-9 on 50 frames (dense matrix of the pipeline operator, ctx.physical_channel_matrix)
    worst, before = 0., []
    for f in range(50):
        fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)   # raises if |power - 1| >= 1e-9
        worst = max(worst, abs(fg['power_after'] - 1.))
        before.append(fg['power_before'])
    res['CG1'] = dict(frames=50, worst_abs_deviation_pipeline_matrix=worst, power_before_renorm=dict(min=float(min(before)), max=float(max(before))), pass_=bool(worst < 1e-9))
    # CG2: Channel.apply vs dense pipeline matrix vs direct CPP propagation (20 frames)
    rng = np.random.default_rng(5)
    w1 = w2 = 0.
    for f in range(20):
        fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
        p = fg['paths']
        x = rng.normal(size=n) + 1j * rng.normal(size=n)
        a = Channel(n, s.c1, s.c2, p['l_i'], p['k_real'], p['g_i']).apply(x)
        b = fg['h'] @ x
        c = ctx.transform(ctx.propagate_cpp(ctx.transform(x, s.c1, s.c2, inverse=True), s.c1, p['l_i'], p['k_real'], p['g_i'], prefix_length=int(s.l_max_cap)), s.c1, s.c2)
        w1 = max(w1, float(np.linalg.norm(a - b) / np.linalg.norm(b)))
        w2 = max(w2, float(np.linalg.norm(c - b) / np.linalg.norm(b)))
    res['CG2'] = dict(frames=20, worst_rel_error_apply_vs_dense=w1, worst_rel_error_cpp_vs_dense=w2, pass_=bool(max(w1, w2) < 1e-9))
    # CG3: rest of the P1 frame is channel-independent; descriptive tap statistics
    diffs, observe_checked = [], 0
    for f in (0, 1, 2, 500):
        for rho in (0.3, 0.5):
            raw_p1, _ = p1ctx.p1_driver.generate(ctx, 'U', rho, 4.5, f, seed_fn)
            msg = ch.cluster_message(ctx, seed_fn, rho, f)
            geom = ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
            for key in ('info', 'coded', 'data', 'pilot', 'noise'):
                if not np.array_equal(np.asarray(raw_p1[key]), np.asarray(msg[key])):
                    diffs.append((f, rho, key))
            if geom['channel_seed'] != raw_p1['channel_seed']:
                diffs.append((f, rho, 'channel_seed'))
            fg = ch.frame_geometry(ctx, ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f)
            raw_base, diag = ch.cluster_base(ctx, fg, msg)
            for snr in (6.0, 14.0):
                raw = ch.at_snr(raw_base, snr)
                ctx.hd.observe(raw, rho, snr)          # asserts the P1 observation conventions (pilot/data power, sigma2)
                ctx.hd.truth_from_raw(raw, diag)
                observe_checked += 1
    taps = {}
    n_multi = n_taps = 0
    for f in range(*C_FRAMES):
        rays = ch.cluster_paths(ch.draw_cluster_geometry(ch.E2CJ_ENTROPY, ch.E2CJ_DOMAIN, f))['rays_per_tap']
        n_multi += sum(r >= 2 for r in rays)
        n_taps += len(rays)
    res['CG3'] = dict(message_noise_channel_seed_differences=diffs, observe_conventions_checked=observe_checked, main_frames=C_FRAMES[1] - C_FRAMES[0],
                      taps=n_taps, taps_with_ge2_rays=n_multi, frac_taps_with_ge2_rays=n_multi / n_taps, pass_=bool(not diffs))
    res['all_pass'] = bool(all(res[k]['pass_'] for k in ('CG1', 'CG2', 'CG3')))
    (out / 'cgates.json').write_text(json.dumps(res, indent=1, default=str) + '\n')
    print(json.dumps({k: v for k, v in res.items() if k != 'source_md5'}, indent=1, default=str))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('gate', 'gate-merge', 'cgate', 'calibrate', 'calibrate-merge', 'run'), required=True)
    p.add_argument('--family', choices=('R', 'C'), default='R')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--p1-rows', type=Path, default=P1_ROWS)
    p.add_argument('--e1-rows', type=Path, default=E1_ROWS)
    p.add_argument('--grid', type=Path, help='C run: GRID.json from calibrate-merge')
    p.add_argument('--snr-list', default=ALL_SNR, help='R family SNR grid (dB)')
    p.add_argument('--smoke', action='store_true', help='smoke run: any frames allowed; rows flagged smoke')
    p.add_argument('--smoke-snr', default='', help='C smoke only: provisional SNR list (dB), replaces GRID.json')
    p.add_argument('--smoke-any-frames', action='store_true')
    p.add_argument('--frames', type=int, default=1000)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--max-triggered', type=int, default=0, help='smoke: stop the shard after this many triggered keys')
    p.add_argument('--g3-max', type=int, default=3, help='gate: triggered states per shard used for the 8-arm double run (G3/G5)')
    a = p.parse_args(argv)
    if a.mode == 'gate':
        a.snr_list = a.snr_list or ALL_SNR
    return a


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    elif A.mode == 'gate-merge':
        gate_merge(A)
    elif A.mode == 'cgate':
        cgate_mode(A, sys.argv[1:])
    elif A.mode == 'calibrate':
        calibrate_mode(A, sys.argv[1:])
    elif A.mode == 'calibrate-merge':
        calibrate_merge(A)
    else:
        run_mode(A, sys.argv[1:])
