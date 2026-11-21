"""Narrow covariance binding over the immutable E-1 geometry source."""
import hashlib
from pathlib import Path
from types import FunctionType

import numpy as np

# The E-1 selector has no covariance injection point. Instantiate its reviewed
# source in a private namespace and replace only its two variance FFT bindings.
E1_SOURCE_MD5 = '26571aa84e39097d264421a90bab23df'


def _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel):
    total, n = variance
    i, j = np.nonzero(left_delay[:, None] == right_delay)
    gamma = np.zeros((len(left_delay), len(right_delay)), dtype=complex)
    gamma[i, j] = total * dkernel(right_nu[j] - left_nu[i], n)
    return gamma


def load(full):
    from physical import dkernel

    def cross(left, right, variance, _c1, gamma_mode='full'):
        if gamma_mode != 'full':
            raise ValueError('The closed-form kernel expects the full-path selector')
        left_delay = np.fromiter((p.delay for p in left), dtype=int, count=len(left))
        right_delay = np.fromiter((p.delay for p in right), dtype=int, count=len(right))
        left_nu = np.fromiter((p.doppler for p in left), dtype=float, count=len(left))
        right_nu = np.fromiter((p.doppler for p in right), dtype=float, count=len(right))
        return _block(left_delay, left_nu, right_delay, right_nu, variance, dkernel)

    def projected_variance(v, delays, dopplers, _c1):
        delays, dopplers = np.asarray(delays), np.asarray(dopplers)
        gamma = _block(delays, dopplers, delays, dopplers, (float(v.sum()), len(v)), dkernel)
        return (gamma + gamma.conj().T) * .5

    p = Path(full.__file__)
    source = p.read_bytes()
    if hashlib.md5(source).hexdigest() != E1_SOURCE_MD5:
        raise ValueError('E-1 geometry source differs from the reviewed binding')
    original_line = b'vf = np.fft.fft(v)'
    if source.count(original_line) != 2:
        raise ValueError('Unexpected number of E-1 variance FFT paths')
    source = source.replace(original_line, b'vf = (float(v.sum()), len(v))')
    route = type(full)('stage3_codelay_geometry')
    route.__file__ = str(p)
    exec(compile(source, str(p), 'exec'), vars(route))
    system = full._system
    route._system = FunctionType(system.__code__,
                                 dict(system.__globals__, projected_variance=projected_variance),
                                 system.__name__, system.__defaults__)
    route._gamma_cross = cross
    return route
