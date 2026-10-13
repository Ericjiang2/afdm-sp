"""Paired descriptive terminal comparison; old blocks are never new samples."""
from pathlib import Path
import hashlib
import json
import statistics

m=Path('.mission/20260913_00-48-38-afdm-trans-next')
e=m/'evidence/exact-harvest-v1'
r=Path('.trellis/tasks/09-13-trans-next/research')
tag='untempered-terminal-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=e/'runs'/tag/'diagnostic/summary.json'
s=json.loads(p.read_text())
audit_path=e/'evidence'/(tag+'-raw-audit.json')
audit=json.loads(audit_path.read_text())
end=json.loads((e/'evidence'/(tag+'-exit.json')).read_text())
assert audit['status']=='PASS' and audit['summary_sha256']==sha(p)
assert s['status']=='COMPLETE' and s['calls']==dict(T=128,D=128)
assert end['exit_code']==0 and not end['timed_out']
p2=e/'runs/terminal-prior-variance-v1/diagnostic/summary.json'
s2=json.loads(p2.read_text())
p0=e/'runs/strong-terminal-oracles-v1/diagnostic/summary.json'
s0=json.loads(p0.read_text())
old={row['block']:row['scores'] for row in s0['rows'] if row['arm']=='EST'}
cells={}
for arm in ['EST__RETAIN__PHYSICAL','EST__ZERO__PHYSICAL','TRUE_H__RETAIN__PHYSICAL','TRUE_H__ZERO__PHYSICAL']:
    current={row['block']:row for row in s['rows'] if row['arm']==arm}
    base={row['block']:row for row in s2['rows'] if row['arm']==arm}
    assert set(current)==set(base)==set(range(32))
    cells[arm]=dict(failures=sum(v['scores']['FER'] for v in current.values()),
        failed_blocks=[b for b,v in current.items() if v['scores']['FER']],
        information_bit_errors=sum(v['scores']['info_bit_errors'] for v in current.values()),
        mean_bit_NLL=statistics.mean(v['scores']['bit_NLL'] for v in current.values()),
        temperature2_failures=sum(v['scores']['FER'] for v in base.values()),
        rescued_vs_temperature2=[b for b in range(32) if base[b]['scores']['FER'] and not current[b]['scores']['FER']],
        new_failures_vs_temperature2=[b for b in range(32) if not base[b]['scores']['FER'] and current[b]['scores']['FER']])
    if arm=='EST__RETAIN__PHYSICAL':
        cells[arm]['rescued_vs_old_strong_reference']=[b for b in range(32) if old[b]['FER'] and not current[b]['scores']['FER']]
        cells[arm]['new_failures_vs_old_strong_reference']=[b for b in range(32) if not old[b]['FER'] and current[b]['scores']['FER']]
result=dict(scope=s['scope'],calls=s['calls'],wall_seconds=end['wall_seconds'],summary_sha256=sha(p),
    temperature2_summary_sha256=sha(p2),old_strong_reference_summary_sha256=sha(p0),
    source_sha256=s['source_sha256'],contract_sha256=s['contract_sha256'],
    raw_audit_sha256=sha(audit_path),raw_audit=audit,cells=cells,rows=s['rows'],
    independent_existing_blocks=32,new_independent_blocks=0,
    conclusion='Classical terminal reference qualification only; full adapter not implemented; no CONF/COST/new contribution.')
(r/'untempered-terminal-results-v1.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(cells,ensure_ascii=False,indent=2))
