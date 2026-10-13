#!/usr/bin/env python3
"""Offline-only crosscheck of the predesignated heavy audit subset."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np

from compact import array_hash, artifact_identity, attach_source, validate_run
from run_stage import final_arrays


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("preserve existing audit receipt")
    evidence = attach_source(args.source)
    checked = validate_run(args.run, args.source)
    from afdm_sp_joint_unrolled.supplement_g1 import physical_channel_matrix

    manifest = checked["manifest"]
    system = __import__("json").loads((args.run / "context_header.json").read_text())["system"]
    n, c1, c2, prefix = (system[key] for key in ("n_total", "c1", "c2", "l_max_cap"))
    frame = manifest["audit_absolute_frame"]
    run_hash = checked["run_identity_sha256"]
    rows = []
    for row in checked["records"]:
        if row["absolute_frame"] != frame:
            continue
        cell, arm = row["cell"], row["arm"]
        stem = f"c{cell:02d}_f{frame:06d}"
        if row["status"] != "ok":
            rows.append({"cell": cell, "arm": arm, "status": row["status"],
                         "nmse_recount": None})
            continue
        truth, _ = evidence.load_artifact(args.run / "heavy" / f"{stem}_truth.npz",
            artifact_identity(run_hash, "heavy_truth", cell, frame))
        heavy, _ = evidence.load_artifact(args.run / "heavy" / f"{stem}_{arm}.npz",
            artifact_identity(run_hash, "heavy_arm", cell, frame, arm))
        compact, _ = evidence.load_artifact(args.run / "compact" / f"{stem}_{arm}.npz",
            artifact_identity(run_hash, "arm", cell, frame, arm))
        h_true = physical_channel_matrix(n, c1, c2, truth["l_i"], truth["k_real"],
                                         truth["g_i"], prefix_length=prefix)
        arrays = final_arrays({"arrays": heavy["result"]})
        if all(name in arrays for name in ("path_delays", "path_dopplers", "path_gains")):
            h_est = physical_channel_matrix(n, c1, c2, arrays["path_delays"],
                arrays["path_dopplers"], arrays["path_gains"], prefix_length=prefix)
        elif "front_H_coo" in heavy:
            coo = heavy["front_H_coo"]
            h_est = np.zeros(tuple(coo["shape"]), dtype=coo["data"].dtype)
            h_est[coo["rows"], coo["columns"]] = coo["data"]
            if "front_H_canary" in heavy and not np.array_equal(h_est, heavy["front_H_canary"]):
                raise ValueError("actual I1 H COO differs from dense canary")
        else:
            raise ValueError(f"audit arm lacks reconstructible H: {cell} {arm}")
        nmse = float(np.vdot(h_est - h_true, h_est - h_true).real /
                     np.vdot(h_true, h_true).real)
        saved = compact["diagnostics"]
        if (not np.isclose(nmse, saved["channel_nmse"], rtol=1e-10, atol=1e-12)
                or not np.isclose(nmse, row["channel_nmse"], rtol=1e-10, atol=1e-12)
                or array_hash(h_est) != saved["channel_estimate_sha256"]
                or array_hash(h_true) != saved["truth_channel_sha256"]):
            raise ValueError(f"heavy H NMSE/hash differs from compact producer score: {cell} {arm}")
        rows.append({"cell": cell, "arm": arm, "status": "ok", "nmse_recount": nmse,
                     "channel_estimate_sha256": array_hash(h_est)})
    if len(rows) != len(manifest["cells"]) * len(manifest["arms"]):
        raise ValueError("audit subset is incomplete")
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    evidence.write_json_atomic(args.out, {"status": "pass", "stage": manifest["stage"],
        "audit_absolute_frame": frame, "audit_arms": len(rows),
        "run_identity_sha256": run_hash,
        "ledger_sha256": evidence.artifact_sha256(args.run / "ledger.jsonl"),
        "audit_script_sha256": script_hash, "rows": rows})
    print(f"heavy audit pass: {len(rows)} arm-cells, stage {manifest['stage']}")


if __name__ == "__main__":
    main()
