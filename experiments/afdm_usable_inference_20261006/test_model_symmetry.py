"""Two tiny fixed contracts; not the registered scientific symmetry matrix."""
import unittest

import numpy as np

from .kernels import EvaluationCounter
from . import model_symmetry
from .model_symmetry import complete_columns, power_design


class TinyFiniteSum:
    N_total = 3

    @staticmethod
    def dirichlet_alpha(m, nu, n):
        return np.mean(np.exp(2j*np.pi*(m+nu)*np.arange(n)/n))


class SymmetryContracts(unittest.TestCase):
    def test_complete_synthesis_has_reversed_index(self):
        counter = EvaluationCounter(4)
        columns, expected, _ = complete_columns(TinyFiniteSum(), [.25], counter)
        np.testing.assert_allclose(columns, expected, atol=2e-15, rtol=0)
        self.assertEqual(counter.report()['total'], 4)
        self.assertGreater(abs(columns[1, 0]-np.exp(2j*np.pi*.25/3)), .1)

    def test_full_channel_amplitudes_and_noise_share_the_constant_column(self):
        columns = np.exp(2j*np.pi*np.outer(np.arange(5), [.25, .5])/5)
        design = power_design(columns)
        # exp, complex modulus, squaring and subtraction each round; this is
        # a fixed-array numerical contract, not a scientific-stage tolerance.
        roundoff = 8*np.finfo(float).eps
        np.testing.assert_allclose(design[:, 0], design[:, 1], atol=roundoff, rtol=0)
        np.testing.assert_allclose(design[:, 0], design[:, 4], atol=roundoff, rtol=0)
        self.assertEqual(np.linalg.matrix_rank(design), 3)

    def test_each_path_must_keep_all_five_rows(self):
        weights = np.ones((5, 2), complex)
        weights[0, 0] = 0
        geometry = dict(weights=weights, physical_clip_mask=np.zeros(2, bool))
        with self.assertRaisesRegex(ValueError, 'every path'):
            model_symmetry.require_five_rows(geometry)


if __name__ == '__main__':
    unittest.main()
