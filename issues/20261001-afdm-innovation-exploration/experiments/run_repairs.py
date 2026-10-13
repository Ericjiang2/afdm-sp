"""Observed-only conditional local, near-cluster, and F1 restart repairs."""
from pathlib import Path
from types import SimpleNamespace
from dataclasses import asdict
import argparse
import json
import os
import sys
import time
import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_development import (write_json,append_json,finite,observed_inputs,branch_payload,bindings)

POLICIES=('coherent3','local4','pair4','f1_restart')


def pair_kernel(kernel):
    def reopen(Y,x,v,paths,**kwargs):
        from physical import daft
        start=time.perf_counter();xt=daft(x,kwargs['c1'],kwargs['c2'],True)
        base=kernel._system(Y,xt,v,paths,kwargs['c1'],kwargs['c2'],kwargs['ridge'])
        initial=float(base[4]);best=initial;chosen=list(paths);tests=0;winner=None
        for anchor in range(len(paths)):
            for slot in range(len(paths)):
                if slot==anchor:continue
                for delta in (-.125,-.0625,.0625,.125):
                    nu=paths[anchor].doppler+delta
                    if not kwargs['doppler_min']<=nu<=kwargs['doppler_max']:continue
                    candidate=kernel.Path(paths[anchor].delay,nu)
                    if kernel._duplicate(candidate,paths[:slot]+paths[slot+1:],kwargs['duplicate_tolerance']):continue
                    trial=list(paths);trial[slot]=candidate
                    value=float(kernel._system(Y,xt,v,trial,kwargs['c1'],kwargs['c2'],kwargs['ridge'])[4]);tests+=1
                    if kernel._improvement(best,value):
                        best=value;chosen=trial;winner=dict(anchor=anchor,slot=slot,offset=delta)
        extra=time.perf_counter()-start
        options=dict(kwargs,max_edits=0)
        result=kernel.reopen_geometry(Y,x,v,chosen,**options)
        timing=result.diagnostics['stage_timing']
        timing['exclusive_seconds']['structural_scoring']+=extra
        timing['total_seconds']+=extra
        result.elapsed_seconds+=extra
        result.evaluations['pair_bank_system_evaluations']=tests+1
        result.diagnostics['near_cluster_bank']=dict(candidate_tests=tests,winner=winner,
            incumbent_objective=initial,selected_objective=best,seconds=extra,
            scope='same P and physical operators; fine candidate bank then original LOCAL; not new Taylor basis')
        return result
    return SimpleNamespace(Path=kernel.Path,reopen_geometry=reopen)


