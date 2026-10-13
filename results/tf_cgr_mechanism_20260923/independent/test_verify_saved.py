#!/usr/bin/env python3
"""Synthetic-only tests for the independent evidence reader and frozen schedule."""
from __future__ import annotations

import json
import hashlib
import tempfile
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import verify_saved as verify  # noqa: E402


def test_evidence_decoder_round_trip():
    identity = {"schema": verify.SCHEMA, "observation_id": "synthetic",
                "arm": "BASE", "round": 0}
    array_a = np.arange(6, dtype=np.int16).reshape(2, 3)
    array_b = np.array([1 + 2j, 3 - 4j], dtype=np.complex128)
    tree = {"array": {verify.ARRAY_SENTINEL: "payload_array"},
            "nested": [{"x": {verify.ARRAY_SENTINEL: "payload_nested_x"}},
                       {verify.TUPLE_SENTINEL: ["ok", {verify.ARRAY_SENTINEL: "payload_nested_y"}]}],
            "scalar": 4.5}
    envelope = {"format_version": 2, "identity": identity, "payload": tree}
    arrays = {"payload_array": array_a,
              "payload_nested_x": np.array([True, False]),
              "payload_nested_y": array_b}
    encoded = dict(arrays)
    encoded[verify.METADATA] = np.frombuffer(
        json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                   allow_nan=False).encode(), dtype=np.uint8)
    with tempfile.TemporaryDirectory(prefix="tf-cgr-independent-") as tmp:
        path = Path(tmp) / "synthetic.npz"
        np.savez_compressed(path, **encoded)
        payload, actual_identity = verify.load_artifact(path, identity)
        assert actual_identity == identity
        assert np.array_equal(payload["array"], array_a)
        assert np.array_equal(payload["nested"][0]["x"], arrays["payload_nested_x"])
        assert payload["nested"][1][0] == "ok"
        assert np.array_equal(payload["nested"][1][1], array_b)
        assert payload["scalar"] == 4.5


def test_schedule_and_entering_hash():
    path = ROOT / "results/tf_cgr_mechanism_20260923_v2/witnesses/witness_manifest.json"
    manifest = json.loads(path.read_text())
    calls = verify.build_calls(manifest["entries"])
    assert len(calls) == 100
    for frame_index, entry in enumerate(manifest["entries"]):
        expected = verify.ARMS[frame_index % 4:] + verify.ARMS[:frame_index % 4]
        assert [arm for item, arm in calls[frame_index * 4:(frame_index + 1) * 4]] == list(expected)
        assert all(item["observation_id"] == entry["observation_id"]
                   for item, _ in calls[frame_index * 4:(frame_index + 1) * 4])
    sample = {"z": np.array([1., 2.], dtype=np.float64),
              "a": [np.array([1 + 1j], dtype=np.complex128)]}
    assert verify._hash_value(sample) == verify._hash_value(sample)
    reordered = {"a": sample["a"], "z": sample["z"]}
    assert verify._hash_value(sample) == verify._hash_value(reordered)
    assert verify._hash_value(sample) != verify._hash_value(
        {"z": np.array([1., 2.], dtype=np.float32), "a": sample["a"]})


def _write_artifact(path, payload, identity):
    arrays = {}

    def pack(value, prefix):
        if isinstance(value, np.ndarray):
            assert prefix and prefix not in arrays
            arrays[prefix] = value
            return {verify.ARRAY_SENTINEL: prefix}
        if isinstance(value, dict):
            assert all(isinstance(key, str) for key in value)
            return {key: pack(item, f"{prefix}_{key}" if prefix else key)
                    for key, item in value.items()}
        if isinstance(value, tuple):
            return {verify.TUPLE_SENTINEL: [pack(item, f"{prefix}_{i}")
                                           for i, item in enumerate(value)]}
        if isinstance(value, list):
            return [pack(item, f"{prefix}_{i}") for i, item in enumerate(value)]
        return value

    tree = pack(payload, "")
    envelope = {"format_version": 2, "identity": identity, "payload": tree}
    arrays[verify.METADATA] = np.frombuffer(
        json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                   allow_nan=False).encode(), dtype=np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    return verify.sha256(path)


