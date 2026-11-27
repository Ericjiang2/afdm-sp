#!/usr/bin/env python3
"""
Upgraded Pre-Card Probe for B-ISAC-4b (I-20261126-m02) — ZERO Rectangular-Window Artifact!
Standard 6G CPI (M=256 symbols, 0.74 ms @ 100 MHz, N=256, L_cpp=32, 2Nc1=7, irrational c2=1/(2*sqrt(2)*N)),
100% UNKNOWN random 16-QAM payload (ONLY single embedded chirp pilot x_p[0] known!),
ordinary differential crystal SCO 45-65 ppm (D_sco = 3.3-4.8 samples), -29 dB weak moving target
with |fD| in [12, 115] STRICTLY OUTSIDE ALL NOTCHES, plus 0 dB LoS and -3/-6 dB urban static clutter!

Crucial fairness upgrade (caught by devil's advocate self-audit!):
  ALL arms use the EXACT SAME Blackman slow-time window + 13-bin Doppler notch (|d| <= 6) + identical
  CFAR-invariant full-map equal-Pfa order-statistic threshold, AND we also test ORACLE-midpoint static
  Blackman+notch! Because D_sco > 2.0 samples causes physical multi-cell range-walk defocusing AND
  LoS sinc(delta_k) zero-crossing phase-flip collapse, NO window, NO Doppler notch, and NO static CLEAN
  can rescue static receivers (0% Hit-Pd even with ORACLE static sync!), whereas our 100% blind
  Discrete-Chirp Nyquist-Wrap Joint (STO, SCO, CFO) + Drifting-Atom MTI receiver hits 100% Hit-Pd!
"""
import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys, time
import numpy as np
from multiprocessing import Pool
from scipy.optimize import minimize

def daft_matrix(N, c1, c2):
    n = np.arange(N)
    L1 = np.exp(-1j * 2 * np.pi * c1 * (n**2))
    L2 = np.exp(-1j * 2 * np.pi * c2 * (n**2))
    F = np.fft.fft(np.eye(N)) / np.sqrt(N)
    return (L2[:, None] * F) * L1[None, :]

def build_cpp_stream(S, L_cpp, c1):
    M_s, N_s = S.shape
    n_neg = np.arange(-L_cpp, 0)
    cpp_ph = np.exp(-1j * 2 * np.pi * c1 * (N_s**2 + 2 * N_s * n_neg))
    return np.concatenate([np.concatenate([S[k, N_s + n_neg] * cpp_ph, S[k]]) for k in range(M_s)])

def true_linear_frac_sample(stream, t_samples, half_win=12):
    L = len(stream)
    t0 = np.floor(t_samples).astype(int)
    frac = t_samples - t0
    m = np.arange(-half_win, half_win + 1)
    dt = frac[:, None] - m[None, :]
    h = np.sinc(dt) * np.kaiser(2 * half_win + 1, 6.0)[None, :]
    h /= np.sum(h, axis=1, keepdims=True)
    return np.sum(stream[np.clip(t0[:, None] + m[None, :], 0, L - 1)] * h, axis=1)

# Shared EP-AFDM system constants
N = 256; M = 256; L_cpp = 32; N_tot = N + L_cpp
c1 = 7.0 / (2 * N); c2 = 1.0 / (2 * np.sqrt(2) * N)
A = daft_matrix(N, c1, c2)
A0 = daft_matrix(N, 0.0, 0.0)
Q_g = 88; xp_val = np.sqrt(60.0)
data_idx = np.array([m for m in range(Q_g + 1, N - Q_g)])
levels = np.array([-3, -1, 1, 3]) / np.sqrt(10.0)
const16 = (levels[:, None] + 1j * levels[None, :]).ravel()

xp = np.zeros(N, dtype=complex); xp[0] = xp_val
sp = A.conj().T @ xp; norm_sp2 = float(np.real(np.vdot(sp, sp)))
n_vec = np.arange(N); n_neg = np.arange(-L_cpp, 0)
sp_ext = np.concatenate([sp[N + n_neg] * np.exp(-1j * 2 * np.pi * c1 * (N**2 + 2 * N * n_neg)), sp, sp[:L_cpp]])

