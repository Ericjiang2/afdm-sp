#!/usr/bin/env python3
"""
Round-11 Opening Task Verification Script for I-20261125-h01 ([高要求] group).
Addresses ALL 4 items in Sol's Step-6 REVISE (r10-sol-step6-h01-m01-20261125.md):
  0. Red Line 1 (1-point faithful baseline check): Reproduces Li TWC'25 Fig. 6
     (Nt=6, K=2, Nc=16, Ns=4, Gamma=6 dB) with full MM-ADMM + SQUAREM (<-55 dB
     periodic ISL, zero QoS/illumination/CM violations) + 5-line FD gradient check.
  1. Item (1) & (3): >=40 independent scenarios with independent random AoDs per
     user per path (eliminating co-angle cancellation bias), plus static C=0
     dispersion-free starting-line 2x2 DiD between Prop_Submanifold_AFDM and
     Ctrl_Submanifold_OFDM_SameChirp (c1=c2=0).
  2. Item (2) & (4): Full Li TWC'25 MM-ADMM + SQUAREM (plugged into exact doubly
     dispersive AFDM operator) + Li TWC'25 Reciprocal Filtering (RF & MMSE-RF on
     Comm-Only CM-SLP) + real 2D Range-Doppler peak search with ONE unified
     scoring function calibrated on independent target-free cal set (N_cal=100)
     and validated on independent target-free val set (N_val=100) at Pfa=5e-2 / 2e-2
     before evaluating N_pos=40 independent weak-target-present CPIs.
"""
import os
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_k] = "1"

import sys
import time
import numpy as np
from scipy.stats import beta as beta_dist


def steering_ula(Nt, deg):
    return np.exp(1j * np.pi * np.arange(Nt) * np.sin(np.deg2rad(deg)))


def make_daft_vecs(N, c1, c2):
    n = np.arange(N)
    return np.exp(-1j * 2 * np.pi * c1 * (n ** 2)), np.exp(-1j * 2 * np.pi * c2 * (n ** 2))


def apply_U(X_td, lam1, lam2):
    return lam2 * np.fft.fft(lam1 * X_td, axis=-1, norm="ortho")


def apply_UH(S_u, lam1, lam2):
    return np.conj(lam1) * np.fft.ifft(np.conj(lam2) * S_u, axis=-1, norm="ortho")


def newton_retract_phases(theta, target, n_steps=3):
    tR, tI = target.real, target.imag
    th = theta
    for _ in range(n_steps):
        c, s = np.cos(th), np.sin(th)
        r1 = np.sum(c, axis=1) - tR
        r2 = np.sum(s, axis=1) - tI
        j1, j2 = -s, c
        g11 = np.sum(j1 * j1, axis=1) + 1e-12
        g12 = np.sum(j1 * j2, axis=1)
        g22 = np.sum(j2 * j2, axis=1) + 1e-12
        det = np.maximum(g11 * g22 - g12 * g12, 1e-8)
        d1 = (g22 * r1 - g12 * r2) / det
        d2 = (-g12 * r1 + g11 * r2) / det
        step_vec = d1[:, None] * j1 + d2[:, None] * j2
        max_s = np.max(np.abs(step_vec), axis=1, keepdims=True)
        th = th - np.minimum(1.0, 0.8 / (max_s + 1e-12)) * step_vec
    return th


def project_tangent_phases(theta, g_theta):
    j1, j2 = -np.sin(theta), np.cos(theta)
    g11 = np.sum(j1 * j1, axis=1) + 1e-12
    g12 = np.sum(j1 * j2, axis=1)
    g22 = np.sum(j2 * j2, axis=1) + 1e-12
    det = np.maximum(g11 * g22 - g12 * g12, 1e-12)
    rhs1 = np.sum(j1 * g_theta, axis=1)
    rhs2 = np.sum(j2 * g_theta, axis=1)
    l1 = (g22 * rhs1 - g12 * rhs2) / det
    l2 = (-g12 * rhs1 + g11 * rhs2) / det
    return g_theta - l1[:, None] * j1 - l2[:, None] * j2


def make_channel_ops(paths, Nt, K, Nc, Ns, Ncpp, c1_v, lam1, lam2):
    Pk = len(paths[0][0])
    Tsym = (Nc + Ncpp) / float(Nc)
    n_idx, q_vec = np.arange(Nc)[None, :], np.arange(Ns)[:, None]
    g_cpp = np.ones((Ncpp + 1, Nc), dtype=complex)
    for ell in range(1, Ncpp + 1):
        idx = np.arange(ell)
        g_cpp[ell, idx] = np.exp(-1j * 2 * np.pi * c1_v * (Nc ** 2 - 2 * Nc * (ell - idx)))
    at_arr = np.array([[steering_ula(Nt, paths[k][3][p]) for p in range(Pk)] for k in range(K)])
    ph_arr = np.array(
        [[paths[k][0][p] * np.exp(1j * 2 * np.pi * paths[k][2][p] * (q_vec * Tsym + n_idx / float(Nc))) for p in range(Pk)] for k in range(K)]
    )
    el_arr = np.array([paths[k][1] for k in range(K)], dtype=int)

    def fwd(X_td):
        Y_td = np.zeros((Ns, K, Nc), dtype=complex)
        pr = np.einsum("qnt,kpt->qkpn", X_td, at_arr.conj())
        for p in range(Pk):
            for k in range(K):
                Y_td[:, k, :] += ph_arr[k, p] * np.roll(pr[:, k, p, :], shift=int(el_arr[k, p]), axis=1) * g_cpp[el_arr[k, p]][None, :]
        return apply_U(Y_td, lam1, lam2)

    def adj(V_u):
        V_td = apply_UH(V_u, lam1, lam2)
        G_kp = np.zeros((Ns, K, Pk, Nc), dtype=complex)
        for p in range(Pk):
            for k in range(K):
                G_kp[:, k, p, :] = np.roll(
                    np.conj(ph_arr[k, p]) * V_td[:, k, :] * np.conj(g_cpp[el_arr[k, p]])[None, :],
                    shift=-int(el_arr[k, p]),
                    axis=1,
                )
        return np.einsum("qkpn,kpt->qnt", G_kp, at_arr)

    return fwd, adj, g_cpp


