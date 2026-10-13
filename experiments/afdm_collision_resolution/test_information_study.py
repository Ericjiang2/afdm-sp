"""Small deterministic information/projection contracts, not research runs."""
import inspect
import json
import unittest

import numpy as np

from experiments.afdm_collision_resolution.collision_teacher import CollisionTeacher, exact_moment_system
from experiments.afdm_collision_resolution.information_study import (
    CONFIG_PATH, batch_summary, fitted_information, moment_projection, nuisance_fd,
)


class InformationTests(unittest.TestCase):
    def test_information_preserves_independent_coefficient(self):
        x = np.arange(32, dtype=float)
        scores = np.column_stack((np.sin(x)+2*np.cos(x), np.cos(x), x/32, (-1.)**x))
        fit = fitted_information(scores[:16])
        heldout = fitted_information(scores[16:], fit['coefficient'])
        np.testing.assert_array_equal(heldout['coefficient'], fit['coefficient'])
        expected = scores[16:, 0]-scores[16:, 1:]@fit['coefficient']
        np.testing.assert_allclose(heldout['effective']['mean'], np.mean(expected**2))
        self.assertEqual(heldout['effective']['batches'], 8)

    def test_moment_projection_absorbed_target(self):
        system = dict(covariance=np.eye(4), derivatives=np.array([[2, 1, 0, 0], [0, 0, 1, 0],
                                                               [0, 0, 0, 1], [0, 0, 0, 0]], float))
        result = moment_projection(system, 4)
        self.assertEqual(result['effective'], 0.)
        np.testing.assert_array_equal(result['witness'], np.zeros(4))

    def test_moment_witness_nuisance_orthogonality(self):
        # A known nonsingular fixture independently determines the answer.
        derivatives = np.column_stack((np.ones(4), np.eye(4)[:, :3]))
        result = moment_projection(dict(covariance=np.eye(4), derivatives=derivatives), 4)
        self.assertEqual(result['effective'], 1.)
        np.testing.assert_array_equal(result['witness'], [0, 0, 0, 1])
        np.testing.assert_allclose(result['witness_nuisance'], 0, atol=1e-14)

    def test_actual_polynomial_identity_qualification(self):
        # A single deterministic basepoint calculation; no observations generated.
        system = exact_moment_system(CollisionTeacher(.35, sigma2=1.))
        for count in (4, 14):
            result = moment_projection(system, count)
            self.assertEqual(result['covariance_rank'], count)
            self.assertLess(np.max(abs(result['witness_nuisance'])), 2e-10)
            self.assertAlmostEqual(result['witness_target'], result['witness_variance'], delta=2e-10)

    def test_registered_allocation_and_observation_interface(self):
        config = json.loads(CONFIG_PATH.read_text())
        self.assertEqual(config['new_observations'], 4*2048)
        self.assertEqual(config['train_size']+config['heldout_size'], 2048)
        self.assertEqual(config['wall_seconds'], 600)
        self.assertEqual(list(inspect.signature(CollisionTeacher.evaluate).parameters), ['self', 'y', 'batch'])

    def test_reject_incomplete_batch_and_indefinite_moments(self):
        with self.assertRaises(ValueError):
            batch_summary(np.zeros(17))
        with self.assertRaises(ValueError):
            moment_projection(dict(covariance=np.diag([-1., 1]), derivatives=np.ones((2, 4))), 2)


if __name__ == '__main__':
    unittest.main()
