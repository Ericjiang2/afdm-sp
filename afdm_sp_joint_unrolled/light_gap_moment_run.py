"""CPU-only moment diagnostics on immutable engineering/development states."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes,load_state,observed_at_snr,sha
from .classical_joint_unrolled import data_uncertainty_gram,build_A_for_DALS_torch
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS,LightRun,setup_guard,verified_record
from .light_gap_moments import (qpsk_moments,atom_layout,compressed_gram,
    weighted_sample_lags,code_subspace_posterior,residual_decomposition,
    graph_pseudovariance,required_lags)


def diagnose(raw,state,observed,code,correlations):
    n = len(raw['H']);ids=np.asarray(state['support'],dtype=int)
    dl,dk=ids//5,ids%5-2
    offsets,phases=atom_layout(n,dl,dk,float(raw['params']['c1']),float(raw['params']['c2']))
    moments=qpsk_moments(state['llr'])
    v=moments['variance'];c=moments['pseudovariance'];mu=moments['mean']
    existing=data_uncertainty_gram(n,torch.tensor(dl),torch.tensor(dk),torch.tensor(v),
        float(raw['params']['c1']),float(raw['params']['c2']),2).numpy()
    diagonal=v.sum()*np.eye(len(ids))
    error=float(np.linalg.norm(existing-diagonal)/max(1.,np.linalg.norm(existing)))
    if len(np.unique(offsets))!=len(ids) or error>1e-12:
        raise ValueError('N1024/515-domain diagonal Gram invariant failed')
    scaled=np.asarray(state['x_soft'],dtype=np.complex128)
    if np.any(np.abs(scaled.real)>.5+1e-6) or np.any(np.abs(scaled.imag)>.5+1e-6):
        raise ValueError('cached I1 damped symbols outside convex QPSK range')
    proxy_variance=np.maximum(0.,.5-np.abs(scaled)**2)
    residuals={
        'cached_outer_mean':residual_decomposition(observed,raw['H'],raw['data'],state['H'],scaled,proxy_variance),
        'terminal_llr_factorized_mean':residual_decomposition(observed,raw['H'],raw['data'],state['H'],mu,v)}
    graphs={}
    for name,sigma in [('BASE',float(state['sigma2_terminal'])),('THERMAL',float(observed['sigma2']))]:
        graphs[name]=graph_pseudovariance(state['H'],v,c,sigma)
    variance_ratio=float(state['sigma2_terminal']/state['sigma2'])
    if variance_ratio != .5:
        raise ValueError('frozen BASE 0.5 scale not reproduced')
    safe=np.divide(np.abs(c),v,out=np.zeros_like(v),where=v>0)
    metrics=dict(N=n,support_size=len(ids),distinct_offsets=len(np.unique(offsets)),
        lag_count=len(required_lags(offsets,n)),full_covariance_entries=n*n,
        compressed_lag_entries=n*len(required_lags(offsets,n)),gamma_entries=len(ids)**2,
        gamma_diagonal_relative_error=error,gamma_diagonal_value=float(v.sum()),
        symbol_variance_mean=float(v.mean()),node_pseudovariance_ratio_quantiles=np.quantile(safe,[0,.5,.9,.99,1]).tolist(),
        thermal_variance=float(observed['sigma2']),raw_adaptive_variance=float(state['sigma2']),
        terminal_variance=float(state['sigma2_terminal']),fixed_terminal_scale=variance_ratio,
        raw_adaptive_to_thermal=float(state['sigma2']/observed['sigma2']),
        terminal_to_thermal=float(state['sigma2_terminal']/observed['sigma2']),
        residuals=residuals,graphs={k:x['summary'] for k,x in graphs.items()},
        moment_source='factorized QPSK from cached clipped terminal Gaussian LLR; not historical CE input',
        cached_mean_source='damped final outer x_soft; actual noise/CE feedback arrays were not saved')
    result=dict(metrics=metrics,moments=moments,gamma_diagonal=existing,
        support=ids,graphs=graphs,correlation=None)
    if correlations:
        sample=code_subspace_posterior(code,state['decoded'],state['llr'],free_bits=5)
        mean,lags=weighted_sample_lags(sample['samples'],sample['weights'],offsets)
        gamma=compressed_gram(offsets,phases,lags)
        direct=np.zeros_like(gamma)
        for x,w in zip(sample['samples'],sample['weights']):
            A=build_A_for_DALS_torch(n,torch.tensor(dl),torch.tensor(dk),torch.tensor(x-mean),
                float(raw['params']['c1']),float(raw['params']['c2']),2).numpy()
            direct+=w*(A.conj().T@A)
        relative=float(np.linalg.norm(gamma-direct)/max(1.,np.linalg.norm(direct)))
        if relative>1e-9 or np.linalg.eigvalsh(gamma).min() < -1e-8:
            raise ValueError('sample covariance compression or PSD identity failed')
        approximation=np.trace(gamma).real/len(ids)*np.eye(len(ids))
        metrics['correlation']=dict(effective_sample_size=sample['effective_sample_size'],
            largest_weight=sample['largest_weight'],restricted_words=len(sample['weights']),
            gamma_norm=float(np.linalg.norm(gamma)),compressed_vs_direct_relative_error=relative,
            diagonal_approximation_relative_error=float(np.linalg.norm(gamma-approximation)/max(1e-15,np.linalg.norm(gamma))),
            scope=sample['scope'],input_likelihood='saved terminal Gaussian clipped LLR; approximate decoder channel')
        result['correlation']=dict(sample=sample,mean=mean,lags={str(k):v for k,v in lags.items()},gamma=gamma,direct_gamma=direct)
    return result


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('frozen moment source or contract changed')
    contract=json.loads(args.contract.read_text())
    if (contract['schema']!='i1-light-moments-v1' or contract['device']!='cpu'
            or contract['snrs']!=[7,8] or contract['engineering_blocks']!=2
            or contract['development_blocks']!=64 or contract['correlation_blocks']!=2
            or contract['bounds']!={'engineering':{'A':4,'seconds':180},'development':{'A':128,'seconds':1800}}):
        raise ValueError('moment run differs from frozen contract')
    root=args.root.resolve()
    if not root.is_relative_to(Path('/data/guoyikun/')):
        raise ValueError('outputs must remain under authorized data root')
    if args.stage=='development':
        if args.admission is None or sha(args.admission)!=args.admission_sha256:
            raise ValueError('hashed engineering admission required')
        a=json.loads(args.admission.read_text())
        if (a['status']!='PASS' or a['contract_sha256']!=args.contract_sha256
                or a['source_sha256']!=args.source_sha256
                or a['engineering_summary_sha256']!=sha(root/'engineering/summary.json')):
            raise ValueError('moment admission does not bind this stage')
    guard=setup_guard(args,contract)
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(root,args.stage,contract['bounds'][args.stage],contract['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir()
        code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        old=Path(contract['old_root']);old_summary=json.loads((old/'runs'/args.stage/'summary.json').read_text())
        env=json.loads((old/'runs'/args.stage/'environment.json').read_text())
        if hashes({k:code[k] for k in CODE_KEYS})!=env['code_identity']:
            raise ValueError('LDPC code identity changed')
        index={(r['block'],r['snr'],r['arm']):r for r in old_summary['records']}
        exo={r['block']:r for r in old_summary['exogenous']}
        blocks=contract[args.stage+'_blocks']
        if len(index)!=len(old_summary['records']) or set(exo)!=set(range(blocks)):
            raise ValueError('old input inventory differs')
        run.write('environment.json',dict(device='cpu',threads=1,numpy=np.__version__,torch=torch.__version__,
            code_identity=env['code_identity'],contract_sha256=args.contract_sha256,source_sha256=args.source_sha256))
        inputs=[]
        for b in range(blocks):
            raw=load_state(exo[b]['state'])
            if hashes({k:raw[k] for k in exo[b]['hashes']})!=exo[b]['hashes']:
                raise ValueError('old exogenous arrays changed')
            for snr in contract['snrs']:
                item=index[b,snr,'I1'];record,state=verified_record(item,old)
                observed=observed_at_snr(raw,snr)
                identity=dict(block=b,snr=snr,arm='I1_MOMENTS',split=exo[b]['split'])
                run.call('A',identity,lambda:diagnose(raw,state,observed,code,b<contract['correlation_blocks']),
                    lambda result:result['metrics'],dict(source_record=item,exogenous_hashes=exo[b]['hashes'],
                        observed_hashes=hashes(observed),truth_access='residual scoring only; legal posterior candidates do not read truth'))
                inputs.append(dict(record=item['record'],sha256=item['sha256'],state=record['state']['file']))
            print(json.dumps(dict(stage=args.stage,block=b,calls=run.counts)),flush=True)
        if run.counts!={'A':blocks*2}:
            raise ValueError('moment observation inventory incomplete')
        for item in inputs:
            if sha(item['record'])!=item['sha256'] or sha(item['state']['path'])!=item['state']['sha256']:
                raise ValueError('old states changed during moment analysis')
        guard.verify();run.meter.verify()
        report=dict(status='COMPLETE',stage=args.stage,calls=dict(run.counts,F=0,T=0,D=0),records=run.records,
            independent_blocks=blocks,exogenous=list(exo.values()),input_inventory=inputs,
            contract_sha256=args.contract_sha256,source_manifest_sha256=args.source_sha256,
            wall_seconds=time.time()-run.started,scope='offline moments; terminal proxies are not historical CE or exact code posterior')
        run.write('summary.json',report);run.meter.verify()
        print(json.dumps({k:report[k] for k in ('status','calls','wall_seconds')}),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=('engineering','development'),required=True)
    for name in ('root','contract','source-manifest'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('contract-sha256','source-sha256'):p.add_argument('--'+name,required=True)
    p.add_argument('--admission',type=Path);p.add_argument('--admission-sha256')
    execute(p.parse_args())


if __name__=='__main__':main()
