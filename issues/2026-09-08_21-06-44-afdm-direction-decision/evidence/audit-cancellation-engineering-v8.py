"""Audit actual engineering records; no confirmation or design FER selection."""
import hashlib,json,sys,time
from pathlib import Path
import numpy as np
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908')
src=root/'source-runtime-v8';sys.path.insert(0,str(src))
from afdm_sp_joint_unrolled.direction_budget import locked,settle_many
from afdm_sp_joint_unrolled.direction_data import source_manifest
from afdm_sp_joint_unrolled.direction_logging import validate_record,validate_pair
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
run=root/'cancel-engineering-v8';out=root/'evidence/cancellation-engineering-audit-v8.json'
started=time.perf_counter();cpu=time.process_time();rid='cancellation-engineering-audit-v8'
with locked(root/'resource-ledger.json') as ledger:
 assert not any(x['id']==rid for x in ledger['completed']+ledger['reservations'])
 for k,amount in dict(host_seconds=120,gpu_seconds=0,cpu_core_seconds=120).items():assert amount+sum(x[k] for x in ledger['completed']+ledger['reservations'])<=ledger['limits'][k]
 ledger['reservations'].append(dict(id=rid,calls={},host_seconds=120,gpu_seconds=0,cpu_core_seconds=120))
status='failed'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
try:
 complete=json.loads((run/'complete.json').read_text());contract=json.loads((run/'run-contract.json').read_text())
 assert complete['status']=='complete' and complete['calls_attempted']==complete['calls_completed']==20
 assert (root/'evidence/cancel-engineering-v8.exit').read_text().strip()=='0'
 assert complete['source_sha256']==source_manifest()==contract['source_sha256']
 assert complete['config_sha256']==hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
 assert len(list(run.glob('call-*-started.json')))==len(list(run.glob('call-*-completed.json')))==20
 rows=[];max_transform_error=0.;bound=[]
 for path in sorted(run.glob('frame-*.json')):
  assert sha(path)==complete['record_sha256'][str(path)]
  row=json.loads(path.read_text());validate_record(row,deployable=True)
  assert row['split']=='engineering' and row['SNR']==8 and row['block_id'] in range(17,22)
  assert row['source_sha256']==complete['source_sha256'] and row['device']=='cuda'
  assert sha(row['snapshot']['path'])==row['snapshot']['sha256']
  with np.load(row['snapshot']['path'],allow_pickle=False) as f:a={k:f[k] for k in f.files}
  assert row['input_hashes']['y']==array_hash(a['y']) and row['input_hashes']['pilot']==array_hash(a['pilot'])
  terminal=[g for g in row['graph_edges_each_stage'] if g['stage']=='final_bp'];assert len(terminal)==1
  if row['arm_id'].startswith('cancel-'):
   H,z,B=a['Hhat'],a['y']-a['Hhat']@a['pilot'],a['cancellation_B'];sigma=float(a['sigma2_terminal_base'])
   mode=row['arm_id'][7:];d=np.sum(abs(B)**2,axis=1)
   if mode=='scalar':expected_H,expected_z,expected_sigma=H,z,sigma+float(d.mean())
   elif mode=='diagonal':
    w=np.sqrt(sigma/(sigma+d));expected_H,expected_z,expected_sigma=w[:,None]*H,w*z,sigma
   else:
    # Independent eigendecomposition of BHB instead of implementation's thin SVD.
    eigen,V=np.linalg.eigh(B.conj().T@B);keep=eigen>1e-14*max(1.,float(eigen.max()))
    U=B@V[:,keep]/np.sqrt(eigen[keep]);q=1/np.sqrt(1+eigen[keep]/sigma)-1
    expected_H=H+U@(q[:,None]*(U.conj().T@H));expected_z=z+U@(q*(U.conj().T@z));expected_sigma=sigma
   err=max(np.linalg.norm(a['detector_H']-expected_H)/max(1.,np.linalg.norm(expected_H)),np.linalg.norm(a['detector_z']-expected_z)/max(1.,np.linalg.norm(expected_z)))
   assert err<1e-10 and np.isclose(float(a['sigma2_terminal']),expected_sigma,rtol=1e-12,atol=0)
   max_transform_error=max(max_transform_error,float(err))
   for k,rk in [('detector_H','detector_H_sha256'),('detector_z','detector_z_sha256'),('cancellation_B','cancellation_B_sha256')]:assert array_hash(a[k])==row[rk]
   graph_H=a['detector_H']
  else:graph_H=a['Hhat']
  assert sum(terminal[0]['row_degrees'])==int(np.count_nonzero(abs(graph_H)>=1e-4))
  assert terminal[0]['H_hash']==array_hash(np.asarray(graph_H,dtype=np.complex128))
  rows.append(row);bound.append(dict(path=str(path),sha256=sha(path),snapshot=row['snapshot']))
 assert len(rows)==20
 for block in range(17,22):validate_pair([r for r in rows if r['block_id']==block])
 cost={}
 for arm in sorted({r['arm_id'] for r in rows}):
  r=[x for x in rows if x['arm_id']==arm and x['block_id']!=17];assert len(r)==4
  t=[x['elapsed_seconds'] for x in r]
  cost[arm]=dict(mean=float(np.mean(t)),p95=float(np.quantile(t,.95)),n=4,raw=t,terminal_edges=[sum(x['graph_edges_each_stage'][-1]['row_degrees']) for x in r])
 result=dict(status='passed',records=20,source_sha256=source_manifest(),config_sha256=complete['config_sha256'],complete=dict(path=str(run/'complete.json'),sha256=sha(run/'complete.json')),cost=cost,max_independent_transform_relative_error=max_transform_error,peak_gpu_bytes=complete['peak_gpu_bytes'],actual_full_job_wall_seconds=complete['wall_seconds'],records_audited=bound,scope='Actual N1024 full receiver/BP/LDPC integration and diagnostic engineering cost. Warmup17 excluded; n4 per arm; no final A2 cost claim; no FER selection.',command=[sys.executable]+sys.argv)
 out.write_text(json.dumps(result,indent=2)+'\n');status='complete'
 print(json.dumps({k:v for k,v in result.items() if k not in ('records_audited','source_sha256')}))
finally:
 settle_many(root/'resource-ledger.json',rid,calls={},resources=dict(host_seconds=time.perf_counter()-started,cpu_core_seconds=time.process_time()-cpu,gpu_seconds=0),evidence=str(out),status=status)
