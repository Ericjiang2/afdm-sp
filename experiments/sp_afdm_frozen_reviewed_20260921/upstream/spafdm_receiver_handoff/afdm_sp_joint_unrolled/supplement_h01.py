"""H-01 mechanism 4H×2-detector diagnostic. Not a deployable receiver."""
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

from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .budgeted_support_eval import build_receiver
from .direction_factorial import residual_ledger, run_factorial
from .direction_logging import publish_snapshot
from .direction_receiver import CHECKPOINT_HASH
from .direction_run import json_value
from .supplement_development_analysis import analyze_development, development_table
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_data import CAMPAIGN_ID, LIMITS, SupplementData
from .supplement_profile import score_errors
from .supplement_run import sha, sources

STAGE = 'H-01'
RECIPE_ID = 'B0-p2-s0.5'
SPLIT = 'mechanism'
SNRS = (7, 8, 9)
N_BLOCKS = LIMITS['mechanism']
TOTAL_F = N_BLOCKS * len(SNRS)
TOTAL_T = 8 * TOTAL_F
FROZEN_D1_SHA256 = '4cb7a61722dcb014d0d1ceb8d567f6a66ea0c597ece15840a18658b0b93632b3'
D1_SCHEMA = 'D1_FREEZE.json'
FORBIDDEN_CLAIMS = ('optimal detector', 'best detector', 'D1 proved', 'detector space exhausted')
FAILURE_RESERVE_BYTES = 256 * 1024
PER_FULL_ESTIMATE_BYTES = 40 * 1024 ** 2
LEDGER_NAME = 'supplement-h01-mechanism-ledger'


def load_d1_freeze(path, expected_sha256=None):
    raw = Path(path).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = expected_sha256 or FROZEN_D1_SHA256
    if digest != expected:
        raise ValueError('D1 freeze hash mismatch')
    value = json.loads(raw)
    if (not isinstance(value, dict) or value.get('schema') != D1_SCHEMA or
            value.get('status') != 'development_selected_frozen_reference' or
            value.get('protocol') != 'DET-01R-v1' or
            value.get('h01_may_start') is not True or value.get('rerun_16T') is not False or
            not isinstance(value.get('selected'), str) or not value['selected'] or
            value['selected'] in ('BP', 'EP10') or
            any(claim not in value.get('not_claims', []) for claim in FORBIDDEN_CLAIMS)):
        raise ValueError('D1 freeze does not admit H-01')
    return value, digest


def detectors_from_d1(d1):
    selected = d1['selected']
    if selected in ('BP', 'EP10') or not isinstance(selected, str):
        raise ValueError('H-01 second detector must be frozen D1, not EP10 or BP')
    return ('BP', selected)


def factorial_snapshot(frame, result):
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
        decoded=np.array(result['decoded'], copy=True))
    residual_ledger(snap, snap['Hhat'], snap['Hhat'])
    return snap


def _identities(start, stop, snrs):
    if (not isinstance(snrs, list) or not snrs or any(s not in SNRS for s in snrs) or
            len(set(snrs)) != len(snrs)):
        raise ValueError('H-01 snrs must be a unique subset of 7/8/9')
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= N_BLOCKS:
        raise ValueError('H-01 blocks must lie in mechanism[0,256)')
    return {(block, int(snr)) for block in range(start, stop) for snr in snrs}


