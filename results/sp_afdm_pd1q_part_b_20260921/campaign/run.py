#!/usr/bin/env python3
"""Execute one bounded native-joint stage with durable round checkpoints."""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path

import numpy as np

from common import (SCHEMA, append_jsonl, attach, bits, byte_count, expected,
                    finite_seconds, identity, observation_hash, plan,
                    script_hashes, seed_descriptor)


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--source", type=Path, required=True)
    value.add_argument("--baseline", type=Path, required=True)
    value.add_argument("--root", type=Path, required=True)
    value.add_argument("--source-commit", required=True)
    return value


def make_manifest(args, evidence, receipt):
    cfg = plan()
    if args.source.name != cfg["source_root_name"]:
        raise ValueError("only the frozen reviewed source root is allowed")
    if evidence.artifact_sha256(args.source / "docs" / "CODEX_HANDOFF.md") != cfg["handoff_sha256"]:
        raise ValueError("canonical handoff differs")
    if args.source_commit != cfg["source_commit"]:
        raise ValueError("frozen numerical source commit differs")
    coordinates = [list(item) for item in expected(cfg)]
    if len(coordinates) != cfg["total_receiver_calls"]:
        raise ValueError("planned receiver call count differs")
    env = evidence.bind_runtime_environment()
    return {"schema": SCHEMA, "stage": "PartB", "phase": "prospective",
            "source_commit": args.source_commit, "baseline_commit": cfg["baseline_commit"],
            "source_hashes": evidence.source_hashes(args.source),
            "baseline_source_hashes": evidence.source_hashes(args.baseline),
            "runner_hashes": script_hashes(),
            "plan_sha256": evidence.artifact_sha256(Path(__file__).with_name("plan.json")),
            "environment": env, "handoff_sha256": cfg["handoff_sha256"],
            "configurations": cfg["arms"], "coordinates": coordinates,
            "seed_namespace": cfg["seed_namespace"],
            "preflight_sha256": evidence.artifact_sha256(args.root / "preflight.json"),
            "seed_registry_sha256": receipt["seed_registry_sha256"],
            "statistical_contract_sha256": cfg["statistical_contract_sha256"],
            "approved_ticket_sha256": cfg["approved_ticket_sha256"],
            "e1_manifest_sha256": cfg["e1_manifest_sha256"],
            "e1_ledger_sha256": cfg["e1_ledger_sha256"],
            "e1_ep2_median_seconds": cfg["e1_ep2_median_seconds"],
            "baseline_root": str(args.baseline.resolve()),
            "source_root": str(args.source.resolve()),
            "storage_cap_bytes": cfg["storage_cap_bytes"],
            "audit_frames": cfg["audit_frames"],
            "no_receiver_warmup": True,
            "scope": "prospective 3072 paired frames / 9696 calls; no optional scope"}


def frame_observation(system, code, snr_centi, frame):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation

    seed = seed_descriptor(snr_centi, frame)
    component_map = {1: 1, 2: 0, 3: 2}

    def rng_factory(replicate, index, component, *, split):
        if replicate != 0 or index != frame or split != 2 or component not in component_map:
            raise ValueError("make_frame requested unexpected RNG coordinate")
        entropy = seed["entropy"][{1: "channel", 2: "message", 3: "noise"}[component]]
        return np.random.default_rng(np.random.SeedSequence(entropy))

    raw = make_frame(system, code, 0, frame, snr_centi / 100, split=2,
                     rng_factory=rng_factory)
    if int(raw["channel_seed"]) != seed["channel_seed"]:
        raise ValueError("actual channel seed differs from registered entropy")
    raw, _ = physical_observation(raw, system, prefix_length=system.l_max_cap)
    unit = np.sqrt(2 * (1 - system.rho))
    observed = {"y": raw["y"] / unit, "pilot": raw["pilot"] / unit,
                "sigma2": float(raw["sigma2"]) / unit**2}
    truth = {key: np.asarray(raw[key]) for key in ("info", "coded", "data", "noise")}
    truth.update({key: np.asarray(raw["params"][key]) for key in
                  ("l_i", "k_real", "g_i")})
    truth["unit_scale"] = float(unit)
    return observed, truth, seed


