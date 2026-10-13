"""One-pass independent recount of the sealed 256-frame, three-arm study."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from verify_saved import (
    ARMS, FRAMES, compose_final_gates, load_sealed_artifact,
    logloss_recount, outcome_recount, sha256_bytes, sha256_file,
    transport_recount, verify_call_ledgers, verify_inventory,
    verify_prediction_cohort, verify_stream_freshness,
)

PROJECT = Path(__file__).resolve().parents[3]
RESULT = PROJECT / "results/tf_cgr_prospective_mechanism_20260923"
PROTOCOL = PROJECT / ".trellis/tasks/09-22-tf-production-gap-audit/cgr-prospective-mechanism.md"
SCHEMA = "tf-cgr-prospective-mechanism/1"
OLD_NAMESPACE = PROJECT / "results/tf_cstate_prospective_20260923/protocol/random_namespace.json"
CODE_CACHE = PROJECT / "afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"


def _json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def _safe(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ValueError(f"unsafe artifact path: {relative}")
    result = (root / rel).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"artifact path escapes sealed root: {relative}")
    return result


def _exact_tree(left: Any, right: Any, label: str) -> None:
    if isinstance(left, np.ndarray):
        if not isinstance(right, np.ndarray) or left.dtype != right.dtype or left.shape != right.shape or not np.array_equal(left, right):
            raise ValueError(f"saved paired array differs: {label}")
    elif isinstance(left, dict):
        if not isinstance(right, dict) or set(left) != set(right):
            raise ValueError(f"saved paired mapping differs: {label}")
        for key in left:
            _exact_tree(left[key], right[key], f"{label}/{key}")
    elif isinstance(left, (list, tuple)):
        if not isinstance(right, type(left)) or len(left) != len(right):
            raise ValueError(f"saved paired sequence differs: {label}")
        for i, (x, y) in enumerate(zip(left, right)):
            _exact_tree(x, y, f"{label}/{i}")
    elif left != right:
        raise ValueError(f"saved paired scalar differs: {label}")


def _frame_id(frame: int) -> str:
    return f"cgrp_s650_f{frame:04d}"


def _stream_ids(entropy: str, domain: int, frame: int) -> dict[str, str]:
    words = [int(x) for x in np.frombuffer(bytes.fromhex(entropy), dtype="<u4")]
    result = {}
    for name, component in (("channel", 1), ("message", 2), ("noise", 3)):
        payload = [*words, domain, 650, frame, component]
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        result[name] = hashlib.sha256(raw).hexdigest()
    return result


def _registered_order(entropy: str) -> list[dict]:
    words = [int(x) for x in np.frombuffer(bytes.fromhex(entropy), dtype="<u4")]
    rng = np.random.default_rng(np.random.SeedSequence(
        [*words, 0x43475250, 650, 0, 4]))
    first = set(int(index) for index in rng.permutation(FRAMES)[: FRAMES // 2])
    return [dict(frame=frame, arms=["CGR", "SHAM"] if frame in first
                 else ["SHAM", "CGR"]) for frame in range(FRAMES)]


def _all_streams(namespace_path: Path, *, old: bool = False) -> list[str]:
    lock = _json(namespace_path)
    entropy = lock["entropy_hex"]
    if not old:
        return [sid for frame in range(FRAMES)
                for sid in _stream_ids(entropy, 0x43475250, frame).values()]
    return [sid for snr in (600, 650, 700) for frame in range(1024)
            for sid in {
                name: hashlib.sha256(json.dumps(
                    [*map(int, np.frombuffer(bytes.fromhex(entropy), dtype="<u4")),
                     0x43535441, snr, frame, component],
                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                for name, component in (("channel", 1), ("message", 2), ("noise", 3))
            }.values()]


def _resolve_commit(repo: Path, commit: str) -> str:
    if not commit or any(ch not in "0123456789abcdef" for ch in commit) or len(commit) < 8:
        raise ValueError("commit identifier must be hexadecimal and at least 8 characters")
    output = subprocess.run(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"],
                            cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
    if len(output) != 40:
        raise ValueError("unexpected Git object format")
    return output


def _git_bytes(repo: Path, commit: str, path: str, expected_sha: str, local: Path) -> dict:
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise ValueError("unsafe Git evidence path")
    saved = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=repo,
                           check=True, capture_output=True).stdout
    saved_sha, local_sha = sha256_bytes(saved), sha256_file(local)
    if saved_sha != expected_sha or local_sha != expected_sha or saved != local.read_bytes():
        raise ValueError(f"committed Git bytes differ from sealed local file: {path}")
    return {"path": path, "sha256": saved_sha}


def _verify_git_chain(root: Path, repo: Path, protocol_commit_arg: str) -> dict:
    protocol = root / "protocol"
    registration = _json(protocol / "registration.json")
    reg_attest = _json(protocol / "registration_attestation.json")
    pred_handoff = _json(protocol / "prediction_handoff.json")
    observed_handoff = _json(protocol / "observed_handoff.json")
    protocol_commit = _resolve_commit(repo, protocol_commit_arg)
    reg_commit = _resolve_commit(repo, reg_attest["registration_commit"])
    pred_commit = _resolve_commit(repo, pred_handoff["prediction_commit"])
    observed_commit = _resolve_commit(repo, observed_handoff["observed_commit"])
    commits = [protocol_commit, reg_commit, pred_commit, observed_commit]
    for older, newer in zip(commits, commits[1:]):
        subprocess.run(["git", "merge-base", "--is-ancestor", older, newer],
                       cwd=repo, check=True, capture_output=True)

    protocol_rel = PROTOCOL.resolve().relative_to(repo.resolve()).as_posix()
    protocol_blob = _git_bytes(repo, protocol_commit, protocol_rel,
                               registration["protocol_sha256"], PROTOCOL)
    if reg_attest.get("registration_sha256") != sha256_file(protocol / "registration.json"):
        raise ValueError("registration attestation does not bind registration bytes")
    attested = reg_attest["git_blobs"]
    for path, claimed in attested.items():
        local = (repo / path).resolve()
        if not local.is_relative_to(repo.resolve()):
            raise ValueError("registration attestation path escapes repository")
        _git_bytes(repo, reg_commit, path, claimed, local)

    base_seal = root / "observed/base/observed_seal.json"
    pred_seal = root / "prediction/prediction_seal.json"
    observed_seal = root / "observed/observed_seal.json"
    truth_seal = root / "truth/truth_seal.json"
    base_rel = base_seal.resolve().relative_to(repo.resolve()).as_posix()
    pred_rel = pred_seal.resolve().relative_to(repo.resolve()).as_posix()
    observed_rel = observed_seal.resolve().relative_to(repo.resolve()).as_posix()
    truth_rel = truth_seal.resolve().relative_to(repo.resolve()).as_posix()
    if pred_handoff["registration_commit"] != reg_commit or pred_handoff["prediction_seal_sha256"] != sha256_file(pred_seal):
        raise ValueError("prediction handoff commit or seal hash differs")
    if (pred_handoff.get("registration_sha256") != sha256_file(protocol / "registration.json") or
            pred_handoff.get("base_seal_sha256") != sha256_file(base_seal)):
        raise ValueError("prediction handoff does not bind registration and BASE seal")
    if observed_handoff["registration_commit"] != reg_commit or observed_handoff["prediction_commit"] != pred_commit:
        raise ValueError("observed handoff ancestor commits differ")
    if (observed_handoff.get("registration_sha256") != sha256_file(protocol / "registration.json") or
            observed_handoff.get("prediction_seal_sha256") != sha256_file(pred_seal)):
        raise ValueError("observed handoff does not bind registration and prediction seal")
    if observed_handoff["observed_seal_sha256"] != sha256_file(observed_seal) or observed_handoff["truth_seal_sha256"] != sha256_file(truth_seal):
        raise ValueError("observed handoff seal hashes differ")
    pred_path = pred_handoff["prediction_seal_git_path"]
    obs_path = observed_handoff["observed_seal_git_path"]
    tr_path = observed_handoff["truth_seal_git_path"]
    if (pred_path != pred_rel or obs_path != observed_rel or tr_path != truth_rel or
            pred_handoff.get("prediction_seal_sha256") != sha256_file(pred_seal)):
        raise ValueError("handoff Git paths do not name the canonical seal files")
    git_blobs = [protocol_blob]
    git_blobs.extend(_git_bytes(repo, pred_commit, path, sha256_file(file), file)
                     for path, file in ((base_rel, base_seal), (pred_path, pred_seal)))
    git_blobs.extend(_git_bytes(repo, observed_commit, path, sha256_file(file), file)
                     for path, file in ((obs_path, observed_seal), (tr_path, truth_seal)))
    return {"status": "pass", "protocol_commit": protocol_commit,
            "registration_commit": reg_commit, "prediction_commit": pred_commit,
            "observed_commit": observed_commit, "ordered_ancestors": True,
            "verified_blobs": git_blobs}


def _phase(root: Path, seal_name: str, expected_calls: int) -> tuple[dict, list[dict], dict]:
    seal_path = root / seal_name
    inventory = verify_inventory(root, seal_path)
    seal = _json(seal_path)
    rows = _jsonl(root / "ledger.jsonl")
    if seal.get("schema") != SCHEMA or seal.get("status") != "pass":
        raise ValueError(f"invalid seal schema/status: {root}")
    if len(rows) != expected_calls:
        raise ValueError(f"ledger row count differs: {root}")
    count_field = "frames" if root.name in ("population", "prediction", "truth") else "completed_calls"
    if seal.get(count_field) != expected_calls:
        raise ValueError(f"sealed phase count differs: {root}")
    return seal, rows, inventory


def _artifact(evidence_path: Path, digest: str, identity: dict | None = None) -> tuple[dict, dict]:
    payload, metadata = load_sealed_artifact(evidence_path, digest, identity)
    if not isinstance(payload, dict):
        raise ValueError(f"artifact payload must be a mapping: {evidence_path}")
    return payload, metadata


def recount(root: Path, protocol_commit: str) -> dict:
    root = Path(root).resolve()
    repo = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=PROJECT,
                               check=True, capture_output=True, text=True).stdout.strip())
    protocol = root / "protocol"
    lock, namespace = _json(protocol / "registration.json"), _json(protocol / "random_namespace.json")
    if (lock.get("schema") != SCHEMA or lock.get("status") != "locked" or
            lock.get("population") != {"snr_centi_db": 650, "frames": FRAMES} or
            lock.get("arms") != list(ARMS) or lock.get("new_attempt_cap") != 768 or
            lock.get("protocol_sha256") != sha256_file(PROTOCOL) or
            lock.get("namespace_sha256") != sha256_file(protocol / "random_namespace.json") or
            lock.get("source_bindings_sha256") != sha256_file(protocol / "source_bindings.json")):
        raise ValueError("frozen registration/schema binding differs")
    # No truth ledger or payload is opened before this actual Git-object check.
    git_proof = _verify_git_chain(root, repo, protocol_commit)

    observed = root / "observed"
    population = observed / "population"
    base_root = observed / "base"
    interventions = observed / "interventions"
    prediction = root / "prediction"
    truth_root = root / "truth"
    pop_seal, pop_rows, pop_inventory = _phase(population, "observed_seal.json", FRAMES)
    base_seal, base_rows, base_inventory = _phase(base_root, "observed_seal.json", FRAMES)
    int_seal, int_rows, int_inventory = _phase(interventions, "observed_seal.json", 2 * FRAMES)
    pred_seal, pred_rows, pred_inventory = _phase(prediction, "prediction_seal.json", FRAMES)
    observed_seal_path = observed / "observed_seal.json"
    observed_inventory = verify_inventory(observed, observed_seal_path)
    observed_seal = _json(observed_seal_path)
    if (observed_seal.get("schema") != SCHEMA or observed_seal.get("status") != "pass" or
            observed_seal.get("completed_calls") != 768 or
            observed_seal.get("truth_unopened") is not True or
            observed_seal.get("prediction_commit") != git_proof["prediction_commit"] or
            observed_seal.get("registration_sha256") != sha256_file(protocol / "registration.json")):
        raise ValueError("final observed seal does not bind the fixed unopened-truth phase")
    if (observed_seal.get("population_seal_sha256") != sha256_file(population / "observed_seal.json") or
            observed_seal.get("base_seal_sha256") != sha256_file(base_root / "observed_seal.json") or
            observed_seal.get("intervention_seal_sha256") != sha256_file(interventions / "observed_seal.json") or
            observed_seal.get("prediction_seal_sha256") != sha256_file(prediction / "prediction_seal.json")):
        raise ValueError("global observed seal child-hash binding differs")
    registration_sha = sha256_file(protocol / "registration.json")
    expected_children = (
        (pop_seal, {"registration_sha256": registration_sha}),
        (base_seal, {"registration_sha256": registration_sha,
                     "population_seal_sha256": sha256_file(population / "observed_seal.json")}),
        (pred_seal, {"registration_sha256": registration_sha,
                     "base_seal_sha256": sha256_file(base_root / "observed_seal.json")}),
        (int_seal, {"registration_sha256": registration_sha,
                    "population_seal_sha256": sha256_file(population / "observed_seal.json"),
                    "base_seal_sha256": sha256_file(base_root / "observed_seal.json"),
                    "prediction_seal_sha256": sha256_file(prediction / "prediction_seal.json")}),
    )
    for seal, expected in expected_children:
        if any(seal.get(key) != value for key, value in expected.items()):
            raise ValueError("phase seal parent/registration binding differs")

    schedule = lock["schedule"]
    if len(schedule) != FRAMES or [item["frame"] for item in schedule] != list(range(FRAMES)):
        raise ValueError("registered schedule frame order differs")
    if schedule != _registered_order(namespace["entropy_hex"]):
        raise ValueError("registered arm schedule differs from its independent SeedSequence")
    order = [tuple(item["arms"]) for item in schedule]
    def normalized(rows):
        return [dict(call_index=r["call_index"], frame_index=r["frame"], arm=r["arm"],
                     status=r["status"], input_sha256=r["input_sha256"]) for r in rows]
    call_counts = verify_call_ledgers(normalized(base_rows), normalized(int_rows), order)
    if ([r["frame"] for r in pop_rows] != list(range(FRAMES)) or
            [r["frame"] for r in base_rows] != list(range(FRAMES)) or
            [r["frame"] for r in pred_rows] != list(range(FRAMES)) or
            [r["call_index"] for r in base_rows] != list(range(1, FRAMES + 1)) or
            [r["call_index"] for r in int_rows] != list(range(FRAMES + 1, 3 * FRAMES + 1))):
        raise ValueError("frame order/global call index differs")
    pop_map = {r["frame"]: r for r in pop_rows}
    base_map = {r["frame"]: r for r in base_rows}
    pred_map = {r["frame"]: r for r in pred_rows}
    int_map = {(r["frame"], r["arm"]): r for r in int_rows}
    if len(int_map) != 2 * FRAMES:
        raise ValueError("duplicate intervention arm/frame")
    for frame in range(FRAMES):
        stem = _frame_id(frame)
        if (pop_map[frame]["observation_id"] != stem or base_map[frame]["observation_id"] != stem or
                pred_map[frame]["observation_id"] != stem or
                any(int_map[frame, arm]["observation_id"] != stem for arm in ("CGR", "SHAM"))):
            raise ValueError("registered observation frame identity differs")
        for row in [base_map[frame], int_map[frame, "CGR"], int_map[frame, "SHAM"]]:
            if row["input_sha256"] != pop_map[frame]["observation_sha256"]:
                raise ValueError("wrapper input hash differs from the sealed population")

    # New namespace/stream identities are recomputed and compared with the old 3072 cohort.
    entropy = namespace["entropy_hex"]
    if (len(entropy) != 64 or namespace.get("domain") != 0x43475250 or
            namespace.get("campaign") != "tf_cgr_prospective_mechanism_20260923"):
        raise ValueError("CGR prospective namespace differs")
    new_streams, old_streams = _all_streams(protocol / "random_namespace.json"), _all_streams(OLD_NAMESPACE, old=True)
    stream_freshness = verify_stream_freshness(new_streams, old_streams)
    for frame in range(FRAMES):
        expected_streams = _stream_ids(entropy, 0x43475250, frame)
        if pop_map[frame]["stream_ids"] != expected_streams:
            raise ValueError(f"new registered stream ids differ at frame {frame}")

    # Only sealed observed/base/prediction artifacts are opened in this block.
    raw_by = {}
    observation_payloads = {}
    for frame in range(FRAMES):
        p_row = pop_map[frame]
        p_identity = dict(schema=SCHEMA, kind="observed", observation_id=_frame_id(frame),
                          registration_sha256=sha256_file(protocol / "registration.json"))
        obs_payload, _ = _artifact(_safe(population, p_row["observation_path"]),
                                   p_row["observation_sha256"], p_identity)
        if (obs_payload["observation_id"] != _frame_id(frame) or
                obs_payload["stream_ids"] != p_row["stream_ids"] or
                obs_payload["observation_hash"] != p_row["observation_hash"]):
            raise ValueError("observed population envelope identity differs")
        observation_payloads[frame] = obs_payload
        for arm, row, phase_root in (("BASE", base_map[frame], base_root),
                                     ("CGR", int_map[frame, "CGR"], interventions),
                                     ("SHAM", int_map[frame, "SHAM"], interventions)):
            identity = dict(schema=SCHEMA, observation_id=_frame_id(frame), arm=arm,
                            phase="base" if arm == "BASE" else "interventions")
            raw, _ = _artifact(_safe(phase_root, row["raw_path"]), row["raw_sha256"], identity)
            raw_by[frame, arm] = raw

    # Prediction vectors and eligibility are recalculated from frozen BASE R plus saved vectors.
    cohort_rows, transport_rows = [], []
    for frame in range(FRAMES):
        base = raw_by[frame, "BASE"]
        vector_row = pred_map[frame]
        vector, _ = _artifact(_safe(prediction, vector_row["vector_path"]),
                              vector_row["vector_sha256"],
                              dict(schema=SCHEMA, kind="prediction", observation_id=_frame_id(frame),
                                   registration_sha256=sha256_file(protocol / "registration.json")))
        if (vector["frame"] != frame or vector["observation_id"] != _frame_id(frame) or
                vector["input_sha256"] != pop_map[frame]["observation_sha256"] or
                vector["base_raw_sha256"] != base_map[frame]["raw_sha256"] or
                vector["input_sha256"] != vector_row["input_sha256"] or
                vector["base_raw_sha256"] != vector_row["base_raw_sha256"]):
            raise ValueError("prediction vector is not bound to its BASE/input artifacts")
        for key in ("reaction_max", "clip_boundary_count", "floor_boundary_count",
                    "final_gain_impulse_zero"):
            if vector[key] != vector_row[key]:
                raise ValueError(f"prediction ledger/vector differs in {key} at frame {frame}")
        names = {
            "predicted": {"CGR": "predicted_CGR_unclipped_llr_shift", "SHAM": "predicted_SHAM_unclipped_llr_shift"},
            "predicted_clipped": {"CGR": "predicted_CGR_clipped_llr_shift", "SHAM": "predicted_SHAM_clipped_llr_shift"},
        }
        predicted = {kind: {arm: vector[key] for arm, key in arms.items()} for kind, arms in names.items()}
        predicted_norms = {arm: float(np.linalg.norm(predicted["predicted"][arm])) for arm in ("CGR", "SHAM")}
        triggered = bool(base["triggered"])
        branch_ok = triggered and base["numerical_failure"] is None and base["branch_detector"] is not None and base["branch_decoder"] is not None
        reaction = 0.0
        if branch_ok:
            R = np.asarray(base["gram"]["R"])
            reaction = float(np.max(np.abs(R - np.eye(R.shape[0]))))
        expected_eligible = triggered and branch_ok and reaction > 1e-10 and all(x > 1e-8 for x in predicted_norms.values())
        expected_reason = None if expected_eligible else (
            "native_bypass" if not triggered else
            "zero_physical_reaction" if branch_ok and reaction <= 1e-10 else
            "numerical_zero_prediction" if branch_ok else "base_branch_failure")
        if (bool(vector["eligible"]) != expected_eligible or
                vector["exclusion_reason"] != expected_reason or
                vector["eligible"] != vector_row["eligible"] or
                vector["exclusion_reason"] != vector_row["exclusion_reason"] or
                vector["final_gain_impulse_zero"] is not True):
            raise ValueError(f"sealed prediction cohort/reason differs at frame {frame}")
        for arm in ("CGR", "SHAM"):
            if (not np.isclose(predicted_norms[arm], vector[f"predicted_{arm}_norm"], rtol=1e-12, atol=1e-12) or
                    not np.isclose(predicted_norms[arm], vector_row[f"predicted_{arm}_norm"], rtol=1e-12, atol=1e-12)):
                raise ValueError(f"saved prediction norm differs at frame {frame}/{arm}")
        if not np.isclose(reaction, vector["reaction_max"], rtol=1e-12, atol=1e-12):
            raise ValueError(f"BASE physical reaction differs at frame {frame}")
        cohort_rows.append(dict(frame_index=frame, base_triggered=triggered,
            base_branch_success=branch_ok, max_abs_R_minus_I=reaction,
            predicted_norms=predicted_norms, eligible=bool(vector["eligible"]),
            predicted=predicted["predicted"], predicted_clipped=predicted["predicted_clipped"]))

        actual, actual_clipped = {}, {}
        for arm in ("CGR", "SHAM"):
            arm_raw = raw_by[frame, arm]
            if arm_raw["triggered"] != triggered:
                raise ValueError(f"native trigger differs from BASE at frame {frame}/{arm}")
            if branch_ok:
                if arm_raw["numerical_failure"] is not None or arm_raw["branch_detector"] is None or arm_raw["branch_decoder"] is None:
                    raise ValueError(f"intervention branch missing/fallback at frame {frame}/{arm}")
                actual[arm] = np.asarray(arm_raw["branch_detector"]["extrinsic"]) - np.asarray(base["branch_detector"]["extrinsic"])
                actual_clipped[arm] = np.asarray(arm_raw["branch_decoder"]["incoming_llr"]) - np.asarray(base["branch_decoder"]["incoming_llr"])
            else:
                actual[arm] = np.zeros(2048, dtype=np.float64)
                actual_clipped[arm] = np.zeros(2048, dtype=np.float64)
        transport_rows.append(dict(frame_index=frame, eligible=bool(vector["eligible"]),
            predicted=predicted["predicted"], actual=actual,
            predicted_clipped=predicted["predicted_clipped"], actual_clipped=actual_clipped))

    cohort = verify_prediction_cohort(cohort_rows)
    transport = transport_recount(transport_rows)

    # The truth gate is now open: all observed and prediction seals/blobs and their ancestry passed.
    truth_seal, truth_rows, truth_inventory = _phase(truth_root, "truth_seal.json", FRAMES)
    if (truth_seal.get("registration_sha256") != sha256_file(protocol / "registration.json") or
            truth_seal.get("truth_ledger_sha256") != sha256_file(truth_root / "ledger.jsonl") or
            observed_seal.get("truth_seal_sha256") != sha256_file(truth_root / "truth_seal.json")):
        raise ValueError("truth seal or ledger binding differs")
    if [r["frame"] for r in truth_rows] != list(range(FRAMES)):
        raise ValueError("truth frame order differs")
    if sha256_file(CODE_CACHE) != lock["code_cache_sha256"]:
        raise ValueError("actual frozen LDPC code cache SHA differs")
    with np.load(CODE_CACHE, allow_pickle=False) as archive:
        H, G, free_cols = np.asarray(archive["H"]), np.asarray(archive["G"]), np.asarray(archive["free_cols"])
    if hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest() != lock["code_g_sha256"]:
        raise ValueError("actual G bytes differ from registration")

    outcome_rows, llr_rows, deadlines = [], [], {0.5: {}, 1.0: {}}
    timing = {arm: {"complete": [], "branch_complete": []} for arm in ARMS}
    numerical_fallbacks = 0
    for frame in range(FRAMES):
        truth_row = truth_rows[frame]
        if (truth_row["observation_hash"] != pop_map[frame]["observation_hash"] or
                truth_row["stream_ids"] != pop_map[frame]["stream_ids"]):
            raise ValueError(f"truth/input identity differs at frame {frame}")
        truth, _ = _artifact(_safe(truth_root, truth_row["truth_path"]), truth_row["truth_sha256"],
            dict(schema=SCHEMA, kind="truth", observation_id=_frame_id(frame),
                 registration_sha256=sha256_file(protocol / "registration.json")))
        decoded, clipped = {}, {}
        for arm, phase_root, row in (("BASE", base_root, base_map[frame]),
                                     ("CGR", interventions, int_map[frame, "CGR"]),
                                     ("SHAM", interventions, int_map[frame, "SHAM"])):
            raw = raw_by[frame, arm]
            numerical_fallbacks += int(raw["numerical_failure"] is not None)
            _exact_tree(raw["native_arrays"], raw_by[frame, "BASE"]["native_arrays"], f"frame {frame}/{arm} native")
            if raw["triggered"] != raw_by[frame, "BASE"]["triggered"]:
                raise ValueError(f"trigger pairing differs at frame {frame}/{arm}")
            _exact_tree(raw["entering"], raw_by[frame, "BASE"]["entering"], f"frame {frame}/{arm} entering")
            branch_present = raw["branch_decoder"] is not None
            expected_checkpoints = 3 if branch_present else 2
            if len(row["checkpoints"]) != expected_checkpoints:
                raise ValueError(f"checkpoint count differs at frame {frame}/{arm}")
            final_decoder = raw["branch_decoder"] if branch_present else raw["native_decoder"]
            final_decoded = np.asarray(raw["final_decoded"])
            if not np.array_equal(final_decoded, final_decoder["decoded"]):
                raise ValueError(f"final saved decision differs at frame {frame}/{arm}")
            if branch_present:
                extrinsic = np.asarray(raw["branch_detector"]["extrinsic"])
                incoming = np.asarray(raw["branch_decoder"]["incoming_llr"])
                if not np.array_equal(np.clip(extrinsic, -20, 20), incoming):
                    raise ValueError(f"decoder input != clip(detector extrinsic) at frame {frame}/{arm}")
            else:
                incoming = np.asarray(raw["native_decoder"]["incoming_llr"])
                if not np.array_equal(incoming, np.asarray(raw["native_arrays"]["r1_input_llr"])):
                    raise ValueError(f"native decoder input differs from saved r1 input at frame {frame}/{arm}")
            decoded[arm] = final_decoded
            clipped[arm] = incoming
            timing[arm]["complete"].append(float(row["complete_latency_seconds"]))
            timing[arm]["branch_complete"].append(float(row["branch_complete_seconds"]))
            # Rehash and load every actual checkpoint for 0.5/1 s deadline recounts.
            checkpoint_payloads = []
            phase_name = "base" if arm == "BASE" else "interventions"
            for cp in row["checkpoints"]:
                cp_identity = dict(schema=SCHEMA, observation_id=_frame_id(frame), arm=arm,
                                   phase=phase_name, round=int(cp["round"]))
                cp_payload, _ = _artifact(_safe(phase_root, cp["path"]), cp["artifact_sha256"], cp_identity)
                checkpoint_payloads.append((float(cp["decision_ready_seconds"]), np.asarray(cp_payload["decoded"])))
            for deadline in deadlines:
                ready = [item for item in checkpoint_payloads if item[0] <= deadline]
                best = max(ready, key=lambda item: item[0])[1] if ready else None
                deadline_row = deadlines[deadline].setdefault(arm, {"ready": 0, "missing": 0, "info_error_frames": 0, "coded_error_frames": 0})
                if best is None:
                    deadline_row["missing"] += 1
                else:
                    deadline_row["ready"] += 1
                    deadline_row["info_error_frames"] += int(not np.array_equal(best[free_cols], truth["info"]))
                    deadline_row["coded_error_frames"] += int(not np.array_equal(best, truth["coded"]))
        outcome_rows.append(dict(frame_index=frame, truth_coded=truth["coded"], truth_info=truth["info"], decoded=decoded))
        llr_rows.append(dict(frame_index=frame, truth_coded=truth["coded"],
            eligible=bool(pred_map[frame]["eligible"]),
            base_triggered=bool(raw_by[frame, "BASE"]["triggered"]), clipped_final_llr=clipped))
    outcomes = outcome_recount(outcome_rows, H, G, free_cols)
    logloss = logloss_recount(llr_rows, analysis_seed=int(lock["analysis_seed"]))
    integrity = {
        "ordered_git_chain_and_actual_blobs": True,
        "all_phase_file_inventories": True,
        "256_frame_identity_and_streams": True,
        "768_attempt_order_and_pair_inputs": True,
        "native_prefix_and_entering_exact": True,
        "decoder_clip_boundary_and_saved_decisions": True,
        "prediction_mask_vectors_and_thresholds": True,
    }
    gates = compose_final_gates(integrity, transport, outcomes, logloss,
                                unexpected_fallbacks=numerical_fallbacks)
    def timing_summary(values: list[float]) -> dict:
        a = np.asarray(values, dtype=np.float64)
        return {"count": len(a), "mean_seconds": float(a.mean()),
                "p95_seconds": float(np.percentile(a, 95)), "max_seconds": float(a.max())}
    return {
        "schema": "tf-cgr-independent-recount/1", "status": "complete",
        "truth_values_read": True, "observed_git_proof": git_proof,
        "phase_inventory": {"population_observed": pop_inventory, "base": base_inventory,
            "prediction": pred_inventory, "interventions": int_inventory,
            "global_observed": observed_inventory, "truth": truth_inventory},
        "allocation": call_counts, "stream_freshness": stream_freshness,
        "cohort": cohort, "transport": transport, "outcomes": outcomes,
        "logloss": logloss, "deadlines": {str(k): v for k, v in deadlines.items()},
        "timing": {arm: {kind: timing_summary(vals) for kind, vals in data.items()}
                   for arm, data in timing.items()},
        "unexpected_numerical_fallbacks": numerical_fallbacks,
        "gates": gates,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=RESULT)
    parser.add_argument("--protocol-commit", required=True)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("recount_receipt.json"))
    args = parser.parse_args()
    report = recount(args.root, args.protocol_commit)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"], "frames": report["allocation"]["frames"],
                      "calls": report["allocation"]["calls"], "gates": report["gates"]}, indent=2))
