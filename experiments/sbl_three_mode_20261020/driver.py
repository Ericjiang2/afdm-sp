#!/usr/bin/env python3
"""Bounded replay of Pilot 5: fixed, point, joint on identical E-3 SBL outputs."""
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
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path.insert(0, str(EXP / 'tf_e3_sbl_20261017'))
import e3_driver as e3d  # frozen imports, including the native detector

V = ('L-diag', 'L-cov')
MODES = ('fixed', 'point', 'joint')
GRID = {'U_300': [7., 8.], 'G_300': [7., 8.], 'U_500': [], 'G_500': []}
FRAMES = range(9100, 9150)
OLD = EXP / 'sbl_joint_detector_20261019' / 'out' / 'pilot5'
DEFAULT_OUT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation/afdm_sp_joint_unrolled/outputs_sbl_three_mode_20261020/run1')
FIELDS = ('decoded_sha256', 'info_errors', 'fer')


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def pairs(a):
    return [[float(z.real), float(z.imag)] for z in np.asarray(a, complex)]


def source_identity(ctx):
    checks = e3d.check_frozen_md5(ctx)
    actual_paths = {}
    for rel, check in checks.items():
        stem = Path(rel).stem
        module = sys.modules.get(stem) if rel.endswith('.py') else None
        if rel == 'headroom_ladder_20261008/driver.py':
            path = Path(ctx.hd.__file__)
        elif module is not None and getattr(module, '__file__', None):
            path = Path(module.__file__)
        elif stem in ctx.source_paths:
            path = EXP.parent / ctx.source_paths[stem]
        else:
            path = EXP / rel
        if not path.is_file() or e3d.e3_lib.md5_file(path) != check['expected'] or check['status'] != 'ok':
            raise RuntimeError(f'frozen source not bound: {rel}: {path}: {check}')
        actual_paths[rel] = str(path.resolve())
    return checks, actual_paths


def old_rows(directory):
    rows = {}
    files = sorted(glob.glob(str(directory / 'rows_shard*.jsonl*')))
    if not files:
        raise ValueError(f'old Pilot 5 rows missing: {directory}')
    for path in files:
        with (gzip.open if path.endswith('.gz') else open)(path, 'rt') as handle:
            for line in handle:
                r = json.loads(line)
                key = e3d.key_of(r)
                if key[3] not in FRAMES:
                    continue
                if key in rows or r.get('status') == 'error' or any(r['joint'][v]['status'] != 'ok' for v in V):
                    raise ValueError(f'duplicate or failed old row: {key}')
                rows[key] = r
    expected = {(sc, 300, snr, f) for sc in ('U', 'G') for snr in (700, 800) for f in FRAMES}
    if set(rows) != expected:
        raise ValueError(f'old key coverage {len(rows)}; missing {sorted(expected-set(rows))[:3]} extra {sorted(set(rows)-expected)[:3]}')
    return rows


def bit_loss(llr, bits):
    """Raw extrinsic LLR is log P(bit=0)/P(bit=1); bit order is all I then all Q."""
    L, b = np.asarray(llr, float), np.asarray(bits, np.uint8)
    if L.shape != b.shape or not np.all((b == 0) | (b == 1)) or not np.isfinite(L).all():
        raise ValueError('invalid extrinsic/true codeword')
    return float(np.logaddexp(0., -(1. - 2. * b.astype(float)) * L).mean())


def nmse_dense_gate(ctx):
    """Independent small physical-operator check of the channel NMSE observer."""
    n = 8
    truth = dict(delays=np.array([1, 3]), dopplers=np.array([.25, -.5]), gains=np.array([.7+.1j, -.2+.3j]))
    estimate = dict(delays=np.array([1, 2]), dopplers=np.array([.4, .2]), gains=np.array([.6+.2j, .1-.1j]))
    eye = np.eye(n, dtype=complex)
    def dense(p):
        channel = e3d.make_channel(ctx, n, p['delays'], p['dopplers'], p['gains'])
        return np.column_stack([channel.apply(eye[:, k]) for k in range(n)])
    H, E = dense(truth), dense(estimate)
    expected = float(np.linalg.norm(E-H)**2/np.linalg.norm(H)**2)
    actual = float(e3d.crb.channel_nmse(estimate, truth, n))
    same = float(e3d.crb.channel_nmse(truth, truth, n))
    if not np.isclose(actual, expected, rtol=1e-10, atol=1e-12) or same > 1e-12:
        raise AssertionError(f'channel NMSE dense gate: {actual}, {expected}, self {same}')
    return dict(actual=actual, dense=expected, self_nmse=same)


