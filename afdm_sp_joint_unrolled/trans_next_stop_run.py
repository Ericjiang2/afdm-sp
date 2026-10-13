"""Bounded syndrome-stop qualification on already published CPU inputs."""
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from . import classical_joint_unrolled as joint
from . import supplement_feedback as feedback
from . import supplement_siso_mmse as siso
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha, offline_scores
from .budgeted_support_diagnostics import array_hash
from .budgeted_support_eval import build_receiver
from .loop9_cache_features import _make_config_a
from .supplement_baselines import BaselineReceiver
from .supplement_profile import OperatorProfile
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
from .light_gap_receiver_run import NUMERIC_FIELDS, run_arm, receiver_resources
from .trans_next_profile_run import compare_projection


def same_state(actual, expected):
    """Exact state equality except measured durations and added stop metadata."""
    if isinstance(expected, dict):
        for key, value in expected.items():
            if key in ('seconds', 'CPU_seconds', 'graph_observer_seconds',
                       'inclusive_seconds', 'transfer_seconds'):
                continue
            if key not in actual:
                raise ValueError('missing prefix field: '+key)
            same_state(actual[key], value)
    elif isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            raise ValueError('prefix length differs')
        for a, e in zip(actual, expected):
            same_state(a, e)
    elif isinstance(expected, np.ndarray):
        np.testing.assert_array_equal(actual, expected)
    elif actual != expected:
        raise ValueError('prefix scalar differs')


def same_receiver_state(actual, expected):
    # Recovery binds each original source manifest separately. A changed audit
    # script/test hash is provenance, not a change to the receiver state.
    same_state(actual, {k: v for k, v in expected.items() if k != 'source_sha256'})


def check_prefix(value, reference):
    """Verify executed prefix and actual stopped output, without true bits."""
    terminal = value['terminal_executed']
    n = value['completed_outer_detections']
    full_n = sum(r['stage'] == 'detector_consume' for r in reference['code_feedback_records'])
    decoders = [r for r in value['code_feedback_records'] if r['stage'] == 'decoder']
    if terminal:
        if n != full_n or any(r['decode_ok'] for r in decoders):
            raise ValueError('terminal executed despite valid checkpoint or incomplete prefix')
        for field in NUMERIC_FIELDS:
            np.testing.assert_array_equal(value[field], reference[field])
    else:
        stop = value['checkpoint_stop']
        if (stop['iteration'] != n-1 or not decoders[-1]['decode_ok']
                or any(r['decode_ok'] for r in decoders[:-1]) or value['sigma2_terminal'] is not None):
            raise ValueError('stop did not use first valid checkpoint')
        for field, source in (('llr', 'decoder_input'), ('decoded', 'decoded'),
                              ('mu', 'posterior_mean'), ('var', 'posterior_variance')):
            np.testing.assert_array_equal(value[field], stop[source])
        np.testing.assert_array_equal(value['x_soft'], stop['posterior_mean'].astype(value['x_soft'].dtype))
        np.testing.assert_array_equal(value['decoded'], (decoders[-1]['raw_app'] < 0).astype(np.uint8))
        np.testing.assert_array_equal(value['llr'], decoders[-1]['decoder_input'])
    if not 1 <= n <= full_n or len(value['dals']) != n-1:
        raise ValueError('invalid number of executed CE updates')
    same_state(value['initial_estimator'], reference['initial_estimator'])
    for key in ('dals', 'support_trace', 'code_feedback_records'):
        same_state(value[key], reference[key][:len(value[key])])
    if value.get('detector') == 'siso_mmse':
        if len(value['siso_states']) != n or bool('terminal_siso' in value) != terminal:
            raise ValueError('SISO state inventory differs from executed prefix')
        same_state(value['siso_states'], reference['siso_states'][:n])
        np.testing.assert_array_equal(value['H'], value['siso_states'][-1]['H'])
    else:
        same_state(value['graphs'], reference['graphs'][:len(value['graphs'])])
        graph = value['graphs'][n-1]
        # The shared BP kernel casts H to complex128 before its graph observer.
        if (len(value['graphs']) != n+int(terminal) or graph['dtype'] != 'torch.complex128'
                or array_hash(value['H'].astype(np.complex128)) != graph['H_hash']):
            raise ValueError('BP graph inventory or stopped H differs')
    return dict(outer_detections=n, terminal_executed=terminal,
                checkpoint=None if terminal else n-1, prefix_exact=True)


