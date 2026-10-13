"""Offline, truth-bearing recount of a validated frozen development run.

Never calls a receiver. All population interpretation is left to the registered
protocol; a one-frame screen remains descriptive and cannot produce a lock.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np


def bits(value, count, label):
    value = np.asarray(value)
    if value.shape != (count,) or not np.isin(value, [0, 1]).all():
        raise ValueError(f"invalid {label} bit vector")
    return value


def errors(estimate, truth):
    return int(np.count_nonzero(bits(estimate, len(truth), "estimate") != truth))


def normalized_error(estimate, truth):
    denominator = float(np.vdot(truth, truth).real)
    if denominator <= 0 or estimate.shape != truth.shape or not np.isfinite(estimate).all():
        raise ValueError("invalid full-channel NMSE inputs")
    return float(np.vdot(estimate - truth, estimate - truth).real / denominator)


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)


def final_arrays(payload):
    arrays = payload["result"]
    rounds = sorted({int(key.split("_")[0][5:]) for key in arrays if key.startswith("round")})
    if rounds:
        prefix = f"round{rounds[-1]}_"
        return {key[len(prefix):]: value for key, value in arrays.items() if key.startswith(prefix)}
    return arrays


def plot_report(out, rows, deadlines):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
    families = list(dict.fromkeys(row["family"] for row in rows))
    colors = plt.get_cmap("tab20")
    for index, family in enumerate(families):
        valid = [row for row in rows if row["family"] == family and row.get("info_ber") is not None]
        axes[0].scatter([row["seconds"] for row in valid], [row["info_ber"] for row in valid],
                        label=family, s=28, color=colors(index), alpha=.8)
        valid_h = [row for row in valid if row.get("channel_nmse") is not None]
        axes[1].scatter([row["seconds"] for row in valid_h], [row["channel_nmse"] for row in valid_h],
                        s=28, color=colors(index), alpha=.8)
    for axis in axes:
        axis.set_xlabel("Complete receiver time (s)")
        axis.set_xscale("log")
        axis.grid(alpha=.2)
    axes[0].set_ylabel("Information BER on saved observation")
    axes[1].set_ylabel("Full-channel NMSE (linear)")
    axes[1].set_yscale("log")
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle("Development evidence: individual configuration / observation points")
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(out / f"cost_error.{suffix}", dpi=170)
    plt.close(fig)
    if len({(row['cell'], row['frame']) for row in rows}) == 1:
        labels = [row["arm"] for row in rows]
        matrix = np.array([[entry["deadline_frame_error"] for entry in deadlines
                            if entry["arm"] == arm] for arm in labels])
        fig, axis = plt.subplots(figsize=(6.3, max(4, .22 * len(labels))), constrained_layout=True)
        axis.imshow(matrix, cmap="RdYlBu_r", vmin=0, vmax=1, aspect="auto")
        axis.set_yticks(range(len(labels)), labels, fontsize=7)
        axis.set_xticks(range(4), ["1.0", "1.25", "1.5", "2.0"])
        axis.set_xlabel("Deadline / measured I1 reference time")
        axis.set_title("Single-observation deadline error: blue=0, red=1\nMissing timely decision counts as error")
        for suffix in ("png", "svg", "pdf"):
            fig.savefig(out / f"deadline_observation.{suffix}", dpi=170)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.source / "src"))
    sys.path.insert(0, str(args.source / "upstream" / "spafdm_receiver_handoff"))
    from evidence import artifact_sha256, load_artifact, source_hashes, validate_run, write_json_atomic
    from afdm_sp_joint_unrolled.e1_ldpc import build_code, extract_info
    from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix
    from afdm_sp_joint_unrolled.representation_ledger import match_physical_slots
    from afdm_sp_joint_unrolled.v3_statistics import residual_decomposition

    checked = validate_run(args.run, require_complete=True)
    manifest = checked["manifest"]
    if manifest["phase"] != "development" or manifest["source_hashes"] != source_hashes(args.source):
        raise ValueError("development phase or source identity mismatch")
    if args.out.exists():
        raise FileExistsError("preserve prior derived output; choose a fresh destination")
    system = manifest["header"]["system"]
    n = int(system["n_total"])
    c1, c2 = system["c1"], system["c2"]
    prefix = int(system["l_max_cap"])
    records = checked["records"]
    reference = [record["seconds"] for record in records if record["arm"] == "I1_BP12_r0"]
    if not reference:
        raise ValueError("I1_BP12_r0 reference missing")
    t_ref = float(np.median(reference))
    cells = {cell["id"]: cell for cell in manifest["cells"]}
    codes = {ident: build_code(2048, d_v=3, d_c=6, seed=cell.get("code_seed", 20260726))
             for ident, cell in cells.items()}
    import hashlib
    for ident, code in codes.items():
        metadata = json.loads((args.run / f"cell_{ident:02d}_metadata.json").read_text())
        if (metadata["generator_sha256"] != hashlib.sha256(np.asarray(code["G"]).tobytes()).hexdigest()
                or (code["n"], code["k"]) != (metadata["code_n"], metadata["code_k"])):
            raise ValueError("LDPC code identity differs")
    cache_key = None
    rows, timelines, deadlines, diagnostics, round_rows = [], [], [], [], []
    for record in records:
        cell, frame, arm = record["cell"], record["frame"], record["arm"]
        key = (cell, frame)
        stem = f"c{cell:02d}_f{frame:05d}"
        code = codes[cell]
        if key != cache_key:
            observed, _ = load_artifact(args.run / "arrays" / f"{stem}_input.npz")
            truth, _ = load_artifact(args.run / "truth" / f"{stem}.npz")
            coded = bits(truth["coded"], code["n"], "truth coded")
            info = bits(truth["info"], code["k"], "truth information")
            if not np.array_equal(extract_info(code, coded), info):
                raise ValueError("truth systematic mapping differs")
            h_true = physical_channel_matrix(n, c1, c2, truth["l_i"], truth["k_real"], truth["g_i"], prefix_length=prefix)
            cache_key = key
        configuration = manifest["configurations"][arm]
        row = {"cell": cell, "frame": frame, "snr_db": cells[cell]["snr_db"], "arm": arm,
               "family": configuration["family"], "status": record["status"],
               "seconds": record["seconds"], "info_bits": code["k"], "coded_bits": code["n"],
               "info_errors": None, "code_errors": None, "info_ber": None, "decoded_code_ber": None,
               "frame_error": 1, "channel_nmse": None,
               "numerical_fallback": record.get("failed_round_seconds", 0) > 0 and record["status"] == "ok"}
        for field in ("front_seconds", "refit_seconds", "detector_seconds", "decoder_seconds",
                      "instrumentation_seconds", "failed_round_seconds"):
            row[field] = record[field]
        payload, _ = load_artifact(args.run / "arrays" / f"{stem}_{arm}.npz")
        events = []
        if record["status"] == "ok":
            decoded = bits(payload["decoded"], code["n"], "decoded")
            info_hat = extract_info(code, decoded)
            if not np.array_equal(info_hat, payload["info_hat"]):
                raise ValueError("saved info_hat differs from systematic decoded bits")
            info_errors, code_errors = errors(info_hat, info), errors(decoded, coded)
            if info_errors != record["info_errors"]:
                raise ValueError("ledger information errors differ from raw bits")
            row.update(info_errors=info_errors, code_errors=code_errors,
                       info_ber=info_errors / code["k"], decoded_code_ber=code_errors / code["n"],
                       frame_error=int(info_errors > 0))
            for index, event in enumerate(payload["decision_timeline"]):
                count = errors(extract_info(code, bits(event["decoded"], code["n"], "checkpoint")), info)
                ledger_event = record["timeline"][index]
                if count != ledger_event["info_errors"] or event["elapsed"] != ledger_event["elapsed"]:
                    raise ValueError("checkpoint recount/time differs from ledger")
                events.append({"elapsed": event["elapsed"], "info_errors": count})
                timelines.append({"cell": cell, "frame": frame, "arm": arm, "checkpoint": index, **events[-1]})
            row["decoder_calls_front"] = sum(item.get("stage") == "decoder" for item in payload["front"].get("decoder_records", []))
            row["decoder_calls_terminal_and_rounds"] = len(payload["result_contract"]["decoder_records"])
            row["completed_checkpoints"] = len(events)
            arrays = final_arrays(payload)
            if "final_input" in arrays:
                row["decoder_input_ber"] = errors(np.asarray(arrays["final_input"]) < 0, coded) / code["n"]
                if not np.allclose(arrays["final_app"], arrays["final_input"] + arrays["final_check"], atol=2e-6):
                    raise ValueError("decoder APP/input/check identity failed")
            if "final_detector_mu" in arrays:
                mu = np.asarray(arrays["final_detector_mu"])
                row["posterior_mean_slicer_ber"] = errors(np.r_[mu.real < 0, mu.imag < 0], coded) / code["n"]
            if "final_detector_hard" in arrays:
                hard = np.asarray(arrays["final_detector_hard"])
                row["saved_raw_detector_ber"] = errors(np.r_[hard.real < 0, hard.imag < 0], coded) / code["n"]
            h_front = None
            if "front_H_coo" in payload:
                coo = payload["front_H_coo"]
                h_front = np.zeros(tuple(coo["shape"]), dtype=coo["data"].dtype)
                h_front[coo["rows"], coo["columns"]] = coo["data"]
                if "front_H_canary" in payload and not np.array_equal(h_front, payload["front_H_canary"]):
                    raise ValueError("COO matrix differs from actual I1 dense canary")
                row["front_channel_nmse"] = normalized_error(h_front, h_true)
            if "path_delays" in arrays:
                h_est = physical_channel_matrix(n, c1, c2, arrays["path_delays"], arrays["path_dopplers"], arrays["path_gains"], prefix_length=prefix)
                row["channel_scope"] = "last completed terminal physical path model"
                support = match_physical_slots(np.c_[truth["l_i"], truth["k_real"]], np.c_[arrays["path_delays"], arrays["path_dopplers"]])
            else:
                h_est = h_front
                support = None
                row["channel_scope"] = "actual I1 front H" if arrays else "actual I1 front H; terminal fallback"
            if h_est is not None:
                row["channel_nmse"] = normalized_error(h_est, h_true)
                mean = arrays.get("ce_mu", payload["front"].get("mu"))
                residual = residual_decomposition(observed["y"], h_true, h_est, observed["pilot"], truth["data"] / truth["unit_scale"], mean)
                if residual["relative_vector_closure"] > 1e-10:
                    raise ValueError("offline residual decomposition failed")
                diagnostics.append({"cell": cell, "frame": frame, "arm": arm, "support": support, "residual": residual,
                                    "mean_scope": "CE working mean, not terminal data estimate"})
            for timing in record["round_timings"]:
                round_rows.append({"cell": cell, "frame": frame, "arm": arm, **timing})
        for multiplier in (1., 1.25, 1.5, 2.):
            deadline = multiplier * t_ref
            eligible = [event for event in events if event["elapsed"] <= deadline]
            deadlines.append({"cell": cell, "frame": frame, "arm": arm, "multiplier": multiplier,
                              "deadline_seconds": deadline, "missing_decision": not eligible,
                              "deadline_frame_error": int(not eligible or eligible[-1]["info_errors"] > 0)})
        rows.append(row)
    baseline = {(row["cell"], row["frame"]): row for row in rows if row["arm"] == "I1_BP12_r0"}
    pairs, latency = [], []
    for arm in manifest["configurations"]:
        arm_rows = [row for row in rows if row["arm"] == arm]
        paired = [(row, baseline[row["cell"], row["frame"]]) for row in arm_rows]
        pairs.append({"arm": arm, "baseline": "I1_BP12_r0", "paired_observations": len(paired),
                      "unrestricted_rescues": sum(row["frame_error"] == 0 and base["frame_error"] == 1 for row, base in paired),
                      "unrestricted_harms": sum(row["frame_error"] == 1 and base["frame_error"] == 0 for row, base in paired)})
        times = np.array([row["seconds"] for row in arm_rows])
        latency.append({"arm": arm, "attempts": len(times), "mean_seconds": float(times.mean()),
                        "median_seconds": float(np.median(times)),
                        "sample_p90_seconds": float(np.quantile(times, .9)),
                        "sample_p99_seconds": float(np.quantile(times, .99)),
                        "numerical_failures": sum(row["status"] != "ok" for row in arm_rows),
                        "scope": "all attempts; empirical quantiles only, not tail-latency estimates"})
    args.out.mkdir(parents=True)
    write_csv(args.out / "paired_vs_I1.csv", pairs)
    write_csv(args.out / "latency_all_attempts.csv", latency)
    write_csv(args.out / "frame_metrics.csv", rows)
    write_csv(args.out / "checkpoint_recount.csv", timelines)
    write_csv(args.out / "deadline_errors.csv", deadlines)
    write_csv(args.out / "native_round_times.csv", round_rows)
    write_json_atomic(args.out / "offline_diagnostics.json", diagnostics)
    inventory = [{"path": str(path.relative_to(args.run)), "bytes": path.stat().st_size, "sha256": artifact_sha256(path)}
                 for path in sorted(args.run.rglob("*")) if path.is_file()]
    write_json_atomic(args.out / "raw_inventory.json", inventory)
    plot_report(args.out, rows, deadlines)
    observations = len({(row["cell"], row["frame"]) for row in rows})
    summary = {"_argv": sys.argv, "_config": {key: str(value) for key, value in vars(args).items()},
               "run_identity_sha256": checked["run_identity_sha256"], "analysis_sha256": artifact_sha256(__file__),
               "records": len(rows), "distinct_observations": observations,
               "numerical_failures": sum(row["status"] != "ok" for row in rows),
               "numerical_fallbacks": sum(row["numerical_fallback"] for row in rows),
               "t_ref_seconds": t_ref, "summed_complete_seconds_all_attempts": sum(row["seconds"] for row in rows),
               "raw_bytes": sum(item["bytes"] for item in inventory),
               "source_hashes": manifest["source_hashes"],
               "notice": "Descriptive development recount; configurations sharing an observation are paired, not independent trials. No confirmation lock or population/tail-latency claim. BER with no returned bits is missing, not an invented error vector. Failed attempts remain in cost and deadline errors. Decoder-input BER, posterior-mean slicer BER and saved raw-detector BER are distinct."}
    if observations == 1 and len(manifest["configurations"]) == 59:
        summary["one_observation_full_development_extrapolation"] = {
            "registered_receiver_calls": 9440,
            "receiver_hours": 160 * summary["summed_complete_seconds_all_attempts"] / 3600,
            "conservative_raw_GiB": 160 * summary["raw_bytes"] / 2**30,
            "limitations": "One observation only; cell/channel-dependent compute, warmups, setup, serialization, and audit work require separate allowance. Repeated dense canaries make this storage estimate conservative."}
    write_json_atomic(args.out / "summary.json", summary)
    print(json.dumps({key: value for key, value in summary.items() if key != "source_hashes"}, indent=2))


if __name__ == "__main__":
    main()
