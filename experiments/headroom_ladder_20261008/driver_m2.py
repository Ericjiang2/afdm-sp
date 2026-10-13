#!/usr/bin/env python
"""M2 driver (task 10-08-doppler-cluster, design.md Stage M2).  Wraps driver_f2.py (unchanged), same generator / entropy / CL_DOMAIN,
so rows pair bit-for-bit with F1/F2/M1 at the same (config, snr, frame).

Arms (one JSONL row per (config, snr, frame, arm))
  A0   production B (+CSTATE20 on trigger)      driver.run_a0   (via driver_f2, unchanged)
  A3   true H fixed, TF20R2                      driver.run_a3
  PS   Stage-A arm D (cap 8, keep-slots, CSTATE20 branch)       driver_f2.run_ps
  <name in --m2-config 'arms'>   DPSS-BEM receiver (dpss_rx.DpssRefine(cfg)) inside the frozen native coded schedule:
       interventions._instrumented(rounds=2, iterations=20, gain_mode='joint', refine_override=DpssRefine); no CSTATE.
       Arms are defined by the JSON (frozen test run: M_full, M_adapt; dev tuning: a grid of named configs).
  PB16 PS with the slot cap 16 and no stopping rule (f1_cap.py / native_f1_cap.py copies), same CSTATE20 branch rule as PS.
M arms receive ONLY the observation dict {y, pilot, sigma2}; truth is used afterwards for scoring and for the diagnostic
`misfit` / `missed_energy_fraction` fields (never inside the receiver).
Channel law: --power-norm expected (default, paper-grade: ray gains CN(0, tap_power/R), NO per-frame renormalisation) or realized (F1/F2
law).  The expected law reuses driver_f3.cluster_base_f3 (imported, not copied) by routing driver.cluster_base through it; the draws
(delays, rays, Dopplers, base normals, message, noise) are the F1 draws, only the gain scale differs.
Run one process per shard, single thread (launch_m2.sh).  Extra flags: --m2-config PATH [--m2-config-sha256 HEX] [--pb16-cap 16]
[--power-norm expected|realized].
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import numpy as np

import driver as base
import driver_f2 as f2
import driver_f3
import dpss_rx
import orders
import tapchannel

PB16_ARM = 'PB16'
_orig_cell = f2.run_cell_f2
_orig_load_context = f2.load_context
_orig_parse_args = f2.parse_args
_orig_cluster_base = base.cluster_base
M2 = dict(arms={}, pb16_cap=16, config_sha256=None, power_norm='expected')


def install_power_norm(power_norm):
    """Route driver.cluster_base (used by f2.run_shard and the unit checks) through the F3 generator for the expected law."""
    if power_norm == 'realized':
        base.cluster_base = _orig_cluster_base
    elif power_norm == 'expected':
        base.cluster_base = lambda ctx, msg, geom, config: driver_f3.cluster_base_f3(ctx, msg, geom, config, 'expected')
    else:
        raise ValueError(power_norm)
    M2['power_norm'] = power_norm


# ------------------------------------------------------------------------------------------------ args / config
def parse_args(argv=None):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--m2-config', type=Path, default=None)
    ap.add_argument('--m2-config-sha256', default='')
    ap.add_argument('--pb16-cap', type=int, default=16)
    ap.add_argument('--power-norm', choices=('expected', 'realized'), default='expected')
    ns, rest = ap.parse_known_args(argv)
    args = _orig_parse_args(rest)
    args.m2_config, args.m2_config_sha256, args.pb16_cap = ns.m2_config, ns.m2_config_sha256, ns.pb16_cap
    args.power_norm = ns.power_norm
    install_power_norm(ns.power_norm)
    f2.F2_SPEC['power_norm'] = dict(
        law=ns.power_norm, expected='ray gain CN(0, tap_power/R), no per-frame renormalisation (driver_f3.cluster_base_f3)',
        realized='F1 law: realized sum|g|^2 renormalised to 1 per frame (driver.cluster_base)')
    if ns.m2_config is not None:
        digest = base.sha256_file(ns.m2_config)
        if ns.m2_config_sha256 and ns.m2_config_sha256 != digest:
            raise ValueError(f'm2 config sha256 {digest} != required {ns.m2_config_sha256}')
        spec = json.loads(Path(ns.m2_config).read_text())
        bad = [k for k, cfg in spec['arms'].items() if k in f2.F2_ARMS + (PB16_ARM,) or set(cfg) - set(dpss_rx.CFG_DEFAULT)]
        if bad:
            raise ValueError(f'm2 config arms with reserved name or unknown keys: {bad}')
        M2.update(arms=spec['arms'], config_sha256=digest, config=spec)
        f2.F2_SPEC['m2'] = dict(config_sha256=digest, config=spec, defaults=dpss_rx.CFG_DEFAULT,
                                hook='interventions._instrumented(refine_override=dpss_rx.DpssRefine), rounds=2, TF20 joint, LDPC50, no CSTATE',
                                prior_realisation='column rescaling s_d=sqrt(tau_d P) (dpss_rx docstring)')
    M2['pb16_cap'] = ns.pb16_cap
    f2.F2_SPEC['pb16'] = dict(cap=ns.pb16_cap, files='f1_cap.py (PhysicalF1.acquire copy, range(cap)), native_f1_cap.py',
                              branch='CSTATE20 iff final native syndrome != 0 (as PS)')
    f2.F2_ARMS = tuple(dict.fromkeys(f2.F2_ARMS + tuple(M2['arms']) + (PB16_ARM,)))
    return args


# ---------------------------------------------------------------------------------------------------- M arms
def tap_misfit(truth, n, refiner, gains):
    """sum_l ||a_l - a^_l||^2 / sum_l ||a_l||^2 (taps without columns contribute their full energy); diagnostic only."""
    est = {}
    for tap in refiner.prev['taps']:
        est[tap['delay']] = refiner.prev['M'][:, tap['sl']] @ np.asarray(gains, complex)[tap['sl']]
    num = den = 0.
    for d, (nu, g) in orders.tap_groups(truth['l_i'], truth['k_real'], truth['g_i']).items():
        a = orders.tap_sequence(nu, g, n)
        den += float(np.vdot(a, a).real)
        r = a - est[d] if d in est else a
        num += float(np.vdot(r, r).real)
    return num / den


def compact_log(log):
    out = []
    for r in log:
        kept = [t for t in r['taps'] if t['kept']]
        out.append(dict(n_in=r['n_taps_in'], n_kept=r['n_taps_kept'], n_cols=r['n_cols'],
                        delays=[t['delay'] for t in kept], c=[round(t['c'], 4) for t in kept],
                        W=[round(t['W'], 4) for t in kept], D=[t['D'] for t in kept], E=[round(t['E'], 6) for t in kept],
                        tau_sum=round(r['tau_sum'], 6), tau_min=r['tau_min'], s2=round(r['s2'], 6),
                        cond_Q=r['cond_Q']))
    return out


def run_m(ctx, obs, name, cfg, refiner=None):
    """Count-blind DPSS-BEM receiver: sees obs only.  (`refiner` override is for the unit checks' oracle variants only.)"""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    refiner = dpss_rx.DpssRefine(cfg) if refiner is None else refiner
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='dpss_m2', rounds=2, iterations=20,
                                            gain_mode='joint', refine_override=refiner)
    seconds = time.perf_counter() - start
    d = result.decoder
    ev = result.timing['events']
    return dict(arm=name, decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds,
                triggered=None, refiner=refiner, gains=result.arrays['r1_gains'], n=len(obs['y']),
                sec_pilot=float(result.trace['acquisition_seconds']), sec_ce=float(sum(e['ce'] for e in ev)),
                sec_inference=float(sum(e['inference'] for e in ev)), sec_decoder=float(sum(e['decoder'] for e in ev)))


