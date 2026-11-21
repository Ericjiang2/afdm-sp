"""Schedule the five §8 arms on the replacement frame grid."""

from hashlib import sha256
from pathlib import Path
import random
import re
from types import FunctionType

import gap_receiver as receiver
import kprime


HERE = Path(__file__).resolve().parent
MAIN_OUT = HERE / 'out/main_v2_20261119'
MAIN_FRAMES = range(4800, 5000)
SCENARIOS = ('U', 'G')
RHO_PM = 300
SNRS = (600, 700, 800, 900, 1000, 1100)
MAIN_KEYS = frozenset((scenario, RHO_PM, snr, frame)
                      for frame in MAIN_FRAMES for scenario in SCENARIOS for snr in SNRS)
QUALIFICATION_ARCHIVE_KEYS = frozenset(
    random.Random(20261121).sample(sorted(receiver.ARCHIVE_KEYS), 20)
)
QUALIFICATION_KEYS = QUALIFICATION_ARCHIVE_KEYS | receiver.SMOKE_KEYS
PROVENANCE_FIELDS = ('snapshot_sha256', 'producing_commit', 'freeze_commit', 'glue_commit')
FROZEN_LAUNCH = receiver.FROZEN_DIR / 'run_main.py'
FROZEN_LAUNCH_SHA256 = '4b6612fd6de91ffc2b314117c627d64a135cc7620a9c18253b530719a4736ac7'


def _load_shard_tools():
    source = FROZEN_LAUNCH.read_bytes()
    if sha256(source).hexdigest() != FROZEN_LAUNCH_SHA256:
        raise RuntimeError(f'Frozen shard utility source differs: {FROZEN_LAUNCH}')
    scope = {'__file__': str(FROZEN_LAUNCH), '__name__': 'qualified_unified_shard_tools'}
    exec(compile(source, str(FROZEN_LAUNCH), 'exec'), scope)
    return scope


_shard_tools = _load_shard_tools()
canonical = _shard_tools['canonical']
publish = _shard_tools['publish']
shard_path = _shard_tools['shard_path']
ROW_MANIFEST = _shard_tools['ROW_MANIFEST']

_qualified_key = kprime.bind_key(receiver.SMOKE_KEYS | MAIN_KEYS)


def main_key(ctx, cache, grid, key, *, qualification=False, cap=True, verify_controls=False):
    legal_keys = QUALIFICATION_KEYS if qualification else MAIN_KEYS
    if key not in legal_keys or (not qualification and (not cap or verify_controls)):
        raise ValueError(f'Unregistered Phase 2 key or controls: {key}')
    return _qualified_key(ctx, cache, grid, key, cap=cap, verify_controls=verify_controls)


def _write_shard(out, index, keys, snapshot, commits):
    e3c = receiver.frozen.e3c
    ctx = e3c.p1ctx.load()
    grid = e3c.sbl.full_grid(int(ctx.system.l_max_cap))
    with publish(shard_path(out, index)) as handle:
        for key in keys:
            try:
                row = main_key(ctx, e3c.e3d.PilotCache(), grid, key)
                if (tuple(row['key']) != key or tuple(row['variants']) != receiver.ARMS
                        or row['k_psd']['cap_kind'] != kprime.CAP_KIND):
                    raise RuntimeError('Receiver row does not match the registered key, five arms and K prime schema')
                handle.write(canonical(dict(**commits, snapshot_sha256=snapshot, key=key, row=row)) + '\n')
            except Exception as exc:
                raise RuntimeError(f'Shard {index:03d} failed on key {key}: {exc}') from exc
    print(f'Shard {index:03d} completed ({len(keys)} rows)', flush=True)


def _schedule(workers):
    # Whole frame clusters stay on one worker and are spread across the grid.
    return {index: [(scenario, RHO_PM, snr, frame)
                    for frame in MAIN_FRAMES[index::workers]
                    for scenario in SCENARIOS for snr in SNRS]
            for index in range(workers)}


def run_shards(out, workers, provenance):
    """Publish immutable, complete shards or stop on the first worker failure."""
    from launch_main import FREEZE

    if (provenance['freeze_commit'] != FREEZE or provenance['producing_commit'] != FREEZE
            or provenance['main_frames'] != [MAIN_FRAMES.start, MAIN_FRAMES.stop - 1]):
        raise ValueError('The §8 schedule requires its own refreeze and matching launch configuration')
    out = Path(out).resolve()
    if out != MAIN_OUT or not out.is_dir():
        raise ValueError(f'Use the registered main output directory: {MAIN_OUT}')
    if not 1 <= workers <= 14:
        raise ValueError('Run at most 14 workers to leave room for startup subprocesses')
    provenance = {field: provenance[field] for field in PROVENANCE_FIELDS}
    for field, value in provenance.items():
        width = 64 if field == 'snapshot_sha256' else 40
        if not re.fullmatch(f'[0-9a-f]{{{width}}}', value):
            raise ValueError(f'Invalid main provenance value for {field}')
    manifest = out / ROW_MANIFEST
    if manifest.exists() or any(out.glob('*rows_shard*.jsonl*')):
        raise FileExistsError(f'{out} already contains main shards')

    # Bind only the worker entry point. The qualified coordinator terminates
    # outstanding workers on a failed sentinel.
    run_pending = _shard_tools['run_pending']
    run = FunctionType(run_pending.__code__, dict(run_pending.__globals__, write_shard=_write_shard))
    jobs = _schedule(workers)
    snapshot = provenance.pop('snapshot_sha256')
    run(out, jobs, snapshot, provenance)
    with publish(manifest) as handle:
        for index in jobs:
            path = shard_path(out, index)
            digest = _shard_tools['hex_digest'](path, 'md5')
            handle.write(f'{digest}  {path.name}\n')
    return manifest
