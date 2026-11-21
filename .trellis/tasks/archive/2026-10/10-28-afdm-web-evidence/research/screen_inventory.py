"""Read-only, coarse publication screening of one committed AFDM subtree.

This is planning evidence, not a publisher or deletion list. Git blob equality
identifies exact copies only; retained source paths are never collapsed.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess


PROJECT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(["git", "-C", str(PROJECT), *args])


REPO = Path(git("rev-parse", "--show-toplevel").decode().strip())
PREFIX = PROJECT.relative_to(REPO).as_posix() + "/"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-ref", default="HEAD", help="Committed source to inspect; no working-tree files are published.")
args = parser.parse_args()
SHA = git("rev-parse", "--verify", args.source_ref + "^{commit}").decode().strip()
raw = subprocess.check_output(
    ["git", "-C", str(REPO), "ls-tree", "-rlz", SHA, "--", PREFIX]
)
files = {}
for entry in raw.decode().split("\0"):
    if not entry:
        continue
    meta, full = entry.split("\t")
    mode, kind, oid, size = meta.split()
    if kind == "blob":
        files[full.removeprefix(PREFIX)] = {
            "oid": oid, "bytes": int(size), "mode": mode
        }

denied_roots = {
    ".agents", ".claude", ".codex", ".gemini", ".opencode", ".ccb",
    ".commandcode", ".obsidian", "_archive", "_claim_audit_bundle_v2",
}
binary = {
    ".npz", ".npy", ".pt", ".pth", ".ckpt", ".mat", ".pkl", ".pickle",
    ".h5", ".gz", ".tgz", ".zip", ".tar", ".7z", ".fig", ".pdf",
}
text_suffixes = {".md", ".txt", ".json", ".py", ".sh", ".yaml", ".yml", ".csv"}
initial_families = {
    "experiments/tcom_reference_frame_20261015",
    "experiments/headroom_ladder_20261008",
    "experiments/sp_afdm_native_joint_20260921",
    "experiments/sp_afdm_frozen_20260920",
    "experiments/tf_cstate_validation_20260922",
    "experiments/tf_cstate_e1_20261017",
    "experiments/tf_cstate_e2_20261017",
    "experiments/tf_e3_sbl_20261017",
    "experiments/sbl_joint_detector_20261019",
    "experiments/sbl_three_mode_20261020",
    "experiments/sbl_freeze_replay_20261020",
}
seeds = {
    "STATE.md", "research-assets/index.md", "research-assets/prediction-ledger.md",
    "learning/sp_minimal/README.md", ".trellis/spec/research-protocol.md",
    ".trellis/tasks/09-22-tf-production-gap-audit/research/discovery_negative_results_ledger.md",
    ".trellis/tasks/09-22-tf-production-gap-audit/research/ledger-20261019.md",
    ".trellis/tasks/10-20-sbl-freeze-replay/protocol.md",
    "afdm_sp_joint_unrolled/supplement_messages.py",
}


def exclusion(path):
    p = PurePosixPath(path)
    if p.parts[0] in denied_roots:
        return "archive-or-agent-runtime"
    if ".mission" in p.parts and p.suffix != ".csv":
        return "mission-runtime-trace"
    if "exam" in p.parts:
        return "sealed-exam-no-default-export"
    if p.name.startswith(".env") or p.suffix in {".pem", ".key"}:
        return "credential-like-path"
    if p.suffix.lower() in binary:
        return "binary-or-large-original"
    if files[path]["mode"] == "120000":
        return "symlink-needs-target-review"
    if files[path]["bytes"] > 1024 * 1024:
        return "over-1MiB-review-on-demand"
    return None


status = {}
reason = {}
for path in files:
    why = exclusion(path)
    if why:
        status[path], reason[path] = "excluded", why
    else:
        status[path], reason[path] = "on_demand", "not-in-initial-reading-scope"
        family = any(path.startswith(f + "/") for f in initial_families)
        family_detail = not any(part in PurePosixPath(path).parts for part in ("tests", "upstream", "out", "source_snapshot"))
        family_detail = family_detail and not PurePosixPath(path).name.startswith("test_")
        card = re.fullmatch(r"research-assets/res-\d{8}-\d+\.md", path)
        task = path.startswith(".trellis/tasks/10-20-sbl-freeze-replay/")
        if path in seeds or card or (((family and family_detail) or task) and PurePosixPath(path).suffix in text_suffixes):
            status[path], reason[path] = "initial", "mainline-learning-current-evidence"

# Read Markdown only when needed for explicit evidence links. Never read the exam.
texts = {}


def markdown(path):
    if path not in texts:
        texts[path] = git("show", f"{SHA}:{PREFIX}{path}").decode("utf-8")
    return texts[path]


def references(path, content):
    targets = re.findall(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", content)
    targets += re.findall(r"`([^`\n]+\.(?:md|py|json|csv|txt|sh|png|svg))`", content)
    for target in targets:
        target = target.strip("<>").split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "~", "/")):
            continue
        local = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
        if target in files:
            yield target, target
        else:
            yield target, local


# All cards remain visible, including negative/draft/corrected cards. Expand
# evidence for recent mainline cards and current leads, not every historical arc.
expand = {
    p: 0 for p in files if status[p] == "initial" and p.endswith(".md")
    and (not p.startswith("research-assets/res-") or p >= "research-assets/res-20261015")
}
visited = set()
issues = set()
while expand:
    path, depth = expand.popitem()
    if path in visited:
        continue
    visited.add(path)
    content = markdown(path)
    if path == "STATE.md":
        content = content.split("\n## ", 2)
        content = "\n## ".join(content[:2])
    for target, resolved in references(path, content):
        if resolved.startswith("../"):
            issues.add((path, target, "cross-project-reference-needs-explicit-mapping"))
        elif resolved not in files:
            why = "directory-or-glob-on-demand" if any(x.startswith(resolved.rstrip("/") + "/") for x in files) or "*" in resolved else "untracked-or-absent-at-source-commit"
            issues.add((path, target, why))
        elif status[resolved] == "excluded":
            issues.add((path, target, reason[resolved]))
        elif "source_snapshot" in PurePosixPath(resolved).parts:
            issues.add((path, target, "frozen-source-copy-on-demand"))
        else:
            if status[resolved] != "initial":
                status[resolved], reason[resolved] = "initial", "explicit-evidence-reference"
            if resolved.endswith(".md") and resolved not in visited and depth < 1:
                expand[resolved] = min(expand.get(resolved, depth + 1), depth + 1)

groups = defaultdict(list)
for path, meta in files.items():
    if meta["bytes"]:
        groups[meta["oid"]].append(path)
dupes = [paths for paths in groups.values() if len(paths) > 1]
dupes.sort(key=lambda paths: files[paths[0]]["bytes"] * (len(paths) - 1), reverse=True)
totals = {s: {"files": 0, "bytes": 0} for s in ("initial", "on_demand", "excluded")}
by_root = defaultdict(lambda: {s: {"files": 0, "bytes": 0} for s in totals})
for p, meta in files.items():
    for tally in (totals, by_root[p.split('/')[0]]):
        tally[status[p]]["files"] += 1
        tally[status[p]]["bytes"] += meta["bytes"]
summary = {
    "source_commit": SHA, "source_prefix": PREFIX,
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "planning-only metadata and Markdown-link screening; not a runtime dependency or secret audit",
    "link_expansion": "seed documents plus one further Markdown layer; old evidence remains available on demand",
    "total_files": len(files), "total_bytes": sum(x["bytes"] for x in files.values()),
    "categories": totals, "roots": dict(sorted(by_root.items())),
    "reasons": dict(Counter(reason.values())),
    "duplicate_groups": len(dupes),
    "duplicate_extra_paths": sum(len(g) - 1 for g in dupes),
    "duplicate_extra_bytes": sum(files[g[0]]["bytes"] * (len(g) - 1) for g in dupes),
    "largest_duplicate_groups": [
        {"oid": files[g[0]]["oid"], "bytes_each": files[g[0]]["bytes"],
         "copies": len(g), "sample_paths": g[:6]} for g in dupes[:12]
    ],
    "link_issue_counts": dict(Counter(x[2] for x in issues)),
    "link_issue_samples": [dict(zip(("source", "target", "reason"), row)) for row in sorted(issues)[:45]],
    "missing_required_seeds": sorted(seeds - files.keys()),
    "initial_old_test_paths": [p for p in sorted(files) if status[p] == "initial" and ("test_" in p or "/tests/" in p)],
}
assert sum(x['files'] for x in totals.values()) == len(files)
assert sum(x['bytes'] for x in totals.values()) == summary['total_bytes']
(OUT / "inventory-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
(OUT / "initial-paths.txt").write_text("\n".join(p for p in sorted(files) if status[p] == "initial") + "\n")
print(json.dumps({k: summary[k] for k in ("source_commit", "total_files", "total_bytes", "categories", "duplicate_groups", "duplicate_extra_paths", "duplicate_extra_bytes", "link_issue_counts", "missing_required_seeds")}, indent=2))
