"""Observation-only C2 and actual-prior channels with explicit dependence.

H denotes the time-domain diagonal response, including sqrt(tau), not a dense
DAFT matrix. Latents are returned only for external diagnostics and raw replay.
"""
import numpy as np

from experiments.afdm_efficient_information.prior_likelihood import ActualPrior, daft
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain


def c2(y):
    """Only Y enters Q=T mean' S^-1 mean and the unbiased cross-symbol U.

    S uses ddof=1. No pseudoinverse, regularization, clipping, or truth inputs.
    Numerical failures are explicit records; malformed shapes raise at boundary.
    """
    y = np.asarray(y, dtype=np.complex128, order='C')
    if y.ndim != 2 or y.shape[1] != 4 or len(y) < 3:
        raise ValueError('C2 requires at least three N4 observation rows')
    result = dict(T=len(y), status='failed', failure=None, Q=None, U=None,
                  mean=None, covariance=None, rank=None, eigenvalues=None, ddof=1)
    if not np.isfinite(y).all():
        result['failure'] = 'nonfinite_observation'
        return result
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            power = abs(y)**2
            d = power[:, [0, 2]]-power[:, [1, 3]]
            total = d.sum(axis=0)
            mean = total/len(d)
            centered = d-mean
            covariance = centered.T@centered/(len(d)-1)
            u = float((total@total-np.sum(d*d))/(len(d)*(len(d)-1)))
            values = np.linalg.eigvalsh(covariance)
            rank = int(np.linalg.matrix_rank(covariance))
            result.update(U=u, mean=mean.tolist(), covariance=covariance.tolist(),
                          rank=rank, eigenvalues=values.tolist())
            if rank != 2 or values[0] <= 0:
                result['failure'] = 'nonpositive_or_rank_deficient_covariance'
                return result
            q = float(len(d)*mean@np.linalg.solve(covariance, mean))
            if not np.isfinite(q) or q < 0:
                result['failure'] = 'invalid_quadratic_statistic'
                return result
            result.update(status='ok', Q=q)
    except (FloatingPointError, np.linalg.LinAlgError) as error:
        result['failure'] = type(error).__name__+': '+str(error)
    return result


def conditional_contrast(h):
    """External diagnostic E[d(Y)|H]; never passed to c2."""
    power = abs(np.asarray(h))**2
    return power[..., [0, 2]]-power[..., [1, 3]]


def _latent(model, theta, count, seed, branch):
    # This exact prefix is replayed from ActualPrior.sample to retain its H.
    rng = np.random.default_rng(seed)
    latent = branch['pdp']
    index = rng.choice(len(latent['weights']), count, p=latent['weights'])
    z = (rng.standard_normal((count, 2))+1j*rng.standard_normal((count, 2)))/np.sqrt(2)
    gains = normalize_gain(z*np.sqrt(latent['pdp'][index]), branch['geometry']['gram'])
    h = np.exp(theta[2]/2)*(gains@branch['geometry'][model.model].T)
    return rng, dict(H=h, gains=gains, gaussian=z, pdp_index=index,
                     pdp=latent['pdp'][index])


def generate_group(model, theta, count, seed, mode):
    """One independent group; all requested T are prefixes of these observations.

    iid uses the original sample implementation, replaying only its latent prefix
    for diagnostic storage. That replay creates no second observation stream.
    Coherent draws exactly one actual channel and then independent QPSK/noise.
    """
    if not isinstance(model, ActualPrior) or model.n != 4 or model.model != 'g0' or model.pdp != 'marginal':
        raise ValueError('actual marginal-PDP N4 G0 model required')
    if isinstance(count, bool) or not isinstance(count, int) or count < 3:
        raise ValueError('integer group length >=3 required')
    if mode not in ('coherent', 'iid'):
        raise ValueError('unknown dependence mode')
    theta = model._validate(theta)
    branch = model.branch(theta)
    channels = count if mode == 'iid' else 1
    rng, latent = _latent(model, theta, channels, seed, branch)
    if mode == 'iid':
        y = model.sample(theta, count, seed)
    else:
        symbols = np.exp(1j*(np.pi/4+np.pi/2*rng.integers(0, 4, (count, model.n))))
        x = symbols@daft(model.n).conj()
        noise = (rng.standard_normal((count, model.n))+1j*rng.standard_normal((count, model.n)))/np.sqrt(2)
        y = latent['H']*x+np.exp(theta[3]/2)*noise
    return dict(Y=np.ascontiguousarray(y), seed=np.asarray(seed, dtype=np.uint32),
                theta=np.asarray(theta), conditional_contrast=conditional_contrast(latent['H']),
                gram=branch['geometry']['gram'], weights=branch['geometry']['weights'],
                dopplers=branch['geometry']['dopplers'], **latent)
