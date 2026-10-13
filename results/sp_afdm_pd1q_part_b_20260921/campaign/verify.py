"""Fail-closed validation of the fixed Part B saved attempt evidence."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from common import attach, expected, finite_seconds, identity, observation_hash, unbits


def validate_run(out, source, baseline, *, require_complete=False):
    out = Path(out).resolve()
    evidence = attach(source, baseline)
    manifest = json.loads((out / "manifest.json").read_text())
    if manifest["source_hashes"] != evidence.source_hashes(source):
        raise ValueError("source changed since run creation")
    if manifest["baseline_source_hashes"] != evidence.source_hashes(baseline):
        raise ValueError("baseline changed since run creation")
    from common import plan, script_hashes, seed_descriptor
    cfg = plan()
    if manifest["runner_hashes"] != script_hashes():
        raise ValueError("producer scripts changed since run creation")
    if manifest["plan_sha256"] != evidence.artifact_sha256(Path(__file__).with_name("plan.json")):
        raise ValueError("campaign plan changed")
    if manifest["source_root"] != str(Path(source).resolve()) or manifest["baseline_root"] != str(Path(baseline).resolve()):
        raise ValueError("root binding differs")
    if manifest["configurations"] != cfg["arms"]:
        raise ValueError("arm configurations differ")
    if manifest["stage"] != "PartB" or manifest["source_commit"] != cfg["source_commit"]:
        raise ValueError("Part B stage or frozen source commit differs")
    coordinates = [list(value) for value in expected(cfg)]
    root = out.parent
    if (manifest["statistical_contract_sha256"] != cfg["statistical_contract_sha256"] or
            manifest["statistical_contract_sha256"] != evidence.artifact_sha256(root / "statistical_contract.json") or
            manifest["approved_ticket_sha256"] != cfg["approved_ticket_sha256"] or
            manifest["approved_ticket_sha256"] != evidence.artifact_sha256(root / "approved_ticket.md") or
            manifest["preflight_sha256"] != evidence.artifact_sha256(root / "preflight.json") or
            manifest["e1_manifest_sha256"] != cfg["e1_manifest_sha256"] or
            manifest["e1_ledger_sha256"] != cfg["e1_ledger_sha256"] or
            manifest["e1_ep2_median_seconds"] != cfg["e1_ep2_median_seconds"] or
            manifest["seed_namespace"] != cfg["seed_namespace"] or
            not manifest["no_receiver_warmup"]):
        raise ValueError("Part B preregistered identity differs")
    registry_path = root / "seed_registry.json"
    if manifest["seed_registry_sha256"] != evidence.artifact_sha256(registry_path):
        raise ValueError("prospective seed registry changed")
    registry = json.loads(registry_path.read_text())
    registry_seeds = {(item["snr_centi_db"], item["frame"]): item for item in registry["entries"]}
    if len(registry_seeds) != cfg["total_observations"]:
        raise ValueError("prospective seed registry count differs")
    if manifest["coordinates"] != coordinates:
        raise ValueError("receiver allocation differs")
    run_hash = evidence.canonical_hash(manifest)
    rows = []
    ledger = out / "ledger.jsonl"
    if ledger.exists():
        rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    index = {}
    allowed = {tuple(value) for value in coordinates}
    seen_frames = set()
    seen_channel_seeds = set()
    for position, row in enumerate(rows):
        key = (row["snr_centi_db"], row["frame"], row["arm"])
        if (key not in allowed or key in index or position >= len(coordinates)
                or list(key) != coordinates[position]):
            raise ValueError("duplicate or unplanned receiver attempt")
        index[key] = row
        snr, frame, arm = key
        stem = f"s{snr}_f{frame:04d}"
        input_path = out / "frames" / f"{stem}_input.npz"
        truth_path = out / "frames" / f"{stem}_truth.npz"
        if row["input_sha256"] != evidence.artifact_sha256(input_path) or row["frame_sha256"] != evidence.artifact_sha256(truth_path):
            raise ValueError("paired input/truth hash differs")
        observed, _ = evidence.load_artifact(input_path, identity(run_hash, "frame_input", snr, frame))
        truth, _ = evidence.load_artifact(truth_path, identity(run_hash, "frame_truth", snr, frame))
        if row["input_hash"] != observation_hash(observed) or row["input_hash"] != truth["input_hash"]:
            raise ValueError("paired observed input differs")
        if truth["seed"] != seed_descriptor(snr, frame) or truth["seed"] != registry_seeds[(snr, frame)]:
            raise ValueError("frame seed differs")
        if (snr, frame) not in seen_frames:
            if truth["seed"]["channel_seed"] in seen_channel_seeds:
                raise ValueError("actual channel seed reused")
            seen_frames.add((snr, frame))
            seen_channel_seeds.add(truth["seed"]["channel_seed"])
        info, coded = unbits(truth["info"]), unbits(truth["coded"])
        if row["configuration"] != manifest["configurations"][arm]:
            raise ValueError("receiver config differs")
        seconds = row["seconds"]
        finite_seconds(seconds, "complete cost")
        finite_seconds(row["generation_seconds"], "observation generation")
        finite_seconds(row["scoring_storage_seconds"], "scoring and storage")
        inflight = out / "inflight" / f"{stem}_{arm}.json"
        if row["inflight_sha256"] != evidence.artifact_sha256(inflight):
            raise ValueError("in-flight attempt identity differs")
        opened = json.loads(inflight.read_text())
        if (opened["status"] != "started" or opened["key"] != list(key) or
                opened["run_identity_sha256"] != run_hash or
                opened["input_sha256"] != row["input_sha256"] or
                opened["frame_sha256"] != row["frame_sha256"]):
            raise ValueError("in-flight attempt fields differ")
        marker = out / "attempts" / f"{stem}_{arm}.npz"
        if row["artifact_sha256"] != evidence.artifact_sha256(marker):
            raise ValueError("attempt marker hash differs")
        marker_payload, _ = evidence.load_artifact(marker, identity(run_hash, "attempt", snr, frame, arm))
        if marker_payload["status"] != row["status"] or len(marker_payload["checkpoints"]) != len(row["checkpoints"]):
            raise ValueError("attempt marker differs")
        if row["status"] not in ("ok", "numerical_failure"):
            raise ValueError("invalid attempt status")
        if row["status"] == "ok" and len(row["checkpoints"]) != 2:
            raise ValueError("successful attempt lacks both rounds")
        if row["status"] == "numerical_failure":
            exception = out / "heavy" / f"{stem}_{arm}_exception.json"
            if row["exception_sha256"] != evidence.artifact_sha256(exception):
                raise ValueError("numerical failure traceback differs")
        elif row["exception_sha256"] is not None:
            raise ValueError("successful attempt has exception receipt")
        if row["status"] == "numerical_failure" and len(row["checkpoints"]) > 1:
            raise ValueError("failed attempt has too many prior round decisions")
        previous = -1.0
        for i, cp in enumerate(row["checkpoints"]):
            if cp["round"] != i or cp["event"]["round"] != i:
                raise ValueError("checkpoint round order differs")
            ready = cp["ready"]
            finite_seconds(ready, "checkpoint ready")
            if not previous <= ready <= seconds:
                raise ValueError("checkpoint time differs")
            previous = ready
            path = out / cp["path"]
            if cp["artifact_sha256"] != evidence.artifact_sha256(path):
                raise ValueError("checkpoint hash differs")
            payload, _ = evidence.load_artifact(path, identity(run_hash, "checkpoint", snr, frame, arm, i))
            snapshot = payload["snapshot"]
            decoded = unbits(payload["decoded"], len(coded))
            if not np.array_equal(snapshot["decoded"], decoded):
                raise ValueError("checkpoint decision differs")
            if not np.allclose(snapshot["app"], snapshot["input_llr"] + snapshot["check"], atol=1e-9, rtol=0):
                raise ValueError("decoder APP accounting differs")
            if cp["coded_errors"] != int(np.count_nonzero(decoded != coded)):
                raise ValueError("coded error recount differs")
            if cp["event"] != payload["event"]:
                raise ValueError("checkpoint event differs")
        if row["checkpoints"]:
            if row["coded_errors"] != row["checkpoints"][-1]["coded_errors"] or row["info_errors"] != row["checkpoints"][-1]["info_errors"]:
                raise ValueError("terminal score differs")
        elif row["coded_errors"] is not None or row["info_errors"] is not None:
            raise ValueError("no decision cannot have scores")
    pending = [value for value in coordinates if tuple(value) not in index]
    markers = {path.stem for path in (out / "inflight").glob("*.json")}
    logged = {f"s{snr}_f{frame:04d}_{arm}" for snr, frame, arm in index}
    if markers != logged:
        raise ValueError("in-flight attempt without durable ledger or missing marker")
    if require_complete and pending:
        raise ValueError(f"incomplete campaign: {len(pending)} pending")
    if require_complete and len(rows) != cfg["total_receiver_calls"]:
        raise ValueError("Part B full attempt count differs")
    return {"manifest": manifest, "records": rows, "index": index, "pending": pending,
            "run_identity_sha256": run_hash}
