#!/usr/bin/env python
"""E-1 driver (task 10-17-discrete-acquisition-e1; see PROTOCOL.md, which supersedes design.md where they differ).

--mode select  scan the frozen P1 ledger (arms.B.triggered) for the given SNRs and write triggered_keys.json (the unit list).
--mode run     per unit (scenario, rho, snr, frame) with F0 final syndrome != 0: regenerate the P1 frame, rerun F0
               (native_twofft.receive rounds=2 iterations=20 soft/joint), assert G4a (syndrome != 0), then run arms A1..A6 from that
               SAME F0 state; one JSONL row per unit.
--mode gate    G1/G2/G3/G4b on real P1 states: all keys of the given frames/SNRs (triggered and not).
--mode gate-merge  merge gate shards into gates.json.

Arms (all share the captured F0 state; CSTATE20 branch = run_validation._branch re-implemented with per-arm parameters):
  A1 full Gamma  max_edits=2 compact local_passes=2   (production CSTATE20; must reproduce the ledger bitwise)
  A2 diag Gamma  max_edits=2 compact local_passes=2
  A3 full Gamma  max_edits=0 compact local_passes=2
  A4 diag Gamma  max_edits=0 compact local_passes=2
  A5 no geometry call: Channel(r1_delays, r1_dopplers, r1_gains) -> scalar_joint(prior=r1_check) -> LDPC
  A6 full Gamma  max_edits=0 compact local_passes=0   (soft ridge gain refit only; reported arm)
  A7 literal third F0 round: native_twofft.receive(rounds=3, ...) from scratch on the same observation (PROTOCOL.md section 10, O2);
     G5 (every unit): its round-0 and round-1 arrays are bitwise equal to the captured rounds=2 state.
Nothing frozen is edited; the Gamma variant lives in geometry_*_variant.py.
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
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(EXPERIMENTS / 'tcom_genie_support_20261016'))
import e1_lib  # noqa: E402
import gs_driver as gd  # noqa: E402
from gs_driver import p1ctx  # noqa: E402

P1_ROWS = EXPERIMENTS / 'tcom_reference_frame_20261015' / 'out' / 'p1'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'  # O1: full P1 grid is the primary unit set
GATE_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
ARMS = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7')
ARM_SPECS = {
    'A1': dict(gamma_mode='full', max_edits=2, local_passes=2),
    'A2': dict(gamma_mode='diag', max_edits=2, local_passes=2),
    'A3': dict(gamma_mode='full', max_edits=0, local_passes=2),
    'A4': dict(gamma_mode='diag', max_edits=0, local_passes=2),
    'A5': None,
    'A6': dict(gamma_mode='full', max_edits=0, local_passes=0),
}
A7_SPEC = 'native_twofft.receive rounds=3 iterations=20 ce_mode=soft gain_mode=joint from scratch; G5 compares all r0_*/r1_* arrays with the rounds=2 state'
GEOMETRY_STAGES = ('geometry_setup', 'structural_field_build', 'structural_scoring', 'structural_selection_trace',
                   'structural_refit_refresh', 'structural_fallback_direct', 'local_refinement', 'geometry_finalization')
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')


# ----------------------------------------------------------------------------- provenance
def load_variant():
    e1_lib.prepare_paths()
    import geometry_validation_variant as kvar
    return kvar


def check_frozen_md5(ctx):
    """Every file listed in SOURCE_MD5.txt must have the recorded md5 (on disk, else via the loaded module of the same stem)."""
    results, bad = {}, []
    for line in (HERE / 'SOURCE_MD5.txt').read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        digest, rel = line.split()
        path = EXPERIMENTS / rel
        loaded = ctx.source_md5.get(Path(rel).stem) if rel.endswith('.py') else None
        if loaded is not None:  # prefer what was actually imported (deinlab loads sp_afdm_* from *_reviewed_* dirs)
            actual, how = loaded, 'loaded-module'
        elif path.exists():
            actual, how = e1_lib.md5_file(path), 'file'
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
    names = ('e1_driver.py', 'e1_lib.py', 'geometry_reopen_variant.py', 'geometry_validation_variant.py', 'PROTOCOL.md', 'SOURCE_MD5.txt')
    return {n: e1_lib.md5_file(HERE / n) for n in names if (HERE / n).exists()}


def write_config(out, shard, argv, args, ctx):
    path = out / f'config_shard{shard:03d}.json'
    if path.exists():
        return
    cfg = dict(vars(args), out=str(args.out), keys=str(args.keys) if getattr(args, 'keys', None) else None,
               p1_rows=str(args.p1_rows), arm_specs=ARM_SPECS, a7_spec=A7_SPEC,
               branch='run_validation._branch re-implemented with per-arm parameters (E-1 PROTOCOL.md section 3)',
               schedule='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint; branch: scalar_joint iterations=20 damping=.3 '
                        'gain_mode=joint prior=r1_check; decoder_messages maxiter=50; reopen strategy=compact grid_step=.25 chunk_size=64 '
                        'local_halfwidth=.75 local_max_evals=16 duplicate_tolerance=1e-6 top_k=20 ridge=sigma2 max_delay=system.l_max_cap '
                        'doppler=[-3,3]',
               entropy=p1ctx.p1_driver.ENTROPY_HEX, domain=p1ctx.p1_driver.DOMAIN,
               frozen_md5_check=check_frozen_md5(ctx), own_md5=own_md5(), source_md5=ctx.source_md5, environment=ctx.environment)
    path.write_text(json.dumps(dict(_argv=list(argv), _config=cfg), indent=1, default=str) + '\n')


# ----------------------------------------------------------------------------- ledger
def load_ledger(p1_rows, frames=None, snr_cells=None):
    """P1 ledger fields per key (arms.B / arms.F0); frames/snr_cells restrict the scan result."""
    out = {}
    for p in sorted(glob.glob(str(Path(p1_rows) / 'rows_shard*.jsonl.gz'))):
        with gzip.open(p, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                if frames is not None and r['frame'] not in frames:
                    continue
                if snr_cells is not None and r['snr_centi_db'] not in snr_cells:
                    continue
                b, f0 = r['arms']['B'], r['arms']['F0']
                if b.get('status') != 'ok' or f0.get('status') != 'ok':
                    raise ValueError(f'ledger row not ok: {r["scenario"], r["rho_permille"], r["snr_centi_db"], r["frame"]}')
                out[(r['scenario'], r['rho_permille'], r['snr_centi_db'], r['frame'])] = dict(
                    triggered=bool(b['triggered']), f0_syndrome=int(b.get('f0_syndrome', f0.get('syndrome', -1))),
                    b_sha=b['decoded_sha256'], b_info_errors=int(b['info_errors']), b_fer=int(b['fer']),
                    f0_sha=f0['decoded_sha256'], f0_info_errors=int(f0['info_errors']), f0_fer=int(f0['fer']))
    return out


def select_mode(args, argv):
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    frames = set(range(args.frame_offset, args.frame_offset + args.frames))
    ledger = load_ledger(args.p1_rows, frames, set(snr_cells))
    keys = sorted(k for k, v in ledger.items() if v['triggered'])
    table = {}
    for k in keys:
        cell = f'{k[0]}_rho{k[1]}'
        table.setdefault(cell, {}).setdefault(str(k[2]), 0)
        table[cell][str(k[2])] += 1
    files = sorted(glob.glob(str(Path(args.p1_rows) / 'rows_shard*.jsonl.gz')))
    out = dict(_argv=list(argv), snr_cells=snr_cells, frames=[args.frame_offset, args.frame_offset + args.frames],
               ledger_scanned_rows=len(ledger), n_triggered=len(keys), per_cell_snr=table,
               ledger_files_md5={Path(p).name: e1_lib.md5_file(p) for p in files},
               units=[dict(scenario=k[0], rho_permille=k[1], snr_centi_db=k[2], frame=k[3], **ledger[k]) for k in keys])
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'triggered_keys.json').write_text(json.dumps(out, indent=1) + '\n')
    print(f'select: {len(keys)} triggered of {len(ledger)} ledger rows; per cell/snr {json.dumps(table)}')


# ----------------------------------------------------------------------------- F0 state + branch
def receive_state(ctx, obs, rounds):
    t0 = time.perf_counter()
    dec, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=rounds, iterations=20, ce_mode='soft', gain_mode='joint')
    syn = int(ctx.hd.syndrome_weight(ctx, dec['decoded']))
    return dec, arrays, syn, time.perf_counter() - t0


def f0_state(ctx, obs):
    return receive_state(ctx, obs, 2)


def run_a7(ctx, obs, arrays_ref):
    """A7 = literal third F0 round (rounds=3 from scratch).  G5: every r0_*/r1_* array it exposes must equal the captured
    rounds=2 state bitwise (r1_delays, r1_dopplers, r1_gains, r1_app, r1_check, r1_decoded, r1_input_llr, ce gains, moments, traces)."""
    dec3, arrays3, syn3, seconds = receive_state(ctx, obs, 3)
    keys = sorted(k for k in arrays_ref if k.startswith(('r0_', 'r1_')))
    required = {f'r1_{x}' for x in ('delays', 'dopplers', 'gains', 'app', 'check', 'decoded')}
    missing = sorted((required | set(keys)) - set(arrays3))
    diff = ([f'missing in rounds=3 arrays: {missing}'] if missing or not required <= set(keys) else
            e1_lib.deep_equal({k: arrays_ref[k] for k in keys}, {k: arrays3[k] for k in keys}))
    if not diff and gd.bits_sha(arrays3['r2_decoded']) != gd.bits_sha(dec3['decoded']):
        diff = ['rounds=3 returned decoder differs from r2_decoded']
    return dict(result=None, detector=None, decoder=dec3, arrays=arrays3, syndrome=syn3, seconds=seconds, g5_diff=diff, g5_keys=keys)


def run_arm(ctx, kvar, obs, arrays, arm):
    return run_a7(ctx, obs, arrays) if arm == 'A7' else run_branch(ctx, kvar, obs, arrays, arm)


def run_branch(ctx, kvar, obs, arrays, arm):
    """run_validation._branch (CSTATE20) with per-arm parameters; exclusive-stage timing kept.  A5 skips geometry entirely."""
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
            strategy='compact', gamma_mode=spec['gamma_mode'])
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


def arm_record(ctx, truth, br, arrays):
    dec = br['decoder']['decoded']
    res = br['result']
    r1_delays = [int(x) for x in np.asarray(arrays['r1_delays'])]
    if res is None:
        d, nu = r1_delays, [float(x) for x in np.asarray(arrays['r1_dopplers'])]
        edits, top5, extra = [], [], {}
    else:
        d, nu = [int(p.delay) for p in res.paths], [float(p.doppler) for p in res.paths]
        edits = [dict(step=int(e['step']), slot=int(e['slot']), old=e['old'], new=e['new'], decrease=float(e['decrease']))
                 for e in res.edits]
        trace = res.global_trace
        top5 = [dict(rank=int(t['rank']), slot=int(t['slot']), replacement=t['replacement'], score=float(t['frozen_score']))
                for t in (trace[0]['top_k'][:5] if trace else [])]
        extra = dict(objective_before=float(res.objective_before), objective_after=float(res.objective_after),
                     numerical_fallback=bool(res.diagnostics['numerical_fallback']), condition_number=float(res.condition_number))
    errors = gd.score(ctx, dec, truth)
    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(ctx.hd.syndrome_weight(ctx, dec)),
                decoded_sha256=gd.bits_sha(dec), ldpc_iters=int(br['decoder']['iterations']),
                final_delays=d, final_dopplers=nu,
                n_support_changes=len(set(d) ^ set(r1_delays)), n_delay_replacements=len(set(d) - set(r1_delays)),
                n_edits=len(edits), edits=edits, top5_step1=top5, seconds=float(br['branch_decision_seconds']),
                stages={k: float(x) for k, x in br['exclusive_stages'].items()}, **extra)


def a7_record(ctx, truth, br, arrays_ref, f0_seconds):
    dec = br['decoder']['decoded']
    a3 = br['arrays']
    r1_delays = [int(x) for x in np.asarray(arrays_ref['r1_delays'])]
    d, nu = [int(x) for x in np.asarray(a3['r2_delays'])], [float(x) for x in np.asarray(a3['r2_dopplers'])]
    errors = gd.score(ctx, dec, truth)
    return dict(status='ok', fer=int(errors > 0), info_errors=int(errors), syndrome=int(br['syndrome']), decoded_sha256=gd.bits_sha(dec),
                ldpc_iters=int(br['decoder']['iterations']), final_delays=d, final_dopplers=nu,
                n_support_changes=len(set(d) ^ set(r1_delays)), n_delay_replacements=len(set(d) - set(r1_delays)), n_edits=0, edits=[],
                top5_step1=[], seconds=float(br['seconds']), seconds_minus_f0=float(br['seconds'] - f0_seconds),
                stages={'receive_rounds3': float(br['seconds'])}, g5_ok=not br['g5_diff'], g5_keys=len(br['g5_keys']),
                r1_decoded_sha256=gd.bits_sha(a3['r1_decoded']))


def err_record(error):
    return dict(status='error', error=repr(error), trace=traceback.format_exc()[-1500:])


# ----------------------------------------------------------------------------- run mode
def run_mode(args, argv):
    ctx = p1ctx.load()
    kvar = load_variant()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    keys = json.loads(Path(args.keys).read_text())['units']
    units = keys[args.shard::args.nshard]
    if args.max_units:  # smoke: round-robin over SNR levels (ascending), so low and high SNR units are both exercised
        levels = sorted({u['snr_centi_db'] for u in units})
        per = [[u for u in units if u['snr_centi_db'] == s] for s in levels]
        units = [per[i % len(levels)][i // len(levels)] for i in range(args.max_units) if i // len(levels) < len(per[i % len(levels)])]
    write_config(out, args.shard, argv, args, ctx)
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = gd.load_done(jsonl)
    started = time.perf_counter()
    n_new = 0
    with jsonl.open('a') as handle:
        for u in units:
            k = (u['scenario'], u['rho_permille'], u['snr_centi_db'], u['frame'])
            if k in done:
                continue
            rho = u['rho_permille'] / 1000
            g0 = time.perf_counter()
            raw_base, diag_base = p1ctx.base(ctx, u['scenario'], rho, u['frame'])
            raw, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, u['snr_centi_db'])
            gen_seconds = time.perf_counter() - g0
            dec0, arrays, syn, f0_seconds = f0_state(ctx, obs)
            g4a_ok = syn != 0
            ledger = {x: u[x] for x in ('triggered', 'f0_syndrome', 'b_sha', 'b_info_errors', 'b_fer', 'f0_sha', 'f0_info_errors', 'f0_fer')}
            f0_info = gd.score(ctx, dec0['decoded'], truth)
            row = dict(scenario=u['scenario'], rho=float(rho), rho_permille=u['rho_permille'], snr_centi_db=u['snr_centi_db'],
                       snr_db=u['snr_centi_db'] / 100, frame=u['frame'], sigma2=float(raw['sigma2']), gen_seconds=gen_seconds,
                       f0=dict(syndrome=syn, info_errors=int(f0_info), decoded_sha256=gd.bits_sha(dec0['decoded']),
                               ldpc_iters=int(dec0['iterations']), seconds=f0_seconds),
                       g4a_ok=bool(g4a_ok), ledger=ledger,
                       f0_matches_ledger=bool(gd.bits_sha(dec0['decoded']) == u['f0_sha'] and syn == u['f0_syndrome']),
                       r1=dict(delays=[int(x) for x in np.asarray(arrays['r1_delays'])],
                               dopplers=[float(x) for x in np.asarray(arrays['r1_dopplers'])]),
                       truth=dict(delays=[int(x) for x in np.asarray(truth['l_i'])], dopplers=[float(x) for x in np.asarray(truth['k_real'])]),
                       arms={})
            if g4a_ok:
                row['g5_ok'] = False
                for arm in ARMS:
                    try:
                        br = run_arm(ctx, kvar, obs, arrays, arm)
                        if arm == 'A7':
                            row['arms'][arm] = a7_record(ctx, truth, br, arrays, f0_seconds)
                            row['g5_ok'], row['g5_mismatch'], row['g5_keys'] = bool(not br['g5_diff']), br['g5_diff'][:3], len(br['g5_keys'])
                        else:
                            row['arms'][arm] = arm_record(ctx, truth, br, arrays)
                    except Exception as error:  # recorded, never silently dropped
                        row['arms'][arm] = err_record(error)
                a1 = row['arms']['A1']
                row['a1_matches_ledger'] = bool(a1.get('status') == 'ok' and a1['decoded_sha256'] == u['b_sha'])
            else:
                row['a1_matches_ledger'], row['g5_ok'] = False, False
                print(f'G4A_FAIL {k}: F0 syndrome 0 on a ledger-triggered unit', flush=True)
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
            n_new += 1
            print(f"[{time.perf_counter() - started:8.1f}s] {k} g4a={row['g4a_ok']} a1_ledger={row['a1_matches_ledger']} "
                  + ' '.join(f"{a}:{r.get('info_errors', 'ERR')}" for a, r in row['arms'].items()), flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_new} units in {time.perf_counter() - started:.1f}s', flush=True)


# ----------------------------------------------------------------------------- gate mode
GATE_COMPARE = ('result', 'detector', 'decoder', 'app_input', 'check_prior', 'ce_mu', 'ce_variance', 'initial_paths')


def branch_core(br):
    if 'arrays' in br:  # A7
        return dict(decoder=br['decoder'], arrays=br['arrays'], syndrome=br['syndrome'])
    return {k: br[k] for k in GATE_COMPARE}


def c1_check(ctx, arrays, delays, dopplers):
    """C1: diag(projected_variance(v, ...)) == sum(v)."""
    from messages import moments
    from physical import projected_variance
    _, v, _ = moments(np.clip(arrays['r1_app'], -20, 20), 1 - ctx.system.rho)
    d = np.diag(projected_variance(v, delays, dopplers, ctx.system.c1))
    return float(np.max(abs(d.real - v.sum()) / v.sum())), bool(np.all(d.imag == 0)), v


def top1(res):
    t = res.global_trace[0]['selected'] if res is not None and res.global_trace else None
    return None if t is None else (t['slot'], t['replacement']['delay'], t['replacement']['doppler'])


def gate_mode(args, argv):
    ctx = p1ctx.load()
    kvar = load_variant()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_config(out, args.shard, argv, args, ctx)
    snr_cells = [int(round(float(x) * 100)) for x in gd.parse_list(args.snr_list, str)]
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    ledger = load_ledger(args.p1_rows, set(frames), set(snr_cells))
    records, g3_done = [], 0
    started = time.perf_counter()
    for frame in frames:
        for scenario in gd.SCENARIOS:
            for rho in (0.3, 0.5):
                rho_pm = int(round(rho * 1000))
                raw_base, diag_base = p1ctx.base(ctx, scenario, rho, frame)
                for snr in snr_cells:
                    _, obs, truth = gd.observe(ctx, raw_base, diag_base, rho, snr)
                    dec0, arrays, syn, _ = f0_state(ctx, obs)
                    k = (scenario, rho_pm, snr, frame)
                    led = ledger[k]
                    trig = syn != 0
                    rec = dict(key=list(k), triggered=bool(trig), ledger_triggered=led['triggered'], f0_syndrome=syn,
                               trigger_match=bool(trig == led['triggered']),
                               f0_sha_match=bool(gd.bits_sha(dec0['decoded']) == led['f0_sha']))
                    # G1 (real state): frozen production branch vs variant A1 (full), triggered AND untriggered states
                    prod = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
                    a1 = run_branch(ctx, kvar, obs, arrays, 'A1')
                    g1 = e1_lib.deep_equal(branch_core(prod), branch_core(a1))
                    rec.update(g1_identical=not g1, g1_mismatch=g1[:3])
                    final = a1['decoder']['decoded'] if trig else dec0['decoded']
                    rec['ledger_sha_match'] = bool(gd.bits_sha(final) == led['b_sha'])
                    if trig:
                        # G2 (real state): diag arm assertions and difference from full
                        a2 = run_branch(ctx, kvar, obs, arrays, 'A2')
                        rel_init, imag0_init, v = c1_check(ctx, arrays, arrays['r1_delays'], arrays['r1_dopplers'])
                        rel_fin, imag0_fin, _ = c1_check(ctx, arrays, [p.delay for p in a1['result'].paths],
                                                         [p.doppler for p in a1['result'].paths])
                        g = a2['result'].diagnostics['gamma']
                        offdiag = float(np.max(abs(g - np.diag(np.diag(g)))))
                        diag_rel = float(np.max(abs(np.diag(g).real - v.sum()) / v.sum()))
                        r1, r2 = a1['result'], a2['result']
                        rec.update(
                            g2=dict(c1_rel_err_initial=rel_init, c1_rel_err_final=rel_fin, c1_diag_real=bool(imag0_init and imag0_fin),
                                    diag_gamma_offdiag_max=offdiag, diag_gamma_diag_rel_err=diag_rel,
                                    gains_differ=bool(r1.gains.tobytes() != r2.gains.tobytes()),
                                    support_differs=bool(sorted(p.delay for p in r1.paths) != sorted(p.delay for p in r2.paths)),
                                    edits_differ=bool([e['new'] for e in r1.edits] != [e['new'] for e in r2.edits]),
                                    top1_differs=bool(top1(r1) != top1(r2)),
                                    decoded_differs=bool(gd.bits_sha(a1['decoder']['decoded']) != gd.bits_sha(a2['decoder']['decoded'])),
                                    n_accepted_a1=len(r1.edits), n_accepted_a2=len(r2.edits)))
                        # G3: all seven arms twice, bitwise (A7 also yields G5)
                        if g3_done < args.g3_max:
                            g3 = {}
                            for arm in ARMS:
                                x, y = run_arm(ctx, kvar, obs, arrays, arm), run_arm(ctx, kvar, obs, arrays, arm)
                                g3[arm] = not e1_lib.deep_equal(branch_core(x), branch_core(y))
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
    main_snr = {650, 700, 750, 800}
    sub = [r for r in recs if r['key'][2] in main_snr]
    trig = [r for r in recs if r['triggered']]
    g2 = [r['g2'] for r in trig]
    g3 = [r['g3'] for r in trig if 'g3' in r]
    gates = dict(
        n_states=len(recs), n_triggered=len(trig), n_untriggered=len(recs) - len(trig),
        G1=dict(states=len(recs), identical=sum(r['g1_identical'] for r in recs),
                triggered_identical=sum(r['g1_identical'] for r in trig), untriggered_identical=sum(r['g1_identical'] for r in recs if not r['triggered']),
                mismatches=[r['g1_mismatch'] for r in recs if not r['g1_identical']][:3],
                pass_=bool(len(recs) >= 64 and len(trig) >= 1 and len(recs) > len(trig) and all(r['g1_identical'] for r in recs))),
        G2=dict(triggered_states=len(g2), c1_worst_rel_err=max([max(x['c1_rel_err_initial'], x['c1_rel_err_final']) for x in g2] or [0.]),
                c1_all_diag_real=all(x['c1_diag_real'] for x in g2),
                diag_gamma_offdiag_max=max([x['diag_gamma_offdiag_max'] for x in g2] or [0.]),
                diag_gamma_diag_rel_err_max=max([x['diag_gamma_diag_rel_err'] for x in g2] or [0.]),
                gains_differ=sum(x['gains_differ'] for x in g2), support_differs=sum(x['support_differs'] for x in g2),
                edits_differ=sum(x['edits_differ'] for x in g2), top1_differs=sum(x['top1_differs'] for x in g2),
                decoded_differs=sum(x['decoded_differs'] for x in g2),
                any_decision_differs=sum(x['support_differs'] or x['edits_differ'] or x['top1_differs'] or x['decoded_differs'] for x in g2)),
        G3=dict(states=len(g3), per_arm_identical={a: sum(x[a] for x in g3) for a in ARMS}),
        G4b_main_snr=dict(states=len(sub), trigger_match=sum(r['trigger_match'] for r in sub), ledger_sha_match=sum(r['ledger_sha_match'] for r in sub),
                          f0_sha_match=sum(r['f0_sha_match'] for r in sub), n_triggered=sum(r['triggered'] for r in sub)),
        G4b_all_snr=dict(states=len(recs), trigger_match=sum(r['trigger_match'] for r in recs),
                         ledger_sha_match=sum(r['ledger_sha_match'] for r in recs), f0_sha_match=sum(r['f0_sha_match'] for r in recs)))
    G2 = gates['G2']
    G2['pass_'] = bool(G2['triggered_states'] >= 8 and G2['c1_worst_rel_err'] < 1e-10 and G2['c1_all_diag_real'] and G2['diag_gamma_offdiag_max'] == 0.
                       and G2['diag_gamma_diag_rel_err_max'] < 1e-10 and G2['any_decision_differs'] >= 8)
    g5 = [r['g5_ok'] for r in trig if 'g5_ok' in r]
    gates['G5'] = dict(states=len(g5), identical=sum(g5), pass_=bool(len(g5) >= 1 and all(g5)),
                       note='rounds=3 r0_*/r1_* arrays bitwise equal to the rounds=2 state (all keys of the rounds=2 arrays)')
    gates['G3']['pass_'] = bool(len(g3) >= 1 and all(v == len(g3) for v in gates['G3']['per_arm_identical'].values()))
    for name in ('G4b_main_snr', 'G4b_all_snr'):
        x = gates[name]
        x['pass_'] = bool(x['states'] >= 1 and x['trigger_match'] == x['states'] == x['ledger_sha_match'] == x['f0_sha_match'])
    gates['all_pass'] = all(gates[k]['pass_'] for k in ('G1', 'G2', 'G3', 'G4b_main_snr', 'G4b_all_snr', 'G5'))
    (args.out / 'gates.json').write_text(json.dumps(gates, indent=1) + '\n')
    print(json.dumps(gates, indent=1))


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('select', 'run', 'gate', 'gate-merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--keys', type=Path, help='run mode: triggered_keys.json from --mode select')
    p.add_argument('--p1-rows', type=Path, default=P1_ROWS)
    p.add_argument('--snr-list', default=None, help='select: default 6.5,7.0,7.5,8.0; gate: default all 8 P1 SNRs')
    p.add_argument('--frames', type=int, default=2000)
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--max-units', type=int, default=0, help='run mode (smoke): this many units of the shard, round-robin over SNR levels')
    p.add_argument('--g3-max', type=int, default=3, help='gate mode: triggered states per shard used for the 6-arm double-run G3')
    a = p.parse_args(argv)
    if a.snr_list is None:
        a.snr_list = GATE_SNR if a.mode == 'gate' else DEFAULT_SNR
    return a


if __name__ == '__main__':
    A = parse_args()
    if A.mode == 'select':
        select_mode(A, sys.argv[1:])
    elif A.mode == 'run':
        run_mode(A, sys.argv[1:])
    elif A.mode == 'gate':
        gate_mode(A, sys.argv[1:])
    else:
        gate_merge(A)
