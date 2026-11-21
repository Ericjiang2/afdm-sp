"""Verify and execute the frozen low-pilot edit-budget experiment on deinlab."""

import argparse
from contextlib import contextmanager
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'out/main_20261119'
FREEZE_COMMIT = 'cf582ab743216a79ad16dfc0c56fd66be9dba240'
FRAMES = range(6400, 6800)
SCENARIOS = ('U', 'G')
RHOS = (150, 200, 300)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 1000)
ARMS = ('F0', 'CD2', 'CD4', 'CD6', 'A2-2', 'A2-6')
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
KEY_COUNT = len(FRAMES) * len(SCENARIOS) * len(RHOS) * len(SNRS)
WORKERS = 14
PROCESS_CPU_SECONDS = 1438
CAP_CPU_SECONDS = 6 * 3600
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')
GLUE = {'launch_main.sh', 'run_main.py', 'report_main.py', 'phase2_pins.json'}
GATE = HERE / 'out/phase1b/cap_gate.json'
PIN_FILE = HERE / 'phase2_pins.json'

# The parent and its 14 subprocesses have separate Linux hard CPU limits.
# The launch shell uses the remaining headroom and starts no idle worker pool.
assert (WORKERS + 1) * PROCESS_CPU_SECONDS < CAP_CPU_SECONDS


def digest(path, algorithm='sha256'):
    checksum = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def verify(path, expected):
    actual = digest(path)
    if actual != expected:
        raise RuntimeError(f'Hash mismatch for {path}: expected {expected}, got {actual}')


def verify_files(args):
    if (sys.platform != 'linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != ''
            or any(os.environ.get(key) != '1' for key in THREADS)):
        raise RuntimeError('The frozen run requires Linux CPU and one numerical thread')
    if args.freeze_commit != FREEZE_COMMIT:
        raise ValueError('Launch freeze commit differs from the approved freeze')
    if (not re.fullmatch(r'[0-9a-f]{40}', args.launch_commit)
            or args.launch_commit == FREEZE_COMMIT):
        raise ValueError('Expected the separate committed launch glue revision')
    verify(args.manifest, args.manifest_sha256)
    manifest = json.loads(args.manifest.read_text())
    if manifest['launch_commit'] != args.launch_commit or set(manifest['files']) != GLUE:
        raise RuntimeError('Launch manifest has a different commit or file inventory')
    for name, expected in manifest['files'].items():
        verify(HERE / name, expected)

    pinned = json.loads(PIN_FILE.read_text())
    if pinned['freeze_commit'] != FREEZE_COMMIT:
        raise RuntimeError('Source pins belong to another freeze')
    for name, expected in pinned['files'].items():
        verify(ROOT / name, expected)

    gate = json.loads(GATE.read_text())
    phase_cases = gate['cases']
    if (not gate['passed'] or gate['gate_keys'] != len(phase_cases) or len(phase_cases) != 14
            or gate['continuation_detector_calls'] != 0 or gate['continuation_decoder_calls'] != 0
            or any(case['key'][-1] not in range(5400, 5800) for case in phase_cases)):
        raise RuntimeError('Phase 1b cap-only gate receipt did not qualify these arms')
    for host in ('local', 'remote'):
        audit = json.loads((HERE / f'out/phase1/audit_{host}.json').read_text())
        if (
            audit['status'] != 'PASS' or audit['scope'] != {'local': 'local', 'remote': 'deinlab'}[host]
            or audit['selected'] != [FRAMES.start, FRAMES.stop - 1] or audit['findings']
        ):
            raise RuntimeError(f'The registered frame block did not pass the {host} audit')
    cost = json.loads((HERE / 'out/phase1b/cost.json').read_text())
    if cost['cap_result'] != 'PASS' or cost['keys'] != KEY_COUNT or cost['projected_core_hours'] > 6:
        raise RuntimeError('Frozen cost receipt does not admit the full grid')
    return pinned, manifest, gate


def verified_receiver(pinned, gate):
    import budget_receiver as receiver

    if Path(receiver.__file__).resolve() != HERE / 'budget_receiver.py':
        raise RuntimeError('Imported the wrong budget receiver')
    ctx, kernels, sources = receiver.context()
    if sources != gate['sources'] or ('F0', *receiver.ARMS) != ARMS:
        raise RuntimeError('The loaded receiver differs from the cap-only gate')
    for module, rel in ctx.source_paths.items():
        expected = pinned['files'].get(rel)
        if ctx.source_sha256[module] != expected:
            raise RuntimeError(f'Unpinned or changed imported receiver source {module}: {rel}')
    # These modules load after the frozen context takes its source inventory.
    loaded = [receiver.stage3, receiver.stage3.e1, receiver.sweep, sys.modules['geometry_validation_variant']]
    for module in loaded:
        source = Path(module.__file__).resolve()
        verify(source, pinned['files'][str(source.relative_to(ROOT))])
    previous = ROOT / 'experiments/rho_sweep_20261119/out/main_20261119/config.json'
    environment = json.loads(previous.read_text())['_config']['qualified_sources']['environment']
    env_fields = ('python', 'machine', 'numpy', 'scipy', 'torch', 'torch_cuda_available',
                  'torch_num_threads', 'torch_num_interop_threads')
    if any(ctx.environment[key] != environment[key] for key in env_fields):
        raise RuntimeError('The numerical environment differs from the qualified archive')
    if ctx.header['checkpoint_sha256'] != pinned['checkpoint_sha256']:
        raise RuntimeError('Frozen checkpoint identity differs')
    return receiver, ctx, kernels


