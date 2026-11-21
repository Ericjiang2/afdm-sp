"""Small independent algebra contracts; no native receiver or scientific run."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('__gram_probe_test', Path(__file__).with_name('gram_block_probe.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class GramBlockTest(unittest.TestCase):
    def setUp(self):
        self.f, self.atoms = p.rep.synthetic_fixture()
        self.B = np.column_stack([a @ self.f['pilot'] for a in self.atoms])
        self.v = np.linspace(.05, .8, 32)
        self.G = np.einsum('prk,qrk,k->pq', self.atoms.conj(), self.atoms, self.v)
        self.noise = self.f['sigma2']

    def test_full_matches_augmented_least_squares(self):
        # Stack every uncertain-symbol direction as an independent residual row.
        uncertainty = (self.atoms*np.sqrt(self.v)[None, None, :]).reshape(2, -1).T
        augmented = np.vstack((self.B, uncertainty, np.sqrt(self.noise*2)*np.eye(2)))
        target = np.r_[self.f['y'], np.zeros(uncertainty.shape[0]+2)]
        reference = np.linalg.lstsq(augmented, target, rcond=None)[0]
        actual, detail = p.block.solve_gain(self.B, self.f['y'], self.G, self.noise, 'full')
        np.testing.assert_allclose(actual, reference, rtol=p.rep.RTOL, atol=p.rep.ATOL)
        self.assertEqual(detail['alpha'], 2*self.noise)

    def test_full_mean_covariance_pushforward_and_matched_diagonal(self):
        D = np.kron(np.eye(2), np.ones((1, 2)))
        full, a = p.block.solve_gain(self.B, self.f['y'], self.G, self.noise, 'full')
        copied, b = p.block.solve_gain(self.B @ D, self.f['y'], D.T @ self.G @ D, self.noise, 'full')
        np.testing.assert_allclose(D @ copied, full, rtol=p.rep.RTOL, atol=p.rep.ATOL)
        np.testing.assert_allclose(D @ b['covariance'] @ D.T, a['covariance'], rtol=p.rep.RTOL, atol=p.rep.ATOL)
        diagonal, c = p.block.solve_gain(self.B, self.f['y'], self.G, self.noise, 'diag')
        copied_diag, _ = p.block.solve_gain(self.B @ D, self.f['y'], D.T @ self.G @ D, self.noise, 'diag')
        np.testing.assert_array_equal(c['M'], a['M'])
        np.testing.assert_array_equal(c['b'], a['b'])
        np.testing.assert_array_equal(c['Q'], np.diag(np.diag(a['Q'])))
        m, rhs, alpha = np.diag(a['M']), a['b'], a['alpha']
        delta = m*rhs/((m+2*alpha)*(m+alpha))
        np.testing.assert_allclose(D @ copied_diag-diagonal, delta, rtol=p.rep.RTOL, atol=p.rep.ATOL)
        self.assertGreater(np.linalg.norm(delta), 1e-8)
        # Keeping old coordinate precision after duplication violates the prior contract.
        wrong = np.linalg.solve(b['M']+alpha*np.eye(4), b['b'])
        self.assertFalse(np.allclose(D @ wrong, full, rtol=p.rep.RTOL, atol=p.rep.ATOL))

    def test_mixed_delay_covariance_is_nontrivial_psd(self):
        fixture, v, gamma = p.gamma_fixture()
        self.assertEqual(fixture['delays'].tolist(), [1, 1, 3])
        self.assertGreater(np.ptp(v), .1)
        np.testing.assert_allclose(np.diag(gamma), np.full(3, v.sum()), atol=p.rep.ATOL)
        np.testing.assert_allclose(gamma, gamma.conj().T, atol=p.rep.ATOL)
        self.assertGreater(np.linalg.eigvalsh(gamma)[0], 0)
        self.assertGreater(np.linalg.norm(gamma-np.diag(np.diag(gamma))), .1)

    def test_invalid_inputs_fail_without_covariance_repair(self):
        for gamma in (np.full((2, 2), np.nan), np.array([[1., 2.], [0., 1.]]),
                      np.array([[1., 2.], [2., 1.]]), np.eye(3)):
            with self.assertRaises(ValueError):
                p.block.solve_gain(self.B, self.f['y'], gamma, self.noise, 'full')
        with self.assertRaises(ValueError):
            p.block.solve_gain(self.B, self.f['y'], self.G, 0, 'full')
        with self.assertRaises(ValueError):
            p.block.solve_gain(self.B, self.f['y'], self.G, self.noise, 'other')

    def test_existing_output_rejected_before_loading_native(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):
                p.run(SimpleNamespace(out=Path(folder)))


if __name__ == '__main__':
    unittest.main()
