"""Paired full receiver development, with previously audited references."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from math import comb
from pathlib import Path
import statistics


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def previous(name, evidence):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.analyze(evidence)


def analyze(evidence):
    baseline = previous('analyze-stop-development-v1.py', evidence)
    terminal = previous('analyze-terminal-prior-v1.py', evidence)
    tag = 'retained-chain-development-v1'
    paths = dict(summary=evidence/'runs'/tag/'development/summary.json',
                 audit=evidence/'evidence'/(tag+'-raw-audit.json'),
                 contract=evidence/'contracts'/(tag+'.json'))
    summary, audit, contract = (json.loads(paths[k].read_text()) for k in ('summary', 'audit', 'contract'))
    assert summary['status'] == 'COMPLETE' and summary['calls'] == {'F': 128}
    assert audit['status'] == 'PASS' and audit['records'] == 128
    assert audit['summary_sha256'] == sha(paths['summary'])
    assert audit['contract_sha256'] == summary['contract_sha256'] == sha(paths['contract'])
    assert audit['source_sha256'] == summary['source_sha256'] == contract['engineering_source_sha256']
    assert contract['blocks'] == list(range(32)) and contract['snrs'] == [7, 8]
    assert contract['terminal_summary_sha256'] == terminal['bindings']['summary']
    for name in (tag, tag+'-raw-audit'):
        exit_record = json.loads((evidence/'evidence'/(name+'-exit.json')).read_text())
        assert exit_record['exit_code'] == 0 and exit_record['timed_out'] is False
    ref_path = evidence/'runs/refs-v1/development/summary.json'
    assert sha(ref_path) == contract['input_summary_sha256'] == contract['reference_summary_sha256']
    ref = json.loads(ref_path.read_text())
    assert {r['block']: r['hashes'] for r in summary['exogenous']} == {
        r['block']: r['hashes'] for r in ref['exogenous']}
    new_arms = ['BP_RETAIN', 'BP_RETAIN_STOP']
    expected = {(b, s, a) for b in range(32) for s in (7, 8) for a in new_arms}
    rows = {(r['block'], r['snr'], r['arm']): r for r in summary['records']}
    audited = {(r['block'], r['snr'], r['arm']): r for r in audit['rows']}
    assert len(summary['records']) == len(audit['rows']) == 128
    assert set(rows) == set(audited) == expected
    for key in expected:
        assert rows[key]['scores'] == audited[key]['scores']
        if key[2] == 'BP_RETAIN':
            assert audited[key]['outer_reference_exact'] and audited[key]['terminal_counterfactual_exact']
        else:
            assert audited[key]['prefix_exact']
    for old_tag, arms in [('refs-v1', ['REFRESH47']), ('siso-development-v1', ['SISO_REF47']),
                          ('stop-development-v1', ['BP_STOP', 'SISO_STOP'])]:
        old = json.loads((evidence/'runs'/old_tag/'development/summary.json').read_text())
        for r in old['records']:
            if r['arm'] in arms:
                key = r['block'], r['snr'], r['arm']
                assert key not in rows
                rows[key] = r
    table = list(baseline['table'])
    for snr in (7, 8):
        for arm in new_arms:
            group = [rows[b, snr, arm] for b in range(32)]
            checks = [audited[b, snr, arm] for b in range(32)]
            counts = Counter()
            for r in checks:
                counts.update(r['resources'])
            table.append(dict(snr=snr, arm=arm, n=32,
                failures=sum(r['scores']['FER'] for r in group),
                failed_blocks=[r['block'] for r in group if r['scores']['FER']],
                coded_bit_errors=sum(r['scores']['coded_bit_errors'] for r in group),
                instrumented_mean_seconds=statistics.mean(r['seconds'] for r in group),
                resource_totals=dict(counts),
                terminal_calls=counts['terminal_BP_calls'],
                stop_checkpoints=dict(Counter(str(r.get('checkpoint')) for r in checks))
                    if arm.endswith('STOP') else {}))
    comparisons = []
    pairs = [('BP_RETAIN', 'REFRESH47'), ('BP_RETAIN_STOP', 'BP_STOP'),
             ('BP_RETAIN_STOP', 'SISO_STOP'), ('BP_RETAIN_STOP', 'BP_RETAIN'),
             ('BP_RETAIN', 'SISO_REF47')]
    for snr in (7, 8):
        for candidate, reference in pairs:
            wins, losses = [], []
            for b in range(32):
                c, r = [rows[b, snr, a]['scores']['FER'] for a in (candidate, reference)]
                if c < r: wins.append(b)
                if c > r: losses.append(b)
            n = len(wins)+len(losses)
            p = min(1., 2*sum(comb(n, j) for j in range(min(len(wins), len(losses))+1))/2**n)
            comparisons.append(dict(snr=snr, candidate=candidate, reference=reference,
                rescued_blocks=wins, new_error_blocks=losses, delta_FER=(len(losses)-len(wins))/32,
                exact_McNemar_two_sided=p))
    high = 0.
    for rank, item in enumerate(sorted(comparisons, key=lambda x:x['exact_McNemar_two_sided'])):
        high = max(high, min(1., (len(comparisons)-rank)*item['exact_McNemar_two_sided']))
        item['Holm_10_exploratory_comparisons_p'] = high
    return dict(scope='fixed 32 previously used development blocks; ordinary references, not CONF/COST/novelty',
        independent_blocks=32, table=table, comparisons=comparisons,
        actual_stops=audit['actual_stops'], valid_but_wrong_stops=audit['valid_but_wrong_stops'],
        audit_counts={k:v for k,v in audit.items() if k in ('arrays_audited', 'CE_states',
            'nested_LDPC_replays', 'terminal_LDPC_replays', 'resources')},
        zero_of_32_one_sided_95_binomial_upper=1-.05**(1/32),
        bindings={**{k:sha(v) for k,v in paths.items()}, 'source':summary['source_sha256'],
            'baseline':baseline['bindings'], 'terminal':terminal['bindings'], 'analyzer':sha(Path(__file__))})


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = analyze(args.evidence)
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
