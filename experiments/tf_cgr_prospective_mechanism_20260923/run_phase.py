"""Exactly one registered phase of observed-only full wrappers; no truth access."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np

from attest import verify_prediction_handoff, verify_registration_attestation
from branch import base_common_state, final_branch, hash_value
from common import (DATA_CAP, FRAMES, PROJECT, SCHEMA, SECONDS, append_jsonl,
                    frame_id, observation_hash, read_jsonl, registration, seal,
                    sha256, size, verify_seal, write_json)


def _bound_population(root: Path, registration_sha: str) -> dict[int, dict]:
    saved = verify_seal(root, "observed_seal.json")
    rows = read_jsonl(root / "ledger.jsonl")
    if (saved.get("frames") != FRAMES or saved.get("registration_sha256") != registration_sha or
            len(rows) != FRAMES or
            [row["observation_id"] for row in rows] != [frame_id(i) for i in range(FRAMES)]):
        raise ValueError("population allocation/seal differs")
    for index, row in enumerate(rows):
        if (row["frame"] != index or
                saved["files"].get(row["observation_path"]) != row["observation_sha256"]):
            raise ValueError("population file hash differs")
    return {row["frame"]: row for row in rows}


def _base_reference(root: Path, evidence) -> dict[int, tuple[dict, dict]]:
    saved = verify_seal(root, "observed_seal.json")
    rows = read_jsonl(root / "ledger.jsonl")
    if (saved.get("completed_calls") != FRAMES or len(rows) != FRAMES or
            [row["call_index"] for row in rows] != list(range(1, FRAMES + 1)) or
            any(row["arm"] != "BASE" or row["status"] != "ok" for row in rows)):
        raise ValueError("BASE seal/ledger differs")
    result = {}
    for row in rows:
        raw_file = root / row["raw_path"]
        if sha256(raw_file) != row["raw_sha256"]:
            raise ValueError("BASE raw digest differs")
        result[row["frame"]] = (row, evidence.load_artifact(raw_file)[0])
    return result


def _calls(phase: str, lock: dict) -> list[tuple[int, str]]:
    if phase == "base":
        return [(frame, "BASE") for frame in range(FRAMES)]
    if phase != "interventions":
        raise ValueError("phase differs")
    return [(row["frame"], arm) for row in lock["schedule"] for arm in row["arms"]]


def run(args: argparse.Namespace) -> None:
    if args.out.exists():
        raise FileExistsError(args.out)
    limit = SECONDS["base" if args.phase == "base" else "interventions"]
    if args.seconds > limit or args.bytes_cap > DATA_CAP or args.seconds <= 0:
        raise ValueError("phase resource limit differs")
    lock = registration(args.registration, args.source, args.baseline)
    verify_registration_attestation(args.registration.parent / "registration_attestation.json",
                                    args.registration, args.registration_commit)
    population = _bound_population(args.population, sha256(args.registration))
    sys.path[:0] = [str(PROJECT / "experiments/tf_production_gap_audit_20260922"),
                    str(PROJECT / "experiments/tf_cstate_validation_20260922"),
                    str(PROJECT / "experiments/tf_cgr_mechanism_20260923_v2")]
    from audit_io import attach

    evidence = attach(args.source, args.baseline)
    import native_twofft as native
    import geometry_validation as kernel
    import tf_base
    import tf_cgr
    import tf_sham
    import generate_variants
    from receiver import context

    generate_variants.verify(args.source / "src/twofft.py")

    detectors = {"BASE": tf_base, "CGR": tf_cgr, "SHAM": tf_sham}
    base = {}
    handoff = None
    if args.phase == "interventions":
        base = _base_reference(args.base, evidence)
        verify_seal(args.prediction, "prediction_seal.json")
        handoff = verify_prediction_handoff(
            args.registration.parent / "prediction_handoff.json",
            args.registration.parent, args.prediction, args.base)
        prediction_rows = read_jsonl(args.prediction / "ledger.jsonl")
        if (len(prediction_rows) != FRAMES or
                [row["frame"] for row in prediction_rows] != list(range(FRAMES))):
            raise ValueError("prediction allocation differs")
    environment = evidence.bind_runtime_environment()
    setup = time.perf_counter()
    system, _, code, header = context()
    setup_seconds = time.perf_counter() - setup
    evidence.verify_runtime_binding()
    if (system.N_total != 1024 or system.l_max_cap != 102 or system.rho != .5 or
            header["code_g_sha256"] != lock["code_g_sha256"]):
        raise ValueError("frozen receiver context differs")
    population_system = json.loads((args.population / "manifest.json").read_text())["system"]
    if population_system != dict(n=int(system.N_total), rho=float(system.rho),
                                 c1=float(system.c1), c2=float(system.c2),
                                 l_max_cap=int(system.l_max_cap)):
        raise ValueError("population physical system differs")
    code_cache = (args.baseline / "upstream/spafdm_receiver_handoff/"
                  "afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz")
    if sha256(code_cache) != lock["code_cache_sha256"]:
        raise ValueError("code cache SHA differs")
    with np.load(code_cache, allow_pickle=False) as stored:
        H = np.asarray(stored["H"])
    args.out.mkdir(parents=True)
    for name in ("checkpoints", "raw", "decisions"):
        (args.out / name).mkdir()
    calls = _calls(args.phase, lock)
    write_json(args.out / "manifest.json", dict(
        schema=SCHEMA, phase=args.phase, expected_calls=len(calls),
        global_call_indices=[1, FRAMES] if args.phase == "base" else [FRAMES + 1, 3 * FRAMES],
        registration_sha256=sha256(args.registration),
        registration_commit=args.registration_commit,
        population_seal_sha256=sha256(args.population / "observed_seal.json"),
        base_seal_sha256=sha256(args.base / "observed_seal.json") if base else None,
        prediction_seal_sha256=sha256(args.prediction / "prediction_seal.json") if base else None,
        prediction_handoff_sha256=sha256(args.registration.parent / "prediction_handoff.json") if base else None,
        prediction_commit=None if handoff is None else handoff["prediction_commit"],
        code_g_sha256=lock["code_g_sha256"], runtime_environment=environment,
        setup_seconds=setup_seconds, argv=sys.argv[:], pid=os.getpid(),
        clock="input load through decision write; ledger append separately",
        trace_state_semantics=dict(x="post marginal", mu="post marginal", v="post marginal",
                                   h="post gain", xbar="current damping", hbar="current damping",
                                   s="current residual", alpha="current output precision")))
    ledger = args.out / "ledger.jsonl"
    ledger.touch(exist_ok=False)
    started = time.perf_counter()
    for position, (frame, arm) in enumerate(calls):
        if time.perf_counter() - started >= args.seconds or size(args.study_root) >= args.bytes_cap:
            raise RuntimeError("phase time/data cap reached before next call")
        call_index = position + 1 if args.phase == "base" else FRAMES + position + 1
        stem = frame_id(frame)
        origin = time.perf_counter()
        row = dict(status="inflight", call_index=call_index, frame=frame,
                   observation_id=stem, arm=arm, receiver_started=False, checkpoints=[])
        identity = dict(schema=SCHEMA, observation_id=stem, arm=arm, phase=args.phase)

        def sink(event, decoded, *, origin=origin, stem=stem, arm=arm,
                 identity=identity, row=row):
            round_number = int(event["round"])
            ready = time.perf_counter() - origin
            path = args.out / "checkpoints" / f"{stem}_{arm}_r{round_number}.npz"
            digest = evidence.save_artifact(
                path, dict(event=event, decoded=np.asarray(decoded).copy()),
                dict(identity, round=round_number))
            syndrome = int(np.count_nonzero((H @ np.asarray(decoded, np.int32)) % 2))
            row["checkpoints"].append(dict(
                round=round_number, path=str(path.relative_to(args.out)),
                artifact_sha256=digest, decision_ready_seconds=ready,
                artifact_ready_seconds=time.perf_counter() - origin,
                syndrome_weight=syndrome,
                event={key: value for key, value in event.items() if key != "snapshot"}))

        try:
            input_row = population[frame]
            input_path = args.population / input_row["observation_path"]
            if sha256(input_path) != input_row["observation_sha256"]:
                raise ValueError("observed input SHA differs")
            payload, metadata = evidence.load_artifact(input_path)
            obs = payload["observation"]
            if (metadata.get("observation_id") != stem or
                    payload["observation_id"] != stem or
                    payload["observation_hash"] != input_row["observation_hash"] or
                    observation_hash(obs) != input_row["observation_hash"]):
                raise ValueError("observed input identity differs")
            row["input_sha256"] = input_row["observation_sha256"]
            input_end = time.perf_counter()
            row["receiver_started"] = True
            native_dec, arrays, native_timing = native.receive(
                obs, system, code, rounds=2, iterations=20, ce_mode="soft",
                gain_mode="joint", checkpoint_sink=sink)
            native_end = time.perf_counter()
            if (len(row["checkpoints"]) != 2 or
                    not np.array_equal(native_dec["decoded"], arrays["r1_decoded"])):
                raise ValueError("native two-round checkpoint differs")
            triggered = row["checkpoints"][-1]["syndrome_weight"] != 0
            if base:
                base_row, base_raw = base[frame]
                if (base_row["input_sha256"] != row["input_sha256"] or
                        base_row["triggered"] != triggered or
                        hash_value(base_raw["native_arrays"]) != hash_value(arrays)):
                    raise ValueError("arm native prefix differs from sealed BASE")
            branch = None
            numeric_error = None
            branch_start = time.perf_counter()
            if triggered:
                try:
                    branch = final_branch(obs, system, code, native, kernel, arrays, detectors[arm])
                except (FloatingPointError, np.linalg.LinAlgError) as error:
                    numeric_error = repr(error)
            branch_end = time.perf_counter()
            if base:
                base_row, _ = base[frame]
                if base_row["entering_sha256"] != (None if branch is None else branch["entering_sha256"]):
                    raise ValueError("arm post-refit entering state differs from BASE")
            if branch is not None:
                dec = branch["decoder"]
                event = dict(round=2, ready=branch_end - origin,
                             ce=branch["result"].elapsed_seconds,
                             inference=branch["exclusive_stages"]["tf"],
                             decoder=branch["exclusive_stages"]["ldpc"],
                             ce_evaluations=branch["result"].evaluations,
                             inference_iterations=20, decoder_iterations=int(dec["iterations"]),
                             snapshot=dict(decoded=dec["decoded"], input_llr=dec["incoming_llr"],
                                           app=dec["raw_app"], check=dec["raw_check_extrinsic"],
                                           delays=branch["entering"]["delays"],
                                           dopplers=branch["entering"]["dopplers"],
                                           geometry_gains=branch["entering"]["gains"],
                                           inference_gains=branch["detector"]["gains"]))
                sink(event, dec["decoded"])
            final = native_dec if branch is None else branch["decoder"]
            bits = np.asarray(final["decoded"])
            if bits.shape != (2048,) or not np.isin(bits, (0, 1)).all():
                raise ValueError("invalid final decoded bits")
            final_syndrome = int(np.count_nonzero((H @ bits.astype(np.int32)) % 2))
            common_state = (base_common_state(branch["detector"]["states"], len(obs["y"]))
                            if arm == "BASE" and branch is not None else None)
            raw_payload = dict(
                observation_id=stem, arm=arm, input_sha256=row["input_sha256"],
                native_arrays=arrays, native_timing=native_timing, native_decoder=native_dec,
                triggered=triggered, numerical_failure=numeric_error,
                entering=None if branch is None else branch["entering"],
                gram=None if branch is None else branch["gram"],
                geometry_result=None if branch is None else asdict(branch["result"]),
                branch_detector=None if branch is None else branch["detector"],
                base_common_state=common_state, trace_origin="prospective registered full trace",
                branch_decoder=None if branch is None else branch["decoder"], final_decoded=bits)
            raw_path = args.out / "raw" / f"{stem}_{arm}.npz"
            raw_sha = evidence.save_artifact(raw_path, raw_payload, identity)
            raw_ready = time.perf_counter()
            decision_path = args.out / "decisions" / f"{stem}_{arm}.json"
            decision = dict(schema=SCHEMA, frame=frame, observation_id=stem, arm=arm,
                            input_sha256=row["input_sha256"], triggered=triggered,
                            numerical_failure=numeric_error,
                            baseline_syndrome_weight=row["checkpoints"][1]["syndrome_weight"],
                            final_syndrome_weight=final_syndrome,
                            final_decoded_sha256=hashlib.sha256(bits.tobytes()).hexdigest(),
                            final_decision_ready_seconds=row["checkpoints"][-1]["decision_ready_seconds"],
                            checkpoints=row["checkpoints"],
                            raw_path=str(raw_path.relative_to(args.out)), raw_sha256=raw_sha,
                            entering_sha256=None if branch is None else branch["entering_sha256"])
            write_json(decision_path, decision)
            complete_end = time.perf_counter()
            row.update(status="ok", triggered=triggered, numerical_failure=numeric_error,
                       baseline_syndrome_weight=decision["baseline_syndrome_weight"],
                       final_syndrome_weight=final_syndrome,
                       final_decoded_sha256=decision["final_decoded_sha256"],
                       final_decision_ready_seconds=decision["final_decision_ready_seconds"],
                       input_load_seconds=input_end - origin,
                       native_two_rounds_seconds=native_end - input_end,
                       branch_elapsed_seconds=branch_end - branch_start,
                       branch_decision_seconds=None if branch is None else branch["branch_decision_seconds"],
                       branch_complete_seconds=complete_end - branch_start if triggered else 0.,
                       branch_exclusive_stages=None if branch is None else branch["exclusive_stages"],
                       entering_sha256=decision["entering_sha256"],
                       raw_artifact_ready_seconds=raw_ready - origin,
                       complete_latency_seconds=complete_end - origin,
                       raw_path=decision["raw_path"], raw_sha256=raw_sha,
                       decision_path=str(decision_path.relative_to(args.out)),
                       decision_sha256=sha256(decision_path))
            append_jsonl(ledger, row)
        except BaseException as error:
            row.update(status="failed", exception=repr(error),
                       traceback=traceback.format_exc(),
                       elapsed_seconds=time.perf_counter() - origin)
            append_jsonl(ledger, row)
            write_json(args.out / "blocked.json", dict(call_index=call_index,
                       observation_id=stem, arm=arm, reason=repr(error)))
            raise
        if size(args.study_root) >= args.bytes_cap:
            write_json(args.out / "blocked.json", dict(after_call=call_index,
                       reason="8 GiB total cap reached"))
            raise RuntimeError("8 GiB total cap reached after completed call")
    seal(args.out, "observed_seal.json", dict(
        phase=args.phase, completed_calls=len(calls),
        registration_sha256=sha256(args.registration),
        population_seal_sha256=sha256(args.population / "observed_seal.json"),
        base_seal_sha256=sha256(args.base / "observed_seal.json") if base else None,
        prediction_seal_sha256=sha256(args.prediction / "prediction_seal.json") if base else None,
        elapsed_seconds=time.perf_counter() - started,
        numerical_failures=sum(bool(row["numerical_failure"]) for row in read_jsonl(ledger))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("base", "interventions"), required=True)
    for name in ("source", "baseline", "registration", "population", "study-root", "out"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--prediction", type=Path)
    parser.add_argument("--registration-commit", required=True)
    parser.add_argument("--seconds", type=int)
    parser.add_argument("--bytes-cap", type=int, default=DATA_CAP)
    arguments = parser.parse_args()
    if arguments.seconds is None:
        arguments.seconds = SECONDS["base" if arguments.phase == "base" else "interventions"]
    if arguments.phase == "interventions" and (arguments.base is None or arguments.prediction is None):
        parser.error("intervention phase requires --base and --prediction")
    run(arguments)
