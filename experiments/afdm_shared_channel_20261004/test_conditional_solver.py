"""Independent physical dense matrices verify the sparse covariance contract."""
import unittest

import numpy as np

from experiments.afdm_shared_channel_20261004.conditional_solver import ConditionalSolver, cpp_time_matrix, finite_block_message
from experiments.sp_afdm_frozen_20260920.src.physical import Channel, daft


class ConditionalSolverTests(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.default_rng(714)
        self.n = 12; self.c1 = 5.3/24; self.c2 = .019

    def channel(self, delays):
        p = len(delays)
        return Channel(self.n, self.c1, self.c2, delays, np.linspace(-.32, .47, p),
                       (self.rng.normal(size=p)+1j*self.rng.normal(size=p))/np.sqrt(2*p))

    def test_sparse_cpp_time_action_including_wrap_and_aliases(self):
        for delays in [[0, 2, 5], [0, 11], [3, 3, 11]]:
            channel = self.channel(delays); H = cpp_time_matrix(channel)
            x = self.rng.normal(size=self.n)+1j*self.rng.normal(size=self.n)
            actual = daft(H@daft(x, self.c1, self.c2, True), self.c1, self.c2)
            np.testing.assert_allclose(actual, channel.apply(x), atol=1e-14)
            self.assertLessEqual(H.nnz, self.n*len(set(delays)))

    def test_independent_dense_solve_logdet_likelihood_and_counts(self):
        for delays in [[0, 2, 5], [0, 11], [3, 3, 11]]:
            channel = self.channel(delays)
            H = np.column_stack([channel.apply(e) for e in np.eye(self.n)])
            for target in [np.array([], int), np.array([0]), np.array([0, 7]), np.arange(self.n)]:
                variance = np.full(self.n, .5); variance[target] = 0
                S = .13*np.eye(self.n)+(H*variance)@H.conj().T
                solver = ConditionalSolver(channel, variance, target, .13)
                y = self.rng.normal(size=self.n)+1j*self.rng.normal(size=self.n)
                x = self.rng.normal(size=self.n)+1j*self.rng.normal(size=self.n)
                np.testing.assert_allclose(solver.solve(y), np.linalg.solve(S, y), atol=6e-13)
                self.assertAlmostEqual(solver.logdet, np.linalg.slogdet(S)[1], places=11)
                residual = y-H@x
                reference = -self.n*np.log(np.pi)-np.linalg.slogdet(S)[1]-np.vdot(residual, np.linalg.solve(S, residual)).real
                self.assertAlmostEqual(solver.log_likelihood(y, x), reference, places=10)
                self.assertEqual(solver.stats['sparse_factorizations'], 1)
                self.assertEqual(solver.stats['sparse_solve_calls'], 2+int(len(target)>0))
                self.assertEqual(solver.stats['conditional_likelihoods'], 1)

    def test_rejects_nonuniform_outside_variance_and_invalid_inputs(self):
        channel = self.channel([0, 3])
        with self.assertRaises(NotImplementedError):
            ConditionalSolver(channel, np.linspace(.1, .5, self.n), np.array([0, 1]), .1)
        for target in [[0., 1.], [0, 0], [-1], [self.n]]:
            with self.assertRaises(ValueError):
                ConditionalSolver(channel, .5, target, .1)
        for noise in [0, -1, np.nan]:
            with self.assertRaises(ValueError):
                ConditionalSolver(channel, .5, [0], noise)

    def test_zero_variance_and_multi_rhs(self):
        channel = self.channel([0, 11]); solver = ConditionalSolver(channel, 0., [1], .2)
        rhs = self.rng.normal(size=(self.n, 3))+1j*self.rng.normal(size=(self.n, 3))
        np.testing.assert_allclose(solver.solve(rhs), rhs/.2, atol=1e-13)
        self.assertEqual(solver.stats['sparse_solve_rhs'], 4)

    def test_complete_positive_finite_measure_pair_message(self):
        channel = self.channel([0, 11])
        nodes = np.array([[.3+.2j, .7], [-.4j, .6+.1j], [.9-.3j, -.2]])
        weights = np.array([.1, .3, .6])
        y = self.rng.normal(size=self.n)+1j*self.rng.normal(size=self.n)
        pilot = .4*np.exp(.3j*np.arange(self.n)); target = np.array([0, 7])
        args = (channel, nodes, weights, y, pilot, target, .5, .2)
        result = finite_block_message(*args)
        dense = finite_block_message(*args, backend='dense')
        self.assertEqual(result['candidate_count'], 16)
        self.assertEqual(len(np.unique(result['words'], axis=0)), 16)
        self.assertEqual(result['conditional_likelihood_count'], 48)
        for key in ['conditionals', 'scores', 'logp', 'probability', 'llr']:
            np.testing.assert_allclose(result[key], dense[key], atol=5e-13)
        # Independent ordinary-probability marginalization verifies node weights
        # and target normalization rather than only comparing two backends.
        densities = np.exp(dense['conditionals']-dense['conditionals'].max())
        marginal = weights@densities; marginal /= marginal.sum()
        np.testing.assert_allclose(result['probability'], marginal, atol=1e-14)
        for j in range(4):
            bits = result['bits'][:, j]
            expected = np.log(marginal[bits==0].sum()/marginal[bits==1].sum())
            self.assertAlmostEqual(result['llr'][j], expected, places=12)
        unweighted = densities.sum(axis=0); unweighted /= unweighted.sum()
        self.assertGreater(np.max(abs(marginal-unweighted)), 1e-5)
        self.assertEqual(sum(r['sparse_factorizations'] for r in result['operations']), 3)
        self.assertEqual(sum(r['sparse_solve_rhs'] for r in result['operations']), 54)
        self.assertEqual(sum(r['conditional_likelihoods'] for r in result['operations']), 48)
        with self.assertRaises(ValueError):
            finite_block_message(channel, nodes, [1., 1., 1.], y, pilot, target, .5, .2)


if __name__ == '__main__':
    unittest.main()
