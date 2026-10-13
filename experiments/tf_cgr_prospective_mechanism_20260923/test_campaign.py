"""Synthetic three-arm full-trace serializer and BASE JVP contract smoke."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
sys.path[:0] = [str(HERE), str(PROJECT / "experiments/sp_afdm_native_joint_20260921/src"),
                str(PROJECT / "experiments/sp_afdm_frozen_20260920/src"),
                str(PROJECT / "experiments/tf_cgr_mechanism_20260923_v2")]
import evidence  # noqa: E402
import generate_variants  # noqa: E402
import physical  # noqa: E402
import tf_base  # noqa: E402
import tf_cgr  # noqa: E402
import tf_sham  # noqa: E402
from branch import base_common_state, final_branch  # noqa: E402
from predict import _predict_one  # noqa: E402
import messages  # noqa: E402


@dataclass
class PathSlot:
    delay: int
    doppler: float


@dataclass
class Result:
    paths: list
    gains: np.ndarray
    diagnostics: dict
    elapsed_seconds: float
    evaluations: int


class Kernel:
    Path = PathSlot

    @staticmethod
    def reopen_geometry(Y, x, v, initial, **kwargs):
        stages = {key: 0. for key in (
            "geometry_setup", "structural_field_build", "structural_scoring",
            "structural_selection_trace", "structural_refit_refresh",
            "structural_fallback_direct", "local_refinement", "geometry_finalization")}
        return Result(initial, np.array([.21 + .08j, -.13 + .12j]),
                      dict(stage_timing=dict(exclusive_seconds=stages,
                                             total_seconds=0.)), 0., 1)


class Native:
    @staticmethod
    def decoder_messages(code, llr, maxiter):
        assert maxiter == 50
        return dict(decoded=np.zeros(2048, np.uint8), incoming_llr=llr.copy(),
                    raw_app=llr.copy(), raw_check_extrinsic=np.zeros(2048),
                    iterations=1, decode_ok=True, metadata=dict(seconds=0.),
                    syndrome_trace=[0])


def test_three_arm_roundtrip() -> None:
    generate_variants.verify(PROJECT / "experiments/sp_afdm_native_joint_20260921/src/twofft.py")
    n = 1024
    rng = np.random.default_rng(20260923)
    system = type("System", (), dict(rho=.5, c1=3.7 / (2 * n), c2=.017,
                                      l_max_cap=102))()
    obs = dict(y=rng.normal(size=n) + 1j * rng.normal(size=n),
               pilot=.3 * (rng.normal(size=n) + 1j * rng.normal(size=n)), sigma2=.25)
    arrays = dict(r1_app=rng.normal(size=2048), r1_check=rng.normal(size=2048),
                  r1_delays=np.array([3, 3]), r1_dopplers=np.array([.2, .27]),
                  r1_gains=np.array([.21 + .08j, -.13 + .12j]))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        for arm, detector in (("BASE", tf_base), ("CGR", tf_cgr), ("SHAM", tf_sham)):
            result = final_branch(obs, system, None, Native(), Kernel(), arrays, detector)
            raw = dict(observation_id="synthetic", arm=arm, input_sha256="synthetic",
                       native_arrays=arrays, native_timing=dict(seconds=0.),
                       native_decoder=Native.decoder_messages(None, np.zeros(2048), 50),
                       triggered=True, numerical_failure=None, entering=result["entering"],
                       gram=result["gram"], geometry_result=asdict(result["result"]),
                       branch_detector=result["detector"],
                       base_common_state=base_common_state(result["detector"]["states"], n)
                       if arm == "BASE" else None,
                       branch_decoder=result["decoder"],
                       final_decoded=result["decoder"]["decoded"])
            path = root / f"{arm}.npz"
            digest = evidence.save_artifact(path, raw,
                dict(schema="tf-cgr-prospective-mechanism/1", arm=arm))
            loaded, identity = evidence.load_artifact(path)
            assert identity["arm"] == arm and digest
            assert len(loaded["branch_detector"]["states"]) == 20
            assert len(loaded["branch_detector"]["states"][0]["x"]) == n
            assert loaded["gram"]["group_multiplicities"] == {"3": 2}
            (root / f"{arm}.json").write_text(json.dumps(dict(arm=arm, raw_sha256=digest)))
            if arm == "BASE":
                prediction = _predict_one("synthetic", 0, obs, loaded,
                                          "synthetic", digest,
                                          dict(rho=.5, c1=system.c1, c2=system.c2),
                                          physical, messages, tf_base.TimePathOps)
                assert prediction["final_gain_impulse_zero"]
                assert prediction["predicted_CGR_unclipped_llr_shift"].shape == (2048,)
        assert len(list(root.glob("*.npz"))) == 3


if __name__ == "__main__":
    test_three_arm_roundtrip()
    print("three-arm synthetic full trace/serializer/JVP PASS")
