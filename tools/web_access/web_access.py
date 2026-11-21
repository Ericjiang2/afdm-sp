#!/usr/bin/env python3
"""Package a committed AFDM reading snapshot and review learning returns."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone


PREFIX = "00_Inbox/AFDM-channel-estimation"
PROJECT_ID = "afdm-e2e-main"
REMOTE = "jgw:/srv/git/afdm-sp.git"
SERVER_REMOTE = "/srv/git/afdm-sp.git"
LEARNING = "learning/sp_minimal/"
FORBIDDEN = {"exam", ".aws", ".ssh", ".env", "credentials", "secrets", "private_keys"}
HERE = Path(__file__).resolve().parent


def git(cwd, *args, input_bytes=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout


def safe_path(name):
    path = PurePosixPath(name)
    if (not name or name.startswith("/") or "\\" in name or
            any(part in ("", ".", "..") for part in name.split("/")) or
            any(part.lower() in FORBIDDEN for part in path.parts) or
            any(part.lower().startswith(".env") for part in path.parts)):
        raise ValueError(f"unsafe selected path: {name}")
    return name


def project_root(path):
    root = Path(path).resolve(strict=True)
    if root.as_posix().endswith("/" + PREFIX) is False:
        raise ValueError(f"wrong project root: {root}")
    vault = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != vault / PREFIX:
        raise ValueError(f"project is not the expected vault subtree: {root}")
    return root, vault


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def tree_entries(vault, commit, prefix):
    raw = git(vault, "ls-tree", "-rz", "--full-tree", commit, "--", prefix)
    entries = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        left, name = record.split(b"\t", 1)
        mode, kind, _ = left.decode().split(" ")
        entries[name.decode()] = (mode, kind)
    return entries


def pack(args):
    root, vault = project_root(args.project_root)
    commit = git(vault, "rev-parse", "--verify", "--end-of-options", args.source_ref + "^{commit}").decode().strip()
    selection = Path(args.selection).read_text().splitlines()
    paths = sorted({safe_path(line) for line in selection if line and not line.startswith("#")})
    if len(paths) != len([line for line in selection if line and not line.startswith("#")]):
        raise ValueError("selection has duplicate paths")
    if not paths or "STATE.md" not in paths or "learning/sp_minimal/README.md" not in paths:
        raise ValueError("selection lacks required entry paths")
    entries = tree_entries(vault, commit, PREFIX)
    for path in paths:
        mode, kind = entries.get(f"{PREFIX}/{path}", (None, None))
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"missing, nonregular or symlink source: {path}")
    output = Path(args.output).absolute()
    if output.resolve() == vault or vault in output.resolve().parents:
        raise ValueError("staging output must be outside the vault")
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.parent / ("." + output.name + f".{os.getpid()}.tmp")
    if temp.exists():
        raise ValueError(f"temporary output already exists: {temp}")
    try:
        release = temp / "release"
        exchange = temp / "exchange"
        release.mkdir(parents=True)
        exchange.mkdir()
        archive = git(vault, "archive", "--format=tar", commit, "--", *(f"{PREFIX}/{p}" for p in paths))
        files = {}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                if member.isdir():
                    continue
                name = member.name.removeprefix(PREFIX + "/")
                if name not in paths or not member.isfile():
                    raise ValueError(f"unexpected archive member: {member.name}")
                data = tar.extractfile(member).read()
                target = release / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                files[name] = {"bytes": len(data), "sha256": sha(data)}
        if set(files) != set(paths):
            raise ValueError("archive did not contain exactly the selected files")
        component_hashes = {name: sha((HERE / name).read_bytes())
                            for name in ("web_access.py", "AGENTS.md", "learning_branch.py")}
        identity = {"files": files, "source_commit": commit, "components": component_hashes}
        release_id = sha(canonical(identity))
        entry = (
            f"# AFDM reading snapshot\n\nProject: {PROJECT_ID}\nRelease: {release_id}\n"
            f"Source vault commit: {commit}\nSource prefix: {PREFIX}\n\n"
            "Start at STATE.md; follow its links to result cards, protocols and recorded evidence. "
            "The source files retain their original status and limitations. "
            "This is a reading selection, not a complete runtime checkout.\n\n"
            "The sealed learning exam, raw remote rows and other unselected paths are unavailable here. "
            "A saved log describes its recorded time, not a live experiment.\n"
        ).encode()
        (release / "ENTRY.md").write_bytes(entry)
        manifest = {
            "project_id": PROJECT_ID, "source_prefix": PREFIX,
            "source_ref": args.source_ref, "source_commit": commit,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "release_id": release_id, "files": files,
            "components": component_hashes,
            "entry_sha256": sha(entry),
            "selection": "explicit allowlist; no dependency or runtime closure promised",
            "exclusions": ["learning/sp_minimal/exam/", "unselected source paths", "uncommitted files"],
            "unavailable": ["deinlab-only raw per-frame rows", "unselected remote raw evidence"],
        }
        (release / "manifest.json").write_bytes(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True).encode() + b"\n")
        verify_release(release)
        for name in paths:
            if name.startswith(LEARNING):
                target = exchange / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(release / name, target)
        (exchange / "PROJECT.json").write_text(json.dumps({"project_id": PROJECT_ID, "source_prefix": PREFIX,
                                                       "mac_remote": REMOTE, "server_remote": SERVER_REMOTE}, indent=2) + "\n")
        (exchange / "RELEASE").write_text(release_id + "\n")
        for name in ("AGENTS.md", "learning_branch.py"):
            shutil.copyfile(HERE / name, exchange / name)
        os.rename(temp, output)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    print(json.dumps({"release_id": release_id, "source_commit": commit, "files": len(files), "output": str(output)}))


def verify_release(release):
    release = Path(release)
    if release.is_symlink():
        raise ValueError("release root is a symlink")
    manifest = json.loads((release / "manifest.json").read_text())
    if manifest["project_id"] != PROJECT_ID or manifest["source_prefix"] != PREFIX:
        raise ValueError("wrong project identity")
    files = manifest["files"]
    identity = {"files": files, "source_commit": manifest["source_commit"],
                "components": manifest["components"]}
    if manifest["release_id"] != sha(canonical(identity)):
        raise ValueError("release content identity mismatch")
    expected = set(files) | {"ENTRY.md", "manifest.json"}
    actual = set()
    for path in release.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink in release: {path}")
        if path.is_file():
            actual.add(path.relative_to(release).as_posix())
    if actual != expected:
        raise ValueError(f"release file set mismatch: {sorted(actual ^ expected)}")
    for name, metadata in files.items():
        safe_path(name)
        data = (release / name).read_bytes()
        if len(data) != metadata["bytes"] or sha(data) != metadata["sha256"]:
            raise ValueError(f"payload mismatch: {name}")
    if sha((release / "ENTRY.md").read_bytes()) != manifest["entry_sha256"]:
        raise ValueError("entry mismatch")
    for required in ("STATE.md", "learning/sp_minimal/README.md"):
        if required not in files:
            raise ValueError(f"missing entry: {required}")
    return manifest


def review(args):
    root, vault = project_root(args.project_root)
    if not re.fullmatch(r"origin/chatgpt/[A-Za-z0-9._/-]+", args.proposal) or \
            ".." in args.proposal.split("/") or "//" in args.proposal or args.proposal.endswith("/"):
        raise ValueError("proposal must name an origin/chatgpt/* branch")
    checkout = Path(args.checkout).resolve(strict=True)
    if checkout == root or root in checkout.parents or checkout == vault or vault in checkout.parents:
        raise ValueError("exchange checkout must be external to the vault")
    if Path(git(checkout, "rev-parse", "--show-toplevel").decode().strip()).resolve() != checkout:
        raise ValueError("wrong exchange checkout root")
    if git(checkout, "remote", "get-url", "origin").decode().strip() != REMOTE:
        raise ValueError("wrong exchange remote")
    identity = json.loads(git(checkout, "show", "origin/main:PROJECT.json"))
    if identity != {"project_id": PROJECT_ID, "source_prefix": PREFIX,
                    "mac_remote": REMOTE, "server_remote": SERVER_REMOTE}:
        raise ValueError("wrong exchange project identity")
    branch_ref = "refs/remotes/" + args.proposal
    proposal = git(checkout, "rev-parse", "--verify", "--end-of-options", branch_ref + "^{commit}").decode().strip()
    if json.loads(git(checkout, "show", f"{proposal}:PROJECT.json")) != identity:
        raise ValueError("proposal changed identity")
    base = git(checkout, "merge-base", "origin/main", proposal).decode().strip()
    changed = [p.decode() for p in git(checkout, "diff", "--name-only", "-z", base, proposal).split(b"\0") if p]
    if any(not name.startswith(LEARNING) or not safe_path(name) for name in changed):
        raise ValueError(f"proposal touches paths outside {LEARNING}: {changed}")
    for name in changed:
        target = root / name
        if any(parent.is_symlink() for parent in (target, *target.parents) if parent == root or root in parent.parents):
            raise ValueError(f"Mac learning path traverses symlink: {name}")
        for rev in (base, proposal):
            mode = git(checkout, "ls-tree", rev, "--", name).decode().split(" ", 1)[0]
            if mode and mode not in ("100644", "100755"):
                raise ValueError(f"proposal contains symlink or nonregular file: {name}")
    if not changed:
        print("No learning changes")
        return
    if subprocess.run(["git", "merge-base", "--is-ancestor", proposal, "origin/main"], cwd=checkout).returncode == 0:
        print("Already accepted: proposal is in owner main")
        return
    def blob(rev, name):
        if not git(checkout, "ls-tree", rev, "--", name):
            return None
        return git(checkout, "show", f"{rev}:{name}")
    for name in changed:
        target = root / name
        if target.exists() and not target.is_file():
            raise ValueError(f"Mac learning path is not a regular file: {name}")
    current = {name: (root / name).read_bytes() if (root / name).is_file() else None for name in changed}
    proposed = {name: blob(proposal, name) for name in changed}
    if current == proposed:
        print("Already accepted: Mac learning bytes equal proposal")
        return
    for name in changed:
        if (root / name).is_symlink() or current[name] != blob(base, name):
            raise ValueError(f"Mac learning preimage differs from exchange base: {name}")
    patch = git(checkout, "diff", "--binary", base, proposal, "--", LEARNING.rstrip("/"))
    command = ["git", "apply", "--directory=" + PREFIX]
    subprocess.run(command + ["--check", "-"], cwd=vault, input=patch, check=True)
    sys.stdout.buffer.write(patch)
    if args.apply:
        subprocess.run(command + ["-"], cwd=vault, input=patch, check=True)
        print(f"Applied {len(changed)} learning path(s) from {proposal}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=str(HERE.parent.parent))
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--source-ref", required=True)
    p.add_argument("--selection", required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("verify")
    p.add_argument("--release", required=True)
    p = sub.add_parser("review")
    p.add_argument("--checkout", required=True)
    p.add_argument("--proposal", required=True)
    p.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "pack":
            pack(args)
        elif args.command == "verify":
            manifest = verify_release(args.release)
            print(f"Verified {manifest['release_id']} ({len(manifest['files'])} files)")
        else:
            review(args)
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