def observe(det, channel, truth, data_af):
    if len(det['states']) != 20 or len(det['trace']) != 20:
        raise ValueError('incomplete detector trajectory')
    tp = e3d.truth_paths(truth)
    path = dict(delays=channel.delays, dopplers=channel.dopplers, gains=channel.gains)
    def nmse(h):
        path['gains'] = h
        return float(e3d.crb.channel_nmse(path, tp, channel.n))
    traj = [dict(iteration=-1, h=pairs(channel.gains), channel_nmse=nmse(channel.gains))]
    for i, (state, trace) in enumerate(zip(det['states'], det['trace'])):
        h = state['h']
        if not np.array_equal(h, det['gains']) and i == 19:
            raise AssertionError('last recorded gains differ from detector result')
        traj.append(dict(iteration=i, h=pairs(h), channel_nmse=nmse(h),
                         data_mse=float(np.mean(np.abs(state['mu']-data_af)**2)),
                         symbol_variance=float(np.mean(state['v'])),
                         gain_variance=float(state['vh']), scalar_trace=trace))
    return traj


def process_key(ctx, cache, grid, obs, data_af, truth, meta, old, parity=False):
    captured = []
    coded = ctx.encode(ctx.code, truth['info'])
    if coded.shape != (2 * len(obs['y']),) or not np.array_equal(coded, truth['coded']):
        raise ValueError('re-encoded codeword differs from physical truth')
    original = e3d.detect_decode
    def wrapped(c, observation, channel, prior):
        if prior is None:
            return original(c, observation, channel, prior)
        record = {'support': dict(delays=channel.delays.tolist(), dopplers=channel.dopplers.tolist()),
                  'h0': pairs(channel.gains), 'prior_sha256': sha(prior), 'modes': {}}
        fixed_out = None
        for mode in MODES:
            t0 = time.perf_counter()
            det = c.native.scalar_joint(observation['y'], observation['pilot'], channel, observation['sigma2'],
                                        pd=1-c.system.rho, prior=prior, iterations=20, damping=.3,
                                        gain_mode=mode, record_states=True)
            elapsed = time.perf_counter() - t0
            if mode == 'fixed' and any(not np.array_equal(s['h'], channel.gains) for s in det['states']):
                raise AssertionError('fixed gains moved')
            if mode == 'point' and (np.any(det['gain_variance'] != 0) or any(s['vh'] != 0 for s in det['states'])):
                raise AssertionError('point gain variance nonzero')
            if parity:
                plain = c.native.scalar_joint(observation['y'], observation['pilot'], channel, observation['sigma2'],
                                              pd=1-c.system.rho, prior=prior, iterations=20, damping=.3, gain_mode=mode)
                no_states = {k: v for k, v in det.items() if k != 'states'}
                if e3d.e3_lib.deep_equal(no_states, plain):
                    raise AssertionError(f'record_states parity failed: {mode}')
            dec_t = time.perf_counter()
            dec = c.native.decoder_messages(c.code, np.clip(det['extrinsic'], -20, 20), maxiter=50)
            dt = time.perf_counter() - dec_t
            err = e3d.gd.score(c, dec['decoded'], truth)
            record['modes'][mode] = dict(info_errors=int(err), fer=int(err > 0),
                                         decoded_sha256=e3d.gd.bits_sha(dec['decoded']),
                                         syndrome=int(c.hd.syndrome_weight(c, dec['decoded'])),
                                         ldpc_iters=int(dec['iterations']),
                                         extrinsic_bit_logloss=bit_loss(det['extrinsic'], coded),
                                         trajectory=observe(det, channel, truth, data_af),
                                         detect_seconds=elapsed, decode_seconds=dt)
            if mode == 'fixed':
                fixed_out = (det, dec, elapsed, dt)
        captured.append(record)
        return fixed_out
    with mock.patch.object(e3d, 'detect_decode', wrapped):
        row = e3d.process_key(ctx, cache, grid, obs, data_af, truth, meta, V)
    if len(captured) != 2:
        raise AssertionError(f'expected two SBL variant calls, got {len(captured)}')
    for variant, rec in zip(V, captured):
        fixed, joint = rec['modes']['fixed'], rec['modes']['joint']
        old_fixed, old_joint = old['variants'][variant], old['joint'][variant]
        for field in FIELDS:
            if fixed[field] != old_fixed[field] or joint[field] != old_joint[field]:
                raise AssertionError(f'Pilot 5 replay mismatch {variant}/{field}: {meta}')
        for field in ('n_atoms', 'n_pair', 'atoms'):
            if row['variants'][variant][field] != old_fixed[field]:
                raise AssertionError(f'Pilot 5 SBL mismatch {variant}/{field}: {meta}')
    row['three_mode'] = dict(zip(V, captured))
    row['old_pilot5_replay'] = True
    row['observer_parity'] = bool(parity)
    return row


