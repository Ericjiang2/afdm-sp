"""Full receiver qualification of an ordinary temperature/noise reference."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(args):
    root = args.root
    source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import direction_receiver as api, classical_joint_unrolled as joint, supplement_feedback as feedback
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes, load_state, observed_at_snr, offline_scores
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores, replay_decode, check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import run_arm, receiver_resources, NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_receiver_state, same_state, check_prefix, check_calls
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import FIELDS, check_value, check_finite_prior_message
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash

    contract = root/'contracts'/(args.tag+'.json')
    c = json.loads(contract.read_text())
    manifest = source/'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == 'terminal-controls-chain-v1' and c['snrs'] == [7, 8]
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else list(range(32)))
    names = ['LEGACY', 'UNTEMPERED', 'UNTEMPERED_REPEAT', 'UNTEMPERED_STOP'] if engineering else ['UNTEMPERED', 'UNTEMPERED_STOP']
    assert c['arms'] == names and c['device'] == 'cpu' and c['threads'] == 1
    n = len(c['blocks']); f = n*2*len(names)
    assert c['bounds'] == dict(F=f, T=n, D=f+n, seconds=600 if engineering else 1800)
    assert sha(c['checkpoint_path']) == c['checkpoint_sha256']
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        audit = json.loads((root/audit_path).read_text())
        assert audit['status'] == 'PASS' and audit['summary_sha256'] == sha(root/summary_path)
    if not engineering:
        admission = json.loads((root/c['engineering_audit']).read_text())
        assert admission['status'] == 'PASS' and admission['source_sha256'] == sha(manifest)
        assert admission['script_sha256'] == sha(Path(__file__))
        assert admission['summary_sha256'] == sha(root/c['engineering_summary'])
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    inputs = json.loads((root/'runs/refs-v1/development/summary.json').read_text())
    env = json.loads((root/'runs/refs-v1/development/environment.json').read_text())
    old = json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
    ts = json.loads((root/'runs/untempered-terminal-v1/diagnostic/summary.json').read_text())
    exo = {r['block']: r for r in inputs['exogenous']}
    refs = {(r['block'], r['snr'], r['arm']): r for r in old['records']}
    terminal7 = {r['block']: r for r in ts['records'] if r['kind'] == 'T' and r['arm'] == 'EST__RETAIN__PHYSICAL'}
    assert len(exo) == len(terminal7) == 32 and len(refs) == 128
    out = root/'runs'/args.tag/c['stage']

    def load_input(b, snr):
        raw = load_state(exo[b]['state'])
        assert hashes({k: raw[k] for k in exo[b]['hashes']}) == exo[b]['hashes']
        observed = observed_at_snr(raw, snr)
        _, old_full = verified_record(refs[b, snr, 'BP_RETAIN'], root)
        _, old_stop = verified_record(refs[b, snr, 'BP_RETAIN_STOP'], root)
        decoders = [r for r in old_full['code_feedback_records'] if r['stage'] == 'decoder']
        assert [r['iteration'] for r in decoders] == [1, 4, 7]
        prior = np.clip(decoders[-1]['raw_check_extrinsic'], -20, 20)
        np.testing.assert_array_equal(prior, old_full['finite_message']['prior_llr'])
        expected = dict(H=old_full['H'], z=observed['y']-old_full['H']@observed['pilot'],
                        sigma2_terminal=observed['sigma2'], last_check_prior=prior)
        return raw, observed, old_full, old_stop, expected

    def check_full(value, old_full, old_stop, target, expected, name):
        detail = check_calls(value)
        if name == 'LEGACY':
            same_receiver_state(value, old_full)
            return detail
        assert value['terminal_bp_temperature'] == 1. and value['terminal_variance_source'] == 'physical'
        terminal = value.get('terminal_executed', True)
        assert value['terminal_controls_consumed'] == value['terminal_check_prior_consumed'] == terminal
        assert not value['terminal_scale_applied']
        if 'STOP' in name:
            # The terminal controls cannot alter any early checkpoint decision.
            assert terminal == old_stop['terminal_executed']
            merged = dict(old_full, **{k: target[k] for k in FIELDS}, sigma2_terminal=expected['sigma2_terminal'])
            detail.update(check_prefix(value, merged))
            if not terminal:
                for key in NUMERIC_FIELDS:
                    np.testing.assert_array_equal(value[key], old_stop[key])
                assert 'finite_message' not in value and value['sigma2_terminal'] is None
        else:
            for key in ('H', 'sigma2', 'x_soft', 'gains', 'support', 'dals', 'support_trace', 'capacity_trace',
                        'initial_estimator', 'code_feedback_records', 'graphs', 'bp_schedule'):
                same_state(value[key], old_full[key])
        if terminal:
            assert value['sigma2_terminal'] == expected['sigma2_terminal']
            for key in (*FIELDS, 'raw_llr', 'finite_message'):
                same_state(value[key], target[key])
            check_finite_prior_message(value, expected['last_check_prior'])
            graph = value['graphs'][-1]
            assert graph['H_hash'] == array_hash(expected['H'].astype(np.complex128))
            assert graph['edges'] == np.count_nonzero(abs(expected['H'].astype(np.complex128)) >= 1e-4)
        detail.update(unchanged_outer_or_stop_prefix=True, terminal_matches_saved_reference=terminal)
        return detail

    def audit_records(summary):
        assert summary['calls'] == {k: v for k, v in c['bounds'].items() if k != 'seconds'}
        assert summary['source_sha256'] == sha(manifest) and summary['contract_sha256'] == sha(contract)
        assert summary['script_sha256'] == sha(Path(__file__))
        index = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in summary['records']}
        assert len(index) == len(summary['records']) == f*2+n*2
        rows = []; arrays = 0
        for b in c['blocks']:
            for snr in c['snrs']:
                raw, observed, old_full, old_stop, expected = load_input(b, snr)
                target_entry = terminal7[b] if snr == 7 else index['T', b, snr, 'TERMINAL_EXPECTATION']
                _, target = verified_record(target_entry, root)
                check_value(target, expected, 'RETAIN')
                for name in names+([] if snr == 7 else ['TERMINAL_EXPECTATION']):
                    kind = 'T' if name == 'TERMINAL_EXPECTATION' else 'F'
                    entry = index[kind, b, snr, name]
                    record, value = verified_record(entry, root)
                    assert record['observed_hashes'] == hashes(observed)
                    assert record['reference_record_sha256'] == refs[b, snr, 'BP_RETAIN']['sha256']
                    if kind == 'F':
                        detail = check_full(value, old_full, old_stop, target, expected, name)
                        scores = offline_scores(value, raw, value['H'])
                        rows.append(dict(block=b, snr=snr, arm=name, scores=scores, **detail))
                    else:
                        check_value(value, expected, 'RETAIN'); scores = decoder_scores(value, raw)
                    assert scores == record['scores'] == entry['scores']
                    arrays += finite_arrays(value)
                    dr, decoded = verified_record(index['D', b, snr, name], root)
                    assert dr['source_record_sha256'] == entry['sha256']
                    check_decode_identity(decoded, value)
                    np.testing.assert_array_equal(decoded['llr'], value['llr'])
                    assert decoder_scores(decoded, raw) == dr['scores']
                if engineering:
                    _, a = verified_record(index['F', b, snr, 'UNTEMPERED'], root)
                    _, b_repeat = verified_record(index['F', b, snr, 'UNTEMPERED_REPEAT'], root)
                    same_receiver_state(a, b_repeat)
        return dict(rows=rows, arrays=arrays, saved_records=len(index))

    if args.mode == 'audit':
        started = time.time()
        end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        path = out/'summary.json'; summary = json.loads(path.read_text())
        assert summary['status'] == 'COMPLETE'
        details = audit_records(summary)
        assert details == summary['raw_checks']
        guard.verify()
        result = dict(status='PASS', **details, source_sha256=sha(manifest), script_sha256=sha(Path(__file__)),
            summary_sha256=sha(path), contract_sha256=sha(contract), wall_seconds=time.time()-started,
            new_receiver_or_decoder_calls=0, scope=c['scope'], independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f_out:
            json.dump(result, f_out, indent=2)
        print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
        return

    run = LightRun(root/'runs'/args.tag, c['stage'], c['bounds'], c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        assert hashes({k: code[k] for k in CODE_KEYS}) == env['code_identity']
        system = _make_config_a(1024, 2., 8, 10., 4.)
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        run.write('environment.json', dict(code_identity=env['code_identity'], device='cpu', threads=1,
            numpy=np.__version__, torch=torch.__version__, source_sha256=sha(manifest)))
        for b in c['blocks']:
            for snr in c['snrs']:
                raw, observed, old_full, old_stop, expected = load_input(b, snr)
                before = hashes(observed)
                provenance = dict(observed_hashes=before, reference_record_sha256=refs[b, snr, 'BP_RETAIN']['sha256'], scope=c['scope'])
                if snr == 8:
                    def terminal():
                        edges = []
                        with OperatorProfile(torch.device('cpu')) as profile:
                            value = api.terminal_decode(expected['z'], expected['H'], expected['sigma2_terminal'],
                                observed['constellation'], code, audit=True, code_prior=expected['last_check_prior'],
                                bp_temperature=1., edge_count_observer=edges.append)
                        value.update(expected, operator_profile=profile.rows,
                            resource_counts=dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0), actual_edges=edges[0])
                        return value
                    target, _ = run.call('T', dict(block=b, snr=snr, split=exo[b]['split'], arm='TERMINAL_EXPECTATION'),
                        terminal, lambda v: decoder_scores(v, raw), provenance)
                else:
                    _, target = verified_record(terminal7[b], root)
                check_value(target, expected, 'RETAIN')
                for name in names:
                    control = dict(terminal_check_prior='retain')
                    if name != 'LEGACY':control.update(terminal_bp_temperature=1., terminal_variance_source='physical')
                    fb = dict(refresh_checkpoints=[4, 7], retain_messages=True)
                    if 'STOP' in name:fb['stop_on_valid_codeword'] = True
                    arm = dict(name=name, receiver=control, feedback=fb)
                    def full():
                        with OperatorProfile(torch.device('cpu')) as profile:
                            profile.wrap(joint, 'reconstruct_H_torch', 'dense_H_reconstruction')
                            profile.wrap(joint, 'build_A_for_DALS_torch', 'CE_design')
                            profile.wrap(feedback, 'decoder_messages', 'feedback_LDPC')
                            value = run_arm(receiver, code, observed, arm)
                        value.update(operator_profile=profile.rows, resource_counts=receiver_resources(value))
                        return value
                    value, record = run.call('F', dict(block=b, snr=snr, split=exo[b]['split'], arm=name), full,
                        lambda v: offline_scores(v, raw, v['H']), dict(provenance, configuration=arm))
                    assert hashes(observed) == before
                    check_full(value, old_full, old_stop, target, expected, name)
                    print(json.dumps(dict(block=b, snr=snr, arm=name, calls=run.counts, scores=record['scores'])), flush=True)
        for entry in list(run.records):
            _, state = verified_record(entry, root)
            raw = load_state(exo[entry['block']]['state'])
            run.call('D', {k: entry[k] for k in ('block', 'snr', 'split', 'arm')},
                lambda: replay_decode(code, state, 1., 20., 50), lambda v: decoder_scores(v, raw),
                dict(source_record_sha256=entry['sha256']))
        summary = dict(status='COMPLETE', calls=run.counts, records=run.records,
            source_sha256=sha(manifest), contract_sha256=sha(contract), script_sha256=sha(Path(__file__)), scope=c['scope'])
        summary['raw_checks'] = audit_records(summary)
        guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json', summary)
    except BaseException as exc:
        run.fail(exc); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--mode', choices=['run', 'audit'], default='run')
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--script-sha256', required=True)
    main(p.parse_args())
