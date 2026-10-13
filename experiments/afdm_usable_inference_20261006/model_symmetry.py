"""Deterministic G0 truncation versus full-channel modulation symmetry audit."""
import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import system_for
from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain
from . import kernels as kr


def complete_columns(system, dopplers, counter):
    """Complete all residue classes, without window normalization or pruning.

    The frozen alpha(m+nu) with positive integer synthesis reconstructs the
    reversed sample index. This is a mathematical completion, not the g1 label.
    """
    n = system.N_total
    counter.add('full_Dirichlet_coefficients', n*len(dopplers))
    alpha = np.array([[system.dirichlet_alpha(int(m), float(nu), n)
                       for nu in dopplers] for m in range(n)])
    counter.add('full_Fourier_column_synthesis', len(dopplers))
    synthesis = np.exp(2j*np.pi*np.outer(np.arange(n), np.arange(n))/n)@alpha
    reversed_index = (-np.arange(n)) % n
    direct = np.exp(2j*np.pi*np.outer(reversed_index, dopplers)/n)
    return synthesis, direct, alpha


def power_design(columns):
    first, second = columns.T
    cross = first*second.conj()
    return np.column_stack((abs(first)**2, abs(second)**2,
                            2*cross.real, -2*cross.imag, np.ones(len(first))))


def require_five_rows(geometry):
    if np.any(geometry['physical_clip_mask']):
        raise ValueError('symmetry audit crossed physical clipping')
    weights = geometry['weights']
    if not np.all(weights[:5] != 0) or np.any(weights[5:] != 0):
        raise ValueError('G0 comparison requires five retained rows for every path')


