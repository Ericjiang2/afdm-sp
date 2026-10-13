"""Registered fresh guarded receiver policies. No truth reads in receive stage."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import os
import signal
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_development import (bindings, write_json, append_json, finite,
                             observed_inputs, branch_payload, assert_same, scientific_output)
POLICIES=('scalar3','guard_coherent','guard_f1','f1_alone')


def reused_coherent(obs,system,code,native,variant,third):
    """Reuse exactly third-round geometry and its original check prior."""
    from physical import Channel
    t=time.perf_counter();result=third['result']
    channel=Channel(len(obs['y']),system.c1,system.c2,
                    [p.delay for p in result.paths],[p.doppler for p in result.paths],result.gains)
    det=variant.scalar_joint(obs['y'],obs['pilot'],channel,obs['sigma2'],
        pd=1-system.rho,prior=third['check_prior'],iterations=20,damping=.3,gain_mode='joint')
    dec=native.decoder_messages(code,np.clip(det['extrinsic'],-20,20),maxiter=50)
    return dict(detector=det,decoder=dec,check_prior=third['check_prior'],
                geometry_reused=True,seconds=time.perf_counter()-t)


def f1_call(obs,system,code,H,native,kernel,branch_fn,receive_f1):
    dec,arrays,timing=receive_f1(obs,system,code)
    acq=dict(timing['acquisition']);ch=acq['channel']
    acq['channel']=dict(n=ch.n,c1=ch.c1,c2=ch.c2,delays=ch.delays,dopplers=ch.dopplers,gains=ch.gains)
    result=dict(decoder=dec,arrays=arrays,timing=dict(timing,acquisition=acq),branch=None)
    if np.count_nonzero((H@dec['decoded'])%2):
        b=branch_fn(obs,system,code,native,kernel,arrays,'CSTATE20')
        result['branch']=branch_payload(b);dec=b['decoder']
    result['final_decoder']=dec
    return result


def generate(reg,regsha,system,code,evidence,sha256,project):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
    from analyze_reopening import observation_hash
    observed=HERE/'frontier_population_observed';truthroot=HERE/'frontier_population_truth'
    observed.mkdir(exist_ok=False);truthroot.mkdir(exist_ok=False)
    for folder,kind in [(observed,'observed'),(truthroot,'truth')]:
        write_json(folder/'manifest.json',dict(registration=reg,registration_sha256=regsha,kind=kind))
    old=[project/'results/tf_cstate_prospective_20260923/population_observed/ledger.jsonl',
         HERE/'confirmation_population_observed/ledger.jsonl']
    seen={json.loads(l)['observation_hash'] for p in old for l in p.read_text().splitlines()}
    entropy=[int(x) for x in np.frombuffer(bytes.fromhex(reg['entropy_hex']),dtype='<u4')]
    for snr in (600,650):
        for frame in range(1024):
            stem=f'j{snr}_f{frame:04d}'
            def words(component):return entropy+[reg['domain'],snr,frame,component]
            def factory(_rep,index,component,*,split):
                if index!=frame or split!=2 or component not in (1,2,3):raise ValueError('unregistered stream')
                return np.random.default_rng(np.random.SeedSequence(words(component)))
            state=np.random.get_state()
            try:raw=make_frame(system,code,0,frame,snr/100,split=2,rng_factory=factory)
            finally:np.random.set_state(state)
            raw,diagnostics=physical_observation(raw,system,prefix_length=system.l_max_cap)
            scale=np.sqrt(2*(1-system.rho))
            obs=dict(y=np.asarray(raw['y'])/scale,pilot=np.asarray(raw['pilot'])/scale,sigma2=float(raw['sigma2'])/scale**2)
            digest=observation_hash(obs)
            if digest in seen:raise ValueError('observation collision, no replacement')
            seen.add(digest)
            streams={name:hashlib.sha256(json.dumps(words(i)).encode()).hexdigest() for name,i in [('channel',1),('message',2),('noise',3)]}
            identity=dict(observation_id=stem,registration_sha256=regsha)
            op=observed/'observed'/f'{stem}.npz';tp=truthroot/'truth'/f'{stem}.npz'
            osh=evidence.save_artifact(op,dict(observation=obs,observation_id=stem,observation_hash=digest,stream_ids=streams),dict(identity,kind='observed'))
            true=dict(coded=np.asarray(raw['coded']),info=np.asarray(raw['info']),l_i=raw['params']['l_i'],k_real=raw['params']['k_real'],g_i=raw['params']['g_i'],observation_hash=digest,stream_ids=streams,diagnostics=diagnostics)
            tsh=evidence.save_artifact(tp,true,dict(identity,kind='truth'))
            coord=dict(observation_id=stem,snr_centi_db=snr,frame=frame,observation_hash=digest,stream_ids=streams)
            append_json(observed/'ledger.jsonl',dict(coord,observation_path=str(op.relative_to(observed)),observation_sha256=osh))
            append_json(truthroot/'ledger.jsonl',dict(coord,truth_path=str(tp.relative_to(truthroot)),truth_sha256=tsh))
            if frame%128==0:print('generated',stem,flush=True)
    for folder,kind in [(observed,'observed'),(truthroot,'truth')]:
        write_json(folder/f'{kind}_seal.json',dict(status='pass',observations=2048,registration_sha256=regsha,
            files={str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file()}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True)
    mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--generate',action='store_true');mode.add_argument('--smoke',action='store_true');mode.add_argument('--block',type=int,choices=range(4))
    a=p.parse_args();project=a.project.resolve()
    source=project/'experiments/sp_afdm_native_joint_reviewed_20260921';baseline=project/'experiments/sp_afdm_frozen_reviewed_20260921'
    sys.path[:0]=[str(project/'experiments'/folder) for folder in ('tf_production_gap_audit_20260922','tf_cstate_validation_20260922','tf_geometry_reopen_20260922','cstate_necessity_stageA_20260928')]+[str(HERE.parent/'theory')]
    from audit_io import attach,load_bound,sha256
    evidence=attach(source,baseline)
    regpath=HERE/'frontier_registration.json';reg=json.loads(regpath.read_text());regsha=sha256(regpath)
    if reg['policies']!=list(POLICIES) or reg['cells']!=[dict(snr_centi_db=s,frames=1024) for s in (600,650)]:raise ValueError('allocation drift')
    for path,digest in reg['task_sources'].items():
        if sha256(HERE.parent/path)!=digest:raise ValueError('task source drift '+path)
    for path,digest in reg['f1_hashes'].items():
        if sha256(project/path)!=digest:raise ValueError('F1 drift '+path)
    locked=bindings(project,source,baseline,evidence,sha256)
    if locked!=json.loads((HERE/'dev_registration.json').read_text())['locked_hashes']:raise ValueError('receiver source drift')
    env=evidence.bind_runtime_environment()
    from receiver import context
    system,_,code,header=context();evidence.verify_runtime_binding()
    if a.generate:generate(reg,regsha,system,code,evidence,sha256,project);return
    import native_twofft as native
    import geometry_validation as kernel
    from native_f1 import receive_f1
    from run_validation import _branch
    from tf_reaction_adapter import load_variant
    variant=load_variant(source/'src/twofft.py',expected_sha256=locked['source_hashes']['src/twofft.py'],mode='coherent')
    H=code['H']
    if H.shape!=(1026,2048):raise ValueError('code dimension')
    syndrome=lambda dec:int(np.count_nonzero((H@dec['decoded'])%2))
    population=project/'results/tf_cstate_prospective_20260923/population_observed' if a.smoke else HERE/'frontier_population_observed'
    inputs=[json.loads(l) for l in (population/'ledger.jsonl').read_text().splitlines()]
    if a.smoke:inputs=[r for r in inputs if r['observation_id'] in ('s650_f0000','s650_f0390','s650_f0415')]
    else:
        q=json.loads((HERE/'frontier_smoke_v1/result.json').read_text())
        if q['status']!='pass' or q['registration_sha256']!=regsha or q['completed_calls']!=12:raise ValueError('qualification absent')
        seal=json.loads((population/'observed_seal.json').read_text())
        if seal['observations']!=2048 or seal['registration_sha256']!=regsha:raise ValueError('population seal')
        for path,digest in seal['files'].items():
            if sha256(population/path)!=digest:raise ValueError('population drift')
        if [(r['snr_centi_db'],r['frame']) for r in inputs]!=[(s,f) for s in (600,650) for f in range(1024)]:raise ValueError('population allocation')
        inputs=inputs[a.block*512:(a.block+1)*512]
    out=HERE/('frontier_smoke_v1' if a.smoke else f'frontier_block{a.block}_v1');out.mkdir(exist_ok=False);(out/'raw').mkdir()
    write_json(out/'manifest.json',dict(registration=reg,registration_sha256=regsha,locked_hashes=locked,environment=env,header=header,
        population=str(population),population_ledger_sha256=sha256(population/'ledger.jsonl'),observation_ids=[r['observation_id'] for r in inputs],policies=POLICIES,smoke=a.smoke,pid=os.getpid(),started_epoch=time.time()))
    def expired(*_):raise TimeoutError('2700s unit limit')
    signal.signal(signal.SIGALRM,expired);signal.alarm(2700);count=0;parity_checks=0
    try:
        for i,row in enumerate(inputs):
            for policy in POLICIES[i%4:]+POLICIES[:i%4]:
                identity=dict(observation_id=row['observation_id'],policy=policy,input_sha256=row['observation_sha256'])
                append_json(out/'attempts.jsonl',dict(identity,event='started',call_index=count));t=time.perf_counter()
                obs=observed_inputs(evidence,load_bound,population,row)
                payload=dict(prefix=None,scalar_branch=None,coherent=None,restart=None)
                if policy=='f1_alone':
                    payload['restart']=f1_call(obs,system,code,H,native,kernel,_branch,receive_f1);dec=payload['restart']['final_decoder']
                else:
                    dec,arrays,timing=native.receive(obs,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')
                    payload['prefix']=dict(decoder=dec,arrays=arrays,timing=timing)
                    if syndrome(dec):
                        third=_branch(obs,system,code,native,kernel,arrays,'CSTATE20');dec=third['decoder'];payload['scalar_branch']=branch_payload(third)
                        if syndrome(dec) and policy in ('guard_coherent','guard_f1'):
                            payload['coherent']=reused_coherent(obs,system,code,native,variant,third);dec=payload['coherent']['decoder']
                    if syndrome(dec) and policy=='guard_f1':
                        payload['restart']=f1_call(obs,system,code,H,native,kernel,_branch,receive_f1);dec=payload['restart']['final_decoder']
                ready=time.perf_counter()-t;payload['final_decoder']=dec;finite(payload)
                path=out/'raw'/f"{row['observation_id']}_{policy}.npz";digest=evidence.save_artifact(path,payload,identity)
                item=dict(identity,status='ok',call_index=count,raw_path=str(path.relative_to(out)),raw_sha256=digest,
                    final_syndrome=syndrome(dec),coherent_executed=payload['coherent'] is not None,restart_executed=payload['restart'] is not None,
                    receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-t)
                append_json(out/'ledger.jsonl',item);append_json(out/'attempts.jsonl',dict(item,event='finished'));count+=1
                if a.smoke and payload['coherent'] is not None:
                    alternate=_branch(obs,system,code,SimpleNamespace(scalar_joint=variant.scalar_joint,decoder_messages=native.decoder_messages),kernel,arrays,'CSTATE20')
                    assert_same(scientific_output(payload['coherent']['decoder']),scientific_output(alternate['decoder']));assert_same(scientific_output(payload['coherent']['detector']),scientific_output(alternate['detector']));parity_checks+=1
            if i%64==0:print('completed',count,flush=True)
        if a.smoke and parity_checks<4:raise ValueError('qualification did not exercise reuse and restart')
        write_json(out/'result.json',dict(status='pass',registration_sha256=regsha,completed_calls=count,parity_checks=parity_checks,
            manifest_sha256=sha256(out/'manifest.json'),ledger_sha256=sha256(out/'ledger.jsonl'),attempts_sha256=sha256(out/'attempts.jsonl'),finished_epoch=time.time()))
    except BaseException as exc:
        write_json(out/'failure.json',dict(status='failed',completed_calls=count,error=repr(exc)));raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
