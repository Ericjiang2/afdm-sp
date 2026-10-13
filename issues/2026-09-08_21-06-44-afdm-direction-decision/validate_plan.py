"""Validate planning artifacts only. Does not import or run receiver code."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path

base = Path(__file__).resolve().parent
root = base.parents[1]
stem = base.name
csv_path = base / f'{stem}.csv'
raw = csv_path.read_bytes()
assert raw.startswith(b'\xef\xbb\xbf'), 'Missing UTF-8 BOM'
headers = 'id,priority,phase,area,title,description,acceptance_criteria,test_mcp,required_skills,required_mcp,review_initial_requirements,review_regression_requirements,dev_state,review_initial_state,review_regression_state,git_state,owner,refs,notes'.split(',')
reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''))
assert reader.fieldnames == headers
rows = list(reader)
assert len(rows) == 39
buf = io.StringIO(newline='')
writer = csv.DictWriter(buf,fieldnames=headers,quoting=csv.QUOTE_ALL,lineterminator='\r\n')
writer.writeheader(); writer.writerows(rows)
assert raw == buf.getvalue().encode('utf-8-sig'), 'Quoting/newlines mismatch'
by_id = {r['id']:r for r in rows}
assert len(by_id) == len(rows)

def tag(row,key):
    match = re.search(r'(?:^|;\s*)'+re.escape(key)+r':([^;]+)',row['notes'])
    assert match, (row['id'],key)
    return match.group(1).strip()

deps = {}
ref_count = 0
for row in rows:
    assert None not in row and all(v is not None for v in row.values())
    assert row['priority'] in {'P0','P1','P2'}
    assert row['area'] in {'backend','frontend','both','infra','review'}
    assert row['phase'].isdigit() and int(row['phase']) > 0
    assert row['test_mcp'] in {'AUTOSERVER','AUTOFRONTEND','AUTOE2E','CONTRACT','MIGRATION','MANUAL'}
    for k in ['dev_state','review_initial_state','review_regression_state']:
        assert row[k]=='未开始', (row['id'],k)
    assert row['git_state']=='未提交' and not row['owner']
    value=tag(row,'depends_on')
    deps[row['id']] = [] if value=='none' else value.split(',')
    assert set(deps[row['id']]) <= set(by_id)
    assert row['id'] not in deps[row['id']]
    assert 'WHEN ' in row['acceptance_criteria'] and ' THEN ' in row['acceptance_criteria']
    for ref in row['refs'].split('; '):
        path,line=ref.rsplit(':',1)
        p=Path(path)
        if not p.is_absolute(): p=root/p
        assert p.is_file(), ref
        assert 1 <= int(line) <= len(p.read_text().splitlines()), ref
        ref_count += 1
    assert (base/tag(row,'claim_ledger')).is_file()
    assert 'review_result:vision_met' not in row['notes']

visited,stack=set(),set()
def visit(id):
    assert id not in stack, f'Dependency cycle: {id}'
    if id in visited: return
    stack.add(id)
    for dep in deps[id]: visit(dep)
    stack.remove(id);visited.add(id)
for id in by_id: visit(id)
positions={r['id']:i for i,r in enumerate(rows)}
assert all(positions[d] < positions[id] for id,ds in deps.items() for d in ds)

ledger=json.loads((base/f'{stem}.claims.json').read_text())
claims=ledger['claims']; assert len(claims)==85
cidmap={c['claim_id']:c for c in claims}; assert len(cidmap)==len(claims)
for c in claims:
    assert c['status']=='pending'
    assert c['covered_by']
    for id in c['covered_by']:
        assert id in by_id and c['promise'] in by_id[id]['acceptance_criteria']
        assert c['claim_id'] in tag(by_id[id],'claims').split(',')
        assert tag(by_id[id],'evidence_required')==c['evidence_required']
for r in rows:
    for cid in tag(r,'claims').split(','):
        assert cid in cidmap and r['id'] in cidmap[cid]['covered_by']
manifest=json.loads((base/'source-manifest.json').read_text())
assert hashlib.sha256((base/'source-plan.md').read_bytes()).hexdigest()==manifest['sha256']
assert (base/'source-plan.md').read_bytes()==Path(manifest['original_path']).read_bytes()
assert rows[-1]['id']=='REVIEW-01' and rows[-1]['area']=='review'
assert 'authorization_scope:csv_generation_only' in rows[0]['notes']
assert '下界>0.02' in by_id['GATE-01']['acceptance_criteria']
assert '下界>0.02' in by_id['STATS-01']['acceptance_criteria']
assert '0接收机调用' in by_id['GATE-00']['acceptance_criteria']
assert '24576' in by_id['FREEZE-01']['acceptance_criteria']
assert 'REVIEW-02' in rows[-1]['acceptance_criteria']
assert tag(by_id['FREEZE-01'],'run_if') == 'viable_legal_candidate'
for id in ['CONFIRM-01','SCENE-02','COST-02']:
    assert tag(by_id[id],'run_if').startswith('proceed_confirmation == true AND ')
assert '在读取D_mech结果前' in by_id['GATE-01']['acceptance_criteria']
assert '通过/失败/证据不足判表' in by_id['SCENE-01']['acceptance_criteria']
assert 'proceed_confirmation=false' in by_id['DEV-01']['acceptance_criteria']
report = dict(validation_kind='planning_static_only',result='passed',rows=len(rows),claims=len(claims),
    claim_mapping=f'{len(claims)}/{len(claims)}',claims_verified_by_experiments=0,
    path_claims_mapped=sum(c['production_path_required'] for c in claims),
    wiring_rows=sum('issue_kind:wiring' in r['notes'] for r in rows),refs_checked=ref_count,
    checks=['19-column schema','UTF-8 BOM / QUOTE_ALL / CRLF round-trip','initial states',
      'unique IDs / dependency DAG / topological order','bidirectional claim-AC mapping',
      'existing file:line refs','source byte equality and SHA-256','authorization and review gates',
      'selection preregistration / budget evaluation entry / explicit stop short-circuit / counterexample three-state criteria'],
    limitations=['Static generation validation is not execution or scientific acceptance',
      'Future planned evidence files have not been produced','Conditional branches require evidence at execution time'],
    csv_sha256=hashlib.sha256(raw).hexdigest())
(base/f'{stem}.validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
