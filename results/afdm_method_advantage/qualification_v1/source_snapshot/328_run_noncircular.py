"""Old enriched cohort: guarded fixed-channel proper/widely-linear reference."""
from pathlib import Path
import argparse,json,os,sys,time
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_development import bindings,write_json,append_json,observed_inputs,branch_payload,finite
POLICIES=('scalar3','proper','augmented')


def main():
 p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--smoke',action='store_true');args=p.parse_args();project=args.project.resolve()
 sys.path[:0]=[str(project/'experiments'/x) for x in ('tf_production_gap_audit_20260922','tf_cstate_validation_20260922','tf_geometry_reopen_20260922')]+[str(HERE.parent/'theory')]
 from audit_io import attach,load_bound,sha256
 source=project/'experiments/sp_afdm_native_joint_reviewed_20260921';base=project/'experiments/sp_afdm_frozen_reviewed_20260921'
 evidence=attach(source,base);regpath=HERE/'noncircular_registration.json';reg=json.loads(regpath.read_text());regsha=sha256(regpath)
 for path,digest in reg['task_sources'].items():
  if sha256(HERE.parent/path)!=digest:raise ValueError('source drift')
 locked=bindings(project,source,base,evidence,sha256)
 if locked!=json.loads((HERE/'dev_registration.json').read_text())['locked_hashes']:raise ValueError('frozen receiver drift')
 env=evidence.bind_runtime_environment()
 from receiver import context
 from physical import Channel
 import native_twofft as native
 import geometry_validation as kernel
 from run_validation import _branch
 from noncircular_siso import siso,channel_matrix
 system,_,code,header=context();evidence.verify_runtime_binding();H=code['H']
 syndrome=lambda d:int(np.count_nonzero((H@d['decoded'])%2))
 population=project/'results/tf_cstate_prospective_20260923/population_observed'
 inputs={r['observation_id']:r for r in map(json.loads,(population/'ledger.jsonl').read_text().splitlines())}
 ids=['s650_f0000','s650_f0415'] if args.smoke else reg['observation_ids']
 if reg['policies']!=list(POLICIES) or len(reg['observation_ids'])!=128:raise ValueError('allocation drift')
 if not args.smoke:
  q=json.loads((HERE/'noncircular_smoke_v1/result.json').read_text())
  if q['status']!='pass' or q['completed_calls']!=6 or q['registration_sha256']!=regsha:raise ValueError('qualification missing')
 out=HERE/('noncircular_smoke_v1' if args.smoke else 'noncircular_dev_v1');out.mkdir(exist_ok=False);(out/'raw').mkdir()
 write_json(out/'manifest.json',dict(registration=reg,registration_sha256=regsha,locked_hashes=locked,environment=env,header=header,observations=ids,policies=POLICIES,started_epoch=time.time(),smoke=args.smoke))
 start=time.perf_counter();count=0;matrix_checks=0
 try:
  for i,stem in enumerate(ids):
   for policy in POLICIES[i%3:]+POLICIES[:i%3]:
    if time.perf_counter()-start>2700:raise TimeoutError('2700s unit')
    identity=dict(observation_id=stem,policy=policy,input_sha256=inputs[stem]['observation_sha256']);append_json(out/'attempts.jsonl',dict(identity,event='started',call_index=count));t=time.perf_counter()
    obs=observed_inputs(evidence,load_bound,population,inputs[stem]);dec,arrays,timing=native.receive(obs,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint')
    payload=dict(prefix_decoder=dec,prefix_arrays=arrays,native_timing=timing,scalar_branch=None,siso=None)
    if syndrome(dec):
     third=_branch(obs,system,code,native,kernel,arrays,'CSTATE20');payload['scalar_branch']=branch_payload(third);dec=third['decoder']
     if syndrome(dec) and policy!='scalar3':
      t0=time.perf_counter();r=third['result'];channel=Channel(len(obs['y']),system.c1,system.c2,[p.delay for p in r.paths],[p.doppler for p in r.paths],r.gains)
      A=channel_matrix(channel);matrix_seconds=time.perf_counter()-t0;t1=time.perf_counter()
      detector=siso(obs['y'],obs['pilot'],A,obs['sigma2'],third['check_prior'],1-system.rho,policy)
      detector_seconds=time.perf_counter()-t1;dec=native.decoder_messages(code,np.clip(detector['extrinsic'],-20,20),maxiter=50)
      payload['siso']=dict(detector=detector,decoder=dec,matrix_seconds=matrix_seconds,detector_seconds=detector_seconds,check_prior=third['check_prior'])
    payload['final_decoder']=dec;ready=time.perf_counter()-t;finite(payload)
    raw=out/'raw'/f'{stem}_{policy}.npz';digest=evidence.save_artifact(raw,payload,identity)
    row=dict(identity,status='ok',call_index=count,raw_path=str(raw.relative_to(out)),raw_sha256=digest,final_syndrome=syndrome(dec),siso_executed=payload['siso'] is not None,receiver_ready_seconds=ready,complete_seconds=time.perf_counter()-t)
    append_json(out/'ledger.jsonl',row);append_json(out/'attempts.jsonl',dict(row,event='finished'));count+=1
    if args.smoke and payload['siso'] is not None:
     x=np.exp(1j*np.arange(channel.n)*.314)
     np.testing.assert_allclose(A@x,channel.apply(x),rtol=2e-10,atol=2e-10)
     rng=np.random.default_rng(1927);x=rng.normal(size=channel.n)+1j*rng.normal(size=channel.n)
     np.testing.assert_allclose(A@x,channel.apply(x),rtol=2e-10,atol=2e-10)
     for k in (0,17,511,1023):
      x=np.zeros(channel.n,complex);x[k]=1
      np.testing.assert_allclose(A[:,k],channel.apply(x),rtol=2e-10,atol=2e-10)
     matrix_checks+=1
   if i%16==0:print('completed',count,flush=True)
  if args.smoke and matrix_checks!=2:raise ValueError('matrix qualification did not run')
  write_json(out/'result.json',dict(status='pass',registration_sha256=regsha,completed_calls=count,matrix_checks=matrix_checks,manifest_sha256=sha256(out/'manifest.json'),ledger_sha256=sha256(out/'ledger.jsonl'),attempts_sha256=sha256(out/'attempts.jsonl'),finished_epoch=time.time()))
 except BaseException as exc:write_json(out/'failure.json',dict(status='failed',completed_calls=count,error=repr(exc)));raise

if __name__=='__main__':main()
