"""Fixed soft-data Gaussian elimination and point-Doppler Schur coordinates.

No I/O, reference values, receiver state mutation, clipping or jitter. Source
ownership remains with the canonical PathMoments instance throughout a run.
"""
import time

import numpy as np
import scipy.linalg

from experiments.afdm_sp_fractional_20261007.moments import real_result, real_scalar, vector
from . import continuous
from .gaussian_gain import solve_gain


def _hermitian(value, name):
    continuous.finite(value, name)
    error = float(np.linalg.norm(value-value.conj().T)/max(1., np.linalg.norm(value)))
    if error > 1e-10:
        raise continuous.CoreFailure('non-Hermitian '+name, dict(normalized_error=error))
    return error


def _freeze(*values):
    for value in values:
        value.setflags(write=False)


class CollapsedGain:
    """One base geometry and one immutable soft-data source; no gain fitting prior."""

    def __init__(self, op, source, y, sigma2, counts):
        self.op, self.source, self.counts = op, source, counts
        self.preparations = []
        detail = dict(status='started')
        try:
            op._source(source)
            if op.nodes.shape != (op.p, 1) or not np.all(op.weights == 1):
                raise ValueError('collapsed coordinates require deterministic Dopplers')
            self.dopplers = op.nodes[:, 0].copy()
            if np.any(abs(self.dopplers) > 3):
                raise ValueError('collapsed base Doppler outside [-3,3]')
            self.sigma2 = real_scalar(sigma2, 'collapsed noise variance', positive=True)
            self.y = vector(y, op.n, 'collapsed observation')
            continuous.count(counts, 'collapsed_initial_statistics_started')
            self.gram, self.matched = op.gain_statistics(self.y, source)
            detail.update(gram=self.gram, matched=self.matched)
            _hermitian(self.gram, 'collapsed base Gram')
            continuous.finite(self.matched, 'collapsed base matched vector')
            continuous.count(counts, 'collapsed_initial_statistics_completed')
            continuous.count(counts, 'collapsed_initial_pair_terms', op.p*(op.p-1)*op.n)
            _freeze(self.y, self.dopplers, self.gram, self.matched)
        except Exception as error:
            continuous.raise_with_evidence(error, 'collapsed source preparation failed: ',
                                           dict(detail=detail, counts=dict(counts), source_work=dict(op.work_counts)))

    def prepare(self, coordinate):
        detail = dict(coordinate=coordinate, status='started')
        self.preparations.append(detail)
        try:
            return SchurCoordinate(self, coordinate, detail)
        except Exception as error:
            continuous.raise_with_evidence(error, 'collapsed Schur preparation failed: ',
                                           dict(detail=detail, counts=dict(self.counts),
                                                source_work=dict(self.op.work_counts)))


