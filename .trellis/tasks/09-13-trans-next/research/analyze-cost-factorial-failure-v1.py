"""Read-only failure localization; no receiver or decoder execution."""
import hashlib
import json
from pathlib import Path
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root):
    source=root/'source-cpu-cost-factorial-v1';manifest=source/'source-manifest.json'
    assert sha(manifest)=='087b4c81c6817785562e8b05d20c48873611a6b0f0f0433c536a23b363aea766'
    package=source/'afdm_sp_joint_unrolled'
    assert json.loads(manifest.read_text())=={str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0,str(source))
    import numpy as np
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS, receiver_resources
    from afdm_sp_joint_unrolled.trans_next_cpu_cost_quote import order
    run=root/'runs/cpu-cost-factorial-v1/quote'
    failure=json.loads((run/'failure.json').read_text())
    end=json.loads((root/'evidence/cpu-cost-factorial-v1-exit.json').read_text())
    assert end['exit_code']==1 and not end['timed_out']
    assert failure['status']=='FAILED' and failure['calls']==dict(F=75,D=0)
    assert not (run/'summary.json').exists()
    contract=root/'contracts/cpu-cost-factorial-v1.json';c=json.loads(contract.read_text())
    for name,digest in c['old_inputs'].items():assert sha(root/name)==digest
    reference=json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
    refs={(r['block'],r['snr']):r for r in reference['records'] if r['arm']=='BP_RETAIN_STOP'}
    paths=sorted(run.glob('F-*-result.json'));assert len(paths)==75 and not list(run.glob('D-*-result.json'))
    rows=[];hard=('support','x_hard','decoded','info_hat','decode_ok')
    for index,path in enumerate(paths):
        record=json.loads(path.read_text());planned=order(True)[index]
        assert all(record[k]==v for k,v in planned.items())
        entry=dict(record,record=str(path),sha256=sha(path));_,actual=verified_record(entry,root)
        ref_record,expected=verified_record(refs[record['block'],record['snr']],root)
        assert record['observed_hashes']==ref_record['observed_hashes']
        differences={}
        for field in NUMERIC_FIELDS:
            a,b=actual[field],expected[field]
            if a is None or b is None:
                differences[field]=dict(optional_equal=a is b);continue
            a,b=np.asarray(a),np.asarray(b)
            delta=a.astype(np.complex128)-b.astype(np.complex128)
            differences[field]=dict(exact=bool(np.array_equal(a,b)),mismatches=int(np.count_nonzero(a!=b)),
                max_abs=float(np.max(np.abs(delta))),relative=float(np.linalg.norm(delta)/max(np.linalg.norm(b),1e-12)),
                close=bool(np.allclose(a,b,rtol=1e-5,atol=1e-6)))
            if field in ('decoded','info_hat') and not np.array_equal(a,b):
                differences[field]['mismatch_indices']=np.flatnonzero(a!=b).tolist()
        actual_resources=receiver_resources(actual)
        rows.append(dict(planned,record=str(path),record_sha256=sha(path),reference_record_sha256=refs[record['block'],record['snr']]['sha256'],
            hard_exact=all(differences[f].get('exact',differences[f].get('optional_equal')) for f in hard),
            differences=differences,resources_equal=actual_resources==expected['resource_counts'],
            actual_resources=actual_resources,actual_scores=record['scores'],reference_scores=ref_record['scores'],
            actual_terminal_executed=actual['terminal_executed'],reference_terminal_executed=expected['terminal_executed'],
            actual_completed_outer=actual['completed_outer_detections'],reference_completed_outer=expected['completed_outer_detections']))
    result=dict(status='COMPLETE_FAILURE_LOCALIZATION',producer_status='FAILED',producer_calls=failure['calls'],
        new_calls=dict(F=0,D=0),verified_records=len(rows),hard_exact=sum(r['hard_exact'] for r in rows),
        bound=dict(source=sha(manifest),contract=sha(contract),failure=sha(run/'failure.json'),exit=sha(root/'evidence/cpu-cost-factorial-v1-exit.json'),script=sha(Path(__file__))),
        rows=rows,scope='all 75 saved outputs re-read; incomplete quote, no aggregate cost claim, no new F/D')
    with (root/'evidence/cpu-cost-factorial-v1-failure-localization.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
    print(json.dumps([r for r in rows if not r['hard_exact']],indent=2))


if __name__=='__main__':main(Path(sys.argv[1]))