def save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence):
    stem = f"s{snr}_f{frame:04d}"
    for kind, payload in (("input", observed), ("truth", truth)):
        path = out / "heavy" / f"{stem}_{kind}.npz"
        expected_id = identity(run_hash, f"heavy_{kind}", snr, frame)
        if path.exists():
            evidence.load_artifact(path, expected_id)
        else:
            evidence.save_artifact(path, payload, expected_id)


def process_memory():
    values = {"rss_kib": None, "high_water_kib": None}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            values["rss_kib"] = int(line.split()[1])
        if line.startswith("VmHWM:"):
            values["high_water_kib"] = int(line.split()[1])
    return values


def check_storage(out, cap):
    used = byte_count(out)
    if used >= cap:
        (out / "resource_limit.json").write_text(json.dumps(
            {"status": "resource_limit", "bytes": used, "cap_bytes": cap}, indent=2) + "\n")
        raise RuntimeError("fixed 8 GiB Part B evidence cap reached")


def main(argv=None):
    args = parser().parse_args(argv)
    args.source, args.baseline, args.root = (item.resolve() for item in
                                            (args.source, args.baseline, args.root))
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from native_twofft import receive
    from native_controls import receive_control
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info

    receipt = json.loads((args.root / "preflight.json").read_text())
    registry_path = args.root / "seed_registry.json"
    if (receipt["status"] != "pass" or
            receipt["seed_registry_sha256"] != evidence.artifact_sha256(registry_path) or
            receipt["source_hashes"] != evidence.source_hashes(args.source) or
            receipt["baseline_source_hashes"] != evidence.source_hashes(args.baseline) or
            receipt["statistical_contract_sha256"] != plan()["statistical_contract_sha256"] or
            receipt["statistical_contract_sha256"] != evidence.artifact_sha256(
                args.root / "statistical_contract.json") or
            receipt["approved_ticket_sha256"] != evidence.artifact_sha256(
                args.root / "approved_ticket.md")):
        raise ValueError("preflight/source/seed binding differs")
    registry = json.loads(registry_path.read_text())
    seeds = {(item["snr_centi_db"], item["frame"]): item for item in registry["entries"]}
    if len(seeds) != plan()["total_observations"]:
        raise ValueError("seed registry observation count differs")
    code_cache = (args.baseline / "upstream" / "spafdm_receiver_handoff" /
                  "afdm_sp_joint_unrolled" / "e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if evidence.artifact_sha256(code_cache) != receipt["ldpc_cache_sha256"]:
        raise ValueError("frozen LDPC cache differs after preflight")
    manifest = make_manifest(args, evidence, receipt)
    out = args.root / "run"
    if out.exists():
        from verify import validate_run
        checked = validate_run(out, args.source, args.baseline, require_complete=True)
        if checked["manifest"] != manifest:
            raise ValueError("existing run identity differs before context/write")
        print("complete valid run; no receiver calls", flush=True)
        return
    else:
        (out / "frames").mkdir(parents=True)
        (out / "checkpoints").mkdir()
        (out / "attempts").mkdir()
        (out / "heavy").mkdir()
        (out / "inflight").mkdir()
        evidence.write_json_atomic(out / "manifest.json", manifest)
    run_hash = evidence.canonical_hash(manifest)
    system, model, code, header = context()
    evidence.verify_runtime_binding()
    system.P_paths = plan()["source_scope"]["paths"]
    system.rho = plan()["source_scope"]["rho"]
    header = json.loads(json.dumps(header, default=lambda value: value.item()
                                   if isinstance(value, np.generic) else value,
                                   allow_nan=False))
    if header["code_g_sha256"] != plan()["generator_sha256"]:
        raise ValueError("actual LDPC generator differs")
    header_path = out / "context_header.json"
    if header_path.exists():
        if json.loads(header_path.read_text()) != header:
            raise ValueError("receiver context changed on resume")
    else:
        evidence.write_json_atomic(header_path, header)
    grouped = {}
    for snr, frame, arm in manifest["coordinates"]:
        grouped.setdefault((snr, frame), []).append(arm)
    attempts_done = 0
    for (snr, frame), arms in grouped.items():
        started_generation = time.perf_counter()
        observed, truth, seed = frame_observation(system, code, snr, frame)
        if seed != seeds[(snr, frame)]:
            raise ValueError("generated frame differs from preflight seed registry")
        input_hash = observation_hash(observed)
        generation_seconds = time.perf_counter() - started_generation
        stem = f"s{snr}_f{frame:04d}"
        frame_path = out / "frames" / f"{stem}_truth.npz"
        input_path = out / "frames" / f"{stem}_input.npz"
        input_id = identity(run_hash, "frame_input", snr, frame)
        evidence.save_artifact(input_path, observed, input_id)
        input_sha = evidence.artifact_sha256(input_path)
        frame_payload = {"seed": seed, "input_hash": input_hash,
                         "info": bits(truth["info"]), "coded": bits(truth["coded"]),
                         "l_i": truth["l_i"], "k_real": truth["k_real"],
                         "g_i": truth["g_i"], "unit_scale": truth["unit_scale"]}
        frame_id = identity(run_hash, "frame_truth", snr, frame)
        evidence.save_artifact(frame_path, frame_payload, frame_id)
        frame_sha = evidence.artifact_sha256(frame_path)
        audit = frame in manifest["audit_frames"]
        if audit:
            save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence)
        for arm in arms:
            key = (snr, frame, arm)
            config = manifest["configurations"][arm]
            prefix = f"{stem}_{arm}"
            attempted = out / "attempts" / f"{prefix}.npz"
            inflight = out / "inflight" / f"{prefix}.json"
            evidence.write_json_atomic(inflight, {"status": "started", "key": list(key),
                "run_identity_sha256": run_hash, "input_sha256": input_sha,
                "frame_sha256": frame_sha, "pid": os.getpid(),
                "start_epoch": time.time()})
            inflight_sha = evidence.artifact_sha256(inflight)
            checkpoints = []
            before = process_memory()

            def checkpoint_sink(event, decoded):
                round_index = event["round"]
                snapshot = event["snapshot"]
                metadata = {name: value for name, value in event.items()
                            if name != "snapshot"}
                path = out / "checkpoints" / f"{prefix}_r{round_index}.npz"
                payload = {"event": metadata, "decoded": bits(decoded),
                           "snapshot": {name: value for name, value in snapshot.items()
                                        if name != "inference_states"}}
                if audit and "inference_states" in snapshot:
                    payload["inference_states"] = snapshot["inference_states"]
                digest = evidence.save_artifact(path, payload,
                    identity(run_hash, "checkpoint", snr, frame, arm, round_index))
                checkpoints.append({"round": round_index, "event": metadata,
                                    "artifact_sha256": digest, "path": str(path.relative_to(out)),
                                    "decoded": np.asarray(decoded).copy()})

            started = time.perf_counter()
            status, result, exception = "ok", None, None
            failure_online_seconds = None
            try:
                if config["family"] == "tf":
                    result = receive(observed, system, code, rounds=2, iterations=20,
                                     ce_mode=config["ce_mode"], gain_mode=config["gain_mode"],
                                     checkpoint_sink=checkpoint_sink, record_states=audit)
                else:
                    result = receive_control(observed, system, code,
                        kind=config["family"], iterations=config["iterations"],
                        ce_mode=config["ce_mode"], checkpoint_sink=checkpoint_sink)
            except (np.linalg.LinAlgError, FloatingPointError) as error:
                failure_online_seconds = finite_seconds(time.perf_counter() - started,
                                                        "failed online attempt")
                status, exception = "numerical_failure", traceback.format_exc()
                save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence)
                exception_path = out / "heavy" / f"{prefix}_exception.json"
                evidence.write_json_atomic(exception_path,
                    {"type": type(error).__name__, "message": str(error),
                     "traceback": exception})
            complete = (failure_online_seconds if failure_online_seconds is not None else
                        finite_seconds(time.perf_counter() - started, "complete attempt"))
            if status == "ok" and (len(checkpoints) != 2 or
                                   not np.array_equal(result[0]["decoded"], checkpoints[-1]["decoded"])):
                raise ValueError("completed receiver result differs from durable checkpoints")
            if audit or status != "ok":
                from physical import Channel, daft
                from twofft import TimePathOps

                for checkpoint in checkpoints:
                    snapshot = evidence.load_artifact(out / checkpoint["path"])[0]["snapshot"]
                    channel = Channel(len(observed["y"]), system.c1, system.c2,
                        snapshot["delays"], snapshot["dopplers"], snapshot["gains"])
                    response = TimePathOps(channel).responses_time(
                        daft(observed["pilot"] + snapshot["mu"], system.c1, system.c2, True))
                    path = out / "heavy" / f"{prefix}_r{checkpoint['round']}_path_response.npz"
                    evidence.save_artifact(path, {"path_response": response},
                        identity(run_hash, "path_response", snr, frame, arm, checkpoint["round"]))
            scored = []
            for checkpoint in checkpoints:
                decoded = checkpoint.pop("decoded")
                info_hat = extract_info(code, decoded)
                scored.append({"round": checkpoint["round"],
                               "ready": finite_seconds(checkpoint["event"]["ready"], "decision ready"),
                               "info_errors": int(np.count_nonzero(info_hat != truth["info"])),
                               "coded_errors": int(np.count_nonzero(decoded != truth["coded"])),
                               "syndrome_weight": int(np.count_nonzero((code["H"] @ decoded) % 2)),
                               "artifact_sha256": checkpoint["artifact_sha256"],
                               "path": checkpoint["path"],
                               "event": checkpoint["event"]})
            record = {"snr_centi_db": snr, "frame": frame, "arm": arm,
                      "configuration": config, "status": status, "seconds": complete,
                      "generation_seconds": generation_seconds,
                      "input_hash": input_hash, "input_sha256": input_sha,
                      "frame_sha256": frame_sha,
                      "checkpoints": scored,
                      "info_errors": None if not scored else scored[-1]["info_errors"],
                      "coded_errors": None if not scored else scored[-1]["coded_errors"],
                      "memory_before": before, "memory_after": process_memory(),
                      "memory_scope": "shared-process RSS/HWM snapshots; not isolated receiver peak",
                      "exception_sha256": (None if exception is None else
                          evidence.artifact_sha256(out / "heavy" / f"{prefix}_exception.json")),
                      "inflight_sha256": inflight_sha,
                      "receiver_reported_seconds": None if result is None else result[2]["seconds"]}
            marker_sha = evidence.save_artifact(attempted,
                {"status": status, "checkpoints": scored,
                 "exception": exception}, identity(run_hash, "attempt", snr, frame, arm))
            record["artifact_sha256"] = marker_sha
            record["scoring_storage_seconds"] = finite_seconds(
                time.perf_counter() - started - complete, "scoring/storage")
            append_jsonl(out / "ledger.jsonl", record)
            attempts_done += 1
            if attempts_done % 100 == 0:
                check_storage(args.root, manifest["storage_cap_bytes"])
                print(f"attempts={attempts_done}/{plan()['total_receiver_calls']}", flush=True)
        print(stem, "complete", flush=True)
    check_storage(args.root, manifest["storage_cap_bytes"])
    from verify import validate_run

    checked = validate_run(out, args.source, args.baseline, require_complete=True)
    evidence.write_json_atomic(out / "completion.json",
        {"status": "complete", "records": len(checked["records"]),
         "run_identity_sha256": run_hash, "total_bytes": byte_count(out)})


if __name__ == "__main__":
    main()
