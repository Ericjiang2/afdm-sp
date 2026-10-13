"""Fixed eight paired development comparisons after completed raw audits."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(evidence):
    index, bindings, exogenous = {}, {}, None
    for tag, audit_name, arms, rows in (
            ('refs-v1', 'refs-v1-development-audit.json', ['MEAN', 'REFRESH47'], 320),
            ('siso-development-v1', 'siso-development-v1-raw-audit.json', ['SISO_MEAN', 'SISO_REF47'], 128)):
        summary_path = evidence/'runs'/tag/'development/summary.json'
        audit_path = evidence/'evidence'/audit_name
        summary, audit = (json.loads(p.read_text()) for p in (summary_path, audit_path))
        if (summary['status'] != 'COMPLETE' or audit['status'] != 'PASS'
                or audit['summary_sha256'] != digest(summary_path)
                or len(summary['records']) != audit['records'] or audit['records'] != rows):
            raise ValueError('incomplete or mismatched analysis evidence')
        actual_exogenous = {r['block']: r['hashes'] for r in summary['exogenous']}
        if set(actual_exogenous) != set(range(32)):
            raise ValueError('development does not have 32 external blocks')
        if exogenous is not None and exogenous != actual_exogenous:
            raise ValueError('SISO and BP exogenous arrays do not match')
        exogenous = actual_exogenous
        audited = {(r['block'], r['snr'], r['arm']): r for r in audit.get('rows', audit.get('comparisons', []))}
        selected = [r for r in summary['records'] if r['arm'] in arms]
        for row in selected:
            key = row['block'], row['snr'], row['arm']
            if key in index or key not in audited or row['scores'] != audited[key]['scores']:
                raise ValueError('duplicate or unaudited score')
            index[key] = row
        if len(selected) != 32*2*len(arms):
            raise ValueError('missing paired comparisons')
        bindings[tag] = dict(summary_sha256=digest(summary_path), audit_sha256=digest(audit_path))
    arms = ['MEAN', 'REFRESH47', 'SISO_MEAN', 'SISO_REF47']
    if set(index) != {(b, s, a) for b in range(32) for s in (7, 8) for a in arms}:
        raise ValueError('wrong paired comparison inventory')
    table, comparisons = [], []
    for snr in (7, 8):
        for arm in arms:
            records = [index[b, snr, arm] for b in range(32)]
            fer = [r['scores']['FER'] for r in records]
            if any(v not in (0, 1) for v in fer):
                raise ValueError('invalid block error')
            table.append(dict(snr=snr, arm=arm, failures=sum(fer), blocks=32, FER=sum(fer)/32,
                coded_bit_errors=sum(r['scores']['coded_bit_errors'] for r in records),
                mean_channel_NMSE=statistics.mean(r['scores']['channel_NMSE'] for r in records),
                instrumented_mean_seconds=statistics.mean(r['seconds'] for r in records)))
        for candidate in arms[2:]:
            for reference in arms[:2]:
                pairs = [(index[b, snr, reference]['scores']['FER'],
                          index[b, snr, candidate]['scores']['FER']) for b in range(32)]
                wins, losses = pairs.count((1, 0)), pairs.count((0, 1))
                discordant = wins+losses
                p = min(1., 2*sum(math.comb(discordant, j) for j in range(min(wins, losses)+1))/2**discordant)
                comparisons.append(dict(snr=snr, candidate=candidate, reference=reference,
                    wins=wins, losses=losses, delta_FER=(losses-wins)/32, exact_McNemar_two_sided=p))
    adjusted = 0.
    for rank, row in enumerate(sorted(comparisons, key=lambda r: r['exact_McNemar_two_sided'])):
        adjusted = max(adjusted, min(1., (8-rank)*row['exact_McNemar_two_sided']))
        row['Holm_8_comparisons_p'] = adjusted
    return dict(scope='fixed paired development comparison; not independent CONF or formal COST',
        independent_block_count=32, bindings=bindings, analysis_sha256=digest(Path(__file__)),
        zero_of_32_one_sided_95_binomial_upper=1-.05**(1/32),
        table=table, paired_comparisons=comparisons)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.evidence)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
