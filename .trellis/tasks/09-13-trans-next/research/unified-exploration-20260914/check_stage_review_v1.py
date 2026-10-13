"""Validate stage handoff readiness without rerunning experiments or closing total REVIEW."""
import argparse
import ast
import csv
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError(args.output)

research = Path(__file__).resolve().parent
root = research.parents[4]
stem = '20260914_12-58-51-afdm-unified-exploration'
mission = root / '.mission' / stem
csv_path = mission / (stem + '.csv')
ledger_path = mission / (stem + '.claims.json')
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    assert len(reader.fieldnames) == 19
    assert all(set(row) == set(reader.fieldnames) and None not in row.values() for row in rows)
    return rows


def tags(row):
    return dict(part.strip().split(':', 1) for part in row['notes'].split(';') if ':' in part)


def check_ref(ref):
    # Execution rows use both whole-file references and path:line references.
    match = re.fullmatch(r'(.+):(\d+)', ref)
    name, line = match.groups() if match else (ref, None)
    path = root / name
    if path.resolve() == args.output.resolve():
        assert line in (None, '1')
        return
    assert path.is_file(), ref
    if line is not None:
        assert 1 <= int(line) <= len(path.read_text(encoding='utf-8-sig').splitlines()), ref


rows = read_csv(csv_path)
by_id = {row['id']: row for row in rows}
assert len(rows) == len(by_id) == 36
buffer = io.StringIO(newline='')
writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL, lineterminator='\n')
writer.writeheader()
writer.writerows(rows)
assert csv_path.read_bytes() == buffer.getvalue().encode('utf-8-sig')
states = ['dev_state', 'review_initial_state', 'review_regression_state', 'git_state']
for row in rows:
    assert all(row[key] in ('未开始', '进行中', '已完成') for key in states[:3])
    assert row['git_state'] in ('未提交', '已提交')

manifest = json.loads((research / 'source-manifest.json').read_text())
for source in manifest['local_sources']:
    path = root / source['path']
    assert path.stat().st_size == source['bytes'] and sha(path) == source['sha256'], path
assert len(manifest['local_sources']) == 8
mapping = json.loads((research / 'migration-map.json').read_text())['mappings']
source_rows = {name: {row['id']: row for row in read_csv(root / name)}
               for name in {entry['source_csv'] for entry in mapping}}
counts = Counter((entry['source_csv'], entry['source_id']) for entry in mapping)
assert set(counts) == {(name, rid) for name, source in source_rows.items() for rid in source}
assert len(mapping) == 36 and set(counts.values()) == {1}
assert {rid for entry in mapping for rid in entry['target_ids']} == set(by_id)
historical = [row for row in rows if tags(row)['entry_kind'] == 'historical_completed']
assert len(historical) == 16
for row in historical:
    tag = tags(row)
    original = source_rows[tag['source_csv']][row['id']]
    assert all(row[key] == original[key] for key in states + ['title', 'description', 'acceptance_criteria'])
    assert hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest() == tag['source_row_sha256']
    assert 'continue_now:' not in row['notes']

deferred = ['G1-01', 'COST-01', 'CONF-01', 'SCENE-01', 'CODE-01', 'PAPER-01', 'REVIEW-01']
for rid in deferred:
    row = by_id[rid]
    assert [row[key] for key in states] == ['未开始', '未开始', '未开始', '未提交']
    assert tags(row)['current_candidate'] == 'none_after_A_B_stage'
    assert tags(row)['current_activation'] == 'not_met'
    assert tags(row)['execution_authorized'] == 'false'
stage = [row for row in rows if row not in historical and row['id'] not in deferred]
assert len(stage) == 13
for row in stage:
    if row['id'] != 'STAGE-REVIEW-01':
        assert [row[key] for key in states] == ['已完成', '已完成', '已完成', '已提交'], row['id']
    assert tags(row)['execution_authorized'] == 'true'
    assert tags(row)['C_deferred'] == 'user_20260914'
