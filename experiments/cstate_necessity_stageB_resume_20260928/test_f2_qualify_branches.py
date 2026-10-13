"""Three-branch serialization/accounting stub; zero real estimation or decode."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))
sys.path.insert(0, str(ROOT / "experiments/cstate_necessity_stageB_resume_20260928"))
import evidence  # noqa: E402
import f2_qualify_branches_v2 as qualification  # noqa: E402


@dataclass
class FakeResult:
    paths: list[int]
    evaluations: dict


def test_three_continuations_and_saved_prefix_isolation() -> None:
    arrays = {stem: {"r1_app": np.zeros(2048), "r1_check": np.ones(2048)}
              for stem in ("s650_f0000", "s650_f0044")}
    observed = {stem: {"y": np.zeros(1024, complex),
                       "pilot": np.ones(1024, complex), "sigma2": 0.1}
                for stem in arrays}
    called = []

    def fake_branch(_observation, _system, _code, _native, _kernel, values, mode):
        called.append(mode)
        assert values["r1_app"][0] == 0
        values["r1_app"][0] = 999  # next fork must receive a fresh saved-state copy
        return {"result": FakeResult(list(range(155)), {"local_trials": 1}),
                "decoder": {"decoded": np.zeros(2048, np.uint8)},
                "detector": {"extrinsic": np.zeros(2048)},
                "exclusive_stages": {"tf": .01, "ldpc": .01}}

    def fake_continue(_observation, _system, _code, *, native_app,
                      native_check, native_syndrome_weight, checkpoint_sink):
        assert native_syndrome_weight == 68
        assert native_app[0] == 0 and native_check[0] == 1
        checkpoint_sink({"round": 0}, np.zeros(2048, np.uint8))
        channel = SimpleNamespace(p=155, delays=np.arange(155),
                                  dopplers=np.zeros(155), gains=np.ones(155, complex))
        return ({"decoded": np.zeros(2048, np.uint8)}, {},
                {"estimator": {"channel": channel}, "timing": {"events": []},
                 "initial_data": np.full(1024, 0.5 + 0.5j)})

    bound = {"manifest": {"source_hashes": {},
                          "f0000_input_sha256": "synthetic0",
                          "f0044_input_sha256": "synthetic44"},
             "environment": {}, "evidence": evidence,
             "observations": observed, "arrays": arrays,
             "syndromes": {"s650_f0000": 1, "s650_f0044": 68},
             "branch": fake_branch, "continue_f2t": fake_continue,
             "native": object(), "kernel": object(), "system": object(),
             "code": object(), "H": np.zeros((1, 2048), np.uint8),
             "extract_info": lambda _code, _bits: np.zeros(1024, np.uint8)}
    with tempfile.TemporaryDirectory() as directory:
        out = Path(directory) / "synthetic"
        args = SimpleNamespace(out=out, manifest_sha256="synthetic")
        with patch.object(qualification, "preflight", return_value=bound):
            qualification.run(args)
        seal = json.loads((out / "observed_seal.json").read_text())
        assert seal["completed_continuations"] == 3
        rows = [json.loads(line) for line in (out / "ledger.jsonl").read_text().splitlines()]
        assert [row["arm"] for row in rows] == list(qualification.ARMS)
        assert all(len(row["checkpoints"]) == 1 for row in rows)
        assert called == ["LOCAL20", "CSTATE20"]
        assert arrays["s650_f0000"]["r1_app"][0] == 0
        for row in rows:
            raw, _ = evidence.load_artifact(out / row["raw_path"])
            assert raw["arm"] == row["arm"]
            assert np.asarray(raw["final_decoded"]).shape == (2048,)

        def failed_optional(*args):
            if args[-1] == "CSTATE20":
                raise FloatingPointError("synthetic optional numerical failure")
            return fake_branch(*args)

        called.clear()
        bound["branch"] = failed_optional
        partial = Path(directory) / "partial"
        args.out = partial
        with patch.object(qualification, "preflight", return_value=bound):
            try:
                qualification.run(args)
            except FloatingPointError:
                pass
            else:
                raise AssertionError("optional failure did not fail the process")
        partial_seal = json.loads((partial / "observed_seal.json").read_text())
        assert partial_seal["status"] == "partial_qualified"
        assert partial_seal["qualified_arms"] == list(qualification.ARMS[:2])
        assert partial_seal["excluded_arm"] == qualification.ARMS[2]
        assert len((partial / "ledger.jsonl").read_text().splitlines()) == 2
        failure = json.loads((partial / "failure.json").read_text())
        assert failure["numerical_failure"] and failure["failed_attempt"] == 3
        assert failure["failed_attempt_elapsed_seconds"] >= 0
        assert failure["total_elapsed_seconds"] >= failure["failed_attempt_elapsed_seconds"]


if __name__ == "__main__":
    test_three_continuations_and_saved_prefix_isolation()
    print("F2 branch qualification stub passed; zero real receiver calls")
