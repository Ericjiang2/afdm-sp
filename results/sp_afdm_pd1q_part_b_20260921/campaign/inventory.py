#!/usr/bin/env python3
"""Hash every retained Part B file after validated analysis, without changing evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args()
root, out = args.root.resolve(), args.out.resolve()
if out.exists():
    raise ValueError("inventory receipt already exists")
entries = []
for path in sorted(root.rglob("*")):
    relative = path.relative_to(root)
    if path.is_file() and path != out and not (
            relative.parts[0] == "launch" and
            (relative.name.startswith("inventory_") or relative.name in
             ("lifecycle.txt", "exit_code.txt"))):
        entries.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
                        "sha256": digest(path)})
total = sum(item["bytes"] for item in entries)
receipt = {"schema": "spafdm-pd1q-partb-inventory/1", "status": "pass",
           "file_count": len(entries), "raw_bytes": total,
           "exclusions": ["remote_inventory.json", "active launch/inventory_* receipts",
                          "launch/lifecycle.txt", "launch/exit_code.txt"],
           "entries": entries}
out.write_text(json.dumps(receipt, separators=(",", ":"), allow_nan=False) + "\n")
print(json.dumps({"status": "pass", "files": len(entries), "raw_bytes": total}))
