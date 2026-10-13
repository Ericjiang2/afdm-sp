"""Admitted engineering tests only; importing this file executes no tests.

Data/operator fixtures reuse the deterministic MATH inputs. Extra quadrature
fixtures are uniform, boundary-centered Gaussian, concentrated Fourier, and
an injected resolution disagreement. None samples communication observations.
"""
import unittest
from unittest.mock import patch

import numpy as np
from scipy.special import logsumexp, ndtr

from experiments.afdm_sp_fractional_20261007.moments import PathMoments
from experiments.afdm_sp_fractional_20261007.verify import (
    DOPPLER_NODES, GAIN_COVARIANCE, GAIN_MEAN, WEIGHTS, fixed_inputs)
from .continuous import (ContinuousIntegrator, CoreFailure, PointOptimizer,
                         point_factor, rectangular_nodes)
from .data_step import DataStepper, data_moments
from .receiver import MomentFactory, doppler_sweep, gain_update, receive


def small_case(single=False):
    n = 8
    op = PathMoments(n, 5.3/(2*n), (np.sqrt(2)-1)/(2*n*n),
                     np.array([0] if single else [0, 3]),
                     np.asarray(DOPPLER_NODES[:1] if single else DOPPLER_NODES),
                     np.tile(WEIGHTS, (1 if single else 2, 1)),
                     np.asarray(GAIN_MEAN[:1] if single else GAIN_MEAN),
                     np.asarray(GAIN_COVARIANCE)[:1, :1] if single else GAIN_COVARIANCE)
    return op, fixed_inputs(n)


class QuadratureContracts(unittest.TestCase):
    def test_uniform_analytic_characteristic_and_cache_accounting(self):
        counts = {}
        integrator = ContinuousIntegrator(8, counts)
        factor = integrator.from_coefficients(np.zeros(8, complex), .7)
        np.testing.assert_allclose(factor.phi, np.sinc(6*np.arange(8)/8), atol=2e-12)
        self.assertAlmostEqual(factor.density['log_normalizer'], 0., places=12)
        self.assertEqual([level['nodes'] for level in factor.diagnostics], [128, 256])
        builds = counts['quadrature_cache_builds']
        integrator.from_coefficients(np.zeros(8, complex), .7)
        self.assertEqual(counts['quadrature_cache_builds'], builds)
        self.assertEqual(counts['quadrature_density_nodes'], 2*(128+256))

    def test_truncated_gaussian_boundary_normalization(self):
        integrator = ContinuousIntegrator(8, {})
        for center in (-3., 0., 3.):
            factor = integrator.initial(center)
            mass = ndtr((3-center)/.125)-ndtr((-3-center)/.125)
            expected = np.log(.125*np.sqrt(2*np.pi)*mass/6)
            self.assertAlmostEqual(factor.density['log_normalizer'], expected, places=8)
            self.assertEqual(factor.density['kind'], 'truncated_gaussian')
            self.assertTrue(factor.density['resolution_agreement'])

    def test_tail_removal_and_duplicate_padding_preserve_moments(self):
        coefficients = np.zeros(8, complex)
        coefficients[1] = 80
        factor = ContinuousIntegrator(8, {}).from_coefficients(coefficients, 1.)
        final = factor.diagnostics[-1]
        self.assertGreater(final['dropped_nodes'], 0)
        self.assertLessEqual(final['dropped_mass_bound'], 1e-14)
        self.assertLessEqual(final['moment_tail_bound'], 2e-14)
        self.assertTrue(np.all(factor.weights > 0))
        point = point_factor(.2, 8, {})
        nodes, weights = rectangular_nodes([factor, point], {})
        actual = np.sum(weights[:, :, None]*np.exp(
            2j*np.pi*nodes[:, :, None]*np.arange(8)/8), axis=1)
        np.testing.assert_allclose(actual, [factor.phi, point.phi], atol=2e-13)

    def test_no_success_when_all_resolutions_disagree(self):
        class Disagreeing(ContinuousIntegrator):
            def level(self, order):
                nodes, weights, phase = super().level(order)
                phase = phase.copy()
                phase[:, 1:] *= np.exp(1j*order/16)
                return nodes, weights, phase

        counts = {}
        with self.assertRaises(CoreFailure) as caught:
            Disagreeing(8, counts).from_coefficients(np.zeros(8, complex), 1.)
        self.assertEqual(counts['quadrature_density_nodes'], 128+256+512+1024)
        self.assertEqual(len(caught.exception.evidence['levels']), 4)

    def test_point_keeps_old_candidate_and_ignores_constant_for_selection(self):
        coefficients = np.zeros(8, complex)
        coefficients[1] = 1
        optimizer = PointOptimizer(8, {})
        point, trace = optimizer.update(coefficients, 1., 0.)
        coefficients[0] = 1e6+2j
        shifted, shifted_trace = optimizer.update(coefficients, 1., 0.)
        self.assertEqual(point.nodes[0], 0.)
        np.testing.assert_array_equal(point.nodes, shifted.nodes)
        np.testing.assert_array_equal(trace['grid_scores'], shifted_trace['grid_scores'])


