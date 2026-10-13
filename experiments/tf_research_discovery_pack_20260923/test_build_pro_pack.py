"""Focused boundary checks for the compact Pro-facing archive builder."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from build_pro_pack import build, digest


def jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def table(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def fixture(root: Path) -> tuple[Path, Path, Path]:
    cold, pro, brief = root / "COLD_ARCHIVE", root / "PRO_PACK", root / "brief.md"
    cold.mkdir()
    brief.write_text("# Frozen receiver evidence\n")
    (cold / "source_evidence_manifest.json").write_text('{"status":"complete"}\n')
    (cold / "negative_results_ledger.md").write_text("# Negative results\n")
    (cold / "artifact_hashes.json").write_text("{}\n")
    ids = ["s600_f0000", "s600_f0001", "s600_f0002"]
    frames, traces, truths, physical = [], [], [], []
    for cohort, identifier in zip(("A_remaining_failure", "B_rescued", "C_easy_success"), ids):
        paths = {kind: f"{kind}/{identifier}.npz" for kind in
                 ("observations", "tf_traces", "truth_payloads", "cstate_landscape")}
        for kind, name in paths.items():
            if kind == "cstate_landscape" and cohort == "C_easy_success":
                continue
            target = cold / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((identifier + kind).encode())
        frames.append(dict(observation_id=identifier, snr_centi_db=600, cohort=cohort,
            observed_observation_path=paths["observations"],
            observed_tf_trace_path=paths["tf_traces"],
            postseal_truth_payload_path=paths["truth_payloads"],
            observed_cstate_path=paths["cstate_landscape"]
                if cohort != "C_easy_success" else "",
            observed_input_sha256=digest(cold / paths["observations"]),
            observed_baseline_syndrome_weight=4,
            observed_cstate_score_gain="1.0" if cohort != "C_easy_success" else "",
            offline_truth_rank_min_step0="1" if cohort != "C_easy_success" else ""))
        traces.append(dict(observation_id=identifier, trace_path=paths["tf_traces"],
                           trace_sha256=digest(cold / paths["tf_traces"])))
        truths.append(dict(observation_id=identifier,
            truth_payload_path=paths["truth_payloads"],
            source_truth_sha256=digest(cold / paths["truth_payloads"])))
        physical.append(dict(observation_id=identifier, final_missing_distinct_delay_count=0,
                             full_class_optimum_nmse=None))
    table(cold / "fresh_frame_table.csv", frames)
    table(cold / "failure_taxonomy.csv", [dict(observation_id=ids[0],
                                               exclusive_causal_class="unassigned")])
    dossier = cold / "remaining_failure_dossiers" / f"{ids[0]}.json"
    dossier.parent.mkdir()
    dossier.write_text('{"observation_id":"s600_f0000"}\n')
    table(cold / "remaining_failure_index.csv", [dict(observation_id=ids[0],
        rescued_control_id=ids[1], easy_control_id=ids[2],
        dossier_path=str(dossier.relative_to(cold)))])
    jsonl(cold / "tf_traces.jsonl", traces)
    jsonl(cold / "truth_annotations.jsonl", truths)
    jsonl(cold / "truth_diagnostics" / "frame_diagnostics.jsonl", physical)
    landscape = []
    ranks = []
    for identifier in ids[:2]:
        name = f"cstate_landscape/{identifier}.npz"
        landscape.append(dict(observation_id=identifier, step_count=1,
            top_k=[[dict(frozen_score=float(i)) for i in range(20)]],
            accepted=[dict(frozen_score=0.0, decrease=1.0)],
            valid_tests=[10], grid_shapes=[[2, 2575]],
            landscape_path=name, landscape_sha256=digest(cold / name)))
        ranks.append(dict(observation_id=identifier, global_step=0, best_global_rank=1))
    jsonl(cold / "cstate_landscape.jsonl", landscape)
    jsonl(cold / "truth_candidate_ranks.jsonl", ranks)
    return cold, pro, brief


class BuildProPackTest(unittest.TestCase):
    def test_compact_pack_keeps_raw_objects_in_cold_archive(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cold, pro, brief = fixture(Path(folder))
            result = build(cold, pro, brief, expected_frames=3,
                           expected_failures=1, expected_triggers=2)
            self.assertEqual(result["file_count"], 9)
            self.assertTrue(result["size_target_met"])
            self.assertEqual(json.loads((pro / "manifest.json").read_text())["package_bytes"],
                             sum(path.stat().st_size for path in pro.iterdir()))
            self.assertFalse(any(path.suffix == ".npz" for path in pro.iterdir()))
            with (pro / "02_frame_table.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["cold_tf_trace_sha256"],
                             digest(cold / rows[0]["observed_tf_trace_path"]))
            with (pro / "03_cstate_landscape_summary.csv").open(newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 2)
            self.assertIn("COLD_ARCHIVE/", (pro / "07_evidence_index.md").read_text())

    def test_missing_truth_ranks_fail_before_output_creation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cold, pro, brief = fixture(Path(folder))
            (cold / "truth_candidate_ranks.jsonl").write_text("")
            with self.assertRaisesRegex(ValueError, "truth ranks missing"):
                build(cold, pro, brief, expected_frames=3,
                      expected_failures=1, expected_triggers=2)
            self.assertFalse(pro.exists())

    def test_remote_cold_location_and_single_artifact_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cold, pro, brief = fixture(Path(folder))
            location = "deinlab:/data/guoyikun/research/COLD_ARCHIVE"
            result = build(cold, pro, brief, expected_frames=3,
                           expected_failures=1, expected_triggers=2,
                           cold_location=location)
            self.assertEqual(result["cold_location"], location)
            self.assertIsNone(result["cold_archive_relative_to_pack_parent"])
            index = (pro / "07_evidence_index.md").read_text()
            self.assertIn("scp -o BatchMode=yes 'deinlab:/data/guoyikun/research/"
                          "COLD_ARCHIVE/observations/s600_f0000.npz' .", index)

    def test_unsafe_remote_location_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            cold, pro, brief = fixture(Path(folder))
            with self.assertRaisesRegex(ValueError, "cold location"):
                build(cold, pro, brief, expected_frames=3,
                      expected_failures=1, expected_triggers=2,
                      cold_location="deinlab:/data/../not-the-archive")
            self.assertFalse(pro.exists())


if __name__ == "__main__":
    unittest.main()
