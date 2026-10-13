#!/usr/bin/env python3
"""Offline round-trip and saved-decision recount for one corrected smoke run."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(args.source / "src"))
    from evidence import (  # pylint: disable=import-error,import-outside-toplevel
        load_artifact,
        source_hashes,
        validate_run,
        write_json_atomic,
    )

    checked = validate_run(args.run, require_complete=True)
    manifest = checked["manifest"]
    current_hashes = source_hashes(args.source)
    if manifest["source_hashes"] != current_hashes:
        raise AssertionError("run source manifest differs from current corrected tree")

    artifacts = []
    arm_checks = []
    total_info_errors = 0
    total_code_errors = 0
    for record in checked["records"]:
        cell, frame, arm = record["cell"], record["frame"], record["arm"]
        stem = f"c{cell:02d}_f{frame:05d}"
        run_hash = checked["run_identity_sha256"]
        truth, _ = load_artifact(
            args.run / "truth" / f"{stem}.npz",
            {"kind": "truth", "cell": cell, "frame": frame,
             "run_identity_sha256": run_hash},
        )
        marker = args.run / "arrays" / f"{stem}_{arm}.npz"
        payload, _ = load_artifact(
            marker,
            {"kind": "arm", "cell": cell, "frame": frame, "arm": arm,
             "status": record["status"], "run_identity_sha256": run_hash},
        )
        if record["status"] != "ok":
            raise AssertionError(f"smoke arm did not complete: {arm}")

        info_errors = int(np.count_nonzero(payload["info_hat"] != truth["info"]))
        code_errors = int(np.count_nonzero(payload["decoded"] != truth["coded"]))
        if info_errors != record["info_errors"]:
            raise AssertionError(f"saved info-error recount differs for {arm}")
        total_info_errors += info_errors
        total_code_errors += code_errors

        contract = payload["result_contract"]
        result = payload["result"]
        if not contract["decoder_records"]:
            raise AssertionError(f"decoder records missing for {arm}")
        for field in ("front_seconds", "refit_seconds", "detector_seconds",
                      "decoder_seconds", "instrumentation_seconds"):
            if field not in record:
                raise AssertionError(f"ledger timing {field} missing for {arm}")
        if record["seconds"] < record["front_seconds"]:
            raise AssertionError(f"complete time precedes front time for {arm}")

        configuration = manifest["configurations"][arm]
        native = bool(configuration.get("native"))
        if native:
            rounds = contract["round_timings"]
            decoder_records = contract["decoder_records"]
            if len(rounds) != configuration.get("coded_rounds", 3):
                raise AssertionError(f"native round timings incomplete for {arm}")
            if len(decoder_records) != len(rounds):
                raise AssertionError(f"native decoder records incomplete for {arm}")
            if "native_initial_state" not in payload["front"]:
                raise AssertionError(f"native initial state missing for {arm}")
            if "front_H_coo" in payload:
                raise AssertionError(f"native arm unexpectedly stores I1 H for {arm}")
            h_roundtrip = None
        else:
            for field in ("final_input", "final_app", "final_check",
                          "final_detector_mu", "final_detector_variance"):
                if field not in result:
                    raise AssertionError(f"raw terminal field {field} missing for {arm}")
            if not np.allclose(result["final_app"] - result["final_input"],
                               result["final_check"], rtol=0, atol=2e-6):
                raise AssertionError(f"decoder APP/input/check identity differs for {arm}")
            coo = payload["front_H_coo"]
            shape = tuple(int(value) for value in coo["shape"])
            matrix = np.zeros(shape, dtype=np.asarray(coo["data"]).dtype)
            matrix[coo["rows"], coo["columns"]] = coo["data"]
            canary = payload.get("front_H_canary")
            if canary is None or not np.array_equal(matrix, canary):
                raise AssertionError(f"exact H COO/dense canary round trip differs for {arm}")
            h_roundtrip = {
                "shape": list(shape),
                "stored_nonzero": int(len(coo["data"])),
                "reconstructed_nonzero": int(np.count_nonzero(matrix)),
                "dense_canary_equal": True,
            }
            if configuration.get("method") == "I1":
                for field in ("final_detector_hard", "final_detector_mu",
                              "final_detector_variance"):
                    if field not in result:
                        raise AssertionError(f"I1 raw detector field {field} missing")
                if len(contract["decoder_records"]) != 1:
                    raise AssertionError("I1 terminal decoder was not recorded exactly once")

        arm_checks.append({
            "arm": arm,
            "info_errors": info_errors,
            "code_errors": code_errors,
            "seconds": record["seconds"],
            "front_seconds": record["front_seconds"],
            "refit_seconds": record["refit_seconds"],
            "detector_seconds": record["detector_seconds"],
            "decoder_seconds": record["decoder_seconds"],
            "instrumentation_seconds": record["instrumentation_seconds"],
            "rounds": len(contract.get("round_timings", [])),
            "decoder_records": len(contract["decoder_records"]),
            "h_roundtrip": h_roundtrip,
        })

    for path in sorted(args.run.rglob("*")):
        if path.is_file():
            artifacts.append({
                "path": str(path.relative_to(args.run)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })

    report = {
        "status": "pass",
        "run": str(args.run),
        "source": str(args.source),
        "run_identity_sha256": checked["run_identity_sha256"],
        "source_file_count": len(current_hashes),
        "records": len(checked["records"]),
        "pending": checked["pending"],
        "total_info_errors": total_info_errors,
        "total_code_errors": total_code_errors,
        "arms": arm_checks,
        "artifacts": artifacts,
    }
    write_json_atomic(args.out, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
