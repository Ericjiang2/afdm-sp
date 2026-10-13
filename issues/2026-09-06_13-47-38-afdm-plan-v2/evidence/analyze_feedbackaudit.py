"""Verify actual feedback consumers and separate production/reference equality."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent


def main():
    with tarfile.open(ROOT/'feedbackaudit-runtime.tar.gz') as archive:
        raw={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    q=json.loads(raw['queue-status.json'])
    assert q['complete'] and len(q['runs'])==4 and all(r['exit_code']==0 for r in q['runs'])
    frames={name:json.loads(raw[name+'/frames.jsonl']) for name in ('on','off','det_on','det_off')}
    primary=['output_h_sha256','output_x_sha256','sigma2_final','raw_errors','info_errors','decoded_bits_sha256']
    soft=['final_bp_mu_sha256','final_bp_var_sha256','final_llr_sha256']
    modes={'f_mean':'mean','f_uniform':'covariance_uniform','f_dynamic':'covariance','o_data':'mean'}
    evidence={}
    for name,f in frames.items():
        assert f['input_hashes']==frames['on']['input_hashes'] and set(f['arms'])==set(modes)
        for arm,a in f['arms'].items():
            assert a['finite'] and a['dals_mode']==modes[arm] and a['dals_temperature']==1
            assert a['oracle']==(arm=='o_data')
            assert all(c['unique_count']<=(48 if c['stage']=='temporary' else 40) for c in a['capacity_trace'])
            if name.endswith('on'):
                consumers=a['dals_consumers']
                assert [s['outer_iter'] for s in consumers]==list(range(1,10))
                assert len({s['H']['sha256'] for s in consumers})>1
                assert all(s['oracle_mean']==(arm=='o_data') for s in consumers)
                assert all(s['covariance_frozen_within_solve'] for s in consumers)
                assert all(('covariance' in s)==(arm in ('f_uniform','f_dynamic')) for s in consumers)
                if arm=='f_uniform':
                    assert len({s['consumed_variance']['sha256'] for s in consumers})==1
                if arm=='f_dynamic':
                    assert all(s['consumed_variance']['sha256']==s['finite_variance']['sha256'] for s in consumers)
                assert sorted((r['stage'],r['outer_iter']) for r in a['reliability'])==[
                    (stage,i) for stage in ('dals_feedback','noise_feedback') for i in range(1,10)]
                assert all(sum(b['count'] for b in r['bins'])+r['out_of_range_count']==1024 for r in a['reliability'])
                if arm=='f_mean':
                    comparisons=a['frozen_state_comparisons'];assert len(comparisons)==9
                    assert a['dals_snapshot']['sha256']
                    for c in comparisons:
                        assert set(c['same_support_channel_nmse'])=={'previous','unweighted','uniform','dynamic'}
                        assert all(c[m]['own_objective_after']<=c[m]['own_objective_before'] for m in ('unweighted','uniform','dynamic'))
            else:
                assert a['dals_consumers']==[] and a['reliability']==[]
    assert len({a['dals_consumers'][0]['H']['sha256'] for a in frames['on']['arms'].values()})==1
    historical=json.loads((ROOT/'a0-a2-wire-runtime.json').read_text())['frames'][0]['arms']['baseline']
    for k in primary[:-1]: assert frames['on']['arms']['f_mean'][k]==historical[k]
    for arm in modes:
        a,b,d,e=[frames[n]['arms'][arm] for n in ('on','off','det_on','det_off')]
        assert all(a[k]==b[k] for k in primary)
        assert all(d[k]==e[k] for k in primary+soft)
        assert all(a[k]==d[k] for k in primary)
        evidence[arm]=dict(production_primary_exact=True,
            production_soft_exact={k:a[k]==b[k] for k in soft},
            isolated_deterministic_reference_primary_and_soft_exact=True,
            info_errors=a['info_errors'],dals_events=9)
    result=dict(scope='one fixed calibration frame engineering qualification, no FER inference',
        arms=evidence,queue=q,primary_exact_fields=primary,
        limitation='ordinary production final BP soft reductions are not bitwise repeatable; separate deterministic reference only, production backend unchanged',
        frozen_mean_snapshot=frames['on']['arms']['f_mean']['dals_snapshot'],
        offline_matrix_seconds=frames['on']['arms']['f_mean']['offline_matrix_seconds'],
        snapshot_io_seconds=frames['on']['arms']['f_mean']['dals_snapshot_io_seconds'],
        artifact_sha256={k:hashlib.sha256(v).hexdigest() for k,v in raw.items()})
    (ROOT/'feedbackaudit-runtime-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
