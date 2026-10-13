"""I-02 legal cancellation-statistics arms. Truth is evaluation-only."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import traceback

for _key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_eval import build_receiver
from .direction_cancel_receiver import CancellationTransform
from .direction_receiver import CHECKPOINT_HASH
from .direction_run import json_value
from .supplement_development_analysis import analyze_development, development_table
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_data import CAMPAIGN_ID, LIMITS, SupplementData, campaign_rng
from .supplement_h01 import RECIPE_ID as BSTAR
from .supplement_profile import score_errors
from .supplement_run import sha, sources

STAGE = 'I-02'
RECIPE_ID = BSTAR
SPLIT = 'design'
SNRS = (7, 8, 9)
N_BLOCKS = LIMITS['design']
ARMS = (
    dict(id='I02-baseline', mode=None),
    dict(id='I02-scalar', mode='scalar'),
    dict(id='I02-diagonal', mode='diagonal'),
    dict(id='I02-lowrank', mode='lowrank'),
)
ARM_IDS = tuple(a['id'] for a in ARMS)
TOTAL_F = N_BLOCKS * len(SNRS) * len(ARMS)
LEDGER_NAME = 'supplement-i02-design-ledger'
FAILURE_RESERVE_BYTES = 256 * 1024
PER_FULL_ESTIMATE_BYTES = 8 * 1024 ** 2
GPU_FRACTION = .30
N_BATCHES = 12
FORBIDDEN_CLAIMS = (
    'F_I confirmation',
    'deployable cancellation',
    'truth entered legal transform',
    'rerun 16T',
)


def transform_for(system, arm):
    if arm['mode'] is None:
        return None
    return CancellationTransform(system, arm['mode'])


def _identities(start, stop, snrs):
    if (not isinstance(snrs, list) or not snrs or any(s not in SNRS for s in snrs) or
            len(set(snrs)) != len(snrs)):
        raise ValueError('I-02 snrs must be a unique subset of 7/8/9')
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= N_BLOCKS:
        raise ValueError('I-02 blocks must lie in design[0,192)')
    return {(block, int(snr), arm) for block in range(start, stop)
            for snr in snrs for arm in ARM_IDS}


def validate_args(args):
    if args.split != SPLIT:
        raise ValueError('I-02 uses only the design split')
    snrs = [int(s) for s in args.snrs]
    identities = _identities(args.start, args.stop, snrs)
    n_full = len(identities)
    if args.max_full_calls != n_full:
        raise ValueError('I-02 F reservation must equal block×SNR×4 arms')
    if type(args.deadline_unix) is not int or args.deadline_unix <= int(time.time()):
        raise ValueError('future integer unix deadline required')
    estimated = n_full * PER_FULL_ESTIMATE_BYTES + 32 * 1024 ** 2
    if args.max_output_bytes < estimated:
        raise ValueError('output budget below I-02 estimate')
    if recipe_by_id(RECIPE_ID)['id'] != RECIPE_ID:
        raise ValueError('I-02 recipe identity drifted')
    return dict(snrs=snrs, identities=identities, n_full=n_full, estimated=estimated)


def reserve_i02(out, contract):
    ledger = out.parent / LEDGER_NAME
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        requested = _identities(contract['start'], contract['stop'], list(contract['snrs']))
        if contract['max_full_calls'] != len(requested):
            raise ValueError('invalid I-02 identity reservation')
        used = 0
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if row.get('campaign_id') != CAMPAIGN_ID or row.get('stage') != STAGE:
                raise ValueError('invalid shared I-02 reservation')
            prior = {tuple(item) for item in row['identities']}
            if requested & prior:
                raise ValueError('I-02 block/snr/arm already reserved')
            used += row['max_full_calls']
        if used + len(requested) > TOTAL_F:
            raise ValueError('cumulative I-02 2304F cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, out=str(out.resolve()),
            max_full_calls=len(requested), identities=sorted(requested),
            calls_reserved={'F': len(requested), 'T': 0, 'E': 0},
            policy='all four arms per reserved design identity; no retry'))
    return str(ledger)


def output_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())




def development_contrasts(table, blocks, *, manifest):
    return analyze_development('I-02', table, ('BP', 'BP80'), blocks, manifest)


def _read_batch(batch):
    batch = Path(batch)
    if (batch / 'batch-failure.json').exists():
        raise ValueError('failed I-02 batch present')
    summary = json.loads((batch / 'summary.json').read_text())
    contract = json.loads((batch / 'contract.json').read_text())
    if (summary.get('status') != 'complete' or summary.get('exitcode') != 0 or
            summary.get('failures')):
        raise ValueError('incomplete or failed I-02 batch')
    if (contract.get('recipe_id') != RECIPE_ID or
            list(contract.get('arms', [])) != list(ARM_IDS) or
            contract.get('split') != SPLIT):
        raise ValueError('I-02 batch binding mismatch')
    if summary['calls_completed'] != summary['calls_attempted']:
        raise ValueError('I-02 attempted/completed mismatch')
    cells = {}
    for path in batch.glob('frame-*.json'):
        row = json.loads(path.read_text())
        if (row.get('candidate_eligible') or row.get('deployable') or
                row.get('FER') not in (0, 1) or row.get('arm_id') not in ARM_IDS or
                row.get('truth_access_level') != 'none'):
            raise ValueError('invalid I-02 frame contract')
        key = (int(row['SNR']), row['arm_id'], int(row['block_id']))
        if key in cells:
            raise ValueError('duplicate I-02 frame')
        cells[key] = int(row['FER'])
    return dict(F=summary['calls_completed'], cells=cells)


def harvest_run(run_root, *, contrast_manifest):
    """Read completed I-02 batches. Not F_I confirmation."""
    root = Path(run_root)
    batches = sorted(p for p in root.glob('batch-*') if p.is_dir())
    if len(batches) != N_BATCHES:
        raise ValueError('I-02 harvest requires 12 complete batches')
    totals = {'F': 0}
    cells = {}
    for batch in batches:
        row = _read_batch(batch)
        totals['F'] += row['F']
        overlap = cells.keys() & row['cells'].keys()
        if overlap:
            raise ValueError('overlapping I-02 frame identities')
        cells.update(row['cells'])
    if totals['F'] != TOTAL_F:
        raise ValueError('I-02 harvest totals are not 2304F')
    blocks = list(range(N_BLOCKS))
    table = development_table('I-02', cells, ('BP', 'BP80'), blocks)
    fer = {snr: {arm: float(sum(table[(snr, arm)]) / len(blocks))
                 for arm in ARM_IDS}
           for snr in SNRS}
    return dict(
        schema='supplement-i02-harvest-v2',
        status='complete_development_not_confirmation',
        calls=totals, n_blocks=N_BLOCKS, snrs=list(SNRS), arms=list(ARM_IDS),
        recipe_id=RECIPE_ID, fer_by_cell=fer,
        contrasts=development_contrasts(table, blocks, manifest=contrast_manifest),
        not_claims=list(FORBIDDEN_CLAIMS), rerun_16T=False,
        scope='I-02 design development; truth evaluation-only; not F_I confirmation')


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = completed = 0
    failures = []
    records = []
    active = None
    started, cpu0 = time.perf_counter(), time.process_time()
    command = [sys.executable, *sys.argv]

    def publish(path, value):
        size = len(json.dumps(value, sort_keys=True, allow_nan=False).encode())
        if output_bytes(args.out) + size > args.max_output_bytes - FAILURE_RESERVE_BYTES:
            raise OSError('output publication would exceed frozen storage budget')
        publish_json(path, value)

    try:
        parsed = validate_args(args)
        if sha(args.checkpoint) != CHECKPOINT_HASH:
            raise ValueError('checkpoint mismatch')
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda') or (
                device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable')
        if device.type == 'cuda':
            index = 0 if device.index is None else device.index
            torch.cuda.set_per_process_memory_fraction(GPU_FRACTION, index)

        def timeout(_s, _f):
            raise TimeoutError('I-02 batch deadline')

        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        transforms = {arm['id']: transform_for(system, arm) for arm in ARMS}
        contract = dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, split=SPLIT,
            start=args.start, stop=args.stop, snrs=parsed['snrs'],
            recipe_id=RECIPE_ID, arms=list(ARM_IDS),
            device=str(device), gpu_allocator_fraction=GPU_FRACTION,
            max_full_calls=args.max_full_calls,
            calls_reserved={'F': args.max_full_calls, 'T': 0, 'E': 0},
            source_sha256=sources(), checkpoint_sha256=sha(args.checkpoint),
            protocol_sha256=sha(args.protocol), deadline_unix=args.deadline_unix,
            max_output_bytes=args.max_output_bytes, command=command,
            policy='share GPU; four cancellation arms; truth evaluation-only')
        contract['config_sha256'] = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_i02(args.out, contract)
        publish(args.out / 'contract.json', contract)
        model = build_receiver(args.checkpoint, system, 1024, args.device,
                               receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, RECIPE_ID, system=system)

        def fail(exc, identity):
            item = dict(status='failed', identity=identity, exception=type(exc).__name__,
                        message=str(exc), traceback=traceback.format_exc(), FER=None)
            path = args.out / f'failure-{len(failures):05d}.json'
            publish(path, item)
            failures.append(dict(path=str(path), sha256=sha(path), identity=identity))

        for block in range(args.start, args.stop):
            for snr in parsed['snrs']:
                try:
                    frame = data.make_frame(system, SPLIT, block, snr)
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    for arm in ARM_IDS:
                        fail(exc, dict(block=block, snr=snr, arm_id=arm, full_call_started=False))
                    continue
                order = list(ARMS)
                campaign_rng(SPLIT, block, 'order').shuffle(order)
                for arm in order:
                    if attempted >= args.max_full_calls or time.time() >= args.deadline_unix:
                        raise TimeoutError('I-02 budget/deadline exhausted')
                    attempted += 1
                    active = dict(block=block, snr=snr, arm_id=arm['id'],
                                  full_call_started=True, started_unix=time.time())
                    publish(args.out / f'call-F-{attempted:05d}-started.json', active)
                    try:
                        result = receiver.run(frame.observed, audit=True,
                                              terminal_transform=transforms[arm['id']])
                        if arm['mode'] is None and 'cancellation_transform' in result:
                            raise AssertionError('baseline arm must not apply a transform')
                        if arm['mode'] is not None:
                            if 'cancellation_transform' not in result:
                                raise AssertionError('transformed arm missing cancellation record')
                            diag = result['cancellation_transform']['diagnostics']
                            if diag.get('truth_access') != 'none':
                                raise AssertionError('truth entered legal cancellation transform')
                        scores = score_errors(result, frame._truth)
                        row = dict(schema='supplement-i02-frame-v1', split=SPLIT,
                                   block_id=block, SNR=snr, arm_id=arm['id'], mode=arm['mode'],
                                   recipe_id=RECIPE_ID, truth_access_level='none',
                                   candidate_eligible=False, deployable=False,
                                   cancellation=None if arm['mode'] is None else json_value(
                                       result['cancellation_transform']['diagnostics']),
                                   **scores)
                        publish(args.out / f'frame-{snr}-{block:03d}-{arm["id"]}.json', json_value(row))
                        completed += 1
                        records.append(dict(block=block, snr=snr, arm_id=arm['id'], FER=row['FER']))
                    except (TimeoutError, KeyboardInterrupt):
                        raise
                    except Exception as exc:
                        fail(exc, active)
                        continue
                    active = None
        signal.setitimer(signal.ITIMER_REAL, 0)
        status = 'completed_with_failures' if failures else 'complete'
        publish(args.out / 'summary.json', dict(
            status=status, exitcode=1 if failures else 0,
            calls_attempted=attempted, calls_completed=completed,
            records=records, failures=failures, command=command,
            recipe_id=RECIPE_ID, arms=list(ARM_IDS),
            gpu_allocator_fraction=GPU_FRACTION,
            scope='I-02 development; not confirmation'))
        return 1 if failures else 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out / 'batch-failure.json', dict(
            status='failed', exception=type(exc).__name__, message=str(exc)[:16384],
            traceback=traceback.format_exc()[-32768:],
            calls_attempted=attempted, calls_completed=completed, active_attempt=active))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol', 'checkpoint', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--split', required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--stop', type=int, required=True)
    p.add_argument('--snrs', type=json.loads, required=True)
    p.add_argument('--deadline-unix', type=int, required=True)
    p.add_argument('--max-full-calls', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    p.add_argument('--device', required=True)
    return execute(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
