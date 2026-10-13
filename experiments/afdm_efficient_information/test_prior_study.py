"""Evidence-gate regressions; synthetic fixtures generate no research data."""
import unittest
import numpy as np
from experiments.afdm_efficient_information.prior_likelihood import ActualPrior
from experiments.afdm_efficient_information.prior_study import (
    INFORMATION_CONFIG, discrete_branch, fit_collision_tail, information_refinement,
)


class EvidenceGates(unittest.TestCase):
    def test_discrete_branch_ignores_expected_collision_rank_change(self):
        model = ActualPrior(pdp='marginal')
        collision = model.branch([0., .27, 0., 0.])
        tail = model.branch([.00003, .27, 0., 0.])
        early = model.branch([.01, .27, 0., 0.])
        self.assertNotEqual(collision['moments']['rank'], tail['moments']['rank'])
        self.assertEqual(discrete_branch(collision), discrete_branch(tail))
        self.assertNotEqual(discrete_branch(collision), discrete_branch(early))
        self.assertNotEqual(discrete_branch(collision)['pdp_limits'], discrete_branch(early)['pdp_limits'])

    def test_collision_fit_cannot_replace_an_invalid_registered_tail_point(self):
        coefficient = np.array([1., -1.])
        points = [dict(delta=d, even_change=(coefficient*d*d*np.log(1/d**2)).tolist(),
                       same_as_collision=True) for d in [.03, .01, .003, .001]]
        fit = fit_collision_tail(points, coefficient, count=3, tolerance=.03)
        self.assertTrue(fit['log_slope_refined'])
        points[-2]['same_as_collision'] = False
        fit = fit_collision_tail(points, coefficient, count=3, tolerance=.03)
        self.assertFalse(fit['branch_qualified'])
        self.assertFalse(fit['log_slope_refined'])
        self.assertIsNone(fit['log_slope_coefficient'])
        self.assertEqual(fit['fit_deltas'], [.01, .003, .001])

    def test_bad_or_missing_derivative_step_blocks_refinement(self):
        comparison = dict(logpdf_max=0., score_relative_rms=[0.]*4)
        derivatives = [dict(step=s, comparison=dict(comparison)) for s in INFORMATION_CONFIG['derivative_steps'][1:]]
        estimate = {'fine':dict(quadrature_mass_error=0.)}
        checks = information_refinement([comparison], derivatives, np.zeros(4), estimate, 0.)
        self.assertTrue(all(checks.values()))
        derivatives[0]['comparison'] = dict(logpdf_max=0., score_relative_rms=[.01, 0., 0., 0.])
        checks = information_refinement([comparison], derivatives, np.zeros(4), estimate, 0.)
        self.assertFalse(checks['derivative_steps'])
        self.assertTrue(checks['direct_finite_difference'])
        self.assertFalse(all(checks.values()))
        checks = information_refinement([comparison], [], np.zeros(4), estimate, 0.)
        self.assertFalse(checks['derivative_steps'])


if __name__ == '__main__':
    unittest.main()
