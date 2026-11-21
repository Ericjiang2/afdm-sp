"""Phase 1 receiver, with reference replay and disjoint smoke entry points."""

from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tf_e3c_shrink_20261018'))
import e3c_driver as e3c
from messages import moments
from physical import daft

sbl, ref, e3d = e3c.sbl, e3c.ref, e3c.e3d
lib, arms = e3c.lib, e3c.arms

REFERENCE_ARMS = {'R0': 'diag-off', 'R1': 'cov-off', 'R2': 'cov+ridge'}
SPECTRAL_ARMS = ('S-lo', 'S-hi', 'S-isolo', 'S-isohi')
NEW_ARMS = ('S0', 'T0', *SPECTRAL_ARMS)
SMOKE_ARMS = (*REFERENCE_ARMS, *NEW_ARMS)
REFINEMENT = {
    'R0': 'R0', 'R1': 'R1', 'R2': 'R2', 'S0': 'R1', 'T0': 'R2',
    **dict.fromkeys(SPECTRAL_ARMS, 'R1'),
}
TAU = .5
AMBIGUOUS_INTERVAL = (.25, .75)
TOL = 1e-12


def spectral_ridges(covariance, delays, u, normalization):
    """Build once on candidate indices, retaining blocks for the construction gate."""
    ridges = {name: np.zeros_like(covariance) for name in SPECTRAL_ARMS}
    blocks = []
    n_ambiguous = 0
    for delay in np.unique(delays):
        idx = np.flatnonzero(delays == delay)
        ix = np.ix_(idx, idx)
        d = covariance[ix] / normalization
        values, vectors = np.linalg.eigh((d + d.conj().T) / 2)
        low = vectors[:, values < TAU]
        projector_lo = low @ low.conj().T
        identity = np.eye(len(idx))
        projector_hi = identity - projector_lo
        lo_fraction = low.shape[1] / len(idx)
        hi_fraction = (len(idx) - low.shape[1]) / len(idx)
        ridges['S-lo'][ix] = u * projector_lo
        ridges['S-hi'][ix] = u * projector_hi
        ridges['S-isolo'][ix] = (u * lo_fraction) * identity
        ridges['S-isohi'][ix] = (u * hi_fraction) * identity
        blocks.append((ix, d, projector_lo, projector_hi))
        lo, hi = AMBIGUOUS_INTERVAL
        n_ambiguous += int(np.count_nonzero((values >= lo) & (values <= hi)))
    census = dict(eigenvalues_total=len(delays), eigenvalues_in_025_075=n_ambiguous)
    return ridges, blocks, census


def require_errors(errors):
    failed = {field: error for field, error in errors.items() if not np.isfinite(error) or error > TOL}
    if failed:
        raise AssertionError(f'G2 construction error above {TOL}: {failed}')
    return errors


def matrix_error(actual, expected, scale=1.):
    return float(np.max(np.abs(actual - expected)) / scale)


def check_construction(ridges, blocks, full_ridge, delays, u):
    lo, hi, iso_lo, iso_hi = (ridges[name] for name in SPECTRAL_ARMS)
    off_block = delays[:, None] != delays[None, :]
    scale = u or 1.0
    errors = dict(
        spectral_sum=matrix_error(lo + hi, full_ridge, scale),
        isotropic_sum=matrix_error(iso_lo + iso_hi, full_ridge, scale),
        off_block=max(float(np.max(np.abs(ridge[off_block]), initial=0.) / scale)
                      for ridge in (lo, hi, iso_lo, iso_hi)),
        diagonal=0., hermitian=0., idempotence=0., complement=0.,
        lo_trace=0., hi_trace=0.,
    )
    for ix, d, p_lo, p_hi in blocks:
        block_errors = dict(
            diagonal=matrix_error(np.diag(d), 1.),
            hermitian=matrix_error(p_lo, p_lo.conj().T),
            idempotence=matrix_error(p_lo @ p_lo, p_lo),
            complement=matrix_error(p_lo + p_hi, np.eye(len(d))),
            lo_trace=float(abs(np.trace(lo[ix]) - np.trace(iso_lo[ix])) / scale),
            hi_trace=float(abs(np.trace(hi[ix]) - np.trace(iso_hi[ix])) / scale),
        )
        for field, error in block_errors.items():
            if not np.isfinite(error):
                raise AssertionError(f'nonfinite G2 error: {field}')
            errors[field] = max(errors[field], error)
    return require_errors(errors)