class DataAndGainContracts(unittest.TestCase):
    def test_actual_objective_and_equation8_for_each_accepted_step(self):
        op, inputs = small_case()
        counts = {}
        stepper = DataStepper(op, inputs['y'], inputs['pilot'], .7,
                              np.log(inputs['probabilities']), counts)
        for _ in range(3):
            log_q, trace = stepper.step()
            accepted = trace['proposals'][-1]
            self.assertTrue(accepted['accepted'])
            self.assertLessEqual(abs(accepted['equation8_residual']), accepted['tolerance'])
            self.assertGreaterEqual(accepted['increment'], -accepted['tolerance'])
            np.testing.assert_allclose(logsumexp(log_q, axis=1), 0., atol=2e-14)
        self.assertEqual(counts['gram_matvec_calls'], 1+counts['data_proposals'])
        self.assertEqual(counts['data_objective_evaluations'], 1+counts['data_proposals'])

    def test_finite_log_state_recovers_numerically_underflowed_mass(self):
        op, inputs = small_case(single=True)
        log_q = np.tile([0., -1000., -1200., -1400.], (8, 1))
        self.assertTrue(np.any(data_moments(log_q)[0] == 0))
        stepper = DataStepper(op, inputs['y'], inputs['pilot'], .7, log_q, {})
        result, trace = stepper.step()
        self.assertEqual(trace['accepted_level'], 0)
        self.assertIsNone(trace['proposals'][0]['forward_kl'])
        self.assertTrue(np.isfinite(result).all())
        self.assertTrue(np.all(data_moments(result)[0] > 0))

    def test_identity_failure_aborts_without_backtracking(self):
        op, inputs = small_case()
        counts = {}
        log_q = np.log(inputs['probabilities'])
        stepper = DataStepper(op, inputs['y'], inputs['pilot'], .7, log_q, counts)
        self.assertGreater(stepper.max_level, 0)
        old_objective, old_gx = stepper.objective, stepper.gx.copy()
        with patch.object(stepper, 'evaluate_objective', return_value=stepper.objective-100.):
            with self.assertRaises(CoreFailure) as caught:
                stepper.step()
        np.testing.assert_array_equal(stepper.log_q, log_q)
        np.testing.assert_array_equal(stepper.gx, old_gx)
        self.assertEqual(stepper.objective, old_objective)
        self.assertEqual(counts['data_proposals'], 1)
        proposals = caught.exception.evidence['trace']['proposals']
        self.assertEqual(len(proposals), 1)
        self.assertFalse(proposals[0]['checks']['identity'])
        self.assertGreater(abs(proposals[0]['equation8_residual']), proposals[0]['tolerance'])

    def test_full_gain_covariance_solves_original_precision(self):
        op, inputs = small_case()
        mean, covariance, trace = gain_update(op, inputs['y'], inputs['pilot'],
                                              np.log(inputs['probabilities']), .7, {})
        precision = op.p*np.eye(op.p)+trace['gram']/.7
        np.testing.assert_allclose(precision@covariance, np.eye(op.p), atol=2e-12)
        np.testing.assert_allclose(precision@mean, trace['matched']/.7, atol=2e-12)
        self.assertGreater(abs(covariance[0, 1]), 1e-8)

    def test_incremental_coefficients_equal_fresh_canonical_recalculation(self):
        op, inputs = small_case()
        counts = {}
        factory = MomentFactory(op.n, op.c1, op.c2, op.delays, counts)
        factors = [point_factor(value, op.n, counts) for value in (.05, .62)]
        op = factory.build(factors, op.mean, op.covariance)
        log_q = np.log(inputs['probabilities'])
        seen = []

        class RecordingPoint:
            def update(self, coefficients, sigma2, previous):
                seen.append(coefficients.copy())
                return point_factor(previous+.1, op.n, counts), {}

        doppler_sweep(op, factors, inputs['y'], inputs['pilot'], log_q, .7,
                      RecordingPoint(), counts, [])
        for i in range(op.p):
            fresh = factory.build(factors, op.mean, op.covariance)
            _, mean, variance = data_moments(log_q)
            source = fresh.prepare_source(inputs['pilot'], mean, variance)
            expected = fresh.coordinate_coefficients(inputs['y'], source)[i]
            np.testing.assert_allclose(seen[i], expected, atol=2e-12)
            factors[i] = point_factor(float(factors[i].nodes[0])+.1, op.n, counts)

    def test_truth_input_is_rejected_before_any_operator_or_decoder(self):
        observation = dict(y=np.ones(8), pilot=np.ones(8), sigma2=1., truth='forbidden')
        with self.assertRaises(ValueError) as caught:
            receive(observation, c1=.1, c2=.01,
                    initial_slots=dict(delays=np.array([0]), dopplers=np.array([0.]),
                                       gains=np.array([1.])), mode='vb_point')
        self.assertEqual(caught.exception.evidence['counts'], dict(decoder_calls=0))

    def test_fatal_errors_keep_type_and_partial_evidence(self):
        for error_type in (TypeError, MemoryError, TimeoutError):
            integrator = ContinuousIntegrator(8, {})
            with patch.object(integrator, 'level', side_effect=error_type('injected')):
                with self.assertRaises(error_type) as caught:
                    integrator.from_coefficients(np.zeros(8, complex), 1.)
            self.assertEqual(len(caught.exception.evidence['levels']), 1)
            op, inputs = small_case(single=True)
            stepper = DataStepper(op, inputs['y'], inputs['pilot'], .7,
                                  np.log(inputs['probabilities']), {})
            with patch.object(stepper, 'gram', side_effect=error_type('injected')):
                with self.assertRaises(error_type) as caught:
                    stepper.step()
            self.assertEqual(caught.exception.evidence['trace']['proposals'][0]['status'], 'started')

    def test_numerical_failure_keeps_paid_level_evidence(self):
        integrator = ContinuousIntegrator(8, {})
        with patch.object(integrator, 'level', side_effect=np.linalg.LinAlgError('injected')):
            with self.assertRaises(CoreFailure) as caught:
                integrator.from_coefficients(np.zeros(8, complex), 1.)
        self.assertEqual(caught.exception.evidence['cause_type'], 'LinAlgError')
        self.assertEqual(len(caught.exception.evidence['levels']), 1)


if __name__ == '__main__':
    unittest.main()
