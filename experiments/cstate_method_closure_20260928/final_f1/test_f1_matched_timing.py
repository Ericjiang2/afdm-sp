"""No-receiver checks for the fixed timing allocation and evidence gate."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
import unittest

import f1_matched_timing as subject
import analyze_matched_timing as reader


PROJECT = Path(__file__).resolve().parents[3]
STAGE_A = PROJECT / "results/cstate_necessity_stageA_20260928"
COMPAT = PROJECT / "results/cstate_necessity_stageB_resume_20260928"


class MatchedTimingTest(unittest.TestCase):
    def test_offline_summary_uses_paired_fixed_ids(self) -> None:
        rows = []
        for ordinal, frame in enumerate(range(0, 1024, 16)):
            for arm in subject.schedule(ordinal):
                acquisition = {"F0": .1, "Cref": .4, "Ccompat": .3}[arm]
                row = dict(observation_id=f"s650_f{frame:04d}", arm=arm,
                           status="ok", triggered=False, reference_max_difference=0.0,
                           acquisition_seconds=acquisition,
                           complete_latency_seconds=acquisition + .4,
                           native_seconds=acquisition + .2,
                           refit_seconds=.1, tf_seconds=.04, decoder_seconds=.04,
                           raw_serialization_seconds=.02, decision_record_seconds=.01)
                rows.append(row)
        report = reader.summarize(rows)
        self.assertEqual(report["paid_calls"], 192)
        self.assertAlmostEqual(report["removable_acquisition_fraction"], 1/3)
        self.assertAlmostEqual(report["remaining_measured_acquisition_fraction"], 2/3)
        self.assertFalse(report["legacy_operational_python_bound_rule"])
        rows[0], rows[1] = rows[1], rows[0]
        with self.assertRaisesRegex(ValueError, "allocation"):
            reader.summarize(rows)

    def test_call_timer_covers_attempt_reservation_and_campaign_remainder(self) -> None:
        self.assertAlmostEqual(subject.call_allowance(10.0, 0.0, 39.75), 0.25)
        self.assertAlmostEqual(subject.call_allowance(895.0, 0.0, 899.75), 0.25)
        with self.assertRaises(TimeoutError):
            subject.call_allowance(10.0, 0.0, 40.0)
        with self.assertRaises(TimeoutError):
            subject.call_allowance(895.0, 0.0, 900.0)

    def test_fixed_64_three_arm_balance(self) -> None:
        orders = [subject.schedule(i) for i in range(64)]
        self.assertEqual(sum(map(len, orders)), 192)
        self.assertTrue(all(set(order) == set(subject.ARMS) for order in orders))
        self.assertEqual(Counter(arm for order in orders for arm in order),
                         Counter({arm: 64 for arm in subject.ARMS}))
        for position in range(3):
            counts = Counter(order[position] for order in orders)
            self.assertLessEqual(max(counts.values()) - min(counts.values()), 2)
        with self.assertRaises(ValueError):
            subject.schedule(64)

    def test_full_population_gate_and_malformed_independent_receipt(self) -> None:
        # Synthetic independent receipt exercises parser rejection only; it is
        # not a substitute for the separate raw-to-raw audit before real calls.
        old_receipt = COMPAT / "F1_FAST_EQUIVALENCE_RECEIPT.json"
        old_observed = COMPAT / "observed_f1_compat_v1"
        old_registration = COMPAT / "F1_COMPAT_MANIFEST.json"
        stage_a_observed = STAGE_A / "observed"
        stage_a_registration = STAGE_A / "EXPERIMENT_MANIFEST.json"
        independent = dict(
            schema="f1-ccompat-stagea-raw-equivalence-recount/1", status="pass", n=1024,
            counts={key: 1024 for key in (
                "frames_compared", "frames_exact_discrete_pass",
                "frames_continuous_tolerance_pass", "frames_final_decoded_exact_pass",
                "raw_files_rehashed_per_side")},
            all_exact_discrete_pass=True, all_within_tolerance_pass=True,
            all_final_decoded_exact_pass=True,
            first_mismatch_observation_ids=[], mismatch_observation_ids=[], mismatch_count=0,
            receiver_calls=0, decoder_calls=0, truth_reads=0,
            stage_a_observed_seal_sha256=subject.sha256(stage_a_observed / "observed_seal.json"),
            ccompat_observed_seal_sha256=subject.sha256(old_observed / "observed_seal.json"),
            stage_a_registration_sha256=subject.sha256(stage_a_registration),
            ccompat_registration_sha256=subject.sha256(old_registration),
            contract=dict(continuous_atol=2e-10, continuous_rtol=0,
                          final_bits="exact numpy.array_equal",
                          reference_fields=list(subject.legacy.REFERENCE_FIELDS)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic_independent_receipt.json"
            args = argparse.Namespace(
                compat_registration=old_registration, compat_observed=old_observed,
                compat_equivalence_receipt=old_receipt, independent_rehash_receipt=path,
                stage_a_observed=stage_a_observed, stage_a_registration=stage_a_registration)
            registration = dict(
                compat_registration_sha256=subject.sha256(old_registration),
                compat_observed_seal_sha256=subject.sha256(old_observed / "observed_seal.json"),
                compat_equivalence_receipt_sha256=subject.sha256(old_receipt))

            def check() -> dict:
                path.write_text(json.dumps(independent))
                registration["independent_rehash_receipt_sha256"] = subject.sha256(path)
                return subject.verify_full_equivalence(args, registration)

            self.assertEqual(check()["producer_checked_fast_calls"], 1024)
            independent["mismatch_count"] = 1
            with self.assertRaisesRegex(ValueError, "independent full F1"):
                check()
            independent["mismatch_count"] = 0
            independent["contract"]["continuous_atol"] = 3e-10
            with self.assertRaisesRegex(ValueError, "comparison contract"):
                check()


if __name__ == "__main__":
    unittest.main()