# ------------------------------------------------------------------------------------------------------ PB16
def run_pb16(ctx, obs):
    """PS (driver_f2.run_ps) with the cap-16 acquisition/refit.  Returns the PB16 result dict (PS0-equivalent dropped)."""
    start = time.perf_counter()
    dec0, arrays, timing = ctx.receive_f1_cap(obs, ctx.system, ctx.code, cap=M2['pb16_cap'])
    f1_seconds = time.perf_counter() - start
    syn0 = base.syndrome_weight(ctx, dec0['decoded'])
    common = dict(fit_delays=np.asarray(arrays['r1_delays']), fit_dopplers=np.asarray(arrays['r1_dopplers']), f0_syndrome=syn0,
                  ps_stopping_reason=str(timing['acquisition']['stopping_reason']), ps_acq_seconds=float(timing['pilot_seconds']))
    if syn0 == 0:
        return dict(arm=PB16_ARM, decoded=dec0['decoded'], llr=dec0['incoming_llr'], iters=int(dec0['iterations']),
                    seconds=time.perf_counter() - start, triggered=False, **common)
    branch = ctx.branch(obs, ctx.system, ctx.code, ctx.native, ctx.kernel, arrays, 'CSTATE20')
    final = branch['decoder']
    return dict(arm=PB16_ARM, decoded=final['decoded'], llr=final['incoming_llr'], iters=int(final['iterations']),
                seconds=time.perf_counter() - start, triggered=True, **common)