def check_calls(value, checkpoints=(1, 4, 7), full_outer=10):
    """Cross-check saved resource counters against actual wrapped calls."""
    n = value.get('completed_outer_detections', full_outer)
    terminal = value.get('terminal_executed', True)
    counts = receiver_resources(value)
    operators = {}
    for row in value['operator_profile']:
        if row['status'] != 'complete':
            raise ValueError('failed profiled operator')
        operators[row['operator']] = operators.get(row['operator'], 0)+1
    nested = sum(i < n for i in checkpoints)
    expected = dict(dense_H_reconstruction=n, CE_design=n-1,
                    DA_LS_feedback_gain=n-1, feedback_LDPC=nested, LDPC=int(terminal))
    is_siso = value.get('detector') == 'siso_mmse'
    expected.update(outer_BP=0 if is_siso else n,
                    terminal_BP=0 if is_siso else int(terminal),
                    SISO=n+int(terminal) if is_siso else 0)
    if any(operators.get(k, 0) != v for k, v in expected.items()):
        raise ValueError('actual operator calls differ from stop prefix')
    if counts['LDPC_calls'] != nested+int(terminal) or counts['CE_solves'] != n-1:
        raise ValueError('resource accounting differs from actual prefix')
    if value.get('outer_bp_graph') == 'integer':
        layout_calls = value['integer_graph_calls']
        if (len(layout_calls) != operators.get('outer_BP', 0)
                or [r['outer_iter'] for r in layout_calls] != list(range(n))
                or not all(r['complete_matrix_verified'] for r in layout_calls)):
            raise ValueError('integer graph lacks actual complete-matrix checks for every outer BP')
    return dict(resources=counts, operators=operators)


def load_recovery(c):
    """Admit only complete saved calls from the explicitly bound failed batch."""
    if 'recovery_manifest' not in c:
        return {}
    if sha(c['recovery_manifest']) != c['recovery_manifest_sha256']:
        raise ValueError('changed recovery inventory')
    recovery = json.loads(Path(c['recovery_manifest']).read_text())
    found = {}
    allowed = {(b, s, a['name']) for b in c['blocks'] for s in c['snrs'] for a in c['arms']}
    for stage in recovery['stages']:
        for key in ('contract', 'source_manifest', 'failure', 'exit'):
            if sha(stage[key]) != stage[key+'_sha256']:
                raise ValueError('changed failed-stage binding: '+key)
        old_contract = json.loads(Path(stage['contract']).read_text())
        for key, value in old_contract.items():
            if key not in ('tag', 'recovery_manifest', 'recovery_manifest_sha256') and c[key] != value:
                raise ValueError('recovery changed experiment: '+key)
        old_source = json.loads(Path(stage['source_manifest']).read_text())
        for name, digest in old_source.items():
            if name not in ('trans_next_stop_run.py', 'trans_next_stop_audit.py', 'test_checkpoint_stop.py') and sha(Path(__file__).parent/name) != digest:
                raise ValueError('recovery changed receiver algorithm: '+name)
        failure = json.loads(Path(stage['failure']).read_text())
        ended = json.loads(Path(stage['exit']).read_text())
        records = stage['records']
        if (failure['status'] != 'FAILED' or failure['active'] is not None or failure['calls'] != {'F': len(records)}
                or ended['exit_code'] != 1 or ended['timed_out']):
            raise ValueError('recovery does not cover closed failed-stage calls')
        for item in records:
            key = item['block'], item['snr'], item['arm']
            if key in found or key not in allowed:
                raise ValueError('duplicate or out-of-contract recovery call')
            verified_record(item, Path(c['reference_root']))
            found[key] = item
    return found