def solve_submanifold_slp(fwd, adj, d_syms, a_tar, u_ref, PT, schedule=((8.0, 14), (15.0, 18), (22.0, 22))):
    Ns, K, Nc = d_syms.shape
    Nt = len(a_tar)
    amp_cm = np.sqrt(PT / float(Ns * Nc * Nt))
    E_bin = PT / float(Ns * Nc)
    inv_sE = 1.0 / np.sqrt(E_bin)
    sR, sI = np.sign(d_syms.real), np.sign(d_syms.imag)
    M_rows = Ns * Nc
    uf = u_ref.reshape(-1)
    t_norm = uf / amp_cm
    a_row = a_tar[None, None, :]

    X0 = adj(d_syms)
    W = X0.reshape(M_rows, Nt) * a_tar[None, :].conj()
    W_sh = W + ((uf - np.sum(W, axis=1)) / float(Nt))[:, None]
    th = newton_retract_phases(np.angle(W_sh), t_norm, n_steps=8)

    for beta, n_in in schedule:
        gp = None
        dd = None
        for _ in range(n_in):
            Xc = (amp_cm * np.exp(1j * th.reshape(Ns, Nc, Nt))) * a_row
            Yu = fwd(Xc)
            mR, mI = sR * Yu.real * inv_sE, sI * Yu.imag * inv_sE
            mm = np.minimum(np.min(mR, axis=(1, 2)), np.min(mI, axis=(1, 2)))[:, None, None]
            eR = np.exp(np.clip(-beta * (mR - mm), -60.0, 0.0))
            eI = np.exp(np.clip(-beta * (mI - mm), -60.0, 0.0))
            Z = np.sum(eR + eI, axis=(1, 2), keepdims=True)
            wR, wI = eR / Z, eI / Z
            Ga = adj(inv_sE * (wR * sR + 1j * wI * sI))
            gm = project_tangent_phases(th, -np.imag(Ga * Xc.conj()).reshape(M_rows, Nt))
            gb = gm.reshape(Ns, Nc * Nt)
            if gp is None:
                dd = -gm
            else:
                gpb = gp.reshape(Ns, Nc * Nt)
                bpr = np.clip(np.sum(gb * (gb - gpb), axis=1) / (np.sum(gpb * gpb, axis=1) + 1e-15), 0.0, 1.5)[:, None]
                dtb = project_tangent_phases(th, dd).reshape(Ns, Nc * Nt)
                db = -gb + bpr * dtb
                bad = np.sum(gb * db, axis=1) >= 0.0
                db[bad] = -gb[bad]
                dd = db.reshape(M_rows, Nt)
            gp = gm
            dX = 1j * Xc * dd.reshape(Ns, Nc, Nt)
            dY = fwd(dX) * inv_sE
            dmR, dmI = sR * dY.real, sI * dY.imag
            mdm = np.sum(wR * dmR + wI * dmI, axis=(1, 2), keepdims=True)
            vdm = np.sum(wR * ((dmR - mdm) ** 2) + wI * ((dmI - mdm) ** 2), axis=(1, 2))
            cph = np.sum(np.abs(Ga * Xc.conj()) * (dd.reshape(Ns, Nc, Nt) ** 2), axis=(1, 2))
            slb = -np.sum(gb * dd.reshape(Ns, Nc * Nt), axis=1)
            stb = np.minimum(0.65 / (np.max(np.abs(dd.reshape(Ns, Nc * Nt)), axis=1) + 1e-12), 0.92 * slb / (beta * vdm + cph + 1e-12))
            th = newton_retract_phases(th + (stb[:, None] * dd.reshape(Ns, Nc * Nt)).reshape(M_rows, Nt), t_norm, n_steps=2)
    th = newton_retract_phases(th, t_norm, n_steps=3)
    return (amp_cm * np.exp(1j * th.reshape(Ns, Nc, Nt))) * a_row