@contextmanager
def publish(path):
    part = path.with_name(path.name + '.part')
    with part.open('x', encoding='utf-8', buffering=1) as handle:
        yield handle
        handle.flush()
        os.fsync(handle.fileno())
    os.link(part, path)
    part.unlink()


def write_json(path, doc):
    with publish(path) as handle:
        json.dump(doc, handle, indent=2, allow_nan=False)
        handle.write('\n')


def key_of(row):
    return tuple(row[field] for field in KEY_FIELDS)


def shard_path(shard):
    return OUT / f'rows_shard{shard:03d}.jsonl'


def shard_frames(shard):
    return FRAMES[shard::WORKERS]


def shard_keys(shard):
    return ((scenario, rho, snr, frame) for frame in shard_frames(shard)
            for scenario, rho, snr in product(SCENARIOS, RHOS, SNRS))


def worker(shard, pinned, gate, snapshot):
    receiver, ctx, kernels = verified_receiver(pinned, gate)
    path = shard_path(shard)
    with publish(path) as handle:
        for frame in shard_frames(shard):
            for scenario, rho in product(SCENARIOS, RHOS):
                base = receiver.stage3.inputs(ctx, frame, scenario, rho)
                for snr in SNRS:
                    key = (scenario, rho, snr, frame)
                    try:
                        row = receiver.run_key(ctx, kernels, base, key)
                        if key_of(row) != key:
                            raise RuntimeError('Receiver returned a different key')
                        row['snapshot_sha256'] = snapshot
                        print(json.dumps(row, separators=(',', ':'), allow_nan=False), file=handle)
                    except Exception as error:
                        raise RuntimeError(f'Shard {shard:03d} failed on {key}') from error
    print(f'Completed {path.name}', flush=True)


def run_workers():
    running = {}
    try:
        for shard in range(WORKERS):
            command = [sys.executable, '-B', '-u', str(Path(__file__).resolve()),
                       *sys.argv[1:], '--worker', str(shard)]
            child = subprocess.Popen(command)
            running[child.pid] = child
        while running:
            pid, status = os.wait()
            child = running.pop(pid)
            child.returncode = os.waitstatus_to_exitcode(status)
            if child.returncode:
                raise RuntimeError(f'Worker {pid} exited {child.returncode}; budget guard or worker failure')
    finally:
        for child in running.values():
            child.terminate()
        for child in running.values():
            child.wait()


def read_shards(snapshot):
    rows, inputs = [], {}
    paths = [shard_path(shard) for shard in range(WORKERS)]
    if set(paths) != set(OUT.glob('rows_shard*.jsonl')) or list(OUT.glob('rows_shard*.part')):
        raise RuntimeError('Shard inventory differs from the complete run')
    md5 = {}
    for shard, path in enumerate(paths):
        checksum = hashlib.md5()
        with path.open('rb') as handle:
            for expected, line in zip(shard_keys(shard), handle, strict=True):
                checksum.update(line)
                row = json.loads(line)
                if (key_of(row) != expected or row['snapshot_sha256'] != snapshot
                        or tuple(row['arms']) != ARMS or tuple(row['budget_mechanism']) != ARMS
                        or row['triggered'] != bool(row['syndrome'])):
                    raise RuntimeError(f'Row or snapshot inventory mismatch at {expected}')
                common = tuple(row['inputs'][key] for key in ('info', 'coded', 'noise'))
                if inputs.setdefault(expected[-1], common) != common:
                    raise RuntimeError(f'Common-randomness pairing failed at {expected}')
                if not row['triggered'] and any(row['arms'][a] != row['arms']['F0'] for a in ARMS[1:]):
                    raise RuntimeError(f'An arm changed the F0 bypass at {expected}')
                rows.append(row)
        md5[path.name] = checksum.hexdigest()
    if len(rows) != KEY_COUNT:
        raise RuntimeError('Expected the full frozen grid')
    with publish(OUT / 'REMOTE_ROWS_MD5.txt') as handle:
        for name, checksum in md5.items():
            handle.write(f'{checksum}  {name}\n')
    return rows


