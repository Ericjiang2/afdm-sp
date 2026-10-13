"""Offline audit of saved soft variance; no covariance solve or new inference."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np


def variance_metrics(data,mu,variance,Hc,Htrue,noise,sigma2):
    variance=np.asarray(variance)
    if np.iscomplexobj(variance):raise ValueError('real symbol variance required')
    variance=variance.astype(np.float64)
    data,mu,Hc,Htrue,noise=[np.asarray(v,dtype=np.complex128) for v in (data,mu,Hc,Htrue,noise)]
    n=len(data)
    if (data.shape!=(n,) or mu.shape!=(n,) or variance.shape!=(n,) or noise.shape!=(n,)
            or Hc.shape!=(n,n) or Htrue.shape!=(n,n) or any(not np.isfinite(v).all() for v in (data,mu,variance,Hc,Htrue,noise))
            or not np.isfinite(sigma2) or sigma2<=0 or np.any(variance<0) or np.any(variance>.5+1e-6)):
        raise ValueError('invalid physical QPSK variance inputs')
    np.testing.assert_allclose(abs(data)**2,.5,rtol=1e-6,atol=1e-7)
    error=data-mu;error_sq=abs(error)**2;labels=np.searchsorted([.01,.1,.5],variance/.5,side='right')
    def ratio(actual,predicted):return float(actual/predicted) if predicted else None
    bins=[]
    for k in range(4):
        mask=labels==k;actual=float(error_sq[mask].sum());pred=float(variance[mask].sum())
        bins.append(dict(bin=k,count=int(mask.sum()),actual_error_sum=actual,predicted_variance_sum=pred,error_to_variance=ratio(actual,pred)))
    assert sum(x['count'] for x in bins)==n
    estimated_channel_error=Hc@error;physical_channel_error=Htrue@error;combined=estimated_channel_error+noise
    column_energy=np.sum(abs(Hc)**2,axis=0)
    predicted_data=float(column_energy@variance);predicted_total=predicted_data+n*float(sigma2)
    actual_data=float(np.vdot(estimated_channel_error,estimated_channel_error).real)
    actual_physical=float(np.vdot(physical_channel_error,physical_channel_error).real)
    actual_noise=float(np.vdot(noise,noise).real);cross=float(2*np.vdot(estimated_channel_error,noise).real)
    actual_total=float(np.vdot(combined,combined).real)
    np.testing.assert_allclose(actual_total,actual_data+actual_noise+cross,rtol=1e-12,atol=1e-12)
    return dict(symbol_error_squared=error_sq,variance=variance,estimated_channel_error=estimated_channel_error,physical_channel_error=physical_channel_error,combined_error=combined,metrics=dict(symbols=n,actual_error_sum=float(error_sq.sum()),predicted_variance_sum=float(variance.sum()),error_to_variance=ratio(error_sq.sum(),variance.sum()),zero_variance_symbols=int(np.sum(variance==0)),zero_variance_error_sum=float(error_sq[variance==0].sum()),moment_identity_max_error=float(np.max(abs(abs(mu)**2+variance-.5))),bins=bins,predicted_data_energy=predicted_data,actual_data_energy=actual_data,data_energy_ratio=ratio(actual_data,predicted_data),actual_physical_data_energy=actual_physical,predicted_total_energy=predicted_total,actual_total_energy=actual_total,total_energy_ratio=ratio(actual_total,predicted_total),actual_noise_energy=actual_noise,data_noise_cross_energy=cross))


def main(args):
    root=args.root;source=root/'source-terminal-controls-unit-v1';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    contract=root/'contracts'/(args.tag+'.json');c=json.loads(contract.read_text());manifest=source/'source-manifest.json'
    assert args.tag == c['schema'] == c['tag'] == 'e1a-soft-variance-v1'
    assert sha(contract)==args.contract_sha256 and sha(Path(__file__))==args.script_sha256
    assert sha(manifest)==c['source_sha256']=='5c0fac1eab2b9d8d55c54110c988b0906661bc85be4de8d8d5e3502f1c0602b0'
    assert c['blocks']==list(range(32)) and c['snrs']==[7,8]
    assert c['bounds']==dict(A=32,seconds=300) and c['device']=='cpu' and c['threads']==1
    guard=setup_guard(SimpleNamespace(contract=contract,contract_sha256=args.contract_sha256,
        source_manifest=manifest,source_sha256=sha(manifest)),c);guard.verify()
    for sp,ap in c['audited_inputs'].items():
        a=json.loads((root/ap).read_text());assert a['status']=='PASS' and a['summary_sha256']==sha(root/sp)
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    upstream=json.loads((root/'runs/g1-strong-development-recovery-v1/development/summary.json').read_text())
    old={(r['kind'],r['block'],r['snr'],r['arm']):r for r in upstream['records']}
    out=root/'runs'/args.tag/'analysis'

    def calculate(block):
        pe=old['A',block,7,'G1_PROPAGATION'];_,physical=verified_record(pe,root)
        values={};rows=[]
        for snr in c['snrs']:
            raw,_=reuse_at_snr(physical['raw'],physical['diagnostics'],snr)
            ref=old['F',block,snr,'G1_FULL'];rr,state=verified_record(ref,root)
            observed={k:np.array(raw[k],copy=True) for k in ('y','pilot','sigma2')}
            observed['constellation']=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
            assert rr['observed_hashes']==hashes(observed) and rr['physical_record_sha256']==pe['sha256']
            d=state['dals'][-1];assert d['outer_iter']==9 and d['mode']=='mean' and not d['oracle_mean']
            assert d['moment_source']=='code_feedback.ce'
            noise=np.sqrt(raw['sigma2'])*raw['noise']
            result=variance_metrics(raw['data'],d['mu'],d['finite_variance'],state['H'],raw['H'],noise,raw['sigma2'])
            values[str(snr)]=result
            rows.append(dict(block=block,snr=snr,metrics=result['metrics'],physical_record_sha256=pe['sha256'],reference_record_sha256=ref['sha256']))
        return dict(values=values,rows=rows)

    def audit(summary):
        assert summary['status']=='COMPLETE' and summary['calls']==dict(A=32)
        entries=summary['records'];assert len(entries)==32 and [e['block'] for e in entries]==list(range(32))
        rows=[];arrays=0
        for e in entries:
            record,value=verified_record(e,root);again=calculate(e['block'])
            assert flatten(value,{})==flatten(again,{})
            assert e['kind']=='A' and e['arm']=='SOFT_VARIANCE' and e['snr']==7
            assert e['split']==old['A',e['block'],7,'G1_PROPAGATION']['split']
            assert record['truth_access']=='explicit offline truth decomposition only'
            reservation=json.loads(Path(e['record']).with_name(record['token']+'-reserve.json').read_text())
            assert all(reservation[k]==record[k]==e[k] for k in ('kind','block','snr','arm','split'))
            rows+=value['rows'];arrays+=finite_arrays(value)
        return dict(rows=rows,arrays=arrays,saved_records=32)
    if args.mode=='audit':
        started=time.time();end=json.loads((root/'evidence'/(args.tag+'-exit.json')).read_text())
        assert end['exit_code']==0 and not end['timed_out']
        summary=json.loads((out/'summary.json').read_text())
        assert summary['script_sha256']==args.script_sha256 and summary['contract_sha256']==args.contract_sha256
        result=audit(summary);assert result==summary['raw_checks'];guard.verify()
        result.update(status='PASS',source_sha256=sha(manifest),script_sha256=args.script_sha256,
            contract_sha256=args.contract_sha256,summary_sha256=sha(out/'summary.json'),wall_seconds=time.time()-started,
            new_F_T_D_A_calls=0,new_CE_solves=0,independence='main-session self-review; weak',scope=c['scope'])
        with (root/'evidence'/(args.tag+'-raw-audit.json')).open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
        print(json.dumps({k:v for k,v in result.items() if k not in ('rows','geometries')}));return
    run=LightRun(root/'runs'/args.tag,'analysis',c['bounds'],c['output_bytes'],guard)
    try:
        for b in c['blocks']:
            run.call('A',dict(block=b,snr=7,split=old['A',b,7,'G1_PROPAGATION']['split'],arm='SOFT_VARIANCE'),
                lambda:calculate(b),lambda v:dict(rows=len(v['rows'])),dict(truth_access='explicit offline truth decomposition only'))
            print(json.dumps(dict(block=b,calls=run.counts)),flush=True)
        summary=dict(status='COMPLETE',calls=run.counts,records=run.records,source_sha256=sha(manifest),
            script_sha256=args.script_sha256,contract_sha256=args.contract_sha256,scope=c['scope'])
        summary['raw_checks']=audit(summary);guard.verify();run.meter.verify()
        summary['wall_seconds']=time.time()-run.started;run.write('summary.json',summary)
    except BaseException as exc:
        run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--tag',required=True)
    p.add_argument('--mode',choices=['run','audit'],default='run')
    p.add_argument('--contract-sha256',required=True);p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
