"""Inventory P1 frame labels from archived outputs, without invoking receivers."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
UNIFIED = HERE.parent / "unified_cov_prospective_20261119"
sys.path.insert(0, str(UNIFIED))
import audit_frames as archived  # noqa: E402 (resolve the frozen project scanner)

FIRST, BASE_LAST, EXTENDED_LAST = 4600, 4799, 4999
SCANNER_SHA256 = "40469e202deb18d6d5b546ef3dc1b20e8b33c259896cc8d28b8c2a93eb9c7b6e"
RAW_SHA256 = "0b06f38b0928ab87eed949b155b0dc49c0928ed66425fc6cbe30373f02e2323d"
# Before the prior 746-second scan, whose saved receipt was written at 02:21 UTC.
DELTA_SINCE = datetime(2026, 11, 19, 2, 0, tzinfo=timezone.utc)
UB = "experiments/headroom_ladder_20261008/out/ub_screen/decision_MODEL/"
NUMAX = "experiments/tcom_reference_frame_20261015/out/s0/numax.json"
KNOWN_LOG = "afdm_sp_joint_unrolled/outputs_dpss_paired_screen_20261111_v2/gate.json"


def overlaps(frames, first, last):
    return any(r[0] <= last and r[-1] >= first for r in frames)


def scan(root, remote, last=BASE_LAST, *, first=FIRST):
    scanner = Path(archived.__file__)
    if sha256(scanner.read_bytes()).hexdigest() != SCANNER_SHA256:
        raise RuntimeError("Frozen frame scanner mismatch")

    counts, ignored, unresolved = Counter(), Counter(), []
    if remote:
        raw = UNIFIED / "out/phase1_20261119/frames_deinlab_raw.json"
        if sha256(raw.read_bytes()).hexdigest() != RAW_SHA256:
            raise RuntimeError("Frozen deinlab frame inventory mismatch")
        prior = json.loads(raw.read_text())
    else:
        prior = None

    def check_hit(name, stream, frames):
        if not overlaps(frames, first, last):
            return
        if stream != "P1" and name.startswith(UB):
            ignored["synthetic UB Screen RNG"] += 1
        elif stream != "P1" and name == NUMAX:
            ignored["S0 numax Monte Carlo (draw count)"] += 1
        else:
            unresolved.append(dict(file=name, stream=stream, frames=frames))

    def check_error(name, error):
        if Path(name).name.startswith("._"):
            ignored["AppleDouble sidecar"] += 1
        elif name == KNOWN_LOG and error == "JSONDecodeError":
            path = root / name
            if archived.FRAME.search(path.read_bytes()):
                unresolved.append(dict(file=name, error=error))
            else:
                ignored["legacy gate stdout counters"] += 1
        else:
            unresolved.append(dict(file=name, error=error))

    if prior:
        for hit in prior["hits"]:
            check_hit(hit["file"], hit["stream"], hit["frames"])
        for error in prior["errors"]:
            check_error(error["file"], error["error"])

    groups = (("experiments", (root / "experiments").glob("*/out")),
              ("historical", (root / "afdm_sp_joint_unrolled").glob("outputs_*")))
    for scope, directories in groups:
        for directory in sorted(directories):
            if not directory.is_dir() or directory.parent == HERE:
                continue
            counts[f"{scope}_roots"] += 1
            for folder, _, files in os.walk(directory):
                for name in files:
                    if not name.lower().endswith(archived.WATCH_SUFFIXES):
                        continue
                    path = Path(folder) / name
                    if path.parent == UNIFIED / "out/phase1_20261119" and name in (
                        "frames_deinlab_raw.json", "frames_deinlab_configs.json",
                    ):
                        continue
                    rel = str(path.relative_to(root))
                    if remote and directory.parent != UNIFIED and path.stat().st_ctime < DELTA_SINCE.timestamp():
                        continue
                    structured = not name.endswith((".jsonl", ".jsonl.gz"))
                    counts[f"{scope}_" + ("metadata" if structured else "rows")] += 1
                    try:
                        frames, head = archived.scan_file(path, structured)
                        overlap = sorted(n for n in frames if first <= n <= last)
                        if overlap:
                            check_hit(rel, archived.path_stream(path, head), archived.ranges(overlap))
                    except (OSError, ValueError, EOFError) as exc:
                        check_error(rel, type(exc).__name__)

    base_clear = not any("error" in hit or overlaps(hit["frames"], FIRST, BASE_LAST)
                         for hit in unresolved)
    return dict(status="PASS" if not unresolved else "STOP", interval_inclusive=[first, last],
                base_status="PASS" if base_clear else "STOP",
                extension_inclusive=[4800, EXTENDED_LAST] if last == EXTENDED_LAST else [4700, BASE_LAST],
                scope="deinlab" if remote else "local",
                p1_identity=dict(entropy_prefix=archived.P1.decode(), domain="TCRF"),
                scanner_sha256=SCANNER_SHA256, scanned=dict(counts), ignored=dict(ignored),
                prior_inventory_sha256=RAW_SHA256 if prior else None,
                prior_scanned=prior["scanned"] if prior else None,
                delta_since_utc=DELTA_SINCE.isoformat() if prior else None,
                unresolved=unresolved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--extended", action="store_true")
    scope.add_argument("--extension-only", action="store_true")
    args = parser.parse_args()
    receipt = scan(HERE.parents[1], args.remote,
                   EXTENDED_LAST if args.extended or args.extension_only else BASE_LAST,
                   first=BASE_LAST + 1 if args.extension_only else FIRST)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    gate = "status" if args.extension_only else "base_status"
    raise SystemExit(0 if receipt[gate] == "PASS" else 1)


if __name__ == "__main__":
    main()
