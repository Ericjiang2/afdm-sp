"""Execute the frozen main grid, then aggregate its complete shards."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import multiprocessing
from multiprocessing.connection import wait
import os
from pathlib import Path
import platform
import re
import resource
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out' / 'main_20261119'
FREEZE_COMMIT = '87e7fd2ce168ac61fc3e85d1d3ef092818678e28'
HEADER_COMMIT = '84960739a0efd0ce7e790e0927129143d52597d2'
FRAMES = range(5400, 5800)
SCENARIOS = ('U', 'G')
RHOS = (150, 200, 250, 300, 400, 500)
SNRS = (300, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200)
ARMS = ('F0', 'A2', 'CD')
GRID = {(s, rho): SNRS for s in SCENARIOS for rho in RHOS}
KEY_FIELDS = ('scenario', 'rho_permille', 'snr_centi_db', 'frame')
KEY_COUNT = len(FRAMES) * len(GRID) * len(SNRS)
WORKERS = 24
WALL_LIMIT_SECONDS = 1375
CPU_LIMIT_SECONDS = 10 * 3600
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')

AUDIT = 'out/phase1/audit_remote.json'
QUALIFICATION = 'out/phase1b/qualification.json'
PRECISION = 'out/phase1b/precision.json'
VERDICT_DEPENDENCY = HERE.parent / 'tcom_reference_frame_20261015' / 'p1_agg.py'
VERDICT_DEPENDENCY_SHA256 = 'd28d8b2ff29dcc66982d583636d66dba55609da42319550f24b883d2aa6477a1'
FROZEN_SHA256 = {
    'PROTOCOL.md': '360c2619667eca2d04e1d625b0f4feff3809e09d6aac332675b925527cb11aa2',
    'phase1.py': '4b531189cc268d9978c7bbda6ebea5b486228695dd2d6641203624c8acd419e9',
    'mechanism.py': 'f40a9ebea38427dfa4fadeafec9cb8e5b4e5e656817548cba82e5b5cc6671218',
    'analysis.py': 'e05880699d3862c3cd1ff0856e83bd65779f731eda35c51db9127e5fa29f7708',
    AUDIT: '8daeb758f11c6271fbeda4c5f52c49322c7eeb53d3823b5d6e8e64ecd1925765',
    QUALIFICATION: '47ac0a648ee39b38541ecb228d4fdf30868a131bb05fc6a5e7bb9bdb6325a2a5',
    PRECISION: 'ce89bd729f4bc7a314dabfbd3df2538ff6f294a57b2804c37480be0e01cd6b4a',
}
GLUE = {'launch_main.sh', 'run_main.py', 'report_main.py'}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_digest(path, expected):
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError(f'Expected a SHA-256 digest for {path}')
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(f'Source mismatch for {path}: expected {expected}, got {actual}')


def verify_inputs(args):
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Expected the qualified deinlab Linux CPU environment')
    if any(os.environ.get(name) != '1' for name in THREADS):
        raise RuntimeError('Expected all numerical thread limits set to 1')
    if args.freeze_commit != FREEZE_COMMIT or args.header_commit != HEADER_COMMIT:
        raise ValueError('Freeze or protocol header commit differs from the approved freeze')
    if (not re.fullmatch(r'[0-9a-f]{40}', args.producing_commit)
            or args.producing_commit in {FREEZE_COMMIT, HEADER_COMMIT}
            or not args.glue_reason.strip()):
        raise ValueError('Expected the producing launch commit and its reason')
    verify_digest(args.source_manifest, args.manifest_sha256)
    manifest = json.loads(args.source_manifest.read_text())
    if (manifest.keys() != FROZEN_SHA256.keys() | GLUE
            or any(manifest[name] != digest for name, digest in FROZEN_SHA256.items())):
        raise RuntimeError('Manifest differs from the frozen source inventory')
    for name, digest in manifest.items():
        path = HERE / name
        if path.resolve() != path:
            raise RuntimeError(f'Expected a real file at {path}')
        verify_digest(path, digest)
    verify_digest(VERDICT_DEPENDENCY, VERDICT_DEPENDENCY_SHA256)
    audit = json.loads((HERE / AUDIT).read_text())
    qualification = json.loads((HERE / QUALIFICATION).read_text())
    precision = json.loads((HERE / PRECISION).read_text())
    block = [FRAMES.start, FRAMES.stop - 1]
    if (audit['scope'] != 'deinlab' or audit['selected'] != block or audit['unreadable']
            or precision['frame_decision']['retained_block'] != block):
        raise RuntimeError('The audited and retained frame blocks must match the frozen main block')
    if (qualification['smoke_keys'] != 32 or not all(qualification[name] for name in (
            'smoke_parity', 'smoke_repeatability', 'archived_receiver_parity'))):
        raise RuntimeError('Phase 1b qualification was incomplete')
    return manifest, qualification


def verify_loaded(qualification):
    import phase1 as probe

    for module in (probe, sys.modules['mechanism']):
        if Path(module.__file__).resolve() != HERE / f'{module.__name__}.py':
            raise RuntimeError(f'Unexpected loaded receiver source for {module.__name__}')
    if (probe.ARMS, probe.SCENARIOS, probe.RHOS, probe.SNRS, probe.CELLS) != (
            ARMS, SCENARIOS, RHOS, SNRS, tuple(GRID)):
        raise RuntimeError('The qualified receiver grid differs from the frozen main schedule')
    _, _, sources = probe.preflight()
    if sources != qualification['source_checks']:
        raise RuntimeError('Loaded receiver sources or environment differ from Phase 1b')
    return sources


@contextmanager
def publish(path, *, buffering=-1):
    partial = path.with_suffix(path.suffix + '.part')
    with partial.open('x', encoding='utf-8', buffering=buffering) as handle:
        yield handle
        handle.flush()
        os.fsync(handle.fileno())
    os.link(partial, path)
    partial.unlink()


def write_json(path, value):
    with publish(path) as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def shard_path(index):
    return OUT / f'rows_shard{index:03d}.jsonl'


def row_key(row):
    return tuple(row[field] for field in KEY_FIELDS)


def shard_keys(frames):
    return ((s, rho, snr, frame) for frame in frames
            for s, rho in GRID for snr in SNRS)


def write_shard(index, frames, snapshot):
    import phase1 as probe

    probe.init_worker()
    with publish(shard_path(index), buffering=1) as handle:
        for frame in frames:
            for scenario, rho in GRID:
                base = probe.stage3.inputs(probe.ctx, frame, scenario, rho)
                for snr in SNRS:
                    key = (scenario, rho, snr, frame)
                    try:
                        row = probe.run_key(base, key, ARMS[1:], mechanism=True)
                        if row_key(row) != key:
                            raise RuntimeError('Receiver returned a different key')
                        row['snapshot_sha256'] = snapshot
                        handle.write(json.dumps(row, allow_nan=False, separators=(',', ':')) + '\n')
                    except Exception as exc:
                        raise RuntimeError(f'Shard {index:03d} failed on {key}') from exc
    print(f'Shard {index:03d} completed ({len(frames) * len(GRID) * len(SNRS)} keys)', flush=True)


def run_workers(assignments, snapshot):
    context = multiprocessing.get_context('spawn')
    running = {}
    try:
        for index, frames in assignments.items():
            process = context.Process(target=write_shard, args=(index, frames, snapshot))
            process.start()
            running[process.sentinel] = (index, process)
        while running:
            for ready in wait(running):
                index, process = running.pop(ready)
                process.join()
                code = process.exitcode
                process.close()
                if code:
                    raise RuntimeError(f'Shard {index:03d} exited with status {code}')
    finally:
        for _, process in running.values():
            process.terminate()
        for _, process in running.values():
            process.join()
            process.close()


def validate_shards(assignments, snapshot):
    names = {shard_path(index).name for index in assignments}
    if names != {path.name for path in OUT.glob('rows_shard*.jsonl')}:
        raise RuntimeError('Completed shard inventory differs from the main schedule')
    rows, hashes, frame_inputs = [], {}, {}
    for index, frames in assignments.items():
        path = shard_path(index)
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for key, line in zip(shard_keys(frames), handle, strict=True):
                digest.update(line)
                row = json.loads(line)
                if row_key(row) != key or row['snapshot_sha256'] != snapshot:
                    raise RuntimeError(f'Wrong key or source snapshot at {path.name}, expected {key}')
                shared = tuple(row['inputs'][name] for name in ('info', 'coded', 'noise'))
                if frame_inputs.setdefault(key[-1], shared) != shared:
                    raise RuntimeError(f'Common-randomness pairing differs at {key}')
                rows.append(row)
        hashes[path.name] = digest.hexdigest()
    if len(rows) != KEY_COUNT:
        raise RuntimeError(f'Expected {KEY_COUNT} distinct keys, got {len(rows)}')
    with publish(OUT / 'ROWS_SHA256.txt') as handle:
        for name, digest in hashes.items():
            handle.write(f'{digest}  {name}\n')
    return rows


def used_cpu_seconds():
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.process_time() + children.ru_utime + children.ru_stime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-commit', required=True)
    parser.add_argument('--header-commit', required=True)
    parser.add_argument('--producing-commit', required=True)
    parser.add_argument('--glue-reason', required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    if (not OUT.is_dir() or os.environ.get('TMPDIR') != str(OUT / 'tmp')
            or set(path.name for path in OUT.iterdir()) - {'run.log', 'cpu.txt', 'tmp'}):
        raise RuntimeError('Start the main chain with launch_main.sh and a new output directory')
    manifest, qualification = verify_inputs(args)
    import analysis
    import report_main

    if (Path(report_main.__file__).resolve() != HERE / 'report_main.py'
            or Path(analysis.__file__).resolve() != HERE / 'analysis.py'
            or Path(analysis.p1_agg.__file__).resolve() != VERDICT_DEPENDENCY):
        raise RuntimeError('Loaded reporting or verdict sources differ from the verified files')
    sources = verify_loaded(qualification)

    provenance = dict(_argv=sys.argv, _config=dict(
        freeze_commit=args.freeze_commit, protocol_header_commit=args.header_commit,
        producing_commit=args.producing_commit, glue_reason=args.glue_reason, output=str(OUT),
        frames_inclusive=[FRAMES.start, FRAMES.stop - 1], scenarios=SCENARIOS,
        rhos=RHOS, snrs=SNRS, arms=ARMS, keys=KEY_COUNT,
        workers=WORKERS, start_method='spawn', wall_limit_seconds=WALL_LIMIT_SECONDS,
        core_hour_cap=CPU_LIMIT_SECONDS / 3600,
        threads={name: os.environ[name] for name in (*THREADS, 'CUDA_VISIBLE_DEVICES')},
        source_manifest_sha256=args.manifest_sha256, source_sha256=manifest,
        verdict_dependency_sha256=VERDICT_DEPENDENCY_SHA256, qualified_sources=sources,
    ))
    snapshot = hashlib.sha256(json.dumps(provenance['_config'], sort_keys=True).encode()).hexdigest()
    provenance['_config']['snapshot_sha256'] = snapshot
    with publish(OUT / 'PRODUCING_COMMIT.txt') as handle:
        handle.write(f'{args.producing_commit}\n'
                     f'freeze_commit {args.freeze_commit}\n'
                     f'protocol_header_commit {args.header_commit}\n'
                     f'glue_reason {args.glue_reason}\n')
    write_json(OUT / 'SOURCE_SHA256.json', manifest)
    write_json(OUT / 'config.json', provenance)
    print(f'Sources and qualification verified. Starting {WORKERS} workers on {KEY_COUNT} keys.', flush=True)
    assignments = {index: FRAMES[index::WORKERS] for index in range(WORKERS)}
    run_workers(assignments, snapshot)
    rows = validate_shards(assignments, snapshot)
    report_main.aggregate(OUT, rows, GRID, tuple(FRAMES), provenance, used_cpu_seconds)
    if used_cpu_seconds() >= CPU_LIMIT_SECONDS:
        raise RuntimeError('CPU cap reached')
    print(f'{len(rows)} validated keys. Frozen aggregation completed.', flush=True)


if __name__ == '__main__':
    main()