def arm_settings(v, sigma2, delays, dopplers, c1, smoke):
    specs = {name: arms.arm_spec(frozen_name, v, None, sigma2)
             for name, frozen_name in REFERENCE_ARMS.items()}
    u = specs['R1']['sum_vec']
    if not np.isfinite(u) or u < 0:
        raise ValueError('D_l requires finite nonnegative sum(v)')
    cache = {}
    matrices = {name: arms.sbl_gamma(spec, delays, dopplers, c1, cache)
                for name, spec in specs.items()}
    gamma = matrices['R1']
    full_ridge = u * np.eye(len(delays))
    ridges = {'R2': full_ridge}
    blocks, census = None, None
    if smoke:
        # At u=0 a unit-sum profile recovers the same-delay Doppler kernel.
        # Its spectrum enters the census, while all applied ridges are zero.
        covariance = gamma if u else sbl.gamma_full(
            delays, dopplers, np.full(len(v), 1.0 / len(v)), c1)
        split, blocks, census = spectral_ridges(covariance, delays, u, u or 1.0)
        ridges = {'R2': full_ridge, 'S0': full_ridge, **split}
        matrices.update(S0=matrices['R2'], T0=gamma)
        matrices.update({name: gamma + ridge for name, ridge in split.items()})
    return specs, matrices, ridges, blocks, census


def check_refinement(Y, xt, v, delays, dopplers, c1, c2, spec, sigma2,
                     expected_uncertainty, expected_extra, expected_mode):
    """Check direct _system outputs on the incoming (grid) geometry."""
    paths = [arms.GPath(int(delay), float(nu)) for delay, nu in zip(delays, dopplers)]
    B, Q, _, _, _, gamma = arms._system(Y, xt, v, paths, c1, c2, spec['ridge'], spec['mode'])
    scale = float(np.sum(v)) or 1.0
    identity = np.eye(len(delays))
    gram = B.conj().T @ B
    expected_q = gram + expected_uncertainty + (sigma2 + expected_extra) * identity
    expected_q = (expected_q + expected_q.conj().T) / 2
    return require_errors(dict(
        covariance=matrix_error(gamma, expected_uncertainty, scale),
        ridge=matrix_error(spec['ridge'], sigma2 + expected_extra, scale),
        normal_equations=matrix_error(Q, expected_q, float(np.max(np.diag(gram).real))),
        mode=float(spec['mode'] != expected_mode),
    ))


def posterior_error(B, Y, gamma, result):
    """Independent final active normal equation using the original candidate matrix."""
    idx = result['idx']
    active = B[:, idx]
    component = gamma[np.ix_(idx, idx)]
    gram = active.conj().T @ active
    expected_gram = (gram + gram.conj().T) / 2 + (component + component.conj().T) / 2
    beta = result['beta']
    precision = beta * expected_gram + np.diag(1. / result['gamma'])
    rhs = beta * (active.conj().T @ Y)
    # The frozen final Cholesky has a counted numerical jitter branch. A
    # well-conditioned gate can qualify pruning without a jitter rescue.
    return matrix_error(precision @ result['mu'], rhs, max(1., float(np.max(np.abs(rhs)))))


def fit_sbl(results, name, B, Y, beta0, gamma, max_iter):
    if name == 'T0':
        result = results['R1']
    else:
        result = sbl.sbl_em(B, Y, beta0=beta0, Gamma=gamma, max_iter=max_iter)
    results[name] = result
    return result


