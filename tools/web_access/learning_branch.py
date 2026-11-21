#!/usr/bin/env python3
"""Owner-controlled AFDM learning branch helper for the existing AgentDock clone."""

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path("/srv/agentdock/AgentDock/afdm-sp")
REMOTE = "/srv/git/afdm-sp.git"
BRANCH = "chatgpt/learning"
IDENTITY = {"project_id": "afdm-e2e-main", "source_prefix": "00_Inbox/AFDM-channel-estimation",
            "mac_remote": "jgw:/srv/git/afdm-sp.git", "server_remote": REMOTE}
ALLOWED = "learning/sp_minimal/"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def check_identity():
    if not ROOT.is_dir() or ROOT.resolve() != ROOT:
        raise ValueError(f"wrong or missing clone: {ROOT}")
    if Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve() != ROOT:
        raise ValueError("not at expected AFDM clone root")
    if git("remote", "get-url", "origin").decode().strip() != REMOTE:
        raise ValueError("wrong exchange remote")
    if json.loads((ROOT / "PROJECT.json").read_text()) != IDENTITY:
        raise ValueError("wrong project identity")
    if json.loads(git("show", "origin/main:PROJECT.json")) != IDENTITY:
        raise ValueError("owner main has wrong project identity")


def changed_worktree():
    records = [part for part in git("-c", "status.showUntrackedFiles=all", "status", "--porcelain=v1", "-z").split(b"\0") if part]
    paths = []
    for record in records:
        status = record[:2].decode()
        if "R" in status or "C" in status:
            raise ValueError("rename/copy status requires manual review")
        paths.append(record[3:].decode())
    return paths


def check_allowed(paths):
    for name in paths:
        if not name.startswith(ALLOWED) or ".." in Path(name).parts or (ROOT / name).is_symlink():
            raise ValueError(f"change outside AFDM learning or symlink: {name}")
        if any(parent.is_symlink() for parent in (ROOT / name).parents if parent != ROOT and ROOT in parent.parents):
            raise ValueError(f"symlink parent: {name}")


def check_git_modes(paths, rev=None):
    for name in paths:
        if rev:
            record = git("ls-tree", rev, "--", name).decode()
            mode = record.split(" ", 1)[0]
        else:
            record = git("ls-files", "--stage", "--", name).decode()
            mode = record.split(" ", 1)[0]
        if mode and mode not in ("100644", "100755"):
            raise ValueError(f"symlink or nonregular tracked path: {name}")


def start():
    check_identity()
    if changed_worktree():
        raise ValueError("uncommitted changes; preserve and review them before start")
    git("fetch", "origin")
    check_identity()
    local = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/" + BRANCH], cwd=ROOT)
    if local.returncode == 0:
        git("switch", BRANCH)
    else:
        remote_branch = subprocess.run(["git", "show-ref", "--verify", "--quiet",
                                        "refs/remotes/origin/" + BRANCH], cwd=ROOT)
        git("switch", "-c", BRANCH, "origin/" + BRANCH if remote_branch.returncode == 0 else "origin/main")
    if subprocess.run(["git", "show-ref", "--verify", "--quiet",
                       "refs/remotes/origin/" + BRANCH], cwd=ROOT).returncode == 0:
        git("merge", "--no-edit", "origin/" + BRANCH)
    git("merge", "--no-edit", "origin/main")
    print(f"Ready: {ROOT} on {BRANCH}; evidence pointer {(ROOT / 'RELEASE').read_text().strip()}")


def end(message):
    check_identity()
    if git("branch", "--show-current").decode().strip() != BRANCH:
        raise ValueError(f"not on {BRANCH}")
    git("fetch", "origin")
    check_identity()
    if subprocess.run(["git", "merge-base", "--is-ancestor", "origin/main", "HEAD"], cwd=ROOT).returncode:
        raise ValueError("owner main advanced; run start to merge before publishing")
    if subprocess.run(["git", "show-ref", "--verify", "--quiet",
                       "refs/remotes/origin/" + BRANCH], cwd=ROOT).returncode == 0 and \
            subprocess.run(["git", "merge-base", "--is-ancestor", "origin/" + BRANCH,
                            "HEAD"], cwd=ROOT).returncode:
        raise ValueError("remote learning branch advanced; run start to merge before publishing")
    staged_or_unstaged = changed_worktree()
    check_allowed(staged_or_unstaged)
    committed = [p.decode() for p in git("diff", "--name-only", "-z", "origin/main...HEAD").split(b"\0") if p]
    check_allowed(committed)
    check_git_modes(committed, "HEAD")
    if staged_or_unstaged:
        git("add", "--", "learning/sp_minimal")
        check_git_modes(staged_or_unstaged)
        git("commit", "-m", message)
    committed = [p.decode() for p in git("diff", "--name-only", "-z", "origin/main...HEAD").split(b"\0") if p]
    check_allowed(committed)
    check_git_modes(committed, "HEAD")
    if not committed:
        print("No learning changes to publish")
        return
    git("push", "origin", "HEAD:refs/heads/" + BRANCH)
    print(f"Published {len(committed)} learning path(s) on {BRANCH}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start")
    p = sub.add_parser("end")
    p.add_argument("--message", required=True)
    args = parser.parse_args()
    try:
        if args.command == "start":
            start()
        else:
            end(args.message)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
