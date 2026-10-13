"""Tiny fixed-array contracts only; no AFDM physical probe, QPSK grid, or RNG."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from . import protocol
from .kernels import (EvaluationCounter, add_proper_gaussian_noise, complex_complement,
                      efficient_derivative, inverse_sqrt_jets, ncx2_power_excess,
                      real_center_residual)


def fixture_callback(output):
    raise AssertionError('uncommitted source must never enter calculation')


class Contracts(unittest.TestCase):
    def test_budget_rejects_before_consumption(self):
        counter = EvaluationCounter(2)
        counter.add('fixture', 2)
        with self.assertRaises(ValueError):
            counter.add('excess')
        self.assertEqual(counter.report()['total'], 2)

    def test_center_is_real_not_complex(self):
        residual, coefficient = real_center_residual(np.array([1j]), np.array([1.]))
        np.testing.assert_array_equal(residual, [1j])
        self.assertEqual(coefficient, 0.)
        residual, coefficient = real_center_residual(np.array([2j]), np.array([0.]))
        np.testing.assert_array_equal(residual, [2j])

    def test_real_jacobian_matches_known_orthogonal_residual(self):
        columns = np.eye(3, dtype=complex)[:, :2]
        slopes = np.zeros((3, 2), complex)
        slopes[2] = [1., 1j]
        counter = EvaluationCounter(2)
        result = efficient_derivative(columns, slopes, np.ones(2), 1e-12, counter)
        self.assertAlmostEqual(result['J'], 2.)
        self.assertAlmostEqual(result['direct_J'], 2.)
        self.assertAlmostEqual(result['identity_error'], 0.)
        with self.assertRaises(ValueError):
            complex_complement(np.ones((3, 2)), 1e-12)

    def test_normalizer_derivatives(self):
        np.testing.assert_allclose(inverse_sqrt_jets([4., 1., 0., 0.]),
                                   [.5, -1/16, 3/128, -15/1024], rtol=0, atol=1e-15)
        with self.assertRaises(ValueError):
            inverse_sqrt_jets([0., 1., 0., 0.])

    def test_gaussian_wick_diagonal_keeps_both_pairings(self):
        fourth, covariance = add_proper_gaussian_noise(np.zeros((2, 2, 2, 2)), np.zeros((2, 2)), .5)
        self.assertEqual(fourth[0, 0, 0, 0], .5)
        self.assertEqual(fourth[0, 0, 1, 1], .25)
        self.assertEqual(fourth[0, 1, 0, 1], 0.)
        np.testing.assert_array_equal(covariance, .5*np.eye(2))
        with self.assertRaises(ValueError):
            add_proper_gaussian_noise(fourth, covariance, -1.)

    def test_bounded_power_null_and_rejection(self):
        counter = EvaluationCounter(3)
        result = ncx2_power_excess(np.array([0., 1e-8, 1.]), .05, 1e-6, counter)
        self.assertEqual(result[0], 0.)
        self.assertTrue(0 < result[1] < result[2] < .95)
        self.assertEqual(counter.report()['total'], 3)
        with self.assertRaises(ValueError):
            ncx2_power_excess(np.array([-1.]), .05, 1e-6, EvaluationCounter(1))

    def test_private_adapter_does_not_retarget_old_package(self):
        self.assertEqual(protocol.adapter().PACKAGE, protocol.PACKAGE)
        self.assertNotEqual(protocol.frozen.PACKAGE, protocol.PACKAGE)

    def test_uncommitted_source_rejected_before_callback(self):
        with tempfile.TemporaryDirectory(dir=protocol.PACKAGE) as source_dir, tempfile.TemporaryDirectory() as root_dir:
            source = Path(source_dir)/'fixture.py'
            source.write_text('fixture = True\n')
            root = Path(root_dir)
            (root/'control').mkdir()
            (root/'control/run_contract.json').write_text(json.dumps(dict(
                max_new_development_observations=0, max_geometry_probes=10,
                max_wall_seconds=10, max_total_reserved_wall_seconds=20,
                output_limit_bytes=10000000, max_process_memory_bytes=2147483648)))
            with self.assertRaisesRegex(ValueError, 'uncommitted study source'):
                protocol.run('rejected', dict(seed=[1], new_observations=0, new_geometry_probes=0),
                             [source], fixture_callback, artifact_root=root, wall_seconds=5)
            self.assertFalse((root/'execution').exists())


if __name__ == '__main__':
    unittest.main()
