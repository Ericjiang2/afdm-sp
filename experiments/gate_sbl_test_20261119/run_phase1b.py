"""Replay only the Phase 1 SBL smoke keys, then publish the audited schedule."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import platform
import re
from statistics import mean
import sys

import numpy as np
import scipy

from aggregate_main import s_penalty_summary, x_gate_exposure
from audit_fresh import S_EXTENSION, verify
from main_schedule import choose
from run_phase1 import THREADS
import s_arm
import s_gates

HERE = Path(__file__).resolve().parent
PHASE1 = HERE / 'out/phase1_v4_20261119'
PHASE1_SHA256 = {
    'results.json': '760726734a3a7d7aa9835d07818055e1e6705c6fd13e2498a081bde2653a11f2',
    'sbl_g4.json': '48086ea196b1ca8cdbf8a84ed625ef19d7864e9f08e97055e6b8b493eb66cb8e',
    'sbl_smoke_rows.jsonl': '3843c1238ba1a0751d59e15521dbc4657777e961a86c2d3cb66f3150b5b3bcab',
}
X_G5_SHA256 = '34caabc7d0386c06a9fbb1d7d8afeb6f0c740caa64a836f6b2e8504351ed9c2e'


def audit_extensions(local, remote):
    reports = {}
    for scope, path in (('local', local), ('deinlab', remote)):
        raw = path.read_bytes()
        doc = json.loads(raw)
        s = doc['S']
        if (doc['scope'] != scope or s['interval_inclusive'] != list(S_EXTENSION)
                or (s['domain'], s['entropy_prefix']) != ('TCRF', '2261fde33dab09d1')
                or doc['status'] != s['status']
                or (s['status'] == 'PASS') != (not doc['unresolved'] and not s['overlaps'])):
            raise ValueError(f'Invalid S extension audit from {scope}')
        reports[scope] = dict(status=s['status'], sha256=sha256(raw).hexdigest())
    return reports


def reference_smoke():
    for filename, digest in PHASE1_SHA256.items():
        verify(PHASE1 / filename, digest)
    results = json.loads((PHASE1 / 'results.json').read_text())
    if any(v['S_base'] != 'PASS' or v['X'] != 'PASS' for v in results['audits'].values()):
        raise s_gates.FrozenEvidenceError('Phase 1 fallback and X audits must both have passed')
    g4 = json.loads((PHASE1 / 'sbl_g4.json').read_text())
    expected = {tuple(row['key']): row['sha256'] for row in g4['receipts']}
    if (not g4['passed'] or g4['keys'] != 12 or len(expected) != 12
            or sorted(k[3] for k in expected) != list(range(8400, 8412))):
        raise s_gates.FrozenEvidenceError('Phase 1 G4 lacks the 12 registered smoke keys')
    stable_rows, counts = {}, Counter()
    for line in (PHASE1 / 'sbl_smoke_rows.jsonl').read_text().splitlines():
        row = json.loads(line)
        key = tuple(row['key'])
        stable = s_gates.stable(row)
        if key not in expected or s_gates.fingerprint(stable) != expected[key]:
            raise s_gates.FrozenEvidenceError(f'Phase 1 smoke digest mismatch at {key}')
        stable_rows[key] = stable
        counts[key] += 1
    if set(counts) != set(expected) or set(counts.values()) != {2}:
        raise s_gates.FrozenEvidenceError('Phase 1 smoke archive does not contain two rows per key')
    return results, stable_rows


def smoke_key(key, *, source_identity):
    if key[3] not in range(8400, 8412):
        raise ValueError(f'Phase 1b disallowed key {key}')
    ctx, _, _, _, _, grid, _ = s_gates.context(source_identity)
    return s_arm.run_key(ctx, grid, key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--fresh-local', type=Path, required=True)
    parser.add_argument('--fresh-deinlab', type=Path, required=True)
    parser.add_argument('--base-commit', required=True)
    parser.add_argument('--model', choices=['gpt-6.2-sol'], required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.parent != HERE / 'out' or not out.name.startswith('phase1b_'):
        raise ValueError('Expected a new Phase 1b output directory')
    if platform.system() != 'Linux' or not re.fullmatch(r'[a-f0-9]{40}', args.base_commit):
        raise ValueError('Phase 1b requires deinlab Linux and a full base commit')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '' or any(os.environ.get(v) != '1' for v in THREADS):
        raise ValueError('Phase 1b requires CPU-only single-thread processes')

    audits = audit_extensions(args.fresh_local, args.fresh_deinlab)
    prior, expected = reference_smoke()
    source_identity = tuple(sorted(prior['s_archive']['source_identity'].items()))
    workers = 6
    config = dict(_argv=sys.argv, _config=dict(
        phase='1b', model=args.model, base_commit=args.base_commit, workers=workers,
        threads_per_process=1, extension_audits=audits, phase1_sha256=PHASE1_SHA256,
        numpy=np.__version__, scipy=scipy.__version__, python=sys.version,
        source_sha256={p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))}))
    s_gates.write_json(out, 'config.json', config)

    keys = sorted(expected)
    print('Phase 1b: replay the 12 registered SBL smoke keys', flush=True)
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        rows = list(pool.map(partial(smoke_key, source_identity=source_identity), keys))
    identity = []
    for key, row in zip(keys, rows, strict=True):
        stable = s_gates.stable(row)
        stable.pop('slo_retained_penalty_fro')
        if s_gates.canonical(stable) != s_gates.canonical(expected[key]):
            changed = sorted(k for k in (stable.keys() | expected[key].keys())
                             if s_gates.canonical(stable.get(k)) != s_gates.canonical(expected[key].get(k)))
            raise AssertionError(f'Phase 1b smoke parity mismatch at {key}: {changed}')
        identity.append(dict(key=key, canonical_phase1_sha256=s_gates.fingerprint(stable),
                             slo_retained_penalty_fro=row['slo_retained_penalty_fro'],
                             cpu_seconds=row['seconds']['cpu_total']))
    with (out / 'sbl_smoke_rows.jsonl').open('x') as handle:
        for row in rows:
            print(s_gates.canonical(row), file=handle)
    summary = s_penalty_summary(rows)
    schedule, cost = choose(
        mean(entry['cpu_seconds'] for entry in identity),
        prior['cost']['x_measurement']['projected_cpu_seconds_per_frame'],
        extension_passed=all(audit['status'] == 'PASS' for audit in audits.values()),
    )
    # G5 samples are archived Phase 1 rows. Exercise the new aggregation
    # directly against the checksummed receipt without invoking the X receiver.
    x_g5 = PHASE1 / 'x_g5.json'
    verify(x_g5, X_G5_SHA256)
    x_archived = x_gate_exposure(json.loads(x_g5.read_text())['samples'])
    s_gates.write_json(out, 'main_schedule.json', schedule)
    s_gates.write_json(out, 'results.json', dict(
        **config, retained_penalty=summary, byte_identical_smoke_rows=len(identity),
        smoke=identity, archived_x_exposure=x_archived, x_gate_receipt_sha256=X_G5_SHA256,
        main_schedule=schedule, projected_cost=cost))
    print(f'Byte-identical smoke rows: {len(identity)}. Selected main projection: '
          f'{cost["selected_total_core_hours"]:.4f} core-hours.', flush=True)


if __name__ == '__main__':
    main()
