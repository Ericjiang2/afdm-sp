"""Audit existing v2 raw records for v3 reuse without running a receiver."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile


def archive_rows(path):
    with tarfile.open(path) as archive:
        result = []
        for member in archive.getmembers():
            if member.isfile() and member.name.endswith('/frames.jsonl'):
                result.extend(json.loads(line) for line in archive.extractfile(member).read().splitlines())
    return result


def identity(row):
    return row['replicate'], row['frame_index']


def values_named(value, name):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == name:
                yield child
            else:
                yield from values_named(child, name)
    elif isinstance(value, list):
        for child in value:
            yield from values_named(child, name)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    old = root/'issues/2026-09-06_13-47-38-afdm-plan-v2/evidence'
    names = ['gainpilot-1788687500-runtime.tar.gz', 'gainrest-1788687670-runtime.tar.gz',
             'mechanism48-runtime.tar.gz', 'commonkeep-smoke-runtime.tar.gz',
             'feedback48-runtime.tar.gz', 'fit192-runtime-validation.tar.gz']
    records = {name: archive_rows(old/name) for name in names}
    gain = records[names[0]] + records[names[1]]
    fit = {identity(row): row for row in records[names[5]]}
    reference = {identity(row): row for row in json.loads((old/'gain192-reference.json').read_text())['frames']}
    assert len(gain) == len(fit) == len(reference) == 192
    assert len({identity(row) for row in gain}) == 192
    for row in gain:
        original = reference[identity(row)]
        baseline = original['arms']['baseline']
        assert row['original_sigma'] == baseline['sigma2_final']
        assert row['original_H_hash'] == baseline['output_h_sha256']
        assert row['old_info_errors'] == baseline['info_errors']
        assert row['input_hashes'] == original['input_hashes'] == fit[identity(row)]['input_hashes']
        for name in ('a0', 'baseline'):
            assert original['arms'][name]['info_errors'] == fit[identity(row)]['arms'][name]['info_errors']
            assert original['arms'][name]['output_h_sha256'] == fit[identity(row)]['arms'][name]['output_h_sha256']
    mechanism = records[names[2]] + records[names[3]]
    assert len(mechanism) == len({identity(row) for row in mechanism}) == 48
    tables = [table for row in mechanism
              for table_list in values_named(row['arms']['r11'], 'score_tables') for table in table_list]
    assert len(tables) == 96
    assert sum(len(table['candidates']) for table in tables) == 9207
    relations = Counter(table['state_relation'] for table in tables)
    assert relations == {'same': 69, 'diverged_support_frozen_prior': 27}
    feedback = records[names[4]]
    assert len(feedback) == len({identity(row) for row in feedback}) == 48
    snapshots = []
    for row in feedback:
        mean = row['arms']['f_mean']
        assert len(mean['dals_consumers']) == len(mean['frozen_state_comparisons']) == 9
        snapshots.append(dict(identity=identity(row), **mean['dals_snapshot']))
    old_actions = []
    for rep in range(3):
        p = root/f'.trellis/tasks/09-06-bottleneck-diagnostics/research/runtime/i3-rep{rep}/frames.jsonl'
        old_actions.extend(json.loads(line) for line in p.read_text().splitlines())
    assert len(old_actions) == 24 and all(len(row['local_actions']) == 97 for row in old_actions)
    report = dict(scope='read-only existing raw evidence; no new receiver',
        gain=dict(frames=192, exact_original_sigma=192, exact_original_H_hash=192,
                  exact_input_and_old_errors=192, old_wrong=sum(row['old_info_errors']>0 for row in gain),
                  new_wrong=sum(row['info_errors']>0 for row in gain), intervention='fixed sigma, terminal H-only oracle'),
        B0=dict(arm='a0', frames=192, wrong=sum(row['arms']['a0']['info_errors']>0 for row in fit.values()),
                terminal_H_values_available=False, source='fit192 raw; output hashes only'),
        mechanism=dict(frames=48, score_tables=96, candidate_rows=9207, state_relations=dict(relations),
                       stage='two t=0 repair rounds, not feedback outer', table_keys=sorted(tables[0])),
        feedback=dict(frames=48, states_per_frame=9, snapshot_count=len(snapshots),
                      stage='f_mean pre-DA-LS outer1..9; not B0 trajectory'),
        old_pool=dict(frames=24, actions_per_frame=97, scope='old truth-capacity shell only'),
        gaps=[dict(item='B0 and new simple terminal tensor states', remedy='capture in authorized BASE-04 fit; B0 gap cap192'),
              dict(item='B0 t0/3/6 common trajectory', remedy='do not relabel f_mean; up to48 missing-trajectory frames'),
              dict(item='specific fixed-H sigma-only results', remedy='search remote original result metadata before SIGMA'),
              dict(item='high-confidence wrong subgroup variance/error sums', remedy='read existing full f_mean snapshots first')],
        sources=[dict(path=str((old/name).relative_to(root)),sha256=sha(old/name)) for name in names],
        old_budget=dict(path=str((old/'stage-budget.json').relative_to(root)),sha256=sha(old/'stage-budget.json'),
                        disposition='frozen unresolved old continuous window; no balance transferred into v3'),
        source_code=[dict(path=str(p.relative_to(root)),sha256=sha(p))
                     for p in sorted((root/'afdm_sp_joint_unrolled').rglob('*.py'))],
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        execution_performed=False)
    (out/'EVID-01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'feedback-snapshots.json').write_text(json.dumps(snapshots,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_code','sources')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