def retained_terminal_records(c):
    """Bind the separately audited T counterfactual used as a full-chain expectation."""
    if c['schema'] != 'trans-retained-stop-v1':
        return {}
    for key in ('terminal_summary', 'terminal_audit'):
        if sha(c[key]) != c[key+'_sha256']:
            raise ValueError('changed retained-terminal evidence')
    summary = json.loads(Path(c['terminal_summary']).read_text())
    audit = json.loads(Path(c['terminal_audit']).read_text())
    if (summary['status'] != 'COMPLETE' or audit['status'] != 'PASS'
            or audit['summary_sha256'] != c['terminal_summary_sha256']
            or summary['input_summary_sha256'] != c['input_summary_sha256']):
        raise ValueError('retained-terminal evidence is not paired with this full input')
    selected = [r for r in summary['records'] if r['arm'] == 'RETAIN']
    refs = {(r['block'], r['snr']): r for r in selected}
    if len(refs) != len(selected) or set(refs) != {(b, s) for b in c['blocks'] for s in c['snrs']}:
        raise ValueError('retained-terminal reference coverage differs')
    return refs


def retained_reference(c, base, terminals, block, snr):
    """Expected full output = unchanged outer trace plus audited terminal result.

    This comparison object is not a simulated receiver or new performance record.
    """
    _, terminal = verified_record(terminals[block, snr], c['reference_root'])
    last = [r for r in base['code_feedback_records'] if r['stage'] == 'decoder'][-1]
    for key in ('H', 'sigma2_terminal'):
        np.testing.assert_array_equal(terminal[key], base[key])
    np.testing.assert_array_equal(terminal['last_check_prior'], last['prior_after'])
    expected = dict(base)
    for key in ('mu', 'var', 'llr', 'decoded', 'info_hat', 'x_hard', 'decode_ok', 'raw_llr', 'finite_message'):
        expected[key] = terminal[key]
    return expected


def check_retained_full(value, reference, *, projection=False):
    if projection:
        errors = compare_projection(value, reference, True)
        if not value['terminal_check_prior_consumed']:
            raise ValueError('full projected reference did not consume terminal prior')
        return dict(full_reference_soft_close=True, hard_reference_exact=True,
                    projection_relative_errors=errors)
    for key in NUMERIC_FIELDS:
        np.testing.assert_array_equal(value[key], reference[key])
    for key in ('dals', 'support_trace', 'capacity_trace', 'code_feedback_records', 'initial_estimator', 'graphs'):
        same_state(value[key], reference[key])
    for key in ('finite_message', 'raw_llr'):
        same_state(value[key], reference[key])
    if not value['terminal_check_prior_consumed']:
        raise ValueError('full retained reference did not consume terminal prior')
    return dict(outer_reference_exact=True, terminal_counterfactual_exact=True)


def projection_reference_records(c):
    if c.get('bp_edge_projection') is None:
        return {}
    for key in ('projection_reference_summary', 'projection_reference_audit'):
        if sha(c[key]) != c[key+'_sha256']:
            raise ValueError('changed projection composition reference: '+key)
    summary = json.loads(Path(c['projection_reference_summary']).read_text())
    audit = json.loads(Path(c['projection_reference_audit']).read_text())
    if (summary['status'] != 'COMPLETE' or audit['status'] != 'PASS' or audit['records'] != 16
            or audit['summary_sha256'] != c['projection_reference_summary_sha256']):
        raise ValueError('incomplete projection composition reference')
    return {(r['block'], r['snr'], r['arm']): r for r in summary['records']}


