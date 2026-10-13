"""Inference contracts for synthetic scene outcomes, not receiver evidence."""
import copy
import json
from pathlib import Path
import unittest

from .supplement_scene_analysis import analyze_candidates, summarize_candidate_metrics
from .supplement_statistics import paired_delta


ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT/'.mission/20260909_09-01-15-afdm-comprehensive-supplement'


class AnalysisContracts(unittest.TestCase):
    def setUp(self):
        self.freeze = json.loads((MISSION/'evidence/s01-candidate-freeze-v1.json').read_text())
        self.manifest = json.loads((MISSION/'evidence/global-contrast-manifest.json').read_text())
        self.cells = {(b, s, scene, arm): int(arm == 'Bstar' and b < 8)
                      for b in range(192) for s in (7, 8, 9)
                      for scene in ('integer', 'overlap') for arm in self.freeze['physical_arms']}

    def test_complete_candidate_subset_keeps_full_family_and_direction(self):
        result = analyze_candidates(self.cells, self.freeze, self.manifest)
        self.assertEqual(len(result['contrasts']), 168)
        self.assertEqual(len(result['unmeasured_registered_contrasts']), 104)
        row = next(r for r in result['contrasts'] if r['id'] == 'B_star_1-legal_soft@integer_doppler:8')
        self.assertEqual((row['wins'], row['losses'], row['n']), (8, 0, 192))
        self.assertEqual(row['error_counts'], [8, 0])
        self.assertGreater(row['delta'], 0)
        expected = paired_delta(8, 0, 192, m=272)
        self.assertEqual(row['interval'], [float(expected['lower']), float(expected['upper'])])
        self.assertTrue(all(r['m'] == 272 and r['n'] == 192 and
                            not r['independent_confirmation'] for r in result['contrasts']))

    def test_missing_or_extra_cells_are_not_silently_dropped(self):
        key = next(iter(self.cells))
        for mode in ('missing', 'extra'):
            cells = dict(self.cells)
            if mode == 'missing':
                del cells[key]
            else:
                cells[(192, 8, 'integer', 'Bstar')] = 0
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'identity grid'):
                analyze_candidates(cells, self.freeze, self.manifest)

    def test_binary_outcomes_are_required(self):
        key = next(iter(self.cells))
        for invalid in (2, -1, .5, float('nan')):
            cells = dict(self.cells); cells[key] = invalid
            with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, 'binary'):
                analyze_candidates(cells, self.freeze, self.manifest)

    def test_unused_alpha_is_not_recycled(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['families']['F_R']['m_max'] = 168
        with self.assertRaisesRegex(ValueError, 'global reservation'):
            analyze_candidates(self.cells, self.freeze, manifest)

    def test_changed_reference_direction_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        row = next(r for r in manifest['families']['F_R']['contrasts']
                   if r['id'] == 'B_star_1-legal_soft@integer_doppler:8')
        row['coefficients'] = [-1, 1]
        with self.assertRaisesRegex(ValueError, 'reference-minus-candidate'):
            analyze_candidates(self.cells, self.freeze, manifest)


class DiagnosticDenominators(unittest.TestCase):
    def setUp(self):
        self.cells = {(b, 8, 'integer', arm): int(b == 31)
                      for b in range(192) for arm in ('Bstar', 'soft')}
        self.power = {key: key[0] != 191 for key in self.cells}
        self.diagnostics = {
            key: dict(nll=2., brier=.25, nmse=.5, baseline_eligible=True)
            for key in self.cells if key[3] != 'Bstar' or key[0] < 16}

    def test_reused_scores_do_not_expand_terminal_diagnostic_sample(self):
        result = summarize_candidate_metrics(self.cells, self.diagnostics, self.power)
        baseline = result['integer:8:Bstar']
        candidate = result['integer:8:soft']
        self.assertEqual((baseline['n'], baseline['frame_errors']), (192, 1))
        self.assertEqual((baseline['diagnostic_n'], baseline['eligibility_n']), (16, 16))
        self.assertEqual(baseline['diagnostic_blocks'], list(range(16)))
        self.assertEqual((candidate['diagnostic_n'], candidate['eligibility_n']), (192, 192))
        self.assertEqual((baseline['power_n'], baseline['power_violations']), (192, 1))
        self.assertEqual(baseline['mean_channel_nmse'], .5)

    def test_zero_terminal_records_remain_explicitly_unmeasured(self):
        result = summarize_candidate_metrics(self.cells, {}, self.power)
        self.assertEqual(result['integer:8:Bstar']['diagnostic_n'], 0)
        self.assertIsNone(result['integer:8:Bstar']['mean_nll'])
        self.assertIsNone(result['integer:8:Bstar']['ineligible_records'])

    def test_incomplete_power_coverage_cannot_pass(self):
        self.power.pop(next(iter(self.power)))
        with self.assertRaisesRegex(ValueError, 'power.*coverage'):
            summarize_candidate_metrics(self.cells, self.diagnostics, self.power)

    def test_foreign_diagnostic_identity_is_rejected(self):
        self.diagnostics[(192, 8, 'integer', 'Bstar')] = next(iter(self.diagnostics.values()))
        with self.assertRaisesRegex(ValueError, 'diagnostic.*identity'):
            summarize_candidate_metrics(self.cells, self.diagnostics, self.power)


if __name__ == '__main__':
    unittest.main()