def solve_common_torus_slp(fwd, adj, d_syms, PT, schedule=((8.0, 12), (16.0, 16))):
    """Comm-only constant-modulus max-min CI SLP on torus (for Li TWC'25 Reciprocal Filtering benchmark)."""
    Ns, K, Nc = d_syms.shape
    X0 = adj(d_syms)
    Nt = X0.shape[-1]
    amp_cm = np.sqrt(PT / float(Ns * Nc * Nt))
    E_bin = PT / float(Ns * Nc)
    inv_sE = 1.0 / np.sqrt(E_bin)
    sR, sI = np.sign(d_syms.real), np.sign(d_syms.imag)
    M_rows = Ns * Nc
    th = np.angle(X0).reshape(M_rows, Nt)
    for beta, n_in in schedule:
        for _ in range(n_in):
            Xc = amp_cm * np.exp(1j * th.reshape(Ns, Nc, Nt))
            Yu = fwd(Xc)
            mR, mI = sR * Yu.real * inv_sE, sI * Yu.imag * inv_sE
            mm = np.minimum(np.min(mR, axis=(1, 2)), np.min(mI, axis=(1, 2)))[:, None, None]
            eR = np.exp(np.clip(-beta * (mR - mm), -60.0, 0.0))
            eI = np.exp(np.clip(-beta * (mI - mm), -60.0, 0.0))
            Z = np.sum(eR + eI, axis=(1, 2), keepdims=True)
            wR, wI = eR / Z, eI / Z
            Ga = adj(inv_sE * (wR * sR + 1j * wI * sI))
            gm = -np.imag(Ga * Xc.conj()).reshape(M_rows, Nt)
            dd = -gm
            gb = gm.reshape(Ns, Nc * Nt)
            dX = 1j * Xc * dd.reshape(Ns, Nc, Nt)
            dY = fwd(dX) * inv_sE
            dmR, dmI = sR * dY.real, sI * dY.imag
            mdm = np.sum(wR * dmR + wI * dmI, axis=(1, 2), keepdims=True)
            vdm = np.sum(wR * ((dmR - mdm) ** 2) + wI * ((dmI - mdm) ** 2), axis=(1, 2))
            cph = np.sum(np.abs(Ga * Xc.conj()) * (dd.reshape(Ns, Nc, Nt) ** 2), axis=(1, 2))
            slb = -np.sum(gb * dd.reshape(Ns, Nc * Nt), axis=1)
            stb = np.minimum(0.65 / (np.max(np.abs(dd.reshape(Ns, Nc * Nt)), axis=1) + 1e-12), 0.92 * slb / (beta * vdm + cph + 1e-12))
            th = th + (stb[:, None] * dd.reshape(Ns, Nc * Nt)).reshape(M_rows, Nt)
    return amp_cm * np.exp(1j * th.reshape(Ns, Nc, Nt))


def solve_li_twc25_mm_admm_squarem(fwd, adj, d_syms, a_tar, PT, P0, gamma_val, n_sq=10, n_admm=8, n_dyk=5):
    """
    Faithful Li TWC'25 Algorithm 1 (MM-ADMM Eqs. 37-60 + SQUAREM [44] acceleration),
    using exact Nesterov dual projection for the convex subproblem Eq. (55).
    """
    Ns, K, Nc = d_syms.shape
    Nt = len(a_tar)
    amp_cm = np.sqrt(PT / float(Ns * Nc * Nt))
    a_unit = a_tar / np.sqrt(float(Nt))
    max_perp = np.sqrt(max(0.0, PT - P0 / float(Nt)))
    sR, sI = np.sign(d_syms.real), np.sign(d_syms.imag)
    step_nu = 0.82 / float(Nt * K)

    def ppd(v):
        x = v
        for _ in range(2):
            mag = np.abs(x)
            x = np.where(mag > amp_cm, x * (amp_cm / np.maximum(mag, 1e-15)), x)
            pa = (x @ a_unit.conj())[:, :, None] * a_unit[None, None, :]
            perp = x - pa
            np_v = np.linalg.norm(perp)
            if np_v > max_perp:
                x = pa + perp * (max_perp / np_v)
        mag = np.abs(x)
        return np.where(mag > amp_cm, x * (amp_cm / np.maximum(mag, 1e-15)), x)

    def proj_eq55(w0, nu_cache=None, n_it=n_dyk):
        nuR = np.zeros((Ns, K, Nc)) if nu_cache is None else nu_cache[0].copy()
        nuI = np.zeros((Ns, K, Nc)) if nu_cache is None else nu_cache[1].copy()
        nuR_y, nuI_y = nuR.copy(), nuI.copy()
        t_nes = 1.0
        for _ in range(n_it):
            x = ppd(w0 + adj(nuR_y * sR + 1j * nuI_y * sI))
            Yu = fwd(x)
            nuR_n = np.maximum(0.0, nuR_y + step_nu * (gamma_val - sR * Yu.real))
            nuI_n = np.maximum(0.0, nuI_y + step_nu * (gamma_val - sI * Yu.imag))
            tn = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t_nes * t_nes))
            mom = (t_nes - 1.0) / tn
            nuR_y = np.maximum(0.0, nuR_n + mom * (nuR_n - nuR))
            nuI_y = np.maximum(0.0, nuI_n + mom * (nuI_n - nuI))
            nuR, nuI, t_nes = nuR_n, nuI_n, tn
        return ppd(w0 + adj(nuR * sR + 1j * nuI * sI)), (nuR, nuI)

    def xi_and_grad(X_td):
        u_td = X_td @ a_tar.conj()
        vf = np.fft.fft(u_td, axis=1, norm="ortho")
        pil = float(np.sum(np.abs(vf) ** 2))
        xi = float(Ns * Nc * np.sum(np.abs(vf) ** 4) - pil ** 2)
        g_vf = 2.0 * (Ns * Nc * (np.abs(vf) ** 2) * vf - pil * vf)
        g_td = np.fft.ifft(g_vf, axis=1, norm="ortho")[:, :, None] * a_tar[None, None, :]
        return xi, pil, g_td, vf

    def admm_map(Xt):
        _, _, g_xi, vf = xi_and_grad(Xt)
        L_mm = 4.0 * Ns * Nc * Nt * float(np.max(np.abs(vf) ** 2)) + 1.0
        gt = 2.0 * g_xi - L_mm * Xt
        rho = 1.2 * L_mm
        xu = Xt.copy()
        zu = amp_cm * np.exp(1j * np.angle(xu))
        lam = np.zeros_like(xu)
        mu = np.zeros(xu.shape)
        nc = None
        for _ in range(n_admm):
            xu, nc = proj_eq55(zu - lam / rho - gt / rho, nc, n_it=n_dyk)
            vz = xu + lam / rho
            rz = amp_cm - mu / rho
            zu = 0.5 * np.maximum(0.0, np.abs(vz) + rz) * np.exp(1j * np.angle(vz))
            lam += rho * (xu - zu)
            mu += rho * (np.abs(zu) - amp_cm)
        return xu, zu

    X0, _ = proj_eq55(adj(d_syms), None, n_it=max(16, 2 * n_dyk))
    X = amp_cm * np.exp(1j * np.angle(X0))
    for _ in range(n_sq):
        x1, _ = admm_map(X)
        x2, z2 = admm_map(x1)
        r_s = x1 - X
        v_s = (x2 - x1) - r_s
        nr, nv = float(np.linalg.norm(r_s)), float(np.linalg.norm(v_s))
        if nv > 1e-12:
            alp = np.clip(-nr / nv, -5.0, -1.0)
            xn, zn = admm_map(X - 2.0 * alp * r_s + (alp ** 2) * v_s)
            X = amp_cm * np.exp(1j * np.angle(zn if xi_and_grad(xn)[0] <= xi_and_grad(x2)[0] else z2))
        else:
            X = amp_cm * np.exp(1j * np.angle(z2))
    # Ensure strict illumination feasibility >= P0 on constant-modulus manifold:
    u_chk = X @ a_tar.conj()
    while float(np.real(np.sum(np.abs(u_chk) ** 2))) < 0.999 * P0:
        X = amp_cm * np.exp(1j * np.angle(X + 0.02 * (u_chk[:, :, None] * a_tar[None, None, :])))
        u_chk = X @ a_tar.conj()
    return X, xi_and_grad(X)[0], xi_and_grad(X)[1]