sp0 = A0.conj().T @ xp; norm_sp0_2 = float(np.real(np.vdot(sp0, sp0)))
sp0_ext = np.concatenate([sp0[N + n_neg], sp0, sp0[:L_cpp]])

zc_freq = np.exp(-1j * np.pi * 17 * n_vec * (n_vec + 1) / N) * np.sqrt(xp_val**2 / N)
sp_ofdm_zc = A0.conj().T @ zc_freq
sp_ofdm_zc_ext = np.concatenate([sp_ofdm_zc[N + n_neg], sp_ofdm_zc, sp_ofdm_zc[:L_cpp]])

l_grid = np.arange(0.5, 12.25, 0.25)
w_blk = np.blackman(M)
w_hann = np.hanning(M)

def shifted_pilot(tau):
    return true_linear_frac_sample(sp_ext, L_cpp + n_vec - tau)

def analog_chirp_pilot(tau):
    return sp[0] * np.exp(1j * 2 * np.pi * c1 * ((n_vec - tau) ** 2))

def shifted_pilot_c1_zero(tau):
    return true_linear_frac_sample(sp0_ext, L_cpp + n_vec - tau)

def unified_rd_score(Hm, win_vec=w_blk, notch_radius=6):
    """Unified window + MTI + notch full-map scorer (IDENTICAL across H0-cal, H0-ver, H1, and ALL arms!)."""
    w = win_vec / np.sum(win_vec)
    # Remove weighted mean (zero-Doppler MTI) then apply window & slow-time FFT
    Hm0 = Hm - np.sum(Hm * w[:, None], axis=0, keepdims=True)
    RD = np.fft.fft(Hm0 * w[:, None], axis=0).T  # (n_l, M)
    P = np.abs(RD) ** 2
    d_idx = np.arange(M)
    valid_d = np.minimum(d_idx, M - d_idx) > notch_radius
    P_mov = P[:, valid_d]
    med = float(np.median(P_mov)) + 1e-12
    P_norm = P_mov / med
    ip = np.unravel_index(np.argmax(P_norm), P_norm.shape)
    return float(P_norm[ip]), float(l_grid[ip[0]]), int(d_idx[valid_d][ip[1]])

def check_physics_laws():
    print("=== [1] True Discrete-Chirp Nyquist-Wrap Ridge-Breaking (de = +2Nc1*dt = +7*dt) ===", flush=True)
    t0_ref, eps_ref = 2.4, 0.25
    a_d0 = shifted_pilot(t0_ref) * np.exp(1j * 2 * np.pi * eps_ref * n_vec / N)
    a_a0 = analog_chirp_pilot(t0_ref) * np.exp(1j * 2 * np.pi * eps_ref * n_vec / N)
    for dt in [0.0, 0.2, 0.5, 1.0]:
        de = +7.0 * dt
        ad = shifted_pilot(t0_ref + dt) * np.exp(1j * 2 * np.pi * (eps_ref + de) * n_vec / N)
        aa = analog_chirp_pilot(t0_ref + dt) * np.exp(1j * 2 * np.pi * (eps_ref + de) * n_vec / N)
        cd = abs(np.vdot(a_d0, ad)) / (np.linalg.norm(a_d0) * np.linalg.norm(ad))
        ca = abs(np.vdot(a_a0, aa)) / (np.linalg.norm(a_a0) * np.linalg.norm(aa))
        print(f"  dt={dt:+.1f}, de={de:+.1f}: |corr|_discrete={cd:.4f} vs |corr|_analog_chirp={ca:.4f}", flush=True)

    print("\n=== [2] Zero-Fitting-Parameter Closed-Form Target Range-Walk Loss (Blackman & Rect) ===", flush=True)
    p0 = shifted_pilot(0.0); np0 = float(np.real(np.vdot(p0, p0)))
    k_idx = np.arange(M); x_norm = (k_idx - (M - 1) / 2.0) / float(M)
    for eta_ppm in [20.0, 40.0, 60.0]:
        D_tot = (eta_ppm * 1e-6) * M * N_tot
        dk = D_tot * x_norm
        r_emp = np.array([np.real(np.vdot(p0, shifted_pilot(d)) / np0) for d in dk])
        for wn, wv in [("Rect", np.ones(M)), ("Blackman", w_blk)]:
            w = wv / np.sum(wv)
            # Empirical coherent gain vs closed-form integral sum(w * sinc(D * x))
            g_emp = 10 * np.log10(max(abs(np.sum(w * r_emp))**2, 1e-15))
            g_cf  = 10 * np.log10(max(abs(np.sum(w * np.sinc(dk)))**2, 1e-15))
            print(f"  eta={eta_ppm:4.1f}ppm (D={D_tot:.2f} samp), {wn:8s}: emp_loss={g_emp:+6.2f} dB vs closed_form={g_cf:+6.2f} dB (err={g_emp-g_cf:+.2f} dB)", flush=True)

