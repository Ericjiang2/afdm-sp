"""Bind the frozen inputs and supervise one Phase 2 execution on deinlab."""

import argparse
from hashlib import md5, sha256
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'out/main_20261119'
PINS_FILE = HERE / 'main_pins.json'
PINS_SHA256 = '92e606f64f677c5f1d2c53b88ebc3b9d4189f3428cefacd5255fb5a97edefee4'
FREEZE = 'd292217e6ae2e27f9901fdbab0f24d9bac797959'
LAUNCH_SOURCES = ('launch_main.sh', 'main_pins.json', 'report_main.py', 'run_main.py', 'run_main_rows.py')
SUPERVISOR = ROOT / 'experiments/unified_cov_prospective_20261119/budget_main.py'
SCHEDULE = HERE / 'out/phase1b_20261119/main_schedule.json'
THREADS = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
           'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
WORKERS = 27


def sha_file(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(path, expected):
    actual = sha_file(path)
    if actual != expected:
        raise ValueError(f'SHA-256 mismatch for {path}: {actual} != {expected}')


def inputs(args):
    if (args.freeze_commit != FREEZE or not re.fullmatch(r'[0-9a-f]{40}', args.launch_commit)
            or not re.fullmatch(r'[0-9a-f]{64}', args.launch_manifest_sha256)):
        raise ValueError('Expected pinned freeze and full launch commit and manifest digest')
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Phase 2 requires the CPU-only Linux runner')
    if any(os.environ.get(name) != '1' for name in THREADS):
        raise ValueError('Phase 2 requires one compute thread per process')
    verify(PINS_FILE, PINS_SHA256)
    pins = json.loads(PINS_FILE.read_text())
    if pins['freeze_commit'] != FREEZE:
        raise ValueError('Freeze manifest does not name the registered freeze')
    for name, expected in pins['sha256'].items():
        verify(ROOT / name, expected)

    verify(args.launch_manifest, args.launch_manifest_sha256)
    launch = json.loads(args.launch_manifest.read_text())
    if (launch['launch_commit'] != args.launch_commit or launch['freeze_commit'] != FREEZE
            or set(launch['sha256']) != set(LAUNCH_SOURCES)):
        raise ValueError('Launch manifest identity or source list differs')
    for name, expected in launch['sha256'].items():
        verify(HERE / name, expected)

    schedule = json.loads(SCHEDULE.read_text())
    if (schedule['s_segments'], schedule['s_frames'], schedule['s_keys'], schedule['x_segment'],
        schedule['x_frames'], schedule['x_snr_db'], schedule['x_rho'], schedule['cluster_unit']) != (
            [[5800, 5999], [6200, 6399]], 400, 4800, [1600, 2199], 600, 7, .5, 'physical frame'):
        raise ValueError('Pinned schedule violates the Phase 2 protocol')
    return pins, launch, schedule


def load_supervisor():
    # The imported frozen supervisor accounts for process-group user/system
    # CPU and reserves time to terminate workers before the hard ceiling.
    spec = importlib.util.spec_from_file_location('frozen_cpu_supervisor', SUPERVISOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if (module.CORE_HOURS, module.CPU_LIMIT, module.PROCESS_LIMIT) != (25, 90000, 32):
        raise ValueError('CPU supervisor limits violate the Phase 2 protocol')
    return module


def publish_raw_manifest(budget):
    raw = {}
    for name in ('s_rows.jsonl', 'x_rows.jsonl'):
        digest = md5()
        with (OUT / name).open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(block)
        raw[name] = digest.hexdigest()
    budget.atomic(OUT / 'REMOTE_ROWS_MD5.txt',
                  ''.join(f'{digest}  {name}\n' for name, digest in sorted(raw.items())))
    return raw


def add_operational_receipt(budget, accounting, raw):
    result_path = OUT / 'results.json'
    result = json.loads(result_path.read_text())
    result.update(core_hours_used=accounting['core_hours_used'], raw_rows_md5=raw)
    budget.atomic(result_path, budget.json_text(result))
    report = OUT / 'RESULTS.md'
    text = report.read_text()
    heading = '## Observation\n\n'
    if text.count(heading) != 1:
        raise ValueError('Expected exactly one Observation section in retrieved report')
    receipt = (f'Main chain used **{accounting["core_hours_used"]:.3f} core-hours**. '
               f'Raw rows remain on deinlab in `{OUT}`. '
               'Their hashes are in [REMOTE_ROWS_MD5.txt](REMOTE_ROWS_MD5.txt).\n\n')
    budget.atomic(report, text.replace(heading, heading + receipt, 1))


def run(args):
    started, cpu_started = time.monotonic(), time.process_time()
    OUT.mkdir(exist_ok=False)
    status_path = OUT / 'STATUS'
    notes = []
    reason = None
    raw = None
    budget = None
    with (OUT / 'run.log').open('x', buffering=1) as log:
        try:
            pins, launch, schedule = inputs(args)
            budget = load_supervisor()
            cfg = dict(_argv=sys.argv, _config=dict(
                model=args.model, freeze_commit=FREEZE, launch_commit=args.launch_commit,
                freeze_record=pins['freeze_record'], frozen_manifest_sha256=PINS_SHA256,
                frozen_source_sha256=pins['sha256'], canonical_to_loaded_sources=pins['canonical_to_loaded_sources'],
                launch_manifest_sha256=args.launch_manifest_sha256, launch_source_sha256=launch['sha256'],
                main_schedule=schedule, workers_per_leg=WORKERS, threads_per_process=1, cpu_only=True,
                core_hour_cap=budget.CORE_HOURS, process_limit=budget.PROCESS_LIMIT,
                term_reserve_cpu_seconds=budget.STOP_RESERVE,
                raw_rows_directory=str(OUT), python=sys.version, platform=platform.platform()))
            budget.atomic(OUT / 'config.json', budget.json_text(cfg))
            budget.atomic(OUT / 'PRODUCING_COMMIT.txt', f'{FREEZE}\nLaunch commit {args.launch_commit}\n')
            command = [sys.executable, '-B', '-u']
            for leg in ('s', 'x'):
                budget.stage(leg, [*command, str(HERE / 'run_main_rows.py'), '--leg', leg,
                                   '--out', str(OUT), '--workers', str(WORKERS)],
                             log, sum(stage['cpu_seconds'] for stage in notes), notes, cpu_started)
            budget.stage('aggregate', [*command, str(HERE / 'report_main.py'), '--out', str(OUT)],
                         log, sum(stage['cpu_seconds'] for stage in notes), notes, cpu_started)
            raw = publish_raw_manifest(budget)
        except Exception as exc:
            reason = str(exc)
            print(f'STOPPED {type(exc).__name__}: {reason}', file=log, flush=True)

        charged = sum(stage['cpu_seconds'] for stage in notes) + time.process_time() - cpu_started
        accounting = dict(core_hours_used=charged / 3600, cpu_seconds=charged,
                          core_hour_cap=25, wall_seconds=time.monotonic() - started,
                          stages=notes, stop_reason=reason)
        if reason is None:
            if charged >= budget.CPU_LIMIT:
                reason = '25-core-hour limit reached'
            else:
                try:
                    add_operational_receipt(budget, accounting, raw)
                except Exception as exc:
                    reason = f'{type(exc).__name__}: {exc}'
        status = 'DONE' if reason is None else 'STOPPED'
        accounting.update(status=status, stop_reason=reason)
        (OUT / 'budget.json').write_text(json.dumps(accounting, sort_keys=True, indent=2, allow_nan=False) + '\n')
        status_path.write_text(status + '\n')
        print(f'{status} {accounting["core_hours_used"]:.6f} core-hours'
              + (f' ({reason})' if reason else ''), file=log, flush=True)
    return int(reason is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--launch-commit', required=True)
    parser.add_argument('--launch-manifest', type=Path, required=True)
    parser.add_argument('--launch-manifest-sha256', required=True)
    parser.add_argument('--model', choices=['gpt-6.2-sol'], required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    if args.verify_only:
        pins, launch, _ = inputs(args)
        load_supervisor()
        print(f'Verified {len(pins["sha256"])} frozen files and {len(launch["sha256"])} launch files.')
        return 0
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
