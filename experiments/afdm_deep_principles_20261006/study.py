"""Three deterministic, zero-observation scientific stages; execute on SSH."""
import argparse
from itertools import product
import json
from pathlib import Path

import numpy as np
from scipy.special import roots_legendre

from experiments.afdm_coherent_structure_20261006.geometry import c2_derivative
from experiments.afdm_efficient_information.prior_likelihood import daft, pdp_distribution, system_for
from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_shared_channel_20261004.production_prior import frozen_components, normalize_gain
from .config import CONFIG
from . import protocol, thread_binding
from .kernels import (EvaluationCounter, actual_geometry, add_proper_gaussian_noise, complex_complement,
                      efficient_derivative, ncx2_power_excess, physical_jets)


def complex_gains(value):
    return np.asarray(value, float)@np.array([1., 1j])


def save(output, name, arrays, record):
    with (output/(name+'.npz')).open('xb') as handle:
        np.savez_compressed(handle, **arrays)
    dump(output/(name+'.json'), record)
    return record


def moments(output, config, counter):
    n, mu, tau = config['N'], config['mu'], config['tau']
    system = system_for(n)
    states = np.asarray(list(product(range(4), repeat=n)), dtype=int)
    counter.add('qpsk_states', len(states))
    symbols = np.exp(1j*(np.pi/4+np.pi/2*states))
    transform = daft(n)
    x = symbols@transform.conj()
    row_phase = np.exp(-2j*np.pi*system.c1*np.arange(n)**2)
    column_phase = np.exp(-2j*np.pi*system.c2*np.arange(n)**2)
    indices = np.indices((n, n, n, n))
    ii, jj, kk, ll = indices
    closure = (ii-jj+kk-ll) % n == 0
    holomorphic_sum = np.sum(np.exp(2j*np.pi*(ii+jj+kk+ll)[..., None]*np.arange(n)/n)
                             *column_phase**4, axis=-1)
    contrast = np.array([[1., -1., 0., 0.], [0., 0., 1., -1.]])
    rows = []
    for index, delta in enumerate(config['deltas']):
        geo = actual_geometry(system, mu, delta, counter)
        counter.add('gain_normalizations')
        gains = normalize_gain(complex_gains(config['raw_gains'])[None, :], geo['gram'])[0]
        h = np.sqrt(tau)*(geo['g0']@gains)
        counter.add('symbol_channel_responses', len(states))
        z = h[None, :]*x*row_phase.conj()[None, :]
        second = z.T@z.conj()/len(z)
        pseudo = z.T@z/len(z)
        fourth = np.einsum('bi,bj,bk,bl->ijkl', z, z.conj(), z, z.conj(), optimize=True)/len(z)
        fourth_pure = np.einsum('bi,bj,bk,bl->ijkl', z, z, z, z, optimize=True)/len(z)
        counter.add('K40_coordinates', n**4)
        k40 = fourth_pure-pseudo[ii, jj]*pseudo[kk, ll]-pseudo[ii, kk]*pseudo[jj, ll]-pseudo[ii, ll]*pseudo[jj, kk]
        expected40 = -h[ii]*h[jj]*h[kk]*h[ll]*holomorphic_sum/n**2
        powers = abs(z)**2
        counter.add('power_covariance_coordinates', n*n)
        power_covariance = (powers-powers.mean(0)).T@(powers-powers.mean(0))/len(z)
        for noise in config['noise_variances']:
            counter.add('K22_coordinates', n**4)
            total_fourth, total_second = add_proper_gaussian_noise(fourth, second, noise)
            k22 = (total_fourth-total_second[ii, jj]*total_second[kk, ll]
                   -total_second[ii, ll]*total_second[kk, jj]-pseudo[ii, kk]*pseudo[jj, ll].conj())
            expected22 = -h[ii]*h[jj].conj()*h[kk]*h[ll].conj()*closure/n
            errors = dict(K22=float(np.max(abs(k22-expected22))),
                          K40=float(np.max(abs(k40-expected40))),
                          proper_second=float(np.max(abs(pseudo))))
            arrays = dict(states=states, symbols=symbols, x=x, H=h, gains=gains,
                          gram=geo['gram'], weights=geo['weights'], row_phase=row_phase,
                          K22=k22, K22_formula=expected22, K40=k40, K40_formula=expected40,
                          second=total_second, pseudo_second=pseudo)
            if delta == 0:
                counter.add('null_contrast_covariance_coordinates', 4)
                sigma = contrast@(power_covariance+np.diag(noise**2+2*noise*powers.mean(0)))@contrast.T
                predicted = 2*np.diag((abs(h[[0, 2]])**2+noise)**2)
                errors['null_covariance'] = float(np.max(abs(sigma-predicted)))
                errors['null_contrast'] = float(np.max(abs(contrast@powers.mean(0))))
                arrays.update(Sigma0=sigma, Sigma0_formula=predicted)
            rows.append(save(output, f'moments_{index}_noise_{noise}', arrays,
                        dict(delta=delta, noise=noise, errors=errors,
                             passed=max(errors.values()) < config['absolute_tolerance'],
                             scope='256 complete QPSK states; Gaussian noise integrated algebraically, never sampled')))
    return dict(checks=rows, all_passed=all(row['passed'] for row in rows))


