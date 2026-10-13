"""Summarize the complete audited I-01 design without selecting new parameters."""
import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from afdm_sp_joint_unrolled import supplement_statistics as statistics

ARMS = ('I0', 'Irealloc', 'Isham', 'I1', 'I2', 'I2realloc')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_family(family):
    if (family['alpha'] != 0.05 / 7 or family['m_max'] != 66
            or family['m_used_after_selection'] != 66
            or family['unused_slots_recycle_alpha'] is not False):
        raise ValueError('frozen family error allocation differs')
    all_contrasts = family['contrasts']
    if len(all_contrasts) != 66 or len({c['id'] for c in all_contrasts}) != 66:
        raise ValueError('duplicate or missing family contrast')
    expected = {}
    for snr in (7, 8, 9):
        for a, b in combinations(ARMS, 2):
            expected[f'info:{a}-{b}@nominal:{snr}'] = (
                [a, b], [1, -1], snr, 'paired_CP')
        expected[f'information_x_reallocation@nominal:{snr}'] = (
            ['I0', 'I2', 'Irealloc', 'I2realloc'], [1, -1, -1, 1], snr, 'linear_CP')
    contrasts = [c for c in all_contrasts if set(c['arms']).issubset(ARMS)]
    if {c['id'] for c in contrasts} != set(expected):
        raise ValueError('frozen I-01 contrast inventory differs')
    for c in contrasts:
        actual = (c['arms'], c['coefficients'], c['snr_db'], c['method'])
        if actual != expected[c['id']] or c['scene'] != 'nominal':
            raise ValueError('frozen contrast definition differs')
    return contrasts


def analyze(audit, manifest):
    if audit.get('status') != 'passed' or audit.get('F_audited') != 3456:
        raise ValueError('complete 3456F raw audit required; partial data cannot select or close I-01')
    rows = {}
    for batch in audit['batches']:
        for proof in batch['proofs']:
            identity = tuple(proof['identity'])
            if identity in rows:
                raise ValueError('duplicate audited identity')
            row = proof['errors']
            if type(row['FER']) is not int or row['FER'] not in (0, 1):
                raise ValueError('invalid binary frame error')
            rows[identity] = row
    expected = {(b, s, a) for b in range(192) for s in (7, 8, 9) for a in ARMS}
    if set(rows) != expected:
        raise ValueError('missing/extra development block, SNR or arm')
    family = manifest['families']['F_I']
    contrasts = validate_family(family)
    summaries = []
    for s in (7, 8, 9):
        for arm in ARMS:
            values = [rows[b, s, arm] for b in range(192)]
            sums = {k: sum(v[k] for v in values) for k in
                    ('FER', 'coded_bit_errors', 'raw_bit_errors',
                     'decoded_codeword_bit_errors', 'coded_bits_denominator', 'raw_bits_denominator')}
            summaries.append(dict(arm=arm, snr_db=s, n=192, frame_errors=sums.pop('FER'), **sums))
    intervals = []
    for contrast in contrasts:
        arms, c, s = contrast['arms'], contrast['coefficients'], contrast['snr_db']
        matrix = np.array([[rows[b, s, arm]['FER'] for arm in arms] for b in range(192)])
        if contrast['method'] == 'paired_CP':
            if c != [1, -1] or len(arms) != 2:
                raise ValueError('unsupported paired contrast')
            win = int(np.count_nonzero((matrix[:, 0] == 1) & (matrix[:, 1] == 0)))
            loss = int(np.count_nonzero((matrix[:, 0] == 0) & (matrix[:, 1] == 1)))
            result = statistics.paired_delta(win, loss, 192,
                alpha_family=family['alpha'], m=66)
            detail = dict(W=win, L=loss)
        elif contrast['method'] == 'linear_CP':
            result = statistics.linear_contrast(matrix.sum(axis=0), c, 192,
                alpha_family=family['alpha'], m=66)
            detail = dict(error_counts=matrix.sum(axis=0).tolist())
        else:
            raise ValueError('unregistered interval method')
        intervals.append(dict(id=contrast['id'], arms=arms, coefficients=c,
            **detail, **{k: float(v) if k != 'n' else int(v) for k, v in result.items()}))
    return dict(status='complete_development_summary', F=3456, blocks=192,
        arm_summaries=summaries, contrasts=intervals,
        alpha_family=family['alpha'], m=66,
        scope='development descriptions only; no independent confirmation, COST-02, method selection or deployability claim',
        limitations=['oracle offline_truth_access generic scoring label is overwritten; explicit truth_access_level and consumption records are authoritative',
                     'instrumented/concurrent timing must be tested separately under COST-02',
                     'small or zero point differences do not establish equivalence'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--contrast-manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.contrast_manifest.read_text())
    if digest(statistics.__file__) != manifest['deterministic_engine_sha256']:
        raise ValueError('statistics engine differs from frozen manifest')
    result = analyze(json.loads(args.audit.read_text()), manifest)
    result.update(raw_audit_sha256=digest(args.audit),
                  contrast_manifest_sha256=digest(args.contrast_manifest))
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(status=result['status'], F=result['F'], sha256=digest(args.out))))


if __name__ == '__main__':
    main()
