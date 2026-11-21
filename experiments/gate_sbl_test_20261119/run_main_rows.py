"""Admit the frozen Phase 2 schedule to the qualified receiver arms."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import json
import multiprocessing
import os
from pathlib import Path
import sys
from types import FunctionType, SimpleNamespace

from audit_fresh import S_BASE, S_EXTENSION, X, verify
from main_schedule import S_RHO, S_SCENARIOS, S_SNRS, s_keys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out/main_20261119'
PHASE1 = HERE / 'out/phase1_v4_20261119'
PHASE1B = HERE / 'out/phase1b_20261119'
PHASE1B_RESULT_SHA256 = '37aa28564083a08cfb943b26325ec9b0588647458afd775485ca802afdd2bde3'
SCHEDULE_SHA256 = 'b49e5f30b97fc5ee95a5fe347bbf6a8b198db4e830107bcd440579bf19ea6d24'
X_RECEIPTS = {
    'x_g2.json': '3cf5e0b1ca44606c5420e15a71ff499015003eba9184a007f3a669296ecf68aa',
    'x_g5.json': '34caabc7d0386c06a9fbb1d7d8afeb6f0c740caa64a836f6b2e8504351ed9c2e',
}
MAX_WORKERS = 27
_RUN_ROW = None


def phase2_schedule():
    verify(PHASE1B / 'main_schedule.json', SCHEDULE_SHA256)
    schedule = json.loads((PHASE1B / 'main_schedule.json').read_text())
    segments = tuple(map(tuple, schedule['s_segments']))
    if (segments != (S_BASE, S_EXTENSION) or tuple(schedule['x_segment']) != X
            or schedule['s_rho_permille'] != S_RHO
            or tuple(schedule['s_scenarios']) != S_SCENARIOS
            or tuple(schedule['s_snr_centi_db']) != S_SNRS
            or (schedule['x_snr_db'], schedule['x_rho']) != (7, .5)
            or schedule['cluster_unit'] != 'physical frame'):
        raise ValueError('Phase 1b schedule differs from the freeze')
    s = s_keys(segments)
    x = range(X[0], X[1] + 1)
    if (len(s), len(x), len({key[3] for key in s})) != (4800, 600, 400):
        raise ValueError('Phase 2 schedule has unexpected S keys, X frames, or S clusters')
    return schedule, s, x


def qualification(schedule):
    import numpy
    import scipy
    from run_phase1 import THREADS, fresh_receipts
    from run_phase1b import audit_extensions, reference_smoke

    if (sys.platform != 'linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != ''
            or any(os.environ.get(name) != '1' for name in THREADS)):
        raise RuntimeError('Phase 2 requires deinlab Linux and a CPU-only, single-thread launcher')
    for folder in (PHASE1, PHASE1B):
        if (folder / 'STATUS').read_text() != 'DONE\n':
            raise RuntimeError(f'Qualification is incomplete: {folder}')
    verify(PHASE1B / 'results.json', PHASE1B_RESULT_SHA256)
    p1, _ = reference_smoke()
    p1b = json.loads((PHASE1B / 'results.json').read_text())
    config = p1b['_config']
    if (p1b['main_schedule'] != schedule or p1b['byte_identical_smoke_rows'] != 12
            or config['python'] != sys.version or config['numpy'] != numpy.__version__
            or config['scipy'] != scipy.__version__):
        raise RuntimeError('Schedule, smoke parity, or numerical runtime differs from Phase 1b')

    legacy = HERE / 'out/preflight_v2_20261119'
    if fresh_receipts(legacy / 'fresh_local.json', legacy / 'fresh_deinlab.json') != p1['audits']:
        raise RuntimeError('Phase 1 base or X audit differs from qualification')
    extension = HERE / 'out/preflight_1b_20261119'
    audits = audit_extensions(extension / 'fresh_local.json', extension / 'fresh_deinlab.json')
    if (audits != config['extension_audits']
            or any(record['status'] != 'PASS' for record in audits.values())):
        raise RuntimeError('Phase 1b S extension audit differs from qualification')
    for name, digest in X_RECEIPTS.items():
        path = PHASE1 / name
        verify(path, digest)
        row = json.loads(path.read_text())
        if not row['pass_'] or row['frames'] != 20:
            raise RuntimeError(f'Incomplete X qualification: {name}')
    return tuple(sorted(p1['s_archive']['source_identity'].items())), p1['x_archive']


def _bind(source, **changes):
    bound = FunctionType(source.__code__, dict(source.__globals__, **changes),
                         source.__name__, source.__defaults__, source.__closure__)
    bound.__kwdefaults__ = source.__kwdefaults__
    return bound


def bind_s_key(source, receiver, allowed):
    """Replace the private admission callback while keeping all receiver methods."""
    lib = SimpleNamespace(**dict(vars(receiver.e3c.lib), smoke_keys=lambda: allowed))
    e3c = SimpleNamespace(**dict(vars(receiver.e3c), lib=lib))
    scoped_receiver = SimpleNamespace(**dict(vars(receiver), e3c=e3c))
    bound = _bind(source, receiver=lambda: scoped_receiver)

    def run(ctx, grid, key):
        return bound(ctx, grid, key, replace_with_low=False)

    return run


def bind_x_frame(source, allowed):
    bound = _bind(source, ARCHIVE_FRAMES=allowed)

    def run(ctx, full, cd, frame):
        return bound(ctx, full, cd, frame, gate='actual')

    return run


def validate_x_identity(row):
    census = row['gate_census']
    nonempty = (census['nonempty_trials'] or census['active_refits']
                or any(block['gate_rank'] for blocks in census['local_pass_blocks'] for block in blocks)
                or any(block['gate_rank'] for block in census['final_blocks']))
    fingerprints = row['output_fingerprints']
    if not nonempty and fingerprints['CD'] != fingerprints['G-ex']:
        raise RuntimeError(f"G-ex and CD differ with empty effective projectors on frame {row['frame']}")


def _require_torch_single_thread():
    import torch

    if (torch.get_num_threads(), torch.get_num_interop_threads()) != (1, 1):
        raise RuntimeError('Frozen receiver context did not configure single-thread Torch')


def s_context(source_identity):
    import s_arm
    import s_gates

    ctx, _, _, _, _, grid, _ = s_gates.context(source_identity)
    s_arm.gate_source()
    _require_torch_single_thread()
    return ctx, grid, s_arm


def init_s_worker(source_identity, allowed, init_lock):
    global _RUN_ROW
    # Frozen context initialization can spawn lscpu. Serialize it to keep
    # the short-lived child within the same process budget as the workers.
    with init_lock:
        ctx, grid, arm = s_context(source_identity)
    run = bind_s_key(arm.run_key, arm.receiver(), allowed)
    _RUN_ROW = partial(run, ctx, grid)


def prepare_x(allowed, expected_source):
    import x_arm
    import x_gates

    context, _, source = x_gates._archive_and_context()
    if source != expected_source:
        raise RuntimeError('Loaded MIXED8 source identity differs from Phase 1')
    _require_torch_single_thread()
    run = bind_x_frame(x_arm.one, allowed)

    def one(frame):
        row = run(*context, frame)
        validate_x_identity(row)
        return row

    return one


def worker(item):
    try:
        return _RUN_ROW(item)
    except Exception as exc:
        raise RuntimeError(f'Phase 2 receiver failed at {item}') from exc


def write_rows(out, leg, keys, identity, workers):
    global _RUN_ROW
    if leg == 's':
        mp = multiprocessing.get_context('spawn')
        init = dict(initializer=init_s_worker, initargs=(identity, frozenset(keys), mp.Lock()))
    else:
        # The archived MIXED8 entry point inherits one already verified context.
        mp = multiprocessing.get_context('fork')
        _RUN_ROW = prepare_x(keys, identity)
        init = {}

    with (out / f'{leg}_rows.jsonl').open('x', buffering=1) as handle, ProcessPoolExecutor(
            max_workers=workers, mp_context=mp, **init) as pool:
        for count, (item, row) in enumerate(zip(keys, pool.map(worker, keys), strict=True), 1):
            row_id = tuple(row['key']) if leg == 's' else row['frame']
            if row_id != item:
                raise RuntimeError(f'Phase 2 row identity mismatch: expected {item}, got {row_id}')
            print(json.dumps(row, sort_keys=True, allow_nan=False, separators=(',', ':')), file=handle)
            if count % 100 == 0 or count == len(keys):
                print(f'{leg.upper()} rows: {count}/{len(keys)}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--leg', choices=('s', 'x'), required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=range(1, MAX_WORKERS + 1), default=MAX_WORKERS)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    if args.out.resolve() != OUT or (not args.validate_only and not OUT.is_dir()):
        parser.error('Expected the launcher-owned out/main_20261119 directory')

    schedule, s, x = phase2_schedule()
    s_source, x_source = qualification(schedule)
    if args.validate_only:
        if args.leg == 's':
            s_context(s_source)
        else:
            prepare_x(x, x_source)
        print(f'{args.leg.upper()} identity and qualification verified', flush=True)
        return
    keys, source = (s, s_source) if args.leg == 's' else (x, x_source)
    write_rows(OUT, args.leg, keys, source, args.workers)


if __name__ == '__main__':
    main()
