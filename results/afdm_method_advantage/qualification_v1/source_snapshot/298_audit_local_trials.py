"""Post-qualification, zero-receiver audit of the frozen local trial schedule.

The successful Stage-0 receipt stays immutable.  This check starts each saved
LOCAL/GLOBAL arm at its *local-phase entering geometry* and executes only the
two common local coordinate passes.  No global score grid or decoder is rerun.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import geometry_validation as kernel  # noqa: E402
import qualify_validation as qualification  # noqa: E402
from audit_io import load_bound, sha256, write_csv, write_json  # noqa: E402


def _same(label, actual, expected):
    left, right = np.asarray(actual), np.asarray(expected)
    if left.shape != right.shape or not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError(f'{label}: shape/finiteness differs')
    gap = float(np.max(np.abs(left-right))) if left.size else 0.
    if gap > qualification.ATOL:
        raise AssertionError(f'{label}: max_abs={gap:.17g} exceeds {qualification.ATOL:.17g}')
    return gap


def compare_local(label, result, saved):
    """Compare every local trial and the final common-local state at 2e-10."""
    current, old = result.local_trace, saved['local_trace']
    if len(current) != len(old) or not current:
        raise AssertionError(f'{label}: local coordinate count differs')
    max_trial_score = max_trial_doppler = 0.
    trial_count = 0
    for index, (new, prior) in enumerate(zip(current, old)):
        for key in ('pass_index', 'slot', 'accepted', 'trial_count',
                    'rejected_duplicate_trials', 'local_phase_entering_paths'):
            if new[key] != prior[key]:
                raise AssertionError(f'{label}: local {index}/{key} differs')
        for key in ('center', 'bounds', 'start_objective', 'endpoint_objective'):
            _same(f'{label}/local{index}/{key}', new[key], prior[key])
        for key in ('start', 'endpoint'):
            if new[key]['delay'] != prior[key]['delay']:
                raise AssertionError(f'{label}: local {index}/{key} delay differs')
            _same(f'{label}/local{index}/{key}/doppler',
                  new[key]['doppler'], prior[key]['doppler'])
        if len(new['trials']) != len(prior['trials']) or len(new['trials']) != new['trial_count']:
            raise AssertionError(f'{label}: local {index} trial count differs')
        for trial_index, (a, b) in enumerate(zip(new['trials'], prior['trials'])):
            if a['valid'] != b['valid']:
                raise AssertionError(f'{label}: local {index}/{trial_index} validity differs')
            max_trial_doppler = max(max_trial_doppler, _same(
                f'{label}/local{index}/trial{trial_index}/doppler',
                a['doppler'], b['doppler']))
            if a['valid']:
                max_trial_score = max(max_trial_score, _same(
                    f'{label}/local{index}/trial{trial_index}/score',
                    a['score'], b['score']))
            elif a['score'] is not None or b['score'] is not None:
                raise AssertionError(f'{label}: local {index}/{trial_index} invalid score differs')
            trial_count += 1
    if [p.delay for p in result.paths] != [int(p['delay']) for p in saved['paths']]:
        raise AssertionError(f'{label}: final delay differs')
    final_doppler_gap = _same(f'{label}/final_doppler',
        [p.doppler for p in result.paths], [p['doppler'] for p in saved['paths']])
    final_gain_gap = _same(f'{label}/final_gain', result.gains, saved['gains'])
    final_objective_gap = _same(f'{label}/final_objective',
                                result.objective_after, saved['objective_after'])
    return dict(local_coordinates=len(current), local_trials=trial_count,
        max_trial_doppler_abs=max_trial_doppler,
        max_trial_score_abs=max_trial_score,
        final_doppler_abs=final_doppler_gap,
        final_gain_abs=final_gain_gap,
        final_objective_abs=final_objective_gap)


def audit(args):
    args.run, args.source, args.baseline = (p.resolve() for p in
                                          (args.run, args.source, args.baseline))
    args.a_receipt, args.prior_observed, args.qualification, args.out = (
        p.resolve() for p in (args.a_receipt, args.prior_observed,
                              args.qualification, args.out))
    if args.out.exists():
        raise FileExistsError('local-trial audit output exists')
    for protected in (args.run, args.source, args.baseline,
                      args.prior_observed, args.qualification.parent, HERE):
        if args.out == protected or protected in args.out.parents:
            raise ValueError('local-trial output would modify protected input tree')
    args.out.mkdir(parents=True)
    stage = 'binding'
    try:
        receipt = json.loads(args.qualification.read_text())
        if (receipt.get('status') != 'pass' or receipt.get('receiver_calls') != 0
                or receipt.get('qualified_entered_states') != 145
                or any(receipt.get('source_hashes', {}).get(name) != sha256(HERE/name)
                       for name in ('geometry_validation.py', 'compact_state.py',
                                    'qualify_validation.py'))
                or any(sha256(args.qualification.parent/name) != digest
                       for name, digest in receipt.get('files', {}).items())):
            raise ValueError('successful frozen Stage-0 receipt or files differ')
        evidence, _, system, selection = qualification._bound_inputs(args)
        rows = [json.loads(line) for line in
                (args.prior_observed/'ledger.jsonl').read_text().splitlines()]
        by_key = {(row['observation_id'], row['arm']):row for row in rows}
        if len(by_key) != 150:
            raise ValueError('prior paired ledger allocation differs')
        results = []
        stage = 'local_trial_replay'
        for selected in selection:
            stem = selected['observation_id']
            obs = load_bound(evidence, args.run/'frames'/f'{stem}_input.npz',
                             selected['input_sha256'])
            for arm in ('LOCAL20', 'GLOBAL20'):
                row = by_key[(stem, arm)]
                raw = load_bound(evidence,
                    args.prior_observed/row['raw_path'], row['raw_sha256'])
                Y, x, v, _ = qualification._state(obs, raw, system, kernel)
                saved = raw['geometry_result']
                if not saved['local_trace']:
                    raise ValueError(f'{stem}/{arm}: no saved local phase')
                entering = saved['local_trace'][0]['local_phase_entering_paths']
                if any(item['local_phase_entering_paths'] != entering
                       for item in saved['local_trace']):
                    raise ValueError(f'{stem}/{arm}: local window entering state differs')
                paths = [kernel.Path(int(p['delay']), float(p['doppler']))
                         for p in entering]
                fresh = kernel.reopen_geometry(Y, x, v, paths,
                    c1=system['c1'], c2=system['c2'],
                    ridge=float(obs['sigma2']),
                    **qualification.CONFIG, max_edits=0, local_passes=2,
                    strategy='direct')
                check = compare_local(f'{stem}/{arm}', fresh, saved)
                results.append(dict(observation_id=stem, arm=arm, **check))
        if len(results) != 150:
            raise ValueError('local-trial audit did not cover 75 paired states')
        write_csv(args.out/'local_trial_checks.csv', results)
        response = dict(status='pass', receiver_calls=0, global_score_steps_rerun=0,
            checked_frames=75, checked_arm_states=150,
            checked_local_coordinates=sum(r['local_coordinates'] for r in results),
            checked_local_trials=sum(r['local_trials'] for r in results),
            max_trial_score_abs=max(r['max_trial_score_abs'] for r in results),
            max_trial_doppler_abs=max(r['max_trial_doppler_abs'] for r in results),
            max_final_gain_abs=max(r['final_gain_abs'] for r in results),
            qualification_receipt_sha256=sha256(args.qualification),
            prior_observed_seal_sha256=sha256(args.prior_observed/'observed_seal.json'),
            original_manifest_sha256=sha256(args.run/'manifest.json'),
            source_hashes={name:sha256(HERE/name) for name in (
                'audit_local_trials.py', 'geometry_validation.py',
                'compact_state.py', 'qualify_validation.py')},
            files={'local_trial_checks.csv':sha256(args.out/'local_trial_checks.csv')})
        write_json(args.out/'receipt.json', response)
        return response
    except BaseException as error:
        write_json(args.out/'receipt.json', dict(status='fail', receiver_calls=0,
            failed_stage=stage, exception_type=type(error).__name__, reason=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'source', 'baseline', 'a-receipt', 'prior-observed',
                 'qualification', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    result = audit(parser.parse_args())
    print(json.dumps(dict(status=result['status'], receiver_calls=0,
                          checked_arm_states=result['checked_arm_states'])))


if __name__ == '__main__':
    main()
