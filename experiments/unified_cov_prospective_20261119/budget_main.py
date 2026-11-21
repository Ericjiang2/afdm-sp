"""Supervise the Phase 2 receiver and aggregation under one CPU budget."""

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import shlex
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CORE_HOURS = 25
CPU_LIMIT = CORE_HOURS * 3600
PROCESS_LIMIT = 32
CHECK_SECONDS = 1.
TERM_SECONDS = 2.
# Each admitted process has one compute thread. Reserve time for monitoring
# and termination so a sample at the threshold still leaves CPU headroom.
STOP_RESERVE = PROCESS_LIMIT * (CHECK_SECONDS + TERM_SECONDS + 2.)


class Stopped(RuntimeError):
    pass


def atomic(path, data):
    staging = path.with_suffix(path.suffix + '.tmp')
    with staging.open('w') as handle:
        handle.write(data)
    staging.replace(path)


def json_text(data):
    return json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n'


def child_cpu():
    r = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime + r.ru_stime


def process_group_cpu(group):
    # Keep reaped children in the total via each live parent's cutime/cstime.
    # Scan parents first, so a concurrent reap can temporarily undercount
    # until the next sample, without counting the same CPU twice.
    ticks, count = 0, 0
    for pid in sorted(int(p.name) for p in Path('/proc').iterdir() if p.name.isascii() and p.name.isdecimal()):
        try:
            stat = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if int(stat[2]) == group:
            ticks += sum(map(int, stat[11:15]))
            count += 1
    return ticks / os.sysconf('SC_CLK_TCK'), count


def finish_group(child):
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + TERM_SECONDS
    while time.monotonic() < deadline:
        child.poll()
        if process_group_cpu(child.pid)[1] == 0:
            break
        time.sleep(.1)
    else:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    child.wait()


def stage(name, cmd, log, charged, notes, supervisor_started):
    log.write(f'\n[{name}] {shlex.join(cmd)}\n')
    log.flush()
    start_wall, start_cpu = time.monotonic(), child_cpu()
    child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    peak_cpu, peak_count = 0., 0
    try:
        while child.poll() is None:
            live_cpu, count = process_group_cpu(child.pid)
            peak_cpu = max(peak_cpu, live_cpu)
            peak_count = max(peak_count, count + 1)  # supervisor is outside the group
            if peak_count > PROCESS_LIMIT:
                raise Stopped(f'{name}: observed {peak_count} processes above {PROCESS_LIMIT}')
            if charged + peak_cpu + time.process_time() - supervisor_started >= CPU_LIMIT - STOP_RESERVE:
                raise Stopped(f'{name}: 25-core-hour limit reached within the termination reserve')
            time.sleep(CHECK_SECONDS)
        if child.returncode:
            raise Stopped(f'{name}: exited {child.returncode}; see run.log')
    except BaseException:
        live_cpu, count = process_group_cpu(child.pid)
        peak_cpu = max(peak_cpu, live_cpu)
        if count:
            finish_group(child)
        raise
    finally:
        reaped = child_cpu() - start_cpu
        notes.append(dict(stage=name, exit_code=child.returncode,
                          cpu_seconds=max(reaped, peak_cpu),
                          os_reaped_cpu_seconds=reaped, sampled_peak_cpu_seconds=peak_cpu,
                          wall_seconds=time.monotonic() - start_wall,
                          peak_processes=peak_count))


def add_cost(out, used):
    result_path = out/'results.json'
    result = json.loads(result_path.read_text())
    result['core_hours_used'] = used
    atomic(result_path, json_text(result))
    report = out/'RESULTS.md'
    atomic(report, report.read_text().rstrip() + f'\n\n## CPU accounting\n\nMain chain used **{used:.3f} core-hours**.\n')


def execute(args):
    out = args.out.resolve()
    expected = 'phase2_old_pilot' if args.pilot else 'main_20261119'
    if out != HERE/'out'/expected:
        raise ValueError(f'Expected output directory {HERE / "out" / expected}')
    if platform.system() != 'Linux':
        raise ValueError('Run the CPU supervisor on deinlab Linux')
    prior, history = 0., []
    status = out/'STATUS'
    budget = out/'budget.json'
    if args.resume:
        if not status.read_text().startswith('STOPPED:'):
            raise ValueError('Resume requires an explicitly stopped attempt')
        before = json.loads(budget.read_text())
        prior = before['charged_cpu_seconds']
        history = before['attempts']
        attempt = len(history)
        status.rename(out/f'STATUS.attempt{attempt:02d}')
        for name in ('results.json', 'RESULTS.md'):
            report = out/name
            if report.exists():
                report.rename(report.with_name(f'{report.stem}.attempt{attempt:02d}{report.suffix}'))
    else:
        out.mkdir(exist_ok=False)

    notes = []
    reason = None
    started, cpu_started = time.monotonic(), time.process_time()
    generic = ['--out', str(out), '--producing-commit', args.producing_commit]
    receiver = [sys.executable, '-B', '-u', str(HERE/'run_main.py'), *generic,
                '--manifest', str(args.manifest.resolve()), '--workers', str(args.workers)]
    if args.pilot:
        receiver.append('--pilot')
    if args.resume:
        receiver.append('--resume')
    try:
        with (out/'run.log').open('a', buffering=1) as log:
            stage('receiver', receiver, log, prior, notes, cpu_started)
            if not args.pilot:
                original_commit = (out/'PRODUCING_COMMIT.txt').read_text().strip()
                aggregate = [sys.executable, '-B', '-u', str(HERE/'aggregate_main.py'),
                             '--out', str(out), '--producing-commit', original_commit]
                stage('aggregation', aggregate, log, prior + notes[0]['cpu_seconds'],
                      notes, cpu_started)
    except Exception as exc:
        reason = str(exc) or type(exc).__name__

    charged = prior + sum(n['cpu_seconds'] for n in notes) + time.process_time() - cpu_started
    used = charged / 3600
    if charged > CPU_LIMIT and reason is None:
        reason = 'charged CPU usage exceeded the cap'
    if not args.pilot and reason is None:
        try:
            add_cost(out, used)
        except (OSError, ValueError, TypeError) as exc:
            reason = f'budget report: {exc}'
    history.append(dict(_argv=sys.argv, producing_commit=args.producing_commit,
                        stages=notes, wall_seconds=time.monotonic()-started, reason=reason))
    atomic(budget, json_text(dict(core_hour_cap=CORE_HOURS, core_hours_used=used,
                                 charged_cpu_seconds=charged, termination_reserve_cpu_seconds=STOP_RESERVE,
                                 accounting='OS child rusage, bounded by sampled group CPU when higher, plus supervisor CPU',
                                 attempts=history)))
    atomic(status, 'DONE\n' if reason is None else f'STOPPED: {reason}\n')
    return 0 if reason is None else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--producing-commit', required=True)
    p.add_argument('--workers', type=int, default=28, choices=range(1, 29))
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--resume', action='store_true')
    raise SystemExit(execute(p.parse_args()))
