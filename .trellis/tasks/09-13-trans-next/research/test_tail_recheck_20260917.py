"""Numerical convention/invalid-input tests; never substitute for raw audit."""
import unittest
import numpy as np
from tail_recheck_20260917 import margins


class MarginTests(unittest.TestCase):
    def test_correct_sign(self):
        r = margins(np.array([2., -3.]), np.array([0, 1]))
        self.assertEqual(r['wrong_sign_bits'], 0)
        self.assertIsNone(r['mean_wrong_abs_llr'])
        self.assertAlmostEqual(r['bit_NLL'], (np.log1p(np.exp(-2))+np.log1p(np.exp(-3)))/2)

    def test_wrong_sign(self):
        r = margins(np.array([-2., 3.]), np.array([0, 1]))
        self.assertEqual(r['wrong_positions'], [0, 1])
        self.assertEqual(r['mean_wrong_abs_llr'], 2.5)

    def test_zero_margin_separate(self):
        r = margins(np.zeros(2), np.array([0, 1]))
        self.assertEqual(r['zero_margin_bits'], 2)
        self.assertEqual(r['wrong_sign_bits'], 0)
        self.assertAlmostEqual(r['bit_NLL'], np.log(2))

    def test_invalid(self):
        for x, y in [(np.array([1.]),np.array([0,1])),
                     (np.array([float('nan')]),np.array([0])),
                     (np.array([1.]),np.array([2]))]:
            with self.subTest(x=x,y=y), self.assertRaises(ValueError):
                margins(x,y)


if __name__ == '__main__':
    unittest.main()