def validate_args(args):
    if args.split != SPLIT:
        raise ValueError('H-01 uses only the mechanism split')
    snrs = [int(s) for s in args.snrs]
    identities = _identities(args.start, args.stop, snrs)
    n_full = len(identities)
    n_terminal = 8 * n_full
    if (type(args.max_full_calls) is not int or args.max_full_calls != n_full or
            type(args.max_terminal_calls) is not int or args.max_terminal_calls != n_terminal):
        raise ValueError('H-01 F/T reservation must equal the requested identities')
    if type(args.deadline_unix) is not int or args.deadline_unix <= int(time.time()):
        raise ValueError('future integer unix deadline required')
    estimated = n_full * PER_FULL_ESTIMATE_BYTES + 32 * 1024 ** 2
    if type(args.max_output_bytes) is not int or args.max_output_bytes < estimated:
        raise ValueError('output budget below H-01 uncompressed snapshot estimate')
    if args.d1_sha256 != FROZEN_D1_SHA256:
        raise ValueError('H-01 is bound to the frozen D1 SHA-256')
    load_d1_freeze(args.d1, args.d1_sha256)
    if recipe_by_id(RECIPE_ID)['id'] != RECIPE_ID:
        raise ValueError('H-01 recipe identity drifted')
    return dict(snrs=snrs, identities=identities, n_full=n_full, n_terminal=n_terminal,
                estimated=estimated)


def reserve_h01(out, contract):
    ledger = out.parent / LEDGER_NAME
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        requested = _identities(contract['start'], contract['stop'], list(contract['snrs']))
        if (contract['max_full_calls'] != len(requested) or
                contract['max_terminal_calls'] != 8 * len(requested)):
            raise ValueError('invalid H-01 identity reservation')
        used = 0
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            if (row.get('campaign_id') != CAMPAIGN_ID or row.get('stage') != STAGE or
                    'identities' not in row or
                    any(row.get(key) != contract[key] for key in
                        ('source_sha256', 'checkpoint_sha256', 'protocol_sha256', 'd1_sha256'))):
                raise ValueError('invalid shared H-01 reservation')
            prior = {tuple(item) for item in row['identities']}
            if row['max_full_calls'] != len(prior):
                raise ValueError('H-01 reservation count mismatch')
            if requested & prior:
                raise ValueError('H-01 block/snr already reserved')
            used += row['max_full_calls']
        if used + len(requested) > TOTAL_F:
            raise ValueError('cumulative H-01 768F cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, out=str(out.resolve()),
            max_full_calls=len(requested), max_terminal_calls=8 * len(requested),
            calls_reserved={'F': len(requested), 'T': 8 * len(requested), 'E': 0},
            config_sha256=contract['config_sha256'], source_sha256=contract['source_sha256'],
            checkpoint_sha256=contract['checkpoint_sha256'], protocol_sha256=contract['protocol_sha256'],
            d1_sha256=contract['d1_sha256'], identities=sorted(requested),
            policy='no retry/reclaim; failures remain charged; truth cells are not deployable'))
    return str(ledger)


def _cell_record(cell, snapshot, frame, detectors):
    Hdata = snapshot['Hhat'] if cell['data_source'] == 'estimated' else snapshot['Htrue']
    Hcancel = snapshot['Hhat'] if cell['cancel_source'] == 'estimated' else snapshot['Htrue']
    denom = float(np.linalg.norm(snapshot['Htrue']) ** 2)
    if denom <= 0:
        raise ValueError('nonzero true channel required for NMSE')
    row = dict(
        schema='supplement-h01-cell-v1', campaign_id=CAMPAIGN_ID, stage=STAGE,
        split=frame.metadata['split'], block_id=frame.metadata['block'],
        SNR=frame.metadata['snr_db'], cell_id=cell['cell_id'],
        cancel_source=cell['cancel_source'], data_source=cell['data_source'],
        detector=cell['detector'], detectors=list(detectors),
        truth_access_level=cell['truth_access_level'], diagnostic_only=True,
        candidate_eligible=False, deployable=False,
        FER=cell['FER'], info_errors=cell['info_errors'], decode_ok=cell['decode_ok'],
        H_cancel_source=cell['H_cancel_source'], H_data_source=cell['H_data_source'],
        H_cov_source=cell['H_cov_source'], sigma_source=cell['sigma_source'],
        sigma2_terminal=cell['sigma2_terminal'], z_hash=cell['z_hash'],
        residual=cell['residual'], llr_sha256=cell['llr_sha256'],
        decoded_sha256=cell['decoded_sha256'],
        channel_error={'Hdata_nmse': float(np.linalg.norm(snapshot['Htrue'] - Hdata) ** 2 / denom),
                       'Hcancel_nmse': float(np.linalg.norm(snapshot['Htrue'] - Hcancel) ** 2 / denom)},
        elapsed_seconds=cell['seconds'], process_cpu_seconds=cell['CPU_seconds'],
        peak_gpu_bytes=cell['peak_gpu_bytes'],
        input_hashes=frame.metadata['input_hashes'],
        protocol_sha256=frame.metadata['protocol_sha256'],
        recipe_id=RECIPE_ID, call_type='terminal',
        offline_truth_access='factorial CSI intervention and evaluator; not deployable',
        not_claims=list(FORBIDDEN_CLAIMS))
    json.dumps(row, allow_nan=False)
    if row['FER'] not in (0, 1) or row['candidate_eligible'] or row['deployable']:
        raise ValueError('invalid H-01 cell contract')
    return json_value(row)


