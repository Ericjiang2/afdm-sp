"""Independent CP references and joint-block statistical contracts."""
import unittest
import numpy as np
from scipy.stats import binomtest
from afdm_sp_joint_unrolled.supplement_statistics import (
    cp_bounds, paired_delta, linear_contrast, decisions, paired_power,
    joint_states, joint_power, sufficient_n, search_power,
)


class SupplementStatisticsTests(unittest.TestCase):
    def test_cp_independent_scipy_and_endpoints(self):
        for n in (1, 10, 127):
            for x in (0, n//2, n):
                lo, hi = cp_bounds(x, n, .001)
                ref = binomtest(x, n).proportion_ci(confidence_level=.998, method='exact')
                np.testing.assert_allclose([lo, hi], [ref.low, ref.high], atol=2e-12)
        lo, hi = cp_bounds(0, 100, .001)
        self.assertEqual(lo, 0)
        self.assertAlmostEqual(float(hi), 1-.001**.01)
        lo, hi = cp_bounds(100, 100, .001)
        self.assertEqual(hi, 1)
        self.assertAlmostEqual(float(lo), .001**.01)

    def test_paired_swap_and_multiplicity(self):
        a = paired_delta(30, 10, 100)
        b = paired_delta(10, 30, 100)
        self.assertAlmostEqual(float(a['delta']), .2)
        self.assertAlmostEqual(float(a['lower']), -float(b['upper']))
        wide = paired_delta(30, 10, 100, m=20)
        self.assertLess(wide['lower'], a['lower'])
        self.assertGreater(wide['upper'], a['upper'])
        self.assertEqual(a['tail'], (.05/7)/4)

    def test_invalid_counts(self):
        for args in [(2, 2, 3), (-1, 0, 3), (1., 0, 3), (True, 0, 3), (0, 0, 0), (0, 0, 3.0)]:
            with self.assertRaises(ValueError):
                paired_delta(*args)
        for tail in (0, 1, np.nan):
            with self.assertRaises(ValueError):
                cp_bounds(0, 10, tail)
        with self.assertRaises(ValueError):
            linear_contrast([1, 2], [1, -1, 1], 10)

    def test_linear_independent_signed_reference(self):
        counts, coeff = [10, 20, 30, 40], [1, -1, -1, 1]
        b = linear_contrast(counts, coeff, 100, alpha_family=.04, m=2)
        intervals = [binomtest(x, 100).proportion_ci(confidence_level=1-2*.04/16) for x in counts]
        low = sum(c*(r.low if c > 0 else r.high) for c, r in zip(coeff, intervals))
        high = sum(c*(r.high if c > 0 else r.low) for c, r in zip(coeff, intervals))
        np.testing.assert_allclose([b['lower'], b['upper']], [low, high], atol=1e-12)

    def test_strict_decision_boundaries(self):
        self.assertFalse(decisions(.02, .03)['BENEFIT'])
        self.assertFalse(decisions(-.02, -.01)['HARM'])
        self.assertFalse(decisions(-.01, .01)['EQUIVALENT'])
        self.assertFalse(decisions(-.01, .005)['NONHARM'])
        self.assertFalse(decisions(0, .02)['EXCLUDE_PRACTICAL_BENEFIT'])
        self.assertTrue(decisions(-.009, .009)['EQUIVALENT'])

    def test_joint_truth_and_dependence(self):
        # All arms always fail together: any zero-sum contrast is exactly zero.
        p = np.zeros(16); p[0] = .8; p[-1] = .2
        r = joint_power(200, p, [1, -1, -1, 1], repetitions=100, quick=True)
        self.assertEqual(r['truth'], 0)
        self.assertEqual(r['results']['coverage']['estimate'], 1)
        # A point mass has deterministic effect; truth is derived, not supplied.
        p = np.zeros(256); p[128] = 1
        r = joint_power(200, p, [1, -1, -1, 1, 1, -1, -1, 1], repetitions=100, quick=True)
        self.assertEqual(r['truth'], 1)
        np.testing.assert_array_equal(joint_states(4)[1], [0, 0, 0, 1])
        for p in (np.ones(16), np.full(16, np.nan), [-1]+[2]+[0]*14):
            with self.assertRaises(ValueError):
                joint_power(100, p, [1, -1, -1, 1])

    def test_power_requires_real_repetitions_and_compatible_truth(self):
        with self.assertRaises(ValueError):
            paired_power(100, .01, .05)
        with self.assertRaises(ValueError):
            paired_power(100, .1, .05, repetitions=9999)
        r = paired_power(100, 0, 0, repetitions=100, quick=True)
        self.assertEqual(r['results']['coverage']['count'], 100)
        self.assertLess(r['results']['coverage']['mc_ci95'][0], 1)

    def test_cp_hoeffding_width_and_strict_n(self):
        for n in (1, 11, 101, 1001):
            x = np.arange(n+1)
            lo, hi = cp_bounds(x, n, .0001)
            width = np.sqrt(np.log(1/.0001)/(2*n))
            self.assertLessEqual(float(np.max(hi-x/n)), width+1e-12)
            self.assertLessEqual(float(np.max(x/n-lo)), width+1e-12)
        r = sufficient_n([1, -1, -1, 1], .03, m=10)
        self.assertGreater(r['n'], 16384)
        self.assertLess(r['width_plus_error'], .03)
        previous = r['width_plus_error']*np.sqrt(r['n']/(r['n']-1))
        self.assertGreaterEqual(previous, .03)

    def test_search_does_not_stop_at_4096_and_rejects_wrong_n(self):
        def fixture(n):
            return {'n': n, 'engineering_only': False, 'repetitions': 10000,
                    'results': {'BENEFIT': {'mc_ci95': [.91 if n >= 8192 else .5, 1]}}}
        r = search_power(fixture, 'BENEFIT')
        self.assertEqual(r['n'], 8192)
        self.assertEqual(search_power(fixture, 'BENEFIT', max_n=4096)['status'], 'UNRESOLVED')
        with self.assertRaises(ValueError):
            search_power(lambda n: fixture(n+1), 'BENEFIT')


if __name__ == '__main__':
    unittest.main()
