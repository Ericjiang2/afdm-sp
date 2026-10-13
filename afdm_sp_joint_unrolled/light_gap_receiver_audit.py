"""Recompute full-chain scores and CE normal equations from immutable arrays."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from .bottleneck_pilot import sha,load_state,hashes,observed_at_snr,offline_scores,generate_exogenous
from .light_gap_replay import verified_record
from .budgeted_support_diagnostics import array_hash
from .light_gap_support_exchange_audit import check_exchange
from .light_gap_fresh import (EXOGENOUS_KEYS, fresh_namespace, stage_arms,
                             earlier_exogenous, require_unused_inputs)


def check_fresh_inputs(summary, contract, root, stage, code):
    """Replay the same generator and separately verify random inputs and units."""
    namespace=fresh_namespace(contract)
    if namespace is None:return None
    from .loop9_cache_features import _make_config_a
    system=_make_config_a(1024,2.,8,10.,4.)
    run_root=root/'runs'/contract['tag'];stage_root=run_root/stage
    split=1 if stage=='engineering' else 2
    if (summary.get('fresh_namespace')!=list(namespace)
            or summary.get('generated_exogenous_blocks')!=summary['blocks']
            or [e['block'] for e in summary['exogenous']]!=list(range(summary['blocks']))):
        raise ValueError('fresh input inventory/namespace differs')
    previous=earlier_exogenous(contract,run_root,stage);checked=[];arrays=0;max_bytes=0
    for entry in summary['exogenous']:
        b=entry['block'];identity=dict(block=b,split=split,namespace=list(namespace))
        path=Path(entry['state']['file']['path'])
        if path.resolve()!=stage_root.resolve()/f'exogenous-{b:03d}.npz':
            raise ValueError('fresh raw state lies outside its reserved stage')
        reservation_path=stage_root/f'exogenous-{b:03d}-reserve.json'
        metadata_path=stage_root/f'exogenous-{b:03d}.json'
        reservation=json.loads(reservation_path.read_text())
        if (any(entry[k]!=v or reservation[k]!=v for k,v in identity.items())
                or json.loads(metadata_path.read_text())!=entry):
            raise ValueError('fresh input reservation/metadata differs')
        raw=load_state(entry['state']);identity_hashes=hashes({k:raw[k] for k in EXOGENOUS_KEYS})
        if identity_hashes!=entry['hashes']:raise ValueError('fresh input hashes differ')
        require_unused_inputs(identity_hashes,previous)
        replay=generate_exogenous(system,code,b,split=split,namespace=namespace)
        if hashes({k:replay[k] for k in EXOGENOUS_KEYS})!=identity_hashes:
            raise ValueError('fresh input does not replay from frozen namespace')
        seed=lambda component:np.random.default_rng(np.random.SeedSequence([*namespace,split,b,component]))
        if raw['channel_seed']!=int(seed(1).integers(0,2**31)) or raw['split_id']!=split or raw['uncoded']:
            raise ValueError('fresh physical seed/split differs')
        info=seed(2).integers(0,2,size=code['k']).astype(np.uint8)
        np.testing.assert_array_equal(raw['info'],info)
        coded=((code['G'].astype(np.int32)@info.astype(np.int32))%2).astype(np.uint8)
        np.testing.assert_array_equal(raw['coded'],coded)
        np.testing.assert_array_equal((code['H'].astype(np.int32)@coded.astype(np.int32))%2,0)
        n=len(raw['data']);bits=coded.astype(float)
        expected_data=.5*((1-2*bits[:n])+1j*(1-2*bits[n:]))
        np.testing.assert_allclose(raw['data'],expected_data,rtol=0,atol=1e-15)
        np.testing.assert_allclose(abs(raw['data'])**2,.5,rtol=0,atol=1e-15)
        np.testing.assert_allclose(abs(raw['pilot'])**2,.5,rtol=0,atol=1e-15)
        rng=seed(3);noise=(rng.standard_normal(n)+1j*rng.standard_normal(n))/np.sqrt(2)
        np.testing.assert_array_equal(raw['noise'],noise)
        signal=raw['H']@(raw['pilot']+raw['data'])
        np.testing.assert_allclose(raw['y'],signal+np.sqrt(10.**(-7/10))*noise,rtol=0,atol=1e-12)
        observed7,observed8=observed_at_snr(raw,7),observed_at_snr(raw,8)
        np.testing.assert_allclose(observed7['y']-observed8['y'],
            (np.sqrt(10.**(-7/10))-np.sqrt(10.**(-8/10)))*noise,rtol=0,atol=1e-12)
        checked.append(dict(identity,channel_seed=raw['channel_seed'],hashes=identity_hashes,
            pilot_power=float(np.mean(abs(raw['pilot'])**2)),data_power=float(np.mean(abs(raw['data'])**2)),
            noise_power=float(np.mean(abs(noise)**2))))
        arrays+=len(entry['state']['file']['fields']);previous.append(entry)
        max_bytes=max(max_bytes,path.stat().st_size+reservation_path.stat().st_size+metadata_path.stat().st_size)
    for pattern in ['exogenous-*-reserve.json','exogenous-*.npz']:
        if len(list(stage_root.glob(pattern)))!=summary['blocks']:raise ValueError('unmatched input reservation')
    return dict(status='PASS',blocks=len(checked),arrays_audited=arrays,generator_replays=len(checked),
        max_bytes_per_block=max_bytes,rows=checked,
        scope='same-generator replay plus independent seed/encoding/power/noise and old/new-split disjointness')


def check_feedback(value,arm):
    """Check raw decoder decomposition, replacement, and every prior consumer."""
    if not arm.get('feedback',{}).get('retain_messages',False):return 0
    current=np.zeros(len(value['llr']));count=0
    states={s['outer_iter']:s for s in value['dals']}
    for record in value['code_feedback_records']:
        if record['stage']=='detector_consume':
            if record['prior_sha256']!=array_hash(current):raise ValueError('detector consumed a different prior')
        if record['stage']!='decoder':continue
        count+=1
        np.testing.assert_array_equal(record['prior_before'],current)
        np.testing.assert_array_equal(record['raw_app'],record['decoder_input']+record['raw_check_extrinsic'])
        np.testing.assert_array_equal(record['prior_after'],np.clip(record['raw_check_extrinsic'],-20.,20.))
        np.testing.assert_array_equal(record['prior_after'],record['delivered_prior'])
        if record['delivered_sha256']!=array_hash(record['prior_after']):raise ValueError('delivered code hash differs')
        for key,field in [('incoming_llr','decoder_input'),('raw_app','raw_app'),('raw_check_extrinsic','raw_check_extrinsic')]:
            if record['source']['hashes'][key]!=array_hash(record[field]):raise ValueError('decoder raw message hash differs')
        current=record['prior_after']
        following=record['iteration']+1
        if following in states:
            app=np.clip(record['channel_llr']+current,-20.,20.);n=len(app)//2
            mean=.5*(np.tanh(app[:n]/2)+1j*np.tanh(app[n:]/2))
            np.testing.assert_allclose(states[following]['mu'],mean,rtol=0,atol=9e-8)
            np.testing.assert_allclose(states[following]['finite_variance'],.5-abs(mean)**2,rtol=0,atol=1e-12)
    return count


def check_ce(state, observed, params, consumer, config):
    a=state['A'].astype(complex);y=state['y'];old=state['g_previous'];n,k=a.shape
    mu=state['mu'];v=state['finite_variance'];dl=state['support_delays'];dk=state['support_dopplers']
    if (state['moment_source']!='code_feedback.ce' or state['oracle_mean']
            or array_hash(v)!=consumer['variance_sha256'] or len(set(dl*5+dk))!=k):
        raise ValueError('invalid actual CE moment/source/support')
    np.testing.assert_allclose(v,.5-abs(mu.astype(complex))**2,atol=9e-8,rtol=0)
    x=np.arange(n)[:,None];out=(x+(5*dl+dk)[None,:])%n
    phase=np.exp(2j*np.pi*(-params['c1']*dl[None,:]**2+params['c2']*(out**2-x**2)-x*dl[None,:]/n))
    expected=np.empty_like(a)
    expected[out,np.arange(k)[None,:]]=phase*(observed['pilot'].astype(np.complex64)+mu)[:,None]
    design_error=float(np.linalg.norm(a-expected)/np.linalg.norm(expected))
    if design_error>1e-6:raise ValueError('CE design differs from integer channel operators')
    np.testing.assert_array_equal(y,observed['y'].astype(np.complex64))
    mode=config.get('dals_mode','mean');strength=config.get('dals_strength',1.)
    if state['outer_iter']<config.get('dals_start_iteration',1):mode='mean'
    if state['mode']!=mode or state['normalized_strength']!=strength:raise ValueError('CE mode differs')
    q=state.get('Q',np.zeros((k,k),dtype=complex));lam=float(state['regularization'])
    base=float(state['base_regularization']);scale=float(np.vdot(a,a).real/k)
    expected_q=np.zeros((k,k),dtype=complex);expected_lam=base
    if mode=='jsoft':expected_q=np.eye(k)*v.sum()
    elif mode=='zero_ridge':expected_q=np.eye(k)*strength*scale
    elif mode=='proximal':expected_lam+=strength*scale
    elif mode!='mean':raise ValueError('unregistered CE objective')
    np.testing.assert_allclose(q,expected_q,rtol=2e-6,atol=1e-6)
    np.testing.assert_allclose(lam,expected_lam,rtol=2e-6,atol=1e-6)
    gram=a.conj().T@a;rhs=a.conj().T@y+lam*old;lhs=gram+q+lam*np.eye(k)
    normal=float(np.linalg.norm(lhs@state['g_solution']-rhs)/max(1.,np.linalg.norm(rhs)))
    if normal>1e-5:raise ValueError('CE solution violates registered normal equation')
    return dict(iteration=state['outer_iter'],mode=mode,mean_variance=float(v.mean()),
        gamma_relative_scale=float(v.sum()/scale),effective_lambda=lam,
        design_relative_error=design_error,normal_relative_residual=normal)


def execute(args):
    started=time.time();root=args.root;c=json.loads(args.contract.read_text());tag=c['tag']
    sp=root/'runs'/tag/args.stage/'summary.json';s=json.loads(sp.read_text())
    ep=root/'evidence'/f'{tag}-{args.stage}-exit.json';e=json.loads(ep.read_text())
    src=root/('source-'+tag)/'source-manifest.json'
    if (s['status']!='COMPLETE' or e['exit_code']!=0 or e['timed_out']
            or s['contract_sha256']!=sha(args.contract) or s['source_manifest_sha256']!=sha(src)):
        raise ValueError('full-chain audit input binding differs')
    namespace=fresh_namespace(c)
    n=s['blocks'];arms={a['name']:a for a in stage_arms(c,args.stage)}
    expected={(b,snr,arm) for b in range(n) for snr in [7,8] for arm in arms}
    ldpc=n*2*sum(2+len(a.get('feedback',{}).get('refresh_checkpoints',[])) for a in arms.values())
    if s['calls']!={'F':len(expected),'T':0,'D':0} or s['nested_LDPC']!=ldpc:
        raise ValueError('full/nested call count differs')
    cache=next((sp.parent/'code-cache').glob('e1_ldpc_code_*.npz'))
    with np.load(cache,allow_pickle=False) as z:parity=z['H'];free=z['free_cols']
    fresh=None
    if namespace is not None:
        from .e1_ldpc import build_code
        from .light_gap_replay import CODE_KEYS
        code=build_code(cache_dir=sp.parent/'code-cache')
        environment=json.loads((sp.parent/'environment.json').read_text())
        if hashes({k:code[k] for k in CODE_KEYS})!=environment['code_identity'] or environment['fresh_namespace']!=list(namespace):
            raise ValueError('fresh code/environment identity differs')
        fresh=check_fresh_inputs(s,c,root,args.stage,code)
    ci,bi=np.nonzero(parity);exo={r['block']:r for r in s['exogenous']}
    seen=set();rows=[];arrays=0;max_bytes=0;current=None;truth=None;observed=None;repeats={};repeat_checks=0
    for item in s['records']:
        key=tuple(item[k] for k in ('block','snr','arm'))
        if key in seen or key not in expected:raise ValueError('unexpected/duplicate full arm')
        seen.add(key);record,value=verified_record(item,root)
        arrays+=len(record['state']['file']['fields'])
        rp=Path(item['record']).parent/(record['token']+'-reserve.json');reservation=json.loads(rp.read_text())
        if any(reservation[k]!=record[k] for k in ('block','snr','arm','kind','split','token')):
            raise ValueError('call reservation differs')
        if current!=key[:2]:
            current=key[:2];truth=load_state(exo[key[0]]['state']);observed=observed_at_snr(truth,key[1]);repeats={}
        if namespace is not None and args.stage=='engineering' and key[2] in ('MEAN','MEAN_REPEAT'):
            from .light_gap_receiver_run import NUMERIC_FIELDS
            repeats[key[2]]={field:value[field] for field in NUMERIC_FIELDS}
            if len(repeats)==2:
                for field in NUMERIC_FIELDS:np.testing.assert_array_equal(repeats['MEAN'][field],repeats['MEAN_REPEAT'][field])
                repeat_checks+=1
        if record['observed_hashes']!=hashes(observed) or record['exogenous_hashes']!=exo[key[0]]['hashes']:
            raise ValueError('full arm paired observation differs')
        score=offline_scores(value,truth,value['H'])
        if score!=record['scores'] or score!=item['scores'] or record['configuration']!=arms[key[2]]:
            raise ValueError('full arm raw score/configuration differs')
        if (bool(value['decode_ok'])!=bool(not (np.bincount(ci,weights=value['decoded'][bi],minlength=len(parity))%2).any())
                or not np.array_equal(value['info_hat'],value['decoded'][free])):
            raise ValueError('full arm decoder parity/extraction differs')
        if len(value['support'])!=24:raise ValueError('I1 capacity differs')
        feedback=value['code_feedback_records'];consumers={r['iteration']:r for r in feedback if r['stage']=='CE_consume'}
        arm=arms[key[2]];limit=arm['receiver'].get('outer_iteration_limit',10)
        updates=arm['receiver'].get('ce_update_iterations',list(range(1,limit)))
        checkpoints=[1]+arm.get('feedback',{}).get('refresh_checkpoints',[])
        if (len(value['dals'])!=len(updates) or set(consumers)!=set(updates)
                or [r['iteration'] for r in feedback if r['stage']=='decoder']!=checkpoints
                or len(value['bp_schedule']['calls'])!=limit):
            raise ValueError('missing CE/feedback consumers')
        checked_messages=check_feedback(value,arm)
        exchange=check_exchange(value,observed,truth['params'],arm)
        ce=[check_ce(state,observed,truth['params'],consumers[state['outer_iter']],arms[key[2]]['receiver']) for state in value['dals']]
        resources=value.get('resource_counts')
        if resources is not None:
            expected_resources=dict(outer_BP_calls=limit,
                outer_BP_iterations=sum(r['executed_iterations'] for r in value['bp_schedule']['calls']),
                terminal_BP_calls=1,terminal_BP_iterations=20 if value['graphs'][-1]['edges'] else 0,
                LDPC_calls=len(checkpoints)+1,CE_solves=len(updates))
            if exchange is not None:expected_resources['support_small_solves']=exchange['additional_small_solves']
            if resources!=expected_resources:raise ValueError('actual nested operation inventory differs')
        rows.append(dict(block=key[0],snr=key[1],arm=key[2],scores=score,CE=ce,
            checked_decoder_payloads=checked_messages,resource_counts=resources,support_exchange=exchange,
            seconds=item['seconds'],CPU_seconds=item['CPU_seconds']))
        max_bytes=max(max_bytes,Path(record['state']['file']['path']).stat().st_size+Path(item['record']).stat().st_size+rp.stat().st_size)
    if seen!=expected:raise ValueError('missing full arm')
    if namespace is not None and args.stage=='engineering':
        if (repeat_checks!=n*2 or len(s['engineering_comparisons'])!=n*2
                or any(r.get('CPU_mean_repeat_exact') is not True for r in s['engineering_comparisons'])):
            raise ValueError('fresh engineering repeat evidence is incomplete')
    if any('support_exchange' in a for a in arms.values()):
        actual=sum(r['support_exchange']['additional_small_solves'] for r in rows if r['support_exchange'] is not None)
        if s['nested_support_small_solves']!=actual:raise ValueError('nested support solve count differs')
    for suffix in ('reserve','result'):
        if len(list(sp.parent.glob('F-*-'+suffix+'.json')))!=len(expected):raise ValueError('unmatched reservation')
    target=root/'evidence'/f'{tag}-{args.stage}-audit.json'
    result=dict(status='PASS',stage=args.stage,tag=tag,records=len(rows),arrays_audited=arrays,CE_states=sum(len(r['CE']) for r in rows),
        rows=rows,summary_sha256=sha(sp),contract_sha256=sha(args.contract),exit_sha256=sha(ep),auditor_sha256=sha(__file__),
        new_calls=dict(F=0,T=0,D=0),wall_seconds=time.time()-started,
        scope='raw arrays/scores/paired identities and actual CE moment consumption/normal equations')
    if fresh is not None:result.update(fresh_inputs=fresh,engineering_repeat_checks=repeat_checks)
    with target.open('x') as f:json.dump(result,f,indent=2)
    if args.admit:
        if args.stage!='engineering':raise ValueError('only engineering can admit development')
        max_call=max(r['seconds'] for r in s['records'])
        overhead=max(0,s['wall_seconds']-sum(r['seconds'] for r in s['records']))/len(rows)
        eng_bytes=sum(p.stat().st_size for p in sp.parent.rglob('*') if p.is_file())
        choices=[]
        for blocks in c['development_block_options']:
            calls=blocks*2*len(stage_arms(c,'development'))
            input_seconds=max((e['generation_seconds'] for e in s['exogenous']),default=0.) if fresh else 0.
            input_bytes=fresh['max_bytes_per_block'] if fresh else 0
            seconds=2*(calls*(max_call+overhead)+blocks*input_seconds)+30
            storage=1.25*(eng_bytes+calls*max_bytes+blocks*input_bytes+10*1024**2)
            choices.append(dict(blocks=blocks,F=calls,conservative_seconds=seconds,conservative_bytes=storage,
                admitted=seconds<=c['development_seconds'] and storage<=c['output_bytes']))
        allowed=[r for r in choices if r['admitted']]
        if not allowed:raise RuntimeError('all development options exceed light resource bounds')
        chosen=max(allowed,key=lambda r:r['blocks'])
        admission=dict(status='PASS',**chosen,choices=choices,contract_sha256=sha(args.contract),
            source_sha256=s['source_manifest_sha256'],engineering_summary_sha256=sha(sp),
            engineering_audit_sha256=sha(target))
        with (root/'evidence'/f'{tag}-admission.json').open('x') as f:json.dump(admission,f,indent=2)
    print(json.dumps({k:result[k] for k in ['status','records','arrays_audited','CE_states','wall_seconds']}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--contract',type=Path,required=True);p.add_argument('--stage',choices=('engineering','development'),required=True)
    p.add_argument('--admit',action='store_true');execute(p.parse_args())
