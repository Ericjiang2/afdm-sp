"""Read-only export of the sealed prospective campaign for research discovery.

No receiver, generator, or geometry-search module is imported here. The existing
independent verifier supplies the pre-truth Git/source/seal gate.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
sys.path.insert(0, str(EXPERIMENTS / "tf_cstate_prospective_20260923"))
sys.path.insert(0, str(EXPERIMENTS / "tf_production_gap_audit_20260922"))
from audit_io import attach, load_bound, sha256  # noqa: E402
from verify_prospective import pretruth_gate  # noqa: E402
sys.path.insert(0, str(EXPERIMENTS / "tf_geometry_reopen_20260922"))
from analyze_reopening import add_geometry_proximity, truth_rank_rows  # noqa: E402

CELLS = (600, 650, 700)
FRAMES = 1024
EXPECTED = [f"s{snr}_f{frame:04d}" for snr in CELLS for frame in range(FRAMES)]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def safe_path(root: Path, relative: str) -> Path:
    name = Path(relative)
    require(not name.is_absolute() and name.parts and ".." not in name.parts,
            f"unsafe artifact path: {relative}")
    path = (root / name).resolve()
    require(path.is_relative_to(root.resolve()), f"artifact escapes source root: {relative}")
    return path


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    require(bool(rows), f"empty evidence table: {path.name}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def json_value(value: object) -> object:
    """Expose scalar trace fields; keep full numerical arrays in the trace NPZ."""
    if isinstance(value, np.ndarray):
        return json_value(value.tolist()) if value.size <= 64 else dict(
            saved_in_trace_artifact=True, shape=list(value.shape), dtype=str(value.dtype))
    if isinstance(value, np.generic):
        return json_value(value.item())
    if isinstance(value, complex):
        return dict(real=value.real, imag=value.imag)
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def artifact(evidence, root: Path, reference: dict, path_key: str, hash_key: str) -> dict:
    return load_bound(evidence, safe_path(root, reference[path_key]), reference[hash_key])


def list_number(value: object) -> list[float] | None:
    if value is None:
        return None
    array = np.asarray(value)
    return array.tolist() if array.ndim == 1 and np.issubdtype(array.dtype, np.number) else None


def observed_geometry(raw: dict) -> tuple[list | None, list | None]:
    arrays = raw["baseline_arrays"]
    for prefix in ("r1_", "round1_", ""):
        for delay_name, doppler_name in (("path_delays", "path_dopplers"),
                                         ("delays", "dopplers")):
            delays = list_number(arrays.get(prefix + delay_name))
            dopplers = list_number(arrays.get(prefix + doppler_name))
            if delays is not None and dopplers is not None and len(delays) == len(dopplers):
                return delays, dopplers
    return None, None


def numerical_summary(value: object, *, magnitude: bool = False) -> dict | None:
    if value is None:
        return None
    array = np.asarray(value)
    if not np.issubdtype(array.dtype, np.number) or not array.size:
        return None
    samples = np.abs(array) if magnitude else array
    require(np.isrealobj(samples) and np.isfinite(samples).all(),
            "nonfinite or complex summary input")
    return dict(count=int(samples.size), mean=float(np.mean(samples)),
                minimum=float(np.min(samples)), maximum=float(np.max(samples)),
                rms=float(np.sqrt(np.mean(np.square(samples)))))


def native_round_summaries(arrays: dict) -> list[dict]:
    """Report saved round endpoints; absent diagnostics remain explicit nulls."""
    rows = []
    for round_index in (0, 1):
        prefix = f"r{round_index}_"
        history = list_number(arrays.get(prefix + "ce_history"))
        trace = arrays.get(prefix + "inference_trace")
        rows.append(dict(round=round_index,
            input_llr=numerical_summary(arrays.get(prefix + "input_llr")),
            app_llr=numerical_summary(arrays.get(prefix + "app")),
            check_extrinsic_llr=numerical_summary(arrays.get(prefix + "check")),
            posterior_mean_magnitude=numerical_summary(arrays.get(prefix + "mu"), magnitude=True),
            posterior_variance=numerical_summary(arrays.get(prefix + "variance")),
            gain_magnitude=numerical_summary(arrays.get(prefix + "gains"), magnitude=True),
            gain_variance=numerical_summary(arrays.get(prefix + "gain_variance")),
            ce_objective_first=None if not history else history[0],
            ce_objective_last=None if not history else history[-1],
            inference_iterations=None if trace is None else len(trace),
            observed_residual=None))
    return rows


def cohort_of(label: dict) -> str:
    if label["rescue"] == "True":
        return "rescued"
    if label["remaining_triggered_failure"] == "True":
        return "remaining_failure"
    require(label["tf_correct"] == "True",
            f"unclassified TF failure: {label.get('observation_id')}")
    return "tf_success"


def nearest_control(anchor: dict, candidates: list[dict],
                    observed_by_id: dict[str, dict]) -> str:
    """Match within SNR using observed syndrome, TF time, then ID."""
    same = [row for row in candidates if row["snr_centi_db"] == anchor["snr_centi_db"]]
    require(bool(same), f"no same-SNR control for {anchor['observation_id']}")
    anchor_seconds = observed_by_id[anchor["observation_id"]]["tf_complete_seconds"]
    anchor_syndrome = observed_by_id[anchor["observation_id"]]["baseline_syndrome_weight"]
    return min(same, key=lambda row: (
        abs(observed_by_id[row["observation_id"]]["baseline_syndrome_weight"] -
            anchor_syndrome),
        abs(observed_by_id[row["observation_id"]]["tf_complete_seconds"] - anchor_seconds),
        row["observation_id"]))["observation_id"]


def gate(args) -> tuple[object, dict, dict, list, list, list]:
    """Finish observed gates and recovery checks before opening truth payloads."""
    roots = [args.population_observed, args.truth_root, args.observed,
             args.recovery, args.registration.parent]
    out = args.out.resolve()
    require(not out.exists(), "output already exists; sealed pack export is append-free")
    require(all(not out.is_relative_to(root.resolve()) and
                not root.resolve().is_relative_to(out) for root in roots),
            "output must be disjoint from all source roots")
    registration, receiver_manifest, _, observed_seal_hash = pretruth_gate(args)
    require(args.seal_commit == "929c679b4797de18271065b8e8bf35b67b6de13f",
            "unexpected prospective seal commit")
    receipt = read_json(args.recovery / "analysis" / "receipt.json")
    verification = read_json(args.recovery / "verification" / "receipt.json")
    status = read_json(args.recovery / "status.json")
    require(receipt.get("status") == "complete" and
            receipt.get("evidence_integrity") == "pass" and
            receipt.get("seal_commit") == args.seal_commit and
            receipt.get("observed_seal_sha256") == observed_seal_hash and
            verification.get("status") == "pass" and
            verification.get("seal_commit") == args.seal_commit and
            verification.get("observed_seal_sha256") == observed_seal_hash and
            verification.get("population_observations") == 3072 and
            verification.get("receiver_calls") == 6144 and
            verification.get("checkpoints_recounted") == 12554,
            "postfailure recovery/independent verification receipt differs")
    require(status.get("status") == "completed" and
            status.get("original_campaign_status") == "invalid" and
            status.get("original_observed_seal_commit") == args.seal_commit and
            status.get("analysis_summary_sha256") == receipt["files"]["summary.json"] and
            status.get("verification_receipt_sha256") ==
                sha256(args.recovery / "verification" / "receipt.json"),
            "postfailure recovery status is incomplete")
    outcomes_path = args.recovery / "analysis" / "frame_outcomes.csv"
    require(sha256(outcomes_path) == receipt["files"]["frame_outcomes.csv"],
            "recovered frame outcome table hash differs")
    population = read_jsonl(args.population_observed / "ledger.jsonl")
    receiver = read_jsonl(args.observed / "ledger.jsonl")
    outcomes = read_csv(outcomes_path)
    require([r["observation_id"] for r in population] == EXPECTED and
            [r["observation_id"] for r in outcomes] == EXPECTED,
            "fresh frame allocation/order differs")
    require(len(receiver) == 6144, "paired receiver count differs")
    for index, stem in enumerate(EXPECTED):
        pair = receiver[2 * index:2 * index + 2]
        require({r["arm"] for r in pair} == {"TF", "TF_CSTATE"} and
                all(r["observation_id"] == stem and r["status"] == "ok" for r in pair),
                f"paired receiver identity differs: {stem}")
    require(sum(r["trigger"] == "True" for r in outcomes) == 266 and
            sum(r["remaining_triggered_failure"] == "True" for r in outcomes) == 72,
            "registered trigger/failure counts differ")
    evidence = attach(args.source, args.baseline)
    require(evidence.source_hashes(args.source) == registration["native_source_hashes"] and
            evidence.source_hashes(args.baseline) == registration["baseline_source_hashes"] and
            receiver_manifest["source_hashes"] == registration["registration_source_hashes"],
            "frozen producer source hashes differ")
    return evidence, registration, receipt, population, receiver, outcomes


def export(args) -> dict:
    evidence, registration, receipt, population, receiver, outcomes = gate(args)
    # First truth-root inventory access follows the complete observed gate.
    truth_seal = read_json(args.truth_root / "truth_seal.json")
    actual_truth = {str(p.relative_to(args.truth_root)): sha256(p)
                    for p in args.truth_root.rglob("*")
                    if p.is_file() and p.name != "truth_seal.json"}
    require(truth_seal.get("status") == "pass" and
            truth_seal.get("observations") == 3072 and
            truth_seal.get("files") == actual_truth and
            sha256(args.truth_root / "truth_seal.json") == receipt["truth_seal_sha256"],
            "committed truth inventory differs")
    truth = read_jsonl(args.truth_root / "ledger.jsonl")
    require([r["observation_id"] for r in truth] == EXPECTED,
            "truth allocation/order differs")
    args.out.mkdir(parents=True)
    for folder in ("observations", "tf_traces", "cstate_landscape",
                   "truth_payloads", "remaining_failure_dossiers"):
        (args.out / folder).mkdir()
    observed_rows, outcome_rows, trace_rows, iteration_rows = [], [], [], []
    landscape_rows, truth_rows, truth_rank_annotations, dossiers, cohort_rows = [], [], [], [], []
    tf_trace_cohorts = {"tf_success": 0, "rescued": 0, "remaining_failure": 0}
    for index, stem in enumerate(EXPECTED):
        pop, label, sealed_truth = population[index], outcomes[index], truth[index]
        arms = {r["arm"]: r for r in receiver[2 * index:2 * index + 2]}
        tf, combined = arms["TF"], arms["TF_CSTATE"]
        require(pop["observation_hash"] == tf["observation_hash"] ==
                combined["observation_hash"] == sealed_truth["observation_hash"] and
                pop["stream_ids"] == tf["stream_ids"] == combined["stream_ids"] ==
                sealed_truth["stream_ids"], f"observation/truth identity differs: {stem}")
        require(tf["triggered"] is False and
                combined["triggered"] == (label["trigger"] == "True") and
                tf["baseline_syndrome_weight"] == combined["baseline_syndrome_weight"] ==
                int(label["baseline_syndrome_weight"]),
                f"observed trigger differs: {stem}")
        observation_source = safe_path(args.population_observed, pop["observation_path"])
        observation_copy = args.out / "observations" / f"{stem}.npz"
        shutil.copyfile(observation_source, observation_copy)
        require(sha256(observation_copy) == pop["observation_sha256"],
                f"observation copy differs: {stem}")
        raw_tf = artifact(evidence, args.observed, tf, "raw_path", "raw_sha256")
        raw_combined = artifact(evidence, args.observed, combined, "raw_path", "raw_sha256")
        require(raw_tf["observation_id"] == raw_combined["observation_id"] == stem and
                raw_tf["geometry_result"] is None and
                (raw_combined["geometry_result"] is not None) == combined["triggered"],
                f"raw arm identity/branch differs: {stem}")
        delays, dopplers = observed_geometry(raw_tf)
        observed_rows.append(dict(observation_id=stem, snr_centi_db=pop["snr_centi_db"],
            frame=pop["frame"], observation_hash=pop["observation_hash"],
            input_sha256=pop["observation_sha256"], stream_ids=pop["stream_ids"],
            observation_path=str(observation_copy.relative_to(args.out)),
            trigger=combined["triggered"], baseline_syndrome_weight=combined["baseline_syndrome_weight"],
            tf_final_syndrome_weight=tf["final_syndrome_weight"],
            combined_final_syndrome_weight=combined["final_syndrome_weight"],
            tf_complete_seconds=tf["complete_latency_seconds"],
            combined_complete_seconds=combined["complete_latency_seconds"],
            tf_checkpoints=tf["checkpoints"], combined_checkpoints=combined["checkpoints"],
            combined_stages=combined["branch_exclusive_stages"],
            working_delays=delays, working_dopplers=dopplers,
            native_round_summaries=native_round_summaries(raw_tf["baseline_arrays"]),
            cstate_objective_before=None if not combined["triggered"] else
                raw_combined["geometry_result"]["objective_before"],
            cstate_objective_after=None if not combined["triggered"] else
                raw_combined["geometry_result"]["objective_after"],
            cstate_accepted_moves=None if not combined["triggered"] else
                [step["accepted"] for step in raw_combined["geometry_result"]["global_trace"]],
            tf_raw_source_sha256=tf["raw_sha256"], combined_raw_source_sha256=combined["raw_sha256"]))
        outcome_rows.append(dict(label, evidence_scope="post_seal_recovery_outcome"))
        cohort = cohort_of(label)
        tf_trace_cohorts[cohort] += 1
        cohort_rows.append(dict(observation_id=stem, post_seal_cohort=cohort))
        cp_payloads = [artifact(evidence, args.observed, cp, "path", "artifact_sha256")
                       for cp in tf["checkpoints"]]
        trace_payload = dict(baseline_arrays=raw_tf["baseline_arrays"],
            native_decoder=raw_tf["native_decoder"], native_timing=raw_tf["native_timing"],
            checkpoints=cp_payloads)
        trace_path = args.out / "tf_traces" / f"{stem}.npz"
        trace_sha = evidence.save_artifact(trace_path, trace_payload,
            dict(kind="observed_tf_trace", observation_id=stem,
                 source_raw_sha256=tf["raw_sha256"]))
        trace_rows.append(dict(observation_id=stem,
            trace_path=str(trace_path.relative_to(args.out)), trace_sha256=trace_sha,
            checkpoint_count=len(cp_payloads), checkpoint_ready_seconds=[
                cp["decision_ready_seconds"] for cp in tf["checkpoints"]],
            decoder_syndrome_trajectory=[cp["syndrome_weight"] for cp in tf["checkpoints"]],
            native_array_keys=sorted(raw_tf["baseline_arrays"]),
            native_decoder_keys=sorted(raw_tf["native_decoder"]),
            source_raw_sha256=tf["raw_sha256"]))
        for round_index in (0, 1):
            key = f"r{round_index}_inference_trace"
            for entry in raw_tf["baseline_arrays"].get(key, []):
                iteration_rows.append(dict(observation_id=stem, round=round_index,
                    trace_kind="detector_iteration", saved_state=json_value(entry)))
        for entry in raw_tf["native_decoder"].get("decoder_records", []):
            iteration_rows.append(dict(observation_id=stem,
                trace_kind="decoder_record", saved_state=json_value(entry)))
        if combined["triggered"]:
            geometry = raw_combined["geometry_result"]
            traces = geometry["global_trace"]
            require(len(traces) in (1, 2) and all(
                np.asarray(step["scores"]).shape ==
                    (len(step["entering_paths"]), 2575) == np.asarray(step["valid"]).shape and
                np.asarray(step["scores"]).size == step["slot_tests"] and
                len(step["candidate_delays"]) == len(step["candidate_dopplers"]) == 2575 and
                len(step["top_k"]) == 20 and
                np.asarray(step["valid"]).dtype == np.bool_ and
                np.isfinite(np.asarray(step["scores"])[np.asarray(step["valid"])]).all()
                for step in traces), f"incomplete CSTATE grid: {stem}")
            landscape_path = args.out / "cstate_landscape" / f"{stem}.npz"
            landscape_payload = dict(geometry_result=geometry,
                branch_inputs=raw_combined["branch_inputs"],
                branch_detector=raw_combined["branch_detector"],
                branch_decoder=raw_combined["branch_decoder"])
            landscape_sha = evidence.save_artifact(landscape_path, landscape_payload,
                dict(kind="observed_cstate_landscape", observation_id=stem,
                     source_raw_sha256=combined["raw_sha256"]))
            landscape_rows.append(dict(observation_id=stem,
                landscape_path=str(landscape_path.relative_to(args.out)),
                landscape_sha256=landscape_sha, step_count=len(traces),
                grid_shapes=[list(np.asarray(step["scores"]).shape) for step in traces],
                valid_tests=[int(np.count_nonzero(step["valid"])) for step in traces],
                entering_paths=[step["entering_paths"] for step in traces],
                selected=[step["selected"] for step in traces],
                accepted=[step["accepted"] for step in traces],
                top_k=[step["top_k"] for step in traces],
                objective_before=geometry["objective_before"],
                objective_after=geometry["objective_after"],
                final_paths=geometry["paths"], evaluations=geometry["evaluations"],
                local_trial_count=sum(item["trial_count"] for item in geometry["local_trace"]),
                final_syndrome_weight=combined["final_syndrome_weight"],
                source_raw_sha256=combined["raw_sha256"]))
        truth_payload = artifact(evidence, args.truth_root, sealed_truth,
                                 "truth_path", "truth_sha256")
        require(truth_payload["observation_hash"] == pop["observation_hash"] and
                truth_payload["stream_ids"] == pop["stream_ids"],
                f"truth payload identity differs: {stem}")
        truth_copy = args.out / "truth_payloads" / f"{stem}.npz"
        shutil.copyfile(safe_path(args.truth_root, sealed_truth["truth_path"]), truth_copy)
        require(sha256(truth_copy) == sealed_truth["truth_sha256"],
                f"truth copy differs: {stem}")
        true_delays = np.asarray(truth_payload["l_i"]).astype(int)
        true_dopplers = np.asarray(truth_payload["k_real"], float)
        gains = np.asarray(truth_payload["g_i"])
        require(true_delays.ndim == true_dopplers.ndim == gains.ndim == 1 and
                len(true_delays) == len(true_dopplers) == len(gains),
                f"physical truth shape differs: {stem}")
        if combined["triggered"]:
            for step in raw_combined["geometry_result"]["global_trace"]:
                ranks = truth_rank_rows(step["scores"], step["valid"],
                    step["candidate_delays"], step["candidate_dopplers"],
                    true_delays, true_dopplers, gains,
                    observation_id=stem, global_step=step["step"])
                truth_rank_annotations.extend(add_geometry_proximity(
                    ranks, step["entering_paths"], step["accepted"], grid_step=.25))
        outgoing = raw_combined["geometry_result"]["paths"] if combined["triggered"] else None
        working_set = None if delays is None else set(int(x) for x in delays)
        missing = None if working_set is None else [int(i) for i, d in
            enumerate(true_delays) if int(d) not in working_set]
        power = np.abs(gains) ** 2
        truth_rows.append(dict(observation_id=stem, snr_centi_db=pop["snr_centi_db"],
            diagnostic_non_deployable=True, true_path_count=len(true_delays),
            true_delays=true_delays.tolist(), true_dopplers=true_dopplers.tolist(),
            true_gain_real=gains.real.tolist(), true_gain_imag=gains.imag.tolist(),
            repeated_delay=len(set(true_delays.tolist())) < len(true_delays),
            min_same_delay_doppler_separation=min(
                (abs(true_dopplers[i] - true_dopplers[j]) for i in range(len(true_delays))
                 for j in range(i + 1, len(true_delays)) if true_delays[i] == true_delays[j]),
                default=None),
            working_distinct_delay_coverage=None if working_set is None else
                len(set(true_delays.tolist()) & working_set),
            missing_distinct_delays=None if working_set is None else
                sorted(set(true_delays.tolist()) - working_set),
            missing_path_indices=missing,
            missing_gain_power_fraction=None if missing is None or power.sum() == 0 else
                float(power[missing].sum() / power.sum()),
            accepted_final_paths=outgoing,
            truth_payload_path=str(truth_copy.relative_to(args.out)),
            source_truth_sha256=sealed_truth["truth_sha256"]))
        if index % 256 == 255:
            print(f"exported {index + 1}/3072 frames", flush=True)
    require(len(observed_rows) == len(outcome_rows) == len(trace_rows) == len(truth_rows) == 3072 and
            len(landscape_rows) == 266 and tf_trace_cohorts["remaining_failure"] == 72,
            "exported allocation differs")
    write_jsonl(args.out / "frame_table.jsonl", observed_rows)
    write_csv(args.out / "frame_outcomes.csv", outcome_rows)
    write_jsonl(args.out / "tf_traces.jsonl", trace_rows)
    write_jsonl(args.out / "tf_iteration_traces.jsonl", iteration_rows)
    write_csv(args.out / "tf_trace_cohorts.csv", cohort_rows)
    write_jsonl(args.out / "cstate_landscape.jsonl", landscape_rows)
    write_jsonl(args.out / "truth_annotations.jsonl", truth_rows)
    write_jsonl(args.out / "truth_candidate_ranks.jsonl", truth_rank_annotations)
    by_id = {row["observation_id"]: row for row in observed_rows}
    outcome_by_id = {row["observation_id"]: row for row in outcome_rows}
    rescued = [row for row in outcome_rows if row["rescue"] == "True"]
    easy = [row for row in outcome_rows if row["tf_correct"] == "True" and
            row["trigger"] == "False"]
    for failure in (row for row in outcome_rows if row["remaining_triggered_failure"] == "True"):
        stem = failure["observation_id"]
        rescued_id = nearest_control(failure, rescued, by_id)
        easy_id = nearest_control(failure, easy, by_id)
        def case(identifier):
            observed = by_id[identifier]
            outcome = outcome_by_id[identifier]
            return dict(observation_id=identifier,
                snr_centi_db=observed["snr_centi_db"],
                baseline_syndrome_weight=observed["baseline_syndrome_weight"],
                tf_complete_seconds=observed["tf_complete_seconds"],
                combined_complete_seconds=observed["combined_complete_seconds"],
                working_delays=observed["working_delays"],
                working_dopplers=observed["working_dopplers"],
                post_seal_cohort=cohort_of(outcome),
                post_seal_tf_info_errors=outcome["tf_info_errors"],
                post_seal_combined_info_errors=outcome["combined_info_errors"],
                tf_trace_path=f"tf_traces/{identifier}.npz",
                cstate_path=f"cstate_landscape/{identifier}.npz" if
                    observed["trigger"] else None,
                observation_path=observed["observation_path"])
        dossier = dict(observation_id=stem, outcome="remaining_failure",
            rescued_control_id=rescued_id, easy_control_id=easy_id,
            matching_rule="same SNR, nearest observed baseline syndrome weight, "
                          "then TF complete seconds, ID tie break",
            cases=dict(failure=case(stem), rescued_control=case(rescued_id),
                       easy_control=case(easy_id)),
            observed_row_source="frame_table.jsonl", outcome_source="frame_outcomes.csv",
            tf_trace_source=f"tf_traces/{stem}.npz",
            cstate_source=f"cstate_landscape/{stem}.npz",
            truth_source="truth_annotations.jsonl")
        write_json(args.out / "remaining_failure_dossiers" / f"{stem}.json", dossier)
        dossiers.append(dossier)
    require(len(dossiers) == 72, "remaining-failure dossier count differs")
    write_json(args.out / "cohort_summary.json", dict(
        tf_trace_counts=tf_trace_cohorts, cstate_triggered=len(landscape_rows),
        remaining_failure_dossiers=len(dossiers),
        snr_counts={str(snr): sum(row["snr_centi_db"] == snr for row in observed_rows)
                    for snr in CELLS}))
    provenance = dict(schema="tf-research-discovery-pack/1", status="complete",
        campaign="fresh prospective TF versus frozen TF+CSTATE; no earlier cohorts pooled",
        original_analysis_status="invalid; authorized postfailure offline recovery",
        recovery_receipt_sha256=sha256(args.recovery / "analysis" / "receipt.json"),
        independent_verification_sha256=sha256(args.recovery / "verification" / "receipt.json"),
        registration_sha256=sha256(args.registration),
        seal_commit=args.seal_commit,
        population_observed_seal_sha256=sha256(args.population_observed / "observed_seal.json"),
        receiver_observed_seal_sha256=sha256(args.observed / "observed_seal.json"),
        truth_seal_sha256=sha256(args.truth_root / "truth_seal.json"),
        source_hashes=registration["registration_source_hashes"],
        native_source_hashes=registration["native_source_hashes"],
        baseline_source_hashes=registration["baseline_source_hashes"],
        source_roots={"population_observed": str(args.population_observed),
                      "receiver_observed": str(args.observed),
                      "truth": str(args.truth_root), "recovery": str(args.recovery)})
    write_json(args.out / "source_evidence_manifest.json", provenance)
    shutil.copy2(HERE / "read_artifact.py", args.out / "read_artifact.py")
    shutil.copy2(HERE / "export_pack.py", args.out / "export_pack.py")
    files = {str(path.relative_to(args.out)): sha256(path) for path in args.out.rglob("*")
             if path.is_file() and path.name not in ("MANIFEST.sha256", "artifact_hashes.json")}
    write_json(args.out / "artifact_hashes.json", files)
    files["artifact_hashes.json"] = sha256(args.out / "artifact_hashes.json")
    (args.out / "MANIFEST.sha256").write_text("".join(
        f"{digest}  {name}\n" for name, digest in sorted(files.items())))
    return dict(observations=3072, triggers=266, remaining_failures=72,
                tf_trace_cohorts=tf_trace_cohorts, output=str(args.out),
                manifest_sha256=sha256(args.out / "MANIFEST.sha256"))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("registration", "population-observed", "truth-root", "observed",
                 "recovery", "evidence-git", "source", "baseline", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--registration-commit", required=True)
    p.add_argument("--seal-commit", required=True)
    return p


if __name__ == "__main__":
    print(json.dumps(export(parser().parse_args()), indent=2))
