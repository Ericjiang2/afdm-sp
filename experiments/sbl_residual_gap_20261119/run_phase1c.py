"""Qualify the §8 receiver on archived and smoke keys only."""

import argparse
from concurrent.futures import ProcessPoolExecutor
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
from statistics import mean
import sys
from types import FunctionType

import run_main

# The frozen receiver adds sibling source paths with their own run_phase1.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_phase1 as p1

import kprime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aggregate_main import validate_row

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out/phase1c_20261119'
PARENT_RECEIPT = HERE / 'out/phase1b_20261119/results.json'
PARENT_SHA256 = 'bfcde4878b7256d1a7a6629ed402010f469ec17554837440126bcb15974dd1cf'
MODEL = 'gpt-6.2-sol'
WORKERS = 8
FRAMES = [4800, 4999]


def one(key, **options):
    cache = p1.receiver.frozen.e3c.e3d.PilotCache()
    return run_main.main_key(p1.ctx, cache, p1.grid, key, qualification=True, **options)


def check_archive(item):
    check = FunctionType(p1.g1.__code__, dict(p1.g1.__globals__, one=one))
    return check(item)


def check_smoke(key):
    started = resource.getrusage(resource.RUSAGE_SELF)
    first = one(key)
    ended = resource.getrusage(resource.RUSAGE_SELF)
    elapsed = (ended.ru_utime - started.ru_utime) + (ended.ru_stime - started.ru_stime)
    second = one(key, verify_controls=True)
    uncapped = one(key, cap=False, verify_controls=True)
    checks = second.pop('controls')
    disabled_checks = uncapped.pop('controls')
    p1.compare(p1.stable(first), p1.stable(second), f'G3 smoke repeat {key}')
    for arm, reference in (('K', 'U2'), ('KM', 'M')):
        p1.compare(p1.stable(p1.pick(first['variants'][reference], p1.ARM_FIELDS)),
                   p1.stable(p1.pick(uncapped['variants'][arm], p1.ARM_FIELDS)),
                   f'G2 cap disabled {key}/{arm}')
    controls = {**checks, **{name: value for name, value in disabled_checks.items()
                            if name.startswith('k_uncapped_')}}
    if not all(controls.values()) or first['k_psd']['cap_kind'] != kprime.CAP_KIND:
        raise AssertionError(f'G2 §8 receiver control failed on {key}: {controls}')
    return first, dict(key=key, psd=first['k_psd'], **controls), elapsed


def summarize(rows, timings):
    census = kprime.summarize_census([row['k_census'] for row in rows])
    if not census['per_key_share_count']:
        raise AssertionError('Smoke keys did not exercise the global cap')
    total = mean(timings)
    cost = dict(keys=2400, cpu_seconds_per_key=total, margin=1.3,
                projected_core_hours=2400 * total * 1.3 / 3600,
                main_core_hour_cap=15, smoke_keys=len(rows),
                arm_cpu_seconds_per_key={arm: mean(row['variants'][arm]['seconds']['total'] for row in rows)
                                         for arm in p1.receiver.ARMS})
    return census, cost


