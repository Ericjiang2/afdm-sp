#!/usr/bin/env python
"""P1 confirmation driver (protocol.md section 3 + amendment A1, task 10-15-tcom-reference-frame).

Grid: scenario {U, G} x rho {.3, .5} x SNR 4.5..8.0 step .5 x 2000 frames.  One JSONL row per
(scenario, rho, snr, frame); channel, bits and noise are keyed by (frame, component) only, so they are shared across
rho and SNR (the e_rho pairing design).  Scenario U and G share delays, gains, bits and noise; only Doppler differs.

Arms (every receiver is imported unchanged):
  F0     native TF_J20_R2 (native_twofft.receive, rounds=2, iterations=20, soft/joint)
  B      F0 + CSTATE20 branch (run_validation._branch) only when the F0 final syndrome != 0
  LOCAL  F0 + LOCAL20 branch (same kernel, max_edits=0) only when F0 triggers
  C      F1 frozen NOMP front + the same TF_J20_R2 schedule (cstate_necessity_stageA_20260928/native_f1.receive_f1)
  D      C + CSTATE20 branch when C's final syndrome != 0
  A3     true H fixed (interventions.run_fixed_channel, detector='tf')
Seeds: numpy.SeedSequence(8 uint32 words of ENTROPY_HEX, DOMAIN, frame, component).  Generator: gen_fixed with
scenario flags (D1 + D2 + fix_energy; U = uwa Doppler, G = geometric Doppler).

Run one process per shard, single thread (launch_p1.sh).  Nothing frozen is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
HEADROOM = PROJECT / 'experiments' / 'headroom_ladder_20261008'
STAGE_A = PROJECT / 'experiments' / 'cstate_necessity_stageA_20260928'
sys.path.insert(0, str(HERE))
import gen_fixed  # noqa: E402
from gen_fixed import Flags  # noqa: E402

# --- frozen constants (protocol.md section 3.1 and amendment A1) ------------------------------------------------
# New 256-bit OS entropy (os.urandom(32).hex(), generated 2026-10-15 before any P1 data); never used by an earlier stream.
ENTROPY_HEX = '2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23'
DOMAIN = 0x54435246  # "TCRF"; distinct from HRLD 0x48524C44, CLUS 0x434C5553, CSTA 0x43535441, GEOM 0x47454F4D and every [20260920, ...] stream
COMPONENTS = {'channel': 1, 'message': 2, 'noise': 3}
STREAM_ALGORITHM = ('numpy.SeedSequence(8 entropy uint32 words, TCRF domain, frame, component); NOT keyed by rho, snr or scenario')
SCENARIOS = {'U': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='uwa', fix_energy=True),
             'G': Flags(fix_delay_cap=True, fix_delay_grid=True, doppler_law='geometric', fix_energy=True)}
ALL_ARMS = ('F0', 'B', 'LOCAL', 'C', 'D', 'A3')
DEFAULT_RHO = '0.3,0.5'
DEFAULT_SNR = '4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0'
RECEIVER_CONFIG = dict(
    F0='native_twofft.receive rounds=2 iterations=20 ce_mode=soft gain_mode=joint (TF_J20_R2)',
    B='F0 + run_validation._branch CSTATE20 iff F0 final syndrome != 0 (F0 prefix included in B seconds)',
    LOCAL='F0 + run_validation._branch LOCAL20 iff F0 final syndrome != 0',
    C='cstate_necessity_stageA_20260928/native_f1.receive_f1 (frozen NOMP front + TF_J20_R2)',
    D='C + run_validation._branch CSTATE20 iff C final syndrome != 0',
    A3='interventions.run_fixed_channel detector=tf with the true (l_i, k_real, g_i)',
    final_decoded_sha256='sha256 of uint8 decoded bits (same convention as Stage A / five-policy decisions)')


# ----------------------------------------------------------------------------- headroom driver (frozen, imported)
def load_headroom():
    spec = importlib.util.spec_from_file_location('headroom_driver', HEADROOM / 'driver.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def md5_file(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_module_files():
    """Every imported module whose source lives inside the project tree (not site-packages)."""
    out = {}
    root = str(PROJECT)
    for name, module in sorted(sys.modules.items()):
        if name.startswith('__'):
            continue
        path = getattr(module, '__file__', None)
        if path and os.path.isabs(path) and path.endswith('.py') and str(Path(path).resolve()).startswith(root):
            out[name] = str(Path(path).resolve())
    return out


def load_context():
    """Frozen headroom context (system, code, native, kernel, branch, wrappers, arms) + the Stage-A F1 receiver."""
    hd = load_headroom()
    args = hd.parse_args(['--mode', 'generate', '--out', str(HERE / 'out' / 'p1_ctx'), '--project', str(PROJECT)])
    ctx = hd.load_context(args)
    sys.path.insert(0, str(STAGE_A))
    from native_f1 import receive_f1
    ctx.receive_f1 = receive_f1
    ctx.hd = hd
    files = project_module_files()
    files['p1_driver'] = str(HERE / 'p1_driver.py')
    files['gen_fixed'] = str(HERE / 'gen_fixed.py')
    ctx.source_md5 = {k: md5_file(v) for k, v in sorted(files.items())}
    ctx.source_sha256 = {k: sha256_file(v) for k, v in sorted(files.items())}
    ctx.source_paths = {k: str(Path(v).relative_to(PROJECT)) for k, v in sorted(files.items())}
    return ctx


# ----------------------------------------------------------------------------- seeds
def entropy_words(entropy_hex):
    if re.fullmatch(r'[0-9a-f]{64}', entropy_hex) is None:
        raise ValueError('entropy must be 64 lowercase hex characters')
    return [int(x) for x in np.frombuffer(bytes.fromhex(entropy_hex), dtype='<u4').astype(np.uint32)]


def make_seed_fn(entropy_hex=ENTROPY_HEX, domain=DOMAIN):
    words = entropy_words(entropy_hex)

    def seed_fn(frame, component):
        if type(frame) is not int or frame < 0 or component not in COMPONENTS.values():
            raise ValueError('invalid stream coordinate')
        return words + [domain, frame, component]
    return seed_fn


# ----------------------------------------------------------------------------- arms
def _syndrome(ctx, decoded):
    return ctx.hd.syndrome_weight(ctx, decoded)


def _bits_sha(decoded):
    return hashlib.sha256(np.asarray(decoded, np.uint8).tobytes()).hexdigest()


def _err(error):
    return dict(status='error', error=repr(error), trace=traceback.format_exc()[-1200:])


def f0_family(ctx, obs, want):
    """One F0 run, then the CSTATE20 (B) and LOCAL20 branches from the same state iff F0 is triggered."""
    out = {}
    try:
        t0 = time.perf_counter()
        dec0, arrays, _ = ctx.native.receive(obs, ctx.system, ctx.code, rounds=2, iterations=20,
                                             ce_mode='soft', gain_mode='joint')
        f0_seconds = time.perf_counter() - t0
        syn0 = _syndrome(ctx, dec0['decoded'])
        prefix_seconds = time.perf_counter() - t0
    except Exception as error:  # recorded, never silently dropped
        return {a: _err(error) for a in ('F0', 'B', 'LOCAL') if a in want}
    triggered = syn0 != 0
    out['F0'] = dict(decoded=dec0['decoded'], llr=dec0['incoming_llr'], iters=int(dec0['iterations']),
                     seconds=f0_seconds, triggered=bool(triggered))
    for arm, mode in (('B', 'CSTATE20'), ('LOCAL', 'LOCAL20')):
        if arm not in want:
            continue
        try:
            branch_seconds, final = 0., dec0
            if triggered:
                t1 = time.perf_counter()
                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, mode)['decoder']
                branch_seconds = time.perf_counter() - t1
            out[arm] = dict(decoded=final['decoded'], llr=final['incoming_llr'], iters=int(final['iterations']),
                            seconds=prefix_seconds + branch_seconds, prefix_seconds=prefix_seconds,
                            branch_seconds=branch_seconds, triggered=bool(triggered), f0_syndrome=int(syn0))
            if arm == 'B':
                out[arm].update(fit_delays=[int(x) for x in np.asarray(arrays['r1_delays'])],
                                fit_dopplers=[float(x) for x in np.asarray(arrays['r1_dopplers'])])
        except Exception as error:
            out[arm] = _err(error)
    return out


def f1_family(ctx, obs, want):
    """F1 front + the same native schedule (C); CSTATE20 branch iff C's final syndrome != 0 (D)."""
    out = {}
    try:
        t0 = time.perf_counter()
        decC, arraysC, _ = ctx.receive_f1(obs, ctx.system, ctx.code)
        synC = _syndrome(ctx, decC['decoded'])
        prefix_seconds = time.perf_counter() - t0
    except Exception as error:
        return {a: _err(error) for a in ('C', 'D') if a in want}
    triggered = synC != 0
    out['C'] = dict(decoded=decC['decoded'], llr=decC['incoming_llr'], iters=int(decC['iterations']),
                    seconds=prefix_seconds, triggered=bool(triggered), c_syndrome=int(synC))
    if 'D' in want:
        try:
            branch_seconds, final = 0., decC
            if triggered:
                t1 = time.perf_counter()
                final = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arraysC, 'CSTATE20')['decoder']
                branch_seconds = time.perf_counter() - t1
            out['D'] = dict(decoded=final['decoded'], llr=final['incoming_llr'], iters=int(final['iterations']),
                            seconds=prefix_seconds + branch_seconds, prefix_seconds=prefix_seconds,
                            branch_seconds=branch_seconds, triggered=bool(triggered), c_syndrome=int(synC))
        except Exception as error:
            out['D'] = _err(error)
    return out


