"""Exact offline residual-target decomposition; no new inference or solve."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np


def decompose(y,H,Hc,p,d,mu,noise,A,g0):
    inputs=[np.asarray(v,dtype=np.complex128) for v in (y,H,Hc,p,d,mu,noise,A,g0)]
    y,H,Hc,p,d,mu,noise,A,g0=inputs;n=len(y)
    if (y.shape!=(n,) or H.shape!=(n,n) or Hc.shape!=(n,n)
            or any(v.shape!=(n,) for v in (p,d,mu,noise)) or A.ndim!=2 or A.shape[0]!=n
            or g0.shape!=(A.shape[1],) or any(not np.isfinite(v).all() for v in inputs)):
        raise ValueError('finite matching saved arrays required')
    physical=H@(p+d);saved_defect=y-physical-noise
    scale=np.linalg.norm(y)+np.linalg.norm(physical)+np.linalg.norm(noise)
    if not scale or np.linalg.norm(saved_defect)>1e-6*scale:
        raise ValueError('physical observation mismatch exceeds frozen precision bound')
    names=['pilot_error','channel_error_on_mu','data_decision_error','thermal_noise','projection_anchor','saved_rounding']
    terms=np.stack([(H-Hc)@p,(H-Hc)@mu,H@(d-mu),noise,Hc@(p+mu)-A@g0,saved_defect])
    residual=y-A@g0;reconstructed=terms.sum(axis=0)
    den=np.linalg.norm(residual)+np.linalg.norm(terms)
    reconstruction_error=float(np.linalg.norm(residual-reconstructed)/den) if den else 0.
    if reconstruction_error>1e-12:raise ValueError('residual decomposition mismatch')
    gram=terms.conj()@terms.T
    np.testing.assert_allclose(gram,gram.conj().T,rtol=1e-12,atol=1e-12)
    energy=float(np.vdot(residual,residual).real)
    np.testing.assert_allclose(gram.real.sum(),energy,rtol=1e-12,atol=1e-12)
    ep=terms[0];target_energy=float(gram[0,0].real);target_dot=np.vdot(ep,residual)
    rows={name:dict(energy=float(gram[j,j].real),energy_over_pilot_error=float(gram[j,j].real/target_energy) if target_energy else None,real_alignment_over_pilot_error=float(gram[0,j].real/target_energy) if target_energy else None) for j,name in enumerate(names)}
    return dict(terms=terms,gram=gram,residual=residual,term_names=names,metrics=dict(terms=rows,pilot_error_energy=target_energy,residual_energy=energy,residual_energy_over_pilot_error=energy/target_energy if target_energy else None,residual_real_alignment_over_pilot_error=float(target_dot.real/target_energy) if target_energy else None,residual_squared_complex_correlation=float(abs(target_dot)**2/(energy*target_energy)) if energy and target_energy else None,all_cross_energy=float(gram.real.sum()-np.trace(gram).real),reconstruction_relative_error=reconstruction_error,saved_defect_relative=float(np.linalg.norm(saved_defect)/scale)))


def main(args):
    root=args.root;source=root/'source-terminal-controls-unit-v1';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    contract=root/'contracts'/(args.tag+'.json');c=json.loads(contract.read_text());manifest=source/'source-manifest.json'
    assert args.tag == c['schema'] == c['tag'] == 'e1a-residual-target-v1'
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
    estimators={}
    for sp in c['legal_summaries']:
        for e in json.loads((root/sp).read_text())['records']:
            if e['kind']=='A':
                key=e['block'],e['snr'];assert key not in estimators;estimators[key]=e
    assert len(estimators)==64
    out=root/'runs'/args.tag/'analysis'

    def calculate(block):
        pe=old['A',block,7,'G1_PROPAGATION'];_,physical=verified_record(pe,root)
        values={};rows=[]
        for snr in c['snrs']:
            raw,_=reuse_at_snr(physical['raw'],physical['diagnostics'],snr)
            ref=old['F',block,snr,'G1_FULL'];rr,state=verified_record(ref,root)
            observed={k:np.array(raw[k],copy=True) for k in ('y','pilot','sigma2')}
            observed['constellation']=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j])
            assert rr['observed_hashes']==hashes(observed)
            d=state['dals'][-1];assert d['outer_iter']==9 and d['mode']=='mean' and not d['oracle_mean']
            assert d['moment_source']=='code_feedback.ce'
            ids=d['support_delays']*5+d['support_dopplers']+2
            legal_inputs=dict(y=raw['y'],pilot=raw['pilot'],mu=d['mu'],Hc=state['H'],support=ids,c1=raw['params']['c1'],c2=raw['params']['c2'])
            ae=estimators[block,snr];ar,fit=verified_record(ae,root)
            assert ar['reference_record_sha256']==ref['sha256'] and ar['physical_record_sha256']==pe['sha256']
            assert ar['legal_input_hashes']==hashes(legal_inputs)
            noise=np.sqrt(raw['sigma2'])*raw['noise']
            for capacity in ('S','D'):
                v=fit[capacity]
                result=decompose(raw['y'],raw['H'],state['H'],raw['pilot'],raw['data'],d['mu'],noise,v['A'],v['previous'])
                values[f'{snr}_{capacity}']=result
                rows.append(dict(block=block,snr=snr,capacity=capacity,metrics=result['metrics'],estimate_record_sha256=ae['sha256'],physical_record_sha256=pe['sha256'],reference_record_sha256=ref['sha256']))
        return dict(values=values,rows=rows)

    def audit(summary):
        assert summary['status']=='COMPLETE' and summary['calls']==dict(A=32)
        entries=summary['records'];assert len(entries)==32 and [e['block'] for e in entries]==list(range(32))
        rows=[];arrays=0
        for e in entries:
            record,value=verified_record(e,root);again=calculate(e['block'])
            assert flatten(value,{})==flatten(again,{})
            assert e['kind']=='A' and e['arm']=='RESIDUAL_TARGET' and e['snr']==7
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
            run.call('A',dict(block=b,snr=7,split=old['A',b,7,'G1_PROPAGATION']['split'],arm='RESIDUAL_TARGET'),
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