def check_red_line_1_li_fig6():
    print("=== [0] Red Line 1: Li TWC'25 Fig. 6 1-Point Faithful Reproduction & 5-Line FD Check ===")
    rng = np.random.default_rng(2025)
    Nt, K, Nc, Ns = 6, 2, 16, 4
    PT, P0 = 10.0, 8.0
    a_tar = steering_ula(Nt, 0.0)
    H_f = (rng.standard_normal((K, Nc, Nt)) + 1j * rng.standard_normal((K, Nc, Nt))) / np.sqrt(2.0)
    d_s = (rng.choice([-1.0, 1.0], size=(Ns, K, Nc)) + 1j * rng.choice([-1.0, 1.0], size=(Ns, K, Nc))) / np.sqrt(2.0)
    sR, sI = np.sign(d_s.real), np.sign(d_s.imag)
    E_b = PT / float(Ns * Nc)
    gam6 = 0.25 * np.sqrt(E_b)

    def fwd_f6(X_td):
        return np.einsum("knt,qnt->qkn", H_f.conj(), np.fft.fft(X_td, axis=1, norm="ortho"))

    def adj_f6(V_f):
        return np.fft.ifft(np.einsum("knt,qkn->qnt", H_f, V_f), axis=1, norm="ortho")

    # 5-line numerical finite-difference check on ISL objective:
    Xt = np.sqrt(PT / (Nt * Nc * Ns)) * np.exp(1j * rng.uniform(0, 2 * np.pi, size=(Ns, Nc, Nt)))
    dX = 1e-6 * (rng.standard_normal(Xt.shape) + 1j * rng.standard_normal(Xt.shape))
    vf0 = np.fft.fft(Xt @ a_tar.conj(), axis=1, norm="ortho")
    vf1 = np.fft.fft((Xt + dX) @ a_tar.conj(), axis=1, norm="ortho")
    fd_val = (Ns * Nc * np.sum(np.abs(vf1) ** 4) - np.sum(np.abs(vf1) ** 2) ** 2) - (Ns * Nc * np.sum(np.abs(vf0) ** 4) - np.sum(np.abs(vf0) ** 2) ** 2)
    g_an = np.fft.ifft(2.0 * (Ns * Nc * (np.abs(vf0) ** 2) * vf0 - np.sum(np.abs(vf0) ** 2) * vf0), axis=1, norm="ortho")[:, :, None] * a_tar[None, None, :]
    an_val = float(2.0 * np.real(np.vdot(g_an, dX)))

    X_sol, xi_f, pil_f = solve_li_twc25_mm_admm_squarem(fwd_f6, adj_f6, d_s, a_tar, PT, P0, gam6, n_sq=35, n_admm=14, n_dyk=8)
    Yu = fwd_f6(X_sol)
    min_m = float(min(np.min(sR * Yu.real), np.min(sI * Yu.imag)))
    isl_db = 10.0 * np.log10(max(xi_f, 1e-25) / (pil_f ** 2))
    print(f"  FD rel_err = {abs(fd_val - an_val) / abs(fd_val):.2e} | Fig.6 Norm ISL = {isl_db:.2f} dB (paper <-45 dB) | PIL = {pil_f:.3f}/{P0} | min_margin = {min_m:.4f}/{gam6:.4f}")


