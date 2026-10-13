#!/usr/bin/env python3
"""Run one frozen staged campaign phase with compact, paired evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from compact import (
    SCHEMA, append_jsonl, array_hash, artifact_identity, attach_source,
    campaign_hashes, compact_events, directory_bytes, finite_seconds, load_plan,
    observed_hash, pack_bits, plan_path, process_memory_kib, validate_run,
)

ACTIVE_FRAME = None


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--source", required=True, type=Path)
    result.add_argument("--stage", required=True, type=int, choices=(1, 2))
    result.add_argument("--out", required=True, type=Path)
    result.add_argument("--gate", type=Path)
    result.add_argument("--audit-only", action="store_true")
    return result


def json_safe(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def source_scoped_manifest(source, stage, gate, evidence):
    plan = load_plan()
    catalog = json.loads((source / "protocol" / "configurations.json").read_text())
    contract = plan[f"stage{stage}"]
    if stage == 1:
        if gate is not None:
            raise ValueError("Stage 1 cannot use a selection gate")
        cells, arms, gate_hash = contract["cells"], contract["arms"], None
    else:
        if gate is None:
            raise ValueError("Stage 2 requires frozen Stage 1 gate")
        decision = json.loads(gate.read_text())
        from select_stage import build_gate

        if decision != build_gate(decision["source_run_dir"], source):
            raise ValueError("Stage 1 gate differs from independently recounted Stage 1")
        if decision.get("schema") != "sp-afdm-stage1-gate-v1" or decision.get("decision") != "advance":
            raise ValueError("Stage 1 gate does not permit Stage 2")
        cells, arms = decision["stage2_cells"], decision["stage2_arms"]
        if len(cells) > contract["max_cells"] or len(arms) > contract["max_arms"]:
            raise ValueError("Stage 2 gate exceeds frozen maximum")
        if not arms or arms[0] != decision["selected_i1_anchor"] or len(set(arms)) != len(arms):
            raise ValueError("Stage 2 anchor/arm identity differs")
        gate_hash = evidence.artifact_sha256(gate)
    if any(arm not in catalog for arm in arms):
        raise ValueError("unregistered arm in staged campaign")
    environment = evidence.bind_runtime_environment()
    return {
        "schema": SCHEMA,
        "phase": "development",
        "stage": stage,
        "plan_sha256": evidence.artifact_sha256(plan_path()),
        "frozen_markdown_sha256": plan["frozen_markdown_sha256"],
        "campaign_hashes": campaign_hashes(),
        "receiver_commit": plan["receiver_commit"],
        "receiver_source_hashes": evidence.source_hashes(source),
        "environment": environment,
        "seed_contract": evidence.seed_contract(1),
        "cells": cells,
        "arms": arms,
        "configurations": {arm: catalog[arm] for arm in arms},
        "absolute_frames": list(range(contract["first_absolute_frame"],
                                      contract["first_absolute_frame"] + contract["frames_per_cell"])),
        "audit_absolute_frame": contract["audit_absolute_frame"],
        "selection_gate_sha256": gate_hash,
        "selection_gate_path": None if gate is None else str(gate.resolve()),
        "heavy_cap_bytes": plan["heavy_cap_bytes"],
        "storage_outside_receiver_timer": True,
        "scope": "adaptive exploratory triage; no confirmation lock",
    }


def frame_observation(system, code, cell, frame, contract, evidence):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation

    seed = evidence.frame_seed_descriptor(contract, cell["id"], frame)

    def rng_factory(rep, index, component, *, split):
        entropy = [*contract["entropy_prefix"], contract["phase_code"], cell["id"], index, component]
        return np.random.default_rng(np.random.SeedSequence(entropy))

    raw = make_frame(system, code, 0, frame, cell["snr_db"], split=2, rng_factory=rng_factory)
    if int(raw["channel_seed"]) != seed["channel_seed"]:
        raise ValueError("generated channel seed differs from registered entropy")
    raw, _ = physical_observation(raw, system, prefix_length=system.l_max_cap)
    unit_scale = np.sqrt(2 * (1 - system.rho))
    observed = {"y": raw["y"] / unit_scale, "pilot": raw["pilot"] / unit_scale,
                "sigma2": float(raw["sigma2"]) / unit_scale**2}
    truth = {key: np.asarray(raw[key]) for key in ("info", "coded", "data", "noise")}
    truth.update({key: np.asarray(raw["params"][key]) for key in ("l_i", "k_real", "g_i")})
    truth["unit_scale"] = np.asarray(unit_scale)
    return observed, truth, seed


def truth_payload(truth, seed, input_hash):
    return {"seed": seed, "input_hash": input_hash,
            "info": pack_bits(truth["info"]), "coded": pack_bits(truth["coded"]),
            "l_i": truth["l_i"], "k_real": truth["k_real"], "g_i": truth["g_i"],
            "unit_scale": float(truth["unit_scale"])}


def final_arrays(result):
    arrays = result.get("arrays", {})
    rounds = sorted({int(key.split("_")[0][5:]) for key in arrays if key.startswith("round")})
    if rounds:
        prefix = f"round{rounds[-1]}_"
        return {key[len(prefix):]: value for key, value in arrays.items() if key.startswith(prefix)}
    return arrays


def decoder_summary(result, state):
    def summarize(item):
        record = item.get("record", item)
        metadata = record.get("metadata", {})
        return {"stage": record.get("evidence_stage", record.get("stage")),
                "round": item.get("round"), "iterations": record.get("iterations"),
                "decode_ok": record.get("decode_ok"),
                "syndrome": record.get("syndrome"),
                "syndrome_trace": record.get("syndrome_trace", metadata.get("syndrome_trace"))}

    return {"front": [summarize(x) for x in state.get("decoder_records", [])],
            "terminal_and_rounds": [summarize(x) for x in result.get("decoder_records", [])]}


def nmse_diagnostics(result, state, truth, system):
    from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix

    n = system.N_total
    h_true = physical_channel_matrix(n, system.c1, system.c2,
        truth["l_i"], truth["k_real"], truth["g_i"], prefix_length=system.l_max_cap)
    arrays = final_arrays(result)
    small_paths = None
    if all(name in arrays for name in ("path_delays", "path_dopplers", "path_gains")):
        small_paths = {"delays": np.asarray(arrays["path_delays"]),
                       "dopplers": np.asarray(arrays["path_dopplers"]),
                       "gains": np.asarray(arrays["path_gains"])}
        h_est = physical_channel_matrix(n, system.c1, system.c2,
            small_paths["delays"], small_paths["dopplers"], small_paths["gains"],
            prefix_length=system.l_max_cap)
        scope = "physical-path model; reconstructible from saved parameters"
    elif "H" in state:
        h_est = np.asarray(state["H"])
        scope = "actual damped/masked I1 H; producer-side except fixed heavy audit"
    else:
        raise ValueError("receiver returned no reconstructible channel estimate")
    denominator = float(np.vdot(h_true, h_true).real)
    if denominator <= 0 or h_est.shape != h_true.shape or not np.isfinite(h_est).all():
        raise ValueError("invalid channel estimate for offline NMSE")
    nmse = float(np.vdot(h_est - h_true, h_est - h_true).real / denominator)
    gamma = arrays.get("ce_gamma")
    if gamma is not None:
        gamma = np.asarray(gamma)
        if gamma.size > 256:
            raise ValueError("small Gamma diagnostic unexpectedly exceeds 256 entries")
    history = arrays.get("ce_objective_history")
    selected = arrays.get("selected_shifts")
    return {"channel_nmse": nmse, "channel_scope": scope,
            "channel_estimate_sha256": array_hash(h_est),
            "truth_channel_sha256": array_hash(h_true),
            "fitted_paths": small_paths,
            "initial_support_count": int(len(state.get("delays", []))),
            "final_support_count": None if small_paths is None else int(len(small_paths["delays"])),
            "selected_shift_count": None if selected is None else int(len(selected)),
            "ce_gamma": gamma,
            "ce_gamma_trace": None if gamma is None else np.trace(gamma),
            "ce_gamma_offdiag_fro_ratio": (None if gamma is None else float(
                np.linalg.norm(gamma - np.diag(np.diag(gamma))) / max(np.linalg.norm(gamma), 1e-12))),
            "ce_objective_initial_final": (None if history is None or len(history) == 0
                                           else [float(history[0]), float(history[-1])]),
            "ce_evaluations": next((int(event["evaluations"]) for event in result.get("events", [])
                                    if isinstance(event, dict) and "evaluations" in event), None)}


def heavy_bytes(out):
    folder = out / "heavy"
    return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file()) if folder.exists() else 0


def check_heavy_cap(out, cap):
    used = directory_bytes(out)
    if used >= cap:
        status = {"status": "resource_limit", "total_bytes": used,
                  "heavy_bytes": heavy_bytes(out), "cap_bytes": cap}
        (out / "resource_limit.json").write_text(json.dumps(status, indent=2) + "\n")
        raise RuntimeError("campaign evidence reached the fixed 512 MiB cap")


def heavy_frame(out, run_hash, cell, frame, observed, truth, evidence):
    folder = out / "heavy"
    folder.mkdir(exist_ok=True)
    stem = f"c{cell:02d}_f{frame:06d}"
    for kind, payload in (("input", observed), ("truth", truth)):
        path = folder / f"{stem}_{kind}.npz"
        if path.exists():
            evidence.load_artifact(path, artifact_identity(run_hash, f"heavy_{kind}", cell, frame))
        else:
            evidence.save_artifact(path, payload, artifact_identity(run_hash, f"heavy_{kind}", cell, frame))


def heavy_arm(out, run_hash, cell, frame, arm, result, state, evidence):
    from run_local import _arm_payload

    path = out / "heavy" / f"c{cell:02d}_f{frame:06d}_{arm}.npz"
    payload = _arm_payload(result, state)
    if "H" in state:
        payload["front_H_canary"] = state["H"]
    evidence.save_artifact(path, payload, artifact_identity(run_hash, "heavy_arm", cell, frame, arm))
    return evidence.artifact_sha256(path)


def preserve_orphan(out, path, evidence):
    if not path.exists():
        return None
    digest = evidence.artifact_sha256(path)
    target = out / "orphans" / f"{path.stem}.{digest[:12]}{path.suffix}"
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        raise ValueError("orphan preservation target exists")
    os.replace(path, target)
    return {"original": str(path.relative_to(out)), "preserved": str(target.relative_to(out)),
            "sha256": digest}


def warm_arms(system, model, code, manifest):
    from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
    from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
    from receiver import run, run_native

    def rng_factory(rep, index, component, *, split):
        return np.random.default_rng(np.random.SeedSequence([20260920, 480017, 0, index, component]))

    warm = make_frame(system, code, 0, 0, 8, split=2, rng_factory=rng_factory)
    warm, _ = physical_observation(warm, system, prefix_length=system.l_max_cap)
    observed = {key: warm[key] for key in ("y", "pilot", "sigma2")}
    started = time.perf_counter()
    for arm in manifest["arms"]:
        config = manifest["configurations"][arm]
        if config.get("native"):
            run_native(observed, system, code, config)
        else:
            run(observed, model, system, code, config)
    return time.perf_counter() - started


def main(argv=None):
    global ACTIVE_FRAME
    args = parser().parse_args(argv)
    source = args.source.resolve()
    if source.name != load_plan()["receiver_root_name"]:
        raise ValueError("use the reviewed frozen receiver source root")
    evidence = attach_source(source)
    from afdm_sp_joint_unrolled.e1_ldpc import build_code, extract_info
    from receiver import context, run, run_native

    planned = source_scoped_manifest(source, args.stage, args.gate, evidence)
    out = args.out.resolve()
    if out.exists():
        checked = validate_run(out, source)
        if checked["manifest"] != planned:
            raise ValueError("existing compact run manifest differs")
        done = set(checked["index"])
        if not checked["pending"]:
            print("complete campaign already validated; no receiver execution", flush=True)
            return
    else:
        done = set()
        out.mkdir(parents=True)
        (out / "compact").mkdir()
        (out / "heavy").mkdir()
        evidence.write_json_atomic(out / "manifest.json", planned)
    run_hash = evidence.canonical_hash(planned)
    system, model, base_code, header = context()
    evidence.verify_runtime_binding()
    header = json.loads(json.dumps(header, default=json_safe, allow_nan=False))
    header_path = out / "context_header.json"
    if header_path.exists():
        if json.loads(header_path.read_text()) != header:
            raise ValueError("receiver context header differs on resume")
    else:
        evidence.write_json_atomic(header_path, header)
    started_stage = time.perf_counter()
    warm_seconds = warm_arms(system, model, base_code, planned)
    append_jsonl(out / "warmups.jsonl", {"seconds": warm_seconds,
        "scope": "phase-zero all selected arms; outside timed campaign records",
        "process_wall_started_epoch": time.time(), "pid": os.getpid()})

    all_seed_ids = set()
    if args.stage == 2:
        all_seed_ids.update(json.loads(args.gate.read_text())["stage1_channel_seeds"])
    for cell in planned["cells"]:
        system.P_paths = cell.get("paths", 8)
        system.rho = cell.get("rho", .5)
        code = build_code(2048, d_v=3, d_c=6, seed=20260726)
        code_hash = hashlib.sha256(np.asarray(code["G"]).tobytes()).hexdigest()
        if code_hash != header["code_g_sha256"]:
            raise ValueError("LDPC generator differs from reviewed receiver")
        for frame in planned["absolute_frames"]:
            ACTIVE_FRAME = None
            if args.audit_only and frame != planned["audit_absolute_frame"]:
                continue
            generation_start = time.perf_counter()
            observed, truth, seed = frame_observation(system, code, cell, frame, planned["seed_contract"], evidence)
            if seed["channel_seed"] in all_seed_ids:
                raise ValueError("repeated channel seed within campaign")
            all_seed_ids.add(seed["channel_seed"])
            input_hash = observed_hash(observed)
            ACTIVE_FRAME = {"out": out, "run_hash": run_hash, "cell": cell["id"],
                            "frame": frame, "arm": None, "observed": observed,
                            "truth": truth, "evidence": evidence}
            frame_generation_seconds = time.perf_counter() - generation_start
            stem = f"c{cell['id']:02d}_f{frame:06d}"
            truth_path = out / "compact" / f"{stem}_truth.npz"
            identity = artifact_identity(run_hash, "truth", cell["id"], frame)
            if truth_path.exists():
                prior, _ = evidence.load_artifact(truth_path, identity)
                regenerated = truth_payload(truth, seed, input_hash)
                if (prior["input_hash"] != input_hash or prior["seed"] != seed
                        or any(array_hash(prior[name]) != array_hash(regenerated[name])
                               for name in ("l_i", "k_real", "g_i"))
                        or any(not np.array_equal(prior[name]["bytes"], regenerated[name]["bytes"])
                               for name in ("info", "coded"))):
                    raise ValueError("regenerated frame differs from saved compact truth")
            else:
                evidence.save_artifact(truth_path, truth_payload(truth, seed, input_hash), identity)
            truth_sha = evidence.artifact_sha256(truth_path)
            audit = frame == planned["audit_absolute_frame"]
            if audit:
                heavy_frame(out, run_hash, cell["id"], frame, observed, truth, evidence)
                check_heavy_cap(out, planned["heavy_cap_bytes"])
            ids = planned["arms"]
            rotation = (frame + cell["id"]) % len(ids)
            for arm in ids[rotation:] + ids[:rotation]:
                key = (cell["id"], frame, arm)
                if key in done:
                    continue
                ACTIVE_FRAME["arm"] = arm
                config = planned["configurations"][arm]
                marker = out / "compact" / f"{stem}_{arm}.npz"
                preserved = []
                for path in (marker, out / "heavy" / f"{stem}_{arm}.npz",
                             out / "heavy" / f"{stem}_{arm}_exception.json",
                             out / "heavy" / f"{stem}_{arm}_integrity_exception.json"):
                    item = preserve_orphan(out, path, evidence)
                    if item is not None:
                        preserved.append(item)
                if preserved:
                    append_jsonl(out / "orphans" / "preserved.jsonl", {"key": key,
                                  "artifacts": preserved})
                before = process_memory_kib()
                online_start = time.perf_counter()
                record = {"cell": cell["id"], "absolute_frame": frame, "arm": arm,
                          "snr_db": cell["snr_db"], "input_hash": input_hash,
                          "truth_sha256": truth_sha, "generation_seconds": frame_generation_seconds,
                          "configuration": config}
                try:
                    result, state = (run_native(observed, system, code, config) if config.get("native")
                                     else run(observed, model, system, code, config))
                except (np.linalg.LinAlgError, FloatingPointError) as exc:
                    complete = time.perf_counter() - online_start
                    record.update(status="numerical_failure", seconds=complete,
                        info_errors=None, coded_errors=None, timeline=[],
                        front_seconds=None, refit_seconds=None, detector_seconds=None,
                        decoder_seconds=None, instrumentation_seconds=None,
                        failed_round_seconds=complete, round_timings=[],
                        events=[{"stage": "numerical_failure", "exception": repr(exc)}],
                        traceback=traceback.format_exc(), channel_nmse=None)
                    payload = {"status": "numerical_failure", "decoded": None,
                               "checkpoints": [], "error": repr(exc)}
                    heavy_frame(out, run_hash, cell["id"], frame, observed, truth, evidence)
                    evidence.write_json_atomic(out / "heavy" / f"{stem}_{arm}_exception.json",
                        {"exception": repr(exc), "traceback": record["traceback"]})
                    record["exception_sha256"] = evidence.artifact_sha256(
                        out / "heavy" / f"{stem}_{arm}_exception.json")
                else:
                    complete = finite_seconds(result["seconds_complete"], "receiver complete time")
                    checkpoints = [{"elapsed": float(event["elapsed"]),
                                    "decoded": pack_bits(event["decoded"])}
                                   for event in result.get("decision_timeline", [])]
                    timeline = [{"elapsed": item["elapsed"],
                                 "info_errors": int(np.count_nonzero(
                                     extract_info(code, np.asarray(event["decoded"])) != truth["info"]))}
                                for item, event in zip(checkpoints, result.get("decision_timeline", []))]
                    info_errors = int(np.count_nonzero(result["info_hat"] != truth["info"]))
                    coded_errors = int(np.count_nonzero(result["decoded"] != truth["coded"]))
                    diagnostics = nmse_diagnostics(result, state, truth, system)
                    record.update(status="ok", seconds=complete, info_errors=info_errors,
                        coded_errors=coded_errors, timeline=timeline,
                        front_seconds=result.get("front_seconds"),
                        refit_seconds=result.get("refit_seconds"),
                        detector_seconds=result.get("detector_seconds"),
                        decoder_seconds=result.get("decoder_seconds"),
                        instrumentation_seconds=result.get("instrumentation_seconds"),
                        failed_round_seconds=result.get("failed_round_seconds", 0.0),
                        round_timings=compact_events(result.get("round_timings", [])),
                        events=compact_events(result.get("events", [])),
                        channel_nmse=diagnostics["channel_nmse"],
                        channel_scope=diagnostics["channel_scope"])
                    payload = {"status": "ok", "decoded": pack_bits(result["decoded"]),
                               "checkpoints": checkpoints,
                               "decoder": decoder_summary(result, state),
                               "diagnostics": diagnostics}
                    if audit or result.get("failed_round_seconds", 0.0) > 0:
                        heavy_frame(out, run_hash, cell["id"], frame, observed, truth, evidence)
                        record["heavy_sha256"] = heavy_arm(out, run_hash, cell["id"], frame, arm,
                                                            result, state, evidence)
                record["memory_before"] = before
                record["memory_after"] = process_memory_kib()
                record["memory_scope"] = "shared-process snapshots; not isolated peak RSS"
                marker_hash = evidence.save_artifact(marker, payload,
                    artifact_identity(run_hash, "arm", cell["id"], frame, arm))
                record["artifact_sha256"] = marker_hash
                record["scoring_storage_seconds"] = time.perf_counter() - online_start - complete
                append_jsonl(out / "ledger.jsonl", record)
                done.add(key)
                check_heavy_cap(out, planned["heavy_cap_bytes"])
            print(stem, "complete", flush=True)
            ACTIVE_FRAME = None
    if not args.audit_only:
        checked = validate_run(out, source, require_complete=True)
        warmups = [json.loads(line) for line in (out / "warmups.jsonl").read_text().splitlines()]
        evidence.write_json_atomic(out / "completion.json", {"status": "complete",
            "records": len(checked["records"]), "warmup_seconds_all_invocations": sum(
                item["seconds"] for item in warmups), "warmup_invocations": len(warmups),
            "stage_process_wall_seconds": time.perf_counter() - started_stage,
            "heavy_bytes": heavy_bytes(out), "total_bytes": directory_bytes(out),
            "run_identity_sha256": run_hash})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        if ACTIVE_FRAME is not None:
            context = ACTIVE_FRAME
            try:
                heavy_frame(context["out"], context["run_hash"], context["cell"],
                            context["frame"], context["observed"], context["truth"],
                            context["evidence"])
                stem = f"c{context['cell']:02d}_f{context['frame']:06d}"
                suffix = "frame" if context["arm"] is None else context["arm"]
                path = context["out"] / "heavy" / f"{stem}_{suffix}_integrity_exception.json"
                preserve_orphan(context["out"], path, context["evidence"])
                context["evidence"].write_json_atomic(path, {"exception": repr(exc),
                    "traceback": traceback.format_exc(), "cell": context["cell"],
                    "absolute_frame": context["frame"], "arm": context["arm"]})
            except Exception as preservation_error:
                print(f"integrity exception preservation failed: {preservation_error!r}",
                      file=sys.stderr)
        raise
