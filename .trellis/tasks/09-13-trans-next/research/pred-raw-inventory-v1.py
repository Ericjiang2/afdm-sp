"""Read-only remote evidence inventory; no receiver, CE, BP, or decoder call."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path("/data/guoyikun/00inbox/AFDM-channel-estimation")
OLD = ROOT / "afdm_sp_joint_unrolled/outputs_trans_next_20260913"
DIR = ROOT / "afdm_sp_joint_unrolled/outputs_dirichlet_shrinkage_20260914"
sys.path.insert(0, str(DIR / "source-v4"))
from afdm_sp_joint_unrolled.light_gap_replay import verified_record


def shape(value):
    if hasattr(value, "shape"):
        return {"shape": list(value.shape), "dtype": str(value.dtype)}
    if isinstance(value, dict):
        return {str(k): shape(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return {"length": len(value), "first": [shape(v) for v in value[:1]]}
    return value if isinstance(value, (int, float, bool, str)) or value is None else str(type(value))


out = {"at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "receiver_calls": 0, "CE_calls": 0, "BP_calls": 0, "LDPC_calls": 0,
       "cpu_count": os.cpu_count(), "disk_free_bytes": shutil.disk_usage(ROOT).free,
       "loadavg": os.getloadavg(), "summaries": []}
out["memory"] = {line.split(":")[0]: line.split(":")[1].strip()
                 for line in Path("/proc/meminfo").read_text().splitlines()
                 if line.split(":")[0] in ("MemTotal", "MemAvailable")}
for label, command in [("GPU", ["nvidia-smi"]),
                       ("tmux", ["tmux", "list-sessions", "-F", "#{session_name}"]),
                       ("own_processes", ["ps", "-u", str(os.getuid()), "-o", "pid,etimes,comm"])]:
    r = subprocess.run(command, capture_output=True, text=True, timeout=15)
    out[label] = {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
paths = [OLD / "runs/g1-strong-development-recovery-v1/development/summary.json",
         *sorted((OLD / "runs").glob("*physical*/*/summary.json")),
         DIR / "engineering/summary.json", DIR / "development/summary.json"]
for path in paths:
    summary = json.loads(path.read_text())
    item = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mtime_utc": datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc).isoformat(),
            "status": summary.get("status"), "calls": summary.get("calls"),
            "source_sha256": summary.get("source_sha256"), "contract_sha256": summary.get("contract_sha256"),
            "record_count": len(summary.get("records", []))}
    item["samples"] = []
    for kind, arm in [("A", None), ("F", "G1_FULL" if "g1-strong" in str(path) else None)]:
        entry = next((e for e in summary.get("records", []) if e["kind"] == kind
                      and (arm is None or e["arm"] == arm)), None)
        if entry is not None:
            _, raw = verified_record(entry, OLD if path.is_relative_to(OLD) else DIR)
            item["samples"].append({"entry": entry, "raw_schema": shape(raw)})
    out["summaries"].append(item)
print(json.dumps(out, ensure_ascii=False, allow_nan=False))
