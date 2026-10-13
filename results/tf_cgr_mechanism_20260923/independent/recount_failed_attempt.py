#!/usr/bin/env python3
"""Independent recount of the preserved first failed CGR observed attempt."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import verify_saved as verify  # noqa: E402


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    base = ROOT / "results/tf_cgr_mechanism_20260923/failed_attempt_20260923"
    run = base / "observed"
    receipt = json.loads((base / "failure_receipt.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    ledger_lines = (run / "ledger.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in ledger_lines]
    blocked = json.loads((run / "blocked.json").read_text())
    require(receipt["attempts"] == len(rows) == 1, "failed-attempt count differs")
    row = rows[0]
    require(row["status"] == "failed" and row["call_index"] == 1 and
            row["observation_id"] == receipt["observation_id"] == "s650_f0390" and
            row["arm"] == receipt["arm"] == "BASE", "failed call identity differs")
    require(blocked["failed_call"] == 1 and blocked["arm"] == "BASE" and
            blocked["reason"] == row["exception"] == receipt["exception"],
            "blocked/ledger/failure receipt disagree")
    require(manifest["expected_calls"] == 100 and manifest["schema"] == verify.SCHEMA,
            "attempt manifest identity differs")

    witness_manifest = json.loads((ROOT / "results/tf_cgr_mechanism_20260923/witnesses/witness_manifest.json").read_text())
    witness_entry = next(e for e in witness_manifest["entries"]
                         if e["observation_id"] == row["observation_id"])
    obs_file = next(f for f in witness_entry["files"] if f["kind"] == "observation")
    obs_path = verify.safe_path(ROOT / "results/tf_cgr_mechanism_20260923/witnesses",
                                obs_file["relative_path"])
    obs_sha = verify.sha256(obs_path)
    require(obs_sha == obs_file["sha256"] == row["input_sha256"],
            "observed input SHA differs from witness manifest / ledger")
    observed, observed_identity = verify.load_artifact(obs_path)
    require(observed_identity.get("kind") == "observed" and
            observed_identity.get("schema") == "tf-cstate-prospective/1" and
            observed_identity.get("observation_id") == row["observation_id"] and
            len(observed_identity.get("registration_sha256", "")) == 64,
            "observed artifact identity differs from its bound witness")
    require(set(observed) == {"observation_id", "observation", "observation_hash", "stream_ids"} and
            observed["observation_id"] == row["observation_id"] and
            set(observed["observation"]) == {"y", "pilot", "sigma2"} and
            set(observed["stream_ids"]) == {"channel", "message", "noise"},
            "observed payload keys differ from the frozen witness contract")
    digest_parts = []
    for key in ("y", "pilot", "sigma2"):
        value = np.asarray(observed["observation"][key])
        digest = hashlib.sha256()
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(value.shape).encode())
        digest.update(np.ascontiguousarray(value).tobytes())
        digest_parts.append(digest.hexdigest())
    independently_reconstructed_observation_hash = hashlib.sha256(
        "|".join(digest_parts).encode()).hexdigest()
    require(independently_reconstructed_observation_hash == observed["observation_hash"],
            "producer observation identity recomputation differs")

    cache = ROOT / "experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
    with np.load(cache, allow_pickle=False) as saved:
        H = np.asarray(saved["H"]).copy()
        G = np.asarray(saved["G"]).copy()
        free = np.asarray(saved["free_cols"]).copy()
    require(H.shape == (1026, 2048) and G.shape == (2048, 1024) and
            free.shape == (1024,), "frozen code dimensions differ")
    require(hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() ==
            manifest["code_g_sha256"], "G data hash differs from run manifest")

    checkpoints = []
    for ordinal, cp in enumerate(row["checkpoints"]):
        require(cp["round"] == ordinal, "checkpoint sequence has a gap or reordering")
        path = verify.safe_path(run, cp["path"])
        actual_sha = verify.sha256(path)
        require(actual_sha == cp["artifact_sha256"] ==
                receipt["checkpoints"][ordinal]["sha256"],
                f"checkpoint SHA differs at round {ordinal}")
        payload, identity = verify.load_artifact(path, {
            "schema": verify.SCHEMA, "observation_id": row["observation_id"],
            "arm": row["arm"], "round": ordinal})
        bits = np.asarray(payload["decoded"])
        require(bits.shape == (2048,) and bits.dtype == np.uint8 and
                np.isin(bits, [0, 1]).all(), f"invalid checkpoint bits at round {ordinal}")
        recount = verify._syndrome(H, bits)
        require(recount == cp["syndrome_weight"] ==
                receipt["checkpoints"][ordinal]["syndrome_weight"],
                f"checkpoint syndrome differs at round {ordinal}")
        event = cp["event"]
        require(event["round"] == ordinal and event["decoder_iterations"] == 50 and
                event["inference_iterations"] == 20,
                f"detector/decoder iteration record differs at round {ordinal}")
        checkpoints.append({
            "round": ordinal,
            "identity": identity,
            "path": cp["path"],
            "sha256": actual_sha,
            "decoded_dtype": str(bits.dtype),
            "decoded_shape": list(bits.shape),
            "syndrome_recount": recount,
            "syndrome_matches_ledger_and_receipt": True,
            "detector_iterations": event["inference_iterations"],
            "decoder_iterations": event["decoder_iterations"],
            "ready_seconds": cp["decision_ready_seconds"],
            "artifact_ready_seconds": cp["artifact_ready_seconds"],
            "event": event,
        })
    require([cp["round"] for cp in checkpoints] == [0, 1, 2],
            "expected 2 native checkpoints plus 1 final branch checkpoint")
    require(len(row["checkpoints"]) == len(receipt["checkpoints"]) == 3,
            "checkpoint count differs")

    # Recompute all 115 source file hashes from the local frozen trees. The
    # reviewer uses equivalent local path names for the bound remote roots.
    source_bindings_path = base / "source_bindings_local_v4.json"
    bindings = json.loads(source_bindings_path.read_text())
    args = type("Paths", (), {})()
    args.geometry = ROOT / "experiments/tf_cstate_validation_20260922"
    args.source = ROOT / "experiments/sp_afdm_native_joint_20260921"
    args.baseline = ROOT / "experiments/sp_afdm_frozen_20260920"
    args.code_cache = cache
    actual = {key: verify.sha256(path) for key, path in verify._source_files(args).items()}
    require(actual == bindings == manifest["source_hashes"],
            "local 115-file source inventory differs from attempt manifest")
    require(verify.sha256(source_bindings_path) == receipt["files"]["source_bindings_local_v4.json"],
            "preserved source binding file SHA differs from receipt")

    fail_dir_inventory = {}
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.name != "failure_receipt.json":
            rel = str(path.relative_to(base))
            fail_dir_inventory[rel] = verify.sha256(path)
    require(fail_dir_inventory == receipt["files"],
            "preserved failure package file inventory differs from Sol receipt")
    require(not (run / "raw/s650_f0390_BASE.npz").exists() and
            not (run / "decisions/s650_f0390_BASE.json").exists() and
            not (run / "observed_seal.json").exists(),
            "unexpected raw/decision/seal artifact exists")

    out = {
        "schema": "tf-cgr-independent-failed-attempt-recount/1",
        "status": "pass",
        "truth_values_read": False,
        "source_commit": receipt["source_commit"],
        "attempts": 1,
        "complete_wrappers": 0,
        "failed_wrapper": {"call_index": 1, "observation_id": row["observation_id"],
            "arm": row["arm"], "role": row["role"], "receiver_started": row["receiver_started"],
            "failure_stage": "raw serialization after final branch checkpoint",
            "exception": row["exception"], "elapsed_seconds": row["elapsed_seconds"],
            "input_sha256": obs_sha,
            "producer_observation_hash": observed["observation_hash"],
            "producer_observation_hash_recomputed": independently_reconstructed_observation_hash,
            "observation_payload_identity": observed_identity},
        "completed_decode_path": {
            "native_round_count": 2,
            "final_branch_count": 1,
            "inference_detector_calls": 3,
            "inference_iterations_each": 20,
            "ldpc_decoder_calls": 3,
            "ldpc_iterations_each": 50,
            "checkpoint_count": len(checkpoints),
            "checkpoints": checkpoints,
            "final_ready_seconds": checkpoints[-1]["ready_seconds"],
            "final_checkpoint_persisted_seconds": checkpoints[-1]["artifact_ready_seconds"],
            "attempt_failed_elapsed_seconds": row["elapsed_seconds"],
            "timing_note": "ready and checkpoint persistence are distinct; no complete raw/decision serialization timing was saved",
        },
        "source_integrity": {"bound_files": len(actual), "all_local_hashes_match": True,
            "source_bindings_sha256": verify.sha256(source_bindings_path)},
        "saved_artifacts": {
            "raw_artifact_available": False, "decision_record_available": False,
            "observed_seal_available": False, "blocked_record_sha256": verify.sha256(run / "blocked.json"),
            "ledger_sha256": verify.sha256(run / "ledger.jsonl"),
            "manifest_sha256": verify.sha256(run / "manifest.json"),
        },
        "recount_boundary": "Three checkpoint artifacts, 115 source hashes, and the observation input hash independently verified. Truth, information-bit correctness, and campaign-level metrics were not inspected or computed.",
    }
    receipt_path = HERE / "failed_attempt_recount.json"
    receipt_path.write_text(json.dumps(out, indent=2, sort_keys=True,
                                      allow_nan=False) + "\n")
    print(json.dumps({"status": "pass", "attempts": 1, "complete_wrappers": 0,
                      "checkpoints": 3, "truth_values_read": False,
                      "output": str(receipt_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
