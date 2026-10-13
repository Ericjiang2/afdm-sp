"""Independent radial-Bessel/BPSK integrals; no use of primary GH routine."""
import json
import hashlib
import warnings

import numpy as np
from scipy.integrate import IntegrationWarning, quad
from scipy.special import i0e, roots_legendre


def scalar_reference(gamma):
    if not np.isfinite(gamma) or gamma < 0:
        raise ValueError('finite nonnegative SNR required')
    def radial(u):
        arg = 2*np.sqrt(gamma)*u
        bessel = i0e(arg)
        density = 2*u*np.exp(-(u-np.sqrt(gamma))**2)*bessel
        return density*(np.log(bessel)+arg)

    def conditional_entropy(z):
        return np.exp(-z*z/2)/np.sqrt(2*np.pi)*np.logaddexp(0., -2*gamma-2*np.sqrt(gamma)*z)

    with warnings.catch_warnings():
        warnings.simplefilter('error', IntegrationWarning)
        circle_term, err_circle = quad(radial, 0, np.inf, epsabs=2e-11, epsrel=2e-11)
        conditional, err_bpsk = quad(conditional_entropy, -np.inf, np.inf, epsabs=2e-11, epsrel=2e-11)
    qpsk = 2*(np.log(2.)-conditional)
    return dict(phase=float(2*gamma-circle_term-qpsk),
                gaussian=float(np.log1p(gamma)-qpsk),
                reported_integration_error=float(err_circle+2*err_bpsk))


def audit(source, config):
    validate_primary(source, config)
    saved = json.loads(source.read_text())
    require(saved['new_observations'] == saved['geometry_probes'] == saved['acquisition_calls'] == saved['random_draws'] == 0,
            'zero data/call contract')
    records = saved['records']
    validate_structure(saved, config)
    saved_change = validate_convergence(records, config)
    direct = []
    max_error = 0.
    for point in saved['points']:
        reference = scalar_reference(point['gamma'])
        error = max(abs(point[k]-reference[k]) for k in ('phase', 'gaussian'))
        require(error <= config['scalar_tolerance'], 'independent point quadrature')
        require(abs(point['radial']-(reference['gaussian']-reference['phase'])) <= config['scalar_tolerance'],
                'independent point radial KL')
        direct.append(dict(rho=point['rho'], **reference, max_difference=error))
        max_error = max(max_error, error)
    recomputed_bounds = []
    for record in records:
        rho = np.array(record['rho'])
        weights = np.array(record['weights'])
        require(len(rho) == record['rho_order'] and abs(weights.sum()-1) < 1e-12,
                'normalized radius prior')
        require(np.all((rho > .75) & (rho < 1.25)) and np.all(weights > 0), 'radius support')
        # This independent formula audits every saved rho state, not only endpoints.
        refs = [scalar_reference(10**(config['snr_db']/10)*r*r) for r in rho]
        for a, b in zip(record['values'], refs):
            require(a['phase'] >= -config['scalar_tolerance'] and a['radial'] >= -config['scalar_tolerance'],
                    'KL nonnegativity')
            error = max(abs(a[k]-b[k]) for k in ('phase', 'gaussian'))
            require(error <= config['scalar_tolerance'], 'independent all-node quadrature')
            require(abs(a['radial']-(b['gaussian']-b['phase'])) <= config['scalar_tolerance'],
                    'independent all-node radial KL')
            max_error = max(max_error, error)
        bounds = []
        for item in record['bounds']:
            samples, labels = item['samples'], item['labels']
            phase = np.array([r['phase'] for r in refs])
            gaussian = np.array([r['gaussian'] for r in refs])
            recomputed = float(sum(weights*np.maximum(0., 1-(samples*phase+np.log(2))/np.log(labels))))
            require(abs(recomputed-item['phase_fano']) < config['fano_tolerance'], 'conditional Fano before averaging')
            gaussian_fano = float(sum(weights*np.maximum(0., 1-(samples*gaussian+np.log(2))/np.log(labels))))
            average_first = float(max(0., 1-(samples*sum(weights*phase)+np.log(2))/np.log(labels)))
            require(abs(gaussian_fano-item['gaussian_fano']) < config['fano_tolerance'], 'Gaussian control')
            require(abs(average_first-item['phase_average_first']) < config['fano_tolerance'], 'average-first control')
            require(item['phase_fano']+1e-12 >= item['phase_average_first'], 'Jensen direction')
            require(item['phase_fano']+1e-12 >= item['gaussian_fano'], 'circular reference improvement')
            bounds.append(recomputed)
        recomputed_bounds.append(bounds)
    matrix = np.array(recomputed_bounds)
    max_change = float(np.max(abs(matrix-matrix[-1])))
    require(max_change <= config['fano_tolerance'], 'frozen quadrature convergence')
    return dict(new_observations=0, geometry_probes=0, acquisition_calls=0, random_draws=0,
                audit_pass=True, independent_points=direct, max_scalar_difference=max_error,
                max_fano_resolution_change=max_change, finest_bounds=records[-1]['bounds'],
                max_saved_fano_resolution_change=saved_change,
                scope='All scalar nodes independently integrated; numerical tolerances are not rigorous interval enclosures.')


