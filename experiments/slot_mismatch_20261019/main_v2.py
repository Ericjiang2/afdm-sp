"""Run the frozen complete slot-mismatch cohort and publish one terminal status."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import re
import resource
import shutil
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
FRAMES = range(10000, 11000)
FRAMES_PER_SHARD = 5
WORKERS = 24
CORE_HOURS = 40
CELLS = tuple((s, r) for s in ('U', 'G') for r in (.3, .5))
KNOWN_FAMILIES = ('M', 'T6', 'T10')
THREADS = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
EXPECTED_PER_FRAME = {'M': 32, 'T6': 32, 'T10': 32, 'N': 8}


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + '.pending')
    with temporary.open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')
    temporary.rename(path)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def cap_record(q, ctx, variant, full, closed, obs, truth, cap, nominated):
    sm = q.sm
    dec, arrays, syndrome, _ = sm.f0_state(ctx, variant, obs, cap)
    slots = sm.slot_record(arrays, cap, nominated)
    if not slots['ok']:
        raise ValueError(f'Actual slot counts differ from min(cap, nominated): {slots}')
    delays = [int(x) for x in arrays['r1_delays']]
    f0 = dict(info_errors=sm.gd.score(ctx, dec['decoded'], truth), syndrome=syndrome,
              slot_count=slots['slot_count'], slot_count_r0=slots['slot_count_r0'], r1_delays=delays,
              r1_dopplers=[float(x) for x in arrays['r1_dopplers']])
    arms = {}
    if syndrome:
        true_delays = set(truth['l_i'])
        for name, kernel, arm in (('A1c', closed, 'A1'), ('A2', full, 'A2')):
            result = sm.e1d.run_branch(ctx, kernel, obs, arrays, arm)
            geometry = result['result']
            support = delays.copy()
            edits = []
            for edit in geometry.edits:
                slot, old, new = int(edit['slot']), edit['old'], edit['new']
                if support[slot] != old['delay']:
                    raise ValueError('Accepted edit disagrees with the entering slot')
                phantom = new['delay'] in support[:slot] + support[slot + 1:]
                edits.append(dict(step=int(edit['step']), slot=slot, old=old, new=new, phantom=phantom,
                                  dropped_true=old['delay'] in true_delays))
                support[slot] = new['delay']
            final_delays = [int(p.delay) for p in geometry.paths]
            if support != final_delays:
                raise ValueError('Accepted edits do not reproduce final delay support')
            arms[name] = dict(info_errors=sm.gd.score(ctx, result['decoder']['decoded'], truth),
                              final_delays=final_delays,
                              final_dopplers=[float(p.doppler) for p in geometry.paths], edits=edits)
    return dict(f0=f0, triggered=bool(syndrome), arms=arms)


def observation_rows(frame, q, ctx, variant, full, closed, generators, stop_requested):
    sm = q.sm
    for scenario, rho in CELLS:
        for family in KNOWN_FAMILIES:
            p, _ = q.FAMILIES[family]
            if stop_requested():
                return
            base, diagnostics = sm.p1ctx.base(generators[p], scenario, rho, frame)
            draws = q.fingerprint(base)
            if family == 'M':
                reference_draws = draws
            elif draws != reference_draws:
                raise ValueError(f'Exogenous streams changed in {frame}/{scenario}/{rho}/{family}')
            for snr in sm.ALL_SNR:
                if stop_requested():
                    return
                _, actual, truth = sm.gd.observe(ctx, base, diagnostics, rho, snr)
                truth_delays = [int(x) for x in truth['l_i']]
                if len(truth_delays) != p or max(truth_delays) > ctx.system.l_max_cap:
                    raise ValueError(f'True support mismatch in {frame}/{scenario}/{rho}/{family}')
                families = (family, 'N') if (family, scenario, rho) == ('M', 'G', .3) else (family,)
                for observed_family in families:
                    if stop_requested():
                        return
                    key = (observed_family, frame, scenario, rho, snr)
                    obs, noise = q.observe_only(actual, observed_family == 'N')
                    if noise is not None:
                        noise['ratio'] = noise['estimate'] / float(actual['sigma2'])
                    try:
                        nominated = sm.n_nominated(ctx, variant, obs)
                        by_cap = {str(cap): cap_record(q, ctx, variant, full, closed, obs, truth, cap, nominated)
                                  for cap in q.FAMILIES[observed_family][1]}
                        a3 = sm.p1ctx.p1_driver.compute_arms(ctx, obs, truth, ['A3'])['A3']
                        if a3['status'] != 'ok':
                            raise RuntimeError(a3)
                    except Exception as error:
                        raise RuntimeError(f'Receiver key failed: {key}') from error
                    yield dict(family=observed_family, frame=frame, scenario=scenario, rho=rho,
                               rho_permille=int(round(rho * 1000)), snr_centi_db=snr, P_true=p,
                               truth=dict(delays=truth_delays), n_distinct_nominated_delays=nominated,
                               noise=noise, s=by_cap, A3=dict(info_errors=int(a3['info_errors'])))


def initialize_worker(stop_path):
    global worker
    import qualify_v2 as q

    ctx, variant, full, closed, sources = q.load()
    generators = {p: q.generation(ctx, p) for p in (6, 10)}
    generators[8] = ctx
    worker = (q, ctx, variant, full, closed, generators, stop_path.exists, sources)


def write_shard(out, shard, frames, commit):
    q, ctx, variant, full, closed, generators, stop_requested, sources = worker
    started, cpu_start = utc_now(), time.process_time()
    counts = Counter()
    status = 'error'
    error = None
    try:
        if shard == 0:
            pinned = ('main_v2.py', 'qualify_v2.py', 'sm_driver.py', 'native_twofft_variant.py', 'PROTOCOL.md')
            write_json(out / 'RUN_CONFIG.json',
                       dict(_argv=sys.argv, _config=dict(commit=commit, scope='complete',
                            entropy=q.sm.p1ctx.p1_driver.ENTROPY_HEX, domain=q.sm.p1ctx.p1_driver.DOMAIN,
                            frame_range=[FRAMES.start, FRAMES.stop - 1], cells=CELLS, snr_centi_db=q.sm.ALL_SNR,
                            families=q.FAMILIES, expected_keys=len(FRAMES) * sum(EXPECTED_PER_FRAME.values()),
                            workers=WORKERS, frames_per_shard=FRAMES_PER_SHARD, budget_core_hours=CORE_HOURS,
                            environment=ctx.environment, source_parity=sources,
                            source_paths=ctx.source_paths, source_md5=ctx.source_md5,
                            own_sha256={n: hashlib.sha256((HERE / n).read_bytes()).hexdigest() for n in pinned},
                            codelay_source_sha256=q.CODELAY_SHA)))
        with (out / f'rows_shard{shard:03d}.jsonl').open('x', buffering=1) as handle:
            if shard == 0:
                write_json(out / 'FIRST_SHARD', dict(shard=shard, pid=os.getpid(), started_utc=started,
                                                    frozen_commit=commit))
            for frame in frames:
                for row in observation_rows(frame, q, ctx, variant, full, closed, generators, stop_requested):
                    handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                    counts[row['family']] += 1
        expected = {family: n * len(frames) for family, n in EXPECTED_PER_FRAME.items()}
        if counts == expected:
            status = 'complete'
        elif stop_requested():
            status = 'interrupted'
        else:
            raise ValueError(f'Incomplete shard {shard}: {dict(counts)} != {expected}')
    except Exception:
        error = traceback.format_exc()
    finally:
        receipt = dict(shard=shard, pid=os.getpid(), commit=commit, status=status,
                       frames=[frames.start, frames.stop - 1], keys_by_family=counts,
                       started_utc=started, ended_utc=utc_now(), cpu_seconds=time.process_time()-cpu_start,
                       error=error)
        write_json(out / f'shard{shard:03d}.json', receipt)
    return receipt


def archive_rows(out):
    pending_manifest = out / 'REMOTE_ROWS_MD5.txt.pending'
    with pending_manifest.open('x', buffering=1) as manifest:
        for raw in sorted(out.glob('rows_shard*.jsonl')):
            archived = raw.with_suffix('.jsonl.gz')
            temporary = archived.with_suffix('.gz.pending')
            with raw.open('rb') as src, temporary.open('xb') as dest:
                with gzip.GzipFile(filename='', mode='wb', fileobj=dest, compresslevel=6, mtime=0) as gz:
                    shutil.copyfileobj(src, gz)
            md5 = hashlib.md5()
            with temporary.open('rb') as handle:
                for block in iter(lambda: handle.read(1 << 20), b''):
                    md5.update(block)
            temporary.rename(archived)
            manifest.write(f'{md5.hexdigest()}  {archived.name}\n')
            raw.unlink()
    pending_manifest.rename(out / 'REMOTE_ROWS_MD5.txt')


def worker_loop(out, commit, channel, stop_path):
    with channel:
        try:
            initialize_worker(stop_path)
            while (assignment := channel.recv()) is not None:
                shard, frames = assignment
                channel.send((write_shard(out, shard, frames, commit), None))
        except Exception:
            channel.send((None, traceback.format_exc()))


def worker_cpu_seconds(pid, clock_ticks):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    return (int(fields[11]) + int(fields[12])) / clock_ticks


def schedule(out, commit, groups):
    # Bare processes and pipes avoid POSIX semaphores on the shared server.
    runtime = multiprocessing.get_context('spawn')
    stop_path = out / '.stop_workers'
    clock_ticks = os.sysconf('SC_CLK_TCK')
    worker_seconds = {}
    cpu_start = time.process_time()
    processes, pending, receipts, reason, failures = {}, {}, [], None, []
    try:
        remaining = iter(enumerate(groups))
        for _ in range(min(WORKERS, len(groups))):
            shard, frames = next(remaining)
            parent, child = runtime.Pipe()
            process = runtime.Process(target=worker_loop, args=(out, commit, child, stop_path))
            try:
                process.start()
            finally:
                child.close()
            processes[parent] = process
            pending[parent] = shard
            parent.send((shard, frames))
        while pending:
            finished = wait(pending, timeout=1)
            for process in processes.values():
                seconds = worker_cpu_seconds(process.pid, clock_ticks)
                if seconds is not None:
                    worker_seconds[process.pid] = seconds
            if (sum(worker_seconds.values()) + time.process_time() - cpu_start) / 3600 > CORE_HOURS:
                reason = reason or 'core_budget'
            for channel in finished:
                shard = pending.pop(channel)
                try:
                    receipt, error = channel.recv()
                except (EOFError, OSError) as exc:
                    receipt, error = None, repr(exc)
                if receipt is not None:
                    receipts.append(receipt)
                    error = receipt['error']
                if error:
                    reason = reason or f'shard_{shard:03d}_error'
                    failures.append(dict(shard=shard, traceback=error))
            if reason is not None:
                if not stop_path.exists():
                    stop_path.touch(exist_ok=False)
                continue
            for channel, (shard, frames) in zip(finished, remaining):
                channel.send((shard, frames))
                pending[channel] = shard
    except Exception:
        reason = reason or 'scheduler_error'
        failures.append(dict(stage='scheduler', traceback=traceback.format_exc()))
        stop_path.touch()
    finally:
        for channel in processes:
            try:
                channel.send(None)
            except (BrokenPipeError, OSError):
                pass  # A dead worker is already recorded at its assigned shard.
            finally:
                channel.close()
        for process in processes.values():
            process.join()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    core_hours = (usage.ru_utime + usage.ru_stime + time.process_time() - cpu_start) / 3600
    return receipts, reason, core_hours, failures


def launch(out, commit):
    if any(os.environ.get(name) != '1' for name in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('CPU-only run requires hidden CUDA and one BLAS/OpenMP thread')
    if not (HERE / 'PROTOCOL.md').read_text().startswith('# FROZEN '):
        raise ValueError('Main run requires the frozen protocol')
    load = os.getloadavg()[0]
    available = len(os.sched_getaffinity(0))
    if available - math.ceil(load) < WORKERS + 16:
        raise RuntimeError(f'24 workers would leave fewer than 16 CPUs free: CPUs={available}, load={load}')
    out.mkdir(parents=True, exist_ok=False)
    groups = [FRAMES[i:i + FRAMES_PER_SHARD] for i in range(0, len(FRAMES), FRAMES_PER_SHARD)]
    started = utc_now()
    receipts, reason, hours, failures = schedule(out, commit, groups)
    completed = sum(r['status'] == 'complete' for r in receipts)
    if reason is None:
        if hours > CORE_HOURS:
            reason = 'core_budget'
        elif completed != len(groups):
            reason = 'incomplete_shards'
    pending_status = out / 'STATUS.pending'
    line = f'DONE {completed} {hours:.6f}' if reason is None else f'STOPPED {reason} {hours:.6f}'
    pending_status.write_text(line + '\n')
    archive_started = time.process_time()
    try:
        archive_rows(out)
    except Exception:
        failures.append(dict(stage='archive', traceback=traceback.format_exc()))
        reason = 'archive_error'
    hours += (time.process_time() - archive_started) / 3600
    if reason is None and hours > CORE_HOURS:
        reason = 'core_budget'
    line = f'DONE {completed} {hours:.6f}' if reason is None else f'STOPPED {reason} {hours:.6f}'
    pending_status.write_text(line + '\n')
    total = Counter()
    for receipt in receipts:
        total.update(receipt['keys_by_family'])
    write_json(out / 'main_receipt.json',
               dict(_argv=sys.argv, _config=dict(commit=commit, workers=WORKERS, core_hour_cap=CORE_HOURS),
                    started_utc=started, ended_utc=utc_now(), completed_shards=completed, planned_shards=len(groups),
                    keys_by_family=total, core_hours=hours, reason=reason, failures=failures))
    pending_status.rename(out / 'STATUS')
    return reason is None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    if re.fullmatch('[a-f0-9]{40}', args.commit) is None:
        parser.error('Expected the full frozen Git commit')
    sys.exit(0 if launch(args.out.resolve(), args.commit) else 1)
