"""Synthetic complete panels and threshold tests for the primary verdict."""

from itertools import product
import json
import unittest

import primary as verdict


def interval(lo, hi):
    return dict(evaluable=lo is not None and hi is not None, ci_lo=lo, ci_hi=hi)


def synthetic_rows(frames, case):
    rows = []
    for rho, snrs in verdict.PRIMARY_SNRS.items():
        cells = tuple(enumerate(product(verdict.SCENARIOS, snrs)))
        for frame, (cell, (scenario, snr)) in product(frames, cells):
            triggered, errors2, errors4 = case(frame, rho, cell)
            rows.append(dict(scenario=scenario, rho_permille=rho, snr_centi_db=snr, frame=frame,
                             triggered=triggered, syndrome=3 if triggered else 0,
                             arms=dict(CD2=dict(errors=errors2), CD4=dict(errors=errors4))))
    return rows


class VerdictTest(unittest.TestCase):
    def test_independent_rules_and_thresholds(self):
        for gain, matched, did, expected in (
            ((.03, .08), (-.03, .03), (.01, .06), ('supported', 'meaningful', 'unchanged')),
            ((.01, .02), (-.01, .01), (.01, .03), ('supported', 'not_meaningful', 'unchanged')),
            ((0, .03), (-.031, .03), (.01, .02), ('not_supported', 'uncertain', 'not_established')),
            ((.01, .04), (-.03, .031), (0, .03), ('not_supported', 'uncertain', 'not_established')),
            ((.03, .04), (None, None), (None, None), ('unresolved', 'meaningful', 'unresolved')),
            ((None, None), (-.01, .01), (None, None), ('unresolved', 'unresolved', 'unchanged')),
            ((.03, .04), (-.01, .01), (None, None), ('unresolved', 'meaningful', 'unchanged')),
            ((None, None), (None, None), (None, None), ('unresolved', 'unresolved', 'unresolved')),
        ):
            with self.subTest(gain=gain, matched=matched, did=did):
                result = verdict.classify(interval(*gain), interval(*matched), interval(*did))
                self.assertEqual(result, dict(zip(('direction', 'practical_size', 'matched_30'), expected)))

    def test_support_and_equivalence_from_complete_matched_panel(self):
        frames = range(5)

        def case(frame, rho, cell):
            if rho == 150 or cell == 0:
                return True, 1, 0
            if cell == 1:
                return True, 0, 1
            return True, 0, 0

        rows = synthetic_rows(frames, case)
        # These old-control and secondary rows lie outside the primary panel.
        rows.extend([rows[0] | dict(rho_permille=300, snr_centi_db=600),
                     rows[0] | dict(rho_permille=150, snr_centi_db=450),
                     rows[0] | dict(rho_permille=200)])
        result = verdict.readout(rows, frames)
        self.assertEqual(result['n_frame_clusters'], 5)
        self.assertEqual(result['counts'][150]['keys'], 40)
        self.assertEqual(result['counts'][300]['keys'], 20)
        self.assertEqual(result['counts'][300]['snrs_centi_db'], (450, 500))
        self.assertEqual(result['counts'][300]['discordant_frames'], 5)
        self.assertEqual(result['counts'][300]['new_rescues'], 5)
        self.assertEqual(result['counts'][300]['new_harms'], 5)
        self.assertEqual(result['gain'][300]['point'], 0)
        self.assertEqual(result['direction'], 'supported')
        self.assertEqual(result['practical_size'], 'meaningful')
        self.assertEqual(result['matched_30'], 'unchanged')
        self.assertEqual(result['bootstrap']['draws'], 20_000)
        self.assertEqual(result['bootstrap']['seed'], 20261125)
        json.dumps(result, allow_nan=False)

    def test_bootstrap_pairs_all_cells_and_both_rhos(self):
        frames = range(6)
        # Every resample gives the same gains in the two rho panels. Odd frames
        # worsen while even frames improve, and every key in each frame agrees.
        rows = synthetic_rows(frames, lambda f, rho, c: (True, int(f % 2 == 0), int(f % 2 != 0)))
        result = verdict.readout(rows, frames)
        self.assertEqual(result, verdict.readout(reversed(rows), reversed(frames)))
        self.assertEqual(result['gain'][150]['point'], 0)
        self.assertAlmostEqual(result['gain'][150]['ci_lo'], -2 / 3)
        self.assertAlmostEqual(result['gain'][150]['ci_hi'], 2 / 3)
        self.assertEqual(result['did']['ci_lo'], 0)
        self.assertEqual(result['did']['ci_hi'], 0)
        self.assertEqual(result['direction'], 'not_supported')
        self.assertEqual(result['practical_size'], 'uncertain')
        self.assertEqual(result['matched_30'], 'not_established')
        self.assertEqual(result['counts'][150]['new_harms'], 24)
        self.assertEqual(result['counts'][150]['new_rescues'], 24)

    def test_each_draw_reweighs_pooled_trigger_denominator(self):
        frames = range(8)

        def case(frame, rho, cell):
            if rho == 300:
                return True, 1, 0
            if frame % 2 == 0:
                return cell == 0, 1, 0
            return True, 0, 1

        result = verdict.readout(synthetic_rows(frames, case), frames)
        self.assertEqual(result['gain'][150]['point'], -7 / 9)
        self.assertEqual(result['did']['point'], -7 / 9 - 1)
        # The tails contain one of eight or seven of eight improving frames.
        self.assertAlmostEqual(result['gain'][150]['ci_lo'], -55 / 57)
        self.assertAlmostEqual(result['gain'][150]['ci_hi'], -1 / 15)
        self.assertEqual(result['practical_size'], 'not_meaningful')
        self.assertEqual(result['counts'][150], dict(
            snrs_centi_db=(600, 650, 700, 800), keys=64, triggered=36, triggered_frames=8,
            discordant_frames=8, rescued_cd2=32, rescued_cd4=4, new_rescues=4, new_harms=32,
        ))

    def test_rare_group_suppresses_its_bounds_and_dependent_labels(self):
        frames = range(8)
        for rare_rho in (150, 300):
            with self.subTest(rare_rho=rare_rho):
                rows = synthetic_rows(frames, lambda f, rho, c: (True, int(f < 4 or rho != rare_rho), 0))
                result = verdict.readout(rows, frames)
                self.assertGreater(result['counts'][rare_rho]['new_rescues'], 5)
                self.assertEqual(result['counts'][rare_rho]['discordant_frames'], 4)
                self.assertIsNone(result['gain'][rare_rho]['ci_lo'])
                self.assertIsNone(result['did']['ci_hi'])
                self.assertEqual(result['direction'], 'unresolved')
                if rare_rho == 150:
                    self.assertEqual(result['practical_size'], 'unresolved')
                    self.assertEqual(result['matched_30'], 'not_established')
                else:
                    self.assertEqual(result['practical_size'], 'meaningful')
                    self.assertEqual(result['matched_30'], 'unresolved')

    def test_undefined_draws_use_joint_mask_for_did(self):
        frames = range(128)
        rows = synthetic_rows(frames, lambda f, rho, c: (f < 5 if rho == 150 else f >= 123, 1, 0))
        result = verdict.readout(rows, frames)
        for gain in result['gain'].values():
            self.assertTrue(gain['evaluable'])
            self.assertGreater(gain['undefined_fraction'], 0)
        self.assertGreater(result['did']['undefined_fraction'], verdict.FAILURE_LIMIT)
        self.assertFalse(result['did']['evaluable'])
        self.assertEqual(result['did']['point'], 0)
        self.assertIsNone(result['did']['ci_hi'])
        self.assertEqual(result['direction'], 'unresolved')

    def test_no_observed_trigger_has_no_estimate(self):
        frames = range(5)
        rows = synthetic_rows(frames, lambda f, rho, c: (rho == 300, 1, 0))
        result = verdict.readout(rows, frames)
        self.assertEqual(result['direction'], 'unresolved')
        for contrast in (result['gain'][150], result['did']):
            self.assertFalse(contrast['evaluable'])
            self.assertEqual(contrast['undefined_fraction'], 1)
            self.assertIsNone(contrast['point'])
            self.assertIsNone(contrast['ci_lo'])
        json.dumps(result, allow_nan=False)

    def test_incomplete_duplicate_or_invalid_primary_inputs_fail(self):
        frames = (123,)
        rows = synthetic_rows(frames, lambda f, rho, c: (True, 0, 0))
        for changed, expected_error in (
            (rows[1:], 'Missing 1 primary rows'),
            (rows + [rows[0]], 'Duplicate or unexpected'),
            (rows + [rows[0] | dict(frame=124)], 'Duplicate or unexpected'),
            ([rows[0] | dict(triggered=False)] + rows[1:], 'Invalid trigger'),
            ([rows[0] | dict(arms=dict(CD2=dict(errors=-1), CD4=dict(errors=0)))] + rows[1:],
             'Invalid decoder error count'),
        ):
            with self.subTest(expected_error=expected_error):
                with self.assertRaisesRegex(ValueError, expected_error):
                    verdict.readout(changed, frames)
        with self.assertRaisesRegex(ValueError, 'distinct registered physical frame IDs'):
            verdict.readout(rows, frames + frames)


if __name__ == '__main__':
    unittest.main()