def cpu_seconds():
    self_usage = resource.getrusage(resource.RUSAGE_SELF)
    workers = resource.getrusage(resource.RUSAGE_CHILDREN)
    return self_usage.ru_utime + self_usage.ru_stime + workers.ru_utime + workers.ru_stime


def interrupted(signum, _frame):
    raise TimeoutError(f'Coordinator interrupted by signal {signum}')


def coordinate(args, pinned, manifest, gate):
    _, ctx, _ = verified_receiver(pinned, gate)
    # The frozen receiver prepends the rho-sweep directory while importing.
    # Restore this experiment's precedence before resolving its report module.
    sys.path.insert(0, str(HERE))
    import report_main

    modules = (
        (report_main, HERE / 'report_main.py'),
        (sys.modules['primary'], HERE / 'primary.py'),
        (report_main.sweep, HERE.parent / 'rho_sweep_20261119/analysis.py'),
        (report_main.sweep.p1_agg, HERE.parent / 'tcom_reference_frame_20261015/p1_agg.py'),
        (sys.modules['sampling'], HERE.parent / 'tf_covariance_audit_20261018/sampling.py'),
    )
    if any(Path(module.__file__).resolve() != path for module, path in modules):
        raise RuntimeError('Imported reporting, verdict or crossing code differs from the verified paths')
    if (report_main.ARMS, report_main.SCENARIOS, report_main.RHOS, report_main.SNRS) != (
            ARMS, SCENARIOS, RHOS, SNRS):
        raise RuntimeError('Report grid differs from the frozen launch grid')
    if args.verify_only:
        print('Frozen files, launch glue, receiver bindings, grid, audits and cap gate verified.')
        return
    config = dict(
        freeze_commit=FREEZE_COMMIT, launch_commit=args.launch_commit, model='gpt-6.2-sol',
        output=str(OUT), frames_inclusive=[FRAMES.start, FRAMES.stop - 1], scenarios=SCENARIOS,
        rhos=RHOS, snrs=SNRS, arms=ARMS, keys=KEY_COUNT, workers=WORKERS,
        hard_cpu_seconds_per_python_process=PROCESS_CPU_SECONDS,
        core_hour_cap=CAP_CPU_SECONDS / 3600, threads={key: os.environ[key] for key in THREADS},
        cuda_visible_devices=os.environ['CUDA_VISIBLE_DEVICES'], launch_hashes=manifest['files'],
        frozen_hashes=pinned['files'], environment=ctx.environment, receiver_header=ctx.header,
        loaded_source_paths=ctx.source_paths,
    )
    snapshot = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    config['snapshot_sha256'] = snapshot
    provenance = dict(_argv=sys.argv, _config=config)
    write_json(OUT / 'config.json', provenance)
    print(f'Starting {WORKERS} workers on {KEY_COUNT} frozen keys.', flush=True)
    run_workers()
    rows = read_shards(snapshot)
    results = report_main.aggregate(rows, FRAMES)
    cpu = cpu_seconds()
    if cpu >= CAP_CPU_SECONDS:
        raise TimeoutError('Six-core-hour CPU cap reached')
    results['execution'] = dict(cpu_core_hours=cpu / 3600, freeze_commit=FREEZE_COMMIT,
                                launch_commit=args.launch_commit, rows_manifest='REMOTE_ROWS_MD5.txt',
                                raw_directory=str(OUT))
    results.update(provenance)
    markdown = report_main.render(results)
    write_json(OUT / 'results.json', results)
    with publish(OUT / 'RESULTS.md') as handle:
        handle.write(markdown if markdown.endswith('\n') else markdown + '\n')
    print(f'{KEY_COUNT} validated rows and frozen aggregation completed.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--launch-commit', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--worker', type=int)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (PROCESS_CPU_SECONDS, PROCESS_CPU_SECONDS))
    if args.worker is not None:
        if not 0 <= args.worker < WORKERS or args.verify_only:
            raise ValueError('Invalid worker index or mode')
        pinned, _, gate = verify_files(args)
        config = json.loads((OUT / 'config.json').read_text())['_config']
        if config['launch_commit'] != args.launch_commit or config['freeze_commit'] != FREEZE_COMMIT:
            raise RuntimeError('Worker was not started by the qualified controller')
        worker(args.worker, pinned, gate, config['snapshot_sha256'])
        return

    signal.signal(signal.SIGTERM, interrupted)
    started = time.monotonic()
    try:
        coordinate(args, *verify_files(args))
    finally:
        if not args.verify_only:
            with publish(OUT / 'cpu.txt') as handle:
                handle.write(f'{cpu_seconds():.6f} CPU seconds\n')
                handle.write(f'{time.monotonic() - started:.6f} wall seconds\n')


if __name__ == '__main__':
    main()
