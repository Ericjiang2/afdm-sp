"""One imported observation: real receiver parity and checkpoint artifact recount."""
import json
import os
import sys
from pathlib import Path

import numpy as np

source = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
sys.path[:0] = [str(source / "src"), str(baseline / "src")]
import evidence
from receiver import context
from native_twofft import receive
from native_controls import receive_control

system, _, code, header = context()
system.P_paths = 8
system.rho = .5
with np.load(source / "results" / "native_0_input_truth.npz", allow_pickle=False) as old:
    observed = {key: old[key] for key in ("y", "pilot", "sigma2")}
out.mkdir(parents=True, exist_ok=False)
rows = []
arms = [
    ("TF_J20_R2", lambda sink: receive(observed, system, code, checkpoint_sink=sink),
     "fair_0_twofft_soft_joint.npz"),
    ("EP2_SOFT_R2", lambda sink: receive_control(observed, system, code, kind="ep",
      iterations=2, ce_mode="soft", checkpoint_sink=sink), "fair_0_EP2_soft_fastCE.npz"),
    ("PBI8_SOFT_R2", lambda sink: receive_control(observed, system, code, kind="pbi",
      iterations=8, ce_mode="soft", checkpoint_sink=sink), "fair_0_PBi8_soft_fastCE.npz"),
]
for name, call, reference in arms:
    checkpoints = []
    def sink(event, decoded):
        index = event["round"]
        payload = {"event": {key: value for key, value in event.items() if key != "snapshot"},
                   "snapshot": event["snapshot"], "decoded": decoded}
        path = out / f"{name}_r{index}.npz"
        digest = evidence.save_artifact(path, payload, {"kind": "fixture", "arm": name,
                                                        "round": index})
        reread, _ = evidence.load_artifact(path, {"kind": "fixture", "arm": name,
                                          "round": index})
        if not np.array_equal(reread["decoded"], decoded):
            raise AssertionError("durable checkpoint decision differs")
        if not np.allclose(reread["snapshot"]["app"],
                           reread["snapshot"]["input_llr"] + reread["snapshot"]["check"],
                           atol=1e-9, rtol=0):
            raise AssertionError("APP/check accounting differs")
        checkpoints.append((index, digest))
    result = call(sink)
    with np.load(source / "results" / reference, allow_pickle=False) as prior:
        for index in (0, 1):
            key = f"r{index}_decoded"
            if not np.array_equal(result[1][key], prior[key]):
                raise AssertionError(f"{name} changed the imported fixture decision at round {index}")
    if len(checkpoints) != 2:
        raise AssertionError("both durable checkpoints required")
    rows.append({"arm": name, "checkpoint_sha256": [item[1] for item in checkpoints],
                 "seconds": result[2]["seconds"], "decision_parity": True})
(out / "summary.json").write_text(json.dumps({"scope": "imported fixture, not new trial",
    "source_hashes": evidence.source_hashes(source), "baseline_hashes": evidence.source_hashes(baseline),
    "rows": rows}, indent=2) + "\n")
print("PASS imported fixture 3-arm parity, six durable checkpoints and APP recount")
