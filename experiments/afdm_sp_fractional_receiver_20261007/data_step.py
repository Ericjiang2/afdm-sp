"""Synchronous QPSK KL-MM with actual-objective and equation (8) checks.

Uniform original symbol priors are fixed. Finite log q is authoritative even
when exponentiation underflows; no probability floor or support deletion.
"""
import numpy as np
from scipy.special import logsumexp

from experiments.sp_afdm_frozen_20260920.src.messages import alphabet
from experiments.afdm_sp_fractional_20261007.moments import real_result
from .continuous import CoreFailure, count, finite, raise_with_evidence

DATA_POWER = .5
OBJECTIVE_TOLERANCE = 1e-9


def validate_log_q(log_q, n):
    values = np.asarray(log_q)
    if (values.shape != (n, 4) or np.iscomplexobj(values) or
            not np.isfinite(values).all()):
        raise ValueError('finite real N x 4 log probabilities required')
    values = values.astype(float, copy=True)
    if np.max(abs(logsumexp(values, axis=1))) > 1e-10:
        raise ValueError('log probabilities must already be normalized')
    return values


def data_moments(log_q):
    symbols, _ = alphabet(DATA_POWER)
    # Exponentiation may lose negligible mass; finite log q remains authoritative.
    with np.errstate(under='ignore'):
        probabilities = np.exp(log_q)
    mean = probabilities@symbols
    variance = np.sum(probabilities*abs(symbols[None, :]-mean[:, None])**2, axis=1)
    finite(mean, 'data mean')
    finite(variance, 'data variance')
    return probabilities, mean, variance


def kl(log_p, log_q):
    with np.errstate(under='ignore'):
        value = float(np.sum(np.exp(log_p)*(log_p-log_q)))
    finite(value, 'probability KL')
    if value < -1e-10*max(1, len(log_p)):
        raise CoreFailure('negative KL exceeds roundoff')
    return value


