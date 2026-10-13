"""Replay the frozen TAIL v2 diagnostic in a new process, without new receivers.

Reuse the original numerical implementation. This checks process reproducibility
and raw provenance; it is not an independent implementation or a new sample.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import resource
import time
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for name in ("tail_script", "contract", "source_dir", "source_manifest",
                 "old_root", "ridge_root", "tail_output", "output_json"):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--reader-sha256", required=True)
    parser.add_argument("--summary-sha256", required=True)
    args = parser.parse_args()
    started = time.monotonic()
    if digest(__file__) != args.reader_sha256 or args.output_json.exists():
        raise ValueError("reader identity differs or verification output exists")
    summary_path = args.tail_output / "summary.json"
    rows_path = args.tail_output / "rows.json"
    if digest(summary_path) != args.summary_sha256:
        raise ValueError("frozen producer summary differs")
    summary = json.loads(summary_path.read_text())
    bindings = {
        args.tail_script: summary["script_sha256"],
        args.contract: summary["contract_sha256"],
        rows_path: summary["rows_sha256"],
        args.source_manifest: summary["source_manifest_sha256"],
    }
    if summary["status"] != "COMPLETE" or any(digest(p) != h for p, h in bindings.items()):
        raise ValueError("frozen TAIL artifact binding differs")
    spec = importlib.util.spec_from_file_location("frozen_tail_v2", args.tail_script)
    tail = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tail)
    tail.assert_threads()
    contract = json.loads(args.contract.read_text())
    tail.require(contract["status"] == "FROZEN_AFTER_INDEPENDENT_REVIEW",
                 "original contract is not frozen")
    tail.require(digest(args.tail_script.with_name("tail_completion_contract_v2.md"))
                 == contract["method_md_sha256"], "original method document differs")
    tail.source_guard(args, contract)
    tail.input_guard(args, contract)
    preflight = tail.memory_preflight()
    saved = json.loads(rows_path.read_text())
    fresh, calls = tail.collect_rows(args, contract, started)
    tail.require(fresh == saved, "new-process raw replay differs from saved rows")
    endpoints = tail.legal_intervals(fresh)
    tail.require(endpoints == summary["legal_four_endpoints"],
                 "new-process paired endpoints differ")
    tail.source_guard(args, contract)
    tail.input_guard(args, contract)
    tail.require(digest(summary_path) == args.summary_sha256
                 and all(digest(p) == h for p, h in bindings.items())
                 and digest(__file__) == args.reader_sha256,
                 "frozen input changed during verification")
    result = {
        "schema": "tail-completion-new-process-verification-v1",
        "status": "PASS",
        "producer_summary_sha256": args.summary_sha256,
        "producer_rows_sha256": summary["rows_sha256"],
        "reader_sha256": args.reader_sha256,
        "tail_script_sha256": summary["script_sha256"],
        "contract_sha256": summary["contract_sha256"],
        "source_manifest_sha256": summary["source_manifest_sha256"],
        "input_binding": summary["input_binding"],
        "exact_saved_rows": len(fresh),
        "paired_endpoints_exact": True,
        "additional_audit_calls": calls,
        "new_production_comparisons": 0,
        "new_F": 0, "new_CE": 0, "new_BP": 0, "new_LDPC": 0,
        "independence": "new process; original implementation; no new sample",
        "memory_preflight": preflight,
        "peak_resident_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "wall_seconds": time.monotonic() - started,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with args.output_json.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "exact_saved_rows": len(fresh),
                      "additional_audit_calls": calls, "new_F": 0}))


if __name__ == "__main__":
    main()
