#!/usr/bin/env python3
"""Idea-funnel Round 2 Batch 1 L2 checks (2026-11-21, runner l, gemini-4-carbon):
  l11      card I-20261121-l11: real decoder soft-feedback 0.1-bin two-candidate blind test (AFDM vs flat-v vs SC-CP vs OFDM + multipath)
  l12      card I-20261121-l12: delay-spread beyond AFDM non-aliasing bound (l_cap 102/240/400) + controlled Δl=205 mod-N resonance vs Δl=185
  l13      card I-20261121-l13: bad-merge challenge (held-out split: 47000..47149 calib, 47150..47449 eval; c10 vs 1st vs 2nd vs full-2path)
  c06cap16 card I-20261121-c06 supplement: max_paths=16 control arm on exact same 600 fractional-delay frames (45000..45599) as out13

Pre-registered criteria & forecasts: ideas/l2/PREDICTIONS_r2_batch1.md
No frozen receiver source files are modified.
"""
import argparse, gzip, json, os, resource, sys, time
from contextlib import contextmanager
from multiprocessing import get_context
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import l2_batch3 as b3  # noqa: E402
from l2_batch3 import setup, SEED, stageA, scale_of  # noqa: E402
from l2_batch7_wideband import to_time, to_daft, wide_path  # noqa: E402

WORKERS = 12

CFG = dict(
    l11=dict(frames=[41000, 41200], scenario='U', rho=100, snr=400, delta_nu=0.1, active_tau=0.2),
    l12=dict(frames=[46000, 46200], scenarios=['G', 'U'], rho=300, snrs=[500, 600, 700], l_caps=[102, 240, 400],
             res_l0=10, res_dl=114, off_dl=94, res_lcap=240, res_jitter=0.20),
    l13=dict(calib_frames=[47000, 47150], eval_frames=[47150, 47450], scenario='G',
             cells=[[150, 450], [250, 450]], bad_loss_thresh=0.08, calib_bad_merge_target=0.08),
    c06cap16=dict(frames=[45000, 45600], scenario='U', rho=250, exp_snrs=[400, 500, 600], max_paths=16),
)


# --------------------------------------------------------------------------- shared helpers
@contextmanager
def with_lmax(C, l_cap):
    """Temporarily set system.l_max_cap and allow pilot_front dictionary_limit=(l_cap+1)*5."""
    import torch
    from physical import Channel
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    ctx = C['ctx']; sys_obj = ctx.system; native = ctx.native
    old_cap = int(sys_obj.l_max_cap); old_front = native.pilot_front

    def pilot_front_ext(observed, system, code):
        n = len(observed['y']); st = time.perf_counter()
        ls = np.repeat(np.arange(int(system.l_max_cap) + 1), 5)
        ks = np.tile(np.arange(-2, 3), int(system.l_max_cap) + 1)
        A = Channel(n, system.c1, system.c2, ls, ks, np.ones(len(ls))).regressors(observed['pilot'])
        est = BaselineInitializer('B0-p2-s0.5', lstsq_driver='gels', dictionary_limit=max(515, len(ls)))
        g, ids = est(torch.tensor(observed['y'], dtype=torch.complex64),
                     torch.tensor(A, dtype=torch.complex64), 40, float(observed['sigma2']))
        ids = np.asarray(ids, int); gs = g.detach().cpu().numpy()[ids].copy()
        return dict(delays=ls[ids], dopplers=ks[ids], gains=gs, mu=np.zeros(n, complex),
                    v=np.full(n, .5), x_soft=np.zeros(n, complex), prior=np.zeros(2 * n),
                    channel_llr=np.zeros(2 * n), sigma_final=float(observed['sigma2']),
                    decoder_records=[], seconds=time.perf_counter() - st, source='observed_pilot_only')

    sys_obj.l_max_cap = int(l_cap)
    native.pilot_front = pilot_front_ext
    try:
        yield
    finally:
        sys_obj.l_max_cap = old_cap
        native.pilot_front = old_front


def distinct_scaled_delays(l_i, old_cap, new_cap):
    if new_cap == old_cap:
        return np.asarray(l_i, dtype=int).copy()
    order = np.argsort(l_i)
    raw = np.round(np.asarray(l_i, float)[order] * (new_cap / float(old_cap))).astype(int)
    raw = np.clip(raw, 0, new_cap)
    for idx in range(1, len(raw)):
        if raw[idx] <= raw[idx - 1]:
            raw[idx] = min(new_cap, raw[idx - 1] + 1)
    for idx in range(len(raw) - 2, -1, -1):
        if raw[idx] >= raw[idx + 1]:
            raw[idx] = max(0, raw[idx + 1] - 1)
    out = np.empty_like(raw)
    out[order] = raw
    return out


