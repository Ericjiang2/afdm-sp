"""Exploratory paired stop comparisons; engineering/selection data stay explicit."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(evidence):
    previous_path = Path(__file__).with_name('analyze-siso-development-v1.py')
    spec = importlib.util.spec_from_file_location('siso_analysis', previous_path)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    # Reuse the existing BP/SISO evidence and exogenous-pairing validation.
    baseline = previous.analyze(evidence)
    summary_path = evidence/'runs/stop-development-v1/development/summary.json'
    audit_path = evidence/'evidence/stop-development-v1-raw-audit.json'
    summary, audit = (json.loads(p.read_text()) for p in (summary_path, audit_path))
    if (summary['status'] != 'COMPLETE' or audit['status'] != 'PASS'
            or audit['summary_sha256'] != digest(summary_path) or audit['records'] != 128):
        raise ValueError('stop development is incomplete or unaudited')
    inputs = json.loads((evidence/'runs/refs-v1/development/summary.json').read_text())
    if ({r['block']: r['hashes'] for r in summary['exogenous']}
            != {r['block']: r['hashes'] for r in inputs['exogenous']}):
        raise ValueError('stop and baseline exogenous arrays differ')
    index = {}
    for tag, names in [('refs-v1', ['REFRESH47']), ('siso-development-v1', ['SISO_REF47']),
                       ('stop-development-v1', ['BP_STOP', 'SISO_STOP'])]:
        data = json.loads((evidence/'runs'/tag/'development/summary.json').read_text())
        for row in data['records']:
            if row['arm'] not in names:
                continue
            key = row['block'], row['snr'], row['arm']
            if key in index:
                raise ValueError('duplicate paired row')
            index[key] = row
    arms = ['REFRESH47', 'BP_STOP', 'SISO_REF47', 'SISO_STOP']
    if set(index) != {(b, s, a) for b in range(32) for s in (7, 8) for a in arms}:
        raise ValueError('missing paired development cell')
    audited = {(r['block'], r['snr'], r['arm']): r for r in audit['rows']}
    for key in audited:
        if index[key]['scores'] != audited[key]['scores']:
            raise ValueError('stop score differs from raw audit')
    table, comparisons = [], []
    for snr in (7, 8):
        for arm in arms:
            records = [index[b, snr, arm] for b in range(32)]
            table.append(dict(snr=snr, arm=arm, n=32,
                failed_blocks=[b for b in range(32) if index[b, snr, arm]['scores']['FER']],
                failures=sum(r['scores']['FER'] for r in records),
                coded_bit_errors=sum(r['scores']['coded_bit_errors'] for r in records),
                instrumented_mean_seconds=statistics.mean(r['seconds'] for r in records),
                outer_detections=[audited[b, snr, arm]['outer_detections'] for b in range(32)]
                    if arm.endswith('STOP') else [10]*32,
                terminal_calls=sum(audited[b, snr, arm]['terminal_executed'] for b in range(32))
                    if arm.endswith('STOP') else 32))
        for reference, candidate in [('REFRESH47', 'BP_STOP'), ('SISO_REF47', 'SISO_STOP'),
                                     ('BP_STOP', 'SISO_STOP')]:
            pairs = [(index[b, snr, reference]['scores']['FER'], index[b, snr, candidate]['scores']['FER'])
                     for b in range(32)]
            wins, losses = pairs.count((1, 0)), pairs.count((0, 1))
            n = wins+losses
            p = min(1., 2*sum(math.comb(n, j) for j in range(min(wins, losses)+1))/2**n)
            comparisons.append(dict(snr=snr, candidate=candidate, reference=reference,
                wins=wins, losses=losses, rescued_blocks=[b for b, pair in enumerate(pairs) if pair == (1, 0)],
                new_error_blocks=[b for b, pair in enumerate(pairs) if pair == (0, 1)],
                delta_FER=(losses-wins)/32, exact_McNemar_two_sided=p))
    adjusted = 0.
    for rank, row in enumerate(sorted(comparisons, key=lambda r: r['exact_McNemar_two_sided'])):
        adjusted = max(adjusted, min(1., (6-rank)*row['exact_McNemar_two_sided']))
        row['Holm_6_comparisons_p'] = adjusted
    return dict(scope='exploratory development after retrospective selection of ordinary stopping; not CONF or COST',
        independent_block_count=32, table=table, comparisons=comparisons,
        zero_of_32_one_sided_95_binomial_upper=1-.05**(1/32),
        actual_stops=audit['actual_stops'], valid_but_wrong_stops=audit['valid_but_wrong_stops'],
        bindings=dict(baselines=baseline['bindings'], stop_summary=digest(summary_path), stop_audit=digest(audit_path),
                      baseline_analyzer=digest(previous_path), analyzer=digest(Path(__file__))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.evidence)
    with args.output.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
