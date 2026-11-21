"""Execute the frozen receiver schedule and publish complete frame shards."""
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
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
MAIN_OUT = OUT / 'main_20261119'
QUALIFICATION = OUT / 'phase1b_attempt01' / 'results.json'
FROZEN_COMMIT = '7061ad84ee9805953c09ddd11ada1c297cd2e177'
FRAMES = range(4400, 4600)
SCENARIOS = ('U', 'G')
SBL_SNRS = (600, 700, 800, 900, 1000, 1100)
CSTATE_SNRS = {300: (500, 550, *SBL_SNRS), 500: (500, 550, 600, 650, *SBL_SNRS[1:])}
ROW_MANIFEST = 'REMOTE_ROWS_MD5.txt'
THREADS = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
           'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')


def canonical(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def hex_digest(path, algorithm):
    digest = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require_digest(path, expected):
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError(f'Invalid SHA256 in run manifest for {path.name}')
    actual = hex_digest(path, 'sha256')
    if actual != expected:
        raise RuntimeError(f'Frozen snapshot mismatch for {path}: expected {expected}, got {actual}')


def verify_inputs(args):
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Expected the qualified deinlab Linux CPU environment')
    if any(os.environ.get(name) != '1' for name in THREADS):
        raise ValueError('Set every numerical thread limit to 1 before Python starts')

    manifest = json.loads(args.manifest.read_text())
    if not re.fullmatch(r'[0-9a-f]{40}', args.producing_commit):
        raise ValueError('Expected the full producing commit')
    if manifest['frozen_commit'] != FROZEN_COMMIT or manifest['producing_commit'] != args.producing_commit:
        raise ValueError('Run manifest commit identity differs')
    require_digest(QUALIFICATION, manifest['phase1b_receipt_sha256'])
    qualification = json.loads(QUALIFICATION.read_text())
    if not all(qualification[gate]['passed'] for gate in ('G1', 'G2', 'G3')):
        raise RuntimeError('Frozen Phase 1b qualification is incomplete')
    if (qualification['fresh']['status'] != 'PASS'
            or qualification['fresh']['eligible_inclusive'] != [4400, 4699]
            or qualification['cost']['sbl_selected_frames'] != len(FRAMES)
            or qualification['leverage']['v5_primary'] != 'fer'
            or qualification['leverage']['same_grid_margin'] != .005):
        raise RuntimeError('Phase 1b receipt does not qualify the frozen execution schedule')

    frozen = manifest['frozen_sources_sha256']
    glue = manifest['glue_sources_sha256']
    qualified_sources = qualification['_config']['own_sources_sha256']
    if (any(frozen.get(name) != digest for name, digest in qualified_sources.items())
            or 'PROTOCOL.md' not in frozen or 'run_main.py' not in glue or frozen.keys() & glue.keys()):
        raise RuntimeError('Run manifest does not cover the qualified, frozen and launch sources')
    for name, digest in (frozen | glue).items():
        if Path(name).name != name or (HERE / name).resolve() != HERE / name:
            raise ValueError(f'Expected a real file in the experiment root: {name}')
        require_digest(HERE / name, digest)
    return manifest, qualification


def verify_loaded(manifest, qualification):
    import numpy
    import scipy
    import run_phase1 as p1

    for name in ('sbl', 'cstate', 'projector', 'archives', 'verdict', 'run_phase1'):
        actual = Path(sys.modules[name].__file__).resolve()
        if actual != HERE / f'{name}.py':
            raise RuntimeError(f'Unexpected actual import for {name}: {actual}')
        require_digest(actual, manifest['frozen_sources_sha256'][actual.name])

    verified = p1.archives.load_preflight(p1.sbl, p1.cstate, p1.C_SMOKE)
    if verified['identity'] != qualification['_config']['sources']:
        raise RuntimeError('Loaded sources or archival references differ from Phase 1b')
    if tuple(p1.cstate.stage3.CELLS) != tuple((s, rho) for s in SCENARIOS for rho in CSTATE_SNRS):
        raise RuntimeError('Loaded Stage 3 cell order differs from the frozen CSTATE grid')
    if p1.cstate.stage3.GRID != CSTATE_SNRS:
        raise RuntimeError('Loaded Stage 3 SNR grid differs from the frozen CSTATE grid')
    runtime = dict(host=platform.node(), python=platform.python_version(), numpy=numpy.__version__,
                   scipy=scipy.__version__, cpu_only=os.environ['CUDA_VISIBLE_DEVICES'] == '',
                   threads={name: os.environ[name] for name in THREADS})
    qualified = qualification['_config']
    if any(runtime[name] != qualified[name] for name in ('host', 'python', 'numpy', 'threads')):
        raise RuntimeError('Execution host, runtime or numerical thread limits differ from Phase 1b')

    smoke_sbl = tuple(p1.sbl.e3c.lib.smoke_keys()[0])
    archived_cstate = next(row for row in verified['cstate_smoke'] if row['triggered'])
    smoke_cstate = p1.archives.key(archived_cstate)
    old_a2 = tuple(qualified['a2_archive_keys'][0])
    if not verified['split_rows'][old_a2]['triggered']:
        raise RuntimeError('Pilot A2 archive key must be a triggered historical row')
    pilot_keys = (('sbl', smoke_sbl), ('cstate', smoke_cstate), ('cstate', old_a2))
    if any(key[3] in range(4400, 4700) for _, key in pilot_keys):
        raise RuntimeError('Pilot key unexpectedly overlaps the audited prospective block')
    return verified['identity'], runtime, pilot_keys


def schedule(workers, pilot_keys=None):
    if pilot_keys is not None:
        frames = sorted({key[3] for _, key in pilot_keys})
        return {index: [(leg, key) for frame in assigned for leg, key in pilot_keys if key[3] == frame]
                for index in range(min(workers, len(frames))) if (assigned := frames[index::workers])}
    return {index: [(leg, (s, rho, snr, frame))
                    for frame in FRAMES[index::workers]
                    for leg, grid in (('sbl', {300: SBL_SNRS}), ('cstate', CSTATE_SNRS))
                    for s in SCENARIOS for rho, snrs in grid.items() for snr in snrs]
            for index in range(workers)}


@contextmanager
def publish(path):
    part = path.with_name(f'.{path.name}.{os.getpid()}.{time.time_ns()}.part')
    with part.open('x', encoding='utf-8') as handle:
        yield handle
        handle.flush()
        os.fsync(handle.fileno())
    part.chmod(0o444)
    # A final name is installed only after success and cannot replace a shard.
    os.link(part, path)
    part.unlink()


def write_json(path, obj):
    with publish(path) as handle:
        json.dump(obj, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write('\n')


def shard_path(out, index):
    return out / f'rows_shard{index:03d}.jsonl'


def write_shard(out, index, jobs, snapshot, launch_commit):
    import run_phase1 as p1

    p1.init_worker()
    base_id = None
    with publish(shard_path(out, index)) as handle:
        for leg, key in jobs:
            s, rho, snr, frame = key
            try:
                if leg == 'sbl':
                    row = p1.s_run(key)
                else:
                    if (frame, s, rho) != base_id:
                        base = p1.cstate.stage3.inputs(p1.c_ctx, frame, s, rho)
                        base_id = (frame, s, rho)
                    row = p1.cstate.one(p1.c_ctx, p1.full, p1.cd, base, *key, admission=True)
                if p1.archives.key(row) != key:
                    raise AssertionError('Receiver returned a row for a different key')
                handle.write(canonical(dict(leg=leg, key=key, row=row,
                                            snapshot_sha256=snapshot, launch_commit=launch_commit)) + '\n')
            except Exception as exc:
                raise RuntimeError(f'Shard {index:03d}, {leg} key {key} failed') from exc
    print(f'Shard {index:03d} completed ({len(jobs)} rows)', flush=True)


def closed_shards(out, jobs, snapshot):
    expected_names = {shard_path(out, index).name for index in jobs}
    if any(path.name not in expected_names for path in out.glob('rows_shard*.jsonl')):
        raise RuntimeError('Unexpected completed shard name under the run directory')
    closed = []
    for index, assigned in jobs.items():
        path = shard_path(out, index)
        if not path.exists():
            continue
        with path.open() as handle:
            for (leg, key), line in zip(assigned, handle, strict=True):
                saved = json.loads(line)
                if (saved['leg'] != leg or tuple(saved['key']) != key
                        or saved['snapshot_sha256'] != snapshot):
                    raise RuntimeError(f'Completed shard {path.name} differs from the frozen snapshot or schedule')
        closed.append(index)
    return closed


def run_pending(out, jobs, snapshot, producing_commit):
    context = multiprocessing.get_context('spawn')
    running = {}
    try:
        for index, assigned in jobs.items():
            process = context.Process(target=write_shard, args=(out, index, assigned, snapshot, producing_commit))
            process.start()
            running[process.sentinel] = (index, process)
        while running:
            for ready in wait(running):
                index, process = running.pop(ready)
                process.join()
                exit_code = process.exitcode
                process.close()
                if exit_code:
                    raise RuntimeError(f'Shard {index:03d} exited with status {exit_code}; see traceback')
    finally:
        for _, process in running.values():
            process.terminate()
        for _, process in running.values():
            process.join()
            process.close()


def run(args):
    if args.verify_only and args.resume:
        raise ValueError('Verification does not resume a run')
    manifest, qualification = verify_inputs(args)
    sources, runtime, pilot_keys = verify_loaded(manifest, qualification)
    if args.verify_only:
        print(canonical(dict(passed=True, frozen_commit=FROZEN_COMMIT,
                             producing_commit=args.producing_commit, pilot_keys=pilot_keys, runtime=runtime)))
        return

    out = args.out.resolve()
    if not out.is_relative_to(OUT) or not out.is_dir() or (out == MAIN_OUT) == args.pilot:
        raise ValueError('Prospective rows must use the registered main output; use a separate output for pilot rows')
    mode = 'pilot' if args.pilot else 'main'
    jobs = schedule(args.workers, pilot_keys if args.pilot else None)
    grid = (dict(pilot_keys=pilot_keys) if args.pilot else
            dict(frames_inclusive=[FRAMES.start, FRAMES.stop - 1], scenarios=SCENARIOS,
                 sbl=dict(rho_permille=300, snr_centi_db=SBL_SNRS, keys=2400, iterations=100),
                 cstate=dict(snr_centi_db={str(rho): snrs for rho, snrs in CSTATE_SNRS.items()},
                             keys=6800, admission=True)))
    snapshot_config = dict(mode=mode, frozen_commit=FROZEN_COMMIT, workers=args.workers, grid=grid,
                           v5_primary='fer', margin=.005, core_hour_cap=25,
                           sources=sources, runtime=runtime,
                           frozen_sources_sha256=manifest['frozen_sources_sha256'],
                           phase1b_receipt_sha256=manifest['phase1b_receipt_sha256'])
    snapshot = hashlib.sha256(canonical(snapshot_config).encode()).hexdigest()
    commit_path = out / 'PRODUCING_COMMIT.txt'
    config_path = out / 'config.json'
    if args.resume:
        previous = json.loads(config_path.read_text())['_config']
        if (previous['snapshot_sha256'] != snapshot
                or canonical({name: previous[name] for name in snapshot_config}) != canonical(snapshot_config)
                or commit_path.read_text().strip() != previous['producing_commit']):
            raise RuntimeError('Resume rejected: scientific snapshot or original producing commit changed')
        closed = closed_shards(out, jobs, snapshot)
    else:
        if config_path.exists() or commit_path.exists() or any(out.glob('rows_shard*.jsonl')):
            raise RuntimeError(f'{out} already contains a run')
        closed = []
        write_json(config_path, dict(_argv=sys.argv, _config=dict(
            snapshot_config, snapshot_sha256=snapshot, producing_commit=args.producing_commit,
            glue_sources_sha256=manifest['glue_sources_sha256'])))
        with publish(commit_path) as handle:
            handle.write(args.producing_commit + '\n')

    pending = {index: assigned for index, assigned in jobs.items() if index not in closed}
    write_json(out / f'attempt_{time.time_ns()}.json', dict(
        _argv=sys.argv, _config=dict(snapshot_sha256=snapshot, producing_commit=args.producing_commit,
                                     glue_sources_sha256=manifest['glue_sources_sha256'],
                                     retained_shards=closed, launched_shards=list(pending))))
    print(f'Verified {mode} snapshot {snapshot}; starting {len(pending)} shards, retained {len(closed)}', flush=True)
    run_pending(out, pending, snapshot, args.producing_commit)

    lines = [f'{hex_digest(shard_path(out, index), "md5")}  {shard_path(out, index).name}\n' for index in jobs]
    md5_path = out / ROW_MANIFEST
    if md5_path.is_file():
        if md5_path.read_text() != ''.join(lines):
            raise RuntimeError('Completed shard manifest does not match the immutable rows')
    else:
        with publish(md5_path) as handle:
            handle.writelines(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--producing-commit', required=True)
    parser.add_argument('--workers', type=int, choices=range(1, 29), default=28)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--verify-only', action='store_true')
    mode.add_argument('--pilot', action='store_true')
    parser.add_argument('--resume', action='store_true')
    run(parser.parse_args())


if __name__ == '__main__':
    main()
