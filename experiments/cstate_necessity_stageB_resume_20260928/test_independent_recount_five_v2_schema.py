"""Offline schema regression against the frozen five-policy primary summaries."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results/cstate_necessity_stageB_resume_20260928"
READER = Path(__file__).with_name("independent_recount_five_v2.py")
POLICIES = ("F0", "B", "F0_LOCAL", "F2T", "F2E")
REPORT_SHA256 = "dbc93d3df5b40e8ee16b7323da413df5c7e659801defda3b6fdf1ac76f729c16"
SUBGROUP_SHA256 = "a34991980a492608a731b71319344f2569f1d006da6539dc6e6f06d215e6dd26"
DISTRIBUTION_KEYS = {"n", "mean", "median", "p95", "p99", "max"}


def frozen_json(path: Path, digest: str) -> dict:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"frozen summary digest changed: {path}")
    return json.loads(data)


def load_schema_reader():
    # The local Python lacks NumPy; execute only the pure schema accessor under test.
    tree = ast.parse(READER.read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name == "primary_complete_latency"]
    if len(nodes) != 1:
        raise ValueError("expected exactly one primary timing schema accessor")
    namespace: dict = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(READER), "exec"), namespace)
    return namespace["primary_complete_latency"]


class FrozenSummarySchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = frozen_json(RESULTS / "population_five_analysis_v2/report.json", REPORT_SHA256)
        cls.subgroup = frozen_json(RESULTS / "population_five_subgroup_v2.json", SUBGROUP_SHA256)
        cls.primary_complete_latency = staticmethod(load_schema_reader())

    def test_complete_latency_is_named_distribution(self) -> None:
        arms = self.report["summary"]["arms"]
        self.assertEqual(set(arms), set(POLICIES))
        for policy in POLICIES:
            with self.subTest(policy=policy):
                arm = arms[policy]
                with self.assertRaises(KeyError):
                    _ = arm["timing"]["mean"]  # The v1 access that stopped at line 551.
                values = self.primary_complete_latency(arm)
                self.assertEqual(set(values), DISTRIBUTION_KEYS)
                self.assertEqual(values["n"], 1024)
                for key in DISTRIBUTION_KEYS - {"n"}:
                    self.assertIsInstance(values[key], (int, float))

    def test_every_planned_primary_summary_access(self) -> None:
        summary = self.report["summary"]
        for policy in POLICIES:
            with self.subTest(policy=policy):
                arm = summary["arms"][policy]
                for field in ("n", "information_failures", "information_FER", "coded_bit_errors",
                              "coded_BER", "syndrome_nonzero", "valid_but_wrong",
                              "triggered_prefix_nonzero", "executed_branch_n"):
                    self.assertIsInstance(arm[field], (int, float))
                for deadline in ("0.5", "1.0"):
                    for field in ("n", "correct", "wrong_ready", "missing"):
                        self.assertIsInstance(arm["deadlines"][deadline][field], int)
                self.assertEqual(set(arm["branch_cost_population"]), DISTRIBUTION_KEYS)
                conditional = arm["branch_cost_conditional_on_execution"]
                if arm["executed_branch_n"]:
                    self.assertEqual(set(conditional), DISTRIBUTION_KEYS)
                else:
                    self.assertIsNone(conditional)
        for policy in POLICIES:
            if policy == "B":
                continue
            paired = summary["paired"][f"B_vs_{policy}"]
            for field in ("first_only_correct", "second_only_correct", "both_correct", "both_wrong", "n"):
                self.assertIsInstance(paired[field], int)
        self.assertIsInstance(self.report["memory"]["campaign_rss_peak_kib_cumulative"], int)

    def test_subgroup_references_the_same_frozen_report(self) -> None:
        self.assertEqual(self.subgroup["input_sha256"]["report.json"], REPORT_SHA256)
        self.assertEqual(self.subgroup["groups"]["original_F0_trigger_40"]["n"], 40)


if __name__ == "__main__":
    unittest.main()