class DataStepper:
    """Three calls to step per sweep; operator is fixed for this object's life."""

    def __init__(self, operator, y, pilot, sigma2, log_q, counts):
        if not np.isfinite(sigma2) or sigma2 <= 0:
            raise ValueError('positive finite noise variance required')
        self.op, self.y, self.pilot = operator, y, pilot
        self.sigma2, self.counts = float(sigma2), counts
        self.log_q = validate_log_q(log_q, operator.n)
        count(counts, 'gram_diagonal_calls')
        self.diagonal = operator.gram_diagonal()
        count(counts, 'gram_diagonal_pair_terms_completed', operator.p*(operator.p-1)*operator.n)
        count(counts, 'mean_adjoint_calls')
        self.matched = operator.mean_adjoint(y)
        count(counts, 'mean_adjoint_path_terms_completed', operator.p*operator.n)
        off_diagonal = ~np.eye(operator.p, dtype=bool)
        gamma = float(np.trace(operator.second).real+abs(operator.second[off_diagonal]).sum())
        gap = gamma-float(np.min(self.diagonal))
        if gap < -1e-10*max(1., gamma):
            raise CoreFailure('invalid safe spectral bound')
        self.bound = max(0., gap)
        self.beta_safe = 2*DATA_POWER*self.bound/self.sigma2
        finite(self.beta_safe, 'safe KL curvature')
        self.max_level = int(np.ceil(np.log2(1+self.beta_safe)))
        _, mean, _ = data_moments(self.log_q)
        self.gx = self.gram(pilot+mean)
        self.objective = self.evaluate_objective(self.log_q)

    def gram(self, value):
        count(self.counts, 'gram_matvec_calls')
        result = self.op.gram_matvec(value)
        count(self.counts, 'gram_matvec_pair_terms_completed', self.op.p*(self.op.p-1)*self.op.n)
        return result

    def evaluate_objective(self, log_q):
        probabilities, mean, variance = data_moments(log_q)
        count(self.counts, 'source_preparations')
        source = self.op.prepare_source(self.pilot, mean, variance)
        count(self.counts, 'expected_quadratic_calls')
        quadratic = self.op.expected_quadratic(self.y, source)
        count(self.counts, 'expected_quadratic_pair_terms_completed',
              self.op.p*(self.op.p-1)//2*self.op.n)
        count(self.counts, 'data_objective_evaluations')
        result = -float(np.sum(probabilities*(log_q+np.log(4.))))-quadratic/self.sigma2
        finite(result, 'fixed data objective')
        return result

    def step(self):
        trace = dict(proposals=[])
        try:
            return self._step(trace)
        except Exception as error:
            raise_with_evidence(error, 'KL-MM data step failed: ',
                                dict(trace=trace, cause_type=type(error).__name__))

    def _step(self, trace):
        symbols, _ = alphabet(DATA_POWER)
        old_log_q = self.log_q
        _, mean, _ = data_moments(old_log_q)
        z = self.matched-self.gx+self.diagonal*mean
        logits = -np.log(4.)+(2/self.sigma2)*np.real(z[:, None]*symbols.conj())
        finite(logits, 'Jacobi log target')
        log_jacobi = logits-logsumexp(logits, axis=1, keepdims=True)
        trace.update(old_objective=self.objective, spectral_bound=self.bound,
                     beta_safe=self.beta_safe, maximum_backtracking_level=self.max_level,
                     fixed_point_kl=kl(old_log_q, log_jacobi))
        count(self.counts, 'data_steps_started')
        for level in range(self.max_level+1):
            beta = 2.**level-1
            eta = 1/(1+beta)
            entry = dict(level=level, beta=beta, eta=eta, status='started')
            trace['proposals'].append(entry)
            count(self.counts, 'data_proposals')
            proposed_logits = logits if level == 0 else eta*logits+(1-eta)*old_log_q
            proposed = proposed_logits-logsumexp(proposed_logits, axis=1, keepdims=True)
            finite(proposed, 'proposed log probabilities')
            probabilities, proposed_mean, _ = data_moments(proposed)
            delta = proposed_mean-mean
            g_delta = self.gram(delta)
            curvature = float(real_result(np.vdot(delta, g_delta-self.diagonal*delta),
                                          'candidate curvature'))/self.sigma2
            reverse = kl(old_log_q, proposed)
            forward = None if level == 0 else kl(proposed, old_log_q)
            penalty = 0. if level == 0 else beta*forward
            objective = self.evaluate_objective(proposed)
            increment = objective-self.objective
            identity_rhs = (1+beta)*reverse+penalty-curvature
            residual = increment-identity_rhs
            tolerance = OBJECTIVE_TOLERANCE*max(1., abs(self.objective), abs(objective))
            checks = dict(curvature=curvature <= penalty+tolerance,
                          identity=abs(residual) <= tolerance,
                          monotonicity=increment >= -tolerance,
                          increment_bound=increment+tolerance >= (1+beta)*reverse)
            accepted = all(checks.values())
            entry.update(status='completed', forward_kl=forward,
                         reverse_kl=reverse, curvature=curvature, penalty=penalty,
                         objective=objective, increment=increment, equation8_rhs=identity_rhs,
                         equation8_residual=residual, tolerance=tolerance, checks=checks,
                         accepted=accepted, exponentiation_zeros=int(np.count_nonzero(probabilities == 0)),
                         minimum_log_probability=float(np.min(proposed)))
            # Equation (8) holds for every geometric proposal, independently of
            # the curvature certificate. Backtracking must not hide a stale
            # Gram cache or another inconsistency by shrinking its residual.
            if not checks['identity']:
                count(self.counts, 'data_consistency_failures')
                raise CoreFailure('KL-MM equation (8) identity failed', trace)
            if checks['curvature'] and not (checks['monotonicity'] and checks['increment_bound']):
                count(self.counts, 'data_consistency_failures')
                raise CoreFailure('KL-MM certified increment is inconsistent', trace)
            if accepted:
                self.log_q, self.objective = proposed, objective
                self.gx = self.gx+g_delta
                count(self.counts, 'data_steps_completed')
                trace.update(accepted_level=level, new_objective=objective)
                return proposed.copy(), trace
            count(self.counts, 'data_proposals_rejected')
        raise CoreFailure('KL-MM final safe proposal failed its numerical checks', trace)
