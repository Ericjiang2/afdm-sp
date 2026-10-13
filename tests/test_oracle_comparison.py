"""Contracts for the frozen small-model approximation comparison."""
import sys
from pathlib import Path
import unittest
import numpy as np
from numpy.testing import assert_allclose

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.afdm_inference_causal_20261002.oracle_comparison import (
    posterior_metrics, compare_case, make_case, CONFIG, load_frozen,
)


class ComparisonTests(unittest.TestCase):
    def test_identical_marginals_zero_excess_brier(self):
        physical, messages, twofft = load_frozen()
        case = make_case(2, 'separated', .6, .8, 0, physical)
        output = compare_case(case, 'pilot_ridge', physical, messages, twofft)
        self.assertEqual(set(output['metrics']),
                         {'scalar_joint', 'scalar_point', 'plugin_joint_gain', 'oracle_product'})
        m = output['metrics']['oracle_product']
        self.assertEqual(m['probability_mse'], 0)
        self.assertEqual(m['llr_rmse'], 0)
        self.assertAlmostEqual(m['h_d_cov_error'], output['exact']['h_d_cov_norm'])
        for method in output['metrics'].values():
            self.assertGreaterEqual(method['probability_mse'], 0)
            self.assertAlmostEqual(method['expected_brier'] - output['exact']['expected_brier'],
                                   method['probability_mse'], places=13)

    def test_grouped_mapping_matches_frozen_messages(self):
        physical, messages, _ = load_frozen()
        case = make_case(3, 'near_duplicate', .6, .15, 1, physical)
        labels = case['bits']
        llr = np.array([.2, -.4, .6, -.8, 1., -1.2])
        logprior = .5*(1-2*labels) @ llr
        weights = np.exp(logprior-logprior.max()); weights /= weights.sum()
        assert_allclose(weights @ case['words'], messages.moments(llr, .5)[0], atol=1e-14)

    def test_grid_is_bounded_and_not_adaptive(self):
        self.assertEqual(CONFIG['iterations'], 20)
        self.assertEqual(CONFIG['case_count'], 48)
        self.assertEqual(CONFIG['cpu_budget_seconds'], 60)
        self.assertEqual(CONFIG['seeds'], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
