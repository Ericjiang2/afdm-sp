"""Independently recount raw decisions without running a receiver or decoder."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "afdm_sp_joint_unrolled/outputs_oamp_ldpc_20261109"
ARCHIVE = PROJECT / "results/tf_cstate_prospective_20260923"
BASELINE = PROJECT / "experiments/sp_afdm_frozen_reviewed_20260921"
sys.path.insert(0, str(BASELINE / "src"))
from evidence import load_artifact


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_bound(path, expected):
    if digest(path) != expected:
        raise ValueError(f"artifact hash differs at {path}")
    return load_artifact(path)[0]


def main():
    results = json.loads((OUT / "results.json").read_text())
    refs = json.loads((OUT / "observed_seal.json").read_text())
    ledger = [json.loads(line) for line in (ARCHIVE / "population_truth/ledger.jsonl").read_text().splitlines()]
    truth = {row["observation_id"]: row for row in ledger}
    cache = BASELINE / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
    with np.load(cache, allow_pickle=False) as saved:
        free_cols, checks = saved["free_cols"], saved["H"]
    if hashlib.sha256(checks.tobytes()).hexdigest() != results["_config"]["ldpc_h_sha256"]:
        raise ValueError("code matrix identity differs")
    recorded = {row["observation_id"]: row for row in results["frames"]}
    if len(refs) != 40 or len(recorded) != 40:
        raise ValueError("expected 40 complete pairs")
    passes = {arm: set() for arm in ("tf_fixed", "oamp", "cstate")}
    timings = {arm: [] for arm in ("tf_fixed", "oamp")}
    setup = []
    for ref in refs:
        key = ref["observation_id"]
        label = truth[key]
        if label["observation_hash"] != ref["observation_hash"]:
            raise ValueError("truth observation identity differs")
        info = load_bound(ARCHIVE / "population_truth" / label["truth_path"], label["truth_sha256"])["info"]
        payload = load_bound(OUT / ref["path"], ref["sha256"])
        row = recorded[key]
        for arm in ("tf", "cstate"):
            errors = int(np.count_nonzero(payload[arm][free_cols] != info))
            if row[arm] != errors:
                raise ValueError("archived bit count differs")
            if arm == "tf" and errors == 0:
                raise ValueError("native error cohort differs")
            if arm == "cstate" and errors == 0:
                passes[arm].add(key)
        rounds_by_arm = payload["decisions"]
        np.testing.assert_array_equal(rounds_by_arm["oamp"]["rounds"][0]["prior"],
                                      rounds_by_arm["tf_fixed"]["rounds"][0]["prior"])
        for arm in ("tf_fixed", "oamp"):
            decision = rounds_by_arm[arm]
            rounds = decision["rounds"]
            if len(rounds) != 2:
                raise ValueError("decoder call allocation differs")
            np.testing.assert_array_equal(rounds[1]["prior"], np.clip(rounds[0]["check"], -20, 20))
            for index, checkpoint in enumerate(rounds):
                decoded = checkpoint["decoded"]
                if decoded.shape != (2048,) or not np.isin(decoded, [0, 1]).all():
                    raise ValueError("invalid decoded bits")
                errors = int(np.count_nonzero(decoded[free_cols] != info))
                if errors != row[arm]["errors"][index]:
                    raise ValueError("new raw bit count differs")
                if not 1 <= checkpoint["sweeps"] <= 50:
                    raise ValueError("decoder sweep allocation differs")
            if errors == 0:
                passes[arm].add(key)
            timings[arm].append(decision["seconds"])
            exclusive = decision["setup_seconds"] + sum(
                checkpoint["detector_seconds"] + checkpoint["decoder_seconds"] for checkpoint in rounds)
            if exclusive > decision["seconds"] + 1e-9:
                raise ValueError("stage times exceed continuation time")
        setup.append(rounds_by_arm["oamp"]["setup_seconds"])
    a, b = passes["oamp"], passes["tf_fixed"]
    computed = dict(oamp_rescues=len(a), tf_fixed_rescues=len(b),
                    archived_cstate_rescues=len(passes["cstate"]),
                    oamp_vs_fixed_rescues=len(a - b), oamp_vs_fixed_harms=len(b - a),
                    oamp_cstate_overlap=len(a & passes["cstate"]),
                    oamp_median_setup_seconds=float(np.median(setup)),
                    median_time_ratio=float(np.median(timings["oamp"]) / np.median(timings["tf_fixed"])))
    expected = results["results"]
    if (computed["oamp_rescues"] != expected["oamp"]["rescued"][-1]
            or computed["tf_fixed_rescues"] != expected["tf_fixed"]["rescued"][-1]
            or computed["median_time_ratio"] != expected["oamp_vs_tf_fixed"]["median_time_ratio"]
            or len(passes["cstate"]) != 34):
        raise ValueError("recomputed summary differs")
    receipt = dict(status="pass", raw_artifacts=40, decoded_checkpoints=160,
                   receiver_calls=0, decoder_calls=0, verify_code_sha256=digest(Path(__file__)),
                   results_sha256=digest(OUT / "results.json"),
                   observed_seal_sha256=digest(OUT / "observed_seal.json"), recomputed=computed)
    (OUT / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
