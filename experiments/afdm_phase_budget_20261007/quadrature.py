"""Deterministic information integrals, without sampling observations."""
import numpy as np
from scipy.special import i0e, roots_hermite, roots_legendre


def phase_information(gamma, order):
    """Direct QPSK/circular-reference KL under one symmetry-equivalent symbol."""
    if not np.isscalar(gamma) or not np.isfinite(gamma) or gamma < 0:
        raise ValueError('finite nonnegative SNR required')
    if isinstance(order, bool) or not isinstance(order, int) or order < 8:
        raise ValueError('integer Hermite order >=8 required')
    nodes, weights = roots_hermite(order)
    weights /= np.sqrt(np.pi)
    z = np.sqrt(gamma/2) + nodes
    u = np.sqrt(2*gamma)*z
    logcosh = np.logaddexp(u, -u)-np.log(2.)
    radius = np.hypot(z[:, None], z[None, :])
    arg = 2*np.sqrt(gamma)*radius
    log_bessel = np.log(i0e(arg))+arg
    local = logcosh[:, None]+logcosh[None, :]-log_bessel
    phase = float(weights @ local @ weights)
    # I_BPSK = gamma - E logcosh(gamma + sqrt(gamma) Z).
    qpsk_information = float(2*gamma-2*(weights @ logcosh))
    gaussian = float(np.log1p(gamma)-qpsk_information)
    if not np.isfinite([phase, gaussian]).all():
        raise FloatingPointError('nonfinite quadrature')
    return dict(phase=phase, gaussian=gaussian, radial=gaussian-phase)


def fano(phase, samples, labels):
    phase = np.asarray(phase)
    return np.maximum(0., 1-(samples*phase+np.log(2.))/np.log(labels))


def calculate(config):
    records = []
    nominal = 10**(config['snr_db']/10)
    for rho_order in config['rho_orders']:
        nodes, weights = roots_legendre(rho_order)
        rho = 1+nodes/4
        # Uniform-radius prior: normalized weights, without an extra rho factor.
        weights = weights/2
        for hermite_order in config['hermite_orders']:
            values = [phase_information(nominal*r*r, hermite_order) for r in rho]
            phase = np.array([x['phase'] for x in values])
            gaussian = np.array([x['gaussian'] for x in values])
            bounds = []
            for samples, labels in config['cases']:
                bounds.append(dict(samples=samples, labels=labels,
                                   phase_fano=float(weights @ fano(phase, samples, labels)),
                                   gaussian_fano=float(weights @ fano(gaussian, samples, labels)),
                                   phase_average_first=float(fano(weights @ phase, samples, labels))))
            records.append(dict(rho_order=rho_order, hermite_order=hermite_order,
                                rho=rho.tolist(), weights=weights.tolist(), values=values, bounds=bounds))
    points = []
    for rho in config['rho_points']:
        value = phase_information(nominal*rho*rho, config['hermite_orders'][-1])
        points.append(dict(rho=rho, gamma=nominal*rho*rho, **value))
    return dict(new_observations=0, geometry_probes=0, acquisition_calls=0,
                random_draws=0, records=records, points=points,
                scope='Deterministic approximate integrals; convergence is not a certified interval proof.')
