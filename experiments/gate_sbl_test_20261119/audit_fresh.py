"""Check archived frame IDs and launch declarations without importing a receiver."""

import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
UNIFIED = EXP / "unified_cov_prospective_20261119"
SCANNER = {
    UNIFIED / "audit_frames.py": "40469e202deb18d6d5b546ef3dc1b20e8b33c259896cc8d28b8c2a93eb9c7b6e",
    EXP / "tf_split_prosp_20261018/verify_frames.py":
        "096d880d23388387495e7979557fa312ade1d268c03fcbbda86cbd2e07d3278a",
}
BASE = UNIFIED / "out/phase1_20261119/frames_deinlab_raw.json"
BASE_SHA = "0b06f38b0928ab87eed949b155b0dc49c0928ed66425fc6cbe30373f02e2323d"
# Same overlapping baseline/delta cutoff as the residual-gap receipts.
DELTA = 1795053600  # 2026-11-19 02:00 UTC
S = (5800, 6199)
S_BASE = (5800, 5999)
S_EXTENSION = (6200, 6399)
X = (1600, 2199)
X_ENTROPY = b"fedc6f5c81c7acbbb2c0d4652b47e8e82b0767d3bde61797e58475853bb5df12"
X_LINEAGE = {
    "cstate_sparse_doublet_screen_20261118", "doublet_conflict_20261119",
    "gate_screen_20261119", "readout_batch_20261119",
}
X_RANGE = re.compile(rb'"[\w_]*?(?:frames|frame_range|inclusive_block)"\s*:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]')
UB = "experiments/headroom_ladder_20261008/out/ub_screen/decision_MODEL/"
NUMAX = "experiments/tcom_reference_frame_20261015/out/s0/numax.json"
LEGACY = "afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111_v2/gate.json"


def verify(path, expected):
    actual = sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Frozen audit input mismatch: {path}: {actual} != {expected}")


def names_mixed8(data):
    return X_ENTROPY in data or b'"MIXED8"' in data or b'S8D2' in data


def mixed8_declarations(path, archived):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rb") as handle:
        data = handle.read()
    declared = set()
    # The frozen manifest reader clips ranges and CLI flags below frame 4400.
    for first, last in X_RANGE.findall(data):
        first, last = int(first), int(last)
        declared.update(range(max(first, X[0]), min(last, X[1]) + 1))
    args = {name: int(value) for name, value in archived.ARGUMENT.findall(data.decode())}
    first = next((args[k] for k in ("frame-offset", "frame-start", "start-frame") if k in args), 0)
    last = next((args[k] for k in ("frame-stop", "frame-end", "end-frame") if k in args), None)
    if last is None and (n := args.get("n-frames", args.get("frames"))) is not None:
        last = first + n - 1
    if last is not None:
        declared.update(range(max(first, X[0]), min(last, X[1]) + 1))
    return declared


def scan(remote, *, extension=False):
    for path, expected in SCANNER.items():
        verify(path, expected)
    sys.path.insert(0, str(UNIFIED))
    import audit_frames as archived

    root = EXP.parent
    first, last = S_EXTENSION if extension else S
    counts, ignored = Counter(), Counter()
    overlaps = {"S": [], "X": []}
    errors = []
    prior = None
    if remote:
        verify(BASE, BASE_SHA)
        prior = json.loads(BASE.read_text())

    def s_hit(name, stream, ranges):
        if stream != "P1" and name.startswith(UB):
            ignored["synthetic UB stream"] += 1
        elif stream != "P1" and name == NUMAX:
            ignored["S0 Monte Carlo draw count"] += 1
        else:
            overlaps["S"].append(dict(file=name, stream=stream, frames=ranges))

    def error(name, kind):
        if Path(name).name.startswith("._"):
            ignored["AppleDouble sidecar"] += 1
        elif name == LEGACY and kind == "JSONDecodeError" and not archived.FRAME.search(
                (root / name).read_bytes()):
            ignored["legacy gate stdout counters"] += 1
        else:
            errors.append(dict(file=name, error=kind))

    if prior:
        for hit in prior["hits"]:
            if any(block[0] <= last and block[-1] >= first for block in hit["frames"]):
                s_hit(hit["file"], hit["stream"], hit["frames"])
        for item in prior["errors"]:
            error(item["file"], item["error"])

    groups = (("experiments", EXP.glob("*/out")),
              ("historical", (root / "afdm_sp_joint_unrolled").glob("outputs_*")))
    for scope, directories in groups:
        for directory in sorted(directories):
            if not directory.is_dir() or directory.parent == HERE:
                continue
            counts[f"{scope}_roots"] += 1
            x_source = directory.parent.name in X_LINEAGE
            for folder, _, files in os.walk(directory):
                for name in files:
                    if not name.lower().endswith(archived.WATCH_SUFFIXES):
                        continue
                    path = Path(folder) / name
                    if path.parent == BASE.parent and name in (BASE.name, "frames_deinlab_configs.json"):
                        continue
                    if (remote and not x_source and directory.parent != UNIFIED
                            and path.stat().st_ctime < DELTA):
                        continue
                    rel = str(path.relative_to(root))
                    structured = not name.endswith((".jsonl", ".jsonl.gz"))
                    counts[f"{scope}_" + ("metadata" if structured else "rows")] += 1
                    try:
                        frames, head = archived.scan_file(path, structured)
                        s = sorted(f for f in frames if first <= f <= last)
                        if s:
                            s_hit(rel, archived.path_stream(path, head), archived.ranges(s))
                        if not extension and (x_source or names_mixed8(head)):
                            x = {f for f in frames if X[0] <= f <= X[1]}
                            if structured:
                                x.update(mixed8_declarations(path, archived))
                            counts["mixed8_files"] += 1
                            if x:
                                overlaps["X"].append(dict(file=rel, frames=archived.ranges(x)))
                    except (OSError, ValueError, EOFError) as exc:
                        error(rel, type(exc).__name__)
    s_base_hits = [hit["file"] for hit in overlaps["S"]
                   if any(block[0] <= S_BASE[1] and block[-1] >= S_BASE[0]
                          for block in hit["frames"])]
    s = dict(interval_inclusive=(first, last), entropy_prefix=archived.P1.decode(), domain="TCRF",
             status="STOP" if errors or overlaps["S"] else "PASS", overlaps=overlaps["S"])
    receipt = dict(status=s["status"], scope="deinlab" if remote else "local",
                   scanned=dict(counts), ignored=dict(ignored),
                   scanner_sha256={str(p.relative_to(EXP)): h for p, h in SCANNER.items()},
                   prior_inventory_sha256=BASE_SHA if remote else None,
                   prior_scanned=prior["scanned"] if remote else None,
                   delta_since_utc="2026-11-19T02:00:00Z" if remote else None,
                   S=s, unresolved=errors)
    if not extension:
        s.update(base_interval_inclusive=S_BASE, base_overlaps=s_base_hits,
                 base_status="STOP" if errors or s_base_hits else "PASS")
        receipt.update(status="STOP" if errors or s_base_hits or overlaps["X"] else "PASS",
                       X=dict(interval_inclusive=X, entropy=X_ENTROPY.decode(), domain="S8D2",
                              status="STOP" if errors or overlaps["X"] else "PASS",
                              lineage=sorted(X_LINEAGE), overlaps=overlaps["X"]))
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--s-extension", action="store_true")
    args = parser.parse_args()
    receipt = scan(args.remote, extension=args.s_extension)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(receipt["status"] != "PASS")
