"""Simulation-only matched A/G/W observations; never an estimator input API."""
import hashlib

import numpy as np


def actual_coded_moments(generator, data_power):
    """Exact second moments from equality of nonzero GF(2) linear forms."""
    g = np.asarray(generator)
    if (g.ndim != 2 or not g.size or len(g) % 2 or not np.isin(g, [0, 1]).all()
            or not np.any(g, axis=1).all()):
        raise ValueError('nonzero binary generator rows and even length required')
    if not np.isfinite(data_power) or data_power < 0:
        raise ValueError('invalid transmitted data power')
    _, ids, counts = np.unique(np.packbits(g.astype(np.uint8), axis=1), axis=0,
                               return_inverse=True, return_counts=True)
    b = (ids[:, None] == ids[None, :]).astype(float)
    n = len(g)//2
    ii, qq, iq, qi = b[:n, :n], b[n:, n:], b[:n, n:], b[n:, :n]
    R = data_power/2*(ii+qq+1j*(qi-iq))
    P = data_power/2*(ii-qq+1j*(qi+iq))
    groups = [np.flatnonzero(ids == i).tolist() for i in np.flatnonzero(counts > 1)]
    return R, P, groups


def coded_second_moments(generator, data_power):
    """Certify second moments for uniform messages and all-I then all-Q QPSK.

    Nonzero distinct GF(2) linear forms produce unbiased pairwise independent
    bits. This does not assert independence of the whole codeword.
    """
    g = np.asarray(generator)
    if g.ndim != 2 or g.shape[0] % 2 or not g.shape[1] or not np.isin(g, [0, 1]).all():
        raise ValueError('binary generator with even nonempty code length required')
    if not np.isfinite(data_power) or data_power < 0:
        raise ValueError('invalid transmitted data power')
    if not np.any(g, axis=1).all():
        raise ValueError('constant coded bit: zero-mean certificate fails')
    if len(np.unique(np.packbits(g.astype(np.uint8), axis=1), axis=0)) != len(g):
        raise ValueError('duplicate coded linear forms: isotropic proper certificate fails')
    return dict(N=len(g)//2, k=g.shape[1], mean=0., covariance_diagonal=float(data_power),
                pseudo_covariance=0., generator_sha256=hashlib.sha256(g.tobytes()).hexdigest(),
                scope='uniform information bits; all-I then all-Q QPSK; pairwise moments only')


def augmented_factor(H, generator, data_power):
    """Complex output factor for a shared 2N-dimensional *real* Gaussian.

    Each equal coded form uses the Gaussian at its smallest bit index. Columns
    at other indices in that class are zero, retaining the coupling to W.
    """
    H=np.asarray(H);g=np.asarray(generator)
    if H.shape != (len(g)//2,len(g)//2) or not np.isfinite(H).all():
        raise ValueError('channel and code dimensions disagree')
    actual_coded_moments(g,data_power)  # validates the nonzero binary forms
    _,first,ids=np.unique(np.packbits(g.astype(np.uint8),axis=1),axis=0,
                           return_index=True,return_inverse=True)
    columns=np.concatenate((H,1j*H),axis=1)*np.sqrt(data_power/2)
    factor=np.zeros_like(columns)
    for j,representative in enumerate(first[ids]):
        factor[:,representative]+=columns[:,j]
    return factor


def matched_observations(H, pilot, data, noise, xi, factor, beta=1.):
    """Construct observations after the coded second-moment certificate passed.

    data already includes sqrt(data_power); noise already includes its scale.
    Expected interference energy is matched, never individual draw energy.
    """
    H = np.asarray(H)
    if H.ndim != 2 or H.shape[0] != H.shape[1] or not H.size:
        raise ValueError('nonempty square channel required')
    vectors = [np.asarray(v) for v in (pilot, data, noise)]
    if not np.isfinite(H).all() or any(v.shape != (len(H),) or not np.isfinite(v).all() for v in vectors):
        raise ValueError('finite channel-sized vectors required')
    xi=np.asarray(xi);factor=np.asarray(factor)
    if (xi.shape != (2*len(H),) or np.iscomplexobj(xi) or not np.isfinite(xi).all()
            or factor.shape != (len(H),2*len(H)) or not np.isfinite(factor).all()
            or beta not in (1., .25)):
        raise ValueError('invalid augmented real Gaussian inputs')
    pilot, data, noise = vectors
    z=(xi[:len(H)]+1j*xi[len(H):])/np.sqrt(2)
    trace = float(np.vdot(factor, factor).real)
    if not np.isfinite(trace):
        raise ValueError('nonfinite expected interference power')
    common = H@pilot+noise
    scale = np.sqrt(beta)
    return dict(A=common+scale*(H@data),
                G=common+scale*(factor@xi),
                W=common+scale*np.sqrt(trace/len(H))*z), dict(trace=trace, white_variance=trace/len(H))


def proper_gaussian(rng, shape, dtype=np.complex128):
    if np.dtype(dtype) not in (np.dtype('complex64'), np.dtype('complex128')):
        raise ValueError('complex Gaussian precision must be explicit')
    return ((rng.standard_normal(shape)+1j*rng.standard_normal(shape))/np.sqrt(2)).astype(dtype)
