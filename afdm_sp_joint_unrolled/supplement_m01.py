"""M-01 common-I structure arms. Geometry oracle only; not deployable."""
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

import numpy as np
import torch

from .afdm_baselines import construct_sensing_matrix
from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash, physical_cluster_weights
from .budgeted_support_eval import build_receiver
from .direction_factorial import residual_ledger
from .direction_logging import publish_snapshot
from .direction_receiver import CHECKPOINT_HASH, terminal_decode
from .direction_run import json_value
from .supplement_development_analysis import analyze_development, development_table
from .direction_structure import fit
from .direction_structure_replay import ARMS
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .representation_ledger import merged_truth_ledger
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_data import CAMPAIGN_ID, LIMITS, SupplementData, campaign_rng
from .supplement_detectors import terminal as catalog_terminal
from .supplement_h01 import FROZEN_D1_SHA256, RECIPE_ID as BSTAR, detectors_from_d1, load_d1_freeze
from .supplement_profile import score_errors
from .supplement_run import sha, sources

STAGE = 'M-01'
RECIPE_ID = BSTAR
SPLIT = 'mechanism'
SNRS = (7, 8, 9)
N_BLOCKS = LIMITS['mechanism']
TOTAL_F = N_BLOCKS * len(SNRS)
TOTAL_E = 4 * TOTAL_F
TOTAL_T = 8 * TOTAL_F
LEDGER_NAME = 'supplement-m01-mechanism-ledger'
FAILURE_RESERVE_BYTES = 256 * 1024
PER_FULL_ESTIMATE_BYTES = 40 * 1024 ** 2
GPU_FRACTION = .35
FORBIDDEN_CLAIMS = (
    'deployable structure',
    'F_M confirmation',
    'optimal detector',
    'sham as competing baseline',
    'rerun 16T',
)


def require_support(snapshot):
    support = snapshot.get('support')
    if support is None:
        raise ValueError('M-01 requires B_star support in the snapshot; H-01 v2 snapshots omit it')
    ids = np.asarray(support)
    if ids.ndim != 1 or ids.dtype.kind not in 'iu' or len(ids) != len(set(ids.tolist())):
        raise ValueError('invalid B_star support identity')
    return ids.astype(int)


def snapshot_from_result(frame, result):
    obs, truth = frame.observed, frame._truth
    snap = dict(
        Hhat=np.array(result['H'], copy=True),
        Htrue=np.array(truth['H'], copy=True),
        y=np.array(obs['y'], copy=True),
        pilot=np.array(obs['pilot'], copy=True),
        data=np.array(truth['data'], copy=True),
        noise=np.array(truth['noise'], copy=True),
        sigma2_thermal=np.asarray(obs['sigma2']),
        sigma2_terminal=np.asarray(result['sigma2_terminal']),
        constellation=np.array(obs['constellation'], copy=True),
        info=np.array(truth['info'], copy=True),
        coded=np.array(truth['coded'], copy=True),
        decoded=np.array(result['decoded'], copy=True),
        support=np.asarray(result['support'], dtype=np.int64),
        gains=np.asarray(result['gains']))
    require_support(snap)
    residual_ledger(snap, snap['Hhat'], snap['Hhat'])
    return snap


def prepare_from_frame(frame, snapshot, system):
    support = require_support(snapshot)
    params = frame._truth['params']
    truth = merged_truth_ledger(params, system.k_max_cap, threshold=0.)
    true_ids = {e['column'] for e in truth['entries']
                if e['above_threshold'] and e['column'] is not None
                and 0 <= e['delay'] <= system.l_max_cap}
    I = np.asarray(sorted(set(support.tolist()) & true_ids), dtype=int)
    geometry = {k: params[k] for k in ('taps', 'l_i', 'k_real')}
    n = len(snapshot['y'])
    if len(I):
        basis = physical_cluster_weights(system, geometry)[I, :]
        Phi = construct_sensing_matrix(system.N_total, snapshot['pilot'], system.c1, system.c2,
                                       system.l_max_cap, system.k_max_cap)[:, I]
    else:
        basis = np.zeros((0, 1), complex)
        Phi = np.zeros((n, 0), complex)
    return dict(snapshot=snapshot, I=I, basis=basis, Phi_I=Phi, geometry=geometry,
                truth_support=sorted(true_ids), pairing_verified=True,
                input_hashes=frame.metadata['input_hashes'])


