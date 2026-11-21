"""Pure aggregator contracts; no receiver, SBL or saved-outcome reads."""
import unittest
import numpy as np
import aggregate_uniform_gamma as a


def constant(point, n=200):
    return np.tile(np.asarray(point, float), (n, 1))


class AdequacyTest(unittest.TestCase):
    def test_pass_at_or_above_threshold(self):
        point = (0., 1., .05)  # F,D,U -> T=.1-.05=.05, retention .95
        result = a.adequacy(point, constant(point))
        self.assertEqual(result['verdict'], 'PASS')
        self.assertAlmostEqual(result['retention_ratio']['point'], .95)
        self.assertAlmostEqual(result['T']['point'], .05)
        self.assertTrue(result['retention_ratio']['evaluable'])

    def test_fail_below_threshold(self):
        point = (0., 1., .95)
        result = a.adequacy(point, constant(point))
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertAlmostEqual(result['retention_ratio']['point'], .05)

    def test_inconclusive_when_interval_straddles(self):
        point = (0., 1., .10)
        draws = constant(point)
        draws[::2, 2] = .05
        draws[1::2, 2] = .15
        result = a.adequacy(point, draws)
        self.assertEqual(result['verdict'], 'INCONCLUSIVE')
        self.assertLess(result['T']['ci95'][0], 0)
        self.assertGreater(result['T']['ci95'][1], 0)

    def test_unevaluable_when_baseline_gap_nonpositive(self):
        point = (0., 0., -.01)
        result = a.adequacy(point, constant(point))
        self.assertEqual(result['verdict'], 'UNEVALUABLE')
        self.assertFalse(result['retention_ratio']['evaluable'])
        self.assertIsNone(result['retention_ratio']['point'])

    def test_projection_diagnostic_fail_closed(self):
        good = dict(original_min_eigenvalue=0., uniform_min_eigenvalue=0., identity_absolute=0.,
                    identity_scale=1., identity_relative=0., gamma_projected_variance_calls=2,
                    actual_gamma_fft_count=2)
        a.g.validate_projection([good] * 20)
        bad = dict(good, identity_relative=1e-9)
        with self.assertRaises(ValueError):
            a.g.validate_projection([bad] * 20)
        with self.assertRaises(ValueError):
            a.g.validate_projection([good] * 19)


if __name__ == '__main__':
    unittest.main()
