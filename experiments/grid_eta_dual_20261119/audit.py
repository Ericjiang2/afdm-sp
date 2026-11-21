"""Inventory archived frame IDs using the prior 11-19 baseline and delta scanner."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
X, S = (56000, 56999), (6800, 6999)
S_EXTENSION = (7000, 7199)
SPLIT_ARCHIVE = "experiments/tf_split_prosp_20261018"
SPLIT_FILES = {
    "PROTOCOL.md": "d602b69a5d65096454acb65b4b62d899eda43bbb42b9a15357081ba723cb9724",
    "out/main/STATUS.txt": "37e3d4efb821eb8e2c66e993ce2c9dcf705464bb21e94e26d262806a70bcbc9b",
    "out/main/REMOTE_ROWS_MD5.txt": "75ec3889a0aa24f223249e376ce771b2806b04079bed9d75940cc02aaeb9c872",
}
TRUNCATED_GATE = "experiments/gate_sbl_test_20261119/out/phase1_v2_20261119/sbl_g3.json"
TRUNCATED_SHA256 = "6e334689592aaec46ce040bfb9af57a682f68fcfb8f3c25c5895629a0612f2e5"


def scan(remote, *, s_extension=False):
    parent = HERE.parent / "sbl_residual_gap_20261119"
    source = parent / "audit_fresh.py"
    digest = sha256(source.read_bytes()).hexdigest()
    if digest != "bac45939e076da46d6a1c5c90e254938d6a495b84f8b8473852dabde35d1e6bf":
        raise RuntimeError(f"Frozen inventory scanner differs: {source}")
    sys.path.insert(0, str(parent))
    import audit_fresh as prior

    # Use one pass for the requested intervals, retaining all parse errors.
    intervals = {"S_extension": S_EXTENSION} if s_extension else {"X": X, "S": S}
    first = min(lo for lo, _ in intervals.values())
    last = max(hi for _, hi in intervals.values())
    inventory = prior.scan(HERE.parents[1], remote, last, first=first)
    hits = inventory.pop("unresolved")
    errors, discarded = [], []
    for hit in (item for item in hits if "error" in item):
        if hit == dict(file=TRUNCATED_GATE, error="JSONDecodeError"):
            path = HERE.parents[1] / hit["file"]
            log = path.with_name("run.log").read_text()
            if (sha256(path.read_bytes()).hexdigest() == TRUNCATED_SHA256
                    and path.with_name("STATUS").read_text().strip() == "STOPPED (1)"
                    and "write_json(out, 'sbl_g3.json', report['G3'])" in log
                    and "TypeError: Object of type bool_ is not JSON serializable" in log):
                # The gate had already published its 24 replay rows separately.
                discarded.append(dict(hit, sha256=TRUNCATED_SHA256,
                                      reason="stopped summary serialization; scanned source rows separately"))
                continue
        errors.append(hit)
    for field in ("status", "base_status", "extension_inclusive", "interval_inclusive",
                  "p1_identity"):
        inventory.pop(field)
    if s_extension:
        # The local vault carries the immutable manifest and completion receipt
        # even where the large row shards live only on deinlab.
        root = HERE.parents[1] / SPLIT_ARCHIVE
        for path, expected in SPLIT_FILES.items():
            if sha256((root / path).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"Frozen split-principle provenance differs: {root / path}")
        hits.append(dict(file=f"{SPLIT_ARCHIVE}/out/main/STATUS.txt", stream="P1/TCRF",
                         frames=[list(S_EXTENSION)], archive_sha256=SPLIT_FILES))
    blocks = {}
    for leg, (first, last) in intervals.items():
        collisions = [hit for hit in hits if "frames" in hit
                      and prior.overlaps(hit["frames"], first, last)]
        blocks[leg] = dict(interval_inclusive=[first, last], collisions=collisions,
                           status="STOP" if collisions or errors else "PASS")
    return dict(inventory, status="STOP" if any(b["status"] == "STOP" for b in blocks.values())
                else "PASS", unresolved=errors, blocks=blocks, scanner_wrapper_sha256=digest,
                discarded_incomplete_summaries=discarded,
                _argv=sys.argv, _config=dict(remote=remote, **intervals))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--s-extension", action="store_true")
    args = parser.parse_args()
    receipt = scan(args.remote, s_extension=args.s_extension)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    raise SystemExit(receipt["status"] != "PASS")