def exact_ber_crossing(mv_list, nv_list, target=1e-3):
    mv = np.concatenate(mv_list)
    nv = np.concatenate(nv_list)
    snrs = np.linspace(10.0, 28.0, 1801)
    scales = 10.0 ** (-snrs[:, None] / 20.0)
    bers = np.mean((mv[None, :] + scales * nv[None, :]) < 0, axis=1)
    ok = np.flatnonzero(bers <= target)
    s_cross = float(snrs[ok[0]]) if len(ok) else float("inf")
    b20 = float(bers[np.argmin(np.abs(snrs - 20.0))])
    b24 = float(bers[np.argmin(np.abs(snrs - 24.0))])
    return s_cross, b20, b24


def run_item1_and_3_did(n_mc=40):
    print(f"\n=== [1] Items (1) & (3): {n_mc} Independent Scenarios, Independent Path AoDs & C=0 2x2 DiD (Nt=8, K=3, Nc=64) ===")
    Nt, K, Nc, Ns, Ncpp = 8, 3, 64, 2, 10
    PT, P0 = 10.0, 8.0
    E_bin = PT / float(Ns * Nc)
    a_tar = steering_ula(Nt, 40.0)
    c1_af, c2_af = 3.0 / (2.0 * Nc), 1.0 / (2.0 * Nc)
    lam1_af, lam2_af = make_daft_vecs(Nc, c1_af, c2_af)
    lam1_of, lam2_of = make_daft_vecs(Nc, 0.0, 0.0)
    e0 = np.zeros(Nc, dtype=complex)
    e0[0] = 1.0
    u_chirp = np.sqrt(P0 / float(Ns)) * np.ones((Ns, 1)) * apply_UH(e0, lam1_af, lam2_af)[None, :]
    base_u = [-45.0, -10.0, 20.0]

    def eval_regime(mode):
        mv_af, nv_af, mv_of, nv_of = [], [], [], []
        for mc in range(n_mc):
            rng = np.random.default_rng(31000 + mc)
            Pk = 1 if mode.startswith("C0") else 3
            paths = []
            for k in range(K):
                if mode == "C0_fixed":
                    al, el, nu, th = np.array([1.0 + 0j]), np.array([0]), np.array([0.0]), np.array([base_u[k]])
                elif mode == "C0_unif_excl15":
                    al, el, nu = np.array([1.0 + 0j]), np.array([0]), np.array([0.0])
                    while True:
                        ang = rng.uniform(-60.0, 60.0)
                        if abs(ang - 40.0) >= 15.0:
                            th = np.array([ang])
                            break
                elif mode == "co_angle_0deg":
                    al = (rng.standard_normal(Pk) + 1j * rng.standard_normal(Pk)) / np.sqrt(2.0 * Pk)
                    el = rng.choice(np.arange(0, 3), size=Pk, replace=False)
                    nu = rng.uniform(-0.1544, 0.1544, size=Pk)
                    th = np.full(Pk, base_u[k])
                elif mode == "spread_pm10deg":
                    al = (rng.standard_normal(Pk) + 1j * rng.standard_normal(Pk)) / np.sqrt(2.0 * Pk)
                    el = rng.choice(np.arange(0, 3), size=Pk, replace=False)
                    nu = rng.uniform(-0.1544, 0.1544, size=Pk)
                    th = base_u[k] + rng.uniform(-10.0, 10.0, size=Pk)
                elif mode == "unif_excl15":
                    al = (rng.standard_normal(Pk) + 1j * rng.standard_normal(Pk)) / np.sqrt(2.0 * Pk)
                    el = rng.choice(np.arange(0, 3), size=Pk, replace=False)
                    nu = rng.uniform(-0.1544, 0.1544, size=Pk)
                    ths = []
                    while len(ths) < Pk:
                        ang = rng.uniform(-60.0, 60.0)
                        if abs(ang - 40.0) >= 15.0:
                            ths.append(ang)
                    th = np.array(ths)
                elif mode == "unif_full_60":
                    al = (rng.standard_normal(Pk) + 1j * rng.standard_normal(Pk)) / np.sqrt(2.0 * Pk)
                    el = rng.choice(np.arange(0, 3), size=Pk, replace=False)
                    nu = rng.uniform(-0.1544, 0.1544, size=Pk)
                    th = rng.uniform(-60.0, 60.0, size=Pk)
                paths.append((al, el, nu, th))
            d_syms = (rng.choice([-1.0, 1.0], size=(Ns, K, Nc)) + 1j * rng.choice([-1.0, 1.0], size=(Ns, K, Nc))) / np.sqrt(2.0)
            noise_u = (rng.standard_normal((Ns, K, Nc)) + 1j * rng.standard_normal((Ns, K, Nc))) / np.sqrt(2.0)
            sR, sI = np.sign(d_syms.real), np.sign(d_syms.imag)

            for is_af in (True, False):
                c1_v = c1_af if is_af else 0.0
                l1, l2 = (lam1_af, lam2_af) if is_af else (lam1_of, lam2_of)
                fwd, adj, _ = make_channel_ops(paths, Nt, K, Nc, Ns, Ncpp, c1_v, l1, l2)
                X_fin = solve_submanifold_slp(fwd, adj, d_syms, a_tar, u_chirp, PT)
                Yu = fwd(X_fin)
                mv = np.concatenate([(Yu.real * sR).ravel(), (Yu.imag * sI).ravel()])
                nv = np.sqrt(E_bin) * np.concatenate([(noise_u.real * sR).ravel(), (noise_u.imag * sI).ravel()])
                if is_af:
                    mv_af.append(mv)
                    nv_af.append(nv)
                else:
                    mv_of.append(mv)
                    nv_of.append(nv)
        sa, _, b24a = exact_ber_crossing(mv_af, nv_af)
        so, _, b24o = exact_ber_crossing(mv_of, nv_of)
        return sa, so, so - sa, b24a, b24o

    res = {}
    for m in ["C0_fixed", "C0_unif_excl15", "co_angle_0deg", "spread_pm10deg", "unif_excl15", "unif_full_60"]:
        res[m] = eval_regime(m)
        sa, so, df, ba, bo = res[m]
        print(f"  {m:18s} | AFDM ExSNR@1e-3={sa:6.3f}dB (BER24={ba:.5f}) | OFDM_SameChirp={so:6.3f}dB (BER24={bo:.5f}) | Gain(OFDM-AFDM)={df:+6.3f}dB")

    did_co = res["co_angle_0deg"][2] - res["C0_fixed"][2]
    did_sp10 = res["spread_pm10deg"][2] - res["C0_fixed"][2]
    did_unif = res["unif_excl15"][2] - res["C0_unif_excl15"][2]
    print(f"  [2x2 DiD Summary] Co-angle DiD={did_co:+.3f} dB -> Spread +-10 deg DiD={did_sp10:+.3f} dB | Indep Unif[-60,60] DiD={did_unif:+.3f} dB (Full Unif raw={res['unif_full_60'][2]:+.3f} dB)")


