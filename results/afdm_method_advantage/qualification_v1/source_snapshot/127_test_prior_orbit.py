"""Small independent probability contracts, plus saved-array recount (no receiver)."""
from pathlib import Path
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from experiments.afdm_inference_causal_20261002.exact_oracle import enumerate_qpsk, exact_posterior
from experiments.afdm_structured_inference_20261003.common import ARTIFACT
from experiments.afdm_structured_inference_20261003.prior import representation, predictive
from experiments.afdm_structured_inference_20261003.orbit import conditional_orbits, analyze


class ProbabilityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = threadpool_limits(limits=1)

    @classmethod
    def tearDownClass(cls):
        cls.threads.restore_original_limits()

    def test_nonuniform_split_is_same_exact_model(self):
        ops = np.stack([np.eye(2), np.array([[0, 1j], [1, 0]])])
        transform = np.array([[1, 1, 0], [0, 0, 1.]])
        mean = np.array([.2j, .1])
        cov = np.array([[.5, .08j], [-.08j, .4]])
        newops, newmean, newcov = representation(ops, transform, mean, cov)
        np.testing.assert_allclose(transform@newmean, mean, atol=1e-14)
        np.testing.assert_allclose(transform@newcov@transform.T, cov, atol=1e-14)
        words, bits = enumerate_qpsk(2)
        y, pilot = np.array([.5+.2j, -.3]), np.array([.4, .2j])
        base = exact_posterior(y, ops, pilot, words, mean, cov, .2, bits=bits)
        split = exact_posterior(y, newops, pilot, words, newmean, newcov, .2, bits=bits)
        np.testing.assert_allclose(base.llr, split.llr, atol=2e-12)
        old_pm, old_pc = predictive(ops, pilot, words, mean, cov)
        new_pm, new_pc = predictive(newops, pilot, words, newmean, newcov)
        np.testing.assert_allclose(old_pm, new_pm, atol=2e-12)
        np.testing.assert_allclose(old_pc, new_pc, atol=2e-12)
        # 1/P after splitting only U changes physical covariance, not a numerical error.
        np.testing.assert_allclose(transform@transform.T/3, np.diag([2/3, 1/3]))
        self.assertGreater(np.linalg.norm(transform@transform.T/3-np.eye(2)/2), .2)

    def test_invalid_transform_rejected(self):
        with self.assertRaises(ValueError):
            representation(np.stack([np.eye(2)]*2), np.zeros((2, 1)), np.zeros(2), np.eye(2))

    def test_fixed_orbit_nonconjugate_cross(self):
        ops = np.stack([np.eye(2), np.array([[0, 1], [1j, 0]])])
        h0 = np.array([[.8+.3j, -.2+.4j]])
        d0 = np.array([[.5+.5j, .5-.5j]])
        pilot, y = np.array([.1, -.1j]), np.array([.2+.7j, .8-.2j])
        sigma, ls = .4, .8
        out = conditional_orbits(y, ops, pilot, h0, d0, sigma, np.array([ls]))
        signs = np.array([1, -1])
        h, d = signs[:, None]*h0, signs[:, None]*d0
        f = np.einsum('kp,pij,kj->ki', h, ops, pilot+d)
        lp = np.array([ls, 0.])-np.sum(abs(y-f)**2, axis=1)/sigma
        probability = np.exp(lp-lp.max()); probability /= probability.sum()
        mh, md = probability@h, probability@d
        pseudo = np.einsum('k,kp,kn->pn', probability, h-mh, d-md)
        wrong_conjugate = np.einsum('k,kp,kn->pn', probability, h-mh, (d-md).conj())
        np.testing.assert_allclose(out['cross'][0], pseudo, atol=2e-14)
        self.assertGreater(np.linalg.norm(pseudo-wrong_conjugate), 1e-4)
        np.testing.assert_allclose(out['prediction'][0], probability@f, atol=2e-14)

    def test_no_pilot_keeps_product_but_not_bit_information(self):
        words, bits = enumerate_qpsk(2, parity_check=np.ones((1, 4), int))
        ops = np.stack([np.eye(2), np.array([[0, 1], [1j, 0]])])
        reps = np.array([[.8+.3j, -.2+.4j], [-.4+.2j, .9-.1j]])
        metrics, raw = analyze(np.array([.4+.1j, -.5j]), ops, np.zeros(2), reps,
                               words, bits, np.array([.6, .4]), np.ones(len(words))/len(words), .3)
        np.testing.assert_allclose(raw['exact_bit_probability'], .5, atol=1e-14)
        self.assertGreater(metrics['methods']['global_mean_product_exact_marginals']['prediction_squared_error'], .01)
        self.assertLess(metrics['exact_marginal_product_llr_max_error'], 1e-13)
        self.assertLess(metrics['methods']['retain_all_cross_moments']['prediction_squared_error'], 1e-25)

    def test_saved_prior_recount(self):
        base = ARTIFACT/'execution/prior_v1'
        if not base.exists():
            self.skipTest('registered prior evidence not yet generated')
        paths = [base/f'prior_{seed}_{geometry}.npz' for seed in range(3)
                 for geometry in ['separated', 'same_delay']]
        for path in paths:
            with self.subTest(path=path.name), np.load(path) as a:
                for name in ['zero_iid_rotation', 'zero_iid_split_support',
                             'zero_iid_split_full_support', 'nonzero_correlated_rotation',
                             'nonzero_correlated_split_support', 'nonzero_correlated_split_full_support']:
                    altops = np.einsum('pij,pq->qij', a['operators'], a[name+'_T'])
                    posterior = exact_posterior(a['y'], altops, a['pilot'], a['words'],
                        a[name+'_beta_mean'], a[name+'_beta_cov'], float(a['sigma2']), bits=a['bits'])
                    np.testing.assert_allclose(posterior.llr, a[name+'_exact_llr'], atol=2e-11)
                    np.testing.assert_allclose(posterior.llr, a[name+'_base_llr'], atol=2e-11)
                np.testing.assert_allclose(a['UUVV_exact_llr'], a['base_exact_llr'], atol=2e-11)
                with np.load(path.with_name(path.stem+'_UV.npz')) as uv, np.load(path.with_name(path.stem+'_UUVV.npz')) as split:
                    np.testing.assert_allclose(uv['physical_h0'], split['physical_h0'], atol=2e-11)
                    aggregated = split['h_trajectory'].reshape(20, 2, 2).sum(axis=2)
                    self.assertGreater(np.linalg.norm(aggregated[0]-uv['h_trajectory'][0]), .001)
                    self.assertGreater(np.linalg.norm(split['llr']-uv['llr']), .01)

    def test_saved_orbit_recount(self):
        base = ARTIFACT/'execution/orbit_v1'
        if not base.exists():
            self.skipTest('registered orbit evidence not yet generated')
        paths = list(base.glob('orbit_*.npz'))
        self.assertEqual(len(paths), 18)
        for path in paths:
            with self.subTest(path=path.name), np.load(path) as a:
                metrics, raw = analyze(a['y'], a['operators'], a['pilot'], a['representatives'],
                    a['words'], a['bits'], a['prior_h'], a['prior_d'], float(a['sigma2']))
                np.testing.assert_allclose(raw['exact_llr'], a['exact_llr'], atol=3e-11)
                self.assertLess(max(metrics['identity_errors'].values()), 3e-11)


if __name__ == '__main__':
    unittest.main()
