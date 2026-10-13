"""Local Git-object proofs, then portable hash-bound production handoffs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (PROJECT, SCHEMA, git_ancestor, git_blob, git_relative,
                    sha256, write_json)

GIT_PREFIX = "00_Inbox/AFDM-channel-estimation/"


def _portable_git_path(path: Path) -> str:
    return GIT_PREFIX + path.resolve().relative_to(PROJECT.resolve()).as_posix()


def attest_registration(protocol: Path, commit: str) -> Path:
    lock = protocol / "registration.json"
    names = ("registration.json", "random_namespace.json", "source_bindings.json")
    files = [protocol / name for name in names]
    files.append(PROJECT / ".trellis/tasks/09-22-tf-production-gap-audit/cgr-prospective-mechanism.md")
    for path in files:
        git_blob(commit, git_relative(path), path)
    report = dict(schema=SCHEMA, kind="registration_git_attestation",
                  registration_commit=commit,
                  git_blobs={git_relative(path): sha256(path) for path in files},
                  registration_sha256=sha256(lock))
    output = protocol / "registration_attestation.json"
    write_json(output, report)
    return output


def verify_registration_attestation(path: Path, registration: Path, commit: str) -> dict:
    value = json.loads(path.read_text())
    required = [registration.parent / name for name in
                ("registration.json", "random_namespace.json", "source_bindings.json")]
    required.append(PROJECT / ".trellis/tasks/09-22-tf-production-gap-audit/cgr-prospective-mechanism.md")
    actual = {_portable_git_path(file): sha256(file) for file in required}
    if (value.get("schema") != SCHEMA or value.get("kind") != "registration_git_attestation" or
            value.get("registration_commit") != commit or
            value.get("registration_sha256") != sha256(registration) or
            value.get("git_blobs") != actual):
        raise ValueError("registration Git attestation/content mismatch")
    return value


def attest_prediction(protocol: Path, prediction: Path, base: Path,
                      registration_commit: str, prediction_commit: str) -> Path:
    seal = prediction / "prediction_seal.json"
    base_seal = base / "observed_seal.json"
    from common import verify_seal

    verify_seal(prediction, "prediction_seal.json")
    verify_seal(base, "observed_seal.json")
    git_ancestor(registration_commit, prediction_commit)
    git_blob(prediction_commit, git_relative(seal), seal)
    value = dict(schema=SCHEMA, kind="prediction_git_handoff",
                 registration_commit=registration_commit,
                 prediction_commit=prediction_commit,
                 prediction_seal_relative_path=seal.relative_to(PROJECT).as_posix(),
                 prediction_seal_git_path=git_relative(seal),
                 prediction_seal_sha256=sha256(seal),
                 base_seal_sha256=sha256(base_seal),
                 registration_sha256=sha256(protocol / "registration.json"))
    output = protocol / "prediction_handoff.json"
    write_json(output, value)
    return output


def verify_prediction_handoff(path: Path, protocol: Path, prediction: Path,
                              base: Path) -> dict:
    value = json.loads(path.read_text())
    if (value.get("schema") != SCHEMA or value.get("kind") != "prediction_git_handoff" or
            value.get("registration_sha256") != sha256(protocol / "registration.json") or
            value.get("prediction_seal_sha256") != sha256(prediction / "prediction_seal.json") or
            value.get("base_seal_sha256") != sha256(base / "observed_seal.json") or
            value.get("prediction_seal_relative_path") !=
            (prediction / "prediction_seal.json").relative_to(PROJECT).as_posix() or
            value.get("prediction_seal_git_path") !=
            _portable_git_path(prediction / "prediction_seal.json")):
        raise ValueError("prediction handoff differs from sealed bytes")
    return value


def attest_observed(protocol: Path, observed: Path, truth: Path, prediction: Path,
                    registration_commit: str, prediction_commit: str,
                    observed_commit: str) -> Path:
    from common import verify_seal

    verify_seal(observed, "observed_seal.json")
    verify_seal(prediction, "prediction_seal.json")
    verify_seal(truth, "truth_seal.json")
    observed_seal = observed / "observed_seal.json"
    truth_seal = truth / "truth_seal.json"
    git_ancestor(registration_commit, prediction_commit)
    git_ancestor(prediction_commit, observed_commit)
    git_blob(observed_commit, git_relative(observed_seal), observed_seal)
    git_blob(observed_commit, git_relative(truth_seal), truth_seal)
    value = dict(schema=SCHEMA, kind="observed_git_handoff",
                 registration_commit=registration_commit,
                 prediction_commit=prediction_commit,
                 observed_commit=observed_commit,
                 observed_seal_sha256=sha256(observed_seal),
                 truth_seal_sha256=sha256(truth_seal),
                 prediction_seal_sha256=sha256(prediction / "prediction_seal.json"),
                 registration_sha256=sha256(protocol / "registration.json"),
                 observed_seal_git_path=git_relative(observed_seal),
                 truth_seal_git_path=git_relative(truth_seal))
    output = protocol / "observed_handoff.json"
    write_json(output, value)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("registration")
    a.add_argument("--protocol", type=Path, required=True)
    a.add_argument("--commit", required=True)
    p = sub.add_parser("prediction")
    for name in ("protocol", "prediction", "base"):
        p.add_argument(f"--{name}", type=Path, required=True)
    p.add_argument("--registration-commit", required=True)
    p.add_argument("--prediction-commit", required=True)
    o = sub.add_parser("observed")
    for name in ("protocol", "observed", "truth", "prediction"):
        o.add_argument(f"--{name}", type=Path, required=True)
    o.add_argument("--registration-commit", required=True)
    o.add_argument("--prediction-commit", required=True)
    o.add_argument("--observed-commit", required=True)
    arguments = parser.parse_args()
    if arguments.command == "registration":
        print(attest_registration(arguments.protocol, arguments.commit))
    elif arguments.command == "prediction":
        print(attest_prediction(arguments.protocol, arguments.prediction,
                                arguments.base, arguments.registration_commit,
                                arguments.prediction_commit))
    else:
        print(attest_observed(arguments.protocol, arguments.observed, arguments.truth,
                              arguments.prediction, arguments.registration_commit,
                              arguments.prediction_commit, arguments.observed_commit))
