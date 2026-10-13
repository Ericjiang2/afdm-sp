"""Print compact A5/A6/A7 fields from sealed raw; no receiver, TF or truth calls."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--selection", type=Path, required=True)
    args = ap.parse_args()
    project = args.project.resolve()
    root = project / "results/tf_cstate_prospective_20260923/observed"
    manifest = json.loads((root / "manifest.json").read_text())
    argv = manifest["argv"]
    baseline = Path(argv[argv.index("--baseline") + 1]).resolve()
    if not baseline.is_relative_to(project / "experiments"):
        raise ValueError("sealed baseline path escapes project")
    sys.path.insert(0, str(baseline / "src"))
    import evidence  # type: ignore[import-not-found]

    selection = json.loads(args.selection.read_text())
    assert len(selection["rows"]) == 72
    rows = [json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()]
    by = {(r["observation_id"], r["arm"]): r for r in rows}
    seal = json.loads((root / "observed_seal.json").read_text())
    if seal["status"] != "pass" or len(rows) != 6144 or len(by) != 6144:
        raise ValueError("observed campaign seal/ledger differs")
    if manifest["population_observed_seal_sha256"] != selection["population_seal_sha256"]:
        raise ValueError("population-to-observed seal differs")
    out = []
    for selected in selection["rows"]:
        stem = selected["observation_id"]
        loaded = {}
        for arm in ("TF", "TF_CSTATE"):
            row = by[(stem, arm)]
            if row["status"] != "ok" or row["input_sha256"] != selected["observation_sha256"]:
                raise ValueError("arm identity differs")
            path = Path(row["raw_path"])
            if path.is_absolute() or ".." in path.parts or seal["files"].get(str(path)) != row["raw_sha256"]:
                raise ValueError("raw path/seal differs")
            raw = root / path
            if digest(raw) != row["raw_sha256"]:
                raise ValueError("raw bytes differ")
            payload, _ = evidence.load_artifact(raw)
            if payload["observation_id"] != stem or payload["input_sha256"] != selected["observation_sha256"]:
                raise ValueError("raw payload identity differs")
            loaded[arm] = payload
        tf = loaded["TF"]
        cstate = loaded["TF_CSTATE"]
        for key in ("r0_delays", "r0_dopplers", "r1_delays", "r1_dopplers"):
            if not np.array_equal(tf["baseline_arrays"][key], cstate["baseline_arrays"][key]):
                raise ValueError("native paired geometry differs")
        arrays = tf["baseline_arrays"]
        geometry = cstate["geometry_result"]
        trigger = bool(cstate["triggered"])
        if trigger != (geometry is not None):
            raise ValueError("CSTATE trigger/geometry differs")
        edits = [] if geometry is None else [dict(step=int(e["step"]), slot=int(e["slot"]),
            old=e["old"], new=e["new"], decrease=float(e["decrease"]))
            for e in geometry["edits"]]
        out.append(dict(observation_id=stem, observation_hash=selected["observation_hash"],
            input_sha256=selected["observation_sha256"],
            tf_raw_sha256=by[(stem, "TF")]["raw_sha256"],
            cstate_raw_sha256=by[(stem, "TF_CSTATE")]["raw_sha256"],
            a5_delays=np.asarray(arrays["r0_delays"]).astype(int).tolist(),
            a5_dopplers=np.asarray(arrays["r0_dopplers"]).astype(float).tolist(),
            a5_ce_objective_history=np.asarray(arrays["r0_ce_history"]).astype(float).tolist(),
            a6_delays=np.asarray(arrays["r1_delays"]).astype(int).tolist(),
            a6_dopplers=np.asarray(arrays["r1_dopplers"]).astype(float).tolist(),
            a6_ce_objective_history=np.asarray(arrays["r1_ce_history"]).astype(float).tolist(),
            a7_triggered=trigger, a7_entering_paths=None if geometry is None else
                geometry["global_trace"][0]["entering_paths"] if geometry["global_trace"] else None,
            a7_edits=edits, a7_final_paths=None if geometry is None else geometry["paths"],
            a7_objective_before=None if geometry is None else float(geometry["objective_before"]),
            a7_objective_after=None if geometry is None else float(geometry["objective_after"])))
    print(json.dumps(dict(schema="cstate-archived-geometry-72/1", source="sealed original raw, no replay",
                          observed_manifest_sha256=digest(root / "manifest.json"),
                          observed_seal_sha256=digest(root / "observed_seal.json"),
                          observed_ledger_sha256=digest(root / "ledger.jsonl"),
                          selection_sha256=digest(args.selection), rows=out),
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
