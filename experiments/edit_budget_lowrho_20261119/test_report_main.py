"""Synthetic checks for the launch-only aggregation glue."""

from itertools import product
import json
import unittest

import numpy as np

import report_main as report


class ReportTest(unittest.TestCase):
    def test_thresholds_from_bounds_preserve_censoring_and_ties(self):
        def bounds(lo, hi=None):
            return report.sweep.Bounds(np.full(5, lo), np.full(5, lo if hi is None else hi))

        pooled = {(rho, arm): bounds(6.) for rho, arm in product(report.RHOS, report.ARMS)}
        pooled[150, 'CD2'] = bounds(10., np.inf)
        pooled[150, 'CD6'] = bounds(7.5)
        # Both arms cross above the observed range, so subtracting the clipped
        # endpoints would falsely identify a zero gain.
        pooled[150, 'A2-2'] = bounds(10., np.inf)
        pooled[150, 'A2-6'] = bounds(10., np.inf)
        pooled[200, 'CD2'] = bounds(6.)
        pooled[200, 'CD6'] = bounds(5.)
        pooled[300, 'CD6'] = bounds(5.)

        result = report.agy_readout(pooled)
        self.assertEqual(result['cd6_gain_thresholds']['150']['point_db'], [2.5, '+inf'])
        self.assertEqual(result['cd6_gain_thresholds']['150']['status'], 'met')
        self.assertEqual(result['cd6_gain_thresholds']['200']['status'], 'met')
        self.assertEqual(result['scalar_minus_cd6_gain']['by_rho']['150']['point_db'], ['-inf', '+inf'])
        self.assertEqual(result['scalar_minus_cd6_gain']['by_rho']['150']['status'], 'unresolved')
        self.assertEqual(result['cd6_optimal_rho']['compatible_rho_permille'], [200, 300])
        self.assertEqual(result['cd6_optimal_rho']['status'], 'unresolved')
        self.assertEqual(result['best_cd6_crossing']['status'], 'missed')

    def test_complete_panel_calls_frozen_primary_and_reports_mechanisms(self):
        frames = tuple(range(8))
        rows = []
        for scenario, rho, snr, frame in product(report.SCENARIOS, report.RHOS, report.SNRS, frames):
            triggered = snr < 800
            errors = {arm: int(triggered) for arm in report.ARMS}
            if rho == 150 and snr in report.SECONDARY_SNRS[150] and frame < 5:
                errors['CD4'] = 0
            if rho == 300 and snr in report.SECONDARY_SNRS[300] and frame < 5:
                errors['CD4'] = 0
            extra = {arm: ([{'step': 3, 'label': 'true_delay'}] if triggered and arm == 'CD4' else [])
                     for arm in report.ARMS}
            mechanisms = {
                arm: dict(cap_exhausted=False, attempted_3_4=len(extra[arm]), accepted_3_4=len(extra[arm]),
                          attempted_5_6=0, accepted_5_6=0, net_true_delay_gain=len(extra[arm]))
                for arm in report.ARMS
            }
            states = {arm: 'fail' if value else 'success' for arm, value in errors.items()}
            rows.append(dict(
                scenario=scenario, rho_permille=rho, snr_centi_db=snr, frame=frame,
                syndrome=int(triggered), triggered=triggered,
                arms={arm: dict(errors=errors[arm], accepted_edits=extra[arm]) for arm in report.ARMS},
                missed_true_delays=[1, 2, 3] if rho == 150 else [1, 2],
                budget_mechanism=mechanisms,
                decoder_transitions={pair: f'{states[left]}_{states[right]}'
                                     for left, right, pair in report.ARM_PAIRS},
            ))

        # A complete primary panel alone cannot bypass the secondary grid check.
        with self.assertRaisesRegex(ValueError, 'Missing 1 grid keys'):
            report.aggregate(rows[:-1], frames)
        result = report.aggregate(iter(rows), frames)
        self.assertEqual(result['primary']['counts'][150]['new_rescues'], 30)
        self.assertEqual(result['primary']['counts'][300]['new_rescues'], 20)
        self.assertEqual(result['secondaries']['astra']['status'], 'undefined')
        self.assertEqual(result['secondaries']['astra']['by_rho']['150']['eligible_frames'], 8)
        self.assertEqual(result['secondaries']['astra']['matched_comparison_status'], 'undefined')
        self.assertEqual(result['secondaries']['claude']['status'], 'missed')
        low = result['secondaries']['mechanism']['150']
        self.assertEqual(low['decoder_transitions']['CD2->CD4']['fail_success'], 30)
        self.assertEqual(low['arms']['CD4']['extra_edits']['3_4']['labels']['true_delay'], low['triggered_keys'])
        self.assertEqual(low['arms']['CD4']['net_true_delay_gain_mean'], 1.0)
        self.assertEqual(result['crossings']['U_150']['F0']['point_db'], [8.0, 8.0])
        result['execution'] = dict(cpu_core_hours=1.25, freeze_commit='frozen',
                                   launch_commit='launched', rows_manifest='ROWS.md5')
        # The text can be regenerated from the archived JSON.
        self.assertEqual(report.render(result), report.render(json.loads(json.dumps(result, allow_nan=False))))


if __name__ == '__main__':
    unittest.main()
