"""Zero-receiver CSTATE qualification against immutable prior geometry evidence.

This reads observations and saved APP state only. It never opens truth, calls a
decoder, or changes the original/reference files. Failure leaves a fresh,
explicitly failed qualification receipt and prevents the campaign gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
AUDIT = EXPERIMENTS / 'tf_production_gap_audit_20260922'
PRIOR_CODE = EXPERIMENTS / 'tf_geometry_reopen_20260922'
sys.path[:0] = [str(AUDIT), str(PRIOR_CODE), str(HERE)]
import audit_io  # noqa: E402
import run_reopening as prior_runner  # noqa: E402

PRIOR_SEAL_SHA256 = '98e741ce5e827bf31e62e76e613a6719444fc81e6d47a9d2029c923b0bb912a8'
PRIOR_KERNEL_SHA256 = 'ad888de73a906d4167938a3391c288db68dd7edb4ec42da0d2e4598079ecf633'
ATOL = 2e-10
CONFIG = dict(max_delay=102, doppler_min=-3., doppler_max=3., grid_step=.25,
              chunk_size=64, local_halfwidth=.75, local_max_evals=16,
              duplicate_tolerance=1e-6, top_k=20)


def _numeric(label, actual, expected, *, tolerance=ATOL):
    a, b = np.asarray(actual), np.asarray(expected)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError(f'{label}: shape or finite-value mismatch')
    difference = float(np.max(np.abs(a-b))) if a.size else 0.
    if difference > tolerance:
        raise AssertionError(f'{label}: max_abs={difference:.17g} > {tolerance:.17g}')
    return difference


def _atom(item):
    return (int(item['delay']), float(item['doppler']))


def _choice(item):
    return None if item is None else (int(item['slot']), _atom(item['replacement']))


def compare_trace(label, actual, saved):
    """All slot×atom scores and the executed lexsort/guard choice."""
    if (not np.array_equal(actual['candidate_delays'], saved['candidate_delays'])
            or not np.array_equal(actual['candidate_dopplers'], saved['candidate_dopplers'])
            or not np.array_equal(actual['valid'], saved['valid'])):
        raise AssertionError(f'{label}: candidate bank or validity mask differs')
    mask = np.asarray(saved['valid'], bool)
    actual_scores = np.asarray(actual['scores'])
    saved_scores = np.asarray(saved['scores'])
    if (actual_scores.shape != mask.shape or saved_scores.shape != mask.shape
            or not np.isfinite(actual_scores).all() or not np.isfinite(saved_scores).all()):
        raise ValueError(f'{label}: score shape or finiteness differs')
    maximum = _numeric(label+'/valid_scores', actual_scores[mask], saved_scores[mask])
    if _choice(actual['selected']) != _choice(saved['selected']):
        raise AssertionError(f'{label}: selected slot/atom differs')
    if len(actual['top_k']) != len(saved['top_k']):
        raise AssertionError(f'{label}: top20 count differs')
    for index, (got_top, old_top) in enumerate(zip(actual['top_k'], saved['top_k'])):
        if (int(got_top['rank']), int(got_top['slot']), _atom(got_top['replacement']),
                got_top['paths']) != (int(old_top['rank']), int(old_top['slot']),
                                     _atom(old_top['replacement']), old_top['paths']):
            raise AssertionError(f'{label}: top20 geometry/order differs at rank {index+1}')
        _numeric(f'{label}/top20_score_{index+1}',
                 got_top['frozen_score'], old_top['frozen_score'])
    got, old = actual['accepted'], saved['accepted']
    if (got is None) != (old is None):
        raise AssertionError(f'{label}: accepted/no-improvement differs')
    optimum_difference = 0.
    if got is not None:
        if (int(got['slot']), _atom(got['new'])) != (int(old['slot']), _atom(old['new'])):
            raise AssertionError(f'{label}: accepted replacement differs')
        optimum_difference = _numeric(label+'/direct_refit_optimum',
                                      got['direct_score'], old['direct_score'])
    entering_difference = _numeric(label+'/entering_objective',
                                   actual['entering_objective'], saved['entering_objective'])
    return dict(score_max_abs=maximum, direct_optimum_abs=optimum_difference,
                entering_objective_abs=entering_difference,
                valid_slot_tests=int(np.count_nonzero(saved['valid'])),
                accepted=got is not None)


def compare_final(label, actual, saved):
    """Compare the complete shared-local endpoint, retaining gain sensitivity."""
    actual_paths = [(int(p.delay), float(p.doppler)) for p in actual.paths]
    saved_paths = [_atom(p) for p in saved['paths']]
    if [p[0] for p in actual_paths] != [p[0] for p in saved_paths]:
        raise AssertionError(f'{label}: final delays differ')
    doppler = _numeric(label+'/final_dopplers', [p[1] for p in actual_paths],
                       [p[1] for p in saved_paths])
    objective = _numeric(label+'/final_objective', actual.objective_after,
                         saved['objective_after'])
    initial_objective = _numeric(label+'/initial_objective', actual.objective_before,
                                 saved['objective_before'])
    gains = _numeric(label+'/final_gains', actual.gains, saved['gains'])
    old_edits = [(int(e['slot']), _atom(e['new'])) for e in saved['edits']]
    new_edits = [(int(e['slot']), _atom(e['new'])) for e in actual.edits]
    if new_edits != old_edits:
        raise AssertionError(f'{label}: complete discrete edit sequence differs')
    if len(actual.global_trace) != len(saved['global_trace']):
        raise AssertionError(f'{label}: global step count differs')
    return dict(doppler_max_abs=doppler, objective_abs=objective,
                initial_objective_abs=initial_objective,
                gain_max_abs=gains, accepted_edits=len(new_edits),
                geometry_seconds=float(actual.diagnostics['stage_timing']['total_seconds']),
                numerical_fallback=bool(actual.diagnostics.get('numerical_fallback', False)),
                fallback_reason=actual.diagnostics.get('fallback_reason'))


def near_tie_fixture(kernel):
    """Pin the executed full-grid score/slot/delay/nu ordering and guard."""
    current = [kernel.Path(3, 0.), kernel.Path(4, 0.)]
    delays = np.array([1, 2], dtype=np.int32)
    nus = np.array([0., 0.])
    valid = np.ones((2, 2), bool)
    scores = np.array([[1.+5e-11, 4.], [1., 3.]])
    winner, selected, top = kernel._select(scores, valid, delays, nus, current, 4)
    if winner != 2 or _choice(selected) != (1, (1, 0.)) or [e['rank'] for e in top] != [1, 2, 3, 4]:
        raise AssertionError('executed near-tie lexsort ordering differs')
    if kernel._improvement(1.+5e-11, 1.) or not kernel._improvement(1.+5e-9, 1.):
        raise AssertionError('executed 1e-10 incumbent guard differs')
    return dict(winner_flat_index=winner, selected_slot=selected['slot'],
                near_tie_delta=5e-11, improvement_guard='1e-10*(1+abs(before))')


def run_reference(out):
    """Execute byte-identical reference scripts in a copied output directory."""
    original = HERE / 'reference'
    scratch = out / 'reference_execution'
    scratch.mkdir()
    sources = {}
    for path in sorted(original.iterdir()):
        if path.is_file():
            shutil.copyfile(path, scratch/path.name)
            sources[path.name] = audit_io.sha256(path)
            if audit_io.sha256(scratch/path.name) != sources[path.name]:
                raise AssertionError(f'reference copy differs: {path.name}')
    runs = []
    for name in ('verify_and_probe.py', 'limiting_cases.py'):
        command = [sys.executable, '-B', name]
        started = time.perf_counter()
        with (scratch/(name+'.stdout.log')).open('w') as stdout, \
                (scratch/(name+'.stderr.log')).open('w') as stderr:
            completed = subprocess.run(command, cwd=scratch, stdout=stdout,
                                       stderr=stderr, timeout=600, check=False)
        runs.append(dict(script=name, argv=command, exit_code=completed.returncode,
                         elapsed_seconds=time.perf_counter()-started))
        if completed.returncode:
            raise RuntimeError(f'unmodified reference {name} failed; see reference_execution logs')
    verify = json.loads((scratch/'verification_and_probe_results.json').read_text())
    limiting = json.loads((scratch/'limiting_case_results.json').read_text())
    extreme = next(row for row in limiting if row['name'] == 'tiny_ridge_nearly_duplicate')
    if (not extreme.get('guarded_fallback') or not extreme.get('guarded_paths_equal_control')
            or ('guarded_gain_maxdiff' in extreme and extreme['guarded_gain_maxdiff'] > ATOL)
            or (extreme['status'] == 'computed' and extreme['max_objective_discrepancy'] <= ATOL)):
        raise AssertionError('extreme unguarded distortion/guarded fallback contract differs')
    for name in ('known_waveform_same_delay', 'uninformative_zero_mean'):
        row = next(item for item in limiting if item['name'] == name)
        if row['status'] != 'computed' or row['max_objective_discrepancy'] >= 1e-8:
            raise AssertionError(f'ordinary reference limiting case failed: {name}')
    return dict(source_hashes=sources, subprocesses=runs,
                verification=verify['verification'],
                extreme_unguarded=dict(status=extreme['status'],
                    max_objective_discrepancy=extreme.get('max_objective_discrepancy'),
                    explicit_numerical_failure=extreme.get('exception'),
                    guarded_fallback=extreme['guarded_fallback'],
                    guarded_paths_equal_control=extreme['guarded_paths_equal_control']))


def _assert_original_file_hashes(prior_manifest, run):
    for label, key, name in (
            ('ledger', 'original_ledger_sha256', 'ledger.jsonl'),
            ('context', 'original_context_header_sha256', 'context_header.json')):
        if prior_manifest.get(key) != audit_io.sha256(run/name):
            raise ValueError(f'prior observed manifest does not bind original {label}')


def _bound_inputs(args):
    prior = args.prior_observed.resolve()
    prior_runner.verify_seal(prior)
    if audit_io.sha256(prior/'observed_seal.json') != PRIOR_SEAL_SHA256:
        raise ValueError('prior observed seal differs from fixed validation source')
    prior_manifest = json.loads((prior/'manifest.json').read_text())
    original = json.loads((args.run/'manifest.json').read_text())
    _assert_original_file_hashes(prior_manifest, args.run)
    evidence = audit_io.attach(args.source, args.baseline)
    audit_io.verify_sources(original, args.source, args.baseline, evidence)
    receipt = json.loads(args.a_receipt.read_text())
    if (receipt.get('status') != 'pass'
            or receipt.get('manifest_sha256') != audit_io.sha256(args.run/'manifest.json')
            or receipt.get('ledger_sha256') != audit_io.sha256(args.run/'ledger.jsonl')
            or prior_manifest.get('original_manifest_sha256') != receipt['manifest_sha256']
            or prior_manifest.get('a_receipt_sha256') != audit_io.sha256(args.a_receipt)
            or prior_manifest.get('selection_sha256') != audit_io.sha256(prior/'selection.json')
            or prior_manifest.get('common_config_sha256') !=
               evidence.canonical_hash(prior_manifest.get('common_config'))
            or prior_manifest.get('common_config', {}).get('geometry', {}).get('top_k') != 20
            or prior_manifest.get('common_config', {}).get('arm_max_edits') !=
               {'LOCAL20':0, 'GLOBAL20':2}
            or prior_manifest.get('frozen_source_hashes') != original['source_hashes']
            or prior_manifest.get('frozen_baseline_hashes') != original['baseline_source_hashes']
            or prior_manifest.get('code_hashes', {}).get('tf_geometry_reopen_20260922/geometry_reopen.py') != PRIOR_KERNEL_SHA256
            or audit_io.sha256(PRIOR_CODE/'geometry_reopen.py') != PRIOR_KERNEL_SHA256):
        raise ValueError('original/prior source or selection binding differs')
    for relative, digest in prior_manifest['code_hashes'].items():
        if audit_io.sha256(EXPERIMENTS/relative) != digest:
            raise ValueError(f'prior observed numerical source changed: {relative}')
    cache = (args.baseline/'upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled'
             /'e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz')
    if audit_io.sha256(cache) != receipt['ldpc_cache_sha256'] or \
            audit_io.sha256(cache) != prior_manifest['cache_sha256']:
        raise ValueError('actual LDPC cache changed')
    with np.load(cache, allow_pickle=False) as archive:
        H = np.asarray(archive['H'])
        G = np.asarray(archive['G'])
    header = json.loads((args.run/'context_header.json').read_text())
    if hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() != header['code_g_sha256']:
        raise ValueError('actual LDPC generator changed')
    selected = prior_runner.select_observations(args.run, evidence, H)
    selection = [dict(observation_id=s['observation_id'], kind=s['kind'],
                      final_syndrome_weight=s['final_syndrome_weight'],
                      input_sha256=s['record']['input_sha256'],
                      original_checkpoint_sha256=[cp['artifact_sha256']
                          for cp in s['record']['checkpoints']]) for s in selected]
    if selection != json.loads((prior/'selection.json').read_text()):
        raise ValueError('selected 75 observations differ from prior sealed run')
    return evidence, prior_manifest, header['system'], selection


def _state(observation, raw, system, kernel):
    from messages import moments
    from physical import daft

    arrays = raw['baseline_arrays']
    app = np.clip(arrays['r1_app'], -20, 20)
    prior = np.clip(arrays['r1_check'], -20, 20)
    mu, variance, _ = moments(app, 1-float(system['rho']))
    if (not np.array_equal(app, raw['app_input'])
            or not np.array_equal(prior, raw['check_prior'])
            or not np.array_equal(mu, raw['ce_mu'])
            or not np.array_equal(variance, raw['ce_variance'])):
        raise ValueError('prior branch APP/check state differs from saved native replay')
    initial = [kernel.Path(int(path['delay']), float(path['doppler']))
               for path in raw['initial_paths']]
    if len(initial) != len(raw['initial_inference_gains']):
        raise ValueError('prior physical slots and gains differ')
    Y = daft(observation['y'], system['c1'], system['c2'], True)
    return Y, observation['pilot']+mu, variance, initial


def _cost(values):
    array = np.asarray(values, float)
    if not len(array) or not np.isfinite(array).all() or np.any(array < 0):
        raise ValueError('invalid stage timing sample')
    return dict(count=len(array), mean_seconds=float(np.mean(array)),
                p95_seconds=float(np.percentile(array, 95)),
                max_seconds=float(np.max(array)))


def qualify(args):
    args.run, args.source, args.baseline = (path.resolve() for path in
                                          (args.run, args.source, args.baseline))
    args.a_receipt, args.prior_observed, args.out = (path.resolve() for path in
                                                   (args.a_receipt, args.prior_observed, args.out))
    if args.out.exists():
        raise FileExistsError('qualification output already exists')
    for protected in (args.run, args.source, args.baseline, args.prior_observed, HERE):
        if args.out == protected or protected in args.out.parents:
            raise ValueError('qualification output would modify protected input tree')
    args.out.mkdir(parents=True)
    stage = 'input_binding'
    try:
        evidence, previous_manifest, system, selection = _bound_inputs(args)
        import geometry_validation as kernel
        source_hashes = {name:audit_io.sha256(HERE/name) for name in
                         ('geometry_validation.py', 'compact_state.py', 'qualify_validation.py')}
        stage = 'reference_execution'
        reference = run_reference(args.out)
        near_tie = near_tie_fixture(kernel)
        prior_rows = [json.loads(line) for line in
                      (args.prior_observed/'ledger.jsonl').read_text().splitlines()]
        rows = {(r['observation_id'], r['arm']):r for r in prior_rows}
        if len(rows) != 150 or set(rows) != {(s['observation_id'], arm)
                                            for s in selection for arm in ('LOCAL20', 'GLOBAL20')}:
            raise ValueError('prior observed ledger allocation differs')
        state_rows, final_rows = [], []
        stage = 'entered_state_qualification'
        for selected in selection:
            stem = selected['observation_id']
            observation = audit_io.load_bound(evidence,
                args.run/'frames'/f'{stem}_input.npz', selected['input_sha256'])
            by_arm = {}
            for arm in ('LOCAL20', 'GLOBAL20'):
                prior_row = rows[(stem, arm)]
                raw = audit_io.load_bound(evidence,
                    args.prior_observed/prior_row['raw_path'], prior_row['raw_sha256'])
                if raw['observation_id'] != stem or raw['arm'] != arm:
                    raise ValueError('prior raw arm identity differs')
                by_arm[arm] = raw
            Y, x, v, initial = _state(observation, by_arm['GLOBAL20'], system, kernel)
            old_global = by_arm['GLOBAL20']['geometry_result']
            if (not old_global['global_trace']
                    or [(p.delay, p.doppler) for p in initial] !=
                       [_atom(p) for p in old_global['global_trace'][0]['entering_paths']]
                    or by_arm['LOCAL20']['initial_paths'] != by_arm['GLOBAL20']['initial_paths']
                    or not np.array_equal(by_arm['LOCAL20']['app_input'], by_arm['GLOBAL20']['app_input'])
                    or not np.array_equal(by_arm['LOCAL20']['check_prior'], by_arm['GLOBAL20']['check_prior'])):
                raise ValueError('prior paired/native entering state differs')
            for saved in old_global['global_trace']:
                label = f'{stem}/global_step{saved["step"]}'
                entered = [kernel.Path(int(p['delay']), float(p['doppler']))
                           for p in saved['entering_paths']]
                kwargs = dict(CONFIG, c1=system['c1'], c2=system['c2'],
                              ridge=float(observation['sigma2']))
                for strategy in ('direct', 'compact'):
                    actual, result = kernel.score_entering_state(
                        Y, x, v, entered, strategy=strategy, **kwargs)
                    comparison = compare_trace(label+'/'+strategy, actual, saved)
                    timing = result.diagnostics['stage_timing']['exclusive_seconds']
                    state_rows.append(dict(observation_id=stem, step=int(saved['step']),
                        strategy=strategy, **comparison,
                        numerical_fallback=bool(result.diagnostics.get('numerical_fallback', False)),
                        fallback_reason=result.diagnostics.get('fallback_reason'),
                        total_seconds=float(result.diagnostics['stage_timing']['total_seconds']),
                        **{f'stage_{name}_seconds':float(value) for name, value in timing.items()}))
            stage = 'full_geometry_qualification'
            for arm in ('LOCAL20', 'GLOBAL20'):
                raw = by_arm[arm]
                Y, x, v, initial = _state(observation, raw, system, kernel)
                kwargs = dict(CONFIG, c1=system['c1'], c2=system['c2'],
                              ridge=float(observation['sigma2']),
                              max_edits=0 if arm == 'LOCAL20' else 2,
                              local_passes=2)
                old = raw['geometry_result']
                for strategy in (('direct', 'compact') if arm == 'GLOBAL20' else ('direct',)):
                    actual = kernel.reopen_geometry(Y, x, v, initial,
                                                    strategy=strategy, **kwargs)
                    comparison = compare_final(f'{stem}/{arm}/{strategy}', actual, old)
                    timing = actual.diagnostics['stage_timing']['exclusive_seconds']
                    final_rows.append(dict(observation_id=stem, arm=arm,
                        strategy=strategy, **comparison,
                        **{f'stage_{name}_seconds':float(value) for name, value in timing.items()}))
            stage = 'entered_state_qualification'
        if len(state_rows) != 290 or sum(r['strategy']=='compact' for r in state_rows) != 145:
            raise ValueError('prior GLOBAL entering-state count differs from declared 145')
        if len(final_rows) != 225:
            raise ValueError('75 LOCAL direct plus 75 GLOBAL direct/compact missing')
        audit_io.write_csv(args.out/'entered_states.csv', state_rows)
        audit_io.write_csv(args.out/'full_geometry.csv', final_rows)
        stage_names = sorted(name for name in final_rows[0] if name.startswith('stage_'))
        costs = {f'{row_arm}/{strategy}':{name:_cost([r[name] for r in final_rows
                                      if r['arm']==row_arm and r['strategy']==strategy])
                 for name in ['geometry_seconds', *stage_names]}
                 for row_arm, strategy in (('LOCAL20', 'direct'), ('GLOBAL20', 'direct'),
                                           ('GLOBAL20', 'compact'))}
        receipt = dict(status='pass', receiver_calls=0,
            original_manifest_sha256=audit_io.sha256(args.run/'manifest.json'),
            a_receipt_sha256=audit_io.sha256(args.a_receipt),
            prior_observed_seal_sha256=audit_io.sha256(args.prior_observed/'observed_seal.json'),
            prior_selection_sha256=audit_io.sha256(args.prior_observed/'selection.json'),
            prior_kernel_sha256=PRIOR_KERNEL_SHA256, source_hashes=source_hashes,
            qualified_entered_states=145, near_tie=near_tie, reference=reference,
            compact_entered_state_fallbacks=sum(r['numerical_fallback'] for r in state_rows
                                                if r['strategy']=='compact'),
            compact_full_geometry_fallbacks=sum(r['numerical_fallback'] for r in final_rows
                                                if r['strategy']=='compact'),
            max_score_abs=max(r['score_max_abs'] for r in state_rows),
            max_direct_optimum_abs=max(r['direct_optimum_abs'] for r in state_rows),
            max_final_doppler_abs=max(r['doppler_max_abs'] for r in final_rows),
            max_final_objective_abs=max(r['objective_abs'] for r in final_rows),
            max_initial_objective_abs=max(r['initial_objective_abs'] for r in final_rows),
            max_final_gain_abs=max(r['gain_max_abs'] for r in final_rows),
            stage_costs=costs, original_cache_sha256=previous_manifest['cache_sha256'],
            reference_execution_hashes={str(p.relative_to(args.out)):audit_io.sha256(p)
                for p in (args.out/'reference_execution').rglob('*') if p.is_file()},
            files={p.name:audit_io.sha256(p) for p in args.out.iterdir() if p.is_file()})
        audit_io.write_json(args.out/'receipt.json', receipt)
        return receipt
    except BaseException as error:
        audit_io.write_json(args.out/'receipt.json', dict(status='fail', receiver_calls=0,
            failed_stage=stage, exception_type=type(error).__name__, reason=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'source', 'baseline', 'a-receipt', 'prior-observed', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    receipt = qualify(parser.parse_args())
    print(json.dumps(dict(status=receipt['status'], receiver_calls=0,
                          qualified_entered_states=receipt['qualified_entered_states'])))


if __name__ == '__main__':
    main()