assert not any(re.match(r'C-\d', rid) for rid in by_id)
review = by_id['STAGE-REVIEW-01']
assert review['dev_state'] == '进行中'
assert tags(review)['review_independence'] == 'weak'
assert tags(review)['handoff'] == 'stage-handoff.md'
assert (mission / tags(review)['handoff']).is_file()
assert not (mission / (stem + '.handoff.md')).exists()
assert json.loads((research.parent.parent / 'task.json').read_text())['status'] == 'in_progress'

visited, visiting = set(), set()


def visit(rid):
    assert rid not in visiting, 'cyclic dependency'
    if rid in visited:
        return
    visiting.add(rid)
    for dependency in tags(by_id[rid]).get('depends_on', 'none').split(','):
        if dependency != 'none':
            assert dependency in by_id
            visit(dependency)
    visiting.remove(rid)
    visited.add(rid)


for rid in by_id:
    visit(rid)
refs = [ref.strip() for row in rows for ref in row['refs'].split(';')]
for ref in refs:
    check_ref(ref)

ledger = json.loads(ledger_path.read_text())
assert ledger['kind'] == 'requirements_not_accepted_scientific_claims'
assert Counter(claim['status'] for claim in ledger['claims']) == {'covered': 5, 'pending': 7}
assert ledger['claim_coverage']['covered'] == 5 and ledger['stage_coverage']['covered'] == 7
assert ledger['review']['scientific_claims_accepted'] == 0 and not ledger['review']['total_research_complete']
stage_claims = {'CLAIM-001', 'CLAIM-002', 'CLAIM-003', 'CLAIM-004', 'CLAIM-005', 'CLAIM-011', 'CLAIM-012'}
assert {claim['claim_id'] for claim in ledger['claims'] if claim['stage_status'] == 'covered'} == stage_claims
for claim in ledger['claims']:
    check_ref(claim['source_ref'])
    assert all(claim['claim_id'] in tags(by_id[rid])['claims'].split(',') for rid in claim['covered_by'])
    assert set(claim['pending_issue_ids']) <= set(deferred)
    for name in claim['evidence_refs']:
        path = root / name
        assert path.is_file() or path.resolve() == args.output.resolve(), name
    if claim['claim_id'] in ('CLAIM-011', 'CLAIM-012'):
        assert claim['status'] == 'pending' and claim['pending_issue_ids'] == ['REVIEW-01']

verdict_path = research / 'syn01-verdict-v1.json'
verdict = json.loads(verdict_path.read_text())
for name, wanted in verdict['source_evidence'].items():
    assert sha(research / name) == wanted, name
assert verdict['claim_supported'] == 'no' and verdict['recommended_candidate'] is None
assert verdict['review_independence'] == 'weak' and not verdict['secondary_agent_called']
confirmation = json.loads((research / 'confirmation-disposition-v1.json').read_text())
assert confirmation['predecessor_sha256'] == sha(verdict_path)
assert confirmation['candidate'] is None and confirmation['new_experiments'] == 0
assert confirmation['deferred_rows'] == deferred
a04 = json.loads((research / 'a04-results-v1.json').read_text())
assert a04['channels'] == 64 and a04['full_receiver_calls'] == 3328
assert a04['usable_candidates'] == [] and len(a04['candidates']) == 9
assert all(candidate['status'] == 'NOT_SUPPORTED' for candidate in a04['candidates'])
assert a04['calibration_channels'] == a04['holdout_channels'] == a04['coding_calls'] == 0
assert a04['actual_calls'] == {'CE': 29952, 'outer_BP': 33280, 'BP_inner_iterations': 665260}
assert a04['empty_graph_outer_calls'] == 17 and len(a04['empty_graph_records']) == 4
primary = [value for value in a04['contrasts'] if value['pilot'] == 'pZ' and value['snr'] == 20
           and value['right'] in ('OMP_SMALL', 'OMP_SMALL_RIDGE')]
