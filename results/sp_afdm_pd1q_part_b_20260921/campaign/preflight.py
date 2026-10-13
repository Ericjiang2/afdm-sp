#!/usr/bin/env python3
"""Read-only old-evidence/source audit and prospective Part B seed lock.

Writes only seed_registry.json and preflight.json inside the new Part B root.
No radio observation or receiver is generated here.
"""
import argparse
import json
import os
import platform
import statistics
from pathlib import Path

import numpy as np

from common import attach, plan, seed_descriptor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--e1-run", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    args.source, args.baseline, args.e1_run, args.root = (
        value.resolve() for value in (args.source, args.baseline, args.e1_run, args.root))
    cfg = plan()
    if args.source.name != cfg["source_root_name"] or args.source_commit != cfg["source_commit"]:
        raise ValueError("frozen numerical source identity differs")
    if (args.root / "preflight.json").exists() or (args.root / "seed_registry.json").exists():
        raise ValueError("Part B preflight identity already exists")
    if (args.root / "run").exists():
        raise ValueError("Part B run exists before seed audit")
    evidence = attach(args.source, args.baseline)
    from receiver import context
    if evidence.artifact_sha256(args.source / "docs" / "CODEX_HANDOFF.md") != cfg["handoff_sha256"]:
        raise ValueError("canonical numerical handoff differs")
    old_manifest_path = args.e1_run / "manifest.json"
    old_ledger_path = args.e1_run / "ledger.jsonl"
    if (evidence.artifact_sha256(old_manifest_path) != cfg["e1_manifest_sha256"]
            or evidence.artifact_sha256(old_ledger_path) != cfg["e1_ledger_sha256"]):
        raise ValueError("frozen E1 deadline source differs")
    old_manifest = json.loads(old_manifest_path.read_text())
    source_hashes, baseline_hashes = evidence.source_hashes(args.source), evidence.source_hashes(args.baseline)
    if old_manifest["source_hashes"] != source_hashes or old_manifest["baseline_source_hashes"] != baseline_hashes:
        raise ValueError("source/baseline changed since E1")
    contract_path, ticket_path = args.root / "statistical_contract.json", args.root / "approved_ticket.md"
    if (evidence.artifact_sha256(contract_path) != cfg["statistical_contract_sha256"]
            or evidence.artifact_sha256(ticket_path) != cfg["approved_ticket_sha256"]):
        raise ValueError("frozen Part B statistical contract/ticket differs")
    environment = evidence.bind_runtime_environment()
    same_host_fields = ("hostname", "machine", "platform", "python", "numpy", "scipy", "torch")
    if any(environment[field] != old_manifest["environment"][field] for field in same_host_fields):
        raise ValueError("E1 deadlines are not proven same-machine/runtime")
    code_cache = (args.baseline / "upstream" / "spafdm_receiver_handoff" /
                  "afdm_sp_joint_unrolled" / "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if not code_cache.is_file():
        raise ValueError("frozen LDPC cache missing; context would modify immutable source")
    code_cache_sha = evidence.artifact_sha256(code_cache)
    system, _, code, header = context()
    evidence.verify_runtime_binding()
    if header["code_g_sha256"] != cfg["generator_sha256"]:
        raise ValueError("actual LDPC generator differs")
    system.P_paths = cfg["source_scope"]["paths"]
    system.rho = cfg["source_scope"]["rho"]
    ledger = [json.loads(line) for line in old_ledger_path.read_text().splitlines()]
    medians = {}
    for snr in cfg["cells"]:
        values = [row["seconds"] for row in ledger
                  if row["snr_centi_db"] == snr and row["arm"] == "EP2_MEAN_R2" and row["status"] == "ok"]
        if len(values) != 32:
            raise ValueError("E1 EP2 full32 same-machine deadline sample differs")
        median = statistics.median(values)
        if median != cfg["e1_ep2_median_seconds"][str(snr)]:
            raise ValueError("E1 full32 EP2 deadline median differs")
        medians[str(snr)] = median
    previous_path = args.e1_run.parent / "campaign" / "prior_actual_channel_seeds.json"
    if evidence.artifact_sha256(previous_path) != cfg["prior_seed_registry_sha256"]:
        raise ValueError("historical actual-channel seed registry differs")
    previous = json.loads(previous_path.read_text())
    if previous["schema"] != "spafdm-native-direction-prior-seeds/1" or len(previous["entries"]) != 88:
        raise ValueError("historical actual-channel seed registry count differs")
    old_seeds = {item["channel_seed"] for item in previous["entries"]}
    if len(old_seeds) != 88:
        raise ValueError("historical actual-channel seed collision")
    old_hash = evidence.canonical_hash(old_manifest)
    for snr in cfg["cells"]:
        for frame in range(32):
            old_path = args.e1_run / "frames" / f"s{snr}_f{frame:03d}_truth.npz"
            old_id = {"schema": "spafdm-native-direction-compact/1",
                      "run_identity_sha256": old_hash, "kind": "frame_truth",
                      "snr_centi_db": snr, "frame": frame}
            truth, _ = evidence.load_artifact(old_path, old_id)
            entropy = [20260921, 940318, 0, snr, frame, 1]
            actual = int(np.random.default_rng(np.random.SeedSequence(entropy)).integers(0, 2**31))
            if truth["seed"]["entropy"]["channel"] != entropy or truth["seed"]["channel_seed"] != actual:
                raise ValueError("E1 D saved actual channel seed differs from declared namespace")
            if actual in old_seeds:
                raise ValueError("historical E1 channel seed collided")
            old_seeds.add(actual)
    if len(old_seeds) != 184:
        raise ValueError("historical actual-channel seed count differs")
    # Scan existing manifest identities as well as the explicit actual-seed registry.
    results_root = args.root.parent
    for path in results_root.rglob("manifest.json"):
        if args.root in path.parents:
            continue
        try:
            identity = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        if identity.get("seed_namespace") == cfg["seed_namespace"]:
            raise ValueError(f"Part B seed namespace already used by {path}")
    registry = []
    fresh_seeds = set()
    for snr in cfg["cells"]:
        for frame in range(cfg["frames_per_cell"]):
            descriptor = seed_descriptor(snr, frame)
            value = descriptor["channel_seed"]
            if value in old_seeds or value in fresh_seeds:
                raise ValueError("Part B actual channel seed collision before generation")
            fresh_seeds.add(value)
            registry.append(descriptor)
    if len(fresh_seeds) != cfg["total_observations"]:
        raise ValueError("Part B unique observation count differs")
    stat = os.statvfs(args.root)
    free_bytes = stat.f_bavail * stat.f_frsize
    if free_bytes < cfg["minimum_data_free_bytes"]:
        raise RuntimeError("/data has insufficient free bytes for Part B cap")
    available_kib = next(int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))
    if available_kib < 8*1024*1024:
        raise RuntimeError("server available memory below 8 GiB preflight floor")
    seed_path = args.root / "seed_registry.json"
    evidence.write_json_atomic(seed_path,
        {"schema": "spafdm-pd1q-partb-seeds/1", "namespace": cfg["seed_namespace"],
         "prior_actual_channel_seed_count": len(old_seeds),
         "new_observation_count": len(registry), "entries": registry})
    receipt = {"schema": "spafdm-pd1q-partb-preflight/1", "status": "pass",
               "receiver_calls_added": 0, "new_radio_observations_generated": 0,
               "source_commit": cfg["source_commit"], "baseline_commit": cfg["baseline_commit"],
               "source_hashes": source_hashes, "baseline_source_hashes": baseline_hashes,
               "source_root": str(args.source), "baseline_root": str(args.baseline),
               "e1_manifest_sha256": cfg["e1_manifest_sha256"],
               "e1_ledger_sha256": cfg["e1_ledger_sha256"],
               "e1_run_identity_sha256": old_hash,
               "e1_ep2_median_seconds": medians,
               "same_machine_environment": {field: environment[field] for field in same_host_fields},
               "effective_torch_threads": {"intra": 1, "interop": 1},
               "generator_sha256": header["code_g_sha256"],
               "ldpc_cache_sha256": code_cache_sha,
               "seed_registry_sha256": evidence.artifact_sha256(seed_path),
               "statistical_contract_sha256": cfg["statistical_contract_sha256"],
               "approved_ticket_sha256": cfg["approved_ticket_sha256"],
               "free_data_bytes": free_bytes, "available_memory_kib": available_kib,
               "storage_cap_bytes": cfg["storage_cap_bytes"],
               "hostname": platform.node()}
    evidence.write_json_atomic(args.root / "preflight.json", receipt)
    print(json.dumps({"status": "pass", "new_seed_count": len(registry),
                      "prior_seed_count": len(old_seeds), "free_data_bytes": free_bytes}))


if __name__ == "__main__":
    main()
