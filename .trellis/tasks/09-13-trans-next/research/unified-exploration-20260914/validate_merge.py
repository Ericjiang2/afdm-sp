"""Validate this immutable CSV migration snapshot; no receiver or network calls."""
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

STAGE = Path(__file__).resolve().parent
ROOT = STAGE.parents[4]
STEM = '20260914_12-58-51-afdm-unified-exploration'
MISSION = ROOT / '.mission' / STEM
CSV_PATH = MISSION / (STEM + '.csv')
REPORT = STAGE / 'validation.json'
FIELDS = 'id,priority,phase,area,title,description,acceptance_criteria,test_mcp,required_skills,required_mcp,review_initial_requirements,review_regression_requirements,dev_state,review_initial_state,review_regression_state,git_state,owner,refs,notes'.split(',')
STATES = ['dev_state', 'review_initial_state', 'review_regression_state', 'git_state']


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDS, path
        rows = list(reader)
    assert all(set(r) == set(FIELDS) and all(v is not None for v in r.values()) for r in rows)
    return rows


def tags(row):
    return dict(part.strip().split(':', 1) for part in row['notes'].split(';') if ':' in part)


def check_ref(ref):
    path, line = ref.rsplit(':', 1)
    target = ROOT / path
    assert target.is_file(), ref
    assert 1 <= int(line) <= len(target.read_text(encoding='utf-8-sig').splitlines()), ref


rows = read(CSV_PATH)
by_id = {r['id']: r for r in rows}
assert len(rows) == len(by_id) == 36
data = CSV_PATH.read_bytes()
assert data.startswith(b'\xef\xbb\xbf')
buf = io.StringIO(newline='')
writer = csv.DictWriter(buf, FIELDS, quoting=csv.QUOTE_ALL, lineterminator='\n')
writer.writeheader()
writer.writerows(rows)
assert data == buf.getvalue().encode('utf-8-sig'), 'encoding/quoting/roundtrip'
for row in rows:
    for state in STATES[:3]:
        assert row[state] in ['未开始', '进行中', '已完成']
    assert row['git_state'] in ['未提交', '已提交']
    assert row['priority'] in ['P0', 'P1', 'P2']
    assert row['phase'].isdigit() and int(row['phase']) >= 1
    assert row['area'] in ['backend', 'frontend', 'both', 'infra', 'review']
    assert row['test_mcp'] in ['AUTOSERVER', 'AUTOFRONTEND', 'AUTOE2E', 'CONTRACT', 'MIGRATION', 'MANUAL']

manifest = json.loads((STAGE / 'source-manifest.json').read_text())
for source in manifest['local_sources']:
    path = ROOT / source['path']
    assert len(path.read_bytes()) == source['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], path

mapping = json.loads((STAGE / 'migration-map.json').read_text())['mappings']
source_paths = {entry['source_csv'] for entry in mapping}
source_rows = {path: {r['id']: r for r in read(ROOT / path)} for path in source_paths}
expected = {(path, rid) for path, source in source_rows.items() for rid in source}
counts = Counter((entry['source_csv'], entry['source_id']) for entry in mapping)
assert set(counts) == expected and all(n == 1 for n in counts.values())
assert all(set(entry['target_ids']) <= set(by_id) for entry in mapping)
assert {rid for entry in mapping for rid in entry['target_ids']} == set(by_id)

historical = [row for row in rows if tags(row)['entry_kind'] == 'historical_completed']
assert len(historical) == 16
for row in historical:
    tag = tags(row)
    original = source_rows[tag['source_csv']][row['id']]
    assert [row[s] for s in STATES] == ['已完成'] * 3 + ['已提交']
    assert all(row[key] == original[key] for key in STATES + ['title', 'description', 'acceptance_criteria'])
    digest = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert digest == tag['source_row_sha256']
    assert 'continue_now:' not in row['notes'] and 'user_authorized_dynamic_execution:true' not in row['notes']

future = [row for row in rows if row not in historical]
assert len(future) == 20
deps = {}
for row in future:
    assert [row[s] for s in STATES] == ['未开始'] * 3 + ['未提交']
    tag = tags(row)
    assert tag['execution_authorized'] == 'false'
    assert tag['C_deferred'] == 'user_20260914'
    depends = tag['depends_on'].split(',') if tag['depends_on'] != 'none' else []
    assert set(depends) <= set(by_id)
    deps[row['id']] = depends
assert not any(re.match(r'C-\d', row['id']) for row in rows)
assert set(deps['B-03']) == {'A-04', 'B-02', 'EDGE-01'}
assert set(deps['CONF-01']) == {'G1-01', 'COST-01'}
assert tags(by_id['EDGE-01'])['entry_kind'] == 'stage_conditional'
assert all(tags(by_id[rid])['entry_kind'].startswith('deferred') for rid in ['CONF-01','COST-01','G1-01','SCENE-01','CODE-01','PAPER-01','REVIEW-01'])
visited, visiting = set(), set()


def visit(rid):
    assert rid not in visiting, 'cyclic dependency'
    if rid in visited:
        return
    visiting.add(rid)
    for dependency in deps.get(rid, []):
        visit(dependency)
    visiting.remove(rid)
    visited.add(rid)


for rid in by_id:
    visit(rid)
reference_count = 0
for row in rows:
    for ref in row['refs'].split(';'):
        check_ref(ref.strip())
        reference_count += 1
ledger = json.loads((MISSION / (STEM + '.claims.json')).read_text())
assert len(ledger['claims']) == 12
claim_ids = {claim['claim_id'] for claim in ledger['claims']}
assert len(claim_ids) == 12
for claim in ledger['claims']:
    check_ref(claim['source_ref'])
    assert claim['status'] == 'pending'
    assert claim['covered_by'] and set(claim['covered_by']) <= set(by_id)
    assert all(claim['claim_id'] in tags(by_id[rid])['claims'].split(',') for rid in claim['covered_by'])
for row in future:
    tag = tags(row)
    assert set(tag['claims'].split(',')) <= claim_ids
    assert (MISSION / tag['claim_ledger']).is_file()

markdown_files = [STAGE/'plan.md', MISSION/'README.md', ROOT/'.trellis/tasks/09-13-trans-next/execution.md']
markdown_files += [ROOT/path for path in ['.mission/20260913_00-48-38-afdm-trans-next/README.md', '.mission/20260914_11-44-58-afdm-two-direction-exploration/README.md']]
link_count = 0
for path in markdown_files:
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if re.match(r'(?:https?://|#)', link):
            continue
        target = (path.parent / link.split('#', 1)[0]).resolve()
        assert target == REPORT or target.exists(), f'{path}: {link}'
        link_count += 1

report = dict(kind='merge_artifact_static_validation_not_research_review', result='PASS', schema_columns=19,
              rows=36, inherited_closed=16, future_unstarted=20, mapped_source_rows=len(mapping),
              source_files_hash_verified=len(manifest['local_sources']), refs_verified=reference_count,
              markdown_links_verified=link_count, claim_requirements_mapped=12, scientific_claims_verified=0,
              dependency_graph='acyclic', source_csv_bytes='unchanged', state_inheritance='original_contract_only',
              new_simulation_calls=0, review_mode='main_session_self_review', review_independence='weak',
              csv_sha256=hashlib.sha256(data).hexdigest(),
              limitations=['仅验证融合快照及其文档合同，不验收未来任务或科学收益', '未来执行更改状态后应保留本报告，不按初始状态断言重新验证执行结果'])
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False))
