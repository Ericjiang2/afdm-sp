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
                    finite_seconds, identity, observation_hash, plan, script_hashes, unbits)


ACTIVE = None


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--source", type=Path, required=True)
    value.add_argument("--baseline", type=Path, required=True)
    value.add_argument("--e1-run", type=Path, required=True)
    value.add_argument("--out", type=Path, required=True)
    value.add_argument("--source-commit", required=True)
    value.add_argument("--replay-only", action="store_true",
                       help="run only three preallocated frame-zero primary parity calls")
    return value


def make_manifest(args, evidence):
    cfg = plan()
    if args.source.name != cfg["source_root_name"]:
        raise ValueError("only the frozen reviewed source root is allowed")
    if evidence.artifact_sha256(args.source / "docs" / "CODEX_HANDOFF.md") != cfg["handoff_sha256"]:
        raise ValueError("canonical handoff differs")
    if args.source_commit != cfg["source_commit"]:
        raise ValueError("frozen numerical source commit differs")
    if evidence.artifact_sha256(args.e1_run / "manifest.json") != cfg["e1_manifest_sha256"]:
        raise ValueError("saved E1 D manifest differs")
    e1_manifest = json.loads((args.e1_run / "manifest.json").read_text())
    if e1_manifest["source_hashes"] != evidence.source_hashes(args.source):
        raise ValueError("frozen numerical source differs from saved E1 D")
    if e1_manifest["baseline_source_hashes"] != evidence.source_hashes(args.baseline):
        raise ValueError("frozen baseline differs from saved E1 D")
    coordinates = [list(item) for item in expected(cfg)]
    if len(coordinates) != cfg["attribution_receiver_calls"]:
        raise ValueError("planned receiver call count differs")
    env = evidence.bind_runtime_environment()
    return {"schema": SCHEMA, "stage": "PartA", "phase": "reused_observation_attribution",
            "source_commit": args.source_commit, "baseline_commit": cfg["baseline_commit"],
            "source_hashes": evidence.source_hashes(args.source),
            "baseline_source_hashes": evidence.source_hashes(args.baseline),
            "runner_hashes": script_hashes(),
            "plan_sha256": evidence.artifact_sha256(Path(__file__).with_name("plan.json")),
            "environment": env, "handoff_sha256": cfg["handoff_sha256"],
            "configurations": cfg["arms"], "coordinates": coordinates,
            "e1_manifest_sha256": cfg["e1_manifest_sha256"],
            "e1_run_identity_sha256": evidence.canonical_hash(e1_manifest),
            "e1_root": str(args.e1_run.resolve()),
            "baseline_root": str(args.baseline.resolve()),
            "source_root": str(args.source.resolve()),
            "storage_cap_bytes": cfg["storage_cap_bytes"],
            "audit_frames": cfg["audit_frames"],
            "scope": "fixed Part A reused-observation attribution; 91 calls, no fresh radio frame"}


def load_e1_frame(args, evidence, manifest, snr, frame):
    e1_hash = manifest["e1_run_identity_sha256"]
    stem = f"s{snr}_f{frame:03d}"
    def e1_identity(kind):
        return {"schema": "spafdm-native-direction-compact/1",
                "run_identity_sha256": e1_hash, "kind": kind,
                "snr_centi_db": snr, "frame": frame}
    input_path = args.e1_run / "frames" / f"{stem}_input.npz"
    truth_path = args.e1_run / "frames" / f"{stem}_truth.npz"
    observed, _ = evidence.load_artifact(input_path,
        e1_identity("frame_input"))
    truth, _ = evidence.load_artifact(truth_path,
        e1_identity("frame_truth"))
    if observation_hash(observed) != truth["input_hash"]:
        raise ValueError("E1 observed/truth binding differs")
    return observed, truth, {
        "input_sha256": evidence.artifact_sha256(input_path),
        "truth_sha256": evidence.artifact_sha256(truth_path)}


