#!/usr/bin/env python3
"""Replay only the archived 200-key SBL cohort.

out/question_a.jsonl: one row per key/upstream/interface, fields scenario,
rho_permille, snr_centi_db, frame, upstream, interface, first_h_relative,
action_relative (three ordered vectors), llr_max_abs, llr_relative_l2,
decoded_agrees, invariant, original, duplicated.
out/question_b.jsonl: one row per key/upstream/interface, same key fields,
operator_relative, original, merged. All score objects contain
info_errors, fer, decoded_sha256, extrinsic_bit_logloss.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
from multiprocessing.connection import wait
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback
from types import SimpleNamespace

STARTED = time.monotonic()
sys.dont_write_bytecode = True
for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np

import kernel
import summarize

HERE = Path(__file__).resolve().parent
REPLAY = HERE.parent / 'sbl_freeze_replay_20261020'
sys.path.insert(0, str(REPLAY))
import aggregate_gram_cohort as cohort_archive
import gram_cohort
import restart_point as replay

sys.path.insert(0, str(HERE.parent / 'slot_mismatch_20261019'))
import sm_driver

FRAMES = tuple(gram_cohort.FRAMES)
UPSTREAMS = gram_cohort.VARIANTS
NATIVE_MODES = ('fixed', 'point', 'joint')
MODES = NATIVE_MODES + ('eG',)
MERGE_MODES = ('fixed', 'joint')
DECISION = ('decoded_sha256', 'info_errors', 'fer')
SMOKE_KEYS = {gram_cohort.KEY}
EXPECTED_COUNTS = dict(zip(UPSTREAMS, ((4, 40, 23, 0), (15, 11, 2, 0))))
EXPECTED_GRAM_SUMMARY = 'eabf7b1f5e134e5d0e02456aaa851a74965590de3471aef2b62e92047da2b443'


class GateFailure(Exception):
    def __init__(self, gate, message, **details):
        super().__init__(message)
        self.gate = gate
        self.details = details


def write_json(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def write_jsonl(path, rows):
    with path.open('x') as handle:
        for row in rows:
            handle.write(json.dumps(row, allow_nan=False) + '\n')


def qualify_sources(ctx, receipt, *, local_smoke):
    """Check the archived module identities with explicit diagnostic imports in scope."""
    identity = receipt['identity']
    archived = identity['source_md5']
    extra = sorted(ctx.source_md5.keys() - archived.keys())
    allowed = {'kernel', 'summarize', 'gram_block', 'gram_cohort', 'aggregate_gram_cohort',
               'restart_point', 'representation_probe', 'sm_driver', 'e2_lib', 'e1_driver',
               'e2_driver', 'e2_calib', 'e2_channels', 'codelay_guard', 'afdm_sp_joint_unrolled',
               'afdm_sp_joint_unrolled.lmmse_baseline', 'afdm_sp_joint_unrolled.drce_baseline',
               'afdm_sp_joint_unrolled.pbigabp_baseline'}
    if set(extra) - allowed:
        raise ValueError(f'unexpected replay module imports: {sorted(set(extra) - allowed)}')
    missing = sorted(archived.keys() - ctx.source_md5.keys())
    changed = sorted(name for name, digest in archived.items() if name in ctx.source_md5 and ctx.source_md5[name] != digest)
    if missing or changed:
        raise ValueError(f'archived source identity differs: missing={missing}; changed={changed}')
    # The frozen qualifier compares its original whole-module table and absolute
    # paths. Relocate only the path prefix in a private copy for the local smoke.
    expected_paths = identity['frozen_actual_paths']
    if local_smoke and HERE.parents[1] != gram_cohort.ROOT:
        expected_paths = {key: str(HERE.parents[1] / Path(path).relative_to(gram_cohort.ROOT))
                          for key, path in expected_paths.items()}
    bound_identity = dict(identity, frozen_actual_paths=expected_paths)
    filtered_ctx = SimpleNamespace(**vars(ctx))
    filtered_ctx.source_md5 = {name: ctx.source_md5[name] for name in archived}
    paths = replay.qualify_sources(filtered_ctx, dict(receipt, identity=bound_identity))
    return dict(loaded_frozen_paths=paths, diagnostic_addon_modules=extra)


def load_references(args, ctx, config):
    provenance = {}

    def qualify(current_ctx, archived_receipt):
        provenance.update(qualify_sources(current_ctx, archived_receipt, local_smoke=args.smoke_one_key))

    helper = SimpleNamespace(e3d=replay.e3d, aggregate=replay.aggregate, replay=replay.replay,
                             qualify_sources=qualify)
    three, inputs, identity = gram_cohort.load_references(args, ctx, helper, cohort_archive.trajectory)
    summary_path = args.gram_rows / 'summary.json'
    summary_sha = hashlib.sha256(summary_path.read_bytes()).hexdigest()
    if summary_sha != EXPECTED_GRAM_SUMMARY:
        raise ValueError(f'qualified Gram-cohort summary SHA256 differs: {summary_sha}')
    summary = json.loads(summary_path.read_text())
    archive_identity = identity
    if args.smoke_one_key and HERE.parents[1] != gram_cohort.ROOT:
        # The validator checked its MD5 before recording its local absolute path.
        validator = Path(identity['three']['validator_path']).relative_to(HERE.parents[1])
        archive_identity = dict(identity, three=dict(identity['three'],
                                                     validator_path=str(gram_cohort.ROOT / validator)))
    cohort, hashes, source, _ = cohort_archive.load(args.gram_rows, three, inputs, archive_identity)
    if summary['raw_sha256'] != hashes or summary['source_identity'] != source:
        raise ValueError('Gram-cohort archive identity differs from its qualified summary')
    block_md5 = replay.e3d.e3_lib.md5_file(Path(kernel.gram_block.__file__))
    if block_md5 != gram_cohort.BLOCK_MD5:
        raise ValueError(f'loaded Gram block source MD5 differs: {block_md5}')
    config['reference'] = dict(archives=identity, gram_summary_sha256=summary_sha, gram_raw_sha256=hashes,
                               environment=ctx.environment, source_md5=ctx.source_md5,
                               gram_block_md5=block_md5,
                               merge_atoms_source_md5=replay.e3d.e3_lib.md5_file(Path(sm_driver.__file__)),
                               **provenance)
    return three, inputs, {replay.e3d.key_of(row): row for row in cohort}


def detect_and_score(ctx, native, physical, obs, channel, prior, truth, mode):
    det = kernel.detect(native, physical, channel, obs, prior, 1 - ctx.system.rho, mode)
    gram_cohort.validate_detection(det, 'full' if mode == 'eG' else mode, channel, obs['sigma2'])
    llr = det['extrinsic']
    dec = ctx.native.decoder_messages(ctx.code, np.clip(llr, -20, 20), maxiter=50)
    errors = int(replay.e3d.gd.score(ctx, dec['decoded'], truth))
    score = dict(info_errors=errors, fer=int(errors > 0), decoded_sha256=replay.e3d.gd.bits_sha(dec['decoded']),
                 extrinsic_bit_logloss=replay.replay.oldd.bit_loss(llr, truth['coded']))
    return score, dict(states=[{'h': det['states'][0]['h']}], extrinsic=llr)


def compare_decision(actual, expected, gate, key, upstream, mode):
    got = {name: actual[name] for name in DECISION}
    want = {name: expected[name] for name in DECISION}
    if got != want:
        raise GateFailure(gate, 'archived decoded result differs', key=key, upstream=upstream,
                          interface=mode, expected=want, actual=got)
    return actual['fer']


def channel_like(channel, delays, dopplers, gains):
    return type(channel)(channel.n, channel.c1, channel.c2, delays, dopplers, gains)


def merge_channel(channel):
    paths = [SimpleNamespace(delay=delay, doppler=doppler)
             for delay, doppler in zip(channel.delays, channel.dopplers)]
    delays, dopplers, gains, _ = sm_driver.merge_atoms(paths, channel.gains)
    return channel_like(channel, delays, dopplers, gains)


def g3_check(native, channel, duplicated, key, upstream):
    metrics = kernel.initial_split_metrics(native, channel, duplicated)
    if (metrics['operator_relative'] > 1e-12 or metrics['gain_aggregate_max'] != 0.0
            or metrics['prior_aggregate_max'] != 0.0):
        raise GateFailure('G3', 'duplicate H or aggregate prior differs', key=key, upstream=upstream, **metrics)
    return metrics


def g4_check(native, physical):
    original = physical.Channel(32, 5 / 64, np.sqrt(2) / 1024, [1, 3], [.25, -.5], [.75 + .25j, -.25 + .5j])
    merged = merge_channel(kernel.duplicate(original))
    same_atoms = all(np.array_equal(getattr(merged, field), getattr(original, field))
                     for field in ('delays', 'dopplers', 'gains'))
    h_relative = kernel.operator_error(native, original, merged)
    details = dict(scope='one original atom per delay; exactly two identical copies per atom',
                   paths=original.p, same_atoms=same_atoms, h_relative=h_relative)
    if not same_atoms or h_relative > 1e-12:
        raise GateFailure('G4', 'exact duplicate merge did not restore the original support and H', **details)
    return dict(status='PASS', **details)


def gate_frame(ctx, native, physical, frame, grid, references):
    three, inputs, gram = references
    for meta, obs, _, truth in replay.e3d.cells_of_frame(ctx, frame, grid, None):
        key = replay.e3d.key_of(meta)
        expected_obs = gram[key]['observation_sha256']
        actual_obs = {field: replay.aggregate.array_sha(obs[field]) for field in ('y', 'pilot')}
        if actual_obs != expected_obs:
            raise GateFailure('G1', 'old observation input differs', key=key, expected=expected_obs, actual=actual_obs)
        _, prior = replay.aggregate.restore_inputs(inputs[key])
        if not np.array_equal(ctx.encode(ctx.code, truth['info']), truth['coded']):
            raise ValueError(f'codeword reconstruction: {key}')
        meta = {name: meta[name] for name in ('scenario', 'rho_permille', 'snr_centi_db', 'frame')}
        for upstream in UPSTREAMS:
            saved = three[key]['three_mode'][upstream]
            support = saved['support']
            channel = replay.e3d.make_channel(ctx, len(obs['y']), support['delays'], support['dopplers'],
                                              replay.replay.complex_array(saved['h0']))
            duplicated = kernel.duplicate(channel)
            geometry = g3_check(native, channel, duplicated, key, upstream)
            baseline = {}
            for mode in MODES:
                gate = 'G2' if mode == 'eG' else 'G1'
                expected = gram[key]['arms'][upstream]['full'] if mode == 'eG' else saved['modes'][mode]
                baseline[mode] = detect_and_score(ctx, native, physical, obs, channel, prior, truth, mode)
                compare_decision(baseline[mode][0], expected, gate, key, upstream, mode)
                if mode == 'eG':
                    actual_loss = baseline[mode][0]['extrinsic_bit_logloss']
                    saved_loss = expected['extrinsic_bit_logloss']
                    if not np.isclose(actual_loss, saved_loss, rtol=gram_cohort.RTOL, atol=gram_cohort.ATOL):
                        raise GateFailure('G2', 'archived full-Gram log loss differs', key=key, upstream=upstream,
                                          expected=saved_loss, actual=actual_loss)
            yield meta, obs, truth, prior, upstream, channel, duplicated, geometry, baseline


def diagnostics(ctx, native, physical, item):
    meta, obs, truth, prior, upstream, channel, duplicated, _, baseline = item
    a, b = [], []
    merged = merge_channel(channel)
    merge_error = kernel.operator_error(native, channel, merged)
    for mode in MODES:
        original, original_det = baseline[mode]
        repeated, repeated_det = detect_and_score(ctx, native, physical, obs, duplicated, prior, truth, mode)
        metrics = kernel.compare_split(native, channel, duplicated, original_det, repeated_det)
        base = dict(meta, upstream=upstream, interface=mode)
        a.append(dict(base, first_h_relative=metrics['operator_relative'],
                      actions=metrics['actions'],
                      action_relative=[action['relative_l2'] for action in metrics['actions']],
                      llr_max_abs=metrics['extrinsic']['max_abs'], llr_relative_l2=metrics['extrinsic']['relative_l2'],
                      decoded_agrees=original['decoded_sha256'] == repeated['decoded_sha256'],
                      invariant=metrics['invariant'], original=original, duplicated=repeated))
        if mode in MERGE_MODES:
            compressed, _ = detect_and_score(ctx, native, physical, obs, merged, prior, truth, mode)
            b.append(dict(base, operator_relative=merge_error, original=original, merged=compressed))
    return a, b


def worker(child, ctx, native, physical, frames, grid, references):
    """Keep replay results in memory while the parent clears all four gates."""
    try:
        items = [item for frame in frames for item in gate_frame(ctx, native, physical, frame, grid, references)]
        child.send(('pass', [dict(meta=item[0], upstream=item[4], geometry=item[-2],
                                  failures={m: item[-1][m][0]['fer'] for m in MODES}) for item in items]))
        if child.recv() != 'diagnose':
            raise RuntimeError('unexpected gate release token')
        a, b = [], []
        for item in items:
            ar, br = diagnostics(ctx, native, physical, item)
            a.extend(ar)
            b.extend(br)
        child.send(('pass', (a, b)))
    except Exception as exc:
        details = dict(gate=exc.gate, **exc.details) if isinstance(exc, GateFailure) else {}
        child.send(('failure', dict(details, error=str(exc), traceback=traceback.format_exc())))
    finally:
        child.close()


def collect(pipes, deadline):
    pending = set(pipes)
    results = []
    while pending:
        ready = wait(pending, timeout=max(0, deadline - time.monotonic()))
        if not ready:
            raise TimeoutError('2 core-hour budget reached')
        for pipe in ready:
            state, value = pipe.recv()
            if state == 'failure':
                gate = value.pop('gate', 'worker')
                message = value.pop('error')
                raise GateFailure(gate, message, **value)
            results.append(value)
            pending.remove(pipe)
    return results


def validate_gate_population(gates, shards, keys, references, smoke):
    rows = [row for shard in shards for row in shard]
    population = {(replay.e3d.key_of(r['meta']), r['upstream']) for r in rows}
    expected = {(key, upstream) for key in keys for upstream in UPSTREAMS}
    if population != expected or len(rows) != len(expected):
        raise GateFailure('G1', 'baseline replay population differs', rows=len(rows), unique=len(population))
    counts = {u: {mode: sum(r['failures'][mode] for r in rows if r['upstream'] == u) for mode in MODES}
              for u in UPSTREAMS}
    for gate, modes in [('G1', NATIVE_MODES), ('G2', ('eG',))]:
        got = {u: {m: counts[u][m] for m in modes} for u in UPSTREAMS}
        if smoke:
            three, _, gram = references
            key = gram_cohort.KEY
            want = {u: {m: (gram[key]['arms'][u]['full'] if m == 'eG' else three[key]['three_mode'][u]['modes'][m])['fer']
                        for m in modes} for u in UPSTREAMS}
        else:
            want = {u: {m: EXPECTED_COUNTS[u][MODES.index(m)] for m in modes} for u in UPSTREAMS}
        if got != want:
            raise GateFailure(gate, 'failure totals differ from qualified archive', actual=got, expected=want)
        gates[gate] = dict(status='PASS', decoded_matches=len(rows) * len(modes), failure_counts=got)
    gates['G2']['logloss_matches'] = len(rows)
    gates['G1']['saved_waveform_hash_pairs_matched'] = len(keys)
    geometry = {metric: max(r['geometry'][metric] for r in rows) for metric in rows[0]['geometry']}
    gates['G3'] = dict(status='PASS', checked=len(rows), **geometry)


def run(args, config, gates, deadline):
    ctx = replay.e3d.p1ctx.load()
    native = sys.modules[ctx.native.scalar_joint.__module__]
    physical = sys.modules['physical']
    config['receiver_modules'] = dict(detector=native.__name__, decoder=ctx.native.__name__, physical=physical.__name__)
    try:
        gates['Synthetic'] = dict(status='PASS', **kernel.synthetic_checks(native, physical))
    except Exception as exc:
        raise GateFailure('Synthetic', str(exc)) from exc
    gates['G4'] = g4_check(native, physical)
    refs = load_references(args, ctx, config)
    keys = SMOKE_KEYS if args.smoke_one_key else gram_cohort.EXPECTED
    frames = sorted({key[3] for key in keys})
    grid = {'U_300': [7.]} if args.smoke_one_key else replay.replay.GRID
    print('Synthetic and G4 pass, archives qualified', flush=True)
    forks = mp.get_context('fork')
    workers = []
    try:
        for shard in range(args.workers):
            parent, child = forks.Pipe()
            process = forks.Process(target=worker, args=(child, ctx, native, physical, frames[shard::args.workers], grid, refs))
            process.start()
            child.close()
            workers.append((process, parent))
        pipes = [pipe for _, pipe in workers]
        validate_gate_population(gates, collect(pipes, deadline), keys, refs, args.smoke_one_key)
        write_json(args.out / 'gates.json', receipt(config, gates))
        print('All gates pass, starting questions A and B', flush=True)
        for pipe in pipes:
            pipe.send('diagnose')
        shards = collect(pipes, deadline)
        for process, _ in workers:
            process.join(max(0, deadline - time.monotonic()))
            if process.exitcode != 0:
                raise RuntimeError(f'diagnostic worker exit {process.exitcode}')
        for index, (filename, modes) in enumerate([('question_a.jsonl', MODES), ('question_b.jsonl', MERGE_MODES)]):
            rows = [row for shard in shards for row in shard[index]]
            rows.sort(key=lambda r: (replay.e3d.key_of(r), r['upstream'], r['interface']))
            identity = {(replay.e3d.key_of(r), r['upstream'], r['interface']) for r in rows}
            expected = {(key, u, mode) for key in keys for u in UPSTREAMS for mode in modes}
            if identity != expected or len(rows) != len(expected):
                raise ValueError(f'incomplete diagnostic population: {filename}')
            write_jsonl(args.out / filename, rows)
    finally:
        for process, pipe in workers:
            if process.is_alive():
                process.kill()
            pipe.close()
        for process, _ in workers:
            process.join()


def receipt(config, gates):
    return dict(_argv=sys.argv[1:], _config=config, gates=gates)


def budget_alarm(_signum, _frame):
    raise TimeoutError('2 core-hour budget reached')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=8, choices=range(1, 9))
    parser.add_argument('--smoke-one-key', action='store_true', help='replay the saved U/.3/7 dB/9100 key without a cohort category')
    parser.add_argument('--out', type=Path, default=HERE / 'out')
    parser.add_argument('--old-rows', type=Path, default=gram_cohort.OLD)
    parser.add_argument('--three-rows', type=Path, default=gram_cohort.THREE)
    parser.add_argument('--gram-rows', type=Path, default=gram_cohort.OUT)
    args = parser.parse_args()
    args.out = args.out.resolve()
    out_root = HERE / 'out'
    if args.out != out_root and args.out.parent != out_root:
        parser.error('use the experiment out/ directory or a new direct child of out/')
    if args.smoke_one_key and args.out == out_root:
        parser.error('--smoke-one-key requires a dedicated --out child')
    if args.smoke_one_key:
        args.workers = 1
    args.out.mkdir(parents=True, exist_ok=False)
    gates = {gate: dict(status='NOT_RUN') for gate in ('Synthetic', 'G1', 'G2', 'G3', 'G4')}
    # Include the coordinator as well as each worker. Reserve time for termination and receipt writes.
    budget_seconds = 7200 / (args.workers + 1) - 2
    frames = [gram_cohort.KEY[3]] * 2 if args.smoke_one_key else [FRAMES[0], FRAMES[-1]]
    config = dict(smoke_one_key=args.smoke_one_key, smoke_key=gram_cohort.KEY if args.smoke_one_key else None,
                  workers=args.workers, threads_per_worker=1, core_hour_cap=2,
                  conservative_wall_cap_seconds=budget_seconds, frames=frames,
                  key_count=1 if args.smoke_one_key else len(gram_cohort.EXPECTED), iterations=20, damping=.3, ldpc_maxiter=50,
                  h_relative_tolerance=1e-10, llr_max_abs_tolerance=1e-9,
                  initial_h_relative_tolerance=1e-12,
                  old_rows=str(args.old_rows), three_rows=str(args.three_rows), gram_rows=str(args.gram_rows),
                  own_sha256={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                              for name in ('driver.py', 'kernel.py', 'summarize.py')})
    deadline = STARTED + budget_seconds
    signal.signal(signal.SIGALRM, budget_alarm)
    signal.setitimer(signal.ITIMER_REAL, max(1e-6, deadline - time.monotonic()))
    try:
        run(args, config, gates, deadline)
        if not args.smoke_one_key:
            summary = summarize.summarize(args.out)
            summary['_argv'] = sys.argv[1:]
            write_json(args.out / 'summary.json', summary)
        exit_code, state = 0, 'DONE'
    except Exception as exc:
        if isinstance(exc, GateFailure) and exc.gate in gates:
            gates[exc.gate] = dict(status='FAIL', **exc.details, error=str(exc))
        error = dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc())
        write_json(args.out / 'failure.json', dict(receipt(config, gates), error=error))
        if not (args.out / 'gates.json').exists():
            write_json(args.out / 'gates.json', receipt(config, gates))
        print(error['traceback'], file=sys.stderr, flush=True)
        exit_code, state = 1, 'STOPPED'
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    wall = time.monotonic() - STARTED
    usage = [resource.getrusage(scope) for scope in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    core_hours = sum(u.ru_utime + u.ru_stime for u in usage) / 3600
    pending = args.out / '.status.pending'
    pending.write_text(f'{state} wall_seconds={wall:.3f} core_hours={core_hours:.6f} workers={args.workers}\n')
    pending.replace(args.out / 'STATUS')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
