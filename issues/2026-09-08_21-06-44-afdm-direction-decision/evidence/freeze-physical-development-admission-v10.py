"""Freeze actual source/cache evidence, then preflight without receiver calls."""
import json,hashlib,sys,time
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');ev=root/'evidence';src=root/'source-runtime-v10'
sys.path.insert(0,str(src))
from afdm_sp_joint_unrolled.direction_data import source_manifest
from afdm_sp_joint_unrolled.direction_run import validate_physical_admission
from afdm_sp_joint_unrolled.direction_budget import locked

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def binding(p):return {'path':str(p),'sha256':sha(p)}
plan=json.loads((ev/'physical-development-preregister.json').read_text());task=src/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence'
assert not (ev/'physical-development-admission-v10.json').exists()
current=source_manifest();prefixed={'afdm_sp_joint_unrolled/'+k:v for k,v in current.items()}
(ev/'source-snapshot-runtime-v10.json').write_text(json.dumps(prefixed,indent=2)+'\n')
segments=[]
for name in ('design-000-096-v4','design-096-192-v4'):
 run=root/name;complete=json.loads((run/'complete.json').read_text())
 entries=[binding(p) for p in sorted(run.glob('frame-*-sbl-s0.5.json'))];assert len(entries)==96
 segments.append(dict(complete=binding(run/'complete.json'),source_sha256=complete['source_sha256'],config_sha256=complete['config_sha256'],records=entries))
decision=dict(status='approved_for_design',source_sha256=current,
 algorithm_sha256=sha(task/'physical-algorithm-preregister.json'),protocol_sha256=sha(task/'campaign-protocol.json'),
 preregister=binding(ev/'physical-development-preregister.json'),engineering_audit=binding(ev/'physical-engineering-audit-v9-v3.json'),
 engineering_complete=binding(root/'physical-engineering-v9/complete.json'),
 required_remaining_resources=dict(host_seconds=3000,gpu_seconds=2400,cpu_core_seconds=10200),
 baseline_cache=segments,baseline_selection=binding(ev/'b-star-selection-v1.json'),
 source_equivalence='v9 numerical code unchanged; v10 adds runner design admission and tests only.',
 tests=dict(command='python -m unittest test_direction_physical_admission + physical/operator/routing suites',passed=22,exit_code=0,scope='fixtures/math only'),
 limitations=['Explicit soft bit-exact exception retained; not a whole-snapshot exact pass.','Only768 anchor full calls admitted. No automatic neighbor or confirmation admission.','Group/parameter reference convergence and actual effects to be assessed after complete anchor.'])
out=ev/'physical-development-admission-v10.json';out.write_text(json.dumps(decision,indent=2)+'\n')
start=time.perf_counter();cpu=time.process_time()
try:
 _,cache=validate_physical_admission(out,sha(out),task/'physical-algorithm-preregister.json',task/'campaign-protocol.json',root/'resource-ledger.json',plan['new_arms'],0,192,8,768)
 result=dict(status='passed',cached_blocks=len(cache),admission=binding(out),source_manifest=binding(ev/'source-snapshot-runtime-v10.json'),receiver_calls=0,command=[sys.executable]+sys.argv,exit_code=0,preflight_host_seconds=time.perf_counter()-start,preflight_cpu_seconds=time.process_time()-cpu)
 (ev/'physical-development-preflight-v10.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
finally:
 with locked(root/'resource-ledger.json') as ledger:
  rid='physical-v10-setup-and-preflight-bound';assert not any(r['id']==rid for r in ledger['completed']+ledger['reservations'])
  # Includes source-copy/transfer and22tests; explicitly conservative, not method timing.
  resources=dict(host_seconds=max(120.,time.perf_counter()-start),gpu_seconds=0.,cpu_core_seconds=max(120.,time.process_time()-cpu))
  for k,v in resources.items():assert sum(r[k] for r in ledger['completed']+ledger['reservations'])+v<=ledger['limits'][k]
  ledger['completed'].append(dict(id=rid,calls={},status='conservative_setup_bound',evidence=str(ev/'physical-development-preflight-v10.json'),**resources))
