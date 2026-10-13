#!/usr/bin/env python3
"""One-time offline rescue of three saved replay calls after a packed-truth score bug.

No receiver is invoked. The original failed run remains immutable in attribution/.
Every imported payload is re-signed under a new producer manifest/run identity.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from common import append_jsonl, attach, identity, plan, unbits
from run import compare_e1_replay, make_manifest
from verify import validate_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--e1-run", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    args.source, args.baseline, args.e1_run, args.old, args.out = (
        value.resolve() for value in
        (args.source, args.baseline, args.e1_run, args.old, args.out))
    if args.out.exists():
        raise ValueError("new identity migration destination must not exist")
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info

    manifest = make_manifest(args, evidence)
    old_manifest = json.loads((args.old / "manifest.json").read_text())
    if (old_manifest["source_hashes"] != manifest["source_hashes"]
            or old_manifest["baseline_source_hashes"] != manifest["baseline_source_hashes"]
            or old_manifest["coordinates"] != manifest["coordinates"]
            or old_manifest["e1_run_identity_sha256"] != manifest["e1_run_identity_sha256"]):
        raise ValueError("old replay scientific binding differs")
    old_hash = evidence.canonical_hash(old_manifest)
    new_hash = evidence.canonical_hash(manifest)
    rows = [json.loads(line) for line in (args.old / "ledger.jsonl").read_text().splitlines()]
    if len(rows) != 3 or {(row["snr_centi_db"], row["frame"], row["arm"]) for row in rows} != {
            (snr, 0, "TF_REPLAY") for snr in plan()["cells"]}:
        raise ValueError("only the three already-paid replay calls may be rescued")
    system, _, code, header = context()
    if header["code_g_sha256"] != plan()["generator_sha256"]:
        raise ValueError("LDPC generator differs")
    header_json = json.loads(json.dumps(header, default=lambda value: value.item()
                       if isinstance(value, np.generic) else value, allow_nan=False))
    if json.loads((args.old / "context_header.json").read_text()) != header_json:
        raise ValueError("old code context differs")
    for folder in ("frames", "checkpoints", "attempts", "heavy"):
        (args.out / folder).mkdir(parents=True, exist_ok=False)
    evidence.write_json_atomic(args.out / "manifest.json", manifest)
    evidence.write_json_atomic(args.out / "context_header.json", header_json)
    mappings = []
    for row in rows:
        snr, frame, arm = row["snr_centi_db"], row["frame"], row["arm"]
        stem = f"s{snr}_f{frame:03d}"
        new_row = dict(row)
        for kind, key in (("frame_input", "input_sha256"), ("frame_truth", "frame_sha256")):
            filename = f"{stem}_{'input' if kind == 'frame_input' else 'truth'}.npz"
            old_path = args.old / "frames" / filename
            payload, _ = evidence.load_artifact(old_path, identity(old_hash, kind, snr, frame))
            new_path = args.out / "frames" / filename
            new_row[key] = evidence.save_artifact(new_path, payload,
                                                  identity(new_hash, kind, snr, frame))
            mappings.append({"old": str(old_path), "old_sha256": evidence.artifact_sha256(old_path),
                             "new": str(new_path), "new_sha256": new_row[key]})
        truth, _ = evidence.load_artifact(args.out / "frames" / f"{stem}_truth.npz")
        info = unbits(truth["info"], plan()["source_scope"]["code_k"])
        coded = unbits(truth["coded"], plan()["source_scope"]["code_n"])
        scored = []
        for cp in row["checkpoints"]:
            old_path = args.old / cp["path"]
            payload, _ = evidence.load_artifact(old_path,
                identity(old_hash, "checkpoint", snr, frame, arm, cp["round"]))
            decoded = unbits(payload["decoded"], len(coded))
            if not np.array_equal(payload["snapshot"]["decoded"], decoded):
                raise ValueError("old replay checkpoint decision differs")
            if not np.array_equal((code["G"] @ info) % 2, coded):
                raise ValueError("imported E1 codeword differs from generator")
            new_path = args.out / cp["path"]
            new_sha = evidence.save_artifact(new_path, payload,
                identity(new_hash, "checkpoint", snr, frame, arm, cp["round"]))
            corrected = dict(cp)
            corrected["artifact_sha256"] = new_sha
            corrected["info_errors"] = int(np.count_nonzero(extract_info(code, decoded) != info))
            corrected["coded_errors"] = int(np.count_nonzero(decoded != coded))
            corrected["syndrome_weight"] = int(np.count_nonzero((code["H"] @ decoded) % 2))
            scored.append(corrected)
            mappings.append({"old": str(old_path), "old_sha256": evidence.artifact_sha256(old_path),
                             "new": str(new_path), "new_sha256": new_sha})
        new_row["checkpoints"] = scored
        new_row["info_errors"] = scored[-1]["info_errors"]
        new_row["coded_errors"] = scored[-1]["coded_errors"]
        old_marker = args.old / "attempts" / f"{stem}_{arm}.npz"
        evidence.load_artifact(old_marker, identity(old_hash, "attempt", snr, frame, arm))
        new_marker = args.out / "attempts" / old_marker.name
        new_row["artifact_sha256"] = evidence.save_artifact(new_marker,
            {"status": row["status"], "checkpoints": scored, "exception": None},
            identity(new_hash, "attempt", snr, frame, arm))
        mappings.append({"old": str(old_marker), "old_sha256": evidence.artifact_sha256(old_marker),
                         "new": str(new_marker), "new_sha256": new_row["artifact_sha256"]})
        new_row["score_migration"] = "offline_from_preserved_checkpoint; no_receiver_call"
        append_jsonl(args.out / "ledger.jsonl", new_row)
    for old_path in sorted((args.old / "heavy").glob("*.npz")):
        payload, old_id = evidence.load_artifact(old_path)
        if old_id["run_identity_sha256"] != old_hash:
            raise ValueError("old heavy identity differs")
        new_id = dict(old_id, run_identity_sha256=new_hash)
        new_path = args.out / "heavy" / old_path.name
        new_sha = evidence.save_artifact(new_path, payload, new_id)
        mappings.append({"old": str(old_path), "old_sha256": evidence.artifact_sha256(old_path),
                         "new": str(new_path), "new_sha256": new_sha})
    checked = validate_run(args.out, args.source, args.baseline)
    if len(checked["records"]) != 3:
        raise ValueError("rescued replay count differs")
    for row in checked["records"]:
        compare_e1_replay(args, evidence, manifest, row["snr_centi_db"], 0,
                          row["checkpoints"])
    evidence.write_json_atomic(args.out / "primary_replay_parity.json",
        {"status": "pass", "records": 3, "run_identity_sha256": new_hash,
         "scope": "three already-paid primary replays; no receiver rerun"})
    evidence.write_json_atomic(args.out / "migration_receipt.json",
        {"status": "pass", "old_run_identity_sha256": old_hash,
         "new_run_identity_sha256": new_hash, "receiver_calls_added": 0,
         "cause": "packed E1 truth was compared as dict during producer score; numerics and saved checkpoints unchanged",
         "old_failed_run": str(args.old), "mappings": mappings})
    print(json.dumps({"status": "pass", "records": 3, "receiver_calls_added": 0,
                      "new_run_identity_sha256": new_hash}))


if __name__ == "__main__":
    main()
