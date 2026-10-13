"""Synthetic/offline Part-B analysis contracts; no receiver calls."""
import unittest

import numpy as np

from analyze import (PRIMARY, SNRS, bootstrap_subset, circular_block_indices,
                     classify_primary, cp_lower, cp_upper, decision_error,
                     expected_coordinates, paired_counts)


CONTRACT = {"reliability_tolerances": {"600": .02, "650": .02, "700": .01},
            "latency_bootstrap": {"subset_block_frames":
                {"primary_1024": 32, "POINT_128": 16, "PBi_32": 4}}}


class PartBAnalysisContracts(unittest.TestCase):
    def test_allocation_fixed_subsets(self):
        coordinates = list(expected_coordinates())
        self.assertEqual(len(coordinates), 9696)
        self.assertEqual(len(set(coordinates)), 9696)
        self.assertIn((600, 127, "TF_POINT20_R2"), coordinates)
        self.assertNotIn((600, 128, "TF_POINT20_R2"), coordinates)
        self.assertIn((700, 31, "PBI8_SOFT_R2"), coordinates)
        self.assertNotIn((700, 32, "PBI8_SOFT_R2"), coordinates)

    def test_exact_zero_all_and_discordance(self):
        tail = .05/12
        self.assertEqual(cp_lower(0, 1024, tail), 0)
        self.assertGreater(cp_upper(0, 1024, tail), 0)
        self.assertEqual(cp_upper(1024, 1024, tail), 1)
        self.assertLess(cp_lower(1024, 1024, tail), 1)
        no_discordance = paired_counts([False]*1024, [False]*1024, primary=True)
        self.assertEqual(no_discordance["delta_fer_TF_minus_comparator"], 0)
        self.assertGreater(no_discordance["upper_excess_fer_six_upper_family"], 0)
        discordance = paired_counts([True, False, True, False],
                                    [False, True, True, False], primary=True)
        self.assertEqual(discordance["harm_TF_wrong_comparator_correct"], 1)
        self.assertEqual(discordance["rescue_TF_correct_comparator_wrong"], 1)
        self.assertEqual(discordance["both_wrong"], 1)
        self.assertEqual(discordance["both_correct"], 1)
        subset = paired_counts([True, False], [False, True], primary=False)
        self.assertEqual(subset["upper_excess_fer_six_upper_family"], "")

    def test_latest_completed_checkpoint_and_deadline(self):
        row = {"status": "numerical_failure", "seconds": 9.,
               "checkpoints": [{"ready": 3., "info_errors": 0},
                               {"ready": 7., "info_errors": 4}]}
        self.assertEqual(decision_error(row), 1)
        self.assertEqual(decision_error(row, 3.), 0)
        self.assertEqual(decision_error(row, 6.), 0)
        self.assertEqual(decision_error(row, 7.), 1)
        self.assertEqual(decision_error(row, 2.99), 1)
        self.assertEqual(decision_error({"checkpoints": []}), 1)

    def test_circular_subset_blocks_are_not_whole_sample_permutations(self):
        rng = np.random.default_rng(941002)
        indices = circular_block_indices(32, 4, rng)
        self.assertEqual(len(indices), 32)
        self.assertTrue(np.all(indices >= 0))
        self.assertTrue(np.all(indices < 32))
        for offset in range(0, 32, 4):
            self.assertTrue(np.all(indices[offset+1:offset+4] ==
                                   (indices[offset:offset+3]+1) % 32))
        self.assertLess(len(set(indices)), 32)

    def test_subset_bootstrap_non_degenerate_and_registered_blocks(self):
        tf = np.linspace(.4, .7, 32)
        other = np.linspace(.65, .85, 32)[::-1]
        result = bootstrap_subset(tf, other, 650, "PBI8_SOFT_R2", CONTRACT)
        bounds = result["ratio_of_medians"]
        self.assertLess(bounds["percentile_2_5"], bounds["percentile_97_5"])
        self.assertIn(("TF_J20_R2", "median_seconds"), result)
        self.assertIn(("PBI8_SOFT_R2", "p95_seconds"), result)
        with self.assertRaises(ValueError):
            bad = {"latency_bootstrap": {"subset_block_frames":
                {"primary_1024": 32, "POINT_128": 16, "PBi_32": 32}}}
            bootstrap_subset(tf, other, 650, "PBI8_SOFT_R2", bad)

    def test_supported_falsified_and_inconclusive_are_distinct(self):
        rows = []
        for snr in SNRS:
            for comparator in PRIMARY[1:]:
                rows.append({"snr_centi_db": snr, "comparator": comparator,
                    "upper_excess_fer_six_upper_family": -.01,
                    "lower_excess_fer_separate_six_lower_family": -.03,
                    "median_ratio_bootstrap_upper95": .7,
                    "median_ratio_bootstrap_lower5": .6,
                    "ratio_of_p90_seconds": .9,
                    "p90_ratio_bootstrap_lower5": .8})
        self.assertEqual(classify_primary(rows, CONTRACT)[0], "supported")
        rows[0]["upper_excess_fer_six_upper_family"] = .03
        self.assertEqual(classify_primary(rows, CONTRACT)[0], "inconclusive")
        rows[0]["lower_excess_fer_separate_six_lower_family"] = .021
        self.assertEqual(classify_primary(rows, CONTRACT)[0], "falsified")


if __name__ == "__main__":
    unittest.main()
