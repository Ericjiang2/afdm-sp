"""Fail-closed recount of compact Stage A/B producer evidence."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from common import attach, bits, expected, identity, observation_hash, unbits


def validate_run(out, source, baseline, *, require_complete=False):
    out = Path(out).resolve()
    evidence = attach(source, baseline)
    manifest = json.loads((out / "manifest.json").read_text())
    if manifest["source_hashes"] != evidence.source_hashes(source):
        raise ValueError("source changed since run creation")
    if manifest["baseline_source_hashes"] != evidence.source_hashes(baseline):
        raise ValueError("baseline changed since run creation")
    from common import plan, script_hashes
    if manifest["runner_hashes"] != script_hashes():
        raise ValueError("producer scripts changed since run creation")
    if manifest["plan_sha256"] != evidence.artifact_sha256(Path(__file__).with_name("plan.json")):
        raise ValueError("campaign plan changed")
    if manifest["source_root"] != str(Path(source).resolve()) or manifest["baseline_root"] != str(Path(baseline).resolve()):
        raise ValueError("root binding differs")
    if manifest["configurations"] != plan()["arms"]:
        raise ValueError("arm configurations differ")
    if manifest["stage"] == "A":
        coordinates = [list(value) for value in expected("A")]
    elif manifest["stage"] == "B":
        gate = json.loads(Path(manifest["gate_path"]).read_text())
        if manifest["gate_sha256"] != evidence.artifact_sha256(manifest["gate_path"]):
            raise ValueError("Stage A gate changed")
        coordinates = [list(value) for value in expected("B", gate)]
    else:
        raise ValueError("invalid stage")
    if manifest["coordinates"] != coordinates:
        raise ValueError("receiver allocation differs")
    run_hash = evidence.canonical_hash(manifest)
    rows = []
    ledger = out / "ledger.jsonl"
    if ledger.exists():
        rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    index = {}
    allowed = {tuple(value) for value in coordinates}
    for row in rows:
        key = (row["snr_centi_db"], row["frame"], row["arm"])
        if key not in allowed or key in index:
            raise ValueError("duplicate or unplanned receiver attempt")
        index[key] = row
        snr, frame, arm = key
        stem = f"s{snr}_f{frame:03d}"
        input_path = out / "frames" / f"{stem}_input.npz"
        truth_path = out / "frames" / f"{stem}_truth.npz"
        if row["input_sha256"] != evidence.artifact_sha256(input_path) or row["frame_sha256"] != evidence.artifact_sha256(truth_path):
            raise ValueError("paired input/truth hash differs")
        observed, _ = evidence.load_artifact(input_path, identity(run_hash, "frame_input", snr, frame))
        truth, _ = evidence.load_artifact(truth_path, identity(run_hash, "frame_truth", snr, frame))
        if row["input_hash"] != observation_hash(observed) or row["input_hash"] != truth["input_hash"]:
            raise ValueError("paired observed input differs")
        from common import seed_descriptor
        if truth["seed"] != seed_descriptor(manifest["stage"], snr, frame):
            raise ValueError("frame seed differs")
        info, coded = unbits(truth["info"]), unbits(truth["coded"])
        if row["configuration"] != manifest["configurations"][arm]:
            raise ValueError("receiver config differs")
        seconds = row["seconds"]
        if not isinstance(seconds, (float, int)) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError("invalid complete cost")
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
        previous = -1.0
        for i, cp in enumerate(row["checkpoints"]):
            if cp["round"] != i or cp["event"]["round"] != i:
                raise ValueError("checkpoint round order differs")
            ready = cp["ready"]
            if not isinstance(ready, (float, int)) or not math.isfinite(ready) or not previous <= ready <= seconds:
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
    if require_complete and pending:
        raise ValueError(f"incomplete campaign: {len(pending)} pending")
    return {"manifest": manifest, "records": rows, "index": index, "pending": pending,
            "run_identity_sha256": run_hash}