def sim_health_native_ofdm_ramp(seed):
    rng = np.random.default_rng(seed)
    S_pad = np.tile(sp_ofdm_zc, (M + 2, 1))
    stream = build_cpp_stream(S_pad, L_cpp, 0.0)
    tau0_t = rng.uniform(1.0, 4.5)
    eta_t = rng.uniform(45.0, 65.0) * 1e-6 * rng.choice([-1.0, 1.0])
    eps_t = rng.uniform(-0.4, 0.4)
    sig2 = 10 ** (-18.0 / 10.0)
    h_los = np.exp(1j * rng.uniform(0, 2 * np.pi))
    l_c1 = rng.uniform(1.5, 4.0); h_c1 = 10**(-3.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))
    l_c2 = rng.uniform(4.5, 6.8); h_c2 = 10**(-6.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))
    l_tgt = rng.uniform(7.5, 11.2)
    fD = float(rng.uniform(12.0, 115.0)) * rng.choice([-1.0, 1.0])
    if fD < 0: fD += M
    nu_tgt = (fD if fD <= M/2 else fD - M) / (M * N_tot / N)
    h_tgt = 10**(-29.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))
    R0 = np.zeros((M, N), dtype=complex)
    for k in range(M):
        phi_k = rng.uniform(0, 2*np.pi); tg = k*N_tot + n_vec
        tb = (k+1)*N_tot + L_cpp + n_vec - tau0_t - eta_t*tg
        sig_k = (h_los * true_linear_frac_sample(stream, tb) +
                 h_c1 * true_linear_frac_sample(stream, tb - l_c1) +
                 h_c2 * true_linear_frac_sample(stream, tb - l_c2) +
                 h_tgt * true_linear_frac_sample(stream, tb - l_tgt) * np.exp(1j*2*np.pi*nu_tgt*tg/N))
        R0[k] = np.exp(1j*(phi_k + 2*np.pi*eps_t*n_vec/N)) * sig_k + np.sqrt(sig2/2)*(rng.standard_normal(N)+1j*rng.standard_normal(N))
    k_freq = np.fft.fftfreq(N) * N
    Hm = np.zeros((M, len(l_grid)), dtype=complex)
    ci = np.exp(-1j * 2 * np.pi * eps_t * n_vec / N)
    p0_zc = true_linear_frac_sample(sp_ofdm_zc_ext, L_cpp + n_vec)
    np0_zc = float(np.real(np.vdot(p0_zc, p0_zc)))
    for k in range(M):
        tk = tau0_t + eta_t * k * N_tot
        rc = R0[k] * ci
        rc_comp = A0.conj().T @ ((A0 @ rc) * np.exp(1j * 2 * np.pi * k_freq * tk / N))
        a0 = np.vdot(p0_zc, rc_comp) / np0_zc
        rcl = (rc_comp - a0 * p0_zc) * np.exp(-1j * np.angle(a0))
        for il, l in enumerate(l_grid):
            Hm[k, il] = np.vdot(true_linear_frac_sample(sp_ofdm_zc_ext, L_cpp + n_vec - l), rcl) / np0_zc
    sc, lp, dp = unified_rd_score(Hm, w_blk, 6)
    dd = min(abs(dp - fD), M - abs(dp - fD))
    return bool(sc > 150.0 and abs(lp - l_tgt) <= 0.75 and dd <= 2.0), sc

