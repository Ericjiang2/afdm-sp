"""Bounded A-02 initial-estimation producer and independent raw replay."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

from ab_model_v1 import physical_module
import a02_estimator_v1 as estimator
from afdm_sp_joint_unrolled.bandlimited_basis import normalized_geometry
from afdm_sp_joint_unrolled.bandlimited_estimation import fit_coefficients
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
from afdm_sp_joint_unrolled.light_gap_replay import LightRun, verified_record
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles


def check_equal(a,b,path='state'):
    """Exact discrete/complex64 results; double diagnostics allow 1e-11 roundoff."""
    if path=='state.times':return
    if isinstance(a,dict):
        assert set(a)==set(b),path
        for key in a:check_equal(a[key],b[key],path+'.'+key)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):check_equal(x,y,path+'.'+str(i))
    elif isinstance(a,np.ndarray):
        assert a.dtype==b.dtype and a.shape==b.shape,path
        if a.dtype in (np.dtype('complex128'),np.dtype('float64')):
            np.testing.assert_allclose(a,b,atol=1e-11,rtol=1e-11,err_msg=path)
        else:np.testing.assert_array_equal(a,b,err_msg=path)
    elif isinstance(a,float):
        np.testing.assert_allclose(a,b,atol=1e-11,rtol=1e-11,err_msg=path)
    else:assert a==b,path


def oracle_score(value,observation,truth):
    """Truth support diagnostic, kept outside the observed estimator."""
    geom=estimator.geometry_from_value(value)
    delays=np.unique(truth['delays'])
    columns=np.concatenate([np.arange(l*geom.q,(l+1)*geom.q) for l in delays])
    design=geom.sensing(observation['pilot'])[:,columns]
    info=normalized_geometry(design)
    result=dict(label='ORACLE_DELAY_ONLY',delays=delays,columns=columns,geometry=info,
        status='QUALIFIED' if info['qualified'] else 'EXCLUDED_RANK_OR_CONDITION')
    if info['qualified']:
        fits={name:fit_coefficients(design,observation['y'],strength) for name,strength in [('ls',0.),('ridge',.1)]}
        result['fits']=fits
        result['scores']=estimator.score(dict(family=value['family'],q=value['q'],basis=value['basis'],
            selection=dict(columns=columns),fits=fits),observation,truth)
    return result


def summaries(value):
    fields=('channel_nmse','pilot_nmse','observed_residual','representation','selection','cross_terms','closure_error')
    out={name:{k:v[k] for k in fields} for name,v in value['external'].items()}
    for name,item in value['external'].items():
        out[name]['components']={key:float(item['component_gram'][i,i]) for i,key in enumerate(item['component_names'])}
    return out


def estimate_and_score(obs,family,q,raw):
    before=hashes(obs)
    counts=dict(lstsq=0,coding_calls=0)
    with torch.no_grad(),estimator.registered_receiver.base.cpu_lstsq(counts),estimator.registered_receiver.base.forbid_coding(counts):
        value=estimator.estimate(obs,family,q)
    value['actual_counts']=counts
    expected=2+(len(value['selection']['columns'])+1 if family=='small' else 0)
    assert counts==dict(lstsq=expected,coding_calls=0)
    start=time.perf_counter()
    value['external']=estimator.score(value,obs,raw)
    value['external_oracle']=oracle_score(value,obs,raw)
    value['times']['external_scoring']=time.perf_counter()-start
    assert hashes(obs)==before
    return value


def main(args):
    root=args.root
    contract_path=root/'contracts'/(args.tag+'.json')
    c=json.loads(contract_path.read_text())
    source=root/c['source_directory'];helpers=source/'helpers'
    assert c['schema']=='a02-v1' and c['stage'] in ('engineering','development')
    engineering=c['stage']=='engineering';split=0 if engineering else 1
    assert c['split']==split and c['blocks']==([0,1] if engineering else list(range(c['blocks'][0],c['blocks'][-1]+1)))
    if not engineering:assert c['blocks'] in (list(range(32)),list(range(32,64)))
    assert c['device']=='cpu' and c['threads']==1
    manifest_path=source/'source-manifest.json';manifest=json.loads(manifest_path.read_text())
    assert sha(manifest_path)==c['source_sha256']
    files={source/'afdm_sp_joint_unrolled'/name:digest for name,digest in manifest.items()}
    files.update({helpers/name:digest for name,digest in c['helper_hashes'].items()})
    files.update({contract_path:sha(contract_path),manifest_path:c['source_sha256'],
        root/'contracts/ab-contract-v1.json':c['ab_contract_sha256'],
        root/'contracts/a02-protocol-v1.md':c['protocol_sha256'],
        root/'contracts/a02-phase-recovery-v1.md':c['phase_protocol_sha256']})
    guard=BoundFiles(files);guard.verify()
    if not engineering:
        a=json.loads((root/c['engineering_audit']).read_text())
        assert a['status']=='PASS' and a['recipe']==c['recipe']
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    physical=physical_module(helpers/'physical_transfer_model_v1.py',split)
    output=root/'runs'/args.tag
    expected_calls=dict(A=len(c['blocks'])*41+(10 if engineering else 0))
    assert {k:v for k,v in c['bounds'].items() if k!='seconds'}==expected_calls
    summary_path=output/c['stage']/'summary.json'
    if args.mode=='audit':
        end=json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code']==0 and not end['timed_out']
        summary=json.loads(summary_path.read_text())
        assert summary['status']=='COMPLETE' and summary['calls']==expected_calls
        entries={(e['block'],e['snr'],e['arm']):e for e in summary['records']}
        assert len(entries)==expected_calls['A']
        checked=0
        for block in c['blocks']:
            ae=entries[block,0,'INPUT'];_,raw=verified_record(ae,output)
            physical.validate(raw,'uwa',block)
            for snr in (10,20):
                for pilot in ('p0','pZ'):
                    obs=physical.observed(raw,pilot,snr)
                    for family,q in estimator.CONFIGS:
                        arm=f'{pilot}__{family}_q{q}'
                        entry=entries[block,snr,arm]
                        record,value=verified_record(entry,output)
                        assert record['observed_hashes']==hashes(obs) and record['input_sha256']==ae['sha256']
                        replay=estimate_and_score(obs,family,q,raw)
                        check_equal(value,replay)
                        assert summaries(value)==entry['scores']==record['scores']
                        checked+=1
                        if engineering and block==0 and snr==20 and pilot=='p0':
                            _,repeat=verified_record(entries[block,snr,arm+'_REPEAT'],output)
                            check_equal(value,repeat)
        guard.verify()
        report=dict(status='PASS',saved_records=len(entries),replayed_estimates=checked,
            paired_fits=2*checked,full_receiver_calls=0,recipe=c['recipe'],
            summary_sha256=sha(summary_path),source_sha256=sha(manifest_path),
            contract_sha256=sha(contract_path),scope='initial estimation and external error accounting; zero BP')
        with (root/'evidence'/(args.tag+'-audit.json')).open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(report),flush=True)
        return
    run=LightRun(output,c['stage'],c['bounds'],c['output_bytes'],guard)
    try:
        run.write('environment.json',dict(numpy=np.__version__,torch=torch.__version__,device='cpu',threads=1,
            coefficient_dtype='complex64',geometry_dtype='complex128',lstsq_driver='gels',recipe=c['recipe']))
        for block in c['blocks']:
            raw,_=run.call('A',dict(block=block,snr=0,arm='INPUT',split=split),
                lambda:physical.generate('uwa',block),lambda _: {},dict(seed_prefix=list(physical.SEED_PREFIX)))
            ae=run.records[-1];physical.validate(raw,'uwa',block)
            for snr in (10,20):
                for pid,pilot in enumerate(('p0','pZ')):
                    obs=physical.observed(raw,pilot,snr)
                    order=list(estimator.CONFIGS)
                    np.random.default_rng([20260914,125851,split,0,block,7,snr,pid]).shuffle(order)
                    for family,q in order:
                        arm=f'{pilot}__{family}_q{q}'
                        value,_=run.call('A',dict(block=block,snr=snr,arm=arm,split=split),
                            lambda:estimate_and_score(obs,family,q,raw),summaries,
                            dict(observed_hashes=hashes(obs),input_sha256=ae['sha256'],order=order))
                        if engineering and block==0 and snr==20 and pilot=='p0':
                            repeated,_=run.call('A',dict(block=block,snr=snr,arm=arm+'_REPEAT',split=split),
                                lambda:estimate_and_score(obs,family,q,raw),summaries,
                                dict(observed_hashes=hashes(obs),input_sha256=ae['sha256']))
                            check_equal(value,repeated)
            print(json.dumps(dict(block=block,calls=run.counts,wall_seconds=time.time()-run.started)),flush=True)
        assert run.counts==expected_calls
        guard.verify()
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,records=run.records,
            source_sha256=sha(manifest_path),contract_sha256=sha(contract_path),recipe=c['recipe'],
            full_receiver_calls=0,wall_seconds=time.time()-run.started))
        print(json.dumps(dict(status='COMPLETE',calls=run.counts)),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--tag',required=True);p.add_argument('--mode',choices=('run','audit'),default='run')
    main(p.parse_args())
