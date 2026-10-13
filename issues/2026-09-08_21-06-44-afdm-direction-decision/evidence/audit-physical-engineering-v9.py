"""Audit all18 actual full calls; no new fits or terminal replays."""
import hashlib,json,sys,time,signal
from pathlib import Path
import numpy as np
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');src=root/'source-runtime-v9'
sys.path.insert(0,str(src))
from afdm_sp_joint_unrolled.direction_budget import locked,settle_many
from afdm_sp_joint_unrolled.direction_logging import validate_record,validate_pair
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
out=root/'evidence/physical-engineering-audit-v9.json';rid='physical-engineering-audit-v9'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
started=time.perf_counter();cpu=time.process_time();status='failed'
with locked(root/'resource-ledger.json') as ledger:
 assert not any(r['id']==rid for r in ledger['completed']+ledger['reservations'])
 for k,amount in dict(host_seconds=120,gpu_seconds=0,cpu_core_seconds=120).items():assert sum(r[k] for r in ledger['completed']+ledger['reservations'])+amount<=ledger['limits'][k]
 ledger['reservations'].append(dict(id=rid,calls={},host_seconds=120,gpu_seconds=0,cpu_core_seconds=120))
def deadline(*args):raise TimeoutError('engineering audit120sec limit')
signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
try:
 state=json.loads((root/'evidence/physical-engineering-v9-status.json').read_text())
 assert state['status']=='complete' and all(j['exit_code']==0 for j in state['jobs'])
 rows=[];arrays={};bindings=[];jobs={}
 for name,version,count in [('physical-baseline-v8',8,1),('physical-baseline-v9',9,1),('physical-engineering-v9',9,16)]:
  run=root/name;complete=json.loads((run/'complete.json').read_text());contract=json.loads((run/'run-contract.json').read_text())
  source=root/f'source-runtime-v{version}'/'afdm_sp_joint_unrolled'
  actual={str(f.relative_to(source)):sha(f) for f in sorted(source.rglob('*.py'))}
  assert complete['status']=='complete' and complete['calls_attempted']==complete['calls_completed']==count
  assert complete['source_sha256']==actual==contract['source_sha256']
  assert complete['config_sha256']==hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
  assert len(list(run.glob('call-*-started.json')))==len(list(run.glob('call-*-completed.json')))==count
  jobs[name]={'complete_sha256':sha(run/'complete.json'),'wall_seconds':complete['wall_seconds'],'CPU_seconds':complete['CPU_seconds'],'peak_gpu_bytes':complete['peak_gpu_bytes'],'calls':count}
  for path in sorted(run.glob('frame-*.json')):
   assert sha(path)==complete['record_sha256'][str(path)]
   r=json.loads(path.read_text());validate_record(r,deployable=True)
   assert r['source_sha256']==actual and r['device']=='cuda' and r['split']=='engineering' and r['SNR']==8
   assert sha(r['snapshot']['path'])==r['snapshot']['sha256']
   with np.load(r['snapshot']['path'],allow_pickle=False) as z:a={k:z[k] for k in z.files}
   terminal=[g for g in r['graph_edges_each_stage'] if g['stage']=='final_bp'];assert len(terminal)==1
   assert terminal[0]['H_hash']==array_hash(np.asarray(a['Hhat'],dtype=np.complex128))
   assert sum(terminal[0]['row_degrees'])==int(np.count_nonzero(abs(a['Hhat'])>=1e-4))
   assert r['H_cancel_source']['sha256']==r['H_data_source']['sha256']==array_hash(a['Hhat'])
   assert array_hash(a['y'])==r['input_hashes']['y'] and array_hash(a['pilot'])==r['input_hashes']['pilot']
   if name=='physical-engineering-v9':
    d=r['physical_refit'];assert len(a['support'])<=40 and d['truth_access']=='none'
    assert d['H_before_sha256']==array_hash(a['H_before_refit']) and d['H_after_sha256']==array_hash(a['Hhat'])
    assert d['gains_before_sha256']==array_hash(a['gains_before_refit']) and d['gains_after_sha256']==array_hash(a['gains_after_refit'])
    # Independent matrix assembly from tap IDs; no estimation/refitting here.
    H=np.zeros((1024,1024),complex);n=np.arange(1024);c1=5/2048
    # c2 is the actual registered model constant from phase0 receiver contract.
    from afdm_sp_joint_unrolled.loop9_cache_features import _make_config_a
    if 'system' not in locals():system=_make_config_a(1024,2.,8,10.,4.)
    for atom,gain in zip(a['support'],a['gains_after_refit']):
     l=int(atom)//5;k=int(atom)%5-2;m=(n+5*l+k)%1024
     H[m,n]+=gain*np.exp(2j*np.pi*(-c1*l*l+system.c2*(m.astype(float)**2-n.astype(float)**2)-l*n/1024))
    np.testing.assert_allclose(H,a['Hhat'],rtol=1e-12,atol=1e-12)
    residual=float(np.linalg.norm(a['y']-H@(a['pilot']+a['x_soft']))**2)
    assert np.isclose(residual,d['residual_squared'],rtol=1e-10,atol=1e-8)
    if r['arm_id']=='m-group':assert d['converged'] and max(d['overlap_degree'])==1
    else:
     assert len(d['center_atom_ids'])<=8 and d['query_count']==len(d['query_trace'])<=d['query_limit']
     assert all(q['status']=='complete' and q['query']==i+1 for i,q in enumerate(d['query_trace']))
     for init in d['initializations']:
      for sweep in init['sweeps']:
       assert all(c['after']<=c['before'] for c in sweep['coordinates'])
   key=(name,r['block_id'],r['arm_id']);arrays[key]=a;rows.append(r);bindings.append({'path':str(path),'sha256':sha(path),'snapshot':r['snapshot']})
 assert len(rows)==18
 a=arrays[('physical-baseline-v8',22,'sbl-s0.5')];b=arrays[('physical-baseline-v9',22,'sbl-s0.5')]
 assert set(a)==set(b)
 for k in a:np.testing.assert_array_equal(a[k],b[k])
 for block in range(22,26):
  group=[r for r in rows if r['run_id']=='physical-engineering-v9' and r['block_id']==block];assert len(group)==4;validate_pair(group)
  ref=arrays[('physical-engineering-v9',block,'m-group')]
  for r in group:
   z=arrays[(r['run_id'],block,r['arm_id'])]
   for k in ('H_before_refit','gains_before_refit','support','x_soft','sigma2_terminal'):np.testing.assert_array_equal(z[k],ref[k])
   if block==22:
    np.testing.assert_array_equal(z['H_before_refit'],b['Hhat'])
    np.testing.assert_array_equal(z['x_soft'],b['x_soft'])
 cost={}
 for arm in ('m-group','m-param-budget','m-param-reference','m-soft'):
  rs=[r for r in rows if r['arm_id']==arm and r['block_id']!=22];times=[r['elapsed_seconds'] for r in rs]
  cost[arm]={'n':3,'raw':times,'mean':float(np.mean(times)),'p95':float(np.quantile(times,.95)),'queries':[r['physical_refit']['query_count'] for r in rs],'converged':[r['physical_refit']['converged'] for r in rs]}
 result={'status':'passed','records':18,'jobs':jobs,'cost':cost,'baseline_all_snapshot_arrays_bit_exact':True,'baseline_arrays_compared':list(a),'same_parent_state_each_block':True,'single_terminal_graph_and_H_consumption_verified':True,'independent_H_assembly_and_fitted_residual_verified':True,'source_snapshot_sha256':sha(root/'evidence/source-snapshot-runtime-v9.json'),'raw_evidence':bindings,'command':[sys.executable]+sys.argv,'exit_code':0,'scope':'Real18full engineering integration; no new CE/terminal calls; n3 timing is provisional, no FER selection or formal A2 cost gate.'}
 out.write_text(json.dumps(result,indent=2)+'\n');status='complete'
 print(json.dumps({k:v for k,v in result.items() if k!='raw_evidence'}))
finally:
 settle_many(root/'resource-ledger.json',rid,calls={},resources=dict(host_seconds=time.perf_counter()-started,cpu_core_seconds=time.process_time()-cpu,gpu_seconds=0),evidence=str(out),status=status)
