"""Independent cavity sums, finite probabilities, demapping and bit decisions."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from scipy.special import logsumexp
from .bottleneck_pilot import sha,load_state,hashes,observed_at_snr
from .light_gap_replay import verified_record,decoder_scores


def check_cavity(value,observed,H,sigma,temperature,method):
    event=value['cavity_final'];r,c=event['row'],event['col'];h=event['h'];n=len(H)
    expected_r,expected_c=np.nonzero(abs(H)>=1e-4)
    np.testing.assert_array_equal(r,expected_r);np.testing.assert_array_equal(c,expected_c)
    np.testing.assert_array_equal(h,H[r,c])
    v=event['incoming_variance'];pseudo=event['incoming_pseudovariance'];mu=event['incoming_mean']
    V=np.full(n,sigma);C=np.zeros(n,dtype=complex);Z=observed['y']-H@observed['pilot']
    np.add.at(V,r,abs(h)**2*v);np.add.at(C,r,h**2*pseudo);np.add.at(Z,r,-h*mu)
    vext=V[r]-abs(h)**2*v;cext=C[r]-h**2*pseudo;zext=Z[r]+h*mu
    for actual,expected in [(event['cavity_variance'],vext),(event['cavity_pseudovariance'],cext),(event['cavity_mean'],zext)]:
        np.testing.assert_allclose(actual,expected,atol=1e-11,rtol=1e-11)
    if np.any(abs(cext)>=vext):raise ValueError('singular noncircular cavity')
    variance=vext/abs(h)**2;p=cext/h**2 if method=='NONCIRC' else np.zeros_like(cext);mean=zext/h
    determinant=variance**2-abs(p)**2;a=variance/determinant;b=p/determinant;t=a*mean-b*mean.conj()
    A=np.zeros(n);B=np.zeros(n,dtype=complex);T=np.zeros(n,dtype=complex)
    np.add.at(A,c,a);np.add.at(B,c,b);np.add.at(T,c,t)
    symbols=observed['constellation']
    def weights(a,b,t):return -a[:,None]*abs(symbols)[None,:]**2+(b.conj()[:,None]*symbols[None,:]**2).real+2*(t.conj()[:,None]*symbols[None,:]).real
    log=weights(A[c]-a,B[c]-b,T[c]-t)/temperature
    probability=np.exp(log-logsumexp(log,axis=1)[:,None])
    np.testing.assert_allclose(event['projection_probabilities'],probability,rtol=1e-9,atol=1e-10)
    projected=probability@symbols;projected_c=probability@(symbols**2)-projected**2
    np.testing.assert_allclose(event['projection_pseudovariance'],projected_c,atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(event['delivered_mean'],.5*mu+.5*projected,atol=1e-10,rtol=1e-9)
    logfinal=weights(A,B,T);posterior=np.exp(logfinal-logsumexp(logfinal,axis=1)[:,None])
    np.testing.assert_allclose(value['finite_message']['probabilities'],posterior,atol=1e-10,rtol=1e-9)
    llr=np.concatenate([logsumexp(logfinal[:,symbols.real>=0],axis=1)-logsumexp(logfinal[:,symbols.real<0],axis=1),
                        logsumexp(logfinal[:,symbols.imag>=0],axis=1)-logsumexp(logfinal[:,symbols.imag<0],axis=1)])
    np.testing.assert_allclose(value['raw_llr'],llr,rtol=1e-9,atol=1e-9)
    np.testing.assert_array_equal(value['llr'],np.clip(value['raw_llr'],-20.,20.))
    zeta=abs(cext)/vext;kl=-.5*np.log1p(-zeta**2);last=value['cavity_trace'][-1]
    np.testing.assert_allclose([last['zeta_mean'],last['zeta_gt01'],last['zeta_gt02'],last['KL_mean']],
        [zeta.mean(),(zeta>.1).mean(),(zeta>.2).mean(),kl.mean()],atol=1e-11,rtol=1e-11)
    return last


def execute(args):
    started=time.time();root=args.root;c=json.loads(args.contract.read_text());tag=c['tag']
    sp=root/'runs'/tag/args.stage/'summary.json';s=json.loads(sp.read_text())
    ep=root/'evidence'/f'{tag}-{args.stage}-exit.json';e=json.loads(ep.read_text())
    if (s['status']!='COMPLETE' or e['exit_code']!=0 or e['timed_out']
            or s['contract_sha256']!=sha(args.contract)
            or s['source_manifest_sha256']!=sha(root/('source-'+tag)/'source-manifest.json')):
        raise ValueError('noncircular source/exit/audit binding differs')
    n=s['blocks'];methods=['CIRC','NONCIRC','C_ZERO'] if args.stage=='engineering' else ['CIRC','NONCIRC']
    expected={(b,snr,case+'_'+method) for b in range(n) for snr in [7,8] for case in c['cases'] for method in methods}
    if s['calls']!={'T':len(expected),'F':0,'D':0}:raise ValueError('noncircular call count differs')
    exo={r['block']:r for r in s['exogenous']};seen=set();rows=[];arrays=0;max_bytes=0
    cache=next((sp.parent/'code-cache').glob('e1_ldpc_code_*.npz'))
    with np.load(cache,allow_pickle=False) as z:parity=z['H'];free=z['free_cols']
    ci,bi=np.nonzero(parity);current=None
    for item in s['records']:
        key=tuple(item[k] for k in ('block','snr','arm'))
        if key not in expected or key in seen:raise ValueError('duplicate/unexpected noncircular record')
        seen.add(key);record,value=verified_record(item,root);arrays+=len(record['state']['file']['fields'])
        rp=Path(item['record']).parent/(record['token']+'-reserve.json');reserve=json.loads(rp.read_text())
        if any(reserve[k]!=record[k] for k in ('block','snr','arm','split','kind','token')):raise ValueError('noncircular reservation differs')
        if current!=key[:2]:
            current=key[:2];truth=load_state(exo[key[0]]['state']);observed=observed_at_snr(truth,key[1])
            _,base=verified_record(record['source_record'],Path(c['old_root']))
        score=decoder_scores(value,truth)
        if score!=record['scores'] or score!=item['scores'] or hashes(observed)!=record['observed_hashes']:
            raise ValueError('noncircular score/input differs')
        if (bool(value['decode_ok'])!=bool(not (np.bincount(ci,weights=value['decoded'][bi],minlength=len(parity))%2).any())
                or not np.array_equal(value['info_hat'],value['decoded'][free])):raise ValueError('decoder extraction differs')
        last=check_cavity(value,observed,base['H'],record['sigma_used'],record['message_temperature'],record['method'])
        rows.append(dict(block=key[0],snr=key[1],arm=key[2],scores=score,cavity=last,trace=value['cavity_trace']))
        max_bytes=max(max_bytes,Path(record['state']['file']['path']).stat().st_size+Path(item['record']).stat().st_size+rp.stat().st_size)
    if seen!=expected:raise ValueError('missing noncircular records')
    for suffix in ('reserve','result'):
        if len(list(sp.parent.glob('T-*-'+suffix+'.json')))!=len(expected):raise ValueError('unmatched terminal call')
    ap=root/'evidence'/f'{tag}-{args.stage}-audit.json'
    result=dict(status='PASS',stage=args.stage,records=len(rows),arrays_audited=arrays,rows=rows,
        summary_sha256=sha(sp),exit_sha256=sha(ep),contract_sha256=sha(args.contract),auditor_sha256=sha(__file__),
        wall_seconds=time.time()-started,new_calls=dict(F=0,T=0,D=0))
    with ap.open('x') as f:json.dump(result,f,indent=2)
    if args.admit:
        if args.stage!='engineering':raise ValueError('only engineering admits')
        overhead=max(0,s['wall_seconds']-sum(r['seconds'] for r in s['records']))/len(rows)
        max_call=max(r['seconds'] for r in s['records']);engbytes=sum(p.stat().st_size for p in sp.parent.rglob('*') if p.is_file())
        choices=[]
        for blocks in c['development_block_options']:
            calls=blocks*8;seconds=2*calls*(max_call+overhead)+30;storage=1.25*(engbytes+calls*max_bytes+10*1024**2)
            choices.append(dict(blocks=blocks,T=calls,conservative_seconds=seconds,conservative_bytes=storage,
                                admitted=seconds<=c['development_seconds'] and storage<=c['output_bytes']))
        allowed=[r for r in choices if r['admitted']]
        if not allowed:raise RuntimeError('noncircular development exceeds light budget')
        chosen=max(allowed,key=lambda r:r['blocks'])
        admission=dict(status='PASS',**chosen,choices=choices,contract_sha256=sha(args.contract),source_sha256=s['source_manifest_sha256'],
            engineering_summary_sha256=sha(sp),engineering_audit_sha256=sha(ap))
        with (root/'evidence'/f'{tag}-admission.json').open('x') as f:json.dump(admission,f,indent=2)
    print(json.dumps({k:result[k] for k in ['status','records','arrays_audited','wall_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--stage',choices=('engineering','development'),required=True);p.add_argument('--admit',action='store_true');execute(p.parse_args())
