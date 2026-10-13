"""Source-independent contracts for offline cohort derivation."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from derive_cohorts import derive, select_cohort


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture(root: Path) -> None:
    observed, outcomes, truth, ranks, landscapes = [], [], [], [], []
    dossiers = root / "remaining_failure_dossiers"
    dossiers.mkdir()
    for snr in (600, 650, 700):
        for frame in range(4):
            identifier = f"s{snr}_f{frame:04d}"
            failure = snr in (600, 650) and frame == 0
            rescue = snr in (600, 650) and frame == 1
            trigger = failure or rescue
            observed.append(dict(observation_id=identifier, snr_centi_db=snr,
                frame=frame, observation_path=f"observations/{identifier}.npz",
                trigger=trigger, baseline_syndrome_weight=2 if trigger else 0,
                tf_complete_seconds=.3 + frame / 100,
                combined_complete_seconds=.4 + frame / 100,
                cstate_objective_before=10 if trigger else None,
                cstate_objective_after=8 if trigger else None))
            outcomes.append(dict(observation_id=identifier, snr_centi_db=str(snr),
                frame=str(frame), trigger=str(trigger), tf_correct=str(not trigger),
                combined_correct=str(not failure), rescue=str(rescue),
                remaining_triggered_failure=str(failure),
                tf_info_errors="1" if trigger else "0",
                combined_info_errors="1" if failure else "0"))
            truth.append(dict(observation_id=identifier, snr_centi_db=snr,
                true_path_count=1, missing_distinct_delays=[3] if failure else [],
                missing_gain_power_fraction=.5 if failure else 0,
                truth_payload_path=f"truth_payloads/{identifier}.npz"))
            if trigger:
                landscapes.append(dict(observation_id=identifier, step_count=1,
                    objective_before=10, objective_after=8,
                    landscape_path=f"cstate_landscape/{identifier}.npz"))
                ranks.append(dict(observation_id=identifier, global_step=0,
                    true_path_index=0, best_global_rank=30 if failure else 3,
                    missing_or_all_slots_masked=False))
            if failure:
                (dossiers / f"{identifier}.json").write_text(json.dumps(dict(
                    observation_id=identifier,
                    rescued_control_id=f"s{snr}_f0001",
                    easy_control_id=f"s{snr}_f0002",
                    matching_rule="same SNR, observed syndrome, time, ID")))
    write_jsonl(root / "frame_table.jsonl", observed)
    write_csv(root / "frame_outcomes.csv", outcomes)
    write_jsonl(root / "truth_annotations.jsonl", truth)
    write_jsonl(root / "truth_candidate_ranks.jsonl", ranks)
    write_jsonl(root / "cstate_landscape.jsonl", landscapes)


class DeriveCohortsTest(unittest.TestCase):
    def test_complete_cohorts_and_qualified_taxonomy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            fixture(pack)
            summary = derive(pack, expected_per_snr=4,
                             expected_cohorts={"A_remaining_failure": 2,
                                               "B_rescued": 2, "C_easy_success": 8})
            self.assertEqual(summary["fresh_observations"], 12)
            self.assertEqual(summary["trigger_count"], 4)
            with (pack / "fresh_frame_table.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 12)
            self.assertEqual(rows[0]["offline_truth_rank_min_step0"], "30")
            self.assertEqual(rows[0]["offline_physical_missing_reason"],
                             "physical_derivation_not_supplied")
            with (pack / "failure_taxonomy.csv").open(newline="") as stream:
                taxonomy = list(csv.DictReader(stream))
            self.assertEqual(len(taxonomy), 2)
            self.assertEqual(taxonomy[0]["structural_rank_indicator"],
                             "nearest_truth_outside_top20")
            self.assertEqual(taxonomy[0]["exclusive_causal_class"], "unassigned")
            self.assertEqual(taxonomy[0]["in_span_inference_indicator"],
                             "physical_projection_unavailable")
            self.assertEqual(taxonomy[0]["full_class_optimum_unavailable_reason"],
                             "physical_derivation_not_supplied")
            self.assertIn("no significance test", (pack / "cohort_comparison.md").read_text())
            with self.assertRaisesRegex(ValueError, "derived output exists"):
                derive(pack, expected_per_snr=4,
                       expected_cohorts={"A_remaining_failure": 2,
                                         "B_rescued": 2, "C_easy_success": 8})

    def test_optional_physical_join_and_missingness(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            fixture(pack)
            physical = pack / "truth_diagnostics"
            physical.mkdir()
            write_jsonl(physical / "frame_diagnostics.jsonl", [
                dict(observation_id=f"s{snr}_f{frame:04d}",
                     projection_error=float(frame), path_vector=[1, 2],
                     final_selected_geometry_projection_nmse=float(frame),
                     final_saved_gain_operator_mismatch_nmse=(
                         None if snr == 650 and frame == 0 else float(frame) + .5),
                     final_missing_distinct_delay_count=1 if frame == 0 else 0,
                     full_class_optimum_nmse=None,
                     full_class_optimum_unavailable_reason="global bank optimum uncomputed")
                for snr in (600, 650, 700) for frame in range(4)])
            summary = derive(pack, expected_per_snr=4,
                             expected_cohorts={"A_remaining_failure": 2,
                                               "B_rescued": 2, "C_easy_success": 8})
            self.assertEqual(summary["physical_diagnostics"], "complete")
            with (pack / "fresh_frame_table.csv").open(newline="") as stream:
                first = next(csv.DictReader(stream))
            self.assertEqual(first["offline_physical_projection_error"], "0.0")
            self.assertNotIn("offline_physical_path_vector", first)
            self.assertEqual(first["offline_final_saved_gain_excess_nmse"], "0.5")
            with (pack / "failure_taxonomy.csv").open(newline="") as stream:
                taxonomy = list(csv.DictReader(stream))
            self.assertEqual(taxonomy[0]["final_selected_geometry_projection_nmse"], "0.0")
            self.assertEqual(taxonomy[0]["final_saved_gain_operator_mismatch_nmse"], "0.5")
            self.assertEqual(taxonomy[0]["final_saved_gain_excess_nmse"], "0.5")
            self.assertEqual(taxonomy[0]["final_missing_distinct_delay_count"], "1")
            self.assertEqual(taxonomy[0]["in_span_inference_indicator"],
                             "fixed_geometry_projection_and_saved_gain_available")
            self.assertEqual(taxonomy[1]["in_span_inference_indicator"],
                             "fixed_geometry_projection_only_saved_gain_unavailable")
            self.assertEqual(taxonomy[1]["final_saved_gain_excess_nmse"], "")

    def test_rejects_inconsistent_outcome_and_cross_snr_control(self) -> None:
        with self.assertRaisesRegex(ValueError, "remaining-failure label inconsistent"):
            select_cohort(dict(trigger="False", tf_correct="False",
                               combined_correct="False", rescue="False",
                               remaining_triggered_failure="True"))
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            fixture(pack)
            dossier = pack / "remaining_failure_dossiers" / "s600_f0000.json"
            value = json.loads(dossier.read_text())
            value["rescued_control_id"] = "s650_f0001"
            dossier.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "control mismatch"):
                derive(pack, expected_per_snr=4,
                       expected_cohorts={"A_remaining_failure": 2,
                                         "B_rescued": 2, "C_easy_success": 8})


if __name__ == "__main__":
    unittest.main()