def execute(args):
    if sha(args.contract) != args.contract_sha256 or sha(args.source_manifest) != args.source_sha256:
        raise ValueError('stop source or contract changed')
    c = json.loads(args.contract.read_text())
    stage = c.get('stage', 'engineering')
    if stage not in ('engineering', 'development'):
        raise ValueError('unknown stop stage')
    development = stage == 'development'
    retained = c['schema'] == 'trans-retained-stop-v1'
    integer_graph = c.get('outer_bp_graph')
    projection = c.get('bp_edge_projection')
    if projection not in (None, 'qpsk_tanh') or (projection is not None and (not retained or development or integer_graph != 'integer')):
        raise ValueError('projection composition is registered for retained engineering only')
    projection_refs = projection_reference_records(c)
    if integer_graph not in (None, 'integer') or (integer_graph is not None and not retained):
        raise ValueError('integer graph qualification requires the retained reference contract')
    terminals = retained_terminal_records(c)
    names = (['BP_STOP', 'SISO_STOP'] if development else
             ['BP_REF47', 'BP_STOP', 'BP_STOP_REPEAT', 'SISO_REF47', 'SISO_STOP', 'SISO_STOP_REPEAT'])
    if retained:
        names = ['BP_RETAIN', 'BP_RETAIN_STOP'] if development else [
            'BP_REF47', 'BP_RETAIN', 'BP_RETAIN_STOP', 'BP_RETAIN_STOP_REPEAT']
    blocks = list(range(32)) if development else [0, 1]
    if (c['schema'] not in ('trans-stop-engineering-v1', 'trans-retained-stop-v1') or c['device'] != 'cpu' or c['threads'] != 1
            or c['blocks'] != blocks or c['snrs'] != [7, 8] or c['F_limit'] != len(blocks)*2*len(names)
            or [a['name'] for a in c['arms']] != names or args.root.name != c['tag']):
        raise ValueError('unregistered stop engineering boundary')
    if development:
        if 'recovery_manifest' in c:
            raise ValueError('development recovery is not registered')
        if sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('changed engineering admission')
        admission = json.loads(Path(c['engineering_admission']).read_text())
        if (admission['status'] != 'PASS' or admission['records'] != (16 if retained else 24)
                or admission['source_sha256'] != c['engineering_source_sha256']):
            raise ValueError('incomplete stop engineering qualification')
        if sha(c['engineering_source_manifest']) != c['engineering_source_sha256']:
            raise ValueError('changed qualified source manifest')
        for name, digest in json.loads(Path(c['engineering_source_manifest']).read_text()).items():
            if name not in ('trans_next_stop_run.py', 'trans_next_stop_audit.py') and sha(Path(__file__).parent/name) != digest:
                raise ValueError('changed qualified stop algorithm: '+name)
    for key in ('input_summary', 'reference_summary', 'checkpoint_path'):
        digest_key = 'checkpoint_sha256' if key == 'checkpoint_path' else key+'_sha256'
        if sha(c[key]) != c[digest_key]:
            raise ValueError('bound input changed: '+key)
    for arm in c['arms']:
        receiver = dict(detector='siso_mmse') if arm['name'].startswith('SISO') else {}
        fb = dict(refresh_checkpoints=[4, 7], retain_messages=True)
        if 'STOP' in arm['name']:
            fb['stop_on_valid_codeword'] = True
        if retained and 'RETAIN' in arm['name']:
            receiver['terminal_check_prior'] = 'retain'
            if integer_graph is not None:
                receiver['outer_bp_graph'] = integer_graph
            if projection is not None:
                receiver['bp_edge_projection'] = projection
        if arm['receiver'] != receiver or arm['feedback'] != fb:
            raise ValueError('unregistered stop configuration')
    guard = setup_guard(args, c)
    recovery = load_recovery(c)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(args.root, stage, dict(F=c['F_limit']-len(recovery), seconds=c['seconds']), c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        inputs = json.loads(Path(c['input_summary']).read_text())
        old = json.loads(Path(c['reference_summary']).read_text())
        env = json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
        if (inputs['status'] != 'COMPLETE' or old['status'] != 'COMPLETE'
                or hashes({k: code[k] for k in CODE_KEYS}) != env['code_identity']):
            raise ValueError('incomplete inputs or changed LDPC')
        exo = {e['block']: e for e in inputs['exogenous']}
        refs = {(r['block'], r['snr'], r['arm']): r for r in old['records']}
        if development:
            refs.update({(r['block'], r['snr'], r['arm']): r for r in inputs['records']})
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        run.write('environment.json', dict(code_identity=env['code_identity'], device='cpu', threads=1,
            numpy=np.__version__, torch=torch.__version__, initial_lstsq_driver='gels'))
        checks, totals = [], {}
        for block in c['blocks']:
            raw = load_state(exo[block]['state'])
            if hashes({k: raw[k] for k in exo[block]['hashes']}) != exo[block]['hashes']:
                raise ValueError('raw input changed')
            for snr in c['snrs']:
                observed = observed_at_snr(raw, snr)
                before = hashes(observed)
                groups = [[a] for a in c['arms']] if development else ([c['arms']] if retained else [c['arms'][:3], c['arms'][3:]])
                if (block+snr) % 2:
                    groups.reverse()
                for group in groups:
                    base = repeat = None
                    if development:
                        ref_name = 'SISO_REF47' if group[0]['name'].startswith('SISO') else 'REFRESH47'
                        _, base = verified_record(refs[block, snr, ref_name], Path(c['reference_root']))
                        if retained:
                            base = retained_reference(c, base, terminals, block, snr)
                    for arm in group:
                        def full():
                            with OperatorProfile(torch.device('cpu')) as profile:
                                profile.wrap(joint, 'reconstruct_H_torch', 'dense_H_reconstruction')
                                profile.wrap(joint, 'build_A_for_DALS_torch', 'CE_design')
                                profile.wrap(feedback, 'decoder_messages', 'feedback_LDPC')
                                profile.wrap(siso, 'siso_mmse', 'SISO')
                                value = run_arm(receiver, code, observed, arm)
                            value['operator_profile'] = profile.rows
                            value['resource_counts'] = receiver_resources(value)
                            check_calls(value)
                            return value
                        identity = dict(block=block, snr=snr, split=exo[block]['split'], arm=arm['name'])
                        key = block, snr, arm['name']
                        if key in recovery:
                            item = recovery[key]
                            record, value = verified_record(item, Path(c['reference_root']))
                            if record['observed_hashes'] != before or record['configuration'] != arm:
                                raise ValueError('recovered call input/configuration differs')
                            run.records.append(item)
                        else:
                            value, record = run.call('F', identity, full, lambda v: offline_scores(v, raw, v['H']),
                                dict(observed_hashes=before, configuration=arm, scope=c['scope']))
                        if hashes(observed) != before:
                            raise ValueError('receiver mutated observation')
                        _, saved = verified_record(run.records[-1], Path(c['reference_root']))
                        same_state(saved, value)
                        if offline_scores(saved, raw, saved['H']) != record['scores']:
                            raise ValueError('saved scores differ')
                        detail = check_calls(saved)
                        if 'STOP' not in arm['name']:
                            ref_name = 'SISO_REF47' if arm['name'].startswith('SISO') else 'REFRESH47'
                            _, reference = verified_record(refs[block, snr, ref_name], Path(c['reference_root']))
                            if retained and 'RETAIN' in arm['name']:
                                expected = retained_reference(c, reference, terminals, block, snr)
                                detail.update(check_retained_full(saved, expected, projection=projection is not None))
                            else:
                                for field in NUMERIC_FIELDS:
                                    np.testing.assert_array_equal(saved[field], reference[field])
                                detail['old_reference_exact'] = True
                            base = saved
                        else:
                            detail.update(check_prefix(saved, base))
                            if retained and saved['terminal_check_prior_consumed'] != saved['terminal_executed']:
                                raise ValueError('stopped receiver consumed terminal prior')
                            if repeat is None:
                                repeat = saved
                            else:
                                same_receiver_state(saved, repeat)
                        if projection is not None:
                            _, expected_projection = verified_record(projection_refs[key], Path(c['reference_root']))
                            detail['composition_reference_errors'] = compare_projection(
                                saved, expected_projection, 'RETAIN' in arm['name'])
                        for key, count in saved['resource_counts'].items():
                            totals[key] = totals.get(key, 0)+count
                        checks.append(dict(identity, **detail, scores=record['scores']))
                        print(json.dumps(dict(identity, calls=run.counts)), flush=True)
        guard.verify()
        if retained_terminal_records(c) != terminals:
            raise ValueError('terminal references changed during full run')
        if load_recovery(c) != recovery:
            raise ValueError('recovery changed during engineering')
        if sha(c['reference_summary']) != c['reference_summary_sha256']:
            raise ValueError('reference changed during engineering')
        if sha(c['input_summary']) != c['input_summary_sha256']:
            raise ValueError('input summary changed during run')
        if projection_reference_records(c) != projection_refs:
            raise ValueError('projection reference changed during run')
        if development and sha(c['engineering_admission']) != c['engineering_admission_sha256']:
            raise ValueError('engineering admission changed during development')
        run.write('summary.json', dict(status='COMPLETE', records=run.records, checks=checks,
            resource_totals=totals, calls=run.counts, contract_sha256=args.contract_sha256,
            source_sha256=args.source_sha256, recovered_calls=len(recovery), stage=stage,
            exogenous=[exo[b] for b in c['blocks']], scope=c['scope']))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'contract', 'source-manifest'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('contract-sha256', 'source-sha256'):
        parser.add_argument('--'+name, required=True)
    execute(parser.parse_args())
