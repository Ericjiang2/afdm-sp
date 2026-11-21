"""Synthetic tests of the DRAFT §7 verdict and its bootstrap inputs."""

from itertools import product
import unittest

import numpy as np

import verdict

PASSING_GAP = dict(point=.02, ci_lo=.01, denominator_nonpositive_fraction=.01)
AT_LEAST_HALF = 'recovers at least half'
LESS_THAN_QUARTER = 'recovers less than one quarter'
INTERVALS = {
    AT_LEAST_HALF: dict(half=dict(ci_lo=.001, ci_hi=.01), quarter=dict(ci_lo=.006, ci_hi=.015)),
    LESS_THAN_QUARTER: dict(half=dict(ci_lo=-.01, ci_hi=-.006), quarter=dict(ci_lo=-.005, ci_hi=-.001)),
    'uncertain': dict(half=dict(ci_lo=-.001, ci_hi=.003), quarter=dict(ci_lo=.004, ci_hi=.008)),
}


def repeated_grid(failures_by_arm, n_frames=200):
    outcomes = {
        arm: np.tile([True] * failures + [False] * (12 - failures), n_frames)
        for arm, failures in failures_by_arm.items()
    }
    return outcomes, np.repeat(np.arange(n_frames), 12)


class VerdictTest(unittest.TestCase):
    def test_all_arm_classifications_and_joint_outcomes(self):
        joint = {
            (AT_LEAST_HALF, LESS_THAN_QUARTER): 'H-cap supported',
            (LESS_THAN_QUARTER, AT_LEAST_HALF): 'H-ref supported',
            (AT_LEAST_HALF, AT_LEAST_HALF): 'both interventions recover at least half',
            (LESS_THAN_QUARTER, LESS_THAN_QUARTER): 'both interventions recover less than one quarter',
        }
        for statuses in product(INTERVALS, repeat=2):
            by_arm = dict(zip(('K', 'M'), statuses, strict=True))
            contrasts = {arm: INTERVALS[status] for arm, status in by_arm.items()}
            with self.subTest(statuses=statuses):
                result = verdict.classify(PASSING_GAP, contrasts, dict(K=5, M=5))
                self.assertEqual(result['by_arm'], by_arm)
                self.assertEqual(result['verdict'], joint.get(statuses, 'uncertain'))

    def test_each_premise_gate_and_inclusive_one_percent_limit(self):
        for failed_check, change in [
            ('point_positive', {'point': 0.}),
            ('lower_bound_positive', {'ci_lo': 0.}),
            ('denominator_failure_within_limit', {'denominator_nonpositive_fraction': .01005}),
        ]:
            with self.subTest(failed_check=failed_check):
                result = verdict.classify(PASSING_GAP | change, {}, {})
                self.assertFalse(result['gap_established'])
                self.assertEqual(result['verdict'], 'not evaluable')
                self.assertEqual(result['by_arm'], dict(K='not evaluable', M='not evaluable'))
                self.assertEqual([name for name, passed in result['premise_checks'].items() if not passed],
                                 [failed_check])
        contrasts = dict(K=INTERVALS[AT_LEAST_HALF], M=INTERVALS[LESS_THAN_QUARTER])
        self.assertTrue(verdict.classify(PASSING_GAP, contrasts, dict(K=5, M=5))['gap_established'])

    def test_sparse_clusters_take_precedence(self):
        contrasts = dict(K=INTERVALS[AT_LEAST_HALF], M=INTERVALS[LESS_THAN_QUARTER])
        result = verdict.classify(PASSING_GAP, contrasts, dict(K=4, M=5))
        self.assertEqual(result['by_arm'], dict(K='uncertain', M=LESS_THAN_QUARTER))
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertEqual(verdict.classify(PASSING_GAP, contrasts, dict(K=5, M=5))['verdict'], 'H-cap supported')

    def test_cutoff_equality_and_confidence_level(self):
        outcomes, frames = repeated_grid(dict(R0=2, U2=10, K=6, M=8, KM=2))
        result = verdict.readout(outcomes, frames)
        self.assertEqual(result['cutoff_contrasts']['K']['half']['ci_lo'], 0.)
        self.assertEqual(result['cutoff_contrasts']['M']['quarter']['ci_hi'], 0.)
        self.assertEqual(result['verdict']['by_arm'], dict(K='uncertain', M='uncertain'))
        interval = verdict.cutoff_summary(.5, np.linspace(0, 1, 1001))
        self.assertEqual(interval['confidence_level'], .975)
        self.assertEqual((interval['ci_lo'], interval['ci_hi']), (.0125, .9875))

    def test_complete_synthetic_grid_and_interaction_sign(self):
        outcomes, frames = repeated_grid(dict(R0=2, U2=10, K=5, M=9, KM=3), n_frames=400)
        result = verdict.readout(outcomes, frames)
        self.assertEqual(result['bootstrap'], dict(draws=20000, seed=20261121))
        self.assertEqual(result['n_frame_clusters'], 400)
        self.assertEqual(result['gap']['point'], 8 / 12)
        self.assertAlmostEqual(result['recovery']['K']['point'], .625, places=15)
        self.assertEqual(result['recovery']['M']['point'], .125)
        self.assertEqual(result['cutoff_contrasts']['K']['half']['ci_lo'], 1 / 12)
        self.assertEqual(result['cutoff_contrasts']['M']['quarter']['ci_hi'], -1 / 12)
        self.assertEqual(result['difference_vs_R0']['KM']['point'], 1 / 12)
        self.assertEqual(result['cap_by_refinement_interaction']['point'], -1 / 12)
        self.assertEqual(result['cap_by_refinement_interaction']['ci_hi'], -1 / 12)
        self.assertEqual(result['verdict']['verdict'], 'H-cap supported')

    def test_discordance_uses_any_paired_row_and_kappa_is_unclipped(self):
        outcomes, frames = repeated_grid(dict(R0=4, U2=8, K=8, M=9, KM=2))
        for start in range(0, 4 * 12, 12):
            outcomes['K'][[start, start + 8]] = [False, True]
        result = verdict.readout(outcomes, frames)
        self.assertEqual(result['gap']['point'], 4 / 12)
        self.assertEqual(result['discordant_frame_clusters'], dict(K=4, M=200))
        self.assertEqual(result['recovery']['K']['point'], 0.)
        self.assertEqual(result['recovery']['M']['point'], -.25)
        self.assertEqual(result['verdict']['by_arm'], dict(K='uncertain', M=LESS_THAN_QUARTER))
        outcomes['K'] = np.tile([True] * 3 + [False] * 9, 200)
        self.assertAlmostEqual(verdict.readout(outcomes, frames)['recovery']['K']['point'], 1.25, places=15)

    def test_cutoff_intervals_include_nonpositive_gap_draws(self):
        outcomes = dict(R0=[0, 1, 0], U2=[1, 0, 1], K=[0, 1, 0], M=[0, 1, 0], KM=[0, 1, 0])
        result = verdict.readout(outcomes, [0, 1, 2])
        self.assertGreater(result['gap']['denominator_nonpositive_fraction'], .01)
        self.assertEqual(result['gap']['ci_lo'], -1.)
        self.assertEqual(result['cutoff_contrasts']['K']['half']['ci_lo'], -.5)
        self.assertEqual(result['recovery']['K']['ci_lo'], 1.)
        self.assertFalse(result['recovery']['K']['evaluable'])
        self.assertEqual(result['verdict']['verdict'], 'not evaluable')

    def test_pairing_and_differences_when_gap_fails(self):
        # Independent draws across arms would give the exactly zero gap a nonzero width.
        outcomes = [0, 0, 0, 1]
        columns = dict(R0=outcomes, U2=outcomes, K=[0] * 4, M=outcomes, KM=[0] * 4)
        result = verdict.readout(columns, [0, 0, 0, 1])
        self.assertEqual(result['fer']['U2']['point'], .25)
        self.assertEqual(result['fer']['U2']['ci_hi'], 1.)
        self.assertEqual(result['gap']['ci_width'], 0.)
        self.assertEqual(result['difference_vs_R0']['KM']['point'], -.25)
        self.assertEqual(result['gap']['denominator_nonpositive_fraction'], 1.)
        self.assertIsNone(result['recovery']['M']['point'])
        self.assertEqual(result['verdict']['verdict'], 'not evaluable')

    def test_rejects_unpaired_or_nonbinary_data(self):
        outcomes = dict.fromkeys(('R0', 'U2', 'K', 'M', 'KM'), [0, 1])
        with self.assertRaisesRegex(ValueError, 'Expected paired outcomes'):
            verdict.readout(dict(R0=[0, 1]), [0, 1])
        with self.assertRaisesRegex(ValueError, 'binary'):
            verdict.readout(outcomes | {'K': [0, .5]}, [0, 1])
        with self.assertRaisesRegex(ValueError, 'shape mismatch'):
            verdict.readout(outcomes | {'K': [0]}, [0, 1])


if __name__ == '__main__':
    unittest.main()