def process_key(ctx, cache, grid, key, mode):
    """Prepare and score an allowlisted key. No Phase 1 entry for main new arms."""
    allowed = {'parity': lib.gate_keys, 'smoke': lib.smoke_keys}
    if mode not in allowed or key not in allowed[mode]():
        raise ValueError(f'Phase 1 key disallowed: mode={mode}, key={key}')
    smoke = mode == 'smoke'
    selected = SMOKE_ARMS if smoke else REFERENCE_ARMS
    shared_start = time.perf_counter()
    scenario, rho, snr, frame = key
    raw_base, diag_base = e3c.p1ctx.base(ctx, scenario, rho / 1000, frame)
    gen_seconds = time.perf_counter() - shared_start
    meta, obs, data_true, truth = e3d.observe_key(ctx, raw_base, diag_base, *key, gen_seconds)
    # Shared setup from E-3c e3c_driver.process_key, split before dispatch because the frozen loop hardcodes six different arms.
    system = ctx.system
    n, c1, c2 = len(obs['y']), system.c1, system.c2
    pd = 1 - system.rho
    sigma2 = float(obs['sigma2'])
    delays_g, nus_g = grid
    tp = e3d.truth_paths(truth)
    Y = daft(obs['y'], c1, c2, True)
    Bp = cache.columns(obs['pilot'], c1, c2, delays_g, nus_g)
    cand1 = sbl.screen(Bp, Y, sbl.N_SCREEN)
    stage1 = sbl.sbl_em(Bp[:, cand1], Y, beta0=1.0 / (sigma2 + pd), Gamma=None)
    g1_idx, g1_mu, g1_e = sbl.select_output(cand1[stage1['idx']], stage1['mu'])
    ch1 = e3d.make_channel(ctx, n, delays_g[g1_idx], nus_g[g1_idx], g1_mu)
    _, dec1, _, _ = e3d.detect_decode(ctx, obs, ch1, None)
    mu_d, v, _ = moments(np.clip(dec1['raw_app'], -20, 20), pd)
    check = np.clip(dec1['raw_check_extrinsic'], -20, 20)
    err1 = e3c.gd.score(ctx, dec1['decoded'], truth)
    xt = e3d.self_xt(obs['pilot'] + mu_d, c1, c2)
    Bs = sbl.columns(xt, delays_g, nus_g, c1, c2)
    top2 = sbl.screen(Bs, Y, sbl.N_SCREEN)
    kept_delays = set(int(x) for x in delays_g[g1_idx])
    cand2 = sbl.candidate_union(top2, kept_delays, delays_g)
    stage1_count = {k: stage1[k] for k in ('iterations', 'converged', 'n_final', 'beta', 'jitter_events')}
    stage1_path = dict(delays=delays_g[g1_idx], dopplers=nus_g[g1_idx], gains=g1_mu)
    row = dict(
        meta, key=list(key), sigma2=sigma2,
        stage1=dict(stage1_count, n_candidates=int(len(cand1)),
                    atoms=e3d.atoms_record(delays_g[g1_idx], nus_g[g1_idx], g1_e),
                    nmse=float(e3c.crb.channel_nmse(stage1_path, tp, n))),
        round1=dict(info_errors=int(err1), syndrome=int(ctx.hd.syndrome_weight(ctx, dec1['decoded'])),
                    decoded_sha256=e3c.gd.bits_sha(dec1['decoded']), ldpc_iters=int(dec1['iterations'])),
        mean_v=float(np.mean(v)), n_candidates_stage2=int(len(cand2)),
        kept_delays_stage1=len(kept_delays), candidates_sha256=e3c.array_sha(cand2),
        input_sha256={name: e3c.array_sha(value) for name, value in
                      dict(y=obs['y'], pilot=obs['pilot'], data_true=data_true, soft_mean=mu_d, app_v=v).items()},
        rng_domain=str(e3c.p1ctx.p1_driver.DOMAIN), rng_entropy=e3c.p1ctx.p1_driver.ENTROPY_HEX,
        pairing=dict(noise_sha256=truth['noise_sha256'], physical_gains_sha256=truth['physical_gains_sha256'],
                     coded_sha256=e3c.array_sha(truth['coded']), info_sha256=e3c.array_sha(truth['info'])),
    )

    beta0 = 1.0 / (sigma2 + row['mean_v'])
    B = Bs[:, cand2]
    delays, dopplers = delays_g[cand2], nus_g[cand2]
    specs, matrices, ridges, blocks, census = arm_settings(v, sigma2, delays, dopplers, c1, smoke)
    row['seconds'] = dict(total=time.perf_counter() - shared_start)
    gamma = matrices['R1']
    u = specs['R1']['sum_vec']
    scale = u or 1.0
    if smoke:
        row['census'] = census
        if specs[REFINEMENT['S0']] is not specs[REFINEMENT['R1']]:
            raise AssertionError('G2 S0 refinement settings differ from R1')
        construction = check_construction(ridges, blocks, ridges['S0'], delays, u)
        construction.update(require_errors(dict(
            r2_sbl_vs_full_ridge=matrix_error(matrices['R2'], gamma + ridges['R2'], scale),
            s0_sbl_vs_r2=matrix_error(matrices['S0'], matrices['R2'], scale),
            t0_sbl_vs_r1=matrix_error(matrices['T0'], matrices['R1'], scale),
        )))

    def run_budget(max_iter):
        variants, results, refinement_errors, pruning = {}, {}, {}, {}
        for name in selected:
            arm_start = time.perf_counter()
            res = fit_sbl(results, name, B, Y, beta0, matrices[name], max_iter)
            pos, mu, energies = sbl.select_output(res['idx'], res['mu'])
            sbl_seconds = 0. if name == 'T0' else time.perf_counter() - arm_start
            dl, dn0 = delays[pos], dopplers[pos]
            spec = specs[REFINEMENT[name]]
            rf = ref.refine(Y, xt, v, dl, dn0, c1, c2, spec['ridge'], spec['mode'])
            score = e3c.score_stage(ctx, obs, check, tp, truth, dl, rf['dopplers'], rf['gains'], n)
            score['seconds'] = dict(total=time.perf_counter() - arm_start, sbl=sbl_seconds)
            pairs = sbl.codelay_pairs(dl, rf['dopplers'], n, tp['delays'])
            sbl_stats = {k: res[k] for k in ('iterations', 'converged', 'n_start', 'n_final', 'beta', 'jitter_events')}
            score.update(
                atoms_ongrid=e3d.atoms_record(dl, dn0, energies),
                atoms=e3d.atoms_record(dl, rf['dopplers'], np.abs(rf['gains']) ** 2),
                n_pair=len(pairs), pairs=pairs, sbl=dict(sbl_stats, max_iter=max_iter),
                sbl_state_sha256={k: e3c.array_sha(res[k]) for k in ('idx', 'gamma', 'mu')},
                sbl_gain_sha256=e3c.array_sha(mu),
                refine={k: val for k, val in rf.items() if k not in ('dopplers', 'gains')},
                added_trace_sbl=(float(np.trace(ridges[name]).real) if name in ridges else 0.),
                added_trace_refinement=spec['extra_ridge'] * len(dl),
            )
            variants[name] = score

            if smoke:
                score['census'] = census
                expected_extra = u if name in ('R2', 'T0') else 0.
                expected_mode = 'diag' if name == 'R0' else 'full'
                expected_gamma = u * np.eye(len(pos)) if name == 'R0' else gamma[np.ix_(pos, pos)]
                refinement_errors[name] = check_refinement(
                    Y, xt, v, dl, dn0, c1, c2, spec, sigma2, expected_gamma, expected_extra, expected_mode)
                if name in SPECTRAL_ARMS:
                    pruning[name] = dict(
                        n_pruned=res['n_start'] - res['n_final'],
                        posterior_relative_residual=posterior_error(B, Y, gamma + ridges[name], res),
                    )

        budget = dict(variants=variants)
        if smoke:
            t0_reuses_r1 = results['T0'] is results['R1'] and all(
                variants['T0'][k] == variants['R1'][k]
                for k in ('sbl', 'sbl_state_sha256', 'sbl_gain_sha256', 'atoms_ongrid'))
            if not t0_reuses_r1:
                raise AssertionError('G2 T0 SBL output differs from R1')
            require_errors({name: item['posterior_relative_residual'] for name, item in pruning.items()})
            budget['g2'] = dict(passed=True, construction=construction, refinement=refinement_errors,
                                s0_refinement_vs_r1=(specs[REFINEMENT['S0']] is specs[REFINEMENT['R1']]),
                                t0_sbl_bit_identical_to_r1=t0_reuses_r1, pruning=pruning)
        return budget

    if smoke:
        row['budgets'] = {str(max_iter): run_budget(max_iter) for max_iter in (100, 400)}
    else:
        row.update(run_budget(100))
    return row


