"""Synthetic-only checks for the sealed-output CGR analyzer; no cold truth is opened."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [
    str(HERE),
    str(ROOT / "experiments/sp_afdm_frozen_20260920/src"),
    str(ROOT / "experiments/sp_afdm_native_joint_20260921/src"),
]
import analyze  # noqa: E402


def check_git_and_paths():
    with TemporaryDirectory() as temp:
        root = Path(temp)
        repo = root / "repo"
        repo.mkdir()
        seal = repo / "observed_seal.json"
        seal.write_text('{"status":"pass"}\n')
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "add", "observed_seal.json"], check=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "seal",
            ],
            check=True,
        )
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()
        assert (
            analyze._git_seal(repo, commit, "observed_seal.json", seal)["commit"]
            == commit
        )
        seal.write_text('{"status":"altered"}\n')
        try:
            analyze._git_seal(repo, commit, "observed_seal.json", seal)
        except ValueError:
            pass
        else:
            raise AssertionError("mismatched seal accepted")
        for bad in ("0" * 40, commit[:-1]):
            try:
                analyze._git_seal(repo, bad, "observed_seal.json", seal)
            except ValueError:
                pass
            else:
                raise AssertionError("missing/short seal commit accepted")
        observed = root / "observed"
        witness = root / "witness"
        observed.mkdir()
        witness.mkdir()
        for out in (observed / "analysis", witness / "analysis"):
            try:
                analyze._safe_output_path(
                    SimpleNamespace(out=out, observed=observed, witness_root=witness)
                )
            except ValueError:
                pass
            else:
                raise AssertionError("sealed input subtree accepted as output")
        analyze._safe_output_path(
            SimpleNamespace(
                out=root / "analysis", observed=observed, witness_root=witness
            )
        )


def check_code_and_recount():
    with TemporaryDirectory() as temp:
        root = Path(temp)
        baseline = root / "baseline"
        observed = root / "observed"
        observed.mkdir()
        cache = (
            baseline
            / "upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc_code_n2048_dv3_dc6_seed20260726.npz"
        )
        cache.parent.mkdir(parents=True)
        H = np.zeros((1026, 2048), dtype=np.uint8)
        G = np.zeros((2048, 1024), dtype=np.uint8)
        free = np.arange(2047, 1023, -1, dtype=np.int32)
        np.savez_compressed(cache, H=H, G=G, free_cols=free)

        def sha(p):
            return hashlib.sha256(p.read_bytes()).hexdigest()

        (observed / "manifest.json").write_text(
            json.dumps(
                dict(
                    source_hashes={"code_cache": sha(cache)},
                    code_g_sha256=hashlib.sha256(
                        np.ascontiguousarray(G).tobytes()
                    ).hexdigest(),
                )
            )
        )
        args = SimpleNamespace(baseline=baseline, observed=observed)
        actual_H, actual_free = analyze._code(args, {})
        assert np.array_equal(actual_H, H) and np.array_equal(actual_free, free)
        truth = {
            "coded": np.zeros(2048, dtype=np.uint8),
            "info": np.zeros(1024, dtype=np.uint8),
        }
        wrong = truth["coded"].copy()
        wrong[free[17]] = 1
        result = analyze._recount(wrong, truth, actual_H, actual_free)
        assert result == {"info_errors": 1, "coded_errors": 1, "syndrome_weight": 0}
        broken = {"coded": truth["coded"].copy(), "info": truth["info"].copy()}
        broken["info"][17] = 1
        try:
            analyze._recount(wrong, broken, actual_H, actual_free)
        except ValueError:
            pass
        else:
            raise AssertionError("coded/free/info inconsistency accepted")
        with np.load(cache, allow_pickle=False) as saved:
            np.savez_compressed(
                cache,
                H=np.asarray(saved["H"]),
                G=np.asarray(saved["G"]),
                free_cols=np.arange(1024, dtype=np.int32),
            )
        try:
            analyze._code(args, {})
        except ValueError:
            pass
        else:
            raise AssertionError("changed code cache with same G accepted")


def check_projection_and_moments():
    from physical import Channel

    n = 32
    c1 = 3.7 / (2 * n)
    c2 = 0.017
    truth = {
        "l_i": np.array([2, 5]),
        "k_real": np.array([0.38, -0.15]),
        "g_i": np.array([0.7 + 0.2j, -0.3 + 0.1j]),
    }
    for separation in (0.0, 1e-5, 0.1):
        selected = {
            "delays": np.array([2, 2, 5]),
            "dopplers": np.array([0.3, 0.3 + separation, -0.2]),
        }
        fit = analyze._projection(selected, truth, n, c1, c2)
        assert fit["operator_frobenius_squared"] >= 0
        assert fit["physical_residual_rcond_sensitivity"] >= 0
        assert np.isfinite(fit["ls_normal_residual"])
        selected_ops = []
        true_signal = np.zeros(n * n, complex)
        eye = np.eye(n, dtype=complex)
        for delay, nu in zip(selected["delays"], selected["dopplers"]):
            channel = Channel(n, c1, c2, [delay], [nu], [1])
            selected_ops.append(
                np.column_stack([channel.apply(eye[:, j]) for j in range(n)]).ravel()
            )
        for delay, nu, gain in zip(truth["l_i"], truth["k_real"], truth["g_i"]):
            channel = Channel(n, c1, c2, [delay], [nu], [gain])
            true_signal += np.column_stack(
                [channel.apply(eye[:, j]) for j in range(n)]
            ).ravel()
        matrix = np.column_stack(selected_ops)
        dense_gains = np.linalg.lstsq(matrix, true_signal, rcond=1e-10)[0]
        dense_residual = float(np.linalg.norm(matrix @ dense_gains - true_signal) ** 2)
        assert np.isclose(
            fit["operator_frobenius_squared"], dense_residual, rtol=1e-9, atol=1e-9
        )
        if separation == 1e-5:
            assert fit["coefficient_rcond_sensitivity"] > 0
        variance = np.linspace(0.1, 0.7, n)
        moment = analyze._working_moment(
            selected, variance, float(variance.mean()), n, c1, c2
        )
        assert moment["same_delay_max_absolute_error"] < 1e-8


def check_pairs_deadlines_and_gates():
    roles = (
        ["target_remaining_failure"] * 8
        + ["matched_rescued_control"] * 7
        + ["matched_easy_control"] * 7
        + ["distinct_delay_failure_specificity"] * 3
    )
    cohort = [{"observation_id": f"c{i}", "role": role} for i, role in enumerate(roles)]
    cohort_by = {
        (entry["observation_id"], "BASE"): {
            "correct": entry["role"]
            in ("matched_rescued_control", "matched_easy_control")
        }
        for entry in cohort
    }
    analyze._assert_base_cohort(cohort, cohort_by)
    cohort_by[("c0", "BASE")]["correct"] = True
    try:
        analyze._assert_base_cohort(cohort, cohort_by)
    except ValueError:
        pass
    else:
        raise AssertionError("historical cohort drift accepted")
    detector = {
        key: np.zeros(2) for key in ("extrinsic", "app", "mu", "variance", "gains")
    }
    items = [
        dict(
            entering={"delays": np.array([2, 5])},
            branch_detector=detector,
            final_decoded=np.zeros(2, dtype=np.uint8),
        )
        for _ in analyze.ARMS
    ]
    assert analyze._distinct_identity(items, "distinct")["CGR"]["final_bits_equal"]
    items[1] = {**items[1], "branch_detector": None}
    try:
        analyze._distinct_identity(items, "distinct")
    except ValueError:
        pass
    else:
        raise AssertionError("missing distinct-delay CGR branch accepted")
    entries = [{"observation_id": f"f{i}"} for i in range(4)]
    outcomes = {
        "BASE": [False, True, True, False],
        "CGR": [True, True, False, False],
        "SHAM": [False, True, True, False],
        "BLOCK": [True, False, True, False],
    }
    by = {
        (f"f{i}", arm): {"correct": value, "valid_but_wrong": i == 3 and arm == "BLOCK"}
        for arm, values in outcomes.items()
        for i, value in enumerate(values)
    }
    pair, changes = analyze._paired_summary(entries, by)
    assert pair["BASE"]["CGR"] == {
        "both_correct": 1,
        "left_only": 1,
        "right_only": 1,
        "neither_correct": 1,
    }
    assert changes["CGR"]["rescues"] == ["f0"] and changes["CGR"]["harms"] == ["f2"]
    assert changes["BLOCK"]["valid_but_wrong"] == ["f3"]
    for arm in analyze.ARMS:
        checkpoints = [
            {"round": 0, "decision_ready_seconds": 0.2, "arm": arm},
            {"round": 1, "decision_ready_seconds": 0.8, "arm": arm},
            {"round": 2, "decision_ready_seconds": 1.2, "arm": arm},
        ]
        assert analyze._deadline_choice(checkpoints, 0.5)["round"] == 0
        assert analyze._deadline_choice(checkpoints, 1.0)["round"] == 1
        assert analyze._deadline_choice(checkpoints, 0.1) is None
    branch = {arm: {"mean": 1.0} for arm in analyze.ARMS}
    target = {"CGR": 3, "SHAM": 2, "BLOCK": 4, "BASE": 0}
    good = analyze._engineering_gates(
        ["a", "b"], [], [], 3, target, "qualified_support", branch
    )
    assert len(good) == 5 and all(good.values())
    cases = [
        (["a"], [], [], 3, target, "qualified_support", branch),
        (["a", "b"], [], [], 2, target, "qualified_support", branch),
        (["a", "b"], [], [], 3, target, "inconclusive", branch),
        (
            ["a", "b"],
            [],
            [],
            3,
            target,
            "qualified_support",
            {**branch, "CGR": {"mean": 1.11}},
        ),
        (["a", "b"], [], [], 3, {**target, "BLOCK": 5}, "qualified_support", branch),
    ]
    for index, case in enumerate(cases):
        result = analyze._engineering_gates(*case)
        assert sum(not value for value in result.values()) == 1, (index, result)
    trace = []
    for arm in ("BASE", "CGR"):
        for iteration in range(20):
            trace.append(
                dict(
                    observation_id="a",
                    arm=arm,
                    iteration=iteration,
                    operator_frobenius_squared=2.0 if arm == "BASE" else 1.0,
                    signed_common_state_physical_effect=1.0 if arm == "BASE" else 0.0,
                    predicted_dh_physical_norm_squared=0.1,
                )
            )
    status, all_trace = analyze._directional_support(trace, ["a"])
    assert status == "qualified_support" and len(all_trace[0]["signed_effects"]) == 20
    trace[0]["signed_common_state_physical_effect"] = -0.1
    assert analyze._directional_support(trace, ["a"])[0] == "inconclusive"


if __name__ == "__main__":
    check_git_and_paths()
    check_code_and_recount()
    check_projection_and_moments()
    check_pairs_deadlines_and_gates()
    print("synthetic analyzer checks: pass")
