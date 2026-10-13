"""O2: one true-data CE per saved FULL work point; truth stays offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np


# Predeclared complex64-vs-double algebra gate; never widen after reading raw.
DTYPE_RELATIVE_TOLERANCE = 2e-5


def energy(v):
    return float(np.vdot(v, v).real)


def account(A, B, c, g, R, H, x, d, mu, noise, solution, *, feedback):
    """Double algebra; original complex64 solution is a separate rounding check."""
    A, B, c, g, R, H, x, d, mu, noise, solution = (
        np.asarray(v, dtype=np.complex128) for v in
        (A, B, c, g, R, H, x, d, mu, noise, solution))
    terms = {
        'map': (B @ A - np.eye(len(g))) @ g + c,
        'tail': B @ (R @ x),
        'noise': B @ noise,
    }
    if feedback:
        terms['feedback'] = B @ (H @ (d - mu))
    # R acts on the design input; the feedback term supplies the full H delta.
    affine = B @ (H @ (x + d - mu) + noise) + c
    reconstructed = sum(terms.values())
    defect = affine - g - reconstructed
    cross = {f'{a}:{b}': 2 * float(np.vdot(terms[a], terms[b]).real)
             for i, a in enumerate(terms) for b in list(terms)[i + 1:]}
    components = sum(energy(v) for v in terms.values()) + sum(cross.values())
    affine_error = energy(affine - g)
    scale = max(1., np.linalg.norm(affine), np.linalg.norm(g))
    if np.linalg.norm(defect) > 2e-10 * scale or abs(components - affine_error) > 2e-9 * max(1., affine_error):
        raise FloatingPointError('affine error accounting does not close')
    rounding = float(np.linalg.norm(solution - affine) / scale)
    if rounding > DTYPE_RELATIVE_TOLERANCE:
        raise FloatingPointError('complex64 saved/actual CE differs from double affine solution')
    return dict(terms=terms, squared={k: energy(v) for k, v in terms.items()},
                cross=cross, affine_solution=affine, affine_error=affine_error,
                actual_error=energy(solution - g), closure_relative=float(np.linalg.norm(defect) / scale),
                dtype_rounding_relative=rounding,
                actual_minus_affine_energy=energy(solution - affine),
                actual_energy_minus_affine=energy(solution - g) - components)


def affine(A, previous, lam):
    A = np.asarray(A, dtype=np.complex128)
    previous = np.asarray(previous, dtype=np.complex128)
    lam = float(lam)
    if not np.isfinite(lam) or lam < 0:
        raise ValueError('invalid proximal regularization')
    M = A.conj().T @ A + lam * np.eye(A.shape[1])
    B = np.linalg.solve(M, A.conj().T)
    c = lam * np.linalg.solve(M, previous)
    return dict(M=M, B=B, c=c, extra_algebra_solves=2)


def schur(A, full, support_ids):
    """One batched algebra solve for candidate Schur complements, no CE."""
    A = np.asarray(A, dtype=np.complex128)
    full = np.asarray(full, dtype=np.complex128)
    ids = np.asarray(support_ids, dtype=int)
    if len(set(ids.tolist())) != len(ids) or full.shape[0] != A.shape[0]:
        raise ValueError('invalid support/full design for Schur')
    remaining = np.setdiff1d(np.arange(full.shape[1]), ids)
    candidate = full[:, remaining]
    gram = A.conj().T @ A
    r = A.conj().T @ candidate
    h = np.sum(abs(candidate)**2, axis=0)
    z = np.linalg.solve(gram, r)
    s = h - np.sum(r.conj() * z, axis=0).real
    if np.any(s < -1e-7 * np.maximum(1, h)):
        raise FloatingPointError('negative Schur complement')
    threshold = np.finfo(float).eps * max(A.shape) * np.maximum(1., h)
    valid = s > threshold
    increment = np.zeros(len(s), dtype=float)
    increment[valid] = (1 + np.sum(abs(z[:, valid])**2, axis=0)) / s[valid]
    if not np.isfinite(increment).all():
        raise FloatingPointError('finite valid Schur increment required')
    return dict(candidate_ids=remaining, cross_gram=r, candidate_energy=h,
                gram_solved_cross=z, schur=np.maximum(s, 0), rank_threshold=threshold,
                increment_valid=valid, increment_invalid_reason='schur_at_or_below_float64_rank_tolerance',
                white_variance_increment=increment,
                extra_algebra_solves=1)


def coefficient_histogram(g, old, new, ids):
    bins = np.array([0., .001, .003, .01, .03, .1, .3, 1., np.finfo(float).max])
    return dict(bin_edges=bins, true=np.histogram(abs(g), bins)[0],
                old_error=np.histogram(abs(old - g), bins)[0],
                oracle_error=np.histogram(abs(new - g), bins)[0], support_ids=ids)


def verify_saved(value):
    """Read-only equation audit: no new CE, projection, or candidate solve."""
    g = np.asarray(value['gS'], dtype=np.complex128)
    H = np.asarray(value['H'], dtype=np.complex128)
    HS = np.asarray(value['HS'], dtype=np.complex128)
    R = np.asarray(value['R'], dtype=np.complex128)
    if np.linalg.norm(H - HS - R) > 2e-10 * max(1., np.linalg.norm(H)):
        raise FloatingPointError('saved Frobenius residual does not reconstruct H')
    for arm, key in (('old', 'ordinary'), ('new', 'oracle')):
        A = np.asarray(value['A_' + arm], dtype=np.complex128)
        Aexact = np.asarray(value['A_exact_' + arm], dtype=np.complex128)
        mapping = value[arm + '_affine']
        B, c, M = (np.asarray(mapping[k], dtype=np.complex128) for k in ('B', 'c', 'M'))
        previous = np.asarray(value['previous'], dtype=np.complex128)
        lam = float(value['regularization'])
        if (np.linalg.norm(M - A.conj().T @ A - lam * np.eye(len(g))) > 1e-9 * max(1., np.linalg.norm(M))
                or np.linalg.norm(M @ B - A.conj().T) > 1e-9 * max(1., np.linalg.norm(A))
                or np.linalg.norm(M @ c - lam * previous) > 1e-9 * max(1., np.linalg.norm(previous))):
            raise FloatingPointError('saved affine normal equations differ')
        result = value[key]
        x = np.asarray(value['x_' + arm], dtype=np.complex128)
        delta = np.asarray(value['d'], dtype=np.complex128) - np.asarray(value['mu'], dtype=np.complex128)
        expected = dict(map=(B @ Aexact - np.eye(len(g))) @ g + c,
                        tail=B @ (R @ x), noise=B @ np.asarray(value['noise'], dtype=np.complex128))
        if arm == 'old':
            expected['feedback'] = B @ (H @ delta)
        for name, term in expected.items():
            if np.linalg.norm(np.asarray(result['terms'][name]) - term) > 2e-10 * max(1., np.linalg.norm(term)):
                raise FloatingPointError('saved error term differs: ' + name)
        if set(result['terms']) != set(expected):
            raise ValueError('saved error terms differ')
        for i, a in enumerate(expected):
            if abs(result['squared'][a] - energy(expected[a])) > 1e-8 * max(1., energy(expected[a])):
                raise FloatingPointError('saved term square differs')
            for b in list(expected)[i + 1:]:
                cross = 2 * float(np.vdot(expected[a], expected[b]).real)
                if abs(result['cross'][f'{a}:{b}'] - cross) > 1e-8 * max(1., abs(cross)):
                    raise FloatingPointError('saved cross term differs')
        affine_solution = B @ np.asarray(value['y'], dtype=np.complex128) + c
        actual = np.asarray(value['old_solution' if arm == 'old' else 'oracle_solution'], dtype=np.complex128)
        if (np.linalg.norm(affine_solution - result['affine_solution']) > DTYPE_RELATIVE_TOLERANCE * max(1., np.linalg.norm(affine_solution))
                or abs(result['actual_error'] - energy(actual - g)) > 1e-8 * max(1., result['actual_error'])
                or abs(result['actual_energy_minus_affine'] - (result['actual_error'] - result['affine_error'])) > 1e-8 * max(1., result['actual_error'])):
            raise FloatingPointError('saved actual/affine gain error differs')
        decomposition = sum(expected.values())
        if np.linalg.norm(affine_solution - g - decomposition) > DTYPE_RELATIVE_TOLERANCE * max(1., np.linalg.norm(affine_solution)):
            raise FloatingPointError('saved physical error reconstruction differs')
    Q = np.asarray(value['Q_plugin_mean_unused'])
    variance = np.asarray(value['finite_variance'], dtype=float)
    if (Q.shape != (len(g), len(g)) or not np.isfinite(Q).all()
            or np.linalg.norm(Q - Q.conj().T) > 1e-8 * max(1., np.linalg.norm(Q))
            or np.linalg.norm(Q - variance.sum() * np.eye(len(g))) > 1e-8 * max(1., abs(variance.sum()))
            or np.any(np.asarray(value['Q_true_data_consumed']) != 0)):
        raise ValueError('diagnostic Q differs or deterministic CE consumed variance')
    for name, arm in (('schur_old', 'old'), ('schur_new', 'new')):
        row = value[name]; s = np.asarray(row['schur'])
        q = np.asarray(row['cross_gram']); h = np.asarray(row['candidate_energy'])
        z = np.asarray(row['gram_solved_cross'])
        gram = np.asarray(value['A_' + arm], dtype=np.complex128).conj().T @ np.asarray(value['A_' + arm], dtype=np.complex128)
        calculated = h - np.sum(q.conj() * z, axis=0).real
        valid = np.asarray(row['increment_valid'], dtype=bool)
        threshold = np.asarray(row['rank_threshold'], dtype=float)
        expected_threshold = np.finfo(float).eps * max(np.asarray(value['A_' + arm]).shape) * np.maximum(1., h)
        increment = np.zeros(len(s), dtype=float)
        increment[valid] = (1 + np.sum(abs(z[:, valid])**2, axis=0)) / s[valid]
        if (len(s) != 515 - len(g) or not np.isfinite(s).all() or np.any(s < 0)
                or valid.shape != s.shape or threshold.shape != s.shape
                or not np.allclose(threshold, expected_threshold, rtol=0, atol=0)
                or not np.array_equal(valid, calculated > expected_threshold)
                or row['increment_invalid_reason'] != 'schur_at_or_below_float64_rank_tolerance'
                or np.linalg.norm(gram @ z - q) > 1e-8 * max(1., np.linalg.norm(q))
                or np.linalg.norm(s - np.maximum(calculated, 0)) > 1e-8 * max(1., np.linalg.norm(s))
                or np.linalg.norm(increment - row['white_variance_increment']) > 1e-8 * max(1., np.linalg.norm(increment))):
            raise ValueError('candidate Schur array differs')
    hist = value['coefficient_histogram']
    if any(int(np.asarray(hist[k]).sum()) != len(g) for k in ('true', 'old_error', 'oracle_error')):
        raise ValueError('coefficient histogram misses support atoms')
    return True


def main(args):
    root = args.root.resolve(); source = root / 'source-terminal-controls-unit-v1'
    sys.path.insert(0, str(source))
    import torch
    from afdm_sp_joint_unrolled.bottleneck_pilot import sha, hashes
    from afdm_sp_joint_unrolled.budgeted_support_diagnostics import project_channel_on_support
    from afdm_sp_joint_unrolled.classical_joint_unrolled import (
        build_A_for_DALS_torch, construct_sensing_matrix_torch, data_uncertainty_gram, soft_gain_update)
    from afdm_sp_joint_unrolled.light_gap_replay import LightRun, setup_guard, verified_record
    from afdm_sp_joint_unrolled.supplement_g1 import reuse_at_snr
    from afdm_sp_joint_unrolled.trans_next_siso_audit import finite_arrays

    contract = root / 'contracts' / (args.tag + '.json')
    c = json.loads(contract.read_text()); manifest = source / 'source-manifest.json'
    if (sha(contract) != args.contract_sha256 or sha(Path(__file__)) != args.script_sha256
            or sha(manifest) != c['source_sha256']):
        raise ValueError('contract, script, or source hash differs')
    if (c['schema'] != args.tag or c['tag'] != args.tag or c['blocks'] != list(range(32))
            or c['snrs'] != [7, 8] or c['device'] != 'cpu' or c['threads'] != 1
            or c['bounds'] != dict(E=64, A=64, seconds=7200)
            or c['dtype_relative_tolerance'] != DTYPE_RELATIVE_TOLERANCE
            or c['output_bytes'] > 20 * 1024**3):
        raise ValueError('O2 frozen 64 CE / 64 analysis / 2h / 20GiB contract differs')
    guard = setup_guard(SimpleNamespace(contract=contract, contract_sha256=args.contract_sha256,
        source_manifest=manifest, source_sha256=sha(manifest)), c)
    guard.verify()
    for summary_path, receipt_path in c['audited_inputs'].items():
        receipt = json.loads((root / receipt_path).read_text())
        if receipt['status'] != 'PASS' or receipt['summary_sha256'] != sha(root / summary_path):
            raise ValueError('upstream raw audit receipt differs')
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    upstream = json.loads((root / c['old_summary']).read_text())
    if upstream['status'] != 'COMPLETE' or len(upstream['records']) != 288:
        raise ValueError('old FULL summary incomplete')
    index = {(e['kind'], e['block'], e['snr'], e['arm']): e for e in upstream['records']}
    if len(index) != 288:
        raise ValueError('old summary contains duplicate identities')

    def inputs(block, snr):
        pe = index['A', block, 7, 'G1_PROPAGATION']
        ref = index['F', block, snr, 'G1_FULL']
        _, physical = verified_record(pe, root)
        record, state = verified_record(ref, root)
        raw, _ = reuse_at_snr(physical['raw'], physical['diagnostics'], snr)
        if len(state['dals']) != 9 or [v['outer_iter'] for v in state['dals']] != list(range(1, 10)):
            raise ValueError('FULL CE prefix differs')
        old = state['dals'][-1]
        forbidden = ('Q', 'covariance', 'C', 'consumed_variance')
        if (old['mode'] != 'mean' or old.get('requested_mode') != 'mean'
                or old['oracle_mean'] or old['moment_source'] != 'code_feedback.ce'
                or any(k in old for k in forbidden)):
            raise ValueError('unknown weighted/prior CE state; no mean-mode fallback')
        if old['A'].dtype != np.dtype('complex64') or old['mu'].dtype != np.dtype('complex64'):
            raise ValueError('saved CE dtype differs')
        observed = {k: np.array(raw[k], copy=True) for k in ('y', 'pilot', 'sigma2')}
        observed['constellation'] = np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j])
        if record['observed_hashes'] != hashes(observed):
            raise ValueError('paired observation hash differs')
        return pe, ref, raw, old, state

    def analyze(block, snr, pe, ref, raw, old):
        N = len(raw['pilot']); params = raw['params']; c1, c2 = params['c1'], params['c2']
        if N != 1024 or abs(2 * N * c1 - 5) > 1e-10:
            raise ValueError('old p0/W2 geometry differs')
        delays = np.asarray(old['support_delays'], dtype=np.int64)
        dopplers = np.asarray(old['support_dopplers'], dtype=np.int64)
        ids = delays * 5 + dopplers + 2
        if (len(ids) != 24 or len(set(ids.tolist())) != 24 or np.any(ids < 0)
                or np.any(ids >= 515)):
            raise ValueError('saved active support differs')
        td, tk = torch.from_numpy(delays), torch.from_numpy(dopplers)
        H = np.asarray(raw['H'], dtype=np.complex128)
        HS, g = project_channel_on_support(torch.from_numpy(H), td, tk, c1, c2, 2)
        HS, g = HS.numpy(), g.numpy(); R = H - HS
        p, d = np.asarray(raw['pilot']), np.asarray(raw['data'])
        mu = np.asarray(old['mu']); xold = p + mu; xnew = p + d
        torch_old = torch.as_tensor(p, dtype=torch.complex64) + torch.as_tensor(mu, dtype=torch.complex64)
        torch_new = torch.as_tensor(p, dtype=torch.complex64) + torch.as_tensor(d, dtype=torch.complex64)
        native = build_A_for_DALS_torch(N, td, tk, torch_old, c1, c2, 2,
                                        cdtype=torch.complex64).numpy()
        np.testing.assert_array_equal(native, old['A'])
        Anew = build_A_for_DALS_torch(N, td, tk, torch_new,
                                      c1, c2, 2, cdtype=torch.complex64).numpy()
        Aexact_old = build_A_for_DALS_torch(N, td, tk, torch.as_tensor(xold, dtype=torch.complex128),
                                            c1, c2, 2, cdtype=torch.complex128).numpy()
        Aexact_new = build_A_for_DALS_torch(N, td, tk, torch.as_tensor(xnew, dtype=torch.complex128),
                                            c1, c2, 2, cdtype=torch.complex128).numpy()
        if (np.linalg.norm(Aexact_old @ g - HS @ xold) > 2e-10 * max(1., np.linalg.norm(HS @ xold))
                or np.linalg.norm(Aexact_new @ g - HS @ xnew) > 2e-10 * max(1., np.linalg.norm(HS @ xnew))):
            raise FloatingPointError('double support sensing/projected H action differs')
        noise = np.sqrt(float(raw['sigma2'])) * np.asarray(raw['noise'])
        physical_defect = np.linalg.norm(np.asarray(raw['y']) - H @ xnew - noise)
        if physical_defect > 1e-6 * max(1., np.linalg.norm(raw['y'])):
            raise ValueError('physical y/p+d/noise do not close')
        lam = float(old['regularization']); previous = np.asarray(old['g_previous'])
        old_map, new_map = affine(old['A'], previous, lam), affine(Anew, previous, lam)
        old_result = account(Aexact_old, old_map['B'], old_map['c'], g, R, H, xold, d, mu,
                             noise, old['g_solution'], feedback=True)
        # Q is saved for analysis only. Existing mean CE consumes no finite variance.
        Qplugin = data_uncertainty_gram(N, td, tk, torch.as_tensor(old['finite_variance']),
                                        c1, c2, 2, cdtype=torch.complex128).numpy()
        full_old = construct_sensing_matrix_torch(N, torch_old,
                    c1, c2, 102, 2, cdtype=torch.complex64).numpy()
        full_new = construct_sensing_matrix_torch(N, torch_new,
                    c1, c2, 102, 2, cdtype=torch.complex64).numpy()
        np.testing.assert_allclose(full_old[:, ids], old['A'], rtol=2e-6, atol=2e-6)
        np.testing.assert_allclose(full_new[:, ids], Anew, rtol=2e-6, atol=2e-6)
        return dict(A_old=np.asarray(old['A']), A_new=Anew,
            A_exact_old=Aexact_old, A_exact_new=Aexact_new, y=np.asarray(raw['y']),
            x_old=xold, x_new=xnew, d=d, mu=mu, noise=noise, H=H, HS=HS, R=R, gS=g,
            previous=previous, regularization=np.asarray(old['regularization']),
            finite_variance=np.asarray(old['finite_variance']),
            old_solution=np.asarray(old['g_solution']), old_affine=old_map, new_affine=new_map,
            ordinary=old_result, Q_plugin_mean_unused=Qplugin,
            Q_true_data_consumed=np.zeros_like(Qplugin),
            schur_old=schur(old['A'], full_old, ids), schur_new=schur(Anew, full_new, ids),
            support_ids=ids, reference_record_sha256=ref['sha256'],
            physical_record_sha256=pe['sha256'], physical_y_relative=float(physical_defect / max(1., np.linalg.norm(raw['y']))),
            resource_counts=dict(new_CE=0, old_CE_reused=1, extra_affine_solves=4,
                                 extra_schur_solves=2, new_BP=0, new_LDPC=0, new_F=0))

    def estimate(v):
        actual = soft_gain_update(torch.as_tensor(v['A_new']), torch.as_tensor(v['y'], dtype=torch.complex64),
                    torch.as_tensor(v['previous'], dtype=torch.complex64),
                    torch.as_tensor(v['regularization'], dtype=torch.float32)).numpy()
        result = account(v['A_exact_new'], v['new_affine']['B'], v['new_affine']['c'], v['gS'],
                         v['R'], v['H'], v['x_new'], v['d'], v['d'], v['noise'], actual, feedback=False)
        v = dict(v, oracle_solution=actual, oracle=result,
                 coefficient_histogram=coefficient_histogram(v['gS'], v['old_solution'], actual, v['support_ids']))
        v['resource_counts'] = dict(v['resource_counts'], new_CE=1)
        return v

    def audit_saved(summary):
        from afdm_sp_joint_unrolled.supplement_adjacent_run import flatten
        if summary['status'] != 'COMPLETE' or summary['calls'] != dict(E=64, A=64):
            raise ValueError('O2 run did not complete 64 paired work points')
        entries = summary['records']
        if len(entries) != 128:
            raise ValueError('O2 record count differs')
        rows, arrays, analysis_states = [], 0, {}
        for e in entries:
            record, value = verified_record(e, root)
            reservation = json.loads(Path(e['record']).with_name(record['token'] + '-reserve.json').read_text())
            for k in ('kind', 'block', 'snr', 'arm', 'split'):
                if reservation[k] != record[k] or record[k] != e[k]:
                    raise ValueError('reservation/result identity differs')
            if e['kind'] == 'A':
                if value['resource_counts']['new_CE'] != 0:
                    raise ValueError('analysis consumed CE')
                key = (e['block'], e['snr'])
                if key in analysis_states:
                    raise ValueError('duplicate O2 analysis state')
                analysis_states[key] = sha(Path(record['state']['file']['path']))
                continue
            if e['kind'] != 'E' or e['arm'] != 'TRUE_DATA_FIXED_S_CE':
                raise ValueError('unexpected O2 call kind')
            if record['analysis_record_sha256'] != analysis_states.get((e['block'], e['snr'])):
                raise ValueError('CE result is not bound to its saved analysis state')
            old = value['ordinary']; new = value['oracle']
            verify_saved(value)
            if (old['dtype_rounding_relative'] > DTYPE_RELATIVE_TOLERANCE or new['dtype_rounding_relative'] > DTYPE_RELATIVE_TOLERANCE
                    or len(old['cross']) != 6 or len(new['cross']) != 3):
                raise FloatingPointError('O2 saved closure/dtype contract differs')
            arrays += finite_arrays(value)
            rows.append(dict(block=e['block'], snr=e['snr'], split=e['split'],
                error_before=old['actual_error'], error_after=new['actual_error'],
                absolute_after_minus_before=new['actual_error'] - old['actual_error'],
                reference_record_sha256=value['reference_record_sha256'],
                physical_record_sha256=value['physical_record_sha256']))
        if {(v['block'], v['snr']) for v in rows} != {(b, s) for b in range(32) for s in (7, 8)}:
            raise ValueError('missing O2 work points')
        return dict(rows=rows, arrays=arrays, saved_records=128, new_CE=64,
                    extra_affine_solves=256, extra_schur_solves=128, new_BP=0, new_LDPC=0, new_F=0)

    out = root / 'runs' / args.tag / 'analysis'
    if args.mode == 'audit':
        end = json.loads((root / 'evidence' / (args.tag + '-exit.json')).read_text())
        if end['exit_code'] != 0 or end['timed_out']:
            raise ValueError('producer exit did not succeed')
        summary = json.loads((out / 'summary.json').read_text())
        if summary['script_sha256'] != args.script_sha256 or summary['contract_sha256'] != args.contract_sha256:
            raise ValueError('producer identity differs')
        checks = audit_saved(summary)
        if checks != summary['raw_checks']:
            raise ValueError('raw checks differ')
        guard.verify()
        checks.update(status='PASS', summary_sha256=sha(out / 'summary.json'),
                      script_sha256=args.script_sha256, contract_sha256=args.contract_sha256,
                      audit_new_CE=0, scope=c['scope'], independence='main-session self-review; weak')
        with (root / 'evidence' / (args.tag + '-raw-audit.json')).open('x') as f:
            json.dump(checks, f, indent=2, allow_nan=False)
        print(json.dumps({k: v for k, v in checks.items() if k != 'rows'})); return
    run = LightRun(root / 'runs' / args.tag, 'analysis', c['bounds'], c['output_bytes'], guard)
    try:
        for block in c['blocks']:
            for snr in c['snrs']:
                pe, ref, raw, old, _ = inputs(block, snr)
                identity = dict(block=block, snr=snr, split=pe['split'], arm='TRUE_DATA_FIXED_S_CE')
                analysis, ae = run.call('A', identity, lambda: analyze(block, snr, pe, ref, raw, old),
                                        lambda v: {}, dict(reference_record_sha256=ref['sha256']))
                run.call('E', identity, lambda: estimate(analysis),
                         lambda v: dict(coefficient_error_before=v['ordinary']['actual_error'],
                                        coefficient_error_after=v['oracle']['actual_error']),
                         dict(analysis_record_sha256=sha(Path(ae['state']['file']['path'])),
                              reference_record_sha256=ref['sha256']))
                print(json.dumps(dict(block=block, snr=snr, calls=run.counts)), flush=True)
        summary = dict(status='COMPLETE', calls=run.counts, records=run.records,
                       source_sha256=sha(manifest), script_sha256=args.script_sha256,
                       contract_sha256=args.contract_sha256, scope=c['scope'])
        summary['raw_checks'] = audit_saved(summary)
        guard.verify(); run.meter.verify()
        summary['wall_seconds'] = time.time() - run.started
        run.write('summary.json', summary)
    except BaseException as exc:
        run.fail(exc); raise


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--tag', required=True)
    p.add_argument('--mode', choices=('run', 'audit'), default='run')
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--script-sha256', required=True)
    main(p.parse_args())