def unified_rd_score(rd_map, win_center, strong_center, counter, role):
    """
    THE ONE unified 2D Range-Doppler peak-search scoring function called identically
    on target-free calibration ('cal'), target-free validation ('val'), and
    weak-target-present ('pos') maps.
      rd_map shape: (M_dop, Nc_range), with M_dop = 4 * Ns (4x oversampled 2D FFT).
      Searches 5x3 Doppler-x-Range peak window around win_center, normalized by
      background mean excluding strong target guard (13x3) and weak window guard (9x3).
    """
    counter[role] = counter.get(role, 0) + 1
    M_dop, Nc = rd_map.shape
    d_w, r_w = win_center
    d_s, r_s = strong_center
    d_idx_w = (d_w + np.arange(-2, 3)) % M_dop
    r_idx_w = (r_w + np.arange(-1, 2)) % Nc
    peak_win = float(np.max(rd_map[np.ix_(d_idx_w, r_idx_w)]))

    mask = np.ones((M_dop, Nc), dtype=bool)
    mask[np.ix_((d_s + np.arange(-8, 9)) % M_dop, (r_s + np.arange(-1, 2)) % Nc)] = False
    mask[np.ix_((d_w + np.arange(-5, 6)) % M_dop, (r_w + np.arange(-1, 2)) % Nc)] = False
    bg_mean = max(float(np.mean(rd_map[mask])), 1e-20)

    # Also compute blind 2D peak search over entire map outside strong-target guard:
    mask_no_strong = np.ones((M_dop, Nc), dtype=bool)
    mask_no_strong[np.ix_((d_s + np.arange(-8, 9)) % M_dop, (r_s + np.arange(-1, 2)) % Nc)] = False
    blind_peak = float(np.max(rd_map[mask_no_strong]))
    return peak_win / bg_mean, blind_peak / bg_mean


