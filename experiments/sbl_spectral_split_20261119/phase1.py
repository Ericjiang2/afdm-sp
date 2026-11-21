"""Qualify the spectral split without evaluating any new arm on a main key."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import statistics
import sys

import numpy as np
import scipy

from spectral_receiver import NEW_ARMS, REFERENCE_ARMS, e3c, process_key, synthetic

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
E3 = EXPERIMENTS / 'tf_e3_sbl_20261017'
E3C = EXPERIMENTS / 'tf_e3c_shrink_20261018'
FREEZE = E3C / 'out/qualified_v3/FREEZE.json'
ARCHIVE = FREEZE.parent / 'main'
EXTENDED_ARMS = ('R1', 'S0', 'S-lo', 'S-hi')
PINNED = {
    E3 / 'CODE_MD5.txt': '11d3a2ba368f987bb5372baddd0ed302b2bf96e629d7fe4d1af943dc05f13347',
    E3C / 'CODE_MD5.txt': 'e1b3b47a7d7e2e43defd5721aea846c09ee8a15e5aa0f2e2ab3160db88ebdc02',
    FREEZE: '60cf81af6cb77957d04c332e88db6cf855b241642e027b87a676799863807160',
    ARCHIVE / 'REMOTE_ROWS_MD5.txt': '6dc8f63c3b7de8de58582ab4923f3435b9c521d2edd7ca9e52be23efd3a82092',
}
THREAD_ENV = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
COST_CAP = 30
COST_FACTOR = 1.3


class FrozenEvidenceError(RuntimeError):
    """Frozen source or archived row mismatch. Stop before advancing gates."""


def digest(path, algorithm):
    checksum = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def canonical(value):
    # Round-trip float serialization also distinguishes +0.0 from -0.0.
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':'))


def write_json(path, payload):
    with path.open('x') as handle:
        json.dump(payload, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write('\n')


def frozen_identity(ctx):
    for path, expected in PINNED.items():
        if digest(path, 'sha256') != expected:
            raise FrozenEvidenceError(f'Pinned manifest differs: {path}')
    for directory in (E3, E3C):
        for line in (directory / 'CODE_MD5.txt').read_text().splitlines():
            if line.strip() and not line.startswith('#'):
                expected, name = line.split()
                if digest(directory / name, 'md5') != expected:
                    raise FrozenEvidenceError(f'Frozen code differs: {directory / name}')
    expected = json.loads(FREEZE.read_text())['sources_sha256']
    identity = e3c.source_identity(ctx)
    if identity != expected:
        different = sorted(path for path in identity.keys() | expected.keys()
                           if identity.get(path) != expected.get(path))
        raise FrozenEvidenceError(f'Loaded E-3c source identity differs: {different}')
    return identity


def load_archive(gate_keys):
    """Verify all archived references and retain only the seeded parity keys."""
    expected_keys = set(e3c.lib.main_keys())
    seen = set()
    parity = {}
    shared_fields = ('stage1', 'round1', 'n_candidates_stage2', 'kept_delays_stage1', 'input_sha256', 'pairing')
    manifest = ARCHIVE / 'REMOTE_ROWS_MD5.txt'
    shards = [line.split() for line in manifest.read_text().splitlines() if line.strip()]
    if len(shards) != 24:
        raise FrozenEvidenceError('Expected the 24 E-3c row shards')
    for expected_digest, name in shards:
        path = ARCHIVE / name
        if digest(path, 'md5') != expected_digest:
            raise FrozenEvidenceError(f'E-3c archive shard differs: {name}')
        with gzip.open(path, 'rt') as handle:
            for line in handle:
                row = json.loads(line)
                key = e3c.lib.key_of(row)
                if key not in expected_keys or key in seen or row['status'] != 'ok':
                    raise FrozenEvidenceError(f'Unexpected, failed or duplicate archive key: {key}')
                seen.add(key)
                for arm in REFERENCE_ARMS.values():
                    score = row['variants'][arm]
                    sbl = score['sbl']
                    counts = [score['n_atoms'], score['n_pair'], sbl['n_final'], sbl['iterations']]
                    if (any(type(count) is not int or count < 0 for count in counts)
                            or len(score['pairs']) != score['n_pair'] or type(sbl['converged']) is not bool
                            or score['fer'] not in (0, 1) or not math.isfinite(score['nmse'])
                            or not math.isfinite(sbl['beta'])):
                        raise FrozenEvidenceError(f'Invalid required join fields: {key}/{arm}')
                if key in gate_keys:
                    parity[key] = {field: row[field] for field in shared_fields}
                    parity[key]['variants'] = {short: row['variants'][arm] for short, arm in REFERENCE_ARMS.items()}
    if seen != expected_keys:
        raise FrozenEvidenceError(f'E-3c archive missing {len(expected_keys - seen)} keys')
    return parity, dict(shards_verified=len(shards), paired_keys=len(seen),
                        reference_arm_rows=len(seen) * len(REFERENCE_ARMS),
                        manifest_sha256=PINNED[manifest], decision='join')


def check_parity(row, archive):
    arm_fields = ('atoms_ongrid', 'atoms', 'decoded_sha256', 'info_errors', 'nmse',
                  'sbl', 'n_atoms', 'n_pair', 'pairs', 'fer')
    shared = {field: canonical(row[field]) == canonical(value)
              for field, value in archive.items() if field != 'variants'}
    variants = {arm: {
        field: canonical(row['variants'][arm][field]) == canonical(archive['variants'][arm][field])
        for field in arm_fields} for arm in REFERENCE_ARMS}
    passed = all(shared.values()) and all(all(checks.values()) for checks in variants.values())
    return dict(key=row['key'], passed=passed, shared=shared, variants=variants)


def init_worker():
    global worker_ctx, worker_grid
    worker_ctx = e3c.p1ctx.load()
    worker_grid = e3c.sbl.full_grid(int(worker_ctx.system.l_max_cap))


def parity_worker(item):
    key, archive = item
    row = process_key(worker_ctx, e3c.e3d.PilotCache(), worker_grid, key, 'parity')
    return row, check_parity(row, archive)


def smoke_worker(key):
    first = process_key(worker_ctx, e3c.e3d.PilotCache(), worker_grid, key, 'smoke')
    second = process_key(worker_ctx, e3c.e3d.PilotCache(), worker_grid, key, 'smoke')
    deterministic = canonical(e3c.strip_timing(first)) == canonical(e3c.strip_timing(second))
    return first, second, dict(key=key, passed=deterministic)


def summarize_smoke(rows):
    by_budget = {}
    for budget in ('100', '400'):
        by_budget[budget] = {
            arm: {field: statistics.mean(row['budgets'][budget]['variants'][arm]['seconds'][field]
                                         for row in rows) for field in ('total', 'sbl')}
            for arm in (*REFERENCE_ARMS, *NEW_ARMS)}
    shared = statistics.mean(row['seconds']['total'] for row in rows)
    # At 100, joined R1 scoring costs zero. Its live SBL result is still a T0 dependency.
    per_key_100 = shared + by_budget['100']['R1']['sbl'] + sum(
        by_budget['100'][arm]['total'] for arm in NEW_ARMS)
    per_key_400 = shared + sum(by_budget['400'][arm]['total'] for arm in EXTENDED_ARMS)
    main_keys = e3c.lib.main_keys()
    options = []
    for last_frame in (4049, 4024):
        count_400 = sum(key[3] <= last_frame for key in main_keys)
        projected = COST_FACTOR * (len(main_keys) * per_key_100 + count_400 * per_key_400) / 3600
        options.append(dict(frames_400=[4000, last_frame], keys_400=count_400,
                            projected_core_hours=projected))
        if projected <= COST_CAP:
            break
    total = sum(row['census']['eigenvalues_total'] for row in rows)
    ambiguous = sum(row['census']['eigenvalues_in_025_075'] for row in rows)
    return dict(mean_arm_seconds=by_budget, mean_shared_seconds=shared,
                mean_schedule_seconds={'100': per_key_100, '400': per_key_400},
                cost=dict(passed=options[-1]['projected_core_hours'] <= COST_CAP, factor=COST_FACTOR,
                          suggested_cap_core_hours=COST_CAP, arms_100=NEW_ARMS, keys_100=len(main_keys),
                          arms_400=EXTENDED_ARMS, considered=options, selected=options[-1]),
                census=dict(smoke_keys=len(rows), eigenvalues_total=total, eigenvalues_in_025_075=ambiguous,
                            eigenvalue_share_in_025_075=ambiguous / total))


def run(out, workers):
    for name in THREAD_ENV:
        if os.environ.get(name) != '1':
            raise RuntimeError(f'{name}=1 must be set before Python starts')
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Phase 1 expects the deinlab Linux CPU environment')

    ctx = e3c.p1ctx.load()
    identity = frozen_identity(ctx)
    gate_keys = e3c.lib.gate_keys()
    smoke_keys = e3c.lib.smoke_keys()
    archive, join = load_archive(set(gate_keys))
    own_sources = {f.name: digest(f, 'sha256') for f in HERE.iterdir()
                   if f.suffix in ('.py', '.sh') or f.name == 'PROTOCOL.md'}
    provenance = dict(_argv=sys.argv, _config=dict(
        workers=workers, out=str(out), gate_keys=gate_keys, smoke_keys=smoke_keys,
        gate_seed=e3c.lib.SEED, budgets=[100, 400], reference=REFERENCE_ARMS, new_arms=NEW_ARMS,
        extended_arms=EXTENDED_ARMS, suggested_cap_core_hours=COST_CAP, cost_factor=COST_FACTOR,
        frozen_sources_sha256=identity, own_sources_sha256=own_sources,
        runtime=dict(host=platform.node(), python=platform.python_version(),
                     numpy=np.__version__, scipy=scipy.__version__,
                     environment={k: os.environ[k] for k in (*THREAD_ENV, 'CUDA_VISIBLE_DEVICES')}),
        hyper_sbl=e3c.sbl.HYPER, hyper_refine=e3c.ref.HYPER))
    write_json(out / 'config.json', provenance)
    evidence = synthetic()
    write_json(out / 'g2_synthetic.json', dict(passed=True, evidence=evidence))
    print('G2 synthetic passed', flush=True)

    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=init_worker) as pool:
        parity = []
        with (out / 'g1_rows.jsonl').open('x') as handle:
            for row, check in pool.map(parity_worker, ((key, archive[key]) for key in gate_keys)):
                handle.write(canonical(row) + '\n')
                parity.append(check)
                if not check['passed']:
                    write_json(out / 'g1.json', dict(passed=False, archive=join, checks=parity))
                    raise FrozenEvidenceError(f'G1 archived parity mismatch: {check}')
                print(f'G1 {len(parity)}/{len(gate_keys)} passed', flush=True)
        write_json(out / 'g1.json', dict(passed=True, archive=join, checks=parity))

        smoke_rows, g2, g3 = [], [], []
        with (out / 'smoke_rows.jsonl').open('x') as handle:
            for first, second, check in pool.map(smoke_worker, smoke_keys):
                handle.write(canonical(dict(first=first, second=second)) + '\n')
                smoke_rows.append(first)
                g2.append(dict(key=check['key'], budgets={budget: value['g2']
                                                        for budget, value in first['budgets'].items()}))
                g3.append(check)
                if not check['passed']:
                    write_json(out / 'g3.json', dict(passed=False, checks=g3))
                    raise AssertionError(f'G3 nondeterminism: {check["key"]}')
                print(f'G2/G3 smoke {len(g3)}/{len(smoke_keys)} passed', flush=True)
        write_json(out / 'g2_smoke.json', dict(passed=True, checks=g2))
        write_json(out / 'g3.json', dict(passed=True, checks=g3))

    summary = summarize_smoke(smoke_rows)
    write_json(out / 'phase1.json', dict(
        G1=dict(passed=True, keys=len(parity), reference_arms=len(REFERENCE_ARMS)),
        G2=dict(passed=True, synthetic=True, smoke_keys=len(g2), budgets=[100, 400]),
        G3=dict(passed=True, smoke_keys=len(g3), new_arms=len(NEW_ARMS), budgets=[100, 400]),
        join=join, **summary))
    if not summary['cost']['passed']:
        raise SystemExit('Projected main cost exceeds the 30 core-hour draft cap after subset reduction')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--workers', type=int, choices=range(1, 13), default=12)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.parent != HERE / 'out' or not out.is_dir():
        parser.error('--out must be a fresh attempt directory directly under the experiment out/')
    run(out, args.workers)
