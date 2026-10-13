"""Bounded full CPU cost quote on audited development inputs, not formal COST."""
import argparse
import json
import os
from pathlib import Path
import resource
import time

import numpy as np
import torch

from .bottleneck_pilot import hashes, load_state, observed_at_snr, offline_scores, sha
from .budgeted_support_eval import build_receiver
from .e1_ldpc import build_code
from .light_gap_receiver_run import run_arm, receiver_resources
from .light_gap_replay import CODE_KEYS, LightRun, replay_decode, setup_guard, verified_record
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .trans_next_stop_run import same_state
from .trans_next_profile_run import compare_projection


def arms(factorial=False):
    settings = [('DENSE', {}), ('INTEGER', dict(outer_bp_graph='integer'))]
    if factorial:
        settings += [('DENSE_QPSK', dict(bp_edge_projection='qpsk_tanh')),
                     ('INTEGER_QPSK', dict(outer_bp_graph='integer', bp_edge_projection='qpsk_tanh'))]
    return [dict(name=name, receiver=dict(terminal_check_prior='retain', **options),
                 feedback=dict(refresh_checkpoints=[4, 7], retain_messages=False,
                               stop_on_valid_codeword=True))
            for name, options in settings]


def order(factorial=False):
    rows = []
    for phase, blocks, snrs in [('warmup', [0], [7]), ('measurement', range(8), [7, 8])]:
        for block in blocks:
            for snr in snrs:
                for repeat in range(2):
                    names = ['DENSE', 'INTEGER']
                    if factorial:
                        names += ['DENSE_QPSK', 'INTEGER_QPSK']
                        rotation = (block + repeat + 2*(snr-7)) % 4
                        names = names[rotation:] + names[:rotation]
                    elif (block + snr + repeat) % 2:
                        names.reverse()
                    rows.extend(dict(phase=phase, block=block, snr=snr, repeat=repeat, arm=a)
                                for a in names)
    return rows


def validate(c, args):
    factorial = c['schema'] == 'trans-cpu-cost-factorial-v1'
    count = 136 if factorial else 68
    if (c['schema'] not in ('trans-cpu-cost-quote-v1', 'trans-cpu-cost-factorial-v1') or c['device'] != 'cpu' or c['threads'] != 1
            or c['blocks'] != list(range(8)) or c['snrs'] != [7, 8] or c['arms'] != arms(factorial)
            or c['order'] != order(factorial) or c['bounds'] != dict(F=count, D=count, seconds=600)
            or c['output_bytes'] != (8 if factorial else 4) * 1024**3 or args.root.name != c['tag']):
        raise ValueError('unregistered full CPU quote boundary')
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('source or contract changed')
    if sha(c['checkpoint_path']) != c['checkpoint_sha256']:
        raise ValueError('checkpoint changed')
    predecessors = ['integer-graph-development-v1', 'retained-chain-development-v1',
                    'schedule-graph-engineering-v1']
    if factorial:
        predecessors += ['execution-count-engineering-v1', 'composition-engineering-v1']
    for tag in predecessors:
        root = Path(c['old_root'])
        audit = json.loads((root/'evidence'/(tag+'-raw-audit.json')).read_text())
        stage = 'engineering' if 'engineering' in tag else 'development'
        if (audit['status'] != 'PASS'
                or audit['summary_sha256'] != sha(root/'runs'/tag/stage/'summary.json')):
            raise ValueError('predecessor raw qualification missing')
        for suffix in ('', '-raw-audit'):
            end = json.loads((root/'evidence'/(tag+suffix+'-exit.json')).read_text())
            if end['exit_code'] != 0 or end['timed_out']:
                raise ValueError('predecessor did not finish successfully')


def compare_scores(actual, expected, optimized):
    if actual.keys() != expected.keys():
        raise ValueError('score schema differs')
    for key, value in expected.items():
        if optimized and isinstance(value, float):
            np.testing.assert_allclose(actual[key], value, rtol=1e-5, atol=1e-6)
        elif actual[key] != value:
            raise ValueError('quote score differs from audited reference: '+key)


