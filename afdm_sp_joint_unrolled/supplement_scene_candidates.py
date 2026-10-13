"""Frozen candidate development in the two existing S-01 counterexample scenes."""
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

for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'

import numpy as np
import torch

from .budgeted_frame_store import publish_json
from .budgeted_support_diagnostics import array_hash
from .budgeted_support_eval import build_receiver
from .direction_cancel_receiver import CancellationTransform
from .direction_logging import publish_snapshot
from .direction_receiver import CHECKPOINT_HASH
from .e1_ldpc import build_code, extract_info
from .supplement_a01_diagnostics import terminal_diagnostics
from .supplement_baselines import BaselineReceiver, recipe_by_id
from .supplement_baseline_run import output_bytes, terminal_snapshot
from .supplement_data import SupplementData, campaign_rng
from .supplement_feedback import CodeFeedback
from .supplement_feedback_run import compact_audit, validate_result_audit
from .supplement_feedback_schedule import UniformBPSchedule
from .supplement_i02_cache import checked_path, file_binding
from .supplement_pilot_frames import pilot_frames
from .supplement_profile import score_errors
from .supplement_run import json_value, sha
from .supplement_s01 import _read_batch, system_for

SCENES = ('integer', 'overlap')
SNRS = (7, 8, 9)
SCORE_FIELDS = ('FER', 'coded_bit_errors', 'raw_bit_errors', 'decoded_codeword_bit_errors',
                'raw_bits_denominator', 'coded_bits_denominator', 'offline_truth_access')
INPUT_FILES = {
    'A02_representatives': 'A02-representatives.json',
    'pilot_receiver_selection': 'pilot-receiver-selection.json',
    'pilot_npz': 'pilots.npz', 'pilot_manifest': 'pilot-manifest.json',
    'I01_protocol': 'I01-protocol.json', 'scenario_protocol': 'data-protocol.json',
    'global_contrasts': 'global-contrast-manifest.json',
}


def validate_freeze(freeze, inputs):
    """Resolve methods from the already frozen A/I/P selections, not scene FER."""
    a02 = inputs['A02_representatives']
    pilot = inputs['pilot_receiver_selection']
    feedback = inputs['I01_protocol']
    expected = {
        'Bstar': dict(recipe=a02['recipes']['B_star_1']['source_recipe_id'], pilot='p0', interface='baseline'),
        'hard': dict(recipe=a02['symbolic_arm_mapping']['bounded_hard'], pilot='p0', interface='baseline'),
        'group': dict(recipe=a02['symbolic_arm_mapping']['group_or_hierarchical'], pilot='p0', interface='baseline'),
        'soft': dict(recipe=a02['selected_soft_arm'], pilot='p0', interface='baseline'),
        'I1': dict(recipe=feedback['baseline_recipe'], pilot='p0', interface='I1',
                   checkpoint=feedback['checkpoint'], outer_BP=feedback['bp_counts']['I1'], terminal_BP=20),
    }
    for mode in ('scalar', 'diagonal', 'lowrank'):
        expected[mode] = dict(recipe=expected['Bstar']['recipe'], pilot='p0', interface=mode)
    for name in ('p1', 'p2'):
        expected['Pfixed-'+name] = dict(recipe=expected['Bstar']['recipe'], pilot=name, interface='baseline')
        expected['Pmatched-'+name] = dict(recipe=pilot['pilots'][name]['primary'], pilot=name, interface='baseline')
    aliases = dict(B_star_1='Bstar', B_star_2='hard', bounded_hard='hard',
                   group_or_hierarchical='group', legal_soft='soft', I1='I1',
                   scalar_calibrated='scalar', diagonal='diagonal', low_rank='lowrank')
    for protocol in ('Pfixed', 'Pmatched'):
        aliases[protocol+':p0'] = 'Bstar'
        for name in ('p1', 'p2'):
            aliases[protocol+':'+name] = protocol+'-'+name
    if (freeze.get('schema') != 'S01-frozen-candidate-development-v1'
            or freeze.get('physical_arms') != expected or freeze.get('symbolic_aliases') != aliases
            or freeze.get('scenarios') != list(SCENES) or freeze.get('snrs') != list(SNRS)
            or freeze.get('blocks') != 192 or freeze.get('split') != 'counterexample'
            or freeze.get('maximum_new_calls') != dict(F=12768, E=0, T=0)
            or freeze.get('baseline_recapture_calls') != 96
            or freeze.get('m') != 272 or freeze.get('alpha_family') != .05/7
            or pilot['pilots']['p0']['primary'] != expected['Bstar']['recipe']
            or expected['I1']['checkpoint'] != 1 or expected['I1']['outer_BP'] != 12):
        raise ValueError('S-01 candidates differ from frozen A/I/P methods or coverage')
    registry = inputs['global_contrasts']['families']['F_R']
    registered = {arm for row in registry['contrasts'] for arm in row['arms']}
    if set(aliases) != registered - {'A2', 'B0', 'old_B_star'} or registry['m_max'] != 272:
        raise ValueError('S-01 symbolic coverage differs from the global reservation')
    for desc in expected.values():
        recipe_by_id(desc['recipe'])
    return expected


