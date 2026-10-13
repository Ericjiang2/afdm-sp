import hashlib,json,sys
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');src=root/'source-runtime-v8'
sys.path.insert(0,str(src))
from afdm_sp_joint_unrolled.direction_data import source_manifest
from afdm_sp_joint_unrolled.direction_run import validate_cancellation_admission
from afdm_sp_joint_unrolled.budgeted_frame_store import publish_json
p=src/'issues/2026-09-08_21-06-44-afdm-direction-decision/evidence'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=root/'evidence/cancellation-engineering-audit-v8.json';a=json.loads(audit.read_text());assert a['status']=='passed' and a['records']==20
old=json.loads((root/'evidence/cost-feasibility.json').read_text())
A2=old['microcost']['A2'];ratios={arm:{k:v[k]/A2[k] for k in ('mean','p95')} for arm,v in a['cost'].items() if arm.startswith('cancel-')}
allowed=[arm[7:] for arm,v in ratios.items() if all(x<=1.1 for x in v.values())];assert len(allowed)==3
ledger=json.loads((root/'resource-ledger.json').read_text());assert not ledger['reservations']
remaining={k:v-sum(x[k] for x in ledger['completed']) for k,v in ledger['limits'].items()}
cF=max(1.8,1.3*a['actual_full_job_wall_seconds']/20)
# This is a staged feasibility envelope, never a final precision/sample-size freeze.
counts=dict(prototype_including_correction=2304,confirmation_provisional=4096,counterexample_provisional=1024)
projected=cF*sum(counts.values())+1200*1.8+600
required=dict(host_seconds=projected,gpu_seconds=projected,cpu_core_seconds=4*projected)
assert all(required[k]<=remaining[k] for k in required)
d=dict(status='approved_for_design',registry_sha256=sha(p/'cancellation-algorithm-preregister.json'),protocol_sha256=sha(p/'campaign-protocol.json'),source_sha256=source_manifest(),allowed_modes=allowed,engineering_complete=a['complete'],engineering_audit=dict(path=str(audit),sha256=sha(audit)),A2_micro_reference=dict(path=str(root/'evidence/cost-feasibility.json'),sha256=sha(root/'evidence/cost-feasibility.json')),engineering_A2_mean_p95_ratios=ratios,required_remaining_resources=required,available_at_freeze=remaining,projection=dict(cF=cF,counts=counts,timing_calls=1200,timing_envelope=1.8,additional_analysis_seconds=600),limits=['Engineering n4/arm and original A2 n6 differ in run/observation instrumentation; ratios are a provisional compatibility screen, not formal mean/p95 certification.','Projection permits staged development only. Confirmation provisional4096 calls corresponds to two arms:1024 anchor and512 per neighbor. This is NOT a precision/power freeze or permission to remove strong comparators.','FREEZE-01 must compute actual powered n and retain required comparator/scenes. If that fails remaining budget, no confirmation; do not reduce precision or claim no-method.','Future M prototype cost must be measured before launch; counterexample1024 is a staging envelope, not permission to weaken required falsification.','No confirmation unlock token or sealed D_test access.'])
out=root/'evidence/cancellation-design-admission-v8.json';publish_json(out,d)
validate_cancellation_admission(out,sha(out),p/'cancellation-algorithm-preregister.json',p/'campaign-protocol.json',root/'resource-ledger.json',['cancel-'+x for x in allowed])
print(json.dumps({'path':str(out),'sha256':sha(out),'allowed_modes':allowed,'required_remaining_resources':required,'available_at_freeze':remaining,'ratios':ratios}))
