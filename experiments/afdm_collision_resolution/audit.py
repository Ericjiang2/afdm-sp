"""Independent formula/raw reconstruction; no reader or teacher implementation.

Only the frozen hash/admission plumbing is reused. This module draws no random
inputs and constructs no integration grid. Numerical imports are all top-level.
"""
import argparse
from itertools import combinations_with_replacement, product
import math
from pathlib import Path
import sys

import numpy as np
from scipy import linalg, special

from experiments.afdm_efficient_information.audit import (
    audit_hashes, loaded_project_sources, read_json, read_npz, sha,
)
from experiments.afdm_collision_resolution.protocol import ROOT, ARTIFACT, MISSION, dump, run

CONFIG_PATH = ARTIFACT/'AUDIT_CONFIG.json'
PROTECTED = MISSION/'protected_baseline.json'


class Checks:
    """Keep every comparison, including failures and its declared tolerance."""
    def __init__(self, tolerances):
        self.tolerances, self.records = tolerances, []

    def close(self, actual, expected, label, kind='algebra'):
        a, b = np.asarray(actual), np.asarray(expected)
        if a.dtype.kind in 'bOUS' or b.dtype.kind in 'bOUS':
            self.equal(actual, expected, label)
            return
        tolerance = self.tolerances[kind]
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            self.records.append(dict(label=label, passed=False, reason='shape/nonfinite mismatch', kind=kind))
            return
        error = float(np.max(abs(a-b))) if a.size else 0.
        self.records.append(dict(label=label, passed=bool(np.allclose(a, b, **tolerance)),
                                 maximum_absolute_error=error, kind=kind))

    def equal(self, actual, expected, label):
        def plain(value):
            if isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, np.generic):
                return value.item()
            if isinstance(value, dict):
                return {key:plain(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [plain(item) for item in value]
            return value
        self.records.append(dict(label=label, passed=bool(plain(actual) == plain(expected)), kind='exact'))

    def tree(self, actual, expected, label, kind='algebra'):
        """Compare every independently reconstructed field; no substring gates."""
        if isinstance(expected, dict):
            for key, value in expected.items():
                if key not in actual:
                    self.records.append(dict(label=label+'/'+key, passed=False, reason='missing field', kind='exact'))
                else:
                    self.tree(actual[key], value, label+'/'+key, kind)
        elif isinstance(expected, (str, bool)) or expected is None:
            self.equal(actual, expected, label)
        else:
            self.close(actual, expected, label, kind)


def geometry(mu, tau=1., sigma2=1.):
    """Closed Dirichlet formula/derivative and explicit N4 DAFT/PDP law."""
    if not .26 < mu < .36 or min(tau, sigma2) <= 0:
        raise ValueError('audit geometry only covers the registered fixed N4 branch')
    n = 4
    offsets = np.arange(-2, 3)
    argument = offsets+mu
    alpha = (np.exp(.75j*np.pi*argument)*np.sin(np.pi*argument)
             /(4*np.sin(np.pi*argument/4)))
    dot = alpha*(.75j*np.pi+np.pi/np.tan(np.pi*argument)
                 -(np.pi/4)/np.tan(np.pi*argument/4))
    norm = linalg.norm(alpha)
    normalized_dot = dot/norm-alpha*np.real(np.vdot(alpha, dot))/norm**3
    weights = alpha[1:4]/norm
    atom = np.exp(.5j*np.pi*np.outer(np.arange(n), [-1, 0, 1]))
    w, w_dot = atom@weights, atom@normalized_dot[1:4]
    norm_w = linalg.norm(w)
    b = w_dot-w*np.vdot(w, w_dot)/norm_w**2
    u0, u1 = w/norm_w, b/linalg.norm(b)
    u0_dot = w_dot/norm_w-w*np.real(np.vdot(w, w_dot))/norm_w**3
    k = np.arange(n)
    daft = (np.exp(2j*np.pi*(.1/n**2)*k[:, None]**2)
            *np.exp(-2j*np.pi*np.outer(k, k)/n)/np.sqrt(n)
            *np.exp(2j*np.pi*(2.5/n)*k[None, :]**2))
    ids = np.asarray([(0, *tail) for tail in product(range(4), repeat=3)])
    states = np.exp(.25j*np.pi+.5j*np.pi*ids)@daft.conj()
    increments = np.arange(1, 70)
    powers = 10.**(-increments/40)
    pdp = np.vstack([np.column_stack([np.ones(69), powers]),
                     np.column_stack([powers, np.ones(69)])])
    survival = np.exp(-5/32)
    masses = .5*(1-survival)*survival**(increments-1)*(1-survival**(70-increments))
    probability = np.tile(masses, 2)/(2*masses.sum())
    kappa = float(probability@(4*pdp.prod(axis=1)/pdp.sum(axis=1)**2)
                  *np.vdot(b, b).real/norm_w**2)
    scale = np.sqrt(tau*n)
    return dict(w=w, w_dot=w_dot, b=b, m0=scale*states*u0,
                m1=scale*states*u1, m_mu=scale*states*u0_dot, kappa=kappa,
                pdp=pdp, pdp_weights=probability, daft=daft,
                response=np.column_stack([w, w]),
                gram=np.full((2, 2), norm_w**2/n, complex))


def likelihood(y, state, noise, want_score=True):
    """Bessel phase posterior moments derived from the Gaussian kernel."""
    y = np.asarray(y, complex)
    if y.ndim != 2 or y.shape[1] != 4 or not np.isfinite(y).all() or noise <= 0:
        raise ValueError('finite N4 observations and positive noise required')
    m, b, dm = state['m0'], state['m1'], state['m_mu']
    density, scores = [], []
    m_power = np.einsum('ki,ki->k', m.conj(), m).real
    b_power = np.einsum('ki,ki->k', b.conj(), b).real
    mb = np.einsum('ki,ki->k', m.conj(), b)
    for start in range(0, len(y), 128):
        obs = y[start:start+128]
        c = np.einsum('bi,ki->bk', obs.conj(), m)
        radius = abs(c)
        concentration = 2*radius/noise
        i0 = special.ive(0, concentration)
        component = (np.log(i0)+concentration
                     -(np.sum(abs(obs)**2, axis=1)[:, None]+m_power)/noise
                     -4*np.log(np.pi*noise)-np.log(len(m)))
        total = special.logsumexp(component, axis=1)
        density.append(total)
        if not want_score:
            continue
        phase_mean = np.divide(special.ive(1, concentration)*c.conj(), i0*radius,
                               out=np.zeros_like(c), where=radius > 0)
        d = np.einsum('bi,ki->bk', obs.conj(), b)
        expected_square = abs(d)**2+abs(mb)**2-2*np.real(phase_mean*d*mb.conj())
        expected_radial = np.real(phase_mean*c)-m_power
        r_score = state['kappa']*(expected_square/noise**2-b_power/noise-expected_radial/noise)
        mu_score = 2*(np.real(phase_mean*np.einsum('bi,ki->bk', obs.conj(), dm))
                      -np.real(np.einsum('ki,ki->k', m.conj(), dm)))/noise
        noise_score = -4+(np.sum(abs(obs)**2, axis=1)[:, None]+m_power
                          -2*np.real(phase_mean*c))/noise
        component_score = np.stack([r_score, mu_score, expected_radial/noise, noise_score], axis=2)
        scores.append(np.einsum('bk,bkj->bj', np.exp(component-total[:, None]), component_score))
    return dict(logpdf=np.concatenate(density), score=np.concatenate(scores) if want_score else None)


def finite_differences(y, point, steps):
    coordinate = np.array([point['mu'], np.log(point['tau']), np.log(point['sigma2'])])
    values = []
    for step in steps:
        columns = []
        for axis in range(3):
            endpoints = []
            for sign in (-1, 1):
                shifted = coordinate.copy()
                shifted[axis] += sign*step
                mu, tau, noise = shifted[0], np.exp(shifted[1]), np.exp(shifted[2])
                endpoints.append(likelihood(y, geometry(mu, tau, noise), noise, False)['logpdf'])
            columns.append((endpoints[1]-endpoints[0])/(2*step))
        values.append(np.column_stack(columns))
    return np.asarray(values)


def signal_polynomial(m, b, dm, exponent):
    """Coefficient of z^0 t^2 after m -> m(1-t^2/2)+t*z*b.

    Truncated polynomial multiplication replaces the teacher's Hessian loop;
    averaging relative phase selects Laurent exponent zero. A separate dual
    product gives the mu derivative, without dividing by any mean coordinate.
    """
    polynomial = {(0, 0):np.ones(len(m), complex)}
    value, derivative = np.ones(len(m), complex), np.zeros(len(m), complex)
    for index, count in enumerate(exponent):
        for conjugate in (False, True):
            factor = m[:, index].conj() if conjugate else m[:, index]
            tangent = b[:, index].conj() if conjugate else b[:, index]
            direction = dm[:, index].conj() if conjugate else dm[:, index]
            terms = {(0, 0):factor, (1, -1 if conjugate else 1):tangent, (2, 0):-factor/2}
            for _ in range(int(count)):
                derivative = derivative*factor+value*direction
                value = value*factor
                result = {}
                for (degree, phase), coefficient in polynomial.items():
                    for (extra, harmonic), multiplier in terms.items():
                        if degree+extra <= 2:
                            key = (degree+extra, phase+harmonic)
                            result[key] = result.get(key, 0)+coefficient*multiplier
                polynomial = result
    tangent = polynomial.get((2, 0), np.zeros(len(m)))
    return value.real, derivative.real, tangent.real


def exact_moment(state, exponent, noise):
    exponent = np.asarray(exponent, int)
    mean, derivatives = 0., np.zeros(4)
    for removed in product(*(range(int(k)+1) for k in exponent)):
        removed = np.asarray(removed)
        remaining = exponent-removed
        coefficient = noise**removed.sum()
        for power, contractions in zip(exponent, removed):
            coefficient *= math.comb(int(power), int(contractions))**2*math.factorial(int(contractions))
        value, mu, tangent = signal_polynomial(state['m0'], state['m1'], state['m_mu'], remaining)
        term = coefficient*value.mean()
        mean += term
        derivatives += [coefficient*state['kappa']*tangent.mean(), coefficient*mu.mean(),
                        remaining.sum()*term, removed.sum()*term]
    return float(mean), derivatives


def moment_system(state, noise):
    exponents = np.asarray([np.bincount(indices, minlength=4) for degree in (1, 2)
                           for indices in combinations_with_replacement(range(4), degree)])
    keys = {tuple(k) for k in exponents}
    keys.update(tuple(a+b) for a in exponents for b in exponents)
    moments = {key:exact_moment(state, key, noise) for key in sorted(keys)}
    means = np.asarray([moments[tuple(k)][0] for k in exponents])
    covariance = np.asarray([[moments[tuple(a+b)][0] for b in exponents] for a in exponents])-means[:, None]*means
    return dict(exponents=exponents, mean=means, derivatives=np.asarray([moments[tuple(k)][1] for k in exponents]),
                covariance=covariance, distinct_moments=len(keys))


def batches(values, count=8):
    x = np.asarray(values, float)
    if len(x) < count or len(x) % count or not np.isfinite(x).all():
        raise ValueError('finite complete equal batches required')
    means = x.reshape(count, len(x)//count, *x.shape[1:]).mean(axis=1)
    center = means.mean(axis=0)
    return dict(mean=x.mean(axis=0), batch_se=np.sqrt(np.sum((means-center)**2, axis=0)/(count*(count-1))),
                batches=count, batch_means=means)


def least_squares(design, target, rcond):
    return linalg.lstsq(design, target, cond=rcond, lapack_driver='gelsd')


def information(scores, rcond, coefficient=None):
    beta, _, rank, singular = least_squares(scores[:, 1:], scores[:, 0], rcond)
    if coefficient is not None:
        beta = coefficient
    residual = scores[:, 0]-np.einsum('ij,j->i', scores[:, 1:], beta)
    return dict(coefficient=beta, nuisance_rank=rank, nuisance_singular_values=singular,
                raw=batches(scores[:, 0]**2), effective=batches(residual**2),
                score_mean=batches(scores), efficient_mean=batches(residual),
                gram=np.einsum('ni,nj->ij', scores, scores)/len(scores)), residual


def analytic_projection(system, count, rcond):
    covariance, derivative = system['covariance'][:count, :count], system['derivatives'][:count]
    values, vectors = linalg.eigh(covariance, driver='evr')
    if values[-1] <= 0 or values[0] < -rcond*values[-1]:
        raise ValueError('independent analytic covariance is not positive semidefinite')
    keep = values > rcond*values[-1]
    whitened = (vectors[:, keep].T@derivative)/np.sqrt(values[keep, None])
    gram = whitened.T@whitened
    beta, _, rank, singular = least_squares(gram[1:, 1:], gram[1:, 0], rcond)
    linear = vectors[:, keep]@(whitened/np.sqrt(values[keep, None]))
    witness = linear[:, 0]-linear[:, 1:]@beta
    target, nuisance, variance = float(witness@derivative[:, 0]), witness@derivative[:, 1:], float(witness@covariance@witness)
    return dict(covariance_eigenvalues=values, covariance_rank=int(keep.sum()),
                covariance_condition=float(values[-1]/values[keep][0]), gram=gram,
                coefficient=beta, nuisance_gram_rank=rank, nuisance_gram_singular_values=singular,
                raw=float(gram[0, 0]), effective=float(gram[0, 0]-gram[0, 1:]@beta),
                witness=witness, witness_target=target, witness_nuisance=nuisance,
                witness_variance=variance, witness_ratio=target**2/variance if variance > 0 else None,
                linear_score_coefficients=linear)


def bridge(logratio):
    """Posterior-probability distance identity; no reader bridge is imported."""
    value = np.asarray(logratio, float)
    if not np.isfinite(value).all():
        raise ValueError('finite saved LLR required')
    # Work in long double to independently avoid small-L cancellation.
    half = abs(value.astype(np.longdouble))/2
    decay = np.exp(-half)
    tv = -np.expm1(-2*half)/(1+decay**2)
    h2 = 2*np.expm1(-half)**2/(1+decay**2)
    return dict(tv=np.asarray(tv, float), hellinger_squared=np.asarray(h2, float))


def ordinary_summary(x):
    x = np.asarray(x, float)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('at least two finite independent group values required')
    mean = math.fsum(x)/len(x)
    variance = math.fsum((float(value)-mean)**2 for value in x)/(len(x)-1)
    return dict(groups=len(x), mean=mean, sample_variance=variance, standard_error=math.sqrt(variance/len(x)))


def bridge_summary(first, second, bound, alpha, comparisons):
    a, b = ordinary_summary(first), ordinary_summary(second)
    estimate = (a['mean']+b['mean'])/2
    result = dict(null=a, alternative=b, estimate=estimate, group_weights=[.5, .5], range=[0., bound],
                  standard_error=.5*math.sqrt(a['sample_variance']/a['groups']+b['sample_variance']/b['groups']),
                  simultaneous_comparisons=comparisons)
    for name, failure in [('pointwise', alpha), ('simultaneous', alpha/comparisons)]:
        radius = bound*math.sqrt(math.log(2/failure)*(1/a['groups']+1/b['groups'])/8)
        result[name] = dict(lower=max(0., estimate-radius), upper=min(bound, estimate+radius),
                            radius=radius, failure_probability=failure)
    return result


def repeat_h2(value, repeats):
    value = np.asarray(value, np.longdouble)
    if repeats < 1 or np.any(value < 0) or np.any(value > 2):
        raise ValueError('valid Hellinger distance and repetitions required')
    # Finite geometric sum avoids the reader's log1p/expm1 implementation.
    affinity = 1-value/2
    total = np.zeros_like(value)
    power = np.ones_like(value)
    for _ in range(repeats):
        total += power
        power *= affinity
    result = np.asarray(value*total, float)
    return result.item() if result.ndim == 0 else result


def verify_bindings(config):
    if sha(PROTECTED) != config['protected_manifest_sha256']:
        raise ValueError('protected manifest binding changed')
    if len(read_json(PROTECTED)) != config['protected_file_count']:
        raise ValueError('protected baseline coverage changed')
    folders = {}
    for key, binding in config['inputs'].items():
        folder = ROOT/binding['path']
        for name, digest in binding['records'].items():
            if sha(folder/name) != digest:
                raise ValueError(f'{key}: bound source record changed: {name}')
        registration, attempt = read_json(folder/'registration.json'), read_json(folder/'attempt.json')
        if attempt['status'] != 'complete' or registration['git_head'] != binding['git_head']:
            raise ValueError(f'{key}: source stage is not the frozen completed attempt')
        if attempt['artifact_sha256'] != binding['artifacts']:
            raise ValueError(f'{key}: artifact manifest changed')
        for name, digest in binding['artifacts'].items():
            if sha(ROOT/name) != digest:
                raise ValueError(f'{key}: bound artifact changed: {name}')
        folders[key] = folder
    return folders


def audit_distances(folders, checks, config):
    source, folder = folders['oracle'], folders['distance']
    registration = read_json(folder/'registration.json')['config']
    rows = read_json(folder/'distance_cases.json')
    projections = read_json(folder/'repetition_projection.json')
    original_rows = read_json(source/'oracle_pairs.json')
    row_map = {(r['family'], r['pair_id'], r['repeats']):r for r in rows}
    original_map = {(r['family'], r['pair_id'], r['repeats']):r for r in original_rows}
    expected_keys, recomputed, coverage = set(), {}, []
    for family, definition in registration['families'].items():
        raw, saved = read_npz(source/f'oracle_{family}.npz'), read_npz(folder/f'bridge_{family}.npz')
        for field in ('pair_indices', 'repeats', 'candidates'):
            checks.equal(saved[field], raw[field], family+'/'+field)
        checks.equal(raw['repeats'], definition['repeats'], family+'/registered_R')
        checks.equal(len(raw['pair_indices']), definition['pairs'], family+'/registered_pairs')
        values = {}
        for role, source_name in [('null', 'evaluation_null_llr'), ('alternative', 'evaluation_alt_llr')]:
            llr = raw[source_name]
            checks.equal(llr.shape, [len(definition['repeats']), definition['pairs'], definition['evaluation_groups']],
                         family+'/'+role+'/denominators')
            values[role] = bridge(llr)
            for metric, array in values[role].items():
                checks.close(saved[role+'_'+metric], array, family+'/'+role+'/'+metric, 'distance')
        for ri, repeat in enumerate(raw['repeats']):
            for pi, (null, alt) in enumerate(raw['pair_indices']):
                key = (family, pi, int(repeat))
                expected_keys.add(key)
                if key not in row_map or key not in original_map:
                    raise ValueError(f'missing original/distance pair {key}')
                row, original = row_map[key], original_map[key]
                label = f'distance/{family}/{pi}/R{repeat}'
                checks.equal(row['null_condition'], int(null), label+'/null_id')
                checks.equal(row['alt_condition'], int(alt), label+'/alt_id')
                checks.equal([original['null_condition'], original['alt_condition']], [null, alt], label+'/source_ids')
                checks.equal([original['false_alarm']['groups'], original['power']['groups']],
                             [definition['evaluation_groups']]*2, label+'/source_denominators')
                checks.equal(row['null_theta'], raw['candidates'][null], label+'/null_theta')
                checks.equal(row['alternative_theta'], raw['candidates'][alt], label+'/alt_theta')
                checks.equal(raw['candidates'][null, 1:], raw['candidates'][alt, 1:], label+'/same_nuisance')
                checks.equal(bool(raw['candidates'][null, 0] < raw['candidates'][alt, 0]), True, label+'/ordered_interest')
                for metric, bound in [('tv', 1.), ('hellinger_squared', 2.)]:
                    summary = bridge_summary(values['null'][metric][ri, pi], values['alternative'][metric][ri, pi],
                                             bound, registration['interval_failure_probability'], 224)
                    checks.tree(row[metric], summary, label+'/'+metric, 'distance')
                    recomputed[key, metric] = summary
                checks.tree(row['null_negative_llr'], ordinary_summary(-raw['evaluation_null_llr'][ri, pi]), label+'/null_KL', 'distance')
                checks.tree(row['alternative_llr'], ordinary_summary(raw['evaluation_alt_llr'][ri, pi]), label+'/alt_KL', 'distance')
                checks.equal(row['uniform_log_ratio_error_certificate'], None, label+'/no_uniform_certificate')
                checks.equal(row['proxy_bias_certificate'], None, label+'/no_bias_certificate')
                coverage.append(dict(family=family, pair_id=pi, repeats=int(repeat), groups_per_law=definition['evaluation_groups']))
    checks.equal(len(rows), config['distance_rows'], 'distance/all_rows')
    checks.equal(len(row_map), len(rows), 'distance/no_duplicate_rows')
    checks.equal(set(row_map) == expected_keys, True, 'distance/exact_pair_grid')
    checks.equal(set(original_map) == expected_keys, True, 'distance/all_original_pairs')
    checks.equal(registration['simultaneous_comparisons'], 2*len(expected_keys), 'distance/Bonferroni_denominator')
    seen = set()
    for row in projections:
        key = (row['family'], row['pair_id'], row['repeats'])
        seen.add(key)
        first = recomputed[((key[0], key[1], 1), 'hellinger_squared')]
        repeat = key[2]
        expected = dict(plugin_hellinger_squared=repeat_h2(first['estimate'], repeat),
                        projected_pointwise=repeat_h2([first['pointwise']['lower'], first['pointwise']['upper']], repeat),
                        projected_simultaneous=repeat_h2([first['simultaneous']['lower'], first['simultaneous']['upper']], repeat),
                        observed_original_R=key in expected_keys, no_new_experiment=True, calibrated_detection_guarantee=False)
        if key in expected_keys:
            direct = recomputed[(key, 'hellinger_squared')]
            expected.update(direct_estimate=direct['estimate'],
                            direct_simultaneous=[direct['simultaneous']['lower'], direct['simultaneous']['upper']],
                            direct_minus_plugin=direct['estimate']-expected['plugin_hellinger_squared'])
        checks.tree(row, expected, 'projection/'+str(key), 'distance')
    expected_projection = {(family, pair, repeat) for family, pair, r in expected_keys if r == 1
                           for repeat in registration['projection_repeats']}
    checks.equal(len(projections), config['projection_rows'], 'projection/all_rows')
    checks.equal(len(seen), len(projections), 'projection/no_duplicates')
    checks.equal(seen == expected_projection, True, 'projection/exact_grid')
    result = read_json(folder/'results.json')
    checks.tree(result, dict(cases=len(expected_keys), projections=len(expected_projection), new_observations=0,
                            new_scientific_nodes=0, new_scientific_rules=0, actual_distance_certified=False,
                            empirical_optimal_power_certified=False, failures=0), 'distance/result', 'distance')
    return coverage


def audit_information(folders, checks, config):
    folder = folders['information']
    registration = read_json(folder/'registration.json')['config']
    rows = read_json(folder/'information_cases.json')
    result = read_json(folder/'results.json')
    checks.equal(len(rows), 4, 'information/four_points')
    checks.equal(result['rows'], rows, 'information/result_rows')
    checks.equal(registration['points'], config['points'], 'information/registered_points')
    checks.equal(registration['rcond'], config['rcond'], 'information/registered_rank_cutoff')
    checks.equal(registration['nuisance_fd_steps'], config['fd_steps'], 'information/registered_FD_steps')
    checks.equal([registration['train_size'], registration['heldout_size'], registration['batch_count']],
                 [config['train_size'], 1024, 8], 'information/registered_splits_and_batches')
    coverage = []
    for index, (row, point) in enumerate(zip(rows, config['points'])):
        name = f'point_{index:02d}'
        checks.equal(row, read_json(folder/f'{name}_summary.json'), name+'/summary_copy')
        checks.equal(row['point_id'], name, name+'/point_id')
        checks.equal(row['public_point'], point, name+'/public_point')
        checks.equal([row['new_observations'], row['train'], row['heldout']], [2048, 1024, 1024], name+'/all_denominators')
        raw = read_npz(folder/f'{name}_observations.npz')
        components = read_npz(folder/f'{name}_components.npz')
        saved = read_npz(folder/f'{name}_teacher.npz')
        state = geometry(**point)
        for key in components:
            checks.close(components[key], state[key], name+'/component/'+key)
        checks.equal(raw['public_point'], [point['mu'], point['tau'], point['sigma2']], name+'/raw_public_point')
        checks.equal(raw['y'].shape, [2048, 4], name+'/Y_shape')
        checks.equal(raw['gaussian_gain'].shape, [2048, 2], name+'/gain_shape')
        ids = raw['pdp_index']
        if ids.shape != (2048,) or not np.issubdtype(ids.dtype, np.integer) or np.any(ids < 0) or np.any(ids >= len(state['pdp'])):
            raise ValueError('invalid saved PDP assignment')
        symbols_id = raw['symbols_id']
        if symbols_id.shape != (2048, 4) or not np.issubdtype(symbols_id.dtype, np.integer) or np.any(symbols_id < 0) or np.any(symbols_id > 3):
            raise ValueError('invalid saved QPSK assignment')
        gain = raw['gaussian_gain']*np.sqrt(state['pdp'][ids])
        norm2 = np.einsum('bi,ij,bj->b', gain.conj(), state['gram'], gain).real
        if np.any(norm2 <= 0):
            raise ValueError('invalid saved actual gain normalization')
        normalized = gain/np.sqrt(norm2[:, None])
        response = normalized@state['response'].T
        symbols = np.exp(.25j*np.pi+.5j*np.pi*symbols_id)@state['daft'].conj()
        y = np.sqrt(point['tau'])*response*symbols+np.sqrt(point['sigma2'])*raw['standard_noise']
        checks.close(raw['normalized_gain'], normalized, name+'/latent/normalization')
        checks.close(raw['time_response'], response, name+'/latent/response')
        checks.close(raw['y'], y, name+'/latent/Y_replay')
        checks.close(np.sum(abs(response)**2, axis=1), np.full(2048, 4.), name+'/latent/G0_energy')
        evaluated = likelihood(raw['y'], state, point['sigma2'])
        checks.close(saved['logpdf'], evaluated['logpdf'], name+'/Bessel/logpdf', 'score')
        checks.close(saved['score'], evaluated['score'], name+'/Bessel/four_scores', 'score')
        fd = finite_differences(raw['y'], point, config['fd_steps'])
        errors = abs(fd-evaluated['score'][None, :, 1:])
        checks.equal(saved['steps'], config['fd_steps'], name+'/FD/steps')
        checks.close(saved['nuisance_fd'], fd, name+'/FD/all_values', 'finite_difference')
        checks.close(saved['nuisance_fd_error'], errors, name+'/FD/all_errors', 'finite_difference')
        qualified = np.all(errors <= registration['nuisance_fd_abs_tolerance'], axis=(0, 2))
        checks.equal(saved['formula_qualified'], qualified, name+'/FD/all_flags')
        checks.equal([row['formula_qualified'], row['formula_unqualified']], [int(qualified.sum()), int((~qualified).sum())], name+'/FD/counts')
        checks.close(row['fd_absolute_max_by_step'], errors.max(axis=(1, 2)), name+'/FD/maxima', 'finite_difference')
        geometric_fd = []
        for step in config['fd_steps']:
            wp, wm = geometry(point['mu']+step)['w'], geometry(point['mu']-step)['w']
            geometric_fd.append(dict(step=step, w_dot_max=float(np.max(abs((wp-wm)/(2*step)-state['w_dot']))),
                u0_dot_max=float(np.max(abs((wp/linalg.norm(wp)-wm/linalg.norm(wm))/(2*step)
                                            -(state['w_dot']/linalg.norm(state['w'])
                                              -state['w']*np.real(np.vdot(state['w'], state['w_dot']))/linalg.norm(state['w'])**3))))))
        for actual, expected in zip(row['geometry_fd'], geometric_fd):
            checks.tree(actual, expected, name+'/geometry_fd/'+str(expected['step']), 'finite_difference')
        checks.equal(row['geometry_signature'], [[True]*6+[False]*18, [False, False], [70, 70], [0, 0]], name+'/physical_signature')
        checks.close(row['kappa'], state['kappa'], name+'/kappa')
        checks.equal(row['pdp_components'], 138, name+'/actual_PDP_support')
        score, train_size, rcond = evaluated['score'], config['train_size'], config['rcond']
        train, heldout = score[:train_size], score[train_size:]
        fit, train_residual = information(train, rcond)
        test, heldout_residual = information(heldout, rcond, fit['coefficient'])
        projection = read_npz(folder/f'{name}_full_projection.npz')
        checks.tree(projection, dict(coefficient=fit['coefficient'], train_residual=train_residual,
                                     heldout_residual=heldout_residual), name+'/full_projection', 'linear_algebra')
        checks.tree(row['train_information'], fit, name+'/train_information', 'linear_algebra')
        checks.tree(row['heldout_information'], test, name+'/heldout_information', 'linear_algebra')
        zmean = abs(test['score_mean']['mean'])/test['score_mean']['batch_se']
        checks.close(row['heldout_score_mean_z'], zmean, name+'/score_mean_z', 'linear_algebra')
        checks.equal(row['score_mean_within_four_se'], zmean <= 4, name+'/mean_flags')
        checks.equal(row['positivity_diagnostic'], bool(test['effective']['mean'] > 4*test['effective']['batch_se']), name+'/positivity_diagnostic')
        system = moment_system(state, point['sigma2'])
        moment = read_npz(folder/f'{name}_moments.npz')
        for key in moment:
            checks.close(moment[key], system[key], name+'/moment/'+key)
        checks.equal(row['exact_moments_evaluated'], system['distinct_moments'], name+'/moment/full_catalog')
        powers = abs(state['m0'])**2
        checks.close(system['mean'][:4], powers.mean(axis=0)+point['sigma2'], name+'/moment/explicit_first')
        explicit_second = []
        for i, j in combinations_with_replacement(range(4), 2):
            if i == j:
                value = powers[:, i]**2+4*point['sigma2']*powers[:, i]+2*point['sigma2']**2
            else:
                value = (powers[:, i]+point['sigma2'])*(powers[:, j]+point['sigma2'])
            explicit_second.append(value.mean())
        checks.close(system['mean'][4:], explicit_second, name+'/moment/explicit_second')
        zero_mean, zero_derivative = exact_moment(state, np.zeros(4, int), point['sigma2'])
        checks.close([zero_mean, *zero_derivative], [1, 0, 0, 0, 0], name+'/moment/constant')
        ypower = raw['y'].real**2+raw['y'].imag**2
        features = np.column_stack([ypower, *[ypower[:, i]*ypower[:, j] for i, j in combinations_with_replacement(range(4), 2)]])
        checks.equal(len(row['feature_rows']), 2, name+'/two_feature_spaces')
        witness_diagnostics, identity_exceedances = [], []
        for feature_row, (level, count) in zip(row['feature_rows'], [('powers_degree1', 4), ('powers_degree1_and2', 14)]):
            label = name+'/'+level
            checks.equal([feature_row['level'], feature_row['dimension']], [level, count], label+'/identity')
            saved_feature = read_npz(folder/f'{name}_{level}.npz')
            analytic = analytic_projection(system, count, rcond)
            # Near zero, two valid roundoff paths can give unrelated 0/0 ratios.
            # Compare the identifiable algebra first, then replay the saved
            # witness itself against independently reconstructed D and V.
            checks.tree(feature_row['analytic'], {key:value for key, value in analytic.items() if key != 'witness_ratio'},
                        label+'/analytic', 'linear_algebra')
            frozen_witness = saved_feature['analytic_witness']
            target = float(frozen_witness@system['derivatives'][:count, 0])
            variance = float(frozen_witness@system['covariance'][:count, :count]@frozen_witness)
            ratio = target**2/variance if variance > 0 else None
            checks.tree(feature_row['analytic'], dict(witness_target=target, witness_variance=variance,
                        witness_nuisance=frozen_witness@system['derivatives'][:count, 1:], witness_ratio=ratio),
                        label+'/frozen_witness_arithmetic', 'linear_algebra')
            cancellation_scale = max(1., linalg.norm(analytic['linear_score_coefficients'][:, 0]),
                                     linalg.norm(analytic['linear_score_coefficients'][:, 1:]@analytic['coefficient']))
            witness_relative_size = float(linalg.norm(frozen_witness)/cancellation_scale)
            witness_diagnostics.append(dict(level=level, saved_ratio=feature_row['analytic']['witness_ratio'],
                replayed_ratio=ratio, independently_refitted_ratio=analytic['witness_ratio'],
                target=target, variance=variance, target_minus_variance=target-variance,
                witness_relative_size=witness_relative_size, rank_cutoff=rcond,
                below_registered_rank_scale=bool(witness_relative_size <= rcond), certified_positive_witness=False,
                scope='roundoff cancellation diagnostic only; unstable near-zero ratios are retained, never positivity certificates'))
            centered = features[:, :count]-system['mean'][:count]
            standardized = centered/np.sqrt(np.diag(system['covariance'])[:count])
            regression, _, rank, singular = least_squares(standardized[:train_size], train, rcond)
            prediction = standardized@regression
            pred_fit, residual_fit = information(prediction[:train_size], rcond)
            pred_test, residual_test = information(prediction[train_size:], rcond, pred_fit['coefficient'])
            linear_score, linear_residual = centered@analytic['linear_score_coefficients'], centered@analytic['witness']
            checks.tree(saved_feature, dict(features=features[:, :count], standardized=standardized, regression=regression,
                prediction=prediction, regression_nuisance_coefficient=pred_fit['coefficient'], linear_score=linear_score,
                linear_efficient_score=linear_residual, analytic_witness=analytic['witness'],
                analytic_linear_coefficients=analytic['linear_score_coefficients'], analytic_nuisance_coefficient=analytic['coefficient'],
                train_regression_residual=residual_fit, heldout_regression_residual=residual_test), label+'/raw', 'linear_algebra')
            cross = np.einsum('ni,nj->nij', centered[train_size:], heldout)
            expected = dict(regression_rank=rank, regression_singular_values=singular,
                regression_train=pred_fit, regression_heldout=pred_test,
                heldout_mse=batches((prediction[train_size:]-heldout)**2),
                linear_heldout_raw=batches(linear_score[train_size:, 0]**2),
                linear_heldout_effective=batches(linear_residual[train_size:]**2),
                score_feature_cross_heldout=cross.mean(axis=0),
                score_feature_identity_error=cross.mean(axis=0)-system['derivatives'][:count],
                identity_cross_batch_se=batches(cross)['batch_se'])
            checks.tree(feature_row, expected, label+'/statistics', 'linear_algebra')
            for feature_index, score_index in np.argwhere(abs(expected['score_feature_identity_error'])
                                                          > 4*expected['identity_cross_batch_se']):
                identity_exceedances.append(dict(level=level, feature=int(feature_index), score=int(score_index),
                    error=float(expected['score_feature_identity_error'][feature_index, score_index]),
                    batch_se=float(expected['identity_cross_batch_se'][feature_index, score_index]),
                    scope='descriptive four-SE exceedance from eight batches, not a familywise significance test'))
        coverage.append(dict(point_id=name, observations=len(score), train=len(train), heldout=len(heldout),
                             formula_unqualified=int((~qualified).sum()), moments=system['distinct_moments'], feature_spaces=2,
                             independent_raw=float(test['raw']['mean']), independent_effective=float(test['effective']['mean']),
                             witness_diagnostics=witness_diagnostics, cross_identity_exceedances=identity_exceedances))
    checks.tree(result, dict(new_observations=8192, cases=4, observations_per_point=2048,
                            formula_unqualified=sum(r['formula_unqualified'] for r in coverage),
                            receiver_calls=0, decoder_calls=0, new_confirmation_stream=False), 'information/result')
    costs = read_json(folder/'costs.json')
    checks.equal(costs, result['costs'], 'information/cost_copies')
    checks.equal(len(costs), 4, 'information/all_cost_rows')
    for index, cost in enumerate(costs):
        checks.tree(cost, dict(point_id=f'point_{index:02d}', finite_qpsk_orbits=64, phase_quadrature_nodes=0,
                               new_observations=2048), 'information/cost/'+str(index))
        times = [cost[key] for key in ('sample_seconds', 'teacher_and_fd_seconds', 'moments_and_projections_seconds', 'complete_case_seconds')]
        checks.equal(bool(np.isfinite(times).all() and min(times) >= 0 and sum(times[:3]) <= times[3]), True,
                     'information/cost/'+str(index)+'/finite_complete_time')
    return coverage


def calculate(output):
    config = read_json(CONFIG_PATH)
    folders = verify_bindings(config)
    before = audit_hashes(list(folders.values()), protected=PROTECTED)
    checks = Checks(config['tolerances'])
    checks.equal(before['counts']['protected'], 8669, 'hashes/complete_protected_baseline')
    distance = audit_distances(folders, checks, config)
    information_rows = audit_information(folders, checks, config)
    after = audit_hashes(list(verify_bindings(config).values()), protected=PROTECTED)
    checks.equal(before, after, 'hashes/before_after_and_costs')
    dump(output/'checks.json', checks.records)
    dump(output/'distance_coverage.json', distance)
    dump(output/'information_coverage.json', information_rows)
    dump(output/'input_audit.json', after)
    failures = [row for row in checks.records if not row['passed']]
    return dict(schema='collision-independent-audit/1', passed=not failures, checks=len(checks.records), failures=failures,
                distance_rows=len(distance), projection_rows=config['projection_rows'], information_rows=len(information_rows),
                reused_information_observations=sum(r['observations'] for r in information_rows),
                new_observations=0, new_scientific_nodes=0, new_scientific_rules=0, receiver_calls=0, decoder_calls=0,
                input_hash_counts=after['counts'], source_hashes_unchanged=before == after,
                scope='independent raw/formula/statistic replay; no theorem self-review or global numerical error certificate')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    config = read_json(CONFIG_PATH)
    sources = [*loaded_project_sources(sys.modules), Path(__file__).with_name('test_audit.py'), CONFIG_PATH, PROTECTED]
    for binding in config['inputs'].values():
        sources.extend(ROOT/binding['path']/name for name in binding['records'])
    run(args.stage, config, sources, calculate, wall_seconds=config['wall_seconds'])


if __name__ == '__main__':
    main()
