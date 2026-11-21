"""Verified archive join and bounded execution of the frozen Phase 2 schedule."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
import json
import multiprocessing
import os
from pathlib import Path
import platform
import resource
import signal
import sys
import time

import numpy as np
import scipy

import phase1
from main_receiver import MAIN_ARMS, main_budgets, process_main_key

HERE = Path(__file__).resolve().parent
e3c = phase1.e3c
PHASE1_RECEIPTS = 'out/phase1_20261119_attempt02'
CAP_CORE_SECONDS = 30 * 3600
FROZEN_COMMIT = '2d4c660b251c461ad1630b8facc63ca3da3b2e50'
AUTHORIZATION_COMMIT = '15002fa034a33d1315d041f7b542eab45fb51a2f'
FROZEN_FILES = ('PROTOCOL.md', 'phase1.py', 'spectral_receiver.py')
MAIN_FILES = ('aggregate.py', 'launch_main.sh', 'main_receiver.py', 'run_main.py', 'test_aggregate.py')


def verify_freeze(producing_commit):
    if platform.system() != 'Linux' or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise RuntimeError('Expected the deinlab Linux CPU environment')
    if any(os.environ.get(name) != '1' for name in phase1.THREAD_ENV):
        raise RuntimeError('All numerical thread limits must be 1 before Python startup')
    freeze_path = HERE / 'FREEZE.json'
    freeze = json.loads(freeze_path.read_text())
    if not (freeze['git_commit'] == FROZEN_COMMIT
            and freeze['authorization_commit'] == AUTHORIZATION_COMMIT
            and freeze['producing_commit'] == producing_commit):
        raise phase1.FrozenEvidenceError('Freeze commit, authorization or producing commit differs')
    if set(freeze['sources_sha256']) != set(FROZEN_FILES + MAIN_FILES):
        raise phase1.FrozenEvidenceError('Freeze source inventory is incomplete')
    for name, expected in (freeze['sources_sha256'] | freeze['phase1_receipts_sha256']).items():
        if phase1.digest(HERE / name, 'sha256') != expected:
            raise phase1.FrozenEvidenceError(f'Frozen hash differs: {name}')
    qualified = json.loads((HERE / PHASE1_RECEIPTS / 'phase1.json').read_text())
    if not all(qualified[gate]['passed'] for gate in ('G1', 'G2', 'G3')):
        raise phase1.FrozenEvidenceError('Required Phase 1 gates did not pass')
    phase1_config = json.loads((HERE / PHASE1_RECEIPTS / 'config.json').read_text())['_config']
    for name in FROZEN_FILES:
        if freeze['sources_sha256'][name] != phase1_config['own_sources_sha256'][name]:
            raise phase1.FrozenEvidenceError(f'Source differs from the qualified receiver: {name}')
    identity = phase1.frozen_identity(e3c.p1ctx.load())
    if identity != freeze['frozen_e3c_sources_sha256']:
        raise phase1.FrozenEvidenceError('Loaded E-3c source identity differs from Phase 2 freeze')
    return dict(passed=True, freeze=freeze, freeze_sha256=phase1.digest(freeze_path, 'sha256'),
                verification_host=platform.node())


def score_fields(score):
    return {name: score[name] for name in (
        'fer', 'info_errors', 'decoded_sha256', 'nmse', 'sbl', 'n_atoms', 'n_pair', 'pairs',
        'atoms', 'atoms_ongrid', 'sbl_gain_sha256')}


def init_worker():
    global ctx, grid
    ctx = e3c.p1ctx.load()
    grid = e3c.sbl.full_grid(int(ctx.system.l_max_cap))


def run_key(item):
    key, reference, config_sha = item
    row = process_main_key(ctx, e3c.e3d.PilotCache(), grid, key)
    for name, expected in reference.items():
        if name != 'variants' and phase1.canonical(row[name]) != phase1.canonical(expected):
            raise phase1.FrozenEvidenceError(f'{key}: archive pairing mismatch in {name}')
    if tuple(row['budgets']) != tuple(map(str, main_budgets(key))):
        raise RuntimeError(f'{key}: computed budgets differ from the frozen schedule')
    for budget, value in row['budgets'].items():
        if set(value['variants']) != set(MAIN_ARMS[int(budget)]):
            raise RuntimeError(f'{key}: computed arms differ from the frozen schedule')
    primary = row['budgets']['100']['variants']
    archived_r1 = reference['variants']['R1']
    for name in ('atoms_ongrid', 'sbl', 'sbl_gain_sha256'):
        if phase1.canonical(primary['T0'][name]) != phase1.canonical(archived_r1[name]):
            raise phase1.FrozenEvidenceError(f'{key}: T0 live R1 SBL differs from archive in {name}')
    for arm, reference_score in reference['variants'].items():
        score = score_fields(reference_score)
        extra = reference_score['regularization']['extra_ridge']
        if extra != (row['sum_v'] if arm == 'R2' else 0.):
            raise phase1.FrozenEvidenceError(f'{key}: {arm} archive ridge differs')
        primary[arm] = dict(score, census=row['census'], provenance='verified E-3c row',
                            added_trace_sbl=extra * row['n_candidates_stage2'],
                            added_trace_refinement=extra * score['n_atoms'])
    budget_seconds = {budget: value['seconds'] for budget, value in row['budgets'].items()}
    row.update(budget_seconds=budget_seconds, status='ok', config_sha256=config_sha,
               budgets={budget: value['variants'] for budget, value in row['budgets'].items()})
    return row


def cpu_seconds():
    usage = [resource.getrusage(which) for which in (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)]
    return sum(value.ru_utime + value.ru_stime for value in usage)


def run(args, verified):
    import aggregate

    out = args.out.resolve()
    started = time.monotonic()
    charged_from = cpu_seconds()
    completed = 0
    try:
        keys = e3c.lib.main_keys()
        archive, archive_receipt = phase1.load_archive(set(keys))
        phase1.write_json(out / 'config.json', dict(_argv=sys.argv, _config=dict(
            workers=args.workers, archive=archive_receipt, verification=verified,
            core_hour_cap=30, wall_seconds=args.wall_seconds, kill_grace_seconds=10,
            extended_frames=[4000, 4049], keys=keys, live_arms=MAIN_ARMS,
            runtime=dict(host=platform.node(), python=platform.python_version(),
                         numpy=np.__version__, scipy=scipy.__version__,
                         environment={k: os.environ[k] for k in (*phase1.THREAD_ENV, 'CUDA_VISIBLE_DEVICES')}),
            hyper_sbl=e3c.sbl.HYPER, hyper_refine=e3c.ref.HYPER)))
        config_sha = phase1.digest(out / 'config.json', 'sha256')
        paths = [out / f'rows_shard{index:03d}.jsonl' for index in range(args.workers)]
        with ExitStack() as stack:
            files = [stack.enter_context(path.open('x', buffering=1)) for path in paths]
            pool = ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker,
                                       mp_context=multiprocessing.get_context('spawn'))
            try:
                jobs = ((key, archive[key], config_sha) for key in keys)
                for index, row in enumerate(pool.map(run_key, jobs)):
                    files[index % args.workers].write(phase1.canonical(row) + '\n')
                    completed = index + 1
                    if completed % 100 == 0:
                        print(f'{completed}/{len(keys)} keys recorded', flush=True)
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
        if completed != len(keys):
            raise RuntimeError(f'Incomplete receiver run: {completed}/{len(keys)}')
        with (out / 'REMOTE_ROWS_MD5.txt').open('x') as handle:
            for path in paths:
                handle.write(f"{phase1.digest(path, 'md5')}  {path.name}\n")
        phase1.write_json(out / 'receiver_receipt.json', dict(
            completed_keys=completed, extended_keys=sum(400 in main_budgets(key) for key in keys),
            config_sha256=config_sha, receiver_wall_seconds=time.monotonic() - started,
            receiver_core_hours=(cpu_seconds() - charged_from) / 3600))
        aggregate.main(['--out', str(out)])
    finally:
        phase1.write_json(out / 'budget.json', dict(
            core_hours_used=cpu_seconds() / 3600, core_hour_cap=30, completed_keys=completed,
            wall_seconds=time.monotonic() - started,
            hard_wall_seconds=args.wall_seconds, maximum_compute_processes=args.workers + 1,
            accounting='Linux user plus system CPU seconds across the coordinator and reaped children'))


def timeout(signum, frame):
    raise TimeoutError('The 30 core-hour execution envelope expired')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--producing-commit', required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--workers', type=int, choices=range(1, 13), default=12)
    parser.add_argument('--wall-seconds', type=int, default=8250)
    args = parser.parse_args()
    if args.verify_only:
        print(json.dumps(verify_freeze(args.producing_commit), sort_keys=True, allow_nan=False))
    else:
        if args.out is None or args.out.resolve().parent != HERE / 'out' or not args.out.is_dir():
            parser.error('use a freshly created attempt in the experiment out/ directory')
        if args.wall_seconds <= 0 or (args.workers + 1) * (args.wall_seconds + 10) > CAP_CORE_SECONDS:
            parser.error('wall-time envelope must bound all compute processes to 30 core-hours')
        signal.signal(signal.SIGTERM, timeout)
        verified = verify_freeze(args.producing_commit)
        run(args, verified)
