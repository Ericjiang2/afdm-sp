#!/usr/bin/env python3
"""Read-only inventory of sealed v2 observed raw artifacts (never opens truth)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OBS = ROOT / "results/tf_cgr_mechanism_20260923_v2/observed"
WITNESS = ROOT / "results/tf_cgr_mechanism_20260923_v2/witnesses/witness_manifest.json"
SEAL_COMMIT = "dc228d7254274f3be3403514fc75f0758aacc15c"
SEAL_SHA256 = "42228ad286f13a8f518fd4d2278375ca0592cc67c424f79a3536fe1150175c43"
TARGETS = {
    "s650_f0390", "s650_f0415", "s650_f0718", "s650_f0720",
    "s650_f0770", "s650_f0996", "s600_f0600", "s700_f0732",
}
RESCUED = {
    "s600_f0958", "s650_f0127", "s650_f0413", "s650_f0519",
    "s650_f0761", "s650_f0797", "s700_f0184",
}
DISTINCT = {"s600_f0087", "s600_f0552", "s700_f0509"}
EASY = {
    "s650_f0190", "s650_f0198", "s650_f0563", "s650_f0631",
    "s650_f0838", "s600_f0985", "s700_f0436",
}
ARMS = ("BASE", "CGR", "SHAM", "BLOCK")
META = "__evidence_metadata__"
ARRAY_REF = "__evidence_array__"
TUPLE_REF = "__evidence_tuple__"
VECTOR_STATE_FIELDS = ("x", "xbar", "mu", "v", "s", "rx", "app", "extrinsic")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def safe_observed_file(relative: str) -> Path:
    rel = Path(relative)
    require(not rel.is_absolute() and ".." not in rel.parts, f"unsafe path {relative}")
    candidate = OBS / rel
    require(not candidate.is_symlink(), f"symlink rejected: {relative}")
    full = candidate.resolve()
    require(full.is_relative_to(OBS.resolve()) and full.is_file(), f"missing/escaping file: {relative}")
    return full


def array_refs(tree: Any) -> set[str]:
    if isinstance(tree, dict):
        if set(tree) == {ARRAY_REF}:
            ref = tree[ARRAY_REF]
            require(isinstance(ref, str) and ref, "invalid evidence array reference")
            return {ref}
        if set(tree) == {TUPLE_REF}:
            tree = tree[TUPLE_REF]
        children = tree.values() if isinstance(tree, dict) else tree
        refs: set[str] = set()
        for value in children:
            refs.update(array_refs(value))
        return refs
    if isinstance(tree, list):
        refs: set[str] = set()
        for value in tree:
            refs.update(array_refs(value))
        return refs
    return set()


def scalar_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return type(value).__name__


def inspect_npz(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read raw evidence metadata and array dtype/shape only; no value math."""
    with np.load(path, allow_pickle=False) as archive:
        physical_keys = sorted(archive.files)
        require(META in physical_keys, f"missing {META}: {path}")
        meta = np.asarray(archive[META])
        require(meta.dtype == np.uint8 and meta.ndim == 1, f"invalid metadata encoding: {path}")
        envelope = json.loads(meta.tobytes().decode("utf-8"))
        require(envelope.get("format_version") == 2, f"evidence format differs: {path}")
        payload = envelope.get("payload")
        refs = array_refs(payload)
        require(refs == set(physical_keys) - {META}, f"array inventory differs: {path}")
        arrays: dict[str, dict[str, Any]] = {}
        for key in sorted(refs):
            array = np.asarray(archive[key])
            require(not array.dtype.hasobject, f"object dtype rejected: {path}:{key}")
            arrays[key] = {"dtype": str(array.dtype), "shape": list(array.shape)}
        # Keep only a compact per-schema key/dtype/shape table; raw numeric values
        # are never copied into the inventory.
    return ({"physical_npz_keys": physical_keys,
             "array_headers": arrays},
            {"payload": payload, "envelope": envelope})


