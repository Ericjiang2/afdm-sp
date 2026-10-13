#!/usr/bin/env python
"""C1 V2 mechanism probe of the round-1 law (task 10-08-doppler-cluster; research/c1-round1-loop-theory.md, section 7 "V2" + "V2 amendment").

Question: is the round-1 channel error of the joint loop the independent-error refit law e_ind(v) amplified by a linear self-absorption factor
(1 - c)^-2, with c = kappa beta d (and kappa = w under H_w)?  Per (cell, frame) this driver measures every object of that algebra on ONE
observation; nothing is fitted.  Mechanism probe only (the alternating detector-refit map is the theory's object, not the receiver's dynamics).

Observations are IDENTICAL to driver_c1 SPg_flat (same entropy 129abc..., c1 domain/streams, genie delays, flat prior tau_d = 1/K, K = 8L): the
generator, GenieRefine, eps_of, reliability and the shard/resume/merge logic are imported from driver_c1 / driver_c1i / driver; nothing frozen
is edited.  Default cells: 8 dB, rho {.2,.3,.5} x L {8,24}, frames 600-639.

Per row (arm 'V2'; all internal units: data power pd = .5, pilot power rho/(2(1-rho)); eps metric = ||H - H^||_F^2/N = ||coefficient error||^2):
  Round 1 = the unmodified receiver (pilot-only refit -> native scalar_joint_cols, 20 joint updates), run through interventions._instrumented with
    rounds = 1 (round 1 does not depend on later rounds).  record_states is NOT used: the vector-prior kernel (dpss_rx.scalar_joint_cols) has no state
    recording and the router drops the flag; the final state is read from the identical round arrays r0_gains / r0_mu / r0_variance and
    r0_inference_trace[-1]['data_pseudo_variance'] (= vr = 1/J_x of the last update).
  e_star = eps_of(h*) (= eps_det1), e_ce1 = pilot-only refit error, e_soft / e_true / e_indep = eps of the receiver's own soft refit
    (GenieRefine, fresh instance = the round >= 2 refit: same taps, flat E_l = 1/L) on the same y with (mu*, v*) / (true data, v = 0) /
    (soft symbols of an independent AWGN observation of the true data whose mean reported variance equals mean(v*); SINR by brentq on log q).
    Amendment 2 (A), report-only: e_indep_mse = refit with independent AWGN soft symbols whose TRUE normalised MSE equals vmeas_star, fed the
    reported variance v* of mu* (same refit weights as e_soft); fields indep_mse_q / indep_mse_snr_db / indep_mse_status, vmeas_indep_mse (check).
  v_meas = normalised true MSE mean|x - mu|^2 / pd of the soft symbols used (mu*: vmeas_star; independent: vmeas_indep).
  d_hat = mean(v*)/vr, w_hat = ||mu*||^2/(||p||^2 + ||mu*||^2), beta_hat = tr[(B^H B + lam I)^-1 B^H B]/K of the refit at (mu*, v*).
  Linear response: 4 seeded complex-Gaussian coefficient-space directions delta_j, |delta_j|^2 = .05 e*; frozen twofft.scalar_joint(gain_mode='fixed',
    20 updates, round-1 prior) at h* +- delta_j; refit with the soft refit; c_hat = mean_j Re<h^(+) - h^(-), delta_j>/(2|delta_j|^2) (c_dirs = the 4 terms).
    one-sided c_plus / c_minus = mean_j Re<h^(+) - h^(0), delta>/|delta|^2 and Re<h^(0) - h^(-), delta>/|delta|^2 (h^(0) = refit at delta = 0).
    delta = 0 control: e_0 (refit of the fixed-gain detector at h*), mu0_nmse = mean|mu(h*) - mu*|^2/pd.
  d_fixed0 = mean(v)/vr of the delta = 0 fixed-gain detector (no gain-variance terms; compare d_hat); e_real_taps = sum_l |a_l|^2/N (= head e_real).
  Report-only R3: r3_alpha = Re<h*, h>/|h*|^2, r3_U = |<h*, h>|^2/|h*|^2, r3_hnorm2 = |h*|^2 (eps metric, same as eps_of).
  Report-only R1: calibration loss max_alpha MI(alpha L) - MI(L) of the clipped round-1 decoder-input LLR, alpha = 4^linspace(-1,1,41); R2: pilot-Gram
    d_p/N, tr Q_p^2/N, retention 1 - 2 d_p/N + tr Q_p^2/N (lam = K(n0 + P_d)) and the equal-Gram values.
Run one process per shard, single thread (launch_c1v2.sh).
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
from scipy.optimize import brentq

import driver as base
import driver_c1 as c1
import driver_c1i as c1i
import dpss_rx
import tapchannel

HERE = base.HERE
V2_ENTROPY = c1i.C1_MAP_ENTROPY  # 129abc3b...: same as c1_boot / c1_map
V2_COMPONENTS = {'indep_noise': 6, 'directions': 7}  # new seed components (c1: 1-3, c1e: 4-5)
N_DIR = 4
D_COEF_L = c1.D_COEF  # K = 8 L
DELTA_FRAC = .05
ALPHA_GRID = 4.0 ** np.linspace(-1., 1., 41)  # alpha = 1 is element 20 exactly
INDEP_LOGQ = (np.log(1e-3), np.log(1e5))
V2_PARAMS = dict(
    pairing='observations identical to driver_c1 SPg_flat (entropy 129abc..., c1 domain/streams, genie delays, flat prior); arm V2 = rounds 1 only',
    round1='interventions._instrumented(rounds=1, iterations=20, gain_mode=joint) with GenieRefine(flat) under dpss_rx.vector_prior; '
           'final (h*, mu*, v*, vr) from r0_gains / r0_mu / r0_variance / r0_inference_trace[-1] (record_states unsupported by the vector kernel)',
    refit='fresh GenieRefine(flat) first call = receiver soft refit (taps c=0, W=2.5, D=8 per genie delay, E_l = 1/L, s2 = noise + mean(v))',
    indep_mse='same AWGN construction and draw w0, q by brentq so that mean|x - mu|^2 = vmeas_star*pd; refit gets v* (amendment 2 A)',
    indep='z = x_true + sqrt(pd/q) w0, w0 CN(0,1) seeded; posterior-mean QPSK soft symbols (messages.marginal, zero prior); log q by brentq in '
          '[ln 1e-3, ln 1e5] s.t. mean(v_rep) = mean(v*)',
    directions='4 complex Gaussian coefficient-space directions, |delta|^2 = .05 e*; seeds SeedSequence(entropy + [C1_DOMAIN, frame, L, 7])',
    linear_response='twofft.scalar_joint gain_mode fixed, 20 iterations, pd = .5, prior = round-1 prior (zeros), channel = refit channel with gains h* +- delta_j',
    definitions='d_hat = mean(v*)/vr; w_hat = ||mu*||^2/(||p||^2+||mu*||^2); beta_hat = tr[(B^H B + lam I)^-1 B^H B]/K at (mu*, v*)',
    report_only='R1 alpha-calibration loss of r0_input_llr (clip 20, alpha*L not re-clipped), R2 pilot-Gram absorption / retention + equal-Gram values',
    seeds='indep noise component 6, directions component 7: SeedSequence(entropy + [C1_DOMAIN, frame, L, comp]) (shared across rho)')
CODE_FILES = ('driver_c1v2.py', 'driver_c1.py', 'driver_c1i.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'arms.py', 'orders.py')
CODE_MODULES = ('twofft', 'native_twofft', 'messages', 'receiver', 'interventions', 'physical')


def md5_file(path):
    digest = hashlib.md5()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def code_md5():
    out = {name: md5_file(HERE / name) for name in CODE_FILES}
    for name in CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = md5_file(module.__file__)
    return out


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--Ls', default='8,24')
    p.add_argument('--rho-list', default='0.2,0.3,0.5')
    p.add_argument('--snr-list', default='8')
    p.add_argument('--frames', type=int, default=40)
    p.add_argument('--frame-offset', type=int, default=600)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=V2_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1v2'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ receiver pieces
class ProbeRefine(c1.GenieRefine):
    """GenieRefine (genie delays, flat prior tau_d = 1/K) that also keeps, per call, the refit channel and the ridge design
    (B^H B, s2, tau) handed to the init_gains hook.  Numerically identical to GenieRefine."""

    def __init__(self, delays, cfg):
        super().__init__(delays, 'flat', cfg)
        self.captured = []
        self.channels = []

    def init_gains(self, des, idx, tau, s2, kept_taps):
        h, Q = super().init_gains(des, idx, tau, s2, kept_taps)
        self.captured.append(dict(BhB=des.BhB.copy(), s2=float(s2), tau=np.asarray(tau, float).copy()))
        return h, Q

    def __call__(self, *args, **kwargs):
        ch, detail = super().__call__(*args, **kwargs)
        self.channels.append(ch)
        return ch, detail


def soft_refit(ctx, obs, genie, cfg, mu, v):
    """The receiver's own soft refit on the observation (fresh instance: first call = the round >= 2 refit for the flat prior).
    Returns (h, snap, captured)."""
    n = len(obs['y'])
    r = ProbeRefine(genie, cfg)
    r(obs['y'], obs['pilot'], np.asarray(mu, complex), np.asarray(v, float), np.zeros(0, int), np.zeros(0), np.zeros(0, complex),
      ctx.system.c1, ctx.system.c2, obs['sigma2'])
    assert len(r.snaps) == 1 and r.snaps[0]['h'].shape == (len(r.captured[0]['tau']),) and n == len(mu)
    return r.snaps[0]['h'].copy(), r.snaps[0], r.captured[0]


def make_channel(ch, gains):
    new = tapchannel.tap_channel_class()(ch.n, ch.c1, ch.c2, ch.delays, ch.dopplers, np.asarray(gains, complex))
    object.__setattr__(new, 'tap_mods', ch.tap_mods)
    return new


def fixed_detect(ctx, obs, ch1, gains, prior):
    """Frozen twofft.scalar_joint(gain_mode='fixed', 20 updates) at the given gains: (mu, v) of the soft symbols."""
    import twofft
    o = twofft.scalar_joint(obs['y'], obs['pilot'], make_channel(ch1, gains), obs['sigma2'], pd=1. - ctx.system.rho, prior=prior,
                            iterations=20, gain_mode='fixed')
    return np.asarray(o['mu'], complex), np.asarray(o['variance'], float), float(o['trace'][-1]['data_pseudo_variance'])


def link_geometry(snap, gains, a_true, n):
    """R3 (report-only): eps-metric inner product of the estimate with the truth.  alpha = Re<h*, h>/|h*|^2, U = |<h*, h>|^2/|h*|^2,
    |h*|^2 (LMMSE orthogonality would give alpha = 1, |h*|^2 = U = E_real - e*)."""
    ip, nh = 0j, 0.
    gains = np.asarray(gains, complex)
    for delay, sl in snap['taps']:
        ah = snap['M'][:, sl] @ gains[sl]
        ip += np.vdot(ah, a_true[delay])
        nh += float(np.vdot(ah, ah).real)
    ip, nh = ip / n, nh / n
    return dict(r3_alpha=float(ip.real / nh), r3_U=float(abs(ip) ** 2 / nh), r3_hnorm2=nh, r3_ip_re=float(ip.real), r3_ip_im=float(ip.imag))


def indep_soft(x_int, w0, target, pd, kind='rep'):
    """Soft symbols of an independent AWGN observation z = x + sqrt(pd/q) w0 (posterior mean, QPSK, zero prior).  q by brentq on log q such that
    kind 'rep': mean reported variance mean(v) = target (e_indep);  kind 'mse': true error mean|x - mu|^2 = target (e_indep_mse, amendment 2).
    Returns (mu, v, q, status)."""
    from messages import alphabet, marginal
    if kind not in ('rep', 'mse'):
        raise ValueError(kind)
    a, _ = alphabet(pd)
    prior = np.zeros(2 * len(x_int))

    def soft(logq):
        s2 = pd / np.exp(logq)
        z = x_int + np.sqrt(s2) * w0
        _, _, mu, v = marginal(-np.abs(z[:, None] - a) ** 2 / s2, prior, pd)
        return mu, v

    def f(logq):
        mu, v = soft(logq)
        return (float(np.mean(v)) if kind == 'rep' else float(np.mean(np.abs(x_int - mu) ** 2))) - target

    lo, hi = INDEP_LOGQ
    flo, fhi = f(lo), f(hi)
    if flo < 0.:
        logq, status = lo, 'clipped_low'
    elif fhi > 0.:
        logq, status = hi, 'clipped_high'
    else:
        logq, status = float(brentq(f, lo, hi, xtol=1e-13, rtol=1e-13, maxiter=200)), 'ok'
    mu, v = soft(logq)
    return mu, v, float(np.exp(logq)), status


def beta_of(cap):
    """tr[(B^H B + lam I)^-1 B^H B]/K for a captured ridge design (flat prior: lam = s2/tau constant)."""
    lam = cap['s2'] / cap['tau']
    assert np.ptp(lam) <= 1e-12 * float(lam.max()), 'flat prior expected'
    g = np.maximum(np.linalg.eigvalsh(cap['BhB']), 0.)
    return float(np.mean(g / (g + lam[0]))), g, float(lam[0])


def v2_rng(entropy_hex, frame, L, component):
    return np.random.default_rng(np.random.SeedSequence(base.entropy_words(entropy_hex) + [c1.C1_DOMAIN, int(frame), int(L), int(component)]))


def finite(**kw):
    out = {}
    for k, v in kw.items():
        if isinstance(v, (list, tuple, np.ndarray)):
            out[k] = [float(x) for x in np.asarray(v, float).ravel()]
            ok = np.isfinite(out[k]).all()
        elif isinstance(v, (str, bool, int)) or v is None:
            out[k] = v
            ok = True
        else:
            out[k] = float(v)
            ok = np.isfinite(out[k])
        if not ok:
            raise FloatingPointError(f'nonfinite {k}')
    return out


# ------------------------------------------------------------------------ the probe
def run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho):
    """One (cell, frame): round 1 + all V2 measurements.  Truth enters only after the receiver has finished."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    n = len(obs['y'])
    pd = 1. - ctx.system.rho
    coded = truth['coded']
    refiner = ProbeRefine(genie, cfg)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1v2_round1', rounds=1, iterations=20,
                                            gain_mode='joint', refine_override=refiner)
    seconds_r1 = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != 1 or len(refiner.channels) != 1:
        raise RuntimeError(f'expected 1 refit, got {len(refiner.snaps)}')
    snap1, ch1, cap1 = refiner.snaps[0], refiner.channels[0], refiner.captured[0]
    h_star = np.asarray(ar['r0_gains'], complex)
    mu_star = np.asarray(ar['r0_mu'], complex)
    v_star = np.asarray(ar['r0_variance'], float)
    vr = float(ar['r0_inference_trace'][-1]['data_pseudo_variance'])
    prior1 = np.asarray(result.trace['initial_state']['prior'], float)
    diag = c1.reliability(ctx, ar, coded)  # r1_ll_in, r1_ll_app, r1_mabs_*, r1_syn, r1_cerr
    K = len(h_star)
    e_ce1 = c1.eps_of(snap1, snap1['h'], a_true, n)
    e_star = c1.eps_of(snap1, h_star, a_true, n)
    pilot = obs['pilot']
    if not (np.isfinite(vr) and vr > 0 and K == len(cap1['tau']) == D_COEF_L * L and not prior1.any()):
        raise RuntimeError('unexpected round-1 state')

    # ---- refits on the same y
    h_soft, _, cap_soft = soft_refit(ctx, obs, genie, cfg, mu_star, v_star)
    h_true, _, _ = soft_refit(ctx, obs, genie, cfg, x_int, np.zeros(n))
    g = v2_rng(entropy, frame, L, V2_COMPONENTS['indep_noise'])
    w0 = (g.standard_normal(n) + 1j * g.standard_normal(n)) / np.sqrt(2.)
    vbar_star = float(np.mean(v_star))
    mu_i, v_i, q_ind, ind_status = indep_soft(x_int, w0, vbar_star, pd)
    h_ind, _, _ = soft_refit(ctx, obs, genie, cfg, mu_i, v_i)
    vmeas_star = float(np.mean(np.abs(x_int - mu_star) ** 2) / pd)
    mu_m, v_m, q_mse, mse_status = indep_soft(x_int, w0, vmeas_star * pd, pd, kind='mse')  # amendment 2 (A): same true MSE as mu*
    h_ind_mse, _, _ = soft_refit(ctx, obs, genie, cfg, mu_m, v_star)  # reported variance of mu* (same refit weights as e_soft)
    e_indep_mse = c1.eps_of(snap1, h_ind_mse, a_true, n)
    e_soft = c1.eps_of(snap1, h_soft, a_true, n)
    e_true = c1.eps_of(snap1, h_true, a_true, n)
    e_indep = c1.eps_of(snap1, h_ind, a_true, n)
    vmeas_indep = float(np.mean(np.abs(x_int - mu_i) ** 2) / pd)

    # ---- amendment definitions
    d_hat = vbar_star / vr
    w_hat = float(np.vdot(mu_star, mu_star).real / (np.vdot(pilot, pilot).real + np.vdot(mu_star, mu_star).real))
    beta_hat, g_soft, lam_soft = beta_of(cap_soft)

    # ---- linear response (fixed-gain detector -> soft refit)
    mu0, v0, vr0 = fixed_detect(ctx, obs, ch1, h_star, prior1)
    h0, _, _ = soft_refit(ctx, obs, genie, cfg, mu0, v0)
    e_0 = c1.eps_of(snap1, h0, a_true, n)
    mu0_nmse = float(np.mean(np.abs(mu0 - mu_star) ** 2) / pd)
    h0_vs_soft = float(np.vdot(h0 - h_soft, h0 - h_soft).real / e_soft)
    g = v2_rng(entropy, frame, L, V2_COMPONENTS['directions'])
    raw = (g.standard_normal((N_DIR, K)) + 1j * g.standard_normal((N_DIR, K))) / np.sqrt(2.)
    deltas = raw * (np.sqrt(DELTA_FRAC * e_star) / np.linalg.norm(raw, axis=1))[:, None]
    metric_err = 0.
    c_dirs, c_pl, c_mi, v_pm = [], [], [], []
    for dj in deltas:
        eps_metric = sum(float(np.linalg.norm(snap1['M'][:, sl] @ dj[sl]) ** 2) for _, sl in snap1['taps']) / n  # eps-metric norm of delta
        metric_err = max(metric_err, abs(eps_metric / float(np.vdot(dj, dj).real) - 1.))
        resp = []
        for sign in (1., -1.):
            mu_s, v_s, _ = fixed_detect(ctx, obs, ch1, h_star + sign * dj, prior1)
            h_s, _, _ = soft_refit(ctx, obs, genie, cfg, mu_s, v_s)
            resp.append(h_s)
            v_pm.append(float(np.mean(v_s)))
        dd = float(np.vdot(dj, dj).real)
        c_dirs.append(float(np.real(np.vdot(dj, resp[0] - resp[1])) / (2. * dd)))
        c_pl.append(float(np.real(np.vdot(dj, resp[0] - h0)) / dd))  # one-sided responses about the delta = 0 refit; c_dirs = their mean
        c_mi.append(float(np.real(np.vdot(dj, h0 - resp[1])) / dd))
    c_hat = float(np.mean(c_dirs))

    # ---- report-only R1 / R2
    llr = np.clip(np.asarray(ar['r0_input_llr'], float), -20., 20.)
    mi = np.array([1. - ctx.arms.logloss_bits(a * llr, coded) for a in ALPHA_GRID])
    assert ALPHA_GRID[20] == 1. and abs(mi[20] - (1. - diag['r1_ll_in'])) < 1e-12
    beta_p, g_p, lam_p = beta_of(cap1)
    gp = g_p / (g_p + lam_p)
    p_pow = float(np.vdot(pilot, pilot).real / n)
    beta_eq = n * p_pow / (n * p_pow + K * (obs['sigma2'] + pd))
    kk = K / n
    r2 = dict(r2_dp_over_n=float(gp.sum() / n), r2_trq2_over_n=float((gp ** 2).sum() / n),
              r2_retention=float(1. - 2. * gp.sum() / n + (gp ** 2).sum() / n), r2_beta_eq=beta_eq, r2_dp_eq=kk * beta_eq,
              r2_retention_eq=1. - kk * beta_eq * (2. - beta_eq), r2_lam_pilot=lam_p, r2_g_min=float(g_p.min()), r2_g_max=float(g_p.max()),
              beta_hat_pilot=beta_p)
    seconds = time.perf_counter() - start
    fields = finite(
        n_cols=K, e_star=e_star, e_ce1=e_ce1, e_soft=e_soft, e_true=e_true, e_indep=e_indep, e_indep_mse=e_indep_mse, e_0=e_0,
        vmeas_star=vmeas_star, vmeas_indep=vmeas_indep, vrep_star=vbar_star / pd, vrep_indep=float(np.mean(v_i)) / pd,
        indep_q=q_ind, indep_snr_db=10. * np.log10(q_ind), indep_status=ind_status,
        vmeas_indep_mse=float(np.mean(np.abs(x_int - mu_m) ** 2) / pd), vrep_indep_mse=float(np.mean(v_m)) / pd, indep_mse_q=q_mse,
        indep_mse_snr_db=10. * np.log10(q_mse), indep_mse_status=mse_status,
        vr=vr, d_hat=d_hat, w_hat=w_hat, beta_hat=beta_hat, lam_soft=lam_soft, s2_soft=cap_soft['s2'],
        c_hat=c_hat, c_dirs=c_dirs, c_plus=float(np.mean(c_pl)), c_minus=float(np.mean(c_mi)), c_sd=float(np.std(c_dirs, ddof=1)), delta_norm2=DELTA_FRAC * e_star, delta_metric_err=metric_err,
        mu0_nmse=mu0_nmse, h0_vs_soft=h0_vs_soft, vr_fixed0=vr0, d_fixed0=float(np.mean(v0)) / vr0,
        e_real_taps=float(sum(float(np.vdot(a, a).real) for a in a_true.values()) / n), vbar_pm_mean=float(np.mean(v_pm)),
        r1_mi=float(mi[20]), r1_mi_best=float(mi.max()), r1_alpha_best=float(ALPHA_GRID[int(np.argmax(mi))]),
        r1_calib_loss=float(mi.max() - mi[20]),
        eps_det1=e_star, eps_ce1=e_ce1, mu_ms=float(np.mean(np.abs(mu_star) ** 2)), seconds_round1=seconds_r1, seconds_probe=seconds,
        **r2, **link_geometry(snap1, h_star, a_true, n))
    return dict(decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds_r1, triggered=None,
                diag=dict(diag, **fields))


