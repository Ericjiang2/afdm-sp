"""Read-only import of actual old A/B channel seeds and historical tuple seeds."""
import json
import sys
from pathlib import Path
import numpy as np

old = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
out = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(baseline / "src"))
import evidence

entries = []
for stage in ("A", "B"):
    root = old / f"stage_{stage}"
    manifest = json.loads((root / "manifest.json").read_text())
    run_hash = evidence.canonical_hash(manifest)
    for snr, frame in sorted({(item[0], item[1]) for item in manifest["coordinates"]}):
        path = root / "frames" / f"s{snr}_f{frame:03d}_truth.npz"
        ident = {"schema": "spafdm-native-joint-compact/1", "run_identity_sha256": run_hash,
                 "kind": "frame_truth", "snr_centi_db": snr, "frame": frame}
        saved, _ = evidence.load_artifact(path, ident)
        seed = saved["seed"]
        entropy = seed["entropy"]["channel"]
        actual = int(seed["channel_seed"])
        predicted = int(np.random.default_rng(np.random.SeedSequence(entropy)).integers(0, 2**31))
        if actual != predicted:
            raise ValueError("saved actual channel seed differs from entropy")
        entries.append({"scope": f"stage_{stage}_actual", "snr_centi_db": snr,
                        "frame": frame, "entropy": entropy, "channel_seed": actual,
                        "artifact_sha256": evidence.artifact_sha256(path)})
for index in range(20):
    entropy = [20260921, 935170, index, 1]
    value = int(np.random.default_rng(np.random.SeedSequence(entropy)).integers(0, 2**31))
    entries.append({"scope": "prior_exploratory_20_tuple", "frame": index,
                    "entropy": entropy, "channel_seed": value})
for index in range(1, 9):
    entropy = [20260921, 935171, index, 1]
    value = int(np.random.default_rng(np.random.SeedSequence(entropy)).integers(0, 2**31))
    entries.append({"scope": "prior_native_8_tuple", "frame": index,
                    "entropy": entropy, "channel_seed": value})
if len(entries) != 88 or len({x["channel_seed"] for x in entries}) != 88:
    raise ValueError("prior registry incomplete or colliding")
if out.exists():
    raise ValueError("prior registry destination exists")
out.write_text(json.dumps({"schema": "spafdm-native-direction-prior-seeds/1",
    "old_root": str(old), "entries": entries}, indent=2) + "\n")
print("prior actual/historical entries", len(entries))