def fit_arm(prepared, system, arm):
    if arm not in ARMS:
        raise ValueError('unknown M-01 arm')
    s = prepared['snapshot']
    I = prepared['I']
    kwargs = {'sigma_terminal': float(s['sigma2_terminal'])}
    if arm == 'group':
        kwargs['incidence'] = (np.abs(prepared['basis']) > 0) if len(I) else np.zeros((0, 1), bool)
    if arm in ('link', 'sham'):
        kwargs['basis'] = prepared['basis']
    fitted = fit(s['y'], prepared['Phi_I'], I, arm, **kwargs)
    if fitted['atom_ids'] != I.tolist():
        raise AssertionError('fit changed shared support')
    n = len(s['y'])
    if len(I) == 0:
        H = np.zeros((n, n), complex)
    else:
        K = 2 * system.k_max_cap + 1
        H = system.gen_h_daft(fitted['coefficients'], I // K, I % K - system.k_max_cap)
    z = s['y'] - H @ s['pilot']
    residual = residual_ledger(s, H, H)
    return dict(fitted=fitted, H=H, z=z, residual=residual)


def detect_arm(prepared, fitted, code, arm, detector, *, device, before_call):
    if detector == 'EP10':
        raise ValueError('M-01 must not use EP10')
    s = prepared['snapshot']
    before_call('terminal', arm, detector)
    H, z = fitted['H'], fitted['z']
    if detector == 'BP':
        result = terminal_decode(z, H, float(s['sigma2_terminal']),
                                 s['constellation'].copy(), code, device=device, audit=True)
        hard = result['x_hard']
    else:
        result = catalog_terminal(z, H, float(s['sigma2_terminal']),
                                  s['constellation'].copy(), code, detector, device=str(device))
        hard = result['x_hard']
    result.update(arm_id=f'M_{arm}', detector=detector, atom_ids=prepared['I'].tolist(),
                  coefficients=fitted['fitted']['coefficients'], Hfit=H,
                  residual=fitted['residual'], candidate_eligible=False, deployable=False,
                  truth_access_level='geometry_oracle',
                  oracle_information=('support+template' if arm in ('link', 'sham')
                                      else 'support+incidence' if arm == 'group' else 'support'),
                  hard=hard)
    result['info_errors'] = int(np.count_nonzero(result['info_hat'] != s['info']))
    result['FER'] = int(result['info_errors'] > 0)
    return result


def run_arm(prepared, system, code, arm, detector, *, device, before_call):
    before_call('CE', arm, detector)
    fitted = fit_arm(prepared, system, arm)
    return detect_arm(prepared, fitted, code, arm, detector, device=device, before_call=before_call)


def _identities(start, stop, snrs):
    if (not isinstance(snrs, list) or not snrs or any(s not in SNRS for s in snrs) or
            len(set(snrs)) != len(snrs)):
        raise ValueError('M-01 snrs must be a unique subset of 7/8/9')
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= N_BLOCKS:
        raise ValueError('M-01 blocks must lie in mechanism[0,256)')
    return {(block, int(snr)) for block in range(start, stop) for snr in snrs}


def validate_args(args):
    if args.split != SPLIT:
        raise ValueError('M-01 uses only the mechanism split')
    snrs = [int(s) for s in args.snrs]
    identities = _identities(args.start, args.stop, snrs)
    n_full = len(identities)
    n_ce = 4 * n_full
    n_terminal = 8 * n_full
    if (args.max_full_calls != n_full or args.max_ce_calls != n_ce or
            args.max_terminal_calls != n_terminal):
        raise ValueError('M-01 F/E/T reservation must equal requested identities')
    if type(args.deadline_unix) is not int or args.deadline_unix <= int(time.time()):
        raise ValueError('future integer unix deadline required')
    estimated = n_full * PER_FULL_ESTIMATE_BYTES + 32 * 1024 ** 2
    if args.max_output_bytes < estimated:
        raise ValueError('output budget below M-01 snapshot estimate')
    load_d1_freeze(args.d1, args.d1_sha256)
    if recipe_by_id(RECIPE_ID)['id'] != RECIPE_ID:
        raise ValueError('M-01 recipe identity drifted')
    return dict(snrs=snrs, identities=identities, n_full=n_full, n_ce=n_ce,
                n_terminal=n_terminal, estimated=estimated)


def reserve_m01(out, contract):
    ledger = out.parent / LEDGER_NAME
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        requested = _identities(contract['start'], contract['stop'], list(contract['snrs']))
        if (contract['max_full_calls'] != len(requested) or
                contract['max_ce_calls'] != 4 * len(requested) or
                contract['max_terminal_calls'] != 8 * len(requested)):
            raise ValueError('invalid M-01 identity reservation')
        used = 0
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if (row.get('campaign_id') != CAMPAIGN_ID or row.get('stage') != STAGE or
                    'identities' not in row):
                raise ValueError('invalid shared M-01 reservation')
            prior = {tuple(item) for item in row['identities']}
            if requested & prior:
                raise ValueError('M-01 block/snr already reserved')
            used += row['max_full_calls']
        if used + len(requested) > TOTAL_F:
            raise ValueError('cumulative M-01 768F cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, out=str(out.resolve()),
            max_full_calls=len(requested), max_ce_calls=4 * len(requested),
            max_terminal_calls=8 * len(requested),
            calls_reserved={'F': len(requested), 'E': 4 * len(requested), 'T': 8 * len(requested)},
            identities=sorted(requested),
            policy='no retry; geometry oracle arms not deployable; CE once per arm'))
    return str(ledger)


