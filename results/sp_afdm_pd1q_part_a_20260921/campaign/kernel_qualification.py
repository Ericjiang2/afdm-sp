#!/usr/bin/env python3
"""Fixed-map scalar-state qualification followed by interleaved kernel timing.

No receiver, code decoder, radio generator, or Monte Carlo observation is called.
Dense CPP tensors are deliberately restricted to the feasible N=256, P=8 case.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


SEED = 826891
SIZES = ((256, 8), (512, 8), (1024, 8), (2048, 8), (1024, 4), (1024, 16))
ITERATIONS = 20
REPEATS = 7
ATOL = 2e-9
RTOL = 1e-8


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture_hash(values):
    digest = hashlib.sha256()
    for name, value in values.items():
        array = np.asarray(value)
        digest.update(name.encode())
        digest.update(str(array.dtype).encode())
        digest.update(json.dumps(array.shape).encode())
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def independent_cpp_basis(channel):
    """Build U[p] as A T_p A^H, with T_p from direct cyclic CPP entries."""
    n = channel.n
    indices = np.arange(n)
    fourier = np.exp(-2j * np.pi * indices[:, None] * indices / n) / np.sqrt(n)
    af = (np.exp(2j * np.pi * channel.c2 * indices**2)[:, None] * fourier
          * np.exp(2j * np.pi * channel.c1 * indices**2)[None, :])
    basis = []
    for delay, doppler in zip(channel.delays, channel.dopplers):
        path = np.zeros((n, n), complex)
        columns = (indices - delay) % n
        wrap = np.where(indices < delay,
                        np.exp(2j * np.pi * channel.c1 * (n*n + 2*n*(indices-delay))),
                        1.0)
        path[indices, columns] = wrap * np.exp(2j * np.pi * doppler * indices / n)
        basis.append(af @ path @ af.conj().T)
    return np.asarray(basis)


def dense_scalar(y, pilot, channel, noise, prior, basis, *, record_states):
    """Independent direct-tensor version of the frozen scalar map (small N only)."""
    from messages import alphabet, marginal, moments

    n, p_count = channel.n, channel.p
    damping = .3
    tau = 1 / p_count
    symbols, _ = alphabet(.5)
    mu, variance, _ = moments(prior, .5)
    x = pilot + mu
    h = channel.gains.copy()
    vh = tau
    xb, hb = x.copy(), h.copy()
    s = np.zeros(n, complex)
    sv = 0.0
    previous_bar = previous_vp = None
    states = []
    basis_power = float(np.linalg.norm(basis)**2)
    for _ in range(ITERATIONS):
        response = np.einsum("pmk,k->mp", basis, x, optimize=True)
        operator = np.einsum("p,pmk->mk", h, basis, optimize=True)
        vx = float(variance.mean())
        bar = vx * np.linalg.norm(operator)**2 / n + vh * np.linalg.norm(response)**2 / n
        vp = bar + vh * vx * basis_power / n
        if previous_bar is not None:
            bar = damping * bar + (1-damping) * previous_bar
            vp = damping * vp + (1-damping) * previous_vp
        previous_bar, previous_vp = bar, vp
        predicted = response @ h - s * bar
        s = damping * (y-predicted) / (noise+vp) + (1-damping) * s
        sv = damping / (noise+vp) + (1-damping) * sv
        xb = damping * x + (1-damping) * xb
        hb = damping * h + (1-damping) * hb
        barred_response = np.einsum("pmk,k->mp", basis, xb, optimize=True)
        barred_operator = np.einsum("p,pmk->mk", hb, basis, optimize=True)
        vr = 1 / max(sv * np.linalg.norm(barred_operator)**2 / n, 1e-12)
        vq = 1 / max(sv * np.linalg.norm(barred_response)**2 / p_count, 1e-12)
        rx = x + vr * (barred_operator.conj().T @ s
                        - xb * sv * vh * basis_power / n)
        rh = h + vq * (barred_response.conj().T @ s
                        - hb * sv * vx * basis_power / p_count)
        extrinsic, app, mu, variance = marginal(
            -abs((rx-pilot)[:, None]-symbols)**2 / vr, prior, .5)
        x = pilot + mu
        vh = tau * vq / (tau+vq)
        h = tau * rh / (tau+vq)
        if record_states:
            states.append(dict(h=h.copy(), mu=mu.copy(), v=variance.copy(),
                               s=s.copy(), vr=vr, vq=vq, vh=vh, sv=sv,
                               bar=bar, vp=vp))
    return dict(extrinsic=extrinsic, app=app, mu=mu, variance=variance,
                gains=h, states=states)


def maximum_error(left, right):
    maximum = 0.0
    for key in ("h", "mu", "v", "s", "vr", "vq", "vh", "sv", "bar", "vp"):
        for a, b in zip(left["states"], right["states"]):
            maximum = max(maximum, float(np.max(np.abs(np.asarray(a[key])-np.asarray(b[key])))))
    for key in ("extrinsic", "app", "mu", "variance", "gains"):
        maximum = max(maximum, float(np.max(np.abs(np.asarray(left[key])-np.asarray(right[key])))))
    return maximum


def assert_same_map(left, right, label):
    if len(left["states"]) != ITERATIONS or len(right["states"]) != ITERATIONS:
        raise ValueError(f"{label}: incomplete scalar-state trace")
    for index, (a, b) in enumerate(zip(left["states"], right["states"])):
        for key in ("h", "mu", "v", "s", "vr", "vq", "vh", "sv", "bar", "vp"):
            if not np.allclose(a[key], b[key], atol=ATOL, rtol=RTOL):
                raise ValueError(f"{label}: iteration {index} {key} differs")
    for key in ("extrinsic", "app", "mu", "variance", "gains"):
        if not np.allclose(left[key], right[key], atol=ATOL, rtol=RTOL):
            raise ValueError(f"{label}: terminal {key} differs")
    return maximum_error(left, right)


def residual_in_time_domain(result, channel, daft):
    """Only the output residual uses different AF/time coordinates."""
    mapped = dict(result)
    mapped["states"] = [dict(state, s=daft(state["s"], channel.c1,
                                           channel.c2, True))
                        for state in result["states"]]
    return mapped


def build_fixture(n, p_count, rng, Channel):
    started = time.perf_counter()
    delays = np.sort(rng.choice(min(n//8, 103), p_count, replace=False))
    dopplers = rng.uniform(-2, 2, p_count)
    gains = (rng.normal(size=p_count)+1j*rng.normal(size=p_count))/np.sqrt(2*p_count)
    channel = Channel(n, 9/(2*n), .002/n, delays, dopplers, gains)
    pilot = np.sqrt(.5)*np.exp(1j*rng.uniform(0, 2*np.pi, n))
    data = .5*(rng.choice([-1, 1], n)+1j*rng.choice([-1, 1], n))
    noise = .2
    y = channel.apply(pilot+data) + np.sqrt(noise/2)*(
        rng.normal(size=n)+1j*rng.normal(size=n))
    prior = rng.normal(size=2*n)
    values = dict(delays=delays, dopplers=dopplers, gains=gains,
                  pilot=pilot, y=y, prior=prior, noise=np.asarray(noise),
                  c1=np.asarray(channel.c1), c2=np.asarray(channel.c2))
    return channel, y, pilot, noise, prior, values, time.perf_counter()-started


def run_case(n, p_count, rng, Channel, daft, scalar_joint, TimePathOps):
    channel, y, pilot, noise, prior, values, fixture_seconds = build_fixture(
        n, p_count, rng, Channel)
    fixture_sha256 = fixture_hash(values)
    dense_enabled = (n, p_count) == (256, 8)
    dense_basis = None
    dense_setup_seconds = None
    if dense_enabled:
        started = time.perf_counter()
        dense_basis = independent_cpp_basis(channel)
        dense_setup_seconds = time.perf_counter()-started
    methods = {
        "tensor_free_2fft": lambda capture: scalar_joint(
            y, pilot, channel, noise, prior=prior, iterations=ITERATIONS,
            observation_domain="time", record_states=capture),
        "competent_4fft": lambda capture: scalar_joint(
            y, pilot, channel, noise, prior=prior, iterations=ITERATIONS,
            observation_domain="af", record_states=capture),
    }
    if dense_enabled:
        methods["independent_dense_cpp"] = lambda capture: dense_scalar(
            y, pilot, channel, noise, prior, dense_basis, record_states=capture)

    # Every timed implementation first passes the complete state/LLR contract.
    qualified = {name: function(True) for name, function in methods.items()}
    parity = {name: assert_same_map(
                  qualified["tensor_free_2fft"],
                  residual_in_time_domain(result, channel, daft), name)
              for name, result in qualified.items() if name != "tensor_free_2fft"}
    first_call_seconds = {}
    for name, function in methods.items():
        started = time.perf_counter()
        uncaptured = function(False)
        first_call_seconds[name] = time.perf_counter()-started
        for key in ("extrinsic", "app", "mu", "variance", "gains"):
            if not np.allclose(qualified[name][key], uncaptured[key], atol=ATOL, rtol=RTOL):
                raise ValueError(f"{name}: state-capture toggle changed {key}")

    raw_times = {name: [] for name in methods}
    order = list(methods)
    for repeat in range(REPEATS):
        rotated = order[repeat % len(order):] + order[:repeat % len(order)]
        for name in rotated:
            started = time.perf_counter()
            methods[name](False)
            raw_times[name].append(time.perf_counter()-started)

    ops = TimePathOps(channel)
    fixture_bytes = sum(np.asarray(value).nbytes for value in values.values())
    static_operator_bytes = sum(np.asarray(value).nbytes for value in
                                (ops.idx, ops.phase, ops.R))
    return {
        "n": n, "paths": p_count, "fixture_seed": SEED,
        "fixture_sha256": fixture_sha256,
        "parity_max_abs": parity,
        "dense_status": "qualified_and_timed" if dense_enabled else "not_run_feasibility_limit",
        "fixture_generation_seconds": fixture_seconds,
        "dense_basis_setup_seconds": dense_setup_seconds,
        "first_uncaptured_call_seconds": first_call_seconds,
        "raw_times_seconds": raw_times,
        "median_seconds": {name: float(np.median(values)) for name, values in raw_times.items()},
        "explicit_retained_array_bytes": {
            "fixture_arrays": fixture_bytes,
            "time_path_ops_idx_phase_R": static_operator_bytes,
            "dense_cpp_basis": None if dense_basis is None else int(dense_basis.nbytes),
            "scope": "explicit retained arrays only; excludes temporary arrays and process peak memory",
        },
    }


def main():
    args = parse_args()
    source, baseline, out = args.source.resolve(), args.baseline.resolve(), args.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError("kernel output directory must be new or empty")
    sys.path[:0] = [str(source / "src"), str(baseline / "src"),
                    str(baseline / "upstream" / "spafdm_receiver_handoff")]
    from physical import Channel, daft
    from twofft import scalar_joint, TimePathOps
    import evidence

    rng = np.random.default_rng(SEED)
    results = [run_case(n, p_count, rng, Channel, daft, scalar_joint, TimePathOps)
               for n, p_count in SIZES]
    payload = {
        "schema": "spafdm-pd1q-kernel-qualification/1",
        "status": "all_state_and_llr_parity_passed_before_timing",
        "source_root": str(source), "baseline_root": str(baseline),
        "source_hashes": evidence.source_hashes(source),
        "baseline_source_hashes": evidence.source_hashes(baseline),
        "script_sha256": file_hash(__file__),
        "seed": SEED, "sizes": [list(item) for item in SIZES],
        "iterations": ITERATIONS, "repeats": REPEATS,
        "tolerance": {"atol": ATOL, "rtol": RTOL,
                      "rule": "np.allclose for every scalar state and terminal LLR/output"},
        "cache_policy": "fixed fixture and channel per case; no persistent operator cache; per-call path-operator setup included; one uncaptured call before seven interleaved repeats; dense basis built once and cost reported separately",
        "results": results,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "kernel_qualification.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    with (out / "kernel_scaling.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("n", "paths", "method", "dense_status",
            "parity_max_abs", "fixture_sha256", "fixture_generation_seconds",
            "dense_basis_setup_seconds", "first_uncaptured_call_seconds",
            "raw_times_seconds", "median_seconds", "fixture_array_bytes",
            "operator_array_bytes", "dense_basis_bytes"))
        writer.writeheader()
        for row in results:
            for method, times in row["raw_times_seconds"].items():
                writer.writerow({
                    "n": row["n"], "paths": row["paths"], "method": method,
                    "dense_status": row["dense_status"],
                    "parity_max_abs": row["parity_max_abs"].get(method, 0.0),
                    "fixture_sha256": row["fixture_sha256"],
                    "fixture_generation_seconds": row["fixture_generation_seconds"],
                    "dense_basis_setup_seconds": row["dense_basis_setup_seconds"],
                    "first_uncaptured_call_seconds": row["first_uncaptured_call_seconds"][method],
                    "raw_times_seconds": json.dumps(times),
                    "median_seconds": row["median_seconds"][method],
                    "fixture_array_bytes": row["explicit_retained_array_bytes"]["fixture_arrays"],
                    "operator_array_bytes": row["explicit_retained_array_bytes"]["time_path_ops_idx_phase_R"],
                    "dense_basis_bytes": row["explicit_retained_array_bytes"]["dense_cpp_basis"],
                })
    print(json.dumps({"status": payload["status"], "cases": len(results),
                      "dense_cases": sum(row["dense_status"] == "qualified_and_timed"
                                         for row in results), "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()