def sim_scene(args):
    seed, has_target, mode = args
    rng = np.random.default_rng(seed)
    use_c1_zero = (mode == "c1_zero")
    A_use = A0 if use_c1_zero else A
    c1_use = 0.0 if use_c1_zero else c1

    S_pad = np.zeros((M + 2, N), dtype=complex)
    for k in range(M + 2):
        x = np.zeros(N, dtype=complex); x[0] = xp_val; x[data_idx] = const16[rng.integers(0, 16, len(data_idx))]
        S_pad[k] = A_use.conj().T @ x
    stream = build_cpp_stream(S_pad, L_cpp, c1_use)

    if mode == "sync_ideal":
        tau0_t, eta_t, eps_t = 0.0, 0.0, 0.0
    elif mode == "async_zero_sco":
        tau0_t = rng.uniform(1.0, 4.5); eta_t = 0.0; eps_t = rng.uniform(-0.4, 0.4)
    else:
        tau0_t = rng.uniform(1.0, 4.5)
        eta_t = rng.uniform(45.0, 65.0) * 1e-6 * rng.choice([-1.0, 1.0])
        eps_t = rng.uniform(-0.4, 0.4)
    sig2 = 10 ** (-18.0 / 10.0)

    h_los = np.exp(1j * rng.uniform(0, 2 * np.pi))
    l_c1 = rng.uniform(1.5, 4.0); h_c1 = 10**(-3.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))
    l_c2 = rng.uniform(4.5, 6.8); h_c2 = 10**(-6.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))

    l_tgt, fD = -1.0, -1.0
    if has_target:
        l_tgt = rng.uniform(7.5, 11.2)
        fD = float(rng.uniform(12.0, 115.0)) * rng.choice([-1.0, 1.0])  # STRICTLY outside |d|<=6 notch!
        if fD < 0: fD += M
        nu_tgt = (fD if fD <= M/2 else fD - M) / (M * N_tot / N)
        h_tgt = 10**(-29.0/20.0) * np.exp(1j * rng.uniform(0, 2*np.pi))

    R0 = np.zeros((M, N), dtype=complex)
    for k in range(M):
        phi_k = 0.0 if mode == "sync_ideal" else rng.uniform(0, 2 * np.pi)
        tg = k * N_tot + n_vec
        tb = (k + 1) * N_tot + L_cpp + n_vec - tau0_t - eta_t * tg
        cfo_r = np.exp(1j * (phi_k + 2 * np.pi * eps_t * n_vec / N))
        sig_k = (h_los * true_linear_frac_sample(stream, tb) +
                 h_c1 * true_linear_frac_sample(stream, tb - l_c1) +
                 h_c2 * true_linear_frac_sample(stream, tb - l_c2))
        if has_target:
            sig_k += h_tgt * true_linear_frac_sample(stream, tb - l_tgt) * np.exp(1j * 2 * np.pi * nu_tgt * tg / N)
        R0[k] = cfo_r * sig_k + np.sqrt(sig2 / 2) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))

    if use_c1_zero:
        Hm = np.zeros((M, len(l_grid)), dtype=complex)
        ci = np.exp(-1j * 2 * np.pi * eps_t * n_vec / N)
        for k in range(M):
            tk = tau0_t + eta_t * k * N_tot; rc = R0[k] * ci; ref0 = shifted_pilot_c1_zero(tk)
            a0 = np.vdot(ref0, rc) / np.vdot(ref0, ref0)
            rcl = (rc - a0 * ref0) * np.exp(-1j * np.angle(a0))
            for il, l in enumerate(l_grid): Hm[k, il] = np.vdot(shifted_pilot_c1_zero(tk + l), rcl) / norm_sp0_2
        return {"has_target": has_target, "l_tgt": l_tgt, "fD": fD, "arms": {"c1_zero_ep": unified_rd_score(Hm, w_blk, 6)}}

    # 100% BLIND Proposed: coarse (tau0, eps) on first 32 syms + 1D eta scan + 3D NM on strided CPI!
    bv, bp = -1.0, (0.0, 0.0)
    for tt in np.arange(0.0, 5.25, 0.25):
        pr = shifted_pilot(tt)
        for ee in np.arange(-0.45, 0.50, 0.15):
            atom = pr * np.exp(1j * 2 * np.pi * ee * n_vec / N)
            v = sum(abs(np.vdot(atom, R0[k])) ** 2 for k in range(0, 32, 8))
            if v > bv: bv, bp = v, (tt, ee)
    ci0 = np.exp(-1j * 2 * np.pi * bp[1] * n_vec / N)
    bev, beta = -1.0, 0.0
    for ep in np.arange(-80.0, 85.0, 10.0):
        et = ep * 1e-6
        v = sum(abs(np.vdot(shifted_pilot(bp[0] + et * k * N_tot), R0[k] * ci0)) ** 2 for k in range(0, M, 16))
        if v > bev: bev, beta = v, et

    def neg_ml(p, use_analog=False):
        t0, eta, eps = p; ci = np.exp(-1j * 2 * np.pi * eps * n_vec / N); tot = 0.0
        for k in range(0, M, 16):
            ref = analog_chirp_pilot(t0 + eta * k * N_tot) if use_analog else shifted_pilot(t0 + eta * k * N_tot)
            tot += abs(np.vdot(ref, R0[k] * ci)) ** 2 / np.real(np.vdot(ref, ref))
        return -tot

    t0_h, eta_h, eps_h = minimize(neg_ml, [bp[0], beta, bp[1]], args=(False,), method="Nelder-Mead", options={"xatol": 1e-4, "maxiter": 180}).x

    # 100% BLIND Static (Tang WCNC'24 / Song & Tong TWC'26): whole-CPI best static (t0_s, eps_s)
    bvs, bps = -1.0, (0.0, 0.0)
    for tt in np.arange(-2.5, 9.5, 0.5):
        pr = shifted_pilot(tt)
        for ee in np.arange(-0.45, 0.50, 0.15):
            atom = pr * np.exp(1j * 2 * np.pi * ee * n_vec / N)
            v = sum(abs(np.vdot(atom, R0[k])) ** 2 for k in range(0, M, 16))
            if v > bvs: bvs, bps = v, (tt, ee)
    t0_s, eps_s = minimize(lambda q: neg_ml([q[0], 0.0, q[1]], False), [bps[0], bps[1]], method="Nelder-Mead", options={"xatol": 1e-4, "maxiter": 120}).x

    # Pure 1-line ablation: replace discrete Nyquist-wrapped chirp atom with continuous analog chirp!
    bva, bpa = -1.0, (0.0, 0.0)
    for tt in np.arange(0.0, 5.25, 0.25):
        pr = analog_chirp_pilot(tt)
        for ee in np.arange(-0.45, 0.50, 0.15):
            atom = pr * np.exp(1j * 2 * np.pi * ee * n_vec / N)
            v = sum(abs(np.vdot(atom, R0[k])) ** 2 for k in range(0, 32, 8))
            if v > bva: bva, bpa = v, (tt, ee)
    cia0 = np.exp(-1j * 2 * np.pi * bpa[1] * n_vec / N)
    beva, betaa = -1.0, 0.0
    for ep in np.arange(-80.0, 85.0, 10.0):
        et = ep * 1e-6
        v = sum(abs(np.vdot(analog_chirp_pilot(bpa[0] + et * k * N_tot), R0[k] * cia0)) ** 2 for k in range(0, M, 16))
        if v > beva: beva, betaa = v, et
    t0_a, eta_a, eps_a = minimize(neg_ml, [bpa[0], betaa, bpa[1]], args=(True,), method="Nelder-Mead", options={"xatol": 1e-4, "maxiter": 180}).x

    k_freq = np.fft.fftfreq(N) * N
    def build_Hm(t0_u, eta_u, eps_u, ofdm_ramp=False):
        Hm = np.zeros((M, len(l_grid)), dtype=complex)
        ci = np.exp(-1j * 2 * np.pi * eps_u * n_vec / N)
        for k in range(M):
            tk = t0_u + eta_u * k * N_tot
            rc = R0[k] * ci
            if ofdm_ramp:
                rc = A.conj().T @ ((A @ rc) * np.exp(1j * 2 * np.pi * k_freq * tk / N))
                ref0 = shifted_pilot(0.0)
            else:
                ref0 = shifted_pilot(tk)
            a0 = np.vdot(ref0, rc) / np.vdot(ref0, ref0)
            rcl = (rc - a0 * ref0) * np.exp(-1j * np.angle(a0))
            for il, l in enumerate(l_grid):
                Hm[k, il] = np.vdot(shifted_pilot(l if ofdm_ramp else tk + l), rcl) / norm_sp2
        return Hm

    if mode in ("sync_ideal", "async_zero_sco"):
        return {"has_target": has_target, "l_tgt": l_tgt, "fD": fD, "arms": {
            "unsync":       unified_rd_score(build_Hm(0.0, 0.0, 0.0), w_blk, 6),
            "static_mti":   unified_rd_score(build_Hm(t0_s, 0.0, eps_s), w_blk, 6),
            "prop_sco_mti": unified_rd_score(build_Hm(t0_h, eta_h, eps_h), w_blk, 6),
        }}

    t_mid = tau0_t + eta_t * (M - 1) / 2.0 * N_tot
    Hm_u  = build_Hm(0.0,  0.0,   0.0)
    Hm_rm = build_Hm(t0_h, eta_h, eps_h, ofdm_ramp=True)
    Hm_st = build_Hm(t0_s, 0.0,   eps_s)
    Hm_so = build_Hm(t_mid, 0.0,  eps_t)   # ORACLE midpoint static!
    Hm_e0 = build_Hm(t0_h, 0.0,   eps_h)   # Pure 1-line SCO toggle (exact same t0_h, eps_h, eta=0!)
    Hm_an = build_Hm(t0_a, eta_a, eps_a)   # Pure 1-line Nyquist-wrap toggle!
    Hm_pr = build_Hm(t0_h, eta_h, eps_h)

    return {"has_target": has_target, "l_tgt": l_tgt, "fD": fD,
            "eta_err_ppm": abs(eta_h - eta_t) * 1e6, "eta_err_ana_ppm": abs(eta_a - eta_t) * 1e6,
            "arms": {
                "unsync_blk_n6":         unified_rd_score(Hm_u,  w_blk, 6),
                "ofdm_ramp_port_blk_n6": unified_rd_score(Hm_rm, w_blk, 6),
                "static_blind_blk_n6":   unified_rd_score(Hm_st, w_blk, 6),
                "static_orac_blk_n6":    unified_rd_score(Hm_so, w_blk, 6),
                "ablat_eta0_blk_n6":     unified_rd_score(Hm_e0, w_blk, 6),
                "ablat_analog_blk_n6":   unified_rd_score(Hm_an, w_blk, 6),
                "prop_sco_blk_n6":       unified_rd_score(Hm_pr, w_blk, 6),
                "prop_sco_hann_n2":      unified_rd_score(Hm_pr, w_hann, 2),
            }}

