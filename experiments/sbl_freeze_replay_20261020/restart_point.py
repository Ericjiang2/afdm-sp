#!/usr/bin/env python3
"""Run only fresh point20 from the immutable run2 h20/prior; never rerun SBL."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('__freeze_replay', HERE / 'replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)
spec = importlib.util.spec_from_file_location('__restart_aggregate', HERE / 'aggregate_restart.py')
aggregate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aggregate)
e3d = replay.e3d
ROOT = Path('/data/guoyikun/00inbox/AFDM-channel-estimation')
OLD = ROOT / 'afdm_sp_joint_unrolled/outputs_sbl_freeze_replay_20261020/run2'
OUT = OLD.parent / 'restart_point1'
OWN = ('restart_point.py', 'aggregate_restart.py', 'test_aggregate_restart.py', 'launch_restart.sh')


def qualify_sources(ctx, receipt):
    identity = receipt['identity']
    for name, digest in identity['own_md5'].items():
        if e3d.e3_lib.md5_file(HERE / name) != digest:
            raise RuntimeError(f'producing helper changed: {name}')
    previous = identity['old_identity']
    if (ctx.source_md5 != identity['source_md5']
            or e3d.own_md5() != previous['e3_own_md5']
            or e3d.e3_lib.md5_file(Path(replay.oldd.__file__)) != previous['own_md5']['driver.py']
            or e3d.e3_lib.md5_file(Path(replay.oldagg.__file__)) != previous['own_md5']['aggregate.py']):
        raise RuntimeError('loaded receiver/helper source changed')
    frozen, paths = replay.oldd.source_identity(ctx)
    if frozen != identity['frozen_md5_check'] or paths != identity['frozen_actual_paths']:
        raise RuntimeError('actual frozen source paths/hashes changed')
    return paths


def process_key(ctx, obs, data_af, truth, meta, old, gate=False):
    h20, prior = aggregate.restore_inputs(old)
    if prior.shape != (2 * len(obs['y']),):
        raise ValueError('saved prior/observation dimensions')
    support = old['support']
    channel = e3d.make_channel(ctx, len(obs['y']), support['delays'], support['dopplers'], h20)
    coded = ctx.encode(ctx.code, truth['info'])
    if not np.array_equal(coded, truth['coded']):
        raise AssertionError('codeword reconstruction')
    kw = dict(pd=1-ctx.system.rho, prior=prior, damping=.3)
    start = time.perf_counter()
    det = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'],
                                 iterations=20, gain_mode='point', record_states=True, **kw)
    seconds = time.perf_counter() - start
    if (len(det['states']) != 20 or len(det['trace']) != 20
            or np.any(det['gain_variance'] != 0) or any(s['vh'] != 0 for s in det['states'])):
        raise AssertionError('RP trajectory/zero gain variance')
    qualification = None
    if gate:
        replay.checked_plain(ctx, obs, channel, prior, 'point', 20, det)
        rf = ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'],
                                    iterations=20, gain_mode='fixed', record_states=True, **kw)
        if any(not np.array_equal(s['h'], h20) for s in rf['states']):
            raise AssertionError('RF qualification gains moved')
        rf_score = replay.score_arm(ctx, rf, channel, truth, data_af, coded, 0.)
        if any(rf_score[f] != old['arms']['RF'][f] for f in aggregate.SCORE_FIELDS):
            raise AssertionError('saved RF decoder/score replay mismatch')
        first = [ctx.native.scalar_joint(obs['y'], obs['pilot'], channel, obs['sigma2'],
                    iterations=1, gain_mode=mode, record_states=True, **kw) for mode in ('point', 'fixed')]
        # Each symbol update precedes the gain update: the initial outputs must agree.
        for field in ('extrinsic', 'app', 'mu', 'variance'):
            if not np.array_equal(first[0][field], first[1][field]):
                raise AssertionError(f'first symbol update differs: {field}')
        for field in ('mu', 'v', 's', 'vr', 'vq', 'vh', 'sv', 'bar', 'vp'):
            if not np.array_equal(first[0]['states'][0][field], first[1]['states'][0][field]):
                raise AssertionError(f'first state update differs: {field}')
        qualification = dict(rf_score={f:rf_score[f] for f in aggregate.SCORE_FIELDS},
                             rp_observer_parity=True, first_symbol_update_equal=True)
    result = replay.score_arm(ctx, det, channel, truth, data_af, coded, seconds)
    result.update(final_gains=replay.oldd.pairs(det['gains']), trace=det['trace'])
    row = dict(meta, status='ok', old_row_sha256=aggregate.row_sha(old),
               input_sha256=old['input_sha256'], support=support, h20=old['h20'],
               zero_gain_variance=True, observer_parity=bool(gate), RP=result)
    if qualification is not None:
        row['qualification'] = qualification
    aggregate.validate([row], {e3d.key_of(old): old})
    return row


def run(args, argv):
    if not 0 <= args.shard < 12:
        raise ValueError('registered 12-shard cohort only')
    out = args.out.resolve()
    if not out.is_relative_to(ROOT) or out == args.old_rows.resolve():
        raise ValueError('output must be a separate /data/guoyikun project directory')
    old, receipt = aggregate.load_reference(args.old_rows)
    ctx = e3d.p1ctx.load()
    paths = qualify_sources(ctx, receipt)
    if args.gate_only and args.shard != 0:
        raise ValueError('gate uses shard0')
    out.mkdir(parents=True, exist_ok=True)
    config = dict(shard=args.shard, reference=receipt, source_md5=ctx.source_md5,
                  frozen_actual_paths=paths,
                  own_md5={name:e3d.e3_lib.md5_file(HERE / name) for name in OWN}, environment=ctx.environment)
    if args.gate_only:
        target = out / 'gate.json'
        if target.exists():
            raise FileExistsError(target)
        raw, diag = e3d.p1ctx.base(ctx, 'U', .3, 9100)
        meta, obs, data_af, truth = e3d.observe_key(ctx, raw, diag, 'U', 300, 700, 9100)
        row = process_key(ctx, obs, data_af, truth, meta, old[e3d.key_of(meta)], gate=True)
        with target.open('x') as handle:
            handle.write(json.dumps(dict(passed=True, row=row, config=config), allow_nan=False, indent=1) + '\n')
        print('RP/RF qualification passed', flush=True)
        return
    row_path, config_path = out / f'rows_shard{args.shard:03d}.jsonl', out / f'config_shard{args.shard:03d}.json'
    if row_path.exists() or config_path.exists():
        raise FileExistsError('RP shard output exists')
    with config_path.open('x') as handle:
        handle.write(json.dumps(dict(_argv=argv, _config=config), allow_nan=False, indent=1) + '\n')
    start = time.monotonic()
    with row_path.open('x') as handle:
        for frame in list(replay.FRAMES)[args.shard::12]:
            for meta, obs, data_af, truth in e3d.cells_of_frame(ctx, frame, replay.GRID, None):
                key = e3d.key_of(meta)
                try:
                    if time.monotonic() - start > args.deadline_seconds:
                        raise TimeoutError('RP shard deadline')
                    row = process_key(ctx, obs, data_af, truth, meta, old[key],
                                      gate=args.shard == 0 and key == ('U', 300, 700, 9100))
                    e3d.write_row(handle, row)
                    print(f'{key} ok', flush=True)
                except Exception as exc:
                    e3d.write_row(handle, dict(meta, status='error', error=repr(exc), trace=traceback.format_exc()[-3000:]))
                    raise
    print(f'RP shard {args.shard}: {time.monotonic()-start:.1f}s', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-rows', type=Path, default=OLD)
    parser.add_argument('--out', type=Path, default=OUT)
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--deadline-seconds', type=float, default=800)
    parser.add_argument('--gate-only', action='store_true')
    args = parser.parse_args()
    run(args, sys.argv[1:])


if __name__ == '__main__':
    main()
