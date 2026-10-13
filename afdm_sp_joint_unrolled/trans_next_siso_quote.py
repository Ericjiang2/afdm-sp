"""Eight cached-terminal SISO reference quotes, not full receiver comparisons."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import torch
from .bottleneck_pilot import hashes, load_state, observed_at_snr, sha, offline_scores
from .e1_ldpc import build_code, decode_llr, extract_info
from .light_gap_replay import CODE_KEYS, LightRun, setup_guard, verified_record
from .supplement_siso_mmse import siso_mmse


def execute(args):
    if sha(args.contract)!=args.contract_sha256 or sha(args.source_manifest)!=args.source_sha256:
        raise ValueError('SISO quote identity changed')
    c=json.loads(args.contract.read_text())
    if (c['schema']!='trans-siso-terminal-quote-v1' or c['device']!='cpu' or c['threads']!=1
            or c['blocks']!=[0,1] or c['snrs']!=[7,8] or c['T_limit']!=8
            or c['reference_arms']!=['MEAN','REFRESH47'] or args.root.name!=c['tag']
            or sha(c['input_summary'])!=c['input_summary_sha256']):
        raise ValueError('unregistered SISO terminal quote')
    guard=setup_guard(args,c)
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    run=LightRun(args.root,'engineering',dict(T=8,seconds=c['seconds']),c['output_bytes'],guard)
    try:
        cache=run.out/'code-cache';cache.mkdir();code=build_code(cache_dir=cache);run.meter.adopt_tree(cache)
        source=json.loads(Path(c['input_summary']).read_text())
        env=json.loads(Path(c['input_summary']).with_name('environment.json').read_text())
        if source['status']!='COMPLETE' or hashes({k:code[k] for k in CODE_KEYS})!=env['code_identity']:
            raise ValueError('SISO quote source/code differs')
        exo={e['block']:e for e in source['exogenous']}
        refs={(r['block'],r['snr'],r['arm']):r for r in source['records']}
        comparisons=[]
        for b in c['blocks']:
            raw=load_state(exo[b]['state'])
            if hashes({k:raw[k] for k in exo[b]['hashes']})!=exo[b]['hashes']:
                raise ValueError('SISO quote exogenous hash changed')
            for snr in c['snrs']:
                observed=observed_at_snr(raw,snr)
                for arm in c['reference_arms']:
                    rr,state=verified_record(refs[b,snr,arm],Path(c['reference_root']))
                    H=state['H'];z=observed['y']-H@observed['pilot'];sigma=state['sigma2_terminal']
                    prior=np.zeros(2*len(z));before=hashes(dict(z=z,H=H,prior=prior))
                    def terminal():
                        details=siso_mmse(z,H,sigma,prior)
                        llr=np.clip(details['channel_llr'],-20.,20.)
                        decoded,ok=decode_llr(code,llr,maxiter=50)
                        return dict(H=H.copy(),z=z.copy(),sigma2_terminal=sigma,code_prior=prior.copy(),
                            mu=details['posterior_mean'],var=details['posterior_variance'],
                            llr=llr,decoded=decoded,info_hat=extract_info(code,decoded),decode_ok=bool(ok),
                            x_hard=details['hard'],siso=details,resource_counts=dict(T=1,LDPC=1,
                                factorizations=1,linear_rhs=len(z)+1),baseline_eligible=False,
                            scope='cached terminal detector counterfactual; no joint CE update')
                    value,record=run.call('T',dict(block=b,snr=snr,split=exo[b]['split'],arm=arm+'-SISO0'),
                        terminal,lambda v:offline_scores(v,raw,H),dict(reference_record_sha256=refs[b,snr,arm]['sha256'],
                            input_summary_sha256=c['input_summary_sha256'],terminal_input_hashes=before,
                            truth_access='offline error scoring only'))
                    if hashes(dict(z=z,H=H,prior=prior))!=before:raise ValueError('SISO changed terminal input')
                    _,saved=verified_record(run.records[-1],args.root)
                    if offline_scores(saved,raw,saved['H'])!=record['scores']:
                        raise ValueError('SISO raw score does not match')
                    np.testing.assert_array_equal(saved['H'],state['H'])
                    np.testing.assert_array_equal(saved['z'],observed['y']-state['H']@observed['pilot'])
                    comparisons.append(dict(block=b,snr=snr,reference_arm=arm,reference_scores=rr['scores'],
                        siso_scores=record['scores'],seconds=record['seconds'],
                        min_extrinsic_denominator=float(np.min(value['siso']['extrinsic_denominator'])),
                        linear_relative_residual=value['siso']['linear_relative_residual']))
                    print(json.dumps(dict(block=b,snr=snr,arm=arm,calls=run.counts)),flush=True)
        guard.verify()
        if sha(c['input_summary'])!=c['input_summary_sha256']:raise ValueError('input summary changed')
        run.write('summary.json',dict(status='COMPLETE',calls=run.counts,records=run.records,comparisons=comparisons,
            source_sha256=args.source_sha256,contract_sha256=args.contract_sha256,
            input_summary_sha256=c['input_summary_sha256'],wall_seconds=time.time()-run.started,
            scope='8 cached-terminal engineering quotes; not independent FER or full COST'))
        run.meter.verify()
    except BaseException as exc:
        run.fail(exc);raise


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('root','contract','source-manifest'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('contract-sha256','source-sha256'):p.add_argument('--'+name,required=True)
    execute(p.parse_args())
