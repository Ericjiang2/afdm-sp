"""Fresh population generation and observed-only receiving in separate processes."""
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
from run_development import (bindings, run_call, write_json, append_json,
                             verify_qualification, SCHEMA)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--registration',type=Path,default=HERE/'confirmation_registration.json')
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--receive',action='store_true')
    args=parser.parse_args()
    if args.generate == args.receive:raise ValueError('select exactly one process stage')
    project=args.project.resolve(); task=HERE.parent
    source=project/'experiments/sp_afdm_native_joint_reviewed_20260921'
    baseline=project/'experiments/sp_afdm_frozen_reviewed_20260921'
    sys.path[:0]=[str(project/'experiments/tf_production_gap_audit_20260922'),
                  str(project/'experiments/tf_cstate_validation_20260922'),
                  str(project/'experiments/tf_geometry_reopen_20260922'),str(task/'theory')]
    from audit_io import attach,load_bound,sha256
    evidence=attach(source,baseline)
    reg=json.loads(args.registration.read_text()); regsha=sha256(args.registration)
    if reg['source_sha256_pending'] or reg['runner_sha256']!=sha256(Path(__file__)):
        raise ValueError('confirmation source not locked')
    devreg=HERE/'dev_registration.json'
    if sha256(devreg)!=reg['dev_registration_sha256']:raise ValueError('development binding changed')
    locked=bindings(project,source,baseline,evidence,sha256)
    if locked!=json.loads(devreg.read_text())['locked_hashes']:raise ValueError('receiver source drift')
    qualified=verify_qualification(HERE/'qualify_v1',locked,sha256(devreg),sha256)
    from receiver import context
    env=evidence.bind_runtime_environment(); setup=time.perf_counter()
    system,_,code,header=context(); evidence.verify_runtime_binding()
    setup=time.perf_counter()-setup
    allocation=[(c['snr_centi_db'],f) for c in reg['cells'] for f in range(c['frames'])]
    if len(allocation)!=512 or reg['arms']!=['scalar','coherent','full']:
        raise ValueError('initial confirmation allocation differs')
    observed=HERE/'confirmation_population_observed'
    truthroot=HERE/'confirmation_population_truth'
    common=dict(registration_sha256=regsha,registration=reg,environment=env,header=header,
                setup_seconds=setup,pid=os.getpid(),argv=sys.argv,started_epoch=time.time(),
                locked_hashes=locked,qualification_sha256=qualified)
    if args.generate:
        observed.mkdir(exist_ok=False);truthroot.mkdir(exist_ok=False)
        write_json(observed/'manifest.json',dict(common,kind='observed'))
        write_json(truthroot/'manifest.json',dict(common,kind='truth'))
        from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
        from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
        from analyze_reopening import observation_hash
        old=project/'results/tf_cstate_prospective_20260923/population_observed/ledger.jsonl'
        seen={json.loads(line)['observation_hash'] for line in old.read_text().splitlines()}
        entropy=list(np.frombuffer(bytes.fromhex(reg['entropy_hex']),dtype='<u4').astype(int))
        for snr,frame in allocation:
            stem=f'i{snr}_f{frame:04d}'
            def words(component):return entropy+[reg['domain'],snr,frame,component]
            def factory(_rep,index,component,*,split):
                if index!=frame or split!=2 or component not in (1,2,3):raise ValueError('unregistered stream')
                return np.random.default_rng(np.random.SeedSequence(words(component)))
            rngstate=np.random.get_state()
            try:raw=make_frame(system,code,0,frame,snr/100,split=2,rng_factory=factory)
            finally:np.random.set_state(rngstate)
            raw,diagnostics=physical_observation(raw,system,prefix_length=system.l_max_cap)
            scale=np.sqrt(2*(1-system.rho))
            obs=dict(y=np.asarray(raw['y'])/scale,pilot=np.asarray(raw['pilot'])/scale,
                     sigma2=float(raw['sigma2'])/scale**2)
            digest=observation_hash(obs)
            if digest in seen:raise ValueError('new observation hash collision; no resampling')
            seen.add(digest)
            streams={name:hashlib.sha256(json.dumps([int(x) for x in words(i)]).encode()).hexdigest()
                     for name,i in [('channel',1),('message',2),('noise',3)]}
            identity=dict(kind='observed',observation_id=stem,registration_sha256=regsha)
            obsfile=observed/'observed'/f'{stem}.npz'
            obs_sha=evidence.save_artifact(obsfile,dict(observation=obs,observation_id=stem,
                observation_hash=digest,stream_ids=streams),identity)
            true=dict(coded=np.asarray(raw['coded']),info=np.asarray(raw['info']),
                      l_i=np.asarray(raw['params']['l_i']),k_real=np.asarray(raw['params']['k_real']),
                      g_i=np.asarray(raw['params']['g_i']),observation_hash=digest,stream_ids=streams,
                      diagnostics=diagnostics)
            truefile=truthroot/'truth'/f'{stem}.npz'
            true_sha=evidence.save_artifact(truefile,true,dict(identity,kind='truth'))
            coords=dict(observation_id=stem,snr_centi_db=snr,frame=frame,observation_hash=digest,stream_ids=streams)
            append_json(observed/'ledger.jsonl',dict(coords,observation_path=str(obsfile.relative_to(observed)),observation_sha256=obs_sha))
            append_json(truthroot/'ledger.jsonl',dict(coords,truth_path=str(truefile.relative_to(truthroot)),truth_sha256=true_sha))
            if frame%32==0:print('generated',stem,flush=True)
        for folder,name in [(observed,'observed_seal.json'),(truthroot,'truth_seal.json')]:
            files={str(p.relative_to(folder)):sha256(p) for p in folder.rglob('*') if p.is_file()}
            write_json(folder/name,dict(status='pass',observations=512,files=files,registration_sha256=regsha))
        return
    # Receiving has no truth-root reads.
    seal=json.loads((observed/'observed_seal.json').read_text())
    if seal['status']!='pass' or seal['registration_sha256']!=regsha:raise ValueError('new population unsealed')
    for name,digest in seal['files'].items():
        if sha256(observed/name)!=digest:raise ValueError('new population hash changed')
    inputs=[json.loads(line) for line in (observed/'ledger.jsonl').read_text().splitlines()]
    if [(r['snr_centi_db'],r['frame']) for r in inputs]!=allocation:raise ValueError('new allocation differs')
    import native_twofft as native
    import geometry_validation as kernel
    from run_validation import _branch
    from tf_reaction_adapter import load_variant
    variants={arm:load_variant(source/'src/twofft.py',expected_sha256=locked['source_hashes']['src/twofft.py'],mode=arm)
              for arm in ('coherent','full')}
    cache=baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz'
    with np.load(cache) as z:H=z['H']
    out=HERE/'confirmation_v1';out.mkdir(exist_ok=False)
    (out/'raw').mkdir();(out/'checkpoints').mkdir()
    calls=[(r['observation_id'],arm) for i,r in enumerate(inputs)
           for arm in reg['arms'][i%3:]+reg['arms'][:i%3]]
    write_json(out/'manifest.json',dict(common,planned_calls=calls,population_ledger_sha256=sha256(observed/'ledger.jsonl'),
        population_path=str(observed),truth_policy='no truth opened',context_header=header,
        timing='same instrumented full-chain boundary as development; equal iterations, not wall-clock budgets'))
    def expired(*_):raise TimeoutError('confirmation unit2700s deadline')
    signal.signal(signal.SIGALRM,expired);signal.alarm(2700)
    count=0
    try:
        for i,row in enumerate(inputs):
            for arm in reg['arms'][i%3:]+reg['arms'][:i%3]:
                run_call(row['observation_id'],arm,count,row,out=out,population=observed,
                    evidence=evidence,load_bound=load_bound,system=system,code=code,H=H,
                    native=native,variants=variants,kernel=kernel,branch_fn=_branch)
                count+=1
            if i%32==0:print('received',count,'/',len(calls),flush=True)
        write_json(out/'result.json',dict(status='pass',completed_calls=count,mode='fresh_confirmation',
            manifest_sha256=sha256(out/'manifest.json'),ledger_sha256=sha256(out/'ledger.jsonl'),
            allcalls_sha256=sha256(out/'allcalls.jsonl'),finished_epoch=time.time()))
    except BaseException as exc:
        write_json(out/'failure.json',dict(status='failed',error=repr(exc),completed_calls=count));raise
    finally:signal.alarm(0)


if __name__=='__main__':main()