def stability(output, config, counter):
    rows, fine = [], []
    mu, rtol = config['mu'], config['rank_rtol']
    for n in config['Ns']:
        system = system_for(n)
        jets, actual, keep = physical_jets(system, mu, counter)
        response_error = float(np.max(abs(jets[0]-actual)))
        projector, base_singular = complex_complement(jets[:2].T, rtol)
        r2, r3 = projector@jets[2], projector@jets[3]
        q3 = r3-r2*np.vdot(r2, r3).real/np.vdot(r2, r2).real
        bases = dict(jets=jets, actual=actual, mask=keep, r2=r2, r3=r3, q3=q3,
                     base_singular=base_singular)
        rows.append(save(output, f'jets_N{n}', bases,
                    dict(N=n, response_error=response_error,
                         jet_rank=int(np.linalg.matrix_rank(jets.T)),
                         passed=response_error < config['response_absolute_tolerance'])))
        for delta in config['deltas']:
            minus, actual_minus, mask_minus = physical_jets(system, mu-delta, counter)
            plus, actual_plus, mask_plus = physical_jets(system, mu+delta, counter)
            columns = np.column_stack((minus[0], plus[0]))
            slopes = np.column_stack((minus[1], plus[1]))
            physical_error = float(max(np.max(abs(minus[0]-actual_minus)), np.max(abs(plus[0]-actual_plus))))
            if not np.array_equal(mask_minus, keep) or not np.array_equal(mask_plus, keep):
                raise ValueError('derivative check crossed the frozen atom mask')
            for label, encoded in config['gains'].items():
                gains = complex_gains(encoded)
                result = efficient_derivative(columns, slopes, gains, rtol, counter)
                a, b = gains.sum(), gains[1]-gains[0]
                if label == 'generic':
                    exponent = 2
                    coefficient = float(np.vdot(r2, r2).real*(a*b.conjugate()).imag**2/abs(b)**2)
                elif label == 'raw_aligned':
                    exponent = 4
                    coefficient = float(abs(b*b-a*a)**2*np.vdot(q3, q3).real/(9*abs(b)**2))
                elif label == 'equal':
                    exponent = 2
                    coefficient = float(abs(a)**2*(np.vdot(r2, r2).real
                                        -np.vdot(r3, r2).real**2/np.vdot(r3, r3).real))
                else:
                    exponent, coefficient = 0, 0.
                relative_projection = abs(result['J']-result['direct_J'])/max(result['J'], 1e-30)
                passed = result['identity_error'] < config['response_absolute_tolerance']
                passed &= physical_error < config['response_absolute_tolerance']
                coefficient_error = None
                if label == 'single_path':
                    passed &= max(result['J'], result['direct_J']) < config['single_path_absolute_tolerance']
                else:
                    passed &= relative_projection < config['projection_relative_tolerance']
                    if coefficient <= 0:
                        raise ValueError('declared nonzero asymptotic coefficient is not positive')
                    coefficient_error = abs(result['J']/delta**exponent/coefficient-1)
                    if delta == min(config['deltas']):
                        passed &= coefficient_error < config['fine_coefficient_relative_tolerance']
                        fine.append(dict(N=n, gain_case=label, exponent=exponent,
                                         scaled_J=result['J']/delta**exponent, coefficient=coefficient,
                                         relative_error=coefficient_error))
                row = dict(N=n, delta=delta, gain_case=label, J=result['J'], direct_J=result['direct_J'],
                           real_center_coefficient=result['coefficient'], predicted_exponent=exponent,
                           predicted_coefficient=coefficient, relative_projection_error=relative_projection,
                           relative_coefficient_error=coefficient_error, physical_error=physical_error,
                           AB_identity_error=result['identity_error'], passed=bool(passed))
                arrays = {key: value for key, value in result.items() if isinstance(value, np.ndarray)}
                arrays.update(columns=columns, slopes=slopes, gains=gains)
                rows.append(save(output, f'projection_N{n}_{label}_delta_{delta}', arrays, row))
        ratio = config['matched_ratio']
        for label, a, b in [('raw_aligned', 3., 1.), ('equal', 2., 0.)]:
            shift = (-a*(ratio*ratio-1)/(b+np.sqrt(b*b+a*a*(ratio*ratio-1)))
                     if b else np.sqrt(ratio*ratio-1))
            bprime = (b-a*shift)/ratio
            old_gain = np.array([(a-b)/2, (a+b)/2], complex)
            new_gain = np.array([(a-bprime)/2, (a+bprime)/2], complex)
            old_nodes, new_nodes = np.array([-1., 1.]), np.array([shift-ratio, shift+ratio])
            old_m = np.array([sum(old_gain*old_nodes**order) for order in range(4)])
            new_m = np.array([sum(new_gain*new_nodes**order) for order in range(4)])
            counter.add('matched_position_moment_values', 8)
            moment_error = float(np.max(abs(old_m[:3]-new_m[:3])))
            cubic = (new_m[3]-old_m[3])*jets[3]/6
            for delta in config['deltas']:
                old_geo = actual_geometry(system, mu, delta, counter)
                new_geo = actual_geometry(system, mu+shift*delta, ratio*delta, counter)
                f = old_geo['g0']@old_gain
                fprime = new_geo['g0']@new_gain
                relative_cubic = float(np.linalg.norm((fprime-f)/delta**3-cubic)/np.linalg.norm(cubic))
                passed = moment_error < config['matched_moment_tolerance']
                if delta == min(config['deltas']):
                    passed &= relative_cubic < config['fine_cubic_relative_tolerance']
                rows.append(save(output, f'matched_N{n}_{label}_delta_{delta}',
                            dict(f=f, fprime=fprime, old_moments=old_m, new_moments=new_m,
                                 old_gain=old_gain, new_gain=new_gain, cubic_coefficient=cubic),
                            dict(N=n, gain_case=label, delta=delta, ratio=ratio, shift=shift,
                                 low_moment_error=moment_error, cubic_relative_error=relative_cubic,
                                 passed=bool(passed), scope='raw physical response; normalized rate follows analytically')))
    return dict(checks=rows, fine_coefficient_checks=fine, all_passed=all(row['passed'] for row in rows),
                scope='analytic coefficients and independent real projection, no exponent regression or achieved rate claim')


