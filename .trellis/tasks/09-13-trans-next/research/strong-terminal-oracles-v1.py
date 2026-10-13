"""Controlled saved-terminal H interventions, with exact baseline and raw replay."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace


def main(args):
    root = args.root
    source = root/'source-receiver-domain-v2'
    sys.path.insert(0, str(source))
    import numpy as np
    import torch
    from afdm_sp_joint_unrolled import direction_receiver as receiver
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes, load_state
    from afdm_sp_joint_unrolled.e1_ldpc import build_code
    from afdm_sp_joint_unrolled.light_gap_replay import (
        CODE_KEYS, LightRun, setup_guard, verified_record, decoder_scores, replay_decode)
    from afdm_sp_joint_unrolled.supplement_profile import OperatorProfile
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import (
        FIELDS, terminal_inputs, check_value)
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays

    manifest = source/'source-manifest.json'
    contract = root/'contracts/strong-terminal-oracles-v1.json'
    c = json.loads(contract.read_text())
    assert sha(manifest) == '2fd0beb6efd405e7c7921a79c8e209f87203322bed67bc41c7f6cde4a6bb9dd9'
    assert sha(contract) == args.contract_sha256 and sha(Path(__file__)) == args.script_sha256
    assert c['schema'] == c['tag'] == 'strong-terminal-oracles-v1'
    assert c['bounds'] == dict(T=96, D=96, seconds=600)
    assert c['blocks'] == list(range(32)) and c['snrs'] == [7]
    assert c['arms'] == ['EST', 'SUPPORT_ORACLE', 'TRUE_H']
    assert (c['temperature'], c['bp_iterations'], c['ldpc_maxiter'], c['clip']) == (2., 20, 50, 20.)
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    run = LightRun(root/'runs'/c['tag'], 'diagnostic', c['bounds'], c['output_bytes'], guard)
    try:
        cache = run.out/'code-cache'
        cache.mkdir()
        code = build_code(cache_dir=cache)
        run.meter.adopt_tree(cache)
        inputs = json.loads((root/'runs/refs-v1/development/summary.json').read_text())
        environment = json.loads((root/'runs/refs-v1/development/environment.json').read_text())
        references = json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
        projections = json.loads((root/'runs/strong-support-decomposition-v1/analysis/summary.json').read_text())
        assert inputs['status'] == references['status'] == projections['status'] == 'COMPLETE'
        assert hashes({k: code[k] for k in CODE_KEYS}) == environment['code_identity']
        exo = {r['block']: r for r in inputs['exogenous']}
        entries = [r for r in references['records'] if r['snr'] == 7 and r['arm'] == 'BP_RETAIN']
        refs = {r['block']: r for r in entries}
        proj = {r['block']: r for r in projections['records']}
        assert len(entries) == len(projections['records']) == 32
        assert set(exo) == set(refs) == set(proj) == set(range(32))

        def get_inputs(block, arm):
            raw, observed, old, expected = terminal_inputs(c, exo, refs[block], block, 7)
            record, projection = verified_record(proj[block], root)
            assert record['reference_record_sha256'] == refs[block]['sha256']
            assert record['exogenous_hashes'] == exo[block]['hashes']
            np.testing.assert_array_equal(projection['support_ids'], old['support'])
            H = {'EST': old['H'], 'SUPPORT_ORACLE': projection['projected_H'], 'TRUE_H': raw['H']}[arm]
            expected.update(H=H, z=observed['y']-H@observed['pilot'])
            return raw, observed, old, expected

        run.write('environment.json', dict(code_identity=environment['code_identity'],
            source_sha256=sha(manifest), device='cpu', threads=1, scope=c['scope']))
        for block in c['blocks']:
            for arm in c['arms']:
                raw, observed, old, expected = get_inputs(block, arm)
                before = hashes(expected)
                prior = expected['last_check_prior']
                def terminal():
                    edge_counts = []
                    with OperatorProfile(torch.device('cpu')) as profile:
                        value = receiver.terminal_decode(expected['z'], expected['H'],
                            expected['sigma2_terminal'], observed['constellation'], code,
                            audit=True, code_prior=prior, bp_temperature=2.,
                            bp_iterations=20, edge_count_observer=edge_counts.append)
                    assert len(edge_counts) == 1 and edge_counts[0] > 0
                    value.update({k: v.copy() if isinstance(v, np.ndarray) else v for k, v in expected.items()})
                    value.update(operator_profile=profile.rows,
                        resource_counts=dict(T=1, BP=1, BP_iterations=20, LDPC=1, CE=0),
                        actual_edges=edge_counts[0], scope=c['scope'], baseline_eligible=False)
                    return value
                value, record = run.call('T', dict(block=block, snr=7, split=2, arm=arm), terminal,
                    lambda v: decoder_scores(v, raw), dict(reference_record_sha256=refs[block]['sha256'],
                    projection_record_sha256=proj[block]['sha256'], terminal_input_hashes=before,
                    observed_hashes=hashes(observed), truth_access='external scoring' if arm == 'EST' else 'explicit oracle H'))
                check_value(value, expected, 'RETAIN')
                assert hashes(expected) == before
                if arm == 'EST':
                    for field in FIELDS:
                        np.testing.assert_array_equal(value[field], old[field])
                print(json.dumps(dict(block=block, arm=arm, scores=record['scores'], calls=run.counts)), flush=True)

        # Verify all original numeric payloads after collection. D is charged separately.
        terminal_entries = list(run.records)
        rows = []
        arrays = 0
        for entry in terminal_entries:
            run.check()
            record, value = verified_record(entry, root)
            block, arm = entry['block'], entry['arm']
            raw, observed, old, expected = get_inputs(block, arm)
            reservation = json.loads(Path(entry['record']).with_name(record['token']+'-reserve.json').read_text())
            assert all(reservation[k] == record[k] for k in ('token', 'block', 'snr', 'split', 'arm', 'kind'))
            assert record['terminal_input_hashes'] == hashes(expected)
            assert record['observed_hashes'] == hashes(observed)
            assert record['reference_record_sha256'] == refs[block]['sha256']
            assert record['projection_record_sha256'] == proj[block]['sha256']
            check_value(value, expected, 'RETAIN')
            arrays += finite_arrays(value)
            scores = decoder_scores(value, raw)
            assert scores == record['scores'] == entry['scores']
            if arm == 'EST':
                for field in FIELDS:
                    np.testing.assert_array_equal(value[field], old[field])
            identity = {k: entry[k] for k in ('block', 'snr', 'split', 'arm')}
            decoded, replay_record = run.call('D', identity,
                lambda: replay_decode(code, value, 1., 20., 50),
                lambda v: decoder_scores(v, raw), dict(terminal_record_sha256=entry['sha256']))
            assert replay_record['scores'] == scores
            rows.append(dict(block=block, arm=arm, scores=scores, actual_edges=value['actual_edges']))
        for entry in run.records[96:]:
            record, value = verified_record(entry, root)
            raw = load_state(exo[entry['block']]['state'])
            assert decoder_scores(value, raw) == record['scores'] == entry['scores']
            arrays += finite_arrays(value)
        assert run.counts == dict(T=96, D=96) and len(run.records) == 192
        guard.verify()
        assert sha(Path(__file__)) == args.script_sha256
        run.meter.verify()
        run.write('summary.json', dict(status='COMPLETE', calls=run.counts, records=run.records,
            rows=rows, raw_readback_records=192, finite_arrays=arrays, exact_EST=32,
            source_sha256=sha(manifest), contract_sha256=args.contract_sha256,
            script_sha256=args.script_sha256, wall_seconds=time.time()-run.started, scope=c['scope']))
        print(json.dumps(dict(status='COMPLETE', calls=run.counts, raw_readback_records=192)), flush=True)
    except BaseException as exc:
        run.fail(exc)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--script-sha256', required=True)
    main(p.parse_args())
