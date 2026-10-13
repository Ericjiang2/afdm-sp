"""Small matrix qualifications; no full receiver or author-paper reproduction."""
import unittest
import numpy as np
from .supplement_fspai import factorized_sparse_precision
from .supplement_siso_mmse import siso_mmse
from .trans_next_fspai_quote import quote_state


class FSPAITests(unittest.TestCase):
    def test_full_budget_recovers_inverse(self):
        rng = np.random.default_rng(119)
        H = rng.normal(size=(7, 7))+1j*rng.normal(size=(7, 7))
        v = rng.uniform(.01, .5, 7)
        result = factorized_sparse_precision(H, v, .4, graph_tol=0., degree_cutoff=0,
                                             max_added=6, selection_tol=0.)
        C, L = result['covariance'].toarray(), result['factor'].toarray()
        np.testing.assert_allclose(L@L.conj().T, np.linalg.inv(C), rtol=2e-12, atol=2e-12)
        self.assertEqual(result['small_solves'], 21)
        np.testing.assert_array_equal(np.triu(L, 1), 0)

    def test_diagonal_and_bounded_columns(self):
        H = np.diag([1., 2., 0., .5])
        result = factorized_sparse_precision(H, np.array([.5, 0., .2, .4]), .2, max_added=2)
        L = result['factor'].toarray()
        np.testing.assert_allclose(L@L.conj().T, np.linalg.inv(result['covariance'].toarray()), atol=1e-14)
        self.assertEqual(result['small_solves'], 0)
        # Each covariance row has 3 neighbors including itself. The retained
        # author rule removes off-diagonal edges at cutoff 3.
        dense = factorized_sparse_precision(np.eye(3)+.2*np.ones((3, 3)), np.ones(3), .1, max_added=2)
        self.assertEqual(dense['graph_edges_before_prune'], 9)
        self.assertEqual(dense['graph_edges_after_prune'], 3)
        self.assertEqual(dense['factor_nnz'], 3)

    def test_invalid_variance_and_budget_fail(self):
        for v, noise, extra in [(np.array([-.1, 1]), .2, {}), (np.ones(2), 0., {}),
                                (np.ones(2), .2, dict(max_added=2))]:
            with self.assertRaises(ValueError):
                factorized_sparse_precision(np.eye(2), v, noise, **dict({"max_added":1, **extra}))

    def test_quote_exact_diagonal_and_invalid_approximation(self):
        controls = dict(graph_tol=.001, degree_cutoff=3, max_added=0, selection_tol=.001)
        y, prior = np.linspace(-1, 1, 12).astype(complex), np.zeros(24)
        for dense_column in (False, True):
            H = np.eye(12, dtype=complex)
            if dense_column:
                H[:] = 0
                H[:, 0] = 1
            state = dict(siso_mmse(y, H, .2, prior), H=H, y=y, sigma2=.2, consumed_prior=prior)
            result = quote_state(state, controls)
            if dense_column:
                self.assertFalse(result['candidate_valid'])
                self.assertEqual(result['invalid_denominators'], 1)
                self.assertIsNone(result['channel_llr'])
            else:
                self.assertTrue(result['candidate_valid'])
                np.testing.assert_allclose(result['channel_llr'], state['channel_llr'], rtol=1e-13, atol=1e-13)


if __name__ == '__main__':
    unittest.main()
