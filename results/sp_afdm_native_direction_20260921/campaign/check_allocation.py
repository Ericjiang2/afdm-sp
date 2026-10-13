"""Pre-observation check of the frozen 252-call allocation and seed namespace."""
import json
import sys
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
from common import attach, expected, historical_channel_seeds, plan, seed_descriptor

cfg = plan()
rows = list(expected("D"))
counts = Counter((snr, arm) for snr, frame, arm in rows)
assert len(rows) == 252 and len({(snr, frame) for snr, frame, _ in rows}) == 96
for snr in (600, 650, 700):
    assert counts[(snr, "TF_J20_R2")] == counts[(snr, "EP2_MEAN_R2")] == 32
    assert counts[(snr, "EP4_MEAN_R2")] == counts[(snr, "TF_POINT20_R2")] == 8
    assert counts[(snr, "PBI8_SOFT_R2")] == 4
    assert {frame for s, frame, arm in rows if s == snr and arm == "PBI8_SOFT_R2"} == set(range(4))
    assert {frame for s, frame, arm in rows if s == snr and arm == "TF_POINT20_R2"} == set(range(8))
prior = historical_channel_seeds()
fresh = [seed_descriptor("D", snr, frame)["channel_seed"]
         for snr in (600, 650, 700) for frame in range(32)]
assert len(prior) == 88 and len(set(fresh)) == 96 and not (set(fresh) & prior)
assert cfg["audit_frames"] == [0] and cfg["source_commit"] == "2d130b4d"
source, baseline, old = map(Path, sys.argv[1:4])
evidence = attach(source, baseline)
previous = json.loads((old / "stage_A" / "manifest.json").read_text())
assert evidence.source_hashes(source) == previous["source_hashes"]
assert evidence.source_hashes(baseline) == previous["baseline_source_hashes"]
from run import make_manifest
manifest = make_manifest(SimpleNamespace(source=source, baseline=baseline,
    stage="D", source_commit="2d130b4d"), evidence)
assert len(manifest["coordinates"]) == 252 and manifest["audit_frames"] == [0]
print(json.dumps({"status": "pass", "receiver_calls": len(rows), "independent_frames": 96,
                  "prior_channel_seeds": len(prior), "fresh_channel_seeds": len(set(fresh)),
                  "seed_collisions": 0, "audit_frame_per_cell": 0,
                  "numerical_source_identity": "identical to qualified A/B"}))
