"""Tiny fixed-array contracts only; no physical geometry, RNG or study grid."""
import inspect
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from . import kernels, protocol
from .config import load_config

NUMERICS = dict(weak_I4_relative=1e-12, root_xtol=1e-12, reconstruction_rtol=1e-9)


def forbidden_callback(output):
    raise AssertionError('source rejection must precede scientific calculation')


class Contracts(unittest.TestCase):
    def test_budget_before_evaluation(self):
        counter = kernels.EvaluationCounter(1)
        counter.add('fixture')
        with self.assertRaises(ValueError):
            counter.add('excess')
        self.assertEqual(counter.report()['total'], 1)

    def test_input_interface_and_zero_moment_rejection(self):
        parameters = inspect.signature(kernels.infer_power).parameters
        self.assertFalse({'truth', 'sigma', 'tau', 'gain', 'H'} & set(parameters))
        result = kernels.algebraic_inverse(np.zeros(3), 9, [.26, .36], NUMERICS, scale=1.)
        self.assertEqual(result['status'], 'weak_I4')
        self.assertIsNone(result['nu'])
        with self.assertRaises(ValueError):
            kernels.power_moments(np.ones(8))
        ratio = kernels.algebraic_inverse(np.ones(3), 9, [.26, .36], NUMERICS, scale=1.)
        self.assertEqual(ratio['status'], 'invalid_ratio')
        self.assertIsNone(ratio['nu'])

    def test_frozen_config_rejects_mutated_bytes(self):
        self.assertEqual(load_config()['new_observations'], 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'modified.json'
            path.write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'frozen SHA-256'):
                load_config(path)

    def test_dc_does_not_enter_nonzero_power_moments(self):
        power = np.array([1., 2., 1., 3., 2., 1., 4., 2., 3.])
        base = kernels.power_moments(power)
        shifted = kernels.power_moments(power+7.)
        np.testing.assert_allclose(base['I'], shifted['I'], atol=2e-15, rtol=0)
        # Nine floating trigonometric terms need a summation roundoff allowance.
        np.testing.assert_allclose(kernels.moment_matrix(9)@np.ones(9), 0.,
                                   atol=9*np.finfo(float).eps, rtol=0)

    def test_exact_diagonal_power_covariance_contraction(self):
        power = np.ones(9)
        matrix = kernels.moment_matrix(9)
        actual = kernels.oracle_moment_covariance(power, .5)
        dense = 2.25*np.eye(9)-np.ones((9, 9))/9
        np.testing.assert_allclose(actual, matrix@dense@matrix.T, atol=1e-16, rtol=0)
        np.testing.assert_allclose(actual, .125*np.eye(3), atol=1e-16, rtol=0)
        with self.assertRaises(ValueError):
            kernels.oracle_moment_covariance(power, -1.)

    def test_phase_gradient_on_one_fixed_two_coordinate_vector(self):
        y = np.array([[1.+.2j, -.3+.7j]])
        theta, amplitude = np.array([.2, -.1]), np.array([.8, 1.2])
        result = kernels.quartic_samples(y, theta, amplitude)
        step = 1e-5
        differences = []
        for coordinate in range(2):
            direction = np.eye(2)[coordinate]*step
            plus = kernels.quartic_samples(y, theta+direction, amplitude, gradient=False)['score'][0]
            minus = kernels.quartic_samples(y, theta-direction, amplitude, gradient=False)['score'][0]
            differences.append((plus-minus)/(2*step))
        np.testing.assert_allclose(result['gradient'][0], differences, atol=2e-9, rtol=0)
        self.assertAlmostEqual(float(result['gradient'].sum()), 0., places=13)

    def test_private_adapter_and_uncommitted_source_rejection(self):
        self.assertEqual(protocol.adapter().PACKAGE, protocol.PACKAGE)
        self.assertNotEqual(protocol.frozen.PACKAGE, protocol.PACKAGE)
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
                             [source], forbidden_callback, artifact_root=root, wall_seconds=5)
            self.assertFalse((root/'execution').exists())


if __name__ == '__main__':
    unittest.main()
