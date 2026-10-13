"""Analyze all fixed terminal controls; no new sampling or receiver claims."""
import argparse
from collections import Counter
import hashlib
import json
from math import comb
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(evidence):
    tag = 'terminal-prior-development-v1'
    path = evidence/'runs'/tag/'development/summary.json'
    audit_path = evidence/'evidence'/(tag+'-raw-audit.json')
    contract_path = evidence/'contracts'/(tag+'.json')
    summary, audit, contract = (json.loads(p.read_text()) for p in (path, audit_path, contract_path))
    for name in (tag, tag+'-raw-audit'):
        result = json.loads((evidence/'evidence'/(name+'-exit.json')).read_text())
        assert result['exit_code'] == 0 and result['timed_out'] is False
    assert summary['status'] == 'COMPLETE' and summary['calls'] == {'T': 192}
    assert audit['status'] == 'PASS' and audit['records'] == 192
    assert audit['summary_sha256'] == sha(path)
    assert audit['contract_sha256'] == summary['contract_sha256'] == sha(contract_path)
    assert audit['source_sha256'] == summary['source_sha256']
    assert contract['blocks'] == list(range(32)) and contract['snrs'] == [7, 8]
    assert contract['arms'] == ['LEGACY', 'ZERO', 'RETAIN'] and contract['temperature'] == 2.
    rows = summary['records']; keys = [(r['block'], r['snr'], r['arm']) for r in rows]
    expected = {(b, s, a) for b in range(32) for s in (7, 8) for a in contract['arms']}
    assert len(keys) == 192 and set(keys) == expected
    audited = {(r['block'], r['snr'], r['arm']): r['scores'] for r in audit['rows']}
    assert all(audited[(r['block'], r['snr'], r['arm'])] == r['scores'] for r in rows)
    table, comparisons = [], []
    for snr in (7, 8):
        for arm in contract['arms']:
            group = [r for r in rows if r['snr'] == snr and r['arm'] == arm]
            table.append(dict(snr=snr, arm=arm, n=32, failures=sum(r['scores']['FER'] for r in group),
                failed_blocks=[r['block'] for r in group if r['scores']['FER']],
                info_bit_errors=sum(r['scores']['info_bit_errors'] for r in group),
                raw_bit_errors=sum(r['scores']['raw_bit_errors'] for r in group),
                mean_bit_NLL=sum(r['scores']['bit_NLL'] for r in group)/32,
                instrumented_terminal_mean_seconds=sum(r['seconds'] for r in group)/32))
        for candidate, reference in [('ZERO', 'LEGACY'), ('RETAIN', 'ZERO'), ('RETAIN', 'LEGACY')]:
            records = {(r['block'], r['arm']): r for r in rows if r['snr'] == snr}
            wins, losses = [], []
            for b in range(32):
                c, r = [records[b, a]['scores']['FER'] for a in (candidate, reference)]
                if c < r: wins.append(b)
                if c > r: losses.append(b)
            n = len(wins)+len(losses); k = min(len(wins), len(losses))
            p = min(1., 2*sum(comb(n, i) for i in range(k+1))/2**n)
            comparisons.append(dict(snr=snr, candidate=candidate, reference=reference,
                rescued_blocks=wins, new_error_blocks=losses, exact_McNemar_two_sided=p,
                delta_FER=(len(losses)-len(wins))/32))
    high = 0.
    for rank, item in enumerate(sorted(comparisons, key=lambda x:x['exact_McNemar_two_sided'])):
        high = max(high, min(1., (6-rank)*item['exact_McNemar_two_sided']))
        item['Holm_6_comparisons_p'] = high
    return dict(scope='exploratory cached terminal controls; not full receiver, CONF or COST',
        independent_blocks=32, table=table, comparisons=comparisons,
        bindings=dict(summary=sha(path), audit=sha(audit_path), contract=sha(contract_path),
            source=summary['source_sha256'], analyzer=sha(Path(__file__))))


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True);args=p.parse_args()
    result=analyze(args.evidence);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
