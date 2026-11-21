"""Synthetic contracts for the paired cluster reducer; no receiver evidence."""
import unittest

import numpy as np

from sampling import bootstrap_means, linear_summary, ratio_summary


class SamplingTests(unittest.TestCase):
    def test_same_frame_strata_are_resampled_jointly(self):
        # Each frame has two scenarios and two SNRs. Within-frame signed
        # contributions cancel; any split of the strata would break this law.
        ids, values = [], []
        for frame in range(5):
            for scenario in ('U', 'G'):
                for snr in (600, 1100):
                    ids.append(f'entropy/domain/{frame}')
                    values.append((frame+1) * (1 if snr == 600 else -1))
        draws, n = bootstrap_means({'signed': values}, ids, n_boot=1000, seed=20261018)
        self.assertEqual(n, 5)
        np.testing.assert_array_equal(draws['signed'], np.zeros(1000))

    def test_variable_size_clusters_retain_pooled_row_estimand(self):
        # Two clusters: one row worth 10, three rows worth 0. Drawing two
        # clusters yields only 10, 2.5, or 0, not cluster-mean average 5.
        draws, n = bootstrap_means({'x': [10, 0, 0, 0]}, ['a', 'b', 'b', 'b'],
                                   n_boot=20000, seed=20261018)
        self.assertEqual(n, 2)
        self.assertEqual(set(draws['x']), {0., 2.5, 10.})
        for value, probability in ((0., .25), (2.5, .5), (10., .25)):
            self.assertLess(abs(np.mean(draws['x'] == value)-probability), .015)

    def test_arms_share_draws_and_paired_constant_difference(self):
        a = np.array([0., 2., 7., 9., -2.])
        values = dict(a=a, b=a+3)
        draws, _ = bootstrap_means(values, ['a', 'b', 'b', 'c', 'c'],
                                   n_boot=1000, seed=20261018)
        point = {k: float(v.mean()) for k, v in values.items()}
        result = linear_summary(point, draws, {'b': 1, 'a': -1})
        self.assertAlmostEqual(result['point'], 3.)
        self.assertAlmostEqual(result['ci_lo'], 3.)
        self.assertAlmostEqual(result['ci_hi'], 3.)
        np.testing.assert_allclose(draws['b']-draws['a'], 3., atol=2e-15)

    def test_ratio_invalid_draw_fraction_blocks_evaluation(self):
        result = ratio_summary({'n': 1., 'd': .1},
                               {'n': np.ones(100), 'd': np.r_[np.ones(98), 0., -1.]},
                               {'n': 1}, {'d': 1})
        self.assertEqual(result['point'], 10.)
        self.assertEqual(result['denominator_nonpositive_fraction'], .02)
        self.assertFalse(result['evaluable'])
        # The conditional interval is labelled and retained, not silently
        # substituted for an evaluable ratio.
        self.assertEqual(result['ci_lo'], 1.)
        self.assertEqual(result['ci_condition'], 'bootstrap denominator > 0')
        result = ratio_summary({'n': 0., 'd': 0.},
                               {'n': np.zeros(100), 'd': np.zeros(100)}, {'n': 1}, {'d': 1})
        self.assertFalse(result['evaluable'])
        self.assertIsNone(result['point'])
        self.assertIsNone(result['ci_lo'])
        self.assertEqual(result['denominator_nonpositive_fraction'], 1.)

    def test_ratio_one_percent_boundary_and_bad_point_denominator(self):
        draws = {'n': np.ones(100), 'd': np.r_[np.ones(99), 0.]}
        result = ratio_summary({'n': 1., 'd': 1.}, draws, {'n': 1}, {'d': 1})
        self.assertTrue(result['evaluable'])
        result = ratio_summary({'n': 1., 'd': -1.}, draws, {'n': 1}, {'d': 1})
        self.assertFalse(result['evaluable'])
        self.assertIsNone(result['point'])

    def test_reject_invalid_shape_empty_or_nonfinite(self):
        cases = [({}, ['a']), ({'x': []}, []), ({'x': [1]}, ['a', 'b']),
                 ({'x': [[1], [2]]}, ['a', 'b']), ({'x': [np.nan]}, ['a']),
                 ({'x': [np.inf]}, ['a']), ({'x': [1]}, [['domain', 1]])]
        for values, ids in cases:
            with self.subTest(values=values, ids=ids), self.assertRaises(ValueError):
                bootstrap_means(values, ids, n_boot=10)

    def test_reproducible_draws_ignore_row_order_and_batch_size(self):
        values = np.array([1., 2., 3., 4., 5.])
        ids = np.array(['c', 'a', 'a', 'b', 'b'])
        first, _ = bootstrap_means({'x': values}, ids, n_boot=117, seed=20261018, batch_size=1)
        second, _ = bootstrap_means({'x': values[::-1]}, ids[::-1], n_boot=117,
                                    seed=20261018, batch_size=37)
        np.testing.assert_array_equal(first['x'], second['x'])


if __name__ == '__main__':
    unittest.main()
