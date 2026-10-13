"""Re-read complete quote records and their audited reference; no new F or D."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    source = root/'source-cpu-cost-quote-v1'
    manifest = source/'source-manifest.json'
    assert sha(manifest) == '914143e452961a0d8b7676a959e23eb89c3141a94e2e11b37f33f1ca6f985e8d'
    package = source/'afdm_sp_joint_unrolled'
    assert json.loads(manifest.read_text()) == {str(p.relative_to(package)): sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0, str(source))
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record, check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    from afdm_sp_joint_unrolled.trans_next_cpu_cost_quote import order
    summary_path = root/'runs/cpu-cost-quote-v1/quote/summary.json'
    summary = json.loads(summary_path.read_text())
    contract_path = root/'contracts/cpu-cost-quote-v1.json'
    contract = json.loads(contract_path.read_text())
    environment_path = summary_path.with_name('environment.json')
    environment = json.loads(environment_path.read_text())
    end = json.loads((root/'evidence/cpu-cost-quote-v1-run2-exit.json').read_text())
    assert end['exit_code'] == 0 and end['timed_out'] is False
    assert summary['status'] == 'COMPLETE' and summary['calls'] == dict(F=68, D=68)
    assert summary['source_sha256'] == sha(manifest)
    assert summary['contract_sha256'] == sha(contract_path)
    for name, digest in contract['old_inputs'].items():
        assert sha(root/name) == digest
    ref_summary = json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
    refs = {(r['block'], r['snr']): r for r in ref_summary['records'] if r['arm'] == 'BP_RETAIN_STOP'}
    records = summary['records']
    assert len(records) == 136 and [r['kind'] for r in records] == ['F']*68+['D']*68
    reservation_times = {'F': [], 'D': []}
    files = {}
    for i, planned in enumerate(order()):
        f_entry, d_entry = records[i], records[i+68]
        assert all(f_entry[k] == d_entry[k] == v for k, v in planned.items())
        f_record, value = verified_record(f_entry, root)
        d_record, decoded = verified_record(d_entry, root)
        reference_record, expected = verified_record(refs[planned['block'], planned['snr']], root)
        for field in NUMERIC_FIELDS:
            same_state(value[field], expected[field])
        same_state(value['bp_schedule'], expected['bp_schedule'])
        check_decode_identity(decoded, value)
        same_state(decoded['llr'], value['llr'])
        assert d_record['source_record_sha256'] == f_entry['sha256']
        assert f_record['observed_hashes'] == reference_record['observed_hashes']
        assert f_record['scores'] == reference_record['scores'] == f_entry['scores']
        assert f_record['pid'] == environment['pid']
        assert f_record['receiver_instance_id'] == environment['receiver_instance_id']
        assert not value['graphs'] and not value['dals']
        for entry, record in ((f_entry, f_record), (d_entry, d_record)):
            assert entry['seconds'] == record['seconds'] > 0
            assert entry['CPU_seconds'] == record['CPU_seconds'] >= 0
            path = Path(entry['record']).with_name(record['token']+'-reserve.json')
            reserve = json.loads(path.read_text())
            assert reserve['token'] == record['token'] and reserve['kind'] == record['kind']
            reservation_times[record['kind']].append(reserve['reserved_at'])
            files[entry['record']] = entry['sha256']
    assert max(reservation_times['F']) < summary['collection_finished_at'] <= min(reservation_times['D'])
    return dict(status='PASS', F_records=68, D_records=68, numeric_reference_exact=68,
                decoded_saved_identity_exact=68, shared_receiver_instance=True,
                warmup_F=4, measurement_F=64, independent_blocks=8,
                bindings=dict(summary=sha(summary_path), contract=sha(contract_path),
                              source=sha(manifest), environment=sha(environment_path)),
                verified_record_hashes=files,
                scope='read-back of all saved quote and decode outputs; original run executed 68D; this audit adds 0F/0D; not formal COST')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit(args.root), indent=2, allow_nan=False))