def run_block(frame, result, code, detectors, out, *, before_full=None, before_cell, device='cpu'):
    if frame.metadata.get('split') != SPLIT:
        raise ValueError('H-01 run_block requires a mechanism frame')
    snap = factorial_snapshot(frame, result)
    block = frame.metadata['block']
    snr = frame.metadata['snr_db']
    if before_full is not None:
        before_full(dict(block=block, snr=snr, recipe_id=RECIPE_ID, call_type='full'))
    snapshot_meta = publish_snapshot(
        out / f'snapshot-{snr}-{block:06d}.npz',
        {k: snap[k] for k in ('Hhat', 'Htrue', 'y', 'pilot', 'data', 'noise',
                              'sigma2_thermal', 'sigma2_terminal', 'constellation',
                              'info', 'coded', 'decoded')})
    scores = score_errors(result, frame._truth)
    scores['offline_truth_access'] = 'evaluation_only'
    normal = dict(schema='supplement-h01-full-v1', campaign_id=CAMPAIGN_ID, stage=STAGE,
        split=SPLIT, block_id=block, SNR=snr, arm_id=RECIPE_ID, recipe_id=RECIPE_ID,
        detectors=list(detectors), call_type='full', truth_access_level='none',
        candidate_eligible=False, deployable=False,
        H_cancel_source={'stage': 'final_estimate', 'sha256': array_hash(snap['Hhat'])},
        H_data_source={'stage': 'final_estimate', 'sha256': array_hash(snap['Hhat'])},
        H_cov_source={'stage': 'scalar_terminal_BP_no_explicit_C',
                      'H_sha256': array_hash(snap['Hhat'])},
        sigma_source='receiver sigma2_terminal; reused frozen for all eight cells',
        sigma2_terminal=float(snap['sigma2_terminal']),
        snapshot=snapshot_meta, input_hashes=frame.metadata['input_hashes'],
        protocol_sha256=frame.metadata['protocol_sha256'],
        not_claims=list(FORBIDDEN_CLAIMS), **scores)
    publish_json(out / f'normal-full-{snr}-{block:06d}.json', json_value(normal))
    cells = []

    def on_cell(cell):
        record = _cell_record(cell, snap, frame, detectors)
        small = publish_snapshot(
            out / f'cell-{snr}-{block:06d}-{cell["cell_id"]}.npz',
            {k: cell[k] for k in ('mu', 'var', 'llr', 'decoded', 'info_hat', 'hard')})
        record['snapshot'] = small
        publish_json(out / f'cell-{snr}-{block:06d}-{cell["cell_id"]}.json', record)
        cells.append(dict(cell_id=cell['cell_id'], detector=cell['detector'],
                          cancel_source=cell['cancel_source'], data_source=cell['data_source'],
                          FER=cell['FER'], info_errors=cell['info_errors'],
                          z_hash=cell['z_hash'], H_data_source=cell['H_data_source'],
                          truth_access_level=cell['truth_access_level'],
                          candidate_eligible=False))

    factorial = run_factorial(snap, code, device=device, before_call=before_cell,
                              on_cell=on_cell, detectors=detectors)
    comparison = json_value(factorial['normal_output'])
    publish_json(out / f'normal-replay-comparison-{snr}-{block:06d}.json', comparison)
    return dict(recipe_id=RECIPE_ID, detectors=list(detectors), cells=cells,
                normal=json_value(normal), comparison=comparison, calls_attempted=8)




