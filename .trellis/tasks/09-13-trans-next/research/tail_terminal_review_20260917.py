"""Read-only local evidence audit; no receiver calls or remote access."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit(project):
    research = project / '.trellis/tasks/09-13-trans-next/research'
    campaign = project / 'afdm_sp_joint_unrolled/outputs_tail_terminal_v5_20260916'
    result = read(research / 'tail-terminal-v5-results-v1.json')
    contract = read(research / 'tail-terminal-contract-v5.json')
    require(sha(research / 'tail-terminal-contract-v5.json') == result['contract_sha256'], 'contract hash')
    for name, digest in result['artifact_hashes'].items():
        require(sha(campaign / name) == digest, 'artifact hash: ' + name)
    for name, digest in contract['implementation_sha256'].items():
        require(sha(research / name) == digest, 'source hash: ' + name)
    original_contract = read(research / 'tail-terminal-contract-v1.json')
    for version in range(2, 6):
        c = read(research / f'tail-terminal-contract-v{version}.json')
        require({k: v for k, v in c.items() if k not in ('implementation_sha256', 'revision_note', 'contract_revision')} ==
                {k: v for k, v in original_contract.items() if k != 'implementation_sha256'},
                'scientific contract drift')

    points, physical, new_rows, calls = {}, {}, {}, {'T': 0, 'D': 0}
    repeat_scores_equal = True
    for stage, count in [('engineering', 12), ('development', 120)]:
        pp = campaign / f'runs/{stage}/producer/summary.json'
        p = read(pp)
        a = read(campaign / f'runs/{stage}/audit/summary.json')
        require(p['calls'] == {'T': count} and a['calls'] == {'D': count}, 'call count')
        require(a['producer_summary_sha256'] == sha(pp), 'audit producer binding')
        require(p['rows'] == a['rows'] and p['original_rows'] == a['original_rows'], 'audit row mismatch')
        require(len(p['records']) == len(p['rows']) == len(a['records']) == count, 'record inventory')
        calls['T'] += count
        calls['D'] += count
        for row in p['original_rows']:
            key = row['block'], row['snr'], 'ORIGINAL'
            require(key not in points, 'duplicate baseline')
            points[key], physical[key] = row['scores'], row['physical_record_sha256']
        for row, record, replay in zip(p['rows'], p['records'], a['records']):
            key = row['block'], row['snr'], row['arm']
            require(all(record[k] == replay[k] == row[k] for k in ['block', 'snr', 'arm']), 'record identity')
            require(row['scores'] == record['scores'], 'producer score mismatch')
            require(row['scores']['FER'] == replay['scores']['FER'], 'fresh decode FER mismatch')
            require(row['scores']['coded_bit_errors'] == replay['scores']['info_bit_errors'], 'decode bit mismatch')
            require(row['actual_edges'] == row['graph']['edges'], 'edge count mismatch')
            if row['arm'] == 'ORIGINAL':
                require(points[key] == row['scores'], 'baseline replay score mismatch')
                continue
            require(key not in points, 'duplicate method point')
            points[key], physical[key], new_rows[key] = row['scores'], row['provenance']['physical_record_sha256'], row
        older = read(project / f'afdm_sp_joint_unrolled/outputs_tail_terminal_v4_20260916/runs/{stage}/producer/summary.json')
        require(len(older['rows']) == count, 'v4 inventory')
        repeat_scores_equal &= all(x['scores'] == y['scores'] for x, y in zip(older['rows'], p['rows']))
    arms = ['ORIGINAL', 'TAIL', 'RIDGE_T']
    require(set(points) == {(b, s, a) for b in range(32) for s in [7, 8] for a in arms}, 'paired matrix incomplete')
    require(len({physical[b, 7, 'ORIGINAL'] for b in range(32)}) == 32, 'physical duplicates')
    for b in range(32):
        require(len({physical[b, s, a] for s in [7, 8] for a in arms}) == 1, 'physical pairing')
    delta = np.array([[sum(points[b, s, 'TAIL']['FER'] - points[b, s, a]['FER']
                           for s in [7, 8]) / 2 for a in ['ORIGINAL', 'RIDGE_T']] for b in range(32)])
    draws = np.random.default_rng(202609160701).integers(0, 32, (20000, 32))
    boot = delta[draws].mean(axis=1)
    checks = {}
    for j, name in enumerate(['TAIL_minus_ORIGINAL', 'TAIL_minus_RIDGE_T']):
        saved = result['primary_endpoints'][name]
        ci = np.quantile(boot[:, j], [.0125, .9875]).tolist()
        require(saved['mean'] == float(delta[:, j].mean()) and saved['simultaneous_95_percentile'] == ci,
                'bootstrap mismatch')
        nonzero = delta[:, j][delta[:, j] != 0]
        permuted = [abs(sum(np.array(signs) * abs(nonzero)))
                    for signs in itertools.product([-1, 1], repeat=len(nonzero))]
        p = sum(v >= abs(nonzero.sum()) for v in permuted) / len(permuted)
        checks[name] = dict(mean=saved['mean'], frozen_bootstrap_ci=ci,
                           exploratory_exact_cluster_signflip_p=p, bonferroni_adjusted_p=min(1., 2*p))
    mechanism = {}
    for s in [7, 8]:
        mechanism[str(s)] = {
            'failed_TAIL_blocks': [b for b in range(32) if points[b, s, 'TAIL']['FER']],
            'H_improved_vs_original': sum(points[b, s, 'TAIL']['H_NMSE'] < points[b, s, 'ORIGINAL']['H_NMSE'] for b in range(32)),
            'H_improved_vs_ridge': sum(points[b, s, 'TAIL']['H_NMSE'] < points[b, s, 'RIDGE_T']['H_NMSE'] for b in range(32)),
            'tail_worse_than_ridge_blocks': [b for b in range(32) if points[b, s, 'TAIL']['FER'] > points[b, s, 'RIDGE_T']['FER']],
        }
    wall = 0.
    for v in [4, 5]:
        root = project / f'afdm_sp_joint_unrolled/outputs_tail_terminal_v{v}_20260916'
        for p in (root / 'evidence').glob('*-exit.json'):
            exit_record = read(p)
            require(exit_record['exit_code'] == 0 and not exit_record['timed_out'], 'v4/v5 exit failure')
            wall += exit_record['wall_seconds']
    return dict(status='PASS_LOCAL_SUMMARY_SCOPE_WITH_ACCOUNTING_FINDINGS',
                source_sha256=sha(Path(__file__)), input_result_sha256=sha(research/'tail-terminal-v5-results-v1.json'),
                endpoint_checks=checks, mechanism_descriptive=mechanism, v4_v5_scores_equal=repeat_scores_equal,
                v5_calls=calls, unique_method_terminals=len(new_rows),
                known_v4_v5_cumulative=dict(T=264, D=264, LDPC=528, supervisor_seconds=wall),
                limitations=['Original NPZ/result records absent locally; hashes here bind summaries, not a new raw audit.',
                             'v1-v3 failed-attempt counts and resource costs remain unharvested.',
                             'Sign-flip check is post-hoc sensitivity under paired sign exchangeability; does not replace the frozen gate.',
                             'No new receiver, BP, LDPC or physical samples executed by this audit.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit(args.project)
    with args.output.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(value, ensure_ascii=False))
