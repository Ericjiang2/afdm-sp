"""Finite, prelisted local-state experiment; no full receiver or truth access."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import time
import traceback

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[name] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np
import torch

from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
from afdm_sp_joint_unrolled.supplement_adjacent_run import save_state
from afdm_sp_joint_unrolled.supplement_timing_integrity import OutputMeter
from supplement_adjacent_evidence import file_sha, load_raw
from supplement_adjacent_local import bounded_update, reference_update


def run(args):
    if file_sha(args.contract) != args.contract_sha256:
        raise ValueError('local precheck contract changed')
    contract = json.loads(args.contract.read_text())
    if (contract['schema'] != 'adjacent-local-precheck-v1' or contract['max_local_updates'] != 1792
            or args.snr not in (7, 8) or len(contract['configs']) != 7):
        raise ValueError('unexpected local precheck scope')
    audit = json.loads((args.root / 'development-i1-audit-v1/audit.json').read_text())
    if audit['status'] != 'raw_integrity_passed' or audit['local_states'] != 256:
        raise ValueError('complete audited I1 states required')
    reservation = json.loads(args.reservation.read_text())
    if (reservation['contract_sha256'] != args.contract_sha256
            or reservation['local_updates_reserved'] != 1792
            or reservation['worker_snrs'] != [7, 8]):
        raise ValueError('local update reservation differs')
    args.out.mkdir(exist_ok=False)
    meter = OutputMeter(args.out, 1_499_000_000)
    deadline = min(args.deadline_unix, 1789209000.)
    started = time.time()
    attempted, completed, active = 0, 0, None

    def expired(_signal, _frame):
        raise TimeoutError('local precheck deadline reached')

    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - started))
    try:
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        publish_json(args.out / 'run.json', dict(pid=os.getpid(),
            start_ticks=int(Path('/proc/self/stat').read_text().split()[21]),
            started_at_unix=started, deadline_unix=deadline, snr_db=args.snr,
            local_updates_reserved=896, F=0, device='cpu', contract_sha256=args.contract_sha256,
            source_files={path.name: file_sha(path) for path in Path(__file__).parent.glob('*.py')}))
        records = []
        for first, stop in contract['state_blocks']:
            for block in range(first, stop):
                cell = args.root / 'development-i1-gpu' / f'b{block:06d}-s{args.snr}'
                meta = json.loads((cell / 'I1-r0.json').read_text())
                values = load_raw(meta['raw'], args.root)
                states = values['bp_input_states']
                if [state['outer_iter'] for state in states] != contract['outer_iterations']:
                    raise ValueError('prelisted state inventory changed')
                for state in states:
                    iteration = state['outer_iter']
                    rng = np.random.default_rng(np.random.SeedSequence([20260911, args.snr, block, iteration]))
                    order = rng.permutation(len(contract['configs'])).tolist()
                    outputs = {}
                    for ordinal in order:
                        config = contract['configs'][ordinal]
                        active = dict(block=block, snr_db=args.snr, outer_iter=iteration, config=config['id'])
                        attempted += 1
                        if config['rule'] == 'full':
                            result = reference_update(state)
                        else:
                            result = bounded_update(state, config['rule'], config['parameter'])
                        outputs[config['id']] = result
                        completed += 1
                    reference = outputs['full']
                    for config in contract['configs']:
                        result = outputs[config['id']]
                        difference = np.abs(result['llr'] - reference['llr'])
                        certificate = np.tile(2*result['certificate'], 2)
                        if np.any(difference > certificate + 1e-7):
                            raise ValueError('local same-prior LLR certificate violated')
                        identity = dict(block=block, snr_db=args.snr, outer_iter=iteration, config=config['id'])
                        path = args.out / f'b{block:06d}-i{iteration}-{config["id"]}.npz'
                        saved = save_state(path, result, meter, readback=True)
                        record = dict(**identity, partition='fit' if block < 256 else 'heldout',
                            source_result_meta_sha256=file_sha(cell / 'I1-r0.json'),
                            source_state_hashes={key: meta['raw']['metadata']['bp_input_states'][contract['outer_iterations'].index(iteration)][key]
                                for key in ('H', 'y', 'sigma2', 'code_prior', 'constellation')},
                            execution_order=[contract['configs'][index]['id'] for index in order],
                            edges=len(result['retained']), retained_edges=int(result['retained'].sum()),
                            seconds=result['seconds'], timings=result['timings'], recovery=result['recovery'],
                            llr_max_error=float(difference.max()), llr_p95_error=float(np.quantile(difference, .95)),
                            mean_max_error=float(np.abs(result['mean'] - reference['mean']).max()),
                            variance_max_error=float(np.abs(result['variance'] - reference['variance']).max()),
                            certificate_max=float(result['certificate'].max()), raw=saved)
                        publish_json(path.with_suffix('.json'), record)
                        records.append({key: value for key, value in record.items() if key not in ('raw', 'source_state_hashes')})
                print(json.dumps(dict(block=block, snr_db=args.snr, completed_local_updates=completed,
                    attempted_local_updates=attempted, elapsed_seconds=time.time()-started)), flush=True)
        if attempted != 896 or completed != 896 or len(records) != 896:
            raise ValueError('local update count differs from reservation')
        # JSON sidecars are outside save_state's meter; account for them explicitly.
        actual_bytes = sum(path.stat().st_size for path in args.out.rglob('*') if path.is_file())
        if actual_bytes > 1_490_000_000:
            raise ValueError('local output reservation exceeded')
        publish_json(args.out / 'complete.json', dict(status='complete_local_precheck',
            attempted_local_updates=attempted, completed_local_updates=completed,
            started_at_unix=started, finished_at_unix=time.time(), elapsed_seconds=time.time()-started,
            bytes_before_closure=actual_bytes, F=0, records=records,
            scope='one-update frozen BP comparison; no FER experiment or formal cost claim'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        failure = dict(status='incomplete', exception=type(exc).__name__, message=str(exc),
            traceback=traceback.format_exc(), active=active, attempted_local_updates=attempted,
            completed_local_updates=completed, failed_at_unix=time.time(),
            policy='keep all raw outputs and unused reservations; no automatic retry')
        publish_json(args.out / 'failure.json', failure)
        print(json.dumps(failure), flush=True)
        return 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--contract-sha256', required=True)
    parser.add_argument('--reservation', type=Path, required=True)
    parser.add_argument('--snr', type=int, required=True)
    parser.add_argument('--deadline-unix', type=float, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args))