def test_complete_sealed_output_synthetic():
    """Exercise the whole truth-free recount with 100 tiny synthetic calls."""
    witness_root = verify.RESULTS / "witnesses"
    witness_manifest_path = verify.RESULTS / "witnesses/witness_manifest.json"
    witness_manifest = json.loads(witness_manifest_path.read_text())
    registration_path = verify.RESULTS / "registration.json"
    qualification_path = verify.RESULTS / "qualification/local_v1/qualification.json"
    receipt_path = verify.RESULTS / "witness_receipt.json"
    source_bindings_path = verify.RESULTS / "qualification/source_bindings_v1.json"
    args = type("Args", (), {
        "source": verify.EXP / "sp_afdm_native_joint_20260921",
        "baseline": verify.EXP / "sp_afdm_frozen_20260920",
        "geometry": verify.EXP / "tf_cstate_validation_20260922",
        "producer": verify.EXP / "tf_cgr_mechanism_20260923_v2",
        "code_cache": verify.EXP / "sp_afdm_frozen_20260920/upstream/"
            "spafdm_receiver_handoff/afdm_sp_joint_unrolled/"
            "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz",
    })()
    args.witness_manifest = witness_manifest_path
    args.witness_root = witness_root
    args.witness_receipt = receipt_path
    args.registration = registration_path
    args.qualification = qualification_path
    args.source_bindings = source_bindings_path
    args.truth_analysis = False
    args.seal_commit = None

    with np.load(args.code_cache, allow_pickle=False) as archive:
        G = np.asarray(archive["G"])
        zero = np.zeros(2048, dtype=np.uint8)
    tmp_owner = Path(tempfile.mkdtemp(prefix="tf-cgr-sealed-synthetic-"))
    args.run = tmp_owner / "run"
    args.run.mkdir()
    args.out = tmp_owner / "verification.json"
    manifest = {
        "schema": verify.SCHEMA,
        "expected_calls": 100,
        "registration_sha256": verify.sha256(registration_path),
        "qualification_sha256": verify.sha256(qualification_path),
        "witness_manifest_sha256": verify.sha256(witness_manifest_path),
        "witness_receipt_sha256": verify.sha256(receipt_path),
        "source_bindings_sha256": verify.sha256(source_bindings_path),
        "source_hashes": json.loads(source_bindings_path.read_text()),
        "code_g_sha256": hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest(),
        "arms": list(verify.ARMS),
    }
    (args.run / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    rows = []
    calls = verify.build_calls(witness_manifest["entries"])
    for call_index, (entry, arm) in enumerate(calls, 1):
        obs_id = entry["observation_id"]
        obs_file = next(item for item in entry["files"] if item["kind"] == "observation")
        input_path = verify.safe_path(witness_root, obs_file["relative_path"])
        input_sha = verify.sha256(input_path)
        cp_rows = []
        for round_index, ready in ((0, 0.03), (1, 0.06)):
            rel = f"checkpoints/{obs_id}_{arm}_r{round_index}.npz"
            cp_sha = _write_artifact(args.run / rel, {"decoded": zero},
                {"schema": verify.SCHEMA, "observation_id": obs_id,
                 "arm": arm, "round": round_index})
            cp_rows.append({"round": round_index, "path": rel,
                "artifact_sha256": cp_sha, "decision_ready_seconds": ready,
                "artifact_ready_seconds": ready + 0.001, "syndrome_weight": 0,
                "event": {}})
        raw_rel = f"raw/{obs_id}_{arm}.npz"
        raw_sha = _write_artifact(args.run / raw_rel, {
            "observation_id": obs_id, "arm": arm, "input_sha256": input_sha,
            "native_arrays": {"r0_decoded": zero, "r1_decoded": zero},
            "native_decoder": {"decoded": zero}, "triggered": False,
            "numerical_failure": None, "entering": None, "gram": None,
            "geometry_result": None, "branch_detector": None,
            "base_common_state": None, "trace_origin":
                "newly instrumented replay of frozen observed witness",
            "branch_decoder": None, "final_decoded": zero,
        }, {"schema": verify.SCHEMA, "observation_id": obs_id, "arm": arm})
        decoded_sha = hashlib.sha256(zero.tobytes()).hexdigest()
        decision_rel = f"decisions/{obs_id}_{arm}.json"
        decision = {"schema": verify.SCHEMA, "observation_id": obs_id,
            "arm": arm, "input_sha256": input_sha, "triggered": False,
            "numerical_failure": None, "baseline_syndrome_weight": 0,
            "final_syndrome_weight": 0, "final_decoded_sha256": decoded_sha,
            "final_decision_ready_seconds": 0.06, "checkpoints": cp_rows,
            "raw_path": raw_rel, "raw_sha256": raw_sha,
            "entering_sha256": None}
        decision_path = args.run / decision_rel
        decision_path.parent.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(json.dumps(decision, sort_keys=True) + "\n")
        row = {"status": "ok", "call_index": call_index,
            "observation_id": obs_id, "role": entry["role"], "arm": arm,
            "receiver_started": True, "checkpoints": cp_rows,
            "input_sha256": input_sha, "triggered": False,
            "numerical_failure": None, "baseline_syndrome_weight": 0,
            "final_syndrome_weight": 0, "final_decoded_sha256": decoded_sha,
            "final_decision_ready_seconds": 0.06,
            "complete_latency_seconds": 0.09,
            "branch_elapsed_seconds": 0., "branch_decision_seconds": None,
            "branch_complete_seconds": 0., "entering_sha256": None,
            "raw_path": raw_rel, "raw_sha256": raw_sha,
            "decision_path": decision_rel,
            "decision_sha256": verify.sha256(decision_path)}
        rows.append(row)
    ledger = args.run / "ledger.jsonl"
    ledger.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    inventory = {str(path.relative_to(args.run)): verify.sha256(path)
                 for path in args.run.rglob("*") if path.is_file()}
    seal = {"schema": verify.SCHEMA, "status": "pass", "completed_calls": 100,
            "witness_manifest_sha256": verify.sha256(witness_manifest_path),
            "source_bindings_sha256": verify.sha256(source_bindings_path),
            "files": inventory}
    (args.run / "observed_seal.json").write_text(json.dumps(seal, sort_keys=True) + "\n")
    result = verify.verify_observed(args)
    assert result["status"] == "pass" and result["calls"] == 100
    assert result["truth_values_read"] is False
    assert result["prefix_identity"]["round0_bit_mismatches"] == 0
    assert result["timing"]["CGR"]["branch_decision_seconds_successful"]["n"] == 0


if __name__ == "__main__":
    test_evidence_decoder_round_trip()
    test_schedule_and_entering_hash()
    test_complete_sealed_output_synthetic()
    print("synthetic evidence codec, 100-call schedule, and sealed observed recount passed")