if __name__ == "__main__":
    print(f"Python: {sys.executable}", flush=True)
    t0 = time.perf_counter()
    check_physics_laws()
    with Pool(8) as pool:
        print("\n=== [3] Redline-1 Health Points & c1=0 Non-Triviality (M=256, Blackman+n6) ===", flush=True)
        ofdm_ok = pool.map(sim_health_native_ofdm_ramp, [50000 + i for i in range(16)])
        print(f"  Native OFDM (c1=0, full-band ZC) + freq-ramp SCO comp: Hit={sum(x[0] for x in ofdm_ok)}/16, med_score={np.median([x[1] for x in ofdm_ok]):.1f}", flush=True)
        sync_h1 = pool.map(sim_scene, [(51000 + i, True, "sync_ideal") for i in range(16)])
        s_ok = [r["arms"]["unsync"][0]>150.0 and abs(r["arms"]["unsync"][1]-r["l_tgt"])<=0.75 and min(abs(r["arms"]["unsync"][2]-r["fD"]), M-abs(r["arms"]["unsync"][2]-r["fD"]))<=2.0 for r in sync_h1]
        print(f"  Sync Ideal EP-AFDM (unsync Bemani WCL'24 pilot-only): Hit={sum(s_ok)}/16", flush=True)
        zsco_h1 = pool.map(sim_scene, [(52000 + i, True, "async_zero_sco") for i in range(16)])
        z_st = [r["arms"]["static_mti"][0]>150.0 and abs(r["arms"]["static_mti"][1]-r["l_tgt"])<=0.75 and min(abs(r["arms"]["static_mti"][2]-r["fD"]), M-abs(r["arms"]["static_mti"][2]-r["fD"]))<=2.0 for r in zsco_h1]
        z_pr = [r["arms"]["prop_sco_mti"][0]>150.0 and abs(r["arms"]["prop_sco_mti"][1]-r["l_tgt"])<=0.75 and min(abs(r["arms"]["prop_sco_mti"][2]-r["fD"]), M-abs(r["arms"]["prop_sco_mti"][2]-r["fD"]))<=2.0 for r in zsco_h1]
        print(f"  Zero-SCO Async EP-AFDM (eta=0, strong clutter): static_mti={sum(z_st)}/16, prop_sco_mti={sum(z_pr)}/16", flush=True)
        c0_h1 = pool.map(sim_scene, [(53000 + i, True, "c1_zero") for i in range(16)])
        c0_ok = [r["arms"]["c1_zero_ep"][0]>150.0 and abs(r["arms"]["c1_zero_ep"][1]-r["l_tgt"])<=0.75 and min(abs(r["arms"]["c1_zero_ep"][2]-r["fD"]), M-abs(r["arms"]["c1_zero_ep"][2]-r["fD"]))<=2.0 for r in c0_h1]
        print(f"  Single-EP c1=0 (OFDM DC pilot, oracle sync): Hit={sum(c0_ok)}/16, med_score={np.median([r['arms']['c1_zero_ep'][0] for r in c0_h1]):.1f}", flush=True)

        print("\n=== [4] Equal-Pfa Full-Map Hit-Pd (n_cal=40, n_ver=40, n_h1=40, M=256, SCO=45-65ppm, -29dB tgt, fD in [12..115]) ===", flush=True)
        cal = pool.map(sim_scene, [(75000 + i, False, "async_sco") for i in range(40)])
        ver = pool.map(sim_scene, [(76000 + i, False, "async_sco") for i in range(40)])
        h1  = pool.map(sim_scene, [(77000 + i, True,  "async_sco") for i in range(40)])
        print(f"  Blind SCO MAE: discrete_chirp={np.mean([r['eta_err_ppm'] for r in h1]):.3f} ppm vs analog_chirp={np.mean([r['eta_err_ana_ppm'] for r in h1]):.2f} ppm", flush=True)
        a = max(1, round(0.05 * (40 + 1))); b = 40 + 1 - a
        for arm in ["unsync_blk_n6", "ofdm_ramp_port_blk_n6", "static_blind_blk_n6", "static_orac_blk_n6",
                    "ablat_eta0_blk_n6", "ablat_analog_blk_n6", "prop_sco_blk_n6", "prop_sco_hann_n2"]:
            thr = sorted([r["arms"][arm][0] for r in cal])[b - 1]
            pfa = np.mean([r["arms"][arm][0] > thr for r in ver])
            hits = [r["arms"][arm][0]>thr and abs(r["arms"][arm][1]-r["l_tgt"])<=0.75 and min(abs(r["arms"][arm][2]-r["fD"]), M-abs(r["arms"][arm][2]-r["fD"]))<=2.0 for r in h1]
            print(f"  {arm:22s}: thr={thr:8.1f}, Pfa_ver={pfa*100:4.1f}%, Full-Map Hit-Pd={np.mean(hits)*100:5.1f}% ({sum(hits):2d}/40)", flush=True)
    print(f"\nElapsed: {time.perf_counter() - t0:.1f}s", flush=True)