def a3_arm(ctx, obs, truth):
    try:
        return {'A3': ctx.hd.run_a3(ctx, obs, truth)[0]}
    except Exception as error:
        return {'A3': _err(error)}


def compute_arms(ctx, obs, truth, arms):
    """Run the requested arms on one observation; return {arm: scored record}."""
    want = set(arms)
    raw = {}
    if want & {'F0', 'B', 'LOCAL'}:
        raw.update(f0_family(ctx, obs, want | {'F0'}))
    if want & {'C', 'D'}:
        raw.update(f1_family(ctx, obs, want | {'C'}))
    if 'A3' in want:
        raw.update(a3_arm(ctx, obs, truth))
    out = {}
    for arm in ALL_ARMS:
        if arm not in want:
            continue
        res = raw[arm]
        if res.get('status') == 'error':
            out[arm] = res
            continue
        sc = ctx.hd.score(ctx, res, truth)
        rec = dict(status='ok', fer=int(sc['info_errors'] > 0), info_errors=sc['info_errors'], coded_errors=sc['coded_errors'],
                   syndrome=sc['syndrome'], triggered=res.get('triggered'), seconds=sc['seconds'],
                   ldpc_iters=sc['ldpc_iters'], logloss_bits=sc['logloss_bits'],
                   decoded_sha256=_bits_sha(res['decoded']))
        for key in ('prefix_seconds', 'branch_seconds', 'f0_syndrome', 'c_syndrome', 'fit_delays', 'fit_dopplers'):
            if key in res:
                rec[key] = res[key]
        out[arm] = rec
    return out


