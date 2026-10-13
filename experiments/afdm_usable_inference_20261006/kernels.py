"""Observation-only inverse and deterministic diagnostic kernels; no RNG."""
import numpy as np
from scipy.optimize import brentq

from experiments.afdm_deep_principles_20261006.kernels import EvaluationCounter as EvaluationCounter
from experiments.afdm_efficient_information.prior_likelihood import system_for
from experiments.afdm_higher_order_information.prior import geometry


def count(counter, name, size=1):
    if counter is not None:
        counter.add(name, size)


def constants(n):
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 9:
        raise ValueError('integer N>=9 required for unaliased five-atom power')
    h = np.pi/n
    c, e = np.cos(h), np.cos(2*h)
    d = 2*c*c/e
    return h, c, e, d, e*e/(d*c*c)


def power_moments(mean_power, counter=None):
    power = np.asarray(mean_power, float)
    if power.ndim != 1 or not np.isfinite(power).all() or np.any(power < 0):
        raise ValueError('finite nonnegative one-dimensional mean power required')
    h, *_ = constants(len(power))
    count(counter, 'power_to_moments')
    spectrum = np.fft.fft(power)/len(power)
    lags = np.arange(2, 5)
    values = (np.exp(1j*lags*h)*spectrum[lags]).imag
    return dict(spectrum=spectrum, I=values)


def summarize_power(y):
    samples = np.asarray(y, complex)
    if samples.ndim != 2 or not len(samples) or not np.isfinite(samples).all():
        raise ValueError('nonempty finite T-by-N observations required')
    return np.mean(abs(samples)**2, axis=0)


def moment_matrix(n):
    h, *_ = constants(n)
    lags = np.arange(2, 5)[:, None]
    return np.sin(lags*h-2*np.pi*lags*np.arange(n)/n)/n


def _failure(status, diagnostics):
    return dict(status=status, nu=None, mu=None, delta=None, diagnostics=diagnostics)


def algebraic_inverse(values, n, branch, numerics, *, scale, counter=None):
    """Three moment inputs, before actual-mask admission; no hidden truth.

    One complete scalar solve is one kernel value. Its internal function-call
    count is also saved, but is not represented as a geometry or sample count.
    """
    h, c, e, d, k = constants(n)
    values = np.asarray(values, float)
    lower, upper = np.asarray(branch, float)
    if (values.shape != (3,) or not np.isfinite(values).all()
            or not 0 < lower < upper < .5 or not np.isfinite(scale) or scale < 0):
        raise ValueError('finite three moments, scale and positive open branch required')
    if (not 0 < numerics['weak_I4_relative'] < 1
            or not 0 < numerics['root_xtol'] < 1
            or not 0 < numerics['reconstruction_rtol'] < 1):
        raise ValueError('positive frozen numerical tolerances required')
    count(counter, 'algebraic_inverse')
    i2, i3, i4 = values
    diagnostics = dict(I=values.tolist(), scale=float(scale),
                       weak_I4_relative=numerics['weak_I4_relative'],
                       branch=[float(lower), float(upper)], branch_endpoints='open')
    if scale == 0 or abs(i4) <= numerics['weak_I4_relative']*scale:
        return _failure('weak_I4', diagnostics)
    x, v = c*d*i3/((d+1)*e*i4), i2/i4
    if not np.isfinite([x, v]).all():
        return _failure('nonfinite_ratio', diagnostics)
    diagnostics.update(x=float(x), v=float(v), x_minus_d=float(x-d))
    if x <= d:
        return _failure('invalid_ratio', diagnostics)

    def equation(p):
        return e*(1+d*d*p)+k*d*d+k*(d+1)*(d*p+1)/(p+1)*(x-d)-v

    y_low, y_high = np.tan(h)/np.tan(h*np.array([upper, lower]))
    p_low, p_high = y_low*y_low, y_high*y_high
    endpoints = [equation(p_low), equation(p_high)]
    diagnostics.update(product_bracket=[float(p_low), float(p_high)],
                       root_endpoint_residuals=list(map(float, endpoints)))
    if not endpoints[0] < 0 < endpoints[1]:
        return _failure('no_root_in_branch', diagnostics)
    p, solution = brentq(equation, p_low, p_high, xtol=numerics['root_xtol'],
                         full_output=True, disp=False)
    diagnostics.update(root_iterations=solution.iterations,
                       root_function_calls=solution.function_calls+2)
    if not solution.converged:
        return _failure('root_not_converged', diagnostics)
    a = (d-1)*(p+1)*(d*p-1)/(x-d)
    s_squared = (p+1)**2-a
    discriminant = s_squared-4*p
    diagnostics.update(product=float(p), A=float(a), sum_squared=float(s_squared),
                       discriminant=float(discriminant))
    if not np.isfinite([p, a, s_squared, discriminant]).all():
        return _failure('nonfinite_inverse', dict(I=values.tolist()))
    if s_squared <= 0 or discriminant <= 0:
        return _failure('invalid_discriminant', diagnostics)
    s, separation = np.sqrt(s_squared), np.sqrt(discriminant)
    y_plus = (s+separation)/2
    y_minus = p/y_plus
    nodes = np.array([y_plus, y_minus])  # Decreasing y means increasing Doppler.
    nu = np.arctan(np.tan(h)/nodes)/h
    residual = float(abs(equation(p))/max(1., abs(v)))
    diagnostics.update(sum=float(s), nodes=nodes.tolist(), root_residual=residual,
                       minimum_node=float(nodes.min()))
    if np.any(nodes <= 1) or np.any(nu <= lower) or np.any(nu >= upper):
        return _failure('outside_branch', diagnostics)
    if residual > numerics['reconstruction_rtol']:
        return _failure('inverse_residual', diagnostics)
    return dict(status='ok', nu=nu.tolist(), mu=float(nu.mean()),
                delta=float((nu[1]-nu[0])/2), diagnostics=diagnostics)


