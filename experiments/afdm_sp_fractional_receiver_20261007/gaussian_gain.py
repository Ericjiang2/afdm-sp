"""One full Gaussian gain solve for receivers and fixed-source diagnostics."""
import numpy as np
import scipy.linalg

from . import continuous


def solve_gain(gram, matched, sigma2, counts, *, prior_precision=None, with_logdet=False):
    """Solve [I,b] together; optional logdet reuses the same Cholesky factor.

    Default arithmetic, counter order and returned metadata match gain_update.
    Dynamic module lookups preserve the existing operation/fixture observers.
    """
    p = len(matched)
    if np.shape(gram) != (p, p) or np.shape(matched) != (p,) or p < 1:
        raise ValueError('nonempty gain Gram/vector dimensions required')
    if not np.isfinite(sigma2) or sigma2 <= 0:
        raise ValueError('positive finite gain noise variance required')
    prior = p if prior_precision is None else prior_precision
    if not np.isscalar(prior) or not np.isrealobj(prior) or not np.isfinite(prior) or prior <= 0:
        raise ValueError('positive scalar gain prior precision required')
    precision = prior*np.eye(p)+gram/sigma2
    continuous.finite(precision, 'gain precision')
    if np.linalg.norm(precision-precision.conj().T) > 1e-10*max(1., np.linalg.norm(precision)):
        raise continuous.CoreFailure('non-Hermitian gain precision')
    rhs = np.column_stack((np.eye(p), matched/sigma2))
    continuous.count(counts, 'gain_cholesky_calls')
    cholesky = np.linalg.cholesky(precision)
    continuous.count(counts, 'gain_triangular_solve_calls')
    intermediate = scipy.linalg.solve_triangular(cholesky, rhs, lower=True)
    continuous.count(counts, 'gain_triangular_solve_calls')
    solution = scipy.linalg.solve_triangular(cholesky.conj().T, intermediate, lower=False)
    continuous.finite(solution, 'joint gain solution')
    if with_logdet:
        continuous.count(counts, 'gain_residual_matrix_products')
        continuous.count(counts, 'gain_residual_matmul_terms', p*p*(p+1))
    residual = float(np.linalg.norm(precision@solution-rhs)/max(1., np.linalg.norm(rhs)))
    if residual > 1e-10:
        raise continuous.CoreFailure('joint gain solve residual exceeds tolerance', dict(residual=residual))
    covariance, mean = solution[:, :p], solution[:, p]
    continuous.count(counts, 'gain_updates_completed')
    continuous.count(counts, 'gain_solve_rhs_columns', p+1)
    detail = dict(mean=mean.copy(), covariance=covariance.copy(), gram=gram, matched=matched,
                  solve_residual=residual, dimension=p)
    if with_logdet:
        continuous.count(counts, 'gain_logdet_evaluations')
        continuous.count(counts, 'gain_logdet_diagonal_terms', p)
        logdet = float(2*np.log(cholesky.diagonal().real).sum())
        continuous.finite(logdet, 'gain log determinant')
        detail.update(precision=precision, cholesky=cholesky, logdet_precision=logdet,
                      prior_precision=float(prior), identity_rhs_columns=p, matched_rhs_columns=1)
    return mean, covariance, detail