# ----------------------------------------------------------------------------- one cell
def generate(ctx, scenario_or_flags, rho, snr_db, frame, seed_fn):
    flags = SCENARIOS[scenario_or_flags] if isinstance(scenario_or_flags, str) else scenario_or_flags
    return gen_fixed.generate_base(ctx, rho, snr_db, frame, seed_fn, flags)


def truth_fields(ctx, truth, diag):
    out = ctx.hd.truth_summary(truth)
    g = diag['gen_fixed']
    out.update(gen_flags=g['flags'], gen_redraws=int(g['redraws']), gen_fallback_clip=bool(g['fallback_clip']),
               gen_prefix=int(g['prefix_length']), gen_max_delay=int(g['max_delay']), gen_path_power=float(g['path_power']),
               gen_energy_per_dim=float(diag['channel_energy_per_dimension']),
               gen_nu_max=g['nu_max_99'])
    return out


def pair_fingerprint(truth):
    return (truth['channel_seed'], truth['physical_gains_sha256'],
            hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])


# ----------------------------------------------------------------------------- shard i/o (headroom helpers)
def cell_key(row):
    return (row['scenario'], row['rho_permille'], row['snr_centi_db'], row['frame'])


def load_done(path):
    path = Path(path)
    if not path.exists():
        return set()
    data = path.read_bytes()
    cut = data.rfind(b'\n') + 1
    if cut != len(data):  # drop a partial trailing line left by a crash
        path.write_bytes(data[:cut])
    return {cell_key(json.loads(x)) for x in data[:cut].decode().splitlines() if x.strip()}


