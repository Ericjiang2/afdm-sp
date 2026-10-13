"""Coded handoff for the frozen corrected F2 front end.

Importing this module does not run an observation. A future, separately frozen
runner must charge and seal every estimator, TF, LDPC, and branch decision.
"""

from __future__ import annotations

import time

import numpy as np

from f2_estimator import estimate, hard_qpsk
from messages import moments
from receiver import decoder_messages
from twofft import scalar_joint
from physical import Channel


def _observed(observation, system) -> tuple[np.ndarray, np.ndarray, float]:
    if set(observation) != {"y", "pilot", "sigma2"}:
        raise ValueError("F2 accepts only observed y, pilot, sigma2")
    y = np.asarray(observation["y"], dtype=np.complex128)
    pilot = np.asarray(observation["pilot"], dtype=np.complex128)
    sigma2 = float(observation["sigma2"])
    if (y.shape != (1024,) or pilot.shape != (1024,)
            or system.rho != 0.5 or system.l_max_cap != 102
            or sigma2 <= 0 or not np.isfinite(sigma2)):
        raise ValueError("F2 frozen N1024/rho.5/delay102 interface")
    return y, pilot, sigma2


def _coded_rounds(y: np.ndarray, pilot: np.ndarray, sigma2: float,
                  initial_channel: Channel, code, *, rounds: int,
                  initial_prior: np.ndarray | None = None,
                  origin: float | None = None, checkpoint_sink=None,
                  record_states: bool = False) -> tuple[dict, dict, dict]:
    if initial_channel.p != 155:
        raise ValueError("F2 communications support must retain top155 paths")
    if checkpoint_sink is not None and not callable(checkpoint_sink):
        raise TypeError("checkpoint sink must be callable")
    if rounds not in (1, 2):
        raise ValueError("frozen F2 handoff has one triggered or two early coded rounds")
    start = time.perf_counter()
    if origin is None:
        origin = start
    prior = np.zeros(2048) if initial_prior is None else np.asarray(
        initial_prior, dtype=float).copy()
    if prior.shape != (2048,) or not np.isfinite(prior).all():
        raise ValueError("invalid carried native check prior")
    channel = initial_channel
    arrays = {}
    events = []
    for round_index in range(rounds):
        round_start = time.perf_counter()
        detector = scalar_joint(y, pilot, channel, sigma2, pd=0.5,
                                prior=prior, iterations=20, damping=0.3,
                                gain_mode="joint", record_states=record_states)
        detector_end = time.perf_counter()
        decoder = decoder_messages(code, np.clip(detector["extrinsic"], -20, 20),
                                   maxiter=50)
        decoder_end = time.perf_counter()
        prior = np.clip(decoder["raw_check_extrinsic"], -20, 20)
        # APP is carried as the native continuation state even though fixed
        # F2 geometry requires no data-aided front-end refit in round two.
        mu, variance, _ = moments(np.clip(decoder["raw_app"], -20, 20), 0.5)
        snapshot = {"decoded": decoder["decoded"],
                    "incoming_llr": decoder["incoming_llr"],
                    "app": decoder["raw_app"],
                    "check": decoder["raw_check_extrinsic"],
                    "mu": mu, "variance": variance,
                    "delays": channel.delays,
                    "dopplers": channel.dopplers,
                    "gains": detector["gains"],
                    "gain_variance": detector["gain_variance"],
                    "detector_trace": detector["trace"]}
        if record_states:
            snapshot["detector_states"] = detector["states"]
        arrays.update({f"r{round_index}_{key}": value for key, value in snapshot.items()})
        event = {"round": round_index, "refit_seconds": 0.0,
                 "inference_seconds": detector_end - round_start,
                 "decoder_seconds": decoder_end - detector_end,
                 "ready_seconds": decoder_end - origin,
                 "inference_iterations": 20,
                 "decoder_iterations": int(decoder["iterations"])}
        events.append(event)
        if checkpoint_sink is not None:
            checkpoint_sink({**event, "snapshot": snapshot},
                            np.asarray(decoder["decoded"], np.uint8).copy())
        channel = Channel(channel.n, channel.c1, channel.c2, channel.delays,
                          channel.dopplers, detector["gains"])
    return decoder, arrays, {"coded_seconds": time.perf_counter() - start,
                             "events": events}


def receive_f2e(observation, system, code, *, checkpoint_sink=None,
                record_states: bool = False):
    """F2 early front end then unchanged two-round coded TF/LDPC core."""
    y, pilot, sigma2 = _observed(observation, system)
    start = time.perf_counter()
    front = estimate(y, pilot, sigma2, system.c1, system.c2,
                     max_delay=102, nu_min=-3, nu_max=3)
    front_end = time.perf_counter()
    decoded, arrays, timing = _coded_rounds(
        y, pilot, sigma2, front["channel"], code,
        rounds=2, origin=start, checkpoint_sink=checkpoint_sink,
        record_states=record_states)
    timing.update(front_seconds=front_end - start,
                  complete_seconds=time.perf_counter() - start)
    return decoded, arrays, {"timing": timing, "estimator": front}


def continue_f2t(observation, system, code, *, native_app, native_check,
                 native_syndrome_weight: int, checkpoint_sink=None,
                 record_states: bool = False):
    """F2 triggered branch after an already charged, failed F0 native decode.

    The caller supplies the completed native APP and syndrome; this function
    does not perform or hide an extra native acquisition or decoder call.
    """
    y, pilot, sigma2 = _observed(observation, system)
    if type(native_syndrome_weight) is not int or native_syndrome_weight <= 0:
        raise ValueError("F2T requires an observed nonzero native syndrome")
    app = np.asarray(native_app, dtype=float)
    check = np.asarray(native_check, dtype=float)
    if (app.shape != (2048,) or check.shape != (2048,)
            or not np.isfinite(app).all() or not np.isfinite(check).all()):
        raise ValueError("invalid already charged native APP/check")
    mu, _, _ = moments(np.clip(app, -20, 20), 0.5)
    charged_initial_data = hard_qpsk(mu)
    start = time.perf_counter()
    front = estimate(y, pilot, sigma2, system.c1, system.c2,
                     max_delay=102, nu_min=-3, nu_max=3,
                     initial_data=charged_initial_data)
    front_end = time.perf_counter()
    decoded, arrays, timing = _coded_rounds(
        y, pilot, sigma2, front["channel"], code,
        rounds=1, initial_prior=np.clip(check, -20, 20), origin=start,
        checkpoint_sink=checkpoint_sink, record_states=record_states)
    timing.update(front_seconds=front_end - start,
                  complete_seconds=time.perf_counter() - start,
                  native_work_is_external_and_charged=True)
    return decoded, arrays, {"timing": timing, "estimator": front,
                             "initial_data": charged_initial_data}
