"""Read-only CGR mechanism analysis after an actual observed Git seal commit."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
sys.path[:0] = [str(HERE), str(EXP / "tf_production_gap_audit_20260922")]
from audit_io import attach, load_bound, sha256, write_json  # noqa: E402
from run_observed import ARMS, SCHEMA, _hash_value, schedule  # noqa: E402


def _git_seal(repository, commit, relative, seal_path):
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise ValueError("full lowercase seal commit SHA required")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe seal repository path")
    result = subprocess.run(
        ["git", "-C", str(repository), "show", f"{commit}:{path.as_posix()}"],
        capture_output=True,
        check=False,
    )
    if result.returncode or result.stdout != seal_path.read_bytes():
        raise ValueError("committed observed seal object absent or differs")
    meta = subprocess.run(
        ["git", "-C", str(repository), "show", "-s", "--format=%H", commit],
        text=True,
        capture_output=True,
        check=False,
    )
    if meta.returncode or meta.stdout.strip() != commit:
        raise ValueError("observed seal commit metadata differs")
    return dict(commit=commit, path=relative, sha256=sha256(seal_path))


def _file(entry, kind, root):
    matches = [f for f in entry["files"] if f["kind"] == kind]
    if len(matches) != 1:
        raise ValueError(f"{entry['observation_id']} lacks one {kind}")
    relative = Path(matches[0]["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe cold relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("cold artifact path escape")
    return path, matches[0]["sha256"]


def _artifact(evidence, root, relative, digest):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or sha256(path) != digest:
        raise ValueError("observed artifact hash/path differs")
    return evidence.load_artifact(path)[0]


def _summary(values):
    values = np.asarray(values, float)
    if not len(values) or not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError("invalid timing sample")
    return dict(
        n=len(values),
        mean=float(values.mean()),
        p95=float(np.percentile(values, 95)),
        maximum=float(values.max()),
    )


def _deadline_choice(checkpoints, threshold):
    ready = [cp for cp in checkpoints if cp["decision_ready_seconds"] <= threshold]
    return ready[-1] if ready else None


def _safe_output_path(args):
    out = args.out.resolve()
    for root in (args.observed.resolve(), args.witness_root.resolve()):
        if out == root or out.is_relative_to(root):
            raise ValueError(
                "analysis output cannot mutate sealed observed or cold witness roots"
            )
    if args.out.exists():
        raise FileExistsError(args.out)


def _distinct_identity(items, stem):
    entering = items[0]["entering"]
    if (
        entering is None
        or any(item["branch_detector"] is None for item in items[:3])
        or len(set(entering["delays"])) != len(entering["delays"])
    ):
        raise ValueError(
            f"distinct-delay control lacks completed distinct branch: {stem}"
        )
    result = {"observation_id": stem, "distinct_paths": len(entering["delays"])}
    for arm, item in zip(ARMS[1:3], items[1:3]):
        errors = {
            key: float(
                np.max(
                    abs(item["branch_detector"][key] - items[0]["branch_detector"][key])
                )
            )
            for key in ("extrinsic", "app", "mu", "variance", "gains")
        }
        bits_equal = bool(
            np.array_equal(item["final_decoded"], items[0]["final_decoded"])
        )
        if max(errors.values()) > 1e-9 or not bits_equal:
            raise ValueError(f"{arm} distinct-delay identity differs: {stem}")
        result[arm] = {"max_absolute_error": errors, "final_bits_equal": bits_equal}
    return result


def verify_observed(args, evidence):
    root = args.observed.resolve()
    seal_path = root / "observed_seal.json"
    seal = json.loads(seal_path.read_text())
    actual = {
        str(p.relative_to(root)): sha256(p)
        for p in root.rglob("*")
        if p.is_file() and p.name != "observed_seal.json"
    }
    if (
        seal.get("schema") != SCHEMA
        or seal.get("status") != "pass"
        or seal.get("completed_calls") != 100
        or seal.get("files") != actual
    ):
        raise ValueError("complete observed seal inventory differs")
    manifest = json.loads((root / "manifest.json").read_text())
    witness = json.loads(args.witness_manifest.read_text())
    if (
        manifest.get("registration_sha256") != sha256(args.registration)
        or manifest.get("witness_manifest_sha256") != sha256(args.witness_manifest)
        or manifest.get("qualification_sha256") != sha256(args.qualification)
        or manifest.get("source_bindings_sha256") != sha256(args.source_bindings)
        or manifest.get("expected_calls") != 100
        or seal.get("source_bindings_sha256") != sha256(args.source_bindings)
    ):
        raise ValueError("observed registration/source/witness link differs")
    entries = witness["entries"]
    expected = schedule(entries)
    rows = [
        json.loads(line) for line in (root / "ledger.jsonl").read_text().splitlines()
    ]
    if len(rows) != 100 or [(r["observation_id"], r["arm"]) for r in rows] != [
        (entry["observation_id"], arm) for entry, arm in expected
    ]:
        raise ValueError("observed 100-call allocation differs")
    git = _git_seal(args.evidence_git, args.seal_commit, args.seal_repo_path, seal_path)
    raw_by = {}
    historical = []
    distinct = []
    for row in rows:
        if row["status"] != "ok" or not row["receiver_started"]:
            raise ValueError("incomplete observed wrapper")
        if row["complete_latency_seconds"] < row["final_decision_ready_seconds"]:
            raise ValueError("decision later than complete wrapper")
        if (
            row["triggered"]
            and row["numerical_failure"] is None
            and len(row["checkpoints"]) != 3
        ):
            raise ValueError("triggered final checkpoint absent")
        if not row["triggered"] and len(row["checkpoints"]) != 2:
            raise ValueError("nontriggered checkpoint count differs")
        if row["triggered"] and (
            row["branch_complete_seconds"] <= 0
            or row["branch_complete_seconds"] < row["branch_elapsed_seconds"]
        ):
            raise ValueError("branch complete cost omits charged work")
        raw = _artifact(evidence, root, row["raw_path"], row["raw_sha256"])
        bits = np.asarray(raw["final_decoded"])
        if hashlib.sha256(bits.tobytes()).hexdigest() != row["final_decoded_sha256"]:
            raise ValueError("saved final bits differ from ledger")
        if not np.array_equal(
            bits,
            raw["native_decoder"]["decoded"]
            if raw["branch_decoder"] is None
            else raw["branch_decoder"]["decoded"],
        ):
            raise ValueError("final output selects a different checkpoint")
        decision_path = root / row["decision_path"]
        if sha256(decision_path) != row["decision_sha256"]:
            raise ValueError("decision JSON SHA differs")
        decision = json.loads(decision_path.read_text())
        if (
            decision["final_decoded_sha256"] != row["final_decoded_sha256"]
            or decision["raw_sha256"] != row["raw_sha256"]
            or decision["entering_sha256"] != row["entering_sha256"]
        ):
            raise ValueError("decision/ledger identity differs")
        for cp in row["checkpoints"]:
            payload = _artifact(evidence, root, cp["path"], cp["artifact_sha256"])
            if not np.array_equal(
                payload["decoded"], payload["event"]["snapshot"]["decoded"]
            ):
                raise ValueError("checkpoint bits/snapshot differ")
            if cp["decision_ready_seconds"] > cp["artifact_ready_seconds"]:
                raise ValueError("checkpoint available before decision")
        if (
            raw["entering"] is not None
            and _hash_value(raw["entering"]) != row["entering_sha256"]
        ):
            raise ValueError("post-refit entering hash differs")
        raw_by[(row["observation_id"], row["arm"])] = raw
    for entry in entries:
        stem = entry["observation_id"]
        items = [raw_by[(stem, arm)] for arm in ARMS]
        prefix = [_hash_value(item["native_arrays"]) for item in items]
        if len(set(prefix)) != 1:
            raise ValueError(f"four-arm native prefix differs: {stem}")
        enter = [
            None if item["entering"] is None else _hash_value(item["entering"])
            for item in items
        ]
        if len(set(enter)) != 1:
            raise ValueError(f"four-arm post-refit entering state differs: {stem}")
        path, digest = _file(entry, "trace", args.witness_root)
        old = load_bound(evidence, path, digest)
        for round_index in (0, 1):
            if not np.array_equal(
                items[0]["native_arrays"][f"r{round_index}_decoded"],
                old["baseline_arrays"][f"r{round_index}_decoded"],
            ):
                raise ValueError(f"new prefix differs from historical TF bits: {stem}")
        old_final = old["native_decoder"]["decoded"]
        if items[0]["branch_decoder"] is not None:
            path, digest = _file(entry, "landscape", args.witness_root)
            landscape = load_bound(evidence, path, digest)
            old_final = landscape["branch_decoder"]["decoded"]
        if not np.array_equal(items[0]["final_decoded"], old_final):
            raise ValueError(f"BASE differs from historical preserved result: {stem}")
        historical.append(stem)
        if entry["role"] == "distinct_delay_failure_specificity":
            distinct.append(_distinct_identity(items, stem))
    if len(distinct) != 3:
        raise ValueError("three fixed distinct-delay controls absent")
    return dict(
        git=git,
        rows=rows,
        raw_by=raw_by,
        entries=entries,
        historical_base_bits_matched=len(historical),
        distinct_delay_identity=distinct,
    )


def _code(args, registration):
    path = (
        args.baseline
        / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
    )
    manifest = json.loads((args.observed / "manifest.json").read_text())
    if sha256(path) != manifest["source_hashes"]["code_cache"]:
        raise ValueError("actual H/G/free code cache bytes differ from sealed producer")
    with np.load(path, allow_pickle=False) as saved:
        H = np.asarray(saved["H"]).astype(np.int32)
        G = np.asarray(saved["G"])
        free = np.asarray(saved["free_cols"])
    if (
        H.shape != (1026, 2048)
        or G.shape != (2048, 1024)
        or free.shape != (1024,)
        or hashlib.sha256(np.ascontiguousarray(G).tobytes()).hexdigest()
        != manifest["code_g_sha256"]
    ):
        raise ValueError("actual code H/G/free identity differs")
    return H, free


def _recount(bits, truth, H, free):
    coded = np.asarray(truth["coded"])
    info = np.asarray(truth["info"])
    bits = np.asarray(bits)
    if (
        bits.shape != (2048,)
        or coded.shape != (2048,)
        or info.shape != (1024,)
        or not np.isin(bits, [0, 1]).all()
        or not np.isin(coded, [0, 1]).all()
        or not np.isin(info, [0, 1]).all()
        or not np.array_equal(coded[free], info)
    ):
        raise ValueError("invalid exact H/G/free bit recount")
    bits = bits.astype(np.int32)
    return dict(
        info_errors=int(np.count_nonzero(bits[free] != info)),
        coded_errors=int(np.count_nonzero(bits != coded)),
        syndrome_weight=int(np.count_nonzero((H @ bits) % 2)),
    )


def _physical_error(paths, gains, truth, n, c1, c2):
    from physical import Channel
    from twofft import TimePathOps

    delay = np.concatenate((np.asarray(paths["delays"]), truth["l_i"]))
    doppler = np.concatenate((np.asarray(paths["dopplers"]), truth["k_real"]))
    h = np.concatenate((np.asarray(gains), -truth["g_i"]))
    channel = Channel(n, c1, c2, delay, doppler, h)
    R = TimePathOps(channel).R
    energy = float(n * np.vdot(h, R @ h).real)
    if not np.isfinite(energy) or energy < -1e-8:
        raise ValueError("nonfinite or negative physical mismatch")
    return max(0.0, energy)


def _projection(paths, truth, n, c1, c2):
    from physical import Channel
    from twofft import TimePathOps

    delays = np.concatenate((paths["delays"], truth["l_i"]))
    nu = np.concatenate((paths["dopplers"], truth["k_real"]))
    path_ops = TimePathOps(Channel(n, c1, c2, delays, nu, np.ones(len(delays))))
    R = path_ops.R
    P = len(paths["delays"])
    F = R[:P, :P]
    cross = R[:P, P:] @ truth["g_i"]
    # Equal-delay path operators share the same cyclic support; distinct delays
    # are Frobenius-orthogonal. Solve each actual N x P modulation block by SVD.
    phase = path_ops.phase
    groups = []
    for delay in np.unique(delays):
        estimated = np.flatnonzero(delays[:P] == delay)
        actual = P + np.flatnonzero(delays[P:] == delay)
        target = (
            phase[:, actual] @ truth["g_i"][actual - P]
            if len(actual)
            else np.zeros(n, complex)
        )
        groups.append((int(delay), estimated, phase[:, estimated], target))
    optimal = np.zeros(P, complex)
    singular_values = {}
    operator_ranks = {}
    for delay, estimated, matrix, target in groups:
        if len(estimated):
            optimal[estimated], _, rank, values = np.linalg.lstsq(
                matrix, target, rcond=1e-12
            )
            singular_values[str(delay)] = values.tolist()
            operator_ranks[str(delay)] = int(rank)

    def fitted_error(gains):
        return float(
            sum(
                np.linalg.norm(matrix @ gains[estimated] - target) ** 2
                for _, estimated, matrix, target in groups
            )
        )

    fitted_residual = fitted_error(optimal)
    eigenvalues = np.linalg.eigvalsh(F)
    if not np.isfinite(eigenvalues).all() or eigenvalues.min() < -1e-10:
        raise ValueError("selected physical Gram is not PSD")
    true_energy = float(n * np.vdot(truth["g_i"], R[P:, P:] @ truth["g_i"]).real)
    projected = float(n * np.vdot(cross, optimal).real)
    subtraction_residual = true_energy - projected
    stationarity = float(np.linalg.norm(F @ optimal - cross))
    if not np.isfinite(stationarity):
        raise ValueError("selected physical LS normal residual is nonfinite")
    # Independent Gram evaluations expose cancellation from large gain coordinates.
    signed = np.concatenate((optimal, -truth["g_i"]))
    quadratic_residual = float(n * np.vdot(signed, R @ signed).real)
    if not np.isfinite(fitted_residual) or fitted_residual < 0:
        raise ValueError("nonfinite selected physical fitted residual")
    sensitive = np.linalg.pinv(F, hermitian=True, rcond=1e-10) @ cross
    sensitive_residual = fitted_error(sensitive)
    positive = eigenvalues[
        eigenvalues > np.finfo(float).eps * P * max(1.0, float(eigenvalues.max()))
    ]
    return dict(
        optimal_gains=optimal,
        operator_frobenius_squared=fitted_residual,
        subtraction_residual=subtraction_residual,
        quadratic_residual=quadratic_residual,
        subtraction_minus_fitted=float(subtraction_residual - fitted_residual),
        ls_normal_residual=stationarity,
        gram_rank=int(len(positive)),
        gram_eigenvalues=eigenvalues.tolist(),
        operator_singular_values_by_delay=singular_values,
        operator_ranks_by_delay=operator_ranks,
        gain_coordinates_identifiable=all(
            operator_ranks[str(delay)] == len(estimated)
            for delay, estimated, _, _ in groups
            if len(estimated)
        ),
        gram_condition=float(positive.max() / positive.min())
        if len(positive)
        else None,
        coefficient_rcond_sensitivity=float(np.linalg.norm(sensitive - optimal)),
        physical_residual_rcond_sensitivity=float(
            abs(sensitive_residual - fitted_residual)
        ),
    )


def _working_moment(paths, v_pre, vx, n, c1, c2):
    from physical import projected_variance
    from twofft import TimePathOps
    from physical import Channel

    delay = np.asarray(paths["delays"])
    doppler = np.asarray(paths["dopplers"])
    gamma = projected_variance(v_pre, delay, doppler, c1)
    R = TimePathOps(Channel(n, c1, c2, delay, doppler, np.ones(len(delay)))).R
    same = delay[:, None] == delay[None, :]
    expected = n * vx * R
    error = gamma[same] - expected[same]
    return dict(
        same_delay_max_absolute_error=float(np.max(abs(error))),
        same_delay_relative_error=float(
            np.linalg.norm(error) / max(1.0, np.linalg.norm(expected[same]))
        ),
        same_delay_gamma_norm=float(np.linalg.norm(gamma[same])),
        same_delay_nvx_r_norm=float(np.linalg.norm(expected[same])),
        same_delay_gamma_to_nvx_r_ratio=float(
            np.linalg.norm(gamma[same]) / np.linalg.norm(expected[same])
        )
        if np.linalg.norm(expected[same]) > 0
        else None,
    )


def _paired_summary(entries, by):
    outcomes = {}
    for left in ARMS:
        outcomes[left] = {}
        for right in ARMS:
            counts = {
                "both_correct": 0,
                "left_only": 0,
                "right_only": 0,
                "neither_correct": 0,
            }
            for entry in entries:
                stem = entry["observation_id"]
                a = by[(stem, left)]["correct"]
                b = by[(stem, right)]["correct"]
                key = (
                    "both_correct"
                    if a and b
                    else "left_only"
                    if a
                    else "right_only"
                    if b
                    else "neither_correct"
                )
                counts[key] += 1
            outcomes[left][right] = counts
    changes = {}
    for arm in ARMS:
        changes[arm] = dict(
            rescues=[
                e["observation_id"]
                for e in entries
                if not by[(e["observation_id"], "BASE")]["correct"]
                and by[(e["observation_id"], arm)]["correct"]
            ],
            harms=[
                e["observation_id"]
                for e in entries
                if by[(e["observation_id"], "BASE")]["correct"]
                and not by[(e["observation_id"], arm)]["correct"]
            ],
            valid_but_wrong=[
                e["observation_id"]
                for e in entries
                if by[(e["observation_id"], arm)]["valid_but_wrong"]
            ],
        )
    return outcomes, changes


def _assert_base_cohort(entries, by):
    expected = {
        "target_remaining_failure": (8, False),
        "matched_rescued_control": (7, True),
        "matched_easy_control": (7, True),
        "distinct_delay_failure_specificity": (3, False),
    }
    if Counter(e["role"] for e in entries) != Counter(
        {role: count for role, (count, _) in expected.items()}
    ):
        raise ValueError("fixed diagnostic cohort roles/counts differ")
    if any(
        by[(e["observation_id"], "BASE")]["correct"] != expected[e["role"]][1]
        for e in entries
    ):
        raise ValueError("BASE exact outcomes differ from fixed diagnostic cohort")


def _directional_support(trace, rescues):
    """Conservative, fixed sign-pattern interpretation; mixed trajectories are inconclusive."""
    evidence = []
    for stem in rescues:
        base = sorted(
            (x for x in trace if x["observation_id"] == stem and x["arm"] == "BASE"),
            key=lambda x: x["iteration"],
        )
        cgr = sorted(
            (x for x in trace if x["observation_id"] == stem and x["arm"] == "CGR"),
            key=lambda x: x["iteration"],
        )
        if len(base) != 20 or len(cgr) != 20:
            raise ValueError("physical directional trace lacks 20 matched iterations")
        effects = [x["signed_common_state_physical_effect"] for x in base]
        terminal_delta = (
            base[-1]["operator_frobenius_squared"]
            - cgr[-1]["operator_frobenius_squared"]
        )
        evidence.append(
            dict(
                observation_id=stem,
                signed_effects=effects,
                effect_sum=float(sum(effects)),
                negative_iterations=sum(x < 0 for x in effects),
                positive_iterations=sum(x > 0 for x in effects),
                terminal_base_minus_cgr_physical_mismatch=float(terminal_delta),
                common_dh_norm_squared=[
                    x["predicted_dh_physical_norm_squared"] for x in base
                ],
            )
        )
    if not evidence:
        return "inconclusive", evidence
    if all(
        x["negative_iterations"] == 0
        and x["positive_iterations"] > 0
        and x["terminal_base_minus_cgr_physical_mismatch"] > 0
        for x in evidence
    ):
        return "qualified_support", evidence
    if all(
        x["positive_iterations"] == 0
        and x["terminal_base_minus_cgr_physical_mismatch"] <= 0
        for x in evidence
    ):
        return "lack_of_support", evidence
    return "inconclusive", evidence


def _engineering_gates(
    cgr_rescue,
    cgr_harm,
    new_valid_wrong,
    distinct_count,
    target_correct,
    physical_support,
    branch,
):
    return dict(
        target_rescue_and_harm=len(cgr_rescue) >= 2
        and not cgr_harm
        and not new_valid_wrong,
        distinct_delay_identity=distinct_count == 3,
        aligned_exceeds_sham_and_physical_support=target_correct["CGR"]
        >= target_correct["SHAM"] + 1
        and physical_support == "qualified_support",
        added_branch_mean=branch["CGR"]["mean"] <= 1.10 * branch["BASE"]["mean"],
        block_not_two_better=target_correct["BLOCK"] - target_correct["CGR"] < 2,
    )


def analyze(args):
    _safe_output_path(args)
    evidence = attach(args.source, args.baseline)
    observed = verify_observed(args, evidence)  # No truth has been opened yet.
    registration = json.loads(args.registration.read_text())
    H, free = _code(args, registration)
    failed = json.loads(args.failed_attempt_receipt.read_text())
    if (
        failed.get("schema") != "tf-cgr-failed-attempt/1"
        or failed.get("attempts") != 1
        or failed.get("complete_wrappers") != 0
        or len(failed.get("checkpoints", [])) != 3
        or failed.get("raw_artifact_available") is not False
        or failed.get("observed_seal_available") is not False
    ):
        raise ValueError("preserved first failed attempt receipt differs")
    args.out.mkdir(parents=True)
    rows = []
    trace = []
    projection = []
    deadline = []
    working_moments = []
    truth_by = {}
    for entry in observed["entries"]:
        path, digest = _file(entry, "truth", args.witness_root)
        truth_by[entry["observation_id"]] = load_bound(evidence, path, digest)
    for row in observed["rows"]:
        stem = row["observation_id"]
        arm = row["arm"]
        raw = observed["raw_by"][(stem, arm)]
        truth = truth_by[stem]
        counted = _recount(raw["final_decoded"], truth, H, free)
        counted.update(
            observation_id=stem,
            role=row["role"],
            arm=arm,
            correct=counted["info_errors"] == 0,
            valid_but_wrong=counted["syndrome_weight"] == 0
            and counted["info_errors"] > 0,
            triggered=row["triggered"],
            numerical_failure=row["numerical_failure"],
            complete_latency_seconds=row["complete_latency_seconds"],
            branch_complete_seconds=row["branch_complete_seconds"],
            final_decision_ready_seconds=row["final_decision_ready_seconds"],
        )
        rows.append(counted)
        for threshold in (0.5, 1.0):
            cp = _deadline_choice(row["checkpoints"], threshold)
            if cp is not None:
                payload = _artifact(
                    evidence, args.observed, cp["path"], cp["artifact_sha256"]
                )
                result = _recount(payload["decoded"], truth, H, free)
                deadline.append(
                    dict(
                        observation_id=stem,
                        arm=arm,
                        seconds=threshold,
                        available=True,
                        correct=result["info_errors"] == 0,
                        ready_seconds=cp["decision_ready_seconds"],
                        round=cp["round"],
                    )
                )
            else:
                deadline.append(
                    dict(
                        observation_id=stem,
                        arm=arm,
                        seconds=threshold,
                        available=False,
                        correct=False,
                        ready_seconds=None,
                        round=None,
                    )
                )
        if not row["triggered"] or raw["branch_detector"] is None:
            continue
        paths = raw["entering"]
        n = 1024
        # Source-bound context parameters are recorded in the historical observation metadata.
        c1 = 3.7 / (2 * n)
        c2 = 0.017
        projected = _projection(paths, truth, n, c1, c2)
        projection.append(
            dict(
                observation_id=stem,
                arm=arm,
                operator_frobenius_squared=projected["operator_frobenius_squared"],
                subtraction_residual=projected["subtraction_residual"],
                quadratic_residual=projected["quadratic_residual"],
                subtraction_minus_fitted=projected["subtraction_minus_fitted"],
                ls_normal_residual=projected["ls_normal_residual"],
                gram_rank=projected["gram_rank"],
                gram_eigenvalues=projected["gram_eigenvalues"],
                gram_condition=projected["gram_condition"],
                operator_singular_values_by_delay=projected[
                    "operator_singular_values_by_delay"
                ],
                operator_ranks_by_delay=projected["operator_ranks_by_delay"],
                gain_coordinates_identifiable=projected[
                    "gain_coordinates_identifiable"
                ],
                coefficient_rcond_sensitivity=projected[
                    "coefficient_rcond_sensitivity"
                ],
                physical_residual_rcond_sensitivity=projected[
                    "physical_residual_rcond_sensitivity"
                ],
            )
        )
        if row["role"] == "target_remaining_failure":
            from messages import moments

            _, v_pre, _ = moments(paths["check"], 0.5)
        for it, state in enumerate(raw["branch_detector"]["states"]):
            h = np.asarray(state["h"])
            mismatch = _physical_error(paths, h, truth, n, c1, c2)
            item = dict(
                observation_id=stem,
                arm=arm,
                iteration=it,
                operator_frobenius_squared=mismatch,
            )
            if arm == "BASE":
                common = raw["base_common_state"][it]
                with_dh = _physical_error(paths, h + common["dh"], truth, n, c1, c2)
                item.update(
                    predicted_dh_physical_norm_squared=common["physical_norm_squared"],
                    signed_common_state_physical_effect=mismatch - with_dh,
                    reciprocal_precision=common["reciprocal_precision"],
                )
            trace.append(item)
            if row["role"] == "target_remaining_failure":
                moment = _working_moment(paths, v_pre, float(np.mean(v_pre)), n, c1, c2)
                working_moments.append(
                    dict(observation_id=stem, arm=arm, iteration=it, **moment)
                )
                v_pre = np.asarray(state["v"])
    by = {(r["observation_id"], r["arm"]): r for r in rows}
    _assert_base_cohort(observed["entries"], by)
    targets = [
        e["observation_id"]
        for e in observed["entries"]
        if e["role"] == "target_remaining_failure"
    ]
    rescued = [
        e["observation_id"]
        for e in observed["entries"]
        if e["role"] == "matched_rescued_control"
    ]
    cgr_rescue = [
        stem
        for stem in targets
        if not by[(stem, "BASE")]["correct"] and by[(stem, "CGR")]["correct"]
    ]
    cgr_harm = [
        stem
        for stem in rescued
        if by[(stem, "BASE")]["correct"] and not by[(stem, "CGR")]["correct"]
    ]
    new_valid_wrong = [
        stem
        for stem in (e["observation_id"] for e in observed["entries"])
        if by[(stem, "CGR")]["valid_but_wrong"]
        and not by[(stem, "BASE")]["valid_but_wrong"]
    ]
    triggered = [
        e["observation_id"]
        for e in observed["entries"]
        if by[(e["observation_id"], "BASE")]["triggered"]
    ]
    branch = {
        arm: _summary(
            [by[(stem, arm)]["branch_complete_seconds"] for stem in triggered]
        )
        for arm in ARMS
    }
    target_correct = {
        arm: sum(by[(stem, arm)]["correct"] for stem in targets) for arm in ARMS
    }
    physical_support, directional_evidence = _directional_support(trace, cgr_rescue)
    gates = _engineering_gates(
        cgr_rescue,
        cgr_harm,
        new_valid_wrong,
        len(observed["distinct_delay_identity"]),
        target_correct,
        physical_support,
        branch,
    )
    complete = {
        arm: _summary([r["complete_latency_seconds"] for r in rows if r["arm"] == arm])
        for arm in ARMS
    }
    overlaps, changes = _paired_summary(observed["entries"], by)
    deadline_summary = {
        str(t): {
            arm: dict(
                n=25,
                correct=sum(
                    x["correct"]
                    for x in deadline
                    if x["seconds"] == t and x["arm"] == arm
                ),
                wrong_ready=sum(
                    x["available"] and not x["correct"]
                    for x in deadline
                    if x["seconds"] == t and x["arm"] == arm
                ),
                missing=sum(
                    not x["available"]
                    for x in deadline
                    if x["seconds"] == t and x["arm"] == arm
                ),
            )
            for arm in ARMS
        }
        for t in (0.5, 1.0)
    }
    if any(
        sum(v[key] for key in ("correct", "wrong_ready", "missing")) != 25
        for per_arm in deadline_summary.values()
        for v in per_arm.values()
    ):
        raise ValueError("deadline summary omits paired observations")
    report = dict(
        schema="tf-cgr-analysis/1",
        status="complete",
        seal_git=observed["git"],
        historical_base_bits_matched=observed["historical_base_bits_matched"],
        paired_calls=len(rows),
        total_attempted_calls=len(rows) + failed["attempts"],
        preserved_failed_attempt=dict(
            receipt_sha256=sha256(args.failed_attempt_receipt),
            attempts=failed["attempts"],
            complete_wrappers=failed["complete_wrappers"],
            elapsed_seconds=failed["elapsed_seconds"],
            checkpoints=failed["checkpoints"],
            raw_artifact_available=failed["raw_artifact_available"],
        ),
        distinct_delay_identity=observed["distinct_delay_identity"],
        target_correct=target_correct,
        cgr_rescues=cgr_rescue,
        rescued_control_harms=cgr_harm,
        new_valid_but_wrong=new_valid_wrong,
        gates=gates,
        candidate_pass=all(gates.values()),
        complete_times=complete,
        triggered_branch_times=branch,
        paired_outcomes=overlaps,
        arm_changes_from_base=changes,
        deadline=deadline_summary,
        physical_support=physical_support,
        directional_evidence=directional_evidence,
    )
    write_json(args.out / "report.json", report)
    for name, data in (
        ("decisions.json", rows),
        ("physical_trace.json", trace),
        ("projection.json", projection),
        ("working_moments.json", working_moments),
        ("deadline.json", deadline),
    ):
        write_json(args.out / name, data)
    print(
        json.dumps(
            dict(
                status="complete",
                candidate_pass=report["candidate_pass"],
                gates=gates,
                target_correct=target_correct,
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for key in (
        "observed",
        "witness-root",
        "witness-manifest",
        "source",
        "baseline",
        "registration",
        "qualification",
        "source-bindings",
        "evidence-git",
        "out",
    ):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--seal-commit", required=True)
    parser.add_argument("--seal-repo-path", required=True)
    parser.add_argument("--failed-attempt-receipt", type=Path, required=True)
    analyze(parser.parse_args())