def mixture(output, config, counter):
    counter.add('actual_pdp_distribution_calls')
    prior = pdp_distribution(config['N'], config['mu'], 0.)
    counter.add('pdp_component_values', len(prior['weights']))
    d1, d2 = prior['pdp'].T
    ell = 2*np.sqrt(d1*d2)/(d1+d2)
    scales, inverse = np.unique(ell, return_inverse=True)
    mass = np.bincount(inverse, weights=prior['weights'])
    gamma_prior = float(prior['weights']@(ell*ell))
    if not np.array_equal(prior['limits'], [70, 70]):
        raise ValueError('closed prior identity requires the frozen L=70 branch')
    j = np.arange(1, 70)
    counter.add('independent_pdp_component_values', len(j))
    survival = np.exp(-5/32)
    raw_mass = (1-survival)*survival**(j-1)*(1-survival**(70-j))
    probability = raw_mass/raw_mass.sum()
    powers = 10.**(-j/40)
    gamma_closed = float(probability@(4*powers/(1+powers)**2))
    system = system_for(config['N'])
    geo = actual_geometry(system, config['mu'], 0., counter)
    h0 = np.sqrt(config['tau']*config['N'])*geo['g0'][:, 0]/np.linalg.norm(geo['g0'][:, 0])
    sigma = 2*np.diag((abs(h0[[0, 2]])**2+config['noise_variance'])**2)
    counter.add('analytic_null_covariance_and_derivative_values', 6)
    direction = c2_derivative(config['mu'], config['tau'], [1., 1j])
    gamma = float(direction@np.linalg.solve(sigma, direction))
    alpha = config['alpha']
    threshold = -2*np.log(alpha)
    asymptotic = alpha*threshold*gamma_prior*gamma/4
    if gamma <= 0 or not 0 < gamma_prior <= 1 or abs(gamma_prior-gamma_closed) > config['prior_absolute_tolerance']:
        raise AssertionError('actual prior/null covariance identity failed')
    save(output, 'prior_and_null', dict(pdp=prior['pdp'], weights=prior['weights'], ell=ell,
         merged_scales=scales, merged_masses=mass, closed_pdp_powers=powers,
         closed_pdp_masses=probability, Sigma0=sigma, direction=direction, H0=h0),
         dict(Gamma=gamma_prior, Gamma_closed=gamma_closed, gamma=gamma,
              limits=prior['limits'].tolist(), original_components=len(ell), merged_components=len(scales),
              small_h_log_coefficient=asymptotic,
              small_h_scope='analytic formula only; current moderate-h quadrature does not verify this asymptotic'))
    quadratures = {}
    for order in config['quadrature_orders']:
        counter.add('gauss_legendre_nodes', order)
        node, weight = roots_legendre(order)
        endpoint = 1-config['tail_length']
        quadratures[order] = ((node+1)*endpoint/2, weight*endpoint/2)
    rows = []
    previous = alpha
    for local_h in config['h']:
        if local_h == 0:
            rows.append(dict(h=0., power=alpha, power_excess=0., refinement_error=0.,
                             tail_error_bound=0., passed=True, scope='exact null, no quadrature power kernel'))
            continue
        approximations = []
        for order in config['quadrature_orders']:
            u, weight = quadratures[order]
            noncentrality = gamma*local_h**2*scales[:, None]**2*u[None, :]**2/(1-u[None, :]**2)
            excess = ncx2_power_excess(noncentrality, alpha, config['small_noncentrality_cutoff'], counter)
            integral = float(mass@(excess@weight))
            approximations.append(integral)
            with (output/f'integrand_h_{local_h}_order_{order}.npz').open('xb') as handle:
                np.savez_compressed(handle, u=u, weights=weight, scales=scales, masses=mass,
                                    noncentrality=noncentrality, power_excess=excess)
        fine = approximations[-1]
        refinement = abs(fine-approximations[-2])
        tail = (1-alpha)*config['tail_length']
        passed = 0 < fine and alpha+fine < 1 and alpha+fine > previous
        passed &= refinement < config['refinement_absolute_tolerance']
        row = dict(h=local_h, power=alpha+fine, power_excess=fine,
                   quadrature_excesses=approximations, refinement_error=refinement,
                   tail_error_bound=tail,
                   omitted_tail_interval=[0., tail],
                   small_lambda_max_taylor_error=config['small_noncentrality_cutoff']**3/6,
                   passed=bool(passed),
                   scope='numerical interior quadrature plus rigorous omitted-tail length bound; refinement is not a certified interior error bound')
        dump(output/f'power_h_{local_h}.json', row)
        rows.append(row)
        previous = alpha+fine
    return dict(Gamma=gamma_prior, gamma=gamma, local_limit_power=rows,
                all_passed=all(row['passed'] for row in rows),
                small_h_asymptotic='not numerically claimed; moderate-h bounded integration only')


