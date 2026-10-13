"""Read-only remote hash check before a frozen F2 campaign launch."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


project = Path("/data/guoyikun/00inbox/AFDM-channel-estimation")
experiment = project / "experiments"
results = project / "results/cstate_necessity_stageB_resume_20260928"
manifest_path = results / "F2_FIVE_POLICY_MANIFEST.json"
manifest = json.loads(manifest_path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


checks: dict[str, object] = {}
checks["manifest_sha256"] = sha256(manifest_path)
dispatch = json.loads((results / "population_five_dispatch_v1/dispatch.json").read_text())
assert checks["manifest_sha256"] == dispatch["manifest_sha256"]
for name, expected in manifest["producer_source_hashes"].items():
    assert sha256(experiment / "cstate_necessity_stageB_resume_20260928" / name) == expected, name
checks["producer_files"] = len(manifest["producer_source_hashes"])
assert sha256(experiment / "cstate_necessity_stageB_resume_20260928/f2_launch_population_five_once.sh") == manifest["launcher_sha256"]
for key, name in (
    ("authorization_sha256", "F2_FIVE_POLICY_AUTHORIZATION.json"),
    ("domain_recovery_proposal_sha256", "F2_DOMAIN_RECOVERY_PROPOSAL.md"),
    ("method_sha256", "F2_METHOD_CONTRACT.md"),
    ("numerical_amendment_sha256", "F2_NUMERICAL_AMENDMENT.md"),
    ("population_protocol_sha256", "F2_FIVE_POLICY_PROTOCOL.md"),
    ("population_budget_sha256", "F2_FIVE_POLICY_BUDGET.md"),
    ("small_reference_qualification_sha256", "F2_SMALL_REFERENCE_QUALIFICATION.md"),
):
    assert sha256(results / name) == manifest[key], name
checks["contract_documents"] = 7
for name, expected in manifest["analysis_source_hashes"].items():
    assert sha256(experiment / name) == expected, name
checks["analysis_files"] = len(manifest["analysis_source_hashes"])
assert sha256(experiment / "cstate_necessity_stageB_resume_20260928/summarize_trigger_subgroups_five.py") == manifest["subgroup_source_sha256"]
for name, expected in manifest["dependency_source_hashes"].items():
    assert sha256(experiment / name) == expected, name
checks["dependency_files"] = len(manifest["dependency_source_hashes"])

sys.path.insert(0, str(experiment / "tf_production_gap_audit_20260922"))
from audit_io import attach  # noqa: E402

native = experiment / "sp_afdm_native_joint_reviewed_20260921"
baseline = experiment / "sp_afdm_frozen_reviewed_20260921"
evidence = attach(native, baseline)
for key, root in (("native_source_hashes", native), ("baseline_source_hashes", baseline)):
    actual = evidence.source_hashes(root)
    assert actual == manifest[key], key
    checks[key + "_count"] = len(actual)
cache = baseline / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
assert sha256(cache) == manifest["ldpc_cache_sha256"]
checks["ldpc_cache_sha256"] = manifest["ldpc_cache_sha256"]

for label, root, expected in (
    ("population", project / "results/tf_cstate_prospective_20260923/population_observed", manifest["population_observed_seal_sha256"]),
    ("historical", project / "results/cstate_necessity_stageA_20260928/observed", manifest["stage_a_observed_seal_sha256"]),
    ("branch_qualification", results / "branch_qualification_v2", manifest["branch_qualification_seal_sha256"]),
):
    assert sha256(root / "observed_seal.json") == expected, label
    checks[label + "_seal_sha256"] = expected

for name in ("population_five_launch_v1", "population_five_v1"):
    assert not (results / name).exists(), name
checks["output_collision"] = False
checks["status"] = "pass_readonly_no_receiver"
print(json.dumps(checks, sort_keys=True))
