"""Run the frozen MIXED8 replication and score its paired raw rows on deinlab."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import signal
import sys
from time import monotonic

from qualify import ARMS, LEG2, MAIN, P1, verify_audit, verify_leg2

HERE = Path(__file__).resolve().parent
FRAMES = range(2800, 5200)
FREEZE = 'e44f050a'
CPU_SECONDS = 3 * 3600
CONTROLLER_SECONDS = 120
SHELL_RESERVE_SECONDS = 60
BOUND_FILES = (
    'PROTOCOL.md', 'qualify.py', 'verdict.py', 'run_main.py', 'launch_main.sh', 'report_main.py',
    f'../{P1.name}/run_main.py', f'../{LEG2.name}/report_main.py',
    *(f'../{LEG2.name}/out/main_20261120/{file}'
      for file in ('STATUS', 'SOURCE_SHA256.txt', 'results.json')),
    *(f'out/{file}' for file in (
        'STATUS', 'g3.json', 'identity.json', 'g5.json', 'phase1_config.json',
        'frame_audit_local.json', 'frame_audit_deinlab.json',
    )),
)


def check_sources(manifest, digest):
    fields = [line.split() for line in manifest.read_text().splitlines()]
    hashes = {name: expected for expected, name in fields}
    if len(fields) != len(BOUND_FILES) or set(hashes) != set(BOUND_FILES):
        raise ValueError('Unexpected producing source manifest inventory')
    for name, expected in hashes.items():
        if digest(HERE/name, 'sha256') != expected:
            raise ValueError(f'Producing source or receipt checksum differs: {name}')
    if not (HERE/'PROTOCOL.md').read_text().startswith('# FROZEN '):
        raise ValueError('The bound protocol is not marked FROZEN')
    return hashes


def check_qualification(read_json, digest):
    previous = verify_leg2()['_config']
    directory = HERE/'out'
    qualified = read_json(directory/'phase1_config.json')['_config']
    identity = read_json(directory/'identity.json')
    audit = verify_audit(directory/'g3.json', previous['source']['rng'])
    if ((directory/'STATUS').read_text().strip() != 'DONE'
            or read_json(directory/'g5.json')['status'] != 'PASS'
            or identity['status'] != 'PASS'
            or identity['producing_revision'] != previous['producing_revision']
            or audit['fresh'] != [FRAMES.start, FRAMES.stop - 1]
            or qualified['fresh'] != audit['fresh']
            or (qualified['scenario'], qualified['rho'], qualified['main_snr_db']) != ('MIXED8', .5, 7)
            or tuple(qualified['arms']) != ARMS
            or qualified['source'] != previous['source']
            or qualified['audit_sha256'] != digest(directory/'g3.json', 'sha256')
            or qualified['phase1_code_sha256']['qualify.py'] != digest(HERE/'qualify.py', 'sha256')):
        raise ValueError('Phase 1 qualification differs from the frozen replication')
    return qualified


def shard(index, count, cpu, cpu_limit, out, qualified):
    os.sched_setaffinity(0, {cpu})

    def budget_reached(_signal, _frame):
        raise TimeoutError(f'Worker {index:02d} reached its CPU allocation')

    signal.signal(signal.SIGXCPU, budget_reached)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit - 1, cpu_limit))

    sys.path.insert(0, str(LEG2))
    import mixed_paired

    if Path(mixed_paired.__file__).resolve() != LEG2/'mixed_paired.py':
        raise ValueError('Wrong MIXED8 receiver module imported')
    loaded, source = mixed_paired.context()
    if source != qualified['source']:
        raise ValueError('Receiver bindings differ from Phase 1')
    frames = FRAMES[index::count]
    path = out/f'rows-{index:02d}.jsonl'
    with path.open('x', buffering=1) as handle:
        for frame in frames:
            try:
                row, _ = mixed_paired.one(loaded, frame, 7, arms=ARMS)
                handle.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
            except Exception as exc:
                raise RuntimeError(f'Failed MIXED8 frame {frame}') from exc
    print(f'Completed shard {index:02d} with {len(frames)} frames', flush=True)
    return dict(shard=index, cpu=cpu, path=str(path), frames=len(frames))


def main():
    started = monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-revision', required=True)
    parser.add_argument('--producing-revision', required=True)
    args = parser.parse_args()
    if (not all(re.fullmatch('[0-9a-f]{40}', rev) for rev in (args.freeze_revision, args.producing_revision))
            or not args.freeze_revision.startswith(FREEZE)):
        parser.error('Expected the full frozen and producing revisions')
    out = args.out.resolve()
    if out != HERE/'out/main_20261120':
        parser.error('Expected the approved MIXED8 main output directory')

    # Share the P1 launcher's file helpers and physical-core preflight.
    # Use a private file import because this entry point has the same filename.
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('gamma0_p1_launch_helpers', P1/'run_main.py')
    common = module_from_spec(spec)
    spec.loader.exec_module(common)
    if (any(os.environ.get(key) != '1' for key in common.THREAD_ENV)
            or os.environ.get('CUDA_VISIBLE_DEVICES') != ''):
        raise ValueError('Expected CPU-only single-thread execution')
    checks = check_sources(out/'SOURCE_SHA256.txt', common.digest)
    qualified = check_qualification(common.read_json, common.digest)
    idle = common.idle_cores()
    # Reserve process slots for the controller, launcher and wall timer.
    workers = min(21, len(idle) - 17)
    worker_cpus = idle[:workers]
    os.sched_setaffinity(0, {idle[workers]})
    limit = (CPU_SECONDS - CONTROLLER_SECONDS - SHELL_RESERVE_SECONDS) // workers
    config = dict(freeze_revision=args.freeze_revision, producing_revision=args.producing_revision,
                  source_sha256=checks, source=qualified['source'], frames_inclusive=qualified['fresh'],
                  scenario='MIXED8', rho=.5, snr_db=7, frames=len(FRAMES), arms=qualified['arms'],
                  idle_physical_cores_at_kickoff=len(idle), load_average=list(os.getloadavg()),
                  controller_cpu=idle[workers], worker_cpus=worker_cpus, workers=workers,
                  per_worker_cpu_cap_seconds=limit, cpu_cap_core_hours=3, wall_cap_seconds=1800,
                  historical_results=str(MAIN/'results.json'),
                  leg2_producing_revision=qualified['leg2_producing_revision'])
    bound = dict(_argv=sys.argv, _config=config)
    common.write_json(out/'run_config.json', bound)
    print(f'Bound {args.producing_revision}; {len(idle)} idle physical cores; {workers} workers', flush=True)

    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('fork')) as pool:
        jobs = [pool.submit(shard, i, workers, cpu, limit, out, qualified) for i, cpu in enumerate(worker_cpus)]
        resource.setrlimit(resource.RLIMIT_CPU, (CONTROLLER_SECONDS, CONTROLLER_SECONDS))
        shards = sorted((job.result() for job in as_completed(jobs)), key=lambda part: part['shard'])
    if sum(part['frames'] for part in shards) != len(FRAMES):
        raise ValueError('Incomplete frame panel')
    rows = [Path(part['path']) for part in shards]
    raw_manifest = out/'REMOTE_ROWS_MD5.txt'
    with raw_manifest.open('x') as handle:
        for path in rows:
            print(common.digest(path, 'md5'), path, file=handle)

    print('Scoring completed MIXED8 rows with the frozen verdict', flush=True)
    import verdict
    from report_main import render
    if (Path(verdict.__file__).resolve() != HERE/'verdict.py'
            or Path(render.__code__.co_filename).resolve() != HERE/'report_main.py'):
        raise ValueError('Wrong verdict or reporting module imported')
    result = {**bound, **verdict.analyze(verdict.read_rows(rows), FRAMES)}
    common.write_json(out/'results.json', result)
    usage = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    core_hours = sum(item.ru_utime + item.ru_stime for item in usage) / 3600
    receipt = dict(freeze_revision=args.freeze_revision, producing_revision=args.producing_revision,
                   core_hours=core_hours, wall_seconds=monotonic() - started, workers=workers,
                   shards=shards, source_sha256=checks, manifest_md5=common.digest(raw_manifest, 'md5'))
    receipt['idle_physical_cores_left'] = len(idle) - workers - 1
    with (out/'RESULTS.md').open('x') as handle:
        handle.write(render(result, receipt))
    common.write_json(out/'receipt.json', receipt)
    print(f'Completed {len(FRAMES)} frames in {receipt["wall_seconds"]:.2f}s, {core_hours:.6f} core-hours', flush=True)


if __name__ == '__main__':
    main()