def check_forced_pruning(gamma, ridge, delays, u):
    """Compare a two-step fit to dense EM with separately restricted Gamma and ridge."""
    n = len(gamma)
    B = np.eye(n, dtype=complex)
    Y = np.zeros(n, dtype=complex)
    Y[[0, 2]] = [10., 8.j]
    threshold = .08
    fitted = sbl.sbl_em(B, Y, beta0=1., Gamma=gamma + ridge, max_iter=2, prune=threshold)
    idx, variances, beta = np.arange(n), np.ones(n), 1.
    for _ in range(2):
        active = B[:, idx]
        ix = np.ix_(idx, idx)
        component = gamma[ix] + ridge[ix]
        expected_gram = active.conj().T @ active + component
        inv_precision = np.linalg.inv(beta * expected_gram + np.diag(1. / variances))
        mean = beta * (inv_precision @ (active.conj().T @ Y))
        residual = Y - active @ mean
        beta = n / (np.vdot(residual, residual).real + np.vdot(mean, component @ mean).real
                    + np.trace(expected_gram @ inv_precision).real)
        variances = np.abs(mean) ** 2 + np.diag(inv_precision).real
        keep = variances >= threshold * variances.max()
        idx, variances = idx[keep], variances[keep]

    if idx.tolist() != [0, 2] or not np.array_equal(fitted['idx'], idx):
        raise AssertionError(f'G2 forced pruning fixture or EM index mismatch: {idx}, {fitted["idx"]}')
    ix = np.ix_(idx, idx)
    reprojected, _, _ = spectral_ridges(gamma[ix], delays[idx], u, u)
    separation = matrix_error(reprojected['S-lo'], ridge[ix], u)
    if separation < .1:
        raise AssertionError('G2 forced pruning fixture cannot distinguish recomputing the projector')
    errors = require_errors(dict(
        beta_relative=matrix_error(fitted['beta'], beta, beta),
        variances_relative=matrix_error(fitted['gamma'], variances, float(max(variances))),
        posterior_relative_residual=posterior_error(B, Y, gamma + ridge, fitted),
    ))
    return dict(n_pruned=n-len(idx), final_indices=idx.tolist(), reprojected_ridge_difference=separation, **errors)


