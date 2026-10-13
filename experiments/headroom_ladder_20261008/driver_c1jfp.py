#!/usr/bin/env python
"""C1 J run: round-1 joint fixed point (task 10-08-doppler-cluster; research/c1-joint-fp-theory.md, section 4 "J run", FROZEN).

Per (cell, frame) at the round-1 output (h*, m*, v*) of the unmodified receiver (pilot-only refit -> native scalar_joint_cols, 20 joint updates;
interventions._instrumented with rounds = 1, exactly as driver_c1v2.py).  Observations are those of driver_c1 SPg_flat (entropy 129abc..., c1
domain / streams, genie delays, flat prior tau_d = 1/K, K = 8 L): c1_boot cells (8 dB rho .2/.3/.5 x L 8/24, 11 dB rho .2 x L 8/32) and c1_map cells
(6.5 dB rho .3 x L 16/28) share one generator, so the observation of a given (L, rho, SNR, frame) is the stored one (check S1 in c1jfp_analyze.py).
Frames 640-679.  Internal units (pd = .5, pilot power rho/(2(1-rho)), n0 = sigma2_eff); eps metric = ||H - H^||_F^2/N = ||coefficient error||^2 + misfit.
Code reused by import from driver_c1v2 (ProbeRefine, soft_refit, fixed_detect, indep_soft, beta_of, v2_rng, finite); nothing is edited.

  M0  Codex recursion (eqs 12-20 of CODEX_FIRST_ROUND_INFORMATION_DERIVATION.md) re-implemented from Y alone (own B(x), H^H s; T = 20, damping .3,
      floors 1e-12, start eq 5 and v_0 = P_d, V_0 = 1, s_{-1} = u_{-1} = 0, xbar_{-1} = p, hbar_{-1} = h_0).  q0_* = differences to the kernel's round-1
      output (LLR clipped at 20 vs r0_input_llr, soft mean vs r0_mu, gains vs r0_gains, initial gains vs the refit, every field of the per-iteration trace).
      Final-state scalars v_T, V_T, q_T = |h_T|^2, X_T = |x_T|^2/N, u_T = 1/(n0 + a_T) with a_T = v_T q_T + V_T X_T + V_T v_T (fixed-point value of u).
  M1  FP identity (spec section 1): lamJ = (n0 + V_T v_T)(K + u_T N v_T); h_ridge = (B(p+m*)^H B(p+m*) + lamJ)^-1 B(p+m*)^H Y, fp_rel = |h_ridge - h*|/|h*|.
      Variants (report-only): fp_rel_xbar = regressors xbar_{T-1} with lamJ; fpd_rel = xbar_{T-1} with lamJ' = (n0 + V_{T-1} v_{T-1})(K + u_{T-1} N v_{T-1}).
  M2  Delta = h* - h_true (h_true = per-tap least-squares projection of the true tap sequences on the DPSS columns): e_par = |<h_true, Delta>|^2/|h_true|^2,
      e_perp = |Delta|^2 - e_par, p = <h_true, h*>/|h_true|^2 (h* ~ p h_true; complex: p_re, p_im), eps_proj = projection misfit of the truth.
  M3  c_perp (4 seeded complex directions orthogonal to h*, |delta|^2 = .05 e*), c_par_scale (delta = eps h*) and c_par_phase (delta = i eps h*), same energy;
      fixed-gain detector (twofft.scalar_joint, 20 updates, round-1 prior) at h* +- delta, then the receiver's soft refit (c_*) and, report-only, the
      lamJ ridge on B(p + mu^(+-)) (c_*_ridge).  c = Re<h^(+) - h^(-), delta>/(2|delta|^2).
  M4  absorption: fixed-gain detector at h* on Y' = Y +- dy, xi = Y' - B(p + m(Y')) h*, d = 1 - Re<xi(+) - xi(-), 2 dy>/|2 dy|^2.  d_span: dy = B(p + m*) delta_c,
      delta_c complex orthogonal to h*; d_abs: white CN dy; |dy|^2 = .05 n0 N; 4 draws each (d_span, d_abs = means; *_sd).
  M5  matched independent refit (V2 amendment 2): independent AWGN soft symbols of the same TRUE MSE as m*, refit with the reported variance v* (e_ind_*),
      split as M2; report-only e_ind_*_ridge with the lamJ ridge.
  Scalars: beta_hat (soft refit at (m*, v*)), d_hat = mean(v*)/vr, vmeas_star, vrep_star, n0, e_real, hstar2 = |h*|^2, e_soft, e_star, r1_* and eps_det1/eps_ce1.
Run one process per shard, single thread (launch_c1jfp.sh).
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
import driver_c1 as c1
import driver_c1i as c1i
import driver_c1v2 as v2
import dpss_rx

HERE = base.HERE
DEFAULT_CELLS = '8:0.2:8,8:0.2:24,8:0.3:8,8:0.3:24,8:0.5:8,8:0.5:24,6.5:0.3:16,6.5:0.3:28,11:0.2:8,11:0.2:32'
JC = {'orth_dirs': 8, 'span_dc': 9, 'white_dy': 10}  # new seed components (V2: 6 indep noise, 7 directions)
N_DIR = 4
N_DRAW = 4
DELTA_FRAC = .05
DY_FRAC = .05
T_INNER = 20
DAMP = .3
FLOOR = 1e-12
TRACE_MAP = (('b', 'pseudo_variance_bar'), ('a', 'pseudo_variance_total'), ('u', 'output_precision'), ('vr', 'data_pseudo_variance'),
             ('vq', 'gain_pseudo_variance'), ('V', 'gain_variance'), ('q', 'channel_norm_factor'), ('v_next', 'data_variance'))
JFP_PARAMS = dict(
    pairing='observations identical to driver_c1 SPg_flat (same entropy / c1 domain / streams for the c1_boot and c1_map cells); round 1 only',
    recursion='independent numpy re-implementation of Codex eqs 12-20 from Y, p and the DPSS columns (CodexOps.B, CodexOps.HHs)',
    fp_identity='lamJ = (n0 + V_T v_T)(K + u_T N v_T), u_T = 1/(n0 + a_T), a_T = v_T q_T + V_T X_T + V_T v_T; ridge on B(p + m*)',
    split='h_true = per-tap lstsq projection on the DPSS columns; e_par = |<h_true, Delta>|^2/|h_true|^2; e_perp = |Delta|^2 - e_par',
    probes='fixed-gain twofft.scalar_joint(20) + GenieRefine soft refit (as V2); report-only lamJ ridge refit',
    seeds='SeedSequence(entropy + [C1_DOMAIN, frame, L, comp]): 6 indep noise (V2), 8 orthogonal directions, 9 span delta_c, 10 white dy',
    absorption='Y +- dy in the time domain, y\' = daft(Y\') into the detector; xi = Y\' - B(p + m(Y\')) h*')
CODE_FILES = ('driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1.py', 'driver_c1i.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py', 'arms.py', 'orders.py')


def code_md5():
    out = {name: v2.md5_file(HERE / name) for name in CODE_FILES}
    for name in v2.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = v2.md5_file(module.__file__)
    return out


def parse_cells(text):
    cells = []
    for item in str(text).split(','):
        if item.strip():
            snr, rho, L = item.split(':')
            cells.append((int(round(float(snr) * 100)), float(rho), int(L)))
    if not cells or len(set(cells)) != len(cells):
        raise ValueError('bad --cells')
    return cells


# ----------------------------------------------------------------------------- args
def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--cells', default=DEFAULT_CELLS, help='comma list snr_db:rho:L')
    p.add_argument('--frames', type=int, default=40)
    p.add_argument('--frame-offset', type=int, default=640)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=v2.V2_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1jfp'  # base.fingerprint keys cluster params on 'clustered' only
    return args


# ------------------------------------------------------------------------ operators + Codex recursion (independent of scalar_joint_cols)
class CodexOps:
    """B(x) = [A_1 x, ..., A_K x] (time domain, N x K) and H(h)^H s for the DPSS-BEM columns: A_i x = phase_i * xt[(k - l_i) mod N],
    xt = IDAFT(x), phase_i = cp_{l_i} * m_i (cp = chirp-periodic prefix phase, m_i = DPSS column sqrt(N) v_d)."""

    def __init__(self, n, c1_, c2_, delays, mods):
        from physical import daft
        self.daft, self.n, self.c1, self.c2 = daft, n, c1_, c2_
        delays = np.asarray(delays, int)
        k = np.arange(n)
        wrap = k[:, None] - delays
        cp = np.where(wrap < 0, np.exp(2j * np.pi * c1_ * (n * n + 2 * n * wrap)), 1.)
        self.phase = cp * np.asarray(mods, complex)
        self.phase_conj = self.phase.conj()
        self.idx = wrap % n
        self.groups = [(int(l), np.flatnonzero(delays == l)) for l in np.unique(delays)]

    def B(self, x):
        return self.phase * self.daft(x, self.c1, self.c2, True)[self.idx]

    def HHs(self, h, s):
        w = self.phase_conj * np.conj(h)[None, :]
        g = np.zeros(self.n, complex)
        for l, cols in self.groups:
            g += np.roll(w[:, cols].sum(axis=1) * s, -l)
        return self.daft(g, self.c1, self.c2)


def codex_recursion(ops, Y, p, n0, pd, K, T=T_INNER, damp=DAMP, eps=FLOOR):
    """Codex eqs 5, 12-20 (flat prior tau = 1/K, zero decoder prior).  Returns the final state and per-iteration scalars."""
    n = len(Y)
    c = np.sqrt(pd / 2.)
    Bp = ops.B(p)
    h = np.linalg.solve(Bp.conj().T @ Bp + K * (n0 + pd) * np.eye(K), Bp.conj().T @ Y)  # eq 5: h_0 = W_p Y
    h_init = h.copy()
    m = np.zeros(n, complex)
    x = p.copy()
    v, V = float(pd), 1.
    s = np.zeros(n, complex)
    u = 0.
    xb, hb = p.copy(), h.copy()
    b = a = None
    trace, hist = [], []
    for t in range(T):
        X = float(np.vdot(x, x).real) / n
        q = float(np.vdot(h, h).real)  # G_H = I (orthogonal DPSS columns)
        bt = v * q + V * X
        at = bt + V * v
        b, a = (bt, at) if t == 0 else (damp * bt + (1. - damp) * b, damp * at + (1. - damp) * a)
        s_prev, u_prev = s, u
        s = damp * (Y - ops.B(x) @ h + b * s_prev) / (n0 + a) + (1. - damp) * s_prev  # eq 14
        u = damp / (n0 + a) + (1. - damp) * u_prev
        xb = damp * x + (1. - damp) * xb  # eq 15
        hb = damp * h + (1. - damp) * hb
        Jx = max(u * float(np.vdot(hb, hb).real), eps)  # eq 16
        Jh = max(u * float(np.vdot(xb, xb).real), eps)
        z = Jx * (x - p) + ops.HHs(hb, s) - u * V * xb  # eq 17
        lam = 4. * c * np.concatenate([z.real, z.imag])  # eq 18
        m_new = c * (np.tanh(lam[:n] / 2.) + 1j * np.tanh(lam[n:] / 2.))
        v_new = float(np.mean(np.maximum(pd - np.abs(m_new) ** 2, 0.)))  # eq 19
        h_new = (Jh * h + ops.B(xb).conj().T @ s - u * n * v * hb) / (K + Jh)  # eq 20
        V_new = K / (K + Jh)
        trace.append(dict(b=b, a=a, u=u, vr=1. / Jx, vq=1. / Jh, V=V, q=q, v_next=v_new))
        hist.append(dict(u=u, V=V, v=v, xb=xb.copy(), hb=hb.copy()))
        m, x, h, v, V = m_new, p + m_new, h_new, v_new, V_new
        llr = lam
    return dict(llr=llr, m=m, x=x, h=h, v=v, V=V, h_init=h_init, trace=trace, hist_last=hist[-1])


def ridge(ops, Y, x, lam, K):
    B = ops.B(x)
    return np.linalg.solve(B.conj().T @ B + lam * np.eye(K), B.conj().T @ Y)


def split(delta, h_true):
    """(e_par, e_perp) of delta against the complex span of h_true (eps metric = coefficient norm: orthogonal DPSS columns)."""
    tot = float(np.vdot(delta, delta).real)
    par = float(abs(np.vdot(h_true, delta)) ** 2 / np.vdot(h_true, h_true).real)
    return par, tot - par


def orth_to(vecs, h):
    return vecs - (vecs @ h.conj() / np.vdot(h, h).real)[:, None] * h[None, :]  # remove the complex projection on h from every row


# ------------------------------------------------------------------------ the probe
def run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho, snr_db):
    """One (cell, frame).  Truth enters only after the receiver has finished."""
    assert set(obs) == {'y', 'pilot', 'sigma2'}
    from physical import daft
    n = len(obs['y'])
    pd = 1. - ctx.system.rho
    c1_, c2_ = ctx.system.c1, ctx.system.c2
    coded = truth['coded']
    n0 = float(obs['sigma2'])
    pilot = np.asarray(obs['pilot'], complex)
    refiner = v2.ProbeRefine(genie, cfg)
    start = time.perf_counter()
    with dpss_rx.vector_prior(ctx.native):
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1jfp_round1', rounds=1, iterations=T_INNER,
                                            gain_mode='joint', refine_override=refiner)
    seconds_r1 = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != 1 or len(refiner.channels) != 1:
        raise RuntimeError(f'expected 1 refit, got {len(refiner.snaps)}')
    snap1, ch1, cap1 = refiner.snaps[0], refiner.channels[0], refiner.captured[0]
    h_star = np.asarray(ar['r0_gains'], complex)
    mu_star = np.asarray(ar['r0_mu'], complex)
    v_star = np.asarray(ar['r0_variance'], float)
    trace1 = ar['r0_inference_trace']
    vr = float(trace1[-1]['data_pseudo_variance'])
    prior1 = np.asarray(result.trace['initial_state']['prior'], float)
    diag = c1.reliability(ctx, ar, coded)
    K = len(h_star)
    if not (np.isfinite(vr) and vr > 0 and K == len(cap1['tau']) == c1.D_COEF * L and not prior1.any()):
        raise RuntimeError('unexpected round-1 state')
    e_star = c1.eps_of(snap1, h_star, a_true, n)
    e_ce1 = c1.eps_of(snap1, snap1['h'], a_true, n)

    # ---- truth in coefficient space
    h_true = np.zeros(K, complex)
    for delay, sl in snap1['taps']:
        h_true[sl] = np.linalg.lstsq(snap1['M'][:, sl], a_true[delay], rcond=None)[0]
    eps_proj = c1.eps_of(snap1, h_true, a_true, n)
    delta = h_star - h_true
    e_par, e_perp = split(delta, h_true)
    pcoef = complex(np.vdot(h_true, h_star) / np.vdot(h_true, h_true).real)

    # ---- M0: Codex recursion on the frame's Y vs the kernel
    ops = CodexOps(n, c1_, c2_, ch1.delays, ch1.tap_mods)
    Y = daft(obs['y'], c1_, c2_, True)
    rec = codex_recursion(ops, Y, pilot, n0, pd, K)
    q0_dllr = float(np.max(np.abs(np.clip(rec['llr'], -20., 20.) - np.clip(np.asarray(ar['r0_input_llr'], float), -20., 20.))))
    q0_dm = float(np.max(np.abs(rec['m'] - mu_star)))
    q0_dh = float(np.max(np.abs(rec['h'] - h_star)))
    q0_dh0 = float(np.max(np.abs(rec['h_init'] - snap1['h'])))
    q0_dv = float(abs(rec['v'] - float(np.mean(v_star))))
    q0_trace = 0.
    for t, row in enumerate(rec['trace']):
        for mine, theirs in TRACE_MAP:
            ref = float(trace1[t][theirs])
            q0_trace = max(q0_trace, abs(row[mine] - ref) / max(abs(ref), 1e-300))
    b_builder = float(np.max(np.abs(ops.B(pilot + mu_star) - dpss_rx.Design(obs['y'], pilot, mu_star, [dict(delay=int(t['delay']), c=0., W=t['W'], D=t['D'])
                                                                                                     for t in refiner.log[0]['taps']], c1_, c2_).B)))

    # ---- M1: FP identity
    vT, VT = rec['v'], rec['V']
    qT = float(np.vdot(rec['h'], rec['h']).real)
    XT = float(np.vdot(rec['x'], rec['x']).real) / n
    aT = vT * qT + VT * XT + VT * vT
    uT = 1. / (n0 + aT)
    lamJ = (n0 + VT * vT) * (K + uT * n * vT)
    h_ridge = ridge(ops, Y, pilot + mu_star, lamJ, K)
    hl = rec['hist_last']
    lamJd = (n0 + hl['V'] * hl['v']) * (K + hl['u'] * n * hl['v'])
    h_ridge_d = ridge(ops, Y, hl['xb'], lamJd, K)
    hs_norm = float(np.linalg.norm(h_star))
    fp_rel = float(np.linalg.norm(h_ridge - h_star) / hs_norm)
    fpd_rel = float(np.linalg.norm(h_ridge_d - h_star) / hs_norm)
    fp_rel_xbar = float(np.linalg.norm(ridge(ops, Y, hl['xb'], lamJ, K) - h_star) / hs_norm)  # damped regressors, target lamJ

    # ---- soft refit at (m*, v*) -> beta_hat, e_soft
    h_soft, _, cap_soft = v2.soft_refit(ctx, obs, genie, cfg, mu_star, v_star)
    beta_hat, _, lam_soft = v2.beta_of(cap_soft)
    vbar_star = float(np.mean(v_star))
    d_hat = vbar_star / vr
    vmeas_star = float(np.mean(np.abs(x_int - mu_star) ** 2) / pd)

    # ---- M3: c_perp / c_par probes
    def refits(mu_s, v_s):
        return v2.soft_refit(ctx, obs, genie, cfg, mu_s, v_s)[0], ridge(ops, Y, pilot + mu_s, lamJ, K)

    def response(dl):
        hs, hr = [], []
        for sign in (1., -1.):
            mu_s, v_s, _ = v2.fixed_detect(ctx, obs, ch1, h_star + sign * dl, prior1)
            a_, b_ = refits(mu_s, v_s)
            hs.append(a_)
            hr.append(b_)
        dd = float(np.vdot(dl, dl).real)
        return float(np.real(np.vdot(dl, hs[0] - hs[1])) / (2. * dd)), float(np.real(np.vdot(dl, hr[0] - hr[1])) / (2. * dd))

    g = v2.v2_rng(entropy, frame, L, JC['orth_dirs'])
    raw = (g.standard_normal((N_DIR, K)) + 1j * g.standard_normal((N_DIR, K))) / np.sqrt(2.)
    dirs = orth_to(raw, h_star)
    dirs = dirs * (np.sqrt(DELTA_FRAC * e_star) / np.linalg.norm(dirs, axis=1))[:, None]
    orth_err = float(np.max(np.abs(dirs @ h_star.conj()) / (np.linalg.norm(dirs, axis=1) * hs_norm)))
    cp = [response(dl) for dl in dirs]
    c_perp, c_perp_ridge = float(np.mean([x[0] for x in cp])), float(np.mean([x[1] for x in cp]))
    eps_s = np.sqrt(DELTA_FRAC * e_star) / hs_norm
    c_sc, c_sc_r = response(eps_s * h_star)
    c_ph, c_ph_r = response(1j * eps_s * h_star)

    # ---- M4: absorption of in-span / white additive perturbations with the fixed-gain detector at h*
    n_dy2 = DY_FRAC * n0 * n
    g = v2.v2_rng(entropy, frame, L, JC['span_dc'])
    dc = orth_to((g.standard_normal((N_DRAW, K)) + 1j * g.standard_normal((N_DRAW, K))) / np.sqrt(2.), h_star)
    Bs = ops.B(pilot + mu_star)
    dys_span = (Bs @ dc.T).T
    g = v2.v2_rng(entropy, frame, L, JC['white_dy'])
    dys_abs = (g.standard_normal((N_DRAW, n)) + 1j * g.standard_normal((N_DRAW, n))) / np.sqrt(2.)
    rt_err = 0.

    def absorption(dy):
        nonlocal rt_err
        dy = dy * (np.sqrt(n_dy2) / np.linalg.norm(dy))
        xi = []
        for sign in (1., -1.):
            Yp = Y + sign * dy
            yp = daft(Yp, c1_, c2_)
            rt_err = max(rt_err, float(np.max(np.abs(daft(yp, c1_, c2_, True) - Yp))))
            mu_p, _, _ = v2.fixed_detect(ctx, dict(obs, y=yp), ch1, h_star, prior1)
            xi.append(Yp - ops.B(pilot + mu_p) @ h_star)
        return 1. - float(np.real(np.vdot(2. * dy, xi[0] - xi[1])) / np.vdot(2. * dy, 2. * dy).real)

    d_span_l = [absorption(dy) for dy in dys_span]
    d_abs_l = [absorption(dy) for dy in dys_abs]

    # ---- M5: matched independent refit (V2 amendment 2), split as M2
    g = v2.v2_rng(entropy, frame, L, v2.V2_COMPONENTS['indep_noise'])
    w0 = (g.standard_normal(n) + 1j * g.standard_normal(n)) / np.sqrt(2.)
    mu_m, v_m, q_mse, mse_status = v2.indep_soft(x_int, w0, vmeas_star * pd, pd, kind='mse')
    h_im = v2.soft_refit(ctx, obs, genie, cfg, mu_m, v_star)[0]
    h_im_r = ridge(ops, Y, pilot + mu_m, lamJ, K)
    ei_par, ei_perp = split(h_im - h_true, h_true)
    eir_par, eir_perp = split(h_im_r - h_true, h_true)
    er_par, er_perp = split(h_ridge - h_true, h_true)
    h_soft_par, h_soft_perp = split(h_soft - h_true, h_true)
    seconds = time.perf_counter() - start

    fields = v2.finite(
        n_cols=K, e_star=e_star, eps_det1=e_star, eps_ce1=e_ce1, eps_proj=eps_proj, hstar2=float(np.vdot(h_star, h_star).real), htrue2=float(np.vdot(h_true, h_true).real),
        e_par=e_par, e_perp=e_perp, p_re=pcoef.real, p_im=pcoef.imag, e_split_resid=e_star - (e_par + e_perp + eps_proj),
        e_soft=c1.eps_of(snap1, h_soft, a_true, n), e_soft_par=h_soft_par, e_soft_perp=h_soft_perp, e_ridge=c1.eps_of(snap1, h_ridge, a_true, n),
        e_ridge_par=er_par, e_ridge_perp=er_perp,
        q0_dllr=q0_dllr, q0_dm=q0_dm, q0_dh=q0_dh, q0_dh0=q0_dh0, q0_dv=q0_dv, q0_trace_rel=q0_trace, b_builder_diff=b_builder,
        rec_v=vT, rec_V=VT, rec_q=qT, rec_X=XT, rec_a=aT, rec_u=uT, lamJ=lamJ, lamJ_damped=lamJd, lam_soft=lam_soft,
        fp_rel=fp_rel, fpd_rel=fpd_rel, fp_rel_xbar=fp_rel_xbar, fp_ridge_vs_soft=float(np.linalg.norm(h_ridge - h_soft) / hs_norm),
        c_perp=c_perp, c_perp_dirs=[x[0] for x in cp], c_perp_ridge=c_perp_ridge, c_par_scale=c_sc, c_par_phase=c_ph,
        c_par_scale_ridge=c_sc_r, c_par_phase_ridge=c_ph_r, orth_err=orth_err,
        d_span=float(np.mean(d_span_l)), d_span_sd=float(np.std(d_span_l, ddof=1)), d_abs=float(np.mean(d_abs_l)), d_abs_sd=float(np.std(d_abs_l, ddof=1)),
        absorption_roundtrip_err=rt_err,
        e_indep_mse=c1.eps_of(snap1, h_im, a_true, n), e_ind_par=ei_par, e_ind_perp=ei_perp, e_ind_par_ridge=eir_par, e_ind_perp_ridge=eir_perp,
        vmeas_indep_mse=float(np.mean(np.abs(x_int - mu_m) ** 2) / pd), indep_mse_q=q_mse, indep_mse_status=mse_status,
        beta_hat=beta_hat, d_hat=d_hat, vmeas_star=vmeas_star, vrep_star=vbar_star / pd, vr=vr, n0=n0, mu_ms=float(np.mean(np.abs(mu_star) ** 2)),
        seconds_round1=seconds_r1, seconds_probe=seconds)
    return dict(decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds_r1, triggered=None,
                diag=dict(diag, **fields))


def run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho, snr_db):
    genie = sorted(set(int(x) for x in truth['l_i']))
    try:
        res = run_probe(ctx, obs, truth, x_int, genie, cfg, a_true, entropy, frame, L, rho, snr_db)
        return [dict(head, arm='JFP', status='ok', **base.score(ctx, res, truth), **res['diag'])]
    except Exception as error:  # recorded, never silently dropped
        return [dict(head, arm='JFP', status='error', error=repr(error), trace=traceback.format_exc()[-1500:])]


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells = parse_cells(args.cells)
    if any(L < 1 or L > 101 for _, _, L in cells) or not args.frames or not args.entropy_hex:
        raise ValueError('bad --cells / --frames / --entropy-hex')
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1i.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, jfp=JFP_PARAMS, jfp_components=JC, v2_components=v2.V2_COMPONENTS,
                  jfp_n_dir=N_DIR, jfp_n_draw=N_DRAW, jfp_delta_frac=DELTA_FRAC, jfp_dy_frac=DY_FRAC, code_md5=code_md5(),
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
    done = c1i.load_done(jsonl, ['JFP'])
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None  # (info, noise) fingerprint: identical across L, rho, snr
            chan, base_cache, pair = {}, {}, {}
            for snr_centi, rho, L in cells:
                if (f'L{L:02d}', int(round(rho * 1000)), snr_centi, frame) in done:
                    continue
                if L not in chan:
                    paths = c1.draw_c1_paths(entropy, frame, L)
                    H = c1.c1_physical_h(ctx, paths)
                    a_true = c1.tap_sequences(paths, n)
                    e_taps = sum(float(np.vdot(a, a).real) for a in a_true.values()) / n
                    assert np.isclose(e_taps, float(np.vdot(H, H).real) / n, rtol=1e-8), 'tap-sequence energy identity'
                    chan[L] = (paths, H, a_true)
                paths, H, a_true = chan[L]
                if (L, rho) not in base_cache:
                    msg = c1.c1_message(ctx, entropy, frame, rho)
                    base_cache[(L, rho)] = c1.c1_base(ctx, msg, paths, H)
                raw_base, diag_base = base_cache[(L, rho)]
                raw = base.cluster_at_snr(raw_base, snr_centi / 100)
                obs = base.observe(raw, rho, snr_centi / 100)
                truth = base.truth_from_raw(raw, diag_base)
                fp = (truth['channel_seed'], truth['physical_gains_sha256'])
                assert pair.setdefault(L, fp) == fp, 'pairing across rho/snr broken'
                mfp = (hashlib.sha256(np.ascontiguousarray(truth['info']).tobytes()).hexdigest(), truth['noise_sha256'])
                if frame_fp is None:
                    frame_fp = mfp
                assert mfp == frame_fp, 'message/noise pairing across L/rho/snr broken'
                x_int = np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))  # true data in the receiver's internal units (power .5)
                assert np.isclose(float(np.mean(np.abs(x_int) ** 2)), .5, rtol=1e-9)
                head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                rows = run_cell(ctx, obs, truth, x_int, head, a_true, cfg, entropy, frame, L, rho, snr_centi / 100)
                base.append_rows(handle, rows)
                n_cells += 1
                r = rows[0]
                print(f'[{time.perf_counter() - started:8.1f}s] c1jfp snr={snr_centi} rho={rho} L={L} frame={frame} ' +
                      (f"e*={r['e_star']:.4f} par={r['e_par']:.4f} perp={r['e_perp']:.4f} ind_perp={r['e_ind_perp']:.4f} c_perp={r['c_perp']:.3f} "
                       f"d_span={r['d_span']:.3f} fp={r['fp_rel']:.4f} q0={r['q0_dllr']:.1e}/{r['q0_dh']:.1e} t={r['seconds_probe']:.1f}s"
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