def execute(args):
    c = json.loads(args.contract.read_text())
    validate(c, args)
    factorial = c['schema'] == 'trans-cpu-cost-factorial-v1'
    guard = setup_guard(args, c)
    guard.verify()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(args.root, 'quote', c['bounds'], c['output_bytes'], guard)
    try:
        setup_start = time.perf_counter()
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        root = Path(c['old_root'])
        input_path = root/'runs/refs-v1/development/summary.json'
        inputs = json.loads(input_path.read_text())
        input_env = json.loads(input_path.with_name('environment.json').read_text())
        if inputs['status'] != 'COMPLETE' or hashes({k: code[k] for k in CODE_KEYS}) != input_env['code_identity']:
            raise ValueError('input completion or LDPC identity differs')
        reference = json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
        refs = {(r['block'], r['snr']): r for r in reference['records'] if r['arm'] == 'BP_RETAIN_STOP'}
        exogenous = {e['block']: e for e in inputs['exogenous']}
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        setup_seconds = time.perf_counter() - setup_start
        run.write('environment.json', dict(device='cpu', threads=1, numpy=np.__version__,
            torch=torch.__version__, code_identity=input_env['code_identity'], pid=os.getpid(),
            receiver_instance_id=id(receiver), setup_seconds=setup_seconds,
            initial_lstsq_driver='gels', audit=False, retain_messages=False,
            timing_boundary='LightRun measures public run_arm only; serialization, scoring and replay excluded',
            memory_boundary='Linux process RSS high-water in KiB; shared process, not per-arm allocation',
            resource_count_boundary=('actual completed CE/outer/terminal BP/LDPC counts equal audited reference'
                if factorial else 'outer schedule recorded; complete CE/terminal counts belong to audited reference')))
        configured = {a['name']: a for a in c['arms']}
        checks = []
        for planned in c['order']:
            block, snr = planned['block'], planned['snr']
            raw = load_state(exogenous[block]['state'])
            if hashes({k: raw[k] for k in exogenous[block]['hashes']}) != exogenous[block]['hashes']:
                raise ValueError('exogenous input changed')
            observed = observed_at_snr(raw, snr)
            before = hashes(observed)
            reference_record, expected = verified_record(refs[block, snr], root)
            if reference_record['observed_hashes'] != before:
                raise ValueError('reference observation differs')
            identity = dict(planned, split=exogenous[block]['split'])
            arm = configured[planned['arm']]
            value, record = run.call('F', identity,
                lambda: run_arm(receiver, code, observed, arm, audit=False),
                lambda v: offline_scores(v, raw, v['H']),
                dict(observed_hashes=before, configuration=arm, scope=c['scope'],
                     pid=os.getpid(), receiver_instance_id=id(receiver)))
            if hashes(observed) != before or value['graphs'] or value['dals']:
                raise ValueError('mutated input or unexpected full audit payload')
            _, saved = verified_record(run.records[-1], root)
            same_state(saved, value)
            optimized = arm['receiver'].get('bp_edge_projection') == 'qpsk_tanh'
            errors = compare_projection(saved, expected, optimized)
            same_state(saved['bp_schedule'], expected['bp_schedule'])
            compare_scores(record['scores'], reference_record['scores'], optimized)
            resources = receiver_resources(saved) if factorial else None
            if factorial and resources != expected['resource_counts']:
                raise ValueError('actual quote resource counts differ from audited reference')
            checks.append(dict(identity, numeric_exact=not optimized, hard_exact=True,
                projection_relative_errors=errors, actual_resource_counts=resources,
                terminal_executed=value['terminal_executed'],
                completed_outer_detections=value['completed_outer_detections'],
                process_peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
            print(json.dumps(dict(identity, calls=run.counts)), flush=True)
        receiver_records = list(run.records)
        collection_finished = time.time()
        # Replay after every timed receiver call is complete. Each D is separately reserved.
        for entry in receiver_records:
            _, saved = verified_record(entry, root)
            identity = {k: entry[k] for k in ('block', 'snr', 'split', 'arm', 'phase', 'repeat')}
            run.call('D', identity, lambda: replay_decode(code, saved, 1., 20., 50),
                     lambda v: dict(identity_exact=True), dict(source_record_sha256=entry['sha256']))
        guard.verify()
        if sha(c['checkpoint_path']) != c['checkpoint_sha256']:
            raise ValueError('checkpoint changed during quote')
        if run.counts != {key: c['bounds'][key] for key in ('F', 'D')}:
            raise ValueError('quote coverage incomplete')
        run.write('summary.json', dict(status='COMPLETE', stage='quote', calls=run.counts,
            records=run.records, checks=checks, contract_sha256=args.contract_sha256,
            source_sha256=args.source_sha256, setup_seconds=setup_seconds,
            collection_finished_at=collection_finished, finished_at=time.time(),
            process_peak_rss_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            scope=c['scope']))
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--source-manifest', type=Path, required=True)
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--source-sha256', required=True)
    execute(p.parse_args())
