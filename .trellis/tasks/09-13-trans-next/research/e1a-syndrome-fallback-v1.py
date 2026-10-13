"""Retrospective classical policy on audited cached scores; no receiver calls."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def use_secondary(primary_ok):
    if type(primary_ok) is not bool:
        raise TypeError('primary_ok must be a decoder boolean')
    return not primary_ok


def main():
    r = Path(__file__).resolve().parent
    project = r.parents[3]
    e = project / '.mission/20260913_00-48-38-afdm-trans-next/evidence/exact-harvest-v1'
    sources = [
        ('legal-response-errors-v1-results.json', 'legal-response-errors-recovery-v2'),
        ('gcv-response-errors-v1-results.json', 'gcv-response-errors-v1'),
        ('whitened-response-errors-v1-results.json', 'whitened-response-errors-v1'),
    ]
    rows = {}
    provenance = []
    for name, tag in sources:
        path = r / name
        report = json.loads(path.read_text())
        audit_path = e / f'evidence/{tag}-raw-audit.json'
        audit = json.loads(audit_path.read_text())
        assert audit['status'] == 'PASS'
        assert report['raw_audit_sha256'] == sha(audit_path)
        assert report['rows'] == audit['rows']
        provenance.append(dict(report=name, report_sha256=sha(path),
                               raw_audit_sha256=sha(audit_path)))
        for row in report['rows']:
            key = row['block'], row['snr'], row['arm']
            if key in rows:
                assert rows[key] == row
            rows[key] = row

    required = ['S_ALL', 'W_D_ALL', 'D_GCV_ALL', 'D_P_HALF']
    for arm in required:
        assert {(b, s) for b, s, a in rows if a == arm} == {
            (b, s) for b in range(32) for s in (7, 8)}
    selected_rows = []
    summaries = []
    for secondary in required[1:]:
        for snr in (7, 8):
            selected = []
            fallback = []
            primary_failures = []
            for block in range(32):
                primary = rows[block, snr, 'S_ALL']
                # This call cannot access truth, block number or SNR.
                take_secondary = use_secondary(primary['scores']['decode_ok'])
                arm = secondary if take_secondary else 'S_ALL'
                row = rows[block, snr, arm]
                assert row['physical_record_sha256'] == primary['physical_record_sha256']
                scores = row['scores']
                errors = scores['info_bit_errors'] if 'info_bit_errors' in scores else scores['coded_bit_errors']
                bits = scores['info_bits'] if 'info_bits' in scores else scores['coded_bits_denominator']
                assert bits == 1024 and bool(errors) == bool(scores['FER'])
                item = dict(block=block, snr=snr, secondary=secondary, selected_arm=arm,
                            terminal_record_sha256=row['terminal_record_sha256'],
                            physical_record_sha256=row['physical_record_sha256'],
                            primary_decode_ok=primary['scores']['decode_ok'],
                            decode_ok=scores['decode_ok'], FER=scores['FER'],
                            info_bit_errors=errors, info_bits=bits,
                            decoded_codeword_bit_errors=scores['decoded_codeword_bit_errors'])
                selected.append(item)
                if take_secondary:
                    fallback.append(block)
                if primary['scores']['FER']:
                    primary_failures.append(block)
            failures = [v['block'] for v in selected if v['FER']]
            summaries.append(dict(secondary=secondary, snr=snr, blocks=32,
                failures=len(failures), failed_blocks=failures,
                info_bit_errors=sum(v['info_bit_errors'] for v in selected), info_bits=32768,
                fallback_blocks=fallback, fallback_count=len(fallback),
                valid_wrong_codeword_blocks=[v['block'] for v in selected
                    if v['decode_ok'] and v['decoded_codeword_bit_errors'] > 0],
                rescued_vs_S_ALL=sorted(set(primary_failures)-set(failures)),
                new_failures_vs_S_ALL=sorted(set(failures)-set(primary_failures))))
            selected_rows.extend(selected)
    result = dict(status='AUDITED_CACHED_SCORE_POLICY_ANALYSIS', script_sha256=sha(Path(__file__)),
                  protocol_sha256=sha(r/'e1a-syndrome-fallback-v1.md'),
                  provenance=provenance, summaries=summaries, rows=selected_rows,
                  new_receiver_calls=0, new_decoder_calls=0,
                  scope='Post-hoc development classical control; boolean syndrome policy only. '
                        'No independent confirmation, novel method or full-chain cost claim.')
    with (r/'e1a-syndrome-fallback-v1-results.json').open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
