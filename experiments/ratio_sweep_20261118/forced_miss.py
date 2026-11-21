# Sources: frozen slot_mismatch_20261019/native_twofft_variant.py::receive and sp_afdm_frozen_reviewed_20260921/src/receiver.py::pilot_front; inject a pre-nomination delay mask because neither accepts a restricted pilot bank.
"""Forced-miss F0 and truth-free window quantities for the ratio sweep."""

import math
import time
from types import SimpleNamespace

import numpy as np
import torch
from messages import moments
from physical import dkernel
from receiver import BaselineInitializer, Channel, decoder_messages, pilot_front
from twofft import scalar_joint, time_refine

import sweep


RATIOS = (1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 64, 128)
CAL = range(54000, 54200)
MAIN = range(55000, 56000)
SNRS = (4.5, 5.5, 6.5, 7.5, 8.5)
BACKGROUND_CLIP = (.1, .4)


def pilot_bank(max_delay, excluded_delay=None):
    delays = np.repeat(np.arange(max_delay + 1), 5)
    dopplers = np.tile(np.arange(-2, 3), max_delay + 1)
    if excluded_delay is None:
        return delays, dopplers
    included = delays != excluded_delay
    return delays[included], dopplers[included]


# Source: reviewed frozen receiver.py::pilot_front; B0 must receive a restricted dictionary, which the frozen call builds internally.
def masked_pilot_front(obs, system, excluded_delay):
    n = len(obs["y"])
    delays, dopplers = pilot_bank(system.l_max_cap, excluded_delay)
    design = Channel(n, system.c1, system.c2, delays, dopplers,
                     np.ones(len(delays))).regressors(obs["pilot"])
    initializer = BaselineInitializer("B0-p2-s0.5", lstsq_driver="gels")
    gains, ids = initializer(torch.tensor(obs["y"], dtype=torch.complex64),
                             torch.tensor(design, dtype=torch.complex64), 40, float(obs["sigma2"]))
    ids = np.asarray(ids, int)
    return dict(delays=delays[ids], dopplers=dopplers[ids], gains=gains.detach().cpu().numpy()[ids].copy(),
                mu=np.zeros(n, complex), v=np.full(n, .5), prior=np.zeros(2 * n))


# Source: frozen slot_mismatch_20261019/native_twofft_variant.py::receive; inject the masked front because the frozen loop directly calls its own initializer.
def receive(observation,system,code,rounds=2,iterations=20,ce_mode='soft',gain_mode='joint',checkpoint_sink=None,record_states=False,max_paths=8, *, excluded_delay=None):
    if len(observation['y'])!=1024 or system.rho!=.5:raise ValueError('frozen native interface: N=1024, rho=0.5')
    if rounds<1:raise ValueError('at least one coded round required')
    if checkpoint_sink is not None and not callable(checkpoint_sink):raise TypeError('checkpoint_sink must be callable')
    if set(observation)-{'y','pilot','sigma2'}:raise ValueError('Only observed inputs are accepted')
    st = time.perf_counter()
    if excluded_delay is None:
        s = pilot_front(observation, system, code)
    else:
        s = masked_pilot_front(observation, system, excluded_delay)
    tp = time.perf_counter() - st
    arrays={};events=[]
    for r in range(rounds):
        t=time.perf_counter()
        c,detail=time_refine(observation['y'],observation['pilot'],s['mu'],s['v'],s['delays'],s['dopplers'],s['gains'],system.c1,system.c2,observation['sigma2'],mode=ce_mode,max_paths=max_paths,rounds=2)
        # Refine selects only from entering delays, then varies Doppler at fixed delays.
        if excluded_delay is not None and excluded_delay in c.delays:
            raise RuntimeError("F0 refinement selected the excluded delay")
        tc=time.perf_counter()-t;t=time.perf_counter()
        o=scalar_joint(observation['y'],observation['pilot'],c,observation['sigma2'],pd=1-system.rho,prior=s['prior'],iterations=iterations,gain_mode=gain_mode,record_states=record_states)
        ti=time.perf_counter()-t;t=time.perf_counter()
        dec=decoder_messages(code,np.clip(o['extrinsic'],-20,20),maxiter=50)
        td=time.perf_counter()-t;s['prior']=np.clip(dec['raw_check_extrinsic'],-20,20)
        s['mu'],s['v'],_=moments(np.clip(dec['raw_app'],-20,20),1-system.rho)
        s['delays']=c.delays;s['dopplers']=c.dopplers;s['gains']=o['gains']
        events.append(dict(round=r,ce=tc,inference=ti,decoder=td,ready=time.perf_counter()-st,decoder_iterations=int(dec['iterations']),inference_iterations=iterations,ce_evaluations=detail['evaluations'],inference_fft_count=o['fft_count'],ce_fft_count=detail['fft_count']))
        round_arrays={'decoded':dec['decoded'],'input_llr':dec['incoming_llr'],'app':dec['raw_app'],
                      'check':dec['raw_check_extrinsic'],'delays':c.delays,'dopplers':c.dopplers,
                      'gains':o['gains'],'gain_variance':o['gain_variance'],'ce_gains':c.gains,
                      'mu':o['mu'],'variance':o['variance'],'ce_history':np.array(detail['history']),
                      'ce_gamma':detail['gamma'],'inference_trace':o['trace']}
        if record_states:round_arrays['inference_states']=o['states']
        arrays.update({f'r{r}_{k}':v for k,v in round_arrays.items()})
        # Optional caller-owned checkpoint capture survives a later numerical failure.
        # It must not change decisions; any callback cost remains in complete time.
        if checkpoint_sink is not None:
            checkpoint_sink(dict(events[-1],snapshot=round_arrays), dec['decoded'].copy())
    return dec,arrays,dict(seconds=time.perf_counter()-st,pilot_seconds=tp,events=events)


