#!/usr/bin/env python
"""C1 R2 run: the receiver's own symbol errors in the plain refit, D_reg (task 10-08-doppler-cluster; research/c1-round2-own-symbol-theory.md, section 4 "R2 run", FROZEN).

Same 10 cells and entropy as the J / J12 runs, fresh frames 680-719 (unseen).  Observations, round-1 call, h_o (truth on the DPSS basis), h_S (plain soft refit on (m_T, v_T)),
h_I (matched-true-MSE independent refit with v_T, seed component 6) and the J12 scalars are exactly those of driver_c1j12.py (same code path, same seeds); the 80-step
recursion of J12 is not repeated.  Internal units, eps metric = coefficient norm.
Exact split of the plain refit (spec section 1), common ridge lam = K (n0 + mean v_T) = lam_soft, B_X = B(p + m_X), Q_X = B_X^H B_X + lam I, R_X = P_perp Q_X^-1 B_X^H,
X in {S (own m_T), I (independent)}, true symbols x = p + d, e_X = d - m_X, H_o = H(h_o):
  n_X = R_X w (thermal noise: the frame's actual draw, regenerated from the driver_c1 seed path c1_rng(entropy, frame, 0, noise) and checked equal to the generator's draw),
  g_X = R_X H_o e_X (H_o e_X = B(e_X) h_o),  b_X = -lam P_perp Q_X^-1 h_o,  m_X = R_X r_mis (r_mis = (H_true - H_o) x, built independently from the misfit tap sequences),
  and P_perp (h_X - h_o) = n_X + g_X + b_X + m_X (split_resid_X).  Reconstruction check: rec_err = max |Y - B(x) h_o - w - r_mis| / max |Y| (time domain; Y = IDAFT(y)).
Per frame also Delta_T = P_perp (h_T - h_o); gram_rel = |Q_S - Q_I|_F/|Q_I|_F (A1); real-coefficient least squares g_S = -alpha n_S + gamma Delta_T + r_S (columns [-n_S, Delta_T] in
stacked re/im coordinates; alpha, gamma, rS2 = |r_S|^2) and the same for g_I (control: alpha_I, gamma_I, rI2); the J-run M4 absorption measurements (d_span, d_abs: same procedure and seed
components 9, 10 as driver_c1jfp.py); d_hat = mean(v_T)/vr, beta_hat (soft refit at (m_T, v_T)); J12 scalars z2, zu2, u2, zw2, w2, uw2, eperp_{I,S,T}, j12_resid.
Amendment (spec section 6): fixed-gain detector m_F(h) (v2.fixed_detect, 20 updates, same Y) at h_o and at h_T; g_0 = R_S H_o (d - m_F(h_o)), g_img = R_S H_o (m_F(h_o) - m_F(h_T)),
g_det = R_S H_o (m_F(h_T) - m_T), P_perp-projected like g_S, with g_0 + g_img + g_det = g_S (gsum_resid <= 1e-10); nmse of m_F(h_o), m_F(h_T), m_T against the true data.
Saved vectors (re/im lists, rows stay remote): vec_{hT,hS,hI,ho} and the P_perp-projected vec_{nS,nI,gS,gI,bS,bI,mS,mI,dT,g0,gimg,gdet}.
Run one process per shard, single thread (launch_c1r2.sh).
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
import driver_c1jfp as J
import driver_c1j12 as J12
import dpss_rx
import tapchannel

HERE = base.HERE
R2_PARAMS = dict(
    pairing='observations identical to the J / J12 runs on frames 680-719 (same 10 cells, entropy 129abc..., same seed components)',
    split='P_perp(h_X - h_o) = n_X + g_X + b_X + m_X with R_X = P_perp Q_X^-1 B_X^H, lam = lam_soft, B_X = ops.B(p + m_X); w regenerated from c1_rng(entropy, frame, 0, noise)',
    misfit='r_mis = IDAFT(tap_apply(TapChannel(a_l - M_l h_o,l), p + d)); reconstruction Y - B(x) h_o - w - r_mis',
    ls='real-coefficient least squares of g_X on [-n_X, Delta_T] (stacked re/im): g_X = -alpha n_X + gamma Delta_T + r_X',
    absorption='J-run M4 procedure (driver_c1jfp.py) with the same seed components 9 (span delta_c) and 10 (white dy)',
    amendment='section 6: g_S = g_0 + g_img + g_det via fixed-gain detector at h_o and h_T (v2.fixed_detect) through R_S H_o')
CODE_FILES = ('driver_c1r2.py', 'driver_c1j12.py', 'driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1.py', 'driver_c1i.py', 'driver.py', 'dpss_rx.py', 'tapchannel.py',
              'arms.py', 'orders.py')


def code_md5():
    out = {name: v2.md5_file(HERE / name) for name in CODE_FILES}
    for name in v2.CODE_MODULES:
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__file__', None):
            out[f'{name}.py'] = v2.md5_file(module.__file__)
    return out


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--mode', choices=('generate', 'merge'), required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--project', type=Path, default=HERE.parents[1])
    p.add_argument('--native-dir', default='sp_afdm_native_joint_reviewed_20260921')
    p.add_argument('--baseline-dir', default='sp_afdm_frozen_reviewed_20260921')
    p.add_argument('--cells', default=J.DEFAULT_CELLS, help='comma list snr_db:rho:L')
    p.add_argument('--frames', type=int, default=40)
    p.add_argument('--frame-offset', type=int, default=680)
    p.add_argument('--shard', type=int, default=0)
    p.add_argument('--nshard', type=int, default=1)
    p.add_argument('--entropy-hex', default=v2.V2_ENTROPY)
    p.add_argument('--m2-config', type=Path, default=HERE / 'out' / 'm2_dev_exp' / 'frozen_m2_config.json')
    p.add_argument('--m2-config-sha256', default=c1.M2_CONFIG_SHA256)
    args = p.parse_args(argv)
    args.channel_model = 'c1r2'  # base.fingerprint keys cluster params on 'clustered' only
    return args


def ls_fit(g, n_vec, d_vec):
    """Real-coefficient least squares g = -alpha n + gamma d + r (complex vectors in stacked re/im coordinates)."""
    A = np.column_stack([np.concatenate([-n_vec.real, -n_vec.imag]), np.concatenate([d_vec.real, d_vec.imag])])
    y = np.concatenate([g.real, g.imag])
    coef = np.linalg.lstsq(A, y, rcond=None)[0]
    r = y - A @ coef
    K = len(g)
    return float(coef[0]), float(coef[1]), float(np.dot(r, r)), r[:K] + 1j * r[K:]


# ------------------------------------------------------------------------ the probe
def run_probe(ctx, obs, truth, x_int, noise_gen, genie, cfg, a_true, entropy, frame, L, rho, snr_db):
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
        result = ctx.wrappers._instrumented(ctx.native, obs, ctx.system, ctx.code, arm='c1r2_round1', rounds=1, iterations=J.T_INNER,
                                            gain_mode='joint', refine_override=refiner)
    seconds_r1 = time.perf_counter() - start
    d, ar = result.decoder, result.arrays
    if len(refiner.snaps) != 1 or len(refiner.channels) != 1:
        raise RuntimeError(f'expected 1 refit, got {len(refiner.snaps)}')
    snap1, ch1, cap1 = refiner.snaps[0], refiner.channels[0], refiner.captured[0]
    h_T = np.asarray(ar['r0_gains'], complex)
    mu_star = np.asarray(ar['r0_mu'], complex)
    v_star = np.asarray(ar['r0_variance'], float)
    vr = float(ar['r0_inference_trace'][-1]['data_pseudo_variance'])
    prior1 = np.asarray(result.trace['initial_state']['prior'], float)
    diag = c1.reliability(ctx, ar, coded)
    K = len(h_T)
    if not (np.isfinite(vr) and vr > 0 and K == len(cap1['tau']) == c1.D_COEF * L and not prior1.any()):
        raise RuntimeError('unexpected round-1 state')
    e_star = c1.eps_of(snap1, h_T, a_true, n)

    # ---- truth on the DPSS basis, projector
    h_o = np.zeros(K, complex)
    for delay, sl in snap1['taps']:
        h_o[sl] = np.linalg.lstsq(snap1['M'][:, sl], a_true[delay], rcond=None)[0]
    eps_proj = c1.eps_of(snap1, h_o, a_true, n)
    ho2 = float(np.vdot(h_o, h_o).real)

    def P(vec):
        return vec - h_o * (np.vdot(h_o, vec) / ho2)

    # ---- J12 vectors (same code path as driver_c1j12)
    h_S, _, cap_soft = v2.soft_refit(ctx, obs, genie, cfg, mu_star, v_star)
    beta_hat, _, lam_soft = v2.beta_of(cap_soft)
    vbar_star = float(np.mean(v_star))
    vmeas_star = float(np.mean(np.abs(x_int - mu_star) ** 2) / pd)
    g_ = v2.v2_rng(entropy, frame, L, v2.V2_COMPONENTS['indep_noise'])
    w0 = (g_.standard_normal(n) + 1j * g_.standard_normal(n)) / np.sqrt(2.)
    mu_m, v_m, q_mse, mse_status = v2.indep_soft(x_int, w0, vmeas_star * pd, pd, kind='mse')
    h_I = v2.soft_refit(ctx, obs, genie, cfg, mu_m, v_star)[0]
    z, u, w = P(h_I - h_o), P(h_S - h_I), P(h_T - h_S)
    z2, u2, w2 = (float(np.vdot(a_, a_).real) for a_ in (z, u, w))
    zu2, zw2, uw2 = 2. * float(np.vdot(z, u).real), 2. * float(np.vdot(z, w).real), 2. * float(np.vdot(u, w).real)
    eperp_T = float(np.linalg.norm(P(h_T - h_o)) ** 2)
    eperp_S = float(np.linalg.norm(P(h_S - h_o)) ** 2)
    j12_resid = abs(eperp_T - (z2 + zu2 + u2 + zw2 + w2 + uw2)) / z2

    # ---- thermal noise: regenerate the frame's draw from the driver_c1 seed path, build the misfit independently, verify the reconstruction
    rng = c1.c1_rng(entropy, frame, 0, c1.C1_COMPONENTS['noise'])
    N_tot = int(ctx.system.N_total)
    noise_regen = (rng.standard_normal(N_tot) + 1j * rng.standard_normal(N_tot)) / np.sqrt(2.)
    noise_regen_diff = float(np.max(np.abs(noise_regen - noise_gen)))
    ops = J.CodexOps(n, c1_, c2_, ch1.delays, ch1.tap_mods)
    Y = daft(obs['y'], c1_, c2_, True)
    w_time = daft(np.sqrt(n0) * noise_regen, c1_, c2_, True)
    x_tot = pilot + x_int
    delays_s = [int(dl) for dl, _ in snap1['taps']]
    mis_taps = np.column_stack([a_true[dl] - snap1['M'][:, sl] @ h_o[sl] for dl, sl in snap1['taps']])
    ch_mis = tapchannel.make_tap_channel(n, c1_, c2_, delays_s, mis_taps)
    r_mis = daft(tapchannel.tap_apply(ch_mis, x_tot), c1_, c2_, True)
    rec_err = float(np.max(np.abs(Y - ops.B(x_tot) @ h_o - w_time - r_mis)) / np.max(np.abs(Y)))
    mis_energy = float(np.vdot(r_mis, r_mis).real / n)

    # ---- exact split of the two plain refits (spec section 1)
    lam = float(lam_soft)

    def split_refit(mu_x, h_x):
        Bx = ops.B(pilot + mu_x)
        Q = Bx.conj().T @ Bx + lam * np.eye(K)
        e_x = x_int - mu_x
        rhs = np.column_stack([Bx.conj().T @ w_time, Bx.conj().T @ (ops.B(e_x) @ h_o), h_o, Bx.conj().T @ r_mis])
        sol = np.linalg.solve(Q, rhs)
        parts = dict(n=P(sol[:, 0]), g=P(sol[:, 1]), b=-lam * P(sol[:, 2]), m=P(sol[:, 3]))
        resid = float(np.linalg.norm(P(h_x - h_o) - sum(parts.values())) / np.linalg.norm(P(h_x - h_o)))
        return parts, Q, resid

    pS, Q_S, resid_S = split_refit(mu_star, h_S)
    pI, Q_I, resid_I = split_refit(mu_m, h_I)
    gram_rel = float(np.linalg.norm(Q_S - Q_I) / np.linalg.norm(Q_I))
    dT = P(h_T - h_o)
    alpha, gamma, rS2, _ = ls_fit(pS['g'], pS['n'], dT)
    alpha_I, gamma_I, rI2, _ = ls_fit(pI['g'], pI['n'], dT)

    # ---- amendment (spec section 6): counterfactual split of the own-symbol error with the fixed-gain detector m_F(h) (same Y, 20 updates, zero prior)
    mu_Fo = v2.fixed_detect(ctx, obs, ch1, h_o, prior1)[0]
    mu_FT = v2.fixed_detect(ctx, obs, ch1, h_T, prior1)[0]
    B_S = ops.B(pilot + mu_star)
    e_parts = (x_int - mu_Fo, mu_Fo - mu_FT, mu_FT - mu_star)  # g_0, g_img, g_det through R_S H_o
    sol = np.linalg.solve(Q_S, np.column_stack([B_S.conj().T @ (ops.B(e) @ h_o) for e in e_parts]))
    g0, gimg, gdet = P(sol[:, 0]), P(sol[:, 1]), P(sol[:, 2])
    gsum_resid = float(np.linalg.norm(g0 + gimg + gdet - pS['g']) / np.linalg.norm(pS['g']))

    # ---- J-run M4: absorption of in-span / white additive perturbations (fixed-gain detector at h_T)
    n_dy2 = J.DY_FRAC * n0 * n
    g_ = v2.v2_rng(entropy, frame, L, J.JC['span_dc'])
    dc = J.orth_to((g_.standard_normal((J.N_DRAW, K)) + 1j * g_.standard_normal((J.N_DRAW, K))) / np.sqrt(2.), h_T)
    Bs = ops.B(pilot + mu_star)
    dys_span = (Bs @ dc.T).T
    g_ = v2.v2_rng(entropy, frame, L, J.JC['white_dy'])
    dys_abs = (g_.standard_normal((J.N_DRAW, n)) + 1j * g_.standard_normal((J.N_DRAW, n))) / np.sqrt(2.)

    def absorption(dy):
        dy = dy * (np.sqrt(n_dy2) / np.linalg.norm(dy))
        xi = []
        for sign in (1., -1.):
            Yp = Y + sign * dy
            mu_p, _, _ = v2.fixed_detect(ctx, dict(obs, y=daft(Yp, c1_, c2_)), ch1, h_T, prior1)
            xi.append(Yp - ops.B(pilot + mu_p) @ h_T)
        return 1. - float(np.real(np.vdot(2. * dy, xi[0] - xi[1])) / np.vdot(2. * dy, 2. * dy).real)

    d_span_l = [absorption(dy) for dy in dys_span]
    d_abs_l = [absorption(dy) for dy in dys_abs]
    seconds = time.perf_counter() - start

    nrm2 = lambda a_: float(np.vdot(a_, a_).real)  # noqa: E731
    fields = dict(
        n_cols=K, e_star=e_star, eps_det1=e_star, eps_ce1=c1.eps_of(snap1, snap1['h'], a_true, n), eps_proj=eps_proj, htrue2=ho2,
        e_soft=c1.eps_of(snap1, h_S, a_true, n), e_indep_mse=c1.eps_of(snap1, h_I, a_true, n),
        eperp_I=z2, eperp_S=eperp_S, eperp_T=eperp_T, z2=z2, zu2=zu2, u2=u2, zw2=zw2, w2=w2, uw2=uw2, j12_resid=j12_resid,
        noise_regen_diff=noise_regen_diff, rec_err=rec_err, mis_energy=mis_energy, split_resid_S=resid_S, split_resid_I=resid_I, gram_rel=gram_rel,
        alpha=alpha, gamma=gamma, rS2=rS2, alpha_I=alpha_I, gamma_I=gamma_I, rI2=rI2,
        gsum_resid=gsum_resid, g0_2=nrm2(g0), gimg_2=nrm2(gimg), gdet_2=nrm2(gdet),
        mF_o_nmse=float(np.mean(np.abs(x_int - mu_Fo) ** 2) / pd), mF_T_nmse=float(np.mean(np.abs(x_int - mu_FT) ** 2) / pd), mT_nmse=vmeas_star,
        dm_img_nmse=float(np.mean(np.abs(mu_Fo - mu_FT) ** 2) / pd), dm_det_nmse=float(np.mean(np.abs(mu_FT - mu_star) ** 2) / pd),
        nS2=nrm2(pS['n']), nI2=nrm2(pI['n']), gS2=nrm2(pS['g']), gI2=nrm2(pI['g']), dT2=nrm2(dT),
        d_span=float(np.mean(d_span_l)), d_span_sd=float(np.std(d_span_l, ddof=1)), d_abs=float(np.mean(d_abs_l)), d_abs_sd=float(np.std(d_abs_l, ddof=1)),
        beta_hat=beta_hat, d_hat=vbar_star / vr, vmeas_star=vmeas_star, vrep_star=vbar_star / pd, vr=vr, n0=n0, lam_soft=lam,
        vmeas_indep_mse=float(np.mean(np.abs(x_int - mu_m) ** 2) / pd), indep_mse_q=q_mse, indep_mse_status=mse_status,
        seconds_round1=seconds_r1, seconds_probe=seconds)
    fields = v2.finite(**fields)
    vecs = dict(hT=h_T, hS=h_S, hI=h_I, ho=h_o, nS=pS['n'], nI=pI['n'], gS=pS['g'], gI=pI['g'], bS=pS['b'], bI=pI['b'], mS=pS['m'], mI=pI['m'], dT=dT, g0=g0, gimg=gimg, gdet=gdet)
    for name, vec in vecs.items():
        fields.update(v2.finite(**J12.cvec(name, vec)))
    return dict(decoded=d['decoded'], llr=d['incoming_llr'], iters=int(d['iterations']), seconds=seconds_r1, triggered=None, diag=dict(diag, **fields))


def run_cell(ctx, obs, truth, x_int, noise_gen, head, a_true, cfg, entropy, frame, L, rho, snr_db):
    genie = sorted(set(int(x) for x in truth['l_i']))
    try:
        res = run_probe(ctx, obs, truth, x_int, noise_gen, genie, cfg, a_true, entropy, frame, L, rho, snr_db)
        return [dict(head, arm='R2', status='ok', **base.score(ctx, res, truth), **res['diag'])]
    except Exception as error:  # recorded, never silently dropped
        return [dict(head, arm='R2', status='error', error=repr(error), trace=traceback.format_exc()[-1500:])]


# --------------------------------------------------------------------- shard i/o
def run_shard(args, argv):
    if not 0 <= args.shard < args.nshard:
        raise ValueError('shard out of range')
    cells = J.parse_cells(args.cells)
    if any(L < 1 or L > 101 for _, _, L in cells) or not args.frames or not args.entropy_hex:
        raise ValueError('bad --cells / --frames / --entropy-hex')
    base.entropy_words(args.entropy_hex)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfgs, m2_digest, _ = c1.load_cfgs(args)
    cfg = cfgs['SPg_flat']
    ctx = c1.load_context(args)
    for name in ('driver_c1r2.py', 'driver_c1j12.py', 'driver_c1jfp.py', 'driver_c1v2.py', 'driver_c1i.py'):
        ctx.sources[name] = base.sha256_file(HERE / name)
    _, config = base.fingerprint(args, ctx, argv)
    config.update(c1=c1.C1_PARAMS, c1_domain=c1.C1_DOMAIN, c1_components=c1.C1_COMPONENTS, r2=R2_PARAMS, v2_components=v2.V2_COMPONENTS, jfp_components=J.JC,
                  jfp_n_draw=J.N_DRAW, jfp_dy_frac=J.DY_FRAC, code_md5=code_md5(), entropy_hex=args.entropy_hex, sp_cfg=cfg, m2_config_sha256=m2_digest,
                  dpss_defaults=dpss_rx.CFG_DEFAULT)
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
    done = c1i.load_done(jsonl, ['R2'])
    started = time.perf_counter()
    n_cells = 0
    entropy = args.entropy_hex
    n = int(ctx.system.N_total)
    frames = list(range(args.frame_offset, args.frame_offset + args.frames))[args.shard::args.nshard]
    with jsonl.open('a') as handle:
        for frame in frames:
            frame_fp = None
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
                x_int = np.asarray(raw['data']) / np.sqrt(2. * (1. - rho))
                assert np.isclose(float(np.mean(np.abs(x_int) ** 2)), .5, rtol=1e-9)
                head = c1.head_fields(paths, truth, rho, snr_centi, frame, L)
                rows = run_cell(ctx, obs, truth, x_int, np.asarray(raw['noise']), head, a_true, cfg, entropy, frame, L, rho, snr_centi / 100)
                base.append_rows(handle, rows)
                n_cells += 1
                r = rows[0]
                print(f'[{time.perf_counter() - started:8.1f}s] c1r2 snr={snr_centi} rho={rho} L={L} frame={frame} ' +
                      (f"R_S={r['eperp_S'] / r['z2']:.3f} R_T={r['eperp_T'] / r['z2']:.3f} alpha={r['alpha']:.3f} d_span={r['d_span']:.3f} gamma={r['gamma']:.3f} "
                       f"gram={r['gram_rel']:.3f} rec={r['rec_err']:.1e} noise={r['noise_regen_diff']:.1e} split={r['split_resid_S']:.1e}/{r['split_resid_I']:.1e} "
                       f"j12={r['j12_resid']:.1e} gsum={r['gsum_resid']:.1e} t={r['seconds_probe']:.1f}s" if r['status'] == 'ok' else f"ERROR {r['error']}"), flush=True)
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