def synthetic():
    """G2 synthetic identities, stage separation, and real frozen EM pruning."""
    delays = np.array([0, 1, 0, 1, 0, 2])
    dopplers = np.array([0., -.5, .25, .25, .5, -1.])
    v = np.linspace(.005, .015, 16)
    c1, c2, sigma2 = .5 / len(v), 0., .09
    u = float(np.sum(v))
    specs, matrices, ridges, blocks, census = arm_settings(v, sigma2, delays, dopplers, c1, smoke=True)
    errors = check_construction(ridges, blocks, ridges['S0'], delays, u)
    errors.update(require_errors(dict(
        r2_sbl_vs_full_ridge=matrix_error(matrices['R2'], matrices['R1'] + ridges['R2'], u),
        s0_sbl_vs_r2=matrix_error(matrices['S0'], matrices['R2'], u),
        t0_sbl_vs_r1=matrix_error(matrices['T0'], matrices['R1'], u),
    )))
    Y = np.arange(len(v), dtype=complex) / len(v)
    xt = np.exp(1j * np.arange(len(v)))
    refinement_errors = {}
    for name in ('R1', 'R2', 'S0', 'T0'):
        spec = specs[REFINEMENT[name]]
        expected_extra = u if name in ('R2', 'T0') else 0.
        refinement_errors[name] = check_refinement(
            Y, xt, v, delays, dopplers, c1, c2, spec, sigma2, matrices['R1'], expected_extra, 'full')

    # A three-atom complex correlation block whose original low projector
    # changes if recomputed after its third member is pruned.
    fixture = np.eye(len(delays), dtype=complex)
    block = np.array([0, 2, 4])
    phases = np.exp(1j * np.array([0., .3, -.2]))
    fixture[np.ix_(block, block)] = .1 * np.eye(3) + .9 * np.outer(phases, phases.conj())
    fixture *= u
    split, _, _ = spectral_ridges(fixture, delays, u, u)
    pruning = check_forced_pruning(fixture, split['S-lo'], delays, u)
    B = sbl.columns(xt, delays, dopplers, c1, c2)
    results = {}
    for name in ('R1', 'T0'):
        fit_sbl(results, name, B, Y, 1., matrices[name], 100)
    if results['T0'] is not results['R1'] or specs[REFINEMENT['S0']] is not specs[REFINEMENT['R1']]:
        raise AssertionError('G2 synthetic S0 refinement or T0 SBL reuse mismatch')

    zero_v = np.zeros_like(v)
    zero_specs, zero_matrices, zero_ridges, zero_blocks, zero_census = arm_settings(
        zero_v, sigma2, delays, dopplers, c1, smoke=True)
    if (any(np.any(ridge) for ridge in zero_ridges.values())
            or any(np.any(matrix) for matrix in zero_matrices.values())
            or zero_census != census):
        raise AssertionError('G2 zero variance changed the spectrum census or added a penalty')
    zero_errors = check_construction(zero_ridges, zero_blocks, zero_ridges['S0'], delays, 0.)
    zero_errors.update(require_errors(dict(
        same_delay_kernel=max(matrix_error(zero[1], positive[1])
                              for zero, positive in zip(zero_blocks, blocks)))))
    for name in ('R1', 'R2', 'S0', 'T0'):
        if zero_specs[REFINEMENT[name]]['ridge'] != sigma2:
            raise AssertionError('G2 zero variance added a refinement ridge')
    return dict(passed=True, construction=errors, refinement=refinement_errors, census=census,
                s0_refinement_vs_r1=True, t0_sbl_bit_identical_to_r1=True, pruning=pruning,
                zero_variance=dict(construction=zero_errors, census=zero_census))