def development_contrasts(table, detectors, blocks, *, manifest):
    return analyze_development('H-01', table, detectors, blocks, manifest)


def _read_batch(batch, d1_sha256, detectors):
    batch = Path(batch)
    if (batch / 'batch-failure.json').exists():
        raise ValueError('failed H-01 batch present')
    summary = json.loads((batch / 'summary.json').read_text())
    contract = json.loads((batch / 'contract.json').read_text())
    if (summary.get('status') != 'complete' or summary.get('exitcode') != 0 or
            summary.get('failures')):
        raise ValueError('incomplete or failed H-01 batch')
    if (contract.get('d1_sha256') != d1_sha256 or contract.get('recipe_id') != RECIPE_ID or
            'EP10' in contract.get('detectors', [])):
        raise ValueError('H-01 batch binding mismatch')
    pair = tuple(contract['detectors'])
    if detectors is None:
        detectors = pair
    elif pair != detectors:
        raise ValueError('detector pair changed across H-01 batches')
    if summary['calls_completed'] != summary['calls_attempted']:
        raise ValueError('H-01 attempted/completed mismatch')
    cells = {}
    for path in batch.glob('cell-*.json'):
        row = json.loads(path.read_text())
        if row.get('candidate_eligible') or row.get('deployable') or row.get('FER') not in (0, 1):
            raise ValueError('invalid H-01 cell contract')
        key = (int(row['SNR']), row['cell_id'], int(row['block_id']))
        if key in cells:
            raise ValueError('duplicate H-01 cell')
        cells[key] = int(row['FER'])
    snap = next(iter(batch.glob('snapshot-*.npz')))
    with np.load(snap) as arrays:
        fields = tuple(sorted(arrays.files))
    return dict(detectors=detectors, F=summary['calls_completed']['F'],
                T=summary['calls_completed']['T'], cells=cells, snapshot_fields=fields)


def harvest_run(run_root, *, contrast_manifest, d1_sha256=FROZEN_D1_SHA256):
    """Read completed H-01 batches. Not F_H confirmation."""
    root = Path(run_root)
    batches = sorted(p for p in root.glob('batch-*') if p.is_dir())
    if len(batches) != 16:
        raise ValueError('H-01 harvest requires 16 complete batches')
    detectors = None
    totals = {'F': 0, 'T': 0}
    cells = {}
    snapshot_fields = None
    for batch in batches:
        row = _read_batch(batch, d1_sha256, detectors)
        detectors = row['detectors']
        totals['F'] += row['F']
        totals['T'] += row['T']
        if snapshot_fields is None:
            snapshot_fields = row['snapshot_fields']
        elif row['snapshot_fields'] != snapshot_fields:
            raise ValueError('H-01 snapshot fields changed across batches')
        overlap = cells.keys() & row['cells'].keys()
        if overlap:
            raise ValueError('overlapping H-01 cell identities')
        cells.update(row['cells'])
    if totals != {'F': TOTAL_F, 'T': TOTAL_T}:
        raise ValueError('H-01 harvest totals are not 768F+6144T')
    blocks = list(range(N_BLOCKS))
    table = development_table('H-01', cells, detectors, blocks)
    contrasts = development_contrasts(table, detectors, blocks, manifest=contrast_manifest)
    fer = {snr: {cell: float(sum(table[(snr, cell)]) / len(blocks))
                 for cell in {c for s, c in table if s == snr}}
           for snr in SNRS}
    return dict(
        schema='supplement-h01-harvest-v2',
        status='complete_development_not_confirmation',
        calls=totals, n_blocks=N_BLOCKS, snrs=list(SNRS),
        detectors=list(detectors), recipe_id=RECIPE_ID, d1_sha256=d1_sha256,
        snapshot_fields=list(snapshot_fields),
        snapshot_has_support='support' in snapshot_fields,
        m01_can_reuse_h01_snapshots='support' in snapshot_fields,
        fer_by_cell=fer, contrasts=contrasts,
        not_claims=list(FORBIDDEN_CLAIMS), rerun_16T=False,
        scope='H-01 mechanism development; not F_H confirmation or optimal-detector claim')