def actual_geometry(n, mu, delta, counter=None):
    count(counter, 'actual_geometry')
    return geometry(system_for(n), mu, delta)


def qualify_mask(result, n, counter=None):
    """Admit using the original clipping/cap/prune path at inferred nodes."""
    if result['status'] != 'ok':
        return result
    geo = actual_geometry(n, result['mu'], result['delta'], counter)
    keep = geo['weights'] != 0
    diagnostics = dict(result['diagnostics'], actual_weight_mask=keep.tolist(),
                       physical_clip_mask=geo['physical_clip_mask'].tolist())
    supported = (np.all(keep[:5]) and not np.any(keep[5:])
                 and not np.any(geo['physical_clip_mask']))
    if not supported:
        return _failure('unsupported_actual_mask', diagnostics)
    return dict(result, diagnostics=diagnostics)


def infer_power(mean_power, n, branch, numerics, counter=None):
    """Deployable inputs: observed mean power and declared model only."""
    power = np.asarray(mean_power, float)
    if power.shape != (n,):
        raise ValueError('mean power dimension differs from N')
    moments = power_moments(power, counter)
    result = algebraic_inverse(moments['I'], n, branch, numerics,
                               scale=float(np.max(power)), counter=counter)
    return qualify_mask(result, n, counter)


def inverse_jacobian(result, n, counter=None):
    """Analytic 2-by-3 derivative of ordered Dopplers with respect to I2,I3,I4."""
    if result['status'] != 'ok':
        raise ValueError('Jacobian requires an admitted interior inverse')
    count(counter, 'inverse_jacobian')
    h, c, e, d, k = constants(n)
    data = result['diagnostics']
    _, _, i4 = data['I']
    x, v, p, a, s = (data[key] for key in ['x', 'v', 'product', 'A', 'sum'])
    dx = np.array([0., c*d/((d+1)*e), -x])/i4
    dv = np.array([1., 0., -v])/i4
    fx = k*(d+1)*(d*p+1)/(p+1)
    fp = e*d*d+k*(d+1)*(d-1)*(x-d)/(p+1)**2
    dp = (dv-fx*dx)/fp
    ap = (d-1)*(2*d*p+d-1)/(x-d)
    ds = ((2*(p+1)-ap)*dp+a*dx/(x-d))/(2*s)
    separation = np.sqrt(data['discriminant'])
    dy_plus = .5*((1+s/separation)*ds-2*dp/separation)
    dy_minus = .5*((1-s/separation)*ds+2*dp/separation)
    nodes = np.asarray(data['nodes'])
    derivative = -np.tan(h)/(h*(nodes*nodes+np.tan(h)**2))
    jacobian = derivative[:, None]*np.vstack((dy_plus, dy_minus))
    if not np.isfinite(jacobian).all():
        raise FloatingPointError('nonfinite analytic inverse Jacobian')
    return jacobian


def oracle_moment_covariance(signal_power, noise_variance, counter=None):
    """T=1 exact covariance; latent power/noise are diagnostic-only inputs."""
    power = np.asarray(signal_power, float)
    if (power.ndim != 1 or not np.isfinite(power).all() or np.any(power < 0)
            or not np.isfinite(noise_variance) or noise_variance < 0):
        raise ValueError('finite nonnegative signal power/noise required')
    count(counter, 'oracle_moment_covariance')
    b = moment_matrix(len(power))
    values = b@power
    covariance = (b*(power+noise_variance)**2)@b.T-np.outer(values, values)/len(power)
    if not np.isfinite(covariance).all():
        raise FloatingPointError('nonfinite oracle moment covariance')
    return covariance


