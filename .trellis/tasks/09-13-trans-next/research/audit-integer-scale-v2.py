"""Raw full-chain scale checks and descriptive paired timings; no new F/D."""
import hashlib
import json
from pathlib import Path
import statistics
import sys


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    source=root/'source-receiver-domain-v1';package=source/'afdm_sp_joint_unrolled';manifest=source/'source-manifest.json'
    assert sha(manifest)=='147c114aff1904d34deb4479885e7992933c912ab10082fe259aa052d95ad550'
    assert json.loads(manifest.read_text())=={str(p.relative_to(package)):sha(p) for p in package.rglob('*.py')}
    sys.path.insert(0,str(source))
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes,load_state,observed_at_snr
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record,check_decode_identity
    from afdm_sp_joint_unrolled.light_gap_receiver_run import NUMERIC_FIELDS,receiver_resources
    from afdm_sp_joint_unrolled.trans_next_stop_run import same_state
    tag='integer-scale-engineering-v2';path=root/'runs'/tag/'engineering/summary.json';s=json.loads(path.read_text())
    cpath=root/'contracts'/(tag+'.json');c=json.loads(cpath.read_text());end_path=root/'evidence'/(tag+'-exit.json');end=json.loads(end_path.read_text())
    assert end['exit_code']==0 and not end['timed_out']
    assert s['status']=='COMPLETE' and s['calls']==dict(F=30,D=30)
    assert s['contract_sha256']==sha(cpath) and s['source_sha256']==sha(manifest)
    assert s['script_sha256']==sha(root/'evidence'/(tag+'.py'))
    for name,digest in c['old_inputs'].items():assert sha(root/name)==digest
    records=s['records'];assert [r['kind'] for r in records]==['F']*30+['D']*30
    assert len(s['checks'])==30 and len(s['cells'])==len(s['exogenous'])==5
    reserve_times={'F':[],'D':[]};files={};table=[]
    for block,domain in enumerate(c['cells']):
        exo=s['exogenous'][block];assert exo['block']==block and exo['namespace']==c['namespace'] and exo['split']==1
        raw=load_state(exo['state']);assert hashes({k:raw[k] for k in exo['hashes']})==exo['hashes']
        observed_hashes=hashes(observed_at_snr(raw,7));base=None
        cells=s['cells'][block];assert cells['code_identity']==domain['code_identity']
        assert all(cells['domain'][k]==domain[k] for k in cells['domain'])
        entries=records[6*block:6*block+6]
        assert [r['arm'] for r in entries]==['DENSE','INTEGER','INTEGER','DENSE','DENSE','INTEGER']
        assert [r['phase'] for r in entries]==['qualification']*2+['measurement']*4
        assert [r['repeat'] for r in entries]==[0,0,0,0,1,1]
        graph_bounds=[]
        for j,entry in enumerate(entries):
            index=6*block+j;record,value=verified_record(entry,root)
            assert entry['block']==block and entry['snr']==7 and entry['N']==domain['N'] and entry['v_mean']==domain['v_mean']
            assert record['observed_hashes']==observed_hashes and record['code_identity']==domain['code_identity']
            assert record['audit']==(j<2)
            if base is None:base=value
            for field in NUMERIC_FIELDS:same_state(value[field],base[field])
            same_state(value['bp_schedule'],base['bp_schedule'])
            counts=receiver_resources(value);assert counts==receiver_resources(base)
            check=s['checks'][index];assert check['resource_counts']==counts and check['numeric_exact'] is True
            assert check['reference_record_sha256']==entries[0]['sha256']
            if j<2:
                assert len(value['dals'])==counts['CE_solves']
                assert len(value['graphs'])==counts['outer_BP_calls']+counts['terminal_BP_calls']
            else:assert not value['graphs'] and not value['dals']
            if entry['arm']=='INTEGER':
                layouts=value['integer_graph_calls'];calls=value['bp_schedule']['calls']
                assert len(layouts)==len(calls)==counts['outer_BP_calls']
                bounds=[]
                for layout,call in zip(layouts,calls):
                    assert layout['complete_matrix_verified']==(j<2)
                    assert layout['candidate_entries'] % domain['N']==0 and call['edges']<=layout['candidate_entries']
                    bounds.append(dict(D=layout['candidate_entries']//domain['N'],E=call['edges'],N_times_D=layout['candidate_entries'],complete_matrix_verified=layout['complete_matrix_verified']))
                assert bounds==check['integer_graph_bounds']
                if j==1:graph_bounds=bounds
            d_entry=records[30+index];d_record,decoded=verified_record(d_entry,root)
            assert all(entry[k]==d_entry[k] for k in ('block','snr','split','arm','phase','repeat','N','v_mean'))
            assert d_record['source_record_sha256']==entry['sha256'];check_decode_identity(decoded,value);same_state(decoded['llr'],value['llr'])
            for e,r in [(entry,record),(d_entry,d_record)]:
                assert e['seconds']==r['seconds']>0 and e['CPU_seconds']==r['CPU_seconds']>=0
                reserve=json.loads(Path(e['record']).with_name(r['token']+'-reserve.json').read_text())
                assert reserve['token']==r['token'] and reserve['kind']==r['kind']
                reserve_times[r['kind']].append(reserve['reserved_at']);files[e['record']]=e['sha256']
        means={a:statistics.mean(r['seconds'] for r in entries if r['phase']=='measurement' and r['arm']==a) for a in ('DENSE','INTEGER')}
        table.append(dict(block=block,domain=cells['domain'],independent_blocks=1,timed_calls_per_arm=2,
            mean_seconds=means,reduction=1-means['INTEGER']/means['DENSE'],setup_seconds=cells['setup_seconds'],
            generation_seconds=exo['generation_seconds'],resource_counts=receiver_resources(base),integer_graph_bounds=graph_bounds,
            process_peak_rss_KiB=max(r['process_peak_rss_KiB'] for r in s['checks'][6*block:6*block+6])))
    assert max(reserve_times['F']) < s['collection_finished_at'] <= min(reserve_times['D'])
    result=dict(status='PASS',raw_F=30,raw_D=30,exact_same_cell_numeric=30,domains=5,table=table,
        summary_sha256=sha(path),source_sha256=sha(manifest),contract_sha256=sha(cpath),exit_sha256=sha(end_path),
        script_sha256=sha(Path(__file__)),verified_record_hashes=files,
        scope='one independent block per domain, two uninstrumented paired repeats; descriptive scale engineering, not asymptotic proof or formal COST')
    with (root/'evidence/integer-scale-engineering-v2-raw-audit.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('verified_record_hashes','table')}))
    print(json.dumps(table,indent=2))


if __name__=='__main__':audit(Path(sys.argv[1]))
