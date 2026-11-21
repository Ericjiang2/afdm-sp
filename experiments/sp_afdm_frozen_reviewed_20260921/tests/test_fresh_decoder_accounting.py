"""Synthetic decoder-call accounting for ABL_fresh_APP; no radio evidence."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import receiver  # noqa: E402


calls = []


def fake_decoder(code, incoming, *, maxiter):
    calls.append(np.asarray(incoming).copy())
    index = len(calls)
    raw = np.asarray(incoming, dtype=float)
    return {
        "incoming_llr": raw,
        "raw_app": raw + 0.25,
        "raw_check_extrinsic": np.full_like(raw, 0.25),
        "decoded": (raw < 0).astype(np.uint8),
        "decode_ok": False,
        "iterations": index,
        "syndrome_trace": [],
        "metadata": {"seconds": 0.1 * index, "truth_access": "none"},
    }


class FakeChannel:
    delays = np.array([0])
    dopplers = np.array([0.0])
    gains = np.array([1.0 + 0.0j])

    def apply(self, value):
        return np.asarray(value)

    def select(self, weight, cap, tolerance):
        return np.array([0]), np.array([1.0]), 0.0, True

    def diagonals(self, keep):
        return np.ones((1, 2), dtype=complex)

    def row_variance(self, variance, keep):
        return np.zeros(2)


def fake_refine(*args, **kwargs):
    return FakeChannel(), {"history": [1.0], "gamma": np.ones(2), "evaluations": 1}


def fake_sparse_bp(*args, **kwargs):
    return {
        "extrinsic": np.array([1.0, -1.0, 1.0, -1.0]),
        "app": np.zeros(4),
        "mu": np.zeros(2, dtype=complex),
        "variance": np.ones(2),
        "trace": [],
    }


originals = receiver.decoder_messages, receiver.refine, receiver.sparse_bp, receiver.extract_info
receiver.decoder_messages = fake_decoder
receiver.refine = fake_refine
receiver.sparse_bp = fake_sparse_bp
receiver.extract_info = lambda code, decoded: decoded
try:
    observed = {"y": np.zeros(2, dtype=complex), "pilot": np.zeros(2, dtype=complex), "sigma2": 1.0}
    state = {
        "prior": np.zeros(4), "channel_llr": np.array([0.5, -0.5, 0.5, -0.5]),
        "mu": np.zeros(2, dtype=complex), "v": np.full(2, 0.5),
        "x_soft": np.zeros(2, dtype=complex), "delays": np.array([0]),
        "dopplers": np.array([0.0]), "gains": np.array([1.0 + 0.0j]),
        "sigma_final": 1.0,
    }
    result = receiver.finish(observed, state, SimpleNamespace(c1=0.0, c2=0.0), {},
                             {"qsource": "decoder_app"})
finally:
    receiver.decoder_messages, receiver.refine, receiver.sparse_bp, receiver.extract_info = originals

assert len(calls) == 2
assert [record["evidence_stage"] for record in result["decoder_records"]] == [
    "fresh_decoder", "terminal_decoder"]
assert abs(result["decoder_seconds"] - 0.3) < 1e-12
fresh_event = next(event for event in result["events"] if event["stage"] == "fresh_decoder")
assert fresh_event["metadata"]["seconds"] == 0.1
assert result["events"][-1]["metadata"]["seconds"] == 0.2

print("PASS fresh APP and terminal decoder calls are both retained and charged")