assert len(primary) == 18 and all(value['simultaneous_95'][0] > 0 for value in primary)
assert json.loads((research / 'b02-results-v1.json').read_text())['B03_diagnostic_admission'] is False
for name in ('b03-stop-v1.json', 'b04-stop-v1.json'):
    value = json.loads((research / name).read_text())
    assert value['new_receiver_calls'] == value['new_decoder_calls'] == value['calibration_channels_created'] == 0
assert json.loads((research / 'b04-stop-v1.json').read_text())['holdout_channels_created'] == 0
assert not (root / 'EXPERIMENT_AUDIT.json').exists()

remote_path = mission / 'evidence/stage-remote-check-v1.json'
remote = json.loads(remote_path.read_text())
assert remote['status'] == 'PASS' and remote['active_task_processes'] == []
assert remote['record_totals'] == {'A': 2804, 'F': 3453, 'T': 13}
assert len(remote['jobs']) == 28 and len(remote['source_snapshots']) == 6
assert remote['no_new_scope_runs']
source = json.loads((root / 'afdm_sp_joint_unrolled/outputs_unified_exploration_20260914/source-a04-v1/source-manifest.json').read_text())
for name in ('fixed_basis_receiver.py', 'classical_joint_unrolled.py', 'bandlimited_basis.py'):
    assert sha(root / 'afdm_sp_joint_unrolled' / name) == source[name], name

documents = [mission / 'stage-handoff.md', mission / 'README.md', research / 'stage-review-v1.md']
link_count = 0
for path in documents:
    for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
        if re.match(r'(?:https?://|#)', link):
            continue
        target = (path.parent / link.split('#', 1)[0]).resolve()
        assert target.is_file() or target == args.output.resolve(), f'{path}: {link}'
        link_count += 1
script_dir = Path('/Users/guoyikun/.codex/skills/mission-csv-execute/scripts')
mechanical = []
for command in ([str(script_dir / 'validate_claim_ledger.py'), str(csv_path), '--workdir', str(root)],
                [str(script_dir / 'lint_handoff.py'), str(mission / 'stage-handoff.md')]):
    result = subprocess.run(['python3', '-B', *command], capture_output=True, text=True, cwd=root)
    assert result.returncode == 0, result.stdout + result.stderr
    mechanical.append(dict(tool=Path(command[0]).name, exit_code=result.returncode, stdout=result.stdout.strip()))
for path in (Path(__file__), mission / 'dispatch/check_stage_remote.py'):
    ast.parse(path.read_text())

report = dict(status='PASS', kind='stage_review_readiness_not_total_research_completion',
              checked_at=datetime.now(timezone.utc).isoformat(), review_independence='weak',
              csv_state_at_check='STAGE-REVIEW-01 in progress; ready to close',
              csv_sha256=sha(csv_path), checker_sha256=sha(Path(__file__)),
              source_files_hash_verified=8, mapped_source_rows=36, historical_rows_preserved=16,
              prior_stage_rows_closed=12, deferred_rows_unchanged=deferred, dependency_graph='acyclic',
              refs_verified=len(refs), handoff_document_links_verified=link_count,
              complete_requirement_coverage='5/12', applicable_stage_coverage='7/7',
              numerical_report_bindings_verified=8, primary_positive_intervals=18,
              core_source_files_match_audited_snapshot=3, new_runtime_calls=0,
              scientific_claims_accepted=0, total_research_complete=False,
              mechanical_checks=mechanical, remote_receipt_sha256=sha(remote_path),
              checker_corrections=['Initial checker required path:line; corrected to also validate the six existing whole-file references without changing CSV evidence.'],
              artifact_hashes={str(path.relative_to(root)): sha(path) for path in
                              [ledger_path, *documents, verdict_path]},
              limitations=['main-session self-review weak', 'reuses already completed raw audits and tests',
                           'no standardized EXPERIMENT_AUDIT.json', 'total REVIEW intentionally open'])
with args.output.open('x') as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({key: report[key] for key in ('status', 'historical_rows_preserved', 'refs_verified',
                 'handoff_document_links_verified', 'complete_requirement_coverage',
                 'applicable_stage_coverage', 'scientific_claims_accepted')}, ensure_ascii=False))
