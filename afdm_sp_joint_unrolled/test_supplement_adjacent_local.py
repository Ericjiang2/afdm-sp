"""Local arithmetic contracts on synthetic states, not development samples."""
import unittest
import numpy as np
import torch

from supplement_adjacent_local import bounded_update, reference_update


def state(H, y, prior=None):
    n = len(y)
    return dict(H=np.asarray(H, dtype=np.complex128), y=np.asarray(y, dtype=np.complex128),
        code_prior=np.zeros(2*n) if prior is None else np.asarray(prior),
        constellation=np.array([.5+.5j, .5-.5j, -.5+.5j, -.5-.5j]),
        sigma2=.2, threshold=1e-4)


class LocalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_no_omission_matches_independent_production_update(self):
        s = state([[1+.1j, .1-.02j], [.2j, 1-.2j]], [1+.2j, -.3+.4j], [.1, .9, -.2, .3])
        before = {k: v.copy() for k, v in s.items() if isinstance(v, np.ndarray)}
        exact = reference_update(s)
        actual = bounded_update(s, 'amplitude', 0.)
        for key in ('llr', 'mean', 'variance'):
            np.testing.assert_allclose(actual[key], exact[key], atol=1e-10, rtol=1e-10)
        for key, value in before.items():
            np.testing.assert_array_equal(s[key], value)

    def test_weak_variance_is_preserved_and_power_not_multiplied_twice(self):
        s = state([[1, .1], [.1, 1]], [1, 1])
        result = bounded_update(s, 'amplitude', .2)
        self.assertEqual(int(result['retained'].sum()), 2)
        # The omitted .1 edge still contributes .1**2 * .5 to row variance.
        self.assertAlmostEqual(result['llr'][0], 2/(.2 + .1**2*.5), places=10)
        self.assertNotAlmostEqual(result['llr'][0], 2/.2, places=5)

    def test_budget_certificate_controls_same_prior_llr(self):
        s = state([[1, .02j], [.04, .9]], [.3+.1j, -.2j])
        exact = reference_update(s)
        for budget in (.05, .2, 100.):
            approximate = bounded_update(s, 'budget', budget)
            self.assertLessEqual(float(approximate['certificate'].max()), budget + 1e-12)
            bound = np.tile(2*approximate['certificate'], 2)
            self.assertTrue(np.all(np.abs(approximate['llr'] - exact['llr']) <= bound + 1e-9))

    def test_residual_anomaly_explicitly_restores_all_edges(self):
        s = state([[1, .1], [.1, 1]], [20, 20])
        approximate = bounded_update(s, 'reliability', 100.)
        exact = reference_update(s)
        self.assertTrue(approximate['recovery'])
        self.assertTrue(approximate['retained'].all())
        np.testing.assert_allclose(approximate['llr'], exact['llr'], atol=1e-9)

    def test_nonfinite_input_is_rejected(self):
        s = state([[1]], [np.nan])
        with self.assertRaisesRegex(ValueError, 'invalid frozen'):
            bounded_update(s, 'amplitude', .1)


if __name__ == '__main__':
    unittest.main()