class SchurCoordinate:
    def __init__(self, model, coordinate, detail):
        start = time.perf_counter()
        self.model, self.coordinate, self.detail = model, coordinate, detail
        self.column = model.op.prepare_gain_column(model.y, model.source, coordinate)
        self.others = self.column.others
        self.p, self.sigma2 = model.op.p, model.sigma2
        self.counts = model.counts
        continuous.count(self.counts, 'schur_coordinate_preparations')
        self.b_minus = model.matched[self.others]/self.sigma2
        self.diagonal = float(self.p+model.source.energy/self.sigma2)
        if len(self.others):
            continuous.count(self.counts, 'schur_block_factorizations')
            continuous.count(self.counts, 'schur_block_identity_rhs_columns', len(self.others))
            continuous.count(self.counts, 'schur_block_matched_rhs_columns')
            self.z, self.inverse, solved = solve_gain(
                model.gram[np.ix_(self.others, self.others)], model.matched[self.others], self.sigma2,
                self.counts, prior_precision=self.p, with_logdet=True)
            self.block, self.cholesky = solved['precision'], solved['cholesky']
            self.logdet = solved['logdet_precision']
            detail['block_solve'] = solved
        else:
            continuous.count(self.counts, 'schur_empty_block_preparations')
            self.z = np.empty(0, complex)
            self.inverse = np.empty((0, 0), complex)
            self.block = np.empty((0, 0), complex)
            self.cholesky = np.empty((0, 0), complex)
            self.logdet = 0.
        self.constant = float(real_result(np.vdot(self.b_minus, self.z), 'Schur constant'))-self.logdet
        _freeze(self.b_minus, self.z, self.inverse, self.block, self.cholesky)
        detail.update(status='completed', others=self.others, base_dopplers=model.dopplers,
                      A=self.block, b_minus=self.b_minus, inverse_A=self.inverse, z=self.z,
                      logdet_A=self.logdet, constant=self.constant, diagonal=self.diagonal,
                      seconds=time.perf_counter()-start)

    def evaluate(self, doppler, *, derivative=False, score_only=False):
        start, cpu = time.perf_counter(), time.process_time()
        before, source_before = dict(self.counts), dict(self.model.op.work_counts)
        result = dict(coordinate=self.coordinate, doppler=doppler, status='started', derivative=None)
        try:
            if type(score_only) is not bool or (score_only and derivative):
                raise ValueError('score-only evaluation requires a boolean flag and no derivative')
            doppler = real_scalar(doppler, 'collapsed candidate Doppler')
            if not -3 <= doppler <= 3:
                raise ValueError('collapsed candidate Doppler outside [-3,3]')
            continuous.count(self.counts, 'schur_candidates_started')
            column = self.column.evaluate(doppler, derivative=derivative)
            result['column'] = column
            i, other = self.coordinate, self.others
            u = column['gram_column'][other]/self.sigma2
            b_i = column['matched']/self.sigma2
            if len(other):
                continuous.count(self.counts, 'schur_candidate_triangular_solve_calls')
                intermediate = scipy.linalg.solve_triangular(self.cholesky, u, lower=True)
                continuous.count(self.counts, 'schur_candidate_triangular_solve_calls')
                v = scipy.linalg.solve_triangular(self.cholesky.conj().T, intermediate, lower=False)
                continuous.count(self.counts, 'schur_candidate_vector_rhs')
            else:
                v = np.empty(0, complex)
            s = float(real_result(self.diagonal-np.vdot(u, v), 'Schur complement'))
            t = complex(b_i-np.vdot(u, self.z))
            result.update(u=u, b_i=b_i, v=v, s=s, t=t)
            if s <= 0 or s < self.p-1e-10*max(1, self.p):
                raise continuous.CoreFailure('Schur complement violates prior lower bound',
                                             dict(s=s, prior_precision=self.p))
            J = float(abs(t)**2/s-np.log(s))
            if score_only:
                continuous.finite([s, t, J, self.constant+J], 'collapsed score-only result')
                continuous.finite(v, 'collapsed score-only block solution')
                continuous.count(self.counts, 'schur_score_only_candidates_completed')
                continuous.count(self.counts, 'schur_candidates_completed')
                result.update(status='completed', score_only=True, J=J, constant=self.constant,
                              reduced_score=self.constant+J, seconds=time.perf_counter()-start,
                              cpu_seconds=time.process_time()-cpu,
                              work_counts={key: value-before.get(key, 0) for key, value in self.counts.items()
                                           if value != before.get(key, 0)},
                              source_work_counts={key: value-source_before.get(key, 0)
                                                  for key, value in self.model.op.work_counts.items()
                                                  if value != source_before.get(key, 0)})
                return result
            mean = np.empty(self.p, complex)
            mean[i], mean[other] = t/s, self.z-v*(t/s)
            covariance = np.empty((self.p, self.p), complex)
            covariance[i, i] = 1/s
            covariance[other, i] = -v/s
            covariance[i, other] = (-v/s).conj()
            covariance[np.ix_(other, other)] = self.inverse+np.outer(v, v.conj())/s
            continuous.count(self.counts, 'schur_full_covariance_restorations')
            continuous.count(self.counts, 'schur_covariance_entries', self.p**2)
            continuous.count(self.counts, 'schur_covariance_outer_product_terms', len(other)**2)
            gram, matched = self.model.gram.copy(), self.model.matched.copy()
            gram[:, i] = column['gram_column']
            gram[i, :] = column['gram_column'].conj()
            matched[i] = column['matched']
            precision = self.p*np.eye(self.p)+gram/self.sigma2
            b = matched/self.sigma2
            solution = np.column_stack((covariance, mean))
            rhs = np.column_stack((np.eye(self.p), b))
            continuous.count(self.counts, 'schur_residual_matrix_products')
            continuous.count(self.counts, 'schur_residual_matmul_terms', self.p**2*(self.p+1))
            residual = float(np.linalg.norm(precision@solution-rhs)/max(1., np.linalg.norm(rhs)))
            continuous.count(self.counts, 'schur_precision_residual_checks')
            hermitian = dict(gram=_hermitian(gram, 'candidate Gram'),
                             precision=_hermitian(precision, 'candidate precision'),
                             covariance=_hermitian(covariance, 'candidate covariance'))
            continuous.finite([J, self.constant+J, residual], 'collapsed score/residual')
            continuous.finite(mean, 'collapsed gain mean')
            if residual > 1e-10:
                raise continuous.CoreFailure('Schur posterior precision residual exceeds tolerance',
                                             dict(residual=residual))
            result.update(gram=gram, matched=matched, precision=precision, b=b, J=J,
                          constant=self.constant, reduced_score=self.constant+J,
                          mean=mean, covariance=covariance,
                          logdet_precision=self.logdet+float(np.log(s)),
                          precision_residual=residual, hermitian_errors=hermitian)
            if derivative:
                continuous.count(self.counts, 'schur_derivatives_started')
                du = column['derivative']['gram_column'][other]/self.sigma2
                db_i = column['derivative']['matched']/self.sigma2
                ds = float(-2*np.vdot(du, v).real)
                dt = complex(db_i-np.vdot(du, self.z))
                dJ = float(2*np.real(t.conjugate()*dt)/s-(abs(t)**2/s**2+1/s)*ds)
                dprecision = np.zeros((self.p, self.p), complex)
                dprecision[:, i] = column['derivative']['gram_column']/self.sigma2
                dprecision[i, :] = (column['derivative']['gram_column']/self.sigma2).conj()
                db = np.zeros(self.p, complex)
                db[i] = db_i
                continuous.count(self.counts, 'schur_derivative_trace_matrix_products')
                continuous.count(self.counts, 'schur_derivative_trace_matmul_terms', self.p**3)
                envelope = float(real_result(2*np.vdot(db, mean).real-
                    np.trace((covariance+np.outer(mean, mean.conj()))@dprecision), 'envelope derivative'))
                continuous.finite([ds, dt, dJ, envelope], 'collapsed derivative')
                result['derivative'] = dict(s=ds, t=dt, J=dJ, envelope=envelope, b=db, precision=dprecision)
                continuous.count(self.counts, 'schur_derivatives_completed')
            continuous.count(self.counts, 'schur_candidates_completed')
            result.update(status='completed', seconds=time.perf_counter()-start,
                          cpu_seconds=time.process_time()-cpu,
                          work_counts={key: value-before.get(key, 0) for key, value in self.counts.items()
                                       if value != before.get(key, 0)},
                          source_work_counts={key: value-source_before.get(key, 0)
                                              for key, value in self.model.op.work_counts.items()
                                              if value != source_before.get(key, 0)})
            return result
        except Exception as error:
            continuous.raise_with_evidence(error, 'collapsed candidate failed: ',
                                           dict(partial=result, preparation=self.detail,
                                                counts=dict(self.counts), source_work=dict(self.model.op.work_counts)))
