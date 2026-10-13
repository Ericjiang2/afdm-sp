#!/usr/bin/env python3
"""Independently recount four isolated two-call memory probes from saved bits."""
import argparse
import json
from pathlib import Path

import numpy as np

from common import attach, observation_hash, plan, unbits

ARMS = ("TF_J20_R2", "EP2_MEAN_R2", "EP4_MEAN_R2", "PBI8_SOFT_R2")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--e1-run", type=Path, required=True)
    parser.add_argument("--memory-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("memory recount output already exists")
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info

    cfg = plan()
    e1_manifest_path = args.e1_run / "manifest.json"
    if evidence.artifact_sha256(e1_manifest_path) != cfg["e1_manifest_sha256"]:
        raise ValueError("E1 manifest differs")
    e1_manifest = json.loads(e1_manifest_path.read_text())
    if e1_manifest["source_hashes"] != evidence.source_hashes(args.source):
        raise ValueError("numerical source differs")
    if e1_manifest["baseline_source_hashes"] != evidence.source_hashes(args.baseline):
        raise ValueError("baseline source differs")
    e1_hash = evidence.canonical_hash(e1_manifest)
    old_id = {"schema": "spafdm-native-direction-compact/1",
              "run_identity_sha256": e1_hash, "kind": "frame_truth",
              "snr_centi_db": 650, "frame": 0}
    truth, _ = evidence.load_artifact(args.e1_run / "frames" / "s650_f000_truth.npz", old_id)
    info = unbits(truth["info"], cfg["source_scope"]["code_k"])
    coded = unbits(truth["coded"], cfg["source_scope"]["code_n"])
    system, _, code, header = context()
    if header["code_g_sha256"] != cfg["generator_sha256"] or not np.array_equal((code["G"] @ info) % 2, coded):
        raise ValueError("saved E1 bits differ from code")
    details = []
    for arm in ARMS:
        path = args.memory_root / arm
        manifest = json.loads((path / "manifest.json").read_text())
        if (manifest["arm"] != arm or manifest["source_hashes"] != e1_manifest["source_hashes"]
                or manifest["baseline_source_hashes"] != e1_manifest["baseline_source_hashes"]
                or manifest["e1_run_identity_sha256"] != e1_hash
                or manifest["input_hash"] != truth["input_hash"]):
            raise ValueError("isolated memory identity differs")
        run_hash = evidence.canonical_hash(manifest)
        ledger = [json.loads(line) for line in (path / "ledger.jsonl").read_text().splitlines()]
        if [row["attempt"] for row in ledger] != ["warmup", "measured"]:
            raise ValueError("memory attempt order differs")
        for row in ledger:
            label = row["attempt"]
            if row["status"] != "ok" or len(row["checkpoints"]) != 2:
                raise ValueError("memory attempt incomplete")
            marker_id = {"schema": "spafdm-pd1q-isolated-memory/1",
                         "run_identity_sha256": run_hash, "kind": "attempt",
                         "arm": arm, "attempt": label}
            marker, _ = evidence.load_artifact(path / "attempts" / f"{label}.npz", marker_id)
            if marker != row:
                raise ValueError("memory attempt marker differs from ledger")
            for cp in row["checkpoints"]:
                cp_id = {"schema": "spafdm-pd1q-isolated-memory/1",
                         "run_identity_sha256": run_hash, "kind": "checkpoint",
                         "arm": arm, "attempt": label, "round": cp["round"]}
                cp_path = path / cp["path"]
                if cp["artifact_sha256"] != evidence.artifact_sha256(cp_path):
                    raise ValueError("memory checkpoint SHA differs")
                payload, _ = evidence.load_artifact(cp_path, cp_id)
                decoded = unbits(payload["decoded"], len(coded))
                snapshot = payload["snapshot"]
                if not np.array_equal(snapshot["decoded"], decoded):
                    raise ValueError("memory saved decoded bits differ")
                if not np.allclose(snapshot["app"], snapshot["input_llr"] + snapshot["check"], atol=1e-9, rtol=0):
                    raise ValueError("memory decoder input/APP/check accounting differs")
                actual_info = int(np.count_nonzero(extract_info(code, decoded) != info))
                actual_coded = int(np.count_nonzero(decoded != coded))
                if actual_info != cp["info_errors"] or actual_coded != cp["coded_errors"]:
                    raise ValueError("memory bit score differs")
                details.append({"arm": arm, "attempt": label, "round": cp["round"],
                                "info_errors": actual_info, "coded_errors": actual_coded,
                                "syndrome_weight": int(np.count_nonzero((code["H"] @ decoded) % 2))})
    report = {"schema": "spafdm-pd1q-isolated-memory-recount/1", "status": "pass",
              "attempts": 8, "checkpoints": 16, "receiver_calls_added": 0,
              "source_commit": cfg["source_commit"], "e1_run_identity_sha256": e1_hash,
              "scope": "offline saved checkpoint info/coded bits, syndrome and decoder LLR accounting; fresh-process probe costs remain separate",
              "details": details}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": "pass", "attempts": 8, "checkpoints": 16}))


if __name__ == "__main__":
    main()
