"""Retrospective checkpoints: observable syndrome and explicitly offline errors.

No fresh receiver or decoder execution. Reuse restore() for selected arrays
after verifying the complete immutable NPZ file and field inventory.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from afdm_sp_joint_unrolled.bottleneck_pilot import sha, restore, hashes
from afdm_sp_joint_unrolled.light_gap_replay import CODE_KEYS
from afdm_sp_joint_unrolled.e1_ldpc import build_code


def selected(artifact, fields):
    path = Path(artifact['file']['path'])
    assert sha(path) == artifact['file']['sha256']
    with np.load(path, allow_pickle=False) as arrays:
        assert set(arrays.files) == set(artifact['file']['fields'])
        return restore({k: artifact['metadata'][k] for k in fields}, arrays)


def analyze(root, cache):
    cache.mkdir()
    code = build_code(cache_dir=cache)
    rows, bindings = [], {}
    for tag, audit_name, arms, expected_hash in (
        ('refs-v1', 'refs-v1-development-audit.json', ['MEAN', 'REFRESH47'],
         '90cbc1f7a94e482deec27e091945d79615302d79bd480947e51697655a05554b'),
        ('siso-development-v1', 'siso-development-v1-raw-audit.json', ['SISO_MEAN', 'SISO_REF47'],
         '1f88d1bb5df7478882fcece579ba05e857bc2c92532ffb21401ed948dc7736c9')):
        path = root/'runs'/tag/'development/summary.json'
        assert sha(path) == expected_hash
        summary = json.loads(path.read_text())
        audit_path = root/'evidence'/audit_name
        audit = json.loads(audit_path.read_text())
        assert audit['status'] == 'PASS' and audit['summary_sha256'] == expected_hash
        env = json.loads(path.with_name('environment.json').read_text())
        assert hashes({k: code[k] for k in CODE_KEYS}) == env['code_identity']
        exo = {r['block']: r for r in summary['exogenous']}
        bindings[tag] = dict(summary_sha256=expected_hash, audit_sha256=sha(audit_path))
        for entry in summary['records']:
            if entry['arm'] not in arms:
                continue
            record_path = Path(entry['record'])
            assert record_path.resolve().is_relative_to(root.resolve()) and sha(record_path) == entry['sha256']
            record = json.loads(record_path.read_text())
            assert all(record[k] == entry[k] for k in ('block', 'snr', 'arm', 'split', 'scores'))
            value = selected(record['state'], ['code_feedback_records'])
            truth = selected(exo[entry['block']]['state'], ['coded'])['coded']
            checkpoints = []
            for state in value['code_feedback_records']:
                if state['stage'] != 'decoder':
                    continue
                app, before, after = (state[k] for k in ('raw_app', 'prior_before', 'prior_after'))
                hard = (app < 0).astype(np.uint8)
                syndrome = np.bincount(code['chk'], weights=hard[code['var']].astype(float),
                                       minlength=code['H'].shape[0]).astype(np.int64) & 1
                checkpoints.append(dict(iteration=state['iteration'], unsatisfied_checks=int(syndrome.sum()),
                    prior_change_rms=float(np.sqrt(np.mean((after-before)**2))),
                    incoming_entropy=state['source']['entropy_bits']['incoming_llr'],
                    app_entropy=state['source']['entropy_bits']['raw_app'],
                    offline_codeword_bit_errors=int(np.count_nonzero(hard != truth))))
            expected = [1, 4, 7] if entry['arm'] in ('REFRESH47', 'SISO_REF47') else [1]
            assert [s['iteration'] for s in checkpoints] == expected
            valid = [s for s in checkpoints if s['unsatisfied_checks'] == 0]
            rows.append(dict(block=entry['block'], snr=entry['snr'], arm=entry['arm'],
                record_sha256=entry['sha256'], terminal_FER=entry['scores']['FER'],
                first_valid_iteration=valid[0]['iteration'] if valid else None,
                first_valid_offline_errors=valid[0]['offline_codeword_bit_errors'] if valid else None,
                checkpoints=checkpoints))
    assert {(r['block'], r['snr'], r['arm']) for r in rows} == {
        (b, s, a) for b in range(32) for s in (7, 8) for a in ('MEAN', 'REFRESH47', 'SISO_MEAN', 'SISO_REF47')}
    table = []
    for snr in (7, 8):
        for arm in ('MEAN', 'REFRESH47', 'SISO_MEAN', 'SISO_REF47'):
            group = [r for r in rows if r['snr'] == snr and r['arm'] == arm]
            valid = [r for r in group if r['first_valid_iteration'] is not None]
            table.append(dict(snr=snr, arm=arm, records=len(group),
                first_valid_counts={str(i): sum(r['first_valid_iteration'] == i for r in group) for i in (1, 4, 7)},
                never_valid_before_terminal=sum(r['first_valid_iteration'] is None for r in group),
                valid_but_wrong=sum(r['first_valid_offline_errors'] > 0 for r in valid),
                valid_then_terminal_failed=sum(r['terminal_FER'] for r in valid),
                terminal_failures=sum(r['terminal_FER'] for r in group)))
    return dict(scope='existing development checkpoint diagnosis; not a new receiver, policy validation or cost result',
                independent_blocks=32, bindings=bindings, rows=rows, table=table,
                offline_truth_use='checkpoint error labels only; syndrome/entropy/prior-change are observation-only')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'cache', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root, args.cache)
    result['script_sha256'] = sha(Path(__file__))
    with args.output.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}))