# -------------------------------------------------------------------------------------------------- cell / ctx
def run_cell_m2(ctx, arms_wanted, obs, truth, snr_centi, frame, matrix_check):
    m_arms = [a for a in arms_wanted if a in M2['arms']]
    want_pb = PB16_ARM in arms_wanted
    rows = []
    other = [a for a in arms_wanted if a not in M2['arms'] and a != PB16_ARM]
    if other:
        rows += _orig_cell(ctx, other, obs, truth, snr_centi, frame, matrix_check)
    head = dict(rho=.5, rho_permille=500, snr_centi_db=int(snr_centi), snr_db=snr_centi / 100, frame=int(frame),
                **base.truth_summary(truth))
    head.update(base.cluster_row_fields(truth))
    for key in ('truth_l', 'truth_k', 'truth_g2'):
        head.pop(key, None)
    head.update(cl_sum_g2=float(truth['cluster'].get('sum_g2', 1.)), cl_power_norm=truth['cluster'].get('power_norm', 'realized'))
    for name in m_arms:
        try:
            res = run_m(ctx, obs, name, M2['arms'][name])
            row = dict(head, arm=name, status='ok', **base.score(ctx, res, truth))
            log = res['refiner'].log
            fit_delays = [t['delay'] for t in log[-1]['taps'] if t['kept']]
            lost, underfit = ctx.arms.missed_energy(truth['l_i'], truth['k_real'], truth['g_i'], fit_delays)
            row.update(misfit=tap_misfit(truth, res['n'], res['refiner'], res['gains']), missed_energy_fraction=lost,
                       n_fit_delays=len(fit_delays), n_cols=int(log[-1]['n_cols']), m2_log=compact_log(log),
                       sec_pilot=res['sec_pilot'], sec_ce=res['sec_ce'], sec_inference=res['sec_inference'],
                       sec_decoder=res['sec_decoder'])
        except Exception as error:
            rows.append(dict(head, arm=name, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
            continue
        rows.append(row)
    if want_pb:
        try:
            res = run_pb16(ctx, obs)
            row = dict(head, arm=PB16_ARM, status='ok', **base.score(ctx, res, truth))
            row.update(f2.ps_geometry_fields(truth, res, ctx))
            rows.append(row)
        except Exception as error:
            rows.append(dict(head, arm=PB16_ARM, status='error', error=repr(error), trace=traceback.format_exc()[-1500:]))
    return rows


def load_context(args):
    ctx = _orig_load_context(args)
    import twofft  # the native directory's module, already imported by base.load_context
    tapchannel.install_general_taps(twofft)
    from native_f1_cap import receive_f1_cap
    ctx.receive_f1_cap = receive_f1_cap
    for name in ('driver_m2.py', 'dpss_rx.py', 'tapchannel.py', 'f1_cap.py', 'native_f1_cap.py', 'driver_f3.py'):
        ctx.sources[name] = base.sha256_file(f2.HERE / name)
    return ctx


f2.parse_args = parse_args
f2.run_cell_f2 = run_cell_m2
f2.load_context = load_context

if __name__ == '__main__':
    f2.main(sys.argv[1:])
