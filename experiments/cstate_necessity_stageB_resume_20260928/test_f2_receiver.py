"""Synthetic stubs check coded-round cost and native check carry; no decoder runs."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_frozen_20260920/src"))
sys.path.insert(0, str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"))

from physical import Channel  # noqa: E402
import evidence  # noqa: E402
import f2_receiver  # noqa: E402
from f2_estimator import estimate  # noqa: E402


def test_coded_handoff_counts_and_clock() -> None:
    n = 1024
    system = SimpleNamespace(rho=0.5, l_max_cap=102, c1=5 / (2 * n),
                             c2=(np.sqrt(2) - 1) / (2 * n * n))
    observed = {"y": np.zeros(n, complex), "pilot": np.ones(n, complex),
                "sigma2": 0.1}
    channel = Channel(n, system.c1, system.c2, np.zeros(155, int),
                      np.linspace(-3, 3, 155), np.ones(155, complex))
    called = {"estimator": 0, "tf": [], "decoder": 0, "checkpoints": []}

    def fake_estimate(*_args, **kwargs):
        called["estimator"] += 1
        called["initial_data"] = kwargs.get("initial_data")
        time.sleep(0.001)
        return {"channel": channel}

    def fake_tf(_y, _pilot, _channel, _sigma2, **kwargs):
        called["tf"].append(np.asarray(kwargs["prior"]).copy())
        assert _channel.p == 155 and kwargs["iterations"] == 20
        return {"extrinsic": np.zeros(2 * n), "gains": np.ones(155, complex),
                "gain_variance": np.ones(155), "trace": [],
                "mu": np.zeros(n), "variance": np.full(n, 0.5)}

    def fake_decoder(_code, _llr, *, maxiter):
        called["decoder"] += 1
        assert maxiter == 50
        return {"decoded": np.zeros(2 * n, np.uint8),
                "incoming_llr": np.zeros(2 * n),
                "raw_app": np.zeros(2 * n),
                "raw_check_extrinsic": np.full(2 * n, 2.0),
                "iterations": 1}

    def checkpoint(event, _bits):
        called["checkpoints"].append((event, np.asarray(_bits).copy()))

    with (patch.object(f2_receiver, "estimate", fake_estimate),
          patch.object(f2_receiver, "scalar_joint", fake_tf),
          patch.object(f2_receiver, "decoder_messages", fake_decoder)):
        early_decoder, early_arrays, early = f2_receiver.receive_f2e(
            observed, system, object(), checkpoint_sink=checkpoint)
        assert called["estimator"] == 1 and len(called["tf"]) == 2
        assert called["decoder"] == 2 and len(called["checkpoints"]) == 2
        assert np.all(called["tf"][0] == 0)
        assert np.all(called["tf"][1] == 2)
        assert early["timing"]["events"][0]["ready_seconds"] >= \
            early["timing"]["front_seconds"]
        assert "final_channel" not in early["timing"]

        # Round-trip the probe's complete raw and both durable checkpoint
        # envelopes. The front is an actual small synthetic estimator result;
        # the coded arrays/decoder are stubs, so no real receiver is called.
        small_n = 32
        small_c1 = 5 / (2 * small_n)
        small_c2 = (np.sqrt(2) - 1) / (2 * small_n * small_n)
        small_pilot = np.full(small_n, 0.5 + 0.5j)
        small_channel = Channel(small_n, small_c1, small_c2, [1], [0.0],
                                [0.8 + 0.1j])
        small_y = small_channel.apply(small_pilot + np.full(small_n, 0.5 - 0.5j))
        front = estimate(small_y, small_pilot, 0.1, small_c1, small_c2,
                         max_delay=1, nu_min=-1, nu_max=1)
        front_channel = front["channel"]
        summary = {key: value for key, value in front.items() if key != "channel"}
        summary["channel"] = {"delays": front_channel.delays,
                              "dopplers": front_channel.dopplers,
                              "gains": front_channel.gains}
        raw = {"observation_id": "synthetic", "input_sha256": "synthetic",
               "final_decoded": np.asarray(early_decoder["decoded"], np.uint8),
               "coded_arrays": early_arrays, "front": summary,
               "timing": early["timing"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (event, bits) in enumerate(called["checkpoints"]):
                path = root / f"checkpoint{index}.npz"
                evidence.save_artifact(path, {"event": event, "decoded": bits},
                                       {"observation_id": "synthetic", "round": index})
                restored, _ = evidence.load_artifact(path)
                assert np.array_equal(restored["decoded"], bits)
            path = root / "raw.npz"
            evidence.save_artifact(path, raw,
                                   {"observation_id": "synthetic", "arm": "F2E"})
            restored, _ = evidence.load_artifact(path)
            assert np.array_equal(restored["final_decoded"], raw["final_decoded"])
            assert np.array_equal(restored["front"]["channel"]["delays"],
                                  front_channel.delays)
            assert restored["timing"]["events"][0]["round"] == 0

        called["tf"].clear()
        called["checkpoints"].clear()
        check = np.full(2 * n, 7.0)
        _, _, triggered = f2_receiver.continue_f2t(
            observed, system, object(), native_app=np.zeros(2 * n),
            native_check=check, native_syndrome_weight=3,
            checkpoint_sink=checkpoint)
        assert called["estimator"] == 2 and len(called["tf"]) == 1
        assert called["decoder"] == 3 and len(called["checkpoints"]) == 1
        assert np.all(called["tf"][0] == 7)
        assert triggered["timing"]["events"][0]["ready_seconds"] >= \
            triggered["timing"]["front_seconds"]
        assert np.all(called["initial_data"] == 0.5 + 0.5j)


if __name__ == "__main__":
    test_coded_handoff_counts_and_clock()
    print("synthetic coded-handoff contract passed; zero real decoder calls")
