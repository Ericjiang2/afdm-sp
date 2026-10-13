"""Read-only raw comparison of already audited dense/integer CPU campaigns."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root, source):
    manifest = source / 'source-manifest.json'
    assert sha(manifest) == '9f92efcf5c08c2664c7ec394d49b9a57b779be89fb3465abf85a675595b8bbf5'
    package = source / 'afdm_sp_joint_unrolled'
    assert json.loads(manifest.read_text()) == {
        str(p.relative_to(package)): sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0, str(source))
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    pairs = [('integer-graph-development-v1', 'retained-chain-development-v1', 'development', 128),
             ('schedule-graph-engineering-v1', 'integer-graph-engineering-v1', 'engineering', 16)]
    results = []
    for new, old, stage, count in pairs:
        groups, bindings = [], {}
        for tag in (new, old):
            path = root/'runs'/tag/stage/'summary.json'
            summary = json.loads(path.read_text())
            audit_path = root/'evidence'/(tag+'-raw-audit.json')
            audit = json.loads(audit_path.read_text())
            contract_path = root/'contracts'/(tag+'.json')
            assert summary['status'] == 'COMPLETE' and summary['calls'] == {'F': count}
            assert audit['status'] == 'PASS' and audit['records'] == count
            assert audit['summary_sha256'] == sha(path)
            assert audit['contract_sha256'] == summary['contract_sha256'] == sha(contract_path)
            assert audit['source_sha256'] == summary['source_sha256']
            for suffix in ('', '-raw-audit'):
                end = json.loads((root/'evidence'/(tag+suffix+'-exit.json')).read_text())
                assert end['exit_code'] == 0 and end['timed_out'] is False
            rows = {(r['block'], r['snr'], r['split'], r['arm']): r for r in summary['records']}
            assert len(rows) == count
            groups.append((summary, rows))
            bindings[tag] = dict(summary=sha(path), audit=sha(audit_path),
                                 contract=sha(contract_path), source=summary['source_sha256'])
        (new_summary, new_rows), (old_summary, old_rows) = groups
        assert new_rows.keys() == old_rows.keys()
        same_state(new_summary['exogenous'], old_summary['exogenous'])
        checked = []
        for key in sorted(new_rows):
            nr, nv = verified_record(new_rows[key], root)
            rr, rv = verified_record(old_rows[key], root)
            for field in NUMERIC_FIELDS:
                same_state(nv[field], rv[field])
            for field in ('bp_schedule', 'terminal_executed', 'completed_outer_detections'):
                if field in rv:
                    same_state(nv[field], rv[field])
            assert nr['scores'] == rr['scores']
            checked.append(dict(block=key[0], snr=key[1], split=key[2], arm=key[3],
                                numeric_exact=True, scores=nr['scores']))
        results.append(dict(candidate=new, reference=old, records=count,
                            bindings=bindings, checks=checked))
    return dict(status='PASS', new_receiver_calls=0, source=sha(manifest),
                numeric_fields=list(NUMERIC_FIELDS), comparisons=results,
                scope='all saved public numeric fields, schedule and scoring; no cost or novelty claim')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.root, args.source), indent=2, allow_nan=False))
