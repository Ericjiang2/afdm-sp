#!/usr/bin/env python3
"""Verify real-smoke accounting for the fresh-APP ablation."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source / "src"))
    from evidence import load_artifact, source_hashes, validate_run, write_json_atomic

    checked = validate_run(args.run, require_complete=True)
    if checked["manifest"]["source_hashes"] != source_hashes(args.source):
        raise AssertionError("smoke source identity differs from the reviewed tree")
    record = next(row for row in checked["records"] if row["arm"] == "ABL_fresh_APP")
    identity = {
        "kind": "arm", "cell": record["cell"], "frame": record["frame"],
        "arm": record["arm"], "status": record["status"],
        "run_identity_sha256": checked["run_identity_sha256"],
    }
    marker = args.run / "arrays" / "c02_f00000_ABL_fresh_APP.npz"
    payload, _ = load_artifact(marker, identity)
    decoder_records = payload["result_contract"]["decoder_records"]
    stages = [item["evidence_stage"] for item in decoder_records]
    if stages != ["fresh_decoder", "terminal_decoder"]:
        raise AssertionError("fresh-APP decoder records are incomplete or out of order")
    component_seconds = [float(item["metadata"]["seconds"]) for item in decoder_records]
    if abs(sum(component_seconds) - record["decoder_seconds"]) > 1e-12:
        raise AssertionError("fresh plus terminal decoder time differs from the ledger")
    events = payload["result_contract"]["events"]
    fresh_event = next(item for item in events if item["stage"] == "fresh_decoder")
    if "metadata" not in fresh_event:
        raise AssertionError("fresh decoder event lacks metadata")
    report = {
        "status": "pass",
        "run_identity_sha256": checked["run_identity_sha256"],
        "arm": record["arm"],
        "decoder_stages": stages,
        "decoder_component_seconds": component_seconds,
        "ledger_decoder_seconds": record["decoder_seconds"],
        "complete_seconds": record["seconds"],
    }
    write_json_atomic(args.out, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