def parse_list(text, cast):
    return [cast(x) for x in str(text).split(',') if str(x).strip() != '']


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scenarios', default='U,G')
    p.add_argument('--rho-list', default=DEFAULT_RHO)
    p.add_argument('--snr-list', default=DEFAULT_SNR)
    p.add_argument('--frames', type=int, required=True, help='frames per (scenario, rho, snr) cell')
    p.add_argument('--frame-offset', type=int, default=0)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--arms', default=','.join(ALL_ARMS))
    p.add_argument('--label', default='main', help='free text recorded in the config (main / timing)')
    return p.parse_args(argv)


def fingerprint(args, ctx, argv):
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    config.update(ENTROPY_HEX=ENTROPY_HEX, DOMAIN=DOMAIN, components=COMPONENTS, stream_algorithm=STREAM_ALGORITHM,
                  scenario_flags={k: dict(fix_delay_cap=v.fix_delay_cap, fix_delay_grid=v.fix_delay_grid,
                                          doppler_law=v.doppler_law, fix_energy=v.fix_energy) for k, v in SCENARIOS.items()},
                  nu_max_99=gen_fixed.UWA_NU_MAX_99, receiver=RECEIVER_CONFIG,
                  source_md5=ctx.source_md5, source_sha256=ctx.source_sha256, source_paths=ctx.source_paths,
                  code_g_sha256=ctx.header['code_g_sha256'], checkpoint_sha256=ctx.header.get('checkpoint_sha256'),
                  environment=ctx.environment)
    return list(argv), config


def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    scenarios = parse_list(args.scenarios, str)
    arms = parse_list(args.arms, str)
    if not set(scenarios) <= set(SCENARIOS) or not set(arms) <= set(ALL_ARMS):
        raise ValueError('unknown scenario or arm')
    rho_list = parse_list(args.rho_list, float)
    snr_cells = [int(round(float(x) * 100)) for x in parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ctx = load_context()
    hd_module = ctx.hd
    _, config = fingerprint(args, ctx, argv)
    jsonable = lambda v: json.loads(json.dumps(v, default=hd_module.to_jsonable))  # noqa: E731
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment', 'shard', 'out')}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != jsonable(comparable):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=hd_module.to_jsonable, allow_nan=False) + '\n')
    seed_fn = make_seed_fn()
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = load_done(jsonl)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    started = time.perf_counter()
    n_cells = 0
    with jsonl.open('a') as handle:
        for frame in frames:
            for scenario in scenarios:
                pair = None
                for rho in rho_list:
                    rho_pm = int(round(rho * 1000))
                    todo = [s for s in snr_cells if (scenario, rho_pm, s, frame) not in done]
                    if not todo:
                        continue
                    g0 = time.perf_counter()
                    raw_base, diag_base = generate(ctx, scenario, rho, snr_cells[0] / 100, frame, seed_fn)
                    gen_seconds = time.perf_counter() - g0
                    for snr_centi in todo:
                        raw, diag = ctx.reuse_at_snr(raw_base, diag_base, snr_centi / 100)
                        obs = ctx.hd.observe(raw, rho, snr_centi / 100)
                        truth = ctx.hd.truth_from_raw(raw, diag)
                        fp = pair_fingerprint(truth)
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        c0 = time.perf_counter()
                        arm_rows = compute_arms(ctx, obs, truth, arms)
                        cell_seconds = time.perf_counter() - c0
                        row = dict(scenario=scenario, rho=float(rho), rho_permille=rho_pm, snr_centi_db=int(snr_centi),
                                   snr_db=snr_centi / 100, frame=int(frame), label=args.label,
                                   generate_seconds=gen_seconds if snr_centi == todo[0] else 0.,
                                   cell_seconds=cell_seconds, arms=arm_rows, **truth_fields(ctx, truth, diag))
                        handle.write(json.dumps(row, sort_keys=True, allow_nan=False, default=hd_module.to_jsonable) + '\n')
                        handle.flush()
                        os.fsync(handle.fileno())
                        n_cells += 1
                        print(f'[{time.perf_counter() - started:8.1f}s] {scenario} rho={rho} snr={snr_centi} frame={frame} '
                              + ' '.join(f"{a}:{r.get('info_errors', 'ERR')}" for a, r in arm_rows.items()), flush=True)
    print(f'shard {args.shard}/{args.nshard} done: {n_cells} cells in {time.perf_counter() - started:.1f}s', flush=True)


if __name__ == '__main__':
    run_shard(parse_args(), sys.argv[1:])
