"""Frozen anchor analysis; evaluator-only, no fits, receiver calls or adaptive tuning."""
import hashlib,importlib.util,json,signal,sys,time
from pathlib import Path
import numpy as np
ROOT=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908')
sys.path.insert(0,str(ROOT/'source-runtime-v10'))
from afdm_sp_joint_unrolled.direction_select import read,load_run,indexed,paired_interval
from afdm_sp_joint_unrolled.direction_budget import locked,settle_many
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def source(version):
 p=ROOT/('source-runtime-'+version)/'afdm_sp_joint_unrolled'
 return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*.py'))}

def analyze():
 ev=ROOT/'evidence'; prereg,prereg_sha=read(ev/'physical-development-preregister.json')
 admission,admission_sha=read(ev/'physical-development-admission-v10.json')
 assert admission_sha=='8f5f2490683bd5b9f33fe65957b2d50d5fe29d1bc6c1a1609180cb9904e49a48'
 assert prereg_sha==admission['preregister']['sha256']
 contract,_=read(ROOT/'physical-design-v10/run-contract.json')
 assert contract['physical_admission_sha256']==admission_sha and contract['physical_admission']==admission
 assert contract['physical_registry_sha256']==prereg['algorithm_sha256']
 assert contract['source_sha256']==admission['source_sha256']
 assert sha(ev/'physical-engineering-audit-v9-v3.json')==prereg['engineering_audit_sha256']==admission['engineering_audit']['sha256']
 assert sha(ev/'b-star-selection-v1.json')==admission['baseline_selection']['sha256']

 spec=importlib.util.spec_from_file_location('prior_snapshot_audit',ev/'analyze-cancellation-design-v8.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 protocol,phash=read(ROOT/'source-runtime-v10/issues/2026-09-08_21-06-44-afdm-direction-decision/evidence/campaign-protocol.json')
 assert phash==prereg['protocol_sha256']
 old={r['id']:r for r in protocol['design']['recipes']}
 new={arm:dict(id=arm,family='sbl',parameter=.001,terminal_scale=.5,physical_arm=arm) for arm in prereg['new_arms']}
 rows=[];provenance=[];bindings=[]
 for name,recipes,version in [('design-000-096-v4',old,'v4'),('design-096-192-v4',old,'v4'),('physical-design-v10',new,'v10')]:
  chunk,binding=load_run(ROOT/name,phash,recipes,'design')
  assert binding['source_sha256']==source(version)
  rows.extend(chunk);provenance.append(binding)
  for r in chunk:
   if r['arm_id'] not in new and r['arm_id']!='sbl-s0.5':continue
   verified=helper.audit_snapshot(r)
   if r['arm_id'] in new:
    d=r['physical_refit'];assert d['truth_access']=='none' and len(d['support'])<=40
    assert d['H_after_sha256']==verified['graph_H_sha256']
    with np.load(r['snapshot']['path'],allow_pickle=False) as z:
     assert array_hash(z['H_before_refit'].astype(np.complex128))==d['H_before_sha256']
     assert array_hash(z['gains_before_refit'].astype(np.complex128))==d['gains_before_sha256']
     assert array_hash(z['gains_after_refit'])==d['gains_after_sha256']
    if r['arm_id']=='m-group':assert d['converged']
    else:
     assert d['query_count']==len(d['query_trace'])<=d['query_limit'] and len(d['center_atom_ids'])<=8
     assert all(q['status']=='complete' for q in d['query_trace'])
   bindings.append(dict(block=r['block_id'],arm=r['arm_id'],**verified))
 assert len(rows)==2304 and len(bindings)==960
 table=indexed(rows,{**old,**new},range(192),'physical anchor')
 for b in range(192):
  common=table[b,'m-group']['physical_refit']
  for arm in new:
   d=table[b,arm]['physical_refit']
   for k in ('H_before_sha256','gains_before_sha256','support','A_sha256'):assert d[k]==common[k]
  soft=table[b,'m-soft']['physical_refit'];hard=table[b,'m-param-budget']['physical_refit']
  assert soft['locations']==hard['locations'] and soft['query_count']==hard['query_count']
 events={arm:[table[b,arm]['FER'] for b in range(192)] for arm in (*old,*new)}
 assert sum(events['sbl-s0.5'])==31
 pairs=[('sbl-s0.5','m-soft'),('m-group','m-soft'),('m-param-budget','m-soft'),('m-param-reference','m-soft'),('sbl-s0.5','m-group'),('sbl-s0.5','m-param-budget')]
 contrasts={a+'__minus__'+b:paired_interval(events[a],events[b],6) for a,b in pairs}
 engineering=read(ev/'physical-engineering-audit-v9-v3.json')[0]; old_cost=read(ev/'b-star-selection-v1.json')[0]['metrics']
 metrics={}
 for arm in events:
  rs=[table[b,arm] for b in range(192)]; err=sum(events[arm]); ref=31/192
  times=engineering['cost'][arm]['raw'] if arm in new else old_cost[arm]['timing_raw_seconds']
  metrics[arm]={'frame_errors':err,'n':192,'FER':err/192,'delta_vs_Bstar':ref-err/192,
   'relative_FER_reduction_vs_Bstar':(ref-err/192)/ref,
   'info_BER':sum(r['coded_bit_errors'] for r in rs)/sum(r['coded_bits_denominator'] for r in rs),
   'engineering_mean':float(np.mean(times)),'engineering_p95':float(np.quantile(times,.95)),
   'engineering_n':len(times),'development_mean_instrumented_seconds':float(np.mean([r['elapsed_seconds'] for r in rs])),
   'convergence_failures':sum(not r.get('physical_refit',{}).get('converged',True) for r in rs),
   'fallbacks':[b for b in range(192) if table[b,arm].get('physical_refit',{}).get('fallback') is not None],
   'peak_gpu_bytes':max(r['peak_gpu_bytes'] for r in rs)}
 viable=(contrasts['sbl-s0.5__minus__m-soft']['delta']>=.05 and
         contrasts['m-group__minus__m-soft']['delta']>=.02 and
         contrasts['m-param-budget__minus__m-soft']['delta']>=.02 and
         metrics['m-param-reference']['convergence_failures']==0)
 deployed=['sbl-s0.5','m-group','m-param-budget','m-soft']
 pareto=[a for a in deployed if not any(metrics[b]['FER']<=metrics[a]['FER'] and metrics[b]['engineering_mean']<=metrics[a]['engineering_mean'] and (metrics[b]['FER']<metrics[a]['FER'] or metrics[b]['engineering_mean']<metrics[a]['engineering_mean']) for b in deployed if b!=a)]
 return {'status':'complete','stage':'anchor_development_only','preregister_sha256':prereg_sha,'admission_sha256':admission_sha,'metrics':metrics,'contrasts':contrasts,
  'viable_anchor_candidate':bool(viable),'proceed_confirmation':None,'confirmation_unlocked':False,
  'point_Pareto_provisional_cross_run_microtiming':pareto,'statistically_eliminated':[],
  'all_records_retained':True,'strong_classical_point_best':min(deployed[:-1],key=lambda a:(metrics[a]['FER'],metrics[a]['engineering_mean'],a)),
  'source_and_call_provenance':provenance,'snapshot_audit':bindings,'analysis_source_sha256':sha(__file__),
  'reused_snapshot_checker_sha256':sha(ev/'analyze-cancellation-design-v8.py'),
  'limitations':['Exploratory same-design192 blocks, not confirmation.','Raw micro-cost points across runs do not establish COST-02 or statistical Pareto dominance.','Bounded geometry nonconvergence is not failure of full classical methods; high-compute reference separately reported.','Oracle on D_mech has additional information and a different sample; no causal gap subtraction.','Anchor selection does not unlock neighbor/confirmation; negative or reference-inadequate screen cannot be rescued by adaptive samples.']}

def main():
 out=ROOT/'evidence/physical-development-anchor-v10-v2.json'; failure=out.with_name('physical-development-anchor-v10-v2.failure.json')
 assert not out.exists() and not failure.exists()
 rid='physical-development-analysis-v10-v2';started=time.perf_counter();cpu=time.process_time();status='failed'
 with locked(ROOT/'resource-ledger.json') as ledger:
  existing=ledger['completed']+ledger['reservations'];assert not any(r['id']==rid for r in existing)
  for k,v in {'host_seconds':400,'gpu_seconds':0,'cpu_core_seconds':400}.items():assert sum(r[k] for r in existing)+v<=ledger['limits'][k]
  ledger['reservations'].append(dict(id=rid,calls={},host_seconds=400,gpu_seconds=0,cpu_core_seconds=400))
 def timeout(*args):raise TimeoutError('400sec analysis budget')
 signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,400)
 try:
  r=analyze();r['command']=[sys.executable]+sys.argv;r['exit_code']=0;publish_json(out,r);status='complete'
  print(json.dumps({'status':status,'viable_anchor_candidate':r['viable_anchor_candidate'],'metrics':r['metrics'],'contrasts':r['contrasts']}))
 except BaseException as exc:
  publish_json(failure,{'status':'failed','error':repr(exc),'analysis_source_sha256':sha(__file__)});raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  settle_many(ROOT/'resource-ledger.json',rid,calls={},resources=dict(host_seconds=time.perf_counter()-started,cpu_core_seconds=time.process_time()-cpu,gpu_seconds=0),evidence=str(out if status=='complete' else failure),status=status)
if __name__=='__main__':main()