def run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho):
    genie = sorted(set(int(x) for x in truth['l_i']))
    try:
        res = run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho)
        return [dict(head, arm='V2', status='ok', **base.score(ctx, res, truth), **res['diag'])]
    except Exception as error:  # recorded, never silently dropped
        return [dict(head, arm='V2', status='error', error=repr(error), trace=traceback.format_exc()[-1500:])]


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    Ls = base.parse_list(args.Ls, int)
    rhos = base.parse_list(args.rho_list, float)
    if any(L < 1 or L > 101 for L in Ls) or not args.frames or not args.entropy_hex:
        raise ValueError('bad --Ls / --frames / --entropy-hex')
    base.entropy_words(args.entropy_hex)
    snr_cells = [int(round(float(x) * 100)) for x in base.parse_list(args.snr_list, str)]
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    ctx.sources['driver_c1v2.py'] = base.sha256_file(HERE / 'driver_c1v2.py')
    ctx.sources['driver_c1i.py'] = base.sha256_file(HERE / 'driver_c1i.py')
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, v2=V2_PARAMS, v2_components=V2_COMPONENTS,
                  v2_n_dir=N_DIR, v2_delta_frac=DELTA_FRAC, v2_alpha_grid=[float(a) for a in ALPHA_GRID], code_md5=code_md5(),
                  entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest, dpss_defaults=dpss_rx.CFG_DEFAULT)
    config_path = out / f'config_shard{args.shard:03d}.json'
    comparable = {k: v for k, v in config.items() if k not in ('environment',)}
    if config_path.exists():
        previous = json.loads(config_path.read_text())
        if previous.get('_config_cmp') != json.loads(json.dumps(comparable, default=base.to_jsonable)):
            raise ValueError('resume refused: configuration differs from the existing shard')
    else:
        config_path.write_text(json.dumps(dict(_argv=list(argv), _config=config, _config_cmp=comparable),
                                          indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    jsonl = out / f'rows_shard{args.shard:03d}.jsonl'
    done = c1i.load_done(jsonl, ['V2'])
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            for L in Ls:
                cfg_name = f'L{L:02d}'
                todo = [(rho, s) for rho in rhos for s in snr_cells if (cfg_name, int(round(rho * 1000)), s, frame) not in done]
                if not todo:
                    continue
                paths = c1.draw_c1_paths(entropy, frame, L)
                H = c1.c1_physical_h(ctx, paths)
                a_true = c1.tap_sequences(paths, n)
                e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                pair = None
                for rho in rhos:
                    todo_r = [s for (r, s) in todo if r == rho]
                    if not todo_r:
                        continue
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    raw_base, diag_base = c1.c1_base(ctx, msg, paths, H)
                    for snr_centi in todo_r:
                        raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                        obs = base.observe(raw, rho, snr_centi / 100)
                        truth = base.truth_from_raw(raw, diag_base)
                        fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                        if pair is None:
                            pair = fp
                        assert fp == pair, 'pairing across rho/snr broken'
                        mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                        if frame_fp is None:
                            frame_fp = mfp
                        assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                        x_int = np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))  # true data in the receiver's internal units (power .5)
                        assert np.isclose(float(np.mean(np.abs(x_int) ** 2)), .5, rtol=1e-9)
                        head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                        rows = run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho)
                        base.append_rows(handle, rows)
                        n_cells += 1
                        r = rows[0]
                        print(f'[{time.perf_counter() - started:8.1f}s] c1v2 L={L} rho={rho} snr={snr_centi} frame={frame} ' +
                              (f"e*={r['e_star']:.4f} e_soft={r['e_soft']:.4f} e_indep={r['e_indep']:.4f} e_true={r['e_true']:.4f} "
                               f"c={r['c_hat']:.3f} d={r['d_hat']:.3f} w={r['w_hat']:.3f} beta={r['beta_hat']:.3f} t={r['seconds_probe']:.1f}s"
                               if r['status'] == 'ok' else f"ERROR {r['error']}"), flush=True)
    rows_all = [json.loads(x) for x in jsonl.read_text().splitlines() if x.strip()]
    (out / f'results_shard{args.shard:03d}.json').write_text(json.dumps(dict(
        _argv=list(argv), _config=config, shard=args.shard, nshard=args.nshard,
        cells_run_this_invocation=n_cells, n_rows=len(rows_all),
        n_error_rows=sum(r['status'] != 'ok' for r in rows_all),
        rows_sha256=base.sha256_file(jsonl), wall_seconds=time.perf_counter() - started),
        indent=1, default=base.to_jsonable, allow_nan=False) + '\n')
    print(f'shard {args.shard} done: {len(rows_all)} rows', flush=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    args = parse_args(argv)
    if args.mode == 'merge':
        base.merge(args, argv)
    else:
        run_shard(args, argv)


if __name__ == '__main__':
    main()
