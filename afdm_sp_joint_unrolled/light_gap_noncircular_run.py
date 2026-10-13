"""Actual BP cavity diagnostics and paired finite-constellation noncircular BP."""
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes,load_state,observed_at_snr,sha
from .direction_receiver import terminal_decode,_copy_state
from .e1_ldpc import build_code
from .light_gap_replay import CODE_KEYS,LightRun,setup_guard,verified_record,decoder_scores
from .light_gap_receiver_run import parser


def terminal_probe(observed,H,sigma,code,temperature,arm):
    trace=[];last=[]
    def observer(event):
        zeta=event['cavity_pseudovariance'].abs()/event['cavity_variance']
        kl=-.5*torch.log1p(-zeta.square())
        trace.append(dict(iteration=event['iteration'],edges=len(zeta),zeta_mean=float(zeta.mean()),
            zeta_max=float(zeta.max()),zeta_gt01=float((zeta>.1).double().mean()),
            zeta_gt02=float((zeta>.2).double().mean()),KL_mean=float(kl.mean()),
            zeta_quantiles=torch.quantile(zeta,torch.tensor([.5,.9,.99],dtype=zeta.dtype)).tolist()))
        if event['iteration']==20:last.append(_copy_state(event))
    result=terminal_decode(observed['y']-H@observed['pilot'],H,sigma,observed['constellation'],code,
        device='cpu',audit=True,bp_temperature=temperature,bp_noncircular=arm!='CIRC',
        bp_pseudovariance_scale=0. if arm=='C_ZERO' else 1.,cavity_observer=observer)
    if len(trace)!=20 or len(last)!=1:raise ValueError('missing actual edge cavity trajectory')
    result.update(cavity_trace=trace,cavity_final=last[0])
    return result


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('noncircular source/contract differs')
    c=json.loads(args.contract.read_text())
    if (c['schema']!='i1-light-noncircular-v1' or c['device']!='cpu' or c['snrs']!=[7,8]
            or c['engineering_blocks']!=2 or c['cases']!=['BASE_T2','NOISE_T1']):
        raise ValueError('noncircular contract differs')
    guard=setup_guard(args,c)
    arms=['CIRC','NONCIRC','C_ZERO'] if args.stage=='engineering' else ['CIRC','NONCIRC']
    blocks=2;seconds=c['engineering_seconds']
    if args.stage=='development':
        if args.admission is None or sha(args.admission)!=args.admission_sha256:raise ValueError('hashed admission required')
        a=json.loads(args.admission.read_text());blocks=a['blocks'];seconds=c['development_seconds']
        if (a['status']!='PASS' or a['contract_sha256']!=args.contract_sha256 or a['source_sha256']!=args.source_sha256
                or blocks not in c['development_block_options']
                or a['engineering_summary_sha256']!=sha(args.root/'engineering/summary.json')):
            raise ValueError('noncircular admission differs')
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(args.root,args.stage,dict(T=blocks*2*2*len(arms),seconds=seconds),c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        old=Path(c['old_root']);s=json.loads((old/'runs'/args.stage/'summary.json').read_text())
        env=json.loads((old/'runs'/args.stage/'environment.json').read_text())
        if hashes({k:code[k] for k in CODE_KEYS})!=env['code_identity']:raise ValueError('LDPC identity changed')
        index={(r['block'],r['snr'],r['arm']):r for r in s['records']}
        exo={r['block']:r for r in s['exogenous'] if r['block']<blocks}
        run.write('environment.json',dict(device='cpu',threads=1,numpy=np.__version__,torch=torch.__version__,
            code_identity=env['code_identity'],contract_sha256=args.contract_sha256,source_manifest_sha256=args.source_sha256))
        comparisons=[]
        for b in range(blocks):
            raw=load_state(exo[b]['state'])
            for snr in [7,8]:
                obs=observed_at_snr(raw,snr);base_record,base=verified_record(index[b,snr,'I1'],old)
                for case in c['cases']:
                    sigma=base['sigma2_terminal'] if case=='BASE_T2' else float(obs['sigma2'])
                    temperature=2. if case=='BASE_T2' else 1.;result={}
                    for arm in arms:
                        value,_=run.call('T',dict(block=b,snr=snr,split=exo[b]['split'],arm=case+'_'+arm),
                            lambda:terminal_probe(obs,base['H'],sigma,code,temperature,arm),
                            lambda v:decoder_scores(v,raw),dict(case=case,method=arm,sigma_used=sigma,
                                message_temperature=temperature,source_record=index[b,snr,'I1'],
                                observed_hashes=hashes(obs),exogenous_hashes=exo[b]['hashes'],
                                nested_LDPC=1,truth_access='offline scoring only'))
                        result[arm]=value
                    if args.stage=='engineering':
                        for field in ('mu','var','llr','decoded','info_hat','x_hard'):
                            np.testing.assert_array_equal(result['CIRC'][field],result['C_ZERO'][field])
                        row=dict(block=b,snr=snr,case=case,c_zero_exact=True)
                        if case=='BASE_T2':
                            error=float(np.linalg.norm(result['CIRC']['llr']-base['llr'])/max(1.,np.linalg.norm(base['llr'])))
                            if error>1e-6:raise ValueError('finite circular terminal changed old T2 LLR')
                            for field in ('decoded','info_hat','x_hard'):np.testing.assert_array_equal(result['CIRC'][field],base[field])
                            row['old_T2_LLR_relative_error']=error
                        comparisons.append(row)
            print(json.dumps(dict(block=b,calls=run.counts)),flush=True)
        guard.verify();run.meter.verify()
        report=dict(status='COMPLETE',tag=c['tag'],stage=args.stage,blocks=blocks,calls=dict(run.counts,F=0,D=0),
            nested_LDPC=run.counts['T'],records=run.records,exogenous=list(exo.values()),comparisons=comparisons,
            contract_sha256=args.contract_sha256,source_manifest_sha256=args.source_sha256,wall_seconds=time.time()-run.started,
            scope='fixed estimated H; actual finite edge cavity moments; prior-free terminal comparison; legacy mean-only damping retained')
        run.write('summary.json',report);run.meter.verify()
        print(json.dumps(dict(status='COMPLETE',calls=report['calls'],wall_seconds=report['wall_seconds'])),flush=True)
    except BaseException as exc:
        run.fail(exc);raise


if __name__=='__main__':execute(parser().parse_args())
