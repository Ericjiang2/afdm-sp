"""Deterministic small-operator identities; never calls a receiver or decoder."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PHYSICAL = ROOT / "experiments/sp_afdm_frozen_20260920/src/physical.py"
TWOOFFT = ROOT / "experiments/sp_afdm_native_joint_20260921/src/twofft.py"
BASE = ROOT / "experiments/tf_cgr_mechanism_20260923_v2/tf_base.py"
EXPECTED = {
    "physical.py": "c0398247b59d10366a0602a3bf115271e57d339e5a783691dd703e4da02348c6",
    "twofft.py": "c54e832716d72530e38a9b1090ca24f8f8b3c8f4185db0914d30e5f7e2ab9ff0",
    "tf_base.py": "0e3a94045b0b395c28efa02f181433bbc3aa2f569c05683ad83e1d1cf4f9699e",
}
SEEDS = (0, 7, 23)
N = 31  # Odd N makes the design chirp's CPP wrap phase nontrivial (-1).
ATOL = 1e-10
RTOL = 1e-10


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_operators(n: int, delays: np.ndarray, dopplers: np.ndarray,
                          c1: float, c2: float) -> list[np.ndarray]:
    """Dense AF operator from the declared chirps, FFT sign, CPP and cyclic delay."""
    k = np.arange(n)
    fourier = np.exp(-2j * np.pi * np.outer(k, k) / n) / np.sqrt(n)
    transform = (np.exp(2j * np.pi * c2 * k**2)[:, None] * fourier
                 * np.exp(2j * np.pi * c1 * k**2)[None, :])
    operators = []
    for delay, nu in zip(delays, dopplers):
        time = np.zeros((n, n), dtype=np.complex128)
        shifted = k - int(delay)
        cp = np.where(shifted < 0,
                      np.exp(2j * np.pi * c1 * (n * n + 2 * n * shifted)), 1.)
        time[k, shifted % n] = cp * np.exp(2j * np.pi * k * nu / n)
        operators.append(transform @ time @ transform.conj().T)
    return operators


def residual(lhs: object, rhs: object) -> dict[str, float | None]:
    a, b = np.asarray(lhs), np.asarray(rhs)
    difference = a - b
    absolute = float(np.max(np.abs(difference)))
    scale = max(float(np.linalg.norm(a)), float(np.linalg.norm(b)))
    # A relative error at or below the declared absolute tolerance has no
    # stable interpretation. Report NA, while retaining its absolute residual.
    relative = None if scale <= ATOL else float(np.linalg.norm(difference) / scale)
    return {"absolute": absolute, "relative": relative}


def record(maxima: dict, name: str, lhs: object, rhs: object, case: str) -> None:
    got = residual(lhs, rhs)
    previous = maxima.setdefault(name, {"max_absolute": 0., "max_relative": None,
                                         "worst_absolute_case": None,
                                         "worst_relative_case": None,
                                         "relative_na_count": 0})
    if got["absolute"] >= previous["max_absolute"]:
        previous["max_absolute"] = got["absolute"]
        previous["worst_absolute_case"] = case
    if got["relative"] is None:
        previous["relative_na_count"] += 1
    elif previous["max_relative"] is None or got["relative"] >= previous["max_relative"]:
        previous["max_relative"] = got["relative"]
        previous["worst_relative_case"] = case
    if got["absolute"] > ATOL and (got["relative"] is None or got["relative"] > RTOL):
        raise AssertionError(f"{name} failed in {case}: {got}")


def verify() -> dict:
    sources = {name: sha(path) for name, path in
               (("physical.py", PHYSICAL), ("twofft.py", TWOOFFT), ("tf_base.py", BASE))}
    if sources != EXPECTED:
        raise ValueError(f"frozen source hash differs: {sources}")
    sys.path.insert(0, str(PHYSICAL.parent))
    sys.path.insert(0, str(TWOOFFT.parent))
    from physical import Channel, projected_variance  # noqa: E402
    from twofft import TimePathOps  # noqa: E402

    c1 = 5 / (2 * N)
    c2 = (np.sqrt(2) - 1) / (2 * N**2)
    cpp_wrap = np.exp(2j * np.pi * c1 * (N * N - 2 * N * (N - 1)))
    if abs(cpp_wrap - 1) < 1:
        raise AssertionError("CPP boundary case has trivial wrap phase")
    cases = {
        "one_path": ([0], [0.]),
        "distinct_delay": ([0, 5], [.3, -1.2]),
        "same_delay_integer": ([2, 2], [0., 1.]),
        "same_delay_fractional": ([3, 3], [.15, .151]),
        "near_duplicate": ([4, 4], [.15, .15000001]),
        "exact_duplicate": ([5, 5], [.2, .2]),
        "zero_hbar": ([3, 3], [.15, .151]),
        "near_zero_hbar": ([3, 3], [.15, .151]),
        "nonuniform_cross_delay": ([1, 7, 1], [-.7, .25, .42]),
        "cpp_boundary": ([0, N - 1, N - 1], [.6, -.21, -.209]),
    }
    maxima: dict[str, dict] = {}
    cross_examples = []
    floor_count = 0
    for seed in SEEDS:
        random = np.random.default_rng(seed)
        for name, (raw_delays, raw_dopplers) in cases.items():
            label = f"{name}/seed={seed}"
            delays = np.asarray(raw_delays, dtype=int)
            dopplers = np.asarray(raw_dopplers, dtype=float)
            p = len(delays)
            gains = random.normal(size=p) + 1j * random.normal(size=p)
            channel = Channel(N, c1, c2, delays, dopplers, gains)
            operators = independent_operators(N, delays, dopplers, c1, c2)
            basis = np.eye(N, dtype=np.complex128)
            for i in range(p):
                single = Channel(N, c1, c2, delays[i:i + 1], dopplers[i:i + 1],
                                 np.ones(1, dtype=np.complex128))
                source_operator = np.column_stack([single.apply(basis[:, j]) for j in range(N)])
                record(maxima, "direct_CPP_operator", operators[i], source_operator, label)

            direct_r = np.asarray([[np.trace(a.conj().T @ b) / N for b in operators]
                                   for a in operators])
            source_r = TimePathOps(channel).R
            record(maxima, "physical_R_trace", direct_r, source_r, label)
            nonuniform = .01 + random.random(N) / 2
            for vname, variance in (("nonuniform", nonuniform),
                                    ("isotropic", np.full(N, .17))):
                tag = f"{label}/{vname}"
                direct_gamma = np.asarray([
                    [sum(variance[k] * np.vdot(a[:, k], b[:, k]) for k in range(N))
                     for b in operators] for a in operators])
                trace_gamma = np.asarray([[np.trace(a.conj().T @ b @ np.diag(variance))
                                           for b in operators] for a in operators])
                source_gamma = projected_variance(variance, delays, dopplers, c1)
                record(maxima, "eq1_trace", direct_gamma, trace_gamma, tag)
                record(maxima, "eq1_source_Gamma", direct_gamma, source_gamma, tag)
                vx = float(variance.mean())
                if vname == "isotropic":
                    record(maxima, "eq2_isotropic", source_gamma, N * vx * source_r, tag)
                same = delays[:, None] == delays[None, :]
                record(maxima, "eq3_same_delay", source_gamma[same],
                       (N * vx * source_r)[same], tag)
                cross = source_gamma - N * vx * source_r
                record(maxima, "eq3_cross_support", cross[same],
                       np.zeros(np.count_nonzero(same)), tag)
                if vname == "nonuniform" and np.any(~same):
                    cross_examples.append(float(np.max(np.abs(cross[~same]))))
                identity = np.eye(p)
                lhs = np.linalg.norm(source_gamma - N * vx * identity)**2
                rhs = ((N * vx)**2 * np.linalg.norm(source_r - identity)**2
                       + np.linalg.norm(cross)**2)
                record(maxima, "eq4_Frobenius", lhs, rhs, tag)

            hbar = random.normal(size=p) + 1j * random.normal(size=p)
            if name in ("one_path", "zero_hbar"):
                hbar = np.zeros(p, dtype=np.complex128)
            elif name == "near_zero_hbar":
                hbar *= 1e-14
            elif name == "exact_duplicate":
                hbar = np.asarray([1., -1.], dtype=np.complex128)
            hpre = random.normal(size=p) + 1j * random.normal(size=p)
            force = random.normal(size=p) + 1j * random.normal(size=p)
            alpha, vx = .4, .15
            xbar = (np.zeros(N, dtype=np.complex128) if name in ("one_path", "cpp_boundary")
                    else random.normal(size=N) + 1j * random.normal(size=N))
            precision = alpha * float(np.vdot(xbar, xbar).real)
            floor_count += int(precision <= 1e-12)
            vq = 1 / max(precision, 1e-12)
            tau = 1 / p
            rh_base = hpre + vq * (force - hbar * alpha * N * vx)
            rh_cgr = hpre + vq * (force - source_r @ hbar * alpha * N * vx)
            mean_base = tau * rh_base / (tau + vq)
            mean_cgr = tau * rh_cgr / (tau + vq)
            coefficient = alpha * N * vx / (p + 1 / vq)
            defect = -coefficient * (source_r - np.eye(p)) @ hbar
            record(maxima, "eq5_finite_gain_difference", mean_cgr - mean_base,
                   defect, label)
            physical = sum(defect[i] * operators[i] for i in range(p))
            if name == "exact_duplicate":
                if np.linalg.norm(defect) <= 1e-6:
                    raise AssertionError("duplicate null-direction reaction was trivial")
                record(maxima, "duplicate_null_physical", np.linalg.norm(physical)**2 / N,
                       0., label)
            record(maxima, "eq6_physical_norm", np.linalg.norm(physical)**2 / N,
                   np.vdot(defect, source_r @ defect).real, label)
            record(maxima, "eq6_quadratic_form", np.vdot(defect, source_r @ defect).real,
                   coefficient**2 * np.vdot(hbar, (source_r - np.eye(p)) @
                                            source_r @ (source_r - np.eye(p)) @ hbar).real,
                   label)
    return dict(schema="tf-scalar-closure-numerical/1", status="pass",
                date="2026-09-24", authoring_role="Codex theory-to-code audit",
                source_git_commit="49ba637bba592dcda6e612609ff3bdc27048cb8d",
                source_sha256=sources, seeds=list(SEEDS), dimension=N,
                c1=c1, c2=c2, cases=list(cases), comparisons=len(SEEDS) * len(cases),
                cpp_wrap_phase_real=float(cpp_wrap.real),
                cpp_wrap_phase_imag=float(cpp_wrap.imag),
                tolerance=dict(atol=ATOL, rtol=RTOL,
                               relative_denominator="max(norm(lhs),norm(rhs)); NA if <=atol"),
                script_sha256=sha(Path(__file__)), maxima=maxima,
                distinct_delay_nonuniform_cross_max=max(cross_examples),
                gain_precision_floor_cases=floor_count,
                new_receiver_calls=0, new_decoder_calls=0, new_observations=0)


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True, allow_nan=False))