def run(args):
    if (sys.platform != 'linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != ''
            or any(os.environ.get(name) != '1' for name in p1.THREADS)):
        raise RuntimeError('Expected Linux CPU-only and single-thread numerical libraries')
    if (Path(p1.__file__).resolve() != HERE / 'run_phase1.py'
            or Path(validate_row.__code__.co_filename).resolve() != HERE / 'aggregate_main.py'):
        raise RuntimeError('Phase 1c loaded a sibling experiment runner')
    fresh = {}
    for scope, path in (('local', args.fresh_local), ('deinlab', args.fresh_deinlab)):
        receipt = json.loads(path.read_text())
        if (receipt['scope'] != scope or receipt['status'] != 'PASS' or receipt['unresolved']
                or receipt['interval_inclusive'] != FRAMES):
            raise RuntimeError(f'{scope} replacement-frame audit did not pass')
        fresh[scope] = sha256(path.read_bytes()).hexdigest()
    if sha256(PARENT_RECEIPT.read_bytes()).hexdigest() != PARENT_SHA256:
        raise p1.phase1.FrozenEvidenceError('Phase 1b qualification result differs')
    parent = json.loads(PARENT_RECEIPT.read_text())['_config']
    p1.init_worker()
    e3c_hashes = p1.phase1.frozen_identity(p1.ctx)
    if e3c_hashes != parent['frozen_e3c_sha256'] or p1.receiver.FROZEN_SOURCES != parent['frozen_unified_sha256']:
        raise p1.phase1.FrozenEvidenceError('Qualified receiver source identity differs')
    for name in ('gap_receiver.py', 'run_phase1.py', 'verdict.py'):
        if sha256((HERE / name).read_bytes()).hexdigest() != parent['own_sources_sha256'][name]:
            raise p1.phase1.FrozenEvidenceError(f'Frozen local dependency differs: {name}')
    old = sorted(run_main.QUALIFICATION_ARCHIVE_KEYS)
    smoke = sorted(p1.receiver.SMOKE_KEYS)
    if (old != sorted(map(tuple, parent['old_keys'])) or smoke != sorted(map(tuple, parent['smoke_keys']))
            or set(old + smoke) & run_main.MAIN_KEYS):
        raise AssertionError('Phase 1c schedule differs from qualified and disjoint keys')
    archive, _ = p1.archive_rows(old, p1.phase1)
    config = dict(_argv=sys.argv, _config=dict(
        base_commit=args.base_commit, phase='1c', model=MODEL, cpu_only=True, workers=WORKERS,
        host=platform.node(), python=platform.python_version(), numpy=p1.np.__version__, scipy=p1.scipy.__version__,
        threads={name: os.environ[name] for name in p1.THREADS}, core_hour_cap=1.5,
        old_keys=old, smoke_keys=smoke, fresh_frames=FRAMES, fresh_receipts_sha256=fresh,
        arms=['R0', 'U2', 'K′', 'M', 'KM′'], arm_field_aliases={'K′': 'K', 'KM′': 'KM'},
        cap_kind=kprime.CAP_KIND, frozen_phase1b_sha256=PARENT_SHA256,
        archive_manifest_sha256=p1.ARCHIVE_MANIFEST_SHA256, frozen_e3c_sha256=e3c_hashes,
        sources_sha256={name: sha256((HERE / name).read_bytes()).hexdigest() for name in
                        ('kprime.py', 'run_main.py', 'aggregate_main.py', 'run_phase1c.py', 'launch_phase1c.sh', 'audit_fresh.py',
                         'gap_receiver.py', 'run_phase1.py', 'verdict.py', 'PROTOCOL.md')},
    ))
    p1.phase1.write_json(OUT / 'config.json', config)
    synthetic = kprime.synthetic_gate()
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=p1.init_worker,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        archived_receipts = [receipt for _, receipt in pool.map(check_archive, [(key, archive[key]) for key in old])]
        print(f'G1 passed on {len(archived_receipts)} archive keys.', flush=True)
        rows, smoke_receipts, timings = zip(*pool.map(check_smoke, smoke), strict=True)
    with (OUT / 'smoke_rows.jsonl').open('x') as handle:
        fingerprints = {}
        for row, key in zip(rows, smoke, strict=True):
            validate_row(row, key, fingerprints)
            print(p1.canonical(row), file=handle)
    census, cost = summarize(rows, timings)
    usage = [resource.getrusage(kind) for kind in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    result = dict(**config, G1=dict(passed=True, records=archived_receipts),
                  G2=dict(passed=True, synthetic=synthetic, smoke=smoke_receipts),
                  G3=dict(passed=True, exact_nontiming_repeat_keys=smoke), K_prime_census=census, cost=cost,
                  receiver_core_hours_used=sum(u.ru_utime + u.ru_stime for u in usage) / 3600)
    p1.phase1.write_json(OUT / 'results.json', result)
    print(f'G2 and G3 passed on {len(rows)} smoke keys. Projection {cost["projected_core_hours"]:.3f} core-hours.',
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fresh-local', type=Path, required=True)
    parser.add_argument('--fresh-deinlab', type=Path, required=True)
    parser.add_argument('--base-commit', required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
