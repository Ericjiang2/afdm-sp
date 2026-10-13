"""Read all registered historical blocks; compute legal candidate diagnostics."""
import argparse
import json
from pathlib import Path
import time

import numpy as np
import torch

from candidate_margin_v1 import QPSK,candidates,hard_symbols,stability,external_coverage
from afdm_sp_joint_unrolled.bottleneck_pilot import sha,hashes
from afdm_sp_joint_unrolled.light_gap_replay import LightRun,verified_record
from afdm_sp_joint_unrolled.supplement_timing_integrity import BoundFiles
from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
from a02_runner_v1 import check_equal


UARMS=('OMP_HARD','OMP_PLUS4','F2P_HEAD','F2P_RESID')
CARMS=('S_GCV_P','S_GCV_ALL','D_GCV_P','D_GCV_ALL','W_S_P','W_S_ALL','W_D_P','W_D_ALL','S_ALL','D_P_HALF')


def state_metrics(state,raw,obs,anchor,coded):
    h=state['H']
    cancellation=state['cancellation'] if 'cancellation' in state else h@obs['pilot']
    z=state['z'] if 'z' in state else obs['y']-cancellation
    soft=state['finite_message']['posterior_mean'] if coded else state['x_soft']
    candidate=candidates(dict(H=h,z=z,anchor=anchor,sigma2=float(obs['sigma2']),constellation=QPSK))
    norm=lambda v:float(np.vdot(v,v).real)
    hp=raw['H']@obs['pilot']
    metrics=dict(nmse=norm(h-raw['H'])/norm(raw['H']),hp=norm(hp-cancellation)/norm(hp),
        residual=norm(z-h@soft)/norm(obs['y']),margin=candidate['ambiguity_risk'])
    return candidate,metrics