def f0_state(study, obs, excluded_delay):
    """Capture the actual r1 arrays produced by the masked two-round receiver."""
    q, ctx = study[:2]
    variant = SimpleNamespace(receive=lambda *args, **opts: receive(*args, **opts, excluded_delay=excluded_delay))
    dec, arrays, syndrome, _ = q.sm.f0_state(ctx, variant, obs, sweep.CAP)
    return dec, arrays, syndrome


def thresholds(E, u, ridge, z):
    T = E + u + ridge
    if z == 0:
        return math.inf, math.inf
    # Factor the difference of squares to retain accuracy near z = 1.
    scalar = ((1 - z) * E + u + ridge) * (T + z * E) / (z * (u + ridge)) ** 2
    signal = E + u
    numerator = ((1 - z) * signal + ridge) * (T + z * signal)
    codelay = numerator / (z * ridge) ** 2 if numerator > 0 else math.inf
    return scalar, codelay


def window(full, system, obs, r1, ratio):
    """Use the strongest estimated r1 slot and the nearest legal companion."""
    mu, v, _ = moments(np.clip(r1["r1_app"], -20, 20), 1 - system.rho)
    mean = obs["pilot"] + mu
    E, u, ridge = float(np.vdot(mean, mean).real), float(v.sum()), float(obs["sigma2"])
    paths = [full.Path(int(delay), float(nu))
             for delay, nu in zip(r1["r1_delays"], r1["r1_dopplers"], strict=True)]
    if len(paths) < 2:
        return None
    i = int(np.argmax(abs(r1["r1_gains"]) ** 2))
    anchor = paths[i]
    _, _, nus = full._bank(system.l_max_cap, **sweep.BANK)
    bank = [full.Path(anchor.delay, float(nu)) for nu in nus]
    legal = full._valid(paths, bank, sweep.DUPLICATE)[np.arange(len(paths)) != i].any(axis=0)
    if not legal.any():
        return None
    candidate = min((p for p, valid in zip(bank, legal, strict=True) if valid),
                    key=lambda p: (abs(p.doppler - anchor.doppler), p.doppler))
    z = float(abs(dkernel(candidate.doppler - anchor.doppler, len(mean))))
    scalar, codelay = thresholds(E, u, ridge, z)
    return {"E": E, "u": u, "lambda": ridge, "z": z,
            "R_A2_star": scalar, "R_C_star": codelay, "xi": ratio / scalar}


def exchange_from_r1(study, obs, r1, truth, weak, syndrome):
    """Enter both full-bank arms at the same saved r1, even on zero syndrome."""
    return sweep.continuation(study, obs, r1, truth, weak, eligible=True, triggered=bool(syndrome))
