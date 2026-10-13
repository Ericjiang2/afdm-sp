import hashlib,json,sys,time
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');sys.path.insert(0,str(root/'source-runtime-v10'))
from afdm_sp_joint_unrolled.direction_budget import locked
path=root/'resource-ledger.json';prior=hashlib.sha256(path.read_bytes()).hexdigest();audit=json.loads((root/'evidence/final-runtime-audit.json').read_text());assert prior==audit['ledger_sha256']
rid='final-wrapup-metadata-bound'
with locked(path) as ledger:
 assert not ledger['reservations'] and not any(r['id']==rid for r in ledger['completed'])
 resources=dict(host_seconds=60.,gpu_seconds=0.,cpu_core_seconds=60.)
 assert all(sum(r[k] for r in ledger['completed'])+v<=ledger['limits'][k] for k,v in resources.items())
 ledger['completed'].append(dict(id=rid,calls={},status='conservative_final_metadata_bound',evidence='evidence/final-budget-settlement.json',**resources))
ledger=json.loads(path.read_text());out=dict(status='complete',exit_code=0,receiver_calls_added=0,command=[sys.executable,__file__],scope='Conservative60seconds covers final runtime metadata audit, artifact transport and wrapup; no new simulation or method timing.',prior_ledger_sha256=prior,ledger_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),resources_added=resources,resources_used={k:sum(r[k] for r in ledger['completed']) for k in ledger['limits']},resource_limits=ledger['limits'],reservations=ledger['reservations'],verified_unix=time.time())
(root/'evidence/final-budget-settlement.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
