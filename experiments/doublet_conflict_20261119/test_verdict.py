"""Synthetic outcome pairs exercise the DRAFT decision and interval rules."""

import unittest

import numpy as np
from scipy.stats import binom

import doublet_verdict as verdict


class VerdictTest(unittest.TestCase):
    def setUp(self):
        self.frames = np.arange(verdict.N_FRAMES)

    def evaluate(self, u_only=0, cd_only=0, both=0):
        u = np.zeros(verdict.N_FRAMES, dtype=bool)
        cd = u.copy()
        u[:u_only] = True
        cd[u_only:u_only + cd_only] = True
        start_both = u_only + cd_only
        u[start_both:start_both + both] = True
        cd[start_both:start_both + both] = True
        return verdict.evaluate(u, cd, self.frames)

    def test_rare_identical_outcomes_and_zero_count_bound(self):
        result = self.evaluate(both=50)
        upper = 1 - .05 ** (1 / 600)
        self.assertEqual((result['delta'], result['discordant']), (0, 0))
        self.assertAlmostEqual(result['ci_hi'], upper, places=15)
        self.assertAlmostEqual(result['ci_lo'], -upper, places=15)
        self.assertEqual(result['verdict'], 'compatible')
        self.assertFalse(result['small_detectable_harm'])

    def test_rare_asymmetric_bounds_at_four_discordances(self):
        result = self.evaluate(u_only=3, cd_only=1)
        self.assertIn('Clopper', result['method'])
        self.assertEqual(result['delta'], 2 / 600)
        self.assertEqual((result['u_only_failures'], result['cd_only_failures']), (3, 1))
        self.assertAlmostEqual(binom.cdf(3, 600, result['ci_hi']), .05)
        self.assertAlmostEqual(binom.cdf(1, 600, -result['ci_lo']), .05)
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertFalse(result['small_detectable_harm'])

    def test_bootstrap_switch_at_five_and_both_directions(self):
        harm = self.evaluate(u_only=5)
        help_ = self.evaluate(cd_only=5)
        self.assertIn('bootstrap', harm['method'])
        self.assertEqual((harm['delta'], harm['verdict']), (5 / 600, 'conflict'))
        self.assertEqual((help_['delta'], help_['verdict']), (-5 / 600, 'compatible'))
        self.assertAlmostEqual(harm['ci_lo'], -help_['ci_hi'])
        self.assertAlmostEqual(harm['ci_hi'], -help_['ci_lo'])

    def test_bootstrap_paired_common_failures_cancel(self):
        baseline = self.evaluate(u_only=6, cd_only=6)
        self.assertEqual(baseline['verdict'], 'uncertain')
        self.assertEqual(baseline, self.evaluate(u_only=6, cd_only=6, both=200))

    def test_margin_priority_and_critical_equalities(self):
        self.assertEqual(verdict._classify(.001, .01), ('compatible', True))
        self.assertEqual(verdict._classify(0, .01), ('compatible', False))
        self.assertEqual(verdict._classify(0, .011), ('uncertain', False))
        self.assertEqual(verdict._classify(.001, .011), ('conflict', False))

    def test_reject_duplicate_frames_and_nonbinary_outcomes(self):
        u = np.zeros(verdict.N_FRAMES, dtype=int)
        cd = u.copy()
        frames = self.frames.copy()
        frames[-1] = frames[0]
        with self.assertRaisesRegex(ValueError, 'unique integer frame IDs'):
            verdict.evaluate(u, cd, frames)
        u[0] = 2
        with self.assertRaisesRegex(ValueError, 'one binary outcome per frame'):
            verdict.evaluate(u, cd, self.frames)


if __name__ == '__main__':
    unittest.main()