def preload():
    frozen_components()
    # Both modules are already imported; do not run the binding check outside admission.
    return thread_binding.blas_binding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['moments', 'stability', 'mixture'])
    parser.add_argument('--stage')
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--wall-seconds', type=int, default=600)
    parser.add_argument('--print-config', action='store_true')
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    if args.print_config:
        print(json.dumps(CONFIG, indent=2))
        return
    preload()
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.phase is None or not args.stage or args.artifact_root is None or args.config is None:
        parser.error('--phase, --stage, --artifact-root and --config are required')
    config = json.loads(args.config.read_text())
    if config != CONFIG:
        raise ValueError('execution config differs from committed scientific CONFIG')
    registered = dict(study=config, phase=args.phase, seed=config['seed'],
                      new_geometry_probes=config['reservations'][args.phase], new_observations=0,
                      receiver_calls=0, decoder_calls=0, new_confirmation_stream=False)

    def calculate(output):
        counter = EvaluationCounter(registered['new_geometry_probes'])
        try:
            function = {'moments': moments, 'stability': stability, 'mixture': mixture}[args.phase]
            result = function(output, config[args.phase], counter)
            dump(output/'scientific_checks.json', result)
            if not result['all_passed']:
                raise AssertionError('deterministic checks failed; all completed raw checks retained')
        except BaseException:
            dump(output/'kernel_counts_partial.json', counter.report())
            raise
        counts = counter.report()
        dump(output/'kernel_counts.json', counts)
        return dict(**result, kernel_counts=counts, geometry_probes=counts['total'],
                    new_observations=0, receiver_calls=0, decoder_calls=0,
                    accounting='logical kernel values counted before calls; QPSK is exhaustive, noise is algebraic; no random observations')

    protocol.run(args.stage, registered, [args.config.resolve()], calculate,
                 artifact_root=args.artifact_root, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
