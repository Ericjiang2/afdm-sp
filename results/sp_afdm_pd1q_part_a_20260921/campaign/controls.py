"""Two scoped coded-round interventions on the frozen native receiver.

The unmodified primary, POINT and FIXED-inner call native_twofft.receive. This
copy of its round loop exists only to expose the two interventions; it uses the
same frozen pilot, refit, joint detector, decoder and checkpoint functions.
"""
import time

import numpy as np

from receiver import pilot_front, decoder_messages
from messages import moments
from twofft import time_refine, scalar_joint


def receive_intervention(observation, system, code, *, intervention,
                         checkpoint_sink=None, record_states=False):
    if intervention not in ("no_decoder_feedback", "fixed_acquired_geometry_refit_gains"):
        raise ValueError("unregistered Part A intervention")
    if len(observation["y"]) != 1024 or system.rho != .5 or set(observation) != {"y", "pilot", "sigma2"}:
        raise ValueError("frozen observed-only native interface differs")
    start = time.perf_counter()
    state = pilot_front(observation, system, code)
    pilot_seconds = time.perf_counter() - start
    arrays, events, acquired = {}, [], None
    for round_index in range(2):
        stage_start = time.perf_counter()
        if intervention == "fixed_acquired_geometry_refit_gains":
            # time_refine selects the same top-eight pilot-acquired integer centers
            # on round zero. Later calls receive only those eight fixed paths.
            if acquired is not None:
                state["delays"], state["dopplers"] = acquired
            channel, detail = time_refine(
                observation["y"], observation["pilot"], state["mu"], state["v"],
                state["delays"], state["dopplers"], state["gains"], system.c1,
                system.c2, observation["sigma2"], mode="soft", max_paths=8, rounds=0)
            if acquired is None:
                acquired = (channel.delays.copy(), channel.dopplers.copy())
            elif (not np.array_equal(np.sort(channel.delays), np.sort(acquired[0]))
                  or not np.array_equal(channel.dopplers[np.argsort(channel.delays)],
                                        acquired[1][np.argsort(acquired[0])])):
                raise ValueError("fixed acquired geometry changed")
        else:
            channel, detail = time_refine(
                observation["y"], observation["pilot"], state["mu"], state["v"],
                state["delays"], state["dopplers"], state["gains"], system.c1,
                system.c2, observation["sigma2"], mode="soft", max_paths=8, rounds=2)
        ce_seconds = time.perf_counter() - stage_start
        stage_start = time.perf_counter()
        output = scalar_joint(
            observation["y"], observation["pilot"], channel,
            observation["sigma2"], pd=1-system.rho, prior=state["prior"],
            iterations=20, gain_mode="joint", record_states=record_states)
        inference_seconds = time.perf_counter() - stage_start
        stage_start = time.perf_counter()
        decoder = decoder_messages(code, np.clip(output["extrinsic"], -20, 20), maxiter=50)
        decoder_seconds = time.perf_counter() - stage_start
        if intervention == "no_decoder_feedback":
            state["prior"] = np.zeros_like(state["prior"])
            state["mu"], state["v"], _ = moments(np.clip(output["app"], -20, 20),
                                                    1-system.rho)
        else:
            state["prior"] = np.clip(decoder["raw_check_extrinsic"], -20, 20)
            state["mu"], state["v"], _ = moments(np.clip(decoder["raw_app"], -20, 20),
                                                    1-system.rho)
        state["delays"], state["dopplers"], state["gains"] = (
            channel.delays, channel.dopplers, output["gains"])
        event = dict(round=round_index, ce=ce_seconds, inference=inference_seconds,
                     decoder=decoder_seconds, ready=time.perf_counter()-start,
                     decoder_iterations=int(decoder["iterations"]),
                     inference_iterations=20, ce_evaluations=detail["evaluations"],
                     inference_fft_count=output["fft_count"],
                     ce_fft_count=detail["fft_count"], intervention=intervention)
        events.append(event)
        snapshot = dict(decoded=decoder["decoded"], input_llr=decoder["incoming_llr"],
                        app=decoder["raw_app"], check=decoder["raw_check_extrinsic"],
                        delays=channel.delays, dopplers=channel.dopplers,
                        gains=output["gains"], gain_variance=output["gain_variance"],
                        ce_gains=channel.gains, mu=output["mu"],
                        variance=output["variance"],
                        ce_history=np.asarray(detail["history"]),
                        ce_gamma=detail["gamma"], inference_trace=output["trace"])
        if record_states:
            snapshot["inference_states"] = output["states"]
        arrays.update({f"r{round_index}_{key}": value for key, value in snapshot.items()})
        if checkpoint_sink is not None:
            checkpoint_sink(dict(event, snapshot=snapshot), decoder["decoded"].copy())
    return decoder, arrays, dict(seconds=time.perf_counter()-start,
                                 pilot_seconds=pilot_seconds, events=events)
