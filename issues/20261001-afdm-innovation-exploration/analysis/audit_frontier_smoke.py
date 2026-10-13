from pathlib import Path
import sys,json,hashlib
TASK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TASK/'source'))
import evidence_reference as evidence
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
run=TASK/'experiments/frontier_smoke_v1';manifest=json.loads((run/'manifest.json').read_text());result=json.loads((run/'result.json').read_text())
if sha(TASK/'source/evidence_reference.py')!=manifest['locked_hashes']['baseline_hashes']['src/evidence.py']:raise ValueError('loader differs')
for path,key in [('manifest.json','manifest_sha256'),('ledger.jsonl','ledger_sha256'),('attempts.jsonl','attempts_sha256')]:
 if sha(run/path)!=result[key]:raise ValueError('smoke file differs')
records=[]
for row in map(json.loads,(run/'ledger.jsonl').read_text().splitlines()):
 p=run/row['raw_path']
 if sha(p)!=row['raw_sha256']:raise ValueError('raw differs')
 identity=dict(observation_id=row['observation_id'],policy=row['policy'],input_sha256=row['input_sha256'])
 raw,_=evidence.load_artifact(p,identity)
 records.append(dict(observation_id=row['observation_id'],policy=row['policy'],coherent=raw['coherent'] is not None,restart=raw['restart'] is not None,f1_cstate=raw['restart'] is not None and raw['restart']['branch'] is not None,raw_sha256=row['raw_sha256']))
counts=dict(coherent=sum(r['coherent'] for r in records),guarded_restart=sum(r['restart'] and r['policy']=='guard_f1' for r in records),f1_cstate=sum(r['f1_cstate'] for r in records))
if len(records)!=12 or min(counts.values())<1:raise ValueError('smoke coverage missing')
print(json.dumps(dict(status='pass',scope='local raw coverage audit; zero added receivers',loader_sha256=sha(TASK/'source/evidence_reference.py'),result_sha256=sha(run/'result.json'),counts=counts,records=records),indent=2))