def build_baseline_manifest(root, protocol_sha256):
    """Read the completed recovery grid, including the immutable failure ancestry."""
    root = Path(root)
    batches = [root/'batch-000-016-recovery-v3']
    batches += [root/f'batch-{start:03d}-{start+16:03d}' for start in range(16, 192, 16)]
    records, bindings = [], []
    for batch in batches:
        _read_batch(batch)
        contract = json.loads((batch/'contract.json').read_text())
        if (contract['protocol_sha256'] != protocol_sha256
                or contract['checkpoint_sha256'] != CHECKPOINT_HASH):
            raise ValueError('original S-01 data/checkpoint changed')
        bindings += [file_binding(batch/name) for name in ('contract.json', 'summary.json')]
        for block in range(contract['start'], contract['stop']):
            for scene in SCENES:
                for snr in SNRS:
                    path = batch/f'frame-{scene}-{snr}-{block:03d}.json'
                    row = json.loads(path.read_text())
                    capture = not bool(row.get('input_hashes'))
                    if capture != (block < 16):
                        raise ValueError('missing producer hashes differ from the frozen 96-cell repair')
                    records.append(dict(identity=[block, snr, scene], record=file_binding(path), recapture=capture))
    expected = {(b, s, scene) for b in range(192) for s in SNRS for scene in SCENES}
    if len(records) != len(expected) or {tuple(r['identity']) for r in records} != expected:
        raise ValueError('original S-01 baseline grid incomplete or duplicated')
    return dict(schema='S01-candidate-baseline-manifest-v1', records=records, source_batches=bindings,
                protocol_sha256=protocol_sha256, checkpoint_sha256=CHECKPOINT_HASH,
                reused_cells=1056, recaptured_cells=96)


def identities(start, stop, arms):
    if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= 192 or stop-start > 16:
        raise ValueError('S-01 candidate batches require 1..16 original blocks within [0,192)')
    return [(b, s, scene, arm) for b in range(start, stop) for s in SNRS for scene in SCENES for arm in arms]


def full_calls(ids):
    return sum(arm != 'Bstar' or block < 16 for block, _, _, arm in ids)


