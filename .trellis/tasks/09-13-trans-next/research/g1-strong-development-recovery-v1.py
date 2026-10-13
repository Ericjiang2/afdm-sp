"""Resume missing G1 calls while preserving all completed frozen records."""
import argparse
import ast
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def call_with_reuse(run, recovered, consumed, kind, identity, fn, score, provenance, load):
    """Reuse only an exact committed identity; never invoke its computation."""
    key = (kind, identity['block'], identity['snr'], identity['arm'])
    if key not in recovered:
        return run.call(kind, identity, fn, score, provenance)
    if key in consumed:
        raise ValueError('completed identity requested twice')
    entry = recovered[key]
    record, value = load(entry)
    if record['kind'] != kind or any(record[k] != v for k, v in identity.items()):
        raise ValueError('recovery identity mismatch')
    # Scope prose is newly qualified by error accounting. All operational
    # provenance, including physical record and observation hashes, is exact.
    if any(record[k] != v for k, v in provenance.items() if k != 'scope'):
        raise ValueError('recovery provenance mismatch')
    if score(value) != record['scores'] or record['scores'] != entry['scores']:
        raise ValueError('recovery scores mismatch')
    run.check()
    consumed.add(key)
    run.records.append(entry)
    return value, record


def main(args):
    root = args.root
    source = root/'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import classical_joint_unrolled as joint, supplement_feedback as feedback
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes, load_state, offline_scores
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    from afdm_sp_joint_unrolled.budgeted_support_eval import build_receiver
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineReceiver
    from afdm_sp_joint_unrolled.e1_ldpc import build_code, decode_llr, extract_info
    from afdm_sp_joint_unrolled.direction_data import validate_observed
    from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores, check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import run_arm, receiver_resources
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_receiver_state, check_prefix, check_calls
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import check_finite_prior_message
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation, physical_channel_matrix, reuse_at_snr
    from afdm_sp_joint_unrolled.supplement_pilots import transform, propagate_cpp

    contract = root/'contracts'/(args.tag+'.json')
    c = json.loads(contract.read_text()); manifest = source/'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == 'g1-strong-reference-v1' and c['stage'] == 'development'
    assert c['tag'] == args.tag == 'g1-strong-development-recovery-v1'
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else list(range(32))) and c['snrs'] == [7, 8]
    names = ['G1_FULL', 'G1_REPEAT', 'G1_STOP'] if engineering else ['G1_FULL', 'G1_STOP']
    assert c['arms'] == names and c['device'] == 'cpu' and c['threads'] == 1
    n = len(c['blocks']); f = n*2*len(names)
    assert c['bounds'] == dict(A=24, F=97, D=128, seconds=1680)
    assert c['logical_calls'] == dict(A=n, F=f, D=f)
    assert c['recovered_calls'] == dict(A=8, F=31, D=0)
    assert c['prefix_length'] == 102 and sha(c['checkpoint_path']) == c['checkpoint_sha256']
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        audit = json.loads((root/audit_path).read_text())
        assert audit['status'] == 'PASS' and audit['summary_sha256'] == sha(root/summary_path)
    qualification = json.loads((root/c['generator_qualification']).read_text())
    assert qualification['status'] == 'PASS' and qualification['source_sha256'] == sha(manifest)
    assert qualification['operator_evidence_sha256'] == sha(root/c['generator_operator_evidence'])
    if not engineering:
        admission = json.loads((root/c['engineering_audit']).read_text())
        assert admission['status'] == 'PASS' and admission['source_sha256'] == sha(manifest)
        assert admission['script_sha256'] == c['qualified_script_sha256']
        assert admission['summary_sha256'] == sha(root/c['engineering_summary'])
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    inputs = json.loads((root/'runs/refs-v1/development/summary.json').read_text())
    env = json.loads((root/'runs/refs-v1/development/environment.json').read_text())
    old = json.loads((root/'runs/terminal-controls-development-recovery-v1/development/summary.json').read_text())
    exo = {r['block']: r for r in inputs['exogenous']}
    refs = {(r['block'], r['snr'], r['arm']): r for r in old['records'] if r['kind'] == 'F'}
    assert len(exo) == 32 and len(refs) == 128
    system = _make_config_a(1024, 2., 8, 10., 4.)
    assert (system.N_total, system.l_max_cap, system.k_max_cap, system.rho) == (1024, 102, 2, .5)
    out = root/'runs'/args.tag/c['stage']
    parent_script = root / c['qualified_script']
    assert sha(parent_script) == c['qualified_script_sha256']
    parent_contract = json.loads((root/c['parent_contract']).read_text())
    for key in ('device', 'threads', 'blocks', 'snrs', 'arms', 'prefix_length',
                'checkpoint_path', 'checkpoint_sha256', 'source_sha256'):
        assert c[key] == parent_contract[key], key
    # These scientific functions are unchanged; only record orchestration differs.
    original_functions = {node.name: ast.dump(node, include_attributes=False)
        for node in ast.walk(ast.parse(parent_script.read_text())) if isinstance(node, ast.FunctionDef)}
    current_functions = {node.name: ast.dump(node, include_attributes=False)
        for node in ast.walk(ast.parse(Path(__file__).read_text())) if isinstance(node, ast.FunctionDef)}
    for name in ('load_g0', 'observed', 'check_physical', 'check_receiver', 'generate', 'full', 'exact_decode'):
        assert original_functions[name] == current_functions[name], name
    stopped = root/'runs/g1-strong-development-v1/development'
    end = json.loads((root/c['parent_exit']).read_text())
    assert end['exit_code'] == -2 and not end['timed_out'] and not (stopped/'summary.json').exists()
    assert end['wall_seconds'] + c['job_timeout_seconds'] < parent_contract['bounds']['seconds']
    assert {str(p.relative_to(root)) for p in stopped.rglob('*') if p.is_file()} == set(c['parent_files'])
    recovered = {}; recovered_arrays = 0
    for item in c['recovery_records']:
        path = root/item['path']; assert sha(path) == item['sha256']
        record = json.loads(path.read_text())
        entry = {k: record[k] for k in ('kind', 'block', 'snr', 'split', 'arm', 'seconds', 'CPU_seconds', 'scores')}
        entry.update(record=str(path), sha256=item['sha256'])
        _, value = verified_record(entry, root)
        recovered_arrays += finite_arrays(value)
        key = (entry['kind'], entry['block'], entry['snr'], entry['arm'])
        assert key not in recovered and entry['kind'] in ('A', 'F')
        recovered[key] = entry
    assert {kind: sum(k[0] == kind for k in recovered) for kind in ('A', 'F', 'D')} == c['recovered_calls']
    consumed = set()

    def load_g0(b):
        raw = load_state(exo[b]['state'])
        assert hashes({k: raw[k] for k in exo[b]['hashes']}) == exo[b]['hashes']
        assert raw['params']['c1'] == system.c1 and raw['params']['c2'] == system.c2
        assert len(raw['params']['g_i']) == 8 and raw['sigma2'] == 10**(-.7)
        return raw

    def observed(value, snr):
        raw, diag = reuse_at_snr(value['raw'], value['diagnostics'], snr)
        # Use the saved direct time-domain CPP signal, not H@x's last-bit variant.
        obs = {k: np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        obs['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        for item in obs.values():item.flags.writeable = False
        validate_observed(obs, 1024)
        return obs, raw, diag

    def check_physical(value, original):
        raw, diag = value['raw'], value['diagnostics']
        for key in ('pilot', 'data', 'noise', 'coded', 'info', 'uncoded'):
            np.testing.assert_array_equal(raw[key], original[key])
        for key in ('l_i', 'k_real', 'g_i', 'g_i_raw', 'fro_scale'):
            np.testing.assert_array_equal(raw['params'][key], original['params'][key])
        assert raw['params']['representation'] == diag['generator'] == 'physical_cpp_untruncated'
        assert diag['gain_normalization'] == 'reuse_g0_physical_gains_without_rescaling'
        assert diag['transmit_normalization'] == 'none' and diag['prefix_length'] == 102
        assert 'P_actual' not in raw['params'] and 'chan_coef_exp' not in raw['params']
        np.testing.assert_array_equal(raw['g0_reference']['H'], original['H'])
        params = raw['params']
        h = physical_channel_matrix(1024, system.c1, system.c2, params['l_i'], params['k_real'], params['g_i'], prefix_length=102)
        # NumPy exp/FFT alignment may change last bits; physics validation is a
        # predeclared relative tolerance, never a receiver/decoded-bit tolerance.
        h_error = float(np.linalg.norm(h-raw['H'])/np.linalg.norm(raw['H']))
        assert h_error <= 1e-10
        errors = []
        for signal in (raw['pilot']+raw['data'], np.exp(.137j*np.arange(1024))):
            direct = transform(propagate_cpp(transform(signal, system.c1, system.c2, inverse=True),
                system.c1, params['l_i'], params['k_real'], params['g_i'], prefix_length=102), system.c1, system.c2)
            error = float(np.linalg.norm(raw['H']@signal-direct)/max(1., np.linalg.norm(direct)))
            assert error <= 1e-10
            errors.append(error)
        np.testing.assert_allclose(raw['noiseless'], raw['H']@(raw['pilot']+raw['data']), rtol=1e-10, atol=1e-10)
        energy = float(np.vdot(raw['H'], raw['H']).real/1024)
        assert abs(energy-diag['channel_energy_per_dimension']) <= 1e-12*max(1., energy)
        assert array_hash(params['g_i']) == diag['physical_gains_sha256']
        assert array_hash(original['H']) == diag['g0_reference_H_sha256']
        assert diag['waveform']['passes_declared_simulation_power_gate']
        return dict(matrix_regeneration_relative_error=h_error, independent_signal_relative_errors=errors,
            physical_channel_energy=energy, finite_dictionary_projection_nmse=diag['finite_dictionary_projection_nmse'],
            g0_operator_nmse=diag['g0_reference_operator_nmse'])

    def check_receiver(value, obs, full=None):
        detail = check_calls(value)
        terminal = value.get('terminal_executed', True)
        assert value['terminal_bp_temperature'] == 1. and value['terminal_variance_source'] == 'physical'
        assert value['terminal_controls_consumed'] == value['terminal_check_prior_consumed'] == terminal
        assert not value['terminal_scale_applied']
        if full is not None:detail.update(check_prefix(value, full))
        if terminal:
            assert value['sigma2_terminal'] == float(obs['sigma2'])
            decoders = [r for r in value['code_feedback_records'] if r['stage'] == 'decoder']
            assert [r['iteration'] for r in decoders] == [1, 4, 7]
            check_finite_prior_message(value, decoders[-1]['prior_after'])
            graph = value['graphs'][-1]
            assert graph['H_hash'] == array_hash(value['H'].astype(np.complex128))
        else:
            assert value['sigma2_terminal'] is None and 'finite_message' not in value
        return detail

    def audit_records(summary):
        assert summary['calls'] == c['logical_calls']
        assert summary['new_calls'] == {k:v for k,v in c['bounds'].items() if k != 'seconds'}
        assert summary['recovered_calls'] == c['recovered_calls']
        assert summary['source_sha256'] == sha(manifest) and summary['contract_sha256'] == sha(contract)
        assert summary['script_sha256'] == sha(Path(__file__))
        index = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in summary['records']}
        assert len(index) == len(summary['records']) == n+2*f
        rows, physical = [], []; arrays = 0
        for b in c['blocks']:
            original = load_g0(b)
            entry = index['A', b, 7, 'G1_PROPAGATION']
            record, generated = verified_record(entry, root)
            assert record['g0_exogenous_hashes'] == exo[b]['hashes']
            physical.append(dict(block=b, **check_physical(generated, original)))
            arrays += finite_arrays(generated)
            for snr in c['snrs']:
                obs, raw, diag = observed(generated, snr)
                _, full = verified_record(index['F', b, snr, 'G1_FULL'], root)
                for name in names:
                    entry = index['F', b, snr, name]
                    record, value = verified_record(entry, root)
                    assert record['observed_hashes'] == hashes(obs)
                    assert record['physical_record_sha256'] == index['A', b, 7, 'G1_PROPAGATION']['sha256']
                    detail = check_receiver(value, obs, full if name == 'G1_STOP' else None)
                    if name == 'G1_REPEAT':same_receiver_state(value, full)
                    scores = offline_scores(value, raw, value['H'])
                    assert scores == record['scores'] == entry['scores']
                    reference = refs[b, snr, 'UNTEMPERED_STOP' if name == 'G1_STOP' else 'UNTEMPERED']
                    old_record, old_value = verified_record(reference, root)
                    assert offline_scores(old_value, original, old_value['H']) == old_record['scores'] == reference['scores']
                    rows.append(dict(block=b, snr=snr, arm=name, scores=scores, g0_reference_scores=reference['scores'],
                        g0_reference_record_sha256=reference['sha256'], physical_model=diag, **detail))
                    arrays += finite_arrays(value)
                    dr, decoded = verified_record(index['D', b, snr, name], root)
                    assert dr['source_record_sha256'] == entry['sha256']
                    check_decode_identity(decoded, value)
                    np.testing.assert_array_equal(decoded['llr'], value['llr'])
                    assert decoder_scores(decoded, raw) == dr['scores']
        return dict(rows=rows, physical_checks=physical, arrays=arrays, saved_records=len(index))

    if args.mode == 'audit':
        started = time.time(); end = json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        path = out/'summary.json'; summary = json.loads(path.read_text()); assert summary['status'] == 'COMPLETE'
        details = audit_records(summary)
        assert details == summary['raw_checks']
        guard.verify()
        result = dict(status='PASS', **details, source_sha256=sha(manifest), script_sha256=sha(Path(__file__)),
            summary_sha256=sha(path), contract_sha256=sha(contract), wall_seconds=time.time()-started,
            new_receiver_or_decoder_calls=0, repeated_physics_checks=n, scope=c['scope'], independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f_out:json.dump(result, f_out, indent=2)
        print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'physical_checks')}))
        return

    run = LightRun(root/'runs'/args.tag, c['stage'], c['bounds'], c['output_bytes'], guard)
    def recover_call(kind, identity, fn, score, provenance):
        return call_with_reuse(run, recovered, consumed, kind, identity, fn, score, provenance,
                               lambda entry: verified_record(entry, root))
    try:
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        assert hashes({k: code[k] for k in CODE_KEYS}) == env['code_identity']
        model = build_receiver(c['checkpoint_path'], system, 1024, 'cpu', receiver_shell='direct40', active_cap=40)
        receiver = BaselineReceiver(model, code, 'B0-p2-s0.5', system=system, initial_lstsq_driver='gels')
        run.write('environment.json', dict(code_identity=env['code_identity'], device='cpu', threads=1,
            numpy=np.__version__, torch=torch.__version__, source_sha256=sha(manifest),
            physical_scope='integer sample delays, continuous normalized Doppler, untruncated CPP; no time scaling or pulse shaping'))
        for b in c['blocks']:
            original = load_g0(b)
            def generate():
                raw, diag = physical_observation(original, system, prefix_length=102)
                return dict(raw=raw, diagnostics=diag)
            generated, record = recover_call('A', dict(block=b, snr=7, split=exo[b]['split'], arm='G1_PROPAGATION'),
                generate, lambda v: {}, dict(g0_exogenous_hashes=exo[b]['hashes'], scope=c['scope']))
            physical_entry = run.records[-1]
            check_physical(generated, original)
            assert hashes({k: original[k] for k in exo[b]['hashes']}) == exo[b]['hashes']
            for snr in c['snrs']:
                obs, raw, diag = observed(generated, snr); before = hashes(obs); full_value = None
                for name in names:
                    fb = dict(refresh_checkpoints=[4, 7], retain_messages=True)
                    if name == 'G1_STOP':fb['stop_on_valid_codeword'] = True
                    arm = dict(name=name, receiver=dict(terminal_check_prior='retain', terminal_bp_temperature=1., terminal_variance_source='physical'), feedback=fb)
                    def full():
                        with OperatorProfile(torch.device('cpu')) as profile:
                            profile.wrap(joint, 'reconstruct_H_torch', 'dense_H_reconstruction')
                            profile.wrap(joint, 'build_A_for_DALS_torch', 'CE_design')
                            profile.wrap(feedback, 'decoder_messages', 'feedback_LDPC')
                            value = run_arm(receiver, code, obs, arm)
                        value.update(operator_profile=profile.rows, resource_counts=receiver_resources(value))
                        return value
                    value, record = recover_call('F', dict(block=b, snr=snr, split=exo[b]['split'], arm=name), full,
                        lambda v: offline_scores(v, raw, v['H']), dict(observed_hashes=before, configuration=arm,
                            physical_record_sha256=physical_entry['sha256'], scope=c['scope']))
                    assert hashes(obs) == before
                    check_receiver(value, obs, full_value if name == 'G1_STOP' else None)
                    if name == 'G1_FULL':full_value = value
                    if name == 'G1_REPEAT':same_receiver_state(value, full_value)
                    print(json.dumps(dict(block=b, snr=snr, arm=name, calls=run.counts, scores=record['scores'])), flush=True)
        index = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in run.records}
        for entry in list(run.records):
            if entry['kind'] != 'F':continue
            _, state = verified_record(entry, root)
            _, generated = verified_record(index['A', entry['block'], 7, 'G1_PROPAGATION'], root)
            def exact_decode():
                llr = np.asarray(state['llr']).copy()
                assert llr.shape == (code['n'],) and not np.iscomplexobj(llr) and np.isfinite(llr).all()
                if state.get('terminal_executed') is False:
                    np.testing.assert_array_equal(llr, state['checkpoint_stop']['decoder_input'])
                else:assert np.max(abs(llr)) <= 20.
                decoded, ok = decode_llr(code, llr, maxiter=50)
                value = dict(llr=llr, decoded=decoded, info_hat=extract_info(code, decoded), decode_ok=bool(ok))
                check_decode_identity(value, state)
                return value
            run.call('D', {k: entry[k] for k in ('block', 'snr', 'split', 'arm')}, exact_decode,
                lambda v: decoder_scores(v, generated['raw']), dict(source_record_sha256=entry['sha256']))
        assert consumed == set(recovered)
        assert run.counts == {k:v for k,v in c['bounds'].items() if k != 'seconds'}
        logical_calls = {kind:sum(r['kind']==kind for r in run.records) for kind in ('A','F','D')}
        summary = dict(status='COMPLETE', calls=logical_calls, new_calls=run.counts,
            recovered_calls=c['recovered_calls'], parent_failed_reservation_preserved=True,
            recovered_finite_arrays=recovered_arrays, records=run.records,
            source_sha256=sha(manifest), contract_sha256=sha(contract), script_sha256=sha(Path(__file__)), scope=c['scope'])
        summary['raw_checks'] = audit_records(summary)
        guard.verify(); run.meter.verify(); summary['wall_seconds'] = time.time()-run.started
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
