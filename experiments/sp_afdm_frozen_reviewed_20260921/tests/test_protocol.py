"""Synthetic selection/analysis contracts; these rows are not radio evidence."""
import json
import os
import sys
import tempfile
from pathlib import Path

for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ[key] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analyze import analyze_records  # noqa: E402
from seal import create_lock  # noqa: E402


protocol = json.loads((ROOT / "protocol" / "protocol.json").read_text())
catalog = json.loads((ROOT / "protocol" / "configurations.json").read_text())
development = []
for cell in protocol["development_cells"]:
    for frame in range(protocol["development_frames_per_cell"]):
        for arm in catalog:
            error = int(frame % 10 < cell["id"] + 1)
            development.append({
                "cell": cell["id"], "frame": frame, "arm": arm, "status": "ok",
                "seconds": 1.0, "info_errors": error,
                "timeline": [{"elapsed": 1.0, "info_errors": error}],
            })

priced_arm = next(arm for arm in reversed(catalog) if arm != protocol["reference_runtime_arm"])
for record in development:
    if record["arm"] == priced_arm and record["frame"] % 2 == 0:
        record["status"] = "numerical_failure"
        record["seconds"] = 9.0

with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    (directory / "manifest.json").write_text("{}")
    (directory / "ledger.jsonl").write_text("synthetic\n")
    manifest = {"source_hashes": {"synthetic": "a" * 64}, "environment": {"synthetic": True}}
    lock = create_lock(development, manifest, protocol, catalog, directory)
    assert lock["selection_scores"][priced_arm]["median_complete_seconds"] == 5.0

lock["frames_per_cell"] = 16
confirmation = []
for cell in lock["cells"]:
    for frame in range(lock["frames_per_cell"]):
        for arm in lock["configurations"]:
            error = int(frame % 4 == 0)
            confirmation.append({
                "cell": cell["id"], "frame": frame, "arm": arm, "status": "ok",
                "seconds": 1.0, "info_errors": error,
                "timeline": [{"elapsed": 1.0, "info_errors": error}],
            })

results = analyze_records(lock, confirmation)
assert all(result["paired_difference"] == 0 for result in results)
failure_cost_lock = {
    "cells": [{"id": 0}], "frames_per_cell": 2, "primary_method": "A",
    "primary_baseline_by_cell": {"0": "B"}, "primary_deadline": 10.0,
    "configurations": ["A", "B"],
}
failure_cost_records = [
    {"cell": 0, "frame": 0, "arm": "A", "status": "ok", "seconds": 1.0,
     "info_errors": 0, "timeline": [{"elapsed": 1.0, "info_errors": 0}]},
    {"cell": 0, "frame": 1, "arm": "A", "status": "numerical_failure", "seconds": 9.0,
     "info_errors": 1, "timeline": []},
] + [
    {"cell": 0, "frame": frame, "arm": "B", "status": "ok", "seconds": 2.0,
     "info_errors": 0, "timeline": [{"elapsed": 2.0, "info_errors": 0}]}
    for frame in range(2)
]
failure_cost = analyze_records(failure_cost_lock, failure_cost_records)[0]["runtime"]["A"]
assert failure_cost["mean"] == 5.0 and failure_cost["median"] == 5.0
assert failure_cost["numerical_failures"] == 1
(ROOT / "results" / "protocol_test.json").write_text(json.dumps({
    "synthetic": True,
    "development_records": len(development),
    "confirmation_contract_rows": len(confirmation),
    "same_arms_null_test_pass": True,
    "real_confirmation_executed": False,
}, indent=2))
print("PASS synthetic selection/lock/paired-analysis contract; no radio evidence")
