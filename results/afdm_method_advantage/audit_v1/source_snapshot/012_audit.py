"""Independent, registered saved-data audit; no sampling or nuisance refitting.

Every record: reconstruct power moments from fitted parameters and saved Y,
then audit all statistics and summary decisions. Full-score sum/Gram are rebuilt
from Y only for the predeclared group-zero subset (every stage, every R).
No method or analysis statistic is imported. Frozen physical primitives are shared.
"""
import argparse
from functools import lru_cache
import gzip
import hashlib
from itertools import combinations_with_replacement, product
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import special, stats

from experiments.afdm_efficient_information.prior_likelihood import pdp_distribution, qpsk_time, system_for
from experiments.afdm_higher_order_information.prior import frozen_components, geometry
from experiments.afdm_method_advantage.protocol import ROOT, ARTIFACT, MISSION, dump, run

CONFIG_PATH = ARTIFACT/'METHOD_CONFIG.json'
SUPPLEMENT_PATH = ARTIFACT/'SUPPLEMENT_CONFIG.json'
SUPPLEMENT_COHORT = 'selected_supplement'
PROTECTED = MISSION/'protected_baseline.json'
TOLERANCE = dict(atol=1e-7, rtol=2e-6)
SUMMARY_TOLERANCE = dict(atol=1e-11, rtol=1e-9)
FULL_RAW_GROUPS = (0,)
PROTECTED_COUNT = 8862
FIT_NAMES = dict(full_score='mle', full_raw='mle', moment_score='m14', moment_raw='m14', moment_j='m14')


def read_json(path):
    path = Path(path)
    with (gzip.open(path, 'rt', encoding='utf-8') if path.suffix == '.gz'
          else path.open(encoding='utf-8')) as stream:
        return json.load(stream)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def records_file(folder):
    paths = [folder/name for name in ('records.json', 'records.json.gz') if (folder/name).is_file()]
    if len(paths) != 1:
        raise ValueError(f'exactly one record source required: {folder}')
    return paths[0]


class Checks:
    """Retain category counts, numerical errors, and concrete failed comparisons."""
    def __init__(self):
        self.categories = {}
        self.failures = []

    def compare(self, actual, expected, label, category='summary', **tolerance):
        group = self.categories.setdefault(category, dict(checks=0, failures=0, maximum_absolute_error=0.,
                                                         maximum_scaled_error=0.))
        group['checks'] += 1
        exact = expected is None or isinstance(expected, (str, bool, int, np.bool_, np.integer))
        error, scaled, valid = 0., 0., False
        if exact:
            valid = actual == expected and (not isinstance(expected, bool) or isinstance(actual, (bool, np.bool_)))
        else:
            left, right = np.asarray(actual), np.asarray(expected)
            if left.shape == right.shape and (left.dtype.kind in 'bUS' or right.dtype.kind in 'bUS'):
                valid = np.array_equal(left, right)
            elif left.shape == right.shape and left.dtype.kind in 'iufc' and right.dtype.kind in 'iufc':
                if np.isfinite(left).all() and np.isfinite(right).all():
                    delta = abs(left-right)
                    error = float(delta.max()) if delta.size else 0.
                    tol = tolerance or (SUMMARY_TOLERANCE if category == 'summary' else TOLERANCE)
                    scaled = float(np.max(delta/(tol['atol']+tol['rtol']*abs(right)))) if delta.size else 0.
                    valid = scaled <= 1.
        group['maximum_absolute_error'] = max(group['maximum_absolute_error'], error)
        group['maximum_scaled_error'] = max(group['maximum_scaled_error'], scaled)
        if not valid:
            group['failures'] += 1
            self.failures.append(dict(label=label, category=category, maximum_absolute_error=error,
                                      maximum_scaled_error=scaled, reason='value, shape, type or finiteness mismatch'))

    def tree(self, actual, expected, label, category='summary'):
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                self.compare(None, True, label, category)
                return
            for key, value in expected.items():
                if key not in actual:
                    self.compare(None, True, label+'/'+key+' missing', category)
                else:
                    self.tree(actual[key], value, label+'/'+key, category)
        elif isinstance(expected, list) and expected and isinstance(expected[0], dict):
            self.compare(len(actual), len(expected), label+'/length', category)
            for i, value in enumerate(expected):
                if i < len(actual):
                    self.tree(actual[i], value, label+f'/{i}', category)
        else:
            self.compare(actual, expected, label, category)

    def result(self):
        return dict(passed=not self.failures, checks=sum(x['checks'] for x in self.categories.values()),
                    failed_comparisons=len(self.failures), categories=self.categories, failures=self.failures)


