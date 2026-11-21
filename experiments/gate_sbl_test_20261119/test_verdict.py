import unittest

import numpy as np

from gate_verdict import X_MARGIN, _joint_verdict, _x_verdict, paired_interval, readout, s_leg, x_leg


class VerdictTest(unittest.TestCase):
    def test_physical_frame_clusters_and_pooled_key_mean(self):
        result = paired_interval([1, 0, 0, 0], ['a', 'b', 'b', 'b'])
        self.assertEqual(result, paired_interval([0, 1, 0, 0], ['b', 'a', 'b', 'b']))
        self.assertEqual(result['n_frame_clusters'], 2)
        self.assertEqual(result['bootstrap'], {'draws': 20_000, 'seed': 20261123})
        self.assertEqual((result['ci_lo'], result['point'], result['ci_hi']), (0., .25, 1.))

    def test_s_pass_and_sign_annotations(self):
        pass_with_benefit = s_leg([0, 0], [1, 1], [10, 11], [False, False])
        self.assertEqual(pass_with_benefit['verdict'], 'pass')
        self.assertTrue(pass_with_benefit['upper_negative'])
        self.assertFalse(pass_with_benefit['lower_positive'])

        why_sign_matters = s_leg([1] + [0] * 199, [0] * 200, [10] * 200, [False] * 200)
        self.assertEqual(why_sign_matters['verdict'], 'pass')
        self.assertTrue(why_sign_matters['lower_positive'])

    def test_s_fail(self):
        result = s_leg([1, 1], [0, 0], [10, 11], [False, False])
        self.assertEqual(result['verdict'], 'fail')
        self.assertTrue(result['lower_positive'])
        self.assertFalse(result['upper_negative'])

    def test_s_uncertain_when_ci_straddles_margin_or_touches_it(self):
        result = s_leg([1, 0], [0, 0], [10, 11], [False, False])
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertFalse(result['lower_positive'])
        self.assertFalse(result['upper_negative'])
        on_margin = s_leg([1] + [0] * 99, [0] * 100, [10] * 100, [False] * 100)
        self.assertEqual(on_margin['ci_lo'], on_margin['margin'])
        self.assertEqual(on_margin['ci_hi'], on_margin['margin'])
        self.assertEqual(on_margin['verdict'], 'uncertain')
        self.assertTrue(on_margin['equivalent'])

    def test_equivalence_is_inclusive_and_secondary(self):
        frames = [10] * 100
        different = [False] * 100
        no_errors = [0] * 100
        at_negative_margin = s_leg(no_errors, [1] + [0] * 99, frames, different)
        self.assertEqual(at_negative_margin['ci_lo'], -at_negative_margin['margin'])
        self.assertTrue(at_negative_margin['equivalent'])
        self.assertEqual(at_negative_margin['verdict'], 'pass')
        beyond_negative_margin = s_leg(no_errors, [1, 1] + [0] * 98, frames, different)
        self.assertFalse(beyond_negative_margin['equivalent'])
        self.assertEqual(beyond_negative_margin['verdict'], 'pass')
        invalid = readout([0], [0], [10], [True], [True] * 74, [True] * 74)
        self.assertTrue(invalid['s_leg']['equivalent'])
        self.assertEqual(invalid['s_leg']['verdict'], 'uninformative')
        self.assertEqual(invalid['joint'], 'uncertain')

    def test_s_strict_validity_boundary_overrides_ci(self):
        frame_ids = np.arange(100)
        valid = s_leg(np.zeros(100), np.zeros(100), frame_ids, frame_ids < 95)
        invalid = s_leg(np.zeros(100), np.ones(100), frame_ids, frame_ids < 96)
        self.assertEqual(valid['same_projector_fraction'], .95)
        self.assertTrue(valid['valid'])
        self.assertEqual(valid['verdict'], 'pass')
        self.assertFalse(invalid['valid'])
        self.assertEqual(invalid['verdict'], 'uninformative')
        self.assertTrue(invalid['upper_negative'])

    def test_x_pass_and_denominator_filters(self):
        cd = [True] * 74 + [False, False]
        gate = [True] * 74 + [False, True]
        result = x_leg(cd, gate)
        self.assertEqual((result['cd_resolved_frames'], result['lost_frames']), (74, 0))
        self.assertEqual(result['ci_lo'], 0.)
        self.assertAlmostEqual(result['ci_hi'], 1 - .025 ** (1 / 74))
        self.assertEqual(result['verdict'], 'pass')
        self.assertFalse(result['leverage_insufficient'])

    def test_x_fail_with_complete_loss_even_when_leverage_is_insufficient(self):
        result = x_leg([True] * 2, [False] * 2)
        self.assertEqual(result['verdict'], 'fail')
        self.assertEqual(result['ci_hi'], 1.)
        self.assertAlmostEqual(result['ci_lo'], .025 ** .5)
        self.assertTrue(result['leverage_insufficient'])

    def test_x_nonextreme_loss_and_margin_ties(self):
        result = x_leg([True] * 74, [True] * 73 + [False])
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertGreater(result['ci_lo'], 0)
        self.assertLess(result['ci_lo'], result['margin'])
        self.assertGreater(result['ci_hi'], result['margin'])
        self.assertLess(result['ci_hi'], 1)
        self.assertEqual(_x_verdict(0., X_MARGIN, True), 'uncertain')
        self.assertEqual(_x_verdict(X_MARGIN, 1., True), 'fail')

    def test_x_zero_denominator_and_registered_leverage_cutoff(self):
        result = x_leg([False, False], [False, True])
        self.assertIsNone(result['point'])
        self.assertIsNone(result['ci_lo'])
        self.assertIsNone(result['ci_hi'])
        self.assertEqual(result['verdict'], 'uncertain')
        self.assertTrue(result['leverage_insufficient'])

        for n in (72, 73):
            with self.subTest(n=n):
                result = x_leg([True] * n, [True] * n)
                self.assertLess(result['ci_hi'], X_MARGIN)
                self.assertTrue(result['leverage_insufficient'])
                self.assertEqual(result['verdict'], 'uncertain')

    def test_joint_pass_failure_and_uncertainty(self):
        result = readout([0], [0], [10], [False], [True] * 74, [True] * 74)
        self.assertEqual(result['s_leg']['verdict'], 'pass')
        self.assertEqual(result['x_leg']['verdict'], 'pass')
        self.assertEqual(result['joint'], 'supported')
        self.assertEqual(_joint_verdict('fail', 'pass'), 'not_supported')
        self.assertEqual(_joint_verdict('uninformative', 'fail'), 'not_supported')
        self.assertEqual(_joint_verdict('pass', 'uncertain'), 'uncertain')
        self.assertEqual(_joint_verdict('uninformative', 'pass'), 'uncertain')
        self.assertEqual(_joint_verdict('uncertain', 'pass'), 'uncertain')

    def test_incomplete_or_nonbinary_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            s_leg([1], [0, 1], [10], [False])
        with self.assertRaises(ValueError):
            s_leg([1], [0], [10], [None])
        with self.assertRaises(ValueError):
            s_leg([1], [0], [10, 11], [False])
        with self.assertRaises(ValueError):
            x_leg([True], [True, True])
        with self.assertRaises(ValueError):
            x_leg([np.nan], [True])


if __name__ == '__main__':
    unittest.main()