def output_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())




def development_contrasts(table, detectors, blocks, *, manifest):
    return analyze_development('M-01', table, detectors, blocks, manifest)


def _read_batch(batch, d1_sha256, detectors):
    batch = Path(batch)
    if (batch / 'batch-failure.json').exists():
        raise ValueError('failed M-01 batch present')
    summary = json.loads((batch / 'summary.json').read_text())
    contract = json.loads((batch / 'contract.json').read_text())
    if (summary.get('status') != 'complete' or summary.get('exitcode') != 0 or
            summary.get('failures')):
        raise ValueError('incomplete or failed M-01 batch')
    if (contract.get('d1_sha256') != d1_sha256 or contract.get('recipe_id') != RECIPE_ID or
            list(contract.get('arms', [])) != list(ARMS) or
            'EP10' in contract.get('detectors', [])):
        raise ValueError('M-01 batch binding mismatch')
    pair = tuple(contract['detectors'])
    if detectors is None:
        detectors = pair
    elif pair != detectors:
        raise ValueError('detector pair changed across M-01 batches')
    if summary['calls_completed'] != summary['calls_attempted']:
        raise ValueError('M-01 attempted/completed mismatch')
    cells = {}
    for path in batch.glob('cell-*.json'):
        row = json.loads(path.read_text())
        if (row.get('candidate_eligible') or row.get('deployable') or
                row.get('FER') not in (0, 1) or row.get('arm') not in ARMS or
                row.get('truth_access_level') != 'geometry_oracle'):
            raise ValueError('invalid M-01 cell contract')
        key = (int(row['SNR']), f"{row['arm']}__{row['detector']}", int(row['block_id']))
        if key in cells:
            raise ValueError('duplicate M-01 cell')
        cells[key] = int(row['FER'])
    snap = next(iter(batch.glob('snapshot-*.npz')))
    with np.load(snap) as arrays:
        fields = tuple(sorted(arrays.files))
    if 'support' not in fields:
        raise ValueError('M-01 snapshot omitted support')
    completed = summary['calls_completed']
    return dict(detectors=detectors, F=completed['F'], E=completed['E'], T=completed['T'],
                cells=cells, snapshot_fields=fields)