def validate_structure(saved, config):
    records = saved['records']
    expected_orders = [(r, h) for r in config['rho_orders'] for h in config['hermite_orders']]
    require([(r['rho_order'], r['hermite_order']) for r in records] == expected_orders,
            'exact frozen quadrature combinations and order')
    require([p['rho'] for p in saved['points']] == config['rho_points'], 'all fixed radius points')
    for p in saved['points']:
        require(abs(p['gamma']-10**(config['snr_db']/10)*p['rho']**2) < 1e-12, 'point SNR')
        require(np.isfinite([p[k] for k in ('phase', 'gaussian', 'radial')]).all(), 'finite point information')
    for record in records:
        order = record['rho_order']
        require(len(record['values']) == len(record['rho']) == len(record['weights']) == order,
                'no missing quadrature states')
        nodes, weights = roots_legendre(order)
        require(np.allclose(record['rho'], 1+nodes/4, rtol=0, atol=1e-14), 'frozen GL nodes')
        require(np.allclose(record['weights'], weights/2, rtol=0, atol=1e-14), 'frozen GL weights')
        require([[b['samples'], b['labels']] for b in record['bounds']] == config['cases'],
                'all frozen sample/label cases')
        for value in record['values']:
            require(np.isfinite([value[k] for k in ('phase', 'gaussian', 'radial')]).all(),
                    'finite node information')
        for value in record['bounds']:
            require(np.isfinite([value[k] for k in ('phase_fano', 'gaussian_fano', 'phase_average_first')]).all(),
                    'finite bound')


def validate_primary(source, config):
    attempt = json.loads(source.with_name('attempt.json').read_text())
    require(attempt['status'] == 'complete' and attempt['exit_code'] == 0, 'primary completed without error')
    require(attempt['artifact_sha256'][str(source.resolve())] == hashlib.sha256(source.read_bytes()).hexdigest(),
            'primary result SHA256')
    registration = source.with_name('registration.json')
    require(attempt['artifact_sha256'][str(registration.resolve())] == hashlib.sha256(registration.read_bytes()).hexdigest(),
            'primary registration SHA256')
    expected_config = dict(config, phase='Q')
    require(json.loads(registration.read_text())['config'] == expected_config, 'primary frozen registration')


def validate_convergence(records, config):
    matrix = np.array([[[b[k] for k in ('phase_fano', 'gaussian_fano', 'phase_average_first')]
                        for b in r['bounds']] for r in records])
    require(np.isfinite(matrix).all(), 'finite convergence matrix')
    change = float(np.max(abs(matrix-matrix[-1])))
    require(change <= config['fano_tolerance'], 'saved four-resolution Fano convergence')
    return change


def require(condition, message):
    if not condition:
        raise ValueError(message)
