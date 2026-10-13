"""Exact realized observation mismatch decomposition; external truth only, no inference."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np


def decompose(y,H,B,p,d,c,noise,sigma2):
    values=[np.asarray(v,dtype=np.complex128) for v in (y,H,B,p,d,c,noise)]
    y,H,B,p,d,c,noise=values
    if y.ndim!=1 or not len(y):raise ValueError('nonempty observation vector required')
    n=len(y)
    if (H.shape!=(n,n) or B.shape!=(n,n) or any(v.shape!=(n,) for v in (p,d,c,noise))
            or any(not np.isfinite(v).all() for v in values)
            or not np.isfinite(sigma2) or sigma2<=0):
        raise ValueError('finite matching arrays and positive noise variance required')
    physical=H@(p+d);rounding=y-physical-noise
    scale=np.linalg.norm(y)+np.linalg.norm(physical)+np.linalg.norm(noise)
    if not scale or np.linalg.norm(rounding)>1e-6*scale:
        raise ValueError('physical observation mismatch exceeds frozen precision bound')
    terms=np.stack([H@p-c,(H-B)@d,noise,rounding])
    residual=y-c-B@d;clean=terms[0]+terms[1]
    denominator=np.linalg.norm(residual)+np.linalg.norm(terms)
    reconstruction=float(np.linalg.norm(residual-terms.sum(axis=0))/denominator) if denominator else 0.
    if reconstruction>1e-12:raise ValueError('observation residual reconstruction mismatch')
    gram=terms.conj()@terms.T;norm=n*float(sigma2)
    np.testing.assert_allclose(gram,gram.conj().T,rtol=1e-12,atol=1e-12)
    energy=float(np.vdot(residual,residual).real)
    np.testing.assert_allclose(gram.real.sum(),energy,rtol=1e-12,atol=1e-12)
    metrics=dict(pilot_over_noise=float(gram[0,0].real/norm),data_over_noise=float(gram[1,1].real/norm),
        pilot_data_cross_over_noise=float(2*gram[0,1].real/norm),
        clean_over_noise=float(np.vdot(clean,clean).real/norm),
        thermal_over_noise=float(gram[2,2].real/norm),
        clean_noise_cross_over_noise=float(2*(gram[0,2]+gram[1,2]).real/norm),
        rounding_over_noise=float(gram[3,3].real/norm),
        rounding_cross_over_noise=float(2*gram[:3,3].real.sum()/norm),
        total_over_noise=energy/norm,reconstruction_relative_error=reconstruction,
        saved_defect_relative=float(np.linalg.norm(rounding)/scale))
    if not all(np.isfinite(v) for v in metrics.values()):raise ValueError('nonfinite metric')
    return dict(terms=terms,gram=gram,residual=residual,
                term_names=['pilot_error','data_channel_error','thermal_noise','saved_rounding'],metrics=metrics)


def main(args):
    root=args.root;source=root/'source-terminal-controls-unit-v1';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    contract=root/'contracts'/(args.tag+'.json');c=json.loads(contract.read_text());manifest=source/'source-manifest.json'
    assert args.tag == c['schema'] == c['tag'] == 'e1a-observation-residual-v1'
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
    legal={};estimators={}
    for group,summaries in c['terminal_summaries'].items():
        for sp in summaries:
            for e in json.loads((root/sp).read_text())['records']:
                if e['kind']=='A':
                    key=group,e['block'],e['snr'];assert key not in estimators;estimators[key]=e
                if e['kind']=='T':
                    key=e['block'],e['snr'],e['arm'];assert key not in legal;legal[key]=e
    assert len(estimators)==192 and len(legal)==896
    groups={'S_ALL':'legal','D_GCV_ALL':'gcv','W_D_P':'white','W_D_ALL':'white'}
    arms=['A0',*groups]
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
            assert np.allclose(abs(raw['data'])**2,.5,rtol=0,atol=1e-12)
            noise=np.sqrt(raw['sigma2'])*raw['noise'];terminal_values={}
            for arm in arms:
                terminal_sha=None;estimate_sha=None
                if arm=='A0':
                    B=state['H'];cancellation=B@raw['pilot'];scores=ref['scores']
                else:
                    e=legal[block,snr,arm];record,value=verified_record(e,root)
                    ae=estimators[groups[arm],block,snr]
                    assert record['reference_record_sha256']==ref['sha256']
                    assert record['estimate_record_sha256']==ae['sha256']
                    assert record['physical_record_sha256']==pe['sha256']
                    assert record['truth_access']=='external scoring only'
                    assert hashes({k:value[k] for k in ('H','z','cancellation','sigma2_terminal','last_check_prior')})==record['terminal_input_hashes']
                    np.testing.assert_array_equal(value['sigma2_terminal'],raw['sigma2'])
                    np.testing.assert_array_equal(value['z'],raw['y']-value['cancellation'])
                    B=value['H'];cancellation=value['cancellation'];scores=e['scores']
                    terminal_sha=e['sha256'];estimate_sha=ae['sha256']
                    if arm.startswith('W_D'):terminal_values[arm]=(B,cancellation)
                result=decompose(raw['y'],raw['H'],B,raw['pilot'],raw['data'],cancellation,noise,raw['sigma2'])
                values[f'{snr}_{arm}']=result;pair=None
                if arm=='W_D_ALL':
                    Bp,cp=terminal_values['W_D_P']
                    np.testing.assert_array_equal(Bp,state['H'])
                    np.testing.assert_array_equal(cp,cancellation)
                    prior=values[f'{snr}_W_D_P'];delta=(B-Bp)@raw['data'];norm=len(raw['y'])*float(raw['sigma2'])
                    np.testing.assert_allclose(result['residual'],prior['residual']-delta,rtol=1e-12,atol=1e-12)
                    quadratic=float(np.vdot(delta,delta).real/norm)
                    cross=float(-2*np.vdot(delta,prior['residual']).real/norm)
                    actual=result['metrics']['total_over_noise']-prior['metrics']['total_over_noise']
                    np.testing.assert_allclose(actual,quadratic+cross,rtol=1e-12,atol=1e-12)
                    pair=dict(delta_energy_over_noise=quadratic,cross_over_noise=cross,total_change_over_noise=actual)
                rows.append(dict(block=block,snr=snr,arm=arm,metrics=result['metrics'],scores=scores,
                    detector_change=pair,terminal_record_sha256=terminal_sha,estimate_record_sha256=estimate_sha,
                    physical_record_sha256=pe['sha256'],reference_record_sha256=ref['sha256']))
        return dict(values=values,rows=rows)

    def audit(summary):
        assert summary['status']=='COMPLETE' and summary['calls']==dict(A=32)
        entries=summary['records'];assert len(entries)==32 and [e['block'] for e in entries]==list(range(32))
        rows=[];arrays=0
        for e in entries:
            record,value=verified_record(e,root);again=calculate(e['block'])
            assert flatten(value,{})==flatten(again,{})
            assert e['kind']=='A' and e['arm']=='OBSERVATION_RESIDUAL' and e['snr']==7
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
            run.call('A',dict(block=b,snr=7,split=old['A',b,7,'G1_PROPAGATION']['split'],arm='OBSERVATION_RESIDUAL'),
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