def run(args, argv):
    if args.nshard != 12 or not 0 <= args.shard < 12 or args.frames != 50 or args.frame_offset != 9100:
        raise ValueError('registered cohort requires 12 shards, frames 9100..9149')
    old = old_rows(args.old_rows)
    ctx = e3d.p1ctx.load()
    frozen, paths = source_identity(ctx)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.gate_only:
        if args.shard != 0:
            raise ValueError('gate-only uses shard 0')
        nmse_gate = nmse_dense_gate(ctx)
        cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap))
        raw_base, diag_base = e3d.p1ctx.base(ctx, 'U', .3, 9100)
        meta, obs, data_af, truth = e3d.observe_key(ctx, raw_base, diag_base, 'U', 300, 700, 9100)
        row = process_key(ctx, cache, grid, obs, data_af, truth, meta, old[e3d.key_of(meta)], parity=True)
        gate = dict(passed=True, key=list(e3d.key_of(meta)), observer_parity=row['observer_parity'],
                    pilot5_replay=row['old_pilot5_replay'], nmse_dense=nmse_gate,
                    mode_outcomes={v:{m:row['three_mode'][v]['modes'][m]['info_errors'] for m in MODES} for v in V},
                    frozen_md5_check=frozen, frozen_actual_paths=paths)
        (out / 'gate.json').write_text(json.dumps(gate, indent=1, allow_nan=False) + '\n')
        print('gate passed', flush=True)
        return
    path = out / f'rows_shard{args.shard:03d}.jsonl'
    config_path = out / f'config_shard{args.shard:03d}.json'
    if path.exists() or config_path.exists():
        raise FileExistsError(f'run output exists: {path} or {config_path}')
    cfg = dict(_argv=argv, _config=dict(shard=args.shard, nshard=args.nshard, frames=[9100, 9150], grid=GRID,
        old_rows=str(args.old_rows.resolve()), old_rows_md5={p.name:e3d.e3_lib.md5_file(p) for p in sorted(args.old_rows.glob('rows_shard*.jsonl*'))},
        own_md5={p.name:e3d.e3_lib.md5_file(p) for p in HERE.glob('*.py')},
        e3_own_md5=e3d.own_md5(), frozen_md5_check=frozen, frozen_actual_paths=paths,
        source_md5=ctx.source_md5, source_paths=ctx.source_paths, environment=ctx.environment,
        family_P1=dict(entropy=e3d.p1ctx.p1_driver.ENTROPY_HEX, domain=e3d.p1ctx.p1_driver.DOMAIN)))
    config_path.write_text(json.dumps(cfg, indent=1, allow_nan=False, default=str) + '\n')
    cache, grid = e3d.PilotCache(), e3d.sbl.full_grid(int(ctx.system.l_max_cap))
    start = time.monotonic()
    with path.open('x') as handle:
        for frame in list(FRAMES)[args.shard::12]:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, GRID, None):
                key = e3d.key_of(meta)
                try:
                    if time.monotonic()-start > args.deadline_seconds:
                        raise TimeoutError('shard deadline')
                    row = process_key(ctx, cache, grid, obs, data_af, truth, meta, old[key],
                                      parity=(args.shard == 0 and frame == 9100 and key[0] == 'U' and key[2] == 700))
                    e3d.write_row(handle, row)
                    print(f'{key} ok', flush=True)
                except Exception as exc:
                    e3d.write_row(handle, dict(meta, status='error', error=repr(exc), trace=traceback.format_exc()[-3000:]))
                    raise
    print(f'shard {args.shard}: completed in {time.monotonic()-start:.1f}s', flush=True)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=DEFAULT_OUT)
    p.add_argument('--old-rows', type=Path, default=OLD)
    p.add_argument('--frame-offset', type=int, default=9100)
    p.add_argument('--frames', type=int, default=50)
    p.add_argument('--shard', type=int, required=True)
    p.add_argument('--nshard', type=int, default=12)
    p.add_argument('--deadline-seconds', type=float, default=1100)
    p.add_argument('--gate-only', action='store_true')
    a = p.parse_args(argv)
    run(a, sys.argv[1:] if argv is None else argv)

if __name__ == '__main__':
    main()