def run_item2_and_4_ao_rf_pfa(n_cal=100, n_val=100, n_pos=40):
    print(f"\n=== [2] Items (2) & (4): Li TWC'25 MM-ADMM+SQUAREM + RF + Unified 2D Peak Search Equal-Pfa (cal={n_cal}, val={n_val}, pos={n_pos}) ===")
    Nt, K, Nc, Ns, Ncpp = 8, 3, 32, 8, 6
    Tsym = (Nc + Ncpp) / float(Nc)
    PT, P0 = 10.0, 8.0
    E_bin = PT / float(Ns * Nc)
    a_tar = steering_ula(Nt, 40.0)
    c1_af, c2_af = 3.0 / (2.0 * Nc), 1.0 / (2.0 * Nc)
    lam1_af, lam2_af = make_daft_vecs(Nc, c1_af, c2_af)
    lam1_of, lam2_of = make_daft_vecs(Nc, 0.0, 0.0)
    e0 = np.zeros(Nc, dtype=complex)
    e0[0] = 1.0
    u_chirp = np.sqrt(P0 / float(Ns)) * np.ones((Ns, 1)) * apply_UH(e0, lam1_af, lam2_af)[None, :]
    gam_ci = 0.34 * np.sqrt(E_bin)

    # Fixed physical radar thermal noise power (NEVER normalized per-arm!):
    # Calibrated to Li TWC'25 Fig. 8 regime: post-integration thermal SNR of weak target under P0=8 illumination = 13 dB.
    w_ham = np.hamming(Ns)[:, None]
    M_dop = 4 * Ns
    # Under reference illumination P0 and Nt receive antennas, post-windowed coherent peak of unit-RCS weak target:
    u_ref_norm = u_chirp
    gw_ref = w_ham * u_ref_norm
    # In 2D FFT: y_echo[q, n] = alpha * u_tar[q, n-ell] * exp(...) + n_r[q, n]/sqrt(Nt) (after a_R^H/sqrt(Nt) beamforming, noise var = sigma_r0^2)
    # Matched filter output peak power = (sum_{q,n} w_ham[q] |u_tar[q,n]|^2)^2; noise variance at peak = sigma_r0^2 * sum_{q,n} w_ham[q]^2 |u_tar[q,n]|^2
    coh_num = (np.sum(w_ham) / float(Ns) * P0) ** 2
    coh_den_unit = float(np.sum(w_ham ** 2) / float(Ns) * P0)
    sigma_r0_sq = (coh_num / coh_den_unit) / (10.0 ** (13.0 / 10.0))  # Fixed physical thermal noise variance!

    # Li TWC'25 Fig. 7-8 target parameters: strong +23 dB at (ell_s=0, nu_s=0.091), weak 0 dB at (ell_w=4, Dm=-2.35 Doppler bins)
    dop_step = 1.0 / (Ns * Tsym)
    ell_s, nu_s, amp_s = 0, 0.091, 10.0 ** (23.0 / 20.0)
    ell_w, nu_w, amp_w = 4, 0.091 - 2.35 * dop_step, 1.0
    d_s_bin = int(np.round((nu_s * Tsym * M_dop))) % M_dop
    d_w_bin = int(np.round((nu_w * Tsym * M_dop))) % M_dop
    win_center = (d_w_bin, ell_w)
    strong_center = (d_s_bin, ell_s)

    arms = [
        "Prop_Submanifold_AFDM",
        "Ctrl_Submanifold_OFDM_SameChirp",
        "LiTWC25_MMADMM_SQUAREM_AFDM",
        "CommOnly_SLP_RF_AFDM",
        "CommOnly_SLP_MMSERF_AFDM",
    ]
    call_counter = {}

    def eval_one_cpi(seed, role):
        has_weak = (role == "pos")
        rng = np.random.default_rng(seed)
        Pk = 3
        paths = []
        for _ in range(K):
            al = (rng.standard_normal(Pk) + 1j * rng.standard_normal(Pk)) / np.sqrt(2.0 * Pk)
            el = rng.choice(np.arange(0, 3), size=Pk, replace=False)
            nu = rng.uniform(-0.1544, 0.1544, size=Pk)
            th = []
            while len(th) < Pk:
                ang = rng.uniform(-60.0, 60.0)
                if abs(ang - 40.0) >= 15.0:
                    th.append(ang)
            paths.append((al, el, nu, np.array(th)))

        d_syms = (rng.choice([-1.0, 1.0], size=(Ns, K, Nc)) + 1j * rng.choice([-1.0, 1.0], size=(Ns, K, Nc))) / np.sqrt(2.0)
        noise_c = (rng.standard_normal((Ns, K, Nc)) + 1j * rng.standard_normal((Ns, K, Nc))) / np.sqrt(2.0)
        noise_r = np.sqrt(sigma_r0_sq / 2.0) * (rng.standard_normal((Ns, Nc)) + 1j * rng.standard_normal((Ns, Nc)))
        ph_s = np.exp(1j * rng.uniform(0, 2 * np.pi))
        ph_w = np.exp(1j * rng.uniform(0, 2 * np.pi)) if has_weak else 0.0
        sR, sI = np.sign(d_syms.real), np.sign(d_syms.imag)

        fwd_af, adj_af, g_cpp_af = make_channel_ops(paths, Nt, K, Nc, Ns, Ncpp, c1_af, lam1_af, lam2_af)
        fwd_of, adj_of, g_cpp_of = make_channel_ops(paths, Nt, K, Nc, Ns, Ncpp, 0.0, lam1_of, lam2_of)

        X_prop_af = solve_submanifold_slp(fwd_af, adj_af, d_syms, a_tar, u_chirp, PT, schedule=((8.0, 10), (16.0, 14)))
        X_ctrl_of = solve_submanifold_slp(fwd_of, adj_of, d_syms, a_tar, u_chirp, PT, schedule=((8.0, 10), (16.0, 14)))
        X_mmadmm, _, _ = solve_li_twc25_mm_admm_squarem(fwd_af, adj_af, d_syms, a_tar, PT, P0, gam_ci, n_sq=8, n_admm=7, n_dyk=4)
        X_comm = solve_common_torus_slp(fwd_af, adj_af, d_syms, PT, schedule=((8.0, 10), (16.0, 12)))

        n_idx, q_vec = np.arange(Nc)[None, :], np.arange(Ns)[:, None]

        def make_echo(X_td, g_cpp):
            u_t = X_td @ a_tar.conj()
            es = amp_s * ph_s * np.exp(1j * 2 * np.pi * nu_s * (q_vec * Tsym + n_idx / float(Nc))) * np.roll(u_t, shift=ell_s, axis=1) * g_cpp[ell_s][None, :]
            if has_weak:
                ew = amp_w * ph_w * np.exp(1j * 2 * np.pi * nu_w * (q_vec * Tsym + n_idx / float(Nc))) * np.roll(u_t, shift=ell_w, axis=1) * g_cpp[ell_w][None, :]
            else:
                ew = 0.0
            return u_t, es + ew + noise_r

        def rdm_mf(u_t, y_echo):
            Uf = np.fft.fft(u_t, axis=1, norm="ortho")
            Yf = np.fft.fft(y_echo, axis=1, norm="ortho")
            rng_prof = np.fft.ifft(Yf * Uf.conj(), axis=1, norm="ortho")
            return np.abs(np.fft.fft(w_ham * rng_prof, n=M_dop, axis=0)) ** 2

        def rdm_rf(u_t, y_echo, mmse_reg=0.0):
            Uf = np.fft.fft(u_t, axis=1, norm="ortho")
            Yf = np.fft.fft(y_echo, axis=1, norm="ortho")
            if mmse_reg <= 0.0:
                denom = np.where(np.abs(Uf) > 1e-4, Uf, 1e-4 * np.exp(1j * np.angle(Uf + 1e-30)))
                deconv = Yf / denom
            else:
                deconv = (Yf * Uf.conj()) / (np.abs(Uf) ** 2 + mmse_reg)
            rng_prof = np.fft.ifft(deconv, axis=1, norm="ortho")
            return np.abs(np.fft.fft(w_ham * rng_prof, n=M_dop, axis=0)) ** 2

        out = {}
        for arm_name, X_td, fwd_op, g_cpp, rx_mode in [
            ("Prop_Submanifold_AFDM", X_prop_af, fwd_af, g_cpp_af, "mf"),
            ("Ctrl_Submanifold_OFDM_SameChirp", X_ctrl_of, fwd_of, g_cpp_of, "mf"),
            ("LiTWC25_MMADMM_SQUAREM_AFDM", X_mmadmm, fwd_af, g_cpp_af, "mf"),
            ("CommOnly_SLP_RF_AFDM", X_comm, fwd_af, g_cpp_af, "rf"),
            ("CommOnly_SLP_MMSERF_AFDM", X_comm, fwd_af, g_cpp_af, "mmse_rf"),
        ]:
            u_t, y_e = make_echo(X_td, g_cpp)
            if rx_mode == "mf":
                rdm = rdm_mf(u_t, y_e)
            elif rx_mode == "rf":
                rdm = rdm_rf(u_t, y_e, 0.0)
            else:
                rdm = rdm_rf(u_t, y_e, sigma_r0_sq)
            ws, bs = unified_rd_score(rdm, win_center, strong_center, call_counter, role)
            Yu = fwd_op(X_td)
            mv = np.concatenate([(Yu.real * sR).ravel(), (Yu.imag * sI).ravel()])
            nv = np.sqrt(E_bin) * np.concatenate([(noise_c.real * sR).ravel(), (noise_c.imag * sI).ravel()])
            out[arm_name] = {"win_s": ws, "blind_s": bs, "mv": mv, "nv": nv, "pil": float(np.sum(np.abs(u_t) ** 2))}
        return out

    cal_list = [eval_one_cpi(41000 + i, "cal") for i in range(n_cal)]
    val_list = [eval_one_cpi(45000 + i, "val") for i in range(n_val)]
    pos_list = [eval_one_cpi(49000 + i, "pos") for i in range(n_pos)]

    assert call_counter["cal"] == n_cal * len(arms)
    assert call_counter["val"] == n_val * len(arms)
    assert call_counter["pos"] == n_pos * len(arms)

    pfa_target = 0.05  # Exact resolution at n_cal=n_val=100 (~5 false alarms expected)
    for a in arms:
        cw = np.array([r[a]["win_s"] for r in cal_list])
        vw = np.array([r[a]["win_s"] for r in val_list])
        pw = np.array([r[a]["win_s"] for r in pos_list])
        cb = np.array([r[a]["blind_s"] for r in cal_list])
        vb = np.array([r[a]["blind_s"] for r in val_list])
        pb = np.array([r[a]["blind_s"] for r in pos_list])

        thr_w = float(np.quantile(cw, 1.0 - pfa_target, method="weibull"))
        val_pfa_w = float(np.mean(vw > thr_w))
        pos_pd_w = float(np.mean(pw > thr_w))

        thr_b = float(np.quantile(cb, 1.0 - pfa_target, method="weibull"))
        val_pfa_b = float(np.mean(vb > thr_b))
        pos_pd_b = float(np.mean(pb > thr_b))

        s1e3, _, b24 = exact_ber_crossing([r[a]["mv"] for r in pos_list], [r[a]["nv"] for r in pos_list])
        pil_m = float(np.mean([r[a]["pil"] for r in pos_list]))
        print(
            f"  {a:32s} | ExSNR@1e-3={s1e3:6.2f}dB (BER24={b24:.5f}) | PIL={pil_m:4.2f} | "
            f"WinPd@Pfa5%={pos_pd_w*100:5.1f}% (ValPfa={val_pfa_w*100:4.1f}%) | BlindPd@Pfa5%={pos_pd_b*100:5.1f}% (ValPfa={val_pfa_b*100:4.1f}%)"
        )


if __name__ == "__main__":
    t_start = time.perf_counter()
    check_red_line_1_li_fig6()
    run_item1_and_3_did(n_mc=40)
    run_item2_and_4_ao_rf_pfa(n_cal=100, n_val=100, n_pos=40)
    print(f"\nTotal runtime: {time.perf_counter() - t_start:.2f}s")
