"""Paired local research driver with fail-closed, resumable evidence writes."""
import os

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(key, "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import argparse
import hashlib
import json
import time
import traceback
from pathlib import Path

import numpy as np

from evidence import (
    FORMAT_VERSION,
    artifact_sha256,
    bind_runtime_environment,
    canonical_hash,
    frame_seed_descriptor,
    load_artifact,
    manifest_identity,
    save_artifact,
    seed_contract,
    source_hashes,
    validate_run,
    verify_runtime_binding,
    write_json_atomic,
)
from receiver import context, run, run_native
from afdm_sp_joint_unrolled.budgeted_support_eval import make_frame
from afdm_sp_joint_unrolled.supplement_g1 import physical_observation
from afdm_sp_joint_unrolled.e1_ldpc import extract_info, build_code


ROOT = Path(__file__).resolve().parents[1]


def hashes():
    """Compatibility alias for older lock utilities."""
    return source_hashes(ROOT)


def _safe(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def _json_value(value):
    return json.loads(json.dumps(value, default=_safe, allow_nan=False))


def _append_jsonl(path, value):
    payload = json.dumps(value, default=_safe, allow_nan=False) + "\n"
    with Path(path).open("a") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("development", "confirmation"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--frames", type=int)
    parser.add_argument("--arms", nargs="*")
    parser.add_argument("--cell", type=int)
    return parser


def resolve_plan(args, protocol, catalog, current, environment):
    if args.phase == "confirmation":
        if args.lock is None or args.frames is not None or args.arms is not None:
            raise ValueError("confirmation requires --lock and forbids frame/arm overrides")
        lock = json.loads(args.lock.read_text())
        if lock.get("source_hashes") != current:
            raise ValueError("source/configuration hashes changed after lock")
        if lock.get("environment") != environment:
            raise ValueError("runtime environment differs from the development lock")
        cells = lock.get("cells")
        ids = lock.get("configurations")
        frames = lock.get("frames_per_cell")
        phase_code = protocol["phase_codes"]["confirmation"]
    else:
        if args.lock is not None:
            raise ValueError("development does not consume a confirmation lock")
        cells = protocol["development_cells"]
        if args.arms is not None and not args.arms:
            raise ValueError("--arms must name at least one configuration")
        ids = list(catalog) if args.arms is None else list(args.arms)
        frames = protocol["development_frames_per_cell"] if args.frames is None else args.frames
        phase_code = protocol["phase_codes"]["development"]
    if args.cell is not None:
        cells = [cell for cell in cells if cell.get("id") == args.cell]
    if not cells:
        raise ValueError("no registered cells selected")
    if type(frames) is not int or frames < 1:
        raise ValueError("frame count must be a positive integer")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError("configuration IDs must be nonempty and unique")
    if any(ident not in catalog for ident in ids):
        raise ValueError("unknown configuration ID")
    planned = {
        "format_version": FORMAT_VERSION,
        "phase": args.phase,
        "source_hashes": current,
        "cells": cells,
        "configurations": {ident: catalog[ident] for ident in ids},
        "frames": frames,
        "environment": environment,
        "seed_contract": seed_contract(phase_code),
    }
    manifest_identity(planned)
    return planned, phase_code


def _frame_paths(out, cell, frame):
    stem = f"c{cell:02d}_f{frame:05d}"
    return stem, out / "arrays" / f"{stem}_input.npz", out / "truth" / f"{stem}.npz"


def _load_or_create_frame(out, run_hash, system, code, cell, frame, frame_seed_contract):
    stem, input_path, truth_path = _frame_paths(out, cell["id"], frame)
    input_identity = {"kind": "input", "cell": cell["id"], "frame": frame,
                      "run_identity_sha256": run_hash}
    truth_identity = {"kind": "truth", "cell": cell["id"], "frame": frame,
                      "run_identity_sha256": run_hash}
    seed = frame_seed_descriptor(frame_seed_contract, cell["id"], frame)
    if input_path.exists() != truth_path.exists():
        raise ValueError(f"input/truth crash state differs for {stem}")
    if input_path.exists():
        observed, _ = load_artifact(input_path, expected_identity=input_identity)
        truth, _ = load_artifact(truth_path, expected_identity=truth_identity)
        if observed.get("seed") != seed or truth.get("seed") != seed:
            raise ValueError(f"frame seed provenance differs for {stem}")
        return observed, truth, artifact_sha256(input_path), artifact_sha256(truth_path)

    def rng_factory(rep, index, component, *, split):
        return np.random.default_rng(np.random.SeedSequence(
            [*frame_seed_contract["entropy_prefix"], frame_seed_contract["phase_code"],
             cell["id"], index, component]))

    raw = make_frame(system, code, 0, frame, cell["snr_db"], split=2, rng_factory=rng_factory)
    if int(raw["channel_seed"]) != seed["channel_seed"]:
        raise ValueError(f"generated channel seed differs for {stem}")
    if cell.get("same_delay_collision", False):
        raw["params"]["l_i"][1] = raw["params"]["l_i"][0]
    raw, _ = physical_observation(raw, system, prefix_length=system.l_max_cap)
    unit_scale = np.sqrt(2 * (1 - system.rho))
    observed = {
        "y": raw["y"] / unit_scale,
        "pilot": raw["pilot"] / unit_scale,
        "sigma2": float(raw["sigma2"]) / unit_scale ** 2,
        "seed": seed,
    }
    truth = {key: np.asarray(raw[key]) for key in ("coded", "info", "data", "noise")}
    truth.update({key: np.asarray(raw["params"][key]) for key in ("l_i", "k_real", "g_i")})
    truth["unit_scale"] = np.asarray(unit_scale)
    truth["seed"] = seed
    truth_hash = save_artifact(truth_path, truth, truth_identity)
    input_hash = save_artifact(input_path, observed, input_identity)
    return observed, truth, input_hash, truth_hash


def _arm_payload(result, state):
    front_keys = (
        "decoder_records", "ce_inputs", "mu", "v", "prior", "channel_llr",
        "delays", "dopplers", "gains", "source", "sigma_final", "native_initial_state",
    )
    front = {key: state.get(key) for key in front_keys if key in state}
    contract = {key: value for key, value in result.items()
                if key not in ("arrays", "decoded", "info_hat", "llr", "decision_timeline")}
    payload = {
        "decoded": result["decoded"],
        "info_hat": result["info_hat"],
        "llr": result["llr"],
        "result": result.get("arrays", {}),
        "front": front,
        "result_contract": contract,
        "decision_timeline": result.get("decision_timeline", []),
    }
    if "H" in state:
        matrix = np.asarray(state["H"])
        rows, columns = np.nonzero(matrix)
        payload["front_H_coo"] = {
            "rows": rows.astype(np.int32),
            "columns": columns.astype(np.int32),
            "data": matrix[rows, columns],
            "shape": np.asarray(matrix.shape, dtype=np.int32),
            "semantics": "exact nonzero COO of actual damped/masked I1 H_est",
        }
    return payload


def _record_success(result, code, truth, base):
    def optional_seconds(name):
        value = result.get(name)
        return None if value is None else float(value)

    timeline = []
    for event in result.get("decision_timeline", []):
        timeline.append({
            "elapsed": float(event["elapsed"]),
            "info_errors": int(np.sum(extract_info(code, event["decoded"]) != truth["info"])),
        })
    base.update({
        "status": "ok",
        "info_errors": int(np.sum(result["info_hat"] != truth["info"])),
        "seconds": float(result["seconds_complete"]),
        "front_seconds": float(result["front_seconds"]),
        "refit_seconds": optional_seconds("refit_seconds"),
        "detector_seconds": optional_seconds("detector_seconds"),
        "decoder_seconds": optional_seconds("decoder_seconds"),
        "instrumentation_seconds": optional_seconds("instrumentation_seconds"),
        "failed_round_seconds": float(result.get("failed_round_seconds", 0.0)),
        "round_timings": result.get("round_timings", []),
        "timeline": timeline,
        "events": result.get("events", []),
    })
    return base


def main(argv=None):
    args = _parser().parse_args(argv)
    protocol = json.loads((ROOT / "protocol" / "protocol.json").read_text())
    catalog = json.loads((ROOT / "protocol" / "configurations.json").read_text())
    current = source_hashes(ROOT)
    environment = bind_runtime_environment()
    planned, phase_code = resolve_plan(args, protocol, catalog, current, environment)
    out = args.out
    existing = out.exists()
    if existing:
        checked = validate_run(out, expected_identity=planned, reconcile_orphans=True)
        pending = set(checked["pending"])
        if not pending:
            print(out, "already complete; validated without receiver execution", flush=True)
            return
    else:
        pending = {
            (cell["id"], frame, arm)
            for cell in planned["cells"]
            for frame in range(planned["frames"])
            for arm in planned["configurations"]
        }

    system, model, base_code, header = context()
    verify_runtime_binding()
    header = _json_value(header)
    if existing:
        if checked["manifest"].get("header") != header:
            raise ValueError("receiver header differs from the existing run")
        manifest = checked["manifest"]
    else:
        out.mkdir(parents=True)
        (out / "arrays").mkdir()
        (out / "truth").mkdir()
        manifest = dict(planned, header=header, clock="perf_counter",
                        storage_outside_receiver_timer=True)
        write_json_atomic(out / "manifest.json", manifest)
    run_hash = canonical_hash(manifest_identity(manifest))

    pending_arms = {arm for _, _, arm in pending}

    def warm_rng(rep, index, component, *, split):
        return np.random.default_rng(np.random.SeedSequence([20260920, 480017, 0, index, component]))

    warm = make_frame(system, base_code, 0, 0, 8, split=2, rng_factory=warm_rng)
    warm, _ = physical_observation(warm, system, prefix_length=system.l_max_cap)
    warm_observed = {key: warm[key] for key in ("y", "pilot", "sigma2")}
    for ident in planned["configurations"]:
        if ident not in pending_arms:
            continue
        configuration = planned["configurations"][ident]
        if configuration.get("native"):
            run_native(warm_observed, system, base_code, configuration)
        else:
            run(warm_observed, model, system, base_code, configuration)

    for cell in planned["cells"]:
        cell_pending = {key for key in pending if key[0] == cell["id"]}
        if not cell_pending:
            continue
        code = build_code(2048, d_v=3, d_c=6, seed=cell.get("code_seed", 20260726))
        cell_metadata = {
            "cell": cell,
            "code_n": code["n"],
            "code_k": code["k"],
            "generator_sha256": hashlib.sha256(np.asarray(code["G"]).tobytes()).hexdigest(),
            "bit_order": "all I then all Q",
            "internal_data_power": 0.5,
            "run_identity_sha256": run_hash,
        }
        cell_path = out / f"cell_{cell['id']:02d}_metadata.json"
        if cell_path.exists():
            if json.loads(cell_path.read_text()) != cell_metadata:
                raise ValueError(f"cell metadata differs for cell {cell['id']}")
        else:
            write_json_atomic(cell_path, cell_metadata)
        system.P_paths = cell.get("paths", 8)
        system.rho = cell.get("rho", 0.5)
        for frame in range(planned["frames"]):
            frame_pending = {arm for c, f, arm in cell_pending if f == frame and c == cell["id"]}
            if not frame_pending:
                continue
            observed, truth, input_hash, truth_hash = _load_or_create_frame(
                out, run_hash, system, code, cell, frame, planned["seed_contract"])
            stem = f"c{cell['id']:02d}_f{frame:05d}"
            identifiers = list(planned["configurations"])
            rotation = (frame + cell["id"]) % len(identifiers)
            order = identifiers[rotation:] + identifiers[:rotation]
            for ident in order:
                if ident not in frame_pending:
                    continue
                marker = out / "arrays" / f"{stem}_{ident}.npz"
                if marker.exists():
                    raise ValueError(f"pending marker was not reconciled: {marker}")
                configuration = planned["configurations"][ident]
                record = {"cell": cell["id"], "frame": frame, "arm": ident,
                          "snr_db": cell["snr_db"], "input_sha256": input_hash,
                          "truth_sha256": truth_hash}
                arm_started = time.perf_counter()
                try:
                    result, state = (run_native(observed, system, code, configuration)
                                     if configuration.get("native")
                                     else run(observed, model, system, code, configuration))
                except (np.linalg.LinAlgError, FloatingPointError) as exc:
                    failed_seconds = time.perf_counter() - arm_started
                    record.update(status="numerical_failure", info_errors=len(truth["info"]),
                                  seconds=failed_seconds, timeline=[], events=[],
                                  front_seconds=None, refit_seconds=None, detector_seconds=None,
                                  decoder_seconds=None, instrumentation_seconds=None,
                                  failed_round_seconds=failed_seconds, round_timings=[],
                                  stage_timing_scope=("entire receiver attempt failed before a "
                                                      "reliable stage split was returned"),
                                  error=repr(exc), traceback=traceback.format_exc())
                    payload = {"failure": np.asarray([1], dtype=np.uint8),
                               "error": repr(exc), "traceback": record["traceback"]}
                else:
                    record = _record_success(result, code, truth, record)
                    payload = _arm_payload(result, state)
                    if frame < 2 and "H" in state:
                        payload["front_H_canary"] = state["H"]
                marker_identity = {
                    "kind": "arm", "cell": cell["id"], "frame": frame, "arm": ident,
                    "status": record["status"], "run_identity_sha256": run_hash,
                }
                record["artifact_sha256"] = save_artifact(marker, payload, marker_identity)
                _append_jsonl(out / "ledger.jsonl", record)
            print(stem, "done", flush=True)


if __name__ == "__main__":
    main()
