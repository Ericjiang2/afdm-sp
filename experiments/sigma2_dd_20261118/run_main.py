"""Run the frozen sigma2 DD cohort under a measured process CPU budget."""

import argparse
from multiprocessing import get_context
from multiprocessing.connection import wait
from pathlib import Path
import hashlib
import json
import math
import os
import re
import resource
import sys
import time
import traceback

from receiver_study import ARMS, CAP, HERE, RHO, SCENARIO, evaluate_a3, evaluate_b, load

FIRST, STOP = 11000, 12000
SNRS = tuple(range(450, 801, 50))
FRAMES_PER_SHARD = 5
CORE_HOUR_CAP = 5
MAX_WORKERS = 16


def write_shard(study, out, number, frames):
    q, ctx = study[:2]
    keys = 0
    with (out / f'rows_shard{number:03d}.jsonl').open('x', buffering=1) as handle:
        for frame in frames:
            if (out / '.stop_workers').exists():
                return keys
            base, diag = q.sm.p1ctx.base(ctx, SCENARIO, RHO, frame)
            for snr in SNRS:
                if (out / '.stop_workers').exists():
                    return keys
                _, actual, truth = q.sm.gd.observe(ctx, base, diag, RHO, snr)
                truth_delays = [int(d) for d in truth['l_i']]
                if len(truth_delays) != CAP:
                    raise ValueError(f'Unexpected physical path count at frame {frame}')
                arms = {}
                for method in ARMS:
                    b, supplied, _ = evaluate_b(study, method, actual, truth)
                    a3 = evaluate_a3(study, supplied, truth)
                    arms[method] = dict(B=b, A3_errors=a3['info_errors'])
                row = dict(frame=frame, snr_centi_db=snr, sigma2=actual['sigma2'], truth_delays=truth_delays, arms=arms)
                print(json.dumps(row, allow_nan=False, separators=(',', ':')), file=handle)
                keys += 1
    return keys


def worker(frozen_slot, out, qualified, channel):
    with channel:
        try:
            study = load(frozen_slot)
            ctx = study[1]
            if ctx.source_md5 != qualified['source_md5'] or ctx.source_paths != qualified['source_paths']:
                raise ValueError('Loaded receiver source inventory differs from qualification')
            for name in ('hostname', 'numpy', 'scipy', 'torch', 'torch_num_threads', 'torch_num_interop_threads'):
                if ctx.environment[name] != qualified['environment'][name]:
                    raise ValueError(f'Worker environment differs from qualification: {name}')
            while (assignment := channel.recv()) is not None:
                shard, frames = assignment
                channel.send((shard, write_shard(study, out, shard, frames), None))
        except Exception:
            channel.send((None, 0, traceback.format_exc()))