def imaginary_moment_formula(n, nu, effective_gain, counter=None):
    """Independent finite pair expansion, not the power FFT implementation."""
    count(counter, 'imaginary_moment_formula')
    h, c, e, d, _ = constants(n)
    y = np.tan(h)/np.tan(h*np.asarray(nu))
    gamma = np.asarray(effective_gain)
    gamma_factor = (y[1]-y[0])*(gamma[0]*gamma[1].conjugate()).imag
    nodes = np.array([-d, -1., 0., 1., d])
    scales = np.array([e, c, 1., c, e])
    denominators = (1+nodes*y[0])*(1+nodes*y[1])
    result = []
    for lag in (2, 3, 4):
        result.append(gamma_factor*sum(
            (nodes[m+lag]-nodes[m])/(scales[m+lag]*scales[m]*denominators[m+lag]*denominators[m])
            for m in range(5-lag)))
    return np.asarray(result), float(gamma_factor)


def phase_rows(values, n, *, adjoint=False):
    """Apply the actual U=R F^H C or its adjoint to row-stored vectors."""
    index = np.arange(n)
    row = np.exp(-2j*np.pi*(2.5/n)*index**2)
    column = np.exp(-2j*np.pi*(.1/n**2)*index**2)
    if adjoint:
        return np.fft.fft(values*row.conj(), axis=-1, norm='ortho')*column.conj()
    return np.fft.ifft(values*column, axis=-1, norm='ortho')*row


def quartic_samples(y, theta, amplitude, *, gradient=True, counter=None):
    samples, theta, amplitude = np.asarray(y, complex), np.asarray(theta, float), np.asarray(amplitude, float)
    if (samples.ndim != 2 or theta.shape != (samples.shape[1],) or amplitude.shape != theta.shape
            or not np.isfinite(samples).all() or not np.isfinite(theta).all()
            or not np.isfinite(amplitude).all() or np.any(amplitude <= 0)):
        raise ValueError('finite observations/phases and common positive amplitudes required')
    count(counter, 'qpsk_quartic_values', len(samples))
    b = samples*np.exp(-1j*theta)/amplitude
    z = phase_rows(b, samples.shape[1], adjoint=True)
    energy = abs(z)**2
    result = dict(score=np.sum(energy**2, axis=1), energy=np.sum(energy, axis=1), z=z)
    if gradient:
        count(counter, 'qpsk_gradient_vectors', len(samples))
        result['gradient'] = 4*(phase_rows(energy*z, samples.shape[1]).conj()*b).imag
    return result


def population_quartic(h, theta, amplitude, noise_variance, counter=None):
    count(counter, 'population_quartic_formula')
    h, theta, amplitude = np.asarray(h), np.asarray(theta), np.asarray(amplitude)
    if (h.ndim != 1 or theta.shape != h.shape or amplitude.shape != h.shape
            or np.any(amplitude <= 0) or np.any(abs(h) == 0)
            or not np.isfinite(h).all() or not np.isfinite(theta).all()
            or not np.isfinite(amplitude).all() or not np.isfinite(noise_variance) or noise_variance < 0):
        raise ValueError('nonzero finite H, common positive amplitudes and nonnegative noise required')
    n = len(h)
    q, phase = abs(h)/amplitude, np.angle(h)-theta
    transformed = np.fft.fft(q*np.exp(1j*phase))/n
    beta = np.mean(q*q)
    nu = noise_variance*np.mean(amplitude**-2)
    fourth = np.sum(abs(transformed)**4)
    best_fourth = np.sum(abs(np.fft.fft(q)/n)**4)
    unit = np.exp(1j*phase)
    unit_spectrum = np.fft.fft(unit)/n
    peak = int(np.argmax(abs(unit_spectrum)))
    closest = np.exp(1j*(np.angle(unit_spectrum[peak])+2*np.pi*peak*np.arange(n)/n))
    distance = float(np.sum(abs(unit-closest)**2))
    return dict(score=float(n*(2*beta*beta-fourth+4*beta*nu+2*nu*nu)),
                excess=float(n*(best_fourth-fourth)), distance_squared=distance,
                lower_bound=float(np.min(q)**4*distance/2),
                upper_bound=float(2*np.max(q)**4*distance), noise_output_variance=float(nu))