def continuation_arrays(branch):
    decoder=branch['decoder'];result=branch['result']
    return dict(r1_app=decoder['raw_app'],r1_check=decoder['raw_check_extrinsic'],
        r1_delays=np.array([p.delay for p in result.paths]),
        r1_dopplers=np.array([p.doppler for p in result.paths]),
        r1_gains=branch['detector']['gains'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args();project=args.project.resolve()
    source=project/'experiments/sp_afdm_native_joint_reviewed_20260921'
    baseline=project/'experiments/sp_afdm_frozen_reviewed_20260921'
    sys.path[:0]=[str(project/'experiments/tf_production_gap_audit_20260922'),
        str(project/'experiments/tf_cstate_validation_20260922'),
        str(project/'experiments/cstate_necessity_stageA_20260928'),str(HERE.parent/'theory')]
    from audit_io import attach,load_bound,sha256
    evidence=attach(source,baseline)
    from receiver import context
    from native_f1 import receive_f1
    from tf_reaction_adapter import load_variant
    import native_twofft as native
    import geometry_validation as kernel
    from run_validation import _branch
    reg=json.loads((HERE/'repairs_registration.json').read_text())
    if reg['runner_sha256']!=sha256(Path(__file__)):raise ValueError('repair runner drift')
    for name,digest in reg['f1_hashes'].items():
        if sha256(project/name)!=digest:raise ValueError('F1 source drift')
    lock=bindings(project,source,baseline,evidence,sha256)
    if lock!=json.loads((HERE/'dev_registration.json').read_text())['locked_hashes']:raise ValueError('base source drift')
    env=evidence.bind_runtime_environment();system,_,code,header=context();evidence.verify_runtime_binding()
    with np.load(baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz') as z:H=z['H']
    def syndrome(decoder):return int(np.count_nonzero((H@decoder['decoded'])%2))
    variant=load_variant(source/'src/twofft.py',expected_sha256=lock['source_hashes']['src/twofft.py'],mode='coherent')
    coherent=SimpleNamespace(scalar_joint=variant.scalar_joint,decoder_messages=native.decoder_messages)
    population=project/'results/tf_cstate_prospective_20260923/population_observed'
    inputs={r['observation_id']:r for r in map(json.loads,(population/'ledger.jsonl').read_text().splitlines())}
    ids=['s650_f0415'] if args.smoke else reg['observation_ids']
    if reg['policies']!=list(POLICIES) or len(reg['observation_ids'])!=128:raise ValueError('repair allocation drift')
    if not args.smoke:
        qualification=HERE/reg['qualification_directory']
        passed=json.loads((qualification/'result.json').read_text())
        qmanifest=json.loads((qualification/'manifest.json').read_text())
        if (passed['status']!='pass' or passed['completed_calls']!=4 or
                qmanifest['registration_sha256']!=sha256(HERE/'repairs_registration.json')):
            raise ValueError('repair qualification missing or source changed')
        if sha256(qualification/'ledger.jsonl')!=passed['ledger_sha256']:raise ValueError('qualification ledger hash')
        qrows=[json.loads(line) for line in (qualification/'ledger.jsonl').read_text().splitlines()]
        prefix=None
        for row in qrows:
            raw=load_bound(evidence,qualification/row['raw_path'],row['raw_sha256'])
            if not row['repair_trigger']:raise ValueError('qualification failed to exercise repair')
            if prefix is None:prefix=raw['prefix_arrays']
            else:
                from run_development import assert_same
                assert_same(prefix,raw['prefix_arrays'])
            if row['policy']=='coherent3':
                oldrows=[json.loads(line) for line in (HERE/'development_v1/ledger.jsonl').read_text().splitlines()]
                old=next(r for r in oldrows if r['observation_id']=='s650_f0415' and r['arm']=='coherent')
                oldraw=load_bound(evidence,HERE/'development_v1'/old['raw_path'],old['raw_sha256'])
                if not np.array_equal(raw['final_decoder']['incoming_llr'],oldraw['final_decoder']['incoming_llr']):
                    raise ValueError('repair reference differs from frozen coherent development')
    out=args.out;out.mkdir(exist_ok=False,parents=True);(out/'raw').mkdir()
    write_json(out/'manifest.json',dict(registration=reg,registration_sha256=sha256(HERE/'repairs_registration.json'),
        locked_hashes=lock,environment=env,header=header,pid=os.getpid(),argv=sys.argv,
        started_epoch=time.time(),smoke=args.smoke,observations=ids,policies=POLICIES,
        claim='exposed developmental full receiver policies; no truth enters; no population FER'))
    began=time.perf_counter();count=0
    for i,stem in enumerate(ids):
        for policy in POLICIES[i%4:]+POLICIES[:i%4]:
            if time.perf_counter()-began>2700:raise TimeoutError('repair unit2700s')
            origin=time.perf_counter();identity=dict(observation_id=stem,policy=policy,input_sha256=inputs[stem]['observation_sha256'])
            append_json(out/'attempts.jsonl',dict(identity,event='started',call_index=count))
            try:
                obs=observed_inputs(evidence,load_bound,population,inputs[stem])
                dec,arrays,timing=native.receive(obs,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')
                payload=dict(prefix_decoder=dec,prefix_arrays=arrays,native_timing=timing,branches=[],restart=None)
                before=syndrome(dec);repair_trigger=False
                if before:
                    third=_branch(obs,system,code,coherent,kernel,arrays,'CSTATE20')
                    payload['branches'].append(branch_payload(third));dec=third['decoder'];repair_trigger=bool(syndrome(dec))
                    if repair_trigger and policy in ('local4','pair4'):
                        selected=pair_kernel(kernel) if policy=='pair4' else kernel
                        fourth=_branch(obs,system,code,coherent,selected,continuation_arrays(third),'LOCAL20')
                        payload['branches'].append(branch_payload(fourth));dec=fourth['decoder']
                    if repair_trigger and policy=='f1_restart':
                        dec,farrays,ftime=receive_f1(obs,system,code)
                        acquisition=dict(ftime['acquisition'])
                        channel=acquisition['channel']
                        acquisition['channel']=dict(representation='physical_Channel_parameters',
                            n=channel.n,c1=channel.c1,c2=channel.c2,delays=channel.delays,
                            dopplers=channel.dopplers,gains=channel.gains)
                        ftime=dict(ftime,acquisition=acquisition)
                        payload['restart']=dict(decoder=dec,arrays=farrays,timing=ftime)
                        if syndrome(dec):
                            final=_branch(obs,system,code,native,kernel,farrays,'CSTATE20')
                            payload['branches'].append(branch_payload(final));dec=final['decoder']
                ready=time.perf_counter()-origin;payload['final_decoder']=dec;finite(payload)
                path=out/'raw'/f'{stem}_{policy}.npz';digest=evidence.save_artifact(path,payload,identity)
                row=dict(identity,status='ok',call_index=count,raw_path=str(path.relative_to(out)),raw_sha256=digest,
                    native_syndrome=before,repair_trigger=repair_trigger,final_syndrome=syndrome(dec),
                    branch_count=len(payload['branches']),restart_executed=payload['restart'] is not None,
                    receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-origin)
                append_json(out/'ledger.jsonl',row);append_json(out/'attempts.jsonl',dict(row,event='finished'))
                count+=1
            except BaseException as exc:
                append_json(out/'attempts.jsonl',dict(identity,event='failed',call_index=count,error=repr(exc),seconds=time.perf_counter()-origin));raise
        if i%16==0:print('completed',count,flush=True)
    write_json(out/'result.json',dict(status='pass',completed_calls=count,finished_epoch=time.time(),
        manifest_sha256=sha256(out/'manifest.json'),ledger_sha256=sha256(out/'ledger.jsonl'),
        attempts_sha256=sha256(out/'attempts.jsonl')))


if __name__=='__main__':main()
