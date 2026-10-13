"""Raw read-back of the fixed QPSK counterexample; no F/D."""
import hashlib
import json
from pathlib import Path
import sys


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def audit(root):
    source=root/'source-cpu-cost-factorial-v1';package=source/'afdm_sp_joint_unrolled';manifest=source/'source-manifest.json'
    assert sha(manifest)=='087b4c81c6817785562e8b05d20c48873611a6b0f0f0433c536a23b363aea766'
    assert json.loads(manifest.read_text())=={str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0,str(source))
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record,check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS,receiver_resources
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    path=root/'runs/projection-sensitive-replay-v1/diagnostic/summary.json';s=json.loads(path.read_text())
    cpath=root/'contracts/projection-sensitive-replay-v1.json';c=json.loads(cpath.read_text())
    assert s['status']=='COMPLETE' and s['calls']==dict(F=2,D=4)
    assert s['source_sha256']==sha(manifest) and s['contract_sha256']==sha(cpath)
    assert s['script_sha256']==sha(root/'evidence/projection-sensitive-replay-v1.py')
    for name,digest in c['old_inputs'].items():assert sha(root/name)==digest
    end=json.loads((root/'evidence/projection-sensitive-replay-v1-exit.json').read_text());assert end['exit_code']==0 and not end['timed_out']
    fpath=root/'runs/cpu-cost-factorial-v1/quote/F-00075-result.json';f=json.loads(fpath.read_text())
    failed_entry=dict(f,record=str(fpath),sha256=sha(fpath));_,failed=verified_record(failed_entry,root)
    reference=json.loads((root/'runs/retained-chain-development-v1/development/summary.json').read_text())
    r=next(r for r in reference['records'] if r['block']==4 and r['snr']==7 and r['arm']=='BP_RETAIN_STOP');_,ref=verified_record(r,root)
    expected=[ref,failed];digests=[r['sha256'],failed_entry['sha256']]
    records=s['records'];assert [r['kind'] for r in records]==['F','F','D','D','D','D']
    for entry in records[:2]:
        record,value=verified_record(entry,root)
        for field in NUMERIC_FIELDS:same_state(value[field],failed[field])
        assert receiver_resources(value)==ref['resource_counts']
        assert len(value['graphs'])==11 and len(value['dals'])==9
        assert record['observed_hashes']==f['observed_hashes']
        expected.append(value);digests.append(entry['sha256'])
    for entry,state,digest in zip(records[2:],expected,digests):
        record,value=verified_record(entry,root);check_decode_identity(value,state);same_state(value['llr'],state['llr'])
        assert record['source_record_sha256']==digest
    result=dict(status='PASS',raw_F=2,raw_D=4,QPSK_full_reproduction_exact=True,integer_QPSK_equal_dense_QPSK=True,
        all_own_LLR_decodes_exact=True,reference_and_QPSK_decoded_difference_preserved=True,
        summary_sha256=sha(path),contract_sha256=sha(cpath),source_sha256=sha(manifest),
        scope='fixed old failing development block; preserved counterexample; no new statistical sample or complete cost result')
    with (root/'evidence/projection-sensitive-replay-v1-raw-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))


if __name__=='__main__':audit(Path(sys.argv[1]))
