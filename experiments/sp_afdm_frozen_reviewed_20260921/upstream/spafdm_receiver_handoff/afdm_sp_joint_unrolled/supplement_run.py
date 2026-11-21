"""G0 engineering full-chain profiling; never a formal A2 timing gate."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import sys
import time
import traceback
import tempfile

import numpy as np
import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .direction_run import json_value, summarize
from .direction_receiver import ObservedReceiver
from .e1_ldpc import build_code
from .loop9_cache_features import _make_config_a
from .supplement_data import CAMPAIGN_ID, SupplementData, campaign_rng


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    # Bind all local receiver/generator dependencies, including this new entrypoint.
    root = Path(__file__).resolve().parent
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*.py'))}


def validate_request(args):
    if not 0 <= args.start < args.stop <= 32 or args.snr not in (7, 8, 9):
        raise ValueError('engineering requires blocks [0,32) and SNR 7/8/9')
    if not 1 <= args.max_full_calls <= 128:
        raise ValueError('engineering full-call reservation must be in [1,128]')
    if not math.isfinite(args.deadline_unix) or args.deadline_unix <= time.time():
        raise ValueError('deadline must be finite and in the future')
    recipes = json.loads(args.recipes)
    if not isinstance(recipes, list) or not recipes:
        raise ValueError('recipes must be an explicit nonempty JSON array')
    ids, configurations = set(), set()
    for r in recipes:
        if not isinstance(r, dict) or set(r) != {'id', 'family', 'parameter', 'terminal_scale'}:
            raise ValueError('recipe requires exactly id/family/parameter/terminal_scale')
        if not isinstance(r['id'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', r['id']):
            raise ValueError('invalid recipe id')
        config = (r['family'], r['parameter'], r['terminal_scale'])
        if (isinstance(r['parameter'], bool) or isinstance(r['terminal_scale'], bool) or
                config[:2] not in (('b0', None), ('size', 1.), ('ridge', .01), ('sbl', .001)) or
                r['terminal_scale'] not in (.5, 1.)):
            raise ValueError('unsupported observed receiver recipe')
        if r['id'] in ids or config in configurations:
            raise ValueError('duplicate recipe id or equivalent receiver configuration')
        ids.add(r['id']); configurations.add(config)
    if (args.stop - args.start) * len(recipes) > args.max_full_calls:
        raise ValueError('requested full calls exceed batch reservation')
    return recipes


def reserve(out, contract):
    """Sibling batches share one conservative, immutable 128F reservation ledger."""
    ledger = out.parent / 'supplement-engineering-ledger'
    ledger.mkdir(exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = [json.loads(p.read_text()) for p in ledger.glob('reservation-*.json')]
        if any(r['campaign_id'] != CAMPAIGN_ID for r in rows):
            raise ValueError('foreign campaign reservation')
        used = sum(r['max_full_calls'] for r in rows)
        if used + contract['max_full_calls'] > 128:
            raise ValueError('shared engineering 128F cap exceeded')
        key = hashlib.sha256(str(out.resolve()).encode()).hexdigest()
        publish_json(ledger / f'reservation-{key}.json', {
            'campaign_id': CAMPAIGN_ID, 'out': str(out.resolve()),
            'max_full_calls': contract['max_full_calls'], 'contract_sha256': contract['config_sha256'],
            'policy': 'reservations never automatically reclaimed; failed calls included'})
    return str(ledger)


def publish_terminal(path, result):
    """Atomic exclusive compact raw terminal evidence; dense channel is not dumped."""
    arrays = {k: np.asarray(result[k]) for k in
              ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard', 'support')}
    if any(a.dtype.hasobject or not np.isfinite(a).all() for a in arrays.values()):
        raise ValueError('nonfinite or object terminal evidence')
    fd, temporary = tempfile.mkstemp(prefix='.terminal-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            np.savez_compressed(stream, **arrays)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size,
                scope='raw terminal outputs; offline evaluator only')


def frame_record(frame, result, recipe, contract, wall, cpu, peak):
    meta, truth, observed = frame.metadata, frame._truth, frame.observed
    raw = np.concatenate((result['x_hard'].real < 0, result['x_hard'].imag < 0)).astype(np.uint8)
    if (raw.shape != truth['coded'].shape
            or np.asarray(result['decoded']).shape != truth['coded'].shape
            or np.asarray(result['info_hat']).shape != truth['info'].shape):
        raise ValueError('receiver bit dimensions disagree with truth')
    h = np.asarray(result['H'])
    hhash = array_hash(h)
    info_errors = int(np.count_nonzero(result['info_hat'] != truth['info']))
    row = dict(schema='supplement-engineering-frame-v1', campaign_id=CAMPAIGN_ID,
        metadata=meta, recipe=recipe, config_sha256=contract['config_sha256'],
        source_sha256=contract['source_sha256'], checkpoint_sha256=contract['checkpoint_sha256'],
        code_sha256=contract['code_sha256'], input_hashes=meta['input_hashes'],
        protocol_sha256=meta['protocol_sha256'], split='engineering', scenario='G0',
        block_id=meta['block'], SNR=meta['snr_db'], arm_id=recipe['id'],
        truth_access_level='none', offline_truth_access='evaluation_only',
        H_cancel_source={'stage': 'final_estimate', 'sha256': hhash},
        H_data_source={'stage': 'final_estimate', 'sha256': hhash},
        H_cov_source={'stage': 'scalar_terminal_BP_no_explicit_C', 'H_sha256': hhash},
        sigma_source='final_receiver_sigma2 * terminal_scale',
        sigma_value=result['sigma2_terminal'], sigma_estimated=result['sigma2'],
        sigma_thermal=float(observed['sigma2']),
        raw_bit_errors=int(np.count_nonzero(raw != truth['coded'])),
        coded_bit_errors=info_errors, FER=int(info_errors > 0),
        raw_bits_denominator=int(truth['coded'].size), coded_bits_denominator=int(truth['info'].size),
        decoded_codeword_bit_errors=int(np.count_nonzero(result['decoded'] != truth['coded'])),
        decoder_status={'syndrome_ok': bool(result['decode_ok']), 'maxiter': 50},
        hard_output_hash=array_hash(result['decoded']), call_type='full',
        elapsed_seconds=wall, process_cpu_seconds=cpu, peak_gpu_bytes=peak,
        receiver_seconds=result['seconds'], transfer_seconds=result['transfer_seconds'],
        receiver_inclusive_seconds=result['inclusive_seconds'], device=contract['device'],
        channel_nmse=float(np.linalg.norm(truth['H']-h)**2 / np.linalg.norm(truth['H'])**2),
        actual_tx_energy=float(np.mean(abs(observed['pilot'] + truth['data'])**2)),
        pilot_data_cross_term=float(2*np.vdot(observed['pilot'], truth['data']).real / len(truth['data'])),
        support=result['support'], capacity_trace=result['capacity_trace'],
        graph_edges_each_stage=result['graphs'], initial_estimator=result['initial_estimator'],
        posterior_audit={k: summarize(result[k]) for k in ('mu', 'var', 'llr')},
        timing_scope='instrumented engineering profile; not formal A2 mean/p95 evidence',
        failure=None, retry_of=None)
    return validate_record(json_value(row))


def validate_record(row):
    required = {'schema','campaign_id','metadata','recipe','config_sha256','source_sha256',
        'checkpoint_sha256','code_sha256','input_hashes','protocol_sha256','split','scenario',
        'block_id','SNR','arm_id','truth_access_level','offline_truth_access','H_cancel_source',
        'H_data_source','H_cov_source','sigma_source','sigma_value','raw_bit_errors',
        'coded_bit_errors','raw_bits_denominator','coded_bits_denominator','FER',
        'elapsed_seconds','process_cpu_seconds','peak_gpu_bytes','decoder_status','failure'}
    if required - row.keys():
        raise ValueError('incomplete supplement record')
    if (row['schema'] != 'supplement-engineering-frame-v1' or row['split'] != 'engineering'
            or row['scenario'] != 'G0' or type(row['block_id']) is not int
            or not 0 <= row['block_id'] < 32 or row['SNR'] not in (7, 8, 9)
            or row['offline_truth_access'] != 'evaluation_only'
            or row['campaign_id'] != CAMPAIGN_ID or row['truth_access_level'] != 'none'):
        raise ValueError('invalid campaign or receiver truth access')
    meta = row['metadata']
    if (row['block_id'] != meta.get('block') or row['SNR'] != meta.get('snr_db')
            or row['protocol_sha256'] != meta.get('protocol_sha256')
            or row['arm_id'] != row['recipe'].get('id')):
        raise ValueError('inconsistent record identity')
    for numerator, denominator in [('raw_bit_errors','raw_bits_denominator'), ('coded_bit_errors','coded_bits_denominator')]:
        if (type(row[numerator]) is not int or type(row[denominator]) is not int
                or not 0 <= row[numerator] <= row[denominator] or row[denominator] <= 0):
            raise ValueError('invalid bit count')
    if row['FER'] != int(row['coded_bit_errors'] > 0) or row['sigma_value'] <= 0:
        raise ValueError('invalid FER or variance')
    for key in ('elapsed_seconds','process_cpu_seconds','peak_gpu_bytes'):
        if row[key] < 0:
            raise ValueError('invalid resource measurement')
    if row['input_hashes'] != row['metadata']['input_hashes']:
        raise ValueError('inconsistent input hashes')
    json.dumps(row, allow_nan=False)
    return row


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','checkpoint','out'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('start','stop','max-full-calls'):
        p.add_argument('--'+name, type=int, required=True)
    p.add_argument('--snr', type=float, required=True)
    p.add_argument('--deadline-unix', type=float, required=True)
    p.add_argument('--recipes', required=True, help='JSON array of explicit recipe objects')
    p.add_argument('--device', required=True)
    return p


def execute(args):
    # mkdir itself is the run lock; existing output always fails, including partial runs.
    args.out.mkdir(parents=True, exist_ok=False)
    started, cpu0 = time.perf_counter(), time.process_time()
    attempted = completed = 0
    active = None
    command = [sys.executable, *sys.argv]
    records = []
    previous_handler = signal.getsignal(signal.SIGALRM)
    try:
        recipes = validate_request(args)
        def deadline(_signum, _frame):
            raise TimeoutError('engineering wall deadline reached')
        signal.signal(signal.SIGALRM, deadline)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix-time.time())
        device = torch.device(args.device)
        if device.type not in ('cpu','cuda') or (device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested device unavailable or unsupported')
        protocol = json.loads(args.protocol.read_text())
        ldpc = protocol['system']['ldpc']
        (args.out/'code-cache').mkdir()
        code = build_code(n=ldpc['n'], d_v=ldpc['dv'], d_c=ldpc['dc'], seed=ldpc['seed'], cache_dir=args.out/'code-cache')
        if ldpc['maxiter'] != 50:
            raise ValueError('terminal decoder requires maxiter=50')
        data = SupplementData(args.protocol, code)
        system = _make_config_a(1024, 2., 8, 10., 4.)
        contract = dict(campaign_id=CAMPAIGN_ID, split='engineering', scenario='G0',
            start=args.start, stop=args.stop, snr=args.snr, recipes=recipes, device=str(device),
            cpu_affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
            torch_threads=torch.get_num_threads(),
            protocol_sha256=sha(args.protocol), checkpoint_sha256=sha(args.checkpoint),
            code_sha256={k: array_hash(code[k]) for k in ('G','H')}, source_sha256=sources(),
            max_full_calls=args.max_full_calls, campaign_engineering_cap=128,
            deadline_unix=args.deadline_unix, command=command,
            versions={'numpy': np.__version__, 'torch': torch.__version__, 'python': sys.version},
            deterministic_flags={'torch': torch.are_deterministic_algorithms_enabled(),
                'cudnn_deterministic': torch.backends.cudnn.deterministic,
                'cudnn_benchmark': torch.backends.cudnn.benchmark},
            storage_policy='compact raw terminal NPZ and JSON; no dense H snapshots or automatic transfer',
            retry_policy='no resume or overwrite; failed identities retained, no seed replacement')
        contract['config_sha256'] = hashlib.sha256(json.dumps(contract, sort_keys=True, allow_nan=False).encode()).hexdigest()
        ledger = reserve(args.out, contract)
        publish_json(args.out/'batch-manifest.json', dict(contract, shared_ledger=ledger))
        receiver = ObservedReceiver.build(args.checkpoint, system, code, device=args.device)
        for block in range(args.start, args.stop):
            active = dict(stage='generation', block_id=block, snr_db=args.snr,
                          arm_ids=[r['id'] for r in recipes], started_unix=time.time())
            publish_json(args.out/f'block-{block:06d}-generation-started.json', active)
            frame = data.make_frame(system, 'engineering', block, args.snr)
            order = list(range(len(recipes)))
            campaign_rng('engineering', block, 'order').shuffle(order)
            for index in order:
                if time.time() >= args.deadline_unix:
                    raise TimeoutError('deadline before full call')
                if (sources() != contract['source_sha256'] or sha(args.checkpoint) != contract['checkpoint_sha256']
                        or sha(args.protocol) != contract['protocol_sha256']):
                    raise ValueError('source/checkpoint changed during batch')
                recipe = recipes[index]
                attempted += 1
                active = dict(stage='receiver', attempt=attempted, block_id=block, arm_id=recipe['id'],
                    input_hashes=frame.metadata['input_hashes'], started_unix=time.time())
                publish_json(args.out/f'call-{attempted:06d}-started.json', active)
                if device.type == 'cuda':
                    torch.cuda.synchronize(device); torch.cuda.reset_peak_memory_stats(device)
                wall0, c0 = time.perf_counter(), time.process_time()
                result = receiver.run(frame.observed, family=recipe['family'], parameter=recipe['parameter'],
                    terminal_scale=recipe['terminal_scale'], audit=True)
                if device.type == 'cuda':
                    torch.cuda.synchronize(device)
                wall, cpu = time.perf_counter()-wall0, time.process_time()-c0
                peak = int(torch.cuda.max_memory_allocated(device)) if device.type == 'cuda' else 0
                if (sources() != contract['source_sha256'] or sha(args.checkpoint) != contract['checkpoint_sha256']
                        or sha(args.protocol) != contract['protocol_sha256']):
                    raise ValueError('source/checkpoint/protocol changed during full call')
                row = frame_record(frame, result, recipe, contract, wall, cpu, peak)
                row['terminal_evidence'] = publish_terminal(
                    args.out/f'terminal-{block:06d}-{recipe["id"]}.npz', result)
                path = args.out/f'frame-{block:06d}-{recipe["id"]}.json'
                publish_json(path, row)
                records.append({'path': str(path), 'sha256': sha(path)})
                completed += 1
                active = None
                del result
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out/'complete.json', dict(status='complete', exitcode=0,
            calls_attempted=attempted, calls_completed=completed, records=records,
            wall_seconds=time.perf_counter()-started, CPU_seconds=time.process_time()-cpu0,
            config_sha256=contract['config_sha256'], command=command,
            timing_scope='engineering only; not formal A2 cost or scientific confirmation'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out/'failure.json', dict(status='failed', exitcode=130 if isinstance(exc, KeyboardInterrupt) else 1,
            exception=type(exc).__name__, message=str(exc), traceback=traceback.format_exc(),
            calls_attempted=attempted, calls_completed=completed, active_attempt=active,
            records=records, command=command, wall_seconds=time.perf_counter()-started,
            CPU_seconds=time.process_time()-cpu0))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def main():
    return execute(parser().parse_args())


if __name__ == '__main__':
    sys.exit(main())
