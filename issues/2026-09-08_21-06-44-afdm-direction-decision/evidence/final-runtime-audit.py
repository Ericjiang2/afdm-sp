import hashlib,json,subprocess,time
from pathlib import Path
root=Path('/data/guoyikun/00inbox/AFDM-channel-estimation/outputs_direction_decision_20260908');ev=root/'evidence';src=root/'source-runtime-v10'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ledger=read(root/'resource-ledger.json');assert not ledger['reservations']
usage={k:sum(r[k] for r in ledger['completed']) for k in ledger['limits']}
assert all(usage[k]<=v for k,v in ledger['limits'].items())
calls={k:sum(r.get('calls',{}).get(k,0) for r in ledger['completed']) for k in ledger['calls_caps']}
assert all(calls[k]<=v for k,v in ledger['calls_caps'].items())
assert all(calls[k]==0 for k in ('confirmation_full','counterexample_full','timing_full'))
manifest=read(ev/'source-snapshot-runtime-v10.json');actual={str(f.relative_to(src)):sha(f) for f in sorted((src/'afdm_sp_joint_unrolled').rglob('*.py'))};assert actual==manifest
complete=read(root/'physical-design-v10/complete.json');audit=read(ev/'physical-development-anchor-v10-v2.json');status=read(ev/'physical-development-v10-status.json')
assert complete['status']=='complete' and complete['calls_attempted']==complete['calls_completed']==768
assert audit['status']=='complete' and audit['exit_code']==0 and len(audit['snapshot_audit'])==960
assert status['status']=='complete' and status['exit_code']==0
identities=[]
for pid,ticks in [(status['pid'],status['start_ticks']),(status['child_pid'],status['child_start_ticks'])]:
 stat=Path('/proc')/str(pid)/'stat';matching=stat.exists() and stat.read_text().split()[21]==ticks
 assert not matching;identities.append(dict(pid=pid,matching_live_process=matching))
apps=subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.strip()
assert not apps,'unexpected GPU activity; inspect without killing'
r={'status':'passed','exit_code':0,'command':['/home/guoyikun/.conda/envs/AFDM/bin/python',str(Path(__file__))],'receiver_calls_added':0,'complete_sha256':sha(root/'physical-design-v10/complete.json'),'audit_sha256':sha(ev/'physical-development-anchor-v10-v2.json'),'source_manifest_sha256':sha(ev/'source-snapshot-runtime-v10.json'),'source_files':len(actual),'resources_used':usage,'resource_limits':ledger['limits'],'calls_used':calls,'call_limits':ledger['calls_caps'],'reservations':ledger['reservations'],'old_job_identities':identities,'gpu_apps':apps,'ledger_sha256':sha(root/'resource-ledger.json'),'verified_unix':time.time(),'scope':'Current final server state and immutable source/artifact hashes. Prior960snapshot audit is bound, not rerun. No D_test access or receiver calls.'}
(ev/'final-runtime-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
