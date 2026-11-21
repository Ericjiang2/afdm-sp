# Source: sigma2_dd_20261118/run_main.py for bounded scheduling, adapted for the archived trigger population and Phase 1 logger.
"""Replay the frozen admission-law target cohort on deinlab."""

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from multiprocessing import get_context
from multiprocessing.connection import wait
import os
from pathlib import Path
import re
import resource
import sys
import time
import traceback

from gates import CAP, ENV_FIELDS, FROZEN_COMMIT, HERE, TARGET_COUNT, compare_fields, load

FIRST, STOP, SHARD_FRAMES = 10000, 11000, 5
CELLS = tuple((scenario, rho) for scenario in ('U', 'G') for rho in (.3, .5))
SNRS = tuple(range(450, 701, 50))
CORE_HOUR_CAP = 2
MAX_WORKERS = 16
THREADS = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')


def input_tasks(archive, frozen_slot, qualified):
    config = json.loads((archive / 'RUN_CONFIG.json').read_text())['_config']
    receipt = json.loads((archive / 'main_receipt.json').read_text())
    if (config['commit'] != FROZEN_COMMIT or receipt['_config']['commit'] != FROZEN_COMMIT
            or receipt['completed_shards'] != (STOP - FIRST) // SHARD_FRAMES or receipt['reason'] is not None
            or config['frame_range'] != [FIRST, STOP - 1] or config['frames_per_shard'] != SHARD_FRAMES):
        raise ValueError('Wrong or incomplete slot-mismatch archive')
    for name, digest in config['own_sha256'].items():
        if hashlib.sha256((frozen_slot / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Frozen snapshot mismatch at {name}')
    for field in ('source_md5', 'source_paths', 'codelay_source_sha256'):
        gate_field = 'codelay_sha256' if field == 'codelay_source_sha256' else field
        if config[field] != qualified[gate_field]:
            raise ValueError(f'Archive and gate differ at {field}')

    manifest = (archive / 'REMOTE_ROWS_MD5.txt').read_bytes()
    if hashlib.md5(manifest).hexdigest() != 'c7c895f191ed105f12de52c9a8824e69':
        raise ValueError('Input manifest differs from the published slot-mismatch archive')
    inputs = [line.split() for line in manifest.decode().splitlines()]
    if [name for _, name in inputs] != [f'rows_shard{i:03d}.jsonl.gz' for i in range((STOP - FIRST) // SHARD_FRAMES)]:
        raise ValueError('Unexpected input shard inventory')
    groups, total = [], 0
    for shard, (digest, name) in enumerate(inputs):
        path = archive / name
        if hashlib.md5(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Input shard MD5 differs at {name}')
        lo = FIRST + shard * SHARD_FRAMES
        expected = {(f, s, r, n) for f in range(lo, lo + SHARD_FRAMES) for s, r in CELLS for n in SNRS}
        selected = defaultdict(list)
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                if not line.startswith('{"family":"M",'):
                    continue
                row = json.loads(line)
                frame, scenario, rho, snr = (row[k] for k in ('frame', 'scenario', 'rho', 'snr_centi_db'))
                if snr not in SNRS:
                    continue
                expected.remove((frame, scenario, rho, snr))
                cap = row['s'][str(CAP)]
                if cap['triggered'] != (cap['f0']['syndrome'] > 0):
                    raise ValueError(f'Archive trigger mismatch at {frame}/{scenario}/{rho}/{snr}')
                if cap['triggered']:
                    edits = {arm: (result['edits'] or [None])[0] for arm, result in cap['arms'].items()}
                    if set(edits) != {'A1c', 'A2'}:
                        raise ValueError('Target is missing a continuation')
                    selected[frame, scenario, rho].append((snr, cap['f0'], edits))
        if expected:
            raise ValueError(f'Input shard {shard} missed {len(expected)} keys')
        groups.append(dict(selected))
        total += sum(map(len, selected.values()))
    if total != TARGET_COUNT:
        raise ValueError(f'Archive has {total} triggers, expected {TARGET_COUNT}')
    return groups


def replay_shard(study, out, number, group):
    from replay import first_exchange_from_f0

    q, ctx, variant = study[:3]
    sm = q.sm
    path = out / f'rows_shard{number:03d}.jsonl.gz'
    keys = 0
    with path.with_suffix('.gz.pending').open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, compresslevel=3, mtime=0) as handle:
            for (frame, scenario, rho), observations in group.items():
                base, diag = sm.p1ctx.base(ctx, scenario, rho, frame)
                for snr, expected_f0, edits in observations:
                    if (out / '.stop_workers').exists():
                        return keys
                    _, obs, truth = sm.gd.observe(ctx, base, diag, rho, snr)
                    dec, arrays, syndrome, _ = sm.f0_state(ctx, variant, obs, CAP)
                    delays = arrays['r1_delays'].tolist()
                    got = dict(syndrome=syndrome, info_errors=sm.gd.score(ctx, dec['decoded'], truth),
                               slot_count=len(delays), slot_count_r0=len(arrays['r0_delays']),
                               r1_delays=delays, r1_dopplers=arrays['r1_dopplers'].tolist())
                    identity = (frame, scenario, rho, snr)
                    mismatch = compare_fields(got, expected_f0)
                    if mismatch:
                        raise ValueError(f'F0 archive mismatch at {identity}: {mismatch}')
                    result = first_exchange_from_f0(study, obs, arrays, truth)
                    for arm, expected_edit in edits.items():
                        actual = result['arms'][arm]['actual_first_edit']
                        if (actual is None) != (expected_edit is None) or (
                                actual is not None and any(actual[k] != expected_edit[k] for k in ('slot', 'old', 'new'))):
                            raise ValueError(f'{arm} archive first-edit mismatch at {identity}')
                    result.update(family='M', frame=frame, scenario=scenario, rho=rho, snr_centi_db=snr, cap=CAP)
                    line = json.dumps(result, separators=(',', ':'), allow_nan=False) + '\n'
                    handle.write(line.encode())
                    keys += 1
    path.with_suffix('.gz.pending').rename(path)
    return keys


def worker(frozen_slot, out, qualified, connection):
    with connection:
        try:
            study = load(frozen_slot)
            q, ctx = study[:2]
            for key in ('source_md5', 'source_paths'):
                if getattr(ctx, key) != qualified[key]:
                    raise ValueError(f'Loaded receiver differs from G1 at {key}')
            if q.CODELAY_SHA != qualified['codelay_sha256'] or any(
                    ctx.environment[k] != qualified['environment'][k] for k in ENV_FIELDS):
                raise ValueError('Loaded CODELAY or runtime differs from G1')
            while (job := connection.recv()) is not None:
                number, group = job
                connection.send((number, replay_shard(study, out, number, group), None))
        except Exception:
            connection.send((None, 0, traceback.format_exc()))


def schedule(frozen_slot, out, qualified, groups, workers, start_cpu):
    from main_v2 import worker_cpu_seconds

    runtime = get_context('spawn')
    processes, pending, counts, errors = {}, {}, {}, []
    queue = iter(enumerate(groups))
    ticks = os.sysconf('SC_CLK_TCK')
    reason = None

    def dispatch(channel):
        job = next(queue, None)
        if job is not None:
            channel.send(job)
            pending[channel] = job[0]

    try:
        for _ in range(min(workers, len(groups))):
            parent, child = runtime.Pipe()
            process = runtime.Process(target=worker, args=(frozen_slot, out, qualified, child))
            try:
                process.start()
            finally:
                child.close()
            processes[parent] = process
            dispatch(parent)
        while pending:
            ready = wait(pending, timeout=1)
            for channel in ready:
                expected = pending.pop(channel)
                shard, keys, error = channel.recv()
                if error or expected != shard:
                    reason = reason or f'shard_{expected:03d}_error'
                    errors.append(error or f'Shard {expected} returned {shard}')
                else:
                    counts[shard] = keys
            cpu = time.process_time() - start_cpu + sum(
                worker_cpu_seconds(p.pid, ticks) or 0 for p in processes.values())
            if cpu >= CORE_HOUR_CAP * 3600:
                reason = reason or 'core_budget'
            if reason:
                (out / '.stop_workers').touch()
            else:
                for channel in ready:
                    dispatch(channel)
    except (Exception, KeyboardInterrupt):
        reason = reason or 'scheduler_error'
        errors.append(traceback.format_exc())
        (out / '.stop_workers').touch()
    finally:
        for channel, process in processes.items():
            if process.is_alive():
                try:
                    channel.send(None)
                except (BrokenPipeError, OSError):
                    pass
            channel.close()
        for process in processes.values():
            process.join()
    return counts, reason, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--frozen-slot', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    start = time.process_time()
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        parser.error('Pass the full before-run commit')
    if any(os.environ.get(name) != '1' for name in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('CPU-only and single-thread environment required')
    protocol = HERE / 'PROTOCOL.md'
    if protocol.read_text().splitlines()[0] != '# FROZEN 2026-11-18':
        raise ValueError('Expected the frozen protocol')
    gate = json.loads((HERE / 'out/gate_20261118/g1.json').read_text())
    qualified = gate['_config']
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')}
    if gate['status'] != 'PASS' or any(sources[name] != sha for name, sha in qualified['own_sha256'].items()):
        raise ValueError('Expected the G1-qualified replay and helpers')

    sys.path.insert(0, str(args.frozen_slot))
    from main_v2 import utc_now, write_json

    out = args.out
    if any(out.iterdir()):
        # The launcher owns the new output directory and opens its log first.
        if {p.name for p in out.iterdir()} != {'run.log'}:
            raise ValueError('Expected a new output directory')
    started = utc_now()
    workers = min(MAX_WORKERS, len(os.sched_getaffinity(0)) - 16)
    if workers < 1:
        raise RuntimeError('No CPU worker available with required host headroom')
    groups = input_tasks(args.archive, args.frozen_slot, qualified)
    planned_counts = [sum(map(len, group.values())) for group in groups]
    config = dict(commit=args.commit, family='M', frame_range=[FIRST, STOP - 1], cells=CELLS, cap=CAP,
                  snr_centi_db=SNRS, core_hour_cap=CORE_HOUR_CAP, workers=workers, expected_keys=TARGET_COUNT,
                  shard_expected_keys=planned_counts, protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
                  study_sha256=sources, frozen_slot=str(args.frozen_slot), archive=str(args.archive),
                  archive_commit=FROZEN_COMMIT, receiver_source_md5=qualified['source_md5'],
                  receiver_source_paths=qualified['source_paths'], environment=qualified['environment'])
    write_json(out / 'RUN_CONFIG.json', dict(_argv=sys.argv, _config=config))
    print(f'RUNNING {workers} workers {len(groups)} shards {TARGET_COUNT} target keys', flush=True)
    counts, reason, errors = schedule(args.frozen_slot, out, qualified, groups, workers, start)
    complete = sum(counts.get(i) == count for i, count in enumerate(planned_counts))
    if complete != len(groups):
        reason = reason or 'incomplete_shards'
    with (out / 'REMOTE_ROWS_MD5.txt').open('x') as manifest:
        for path in sorted(out.glob('rows_shard*.jsonl.gz')):
            with path.open('rb') as handle:
                digest = hashlib.md5()
                for block in iter(lambda: handle.read(1 << 20), b''):
                    digest.update(block)
            manifest.write(f'{digest.hexdigest()}  {path.name}\n')
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    hours = (usage.ru_utime + usage.ru_stime + time.process_time() - start) / 3600
    if hours >= CORE_HOUR_CAP:
        reason = reason or 'core_budget'
    write_json(out / 'main_receipt.json', dict(_argv=sys.argv, _config=config,
               started_utc=started, ended_utc=utc_now(), completed_shards=complete, keys=sum(counts.values()),
               core_hours=hours, reason=reason, errors=errors))
    status = f'STOPPED {reason} {hours:.6f}' if reason else f'DONE {complete} {hours:.6f}'
    print(status, flush=True)
    pending = out / 'STATUS.pending'
    pending.write_text(status + '\n')
    pending.rename(out / 'STATUS')
    return int(reason is not None)


if __name__ == '__main__':
    raise SystemExit(main())
