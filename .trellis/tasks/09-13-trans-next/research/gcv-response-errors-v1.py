"""External error scores of actual saved legal terminal inputs; no new inference."""
import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np


def metrics(Htrue, Hdet, pilot, cancellation, original):
    target = Htrue@pilot; error = target-cancellation
    initial_error = target-original; correction = cancellation-original
    pilot_power = float(np.vdot(target,target).real)
    channel_power = float(np.vdot(Htrue,Htrue).real)
    base_power = float(np.vdot(initial_error,initial_error).real)
    if min(pilot_power,channel_power) <= 0:
        raise ValueError('zero target energy')
    error_power = float(np.vdot(error,error).real)
    difference = Htrue-Hdet
    row = dict(pilot_nmse=error_power/pilot_power,
        operator_nmse=float(np.vdot(difference,difference).real)/channel_power,
        alignment=float(np.vdot(correction,initial_error).real)/base_power if base_power else None,
        correction_ratio=float(np.vdot(correction,correction).real)/base_power if base_power else None,
        error_ratio=error_power/base_power if base_power else None)
    if base_power:
        np.testing.assert_allclose(row['error_ratio'],1-2*row['alignment']+row['correction_ratio'],atol=1e-12,rtol=1e-12)
    if not np.isfinite(error).all() or any(not np.isfinite(v) for v in row.values() if v is not None):
        raise ValueError('nonfinite response error metric')
    return dict(pilot_error=error,metrics=row)


def main(args):
    root=args.root;source=root/'source-terminal-controls-unit-v1';sys.path.insert(0,str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun,setup_guard,verified_record
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays
    from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
    contract=root/'contracts'/(args.tag+'.json');c=json.loads(contract.read_text());manifest=source/'source-manifest.json'
    assert args.tag == c['schema'] == c['tag'] == 'gcv-response-errors-v1'
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
    for sp in c['legal_summaries']:
        for e in json.loads((root/sp).read_text())['records']:
            if e['kind']=='A':
                key=e['block'],e['snr'];assert key not in estimators;estimators[key]=e
            if e['kind']=='T':
                key=e['block'],e['snr'],e['arm'];assert key not in legal;legal[key]=e
    assert len(legal)==256 and len(estimators)==64
    arms=['S_GCV_P','S_GCV_ALL','D_GCV_P','D_GCV_ALL']
    out=root/'runs'/args.tag/'analysis'

    def calculate(block):
        pe=old['A',block,7,'G1_PROPAGATION'];_,physical=verified_record(pe,root)
        Htrue=physical['raw']['H'];pilot=physical['raw']['pilot'];values={};rows=[];geometries=[]
        for snr in c['snrs']:
            ref=old['F',block,snr,'G1_FULL'];_,state=verified_record(ref,root)
            original=state['H']@pilot
            ae=estimators[block,snr];ar,fit=verified_record(ae,root)
            assert ar['reference_record_sha256']==ref['sha256'] and ar['physical_record_sha256']==pe['sha256']
            for capacity in ('S','D'):
                v=fit[capacity];selection=v['selection'];energy=np.sum(abs(v['A'])**2,axis=0)
                assert energy.max()/energy.min()<1+1e-10
                eigenvalues=selection['singular_values']**2/selection['scale']
                full_rank=bool(selection['singular_values'][-1]>np.finfo(float).eps*max(v['A'].shape)*selection['singular_values'][0])
                geometries.append(dict(block=block,snr=snr,capacity=capacity,columns=len(eigenvalues),
                    full_rank=full_rank,lambda_min=float(eigenvalues[-1]),lambda_max=float(eigenvalues[0]),
                    gram_condition=float(eigenvalues[0]/eigenvalues[-1]) if full_rank else None,
                    white_ls_geometry_factor=float(np.mean(1/eigenvalues)) if full_rank else None,
                    normalized_gram_spectrum_source='previously audited saved SVD; no new decomposition',
                    estimate_record_sha256=ae['sha256']))
            for arm in arms:
                e=legal[block,snr,arm];record,value=verified_record(e,root)
                assert record['reference_record_sha256']==ref['sha256']
                assert record['physical_record_sha256']==pe['sha256']
                assert record['truth_access']=='external scoring only'
                Hdet=value['H'];cancellation=value['cancellation']
                assert hashes({k:value[k] for k in ('H','z','cancellation','sigma2_terminal','last_check_prior')})==record['terminal_input_hashes']
                result=metrics(Htrue,Hdet,pilot,cancellation,original)
                values[f'{snr}_{arm}']=result
                rows.append(dict(block=block,snr=snr,arm=arm,metrics=result['metrics'],scores=e['scores'],
                    terminal_record_sha256=e['sha256'],physical_record_sha256=pe['sha256']))
        return dict(values=values,rows=rows,geometries=geometries)

    def audit(summary):
        assert summary['status']=='COMPLETE' and summary['calls']==dict(A=32)
        entries=summary['records'];assert len(entries)==32 and [e['block'] for e in entries]==list(range(32))
        rows=[];arrays=0;geometries=[]
        for e in entries:
            record,value=verified_record(e,root);again=calculate(e['block'])
            assert flatten(value,{})==flatten(again,{})
            assert e['kind']=='A' and e['arm']=='RESPONSE_ERROR' and e['snr']==7
            assert e['split']==old['A',e['block'],7,'G1_PROPAGATION']['split']
            assert record['truth_access']=='explicit offline external metric only'
            reservation=json.loads(Path(e['record']).with_name(record['token']+'-reserve.json').read_text())
            assert all(reservation[k]==record[k]==e[k] for k in ('kind','block','snr','arm','split'))
            rows+=value['rows'];arrays+=finite_arrays(value);geometries+=value['geometries']
        return dict(rows=rows,arrays=arrays,saved_records=32,geometries=geometries)
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
            run.call('A',dict(block=b,snr=7,split=old['A',b,7,'G1_PROPAGATION']['split'],arm='RESPONSE_ERROR'),
                lambda:calculate(b),lambda v:dict(rows=len(v['rows'])),dict(truth_access='explicit offline external metric only'))
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
