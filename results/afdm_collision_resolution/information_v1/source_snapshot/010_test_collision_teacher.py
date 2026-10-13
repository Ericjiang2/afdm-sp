"""Deterministic formula qualifications, not research observations."""
import unittest

import numpy as np
from scipy.special import logsumexp

from experiments.afdm_collision_resolution.collision_teacher import (
    CollisionTeacher, collision_geometry, exact_moment_system, exact_power_moment,
    monomial_and_derivatives, power_exponents,
)
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior


class TeacherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.teacher = CollisionTeacher(.35, sigma2=.8)
        cls.y = np.array([[0, 0, 0, 0], [1+.2j, -.3+.5j, .8j, .4-.7j],
                          [2j, 1-.4j, -.7-.2j, .3+.9j]])

    def test_analytic_geometry_against_frozen_finite_differences(self):
        for mu in (.27, .35):
            geo = collision_geometry(mu)
            self.assertLess(max(row['w_dot_max'] for row in geo['finite_difference']), 2e-7)
            self.assertLess(max(row['u0_dot_max'] for row in geo['finite_difference']), 2e-7)
            self.assertLess(abs(np.vdot(geo['u0'], geo['u1'])), 1e-13)
            self.assertGreater(geo['kappa'], 0)

    def test_phase_elimination_against_direct_periodic_sum(self):
        model = self.teacher
        phase = np.exp(2j*np.pi*np.arange(256)/256)
        m0 = (model.m0[:, None, :]*phase[None, :, None]).reshape(-1, 4)
        m1 = (model.m1[:, None, :]*phase[None, :, None]).reshape(-1, 4)
        mmu = (model.m_mu[:, None, :]*phase[None, :, None]).reshape(-1, 4)
        rows, logs = [], []
        for y in self.y:
            residual = y-m0
            density_logs = -np.sum(abs(residual)**2, axis=1)/model.sigma2-4*np.log(np.pi*model.sigma2)
            posterior = np.exp(density_logs-logsumexp(density_logs))
            inner0 = np.sum(residual.conj()*m0, axis=1)
            inner1 = np.sum(residual.conj()*m1, axis=1)
            tangent = (abs(inner1)**2/model.sigma2**2-np.sum(abs(m1)**2, axis=1)/model.sigma2
                       -inner0.real/model.sigma2)
            rows.append([model.kappa*(posterior@tangent),
                         posterior@(2*np.sum(residual.conj()*mmu, axis=1).real/model.sigma2),
                         posterior@(inner0.real/model.sigma2),
                         posterior@(-4+np.sum(abs(residual)**2, axis=1)/model.sigma2)])
            logs.append(logsumexp(density_logs)-np.log(len(m0)))
        actual = model.evaluate(self.y)
        np.testing.assert_allclose(actual['logpdf'], logs, rtol=0, atol=2e-12)
        np.testing.assert_allclose(actual['score'], rows, rtol=0, atol=2e-12)

    def test_nuisance_likelihood_finite_differences(self):
        actual = self.teacher.evaluate(self.y)['score']
        for axis in range(3):
            for step in (1e-4, 5e-5, 2.5e-5):
                point = np.array([.35, 0., np.log(.8)])
                plus, minus = point.copy(), point.copy()
                plus[axis] += step; minus[axis] -= step
                a = CollisionTeacher(plus[0], np.exp(plus[1]), np.exp(plus[2]))
                b = CollisionTeacher(minus[0], np.exp(minus[1]), np.exp(minus[2]))
                fd = (a.logpdf(self.y)-b.logpdf(self.y))/(2*step)
                np.testing.assert_allclose(actual[:, axis+1], fd, rtol=2e-6, atol=3e-7)

    def test_actual_rank_one_sampling_replay(self):
        # Eight fixed fixtures only, not a scientific Monte Carlo information run.
        raw = self.teacher.sample(8, [941, 7])
        old = ActualPrior(n=4)
        expected = old.sample([0, .35, 0, np.log(.8)], 8, [941, 7])
        np.testing.assert_array_equal(raw['y'], expected)
        np.testing.assert_allclose(np.sum(abs(raw['time_response'])**2, axis=1), 4, atol=3e-13)
        phase = np.sum(raw['time_response']*self.teacher.geo['u0'].conj(), axis=1)/2
        np.testing.assert_allclose(abs(phase), 1., atol=3e-14)
        np.testing.assert_allclose(raw['time_response'], 2*phase[:, None]*self.teacher.geo['u0'], atol=3e-14)

    def test_constant_moment_and_zero_mean_tangent(self):
        mean, derivative = exact_power_moment(self.teacher, np.zeros(4, int))
        self.assertEqual(mean, 1.)
        np.testing.assert_array_equal(derivative, np.zeros(4))

    def test_power_first_moment_independent_identity(self):
        for i in range(4):
            exponent = np.eye(4, dtype=int)[i]
            mean, derivative = exact_power_moment(self.teacher, exponent)
            expected_mean = abs(self.teacher.m0[:, i])**2+self.teacher.sigma2
            expected_r = self.teacher.kappa*(abs(self.teacher.m1[:, i])**2-abs(self.teacher.m0[:, i])**2)
            np.testing.assert_allclose(mean, expected_mean.mean(), atol=2e-14)
            np.testing.assert_allclose(derivative[0], expected_r.mean(), atol=2e-14)

    def test_polynomial_tangent_independent_phase_difference_with_zeros(self):
        m = np.array([[0, .4+.2j, -.5j, .7]])
        v = np.array([[.3j, .6, -.2, .4j]])
        phi = np.exp(2j*np.pi*np.arange(128)/128)
        t = 1e-6
        moved = np.sqrt(1-t)*m+np.sqrt(t)*phi[:, None]*v
        for exponent in ([1, 0, 0, 0], [1, 1, 0, 0], [0, 2, 1, 1]):
            exponent = np.asarray(exponent)
            base, _, tangent = monomial_and_derivatives(m, v, v, exponent)
            observed = np.prod(abs(moved)**(2*exponent), axis=1).mean()
            self.assertAlmostEqual(float((observed-base[0])/t), float(tangent[0]), delta=2e-7)

    def test_polynomial_nuisance_derivatives_and_covariance(self):
        system = exact_moment_system(self.teacher)
        self.assertEqual(system['derivatives'].shape, (14, 4))
        self.assertGreater(np.linalg.eigvalsh(system['covariance']).min(), 0.)
        for axis in range(3):
            step = 1e-5
            p = np.array([.35, 0., np.log(.8)])
            plus, minus = p.copy(), p.copy(); plus[axis] += step; minus[axis] -= step
            a = CollisionTeacher(plus[0], np.exp(plus[1]), np.exp(plus[2]))
            b = CollisionTeacher(minus[0], np.exp(minus[1]), np.exp(minus[2]))
            for k, expected in zip(system['exponents'], system['derivatives'][:, axis+1]):
                fd = (exact_power_moment(a, k)[0]-exact_power_moment(b, k)[0])/(2*step)
                self.assertAlmostEqual(fd, expected, delta=2e-6)

    def test_reject_platform_branch_and_invalid_inputs(self):
        for mu in (.04, .5, 0., 1., float('nan')):
            with self.assertRaises(ValueError):
                CollisionTeacher(mu)
        for noise in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                CollisionTeacher(.35, sigma2=noise)
        for y in (np.zeros((2, 3)), np.array([[np.nan]*4]), np.empty((0, 4))):
            with self.assertRaises(ValueError):
                self.teacher.evaluate(y)


if __name__ == '__main__':
    unittest.main()
