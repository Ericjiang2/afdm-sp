"""Separate BP edge-projection temperature, noise input and decoder scaling.

The completed legacy-temperature grid is reused. New numerical calls are
explicitly reserved; EP failure traces are inspected without rerunning EP.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes,load_state,observed_at_snr,sha
from .direction_receiver import terminal_decode
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS,LightRun,setup_guard,verified_record,decoder_scores,replay_decode
from .light_gap_support import terminal_equivalence

CASES=('EST_BASE','EST_NOISE','TRUE_BASE','TRUE_NOISE')
OTHER_BETAS=(.5,.75,1.5,2.)
OLD_ARMS=dict(EST_BASE='I1',EST_NOISE='BP_EST_NOISE',TRUE_BASE='BP_TRUE_BASE',TRUE_NOISE='BP_TRUE_NOISE')


def terminal_with_trace(observed,H,sigma,code,temperature,iterations):
    trace=[]
    value=terminal_decode(observed['y']-H@observed['pilot'],H,sigma,observed['constellation'],code,
        device='cpu',audit=True,bp_temperature=temperature,bp_iterations=iterations,
        convergence_observer=trace.append)
    if len(trace)!=1:raise ValueError('BP did not emit one final convergence state')
    state={k:v.detach().cpu().numpy() if torch.is_tensor(v) else v for k,v in trace[0].items()}
    def relative(k):
        a,b=state[k+'_current'],state[k+'_previous']
        return float(np.linalg.norm(a-b)/max(1.,np.linalg.norm(b)))
    value.update(bp_messages=state,bp_diagnostics=dict(message_temperature=temperature,iterations=iterations,
        mean_message_residual=relative('mu'),variance_message_residual=relative('var'),
        scope='last finite-budget edge update; not a posterior-optimality certificate'))
    return value


def summarize_ep(item,old_root):
    record,value=verified_record(item,old_root)
    d=value['diagnostics'];trace=d['trace']
    if len(trace)!=d['iterations'] or any(t['iteration']!=i+1 for i,t in enumerate(trace)):
        raise ValueError('old EP trace inventory differs')
    return dict(block=item['block'],snr=item['snr'],arm=item['arm'],source_record=item,
        source_state=record['state']['file'],reported_converged=d['converged'],
        fixed_point_residual=d['fixed_point_residual'],final_rejected=trace[-1]['rejected_sites'],
        minimum_rejected=min(t['rejected_sites'] for t in trace),
        maximum_rejected=max(t['rejected_sites'] for t in trace),
        final_floor_sites=trace[-1]['variance_floor_sites'],
        max_linear_relative_residual=max(t['linear_relative_residual'] for t in trace),
        trace=trace,interpretation='retained rejected sites can yield a small update without satisfying unprojected EP equations')


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('variance source or contract changed')
    c=json.loads(args.contract.read_text())
    if (c['schema']!='i1-light-variance-v1' or c['device']!='cpu'
            or c['engineering_blocks']!=2 or c['development_blocks']!=64 or c['snrs']!=[7,8]
            or tuple(c['cases'])!=CASES or c['betas']!=[.5,.75,1.,1.5,2.]
            or c['bounds']!={'engineering':{'T':52,'D':64,'seconds':180},
                             'development':{'T':528,'D':2048,'seconds':1800}}):
        raise ValueError('variance contract differs')
    root=args.root.resolve()
    if not root.is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('outputs outside data root')
    if args.stage=='development':
        if args.admission is None or sha(args.admission)!=args.admission_sha256:
            raise ValueError('hashed variance admission required')
        a=json.loads(args.admission.read_text())
        if (a['status']!='PASS' or a['contract_sha256']!=args.contract_sha256 or a['source_sha256']!=args.source_sha256
                or a['engineering_summary_sha256']!=sha(root/'engineering/summary.json')):
            raise ValueError('admission does not bind variance source')
    guard=setup_guard(args,c);torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root,args.stage,c['bounds'][args.stage],c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        old=Path(c['old_root']);s=json.loads((old/'runs'/args.stage/'summary.json').read_text())
        env=json.loads((old/'runs'/args.stage/'environment.json').read_text())
        identity=hashes({k:code[k] for k in CODE_KEYS})
        if identity!=env['code_identity']:raise ValueError('code identity changed')
        index={(r['block'],r['snr'],r['arm']):r for r in s['records']}
        exo={r['block']:r for r in s['exogenous']};blocks=c[args.stage+'_blocks']
        if len(index)!=len(s['records']) or set(exo)!=set(range(blocks)):
            raise ValueError('old inventory differs')
        run.write('environment.json',dict(device='cpu',threads=1,numpy=np.__version__,torch=torch.__version__,
            code_identity=identity,source_manifest_sha256=args.source_sha256,contract_sha256=args.contract_sha256))
        comparisons=[];doubling=[];ep=[];inputs=[]
        for b in range(blocks):
            raw=load_state(exo[b]['state'])
            if hashes({k:raw[k] for k in exo[b]['hashes']})!=exo[b]['hashes']:
                raise ValueError('old exogenous hash changed')
            for snr in c['snrs']:
                observed=observed_at_snr(raw,snr)
                old_i1,baseline=verified_record(index[b,snr,'I1'],old)
                inputs.append(dict(record=index[b,snr,'I1']['record'],sha256=index[b,snr,'I1']['sha256'],state=old_i1['state']['file']))
                new={}
                for case in CASES:
                    H=raw['H'] if case.startswith('TRUE') else baseline['H']
                    sigma=float(observed['sigma2'] if case.endswith('NOISE') else baseline['sigma2_terminal'])
                    provenance=dict(case=case,source_record=index[b,snr,OLD_ARMS[case]],
                        exogenous_hashes=exo[b]['hashes'],observed_hashes=hashes(observed),
                        terminal_input_hashes=hashes(dict(y=observed['y']-H@observed['pilot'],H=H,sigma=np.asarray(sigma))),
                        sigma=sigma,truth_access='explicit true-H terminal oracle' if case.startswith('TRUE') else 'scoring only')
                    nmse=float(np.linalg.norm(H-raw['H'])**2/np.linalg.norm(raw['H'])**2)
                    def invoke(temperature,iterations,suffix=''):
                        tag=f'{case}_T{temperature:g}_{iterations}{suffix}'
                        ident=dict(block=b,snr=snr,split=exo[b]['split'],arm=tag,beta=1.)
                        return run.call('T',ident,lambda:terminal_with_trace(observed,H,sigma,code,temperature,iterations),
                            lambda v:dict(decoder_scores(v,raw),channel_NMSE=nmse),
                            dict(provenance,message_temperature=temperature,iterations=iterations))[0]
                    new[case]=invoke(1.,20)
                    for beta in OTHER_BETAS:
                        tag=f'{case}_T1_20'
                        run.call('D',dict(block=b,snr=snr,split=exo[b]['split'],arm=tag,beta=beta),
                            lambda:replay_decode(code,new[case],beta,20.,50),
                            lambda v:dict(decoder_scores(v,raw),channel_NMSE=nmse),
                            dict(provenance,message_temperature=1.,iterations=20,source_llr_hash=hashes(dict(llr=new[case]['llr']))['llr']))
                    if b<2:
                        doubled=invoke(1.,40)
                        doubling.append(dict(block=b,snr=snr,case=case,
                            relative_llr=float(np.linalg.norm(doubled['llr']-new[case]['llr'])/max(1.,np.linalg.norm(new[case]['llr']))),
                            decoded_equal=bool(np.array_equal(doubled['decoded'],new[case]['decoded'])),
                            base_diagnostics=new[case]['bp_diagnostics'],doubled_diagnostics=doubled['bp_diagnostics']))
                    if args.stage=='engineering':
                        legacy=invoke(2.,20);_,original=verified_record(index[b,snr,OLD_ARMS[case]],old)
                        comparisons.append(dict(block=b,snr=snr,case=case,comparison=terminal_equivalence(legacy,original)))
                        if case=='EST_BASE':
                            repeat=invoke(1.,20,'_REPEAT')
                            comparisons.append(dict(block=b,snr=snr,case='T1_REPEAT',comparison=terminal_equivalence(repeat,new[case])))
                for arm in ('EP_EST_NOISE','EP_TRUE_NOISE','EP_EST_NOISE_DOUBLE','EP_TRUE_NOISE_DOUBLE'):
                    if (b,snr,arm) in index:ep.append(summarize_ep(index[b,snr,arm],old))
            print(json.dumps(dict(stage=args.stage,block=b,calls=run.counts)),flush=True)
        if run.counts!={k:v for k,v in run.bounds.items() if k!='seconds'}:
            raise ValueError('variance call inventory incomplete')
        for item in inputs:
            if sha(item['record'])!=item['sha256'] or sha(item['state']['path'])!=item['state']['sha256']:
                raise ValueError('old input changed during variance probe')
        guard.verify();run.meter.verify()
        report=dict(status='COMPLETE',stage=args.stage,calls=dict(run.counts,F=0),records=run.records,
            independent_blocks=blocks,exogenous=list(exo.values()),input_inventory=inputs,engineering_comparisons=comparisons,
            doubling=doubling,old_ep_audits=ep,contract_sha256=args.contract_sha256,source_manifest_sha256=args.source_sha256,
            wall_seconds=time.time()-run.started,scope='new internal edge-projection temperature on old development; terminal truth oracles are not deployable')
        run.write('summary.json',report);run.meter.verify()
        print(json.dumps({k:report[k] for k in ('status','calls','wall_seconds')}),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('engineering','development'),required=True)
    for k in ('root','contract','source-manifest'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('contract-sha256','source-sha256'):p.add_argument('--'+k,required=True)
    p.add_argument('--admission',type=Path);p.add_argument('--admission-sha256');execute(p.parse_args())


if __name__=='__main__':main()