def harvest_run(run_root, *, contrast_manifest, d1_sha256=FROZEN_D1_SHA256):
    """Read completed M-01 batches. Not F_M confirmation."""
    root = Path(run_root)
    batches = sorted(p for p in root.glob('batch-*') if p.is_dir())
    if len(batches) != 16:
        raise ValueError('M-01 harvest requires 16 complete batches')
    detectors = None
    totals = {'F': 0, 'E': 0, 'T': 0}
    cells = {}
    snapshot_fields = None
    for batch in batches:
        row = _read_batch(batch, d1_sha256, detectors)
        detectors = row['detectors']
        for key in totals:
            totals[key] += row[key]
        if snapshot_fields is None:
            snapshot_fields = row['snapshot_fields']
        elif row['snapshot_fields'] != snapshot_fields:
            raise ValueError('M-01 snapshot fields changed across batches')
        overlap = cells.keys() & row['cells'].keys()
        if overlap:
            raise ValueError('overlapping M-01 cell identities')
        cells.update(row['cells'])
    if totals != {'F': TOTAL_F, 'E': TOTAL_E, 'T': TOTAL_T}:
        raise ValueError('M-01 harvest totals are not 768F+3072E+6144T')
    blocks = list(range(N_BLOCKS))
    table = development_table('M-01', cells, detectors, blocks)
    contrasts = development_contrasts(table, detectors, blocks, manifest=contrast_manifest)
    fer = {snr: {cell: float(sum(table[(snr, cell)]) / len(blocks))
                 for cell in {c for s, c in table if s == snr}}
           for snr in SNRS}
    sham = {snr: {cell: fer[snr][cell] for cell in fer[snr] if cell.startswith('sham__')}
            for snr in SNRS}
    return dict(
        schema='supplement-m01-harvest-v2',
        status='complete_development_not_confirmation',
        calls=totals, n_blocks=N_BLOCKS, snrs=list(SNRS), arms=list(ARMS),
        detectors=list(detectors), recipe_id=RECIPE_ID, d1_sha256=d1_sha256,
        snapshot_fields=list(snapshot_fields),
        snapshot_has_support=True,
        snapshot_has_x_soft='x_soft' in snapshot_fields,
        a01_can_reuse_m01_snapshots='x_soft' in snapshot_fields,
        fer_by_cell=fer, sham_negative_control=sham, contrasts=contrasts,
        not_claims=list(FORBIDDEN_CLAIMS), rerun_16T=False,
        scope='M-01 mechanism development; geometry oracle; not F_M confirmation')


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = {'F': 0, 'E': 0, 'T': 0}
    completed = {'F': 0, 'E': 0, 'T': 0}
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
        d1, d1_sha = load_d1_freeze(args.d1, args.d1_sha256)
        detectors = detectors_from_d1(d1)
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

        def timeout(_signal, _frame):
            raise TimeoutError('M-01 batch deadline')

        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        contract = dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, split=SPLIT,
            start=args.start, stop=args.stop, snrs=parsed['snrs'],
            recipe_id=RECIPE_ID, detectors=list(detectors), arms=list(ARMS),
            d1_sha256=d1_sha, device=str(device), gpu_allocator_fraction=GPU_FRACTION,
            max_full_calls=args.max_full_calls, max_ce_calls=args.max_ce_calls,
            max_terminal_calls=args.max_terminal_calls,
            calls_reserved={'F': args.max_full_calls, 'E': args.max_ce_calls,
                            'T': args.max_terminal_calls},
            source_sha256=sources(), checkpoint_sha256=sha(args.checkpoint),
            protocol_sha256=sha(args.protocol), deadline_unix=args.deadline_unix,
            max_output_bytes=args.max_output_bytes, command=command,
            policy='share GPU with H-01; geometry oracle; not deployable')
        contract['config_sha256'] = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_m01(args.out, contract)
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

        def charge(kind, meta):
            nonlocal active
            if time.time() >= args.deadline_unix:
                raise TimeoutError('deadline before M-01 call')
            key = {'CE': 'E', 'terminal': 'T', 'full': 'F'}[kind]
            cap = {'F': args.max_full_calls, 'E': args.max_ce_calls, 'T': args.max_terminal_calls}[key]
            if attempted[key] >= cap:
                raise RuntimeError('reserved ' + key + ' budget exhausted')
            attempted[key] += 1
            active = dict(meta, call_key=key, ordinal=attempted[key], started_unix=time.time())
            publish(args.out / f'started-{key}-{attempted[key]:06d}.json', active)

        for block in range(args.start, args.stop):
            for snr in parsed['snrs']:
                if attempted['F'] >= args.max_full_calls or time.time() >= args.deadline_unix:
                    raise TimeoutError('M-01 budget/deadline exhausted')
                try:
                    frame = data.make_frame(system, SPLIT, block, snr)
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, dict(block=block, snr=snr, full_call_started=False))
                    continue
                charge('full', dict(block=block, snr=snr, recipe_id=RECIPE_ID))
                try:
                    result = receiver.run(frame.observed, audit=True)
                    snap = snapshot_from_result(frame, result)
                    publish_snapshot(args.out / f'snapshot-{snr}-{block:06d}.npz', snap)
                    scores = score_errors(result, frame._truth)
                    publish(args.out / f'normal-full-{snr}-{block:06d}.json', json_value(dict(
                        schema='supplement-m01-full-v1', split=SPLIT, block_id=block, SNR=snr,
                        recipe_id=RECIPE_ID, support=np.asarray(result['support']).astype(int).tolist(),
                        truth_access_level='none', candidate_eligible=False, deployable=False,
                        **scores)))
                    prepared = prepare_from_frame(frame, snap, system)
                    order = list(ARMS)
                    campaign_rng(SPLIT, block, 'order').shuffle(order)
                    for arm in order:
                        charge('CE', dict(block=block, snr=snr, arm=arm))
                        fitted = fit_arm(prepared, system, arm)
                        completed['E'] += 1
                        for detector in detectors:
                            def before(kind, which, det, arm=arm):
                                if which != arm:
                                    raise AssertionError('arm mismatch')
                                charge(kind, dict(block=block, snr=snr, arm=arm, detector=det))
                            row = detect_arm(prepared, fitted, code, arm, detector,
                                             device=device, before_call=before)
                            publish(args.out / f'cell-{snr}-{block:06d}-{arm}-{detector}.json',
                                    json_value(dict(schema='supplement-m01-cell-v1',
                                                    block_id=block, SNR=snr, arm=arm,
                                                    detector=detector, FER=row['FER'],
                                                    info_errors=row['info_errors'],
                                                    candidate_eligible=False, deployable=False,
                                                    truth_access_level=row['truth_access_level'],
                                                    I=prepared['I'].tolist())))
                            completed['T'] += 1
                    completed['F'] += 1
                    records.append(dict(block=block, snr=snr, I=prepared['I'].tolist()))
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, active or dict(block=block, snr=snr))
                    continue
                active = None
        signal.setitimer(signal.ITIMER_REAL, 0)
        status = 'completed_with_failures' if failures else 'complete'
        exitcode = 1 if failures else 0
        publish(args.out / 'summary.json', dict(
            status=status, exitcode=exitcode, calls_attempted=attempted,
            calls_completed=completed, records=records, failures=failures,
            command=command, detectors=list(detectors), recipe_id=RECIPE_ID,
            d1_sha256=d1_sha, gpu_allocator_fraction=GPU_FRACTION,
            scope='M-01 development; geometry oracle; not confirmation'))
        return exitcode
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
    for name in ('protocol', 'checkpoint', 'out', 'd1'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--d1-sha256', required=True)
    p.add_argument('--split', required=True)
    p.add_argument('--start', type=int, required=True)
    p.add_argument('--stop', type=int, required=True)
    p.add_argument('--snrs', type=json.loads, required=True)
    p.add_argument('--deadline-unix', type=int, required=True)
    p.add_argument('--max-full-calls', type=int, required=True)
    p.add_argument('--max-ce-calls', type=int, required=True)
    p.add_argument('--max-terminal-calls', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    p.add_argument('--device', required=True)
    return execute(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