def compare_e1_replay(args, evidence, manifest, snr, frame, checkpoints):
    """The three preallocated primary replays are the numerical parity checks."""
    old_hash = manifest["e1_run_identity_sha256"]
    for checkpoint in checkpoints:
        round_index = checkpoint["round"]
        old_path = args.e1_run / "checkpoints" / (
            f"s{snr}_f{frame:03d}_TF_J20_R2_r{round_index}.npz")
        old_id = {"schema": "spafdm-native-direction-compact/1",
                  "run_identity_sha256": old_hash, "kind": "checkpoint",
                  "snr_centi_db": snr, "frame": frame,
                  "arm": "TF_J20_R2", "round": round_index}
        old, _ = evidence.load_artifact(old_path, old_id)
        new = evidence.load_artifact(args.out / checkpoint["path"])[0]
        if not np.array_equal(unbits(old["decoded"]), unbits(new["decoded"])):
            raise ValueError("Part A primary replay decision differs from E1 D")
        for name in ("input_llr", "app", "check", "delays", "dopplers",
                     "gains", "gain_variance", "ce_gains", "mu", "variance"):
            if not np.allclose(old["snapshot"][name], new["snapshot"][name],
                               rtol=1e-10, atol=1e-10):
                raise ValueError(f"Part A primary replay {name} differs from E1 D")


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
    args.source, args.baseline, args.out, args.e1_run = (item.resolve() for item in
                                            (args.source, args.baseline, args.out, args.e1_run))
    evidence = attach(args.source, args.baseline)
    from receiver import context
    from native_twofft import receive
    from controls import receive_intervention
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
    grouped = {}
    for snr, frame, arm in manifest["coordinates"]:
        grouped.setdefault((snr, frame), []).append(arm)
    for (snr, frame), arms in grouped.items():
        if args.replay_only and frame != 0:
            continue
        if args.replay_only:
            arms = [arm for arm in arms if arm == "TF_REPLAY"]
        ACTIVE = None
        observed, truth, e1_sources = load_e1_frame(args, evidence, manifest, snr, frame)
        info_truth = unbits(truth["info"], plan()["source_scope"]["code_k"])
        coded_truth = unbits(truth["coded"], plan()["source_scope"]["code_n"])
        input_hash = observation_hash(observed)
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
        frame_payload = {"seed": truth["seed"], "input_hash": input_hash,
                         "e1_sources": e1_sources,
                         "info": truth["info"], "coded": truth["coded"],
                         "l_i": truth["l_i"], "k_real": truth["k_real"],
                         "g_i": truth["g_i"], "unit_scale": truth["unit_scale"]}
        frame_id = identity(run_hash, "frame_truth", snr, frame)
        if frame_path.exists():
            prior, _ = evidence.load_artifact(frame_path, frame_id)
            if (prior["seed"] != truth["seed"] or prior["input_hash"] != input_hash
                    or prior["e1_sources"] != e1_sources
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
        for arm in arms:
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
                    result = receive_intervention(observed, system, code,
                        intervention=config["intervention"],
                        checkpoint_sink=checkpoint_sink, record_states=audit)
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
            if status == "ok" and arm == "TF_REPLAY":
                compare_e1_replay(args, evidence, manifest, snr, frame, checkpoints)
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
                               "info_errors": int(np.count_nonzero(info_hat != info_truth)),
                               "coded_errors": int(np.count_nonzero(decoded != coded_truth)),
                               "syndrome_weight": int(np.count_nonzero((code["H"] @ decoded) % 2)),
                               "artifact_sha256": checkpoint["artifact_sha256"],
                               "path": checkpoint["path"],
                               "event": checkpoint["event"]})
            record = {"snr_centi_db": snr, "frame": frame, "arm": arm,
                      "configuration": config, "status": status, "seconds": complete,
                      "generation_seconds": 0.0, "reused_e1_sources": e1_sources,
                      "input_hash": input_hash, "input_sha256": input_sha,
                      "frame_sha256": frame_sha,
                      "checkpoints": scored,
                      "info_errors": None if not scored else scored[-1]["info_errors"],
                      "coded_errors": None if not scored else scored[-1]["coded_errors"],
                      "memory_before": before, "memory_after": process_memory(),
                      "memory_scope": "shared-process RSS/HWM snapshots; not isolated receiver peak",
                      "exception_sha256": (None if exception is None else
                          evidence.artifact_sha256(out / "heavy" / f"{prefix}_exception.json")),
                      "receiver_reported_seconds": None if result is None else result[2]["seconds"],
                      "pilot_seconds": None if result is None else result[2]["pilot_seconds"]}
            marker_sha = evidence.save_artifact(attempted,
                {"status": status, "checkpoints": scored,
                 "exception": exception}, identity(run_hash, "attempt", snr, frame, arm))
            record["artifact_sha256"] = marker_sha
            record["scoring_storage_seconds"] = finite_seconds(
                time.perf_counter() - started - complete, "scoring/storage")
            append_jsonl(out / "ledger.jsonl", record)
            done.add(key)
            check_storage(out, manifest["storage_cap_bytes"])
            if status != "ok":
                raise RuntimeError("Part A numerical failure saved; stop further scientific calls")
        print(stem, "complete", flush=True)
        ACTIVE = None
    from verify import validate_run

    checked = validate_run(out, args.source, args.baseline,
                           require_complete=not args.replay_only)
    if args.replay_only:
        if len(checked["records"]) != 3:
            raise ValueError("preallocated primary replay count differs")
        evidence.write_json_atomic(out / "primary_replay_parity.json",
            {"status": "pass", "records": 3, "run_identity_sha256": run_hash,
             "scope": "saved E1 D decoded, LLR, path and estimate parity; no extra calls"})
    else:
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
