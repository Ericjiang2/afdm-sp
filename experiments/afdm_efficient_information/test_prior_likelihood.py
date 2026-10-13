"""Small deterministic/qualification contracts, not registered research data."""
import unittest
import numpy as np
from scipy.special import logsumexp

from experiments.afdm_efficient_information.prior_likelihood import (
    ActualPrior, angular_density, cp1_nodes, daft, pdp_distribution,
    project_information, qpsk_time, system_for, actual_signal_covariance, collision_qlogq_coefficient,
)
from experiments.afdm_higher_order_information.prior import geometry, pushforward_jvp
from experiments.afdm_shared_channel_20261004.production_prior import dense_gram, normalize_gain


class PriorContracts(unittest.TestCase):
    theta = np.array([.2, .35, 0., np.log(.8)])

    def test_dense_gram_and_daft(self):
        for n in (4, 8):
            system = system_for(n)
            geo = geometry(system, .35, .2)
            np.testing.assert_allclose(geo['gram'], dense_gram(system, geo['weights']), atol=2e-14)
            a = daft(n)
            np.testing.assert_allclose(a@a.conj().T, np.eye(n), atol=2e-14)
            width = 2*system.k_max_cap+1
            ids = np.flatnonzero(np.any(geo['weights'] != 0, axis=1))
            h = system.gen_h_daft(geo['weights'][ids, 0], ids//width, ids % width-system.k_max_cap)
            np.testing.assert_allclose(a.conj().T@h@a, np.diag(geo['g0'][:, 0]), atol=2e-14)

    def test_discrete_pdp_against_two_increment_enumeration(self):
        result = pdp_distribution(4, .35, .2)
        survival = np.exp(-1/8000/.0008)
        expected = {}
        for assignment in (0, 1):
            l1, l2 = result['limits'] if assignment == 0 else result['limits'][::-1]
            for j1 in range(1, l1+1):
                for j2 in range(1, l2-j1+1):
                    key = (assignment, j2)
                    expected[key] = expected.get(key, 0)+.5*(1-survival)**2*survival**(j1+j2-2)
        for assignment, increment, mass in zip(result['assignments'], result['increments'], result['raw_masses']):
            self.assertAlmostEqual(mass, expected[(assignment, increment)], places=15)
        self.assertGreater(result['event_probability'], 0)
        self.assertLess(result['event_probability'], 1)

    def test_acg_density_and_swap(self):
        nodes, weights = cp1_nodes(40, 8)
        density = angular_density(nodes, np.array([[1., .3]]), np.ones(1))
        self.assertAlmostEqual(weights@density, 1., places=12)
        self.assertGreater(weights@(density*abs(nodes[:, 0])**2), .5)
        plus = pdp_distribution(4, .35, .2)
        minus = pdp_distribution(4, .35, -.2)
        fplus = angular_density(nodes, plus['pdp'], plus['weights'])
        fminus = angular_density(nodes[:, ::-1], minus['pdp'], minus['weights'])
        np.testing.assert_allclose(fplus, fminus, atol=1e-14)

    def test_bessel_against_explicit_global_phase_integral(self):
        model = ActualPrior(order=4, phases=8, pdp='equal')
        y = np.array([[.2+.4j, -.3+.1j, .5-.2j, .1+.7j]])
        components = model._components(self.theta)
        means, lw = components['means'], components['logweights']
        phases = np.exp(2j*np.pi*(np.arange(128)+.5)/128)
        sigma = np.exp(self.theta[3])
        residual = y[:, None, :]-means[:, None, :]*phases[None, :, None]
        explicit = logsumexp(lw[:, None]-np.sum(abs(residual)**2, axis=2)/sigma
                             -model.n*np.log(np.pi*sigma))-np.log(len(phases))
        self.assertAlmostEqual(float(model.logpdf(y, self.theta)[0]), explicit, places=12)

    def test_full_score_vs_likelihood_finite_difference(self):
        for pdp in ('marginal', [1., .3]):
            model = ActualPrior(order=6, phases=12, pdp=pdp)
            y = np.array([[.2+.4j, -.3+.1j, .5-.2j, .1+.7j]])
            score = model.evaluate(y, self.theta, step=1e-5)['score'][0]
            finite = []
            for axis in range(4):
                plus, minus = self.theta.copy(), self.theta.copy()
                plus[axis] += 2e-5; minus[axis] -= 2e-5
                finite.append((model.logpdf(y, plus)[0]-model.logpdf(y, minus)[0])/4e-5)
            np.testing.assert_allclose(score, finite, rtol=2e-5, atol=3e-7)

    def test_full_d_r_response_jvp(self):
        nodes, _ = cp1_nodes(3, 4)
        d = np.array([1., .3]); dd = np.array([.2, -.1])
        r = np.array([[1., .1j], [-.1j, .8]])
        dr = np.array([[.1, .03j], [-.03j, -.2]])
        b = np.array([[1., .2j], [.4j, -.8]])
        db = np.array([[.2, .1j], [.3j, .1]])
        _, jvp = pushforward_jvp(nodes, d, r, b, dd, dr, db)
        step = 1e-5
        plus = normalize_gain(nodes*np.sqrt(d+step*dd), r+step*dr)@(b+step*db).T
        minus = normalize_gain(nodes*np.sqrt(d-step*dd), r-step*dr)@(b-step*db).T
        np.testing.assert_allclose(jvp, (plus-minus)/(2*step), atol=2e-10)

    def test_exact_platform_zero_for_any_pdp(self):
        y = np.array([[.2+.4j, -.3+.1j, .5-.2j, .1+.7j]])
        for pdp in ('marginal', 'equal', [1., .02]):
            model = ActualPrior(pdp=pdp)
            theta = np.array([.015, .04, 0., 0.])
            result = model.evaluate(y, theta)
            np.testing.assert_array_equal(result['score'][:, :2], 0.)
            changed = theta.copy(); changed[0] = .025
            np.testing.assert_array_equal(result['logpdf'], model.logpdf(y, changed))

    def test_singular_g1_not_regularized(self):
        model = ActualPrior(model='g1', pdp='equal')
        theta = np.array([.01, .04, 0., 0.])
        self.assertEqual(model.branch(theta)['moments']['second'], 'infinite')
        with self.assertRaisesRegex(ValueError, 'singular'):
            model.evaluate(np.zeros((1, 4)), theta)

    def test_projection_accepts_singular_nuisance(self):
        score = np.array([[1., 1., 2., 0.], [-1., 1., 2., 0.]])
        result = project_information(score)
        self.assertEqual(result['nuisance_rank'], 1)
        self.assertAlmostEqual(result['effective'], 1.)

    def test_analytic_actual_covariance_against_independent_angular_rule(self):
        model = ActualPrior(order=48, phases=96, pdp='marginal')
        branch = model.branch(self.theta)
        nodes = model.nodes
        gains = normalize_gain(nodes, branch['geometry']['gram'])
        response = gains@branch['geometry']['g0'].T
        weight = model.weights*angular_density(nodes, branch['pdp']['pdp'], branch['pdp']['weights'])
        quadrature = np.einsum('b,bi,bj->ij', weight, response, response.conj())
        analytic = actual_signal_covariance(model, self.theta)
        np.testing.assert_allclose(analytic, quadrature, atol=2e-8)
        self.assertAlmostEqual(np.trace(analytic).real, model.n, places=12)

    def test_nonplatform_collision_analytic_log_coefficient(self):
        model = ActualPrior(pdp='equal')
        expected = collision_qlogq_coefficient(model, .35)
        base = actual_signal_covariance(model, [0., .35, 0., 0.]).diagonal().real
        deltas = np.array([.001, .0001])
        values = [(actual_signal_covariance(model, [d, .35, 0., 0.]).diagonal().real-base)/d**2 for d in deltas]
        slope = (values[1]-values[0])/np.log((deltas[0]/deltas[1])**2)
        np.testing.assert_allclose(slope, expected, rtol=5e-4, atol=1e-4)
        self.assertGreater(np.linalg.norm(expected), 1.)

    def test_sampler_not_quadrature_dependent(self):
        a, b = ActualPrior(order=4, phases=8), ActualPrior(order=9, phases=20)
        np.testing.assert_array_equal(a.sample(self.theta, 4, 981), b.sample(self.theta, 4, 981))


if __name__ == '__main__':
    unittest.main()
