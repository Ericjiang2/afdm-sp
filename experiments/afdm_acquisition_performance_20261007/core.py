"""Observation-only FFT screening and finite-grid QPSK mixture likelihood."""
import numpy as np

ARMS = ('current', 'quadratic', 'random')
METHODS = ('FOURTH', 'SCREEN32', 'FULL')
QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j])/np.sqrt(2)


def row_chirp(n):
    return np.exp(-5j*np.pi*np.arange(n)**2/n)


def ambiguity_objective(v):
    n = len(v)
    w = v**4
    q = w[None, :]*np.conj(w[(np.arange(n)[None, :]-np.arange(1, n)[:, None]) % n])
    values = np.abs(np.fft.ifft(q, axis=1)[:, 4*np.arange(n//4)])
    return float(np.max(values)), values


def simulate(states, standard_noise, v, delay, cfo, gain, sigma2):
    """Generator only; its hidden inputs never cross the estimator boundary."""
    t, n = states.shape
    signal = row_chirp(n)*np.fft.ifft(v*QPSK[states], axis=1, norm='ortho')
    clock = np.arange(t)[:, None]*(n+n//4)+np.arange(n)[None, :]
    return gain*np.exp(2j*np.pi*cfo*clock/n)*np.roll(signal, delay, axis=1)+np.sqrt(sigma2/2)*standard_noise


def fourth_scores(x, v):
    n = x.shape[1]
    shifted = (np.arange(n)[None, :]-np.arange(n)[:, None]) % n
    q = np.mean(x**4, axis=0)[None, :]*np.conj(v[shifted]**4)
    return np.abs(n*np.fft.ifft(q, axis=1)[:, 4*np.arange(n//4)])


def gain_grid():
    return (np.array([.75, 1., 1.25])[:, None]*np.exp(1j*np.arange(16)[None, :]*np.pi/32)).ravel()


def profile_likelihood(x, v, sigma2, hypotheses):
    """Return profile scores and gain indices; batch only to bound memory."""
    n = x.shape[1]
    gains = gain_grid()
    scores = np.empty(len(hypotheses))
    best_gains = np.empty(len(hypotheses), dtype=np.int64)
    for start in range(0, len(hypotheses), 16):
        selected = hypotheses[start:start+16]
        a, delay = selected//(n//4), selected % (n//4)
        shifted = (np.arange(n)[None, :]-a[:, None]) % n
        demod = np.conj(v[shifted])*np.exp(2j*np.pi*delay[:, None]*shifted/n)
        z = (x[None, :, :]*demod[:, None, :]).reshape(len(selected), -1)
        projected = np.sqrt(2)*z[:, None, :]*np.conj(gains)[None, :, None]/sigma2
        value = np.logaddexp(projected.real, -projected.real)
        value += np.logaddexp(projected.imag, -projected.imag)
        value = value.sum(axis=2)-z.shape[1]*(2*np.log(2)+np.abs(gains)**2/sigma2)
        best = np.argmax(value, axis=1)
        scores[start:start+len(selected)] = value[np.arange(len(selected)), best]
        best_gains[start:start+len(selected)] = best
    return scores, best_gains


def estimate(y, v, sigma2, method):
    """Complete call: validate, construct transforms/templates, search, output.

    Only observations, known code, known noise and fixed method enter. No cache.
    """
    y, v = np.asarray(y), np.asarray(v)
    if y.ndim != 2 or y.shape[0] < 1 or y.shape[1] < 4 or y.shape[1] % 4:
        raise ValueError('finite T by N observation with N divisible by four required')
    n = y.shape[1]
    if v.shape != (n,) or not np.isfinite(v).all() or not np.allclose(np.abs(v), 1., atol=1e-12, rtol=0):
        raise ValueError('known unit-modulus code of length N required')
    if not np.isfinite(y).all() or not np.isscalar(sigma2) or not np.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError('finite observations and positive noise variance required')
    if method not in METHODS:
        raise ValueError('unknown acquisition method')
    x = np.fft.fft(y*np.conj(row_chirp(n)), axis=1, norm='ortho')
    fourth = fourth_scores(x, v) if method != 'FULL' else np.empty((0,))
    hypotheses = np.arange(n*(n//4))
    if method == 'FOURTH':
        selected = int(np.argmax(fourth.ravel()))
        scores, best_gains = np.empty(0), np.empty(0, dtype=np.int64)
        hypotheses = np.empty(0, dtype=np.int64)
        objective = float(fourth.ravel()[selected])
        ties = int(np.count_nonzero(fourth == objective))
        gain_index, physical_gain = None, None
    else:
        if method == 'SCREEN32':
            shortlist = np.argsort(-fourth.ravel(), kind='stable')[:32]
            hypotheses = np.sort(shortlist)
        scores, best_gains = profile_likelihood(x, v, sigma2, hypotheses)
        index = int(np.argmax(scores))
        selected, gain_index = int(hypotheses[index]), int(best_gains[index])
        objective, ties = float(scores[index]), int(np.count_nonzero(scores == scores[index]))
        physical_gain = gain_grid()[gain_index]*np.exp(5j*np.pi*(selected % (n//4))**2/n)
        physical_gain = [float(physical_gain.real), float(physical_gain.imag)]
    a, delay = divmod(selected, n//4)
    if not np.isfinite(objective) or not np.isfinite(scores).all() or not np.isfinite(fourth).all():
        raise FloatingPointError('nonfinite acquisition score')
    return dict(a=a, delay=delay, cfo=(a-5*delay) % n, objective=objective,
                gain_index=gain_index, physical_gain_mod_C4=physical_gain, exact_ties=ties,
                hypotheses=hypotheses, profile_scores=scores, best_gain_indices=best_gains,
                fourth_scores=fourth, likelihood_hypotheses=len(hypotheses),
                gain_grid_evaluations=48*len(hypotheses))
