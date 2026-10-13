#!/usr/bin/env python3
"""Execute one bounded native-joint stage with durable round checkpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from common import (SCHEMA, append_jsonl, attach, bits, byte_count, expected,
                    finite_seconds, historical_channel_seeds, identity,
                    observation_hash, plan, script_hashes, seed_descriptor, unbits)


ACTIVE = None


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--source", type=Path, required=True)
    value.add_argument("--baseline", type=Path, required=True)
    value.add_argument("--stage", choices=("A", "B"), required=True)
    value.add_argument("--out", type=Path, required=True)
    value.add_argument("--gate", type=Path)
    value.add_argument("--source-commit", required=True)
    value.add_argument("--audit-only", action="store_true")
    return value


def make_manifest(args, evidence):
    cfg = plan()
    if args.source.name != cfg["source_root_name"]:
        raise ValueError("only the frozen reviewed source root is allowed")
    if evidence.artifact_sha256(args.source / "docs" / "CODEX_HANDOFF.md") != cfg["handoff_sha256"]:
        raise ValueError("canonical handoff differs")
    gate_hash = None
    decision = None
    if args.stage == "B":
        if args.gate is None:
            raise ValueError("Stage B requires the fixed Stage A gate")
        from gate import build_gate

        decision = json.loads(args.gate.read_text())
        if decision != build_gate(decision["stage_a_run"], args.source, args.baseline):
            raise ValueError("Stage A gate differs from fresh recount")
        if decision["decision"] != "advance":
            raise ValueError("Stage A did not license Stage B")
        gate_hash = evidence.artifact_sha256(args.gate)
    elif args.gate is not None:
        raise ValueError("Stage A cannot bind a gate")
    coordinates = [list(item) for item in expected(args.stage, decision)]
    if len(coordinates) != cfg[f"stage_{args.stage.lower()}"]["receiver_calls"]:
        raise ValueError("planned receiver call count differs")
    env = evidence.bind_runtime_environment()
    return {"schema": SCHEMA, "stage": args.stage, "phase": "exploratory",
            "source_commit": args.source_commit, "baseline_commit": cfg["baseline_commit"],
            "source_hashes": evidence.source_hashes(args.source),
            "baseline_source_hashes": evidence.source_hashes(args.baseline),
            "runner_hashes": script_hashes(),
            "plan_sha256": evidence.artifact_sha256(Path(__file__).with_name("plan.json")),
            "environment": env, "handoff_sha256": cfg["handoff_sha256"],
            "configurations": cfg["arms"], "coordinates": coordinates,
            "seed_namespace": cfg[f"stage_{args.stage.lower()}"]["namespace"],
            "gate_sha256": gate_hash,
            "gate_path": None if args.gate is None else str(args.gate.resolve()),
            "baseline_root": str(args.baseline.resolve()),
            "source_root": str(args.source.resolve()),
            "storage_cap_bytes": cfg["storage_cap_bytes"],
            "audit_frames": cfg["audit_frames"],
            "scope": "bounded adaptive exploratory allocation, no confirmation"}


def frame_observation(system, code, stage, snr_centi, frame):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation

    seed = seed_descriptor(stage, snr_centi, frame)
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
    truth = {key: np.asarray(raw[key]) for key in
             ("info", "coded", "data", "noise")}
    truth.update({key: np.asarray(raw["params"][key]) for key in
                  ("l_i", "k_real", "g_i")})
    truth["unit_scale"] = float(unit)
    return observed, truth, seed


def preserve_orphan(out, path, evidence):
    if not path.exists():
        return None
    digest = evidence.artifact_sha256(path)
    target = out / "orphans" / f"{path.stem}.{digest[:12]}{path.suffix}"
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        raise ValueError("orphan target already exists")
    os.replace(path, target)
    return {"original": str(path.relative_to(out)),
            "preserved": str(target.relative_to(out)), "sha256": digest}


def save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence):
    stem = f"s{snr}_f{frame:03d}"
    for kind, payload in (("input", observed), ("truth", truth)):
        path = out / "heavy" / f"{stem}_{kind}.npz"
        expected_id = identity(run_hash, f"heavy_{kind}", snr, frame)
        if path.exists():
            evidence.load_artifact(path, expected_id)
        else:
            evidence.save_artifact(path, payload, expected_id)


def warmup(system, code, configurations):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
    from native_twofft import receive
    from native_controls import receive_control

    def rng_factory(rep, index, component, *, split):
        return np.random.default_rng(np.random.SeedSequence(
            [20260921, 940317, 9, component]))

    raw = make_frame(system, code, 0, 0, 6.5, split=2, rng_factory=rng_factory)
    raw, _ = physical_observation(raw, system, prefix_length=system.l_max_cap)
    unit = np.sqrt(2 * (1 - system.rho))
    obs = {"y": raw["y"] / unit, "pilot": raw["pilot"] / unit,
           "sigma2": float(raw["sigma2"]) / unit**2}
    started = time.perf_counter()
    for arm, config in configurations.items():
        if config["family"] == "tf":
            receive(obs, system, code, rounds=2, iterations=20,
                    ce_mode=config["ce_mode"], gain_mode=config["gain_mode"])
        else:
            receive_control(obs, system, code, kind=config["family"],
                            iterations=config["iterations"], ce_mode=config["ce_mode"])
    return time.perf_counter() - started


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
        raise RuntimeError("fixed 512 MiB campaign evidence cap reached")


def main(argv=None):
    global ACTIVE
    args = parser().parse_args(argv)
    args.source, args.baseline, args.out = (item.resolve() for item in
                                            (args.source, args.baseline, args.out))
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from native_twofft import receive
    from native_controls import receive_control
    from afdm_sp_joint_unrolled.e1_ldpc import extract_info

    manifest = make_manifest(args, evidence)
    out = args.out
    if out.exists():
        from verify import validate_run

        checked = validate_run(out, args.source, args.baseline)
        if checked["manifest"] != manifest:
            raise ValueError("existing run identity differs before context/write")
        done = set(checked["index"])
        if not checked["pending"]:
            print("complete valid run; no receiver calls", flush=True)
            return
    else:
        done = set()
        (out / "frames").mkdir(parents=True)
        (out / "checkpoints").mkdir()
        (out / "attempts").mkdir()
        (out / "heavy").mkdir()
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
    selected = {arm: manifest["configurations"][arm]
                for _, _, arm in manifest["coordinates"]}
    warm_seconds = warmup(system, code, selected)
    append_jsonl(out / "warmups.jsonl", {"seconds": warm_seconds,
        "stage": args.stage, "pid": os.getpid(), "finished_epoch": time.time(),
        "scope": "phase-9 observed warmup, outside measured radio calls"})

    all_seeds = historical_channel_seeds()
    if args.stage == "B":
        gate = json.loads(args.gate.read_text())
        all_seeds.update(gate["stage_a_channel_seeds"])
    grouped = {}
    for snr, frame, arm in manifest["coordinates"]:
        grouped.setdefault((snr, frame), []).append(arm)
    for (snr, frame), arms in grouped.items():
        ACTIVE = None
        if args.audit_only and frame not in manifest["audit_frames"]:
            continue
        started_generation = time.perf_counter()
        observed, truth, seed = frame_observation(system, code, args.stage, snr, frame)
        if seed["channel_seed"] in all_seeds:
            raise ValueError("channel seed collides with imported exploratory or campaign frame")
        all_seeds.add(seed["channel_seed"])
        input_hash = observation_hash(observed)
        generation_seconds = time.perf_counter() - started_generation
        ACTIVE = (out, run_hash, snr, frame, None, observed, truth, evidence)
        stem = f"s{snr}_f{frame:03d}"
        frame_path = out / "frames" / f"{stem}_truth.npz"
        input_path = out / "frames" / f"{stem}_input.npz"
        input_id = identity(run_hash, "frame_input", snr, frame)
        if input_path.exists():
            previous, _ = evidence.load_artifact(input_path, input_id)
            if observation_hash(previous) != input_hash:
                raise ValueError("regenerated observation differs from saved paired input")
        else:
            evidence.save_artifact(input_path, observed, input_id)
        input_sha = evidence.artifact_sha256(input_path)
        frame_payload = {"seed": seed, "input_hash": input_hash,
                         "info": bits(truth["info"]), "coded": bits(truth["coded"]),
                         "l_i": truth["l_i"], "k_real": truth["k_real"],
                         "g_i": truth["g_i"], "unit_scale": truth["unit_scale"]}
        frame_id = identity(run_hash, "frame_truth", snr, frame)
        if frame_path.exists():
            prior, _ = evidence.load_artifact(frame_path, frame_id)
            if (prior["seed"] != seed or prior["input_hash"] != input_hash
                    or any(not np.array_equal(prior[name], frame_payload[name])
                           for name in ("l_i", "k_real", "g_i"))
                    or any(not np.array_equal(unbits(prior[name]), unbits(frame_payload[name]))
                           for name in ("info", "coded"))):
                raise ValueError("regenerated frame differs from saved paired frame")
        else:
            evidence.save_artifact(frame_path, frame_payload, frame_id)
        frame_sha = evidence.artifact_sha256(frame_path)
        audit = frame in manifest["audit_frames"]
        if audit:
            save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence)
            check_storage(out, manifest["storage_cap_bytes"])
        rotation = (frame + snr // 50) % len(arms)
        for arm in arms[rotation:] + arms[:rotation]:
            key = (snr, frame, arm)
            if key in done:
                continue
            ACTIVE = (out, run_hash, snr, frame, arm, observed, truth, evidence)
            config = manifest["configurations"][arm]
            prefix = f"{stem}_{arm}"
            attempted = out / "attempts" / f"{prefix}.npz"
            orphaned = []
            for path in [attempted, *sorted((out / "checkpoints").glob(f"{prefix}_r*.npz")),
                         *sorted((out / "heavy").glob(f"{prefix}*"))]:
                item = preserve_orphan(out, path, evidence)
                if item is not None:
                    orphaned.append(item)
            if orphaned:
                append_jsonl(out / "orphans" / "preserved.jsonl",
                             {"key": key, "artifacts": orphaned})
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
                      "receiver_reported_seconds": None if result is None else result[2]["seconds"]}
            marker_sha = evidence.save_artifact(attempted,
                {"status": status, "checkpoints": scored,
                 "exception": exception}, identity(run_hash, "attempt", snr, frame, arm))
            record["artifact_sha256"] = marker_sha
            record["scoring_storage_seconds"] = finite_seconds(
                time.perf_counter() - started - complete, "scoring/storage")
            append_jsonl(out / "ledger.jsonl", record)
            done.add(key)
            check_storage(out, manifest["storage_cap_bytes"])
        print(stem, "complete", flush=True)
        ACTIVE = None
    if not args.audit_only:
        from verify import validate_run

        checked = validate_run(out, args.source, args.baseline, require_complete=True)
        evidence.write_json_atomic(out / "completion.json",
            {"status": "complete", "records": len(checked["records"]),
             "run_identity_sha256": run_hash, "total_bytes": byte_count(out)})


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if ACTIVE is not None:
            out, run_hash, snr, frame, arm, observed, truth, evidence = ACTIVE
            try:
                save_heavy_frame(out, run_hash, snr, frame, observed, truth, evidence)
                suffix = "frame" if arm is None else arm
                path = out / "heavy" / f"s{snr}_f{frame:03d}_{suffix}_integrity_exception.json"
                preserve_orphan(out, path, evidence)
                evidence.write_json_atomic(path,
                    {"exception": repr(error), "traceback": traceback.format_exc()})
            except Exception as preserve_error:
                print(f"integrity exception preservation failed: {preserve_error!r}",
                      file=sys.stderr)
        raise
