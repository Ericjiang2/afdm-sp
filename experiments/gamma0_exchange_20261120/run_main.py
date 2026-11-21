"""Execute the frozen Gamma=0 panel on deinlab and score the raw rows."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import signal
import sys
from time import monotonic, sleep


HERE = Path(__file__).resolve().parent
FREEZE = '1266052e'
FRAMES = range(9400, 9800)
KEYS = 13_600
CPU_SECONDS = 6 * 3600
CONTROLLER_SECONDS = 120
SHELL_RESERVE_SECONDS = 60
THREAD_ENV = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def digest(path, algorithm):
    # deinlab's AFDM environment uses Python 3.10.
    value = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, payload):
    with path.open('x') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')


def source_checks(manifest):
    names = {
        'PROTOCOL.md', 'paired.py', 'verdict.py', 'run_main.py', 'launch_main.sh', 'report_main.py',
        'out/anchor_calibration.json', 'out/g3.json', 'out/phase1_config.json', 'out/phase1_done.json',
        '../tcom_reference_frame_20261015/p1_agg.py',
    }
    pairs = [line.split() for line in manifest.read_text().splitlines()]
    expected = {name: hash_value for hash_value, name in pairs}
    if len(pairs) != len(names) or set(expected) != names:
        raise ValueError('Producing source manifest has the wrong inventory')
    for path, hash_value in expected.items():
        if digest(HERE/path, 'sha256') != hash_value:
            raise ValueError(f'Producing source checksum differs: {path}')
    if not (HERE/'PROTOCOL.md').read_text().splitlines()[0].startswith('# FROZEN '):
        raise ValueError('The bound protocol is not marked FROZEN')
    return expected


def cpu_snapshot():
    result = {}
    for line in Path('/proc/stat').read_text().splitlines():
        name, *values = line.split()
        if name.startswith('cpu') and name[3:].isdigit():
            ticks = list(map(int, values[:8]))
            result[int(name[3:])] = sum(ticks) - ticks[3] - ticks[4]
    return result


def idle_cores():
    first = cpu_snapshot()
    sleep(1.)
    second = cpu_snapshot()
    allowed = os.sched_getaffinity(0)
    groups = {}
    for cpu in sorted(allowed):
        topology = Path(f'/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list')
        groups.setdefault(topology.read_text().strip(), []).append(cpu)
    idle = [members[0] for members in groups.values()
            if all(second[cpu] == first[cpu] for cpu in members)]
    if len(idle) < 18:
        raise RuntimeError(f'Only {len(idle)} physical cores available before launch')
    return idle


def check_phase1(stage, provenance, qualified):
    original = qualified['source']
    for field in ('bound_files', 'stage3_checks'):
        if provenance[field] != original[field]:
            raise ValueError(f'Frozen dependency identity changed since Phase 1: {field}')
    for field in ('p1_md5', 'p1_paths'):
        if any(original[field].get(name) != value for name, value in provenance[field].items()):
            raise ValueError(f'Frozen P1 import changed since Phase 1: {field}')
    cells = [list(cell) for cell in stage.CELLS]
    grid = {str(rho): list(snrs) for rho, snrs in stage.GRID.items()}
    if (cells, grid) != (qualified['cells'], qualified['grid']):
        raise ValueError('Actual Stage 3 grid differs from the qualified grid')


def shard(index, count, cpu, cpu_limit, out, qualified):
    os.sched_setaffinity(0, {cpu})

    def budget_reached(_signal, _frame):
        raise TimeoutError(f'Worker {index:02d} reached its Phase 2 CPU allotment')

    signal.signal(signal.SIGXCPU, budget_reached)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit - 1, cpu_limit))
    from paired import ARMS, load, one

    stage, ctx, full, cd, slicer, provenance = load()
    check_phase1(stage, provenance, qualified)
    if list(ARMS) != qualified['arms']:
        raise ValueError('Actual paired arms differ from the qualified arms')
    path = out/f'rows-{index:02d}.jsonl'
    rows = 0
    with path.open('x') as handle:
        for frame in FRAMES[index::count]:
            for scenario, rho in stage.CELLS:
                base = stage.inputs(ctx, frame, scenario, rho)
                for snr in stage.GRID[rho]:
                    key = scenario, rho, snr, frame
                    try:
                        row, _ = one(stage, ctx, full, cd, slicer, base, key)
                        handle.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
                    except Exception as exc:
                        raise RuntimeError(f'Failed key {key}') from exc
                    rows += 1
    print(f'Completed shard {index:02d}, {rows} keys', flush=True)
    return dict(shard=index, cpu=cpu, rows=rows, path=str(path)), provenance


def main():
    start = monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--freeze-revision', required=True)
    parser.add_argument('--producing-revision', required=True)
    args = parser.parse_args()
    if (not all(re.fullmatch('[0-9a-f]{40}', r) for r in (args.freeze_revision, args.producing_revision))
            or not args.freeze_revision.startswith(FREEZE)):
        parser.error('Expected the full frozen and producing revisions')
    out = args.out.resolve()
    if out != HERE/'out/main_20261120':
        parser.error('Expected the approved Phase 2 output directory')
    if any(os.environ.get(key) != '1' for key in THREAD_ENV) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Expected CPU-only single-thread execution')

    checks = source_checks(out/'SOURCE_SHA256.txt')
    qualified = read_json(HERE/'out/phase1_config.json')['_config']
    g3 = read_json(HERE/'out/g3.json')
    if (g3['status'] != 'PASS' or g3['fresh'] != [FRAMES.start, FRAMES.stop - 1]
            or qualified['fresh'] != g3['fresh'] or read_json(HERE/'out/phase1_done.json')['status'] != 'DONE'):
        raise ValueError('Frozen frame selection or Phase 1 receipt differs')
    anchor = read_json(HERE/'out/anchor_calibration.json')
    if anchor['s_anchor_floor'] != .8:
        raise ValueError('Frozen scalar anchor differs from the Phase 1 calibration')
    idle = idle_cores()
    n = min(23, len(idle) - 17)
    worker_cpus = idle[:n]
    os.sched_setaffinity(0, {idle[n]})
    cpu_limit = (CPU_SECONDS - CONTROLLER_SECONDS - SHELL_RESERVE_SECONDS) // n
    config = dict(freeze_revision=args.freeze_revision, producing_revision=args.producing_revision,
                  source_sha256=checks, frames_inclusive=g3['fresh'], keys=KEYS,
                  cells=qualified['cells'], grid=qualified['grid'],
                  arms=['F0', *qualified['arms']], anchor_calibration=anchor,
                  idle_physical_cores_at_kickoff=len(idle), load_average=list(os.getloadavg()),
                  controller_cpu=idle[n], worker_cpus=worker_cpus, workers=n,
                  per_worker_cpu_cap_seconds=cpu_limit, cpu_cap_core_hours=6, wall_cap_seconds=1800)
    bound = dict(_argv=sys.argv, _config=config)
    write_json(out/'run_config.json', bound)
    print(f'Bound {args.producing_revision}; {len(idle)} idle physical cores; {n} workers', flush=True)

    parts = []
    loaded = None
    with ProcessPoolExecutor(max_workers=n, mp_context=multiprocessing.get_context('fork')) as pool:
        futures = [pool.submit(shard, i, n, cpu, cpu_limit, out, qualified)
                   for i, cpu in enumerate(worker_cpus)]
        resource.setrlimit(resource.RLIMIT_CPU, (CONTROLLER_SECONDS, CONTROLLER_SECONDS))
        for completed in as_completed(futures):
            part, provenance = completed.result()
            if loaded is None:
                loaded = provenance
            if loaded != provenance:
                raise ValueError('Workers loaded different receiver sources or environments')
            parts.append(part)
    parts.sort(key=lambda part: part['shard'])
    if sum(part['rows'] for part in parts) != KEYS:
        raise ValueError('Incomplete key grid')
    row_paths = [Path(part['path']) for part in parts]
    with (out/'REMOTE_ROWS_MD5.txt').open('x') as handle:
        for path in row_paths:
            print(digest(path, 'md5'), path, file=handle)
    print('Scoring the completed raw rows with the frozen verdict code', flush=True)
    import verdict
    from report_main import render

    if Path(verdict.crossing.__code__.co_filename).resolve() != HERE.parent/'tcom_reference_frame_20261015/p1_agg.py':
        raise ValueError('Verdict loaded the wrong crossing implementation')
    score = verdict.analyze(verdict.read_rows(row_paths), FRAMES, s_anchor_floor=anchor['s_anchor_floor'])
    write_json(out/'results.json', {**bound, **score})
    usage = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    core_seconds = sum(u.ru_utime + u.ru_stime for u in usage)
    receipt = dict(freeze_revision=args.freeze_revision, producing_revision=args.producing_revision,
                   core_hours=core_seconds / 3600, wall_seconds=monotonic() - start,
                   workers=n, shards=parts, source=loaded, source_sha256=checks,
                   manifest_md5=digest(out/'REMOTE_ROWS_MD5.txt', 'md5'))
    write_json(out/'receipt.json', receipt)
    with (out/'RESULTS.md').open('x') as handle:
        handle.write(render({**bound, **score}, receipt))
    print(f'Completed {KEYS} keys in {receipt["wall_seconds"]:.2f}s, {receipt["core_hours"]:.6f} core-hours',
          flush=True)


if __name__ == '__main__':
    main()