def inverse(matrix, rcond):
    a = np.asarray(matrix, float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.isfinite(a).all() or not np.allclose(a, a.T):
        raise ValueError('finite symmetric matrix required for audit')
    eigenvalues, basis = np.linalg.eigh(a)
    if eigenvalues[-1] <= 0 or eigenvalues[0] < -rcond*eigenvalues[-1]:
        raise ValueError('indefinite/nonpositive audit matrix; no regularization')
    retained = eigenvalues > rcond*eigenvalues[-1]
    return (basis[:, retained]/eigenvalues[retained])@basis[:, retained].T


def features(y):
    y = np.asarray(y)
    if y.ndim != 2 or y.shape[1] != 4 or not len(y) or not np.isfinite(y).all():
        raise ValueError('nonempty finite N4 saved observations required')
    power = y.real**2+y.imag**2
    return np.column_stack([power[:, i] for i in range(4)] +
                           [power[:, i]*power[:, j] for i in range(4) for j in range(i, 4)])


@lru_cache(maxsize=1)
def physical_system():
    return system_for(4)


def physical_point(theta):
    """Differentiate finite Fourier weights while taking support from frozen geometry."""
    mu, log_tau, log_noise = np.asarray(theta, float)
    if not .22 <= mu <= .42 or not np.isfinite(theta).all():
        raise ValueError('saved fitted parameter outside public chart')
    system = physical_system()
    frozen = geometry(system, float(mu), 0.)
    time = 2*np.pi*np.arange(4)/4
    offsets = np.arange(-2, 3)
    orbit = np.exp(1j*(mu+offsets[:, None])*time)
    amplitudes = orbit.mean(axis=1)
    derivative = (orbit*(1j*time)).mean(axis=1)
    norm = np.linalg.norm(amplitudes)
    normalized_derivative = derivative/norm-amplitudes*np.real(np.vdot(amplitudes, derivative))/norm**3
    indices = np.arange(-system.k_max_cap, system.k_max_cap+1)
    dots = np.array([normalized_derivative[int(k)+2] if frozen['weights'][i, 0] != 0 else 0.
                     for i, k in enumerate(indices)])
    w = frozen['g0'][:, 0]
    dw = np.exp(1j*time[:, None]*indices)@dots
    length2 = np.vdot(w, w).real
    perpendicular = dw-w*np.vdot(w, dw)/length2
    perpendicular2 = np.vdot(perpendicular, perpendicular).real
    base = w/np.sqrt(length2)
    dbase = (dw-w*np.real(np.vdot(w, dw))/length2)/np.sqrt(length2)
    scale = np.sqrt(4*np.exp(log_tau))
    latent = pdp_distribution(4, float(mu), 0.)
    limit, k = int(latent['limits'][0]), latent['max_corrected_index']
    margin = min(mu-6*(limit/k-1), 6*((limit+1)/k-1)-mu)
    powers = latent['pdp']
    factor = latent['weights']@(4*powers[:, 0]*powers[:, 1]/powers.sum(axis=1)**2)
    return dict(base=scale*base, direction=scale*perpendicular/np.sqrt(perpendicular2),
                mu_derivative=scale*dbase, sigma2=float(np.exp(log_noise)),
                kappa=float(factor*perpendicular2/length2), margin=float(margin))


class MomentAlgebra:
    """Exact Gaussian radial polynomials as one independent coefficient matrix."""
    def __init__(self):
        def indices(dim, degree):
            return [tuple(np.bincount(items, minlength=dim)) for d in range(degree+1)
                    for items in combinations_with_replacement(range(dim), d)]
        self.powers = np.array(indices(4, 4), int)
        self.terms = np.array(indices(5, 4), int)
        row_index = {tuple(x):i for i, x in enumerate(self.powers)}
        term_index = {tuple(x):i for i, x in enumerate(self.terms)}
        self.features = np.array(indices(4, 2)[1:], int)
        self.first = np.array([row_index[tuple(x)] for x in self.features])
        self.second = np.array([[row_index[tuple(a+b)] for b in self.features] for a in self.features])
        self.coefficient = np.zeros((len(self.powers), len(self.terms)))
        symbol_power = abs(qpsk_time(4))**2
        for row, powers in enumerate(self.powers):
            for noise in product(*(range(int(p)+1) for p in powers)):
                signal = powers-np.array(noise)
                multiplier = math.prod(math.comb(int(p), int(j))**2*math.factorial(int(j))
                                       for p, j in zip(powers, noise))
                moment = np.prod(symbol_power**signal, axis=1).mean()
                column = term_index[tuple(signal)+(sum(noise),)]
                self.coefficient[row, column] += multiplier*moment

    def model(self, theta):
        point = physical_point(theta)
        p = abs(point['base'])**2
        variables = np.r_[p, point['sigma2']]
        if np.any(variables <= 0):
            raise ValueError('positive radial variables required in audit chart')
        monomial = np.prod(variables[None, :]**self.terms, axis=1)
        moments = self.coefficient@monomial
        mean = moments[self.first]
        covariance = moments[self.second]-np.outer(mean, mean)
        jac_variables = np.zeros((5, 3))
        jac_variables[:4, 0] = 2*np.real(point['base'].conj()*point['mu_derivative'])
        jac_variables[:4, 1] = p
        jac_variables[4, 2] = point['sigma2']
        jacobian = self.coefficient[self.first]@(monomial[:, None]*(self.terms@(jac_variables/variables[:, None])))
        ratio = point['direction']/point['base']
        radial = np.real(ratio[:, None]*ratio.conj()[None, :])
        signal = self.terms[:, :4]
        generator = np.einsum('bi,ij,bj->b', signal, radial, signal)-signal.sum(axis=1)
        target = point['kappa']*(self.coefficient[self.first]@(monomial*generator))
        return mean, covariance, np.column_stack((target, jacobian)), point


def full_scores(y, theta):
    """Analytic finite-QPSK/global-phase score, evaluated only on registered subset."""
    p = physical_point(theta)
    states = qpsk_time(4)
    means = states*p['base']
    directions = states*p['direction']
    derivatives = states*p['mu_derivative']
    noise = p['sigma2']
    energy = (abs(means)**2).sum(axis=1)
    observed_energy = (abs(y)**2).sum(axis=1)
    inner = y.conj()@means.T
    radius = abs(inner)
    argument = 2*radius/noise
    bessel_ratio = special.i1e(argument)/special.i0e(argument)
    phase = np.divide(inner.conj(), radius, out=np.zeros_like(inner), where=radius != 0)
    log_weights = -(observed_energy[:, None]+energy)/noise+np.log(special.i0e(argument))+argument
    probabilities = special.softmax(log_weights, axis=1)
    derivative_inner = y.conj()@derivatives.T
    target_inner = y.conj()@directions.T
    mean_target = (means.conj()*directions).sum(axis=1)
    target = p['kappa']*((abs(target_inner)**2+abs(mean_target)**2
        -2*bessel_ratio*np.real(target_inner*mean_target.conj()*phase))/noise**2
        -(abs(directions)**2).sum(axis=1)/noise+(energy-bessel_ratio*radius)/noise)
    center = 2*(bessel_ratio*np.real(phase*derivative_inner)
                -np.real((means.conj()*derivatives).sum(axis=1)))/noise
    log_signal = (bessel_ratio*radius-energy)/noise
    log_noise = -4+(observed_energy[:, None]+energy-2*bessel_ratio*radius)/noise
    return np.stack([(probabilities*x).sum(axis=1) for x in (target, center, log_signal, log_noise)], axis=1)


def local_fields(estimate, margin):
    maximum = margin**2*math.log(1/margin**2)
    return dict(unconstrained=float(estimate), one_sided=max(0., float(estimate)), local_only=True,
                fitted_delta_branch_radius=margin, r_branch_max=maximum,
                outside_fitted_local_branch=bool(max(0., estimate) >= maximum),
                unconstrained_below_zero=bool(estimate < 0))


def check_fit(fit, config, check, label):
    bounds = np.asarray(config['bounds'])
    for i, row in enumerate(fit['starts']):
        theta, gradient = np.asarray(row['theta']), np.array(row['gradient'], float)
        lower = abs(theta-bounds[:, 0]) <= config['boundary_tolerance']
        upper = abs(theta-bounds[:, 1]) <= config['boundary_tolerance']
        gradient[(lower & (gradient > 0)) | (upper & (gradient < 0))] = 0
        pg = float(abs(gradient).max())
        check.tree(row, dict(lower_boundary=lower, upper_boundary=upper, projected_gradient_max=pg,
                   success=bool(row['optimizer_success'] and pg <= config['stationarity_tolerance'])),
                   label+f'/start{i}', 'fits')
    selected = min(range(len(fit['starts'])), key=lambda i: fit['starts'][i]['objective'])
    best = fit['starts'][selected]
    check.tree(fit, dict(selected_start=selected, theta=best['theta'], objective=best['objective'],
               success=best['success'], on_boundary=bool(np.any(best['lower_boundary']) or np.any(best['upper_boundary'])),
               total_evaluations=sum(x['evaluations'] for x in fit['starts'])), label, 'fits')


def audit_record(record, y, config, algebra, check, label, raw_full=False):
    r, rcond = len(y), config['rcond']
    check.compare(record['observations'], r, label+'/observations', 'population')
    if 'costs' in record:
        recorded = record['costs']
        durations = [record['complete_seconds'], recorded['setup_seconds'], recorded['setup_original_construction_seconds'],
                     recorded['joint_complete_seconds'], recorded['shared_result_conversion_seconds'],
                     *recorded['per_method_seconds'].values()]
        if not np.isfinite(durations).all() or min(durations) < 0:
            raise ValueError(label+': invalid recorded timing')
        check.compare(recorded['per_method_setup_included'], False, label+'/setup excluded', 'costs')
    observed = features(y)
    expected = {name:None for name in ('full_score', 'full_raw', 'moment_score', 'moment_raw', 'moment_j')}
    fits, diagnostics = record['fits'], record['diagnostics']
    check_fit(fits['mle'], config, check, label+'/mle')
    for step in ('first', 'second'):
        if fits['m14'][step] is not None:
            check_fit(fits['m14'][step], config, check, label+'/m14/'+step)
    selected = fits['m14']['second'] if fits['m14']['second'] is not None else fits['m14']['first']
    check.tree(fits['m14'], {k:selected[k] for k in ('theta', 'success', 'on_boundary')}, label+'/m14', 'fits')
    check.compare(fits['m14']['observed_mean'], observed.mean(axis=0), label+'/observed_mean', 'moments')
    mean, covariance, derivative, point = algebra.model(fits['m14']['theta'])
    if fits['m14']['success']:
        d = diagnostics['moment']
        residual = observed.mean(axis=0)-mean
        weight = inverse(covariance, rcond)
        expected['moment_j'] = float(r*residual@weight@residual)
        check.tree(d, dict(model_mean=mean, covariance_matrix=covariance, observed_mean_residual=residual,
                           j_statistic=expected['moment_j']), label+'/moments', 'moments')
        available = point['margin'] > config['branch_tolerance']
        check.compare(d['tangent_failure'] is None, available, label+'/moment tangent availability', 'failures')
        if available:
            gram = derivative.T@weight@derivative
            beta = inverse(gram[1:, 1:], rcond)@gram[1:, 0]
            witness = weight@(derivative[:, 0]-derivative[:, 1:]@beta)
            raw_witness = weight@derivative[:, 0]
            variance, raw_variance = witness@covariance@witness, raw_witness@covariance@raw_witness
            target = witness@derivative[:, 0]
            expected['moment_score'] = float(np.sqrt(r)*(witness@residual)/np.sqrt(variance))
            expected['moment_raw'] = float(np.sqrt(r)*(raw_witness@residual)/np.sqrt(raw_variance))
            check.tree(d, dict(derivative_matrix=derivative, gram=gram, beta=beta, witness=witness,
                raw_witness=raw_witness, witness_target=float(target), witness_nuisance=witness@derivative[:, 1:],
                witness_variance=float(variance), raw_variance=float(raw_variance),
                numerator=float(r*witness@residual), denominator=float(np.sqrt(r*variance))), label+'/projection', 'moments')
            check.tree(record['r_hat']['moment_score'], local_fields(witness@residual/target, point['margin']),
                       label+'/moment_r', 'estimates')
    if fits['mle']['success']:
        p = physical_point(fits['mle']['theta'])
        available = p['margin'] > config['branch_tolerance']
        check.compare('full_score' in diagnostics, available, label+'/full tangent availability', 'failures')
        if available:
            d = diagnostics['full_score']
            gram, sums = np.asarray(d['gram']), np.asarray(d['score_sum'])
            beta = inverse(gram[1:, 1:], rcond)@gram[1:, 0]
            residual = np.r_[1., -beta]
            variance = residual@gram@residual
            numerator = residual@sums
            expected['full_score'] = float(numerator/np.sqrt(r*variance))
            expected['full_raw'] = float(sums[0]/np.sqrt(r*gram[0, 0]))
            check.tree(d, dict(beta=beta, numerator=float(numerator), score_mean=sums/r,
                raw_numerator=float(sums[0]), effective_second_moment=float(variance),
                raw_second_moment=float(gram[0, 0]), denominator=float(np.sqrt(r*variance))), label+'/full', 'full_sufficient')
            check.tree(record['r_hat']['full_score'], local_fields(numerator/(r*variance), p['margin']),
                       label+'/full_r', 'estimates')
            if raw_full:
                score = full_scores(y, fits['mle']['theta'])
                check.compare(sums, score.sum(axis=0), label+'/raw_full_sum', 'full_from_y')
                check.compare(gram, score.T@score/r, label+'/raw_full_gram', 'full_from_y')
    contrast = observed[:, [0, 2]]-observed[:, [1, 3]]
    average = contrast.mean(axis=0)
    cov = (contrast-average).T@(contrast-average)/r
    expected['second_moment'] = float(r*average@inverse(cov, rcond)@average)
    check.tree(diagnostics['second_moment'], dict(mean=average, covariance=cov,
        fitted_variance_pairs=[float(observed[:, :2].mean()), float(observed[:, 2:4].mean())]), label+'/c2', 'c2')
    for method, value in expected.items():
        check.compare(record['statistics'][method], value, label+'/'+method, 'statistics')
        if value is None:
            owner = 'full_score' if method.startswith('full') else 'moment_score'
            fit = fits['mle' if owner == 'full_score' else 'm14']
            kind = 'optimizer_failed' if not fit['success'] else 'tangent_unavailable'
            if not any(x['method'] == owner and x['kind'] == kind and x['reason'] for x in record['failures']):
                raise ValueError(label+': undefined statistic lacks failure evidence')
    return expected


def stage_binding(folder):
    registration, attempt = read_json(folder/'registration.json'), read_json(folder/'attempt.json')
    if registration['config'].get('mode') in ('calibration', 'evaluation') and registration['config'].get('cohort') not in (None, SUPPLEMENT_COHORT):
        raise ValueError('unregistered scientific cohort')
    return dict(path=str(folder.relative_to(ROOT)), mode=registration['config'].get('mode'),
                condition=registration['config'].get('condition'), cohort=registration['config'].get('cohort'), status=attempt['status'],
                metadata={name:sha(folder/name) for name in ('registration.json', 'attempt.json')},
                artifacts=attempt['artifact_sha256'])


def bind_inputs(summary_name, excluded_name=None):
    if Path(summary_name).name != summary_name:
        raise ValueError('one local summary stage name required')
    bindings = []
    for folder in sorted(ARTIFACT.iterdir()):
        if not folder.is_dir() or folder.name == excluded_name:
            continue
        if (folder/'registration.json').exists():
            bindings.append(stage_binding(folder))
    summary = [x for x in bindings if Path(x['path']).name == summary_name]
    if len(summary) != 1 or summary[0]['mode'] != 'analysis' or summary[0]['status'] != 'complete':
        raise ValueError('completed registered summary is required')
    return bindings


def verify_bindings(bindings):
    count = 0
    for binding in bindings:
        folder = ROOT/binding['path']
        for name, expected in binding['metadata'].items():
            if sha(folder/name) != expected:
                raise ValueError('bound metadata hash changed: '+str(folder/name))
        actual = {str(p.relative_to(ROOT)) for p in folder.rglob('*') if p.is_file() and p.name != 'attempt.json'}
        if actual != set(binding['artifacts']):
            raise ValueError('stage inventory differs from bound manifest: '+str(folder))
        for path, expected in binding['artifacts'].items():
            if sha(ROOT/path) != expected:
                raise ValueError('artifact hash changed: '+path)
            count += 1
    return dict(stages=len(bindings), artifacts=count, metadata=2*len(bindings))


def verify_protected(path=PROTECTED):
    manifest = read_json(path)
    for name, expected in manifest.items():
        if sha(ROOT/name) != expected:
            raise ValueError('protected baseline changed: '+name)
    return len(manifest)


def ordered_rows(dataset, repeat):
    return [dataset['records'][g, repeat] for g in range(dataset['groups'])]


def load_and_audit(bindings, config, check, cohort=None):
    datasets, subset = {}, []
    algebra = MomentAlgebra()
    for binding in bindings:
        mode = binding['mode']
        if mode not in ('calibration', 'evaluation') or binding.get('cohort') != cohort:
            continue
        if binding['status'] != 'complete':
            raise ValueError('failed scientific stage cannot be omitted')
        index = binding['condition']
        points = config['null_points' if mode == 'calibration' else 'evaluation_points']
        if type(index) is not int or not 0 <= index < len(points) or (mode, index) in datasets:
            raise ValueError('duplicate/unregistered scientific condition')
        folder = ROOT/binding['path']
        if [x.name for x in folder.glob('observations_*.npz')] != ['observations_00.npz']:
            raise ValueError('scientific stage must contain exactly one raw archive')
        registration, result = read_json(folder/'registration.json'), read_json(folder/'results.json')
        if registration['config']['frozen_config'] != config:
            raise ValueError('scientific config changed')
        point, groups = points[index], config[mode+'_groups']
        attempt = read_json(folder/'attempt.json')
        check.tree(attempt, dict(exit_code=0, reserved_new_observations=groups*max(config['repeats'])), folder.name+'/attempt')
        check.tree(registration['config'], dict(new_observations=groups*max(config['repeats']),
            receiver_calls=0, decoder_calls=0, new_confirmation_stream=False), folder.name+'/registration')
        generation = read_json(folder/'generation.json')
        seed = [*config['seed'], 1 if mode == 'calibration' else 2, index, 0]
        if len(generation) != 1 or generation[0]['point'] != point or generation[0]['seed'] != seed:
            raise ValueError('scientific generation metadata mismatch')
        with np.load(folder/'observations_00.npz', allow_pickle=False) as archive:
            y = archive['y']
            if (y.shape != (groups*max(config['repeats']), 4) or not np.isfinite(y).all()
                    or not np.array_equal(archive['seed'], seed)
                    or not np.array_equal(archive['theta'], [point['delta'], point['mu'], np.log(point['tau']), np.log(point['sigma2'])])):
                raise ValueError('raw saved population/seed/parameter mismatch')
        rows = read_json(records_file(folder))
        restored = []
        for checkpoint in sorted(folder.glob('checkpoint_*.json*')):
            restored.extend(read_json(checkpoint))
        if restored != rows:
            raise ValueError('checkpoint stream does not exactly reconstruct final records')
        mapping = {}
        for row in rows:
            key = (row['group'], row['repeats'])
            if key in mapping or key[0] not in range(groups) or key[1] not in config['repeats'] or row['local_condition'] != 0:
                raise ValueError('invalid/duplicate group and R prefix')
            observed = y[key[0]*max(config['repeats']):key[0]*max(config['repeats'])+key[1]]
            raw_full = key[0] in FULL_RAW_GROUPS
            audit_record(row, observed, config['method_config'], algebra, check, f'{cohort or "primary"}/{mode}/{index}/{key}', raw_full)
            if raw_full:
                subset.append(dict(stage=folder.name, group=key[0], repeats=key[1],
                    rebuilt='full_score' in row['diagnostics'], failure=not ('full_score' in row['diagnostics'])))
            mapping[key] = row
        if set(mapping) != {(g, r) for g in range(groups) for r in config['repeats']}:
            raise ValueError('incomplete group/R coverage')
        check.tree(result, dict(records=len(rows), failed_records=sum(bool(x['failures']) for x in rows),
            new_observations=groups*max(config['repeats']), groups=groups, points=[point]), folder.name+'/result')
        datasets[mode, index] = dict(records=mapping, groups=groups, binding=binding,
            generation=generation[0], attempt=read_json(folder/'attempt.json'))
    populations = [('evaluation', config['evaluation_points'])]
    if cohort is None:
        populations.insert(0, ('calibration', config['null_points']))
    expected = {(m, i) for m, points in populations for i in range(len(points))}
    if set(datasets) != expected:
        raise ValueError('main scientific stage coverage incomplete')
    return datasets, subset


def numeric_error(estimates, truth):
    array = np.asarray(estimates, float)
    if not len(array):
        return None
    difference = array-np.asarray(truth)
    return dict(count=len(array), bias=difference.mean(axis=0).tolist(), rmse=np.sqrt((difference**2).mean(axis=0)).tolist())


def nuisance_summary(rows, method, point):
    if method == 'second_moment':
        values = np.asarray([x['diagnostics']['second_moment']['fitted_variance_pairs'] for x in rows])
        return dict(failed_fits=0, boundary=0, nuisance_identifiable=False,
            fitted_variance_pairs=dict(count=len(values), mean=values.mean(axis=0).tolist(),
                                       minimum=values.min(axis=0).tolist(), maximum=values.max(axis=0).tolist()))
    fits = [x['fits'][FIT_NAMES[method]] for x in rows]
    estimates = np.asarray([x['theta'] for x in fits])
    transformed = np.column_stack((estimates[:, 0], np.exp(estimates[:, 1:])))
    successful = np.array([x['success'] for x in fits], bool)
    coordinates = [point['mu'], math.log(point['tau']), math.log(point['sigma2'])]
    physical = [point['mu'], point['tau'], point['sigma2']]
    return dict(failed_fits=int((~successful).sum()), boundary=sum(x['on_boundary'] for x in fits),
        all_coordinate_errors=numeric_error(estimates, coordinates), all_physical_errors=numeric_error(transformed, physical),
        successful_coordinate_errors=numeric_error(estimates[successful], coordinates),
        successful_physical_errors=numeric_error(transformed[successful], physical),
        optimizer_evaluations=sum(x['total_evaluations'] for x in fits))


def local_summary(rows, method, point):
    if method not in ('full_score', 'moment_score'):
        return None
    values = [row['r_hat'][method] for row in rows if row['r_hat'][method] is not None]
    mu, delta = point['mu'], point['delta']
    cell = lambda x: math.floor(67*(1+x/6))
    same = cell(mu-delta) == cell(mu) == cell(mu+delta)
    result = dict(available=len(values), missing=len(rows)-len(values), true_branch_preserved=same,
                  physical_delta_estimation_claim=False,
                  eligible=bool(delta > 0 and same and point['role'] != 'finite_separation'))
    if result['eligible']:
        truth = delta**2*math.log(1/delta**2)
        result['true_r'] = truth
        for name in ('unconstrained', 'one_sided'):
            array = np.array([x[name] for x in values])
            result[name] = None if not len(array) else dict(mean=float(array.mean()),
                bias=float((array-truth).mean()), rmse=float(np.sqrt(((array-truth)**2).mean())),
                relative_bias=float((array/truth-1).mean()),
                relative_rmse=float(np.sqrt(((array/truth-1)**2).mean())), zero_fraction=float((array == 0).mean()))
    return result


def wilson_interval(k, n, confidence):
    z = stats.norm.ppf(.5+confidence/2)
    denominator = n+z*z
    midpoint = (k+z*z/2)/denominator
    radius = z*np.sqrt(k*(n-k)/n+z*z/4)/denominator
    return dict(lower=max(0., float(midpoint-radius)), upper=min(1., float(midpoint+radius)), confidence=confidence)


def discordance_interval(candidate, baseline, family, confidence):
    plus = int(np.count_nonzero(candidate & ~baseline))
    minus = int(np.count_nonzero(~candidate & baseline))
    n, tail = len(candidate), (1-confidence)/(4*family)
    def bounds(k):
        return dict(lower=0. if k == 0 else float(special.betaincinv(k, n-k+1, tail)),
                    upper=1. if k == n else float(special.betaincinv(k+1, n-k, 1-tail)))
    p, m = bounds(plus), bounds(minus)
    return dict(groups=n, discordant_plus=plus, discordant_minus=minus, concordant=n-plus-minus,
                difference=(plus-minus)/n, lower=p['lower']-m['upper'], upper=p['upper']-m['lower'],
                plus_probability=p, minus_probability=m, family_size=family, tail_probability=tail,
                simultaneous_confidence=confidence)


def standalone_cost(dataset, repeat, method):
    rows = ordered_rows(dataset, repeat)
    all_costs = [x['costs'] for x in dataset['records'].values()]
    path = math.fsum(x['costs']['per_method_seconds'][method] for x in rows)
    cold = max([x['setup_original_construction_seconds'] for x in all_costs]+
               [x['setup_seconds'] for x in all_costs if not x['setup_cache_hit']]) if method != 'second_moment' else 0.
    warm = math.fsum(x['costs']['setup_seconds'] for x in rows if x['costs']['setup_cache_hit']) if method != 'second_moment' else 0.
    n = len(rows)
    return dict(groups=n, path_seconds=path, cold_setup_seconds=cold, warm_setup_seconds=warm,
                standalone_seconds=path+cold+warm, variable_seconds_per_group=(path+warm)/n,
                amortized_seconds_per_group=(path+cold+warm)/n,
                cold_first_group_seconds=rows[0]['costs']['per_method_seconds'][method]+cold)


def unique_index(rows, fields):
    mapping = {tuple(row[key] for key in fields):row for row in rows}
    if len(mapping) != len(rows):
        raise ValueError('duplicate summary rows')
    return mapping


def audit_summary(folder, datasets, config, check):
    cutoffs = unique_index(read_json(folder/'calibration.json'), ('repeats', 'method'))
    metrics = unique_index(read_json(folder/'metrics.json'), ('condition', 'repeats', 'method'))
    costs = unique_index(read_json(folder/'costs.json'), ('repeats', 'method'))
    comparisons = unique_index(read_json(folder/'comparisons.json'), ('condition', 'repeats', 'baseline'))
    actual_costs = unique_index(read_json(folder/'actual_stage_costs.json'), ('mode', 'condition'))
    decisions, failure_masks, thresholds, cal_failures, point_costs, rebuilt_metrics = {}, {}, {}, {}, {}, {}
    workload = len(config['evaluation_points'])*config['evaluation_groups']
    for r in config['repeats']:
        for method in config['methods']:
            key = (r, method)
            point_thresholds, failed = [], 0
            k = math.ceil((config['calibration_groups']+1)*(1-config['alpha']))
            for i, point in enumerate(config['null_points']):
                values = [x['statistics'][method] for x in ordered_rows(datasets['calibration', i], r)]
                ordered = sorted(math.inf if x is None else x for x in values)
                threshold = ordered[k-1] if k <= len(ordered) else math.inf
                point_thresholds.append(threshold)
                failures = sum(x is None for x in values)
                failed += failures
                check.tree(cutoffs[key]['null_grid'][i], dict(condition=i, point=point, groups=len(values),
                    order_index_one_based=k, failed=failures, threshold=None if math.isinf(threshold) else threshold,
                    finite_threshold=bool(math.isfinite(threshold))), f'calibration/{key}/{i}')
            threshold = max(point_thresholds)
            thresholds[key], cal_failures[key] = threshold, failed
            check.tree(cutoffs[key], dict(failed=failed, threshold=None if math.isinf(threshold) else threshold,
                finite_threshold=bool(math.isfinite(threshold)), calibration_groups=len(config['null_points'])*config['calibration_groups']),
                f'calibration/{key}')
            cal = [standalone_cost(datasets['calibration', i], r, method) for i in range(len(config['null_points']))]
            ev = [standalone_cost(datasets['evaluation', i], r, method) for i in range(len(config['evaluation_points']))]
            total_cal = math.fsum(x['standalone_seconds'] for x in cal)
            total_ev = math.fsum(x['standalone_seconds'] for x in ev)
            cost = dict(calibration_groups=len(config['null_points'])*config['calibration_groups'], evaluation_groups=workload,
                calibration_seconds=total_cal, evaluation_seconds=total_ev, fixed_workload_seconds=total_cal+total_ev,
                fixed_workload_amortized_seconds=(total_cal+total_ev)/workload, calibration_amortized_seconds=total_cal/workload)
            for name, rows in [('calibration', cal), ('evaluation', ev)]:
                cost[name+'_path_seconds'] = math.fsum(x['path_seconds'] for x in rows)
                cost[name+'_setup_seconds'] = math.fsum(x['cold_setup_seconds']+x['warm_setup_seconds'] for x in rows)
            check.tree(costs[key], cost, f'cost/{key}')
            for i, point in enumerate(config['evaluation_points']):
                rows = ordered_rows(datasets['evaluation', i], r)
                mask = np.array([x['statistics'][method] is None for x in rows])
                decision = np.array([x['statistics'][method] is not None and x['statistics'][method] > threshold for x in rows])
                item = (i, r, method)
                decisions[item], failure_masks[item] = decision, mask
                n, rejected, failures = len(rows), int(decision.sum()), int(mask.sum())
                fit = nuisance_summary(rows, method, point)
                c = dict(**ev[i], calibration_allocation_seconds_per_group=total_cal/workload,
                    complete_amortized_seconds_per_group=ev[i]['amortized_seconds_per_group']+total_cal/workload,
                    calibration_allocation_denominator=workload)
                point_costs[item] = c['complete_amortized_seconds_per_group']
                metric = dict(groups=n, rejections=rejected, rate=rejected/n, statistic_failures=failures,
                    wilson=wilson_interval(rejected, n, config['comparison']['confidence']),
                    failed_fits=fit['failed_fits'], boundary=fit['boundary'], fit_diagnostics=fit,
                    failure_bounds=dict(lower=rejected/n, upper=(rejected+failures)/n), calibration_failures=failed,
                    finite_grid_theorem_applies=point['role'] == 'grid_null', cost=c,
                    threshold=None if math.isinf(threshold) else threshold, finite_threshold=bool(math.isfinite(threshold)),
                    local_r_estimation=local_summary(rows, method, point))
                check.tree(metrics[item], metric, f'metric/{item}')
                rebuilt_metrics[item] = metric
    specification = config['comparison']
    candidate = specification['primary_candidate']
    audited = 0
    for i, point in enumerate(config['evaluation_points']):
        if point['delta'] <= 0:
            continue
        nulls = [j for j, p in enumerate(config['evaluation_points']) if p['role'] == 'grid_null' and p['sigma2'] == point['sigma2']]
        for r in config['repeats']:
            for baseline in specification['baselines']:
                ck, bk = (i, r, candidate), (i, r, baseline)
                c, b = decisions[ck], decisions[bk]
                cf, bf = failure_masks[ck], failure_masks[bk]
                interval = discordance_interval(c, b, specification['family_size'], specification['confidence'])
                null_rows = [rebuilt_metrics[j, r, m] for j in nulls for m in (candidate, baseline)]
                null_ok = bool(null_rows) and all(x['wilson']['upper'] <= specification['null_wilson_upper_limit'] for x in null_rows)
                failures = dict(candidate_alternative=int(cf.sum()), baseline_alternative=int(bf.sum()),
                    candidate_calibration=cal_failures[r, candidate], baseline_calibration=cal_failures[r, baseline],
                    related_null_evaluation=sum(x['statistic_failures'] for x in null_rows))
                no_failures = not any(failures.values())
                ratio = point_costs[bk]/point_costs[ck] if point_costs[ck] > 0 else None
                power = interval['difference'] >= specification['minimum_power_gain'] and interval['lower'] > 0
                cheaper = ratio is not None and ratio >= specification['minimum_cost_ratio'] and interval['lower'] > -specification['noninferiority_margin']
                expected = dict(paired=interval, related_null_conditions=nulls, failures=failures,
                    failure_difference_bounds=dict(lower=float(np.mean(c.astype(int)-b.astype(int)-bf)),
                                                   upper=float(np.mean(c.astype(int)+cf-b.astype(int)))),
                    null_gate_passed=null_ok, no_failures=no_failures, power_numeric_criterion=power,
                    cost_numeric_criterion=cheaper, power_advantage=power and null_ok and no_failures,
                    cost_advantage=cheaper and null_ok and no_failures, cost_ratio=ratio,
                    candidate_amortized_seconds=point_costs[ck], baseline_amortized_seconds=point_costs[bk])
                check.tree(comparisons[i, r, baseline], expected, f'comparison/{i}/{r}/{baseline}')
                audited += 1
    check.compare(len(comparisons), specification['family_size'], 'comparison coverage')
    check.compare(audited, specification['family_size'], 'independent comparison coverage')
    check.compare(len(metrics), len(config['evaluation_points'])*len(config['repeats'])*len(config['methods']), 'metric coverage')
    check.compare(len(actual_costs), len(datasets), 'actual cost coverage')
    check.compare(len(costs), len(config['repeats'])*len(config['methods']), 'cost coverage')
    check.compare(len(cutoffs), len(config['repeats'])*len(config['methods']), 'cutoff coverage')
    with np.load(folder/'decisions.npz', allow_pickle=False) as saved:
        shape = (len(config['evaluation_points']), len(config['repeats']), len(config['methods']), config['evaluation_groups'])
        if saved['rejected'].shape != shape or saved['failed'].shape != shape:
            raise ValueError('saved decision tensor dimensions changed')
        check.compare(saved['repeats'], np.array(config['repeats']), 'decision R')
        check.compare(saved['methods'].tolist(), config['methods'], 'decision method order')
        for (i, r, method), values in decisions.items():
            ri, mi = config['repeats'].index(r), config['methods'].index(method)
            check.compare(saved['rejected'][i, ri, mi].astype(int), values.astype(int), f'decision/{i}/{r}/{method}')
            check.compare(saved['failed'][i, ri, mi].astype(int), failure_masks[i, r, method].astype(int), f'failure/{i}/{r}/{method}')
    for key, dataset in datasets.items():
        rows = list(dataset['records'].values())
        result = dict(generation_seconds=dataset['generation']['seconds'])
        for out, source in [('actual_joint_setup_seconds', 'setup_seconds'), ('actual_joint_inference_seconds', 'joint_complete_seconds'),
                            ('shared_json_conversion_seconds', 'shared_result_conversion_seconds')]:
            result[out] = math.fsum(x['costs'][source] for x in rows)
        result['caller_complete_seconds'] = math.fsum(x['complete_seconds'] for x in rows)
        for name in ('wall_seconds', 'cpu_seconds', 'reserved_wall_seconds', 'reserved_new_observations'):
            result[name] = dataset['attempt'][name]
        check.tree(actual_costs[key], result, f'actual_cost/{key}')
    return dict(calibration_rows=len(cutoffs), metric_rows=len(metrics), comparison_rows=audited,
                evaluation_failed_method_groups=sum(int(x.sum()) for x in failure_masks.values()),
                calibration_failed_method_groups=sum(cal_failures.values()),
                power_advantages=sum(x['power_advantage'] for x in comparisons.values()),
                cost_advantages=sum(x['cost_advantage'] for x in comparisons.values()))


def audit_summary_bindings(folder, bindings, check):
    source = read_json(folder/'input_bindings.json')
    main = {x['path']:x for x in bindings if x['mode'] in ('calibration', 'evaluation') and x.get('cohort') is None}
    saved = {x['path']:x for x in source['source_bindings']}
    if len(saved) != len(source['source_bindings']) or set(saved) != set(main):
        raise ValueError('summary source binding population changed')
    artifacts = 0
    for path, binding in main.items():
        location = ROOT/path
        metadata = dict(binding['metadata'])
        metadata.update({name:sha(location/name) for name in (records_file(location).name, 'generation.json', 'results.json')})
        if saved[path]['artifact_sha256'] != binding['artifacts'] or saved[path]['metadata_sha256'] != metadata:
            raise ValueError('summary source hash bindings differ from independent inventory')
        artifacts += len(binding['artifacts'])
    historical = read_json(folder/'registration.json')['config']['excluded_stages']
    names = {x['stage'] for x in historical}
    excluded = {Path(x['path']).name:x for x in bindings if Path(x['path']).name in names}
    if set(excluded) != names:
        raise ValueError('a historical summary exclusion is missing')
    recorded = {x['stage']:x for x in source['excluded_stages']}
    if len(recorded) != len(source['excluded_stages']) or set(recorded) != set(excluded):
        raise ValueError('summary exclusion population changed')
    for name, binding in excluded.items():
        attempt = read_json(ROOT/binding['path']/'attempt.json')
        check.tree(recorded[name], dict(mode=binding['mode'], status=binding['status'],
            metadata_sha256=binding['metadata'], reserved_wall_seconds=attempt['reserved_wall_seconds'],
            reserved_new_observations=attempt['reserved_new_observations']), 'excluded/'+name)
    expected = dict(stages=len(main), artifacts=artifacts, metadata=5*len(main), observations_archives=len(main))
    check.tree(read_json(folder/'input_hash_counts.json'), expected, 'summary input hashes')
    check.tree(read_json(folder/'results.json'), dict(input_hash_counts=expected, source_hashes_unchanged=True), 'summary provenance')


def exact_rate_interval(k, n, confidence):
    tail = (1-confidence)/2
    return dict(lower=0. if k == 0 else float(special.betaincinv(k, n-k+1, tail)),
                upper=1. if k == n else float(special.betaincinv(k+1, n-k, 1-tail)),
                confidence=confidence, tail_probability=tail, interval='two-sided exact pointwise')


def saved_r_summary(rows, method):
    if method not in ('full_score', 'moment_score'):
        return None
    values = [x['r_hat'][method] for x in rows if x['r_hat'][method] is not None]
    result = dict(available=len(values), missing=len(rows)-len(values),
        outside_fitted_local_branch=sum(x['outside_fitted_local_branch'] for x in values),
        unconstrained_below_zero=sum(x['unconstrained_below_zero'] for x in values))
    for name in ('unconstrained', 'one_sided', 'fitted_delta_branch_radius', 'r_branch_max'):
        data = np.array([x[name] for x in values])
        result[name] = None if not len(data) else dict(count=len(data), mean=float(data.mean()),
                                                      minimum=float(data.min()), maximum=float(data.max()))
    return result


def audit_supplement_bindings(folder, primary_folder, bindings, check):
    saved = read_json(folder/'input_bindings.json')
    primary = next(x for x in bindings if ROOT/x['path'] == primary_folder)
    reference = saved['reference_binding']
    if ROOT/reference['path'] != primary_folder or reference['artifact_sha256'] != primary['artifacts']:
        raise ValueError('supplement references a different primary summary')
    for name, digest in reference['metadata_sha256'].items():
        if sha(primary_folder/name) != digest:
            raise ValueError('supplement primary reference hash mismatch')
    supplement = {x['path']:x for x in bindings if x['mode'] == 'evaluation' and x.get('cohort') == SUPPLEMENT_COHORT}
    sources = {x['path']:x for x in saved['source_bindings']}
    if len(sources) != len(saved['source_bindings']) or set(sources) != set(supplement):
        raise ValueError('supplement summary source population mismatch')
    artifacts = 0
    for path, source in supplement.items():
        location = ROOT/path
        metadata = dict(source['metadata'])
        metadata.update({name:sha(location/name) for name in (records_file(location).name, 'generation.json', 'results.json')})
        if metadata != sources[path]['metadata_sha256'] or source['artifacts'] != sources[path]['artifact_sha256']:
            raise ValueError('supplement source manifest mismatch')
        artifacts += len(source['artifacts'])
    counts = dict(stages=len(supplement), metadata=5*len(supplement), artifacts=artifacts,
                  observations_archives=len(supplement))
    check.tree(read_json(folder/'input_hash_counts.json'), counts, 'supplement input hashes')
    check.tree(read_json(folder/'results.json'), dict(input_hash_counts=counts, source_hashes_unchanged=True,
               primary_84_comparisons_unchanged=True), 'supplement provenance')


def audit_supplement_summary(folder, primary_folder, main_datasets, datasets, config, check):
    rows = unique_index(read_json(folder/'metrics.json'), ('condition', 'method'))
    saved_costs = unique_index(read_json(folder/'costs.json'), ('method',))
    paired_rows = unique_index(read_json(folder/'comparisons.json'), ('baseline',))
    actual_costs = unique_index(read_json(folder/'actual_stage_costs.json'), ('condition',))
    frozen_thresholds = unique_index(read_json(primary_folder/'calibration.json'), ('repeats', 'method'))
    thresholds = unique_index(read_json(folder/'calibration.json'), ('repeats', 'method'))
    decision, missing, metrics, amortized, cal_failures = {}, {}, {}, {}, {}
    group_count = config['evaluation_groups']
    workload = 2*group_count
    confidence = config['comparison']['confidence']
    k = math.ceil((config['calibration_groups']+1)*(1-config['alpha']))
    for method in config['methods']:
        key = (256, method)
        if thresholds[key] != frozen_thresholds[key]:
            raise ValueError('supplement modified the old calibration threshold payload')
        candidates, failures = [], 0
        for i in range(len(config['null_points'])):
            values = [x['statistics'][method] for x in ordered_rows(main_datasets['calibration', i], 256)]
            candidates.append(sorted(math.inf if x is None else x for x in values)[k-1])
            failures += sum(x is None for x in values)
        threshold, cal_failures[method] = max(candidates), failures
        check.tree(thresholds[key], dict(failed=failures, finite_threshold=bool(math.isfinite(threshold)),
            threshold=None if math.isinf(threshold) else threshold), 'supplement calibration/'+method)
        cal = [standalone_cost(main_datasets['calibration', i], 256, method) for i in range(len(config['null_points']))]
        ev = [standalone_cost(datasets['evaluation', i], 256, method) for i in range(2)]
        calibration = math.fsum(x['standalone_seconds'] for x in cal)
        evaluation = math.fsum(x['standalone_seconds'] for x in ev)
        check.tree(saved_costs[method,], dict(repeats=256, evaluation_groups=workload,
            calibration_groups=len(config['null_points'])*config['calibration_groups'], calibration_seconds=calibration,
            calibration_path_seconds=math.fsum(x['path_seconds'] for x in cal),
            calibration_setup_seconds=math.fsum(x['cold_setup_seconds']+x['warm_setup_seconds'] for x in cal),
            calibration_amortized_seconds=calibration/workload, evaluation_seconds=evaluation,
            fixed_workload_seconds=calibration+evaluation, fixed_workload_amortized_seconds=(calibration+evaluation)/workload),
            'supplement costs/'+method)
        for i, point in enumerate(config['evaluation_points']):
            records = ordered_rows(datasets['evaluation', i], 256)
            values = [x['statistics'][method] for x in records]
            decision[i, method] = np.array([value is not None and value > threshold for value in values])
            missing[i, method] = np.array([value is None for value in values])
            count, failures = int(decision[i, method].sum()), int(missing[i, method].sum())
            fit = nuisance_summary(records, method, point)
            cost = dict(**ev[i], calibration_allocation_denominator=workload,
                calibration_allocation_seconds_per_group=calibration/workload,
                complete_amortized_seconds_per_group=ev[i]['amortized_seconds_per_group']+calibration/workload)
            amortized[i, method] = cost['complete_amortized_seconds_per_group']
            metric = dict(groups=group_count, rejections=count, rate=count/group_count,
                wilson=wilson_interval(count, group_count, confidence),
                clopper_pearson=exact_rate_interval(count, group_count, confidence), statistic_failures=failures,
                failed_fits=fit['failed_fits'], boundary=fit['boundary'], fit_diagnostics=fit,
                threshold=None if math.isinf(threshold) else threshold, finite_threshold=bool(math.isfinite(threshold)),
                calibration_failures=cal_failures[method], failure_bounds=dict(lower=count/group_count, upper=(count+failures)/group_count),
                cost=cost, finite_grid_theorem_applies=False, local_r_estimation=local_summary(records, method, point),
                saved_r_diagnostics=saved_r_summary(records, method),
                selected_point_on_original_grid=any(all(point[key] == null[key] for key in ('mu', 'tau', 'sigma2', 'delta'))
                                                    for null in config['null_points']))
            metrics[i, method] = metric
            check.tree(rows[i, method], metric, f'supplement metric/{i}/{method}')
    candidate, specification = config['comparison']['candidate'], config['comparison']
    useful_cp = metrics[1, candidate]['clopper_pearson']
    useful = useful_cp['lower'] > specification['minimum_useful_power_lower']
    outcomes = []
    for baseline in specification['baselines']:
        c, b = decision[1, candidate], decision[1, baseline]
        cf, bf = missing[1, candidate], missing[1, baseline]
        interval = discordance_interval(c, b, 2, confidence)
        failures = dict(candidate_alternative=int(cf.sum()), baseline_alternative=int(bf.sum()),
            candidate_calibration=cal_failures[candidate], baseline_calibration=cal_failures[baseline],
            fresh_null=int(missing[0, candidate].sum()+missing[0, baseline].sum()))
        no_failures = not any(failures.values())
        finite = all(metrics[1, m]['finite_threshold'] for m in (candidate, baseline))
        null_checks = [dict(method=m, wilson_upper=metrics[0, m]['wilson']['upper'], failures=metrics[0, m]['statistic_failures'])
                       for m in (candidate, baseline)]
        null_ok = all(x['wilson_upper'] <= specification['null_wilson_upper_limit'] for x in null_checks)
        ratio = amortized[1, baseline]/amortized[1, candidate] if amortized[1, candidate] > 0 else None
        power = interval['difference'] >= specification['minimum_power_gain'] and interval['lower'] > 0
        noninferior = interval['lower'] > -specification['noninferiority_margin']
        fast = ratio is not None and ratio >= specification['minimum_cost_ratio']
        expected = dict(candidate=candidate, repeats=256, condition=1,
            hypothesis='power_gain' if baseline == 'moment_j' else 'useful_cost_noninferiority', paired=interval,
            failure_difference_bounds=dict(lower=float(np.mean(c.astype(int)-b.astype(int)-bf)),
                                           upper=float(np.mean(c.astype(int)+cf-b.astype(int)))),
            failures=failures, no_failures=no_failures, finite_thresholds=finite, null_gate_passed=null_ok,
            null_checks=null_checks, useful_power_passed=useful, useful_power_cp=useful_cp,
            power_numeric_criterion=power, noninferiority_passed=noninferior, cost_ratio_passed=fast,
            candidate_amortized_seconds=amortized[1, candidate], baseline_amortized_seconds=amortized[1, baseline], cost_ratio=ratio,
            power_advantage=baseline == 'moment_j' and power and null_ok and no_failures and finite,
            useful_cost_advantage=baseline == 'full_score' and noninferior and fast and useful and null_ok and no_failures and finite)
        outcomes.append(expected)
        check.tree(paired_rows[baseline,], expected, 'supplement paired/'+baseline)
    with np.load(folder/'decisions.npz', allow_pickle=False) as saved:
        shape = (2, len(config['methods']), group_count)
        if saved['rejected'].shape != shape or saved['failed'].shape != shape:
            raise ValueError('supplement decision dimensions mismatch')
        check.compare(saved['methods'].tolist(), config['methods'], 'supplement method order')
        check.compare(saved['repeats'], [256], 'supplement repeat order')
        for i in range(2):
            for j, method in enumerate(config['methods']):
                check.compare(saved['rejected'][i, j].astype(int), decision[i, method].astype(int), f'supplement decision/{i}/{method}')
                check.compare(saved['failed'][i, j].astype(int), missing[i, method].astype(int), f'supplement failures/{i}/{method}')
    for i in range(2):
        data = datasets['evaluation', i]
        records = list(data['records'].values())
        expected = dict(generation_seconds=data['generation']['seconds'],
            caller_complete_seconds=math.fsum(x['complete_seconds'] for x in records))
        for out, name in [('actual_joint_setup_seconds','setup_seconds'), ('actual_joint_inference_seconds','joint_complete_seconds'),
                          ('shared_json_conversion_seconds','shared_result_conversion_seconds')]:
            expected[out] = math.fsum(x['costs'][name] for x in records)
        for name in ('wall_seconds','cpu_seconds','reserved_wall_seconds','reserved_new_observations'):
            expected[name] = data['attempt'][name]
        check.tree(actual_costs[i,], expected, f'supplement actual costs/{i}')
    check.compare(len(rows), 2*len(config['methods']), 'supplement metric coverage')
    check.compare(len(saved_costs), len(config['methods']), 'supplement cost coverage')
    check.compare(len(thresholds), len(config['methods']), 'supplement threshold coverage')
    check.compare(len(paired_rows), 2, 'supplement comparison coverage')
    check.compare(len(actual_costs), 2, 'supplement actual cost coverage')
    return dict(metric_rows=len(rows), comparison_rows=len(outcomes), family_size=2,
                power_advantages=sum(x['power_advantage'] for x in outcomes),
                useful_cost_advantages=sum(x['useful_cost_advantage'] for x in outcomes),
                failed_method_groups=sum(int(x.sum()) for x in missing.values()))


def calculate(output):
    registration = read_json(output/'registration.json')['config']
    config, bindings = registration['frozen_config'], registration['bindings']
    if (sha(CONFIG_PATH) != registration['method_config_sha256'] or sha(PROTECTED) != registration['protected_manifest_sha256']
            or sha(SUPPLEMENT_PATH) != registration['supplement_config_sha256']):
        raise ValueError('audit registration source changed')
    if bind_inputs(registration['summary_stage'], output.name) != bindings:
        raise ValueError('audit stage population changed after registration')
    before = verify_bindings(bindings)
    protected = verify_protected()
    if protected != registration['protected_count']:
        raise ValueError('protected population count changed')
    checks = Checks()
    datasets, subset = load_and_audit(bindings, config, checks)
    supplement_config = registration['supplement_config']
    supplement, supplement_subset = load_and_audit(bindings, supplement_config, checks, SUPPLEMENT_COHORT)
    subset.extend(supplement_subset)
    all_datasets = [*datasets.values(), *supplement.values()]
    branch_counts = {}
    for method in ('full_score', 'moment_score'):
        estimates = [row['r_hat'][method] for dataset in all_datasets for row in dataset['records'].values()
                     if row['r_hat'][method] is not None]
        branch_counts[method] = dict(available=len(estimates),
            outside_fitted_local_branch=sum(x['outside_fitted_local_branch'] for x in estimates),
            unconstrained_below_zero=sum(x['unconstrained_below_zero'] for x in estimates))
    summary = ARTIFACT/registration['summary_stage']
    audit_summary_bindings(summary, bindings, checks)
    counts = audit_summary(summary, datasets, config, checks)
    checks.tree(read_json(summary/'results.json'), counts, 'summary results')
    supplement_summary = ARTIFACT/registration['supplement_summary_stage']
    audit_supplement_bindings(supplement_summary, summary, bindings, checks)
    supplement_counts = audit_supplement_summary(supplement_summary, summary, datasets, supplement, supplement_config, checks)
    checks.tree(read_json(supplement_summary/'results.json'), supplement_counts, 'supplement results')
    if verify_bindings(bindings) != before or verify_protected() != protected:
        raise ValueError('bound evidence changed during audit')
    excluded = [dict(stage=Path(x['path']).name, mode=x['mode'], status=x['status'],
                     reserved_wall_seconds=read_json(ROOT/x['path']/'attempt.json')['reserved_wall_seconds'],
                     reserved_new_observations=read_json(ROOT/x['path']/'attempt.json')['reserved_new_observations'])
                for x in bindings if x['mode'] not in ('calibration', 'evaluation')]
    result = dict(schema='method-advantage-independent-audit/1', mode='audit', new_observations=0,
        receiver_calls=0, decoder_calls=0, new_confirmation_stream=False, protected_files=protected,
        input_hash_counts=before, summary_counts=counts, supplement_summary_counts=supplement_counts,
        scientific_records=dict(primary=sum(len(x['records']) for x in datasets.values()),
                                supplement=sum(len(x['records']) for x in supplement.values())), comparison=checks.result(),
        full_score_raw_subset=subset, fitted_local_branch_counts=branch_counts, excluded_from_primary_population=excluded,
        coverage='all saved Y power features and fitted null moment models; all full sufficient-statistic algebra; full raw score on fixed group zero of every stage/R',
        limitations='does not refit nuisance, regenerate observations, certify global optimization or validate production latency',
        tolerance=TOLERANCE, summary_tolerance=SUMMARY_TOLERANCE)
    dump(output/'audit.json', result)
    (output/'AUDIT_RESULTS.md').write_text('# Independent saved-data audit\n\n'
        +f"Passed: {result['comparison']['passed']}. Compared {result['comparison']['checks']} quantities; "
        +f"{result['comparison']['failed_comparisons']} failures. Protected files: {protected}.\n\n"
        +result['coverage']+'.\n\n'+result['limitations']+'.\n')
    if not result['comparison']['passed']:
        raise ValueError('independent saved-data audit failed; see audit.json comparison failures')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', required=True)
    parser.add_argument('--summary-stage', default='summary_v1')
    parser.add_argument('--supplement-summary-stage', default='supplement_summary_v1')
    parser.add_argument('--wall-seconds', type=int, default=600)
    args = parser.parse_args()
    config = read_json(CONFIG_PATH)
    if len(read_json(PROTECTED)) != PROTECTED_COUNT:
        raise ValueError('expected exactly 8862 protected baseline files')
    bindings = bind_inputs(args.summary_stage, args.stage)
    supplement_config = read_json(SUPPLEMENT_PATH)
    if any(supplement_config[key] != config[key] for key in ('methods', 'method_config', 'null_points', 'calibration_groups', 'alpha', 'failure_policy')):
        raise ValueError('supplement changed the original methods or calibration')
    selected = [x for x in bindings if Path(x['path']).name == args.supplement_summary_stage]
    if len(selected) != 1 or selected[0]['mode'] != 'supplement_analysis' or selected[0]['status'] != 'complete':
        raise ValueError('complete selected supplement summary required')
    frozen_components()
    physical_system()
    qpsk_time(4)
    sources = {Path(__file__), Path(__file__).with_name('test_audit.py'), CONFIG_PATH, SUPPLEMENT_PATH, PROTECTED}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if filename:
            path = Path(filename).resolve()
            if path.is_relative_to(ROOT) and path.suffix == '.py' and path.is_file():
                sources.add(path)
    for binding in bindings:
        sources.update(ROOT/binding['path']/name for name in ('registration.json', 'attempt.json'))
    specification = dict(seed=config['seed'], mode='audit', new_observations=0, frozen_config=config,
        method_config_sha256=sha(CONFIG_PATH), protected_manifest_sha256=sha(PROTECTED),
        protected_count=PROTECTED_COUNT, summary_stage=args.summary_stage, bindings=bindings,
        supplement_config=supplement_config, supplement_config_sha256=sha(SUPPLEMENT_PATH),
        supplement_summary_stage=args.supplement_summary_stage,
        full_score_raw_group_subset=list(FULL_RAW_GROUPS), receiver_calls=0, decoder_calls=0,
        new_confirmation_stream=False, no_refitting=True, tolerance=TOLERANCE, summary_tolerance=SUMMARY_TOLERANCE)
    run(args.stage, specification, sorted(sources), calculate, wall_seconds=args.wall_seconds)


if __name__ == '__main__':
    main()
