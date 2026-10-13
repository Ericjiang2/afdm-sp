"""Extract only absent frozen F2 campaign files from the Git-bound package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile
import time


project = Path("/data/guoyikun/00inbox/AFDM-channel-estimation")
dispatch = project / "results/cstate_necessity_stageB_resume_20260928/population_five_dispatch_v1"
manifest = json.loads((dispatch / "dispatch.json").read_text())
archive = dispatch / "source.tar.gz"
if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["tar_sha256"]:
    raise ValueError("dispatch tar SHA differs")
expected = manifest["files"]
with tarfile.open(archive, "r:gz") as packed:
    members = packed.getmembers()
    if {member.name for member in members} != set(expected):
        raise ValueError("dispatch tar file set differs")
    contents = {}
    for member in members:
        relative = Path(member.name)
        target = (project / relative).resolve()
        if (not member.isfile() or relative.is_absolute() or ".." in relative.parts
                or not target.is_relative_to(project) or target.exists()):
            raise ValueError(f"unsafe or colliding dispatch member: {member.name}")
        source = packed.extractfile(member)
        if source is None:
            raise ValueError(f"missing tar bytes: {member.name}")
        contents[member.name] = source.read()
        if (len(contents[member.name]) != expected[member.name]["size_bytes"]
                or hashlib.sha256(contents[member.name]).hexdigest() !=
                expected[member.name]["sha256"]):
            raise ValueError(f"dispatch member differs: {member.name}")

for relative, data in contents.items():
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(data)
    target.chmod(0o755 if relative.endswith(".sh") else 0o644)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected[relative]["sha256"]:
        raise ValueError(f"deployed member differs: {relative}")

receipt = {
    "schema": "f2-five-policy-deployment/1",
    "git_commit": manifest["git_commit"],
    "manifest_sha256": manifest["manifest_sha256"],
    "tar_sha256": manifest["tar_sha256"],
    "files": {relative: item["sha256"] for relative, item in expected.items()},
    "deployed_epoch": time.time(),
    "status": "deployed_no_receiver_calls",
}
with (dispatch / "deployed.json").open("x") as stream:
    json.dump(receipt, stream, sort_keys=True)
    stream.write("\n")
print(json.dumps(receipt, sort_keys=True))
