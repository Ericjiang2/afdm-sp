"""Read saved H interventions and decoder identities after the producer exits."""
import hashlib
import json
from pathlib import Path
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root):
    started = time.time()
    source = root/'source-receiver-domain-v2'
    manifest = source/'source-manifest.json'
    package = source/'afdm_sp_joint_unrolled'
    assert sha(manifest) == '2fd0beb6efd405e7c7921a79c8e209f87203322bed67bc41c7f6cde4a6bb9dd9'
    assert json.loads(manifest.read_text()) == {str(p.relative_to(package)): sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0, str(source))
    import numpy as np
    from afdm_sp_joint_unrolled.bottleneck_pilot import load_state, hashes, observed_at_snr
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record, decoder_scores, check_decode_identity
    from afdm_sp_joint_unrolled.trans_next_terminal_prior import FIELDS, check_value
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
    tag = 'strong-terminal-oracles-v1'
    path = root/'runs'/tag/'diagnostic/summary.json'
    s = json.loads(path.read_text())
    contract = root/'contracts'/(tag+'.json')
    c = json.loads(contract.read_text())
    end = json.loads((root/'evidence'/(tag+'-exit.json')).read_text())
    assert end['exit_code'] == 0 and not end['timed_out']
    assert s['status'] == 'COMPLETE' and s['calls'] == dict(T=96, D=96)
    assert s['source_sha256'] == sha(manifest) and s['contract_sha256'] == sha(contract)
    assert s['script_sha256'] == sha(root/'evidence'/(tag+'.py'))
    for name, digest in c['old_inputs'].items():
        assert sha(root/name) == digest
    refs = json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
    refs = {r['block']: r for r in refs['records'] if r['snr'] == 7 and r['arm'] == 'BP_RETAIN'}
    exo = json.loads((root/'runs/refs-v1/development/summary.json').read_text())
    exo = {r['block']: r for r in exo['exogenous']}
    proj = json.loads((root/'runs/strong-support-decomposition-v1/analysis/summary.json').read_text())
    proj = {r['block']: r for r in proj['records']}
    assert [r['kind'] for r in s['records']] == ['T']*96+['D']*96
    rows = []
    for block in range(32):
        raw = load_state(exo[block]['state'])
        assert hashes({k: raw[k] for k in exo[block]['hashes']}) == exo[block]['hashes']
        observed = observed_at_snr(raw, 7)
        _, old = verified_record(refs[block], root)
        _, projection = verified_record(proj[block], root)
        checkpoints = [r for r in old['code_feedback_records'] if r['stage'] == 'decoder']
        assert [r['iteration'] for r in checkpoints] == [1, 4, 7]
        prior = np.clip(checkpoints[-1]['raw_check_extrinsic'], -20, 20)
        np.testing.assert_array_equal(prior, old['finite_message']['prior_llr'])
        for a, arm in enumerate(c['arms']):
            index = block*3+a
            entry = s['records'][index]
            assert (entry['block'], entry['snr'], entry['split'], entry['arm']) == (block, 7, 2, arm)
            record, value = verified_record(entry, root)
            H = {'EST': old['H'], 'SUPPORT_ORACLE': projection['projected_H'], 'TRUE_H': raw['H']}[arm]
            expected = dict(H=H, z=observed['y']-H@observed['pilot'],
                sigma2_terminal=old['sigma2_terminal'], last_check_prior=prior)
            check_value(value, expected, 'RETAIN')
            assert record['terminal_input_hashes'] == hashes(expected)
            assert record['observed_hashes'] == hashes(observed)
            assert record['reference_record_sha256'] == refs[block]['sha256']
            assert record['projection_record_sha256'] == proj[block]['sha256']
            assert len(value['graphs']) == 1
            graph = value['graphs'][0]
            assert graph['stage'] == 'final_bp' and graph['dtype'] == 'torch.complex128'
            assert graph['H_hash'] == array_hash(np.asarray(H, dtype=np.complex128))
            assert graph['threshold'] == 1e-4
            edges = int(np.count_nonzero(abs(np.asarray(H, dtype=np.complex128)) >= 1e-4))
            assert graph['edges'] == value['actual_edges'] == edges
            if arm == 'EST':
                for key in FIELDS:
                    np.testing.assert_array_equal(value[key], old[key])
            scores = decoder_scores(value, raw)
            assert scores == record['scores'] == entry['scores']
            dentry = s['records'][96+index]
            assert all(dentry[k] == entry[k] for k in ('block', 'snr', 'split', 'arm'))
            dr, decoded = verified_record(dentry, root)
            assert dr['terminal_record_sha256'] == entry['sha256']
            check_decode_identity(decoded, value)
            np.testing.assert_array_equal(decoded['llr'], value['llr'])
            assert decoder_scores(decoded, raw) == dr['scores'] == dentry['scores'] == scores
            rows.append(dict(block=block, arm=arm, scores=scores, actual_edges=edges))
    assert rows == s['rows']
    result = dict(status='PASS', raw_T=96, raw_D=96, exact_EST=32,
        actual_H_hash_and_edges=96, actual_retained_prior=96, own_LLR_saved_decode_identity=96,
        new_receiver_or_decoder_calls=0, summary_sha256=sha(path), source_sha256=sha(manifest),
        contract_sha256=sha(contract), audit_script_sha256=sha(Path(__file__)),
        wall_seconds=time.time()-started, scope=c['scope'])
    with (root/'evidence'/(tag+'-raw-audit.json')).open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main(Path(sys.argv[1]))