def main(args):
    root=args.root;old=root.parent/'outputs_trans_next_20260913'
    cpath=root/'contracts/b02-v1.json';c=json.loads(cpath.read_text())
    source=root/'source-b02-v1';manifest=source/'source-manifest.json'
    assert sha(manifest)==c['source_sha256']
    files={source/'afdm_sp_joint_unrolled'/name:digest for name,digest in json.loads(manifest.read_text()).items()}
    files.update({source/'helpers'/name:digest for name,digest in c['helpers'].items()})
    files.update({old/name:digest for name,digest in c['input_summaries'].items()})
    files.update({old/name:digest for name,digest in c['input_audits'].items()})
    files.update({cpath:sha(cpath),root/'contracts/b02-protocol-v1.md':c['protocol_sha256']})
    guard=BoundFiles(files);guard.verify()
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    uindex={};cindex={};legal={}
    for relative in c['input_summaries']:
        s=json.loads((old/relative).read_text());assert s['status']=='COMPLETE'
        if 'physical-transfer-' in relative:
            for e in s['records']:
                if e['kind'] in ('A','F') and not e['arm'].endswith('_REPEAT'):
                    key=e['kind'],e['block'],e['snr'],e['arm'];assert key not in uindex;uindex[key]=e
        elif 'g1-strong-development-recovery' in relative:
            cindex={(e['kind'],e['block'],e['snr'],e['arm']):e for e in s['records']}
        else:
            for e in s['records']:
                if e['kind']=='T' and e['arm'] in CARMS:
                    key=e['block'],e['snr'],e['arm'];assert key not in legal;legal[key]=e
    assert len(legal)==32*2*len(CARMS)

    def calculate(domain,block):
        coded=domain=='coded1024';index=cindex if coded else uindex
        parent=index['A',block,7,'G1_PROPAGATION'] if coded else index['A',block,10,'uwa_INPUT']
        _,physical=verified_record(parent,old);raw=physical['raw'] if coded else physical
        truth=raw['info'] if coded else raw['bits']
        rows=[];arrays={};bindings=[parent]
        for snr in ((7,8) if coded else (10,20)):
            if coded:
                changed,_=reuse_at_snr(raw,physical['diagnostics'],snr)
                observations={'p0':{k:np.array(changed[k],copy=True) for k in ('y','pilot','sigma2')}}
                observations['p0']['constellation']=QPSK.copy()
            else:
                sigma=10.**(-snr/10)
                observations={pilot:dict(y=raw['noiseless'][pilot]+np.sqrt(sigma)*raw['noise'],
                    pilot=raw['pilots'][pilot].copy(),sigma2=np.array(sigma),constellation=QPSK.copy()) for pilot in ('p0','pZ')}
            for pilot,obs in observations.items():
                re=index['F',block,snr,'G1_FULL' if coded else pilot+'__OMP_BASE']
                rr,ref=verified_record(re,old);bindings.append(re)
                assert rr['observed_hashes']==hashes(obs)
                anchor=hard_symbols(ref['finite_message']['posterior_mean'] if coded else ref['x_soft'])
                ref_candidate,ref_metrics=state_metrics(ref,raw,obs,anchor,coded)
                baseline_bits=ref['info_hat'] if coded else ref['bits']
                baseline_error=baseline_bits!=truth
                context=f'{pilot}_{snr}'
                arrays[context+'__reference']=dict(candidates=ref_candidate,coverage=external_coverage(ref_candidate,raw['data']),metrics=ref_metrics)
                for arm in (CARMS if coded else UARMS):
                    entry=legal[block,snr,arm] if coded else index['F',block,snr,pilot+'__'+arm]
                    record,value=verified_record(entry,old);bindings.append(entry)
                    if coded:
                        assert record['reference_record_sha256']==re['sha256']
                        assert record['physical_record_sha256']==parent['sha256']
                    else:assert record['observed_hashes']==hashes(obs)
                    candidate,metrics=state_metrics(value,raw,obs,anchor,coded)
                    certificate=stability(ref_candidate,candidate)
                    actual=value['info_hat'] if coded else value['bits']
                    error=actual!=truth;rescued=baseline_error&~error;added=~baseline_error&error
                    coverage=external_coverage(candidate,raw['data'])
                    key=context+'__'+arm
                    arrays[key]=dict(candidates=candidate,stability=certificate,coverage=coverage,
                        rescued=rescued,added=added,baseline_error=baseline_error,error=error)
                    rows.append(dict(domain=domain,block=block,pilot=pilot,snr=snr,arm=arm,
                        partition='fit' if block%2==0 else 'heldout',metrics=metrics,reference_metrics=ref_metrics,
                        features={k:metrics[k]-ref_metrics[k] for k in metrics},
                        rescued=int(rescued.sum()),added=int(added.sum()),bits=len(truth),
                        reference_errors=int(baseline_error.sum()),errors=int(error.sum()),
                        coverage_fraction=coverage['coverage_fraction'],certified_fraction=certificate['certified_fraction'],
                        winner_changed_fraction=certificate['changed_fraction'],ties=candidate['tie_count'],
                        record_sha256=entry['sha256'],reference_sha256=re['sha256'],parent_sha256=parent['sha256']))
        return dict(domain=domain,block=block,rows=rows,arrays=arrays,input_records=bindings,
            new_receiver_calls=0,new_decoder_calls=0,truth_access='external metric/coverage/labels only')

    output=root/'runs/b02-v1'
    summary_path=output/'analysis/summary.json'
    if args.mode=='audit':
        end=json.loads((root/'evidence/b02-v1-exit.json').read_text());assert end['exit_code']==0 and not end['timed_out']
        s=json.loads(summary_path.read_text());assert s['status']=='COMPLETE' and s['calls']=={'A':48}
        rows=[]
        for entry in s['records']:
            _,value=verified_record(entry,output)
            again=calculate(value['domain'],value['block'])
            check_equal(value,again)
            rows+=value['rows']
        assert rows==s['rows'];guard.verify()
        report=dict(status='PASS',records=48,rows=len(rows),summary_sha256=sha(summary_path),
            source_sha256=sha(manifest),contract_sha256=sha(cpath),new_receiver_calls=0,new_decoder_calls=0,
            scope='historical candidate diagnostic replay, not causal or fresh confirmation')
        with (root/'evidence/b02-v1-audit.json').open('x') as f:json.dump(report,f,indent=2)
        print(json.dumps(report),flush=True);return
    run=LightRun(output,'analysis',dict(A=48,seconds=3600),2*1024**3,guard)
    try:
        rows=[]
        for domain,number,offset in [('uncoded256',16,0),('coded1024',32,1000)]:
            for block in range(number):
                value,_=run.call('A',dict(block=offset+block,snr=0,arm=domain,split=int(block%2)),
                    lambda:calculate(domain,block),lambda v:dict(rows=len(v['rows'])),dict(scope='historical diagnosis'))
                rows+=value['rows']
                print(json.dumps(dict(domain=domain,block=block,calls=run.counts)),flush=True)
        guard.verify()
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,records=run.records,rows=rows,
            contract_sha256=sha(cpath),source_sha256=sha(manifest),wall_seconds=time.time()-run.started,
            new_receiver_calls=0,new_decoder_calls=0))
    except BaseException as exc:run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--mode',choices=('run','audit'),default='run');main(p.parse_args())