def reserve(out, ids, bindings):
    ledger = Path(out).parent/'candidate-ledger'
    ledger.mkdir(exist_ok=True)
    with (ledger/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        wanted, seen, used = set(ids), set(), 0
        if len(wanted) != len(ids):
            raise ValueError('duplicate candidate request')
        for path in ledger.glob('reservation-*.json'):
            row = json.loads(path.read_text())
            prior = {tuple(x) for x in row['identities']}
            if (row['bindings'] != bindings or len(prior) != len(row['identities'])
                    or row['F'] != full_calls(prior) or prior & seen):
                raise ValueError('candidate reservation history or bindings changed')
            seen.update(prior)
            used += row['F']
        if seen & wanted or used + full_calls(ids) > 12768:
            raise ValueError('candidate identity already reserved or finite F cap exceeded')
        name = hashlib.sha256(str(Path(out).resolve()).encode()).hexdigest()
        publish_json(ledger/f'reservation-{name}.json',
                     dict(identities=ids, bindings=bindings, F=full_calls(ids), policy='no retry/reclaim'))


def verify_package(args, bindings=None):
    if bindings is not None and (sha(args.freeze) != bindings['freeze']
            or sha(args.baseline) != bindings['baseline']
            or sha(args.inputs/'source-sha256.json') != bindings['sources']):
        raise ValueError('frozen candidate authority changed during execution')
    manifest = json.loads((args.inputs/'source-sha256.json').read_text())
    if any(sha(args.source/name) != digest for name, digest in manifest.items()):
        raise ValueError('frozen S-01 candidate source changed')


def load_contract(args):
    if sha(args.freeze) != args.freeze_sha256 or sha(args.baseline) != args.baseline_sha256:
        raise ValueError('candidate freeze or baseline manifest changed')
    freeze = json.loads(args.freeze.read_text())
    values = {}
    for key, name in INPUT_FILES.items():
        path = args.inputs/name
        if sha(path) != freeze['bindings'][key]:
            raise ValueError('candidate input binding differs: '+key)
        if key != 'pilot_npz':
            values[key] = json.loads(path.read_text())
    arms = validate_freeze(freeze, values)
    manifest = json.loads(args.baseline.read_text())
    if (manifest['protocol_sha256'] != freeze['bindings']['scenario_protocol']
            or manifest['checkpoint_sha256'] != sha(args.checkpoint) or sha(args.checkpoint) != CHECKPOINT_HASH):
        raise ValueError('baseline/checkpoint/protocol binding differs')
    records = {tuple(row['identity']): row for row in manifest['records']}
    expected = {(b, s, scene) for b in range(192) for s in SNRS for scene in SCENES}
    if len(manifest['records']) != len(records) or set(records) != expected:
        raise ValueError('complete unique original baseline grid required')
    for binding in manifest['source_batches']:
        checked_path(binding)
    for key, value in records.items():
        if value['recapture'] != (key[0] < 16):
            raise ValueError('baseline recapture identities changed')
    verify_package(args)
    return freeze, arms, records


def run_arm(model, code, system, descriptor, observed):
    """Construct the original adapters, passing no frame/truth into the receiver."""
    receiver = BaselineReceiver(model, code, descriptor['recipe'], system=system)
    interface = descriptor['interface']
    kwargs = {}
    if interface == 'I1':
        kwargs.update(code_feedback=CodeFeedback(code, checkpoint=descriptor['checkpoint'], control='legal'),
                      bp_schedule=UniformBPSchedule(outer_bp_iterations=descriptor['outer_BP']))
    elif interface in ('scalar', 'diagonal', 'lowrank'):
        kwargs['terminal_transform'] = CancellationTransform(system, interface)
    elif interface != 'baseline':
        raise ValueError('unknown frozen candidate interface')
    result = receiver.run(observed, audit=True, **kwargs)
    if interface == 'I1':
        validate_result_audit(result, 'I1')
    return result


def validate_baseline(frame, binding):
    row = json.loads(checked_path(binding['record']).read_text())
    key = [frame.metadata['block'], frame.metadata['snr_db'], frame.metadata['scenario']]
    if (key != binding['identity'] or key != [row['block_id'], row['SNR'], row['unit']]
            or row['recipe_id'] != 'B0-p2-s0.5'):
        raise ValueError('baseline identity/recipe mismatch')
    captured = row.get('input_hashes')
    if captured and captured != frame.metadata['input_hashes']:
        raise ValueError('regenerated S-01 inputs differ from original producer hashes')
    if bool(captured) == binding['recapture']:
        raise ValueError('baseline hash/recapture policy mismatch')
    return row


def save_result(out, number, result, frame, code, max_bytes):
    if not np.array_equal(result['info_hat'], extract_info(code, result['decoded'])):
        raise ValueError('decoded/information arrays mismatch')
    if result.get('truth_access_level') == 'true_symbols_oracle':
        raise ValueError('truth entered candidate receiver')
    terminal = terminal_snapshot(out/f'terminal-{number:05d}.npz', frame, result,
                                 budget_root=out, max_bytes=max_bytes-262144)
    detail = dict(terminal=terminal, calibration=terminal_diagnostics(result, frame._truth),
                  capacity_trace=compact_audit(result['capacity_trace']),
                  initial_estimator=compact_audit(result['initial_estimator']),
                  baseline_eligible=bool(result['baseline_eligible']),
                  bp_schedule=compact_audit(result.get('bp_schedule')),
                  feedback=compact_audit(result.get('code_feedback_records', [])))
    if 'channel_refit' in result:
        detail['refit'] = compact_audit(result['channel_refit']['diagnostics'])
    if 'cancellation_transform' in result:
        transformed = result['cancellation_transform']
        detail['cancellation'] = compact_audit(transformed['diagnostics'])
        arrays = {k: transformed[k] for k in ('B', 'z', 'H', 'sigma_out')}
        if output_bytes(out)+sum(np.asarray(x).nbytes for x in arrays.values())+1048576 > max_bytes-262144:
            raise OSError('cancellation raw evidence exceeds batch storage cap')
        detail['cancellation_raw'] = publish_snapshot(out/f'cancellation-{number:05d}.npz', arrays)
    return detail


def execute(args):
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    progress = dict(calls_attempted=dict(F=0, E=0, T=0), calls_completed=dict(F=0, E=0, T=0),
                    reused=0, generator_reconstructions=0, active=None)
    previous = signal.getsignal(signal.SIGALRM)
    records, groups = [], []
    try:
        if (type(args.deadline_unix) is not int or args.deadline_unix <= time.time()
                or not 0 < args.max_output_bytes <= 48*1024**3):
            raise ValueError('future finite deadline and bounded storage required')
        def timeout(*_):
            raise TimeoutError('S-01 candidate batch deadline')
        signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, args.deadline_unix-time.time())
        freeze, arms, baseline = load_contract(args)
        ids = identities(args.start, args.stop, arms)
        bindings = dict(freeze=args.freeze_sha256, baseline=args.baseline_sha256,
                        sources=sha(args.inputs/'source-sha256.json'), checkpoint=sha(args.checkpoint))
        reserve(args.out, ids, bindings)
        torch.set_num_threads(1)
        device = torch.device(args.device)
        if device.type not in ('cpu', 'cuda') or (device.type == 'cuda' and not torch.cuda.is_available()):
            raise ValueError('requested candidate device unavailable')
        if device.type == 'cuda':
            torch.cuda.set_per_process_memory_fraction(.30, device)
        (args.out/'code-cache').mkdir()
        code = build_code(cache_dir=args.out/'code-cache')
        data = SupplementData(args.inputs/'data-protocol.json', code)
        systems = {s: system_for(data.protocol['scenarios'][s]) for s in SCENES}
        models = {s: build_receiver(args.checkpoint, systems[s], 1024, args.device,
                                   receiver_shell='direct40', active_cap=40) for s in SCENES}
        with np.load(args.inputs/'pilots.npz', allow_pickle=False) as archive:
            if set(archive.files) != {'p0', 'p1', 'p2'}:
                raise ValueError('invalid frozen pilot archive')
            pilots = {k: archive[k] for k in archive.files}
        geometry = json.loads((args.inputs/'pilot-manifest.json').read_text())['geometry']
        if any(geometry[k] != getattr(systems['integer'], k) for k in ('c1', 'c2')):
            raise ValueError('frozen pilot geometry differs')
        publish_json(args.out/'contract.json', dict(bindings=bindings, identities=ids,
            calls_reserved=dict(F=full_calls(ids), E=0, T=0), device=str(device), threads=1,
            deadline_unix=args.deadline_unix, max_output_bytes=args.max_output_bytes,
            code_hashes={k: array_hash(code[k]) for k in ('G', 'H')},
            scope='S-01 development, not F_R confirmation', command=[sys.executable, *sys.argv]))
        initialization_seconds = time.perf_counter()-started
        for block in range(args.start, args.stop):
            for scene in SCENES:
                order = list(arms)
                campaign_rng('counterexample', block, 'order', scenario=scene).shuffle(order)
                for snr in SNRS:
                    verify_package(args, bindings)
                    group_start = time.perf_counter()
                    frame = data.make_frame(systems[scene], 'counterexample', block, snr, scenario=scene)
                    progress['generator_reconstructions'] += 1
                    old_binding = baseline[(block, snr, scene)]
                    old = validate_baseline(frame, old_binding)
                    frames = pilot_frames(frame, pilots, c1=systems[scene].c1, c2=systems[scene].c2,
                                          preserve_original_p0=True)
                    truth = {k: frame._truth[k] for k in ('H', 'data', 'noise', 'info', 'coded')}
                    if output_bytes(args.out)+sum(x.nbytes for x in truth.values())+1048576 > args.max_output_bytes-262144:
                        raise OSError('candidate source snapshot exceeds batch storage cap')
                    raw_input = publish_snapshot(args.out/f'input-{scene}-{snr}-{block:03d}.npz', truth)
                    group_calls = 0
                    for arm in order:
                        identity = [block, snr, scene, arm]
                        selected = frames[arms[arm]['pilot']]
                        row = dict(identity=identity, descriptor=arms[arm], metadata=selected.metadata,
                                   source_input=raw_input, truth_access_level='none',
                                   offline_truth_access='scoring_and_diagnostics_only',
                                   independent_confirmation=False, baseline_record=old_binding['record'])
                        if arm == 'Bstar' and not old_binding['recapture']:
                            row.update(call_type='reused', scores={k: old[k] for k in SCORE_FIELDS})
                            progress['reused'] += 1
                        else:
                            if progress['calls_attempted']['F'] >= full_calls(ids):
                                raise ValueError('candidate F reservation exhausted')
                            if output_bytes(args.out)+48*1024**2 > args.max_output_bytes-262144:
                                raise OSError('remaining candidate raw storage exhausted')
                            progress['active'] = identity
                            progress['calls_attempted']['F'] += 1
                            number = progress['calls_attempted']['F']
                            publish_json(args.out/f'call-F-{number:05d}.json',
                                         dict(identity=identity, started_unix=time.time()))
                            if device.type == 'cuda':
                                torch.cuda.synchronize(device)
                                torch.cuda.reset_peak_memory_stats(device)
                            wall, cpu = time.perf_counter(), time.process_time()
                            result = run_arm(models[scene], code, systems[scene], arms[arm], selected.observed)
                            if device.type == 'cuda':
                                torch.cuda.synchronize(device)
                            costs = dict(wall_seconds=time.perf_counter()-wall, cpu_seconds=time.process_time()-cpu,
                                         peak_gpu_bytes=torch.cuda.max_memory_allocated(device) if device.type == 'cuda' else 0,
                                         scope='instrumented full receiver and adapter; excludes generator and offline diagnostics/IO')
                            progress['calls_completed']['F'] += 1
                            group_calls += 1
                            scores = score_errors(result, selected._truth)
                            if arm == 'Bstar' and any(scores[k] != old[k] for k in scores):
                                raise ValueError('recaptured baseline error counts differ from original')
                            row.update(call_type='F', scores=scores, costs=costs,
                                       baseline_recapture=arm == 'Bstar',
                                       **save_result(args.out, number, result, selected, code, args.max_output_bytes))
                            progress['active'] = None
                        path = args.out/f'frame-{scene}-{snr}-{block:03d}-{arm}.json'
                        publish_json(path, json_value(row))
                        records.append(file_binding(path))
                    groups.append(dict(block=block, scene=scene, snr=snr,
                                       elapsed_seconds=time.perf_counter()-group_start, full_calls=group_calls))
            print(json.dumps(dict(event='S01-candidate-block', block=block, **progress)), flush=True)
        verify_package(args, bindings)
        if len(records) != len(ids) or progress['calls_completed']['F'] != full_calls(ids):
            raise ValueError('candidate batch evidence grid incomplete')
        publish_json(args.out/'summary.json', dict(status='complete', exitcode=0, **progress,
            records=records, groups=groups, initialization_seconds=initialization_seconds,
            elapsed_seconds=time.perf_counter()-started, output_bytes=output_bytes(args.out),
            scope='development only; no robustness or formal cost gate'))
        return 0
    except BaseException as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        publish_json(args.out/'failure.json', dict(status='failed', **progress,
            message=str(exc), traceback=traceback.format_exc(), elapsed_seconds=time.perf_counter()-started))
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('out', 'freeze', 'baseline', 'inputs', 'source', 'checkpoint'):
        parser.add_argument('--'+key, type=Path, required=True)
    for key in ('freeze-sha256', 'baseline-sha256', 'device'):
        parser.add_argument('--'+key, required=True)
    for key in ('start', 'stop', 'deadline-unix', 'max-output-bytes'):
        parser.add_argument('--'+key, type=int, required=True)
    raise SystemExit(execute(parser.parse_args()))


if __name__ == '__main__':
    main()