def schedule(frozen, out, qualified, groups, workers, cpu_seconds, clock_ticks):
    """Dispatch only when a worker is free and the CPU budget has room."""
    runtime = get_context('spawn')
    channels, pending, cpu_by_pid, completed, errors = {}, {}, {}, {}, []
    stop_path = out / '.stop_workers'
    queue = iter(enumerate(groups))
    reason = None
    start = time.process_time()

    def hours():
        for process in channels.values():
            seconds = cpu_seconds(process.pid, clock_ticks)
            if seconds is not None:
                cpu_by_pid[process.pid] = seconds
        return (sum(cpu_by_pid.values()) + time.process_time() - start) / 3600

    try:
        for _ in range(min(workers, len(groups))):
            parent, child = runtime.Pipe()
            process = runtime.Process(target=worker, args=(frozen, out, qualified, child))
            try:
                process.start()
            finally:
                child.close()
            channels[parent] = process
            shard, frames = next(queue)
            pending[parent] = shard
            parent.send((shard, frames))
        while pending:
            available = wait(pending, timeout=1)
            for channel in available:
                expected = pending.pop(channel)
                try:
                    shard, keys, error = channel.recv()
                except (EOFError, OSError) as exc:
                    shard, keys, error = expected, 0, repr(exc)
                if error or shard != expected:
                    errors.append(dict(shard=expected, detail=error or f'Received shard {shard}'))
                    reason = reason or f'shard_{expected:03d}_error'
                else:
                    completed[shard] = keys
            if hours() >= CORE_HOUR_CAP:
                reason = reason or 'core_budget'
            if reason:
                stop_path.touch(exist_ok=True)
                continue
            for channel in available:
                next_job = next(queue, None)
                if next_job is None:
                    break
                pending[channel] = next_job[0]
                channel.send(next_job)
    except Exception:
        reason = reason or 'scheduler_error'
        errors.append(dict(detail=traceback.format_exc()))
        stop_path.touch(exist_ok=True)
    finally:
        for channel, process in channels.items():
            if process.is_alive():
                try:
                    channel.send(None)
                except (BrokenPipeError, OSError):
                    pass
            channel.close()
        for process in channels.values():
            process.join()
    return completed, reason, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--frozen-slot', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        parser.error('A full before-run Git commit is required')
    sys.path.insert(0, str(args.frozen_slot))
    from main_v2 import archive_rows, utc_now, worker_cpu_seconds, write_json

    thread_vars = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
    if any(os.environ.get(name) != '1' for name in thread_vars) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('CPU-only run requires hidden CUDA and one BLAS/OpenMP thread')
    protocol = HERE / 'PROTOCOL.md'
    if not protocol.read_text().startswith('# FROZEN 2026-11-18 '):
        raise ValueError('The approved protocol is required')
    gate = json.loads((HERE / 'out/gate_20261118/g1_final.json').read_text())
    if gate['status'] != 'PASS':
        raise ValueError('The revised G1 receipt is required')
    qualified = gate['_config']
    sources = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in HERE.glob('*.py')}
    if any(sources[name] != sha for name, sha in qualified['own_sha256'].items()):
        raise ValueError('Study code differs from qualification')
    available = len(os.sched_getaffinity(0)) - math.ceil(os.getloadavg()[0]) - 16
    workers = min(MAX_WORKERS, available)
    if workers < 1:
        raise RuntimeError('No CPU worker slot available with shared-host headroom')

    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    started, start = utc_now(), time.process_time()
    groups = [range(frame, frame + FRAMES_PER_SHARD) for frame in range(FIRST, STOP, FRAMES_PER_SHARD)]
    config = dict(commit=args.commit, frame_range=[FIRST, STOP - 1], snr_centi_db=SNRS, cap=CAP,
                  scenario=SCENARIO, rho=RHO, arms=ARMS, workers=workers, core_hour_cap=CORE_HOUR_CAP,
                  frames_per_shard=FRAMES_PER_SHARD, expected_keys=(STOP - FIRST) * len(SNRS),
                  entropy='2261fde33dab09d163b6dd926ef8d521e5d44fdda771d356f02efabfee96eb23', domain='TCRF',
                  frozen_slot=str(args.frozen_slot), protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest(),
                  study_sha256=sources, receiver_source_md5=qualified['source_md5'],
                  receiver_source_paths=qualified['source_paths'], environment=qualified['environment'])
    write_json(out / 'RUN_CONFIG.json', dict(_argv=sys.argv, _config=config))
    print(f'RUNNING {workers} workers {len(groups)} shards at cap {CORE_HOUR_CAP} core-hours', flush=True)
    complete, reason, errors = schedule(args.frozen_slot, out, qualified, groups, workers,
                                        worker_cpu_seconds, os.sysconf('SC_CLK_TCK'))
    expected_per_shard = len(SNRS) * FRAMES_PER_SHARD
    done = sum(count == expected_per_shard for count in complete.values())
    if reason is None and done != len(groups):
        reason = 'incomplete_shards'
    try:
        archive_rows(out)
    except Exception:
        reason = reason or 'archive_error'
        errors.append(dict(detail=traceback.format_exc()))
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    hours = (usage.ru_utime + usage.ru_stime + time.process_time() - start) / 3600
    if hours >= CORE_HOUR_CAP:
        reason = reason or 'core_budget'
    write_json(out / 'main_receipt.json',
               dict(_argv=sys.argv, _config=config, started_utc=started, ended_utc=utc_now(),
                    planned_shards=len(groups), completed_shards=done, keys=sum(complete.values()),
                    core_hours=hours, reason=reason, errors=errors))
    status = f'STOPPED {reason} {hours:.6f}' if reason else f'DONE {done} {hours:.6f}'
    pending = out / 'STATUS.pending'
    pending.write_text(status + '\n')
    pending.rename(out / 'STATUS')
    print(status, flush=True)
    return int(reason is not None)


if __name__ == '__main__':
    raise SystemExit(main())
