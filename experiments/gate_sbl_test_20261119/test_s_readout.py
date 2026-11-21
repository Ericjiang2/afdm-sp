import unittest

import numpy as np

from s_arm import S_PROJECTOR_EQUAL_ATOL, block_census, receiver, retained_penalty_fro


class RetainedPenaltyTest(unittest.TestCase):
    def test_uses_full_post_pruning_support_and_both_axes(self):
        sbl = receiver().spectral.sbl
        contrast = np.array([1., 0., -1j, 0.]) / np.sqrt(2.)
        low_penalty = 2 * np.outer(contrast, contrast.conj())
        gate_penalty = low_penalty.conj()
        gate_penalty[3, 3] += 2.
        result = sbl.sbl_em(np.eye(4), [10., 0., 8., 0.], beta0=2.,
                            Gamma=low_penalty, max_iter=2, prune=.1)
        np.testing.assert_array_equal(result['idx'], [0, 2])
        output, _, _ = sbl.select_output(result['idx'], result['mu'], max_atoms=1)
        np.testing.assert_array_equal(output, [0])

        self.assertAlmostEqual(retained_penalty_fro(gate_penalty, low_penalty, result['idx']), np.sqrt(8))
        self.assertEqual(retained_penalty_fro(gate_penalty, low_penalty, output), 0.)
        pruned_difference = low_penalty + np.diag([0., 1., 0., 1.])
        self.assertEqual(retained_penalty_fro(pruned_difference, low_penalty, result['idx']), 0.)

    def test_validity_tolerance_applies_to_projector_distance(self):
        low = np.diag([1., 0.])
        for angle, equivalent in [(2e-9, True), (2e-8, False)]:
            mode = np.array([np.cos(angle), np.sin(angle)])
            projector = np.outer(mode, mode)
            with self.subTest(angle=angle):
                legacy = block_census(projector, 1, low, 1)
                current = block_census(projector, 1, low, 1, equality_atol=S_PROJECTOR_EQUAL_ATOL)
                self.assertFalse(legacy['projectors_equal'])
                self.assertIs(current['projectors_equal'], equivalent)
                self.assertEqual(current['gate_in_s_lo'], legacy['gate_in_s_lo'])


if __name__ == '__main__':
    unittest.main()