def field_descriptor(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return only array header/scalar kind for a direct payload field."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, dict) and set(value) == {ARRAY_REF}:
        return {"array_ref": value[ARRAY_REF]}
    if isinstance(value, dict) and set(value) == {TUPLE_REF}:
        return {"tuple_len": len(value[TUPLE_REF])}
    if isinstance(value, list):
        return {"list_len": len(value)}
    return {"scalar_type": scalar_kind(value)}


def run(output: Path) -> dict[str, Any]:
    seal_path = OBS / "observed_seal.json"
    seal_bytes = seal_path.read_bytes()
    seal_sha = hashlib.sha256(seal_bytes).hexdigest()
    require(seal_sha == SEAL_SHA256, "local observed seal hash differs from committed seal")
    repo = ROOT.parents[1]  # .../my-vault
    seal_repo_path = "00_Inbox/AFDM-channel-estimation/results/tf_cgr_mechanism_20260923_v2/observed/observed_seal.json"
    show = subprocess.run(["git", "-C", str(repo), "show", f"{SEAL_COMMIT}:{seal_repo_path}"],
                          check=True, capture_output=True)
    require(show.stdout == seal_bytes, "seal commit blob bytes differ from local sealed run")
    require(subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                            SEAL_COMMIT, "HEAD"], check=False).returncode == 0,
            "seal commit is not an ancestor of current HEAD")

    seal = json.loads(seal_bytes)
    require(seal.get("schema") == "tf-cgr-observed/1" and seal.get("status") == "pass" and
            seal.get("completed_calls") == 100, "seal status/call count differs")
    sealed = seal.get("files", {})
    require(len(sealed) == 474, f"expected 474 sealed files; got {len(sealed)}")
    extras_on_disk = sorted(str(p.relative_to(OBS)) for top in ("checkpoints", "raw", "decisions")
                            for p in (OBS / top).glob("*") if p.is_file())
    expected_files = set(sealed)
    require(set(extras_on_disk) == expected_files - {"manifest.json", "ledger.jsonl"},
            "sealed file path inventory differs from local output directories")
    file_inventory = []
    total_bytes = 0
    for rel, expected_hash in sorted(sealed.items()):
        path = safe_observed_file(rel)
        digest = sha256(path)
        require(digest == expected_hash, f"sealed SHA mismatch: {rel}")
        size = path.stat().st_size
        total_bytes += size
        file_inventory.append({"path": rel, "sha256": digest, "bytes": size})

    manifest = json.loads(safe_observed_file("manifest.json").read_text())
    witnesses = json.loads(WITNESS.read_text())
    ledger_lines = safe_observed_file("ledger.jsonl").read_text().splitlines()
    ledger = [json.loads(line) for line in ledger_lines]
    require(len(ledger) == 100, "ledger row count differs from 100")
    require(manifest.get("schema") == seal["schema"] and manifest.get("expected_calls") == 100,
            "observed manifest differs from seal")
    require(witnesses.get("schema") == "coherent-gain-witness-request/1" and
            len(witnesses.get("entries", [])) == 25, "witness manifest differs from fixed packet")
    ids_by_role: dict[str, set[str]] = {}
    entries = {}
    for entry in witnesses["entries"]:
        oid, role = entry["observation_id"], entry["role"]
        ids_by_role.setdefault(role, set()).add(oid)
        entries[oid] = entry
    require(ids_by_role.get("target_remaining_failure") == TARGETS, "target IDs differ")
    require(ids_by_role.get("matched_rescued_control") == RESCUED, "rescued control IDs differ")
    require(ids_by_role.get("distinct_delay_failure_specificity") == DISTINCT, "distinct controls differ")
    require(ids_by_role.get("matched_easy_control") == EASY, "easy controls differ")
    require({row.get("call_index") for row in ledger} == set(range(1, 101)), "call indices not 1..100")

    raw_rows = []
    schemas: dict[str, Any] = {}
    arm_role_counts: dict[str, dict[str, int]] = {}
    category_state_summaries: dict[str, Any] = {}
    ledger_by_pair = {(r["observation_id"], r["arm"]): r for r in ledger}
    require(len(ledger_by_pair) == 100, "duplicate ledger pair")
    for oid in sorted(entries):
        entry = entries[oid]
        role = entry["role"]
        category = {
            "target_remaining_failure": "target",
            "matched_rescued_control": "triggered_rescued_control",
            "distinct_delay_failure_specificity": "triggered_distinct_delay_control",
            "matched_easy_control": "easy_bypass_control",
        }[role]
        for arm in ARMS:
            pair = (oid, arm)
            row = ledger_by_pair[pair]
            rel = row["raw_path"]
            raw_path = safe_observed_file(rel)
            raw_sha = sha256(raw_path)
            require(raw_sha == row["raw_sha256"] == sealed[rel], f"raw SHA link mismatch: {rel}")
            schema, decoded = inspect_npz(raw_path)
            payload = decoded["payload"]
            schema_hash = hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            schemas.setdefault(schema_hash, schema)

            detector = payload.get("branch_detector")
            states = detector.get("states") if isinstance(detector, dict) else None
            trace = detector.get("trace") if isinstance(detector, dict) else None
            state_count = len(states) if isinstance(states, list) else None
            trace_count = len(trace) if isinstance(trace, list) else None
            state_field_sets = []
            if isinstance(states, list):
                for state in states:
                    state_field_sets.append(sorted(state) if isinstance(state, dict) else [])
                require(len(set(map(tuple, state_field_sets))) <= 1,
                        f"state key set varies within {oid}/{arm}")
            trace_iterations = [r.get("iteration") for r in trace if isinstance(r, dict)] if isinstance(trace, list) else []
            trace_keys = sorted({k for r in trace if isinstance(r, dict) for k in r}) if isinstance(trace, list) else []
            trace_wallclock_fields = sorted({k for r in trace if isinstance(r, dict) for k in r
                                             if "second" in k or "time" in k.lower()}) if isinstance(trace, list) else []
            decoder = payload.get("branch_decoder")
            decoder_incoming = field_descriptor(decoder, "incoming_llr") if isinstance(decoder, dict) else None
            incoming_ref = decoder_incoming.get("array_ref") if isinstance(decoder_incoming, dict) else None
            incoming_header = schema["array_headers"].get(incoming_ref) if incoming_ref else None
            vector_headers = {}
            for field_name in VECTOR_STATE_FIELDS + ("S",):
                physical_key = f"branch_detector_states_0_{field_name}"
                if physical_key in schema["array_headers"]:
                    vector_headers[field_name] = schema["array_headers"][physical_key]
            detector_headers = {
                name: schema["array_headers"].get(f"branch_detector_{name}")
                for name in ("app", "extrinsic", "mu", "variance", "gain_covariance")
                if f"branch_detector_{name}" in schema["array_headers"]
            }
            base_common = payload.get("base_common_state")
            native_timing = payload.get("native_timing") or {}
            native_events = native_timing.get("events", []) if isinstance(native_timing, dict) else []
            native_timing_rows = [{k: event.get(k) for k in
                                   ("round", "ready", "ce", "inference", "decoder",
                                    "ce_evaluations", "inference_iterations", "decoder_iterations")
                                   if k in event} for event in native_events]
            row_summary = {
                "observation_id": oid,
                "role": role,
                "category": category,
                "arm": arm,
                "triggered": row.get("triggered"),
                "status": row.get("status"),
                "call_index": row.get("call_index"),
                "raw_path": rel,
                "raw_sha256": raw_sha,
                "payload_keys": sorted(payload),
                "schema_sha256": schema_hash,
                "states_count": state_count,
                "state_fields": state_field_sets[0] if state_field_sets else None,
                "state_vector_fields_available": [key for key in VECTOR_STATE_FIELDS
                                                   if state_field_sets and key in state_field_sets[0]],
                "full_vector_history_available": bool(state_field_sets and
                    set(VECTOR_STATE_FIELDS).issubset(state_field_sets[0])),
                "branch_detector_keys": sorted(detector) if isinstance(detector, dict) else None,
                "branch_detector_terminal_array_headers": detector_headers,
                "block_state_S_iteration0_header": vector_headers.get("S"),
                "trace_count": trace_count,
                "trace_iterations": trace_iterations,
                "trace_keys": trace_keys,
                "trace_has_wallclock_fields": trace_wallclock_fields,
                "branch_timing_seconds": {k: row.get(k) for k in
                    ("branch_elapsed_seconds", "branch_decision_seconds", "branch_complete_seconds")},
                "native_two_rounds_seconds": row.get("native_two_rounds_seconds"),
                "complete_latency_seconds": row.get("complete_latency_seconds"),
                "native_timing_events": native_timing_rows,
                "branch_decoder_incoming_llr": decoder_incoming,
                "branch_decoder_incoming_llr_header": incoming_header,
                "iteration0_vector_field_headers": vector_headers,
                "branch_decoder_keys": sorted(decoder) if isinstance(decoder, dict) else None,
                "base_common_state_count": len(base_common) if isinstance(base_common, list) else None,
                "base_common_state_fields": sorted(base_common[0]) if isinstance(base_common, list) and base_common else None,
            }
            raw_rows.append(row_summary)
            arm_role_counts.setdefault(category, {}).setdefault(arm, 0)
            arm_role_counts[category][arm] += 1
            category_state_summaries.setdefault(category, {}).setdefault(arm, {
                "triggered_values": set(), "state_counts": set(), "trace_counts": set(),
                "state_field_sets": set(), "base_common_state_counts": set(),
                "incoming_llr_descriptors": set(), "trace_wallclock_fields": set(),
            })
            c = category_state_summaries[category][arm]
            c["triggered_values"].add(row.get("triggered"))
            c["state_counts"].add(state_count)
            c["trace_counts"].add(trace_count)
            c["state_field_sets"].add(tuple(state_field_sets[0]) if state_field_sets else ())
            c["base_common_state_counts"].add(len(base_common) if isinstance(base_common, list) else None)
            c["incoming_llr_descriptors"].add(json.dumps(decoder_incoming, sort_keys=True))
            c["trace_wallclock_fields"].add(tuple(trace_wallclock_fields))

    # Make aggregate sets JSON-serializable and verify expected branch behavior.
    summary = {}
    for category, arms in category_state_summaries.items():
        summary[category] = {}
        for arm, record in arms.items():
            summary[category][arm] = {key: sorted(value, key=lambda x: str(x))
                                      for key, value in record.items()}
    for cat in ("target", "triggered_rescued_control", "triggered_distinct_delay_control", "easy_bypass_control"):
        require(arm_role_counts.get(cat) == {arm: {"target": 8, "triggered_rescued_control": 7,
                                                   "triggered_distinct_delay_control": 3,
                                                   "easy_bypass_control": 7}[cat]
                                             for arm in ARMS},
                f"per-arm cohort count differs: {cat}")

    target_rows = [r for r in raw_rows if r["category"] == "target"]
    target_full = [r for r in target_rows if r["arm"] == "BASE" and r["states_count"] == 20 and
                   set(VECTOR_STATE_FIELDS).issubset(r["state_vector_fields_available"]) and
                   r["trace_count"] == 20 and r["trace_iterations"] == list(range(20)) and
                   r["branch_decoder_incoming_llr"] is not None]
    require(len(target_full) == 8, f"expected eight full BASE target traces, found {len(target_full)}")
    control_rows = [r for r in raw_rows if r["category"] in
                    ("triggered_rescued_control", "triggered_distinct_delay_control")]
    require(all(r["states_count"] == 20 and
                not set(VECTOR_STATE_FIELDS).intersection(r["state_vector_fields_available"])
                for r in control_rows if r["arm"] == "BASE"),
            "a triggered control unexpectedly retained full vector state")
    easy_rows = [r for r in raw_rows if r["category"] == "easy_bypass_control"]
    require(all(r["triggered"] is False and r["states_count"] is None and
                r["branch_decoder_incoming_llr"] is None for r in easy_rows),
            "easy bypass rows unexpectedly contain triggered branch state/LLR")

    code_hashes = {}
    for label, relative in {
        "producer": "experiments/tf_cgr_mechanism_20260923_v2/run_observed.py",
        "tf_base": "experiments/tf_cgr_mechanism_20260923_v2/tf_base.py",
    }.items():
        path = ROOT / relative
        code_hashes[label] = {"path": relative, "sha256": sha256(path)}
    bindings_path = ROOT / "results/tf_cgr_mechanism_20260923_v2/qualification/source_bindings_v1.json"
    bindings = json.loads(bindings_path.read_text())
    require(code_hashes["producer"]["sha256"] == bindings["cgr/run_observed.py"],
            "producer source hash differs from frozen source binding")
    require(code_hashes["tf_base"]["sha256"] == bindings["cgr/tf_base.py"],
            "TF source hash differs from frozen source binding")
    producer_text = (ROOT / code_hashes["producer"]["path"]).read_text()
    tf_base_text = (ROOT / code_hashes["tf_base"]["path"]).read_text()
    producer_compact = re.sub(r"\s+", "", producer_text)
    scalar_key_literal = "keys=('h_pre','h','hbar','vx','alpha','vq','xbar_energy','vr','vh','bar','vp','physical_R','gain_R')"
    require(scalar_key_literal in producer_compact and
            "if obs_id not in TARGET_IDS:" in producer_text and
            "branch_detector['states']=_scalar_states(branch_detector['states'])" in producer_text,
            "producer scalar-compaction savepoint differs from inspected contract")
    require("iterations=20,damping=.3,gain_mode='joint'" in producer_text and
            "if record_states:states.append(dict(h_pre=h_pre,h=h.copy(),hbar=hb.copy(),x=x.copy(),xbar=xb.copy(),mu=mu.copy(),v=v.copy(),s=s.copy(),rx=rx.copy(),app=app.copy(),extrinsic=ext.copy()" in tf_base_text,
            "TF full-state savepoint differs from inspected contract")

    result = {
        "schema": "tf-cgr-offline-mechanism-raw-inventory/1",
        "truth_payloads_opened": False,
        "receiver_or_generator_or_optimizer_calls": 0,
        "seal": {"path": str(seal_path.relative_to(ROOT)), "sha256": seal_sha,
                 "commit": SEAL_COMMIT, "commit_blob_byte_identical": True,
                 "commit_is_ancestor_of_HEAD": True,
                 "listed_files": len(sealed), "listed_bytes": total_bytes,
                 "hash_mismatches": 0},
        "cohorts": {role: sorted(ids) for role, ids in ids_by_role.items()},
        "per_category_per_arm_raw_count": arm_role_counts,
        "per_category_per_arm_schema_summary": summary,
        "unique_raw_schema_count": len(schemas),
        "unique_raw_schemas": schemas,
        "raw_records": raw_rows,
        "savepoint_source_binding": code_hashes,
        "savepoint_source_contract": {
            "branch_configuration": "20 iterations, damping=0.3, gain_mode='joint', record_states=True",
            "full_tf_state_fields_before_compaction": ["h_pre", "h", "hbar", "x", "xbar", "mu", "v", "s", "rx", "app", "extrinsic", "vx", "vr", "vq", "vh", "alpha", "sv", "bar", "vp", "xbar_energy", "gain_R", "physical_R"],
            "non_target_per_state_retained_fields": ["h_pre", "h", "hbar", "vx", "alpha", "vq", "xbar_energy", "vr", "vh", "bar", "vp", "physical_R", "gain_R"],
            "non_target_compaction_applies_to": "all non-target triggered raw artifacts; per-state BLOCK S is removed by this compaction",
            "block_top_level_gain_covariance": "retained separately as branch_detector.gain_covariance; raw dtype/shape is inventoried",
            "source_checked_at_runtime": True,
        },
        "field_identifiability": {
            "target_BASE_full_20_step_state_and_terminal_llr": {
                "count": len(target_full), "ids": sorted(r["observation_id"] for r in target_full),
                "fields": list(VECTOR_STATE_FIELDS), "states_and_trace_rows": 20,
                "trace_rows_are_iteration-indexed_not_wallclock_timed": True,
                "terminal_branch_llr": "branch_decoder.incoming_llr; archive gives dtype/shape only in this inventory",
            },
            "triggered_controls_BASE": {
                "count": len({r["observation_id"] for r in control_rows if r["arm"] == "BASE"}),
                "states_and_trace_rows": 20,
                "available_state_fields": "h_pre/h/hbar, selected scalar moments, physical_R, gain_R; BLOCK per-state S is cropped; top-level gain_covariance is retained; see raw_records and unique schemas",
                "unavailable_vector_fields": list(VECTOR_STATE_FIELDS),
                "terminal_arrays_not_history": "branch_detector app/extrinsic/mu/variance and branch_decoder.incoming_llr remain terminal arrays only, not per-step vector history",
                "base_common_state": "when present, derived dh/norm/reciprocal precision only; does not restore x/mu/v/s/rx/app/extrinsic vectors",
                "full_vector_history_reconstructible": False,
            },
            "easy_bypass_controls": {
                "count": len({r["observation_id"] for r in easy_rows}),
                "all_four_arms_nontriggered": True,
                "branch_states_and_terminal_branch_llr": "unavailable; branch bypassed",
                "can_support_forced_CGR_or_BLOCK_safety_claim": False,
            },
            "iteration_timing": {
                "raw_tf_trace": "iteration diagnostic rows only; no per-iteration wall-clock field found",
                "raw_native_timing": "two native-round aggregate ready/CE/inference/decoder clocks",
                "observed_ledger": "branch_elapsed_seconds, branch_decision_seconds, branch_complete_seconds, native_two_rounds_seconds, complete_latency_seconds, and exclusive stage timings",
            },
        },
        "inventory": file_inventory,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "observed_raw_inventory.json")
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"output": str(args.output), "sealed_files": result["seal"]["listed_files"],
                      "sealed_bytes": result["seal"]["listed_bytes"],
                      "raw_records": len(result["raw_records"]),
                      "unique_raw_schemas": result["unique_raw_schema_count"],
                      "target_BASE_full_traces": result["field_identifiability"][
                          "target_BASE_full_20_step_state_and_terminal_llr"]["count"],
                      "truth_payloads_opened": False}, sort_keys=True))


if __name__ == "__main__":
    main()
