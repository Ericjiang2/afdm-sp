"""Small runner-contract fixtures; these are not real receiver qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("development_runner", HERE / "run_development.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def observed():
    return dict(observation=dict(y=np.zeros(1024, complex), pilot=np.zeros(1024, complex),
                                sigma2=1.),
                observation_id="s650_f0044", stream_ids={}, observation_hash="fixture")


class RunnerContract(unittest.TestCase):
    def test_registered_rotation_and_qualification(self):
        registration = json.loads((HERE / "dev_registration.json").read_text())
        calls = runner.schedule(registration, False)
        self.assertEqual(len(calls), 384)
        self.assertEqual([arm for _, arm in calls[:9]],
                         ["scalar", "coherent", "full", "coherent", "full", "scalar",
                          "full", "scalar", "coherent"])
        self.assertEqual(runner.schedule(registration, True),
                         [("s650_f0044", arm) for arm in
                          ("scalar", "identity", "coherent", "full")])
        registration["observation_ids"][1] = registration["observation_ids"][0]
        with self.assertRaisesRegex(ValueError, "allocation"):
            runner.schedule(registration, False)

    def test_identity_detects_soft_changes_even_with_same_decoded_word(self):
        left = dict(decoded=np.zeros(2, np.uint8), incoming_llr=np.array([1., 2.]),
                    metadata=dict(seconds=1., hashes={"llr": "same"}))
        right = copy.deepcopy(left)
        right["metadata"]["seconds"] = 2.
        runner.assert_same(runner.scientific_output(left), runner.scientific_output(right))
        right["incoming_llr"][0] += 1e-15
        with self.assertRaisesRegex(AssertionError, "incoming_llr"):
            runner.assert_same(runner.scientific_output(left), runner.scientific_output(right))

    def test_observed_boundary_rejects_truth_and_identity_mismatch(self):
        source = dict(observation_id="s650_f0044", observation_path="observed/f.npz",
                      observation_sha256="fixture")
        payload = observed()
        load = lambda *_: payload
        runner.observed_inputs(None, load, Path("/fixture"), source)
        payload["truth"] = np.zeros(1)
        with self.assertRaisesRegex(ValueError, "non-observation"):
            runner.observed_inputs(None, load, Path("/fixture"), source)
        del payload["truth"]
        payload["observation_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "identity"):
            runner.observed_inputs(None, load, Path("/fixture"), source)

    def test_finite_nested_array_and_metadata(self):
        for value in (dict(a=[np.array([float("nan")])]), dict(a=float("inf"))):
            with self.assertRaises(FloatingPointError):
                runner.finite(value)

    def test_failed_receiver_attempt_is_retained_and_reraised(self):
        def fail(*_args, **_kwargs):
            raise RuntimeError("fixture receiver failure")

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            source = dict(observation_id="s650_f0044", observation_path="observed/f.npz",
                          observation_sha256="fixture")
            with self.assertRaisesRegex(RuntimeError, "fixture receiver failure"):
                runner.run_call("s650_f0044", "scalar", 0, source, out=out,
                    population=Path("/fixture"), evidence=None, load_bound=lambda *_: observed(),
                    system=None, code=None, H=None, native=SimpleNamespace(receive=fail),
                    variants={}, kernel=None, branch_fn=None)
            ledger = [json.loads(line) for line in (out / "ledger.jsonl").read_text().splitlines()]
            events = [json.loads(line) for line in (out / "allcalls.jsonl").read_text().splitlines()]
            self.assertEqual(len(ledger), 1)
            self.assertEqual(ledger[0]["status"], "failed")
            self.assertTrue(ledger[0]["receiver_started"])
            self.assertEqual([event["event"] for event in events],
                             ["attempt_started", "attempt_failed"])
            self.assertFalse((out / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
