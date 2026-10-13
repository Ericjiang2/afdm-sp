"""Bounded leave-one-physical-channel-out AFDM candidate score diagnostics.

Uses audited saved N1024 arrays. No receiver, BP, LDPC, F, or new channel call.
The crossfit Gamma is an oracle-calibrated plug-in working model, not a true
independent channel posterior or a deployment detector.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np

N, LMAX, W, Q = 1024, 24, 5, 275
PILOTS, SNRS, STATES = ('p0','pZ'), (10,20), (1,9)
IDS = tuple(range(40))
MAX_PAIRS, MAX_SECONDS, MAX_BYTES = 5120, 7200, 20*1024**3
PEAK_ESTIMATE_BYTES = 4*1024**3


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(value):
    a=np.ascontiguousarray(value); h=hashlib.sha256()
    h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()


def require(ok,message):
    if not ok: raise ValueError(message)


def source_synthesis():
    path=Path(__file__).with_name('ce_synthesis_offline_v1.py')
    spec=importlib.util.spec_from_file_location('ce_synthesis_offline_v1',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module,path


def layout(n,lmax,w,c1,c2):
    """Input-indexed phases; column j acts once at row (input+offset_j)%n."""
    from afdm_sp_joint_unrolled.physical_stride import physical_stride
    q=physical_stride(n,c1)
    delays=np.repeat(np.arange(lmax+1,dtype=np.int64),2*w+1)
    dopplers=np.tile(np.arange(-w,w+1,dtype=np.int64),lmax+1)
    offsets=(q*delays+dopplers)%n
    require(len(np.unique(offsets))==len(offsets),
            'registered full dictionary needs unique physical offsets')
    inputs=np.arange(n,dtype=np.int64)
    rows=(inputs[:,None]+offsets[None,:])%n
    phase=np.exp(2j*np.pi*(-c1*delays[None,:]**2
        +c2*(rows.astype(float)**2-inputs[:,None].astype(float)**2)
        -inputs[:,None]*delays[None,:]/n))
    return dict(n=n,lmax=lmax,w=w,q=q,c1=c1,c2=c2,delays=delays,dopplers=dopplers,
                offsets=offsets,rows=rows,phase=phase)


def project_full(H,operator):
    """Truth-side Frobenius coefficients, with no dense atom stack."""
    H=np.asarray(H,dtype=np.complex128);n=operator['n'];d=len(operator['delays'])
    require(H.shape==(n,n) and np.isfinite(H).all(), 'physical H shape/finiteness differs')
    inputs=np.arange(n)[:,None]
    coeff=np.sum(operator['phase'].conj()*H[operator['rows'],inputs],axis=0)/n
    tail_sq=float(np.vdot(H,H).real-n*np.vdot(coeff,coeff).real)
    physical_sq=float(np.vdot(H,H).real)
    require(physical_sq>0,'physical H has zero projection reference energy')
    require(tail_sq >= -1e-8*max(1.,physical_sq),
            'Frobenius dictionary projection energy does not close')
    require(coeff.shape==(d,), 'full projection coefficient count differs')
    return coeff,dict(tail_frobenius_squared=max(0.,tail_sq),
        physical_frobenius_squared=physical_sq,
        tail_relative_squared=max(0.,tail_sq)/physical_sq,
        projected_gain_sha256=array_sha(coeff))


def embed_gain(state,operator):
    dl,dk=(np.asarray(state[k],dtype=np.int64) for k in ('support_delays','support_dopplers'))
    gains=np.asarray(state['g_solution'],dtype=np.complex128)
    A=np.asarray(state['A'])
    n,lmax,w=operator['n'],operator['lmax'],operator['w']
    require(dl.ndim==dk.ndim==gains.ndim==1 and dl.shape==dk.shape==gains.shape
            and A.shape==(n,len(gains)) and np.all((dl>=0)&(dl<=lmax))
            and np.all(abs(dk)<=w), 'CE active gain/support/A mapping differs')
    ids=dl*(2*w+1)+(dk+w)
    require(len(set(ids.tolist()))==len(ids), 'duplicate CE active atom')
    value=np.zeros(len(operator['delays']),np.complex128);value[ids]=gains
    return value,dict(active_columns=len(ids),atom_ids=ids.tolist(),
        g_solution_sha256=array_sha(state['g_solution']),
        full_gain_sha256=array_sha(value))


def fold(training, target):
    """Only 15 other physical channels; error rows are in common D275."""
    require(target in range(16) and set(training)==set(range(16))-{target},
            'target physical channel or condition leaked into calibration fold')
    ids=tuple(sorted(training))
    E=np.stack([np.asarray(training[j],dtype=np.complex128) for j in ids])
    require(E.ndim==2 and E.shape[0]==15 and np.isfinite(E).all(),
            '15 finite common-dictionary errors required')
    m=E.mean(axis=0);center=E-m
    U=center.T/np.sqrt(14.)  # 15 columns, numerical rank <=14
    gamma=U@U.conj().T; pseudo=U@U.T
    gamma_norm=float(np.linalg.norm(gamma));pseudo_norm=float(np.linalg.norm(pseudo))
    singular=np.linalg.svd(U,compute_uv=False)
    rank=int(np.sum(singular>1e-12*singular[0])) if singular[0] else 0
    require(rank<=14, 'centered 15-channel factor exceeds rank14')
    return dict(channels=ids,E=E,m_e=m,U=U,rank=rank,
        gamma_frobenius=gamma_norm,pseudo_frobenius=pseudo_norm,
        pseudo_to_gamma=None if gamma_norm==0 else pseudo_norm/gamma_norm,
        E_sha256=array_sha(E),m_e_sha256=array_sha(m),U_sha256=array_sha(U))


def baseline_action(x,operator,m,U):
    """Full D action once per state; candidates update 275 output rows."""
    n,d=operator['n'],len(operator['delays'])
    x=np.asarray(x,dtype=np.complex128);m=np.asarray(m,dtype=np.complex128)
    U=np.asarray(U,dtype=np.complex128)
    require(x.shape==(n,) and m.shape==(d,) and U.shape[0]==d
            and np.isfinite(x).all() and np.isfinite(m).all() and np.isfinite(U).all(),
            'baseline action input differs')
    D=np.empty((n,d),np.complex128)
    D[operator['rows'],np.arange(d)[None,:]]=operator['phase']*x[:,None]
    return D@m,D@U


def updated_action(mean,Z,operator,m,U,index,delta):
    rows=operator['rows'][index]
    require(len(set(rows.tolist()))==len(rows), 'candidate update rows collide')
    factor=delta*operator['phase'][index]
    new_mean=mean.copy();new_Z=Z.copy()
    new_mean[rows]+=factor*m
    new_Z[rows,:]+=factor[:,None]*U
    return new_mean,new_Z


def factor_covariance(Z,sigma2):
    """One <=15-dimensional Cholesky per distinct candidate covariance."""
    require(sigma2>0 and np.isfinite(sigma2) and Z.ndim==2
            and np.isfinite(Z).all(),
            'positive thermal noise and finite lowrank action required')
    K=np.eye(Z.shape[1],dtype=np.complex128)+(Z.conj().T@Z)/sigma2
    L=np.linalg.cholesky(K)
    logdet=float(Z.shape[0]*np.log(sigma2)+2*np.log(np.diag(L).real).sum())
    require(np.isfinite(logdet), 'finite candidate logdet required')
    return L,logdet


def quadratic_from_factor(y,mean,Z,sigma2,L):
    y=np.asarray(y,dtype=np.complex128);r=y-mean
    require(r.ndim==1 and Z.shape[0]==len(r) and L.shape==(Z.shape[1],Z.shape[1])
            and np.isfinite(r).all(), 'fixed/candidate quadratic inputs differ')
    z=Z.conj().T@r
    reduction=np.linalg.norm(np.linalg.solve(L,z))**2/sigma2**2
    quadratic=float((np.vdot(r,r).real/sigma2)-reduction)
    require(np.isfinite(quadratic) and quadratic>=-1e-8,
            'finite positive lowrank Gaussian score required')
    return max(0.,quadratic)


def lowrank_terms(y,mean,Z,sigma2):
    """Woodbury and determinant lemma in 15 dimensions; Gamma may be singular."""
    L,logdet=factor_covariance(Z,sigma2)
    return dict(quadratic=quadratic_from_factor(y,mean,Z,sigma2,L),
                logdet=logdet,Cholesky_dimension=Z.shape[1])


def candidate_pair(y,pilot,mu,m,U,operator,sigma2,index,baseline=None):
    """One fixed real-bit pair; no true target symbol enters the score."""
    n=operator['n'];mu=np.asarray(mu,dtype=np.complex128)
    pilot=np.asarray(pilot,dtype=np.complex128)
    require(mu.shape==pilot.shape==(n,) and index in IDS and
            np.isfinite(mu).all() and np.isfinite(pilot).all(),
            'preselected symbol and observed pilot/mu required')
    if baseline is None:
        mean0,Z0=baseline_action(pilot+mu,operator,m,U)
        L0,logdet0=factor_covariance(Z0,sigma2)
    else:
        mean0,Z0,L0,logdet0=baseline
    imag=.5 if mu[index].imag>=0 else -.5
    cand={sign:sign*.5+1j*imag for sign in (+1,-1)}
    scores={};fixed={}
    for sign in (+1,-1):
        mean,Z=updated_action(mean0,Z0,operator,m,U,index,cand[sign]-mu[index])
        scores[sign]=lowrank_terms(y,mean,Z,sigma2)
        fixed[sign]=quadratic_from_factor(y,mean,Z0,sigma2,L0)
    mean_delta=fixed[+1]-fixed[-1]
    inverse_delta=(scores[+1]['quadratic']-fixed[+1])-(scores[-1]['quadratic']-fixed[-1])
    logdet_delta=scores[+1]['logdet']-scores[-1]['logdet']
    direct=(scores[+1]['quadratic']+scores[+1]['logdet'])-(
        scores[-1]['quadratic']+scores[-1]['logdet'])
    closure=(mean_delta+inverse_delta+logdet_delta)-direct
    require(abs(closure)<=1e-9*max(1.,abs(direct)),
            'candidate three-term NLL difference does not close')
    return dict(index=index,candidate_plus=[cand[+1].real,cand[+1].imag],
        candidate_minus=[cand[-1].real,cand[-1].imag],
        scalar_terms=dict(q_plus=scores[+1]['quadratic'],q_minus=scores[-1]['quadratic'],
            fixed_q_plus=fixed[+1],fixed_q_minus=fixed[-1],
            logdet_plus=scores[+1]['logdet'],logdet_minus=scores[-1]['logdet']),
        delta_frozen_covariance_mean=float(mean_delta),
        delta_inverse_covariance_change=float(inverse_delta),
        delta_logdet_change=float(logdet_delta),
        delta_total_NLL=float(direct),closure_absolute=float(abs(closure)),
        baseline_real_choice=1 if mean_delta<=0 else -1,
        corrected_real_choice=1 if direct<=0 else -1,
        candidate_prior_term='omitted_by_working_score_definition_zero',
        score_calls=dict(frozen_C_mu=1 if baseline is None else 0,candidate_C=2,
            fixed_C_mu_quadratics=2,small_Cholesky_candidate=2))


def check_scope(scope):
    require(scope.get('schema')=='gamma-crossfit-scope-v1'
        and scope.get('status')=='frozen_after_review'
        and scope.get('existing_frames')==64
        and scope.get('independent_physical_channels')==16
        and scope.get('pilots')==list(PILOTS)
        and scope.get('snrs')==list(SNRS)
        and scope.get('states')==list(STATES)
        and scope.get('symbol_indices')==list(IDS)
        and scope.get('training_channels_per_target')==15
        and scope.get('maximum_candidate_pair_differences')==MAX_PAIRS
        and scope.get('single_candidate_scores_per_pair')==2
        and (scope.get('new_F'),scope.get('new_BP'),scope.get('new_LDPC'),
             scope.get('new_physical_channels'))==(0,0,0,0)
        and scope.get('wall_seconds_cap')==MAX_SECONDS
        and scope.get('new_disk_bytes_cap')==MAX_BYTES
        and scope.get('threads')==1,
        'frozen Gamma crossfit source/scope/budget contract differs')


def source_guard(scope,args,helper_path):
    require(sha(args.scope)==args.scope_sha256
        and sha(Path(__file__))==args.script_sha256,
        'Gamma scope or runner script SHA differs')
    require(scope.get('helper_sha256')==sha(helper_path),
        'frozen offline synthesis helper SHA differs')
    source=Path(scope['analysis_source_directory']).resolve()
    manifest=source/'source-manifest.json'
    require(sha(manifest)==scope['analysis_source_manifest_sha256'],
        'analysis-v4 source manifest SHA differs')
    package=source/'afdm_sp_joint_unrolled'
    inventory=json.loads(manifest.read_text())
    observed={str(p.relative_to(package)) for p in package.rglob('*.py')}
    require(set(inventory)==observed,'analysis-v4 Python inventory differs')
    for name,expected in inventory.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and sha(package/name)==expected,
                'analysis-v4 package source differs: '+name)
    if str(source) not in sys.path:
        sys.path.insert(0,str(source))
    import afdm_sp_joint_unrolled as loaded
    require(Path(loaded.__file__).resolve().parent==package.resolve(),
        'loaded analysis package is not bound analysis-v4 source')
    return dict(scope_sha256=args.scope_sha256,script_sha256=args.script_sha256,
        helper_sha256=sha(helper_path),analysis_manifest_sha256=sha(manifest),
        analysis_source_directory=str(source))


def nsize_paths(root):
    base=root/'runs/nsize-uwa-1024-v1';evidence=root/'evidence'
    return SimpleNamespace(nsize_root=root,
        nsize_engineering_summary=base/'engineering/summary.json',
        nsize_engineering_audit=evidence/'nsize-uwa-1024-v1-engineering-raw-audit.json',
        nsize_development_summary=base/'development/summary.json',
        nsize_development_audit=evidence/'nsize-uwa-1024-v1-development-raw-audit.json',
        g1_root=None)


def load_inputs(root,syn):
    """All original A/F calls are read back and audited before first comparison."""
    import torch
    from afdm_sp_joint_unrolled.classical_joint_unrolled import build_A_for_DALS_torch
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    from afdm_sp_joint_unrolled.bottleneck_pilot import hashes
    source,_=syn.validated_sources(nsize_paths(root))
    require(source['source_sha256'] is not None,
            'original receiver source SHA missing')
    index=source['index'];raws={};projection={};project_meta={};targets={};operator=None
    for b in range(16):
        ae=index['A',b,10,'UWA_N1024_INPUT']
        A_record,raw=verified_record(ae,root)
        require(raw['domain']=='uwa' and raw['N']==N and raw['block']==b,
                'audited N1024 A identity/shape differs')
        meta=raw['metadata']
        require((meta['l_max'],meta['k_max'],meta['dictionary_size'])==(LMAX,W,Q)
                and abs(2*N*meta['c1']-11)<1e-10,
                'N1024 physical dictionary metadata differs')
        if operator is None:
            operator=layout(N,LMAX,W,meta['c1'],meta['c2'])
        else:
            require((meta['c1'],meta['c2'])==(operator['c1'],operator['c2']),
                    'physical dictionary geometry differs by channel')
        projection[b],project_meta[b]=project_full(raw['H'],operator)
        raws[b]=dict(raw=raw,A_entry=ae,A_state_npz_sha256=A_record['state']['file']['sha256'])
        for pilot in PILOTS:
            for snr in SNRS:
                fe=index['F',b,snr,pilot+'__OMP_BASE']
                record,value=verified_record(fe,root)
                require(record['input_record_sha256']==ae['sha256'],
                        'N1024 F/A parent hash differs')
                sigma2=10.**(-snr/10)
                y=raw['noiseless'][pilot]+np.sqrt(sigma2)*raw['noise']
                p=np.asarray(raw['pilots'][pilot]).copy()
                obs=dict(y=y,pilot=p,sigma2=np.asarray(sigma2),
                    constellation=np.array([.5+.5j,.5-.5j,-.5+.5j,-.5-.5j]))
                require(record['observed_hashes']==hashes(obs),
                        'N1024 observed input hash differs')
                ce=value['CE']
                require(len(ce)==9 and [s['outer_iter'] for s in ce]==list(range(1,10)),
                        'N1024 nine actual CE states required')
                for t in STATES:
                    state=ce[t-1]
                    require(state['mode']=='mean' and np.asarray(state['mu']).shape==(N,),
                            'N1024 mean CE working state differs')
                    ghat,embed=embed_gain(state,operator)
                    td=torch.as_tensor(state['support_delays'],dtype=torch.long)
                    tk=torch.as_tensor(state['support_dopplers'],dtype=torch.long)
                    total=torch.as_tensor(p,dtype=torch.complex64)+torch.as_tensor(
                        state['mu'],dtype=torch.complex64)
                    direct_A=build_A_for_DALS_torch(N,td,tk,total,meta['c1'],meta['c2'],
                        W,cdtype=torch.complex64).numpy()
                    np.testing.assert_allclose(np.asarray(state['A']),direct_A,
                        rtol=2e-6,atol=2e-6)
                    targets[b,pilot,snr,t]=dict(block=b,pilot=pilot,snr=snr,t=t,
                        y=np.asarray(y,dtype=np.complex128),pilot_array=np.asarray(p,dtype=np.complex128),
                        sigma2=sigma2,mu=np.asarray(state['mu'],dtype=np.complex128),
                        ghat=ghat,embed=embed,F_entry=fe,A_entry=ae,
                        F_state_npz_sha256=record['state']['file']['sha256'],
                        A_state_npz_sha256=raws[b]['A_state_npz_sha256'],
                        CE_A_sha256=array_sha(state['A']),
                        CE_mu_sha256=array_sha(state['mu']),
                        direct_A_relative_error=float(np.linalg.norm(
                            np.asarray(state['A'])-direct_A)/max(1.,np.linalg.norm(direct_A))))
    require(len(targets)==128,'N1024 two-state audited target inventory differs')
    return source,operator,raws,projection,project_meta,targets


def output_size(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())


def proc_kib(name,path):
    for line in Path(path).read_text().splitlines():
        if line.startswith(name+':'):
            return int(line.split()[1])*1024
    raise ValueError('Linux resource field missing: '+name)


def memory_preflight():
    available=proc_kib('MemAvailable','/proc/meminfo')
    require(PEAK_ESTIMATE_BYTES<=MAX_BYTES and available>=2*PEAK_ESTIMATE_BYTES,
            'Gamma conservative 4GiB peak requires at least 8GiB available memory')
    return dict(MemAvailable_bytes=available,conservative_peak_estimate_bytes=PEAK_ESTIMATE_BYTES,
        required_available_multiplier=2)


def check_budget(started,out):
    require(time.monotonic()-started<MAX_SECONDS,
            'Gamma offline 2h wall budget exhausted')
    require(output_size(out)<=MAX_BYTES,
        'Gamma offline new disk 20GiB budget exhausted')
    require(proc_kib('VmHWM','/proc/self/status')<=MAX_BYTES,
            'Gamma offline process peak memory 20GiB budget exhausted')


def build_folds(targets,projection,operator):
    errors={}
    for pilot in PILOTS:
        for snr in SNRS:
            for t in STATES:
                errors[pilot,snr,t]={b:targets[b,pilot,snr,t]['ghat']-projection[b]
                                    for b in range(16)}
    require(all(all(np.asarray(e).shape==(Q,) for e in group.values())
                for group in errors.values()),
            'crossfit errors not on common D275')
    return errors


def run(args,scope,binding,syn):
    from afdm_sp_joint_unrolled.light_gap_replay import verified_record
    started=time.monotonic();cpu_started=time.process_time()
    root=Path(args.root).resolve();out=Path(args.output_dir).resolve()
    require(out.is_relative_to(root), 'new Gamma output must stay within source output root')
    memory_contract=memory_preflight()
    source,operator,raws,projection,project_meta,targets=load_inputs(root,syn)
    require(source['source_sha256']==scope['original_receiver_source_sha256'],
            'original N1024 receiver source is not frozen scope source')
    out.mkdir(parents=True,exist_ok=False);(out/'folds').mkdir()
    fold_rows=[];pair_count=0;baseline_count=0
    try:
        errors=build_folds(targets,projection,operator)
        with (out/'comparisons.jsonl').open('x') as pair_file:
            for b in range(16):
                for pilot in PILOTS:
                    for snr in SNRS:
                        for t in STATES:
                            check_budget(started,out)
                            target=targets[b,pilot,snr,t]
                            group=errors[pilot,snr,t]
                            training={j:group[j] for j in range(16) if j!=b}
                            cal=fold(training,b)
                            require(cal['channels']==tuple(j for j in range(16) if j!=b),
                                'fold physical channel membership differs')
                            fold_name=f'b{b:02d}-{pilot}-{snr}-t{t}'
                            fold_path=out/'folds'/(fold_name+'.npz')
                            np.savez(fold_path,E=cal['E'],m_e=cal['m_e'],U=cal['U'],
                                     channels=np.asarray(cal['channels'],np.int64))
                            fold_record=dict(block=b,pilot=pilot,snr=snr,t=t,
                                channels=list(cal['channels']),E_sha256=cal['E_sha256'],
                                excluded_target_conditions=[dict(pilot=pp,snr=ss,t=tt)
                                    for pp in PILOTS for ss in SNRS for tt in range(1,10)],
                                m_e_sha256=cal['m_e_sha256'],U_sha256=cal['U_sha256'],
                                factor_rank=cal['rank'],Gamma_frobenius=cal['gamma_frobenius'],
                                pseudo_frobenius=cal['pseudo_frobenius'],
                                pseudo_to_Gamma=cal['pseudo_to_gamma'],
                                fold_npz=str(fold_path),fold_npz_sha256=sha(fold_path),
                                target_F_sha256=target['F_entry']['sha256'],
                                target_A_sha256=target['A_entry']['sha256'],
                                target_F_state_npz_sha256=target['F_state_npz_sha256'],
                                target_A_state_npz_sha256=target['A_state_npz_sha256'],
                                training_F_sha256=[targets[j,pilot,snr,t]['F_entry']['sha256']
                                    for j in cal['channels']],
                                training_A_sha256=[targets[j,pilot,snr,t]['A_entry']['sha256']
                                    for j in cal['channels']],
                                training_F_state_npz_sha256=[targets[j,pilot,snr,t]['F_state_npz_sha256']
                                    for j in cal['channels']],
                                training_A_state_npz_sha256=[targets[j,pilot,snr,t]['A_state_npz_sha256']
                                    for j in cal['channels']])
                            fold_rows.append(fold_record)
                            m0=target['ghat']-cal['m_e']
                            fold_record['m0_sha256']=array_sha(m0)
                            mean0,Z0=baseline_action(target['pilot_array']+target['mu'],
                                operator,m0,cal['U'])
                            L0,logdet0=factor_covariance(Z0,target['sigma2'])
                            baseline=(mean0,Z0,L0,logdet0);baseline_count+=1
                            for index in IDS:
                                check_budget(started,out)
                                score=candidate_pair(target['y'],target['pilot_array'],target['mu'],
                                    m0,cal['U'],operator,target['sigma2'],index,baseline)
                                identity=dict(block=b,pilot=pilot,snr=snr,t=t,index=index,
                                    fold_npz_sha256=fold_record['fold_npz_sha256'],
                                    target_F_sha256=target['F_entry']['sha256'],
                                    target_A_sha256=target['A_entry']['sha256'],
                                    target_F_state_npz_sha256=target['F_state_npz_sha256'],
                                    target_A_state_npz_sha256=target['A_state_npz_sha256'],
                                    target_mu_sha256=target['CE_mu_sha256'],
                                    target_CE_A_sha256=target['CE_A_sha256'],
                                    m0_sha256=array_sha(m0),sigma2=target['sigma2'])
                                pair_file.write(json.dumps(dict(identity,**score))+'\n')
                                pair_count+=1
                if b==1:
                    require(pair_count==640 and baseline_count==16,
                        'Gamma 2-channel engineering gate count differs')
                    (out/'engineering.json').write_text(json.dumps(dict(status='PASS',
                        completed_physical_channels=[0,1],candidate_pair_differences=640,
                        baseline_C_mu_factors=16,source_binding=binding),indent=2))
                print(json.dumps(dict(block=b,pairs=pair_count,baselines=baseline_count)),flush=True)
        require(pair_count==MAX_PAIRS and baseline_count==128,
            'Gamma final pair/baseline counts differ')
        (out/'folds.json').write_text(json.dumps(fold_rows,indent=2))
        # Target truth is read only after all candidate scores are durable.
        evaluation=evaluate_saved_pairs(out/'comparisons.jsonl',raws)
        (out/'evaluation.json').write_text(json.dumps(evaluation,indent=2))
        source_summaries={name:dict(summary_sha256=v['summary_sha256'],
            audit_sha256=v['audit_sha256']) for name,v in source['stages'].items()}
        summary=dict(status='COMPLETE',schema='gamma-crossfit-v1',scope_binding=binding,
            original_receiver_source_sha256=source['source_sha256'],
            source_summaries=source_summaries,
            source_parent_A_sha256=[raws[b]['A_entry']['sha256'] for b in range(16)],
            source_parent_F_sha256=sorted({v['F_entry']['sha256'] for v in targets.values()}),
            physical_projection=project_meta,
            original_A_record_reads=16,original_F_record_reads=64,
            physical_projection_computations=16,CE_A_rebuild_checks=128,
            saved_folds=128,candidate_pair_differences=pair_count,
            baseline_C_mu_factors=baseline_count,candidate_C_factors=2*pair_count,
            fixed_C_mu_quadratic_triangular_solves=2*pair_count,
            total_small_Cholesky_factors=baseline_count+2*pair_count,
            new_F=0,new_BP=0,new_LDPC=0,new_physical_channels=0,
            comparisons_sha256=sha(out/'comparisons.jsonl'),
            folds_sha256=sha(out/'folds.json'),evaluation_sha256=sha(out/'evaluation.json'),
            engineering_sha256=sha(out/'engineering.json'),
            truth_scope='all H preloaded as other-fold calibration bank; each target fold excludes its own H/data; target data used only after saved scores',
            candidate_prior_term='omitted_by_working_score_definition_zero',
            model_scope='crossfit oracle-calibrated lowrank proper-complex plug-in working score; '
                'same-y mean/support/mu, outside-D tail and other soft-data error unmodelled',
            memory_preflight=memory_contract,peak_resident_bytes=proc_kib(
                'VmHWM','/proc/self/status'),
            wall_seconds=time.monotonic()-started,CPU_seconds=time.process_time()-cpu_started)
        check_budget(started,out)
        verify_binding(scope,args,binding,syn,source)
        (out/'summary.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps(dict(status='COMPLETE',pairs=pair_count,output=str(out))),flush=True)
    except BaseException as exc:
        (out/'failure.json').write_text(json.dumps(dict(status='FAILED',
            pairs=pair_count,baselines=baseline_count,error=repr(exc)),indent=2))
        raise


def evaluate_saved_pairs(path,raws):
    """Separate post-score truth read: real-bit changes only, no FER claim."""
    rows={b:dict(block=b,pairs=0,baseline_real_errors=0,
        corrected_real_errors=0,rescued=0,new_errors=0,changed_choices=0)
        for b in range(16)}
    with Path(path).open() as handle:
        for line in handle:
            v=json.loads(line);b=v['block'];truth=np.asarray(raws[b]['raw']['data'])[v['index']]
            sign=1 if truth.real>0 else -1
            base=v['baseline_real_choice'];new=v['corrected_real_choice'];row=rows[b]
            row['pairs']+=1;row['baseline_real_errors']+=int(base!=sign)
            row['corrected_real_errors']+=int(new!=sign)
            row['rescued']+=int(base!=sign and new==sign)
            row['new_errors']+=int(base==sign and new!=sign)
            row['changed_choices']+=int(base!=new)
    require(sum(v['pairs'] for v in rows.values())==MAX_PAIRS,
        'post-score real-symbol evaluation pair count differs')
    return dict(channel_rows=list(rows.values()),
        scope='same saved development channels; real-component offline choices only, not FER/CONF')


def verify_binding(scope,args,binding,syn,source):
    helper_path=Path(__file__).with_name('ce_synthesis_offline_v1.py')
    require(source_guard(scope,args,helper_path)==binding,
        'Gamma source/scope changed during offline run')
    for name,stage in source['stages'].items():
        require(sha(stage['summary_path'])==stage['summary_sha256']
            and sha(stage['audit_path'])==stage['audit_sha256'],
            'original N1024 '+name+' summary/audit changed during run')


def audit(args,scope,binding,syn):
    """Read-only source/fold/closure audit; no new candidate covariance score."""
    root=Path(args.root).resolve();out=Path(args.output_dir).resolve()
    summary=json.loads((out/'summary.json').read_text())
    require(summary['status']=='COMPLETE' and summary['scope_binding']==binding
        and summary['candidate_pair_differences']==MAX_PAIRS
        and summary['saved_folds']==128 and summary['baseline_C_mu_factors']==128
        and summary['candidate_C_factors']==10240
        and summary['new_F']==summary['new_BP']==summary['new_LDPC']==0,
        'Gamma saved run summary/counts differ')
    source,operator,raws,projection,project_meta,targets=load_inputs(root,syn)
    verify_binding(scope,args,binding,syn,source)
    require(summary['original_receiver_source_sha256']==source['source_sha256']
        and summary['physical_projection']=={str(b):v for b,v in project_meta.items()}
        and summary['source_parent_A_sha256']==[raws[b]['A_entry']['sha256']
            for b in range(16)]
        and summary['source_parent_F_sha256']==sorted({v['F_entry']['sha256']
            for v in targets.values()}),
        'Gamma saved original source/projection/parent hashes differ')
    require(sha(out/'comparisons.jsonl')==summary['comparisons_sha256']
        and sha(out/'folds.json')==summary['folds_sha256']
        and sha(out/'evaluation.json')==summary['evaluation_sha256']
        and sha(out/'engineering.json')==summary['engineering_sha256'],
        'Gamma saved result hash differs')
    engineering=json.loads((out/'engineering.json').read_text())
    require(engineering['status']=='PASS'
        and engineering['completed_physical_channels']==[0,1]
        and engineering['candidate_pair_differences']==640
        and engineering['baseline_C_mu_factors']==16
        and engineering['source_binding']==binding,
        'Gamma in-run engineering gate differs')
    errors=build_folds(targets,projection,operator)
    fold_rows=json.loads((out/'folds.json').read_text())
    require(len(fold_rows)==128,'Gamma saved fold count differs')
    fold_by_key={}
    for row in fold_rows:
        b,pilot,snr,t=(row[k] for k in ('block','pilot','snr','t'))
        key=(b,pilot,snr,t)
        require(key not in fold_by_key,'duplicate Gamma saved fold')
        fold_by_key[key]=row
        group=errors[pilot,snr,t]
        training={j:group[j] for j in range(16) if j!=b}
        expected=fold(training,b)
        path=Path(row['fold_npz'])
        require(path.is_relative_to(out) and sha(path)==row['fold_npz_sha256'],
                'Gamma fold NPZ path/hash differs')
        with np.load(path,allow_pickle=False) as saved:
            require(set(saved.files)=={'E','m_e','U','channels'}
                and np.array_equal(saved['E'],expected['E'])
                and np.array_equal(saved['m_e'],expected['m_e'])
                and np.array_equal(saved['U'],expected['U'])
                and np.array_equal(saved['channels'],np.asarray(expected['channels'])),
                'Gamma saved fold arrays differ from 15 original channels')
        require(row['channels']==list(expected['channels'])
            and row['excluded_target_conditions']==[dict(pilot=pp,snr=ss,t=tt)
                for pp in PILOTS for ss in SNRS for tt in range(1,10)]
            and row['E_sha256']==expected['E_sha256']
            and row['m_e_sha256']==expected['m_e_sha256']
            and row['U_sha256']==expected['U_sha256']
            and row['target_F_sha256']==targets[b,pilot,snr,t]['F_entry']['sha256']
            and row['target_A_sha256']==targets[b,pilot,snr,t]['A_entry']['sha256']
            and row['target_F_state_npz_sha256']==targets[b,pilot,snr,t]['F_state_npz_sha256']
            and row['target_A_state_npz_sha256']==targets[b,pilot,snr,t]['A_state_npz_sha256']
            and row['m0_sha256']==array_sha(targets[b,pilot,snr,t]['ghat']-expected['m_e'])
            and row['training_F_sha256']==[targets[j,pilot,snr,t]['F_entry']['sha256']
                for j in expected['channels']]
            and row['training_A_sha256']==[targets[j,pilot,snr,t]['A_entry']['sha256']
                for j in expected['channels']]
            and row['training_F_state_npz_sha256']==[targets[j,pilot,snr,t]['F_state_npz_sha256']
                for j in expected['channels']]
            and row['training_A_state_npz_sha256']==[targets[j,pilot,snr,t]['A_state_npz_sha256']
                for j in expected['channels']],
            'Gamma fold membership/source hash differs')
    require(set(fold_by_key)=={(b,p,s,t) for b in range(16) for p in PILOTS
        for s in SNRS for t in STATES},'Gamma saved fold grid differs')
    pairs=set();closure_checks=0
    with (out/'comparisons.jsonl').open() as handle:
        for line in handle:
            row=json.loads(line);key=tuple(row[k] for k in ('block','pilot','snr','t','index'))
            require(key not in pairs and row['candidate_prior_term']
                =='omitted_by_working_score_definition_zero',
                'Gamma candidate identity/prior scope differs')
            pairs.add(key)
            b,p,s,t,index=key;target=targets[b,p,s,t];fold_row=fold_by_key[b,p,s,t]
            imag=.5 if target['mu'][index].imag>=0 else -.5
            require(row['candidate_plus']==[.5,imag]
                and row['candidate_minus']==[-.5,imag]
                and row['fold_npz_sha256']==fold_row['fold_npz_sha256']
                and row['target_F_sha256']==target['F_entry']['sha256']
                and row['target_A_sha256']==target['A_entry']['sha256']
                and row['target_F_state_npz_sha256']==target['F_state_npz_sha256']
                and row['target_A_state_npz_sha256']==target['A_state_npz_sha256']
                and row['target_mu_sha256']==target['CE_mu_sha256']
                and row['target_CE_A_sha256']==target['CE_A_sha256']
                and row['m0_sha256']==fold_row['m0_sha256']
                and row['sigma2']==target['sigma2']
                and row['score_calls']==dict(frozen_C_mu=0,candidate_C=2,
                    fixed_C_mu_quadratics=2,small_Cholesky_candidate=2),
                'Gamma pair source/candidate/cost binding differs')
            scalar=row['scalar_terms']
            require(set(scalar)=={'q_plus','q_minus','fixed_q_plus','fixed_q_minus',
                'logdet_plus','logdet_minus'} and all(np.isfinite(v) for v in scalar.values()),
                'Gamma saved six scalar score terms differ')
            mean_delta=scalar['fixed_q_plus']-scalar['fixed_q_minus']
            inverse_delta=(scalar['q_plus']-scalar['fixed_q_plus'])-(
                scalar['q_minus']-scalar['fixed_q_minus'])
            logdet_delta=scalar['logdet_plus']-scalar['logdet_minus']
            direct=(scalar['q_plus']+scalar['logdet_plus'])-(
                scalar['q_minus']+scalar['logdet_minus'])
            tolerance=1e-9*max(1.,abs(direct))
            require(abs(mean_delta-row['delta_frozen_covariance_mean'])<=tolerance
                and abs(inverse_delta-row['delta_inverse_covariance_change'])<=tolerance
                and abs(logdet_delta-row['delta_logdet_change'])<=tolerance
                and abs(direct-row['delta_total_NLL'])<=tolerance
                and row['baseline_real_choice']==(1 if mean_delta<=0 else -1)
                and row['corrected_real_choice']==(1 if direct<=0 else -1),
                'Gamma saved scalar decomposition or real choice differs')
            close=row['delta_frozen_covariance_mean']+row['delta_inverse_covariance_change']
            close+=row['delta_logdet_change']
            require(abs(close-row['delta_total_NLL'])<=1e-9*max(1.,abs(row['delta_total_NLL']))
                and row['closure_absolute']<=1e-9*max(1.,abs(row['delta_total_NLL'])),
                'saved Gamma candidate three-term arithmetic differs')
            closure_checks+=1
    expected_keys={(b,p,s,t,i) for b in range(16) for p in PILOTS for s in SNRS
        for t in STATES for i in IDS}
    require(pairs==expected_keys and closure_checks==MAX_PAIRS,
        'Gamma saved candidate grid differs')
    require(evaluate_saved_pairs(out/'comparisons.jsonl',raws)==
        json.loads((out/'evaluation.json').read_text()),
        'Gamma saved offline real-bit evaluation differs from original data')
    result=dict(status='PASS',schema='gamma-crossfit-v1-raw-audit',
        summary_sha256=sha(out/'summary.json'),scope_binding=binding,
        original_A_record_rereads=16,original_F_record_rereads=64,
        physical_projection_recomputations=16,CE_A_rebuild_recomputations=128,
        fold_array_recomputations=128,scalar_closure_recomputations=MAX_PAIRS,
        postscore_realbit_recomputations=MAX_PAIRS,
        candidate_covariance_recomputations=0,new_F=0,new_BP=0,new_LDPC=0,
        independence='main-session saved-array/self-audit; scientific review weak',
        scope='crossfit oracle-calibrated plug-in working model, not CONF or FER')
    target=out/'raw-audit.json'
    with target.open('x') as handle:json.dump(result,handle,indent=2)
    print(json.dumps(result),flush=True)


def main(args):
    scope=json.loads(Path(args.scope).read_text());check_scope(scope)
    syn,helper_path=source_synthesis()
    binding=source_guard(scope,args,helper_path)
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
        require(os.environ.get(name)=='1','single-thread CPU environment required: '+name)
    if args.mode=='run':run(args,scope,binding,syn)
    else:audit(args,scope,binding,syn)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=('run','audit'),required=True)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--scope',type=Path,required=True)
    p.add_argument('--scope-sha256',required=True)
    p.add_argument('--script-sha256',required=True)
    main(p.parse_args())