def calculate(output, study, counter):
    config = study['symmetry']
    raw = np.asarray(config['raw_gains'], float)@np.array([1., 1j])
    rows = []
    for n in config['Ns']:
        system = system_for(n)
        center, delta, shift = config['mu'], config['delta'], config['common_shift']
        noise, tau = config['noise_variance'], config['tau']
        base = kr.actual_geometry(n, center, delta, counter)
        moved = kr.actual_geometry(n, center+shift, delta, counter)
        for geo in (base, moved):
            require_five_rows(geo)
        full0, exact0, alpha0 = complete_columns(system, base['dopplers'], counter)
        full1, exact1, alpha1 = complete_columns(system, moved['dopplers'], counter)
        counter.add('full_Gram_matrices', 2)
        gram0, gram1 = full0.conj().T@full0/n, full1.conj().T@full1/n
        counter.add('gain_normalization', 4)
        full_gain0 = normalize_gain(raw[None, :], gram0)[0]
        full_gain1 = normalize_gain(raw[None, :], gram1)[0]
        g0_gain0 = normalize_gain(raw[None, :], base['gram'])[0]
        g0_gain1 = normalize_gain(raw[None, :], moved['gram'])[0]
        full_h0, full_h1 = np.sqrt(tau)*full0@full_gain0, np.sqrt(tau)*full1@full_gain1
        g0_h0, g0_h1 = np.sqrt(tau)*base['g0']@g0_gain0, np.sqrt(tau)*moved['g0']@g0_gain1
        # The existing g1 control shares G0 normalization. Its scalar dependence
        # on center is absorbed by the explicitly unknown tau, not by hidden data.
        energy0 = float(np.vdot(raw, base['gram']@raw).real)
        energy1 = float(np.vdot(raw, moved['gram']@raw).real)
        compensated_tau = tau*energy1/energy0
        g1_h0 = np.sqrt(tau)*base['g1']@g0_gain0
        g1_h1 = np.sqrt(compensated_tau)*moved['g1']@g0_gain1
        forward_phase = np.exp(2j*np.pi*shift*np.arange(n)/n)
        reversed_phase = np.exp(2j*np.pi*shift*((-np.arange(n)) % n)/n)
        counter.add('model_symmetry_comparisons', 8)
        errors = {
            'full_Dirichlet_identity': float(max(np.max(abs(full0-exact0)), np.max(abs(full1-exact1)))),
            'full_Gram_invariance': float(np.max(abs(gram0-gram1))),
            'full_H_modulation': float(np.max(abs(full_h1-reversed_phase*full_h0))),
            'full_power_invariance': float(np.max(abs(abs(full_h0)**2-abs(full_h1)**2))),
            'direct_G1_modulation': float(np.max(abs(moved['g1']-forward_phase[:, None]*base['g1']))),
            'G1_tau_compensated_modulation': float(np.max(abs(g1_h1-forward_phase*g1_h0))),
            'G1_tau_compensated_power': float(np.max(abs(abs(g1_h0)**2-abs(g1_h1)**2))),
            'full_signal_power': float(max(abs(np.mean(abs(full_h0)**2)-tau), abs(np.mean(abs(full_h1)**2)-tau))),
        }
        g0_difference = float(np.max(abs(abs(g0_h0)**2-abs(g0_h1)**2)))
        counter.add('power_design_SVD', 2)
        full_singular = np.linalg.svd(power_design(base['g1']), compute_uv=False)
        g0_singular = np.linalg.svd(power_design(base['g0']), compute_uv=False)
        full_rank = int(np.sum(full_singular > config['rank_rtol']*full_singular[0]))
        g0_rank = int(np.sum(g0_singular > config['rank_rtol']*g0_singular[0]))
        # This analytic contrast is valid for arbitrary nonzero H. No symbols or
        # noise are sampled here; Gaussian noise enters its exact expectation.
        contrast = kr.population_quartic(g1_h0, np.angle(g1_h1), np.ones(n), noise, counter)
        inverse0 = kr.infer_power(abs(g0_h0)**2+noise, n, study['branch'], study['numerics'], counter)
        inverse1 = kr.infer_power(abs(g0_h1)**2+noise, n, study['branch'], study['numerics'], counter)
        g0_inverse_ok = inverse0['status'] == inverse1['status'] == 'ok'
        recovered_shift_error = None
        if g0_inverse_ok:
            recovered_shift_error = abs(inverse1['mu']-inverse0['mu']-shift)
        passed = (max(errors.values()) < config['identity_atol']
                  and g0_difference > config['g0_min_power_difference']
                  and full_rank == 3 and g0_rank == 5
                  and contrast['excess'] > config['minimum_quartic_gap']
                  and contrast['distance_squared'] > 0
                  and contrast['excess'] >= contrast['lower_bound']-config['identity_atol']
                  and g0_inverse_ok and recovered_shift_error < study['algebra']['node_atol'])
        record = dict(N=n, errors=errors, passed=bool(passed),
                      G0_max_power_difference=g0_difference, G0_inverses=[inverse0, inverse1],
                      G0_recovered_shift_error=recovered_shift_error,
                      G1_compensated_tau=compensated_tau,
                      full_power_design_rank=full_rank, G0_power_design_rank=g0_rank,
                      G1_phase_only_population_contrast=contrast,
                      scope='G0 truncation-specific information versus full/G1 symmetry; no finite-sample or receiver claim')
        with (output/f'symmetry_N{n}.npz').open('xb') as handle:
            np.savez_compressed(handle, raw=raw, dopplers=base['dopplers'], shifted_dopplers=moved['dopplers'],
                                alpha=alpha0, shifted_alpha=alpha1, full_columns=full0, shifted_full_columns=full1,
                                exact_columns=exact0, shifted_exact_columns=exact1, full_Gram=gram0, shifted_full_Gram=gram1,
                                full_H=full_h0, shifted_full_H=full_h1, G0_H=g0_h0, shifted_G0_H=g0_h1,
                                G1_H=g1_h0, compensated_G1_H=g1_h1, G0_weights=base['weights'],
                                shifted_G0_weights=moved['weights'], full_power_design_singular=full_singular,
                                G0_power_design_singular=g0_singular)
        dump(output/f'symmetry_N{n}.json', record)
        rows.append(record)
    return dict(checks=rows, all_passed=all(row['passed'] for row in rows),
                scope='zero-random-observation modulation symmetry audit')
