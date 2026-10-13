"""Frozen CSTATE final branch shared by the three registered detector arms."""
from __future__ import annotations

import hashlib
import json
import time

import numpy as np


STAGES = (
    "message_handling", "y_transform", "geometry_setup", "structural_field_build",
    "structural_scoring", "structural_selection_trace", "structural_refit_refresh",
    "structural_fallback_direct", "local_refinement", "geometry_finalization",
    "geometry_wrapper_overhead", "wrapper_validation", "channel_construction", "tf", "ldpc",
)


def hash_value(value: object) -> str:
    digest = hashlib.sha256()

    def visit(item: object) -> None:
        if isinstance(item, dict):
            for key in sorted(item):
                if not isinstance(key, str):
                    raise TypeError("evidence keys must be strings")
                digest.update(key.encode())
                visit(item[key])
        elif isinstance(item, (list, tuple)):
            digest.update(str(len(item)).encode())
            for member in item:
                visit(member)
        elif isinstance(item, np.ndarray):
            array = np.ascontiguousarray(item)
            digest.update(str(array.dtype).encode())
            digest.update(json.dumps(array.shape).encode())
            digest.update(array.tobytes())
        else:
            digest.update(json.dumps(item, sort_keys=True, allow_nan=False).encode())

    visit(value)
    return digest.hexdigest()


def final_branch(obs, system, code, native, kernel, arrays, detector):
    """Identical geometry/prior/LDPC boundary to the reviewed v2 branch."""
    from messages import moments
    from physical import Channel, daft
    from twofft import TimePathOps

    stamp = time.perf_counter()
    app = np.clip(arrays["r1_app"], -20, 20)
    check = np.clip(arrays["r1_check"], -20, 20)
    mu, variance, _ = moments(app, 1 - system.rho)
    initial = [kernel.Path(int(delay), float(nu)) for delay, nu in zip(
        arrays["r1_delays"], arrays["r1_dopplers"])]
    if len(initial) != len(arrays["r1_gains"]):
        raise ValueError("native path slots differ")
    message_end = time.perf_counter()
    Y = daft(obs["y"], system.c1, system.c2, True)
    transform_end = time.perf_counter()
    result = kernel.reopen_geometry(
        Y, obs["pilot"] + mu, variance, initial,
        c1=system.c1, c2=system.c2, ridge=float(obs["sigma2"]),
        max_delay=system.l_max_cap, doppler_min=-3., doppler_max=3.,
        grid_step=.25, max_edits=2, chunk_size=64, local_passes=2,
        local_halfwidth=.75, local_max_evals=16,
        duplicate_tolerance=1e-6, top_k=20, strategy="compact")
    geometry_end = time.perf_counter()
    if len(result.paths) != len(initial):
        raise ValueError("CSTATE changed slot count")
    stage = result.diagnostics["stage_timing"]
    exclusive = stage["exclusive_seconds"]
    if (set(exclusive) != set(STAGES[2:10]) or
            any(not np.isfinite(x) or x < 0 for x in exclusive.values()) or
            not np.isclose(sum(exclusive.values()), stage["total_seconds"], rtol=0, atol=1e-6)):
        raise ValueError("CSTATE exclusive stage timing differs")
    overhead = geometry_end - transform_end - stage["total_seconds"]
    if overhead < 0:
        raise ValueError("CSTATE clock exceeds wrapper")
    validation_end = time.perf_counter()
    channel = Channel(len(obs["y"]), system.c1, system.c2,
                      [path.delay for path in result.paths],
                      [path.doppler for path in result.paths], result.gains)
    channel_end = time.perf_counter()
    entering = dict(
        app=app, check=check, ce_mu=mu, ce_variance=variance,
        initial_delays=np.asarray([path.delay for path in initial]),
        initial_dopplers=np.asarray([path.doppler for path in initial]),
        delays=channel.delays, dopplers=channel.dopplers, gains=channel.gains)
    entering_sha256 = hash_value(entering)
    R = TimePathOps(channel).R
    eigenvalues = np.linalg.eigvalsh(R)
    tol = 1e-10
    if (np.max(abs(R - R.conj().T)) > tol or
            np.max(abs(np.diag(R) - 1)) > tol or eigenvalues.min() < -tol):
        raise ValueError("physical R qualification failed")
    groups = {str(int(delay)): int(np.count_nonzero(channel.delays == delay))
              for delay in np.unique(channel.delays)}
    gamma = channel.gamma(variance)
    B = channel.regressors(obs["pilot"] + mu)
    same = channel.delays[:, None] == channel.delays[None, :]
    moment_error = float(np.max(abs((gamma - len(obs["y"]) * float(variance.mean()) * R)[same])))
    if moment_error > 1e-8:
        raise ValueError("same-delay working moment identity differs")
    gram = dict(R=R, eigenvalues=eigenvalues, group_multiplicities=groups,
                max_within_group_coherence=float(np.max(abs(R - np.eye(channel.p)))),
                Gamma=gamma, response_gram=B.conj().T @ B,
                same_delay_moment_error=moment_error)
    detector_result = detector.scalar_joint(
        obs["y"], obs["pilot"], channel, obs["sigma2"],
        pd=1 - system.rho, prior=check, iterations=20,
        damping=.3, gain_mode="joint", record_states=True)
    tf_end = time.perf_counter()
    if len(detector_result["states"]) != 20:
        raise ValueError("triggered branch lacks 20 full states")
    decoder = native.decoder_messages(
        code, np.clip(detector_result["extrinsic"], -20, 20), maxiter=50)
    decision_end = time.perf_counter()
    stages = dict(message_handling=message_end - stamp,
                  y_transform=transform_end - message_end, **exclusive,
                  geometry_wrapper_overhead=overhead,
                  wrapper_validation=validation_end - geometry_end,
                  channel_construction=channel_end - validation_end,
                  tf=tf_end - channel_end, ldpc=decision_end - tf_end)
    if not np.isclose(sum(stages.values()), decision_end - stamp, rtol=0, atol=1e-7):
        raise ValueError("branch exclusive clocks differ")
    return dict(result=result, detector=detector_result, decoder=decoder,
                entering=entering, entering_sha256=entering_sha256,
                gram=gram, decision_ready_at=decision_end, branch_origin=stamp,
                exclusive_stages=stages, branch_decision_seconds=decision_end - stamp)


def base_common_state(states: list[dict], n: int) -> list[dict]:
    rows = []
    for iteration, state in enumerate(states):
        R = state["physical_R"]
        p = len(state["hbar"])
        dh = (-state["alpha"] * n * state["vx"] / (p + 1 / state["vq"])
              * (R - np.eye(p)) @ state["hbar"])
        physical = float(np.vdot(dh, R @ dh).real)
        if physical < -1e-10:
            raise ValueError("negative physical correction norm")
        rows.append(dict(iteration=iteration, dh=dh,
                         physical_norm_squared=max(0., physical),
                         reciprocal_precision=1 / state["vq"]))
    return rows
