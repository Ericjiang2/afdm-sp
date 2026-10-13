"""Contracts for development reanalysis; no receiver simulations."""
import copy
import json
import os
from pathlib import Path
import unittest

from .supplement_development_analysis import analyze_development, arm_map


MANIFEST_PATH = Path(os.environ.get('AFDM_TEST_CONTRAST_MANIFEST', str(
    Path(__file__).resolve().parents[1] / '.mission' /
    '20260909_09-01-15-afdm-comprehensive-supplement/evidence/global-contrast-manifest.json')))
MANIFEST = json.loads(MANIFEST_PATH.read_text())


def table_for(stage, n=16):
    return {(snr, raw): [0] * n for snr in (7, 8, 9)
            for raw in arm_map(stage, ('BP', 'BP80')).values()}


class DevelopmentAnalysisTests(unittest.TestCase):
    def analyze(self, stage, table, n=16):
        return analyze_development(stage, table, ('BP', 'BP80'), list(range(n)), MANIFEST)

    def test_full_registered_stage_coverage_and_reserved_alpha(self):
        for stage, count, m in [('H-01', 63, 63), ('M-01', 24, 24),
                                 ('A-01', 396, 441), ('I-02', 18, 66)]:
            with self.subTest(stage=stage):
                rows = self.analyze(stage, table_for(stage))
                self.assertEqual(len(rows), count)
                self.assertTrue(all(r['m'] == m for r in rows))
                self.assertTrue(all(r['alpha_family'] == .05 / 7 for r in rows))
                self.assertTrue(all(r['independent_confirmation'] is False for r in rows))
                self.assertTrue(all(r['n'] == 16 for r in rows))

    def test_improvement_direction_and_win_loss_counts(self):
        table = table_for('H-01', 4)
        table[(8, 'cancel_estimated__data_estimated__BP')] = [1, 1, 0, 0]
        rows = self.analyze('H-01', table, 4)
        row = next(r for r in rows if r['id'] == 'BP:C|D0@nominal:8')
        self.assertEqual((row['delta'], row['wins'], row['losses']), (.5, 2, 0))
        self.assertEqual(row['error_counts'], [2, 0])
        self.assertEqual(row['arms'], ['BP:C0D0', 'BP:C1D0'])

    def test_joint_interactions_use_all_frozen_coefficients(self):
        table = table_for('H-01', 4)
        table[(8, 'cancel_estimated__data_estimated__BP')] = [1, 1, 0, 0]
        table[(8, 'cancel_true__data_estimated__BP')] = [0, 1, 0, 0]
        row = next(r for r in self.analyze('H-01', table, 4)
                   if r['id'] == 'CxDxdet@nominal:8')
        self.assertEqual(row['delta'], .25)
        self.assertEqual(len(row['coefficients']), 8)
        self.assertEqual(row['method'], 'linear_CP')
        self.assertNotIn('wins', row)

    def test_zero_discordance_does_not_collapse_uncertainty(self):
        row = self.analyze('I-02', table_for('I-02'))[0]
        self.assertEqual((row['wins'], row['losses'], row['delta']), (0, 0, 0))
        self.assertLess(row['interval'][0], -.01)
        self.assertGreater(row['interval'][1], .01)

    def test_missing_cell_and_duplicate_blocks_are_rejected(self):
        table = table_for('M-01')
        del table[(9, 'link__BP80')]
        with self.assertRaisesRegex(ValueError, 'cell'):
            self.analyze('M-01', table)
        with self.assertRaisesRegex(ValueError, 'block'):
            analyze_development('H-01', table_for('H-01'), ('BP', 'BP80'), [0] * 16, MANIFEST)

    def test_global_manifest_cannot_silently_drop_contrasts(self):
        changed = copy.deepcopy(MANIFEST)
        changed['families']['F_H']['contrasts'].pop()
        with self.assertRaisesRegex(ValueError, 'manifest'):
            analyze_development('H-01', table_for('H-01'), ('BP', 'BP80'), list(range(16)), changed)


if __name__ == '__main__':
    unittest.main()
