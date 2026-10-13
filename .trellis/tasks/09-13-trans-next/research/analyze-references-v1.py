"""Post-development descriptive paired analysis; no confirmation gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(evidence):
    summary_path = evidence / 'runs/refs-v1/development/summary.json'
    audit_path = evidence / 'evidence/refs-v1-development-audit.json'
    summary = json.loads(summary_path.read_text())
    audit = json.loads(audit_path.read_text())
    overlap = json.loads((evidence / 'evidence/refs-v1-development-prior-fresh-overlap.json').read_text())
    assert summary['status'] == 'COMPLETE' and audit['status'] == overlap['status'] == 'PASS'
    assert overlap['summary_sha256'] == digest(summary_path)
    assert audit['records'] == len(summary['records']) == 320
    assert summary['calls']['F'] == 320 and summary['nested_LDPC'] == 896
    arms = ['MEAN', 'REFRESH4', 'REFRESH47', 'ZERO_RIDGE_0p1', 'REFRESH4_RIDGE_0p1']
    keys = {(r['block'], r['snr'], r['arm']): r for r in summary['records']}
    assert len(keys) == 320
    assert set(keys) == {(b, s, a) for b in range(32) for s in (7, 8) for a in arms}
    audited = {(r['block'], r['snr'], r['arm']): r for r in audit['rows']}
    assert set(audited) == set(keys)
    for key, row in keys.items():
        assert row['scores'] == audited[key]['scores']
    # One block resampling matrix shared across arms and SNRs preserves pairing.
    rng = np.random.default_rng(20260913031)
    draws = rng.integers(0, 32, size=(50000, 32))
    table, comparisons = [], []
    for snr in (7, 8):
        base = np.array([keys[b, snr, 'MEAN']['scores']['FER'] for b in range(32)])
        for arm in arms:
            rows = [keys[b, snr, arm] for b in range(32)]
            fer = np.array([r['scores']['FER'] for r in rows])
            assert np.isin(fer, [0, 1]).all()
            table.append(dict(snr=snr, arm=arm, failures=int(fer.sum()), blocks=32,
                FER=float(fer.mean()), coded_bit_errors=sum(r['scores']['coded_bit_errors'] for r in rows),
                mean_channel_NMSE=float(np.mean([r['scores']['channel_NMSE'] for r in rows])),
                instrumented_mean_seconds=float(np.mean([r['seconds'] for r in rows]))))
            if arm == 'MEAN':
                continue
            wins = int(np.sum((base == 1) & (fer == 0)))
            losses = int(np.sum((base == 0) & (fer == 1)))
            discordant = wins + losses
            p = min(1., 2 * sum(math.comb(discordant, j) for j in range(min(wins, losses) + 1)) / 2**discordant)
            delta = fer - base
            interval = np.quantile(delta[draws].mean(axis=1), [.025, .975])
            comparisons.append(dict(snr=snr, arm=arm, wins=wins, losses=losses,
                delta_FER=float(delta.mean()), relative_FER_reduction=None if not base.sum() else float(1-fer.sum()/base.sum()),
                exploratory_paired_percentile_95=interval.tolist(), exact_McNemar_two_sided=p))
    adjusted = 0.
    for rank, row in enumerate(sorted(comparisons, key=lambda x: x['exact_McNemar_two_sided'])):
        adjusted = max(adjusted, min(1., (len(comparisons)-rank)*row['exact_McNemar_two_sided']))
        row['Holm_8_comparisons_p'] = adjusted
    return dict(scope='post-development descriptive analysis, not independent confirmation; percentile intervals are unadjusted and can degenerate at zero events',
        input_summary_sha256=digest(summary_path), raw_audit_sha256=digest(audit_path),
        analysis_source_sha256=digest(Path(__file__)), bootstrap_replicates=50000,
        bootstrap_seed=20260913031, independent_block_count=32,
        zero_of_32_one_sided_95_binomial_upper=1-.05**(1/32),
        cost_scope='instrumented receiver only, excludes input preparation/serialization/audit; not formal COST',
        table=table, paired_comparisons=comparisons)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.evidence)
    with args.output.open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))
