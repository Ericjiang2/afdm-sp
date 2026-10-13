"""Raw read-back of corrected support metadata; no new F/D."""
import hashlib
import json
from pathlib import Path
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    source=root/'source-receiver-domain-v2';manifest=source/'source-manifest.json';package=source/'afdm_sp_joint_unrolled'
    assert sha(manifest)=='2fd0beb6efd405e7c7921a79c8e209f87203322bed67bc41c7f6cde4a6bb9dd9'
    assert json.loads(manifest.read_text())=={str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0,str(source))
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record,check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS,receiver_resources
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    tag='scale-support-regression-v1';path=root/'runs'/tag/'regression/summary.json';s=json.loads(path.read_text())
    contract=root/'contracts'/(tag+'.json');c=json.loads(contract.read_text());end=json.loads((root/'evidence'/(tag+'-exit.json')).read_text())
    assert end['exit_code']==0 and not end['timed_out'] and s['status']=='COMPLETE' and s['calls']==dict(F=4,D=4)
    assert s['source_sha256']==sha(manifest) and s['contract_sha256']==sha(contract) and s['script_sha256']==sha(root/'evidence'/(tag+'.py'))
    for name,digest in c['old_inputs'].items():assert sha(root/name)==digest
    old=json.loads((root/'runs/integer-scale-engineering-v2/engineering/summary.json').read_text())
    records=s['records'];assert [r['kind'] for r in records]==['F']*4+['D']*4
    checks=[]
    for i,block in enumerate([0,2,3,4]):
        entry=records[i];record,value=verified_record(entry,root);assert entry['block']==block
        ref_entry=next(r for r in old['records'] if r['kind']=='F' and r['block']==block and r['phase']=='qualification' and r['arm']=='INTEGER')
        ref_record,reference=verified_record(ref_entry,root)
        assert record['reference_record_sha256']==ref_entry['sha256'] and record['observed_hashes']==ref_record['observed_hashes']
        for field in NUMERIC_FIELDS:
            if field!='support':same_state(value[field],reference[field])
        same_state(value['bp_schedule'],reference['bp_schedule']);assert receiver_resources(value)==receiver_resources(reference)
        k=c['cells'][block]['k_max'];ce=reference['dals'][-1]
        expected=(ce['support_delays']*(2*k+1)+ce['support_dopplers']+k).tolist()
        assert value['support']==value['support_trace'][-1]['expanded_atom_ids']==expected
        assert all(row['complete_matrix_verified'] for row in value['integer_graph_calls'])
        d_record,decoded=verified_record(records[4+i],root);check_decode_identity(decoded,value);same_state(decoded['llr'],value['llr'])
        assert d_record['source_record_sha256']==entry['sha256']
        checks.append(dict(block=block,k_max=k,support_correct=True,other_numeric_exact=True,own_LLR_decode_exact=True))
    result=dict(status='PASS',raw_F=4,raw_D=4,checks=checks,summary_sha256=sha(path),source_sha256=sha(manifest),contract_sha256=sha(contract),
        scope='four reused non-K5 inputs; corrected metadata only; no new cost qualification')
    with (root/'evidence'/(tag+'-raw-audit.json')).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':audit(Path(sys.argv[1]))