def output_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def _unchanged(args, contract):
    if sources() != contract['source_sha256']:
        raise ValueError('source snapshot changed')
    if sha(args.protocol) != contract['protocol_sha256']:
        raise ValueError('protocol content changed')
    if sha(args.checkpoint) != contract['checkpoint_sha256']:
        raise ValueError('checkpoint content changed')
    if sha(args.d1) != contract['d1_sha256']:
        raise ValueError('D1 freeze content changed')


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    previous = signal.getsignal(signal.SIGALRM)
    attempted = {'F': 0, 'T': 0}
    completed = {'F': 0, 'T': 0}
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

        def timeout(_signal, _frame):
            raise TimeoutError('H-01 batch deadline')

        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix - time.time())
        (args.out / 'code-cache').mkdir()
        code = build_code(cache_dir=args.out / 'code-cache')
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        contract = dict(
            campaign_id=CAMPAIGN_ID, stage=STAGE, split=SPLIT,
            start=args.start, stop=args.stop, snrs=parsed['snrs'],
            recipe_id=RECIPE_ID, detectors=list(detectors),
            d1_selected=d1['selected'], d1_sha256=d1_sha,
            device=str(device), max_full_calls=args.max_full_calls,
            max_terminal_calls=args.max_terminal_calls,
            calls_reserved={'F': args.max_full_calls, 'T': args.max_terminal_calls, 'E': 0},
            source_sha256=sources(), checkpoint_sha256=sha(args.checkpoint),
            protocol_sha256=sha(args.protocol),
            deadline_unix=args.deadline_unix, max_output_bytes=args.max_output_bytes,
            estimated_output_bytes=parsed['estimated'], command=command,
            versions=dict(numpy=np.__version__, torch=torch.__version__, python=sys.version),
            threads=torch.get_num_threads(),
            policy='no resume/retry; truth cells not deployable; not an optimal-detector claim',
            not_claims=list(FORBIDDEN_CLAIMS))
        contract['config_sha256'] = hashlib.sha256(
            json.dumps(contract, sort_keys=True).encode()).hexdigest()
        contract['ledger'] = reserve_h01(args.out, contract)
        publish(args.out / 'contract.json', contract)
        model = build_receiver(args.checkpoint, system, 1024, args.device,
                               receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, RECIPE_ID, system=system)

        def fail(exc, identity):
            item = dict(status='failed', identity=identity, exception=type(exc).__name__,
                        message=str(exc), traceback=traceback.format_exc(),
                        config_sha256=contract['config_sha256'], FER=None)
            path = args.out / f'failure-{len(failures):05d}.json'
            publish(path, item)
            failures.append(dict(path=str(path), sha256=sha(path), identity=identity))

        def before_cell(meta):
            nonlocal active
            if time.time() >= args.deadline_unix:
                raise TimeoutError('deadline before terminal attempt')
            if attempted['T'] >= args.max_terminal_calls:
                raise RuntimeError('reserved T budget exhausted')
            attempted['T'] += 1
            active = dict(meta, call_key='T', ordinal=attempted['T'], started_unix=time.time())
            publish(args.out / f'started-T-{attempted["T"]:06d}.json', active)

        for block in range(args.start, args.stop):
            for snr in parsed['snrs']:
                _unchanged(args, contract)
                if attempted['F'] >= args.max_full_calls or time.time() >= args.deadline_unix:
                    raise TimeoutError('H-01 budget/deadline exhausted')
                active = dict(stage='generation', block=block, split=SPLIT, snr=snr)
                publish(args.out / f'generation-{snr}-{block:03d}-started.json', active)
                try:
                    frame = data.make_frame(system, SPLIT, block, snr)
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, dict(active, full_call_started=False))
                    continue
                meta = frame.metadata
                if (meta.get('split') != SPLIT or meta.get('block') != block or
                        meta.get('snr_db') != snr or
                        meta.get('protocol_sha256') != contract['protocol_sha256']):
                    raise ValueError('generated frame identity differs from H-01 contract')
                attempted['F'] += 1
                active = dict(stage='full_receiver', attempt=attempted['F'], block=block,
                              snr=snr, arm_id=RECIPE_ID, full_call_started=True,
                              started_unix=time.time())
                publish(args.out / f'call-F-{attempted["F"]:05d}-started.json', active)
                try:
                    if device.type == 'cuda':
                        torch.cuda.synchronize(device)
                        torch.cuda.reset_peak_memory_stats(device)
                    result = receiver.run(frame.observed, audit=True)
                    if device.type == 'cuda':
                        torch.cuda.synchronize(device)
                    t_before = attempted['T']
                    row = run_block(frame, result, code, detectors, args.out,
                                    before_cell=before_cell, device=str(device))
                    if attempted['T'] - t_before != 8:
                        raise AssertionError('H-01 block did not consume eight terminal calls')
                except (TimeoutError, KeyboardInterrupt):
                    raise
                except Exception as exc:
                    fail(exc, active)
                    continue
                completed['F'] += 1
                completed['T'] += 8
                records.append(dict(block=block, snr=snr, recipe_id=RECIPE_ID,
                                    cells=[c['cell_id'] for c in row['cells']]))
                active = None
                if output_bytes(args.out) > args.max_output_bytes:
                    raise OSError('actual output exceeded frozen storage budget')
        _unchanged(args, contract)
        signal.setitimer(signal.ITIMER_REAL, 0)
        status = 'completed_with_failures' if failures else 'complete'
        exitcode = 1 if failures else 0
        publish(args.out / 'summary.json', dict(
            status=status, exitcode=exitcode, calls_attempted=attempted,
            calls_completed=completed, records=records, failures=failures,
            command=command, reservation_ledger=contract['ledger'],
            config_sha256=contract['config_sha256'],
            detectors=list(detectors), recipe_id=RECIPE_ID,
            d1_sha256=d1_sha, wall_seconds=time.perf_counter() - started,
            CPU_seconds=time.process_time() - cpu0,
            scope='H-01 mechanism development; not confirmation or optimal-detector claim',
            not_claims=list(FORBIDDEN_CLAIMS)))
        return exitcode
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out / 'batch-failure.json', dict(
            status='failed', exitcode=130 if isinstance(exc, KeyboardInterrupt) else 1,
            exception=type(exc).__name__, message=str(exc)[:16384],
            traceback=traceback.format_exc()[-32768:],
            calls_attempted=attempted, calls_completed=completed, active_attempt=active,
            recorded_failure_count=len(failures)))
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
    p.add_argument('--max-terminal-calls', type=int, required=True)
    p.add_argument('--max-output-bytes', type=int, required=True)
    p.add_argument('--device', required=True)
    return execute(p.parse_args())


if __name__ == '__main__':
    sys.exit(main())
