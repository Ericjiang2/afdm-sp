"""Saved G1 terminal pilot-only interventions; frozen detector and prior."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(args):
    root = args.root
    source = root / 'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import direction_receiver as receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import (
        CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores,
        replay_decode, check_decode_identity)
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import FIELDS, check_value
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.trans_next_stop_run import check_calls

    contract = root / 'contracts' / (args.tag + '.json')
    c = json.loads(contract.read_text()); manifest = source / 'source-manifest.json'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert sha(manifest) == c['source_sha256'] == '5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['schema'] == 'e1a-pilot-response-v1' and c['tag'] == args.tag
    assert c['stage'] in ('engineering', 'development')
    engineering = c['stage'] == 'engineering'
    assert c['blocks'] == ([0, 20] if engineering else [b for b in range(32) if b not in (0, 20)])
    assert c['snrs'] == [7, 8] and c['arms'] == ['A0', 'A_ORACLE']
    assert c['device'] == 'cpu' and c['threads'] == 1
    count = len(c['blocks']) * 4
    assert c['bounds'] == dict(T=count-int(engineering), D=count, seconds=120 if engineering else 600)
    assert (c['temperature'], c['bp_iterations'], c['ldpc_maxiter'], c['clip']) == (1., 20, 50, 20.)
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, audit_path in c['audited_inputs'].items():
        admission = json.loads((root / audit_path).read_text())
        assert admission['status'] == 'PASS' and admission['summary_sha256'] == sha(root / summary_path)
    if not engineering:
        admission = json.loads((root / c['engineering_audit']).read_text())
        assert admission['source_sha256'] == sha(manifest) and admission['script_sha256'] == sha(Path(__file__))
        assert admission['exact_A0'] == 4 and admission['saved_records'] == 16
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root / 'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    index = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in upstream['records']}
    assert len(index) == len(upstream['records']) == 288
    env = json.loads((root / 'runs/refs-v1/development/environment.json').read_text())
    out = root / 'runs' / args.tag / c['stage']

    def inputs(block, snr, arm):
        pe = index['A', block, 7, 'G1_PROPAGATION']
        _, physical = verified_record(pe, root)
        raw, _ = reuse_at_snr(physical['raw'], physical['diagnostics'], snr)
        observed = {k: np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        observed['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        ref = index['F', block, snr, 'G1_FULL']
        record, old = verified_record(ref, root)
        assert record['observed_hashes'] == hashes(observed)
        assert record['physical_record_sha256'] == pe['sha256'] and ref['split'] == pe['split']
        detail = check_calls(old)
        assert detail['operators']['terminal_BP'] == 1 and detail['resources']['LDPC_calls'] == 4
        assert old['terminal_check_prior_consumed'] and old['terminal_controls_consumed']
        assert old['terminal_bp_temperature'] == 1. and old['terminal_variance_source'] == 'physical'
        assert not old['terminal_scale_applied'] and old['sigma2_terminal'] == float(observed['sigma2'])
        checkpoints = [r for r in old['code_feedback_records'] if r['stage'] == 'decoder']
        assert [r['iteration'] for r in checkpoints] == [1, 4, 7]
        last = checkpoints[-1]
        np.testing.assert_array_equal(last['prior_after'], np.clip(last['raw_check_extrinsic'], -20., 20.))
        # Hc retains the original dtype and multiplication order for exact A0.
        cancellation = (old['H'] if arm == 'A0' else raw['H']) @ observed['pilot']
        expected = dict(H=old['H'], z=observed['y']-cancellation,
            cancellation=cancellation, sigma2_terminal=old['sigma2_terminal'],
            last_check_prior=last['prior_after'])
        provenance = dict(reference_record_sha256=ref['sha256'], physical_record_sha256=pe['sha256'],
            terminal_input_hashes=hashes(expected), observed_hashes=hashes(observed),
            temperature=1., truth_access='external scoring only' if arm == 'A0' else 'explicit truth pilot response only; external scoring')
        return raw, observed, old, expected, provenance, ref['split']

    def check_terminal(value, old, expected, arm):
        check_value(value, expected, 'RETAIN')
        assert value['baseline_eligible'] is False and value['scope'] == c['scope']
        graph = value['graphs'][0]
        assert len(value['graphs']) == 1 and graph['stage'] == 'final_bp'
        assert graph['H_hash'] == array_hash(np.asarray(old['H'], dtype=np.complex128))
        assert graph['threshold'] == 1e-4 and graph['dtype'] == 'torch.complex128'
        assert graph['edges'] == value['actual_edges'] == old['graphs'][-1]['edges']
        assert graph['edges'] == int(np.count_nonzero(abs(np.asarray(old['H'], dtype=np.complex128)) >= 1e-4))
        if arm == 'A0':
            for key in (*FIELDS, 'raw_llr'):
                np.testing.assert_array_equal(value[key], old[key])
            assert hashes(value['finite_message']) == hashes(old['finite_message'])

    def audit(summary):
        assert summary['status'] == 'COMPLETE' and summary['calls'] == dict(T=count-int(engineering), D=count)
        assert summary['recovered_calls'] == dict(T=int(engineering), D=0)
        assert summary['source_sha256'] == sha(manifest) and summary['script_sha256'] == args.script_sha256
        assert summary['contract_sha256'] == args.contract_sha256
        records = {(r['kind'], r['block'], r['snr'], r['arm']): r for r in summary['records']}
        wanted = {(k, b, s, a) for k in ('T', 'D') for b in c['blocks'] for s in c['snrs'] for a in c['arms']}
        assert set(records) == wanted and len(records) == len(summary['records']) == 2 * count
        arrays = 0; rows = []
        for b in c['blocks']:
            for snr in c['snrs']:
                for arm in c['arms']:
                    raw, observed, old, expected, provenance, split = inputs(b, snr, arm)
                    entry = records['T', b, snr, arm]
                    record, value = verified_record(entry, root)
                    assert entry['split'] == split
                    for key, item in provenance.items(): assert record[key] == item
                    check_terminal(value, old, expected, arm)
                    scores = decoder_scores(value, raw)
                    assert scores == record['scores'] == entry['scores']
                    de = records['D', b, snr, arm]
                    dr, decoded = verified_record(de, root)
                    assert dr['terminal_record_sha256'] == entry['sha256'] and de['split'] == split
                    check_decode_identity(decoded, value)
                    np.testing.assert_array_equal(decoded['llr'], value['llr'])
                    assert decoder_scores(decoded, raw) == dr['scores'] == de['scores'] == scores
                    for e, r in ((entry, record), (de, dr)):
                        reservation = json.loads(Path(e['record']).with_name(r['token']+'-reserve.json').read_text())
                        assert all(reservation[k] == r[k] == e[k] for k in ('block', 'snr', 'split', 'arm', 'kind'))
                        assert reservation['token'] == r['token']
                    arrays += finite_arrays(value) + finite_arrays(decoded)
                    rows.append(dict(block=b, snr=snr, arm=arm, scores=scores,
                        actual_edges=value['actual_edges'], reference_record_sha256=provenance['reference_record_sha256']))
        return dict(rows=rows, arrays=arrays, exact_A0=count//2, saved_records=count*2)

    if args.mode == 'audit':
        started = time.time()
        end = json.loads((root / 'evidence' / (args.tag+'-exit.json')).read_text())
        assert end['exit_code'] == 0 and not end['timed_out']
        summary = json.loads((out / 'summary.json').read_text())
        result = audit(summary); assert result == summary['raw_checks']; guard.verify()
        result.update(status='PASS', summary_sha256=sha(out/'summary.json'), source_sha256=sha(manifest),
            script_sha256=args.script_sha256, contract_sha256=args.contract_sha256,
            wall_seconds=time.time()-started, new_F_T_D_A_calls=0, scope=c['scope'],
            independence='main-session self-review; weak')
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f: json.dump(result, f, indent=2)
        print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
        return

    run = LightRun(root/'runs'/args.tag, c['stage'], c['bounds'], c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'; cache.mkdir(); code = build_code(cache_dir=cache); run.meter.adopt_tree(cache)
        assert hashes({k:code[k] for k in CODE_KEYS}) == env['code_identity']
        run.write('environment.json', dict(code_identity=env['code_identity'], source_sha256=sha(manifest),
            numpy=np.__version__, torch=torch.__version__, device='cpu', threads=1, scope=c['scope']))
        for b in c['blocks']:
            for snr in c['snrs']:
                for arm in c['arms']:
                    raw, observed, old, expected, provenance, split = inputs(b, snr, arm)
                    def terminal():
                        edge_counts = []
                        with OperatorProfile(torch.device('cpu')) as profile:
                            value = receiver.terminal_decode(expected['z'], expected['H'], expected['sigma2_terminal'],
                                observed['constellation'], code, audit=True, code_prior=expected['last_check_prior'],
                                bp_temperature=1., bp_iterations=20, edge_count_observer=edge_counts.append)
                        assert len(edge_counts) == 1 and edge_counts[0] > 0
                        value.update(expected, operator_profile=profile.rows, actual_edges=edge_counts[0],
                            resource_counts=dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0),
                            baseline_eligible=False, scope=c['scope'])
                        return value
                    identity = dict(block=b, snr=snr, split=split, arm=arm)
                    if engineering and (b, snr, arm) == (0, 7, 'A0'):
                        entry = c['recovered_entry']
                        record, value = verified_record(entry, root)
                        assert all(entry[k] == v for k, v in identity.items())
                        assert all(record[k] == v for k, v in provenance.items())
                        assert decoder_scores(value, raw) == entry['scores'] == record['scores']
                        run.records.append(entry)
                    else:
                        value, record = run.call('T', identity, terminal, lambda v: decoder_scores(v, raw), provenance)
                        entry = run.records[-1]
                    check_terminal(value, old, expected, arm)
                    assert hashes(expected) == provenance['terminal_input_hashes']
                    run.call('D', identity, lambda: replay_decode(code, value, 1., 20., 50),
                        lambda v: decoder_scores(v, raw), dict(terminal_record_sha256=entry['sha256']))
                    print(json.dumps(dict(block=b, snr=snr, arm=arm, scores=entry['scores'], calls=run.counts)), flush=True)
        summary = dict(status='COMPLETE', calls=run.counts, recovered_calls=dict(T=int(engineering), D=0),
            records=run.records, source_sha256=sha(manifest),
            script_sha256=args.script_sha256, contract_sha256=args.contract_sha256, scope=c['scope'])
        summary['raw_checks'] = audit(summary)
        guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time()-run.started
        run.write('summary.json', summary)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--mode', choices=['run', 'audit'], default='run')
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--script-sha256', required=True)
    main(p.parse_args())