# --------------------------------------------------------------------------- 1. Card l11
def job_l11(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l11']
    from messages import moments
    from physical import Channel
    import torch
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer

    s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    raw, obs, truth = stage3.observed(ctx, stage3.inputs(ctx, frame, cfg['scenario'], cfg['rho']), cfg['rho'], cfg['snr'])
    n = len(obs['y']); idx = np.arange(n)
    sc = scale_of(raw, obs)
    d = np.asarray(raw['data'], complex) / sc
    p_af = np.asarray(obs['pilot'], complex)
    s2 = float(obs['sigma2'])
    w_af = np.sqrt(s2) * np.asarray(raw['noise'], complex)

    l_true = np.asarray(truth['l_i'], int)
    nu_true = np.asarray(truth['k_real'], float)
    g_true = np.asarray(truth['g_i'], complex)
    pw = np.abs(g_true) ** 2
    active = pw >= cfg['active_tau'] * s2

    # Unitary bases mapping symbol vector -> time domain:
    # AFDM: B = A^H (to_time); SC-CP: B = I; OFDM: B = F^H (ifft * sqrt(n))
    p_time = to_time(p_af, c1, c2)
    w_time = to_time(w_af, c1, c2)
    d_time_af = to_time(d, c1, c2)

    def apply_time_ch(sig_time, ls, nus, gs):
        out = np.zeros(n, complex)
        for li, nui, gi in zip(ls, nus, gs):
            out += gi * sig_time[(idx - int(li)) % n] * np.exp(2j * np.pi * idx * float(nui) / n)
        return out

    # Gate check: time-domain AFDM channel matches obs['y']
    y_time_af = apply_time_ch(p_time + d_time_af, l_true, nu_true, g_true) + w_time
    gate_err = float(np.linalg.norm(to_daft(y_time_af, c1, c2) - obs['y']) / np.linalg.norm(obs['y']))

    # Round-0 pilot capture comparison: AFDM vs SC-CP with identical time-domain pilot & noise
    y_time_sc = apply_time_ch(p_time + d, l_true, nu_true, g_true) + w_time
    ls_grid = np.repeat(np.arange(int(s.l_max_cap) + 1), 5)
    ks_grid = np.tile(np.arange(-2, 3), int(s.l_max_cap) + 1)
    # Time-domain pilot dictionary (unitary equivalent to AFDM dictionary!)
    Phi_time = np.column_stack([
        p_time[(idx - int(lg)) % n] * np.exp(2j * np.pi * idx * float(kg) / n)
        for lg, kg in zip(ls_grid, ks_grid)
    ])
    est = BaselineInitializer('B0-p2-s0.5', lstsq_driver='gels', dictionary_limit=len(ls_grid))
    g_af0, ids_af0 = est(torch.tensor(y_time_af, dtype=torch.complex64), torch.tensor(Phi_time, dtype=torch.complex64), 40, s2)
    g_sc0, ids_sc0 = est(torch.tensor(y_time_sc, dtype=torch.complex64), torch.tensor(Phi_time, dtype=torch.complex64), 40, s2)

    def top8_recall(g_vec, ids_vec):
        ids_a = np.asarray(ids_vec, int); gs_a = g_vec.detach().cpu().numpy()[ids_a]
        ls_sel = ls_grid[ids_a]; uniq = np.unique(ls_sel)
        en = np.array([np.sum(np.abs(gs_a[ls_sel == dl]) ** 2) for dl in uniq])
        top = set(int(x) for x in uniq[np.argsort(-en)[:8]])
        act_idx = np.flatnonzero(active)
        if len(act_idx) == 0:
            return 1.0
        return float(sum(int(l_true[i]) in top for i in act_idx) / len(act_idx))

    rec_af = top8_recall(g_af0, ids_af0)
    rec_sc = top8_recall(g_sc0, ids_sc0)

    # Run AFDM F0 to get real Round-0 and Round-1 APP moments
    dec, arrays, syn, _ = stageA.f0(C, obs)
    path_rows = {}
    for rtag, app_key in (('r0', 'r0_app'), ('r1', 'r1_app')):
        mu, v, _ = moments(np.clip(arrays[app_key], -20, 20), 0.5)
        v_flat = np.full(n, float(np.mean(v)))
        err_sym = d - mu
        # Precompute basis-transformed error vectors in time domain
        e_af = to_time(err_sym, c1, c2)
        e_sc = err_sym.copy()
        e_of = np.fft.ifft(err_sym) * np.sqrt(n)
        # Full multipath residual in time domain for AFDM (for multipath survival check)
        full_mp_af = apply_time_ch(e_af, l_true, nu_true, g_true)

        scores_acc = {k: 0.0 for k in ('afdm_var', 'afdm_flat', 'sc_var', 'ofdm_var', 'afdm_mp')}
        tie_checks = {'afdm_flat': True, 'sc_var': True}
        wsum = 0.0
        n_act = 0
        for i in np.flatnonzero(active):
            li = int(l_true[i]); nui = float(nu_true[i]); gi = complex(g_true[i]); pwi = float(pw[i])
            rng = np.random.default_rng([SEED, frame, 111, int(i), 0 if rtag == 'r0' else 1])
            wp = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * np.sqrt(s2 / 2.0)
            sgn = 1.0 if rng.integers(0, 2) == 1 else -1.0
            nu_cand = (nui, nui + sgn * cfg['delta_nu'])

            def nll_score(r_time, nu_val, v_vec, inv_basis):
                # B^H Pi_l^H D_nu^H r_time: first undo Doppler D_nu, then undo circular shift Pi_l, then apply B^H
                undop = r_time * np.exp(-2j * np.pi * idx * nu_val / n)
                unshift = undop[(idx + li) % n]
                sym = inv_basis(unshift)
                denom = s2 + pwi * v_vec
                return float(np.sum((np.abs(sym) ** 2) / denom))

            def judge(r_time, v_vec, inv_basis):
                s_true = nll_score(r_time, nu_cand[0], v_vec, inv_basis)
                s_fake = nll_score(r_time, nu_cand[1], v_vec, inv_basis)
                if abs(s_true - s_fake) <= 1e-11 * max(1.0, abs(s_true), abs(s_fake)):
                    return 0.5
                return 1.0 if s_true < s_fake else 0.0

            r_af = gi * e_af[(idx - li) % n] * np.exp(2j * np.pi * idx * nui / n) + wp
            r_sc = gi * e_sc[(idx - li) % n] * np.exp(2j * np.pi * idx * nui / n) + wp
            r_of = gi * e_of[(idx - li) % n] * np.exp(2j * np.pi * idx * nui / n) + wp
            r_mp = full_mp_af + wp

            inv_af = lambda u: to_daft(u, c1, c2)
            inv_sc = lambda u: u
            inv_of = lambda u: np.fft.fft(u) / np.sqrt(n)

            j_af = judge(r_af, v, inv_af)
            j_fl = judge(r_af, v_flat, inv_af)
            j_sc = judge(r_sc, v, inv_sc)
            j_of = judge(r_of, v, inv_of)
            j_mp = judge(r_mp, v, inv_af)

            if j_fl != 0.5:
                tie_checks['afdm_flat'] = False
            if j_sc != 0.5:
                tie_checks['sc_var'] = False

            for k_name, val in (('afdm_var', j_af), ('afdm_flat', j_fl), ('sc_var', j_sc), ('ofdm_var', j_of), ('afdm_mp', j_mp)):
                scores_acc[k_name] += pwi * val
            wsum += pwi; n_act += 1

        path_rows[rtag] = dict(
            wsum=wsum, n_active=n_act, v_mean=float(np.mean(v)), v_std=float(np.std(v)),
            weighted_correct={k: scores_acc[k] for k in scores_acc},
            tie_ok=bool(tie_checks['afdm_flat'] and tie_checks['sc_var']),
        )

    return [dict(frame=frame, gate_err=gate_err, recall_afdm=rec_af, recall_sc=rec_sc, **path_rows)]


# --------------------------------------------------------------------------- 2. Card l12
def eval_four_arms(C, obs, truth, l_cap):
    import stageA2
    ctx, stage3 = C['ctx'], C['stage3']
    full_k = C.setdefault('full', stage3.e1.load_variant())
    with with_lmax(C, l_cap):
        dec_t, arr_t, syn_t, _ = stageA2.f0_true(C, obs, truth, 'true')
        true_err = int(stage3.e1.gd.score(ctx, dec_t['decoded'], truth) > 0)

        dec, arrays, syn, _ = stageA.f0(C, obs)
        f0_err = int(stage3.e1.gd.score(ctx, dec['decoded'], truth) > 0)
        if syn:
            br_cd = stage3.e1.run_branch(ctx, C['cd'], obs, arrays, 'A1')
            cd_err = int(stage3.e1.gd.score(ctx, br_cd['decoder']['decoded'], truth) > 0)
            br_fu = stage3.e1.run_branch(ctx, full_k, obs, arrays, 'A1')
            fu_err = int(stage3.e1.gd.score(ctx, br_fu['decoder']['decoded'], truth) > 0)
        else:
            cd_err = f0_err; fu_err = f0_err
    return dict(trueH=true_err, F0=f0_err, CD=cd_err, FULL=fu_err, syn=int(syn)), arrays


def job_l12(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l12']
    from physical import Channel, projected_variance
    from messages import moments

    s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    rec = dict(frame=frame, partA={}, partB={})

    for scen in cfg['scenarios']:
        base = stage3.inputs(ctx, frame, scen, cfg['rho'])
        rec['partA'][scen] = {}
        for snr in cfg['snrs']:
            raw, obs, truth = stage3.observed(ctx, base, cfg['rho'], snr)
            n = len(obs['y']); sc = scale_of(raw, obs)
            x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / sc
            w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'], complex)
            l_orig = np.asarray(truth['l_i'], int)
            k_orig = np.asarray(truth['k_real'], float)
            g_orig = np.asarray(truth['g_i'], complex)

            rec['partA'][scen][str(snr)] = {}
            for l_cap in cfg['l_caps']:
                l_sc = distinct_scaled_delays(l_orig, 102, l_cap)
                y_sc = Channel(n, c1, c2, l_sc, k_orig, g_orig).apply(x) + w
                if l_cap == 102 and snr == cfg['snrs'][0] and scen == 'G':
                    rec['gate_y102'] = float(np.linalg.norm(y_sc - obs['y']) / np.linalg.norm(obs['y']))
                t_sc = dict(truth, l_i=l_sc)
                o_sc = dict(obs, y=y_sc)
                res4, _ = eval_four_arms(C, o_sc, t_sc, l_cap)
                rec['partA'][scen][str(snr)][str(l_cap)] = res4

            # Part B on scenario G: controlled near-resonance Δl=205 vs off-resonance Δl=185 at l_cap=240
            if scen == 'G':
                order_pw = np.argsort(-np.abs(g_orig) ** 2)
                p0, p1 = int(order_pw[0]), int(order_pw[1])
                bg_idx = [i for i in range(len(l_orig)) if i not in (p0, p1)]
                l_bg_raw = distinct_scaled_delays(l_orig[bg_idx], 102, cfg['res_lcap'])
                forb = {cfg['res_l0'], cfg['res_l0'] + cfg['res_dl'], cfg['res_l0'] + cfg['off_dl']}
                l_bg = []
                for lb in l_bg_raw:
                    cand = int(lb)
                    while cand in forb or cand in l_bg:
                        cand = (cand + 3) % (cfg['res_lcap'] + 1)
                    l_bg.append(cand)

                rng = np.random.default_rng([SEED, frame, 112])
                jit = float(rng.uniform(-cfg['res_jitter'], cfg['res_jitter']))
                # Production system has 2*N*c1 = 9: 9*114 = 1026 == +2 (mod 1024), so dnu = -2 + jit hits 0 (mod 1024)
                nu0 = 1.0 + 0.5 * jit
                nu1 = -1.0 + 1.5 * jit  # nu1 - nu0 = -2.0 + jit, both strictly within [-1.3, +1.3] subset [-1.62, +1.62]

                rec['partB'][str(snr)] = {}
                for tag, dl_val in (('res205', cfg['res_dl']), ('off185', cfg['off_dl'])):
                    l_b = l_orig.copy(); k_b = k_orig.copy()
                    for bi, b_val in zip(bg_idx, l_bg):
                        l_b[bi] = b_val
                    l_b[p0] = cfg['res_l0']; l_b[p1] = cfg['res_l0'] + dl_val
                    k_b[p0] = nu0; k_b[p1] = nu1
                    y_b = Channel(n, c1, c2, l_b, k_b, g_orig).apply(x) + w
                    t_b = dict(truth, l_i=l_b, k_real=k_b)
                    o_b = dict(obs, y=y_b)
                    res_b, arr_b = eval_four_arms(C, o_b, t_b, cfg['res_lcap'])
                    _, v_r1, _ = moments(np.clip(arr_b['r1_app'], -20, 20), 0.5)
                    gam = projected_variance(v_r1, [int(l_b[p0]), int(l_b[p1])], [float(k_b[p0]), float(k_b[p1])], c1)
                    denom = float(np.sqrt(max(gam[0, 0].real * gam[1, 1].real, 1e-30)))
                    res_b['gamma_cross_ratio'] = float(abs(gam[0, 1]) / denom)
                    rec['partB'][str(snr)][tag] = res_b

    return [rec]


# --------------------------------------------------------------------------- 3. Card l13
def op_inner_product(dtau, dnu, n):
    """Exact normalized Hilbert-Schmidt inner product (1/N) tr(A(tau1,nu1)^H A(tau2,nu2))
    where A(tau, nu) applies periodic bandlimited shift tau then midpoint-referenced Doppler nu.
    """
    idx = np.arange(n) - n / 2.0
    kk = np.fft.fftfreq(n, 1.0 / n)
    f_tau = np.mean(np.exp(-2j * np.pi * dtau * kk / n))
    f_nu = np.mean(np.exp(2j * np.pi * dnu * idx / n))
    return complex(f_tau * f_nu)


def exact_bad_loss(g1, tau1, nu1, g2, tau2, nu2, n):
    """Exact continuous single-path approximation loss min_{tau,nu,g} ||H2 - g A(tau,nu)||_F^2 / ||H2||_F^2."""
    from scipy.optimize import minimize
    ip12 = op_inner_product(tau2 - tau1, nu2 - nu1, n)
    norm2 = float(abs(g1) ** 2 + abs(g2) ** 2 + 2.0 * np.real(np.conj(g1) * g2 * ip12))
    if norm2 <= 1e-15:
        return 0.0
    w1 = abs(g1) ** 2 / (abs(g1) ** 2 + abs(g2) ** 2)
    starts = [
        (w1 * tau1 + (1 - w1) * tau2, w1 * nu1 + (1 - w1) * nu2),
        (0.5 * (tau1 + tau2), 0.5 * (nu1 + nu2)),
        (tau1, nu1),
        (tau2, nu2),
    ]
    best_proj = 0.0
    for st in starts:
        def neg_proj(x):
            t, u = float(x[0]), float(x[1])
            c = g1 * op_inner_product(tau1 - t, nu1 - u, n) + g2 * op_inner_product(tau2 - t, nu2 - u, n)
            return -float(abs(c) ** 2)
        res = minimize(neg_proj, x0=np.array(st, float), method='Nelder-Mead',
                       options=dict(xatol=1e-3, fatol=1e-6, maxiter=80))
        best_proj = max(best_proj, -float(res.fun))
    return float(max(0.0, 1.0 - best_proj / norm2))


def atom_and_derivs(S_pilot, kk, idx_c, n, tau, nu, order=2):
    """Continuous pilot atom a(tau, nu) in time domain (midpoint Doppler phase) and its derivatives."""
    shift_f = np.exp(-2j * np.pi * tau * kk / n) * S_pilot
    s_tau = np.fft.ifft(shift_f) * n
    d_nu = np.exp(2j * np.pi * idx_c * nu / n)
    a = d_nu * s_tau
    if order == 0:
        return a
    w_tau = -2j * np.pi * kk / n
    w_nu = 2j * np.pi * idx_c / n
    s_t1 = np.fft.ifft(w_tau * shift_f) * n
    a_t = d_nu * s_t1
    a_u = w_nu * a
    if order == 1:
        return a, a_t, a_u
    s_t2 = np.fft.ifft((w_tau ** 2) * shift_f) * n
    a_tt = d_nu * s_t2
    a_tu = w_nu * a_t
    a_uu = (w_nu ** 2) * a
    return a, a_t, a_u, a_tt, a_tu, a_uu


def fit_single_continuous(r_time, S_pilot, kk, idx_c, n, tau_init, nu_init):
    from scipy.optimize import minimize
    def obj(x):
        a = atom_and_derivs(S_pilot, kk, idx_c, n, float(x[0]), float(x[1]), order=0)
        ip = np.vdot(a, r_time)
        return -float(abs(ip) ** 2 / max(np.vdot(a, a).real, 1e-15))
    res = minimize(obj, x0=np.array([tau_init, nu_init], float), method='Nelder-Mead',
                   options=dict(xatol=2e-3, fatol=1e-5, maxiter=60))
    tau_h, nu_h = float(res.x[0]), float(res.x[1])
    a = atom_and_derivs(S_pilot, kk, idx_c, n, tau_h, nu_h, order=0)
    g_h = complex(np.vdot(a, r_time) / max(np.vdot(a, a).real, 1e-15))
    return tau_h, nu_h, g_h, a


def eval_l13_instance(y_time, p_time, s2, l_max_cap, l_loc_ref, n):
    """Observation-only evaluation returning raw statistics for all 4 arms (no truth read!)."""
    import torch
    from afdm_sp_joint_unrolled.supplement_baselines import BaselineInitializer
    idx = np.arange(n); idx_c = idx - n / 2.0
    kk = np.fft.fftfreq(n, 1.0 / n)
    S_pilot = np.fft.fft(p_time) / n

    # Step 1: Pilot-only front-end atom selection in time domain (midpoint-referenced Doppler)
    ls_grid = np.repeat(np.arange(l_max_cap + 1), 5)
    ks_grid = np.tile(np.arange(-2, 3), l_max_cap + 1)
    Phi = np.column_stack([
        p_time[(idx - int(lg)) % n] * np.exp(2j * np.pi * idx_c * float(kg) / n)
        for lg, kg in zip(ls_grid, ks_grid)
    ])
    est = BaselineInitializer('B0-p2-s0.5', lstsq_driver='gels', dictionary_limit=len(ls_grid))
    g_omp, ids_omp = est(torch.tensor(y_time, dtype=torch.complex64), torch.tensor(Phi, dtype=torch.complex64), 40, s2)
    ids_a = np.asarray(ids_omp, int); gs_a = g_omp.detach().cpu().numpy()[ids_a]
    ls_sel = ls_grid[ids_a]; ks_sel = ks_grid[ids_a]

    # Group selected delays into clusters separated by <= 2 taps
    uniq_l = np.sort(np.unique(ls_sel))
    clusters = []
    for d_val in uniq_l:
        if not clusters or d_val - clusters[-1][-1] > 2:
            clusters.append([int(d_val)])
        else:
            clusters[-1].append(int(d_val))
    # Keep top-8 clusters by energy
    cl_en = []
    for cl in clusters:
        mask = np.isin(ls_sel, cl)
        cl_en.append(float(np.sum(np.abs(gs_a[mask]) ** 2)))
    order_cl = np.argsort(-np.array(cl_en))[:8]
    clusters = [clusters[i] for i in order_cl]

    # Identify candidate cluster covering the target neighborhood (within +-2 taps of l_loc_ref)
    target_idx = None
    for ci, cl in enumerate(clusters):
        if any(abs(d_val - l_loc_ref) <= 2 for d_val in cl):
            target_idx = ci
            break
    if target_idx is None:
        return dict(detected=False)

    # Fit 1 continuous path per cluster (1 coordinate pass)
    cl_fits = []
    for cl in clusters:
        mask = np.isin(ls_sel, cl)
        sub_l = ls_sel[mask]; sub_k = ks_sel[mask]; sub_g = gs_a[mask]
        j_best = int(np.argmax(np.abs(sub_g)))
        t0, u0, gh, ah = fit_single_continuous(y_time, S_pilot, kk, idx_c, n, float(sub_l[j_best]), float(sub_k[j_best]))
        cl_fits.append([t0, u0, gh, ah])

    # Joint LS gain refit across clusters, then subtract background clusters != target_idx
    A_cl = np.column_stack([f[3] for f in cl_fits])
    g_joint = np.linalg.lstsq(A_cl, y_time, rcond=None)[0]
    bg_cols = [i for i in range(len(cl_fits)) if i != target_idx]
    r_loc = y_time - (A_cl[:, bg_cols] @ g_joint[bg_cols] if bg_cols else 0.0)
    tau0, nu0, _, _ = fit_single_continuous(r_loc, S_pilot, kk, idx_c, n, cl_fits[target_idx][0], cl_fits[target_idx][1])

    # Effective noise + data interference variance scale per sample
    var_eff = float(np.vdot(r_loc, r_loc).real / n)
    noise_scale = max(s2 + 0.5, 1e-6)  # observed pilot+data interference floor (~ (1-rho) + sigma2)

    # Arm 1: c10 two-tap gain-ratio phase distance to {0, pi}
    l_int = int(np.clip(np.round(tau0), 0, l_max_cap - 1))
    a_i0 = atom_and_derivs(S_pilot, kk, idx_c, n, float(l_int), nu0, order=0)
    a_i1 = atom_and_derivs(S_pilot, kk, idx_c, n, float(l_int + 1), nu0, order=0)
    a_im1 = atom_and_derivs(S_pilot, kk, idx_c, n, float(max(0, l_int - 1)), nu0, order=0)
    g_pair_p = np.linalg.lstsq(np.column_stack([a_i0, a_i1]), r_loc, rcond=None)[0]
    g_pair_m = np.linalg.lstsq(np.column_stack([a_im1, a_i0]), r_loc, rcond=None)[0]
    g_pair = g_pair_p if abs(g_pair_p[1]) >= abs(g_pair_m[0]) else g_pair_m
    ratio_ph = abs(np.angle(g_pair[1] / (g_pair[0] + 1e-15)))
    c10_stat = float(min(ratio_ph, abs(np.pi - ratio_ph)))

    # Build local derivative subspace at (tau0, nu0), projecting out background atoms
    t_comp_start = time.process_time()
    vecs6 = list(atom_and_derivs(S_pilot, kk, idx_c, n, tau0, nu0, order=2))
    if bg_cols:
        Q_bg, _ = np.linalg.qr(A_cl[:, bg_cols])
        vecs6 = [v - Q_bg @ (Q_bg.conj().T @ v) for v in vecs6]

    Q1, _ = np.linalg.qr(np.column_stack(vecs6[:3]))
    Q2, _ = np.linalg.qr(np.column_stack(vecs6))
    z1 = Q1.conj().T @ r_loc
    z2 = Q2.conj().T @ r_loc

    # Candidate grid in local neighborhood around (tau0, nu0) for compressed & bad-set fitting
    dt_grid = np.linspace(-0.75, 0.75, 9)
    du_grid = np.linspace(-0.75, 0.75, 9)
    cand_pts = [(tau0 + dt, nu0 + du) for dt in dt_grid for du in du_grid]
    cand_atoms = np.column_stack([atom_and_derivs(S_pilot, kk, idx_c, n, t, u, order=0) for t, u in cand_pts])
    if bg_cols:
        cand_atoms = cand_atoms - Q_bg @ (Q_bg.conj().T @ cand_atoms)
    C1 = Q1.conj().T @ cand_atoms  # (3, 81)
    C2 = Q2.conj().T @ cand_atoms  # (6, 81)

    # Best 1-path residual in Q1 and Q2
    c1_norms = np.maximum(np.sum(np.abs(C1) ** 2, axis=0), 1e-15)
    R1_q1 = float(np.vdot(z1, z1).real - np.max(np.abs(C1.conj().T @ z1) ** 2 / c1_norms))
    c2_norms = np.maximum(np.sum(np.abs(C2) ** 2, axis=0), 1e-15)
    R1_q2 = float(np.vdot(z2, z2).real - np.max(np.abs(C2.conj().T @ z2) ** 2 / c2_norms))

    # Best 2-path residual in Q1 and Q2 over symmetric/local pairs around (tau0, nu0)
    pair_specs = []
    for dtau in (0.25, 0.45, 0.65, 0.85):
        for dnu in (-0.8, -0.4, 0.0, 0.4, 0.8):
            for sh_t in (-0.15, 0.0, 0.15):
                pair_specs.append((tau0 + sh_t - 0.5 * dtau, nu0 - 0.5 * dnu,
                                   tau0 + sh_t + 0.5 * dtau, nu0 + 0.5 * dnu, dtau, dnu))

    Rstar_q1 = R1_q1; Rstar_q2 = R1_q2; Rbad_q2 = float(np.vdot(z2, z2).real)
    for t1, u1, t2, u2, dtau, dnu in pair_specs:
        a1 = atom_and_derivs(S_pilot, kk, idx_c, n, t1, u1, order=0)
        a2 = atom_and_derivs(S_pilot, kk, idx_c, n, t2, u2, order=0)
        if bg_cols:
            a1 = a1 - Q_bg @ (Q_bg.conj().T @ a1)
            a2 = a2 - Q_bg @ (Q_bg.conj().T @ a2)
        M1 = np.column_stack([Q1.conj().T @ a1, Q1.conj().T @ a2])
        g_m1 = np.linalg.lstsq(M1, z1, rcond=None)[0]
        res_m1 = float(np.linalg.norm(z1 - M1 @ g_m1) ** 2)
        if res_m1 < Rstar_q1:
            Rstar_q1 = res_m1

        M2 = np.column_stack([Q2.conj().T @ a1, Q2.conj().T @ a2])
        g_m2 = np.linalg.lstsq(M2, z2, rcond=None)[0]
        res_m2 = float(np.linalg.norm(z2 - M2 @ g_m2) ** 2)
        if res_m2 < Rstar_q2:
            Rstar_q2 = res_m2
        # Operator loss L(H2) of the fitted candidate pair
        loss_cand = exact_bad_loss(complex(g_m2[0]), t1, u1, complex(g_m2[1]), t2, u2, n)
        if loss_cand >= CFG['l13']['bad_loss_thresh'] and res_m2 < Rbad_q2:
            Rbad_q2 = res_m2

    t_comp = time.process_time() - t_comp_start

    # Arm 4 (Sol's baseline): Direct full-waveform continuous 1-path vs 2-path optimization on r_loc
    from scipy.optimize import minimize
    t_full_start = time.process_time()
    _, _, _, a1_full = fit_single_continuous(r_loc, S_pilot, kk, idx_c, n, tau0, nu0)
    g1_f = np.vdot(a1_full, r_loc) / max(np.vdot(a1_full, a1_full).real, 1e-15)
    R1_full = float(np.linalg.norm(r_loc - g1_f * a1_full) ** 2)

    best_R2_full = R1_full
    init_2p = [
        np.array([tau0 - 0.3, nu0 - 0.25, tau0 + 0.3, nu0 + 0.25], float),
        np.array([tau0 - 0.3, nu0 + 0.25, tau0 + 0.3, nu0 - 0.25], float),
    ]
    for x0 in init_2p:
        def obj2(x):
            if abs(x[2] - x[0]) < 0.05 and abs(x[3] - x[1]) < 0.05:
                return R1_full
            aa1 = atom_and_derivs(S_pilot, kk, idx_c, n, float(x[0]), float(x[1]), order=0)
            aa2 = atom_and_derivs(S_pilot, kk, idx_c, n, float(x[2]), float(x[3]), order=0)
            M = np.column_stack([aa1, aa2])
            gf = np.linalg.lstsq(M, r_loc, rcond=None)[0]
            return float(np.linalg.norm(r_loc - M @ gf) ** 2)
        res2 = minimize(obj2, x0=x0, method='Nelder-Mead', options=dict(xatol=1e-2, fatol=1e-3, maxiter=70))
        best_R2_full = min(best_R2_full, float(res2.fun))
    t_full = time.process_time() - t_full_start

    return dict(
        detected=True,
        c10_stat=c10_stat,
        comp1_glrt=float((R1_q1 - Rstar_q1) / noise_scale),
        comp2_glrt=float((R1_q2 - Rstar_q2) / noise_scale),
        comp2_r1=float(R1_q2 / noise_scale),
        comp2_rbad_gap=float(max(0.0, Rbad_q2 - R1_q2) / noise_scale),
        full_glrt=float((R1_full - best_R2_full) / noise_scale),
        var_eff=var_eff,
        cpu_comp2=float(t_comp),
        cpu_full=float(t_full),
    )


def job_l13(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['l13']
    s = ctx.system; c1, c2 = float(s.c1), float(s.c2); lmax = int(s.l_max_cap)
    idx_c = np.arange(1024) - 512.0; kk = np.fft.fftfreq(1024, 1.0 / 1024)
    out = []

    for rho, snr in cfg['cells']:
        base = stage3.inputs(ctx, frame, cfg['scenario'], rho)
        raw, obs, truth = stage3.observed(ctx, base, rho, snr)
        n = len(obs['y']); sc = scale_of(raw, obs)
        p_af = np.asarray(obs['pilot'], complex)
        d_af = np.asarray(raw['data'], complex) / sc
        x_time = to_time(p_af + d_af, c1, c2)
        p_time = to_time(p_af, c1, c2)
        S_x = np.fft.fft(x_time) / n
        s2 = float(obs['sigma2']) * (1.0 - rho / 1000.0) / 0.5 + 0.0  # wait: keep exact obs['sigma2'] scaling!
        s2 = float(obs['sigma2'])
        w_time = to_time(np.sqrt(s2) * np.asarray(raw['noise'], complex), c1, c2)

        l_orig = np.asarray(truth['l_i'], int)
        k_orig = np.asarray(truth['k_real'], float)
        g_orig = np.asarray(truth['g_i'], complex)
        rng = np.random.default_rng([SEED, frame, rho, snr, 113])

        # Pick strongest 2 paths to form total local power P_loc, keep remaining 6 as background fractional paths
        order_pw = np.argsort(-np.abs(g_orig) ** 2)
        p0, p1 = int(order_pw[0]), int(order_pw[1])
        bg_idx = [i for i in range(len(l_orig)) if i not in (p0, p1)]
        off_bg = rng.uniform(-0.5, 0.5, len(bg_idx))
        tau_bg = l_orig[bg_idx].astype(float) + off_bg
        nu_bg = k_orig[bg_idx].astype(float)
        g_bg = g_orig[bg_idx]

        # Choose a clean integer center l_loc in [8, lmax-8] separated by >= 5 taps from background delays
        cand_locs = [L for L in range(8, lmax - 8) if all(abs(L - tb) >= 5.0 for tb in tau_bg)]
        l_loc = int(cand_locs[int(rng.integers(0, len(cand_locs)))])
        P_loc = float(abs(g_orig[p0]) ** 2 + abs(g_orig[p1]) ** 2)

        def synth_wave(taus, nus, gs):
            y_t = np.zeros(n, complex)
            for ti, ui, gi in zip(taus, nus, gs):
                sh = np.fft.ifft(np.exp(-2j * np.pi * float(ti) * kk / n) * S_x) * n
                y_t += gi * np.exp(2j * np.pi * idx_c * float(ui) / n) * sh
            return y_t

        y_bg = synth_wave(tau_bg, nu_bg, g_bg)

        # Case 1: Genuine single fractional path
        tau_c = l_loc + float(rng.uniform(-0.45, 0.45))
        nu_c = float(rng.uniform(-1.2, 1.2))
        phi0 = float(rng.uniform(0, 2 * np.pi))
        g_1p = np.sqrt(P_loc) * np.exp(1j * phi0)
        y_1p = y_bg + synth_wave([tau_c], [nu_c], [g_1p]) + w_time
        ev_1p = eval_l13_instance(y_1p, p_time, s2, lmax, l_loc, n)

        # Case 2: Controlled two near-delay paths (half random phase, half near in-phase |dphi| <= 0.25)
        in_phase = bool(frame % 2 == 0)
        dtau = float(rng.uniform(0.35, 0.95))
        dnu = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.25, 1.05))
        alpha_p = float(rng.uniform(0.25, 0.50))
        dphi = float(rng.uniform(-0.25, 0.25) if in_phase else rng.uniform(-np.pi, np.pi))
        tau1, tau2 = tau_c - 0.5 * dtau, tau_c + 0.5 * dtau
        nu1, nu2 = nu_c - 0.5 * dnu, nu_c + 0.5 * dnu
        g1_raw = np.sqrt(alpha_p) * np.exp(1j * phi0)
        g2_raw = np.sqrt(1.0 - alpha_p) * np.exp(1j * (phi0 + dphi))
        ip12 = op_inner_product(dtau, dnu, n)
        norm_raw = float(max(abs(g1_raw) ** 2 + abs(g2_raw) ** 2 + 2.0 * np.real(np.conj(g1_raw) * g2_raw * ip12), 0.15))
        scale_2p = np.sqrt(P_loc / norm_raw)
        g1, g2 = g1_raw * scale_2p, g2_raw * scale_2p
        loss_true = exact_bad_loss(g1, tau1, nu1, g2, tau2, nu2, n)

        y_2p = y_bg + synth_wave([tau1, tau2], [nu1, nu2], [g1, g2]) + w_time
        ev_2p = eval_l13_instance(y_2p, p_time, s2, lmax, l_loc, n)

        out.append(dict(
            frame=frame, rho=rho, snr=snr, P_loc=P_loc, in_phase=in_phase,
            dtau=dtau, dnu=dnu, dphi=dphi, loss_true=loss_true,
            one_path=ev_1p, two_path=ev_2p,
        ))
    return out


# --------------------------------------------------------------------------- 4. Card c06 supplement (cap 16)
def job_c06cap16(frame):
    C = setup(); stage3, ctx = C['stage3'], C['ctx']; cfg = CFG['c06cap16']
    s = ctx.system; c1, c2 = float(s.c1), float(s.c2)
    base = stage3.inputs(ctx, frame, cfg['scenario'], cfg['rho']); sig_exp = None; rec = dict(frame=frame)

    native = ctx.native; orig_refine = native.time_refine

    def refine_cap16(*a, **kw):
        return orig_refine(*a, **dict(kw, max_paths=cfg['max_paths']))

    for snr in cfg['exp_snrs']:
        raw, obs, truth = stage3.observed(ctx, base, cfg['rho'], snr)
        w = np.sqrt(float(obs['sigma2'])) * np.asarray(raw['noise'], complex)
        if sig_exp is None:
            x = np.asarray(obs['pilot'], complex) + np.asarray(raw['data'], complex) / scale_of(raw, obs)
            tsig = to_time(x, c1, c2)
            l = np.asarray(truth['l_i'], int); k = np.asarray(truth['k_real'], float); g = np.asarray(truth['g_i'], complex)
            off = np.random.default_rng([SEED, frame, 93]).uniform(-0.5, 0.5, len(l))
            ce = sum(gi * wide_path(tsig, float(li) + oi, ki, 0.0) for li, ki, gi, oi in zip(l, k, g, off))
            sig_exp = to_daft(ce, c1, c2)
        o = dict(obs, y=sig_exp + w)
        native.time_refine = refine_cap16
        try:
            dec, arr, syn, _ = stageA.f0(C, o)
            r = b3.score_f0(C, o, truth, dec, arr, syn, True)
        finally:
            native.time_refine = orig_refine
        rec[f'cap16_{snr}'] = int(r['errors'] > 0)
        rec[f'cap16_{snr}_f0'] = int(r['f0_errors'] > 0)
        rec[f'cap16_{snr}_npaths'] = int(len(arr['r1_delays']))
    return [rec]


# --------------------------------------------------------------------------- smoke, runner, and readouts
def smoke(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    C = setup(); ctx = C['ctx']
    # Gate 1: with_lmax(102) reproduces original stageA.f0 bitwise
    raw, obs, truth = C['stage3'].observed(ctx, C['stage3'].inputs(ctx, 41000, 'U', 150), 150, 500)
    dec0, arr0, syn0, _ = stageA.f0(C, obs)
    with with_lmax(C, 102):
        dec1, arr1, syn1, _ = stageA.f0(C, obs)
    g_l12_id = bool(syn0 == syn1 and np.array_equal(dec0['decoded'], dec1['decoded'])
                    and np.array_equal(arr0['r0_delays'], arr1['r0_delays']))

    # Gate 2: op_inner_product matches explicit matrix Frobenius inner product on N=64
    n_test = 64; idx_c = np.arange(n_test) - n_test / 2.0; kk = np.fft.fftfreq(n_test, 1.0 / n_test)
    F_n = np.fft.fft(np.eye(n_test), axis=0) / n_test
    Finv_n = np.fft.ifft(np.eye(n_test), axis=0) * n_test
    def mat_op(tau, nu):
        S_shift = Finv_n @ (np.exp(-2j * np.pi * tau * kk / n_test)[:, None] * F_n)
        return np.exp(2j * np.pi * idx_c * nu / n_test)[:, None] * S_shift
    A1 = mat_op(3.35, 0.42); A2 = mat_op(3.95, -0.31)
    ip_mat = np.vdot(A1, A2) / n_test
    ip_cf = op_inner_product(3.95 - 3.35, -0.31 - 0.42, n_test)
    g_l13_ip = float(abs(ip_mat - ip_cf))

    t0 = time.process_time(); r11 = job_l11(41000)[0]; t11 = time.process_time() - t0
    t0 = time.process_time(); r12 = job_l12(46000)[0]; t12 = time.process_time() - t0
    t0 = time.process_time(); r13 = job_l13(47000); t13 = time.process_time() - t0
    t0 = time.process_time(); rc6 = job_c06cap16(45000)[0]; tc6 = time.process_time() - t0

    res = dict(
        gate_l12_lmax102_bitwise=g_l12_id,
        gate_l12_y_relerr=r12['gate_y102'],
        gate_l11_y_relerr=r11['gate_err'],
        gate_l11_ties_ok=bool(r11['r0']['tie_ok'] and r11['r1']['tie_ok']),
        gate_l13_ip_err=g_l13_ip,
        cpu_per_frame=dict(l11=t11, l12=t12, l13=t13, c06cap16=tc6),
        est_core_hours=dict(
            l11=t11 * 200 / 3600,
            l12=t12 * 200 / 3600,
            l13=t13 * 450 / 3600,
            c06cap16=tc6 * 600 / 3600,
        ),
        sample_c06cap16_npaths=rc6['cap16_500_npaths'],
    )
    if not (g_l12_id and r12['gate_y102'] < 1e-11 and r11['gate_err'] < 1e-11
            and res['gate_l11_ties_ok'] and g_l13_ip < 1e-12 and rc6['cap16_500_npaths'] > 8):
        raise AssertionError(f'Smoke gate failed: {res}')
    (out / 'smoke.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def run_task(mode, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    path = out / f'{mode}_rows.jsonl'
    if path.exists() or Path(str(path) + '.gz').exists():
        raise FileExistsError(path)
    dispatch = dict(
        l11=(job_l11, list(range(*CFG['l11']['frames']))),
        l12=(job_l12, list(range(*CFG['l12']['frames']))),
        l13=(job_l13, list(range(CFG['l13']['calib_frames'][0], CFG['l13']['eval_frames'][1]))),
        c06cap16=(job_c06cap16, list(range(*CFG['c06cap16']['frames']))),
    )
    fn, frames = dispatch[mode]
    t0 = time.time(); nrow = 0
    with get_context('spawn').Pool(WORKERS) as pool, open(path, 'x') as fh:
        for rows in pool.imap_unordered(fn, frames):
            for r in rows:
                print(json.dumps(r), file=fh); nrow += 1
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    meta = dict(_argv=sys.argv, mode=mode, _config=CFG[mode], seed=SEED, workers=WORKERS,
                rows=nrow, core_hours=(ch.ru_utime + ch.ru_stime) / 3600, wall_seconds=time.time() - t0)
    (out / f'{mode}_run.json').write_text(json.dumps(meta, indent=1))
    os.system(f'gzip -n {path}')
    print(mode, 'rows', nrow, 'core-hours', round(meta['core_hours'], 3), 'wall', round(meta['wall_seconds'], 1))


def read_all(out):
    out = Path(out); rng = np.random.default_rng(SEED); summary = {}

    # --- Read l11 ---
    p11 = out / 'l11_rows.jsonl.gz'
    if p11.exists():
        rows = sorted([json.loads(x) for x in gzip.open(p11, 'rt')], key=lambda r: r['frame'])
        n = len(rows)
        rec_diff = np.array([r['recall_afdm'] - r['recall_sc'] for r in rows])
        bs_rec = [rec_diff[rng.integers(0, n, n)].mean() for _ in range(4000)]
        s11 = dict(
            frames=n,
            gate_err_max=max(r['gate_err'] for r in rows),
            ties_all_ok=bool(all(r['r0']['tie_ok'] and r['r1']['tie_ok'] for r in rows)),
            recall_afdm_mean=float(np.mean([r['recall_afdm'] for r in rows])),
            recall_sc_mean=float(np.mean([r['recall_sc'] for r in rows])),
            recall_diff_afdm_minus_sc=dict(point=float(rec_diff.mean()),
                                           ci95=[float(np.percentile(bs_rec, 2.5)), float(np.percentile(bs_rec, 97.5))]),
        )
        for rtag in ('r0', 'r1'):
            w = np.array([r[rtag]['wsum'] for r in rows])
            arms_res = {}
            for arm in ('afdm_var', 'afdm_flat', 'sc_var', 'ofdm_var', 'afdm_mp'):
                num = np.array([r[rtag]['weighted_correct'][arm] for r in rows])
                pt = float(num.sum() / max(w.sum(), 1e-15))
                bs = []
                for _ in range(4000):
                    ii = rng.integers(0, n, n)
                    bs.append(float(num[ii].sum() / max(w[ii].sum(), 1e-15)))
                arms_res[arm] = dict(point=pt, ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
            s11[rtag] = dict(
                total_active_paths=int(sum(r[rtag]['n_active'] for r in rows)),
                v_mean_avg=float(np.mean([r[rtag]['v_mean'] for r in rows])),
                v_std_avg=float(np.mean([r[rtag]['v_std'] for r in rows])),
                arms=arms_res,
            )
        ci_r0 = s11['r0']['arms']['afdm_var']['ci95']
        s11['verdict_kill_r0'] = bool(ci_r0[1] < 0.60)
        s11['verdict_pass_r0'] = bool(ci_r0[0] > 0.60)
        summary['l11'] = s11

    # --- Read l12 ---
    p12 = out / 'l12_rows.jsonl.gz'
    if p12.exists():
        rows = sorted([json.loads(x) for x in gzip.open(p12, 'rt')], key=lambda r: r['frame'])
        n = len(rows)
        def pair_ci(a_arr, b_arr):
            d = a_arr - b_arr
            bs = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
            return dict(point=float(d.mean()), ci95=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                        a_only=int(((a_arr == 1) & (b_arr == 0)).sum()), b_only=int(((b_arr == 1) & (a_arr == 0)).sum()))

        partA = {}
        for scen in CFG['l12']['scenarios']:
            partA[scen] = {}
            for snr in map(str, CFG['l12']['snrs']):
                partA[scen][snr] = {}
                for lcap in map(str, CFG['l12']['l_caps']):
                    cells = [r['partA'][scen][snr][lcap] for r in rows]
                    cd_a = np.array([c['CD'] for c in cells]); fu_a = np.array([c['FULL'] for c in cells])
                    partA[scen][snr][lcap] = dict(
                        fail={k: int(sum(c[k] for c in cells)) for k in ('trueH', 'F0', 'CD', 'FULL')},
                        cd_minus_full=pair_ci(cd_a, fu_a),
                    )
            # Key >1 dB loss checks on CD and trueH: l_cap=400 @ 6.0 dB vs l_cap=102 @ 5.0 dB, and l_cap=240 @ 6.0 dB vs 102 @ 5.0 dB
            for arm_k in ('CD', 'trueH', 'F0'):
                a400_6 = np.array([r['partA'][scen]['600']['400'][arm_k] for r in rows])
                a240_6 = np.array([r['partA'][scen]['600']['240'][arm_k] for r in rows])
                a102_5 = np.array([r['partA'][scen]['500']['102'][arm_k] for r in rows])
                a400_7 = np.array([r['partA'][scen]['700']['400'][arm_k] for r in rows])
                a102_6 = np.array([r['partA'][scen]['600']['102'][arm_k] for r in rows])
                partA[scen][f'{arm_k}_400at6_minus_102at5'] = pair_ci(a400_6, a102_5)
                partA[scen][f'{arm_k}_240at6_minus_102at5'] = pair_ci(a240_6, a102_5)
                partA[scen][f'{arm_k}_400at7_minus_102at5'] = pair_ci(a400_7, a102_5)
                partA[scen][f'{arm_k}_400at7_minus_102at6'] = pair_ci(a400_7, a102_6)

        partB = {}
        for snr in map(str, CFG['l12']['snrs']):
            res_c = [r['partB'][snr]['res205'] for r in rows]
            off_c = [r['partB'][snr]['off185'] for r in rows]
            partB[snr] = dict(
                res205_fail={k: int(sum(c[k] for c in res_c)) for k in ('trueH', 'F0', 'CD', 'FULL')},
                off185_fail={k: int(sum(c[k] for c in off_c)) for k in ('trueH', 'F0', 'CD', 'FULL')},
                res205_gamma_ratio_median=float(np.median([c['gamma_cross_ratio'] for c in res_c])),
                off185_gamma_ratio_median=float(np.median([c['gamma_cross_ratio'] for c in off_c])),
                res205_cd_minus_full=pair_ci(np.array([c['CD'] for c in res_c]), np.array([c['FULL'] for c in res_c])),
                res_minus_off_CD=pair_ci(np.array([c['CD'] for c in res_c]), np.array([c['CD'] for c in off_c])),
                res_minus_off_trueH=pair_ci(np.array([c['trueH'] for c in res_c]), np.array([c['trueH'] for c in off_c])),
            )
        summary['l12'] = dict(frames=n, gate_y102_max=max(r.get('gate_y102', 0.0) for r in rows), partA=partA, partB=partB)

    # --- Read l13 ---
    p13 = out / 'l13_rows.jsonl.gz'
    if p13.exists():
        rows = [json.loads(x) for x in gzip.open(p13, 'rt')]
        c_lo, c_hi = CFG['l13']['calib_frames']
        calib = [r for r in rows if c_lo <= r['frame'] < c_hi]
        ev = [r for r in rows if r['frame'] >= c_hi]

        # Calibrate thresholds ONLY on calibration frames: target <= 8% bad-merge on detected bad 2-path calib cases
        bad_cal = [r['two_path'] for r in calib if r['loss_true'] >= CFG['l13']['bad_loss_thresh'] and r['two_path']['detected']]
        one_cal = [r['one_path'] for r in calib if r['one_path']['detected']]
        q_target = CFG['l13']['calib_bad_merge_target']  # 8% quantile of split statistic on bad 2-path -> <=8% false merge
        th = dict(
            c10=float(np.quantile([x['c10_stat'] for x in bad_cal], q_target)),
            comp1=float(np.quantile([x['comp1_glrt'] for x in bad_cal], q_target)),
            comp2_split=float(np.quantile([x['comp2_glrt'] for x in bad_cal], q_target)),
            comp2_r1_max=float(np.quantile([x['comp2_r1'] for x in one_cal], 0.92)),
            full=float(np.quantile([x['full_glrt'] for x in bad_cal], q_target)),
        )

        def decide_arms(inst):
            if not inst['detected']:
                return {k: 'undecided' for k in ('c10_phase', 'comp_1st', 'comp_2nd', 'comp_2nd_3way', 'full_2path')}
            d_c10 = 'merge' if inst['c10_stat'] < th['c10'] else 'split'
            d_c1 = 'merge' if inst['comp1_glrt'] < th['comp1'] else 'split'
            d_c2 = 'merge' if inst['comp2_glrt'] < th['comp2_split'] else 'split'
            # 3-way rule (merge / split / undecided) using R1 goodness-of-fit + GLRT
            if inst['comp2_glrt'] >= th['comp2_split']:
                d_c2_3 = 'split'
            elif inst['comp2_r1'] <= th['comp2_r1_max']:
                d_c2_3 = 'merge'
            else:
                d_c2_3 = 'undecided'
            d_fu = 'merge' if inst['full_glrt'] < th['full'] else 'split'
            return dict(c10_phase=d_c10, comp_1st=d_c1, comp_2nd=d_c2, comp_2nd_3way=d_c2_3, full_2path=d_fu)

        arms_names = ('c10_phase', 'comp_1st', 'comp_2nd', 'comp_2nd_3way', 'full_2path')
        s13 = dict(calib_n=len(calib), eval_n=len(ev), thresholds=th,
                   bad_eval_n=int(sum(r['loss_true'] >= CFG['l13']['bad_loss_thresh'] for r in ev)),
                   bad_inphase_eval_n=int(sum(r['loss_true'] >= CFG['l13']['bad_loss_thresh'] and r['in_phase'] for r in ev)),
                   cpu_ms_mean=dict(
                       comp2=float(1000 * np.mean([r['two_path']['cpu_comp2'] for r in ev if r['two_path']['detected']])),
                       full=float(1000 * np.mean([r['two_path']['cpu_full'] for r in ev if r['two_path']['detected']])),
                   ),
                   arms={})

        ev_frames = sorted({r['frame'] for r in ev})
        by_f = {f: [r for r in ev if r['frame'] == f] for f in ev_frames}

        for arm in arms_names:
            def metrics_on(sub_rows):
                m1 = [decide_arms(r['one_path'])[arm] == 'merge' for r in sub_rows]
                bad_rows = [r for r in sub_rows if r['loss_true'] >= CFG['l13']['bad_loss_thresh']]
                fm = [decide_arms(r['two_path'])[arm] == 'merge' for r in bad_rows]
                inp_rows = [r for r in bad_rows if r['in_phase']]
                sp_inp = [decide_arms(r['two_path'])[arm] == 'split' for r in inp_rows]
                return float(np.mean(m1)), float(np.mean(fm)), float(np.mean(sp_inp))

            pt_m1, pt_fm, pt_inp = metrics_on(ev)
            bs_m1, bs_fm, bs_inp = [], [], []
            for _ in range(2000):
                fs = [ev_frames[i] for i in rng.integers(0, len(ev_frames), len(ev_frames))]
                sub = [r for f in fs for r in by_f[f]]
                a, b, c = metrics_on(sub)
                bs_m1.append(a); bs_fm.append(b); bs_inp.append(c)
            s13['arms'][arm] = dict(
                true1_merge_rate=dict(point=pt_m1, ci95=[float(np.percentile(bs_m1, 2.5)), float(np.percentile(bs_m1, 97.5))]),
                bad2_false_merge_rate=dict(point=pt_fm, ci95=[float(np.percentile(bs_fm, 2.5)), float(np.percentile(bs_fm, 97.5))]),
                inphase_bad2_split_rate=dict(point=pt_inp, ci95=[float(np.percentile(bs_inp, 2.5)), float(np.percentile(bs_inp, 97.5))]),
            )
        summary['l13'] = s13

    # --- Read c06cap16 ---
    pc6 = out / 'c06cap16_rows.jsonl.gz'
    if pc6.exists():
        rows = sorted([json.loads(x) for x in gzip.open(pc6, 'rt')], key=lambda r: r['frame'])
        out13_sum = json.loads((HERE / 'out13' / 'summary.json').read_text())
        s_c6 = dict(
            frames=len(rows),
            cap16_fail={k: int(sum(r[k] for r in rows)) for k in ('cap16_400', 'cap16_400_f0', 'cap16_500', 'cap16_500_f0', 'cap16_600', 'cap16_600_f0')},
            mean_npaths_500=float(np.mean([r['cap16_500_npaths'] for r in rows])),
            out13_ref_fail=out13_sum['fail'],
        )
        summary['c06cap16'] = s_c6

    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('smoke', 'l11', 'l12', 'l13', 'c06cap16', 'read'))
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    if args.mode == 'smoke':
        smoke(args.out)
    elif args.mode == 'read':
        read_all(args.out)
    else:
        run_task(args.mode, args.out)
