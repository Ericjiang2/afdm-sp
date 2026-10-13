#!/usr/bin/env python3
"""Recount E1 D saved mechanism evidence and extend the frame-zero vector audit.

Offline only: no receiver, decoder, scalar_joint, or radio-frame generator call.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


SCHEMA = "spafdm-pd1q-saved-mechanism-extension/1"
OLD_SCHEMA = "spafdm-native-direction-compact/1"
ARMS = ("TF_J20_R2", "TF_POINT20_R2")
SNRS = (600, 650, 700)
N, FRAMES, ROUNDS, STEPS = 1024, 8, 2, 20
DAMPING = .3


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--e1-run", type=Path, required=True,
                        help="saved E1 direction stage_D directory")
    parser.add_argument("--prior-tables", type=Path, required=True,
                        help="existing mechanism/extracted directory with receipt and CSVs")
    parser.add_argument("--out", type=Path, required=True,
                        help="new empty mechanism_extension directory")
    return parser.parse_args()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_close(actual, expected, label, *, atol=1e-8, rtol=1e-9):
    if not np.allclose(actual, expected, atol=atol, rtol=rtol):
        difference = float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
        raise ValueError(f"{label} differs: max_abs={difference}")


def write_csv(path, rows):
    if not rows:
        raise ValueError("empty mechanism output")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def old_key(row):
    return (int(row["snr_centi_db"]), int(row["frame"]), row["arm"],
            int(row["round"]), int(row["iteration"]))


def load_prior(prior, receipt, name, count):
    path = prior / name
    hash_field = "audit_csv_sha256" if name.startswith("audit_") else "scalar_csv_sha256"
    if sha(path) != receipt[hash_field]:
        raise ValueError(f"existing {name} differs from its extraction receipt")
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != count:
        raise ValueError(f"existing {name} row count differs")
    index = {old_key(row): row for row in rows}
    if len(index) != count:
        raise ValueError(f"existing {name} coordinates duplicated")
    return index


def check_old_row(prior, current, label):
    for name, expected in current.items():
        if name not in prior:
            raise ValueError(f"existing {label} lacks {name}")
        actual = prior[name]
        if isinstance(expected, (float, int)) and not isinstance(expected, bool):
            if not math.isfinite(float(actual)) or not math.isclose(
                    float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-8):
                raise ValueError(f"existing {label} {name} recount differs")
        elif str(actual) != str(expected):
            raise ValueError(f"existing {label} {name} recount differs")


def main():
    args = arguments()
    args.source, args.baseline, args.e1_run, args.prior_tables, args.out = (
        item.resolve() for item in (args.source, args.baseline, args.e1_run,
                                    args.prior_tables, args.out))
    if args.out.exists() and any(args.out.iterdir()):
        raise ValueError("mechanism extension output must be new or empty")
    sys.path[:0] = [str(args.source / "src"), str(args.baseline / "src")]
    import evidence
    from physical import Channel, daft
    from twofft import TimePathOps
    from messages import moments

    manifest_path = args.e1_run / "manifest.json"
    ledger_path = args.e1_run / "ledger.jsonl"
    manifest = json.loads(manifest_path.read_text())
    if manifest["stage"] != "D" or manifest["source_commit"] != "2d130b4d":
        raise ValueError("saved E1 D numerical identity differs")
    if (manifest["source_hashes"] != evidence.source_hashes(args.source) or
            manifest["baseline_source_hashes"] != evidence.source_hashes(args.baseline)):
        raise ValueError("frozen numerical or baseline source differs")
    run_hash = evidence.canonical_hash(manifest)
    receipt_path = args.prior_tables / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if (receipt["status"] != "pass" or receipt["run_identity_sha256"] != run_hash or
            receipt["source_manifest_sha256"] != sha(manifest_path) or
            receipt["source_ledger_sha256"] != sha(ledger_path) or
            receipt["audited_rows"] != 240 or receipt["paired_scalar_rows"] != 1920):
        raise ValueError("existing mechanism extraction identity/count differs")
    old_audit = load_prior(args.prior_tables, receipt, "audit_iteration_metrics.csv", 240)
    old_scalar = load_prior(args.prior_tables, receipt, "paired_saved_scalar_traces.csv", 1920)
    ledger = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    index = {(row["snr_centi_db"], row["frame"], row["arm"]): row for row in ledger}
    if len(ledger) != 252 or len(index) != 252:
        raise ValueError("saved E1 D252 ledger count differs")
    header = json.loads((args.e1_run / "context_header.json").read_text())
    if int(header["system"]["n_total"]) != N:
        raise ValueError("saved E1 system size differs")
    c1, c2 = float(header["system"]["c1"]), float(header["system"]["c2"])

    def saved(kind, snr, frame, arm=None, round_index=None):
        stem = f"s{snr}_f{frame:03d}"
        if kind == "frame_input":
            path = args.e1_run / "frames" / f"{stem}_input.npz"
        else:
            path = args.e1_run / "checkpoints" / f"{stem}_{arm}_r{round_index}.npz"
        identity = {"schema": OLD_SCHEMA, "run_identity_sha256": run_hash,
                    "kind": kind, "snr_centi_db": snr, "frame": frame}
        if arm is not None:
            identity.update(arm=arm, round=round_index)
        payload, _ = evidence.load_artifact(path, identity)
        return payload, path

    scalar_checked = 0
    audit_checked = 0
    extended = []
    vectors = []
    checkpoint_inventory = []
    reset_checks = []
    max_parity = defaultdict(float)
    for snr in SNRS:
        observed, input_path = saved("frame_input", snr, 0)
        pilot = np.asarray(observed["pilot"], complex)
        noise = float(observed["sigma2"])
        if pilot.shape != (N,) or not math.isfinite(noise) or noise <= 0:
            raise ValueError("saved E1 observation shape/noise differs")
        for arm in ARMS:
            gain_mode = "joint" if arm == "TF_J20_R2" else "point"
            previous_check = None
            for frame in range(FRAMES):
                row = index[(snr, frame, arm)]
                if row["status"] != "ok" or len(row["checkpoints"]) != ROUNDS:
                    raise ValueError("selected E1 trace lacks two completed rounds")
                if frame == 0 and sha(input_path) != row["input_sha256"]:
                    raise ValueError("audited saved input ledger hash differs")
                for round_index, cp in enumerate(row["checkpoints"]):
                    if cp["round"] != round_index:
                        raise ValueError("saved coded round order differs")
                    payload, path = saved("checkpoint", snr, frame, arm, round_index)
                    if sha(path) != cp["artifact_sha256"]:
                        raise ValueError("saved checkpoint ledger hash differs")
                    snapshot = payload["snapshot"]
                    trace = snapshot["inference_trace"]
                    p_count = len(snapshot["ce_gains"])
                    if len(trace) != STEPS or p_count <= 0 or p_count != len(snapshot["delays"]):
                        raise ValueError("saved scalar trace/path count differs")
                    checkpoint_inventory.append({"snr_centi_db": snr, "frame": frame,
                        "arm": arm, "round": round_index,
                        "path": str(path), "sha256": cp["artifact_sha256"]})
                    for iteration, t in enumerate(trace):
                        if t["iteration"] != iteration:
                            raise ValueError("saved scalar trace order differs")
                        scalar = {"snr_centi_db": snr, "frame": frame, "arm": arm,
                            "round": round_index, "iteration": iteration, "n": N,
                            "p_count": p_count,
                            "trace_post_vx": float(t["data_variance"]),
                            "trace_post_vh": float(t["gain_variance"]),
                            "trace_channelpower_pre": float(t["channel_norm_factor"]),
                            "trace_bar": float(t["pseudo_variance_bar"]),
                            "trace_vp": float(t["pseudo_variance_total"]),
                            "trace_vr": float(t["data_pseudo_variance"]),
                            "trace_vq": float(t["gain_pseudo_variance"]),
                            "trace_sv": float(t["output_precision"]),
                            "trace_data_precision_floor": int(t["data_precision_floor"]),
                            "trace_gain_precision_floor": int(t["gain_precision_floor"]),
                            "trace_fft_count": int(t["fft_count"]),
                            "n_trace_post_vh": N*float(t["gain_variance"]),
                            "n_trace_vq": N*float(t["gain_pseudo_variance"])}
                        check_old_row(old_scalar[old_key(scalar)], scalar, "scalar trace")
                        scalar_checked += 1
                    if frame != 0:
                        continue
                    states = payload.get("inference_states")
                    if len(states or ()) != STEPS:
                        raise ValueError("predeclared frame-zero vector audit missing")
                    prior = np.zeros(2*N) if round_index == 0 else np.clip(previous_check, -20, 20)
                    mu_pre, v_pre, _ = moments(prior, .5)
                    h_pre = np.asarray(snapshot["ce_gains"], complex).copy()
                    vh_pre = 1/p_count if gain_mode == "joint" else 0.
                    xb_prev = pilot + mu_pre
                    hb_prev = h_pre.copy()
                    bb_prev = None
                    bar_prev = vp_prev = None
                    sv_prev = 0.
                    operator = TimePathOps(Channel(N, c1, c2, snapshot["delays"],
                                                   snapshot["dopplers"], snapshot["ce_gains"]))
                    reset_checks.append({"snr_centi_db": snr, "arm": arm,
                        "round": round_index, "initial_vh": vh_pre,
                        "initial_sv": sv_prev, "initial_bar_history": bar_prev,
                        "initial_vp_history": vp_prev,
                        "prior_source": "zero" if round_index == 0 else "previous_round_check_clipped"})
                    for iteration, (state, t) in enumerate(zip(states, trace)):
                        x_pre = pilot + mu_pre
                        vx_pre = float(np.mean(v_pre))
                        xpower = float(np.vdot(x_pre, x_pre).real/N)
                        channelpower = operator.power(h_pre)
                        xt = daft(x_pre, c1, c2, True)
                        response = operator.responses_time(xt)
                        raw_bar = vx_pre*channelpower + p_count*vh_pre*xpower
                        raw_vp = raw_bar + p_count*vh_pre*vx_pre
                        bar = raw_bar if bar_prev is None else DAMPING*raw_bar+(1-DAMPING)*bar_prev
                        vp = raw_vp if vp_prev is None else DAMPING*raw_vp+(1-DAMPING)*vp_prev
                        xb = DAMPING*x_pre+(1-DAMPING)*xb_prev
                        hb = DAMPING*h_pre+(1-DAMPING)*hb_prev
                        bb = response.copy() if bb_prev is None else DAMPING*response+(1-DAMPING)*bb_prev
                        s = np.asarray(state["s"], complex)
                        sv = float(state["sv"])
                        alpha_x = sv*operator.power(hb)
                        alpha_h = sv*float(np.vdot(xb, xb).real)
                        vr = 1/max(alpha_x, 1e-12)
                        vq = 1/max(alpha_h, 1e-12)
                        back_data = daft(operator.adjoint_time(hb, s), c1, c2)
                        reaction_data = xb*(sv*p_count*vh_pre)
                        back_gain = bb.conj().T @ s
                        reaction_gain = hb*(sv*N*vx_pre)
                        h_post = np.asarray(state["h"], complex)
                        vh_post = float(state["vh"])
                        vx_post = float(np.mean(state["v"]))
                        gain_move = float(np.linalg.norm(h_post-h_pre))
                        gain_den = float(np.linalg.norm(h_pre))
                        data_den = float(np.linalg.norm(back_data))
                        if min(gain_den, data_den) <= 0:
                            raise ValueError("saved mechanism norm denominator is zero")
                        correction = p_count*vh_pre*(xpower+vx_pre)/(noise+vx_pre*channelpower)
                        latent_vh = (1/p_count)*vq/(1/p_count+vq)
                        expected = {
                            "bar": (bar, state["bar"]), "vp": (vp, state["vp"]),
                            "vr": (vr, state["vr"]), "vq": (vq, state["vq"]),
                            "channelpower": (channelpower, t["channel_norm_factor"]),
                            "post_vx": (vx_post, t["data_variance"]),
                            "post_vh": (vh_post, t["gain_variance"]),
                            "sv": (sv, t["output_precision"]),
                            "gain_posterior": (vh_post, latent_vh if gain_mode == "joint" else 0.),
                            "sv_update": (sv, DAMPING/(noise+vp)+(1-DAMPING)*sv_prev),
                        }
                        for name, (actual, reference) in expected.items():
                            require_close(actual, reference, name)
                            max_parity[name] = max(max_parity[name], abs(float(actual-reference)))
                        current = {"snr_centi_db": snr, "frame": 0, "arm": arm,
                            "gain_mode": gain_mode, "round": round_index,
                            "iteration": iteration, "n": N, "p_count": p_count,
                            "sigma2": noise,
                            "pre_vh": vh_pre, "post_vh": vh_post,
                            "latent_posterior_vh": latent_vh,
                            "pre_vx": vx_pre, "post_vx": vx_post,
                            "xpower": xpower, "xb_power": float(np.vdot(xb, xb).real/N),
                            "channelpower": channelpower,
                            "vq": vq, "sv": sv, "correction": correction,
                            "actual_reaction_ratio": float(np.linalg.norm(reaction_data))/data_den,
                            "user_literal_reaction_ratio":
                                float(np.linalg.norm(p_count*vh_pre*x_pre))*sv/data_den,
                            "gain_movement_ratio": gain_move/gain_den,
                            "n_pre_vh": N*vh_pre, "n_post_vh": N*vh_post,
                            "n_latent_posterior_vh": N*latent_vh,
                            "n_vq": N*vq,
                            "n_vh_prediction": 1/(sv*float(np.vdot(xb, xb).real/N)+p_count/N),
                            "correction_over_p_over_n": correction/(p_count/N),
                            "reaction_over_p_over_n":
                                float(np.linalg.norm(reaction_data))/data_den/(p_count/N),
                            "gain_movement_over_p_over_n": gain_move/gain_den/(p_count/N),
                            "trace_gain_precision_floor": int(t["gain_precision_floor"]),
                            "trace_data_precision_floor": int(t["data_precision_floor"])}
                        check_old_row(old_audit[old_key(current)], current, "vector audit")
                        audit_checked += 1
                        extended.append({
                            "snr_centi_db": snr, "frame": 0, "arm": arm,
                            "round": round_index, "iteration": iteration,
                            "vector_index": len(vectors), "n": N, "p_count": p_count,
                            "vh_pre": vh_pre, "vh_post": vh_post,
                            "vx_pre": vx_pre, "vx_post": vx_post,
                            "alpha_x": alpha_x, "alpha_h": alpha_h,
                            "vr": vr, "vq": vq, "sv": sv,
                            "raw_bar": raw_bar, "damped_bar": bar,
                            "raw_vp": raw_vp, "damped_vp": vp,
                            "xpower_pre": xpower, "channelpower_pre": channelpower,
                            "data_backprojection_norm": data_den,
                            "data_reaction_norm": float(np.linalg.norm(reaction_data)),
                            "gain_backprojection_norm": float(np.linalg.norm(back_gain)),
                            "gain_reaction_norm": float(np.linalg.norm(reaction_gain)),
                            "gain_move_norm": gain_move,
                            "gain_move_ratio": gain_move/gain_den,
                            "output_correction_raw_ratio": correction,
                            "data_precision_floor": int(alpha_x <= 1e-12),
                            "gain_precision_floor": int(alpha_h <= 1e-12)})
                        vectors.append({"x_pre": x_pre.copy(), "h_pre": h_pre.copy(),
                                        "xb": xb.copy(), "hb": hb.copy(),
                                        "data_backprojection": back_data,
                                        "data_reaction": reaction_data,
                                        "gain_backprojection": back_gain,
                                        "gain_reaction": reaction_gain})
                        mu_pre = np.asarray(state["mu"])
                        v_pre = np.asarray(state["v"])
                        h_pre = h_post
                        vh_pre = vh_post
                        xb_prev, hb_prev, bb_prev = xb, hb, bb
                        bar_prev, vp_prev, sv_prev = bar, vp, sv
                    previous_check = np.asarray(snapshot["check"])

    if scalar_checked != 1920 or audit_checked != 240 or len(vectors) != 240:
        raise ValueError("mechanism recount count differs")
    summary_rows = []
    for snr in SNRS:
        for arm in ARMS:
            for round_index in range(ROUNDS):
                for period, selection in (("init_it0", lambda i: i == 0),
                                          ("it1_4", lambda i: 1 <= i <= 4),
                                          ("it5_19", lambda i: i >= 5)):
                    group = [row for row in extended if row["snr_centi_db"] == snr and
                             row["arm"] == arm and row["round"] == round_index and
                             selection(row["iteration"])]
                    if len(group) != (1 if period == "init_it0" else 4 if period == "it1_4" else 15):
                        raise ValueError("mechanism phase count differs")
                    summary_rows.append({"snr_centi_db": snr, "arm": arm,
                        "round": round_index, "period": period,
                        "iterations": len(group),
                        **{f"median_{key}": float(np.median([row[key] for row in group]))
                           for key in ("vh_pre", "vh_post", "alpha_x", "alpha_h",
                                       "raw_bar", "damped_bar", "raw_vp", "damped_vp",
                                       "data_backprojection_norm", "data_reaction_norm",
                                       "gain_backprojection_norm", "gain_reaction_norm",
                                       "gain_move_ratio")}})

    args.out.mkdir(parents=True, exist_ok=True)
    metrics_path = args.out / "extended_audit_metrics.csv"
    summary_path = args.out / "mechanism_extension_summary.csv"
    vectors_path = args.out / "audit_vectors.npz"
    write_csv(metrics_path, extended)
    write_csv(summary_path, summary_rows)
    vector_identity = {"schema": SCHEMA, "kind": "audit_vectors",
                       "e1_run_identity_sha256": run_hash,
                       "source_commit": manifest["source_commit"], "rows": len(vectors)}
    evidence.save_artifact(vectors_path, {"rows": vectors}, vector_identity)
    evidence.load_artifact(vectors_path, vector_identity)
    report = {"schema": SCHEMA, "status": "pass", "scope":
              "offline E1 D saved evidence only; vector audit frame0 TF/POINT, 3 cells, 2 rounds; first8 paired scalar traces; no receiver calls",
              "source_commit": manifest["source_commit"],
              "run_identity_sha256": run_hash,
              "counts": {"vector_rows": audit_checked, "scalar_rows": scalar_checked,
                         "audited_batches": len(reset_checks), "summary_rows": len(summary_rows)},
              "round_reset_checks": reset_checks,
              "max_saved_state_parity_abs": dict(max_parity),
              "meaning": {"pre_post": "pre values enter each iteration; post values are saved posterior state",
                  "output": "raw bar/vp precede output damping; damped bar/vp enter residual update",
                  "alpha": "alpha_x=sv*power(hb), alpha_h=sv*||xb||^2; vr/vq use 1e-12 floors",
                  "reaction": "data: sv*P*vh_pre*xb versus DAFT(adjoint_time(hb,s)); gain: sv*N*vx_pre*hb versus damped B(xb)^H s",
                  "reset": "each coded round initializes sv=0, bar/vp history empty, xb/hb from fresh prior/CE; r1 code prior is clipped prior round check"},
              "sources": {"e1_run_manifest": str(manifest_path), "e1_run_ledger": str(ledger_path),
                  "e1_input_frame0": {str(snr): str(args.e1_run / "frames" / f"s{snr}_f000_input.npz") for snr in SNRS},
                  "audited_and_scalar_checkpoints": checkpoint_inventory,
                  "prior_extraction_receipt": str(receipt_path)},
              "sha256": {"script": sha(__file__), "e1_manifest": sha(manifest_path),
                  "e1_ledger": sha(ledger_path), "prior_receipt": sha(receipt_path),
                  "prior_audit_csv": sha(args.prior_tables / "audit_iteration_metrics.csv"),
                  "prior_scalar_csv": sha(args.prior_tables / "paired_saved_scalar_traces.csv"),
                  "extended_metrics_csv": sha(metrics_path),
                  "summary_csv": sha(summary_path), "vectors_npz": sha(vectors_path)}}
    (args.out / "receipt.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "pass", "vector_rows": audit_checked,
                      "scalar_rows": scalar_checked, "summary_rows": len(summary_rows)}))


if __name__ == "__main__":
    main()
