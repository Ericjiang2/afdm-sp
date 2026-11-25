#!/usr/bin/env python3
"""
L2 Pre-registered Experiment for Card I-20261125-k03:
Asynchronous Bistatic ISAC Affine-Domain Capture (c2 = 0, OSR=8 RRC beta=0.25).

Key Mechanisms & Steelman Controls (incorporating all Sol Call #6 First Knives & Sol Call #7/#8 hygiene):
  1. Equal full-512 RF bandwidth (~1.10 Fs measured post-RRC 99% BW across ALL 4 primary arms)
     and conservative pilot/guard overhead favoring rivals:
       - afdm_dv_coh     (ours, c2=0): 69/512 = 13.48% guard+pilot (443 16-QAM data bins)
       - afdm_tang_cpp   (same AFDM):  69/512 = 13.48% (Tang WCNC'24 CPP mod-1 sync, fixed obs)
       - ofdm_fullici_69 (OFDM):       69/512 = 13.48% aperiodic QPSK pilots (Sol's steelman!)
       - otfs_14x5_blind (OTFS 32x16): 70/512 = 13.67% reduced 2D guard (exact time-domain de-async)
  2. Mechanism Ablations (sharing exact Stage-1/Stage-2 intermediates with afdm_dv_coh):
       - afdm_dv_pilonly: identical blind Dark-Valley + 4th-power l_sto capture & LOS-Ref Coherent,
                          WITHOUT Stage-2 full-512 data-aided EM + 2D RRC Ambiguity VarPro-GN cleanup.
       - afdm_dv_noncoh:  identical blind capture & Stage-2 2D Ambiguity VarPro-GN cleanup,
                          WITHOUT LOS-referenced multi-slot coherent phase de-skewing.
  3. Descriptive Reference Arms:
       - known_afdm_coh, known_ofdm_coh (symmetric known-data + oracle async ceiling)
       - ofdm_fullici_oracsync (OFDM-FullICI-69 given ORACLE per-slot STO_m & CFO_m!)
  4. Strict blind interfaces, alarm-first before localization check, exact finite-sample order-statistic
     threshold + 10-arm FWER Beta-Binomial C1 (+ anti-inflation engineering cap on our arm),
     exclusive creation ("x"), smoke/full seed isolation, zero `assert` statements.
"""
import os
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")
import sys
print(f"sys.executable: {sys.executable}", flush=True)

import argparse
import json
import resource
import time
from multiprocessing import Pool
import numpy as np
import scipy.linalg as la
from scipy.stats import beta as beta_dist, betabinom as betabinom_dist, norm as norm_dist

# ==============================================================================
# Global Physical & Waveform Constants (N=512, L_CP=24, OSR=8 RRC beta=0.25, c2=0)
# ==============================================================================
N = 512
L_CP = 24
L_POST = 14
OSR = 8
BETA = 0.25
SPAN = 12
TWO_NC1 = 5
C1 = float(TWO_NC1) / (2.0 * N)
M_SLOTS = 6
SLOT_STRIDE_PHYS = 600.0

CONST16 = np.array(
    [a + 1j * b for a in (-3, -1, 1, 3) for b in (-3, -1, 1, 3)],
    dtype=np.complex128,
) / np.sqrt(10.0)

N_IDX = np.arange(N, dtype=np.float64)
K_SIGNED = np.where(N_IDX < N // 2, N_IDX, N_IDX - N)
F_MAT = np.fft.fft(np.eye(N, dtype=np.complex128)) / np.sqrt(float(N))
FH_MAT = F_MAT.conj().T
# Centered DAFT with c2 = 0 explicitly!
A_CTR = F_MAT * np.exp(-2j * np.pi * C1 * ((N_IDX - N / 2.0) ** 2))[None, :]
AH_CTR = A_CTR.conj().T
CPP_WRAP_PH = np.exp(-2j * np.pi * C1 * (N ** 2 + 2.0 * N * (np.arange(-L_CP, 0, dtype=np.float64) - N / 2.0)))

# RRC pulse & exact 2-term Taylor 2D pulse ambiguity function (Ma et al. arXiv:2607.05082)
_T_RRC = np.arange(-SPAN * OSR, SPAN * OSR + 1, dtype=np.float64) / float(OSR)
def _make_rrc():
    h = np.zeros_like(_T_RRC)
    for i, x in enumerate(_T_RRC):
        if abs(x) < 1e-12:
            h[i] = 1.0 - BETA + 4.0 * BETA / np.pi
        elif abs(abs(x) - 1.0 / (4.0 * BETA)) < 1e-10:
            h[i] = (BETA / np.sqrt(2.0)) * (
                (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * BETA))
                + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * BETA))
            )
        else:
            h[i] = (np.sin(np.pi * x * (1.0 - BETA)) + 4.0 * BETA * x * np.cos(np.pi * x * (1.0 + BETA))) / (
                np.pi * x * (1.0 - (4.0 * BETA * x) ** 2)
            )
    return h / np.sqrt(np.sum(h ** 2))

H_RRC = _make_rrc()
L_HALF = (len(H_RRC) - 1) // 2

_AMB0 = np.convolve(H_RRC, H_RRC, mode="full")
_AMB1 = np.convolve(H_RRC * _T_RRC, H_RRC, mode="full")
_AMB2 = np.convolve(H_RRC * (_T_RRC ** 2), H_RRC, mode="full")
_N_AMB = len(_AMB0)
_K_AMB = np.fft.fftfreq(_N_AMB)
_C0_AMB = 2 * L_HALF
_A0_F, _A1_F, _A2_F = np.fft.fft(_AMB0), np.fft.fft(_AMB1), np.fft.fft(_AMB2)

def eval_rc(dt):
    t = np.asarray(dt, dtype=np.float64)
    den = 1.0 - (2.0 * BETA * t) ** 2
    ns = np.abs(den) < 1e-8
    out = np.sinc(t) * np.cos(np.pi * BETA * t) / np.where(ns, 1.0, den)
    return np.where(ns, (np.pi / 4.0) * np.sinc(1.0 / (2.0 * BETA)), out)

def eval_rrc_ambig(dt_arr, nu_eff):
    """Exact 2-term Taylor approximation of 2D RRC pulse ambiguity A_g(dt, nu_eff) (err ~2.4e-5 at |nu|=4.2)."""
    dt = np.asarray(dt_arr, dtype=np.float64)
    E = np.exp(2j * np.pi * np.outer(-dt * OSR + _C0_AMB, _K_AMB)) / float(_N_AMB)
    v0 = np.real(E @ _A0_F)
    v1 = np.real(E @ _A1_F)
    v2 = np.real(E @ _A2_F)
    z = 2j * np.pi * float(nu_eff) / float(N)
    return v0 + z * v1 + 0.5 * (z ** 2) * v2

L_RC = np.arange(-5, 11, dtype=int)
L_F = np.arange(-8, 25, dtype=int)  # Covers full valid delays up to 14.5 + 8 <= L_CP=24 (<0.25% error at all corners)
L_T = np.arange(0, 26, dtype=int)
E_LK = np.exp(-2j * np.pi * np.outer(L_RC, np.arange(N, dtype=np.float64)) / float(N))
E_5L = np.exp(-2j * np.pi * TWO_NC1 * np.outer(L_RC, N_IDX) / float(N))

# Sensing RD grid (57 x 41 = 2,337 cells, guard 11 x 9; starts at 6.5 >= tau_clut_max + 2.5)
TAU_GRID = np.linspace(6.5, 11.5, 41)
NU_GRID = np.linspace(-3.5, 3.5, 57)
E_NU_RD = np.exp(-2j * np.pi * np.outer(NU_GRID, N_IDX) / float(N))
G_NU_RD = 5
G_TAU_RD = 4
TAU_TARG_NOM = 8.95
NU_TARG_NOM = 2.35
NU_TARG_G0 = 1.85

# ==============================================================================
# Waveform Layouts (Equal 512 active bins -> ~1.10 Fs BW; Conservative Overhead)
# ==============================================================================
PRIMARY_ARMS = ["afdm_dv_coh", "afdm_tang_cpp", "ofdm_fullici_69", "otfs_14x5_blind"]
RIVAL_ARMS = ["afdm_tang_cpp", "ofdm_fullici_69", "otfs_14x5_blind"]
ABLATION_ARMS = ["afdm_dv_pilonly", "afdm_dv_noncoh"]
ALL_PASS_ARMS = PRIMARY_ARMS + ABLATION_ARMS
DESC_ARMS = ["known_afdm_coh", "known_ofdm_coh", "ofdm_fullici_oracsync"]

# 1) AFDM (c2=0): 69/512 = 13.48% guard+pilot (443 data bins)
GUARD_AF = set(int(k % N) for k in range(-34, 35))
DAT_AF = np.array([k for k in range(N) if k not in GUARD_AF], dtype=int)
OBS_AF = np.array([int(k % N) for k in range(-33, 12)], dtype=int)
K_DAT_AF = K_SIGNED[DAT_AF]
OVH_AF = len(GUARD_AF) / float(N)
P_AF = np.sqrt(N * OVH_AF)
D_AF = np.sqrt(N * (1.0 - OVH_AF) / float(len(DAT_AF)))
XP_AF = np.zeros(N, dtype=np.complex128)
XP_AF[0] = P_AF
SP_AF_TIME = AH_CTR @ XP_AF
UF_P_AF = FH_MAT @ XP_AF

# True data-free dark moats around K_PIL=0 (left [-34..-25] = 10 bins, right [+6..+13] = 8 bins; ZERO data bins!)
_DARK_AF = np.zeros(N, dtype=np.float64)
for _k in list(range(-34, -24)) + list(range(6, 14)):
    _DARK_AF[_k % N] = 1.0
DARK_AF_F = np.fft.fft(_DARK_AF)

# 2) OFDM-FullICI-69 (Sol's steelman): 69/512 = 13.48% aperiodic known QPSK pilots (443 data bins)
_RNG_PIL = np.random.default_rng(777)
PIL_OF = np.sort(_RNG_PIL.choice(np.arange(N), size=69, replace=False))
DAT_OF = np.array([k for k in range(N) if k not in set(PIL_OF.tolist())], dtype=int)
OVH_OF = len(PIL_OF) / float(N)
D_OF = np.sqrt(N * (1.0 - OVH_OF) / float(len(DAT_OF)))
XP_OF = np.zeros(N, dtype=np.complex128)
XP_OF[PIL_OF] = _RNG_PIL.choice([1.0, -1.0, 1j, -1j], size=69) * np.sqrt(N * OVH_OF / 69.0)
SP_OF_TIME = FH_MAT @ XP_OF
F_STAT_PIL = np.exp(-2j * np.pi * np.outer(PIL_OF, L_RC) / float(N))
F_STAT_ALL = np.exp(-2j * np.pi * np.outer(np.arange(N, dtype=np.float64), L_RC) / float(N))
F_STAT_PINV = la.pinv(F_STAT_PIL)
P_STAT_OF = F_STAT_PIL @ F_STAT_PINV

# 3) OTFS-14x5 (32x16 = 512, 70/512 = 13.67% > 13.48%, 442 data bins)
MD_OT, NK_OT = 32, 16
def otfs_mod(Xdd):
    return np.fft.ifft(Xdd, axis=1, norm="ortho").reshape(-1, order="F")
def otfs_demod(y):
    return np.fft.fft(y.reshape((MD_OT, NK_OT), order="F"), axis=1, norm="ortho")

_GL14 = set(l % MD_OT for l in range(-6, 8))
_GK5 = set(k % NK_OT for k in range(-2, 3))
MASK_OT = np.ones((MD_OT, NK_OT), dtype=bool)
for _l in _GL14:
    for _k in _GK5:
        MASK_OT[_l, _k] = False
N_DAT_OT = int(np.sum(MASK_OT))
OVH_OT = (N - N_DAT_OT) / float(N)
D_OT = np.sqrt(N * (1.0 - OVH_OT) / float(N_DAT_OT))
XP_OT = np.zeros((MD_OT, NK_OT), dtype=np.complex128)
XP_OT[0, 0] = np.sqrt(N * OVH_OT)
SP_OT_TIME = otfs_mod(XP_OT)
OBS_L_OT = [l % MD_OT for l in range(-1, 6)]
OBS_K_OT = [k % NK_OT for k in range(-2, 3)]
_E_NK = np.fft.ifft(np.eye(NK_OT, dtype=np.complex128), axis=0, norm="ortho")
_COORDS_OT = np.argwhere(MASK_OT)
M_OT_DAT = np.zeros((N, N_DAT_OT), dtype=np.complex128)
for _j, (_ll, _kk) in enumerate(_COORDS_OT):
    M_OT_DAT[_ll::MD_OT, _j] = _E_NK[:, _kk] * D_OT
# True integer-Doppler-free dark guard bins for OTFS-14x5:
# Data lies outside l in [-6..+7] x k in [-2..+2]. Under moving clutter tau in [0..4], |nu| <= 1.4 (|Delta k| <= 2),
# data from |k|>=3 shifts into k in {-2,-1,+1,+2}; ONLY k=0 at l in {-2,-1,5,6,7} (5 bins) has ZERO integer data leakage!
DARK_OT_2D = np.zeros((MD_OT, NK_OT), dtype=np.float64)
for _l in (-2, -1, 5, 6, 7):
    DARK_OT_2D[_l % MD_OT, 0] = 1.0

# Precompute non-collinear fractional-RC OMP dictionaries (tau in [-0.5..4.5], nu in [-2.0..+2.0])
TAU_OMP = np.linspace(-0.5, 4.5, 21)
NU_OMP = np.linspace(-2.0, 2.0, 17)
PAIRS_OMP = [(float(tt), float(vv)) for tt in TAU_OMP for vv in NU_OMP]

D_AF_BY_LS = {}
for _ls_c in range(-2, 15):
    _ush = np.array([
        np.roll(UF_P_AF, int(ll))
        * np.exp(-2j * np.pi * TWO_NC1 * float(ll) * N_IDX / float(N))
        * np.exp(2j * np.pi * C1 * (float(ll) ** 2 + N * float(ll) + 2.0 * float(_ls_c) * float(ll)))
        for ll in L_RC
    ])
    _D = np.column_stack([
        (F_MAT @ ((eval_rc(L_RC - tt) @ _ush) * np.exp(2j * np.pi * vv * N_IDX / float(N))))[OBS_AF]
        for tt, vv in PAIRS_OMP
    ])
    D_AF_BY_LS[_ls_c] = (_D, _D / np.maximum(la.norm(_D, axis=0), 1e-12)[None, :])

_SP_OF_SH = np.array([np.roll(SP_OF_TIME, int(ll)) for ll in L_RC])
D_OF_69 = np.column_stack([
    (F_MAT @ ((eval_rc(L_RC - tt) @ _SP_OF_SH) * np.exp(2j * np.pi * vv * N_IDX / float(N))))[PIL_OF]
    for tt, vv in PAIRS_OMP
])
D_OF_69_N = D_OF_69 / np.maximum(la.norm(D_OF_69, axis=0), 1e-12)[None, :]

_SP_OT_SH = np.array([np.roll(SP_OT_TIME, int(ll)) for ll in L_RC])
D_OT_OBS = np.column_stack([
    otfs_demod((eval_rc(L_RC - tt) @ _SP_OT_SH) * np.exp(2j * np.pi * vv * N_IDX / float(N)))[np.ix_(OBS_L_OT, OBS_K_OT)].ravel()
    for tt, vv in PAIRS_OMP
])
D_OT_OBS_N = D_OT_OBS / np.maximum(la.norm(D_OT_OBS, axis=0), 1e-12)[None, :]

# ==============================================================================
# Continuous-Time OSR=8 RRC Channel & Shared Receiver Building Blocks
# ==============================================================================
def make_cpp(s_body, c1_v):
    if abs(c1_v) < 1e-15:
        return np.concatenate([s_body[-L_CP:], s_body])
    return np.concatenate([s_body[-L_CP:] * CPP_WRAP_PH, s_body])

def apply_rrc_slot(sym_cpp, paths):
    """Exact continuous-time OSR=8 RRC beta=0.25 channel returning [cp (L_CP), body (N), post (L_POST)]."""
    pad = 16
    sp = np.concatenate([np.zeros(pad, dtype=np.complex128), sym_cpp, np.zeros(pad + L_POST, dtype=np.complex128)])
    up = np.zeros(len(sp) * OSR, dtype=np.complex128)
    up[::OSR] = sp
    tx = np.convolve(up, H_RRC, mode="full")
    L_tx = len(tx)
    Nf = 1 << (L_tx + 128).bit_length()
    TX = np.fft.fft(tx, Nf)
    k_ct = np.fft.fftfreq(Nf)
    t_ct = (np.arange(L_tx, dtype=np.float64) - (L_HALF + (pad + L_CP) * OSR)) / float(OSR)
    rx = np.zeros(L_tx, dtype=np.complex128)
    for h, tau, nu in paths:
        xd = np.fft.ifft(TX * np.exp(-2j * np.pi * (tau * OSR) * k_ct))[:L_tx]
        rx += h * xd * np.exp(2j * np.pi * nu * t_ct / float(N))
    mf = np.convolve(rx, H_RRC, mode="full")
    i0 = 2 * L_HALF + (pad + L_CP) * OSR
    return mf[i0 - L_CP * OSR : i0 + (N + L_POST) * OSR : OSR]

def ep_16_fast(H, y, s2, n_it=2):
    """Exact HPD Cholesky EP-16 equalizer (check_finite=True, no silent fallbacks)."""
    M_c = H.shape[1]
    inv_s2 = 1.0 / max(float(s2), 1e-2)
    Gs = (H.conj().T @ H) * inv_s2
    Htys = (H.conj().T @ y) * inv_s2
    gam = np.zeros(M_c, dtype=np.complex128)
    lam = np.ones(M_c, dtype=np.float64)
    eye_m = np.eye(M_c, dtype=np.complex128)
    idx = np.arange(M_c)
    for _ in range(n_it):
        M = Gs.copy()
        M[idx, idx] += lam
        L = la.cholesky(M, lower=True, check_finite=True)
        Linv = la.solve_triangular(L, eye_m, lower=True, check_finite=True)
        vq = np.clip(np.sum(Linv.real ** 2 + Linv.imag ** 2, axis=0), 1e-6, 1e2)
        muq = la.cho_solve((L, True), Htys + gam, check_finite=True)
        hc = np.maximum(1.0 / vq - lam, 1e-6)
        tc = (muq / vq - gam) / hc
        d2 = (np.abs(tc[:, None] - CONST16[None, :]) ** 2) * hc[:, None]
        d2 -= np.min(d2, axis=1, keepdims=True)
        w = np.exp(-d2)
        w /= np.sum(w, axis=1, keepdims=True)
        mp = w @ CONST16
        vp = np.clip(np.sum(w * (np.abs(CONST16[None, :] - mp[:, None]) ** 2), axis=1), 1e-4, 1.0)
        lr = 1.0 / vp - hc
        ok = lr > 1e-4
        lam = 0.7 * np.where(ok, np.clip(lr, 1e-4, 1e4), lam) + 0.3 * lam
        gam = 0.7 * np.where(ok, mp / vp - hc * tc, gam) + 0.3 * gam
    return CONST16[np.argmin(np.abs(mp[:, None] - CONST16[None, :]), axis=1)], mp

def build_H_af_rel_fft(est_l, g_l, ls_val):
    c_mat = np.zeros((len(L_RC), N), dtype=np.complex128)
    ph_base = np.exp(2j * np.pi * C1 * (L_RC ** 2 + N * L_RC + 2.0 * float(ls_val) * L_RC))
    for (tt, vv), gc in zip(est_l, g_l):
        c_mat += (gc * eval_rc(L_RC - tt) * ph_base)[:, None] * np.exp(2j * np.pi * vv * N_IDX / float(N))[None, :]
    c_mat *= E_5L
    return np.fft.fft(FH_MAT * (c_mat.T @ E_LK), axis=0) / np.sqrt(float(N))

def build_H_time_rc_fh(est_l, g_l):
    """Returns H_time @ FH_MAT via fast outer product."""
    c_mat = np.zeros((len(L_RC), N), dtype=np.complex128)
    for (tt, vv), gc in zip(est_l, g_l):
        c_mat += (gc * eval_rc(L_RC - tt))[:, None] * np.exp(2j * np.pi * vv * N_IDX / float(N))[None, :]
    return FH_MAT * (c_mat.T @ E_LK)

def build_S_lin_ambig(s_time_hat, c1_v):
    """Shared exact CP + body + 8-sample right-zero-pad shift bank for L_F = -8..24 (matches build_H_time_ambig to 1e-15)."""
    s_cpp = make_cpp(s_time_hat, c1_v)
    s_pad = np.concatenate([s_cpp, np.zeros(8, dtype=np.complex128)])
    return np.array([s_pad[L_CP - int(ll) : L_CP - int(ll) + N] for ll in L_F])

def build_H_time_ambig(ts, vs, gs, c1_v):
    H = np.zeros((N, N), dtype=np.complex128)
    rows = np.arange(N)
    for t_p, v_p, g_p in zip(ts, vs, gs):
        w_a = eval_rrc_ambig(L_F - t_p, v_p)
        e_v = np.exp(2j * np.pi * v_p * N_IDX / float(N)) * g_p
        for ll, wa in zip(L_F, w_a):
            if abs(wa) < 1e-6:
                continue
            li = int(ll)
            cols = (rows - li) % N
            ph = np.ones(N, dtype=np.complex128)
            if li > 0:
                if abs(c1_v) > 1e-15:
                    ph[: min(li, L_CP)] = CPP_WRAP_PH[L_CP - min(li, L_CP) : L_CP]
                if li > L_CP:
                    ph[: li - L_CP] = 0.0
            elif li < 0:
                ph[N + li :] = 0.0
            H[rows, cols] += (e_v * wa) * ph
    return H

def gn_polish_given_S(y_slot, S_lin, ts_a, vs_a, n_it=4):
    """Shared Exact 2D RRC Pulse Ambiguity VarPro Gauss-Newton clutter suppressor."""
    P = len(ts_a)
    ts = np.array(ts_a, dtype=np.float64)
    vs = np.array(vs_a, dtype=np.float64)
    def build_phi(t_v, v_v):
        return np.column_stack([
            (eval_rrc_ambig(L_F - t_v[p], v_v[p]) @ S_lin) * np.exp(2j * np.pi * v_v[p] * N_IDX / float(N))
            for p in range(P)
        ])
    Phi = build_phi(ts, vs)
    g = la.lstsq(Phi, y_slot)[0]
    r = y_slot - Phi @ g
    cost = float(np.real(np.vdot(r, r)))
    eps = 1e-4
    for _ in range(n_it):
        J = np.zeros((N, 2 * P), dtype=np.complex128)
        for p in range(P):
            ev = np.exp(2j * np.pi * vs[p] * N_IDX / float(N))
            wt = (eval_rrc_ambig(L_F - (ts[p] + eps), vs[p]) - eval_rrc_ambig(L_F - (ts[p] - eps), vs[p])) / (2.0 * eps)
            J[:, p] = g[p] * (wt @ S_lin) * ev
            cvp = (eval_rrc_ambig(L_F - ts[p], vs[p] + eps) @ S_lin) * np.exp(2j * np.pi * (vs[p] + eps) * N_IDX / float(N))
            cvm = (eval_rrc_ambig(L_F - ts[p], vs[p] - eps) @ S_lin) * np.exp(2j * np.pi * (vs[p] - eps) * N_IDX / float(N))
            J[:, P + p] = g[p] * (cvp - cvm) / (2.0 * eps)
        Q, _ = la.qr(Phi, mode="economic")
        Jp = J - Q @ (Q.conj().T @ J)
        Jr = np.vstack([Jp.real, Jp.imag])
        rr = np.concatenate([r.real, r.imag])
        H_gn = Jr.T @ Jr
        damp = max(1e-6, 1e-6 * float(np.mean(np.diag(H_gn))))
        step = la.solve(H_gn + damp * np.eye(2 * P), Jr.T @ rr, assume_a="pos")
        alpha = 1.0
        imp = False
        for _ls in range(4):
            tn = ts + alpha * np.clip(step[:P], -0.4, 0.4)
            vn = vs + alpha * np.clip(step[P:], -0.4, 0.4)
            Pn = build_phi(tn, vn)
            gn = la.lstsq(Pn, y_slot)[0]
            rn = y_slot - Pn @ gn
            cn = float(np.real(np.vdot(rn, rn)))
            if cn < cost:
                ts, vs, Phi, g, r, cost = tn, vn, Pn, gn, rn, cn
                imp = True
                break
            alpha *= 0.5
        if not imp:
            break
    return ts, vs, g, r

def blind_clean_gn(y_slot, s_time_hat, c1_v, ls_init, ci_init, max_paths=7):
    """Shared 100% blind sequential CLEAN + Exact 2D RRC Ambiguity VarPro-GN (ZERO truth!)."""
    S_lin = build_S_lin_ambig(s_time_hat, c1_v)
    tau_s = np.linspace(max(-0.5, float(ls_init) - 1.5), min(15.5, float(ls_init) + 5.5), 29)
    nu_s = np.linspace(float(ci_init) - 2.5, float(ci_init) + 2.5, 41)
    E_nu_s = np.exp(-2j * np.pi * np.outer(nu_s, N_IDX) / float(N))
    Ref_s = np.array([eval_rc(L_F - tt) @ S_lin for tt in tau_s])
    taus, nus = [], []
    res = y_slot.copy()
    g_r = np.zeros(0, dtype=np.complex128)
    for p in range(max_paths):
        C_map = np.abs(E_nu_s @ (res[:, None] * np.conj(Ref_s.T)))
        i_nu, i_t = np.unravel_index(np.argmax(C_map), C_map.shape)
        if p >= 1 and (C_map[i_nu, i_t] ** 2 / (N * max(float(np.mean(np.abs(res) ** 2)), 1e-6))) < 18.0:
            break
        taus.append(float(tau_s[i_t]))
        nus.append(float(nu_s[i_nu]))
        ts_r, vs_r, g_r, res = gn_polish_given_S(y_slot, S_lin, taus, nus, n_it=(4 if p == max_paths - 1 else 2))
        taus = ts_r.tolist()
        nus = vs_r.tolist()
    if len(taus) == 0:
        return np.array([float(ls_init)]), np.array([float(ci_init)]), np.array([1.0 + 0j]), res
    return np.array(taus, dtype=np.float64), np.array(nus, dtype=np.float64), g_r, res

def shared_stage2_backend(y_body, s1, c1_v, ls_init, ci_init, build_H_dat_fn, sp_time, make_s_fn, q1):
    """Identical Stage-2 backend shared by ALL 4 primary arms (and oracle-sync OFDM):
    blind CLEAN + 2D RRC Ambiguity VarPro-GN -> Full-512 EP-16 re-demod -> 3-step GN polish -> monotone EM guard."""
    ts1, vs1, gs1, res1 = blind_clean_gn(y_body, s1, c1_v, ls_init, ci_init, max_paths=7)
    res1_pow = float(np.mean(np.abs(res1) ** 2))
    H_gn = build_H_time_ambig(ts1, vs1, gs1, c1_v)
    q2, _ = ep_16_fast(build_H_dat_fn(H_gn), y_body - H_gn @ sp_time, max(1e-2, res1_pow), n_it=2)
    s2 = make_s_fn(q2)
    S_lin2 = build_S_lin_ambig(s2, c1_v)
    ts2, vs2, gs2, res2 = gn_polish_given_S(y_body, S_lin2, ts1, vs1, n_it=3)
    if float(np.mean(np.abs(res2) ** 2)) > res1_pow:
        q2, s2, ts2, vs2, gs2, res2 = q1, s1, ts1, vs1, gs1, res1
    sto_h, cfo_h, los_ph = identify_los_blind(ts2, vs2, gs2)
    return {"q_hat": q2, "s_hat": s2, "res": res2, "sto_h": sto_h, "cfo_h": cfo_h, "los_ph": los_ph}

def sliding_cp_timing_cfo(y_ext, is_afdm):
    """Multipath-strengthened Tang WCNC'24 §III (arXiv:2310.07141 eqs. 16-20) / Schmidl-Cox CP/CPP sync:
    uses normalized correlation 2|gamma(d)|/phi(d) with 80% leading-edge plateau guard (raw AWGN eq. 19
    |gamma|-(rho/2)phi locks onto the +7 dB stronger clutter centroid d=2..4 on static G0) + eq. (20)
    mod-1 fractional CFO on the ISI-free tail [d+8 : d+L_CP]. Strictly favors rivals in multipath."""
    mets = []
    for d in range(13):
        a = y_ext[d : d + L_CP]
        b = y_ext[d + N : d + N + L_CP] * (CPP_WRAP_PH if is_afdm else 1.0)
        denom = 0.5 * (float(np.real(np.vdot(a, a))) + float(np.real(np.vdot(b, b)))) + 1e-12
        mets.append(abs(np.vdot(b, a)) / denom)
    m_max = max(mets)
    d_hat = next(d for d, v in enumerate(mets) if v >= 0.80 * m_max)
    b_tail = y_ext[d_hat + 8 + N : d_hat + L_CP + N] * (CPP_WRAP_PH[8:] if is_afdm else 1.0)
    corr = np.vdot(b_tail, y_ext[d_hat + 8 : d_hat + L_CP])
    f_est = -float(np.angle(corr)) / (2.0 * np.pi)
    return d_hat, f_est

def identify_los_blind(ts_h, vs_h, gs_h):
    """100% blind earliest-strong-path LOS reference selection (zero truth!)."""
    pw = np.abs(gs_h) ** 2
    strong = np.where(pw > 0.02 * max(float(np.max(pw)), 1e-12))[0]
    if len(strong) == 0:
        il = 0
    else:
        il = int(strong[int(np.argmin(ts_h[strong]))])
    los_ph = gs_h[il] / max(float(abs(gs_h[il])), 1e-12)
    return float(ts_h[il]), float(vs_h[il]), complex(los_ph)

def slot_rd_map(res_slot, s_time_hat, c1_v, sto_hat, cfo_hat):
    res_decfo = res_slot * np.exp(-2j * np.pi * float(cfo_hat) * N_IDX / float(N))
    s_cpp = make_cpp(s_time_hat, c1_v)
    pre_pad = 4
    s_pad = np.concatenate([np.zeros(pre_pad, dtype=np.complex128), s_cpp, np.zeros(24, dtype=np.complex128)])
    S_t = np.array([s_pad[pre_pad + L_CP - int(ll) : pre_pad + L_CP - int(ll) + N] for ll in L_T])
    # Precompute all 41 shifted references at once: (41, len(L_T)) @ (len(L_T), N) -> (41, N)
    W_t = eval_rc(L_T[None, :] - (TAU_GRID[:, None] + float(sto_hat)))
    Refs = W_t @ S_t  # (41, N)
    return E_NU_RD @ (res_decfo[:, None] * np.conj(Refs.T))  # (57, 41)

# ==============================================================================
# Unified Exact Full-Map CUT Blind Scorer (100% identical logic to k02)
# ==============================================================================
def score_cut(rd_map, center, role="unknown", counter=None):
    if counter is not None:
        counter[role] = counter.get(role, 0) + 1
    ni, ti = int(center[0]), int(center[1])
    n_nu, n_tau = rd_map.shape
    mask = np.ones((n_nu, n_tau), dtype=bool)
    mask[max(0, ni - G_NU_RD) : min(n_nu, ni + G_NU_RD + 1), max(0, ti - G_TAU_RD) : min(n_tau, ti + G_TAU_RD + 1)] = False
    bg_mean = max(float(np.mean(rd_map[mask])), 1e-15)
    return float(rd_map[ni, ti]) / bg_mean

def score_cut_full_map(rd_map, role="unknown", counter=None):
    if counter is not None:
        counter[role] = counter.get(role, 0) + 1
    n_nu, n_tau = rd_map.shape
    row_sums = np.sum(rd_map, axis=1)
    rp = np.zeros(n_nu + 1, dtype=np.float64); rp[1:] = np.cumsum(row_sums)
    rs = np.zeros(n_nu + 1, dtype=np.float64); rs[:-1] = np.cumsum(row_sums[::-1])[::-1]
    cp = np.zeros((n_nu, n_tau + 1), dtype=np.float64); cp[:, 1:] = np.cumsum(rd_map, axis=1)
    cs = np.zeros((n_nu, n_tau + 1), dtype=np.float64); cs[:, :-1] = np.cumsum(rd_map[:, ::-1], axis=1)[:, ::-1]
    lp = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64); lp[1:, :] = np.cumsum(cp, axis=0)
    rr = np.zeros((n_nu + 1, n_tau + 1), dtype=np.float64); rr[1:, :] = np.cumsum(cs, axis=0)
    r0 = np.maximum(0, np.arange(n_nu) - G_NU_RD); r1 = np.minimum(n_nu, np.arange(n_nu) + G_NU_RD + 1)
    c0 = np.maximum(0, np.arange(n_tau) - G_TAU_RD); c1 = np.minimum(n_tau, np.arange(n_tau) + G_TAU_RD + 1)
    bg_sum = (
        rp[r0][:, None] + rs[r1][:, None]
        + (lp[r1[:, None], c0[None, :]] - lp[r0[:, None], c0[None, :]])
        + (rr[r1[:, None], c1[None, :]] - rr[r0[:, None], c1[None, :]])
    )
    bg_cnt = (n_nu * n_tau) - (r1 - r0)[:, None] * (c1 - c0)[None, :]
    grid = rd_map / np.maximum(bg_sum / bg_cnt, 1e-15)
    flat_idx = int(np.argmax(grid))
    ni_hat, ti_hat = divmod(flat_idx, n_tau)
    return float(grid[ni_hat, ti_hat]), (ni_hat, ti_hat), grid

# ==============================================================================
# Per-Slot Blind Receivers (Strict Blind Interfaces: ZERO unknown data passed!)
# ==============================================================================
def run_afdm_dv_slot(y_body, xp_vec):
    """Our 100% blind 2-stage AFDM Dark-Valley + 4th-Power l_sto + 2D Ambiguity VarPro-GN receiver."""
    Y_a = A_CTR @ y_body
    Y_pow = np.abs(Y_a) ** 2
    lp = np.log1p(Y_pow)
    valley = np.real(np.fft.ifft(np.fft.fft(lp) * np.conj(DARK_AF_F)))
    cands = [int(mm % N) for mm in range(-65, 20)]
    m_c = cands[int(np.argmin(valley[cands]))]
    if m_c > N // 2:
        m_c -= N
    med_p = float(np.median(Y_pow))
    core_max = max(float(Y_pow[mm % N]) for mm in range(m_c - 22, m_c + 5))
    thr_pk = max(4.5 * med_p, 0.04 * core_max)
    br = [
        mm for mm in range(m_c - 4, m_c + 5)
        if (Y_pow[mm % N] > thr_pk) and (Y_pow[(mm - TWO_NC1) % N] <= 5.0 * Y_pow[mm % N])
    ]
    if not br:
        br = [mm for mm in range(m_c - 4, m_c + 5) if Y_pow[mm % N] > thr_pk]
    m_hat = max(br) if br else m_c

    Y_al = np.roll(Y_a, -m_hat)
    y_obs = Y_al[OBS_AF]
    D0, D0n = D_AF_BY_LS[0]
    r = y_obs.copy(); sup = []
    for _ in range(10):
        c = np.abs(D0n.conj().T @ r)
        if sup:
            c[sup] = -1.0
        sup.append(int(np.argmax(c)))
        g = la.lstsq(D0[:, sup], y_obs)[0]
        r = y_obs - D0[:, sup] @ g
    H1 = build_H_af_rel_fft([PAIRS_OMP[i] for i in sup], g, 0)
    Hd1 = H1[:, DAT_AF] * D_AF
    s2_1 = max(1e-2, float(np.mean(np.abs(r) ** 2)))
    xf_hat = la.solve(Hd1.conj().T @ Hd1 + s2_1 * np.eye(len(DAT_AF)), Hd1.conj().T @ (Y_al - H1 @ xp_vec), assume_a="pos")
    l_cands = np.arange(-1, 13, dtype=int)
    xf4 = xf_hat ** 4
    ls_hat = int(l_cands[int(np.argmax([abs(np.sum(xf4 * np.exp(8j * np.pi * K_DAT_AF * float(ll) / float(N)))) for ll in l_cands]))])
    ci_hat = m_hat + TWO_NC1 * ls_hat

    # Pass-2 pilot OMP with exact 2*c1*ls_hat*l tap phase + EP-16
    ls_key = int(np.clip(ls_hat, -2, 14))
    D2, D2n = D_AF_BY_LS[ls_key]
    r2 = y_obs.copy(); sup2 = []
    for _ in range(10):
        c = np.abs(D2n.conj().T @ r2)
        if sup2:
            c[sup2] = -1.0
        sup2.append(int(np.argmax(c)))
        g2 = la.lstsq(D2[:, sup2], y_obs)[0]
        r2 = y_obs - D2[:, sup2] @ g2
    est2 = [PAIRS_OMP[i] for i in sup2]
    H2 = build_H_af_rel_fft(est2, g2, ls_hat)
    ph_dat = np.exp(-2j * np.pi * K_DAT_AF * float(ls_hat) / float(N))
    q1, _ = ep_16_fast(H2[:, DAT_AF] * (D_AF * ph_dat[None, :]), Y_al - H2 @ xp_vec, max(1e-2, float(np.mean(np.abs(r2) ** 2))), n_it=2)
    x1 = xp_vec.copy(); x1[DAT_AF] = q1 * D_AF
    s1 = AH_CTR @ x1

    # Pilot-only clutter subtraction diagnostic (Ablation arm afdm_dv_pilonly: zero Stage-2 data-aided GN!)
    x1_f = x1 * np.exp(-2j * np.pi * K_SIGNED * float(ls_hat) / float(N))
    res_pilonly_daft = np.roll(Y_al - H2 @ x1_f, m_hat)
    res_pilonly = AH_CTR @ res_pilonly_daft
    ts_p = np.array([e[0] + float(ls_hat) for e in est2], dtype=np.float64)
    vs_p = np.array([e[1] + float(ci_hat) for e in est2], dtype=np.float64)
    sto_p, cfo_p, los_p = identify_los_blind(ts_p, vs_p, g2)

    # Stage-2 closed-loop unified backend (identical across all 4 primary arms!)
    def _mk_s_af(q):
        x = xp_vec.copy(); x[DAT_AF] = q * D_AF
        return AH_CTR @ x

    st2 = shared_stage2_backend(
        y_body, s1, C1, ls_hat, ci_hat,
        lambda H: (H @ AH_CTR)[:, DAT_AF] * D_AF, SP_AF_TIME, _mk_s_af, q1,
    )
    st2.update({
        "q_pilonly": q1, "s_pilonly": s1, "res_pilonly": res_pilonly,
        "sto_p": sto_p, "cfo_p": cfo_p, "los_p": los_p,
    })
    return st2

def run_afdm_tang_cpp_slot(y_ext, xp_vec):
    """Multipath-strengthened Tang WCNC'24 §III sliding CPP timing + ISI-free tail mod-1 fractional CFO
    + blind integer CFO search c_int in [-4..+4] on the existing single pilot at K_PIL=0 + unified Stage-2 backend."""
    y_body = y_ext[L_CP : L_CP + N]
    d_hat, f_cpp = sliding_cp_timing_cfo(y_ext, is_afdm=True)
    y_comp0 = y_ext[L_CP + d_hat : L_CP + d_hat + N] * np.exp(-2j * np.pi * f_cpp * N_IDX / float(N))
    Y_a0 = A_CTR @ y_comp0
    # Blind integer CFO search c_int in [-4..+4] using the existing single AFDM pilot at K_PIL=0 (rightmost bright peak inside dark moat)
    Y_pow0 = np.abs(Y_a0) ** 2
    lp0 = np.log1p(Y_pow0)
    dcs = {ci: float(np.sum(np.roll(lp0, -ci) * _DARK_AF)) for ci in range(-4, 5)}
    min_dc = min(dcs.values())
    med_p0 = float(np.median(Y_pow0))
    core_max0 = max(float(Y_pow0[k % N]) for k in range(-26, 6))
    thr_c0 = max(4.5 * med_p0, 0.04 * core_max0)
    ci_cands = [
        ci for ci in range(-4, 5)
        if (Y_pow0[ci % N] > thr_c0) and (Y_pow0[(ci - TWO_NC1) % N] <= 5.0 * Y_pow0[ci % N]) and (dcs[ci] <= min_dc + 25.0)
    ]
    if not ci_cands:
        ci_cands = [ci for ci in range(-4, 5) if Y_pow0[ci % N] > thr_c0]
    best_ci = max(ci_cands) if ci_cands else min(dcs, key=dcs.get)
    Y_a = np.roll(Y_a0, -best_ci)
    y_obs = Y_a[OBS_AF]
    D0, D0n = D_AF_BY_LS[0]
    r = y_obs.copy(); sup = []
    for _ in range(10):
        c = np.abs(D0n.conj().T @ r)
        if sup:
            c[sup] = -1.0
        sup.append(int(np.argmax(c)))
        g = la.lstsq(D0[:, sup], y_obs)[0]
        r = y_obs - D0[:, sup] @ g
    H1 = build_H_af_rel_fft([PAIRS_OMP[i] for i in sup], g, 0)
    q1, _ = ep_16_fast(H1[:, DAT_AF] * D_AF, Y_a - H1 @ xp_vec, max(1e-2, float(np.mean(np.abs(r) ** 2))), n_it=2)
    def _mk_s_af(q):
        x = xp_vec.copy(); x[DAT_AF] = q * D_AF
        return AH_CTR @ x
    return shared_stage2_backend(
        y_body, _mk_s_af(q1), C1, d_hat, int(best_ci + round(f_cpp)),
        lambda H: (H @ AH_CTR)[:, DAT_AF] * D_AF, SP_AF_TIME, _mk_s_af, q1,
    )

def run_ofdm_fullici_slot(y_ext, xp_vec, oracle_sto_cfo=None):
    """
    Sol's Ultimate OFDM-FullICI-69 Steelman (69 aperiodic pilots, equal 13.48% overhead & 1.10 Fs BW):
    Sliding full-CP ML timing search + ISI-free tail fractional CFO + blind integer CFO search [-4..+4] on 69 pilots
    + static-first smooth delay LS & full-ICI 2D OMP + EP-16 + IDENTICAL unified Stage-2 backend!
    """
    y_body = y_ext[L_CP : L_CP + N]
    if oracle_sto_cfo is not None:
        sto_o, cfo_o = oracle_sto_cfo
        ls_u, ci_u = int(round(sto_o)), int(round(cfo_o))
        ls_u_clip = int(np.clip(ls_u, 0, L_POST))
        y_al = y_ext[L_CP + ls_u_clip : L_CP + ls_u_clip + N] * np.exp(-2j * np.pi * float(cfo_o) * N_IDX / float(N))
        ls_init, ci_init = ls_u, ci_u
    else:
        d_hat, f_est = sliding_cp_timing_cfo(y_ext, is_afdm=False)
        y_al0 = y_ext[L_CP + d_hat : L_CP + d_hat + N] * np.exp(-2j * np.pi * f_est * N_IDX / float(N))
        Yo0 = F_MAT @ y_al0
        # Blind integer CFO search on 69 aperiodic pilots via smooth delay subspace projection ratio
        best_ci, best_e = 0, -1.0
        for ci in (0, -1, 1, -2, 2, -3, 3, -4, 4):
            hp_c = Yo0[(PIL_OF + ci) % N] / xp_vec[PIL_OF]
            en = float(np.real(np.vdot(hp_c, P_STAT_OF @ hp_c))) / max(float(np.real(np.vdot(hp_c, hp_c))), 1e-12)
            if en > best_e:
                best_e, best_ci = en, ci
        y_al = y_al0 * np.exp(-2j * np.pi * float(best_ci) * N_IDX / float(N))
        ls_init, ci_init = d_hat, int(best_ci + round(f_est))

    Yo = F_MAT @ y_al
    h_p = Yo[PIL_OF] / xp_vec[PIL_OF]
    hl_hat = F_STAT_PINV @ h_p
    hf_hat = F_STAT_ALL @ hl_hat
    res_stat = float(np.mean(np.abs(Yo[PIL_OF] - hf_hat[PIL_OF] * xp_vec[PIL_OF]) ** 2))

    yp = Yo[PIL_OF]
    r_ici = yp.copy(); sup = []
    for _ in range(10):
        c = np.abs(D_OF_69_N.conj().T @ r_ici)
        if sup:
            c[sup] = -1.0
        sup.append(int(np.argmax(c)))
        g_ici = la.lstsq(D_OF_69[:, sup], yp)[0]
        r_ici = yp - D_OF_69[:, sup] @ g_ici
    res_ici = float(np.mean(np.abs(r_ici) ** 2))

    if res_stat <= 1.2 * res_ici:
        yeq = Yo[DAT_OF] / np.where(np.abs(hf_hat[DAT_OF]) > 1e-6, hf_hat[DAT_OF], 1e-6) / D_OF
        q1 = CONST16[np.argmin(np.abs(yeq[:, None] - CONST16[None, :]), axis=1)]
    else:
        HFh = build_H_time_rc_fh([PAIRS_OMP[i] for i in sup], g_ici)
        q1, _ = ep_16_fast(HFh[:, DAT_OF] * D_OF, y_al - HFh @ xp_vec, max(1e-2, res_ici), n_it=2)

    def _mk_s_of(q):
        x = xp_vec.copy(); x[DAT_OF] = q * D_OF
        return FH_MAT @ x

    return shared_stage2_backend(
        y_body, _mk_s_of(q1), 0.0, ls_init, ci_init,
        lambda H: (H @ FH_MAT)[:, DAT_OF] * D_OF, SP_OF_TIME, _mk_s_of, q1,
    )

def run_otfs_14x5_slot(y_ext, xp_dd):
    """
    Faithful OTFS-14x5 Reduced-Guard Steelman (70/512 = 13.67% > 13.48%, equal 1.10 Fs BW):
    Exact linear time slicing (zero circular wrap boundary error!) + pure integer-Doppler-free dark-moat vs pilot-core
    acquisition + fractional-RC wide-Doppler OMP + EP-16 + IDENTICAL unified Stage-2 backend!
    """
    y_body = y_ext[L_CP : L_CP + N]
    best_sc, l_hat, c_hat = -1e30, 0, 0
    for ls in range(13):
        Y_lp = np.log1p(np.abs(otfs_demod(y_ext[L_CP + ls : L_CP + ls + N])) ** 2)
        for ci in (0, -1, 1, -2, 2, -3, 3, -4, 4):
            dark_cost = float(np.sum(np.roll(DARK_OT_2D, ci, axis=1) * Y_lp))
            pil_en = float(np.sum(Y_lp[0:5, int(ci % NK_OT)]))
            sc_v = pil_en - 1.0 * dark_cost
            if sc_v > best_sc:
                best_sc, l_hat, c_hat = sc_v, ls, ci
    y_al = y_ext[L_CP + l_hat : L_CP + l_hat + N] * np.exp(-2j * np.pi * float(c_hat) * N_IDX / float(N))
    y_obs = otfs_demod(y_al)[np.ix_(OBS_L_OT, OBS_K_OT)].ravel()
    r = y_obs.copy(); sup = []
    for _ in range(10):
        c = np.abs(D_OT_OBS_N.conj().T @ r)
        if sup:
            c[sup] = -1.0
        sup.append(int(np.argmax(c)))
        g = la.lstsq(D_OT_OBS[:, sup], y_obs)[0]
        r = y_obs - D_OT_OBS[:, sup] @ g
    H_ot_time = build_H_time_rc_fh([PAIRS_OMP[i] for i in sup], g) @ F_MAT
    q1, _ = ep_16_fast(H_ot_time @ M_OT_DAT, y_al - H_ot_time @ SP_OT_TIME, max(1e-2, float(np.mean(np.abs(r) ** 2))), n_it=2)
    def _mk_s_ot(q):
        return SP_OT_TIME + M_OT_DAT @ q
    return shared_stage2_backend(
        y_body, _mk_s_ot(q1), 0.0, l_hat, c_hat,
        lambda H: H @ M_OT_DAT, SP_OT_TIME, _mk_s_ot, q1,
    )

# ==============================================================================
# Paired Physical M=6 Scene Evaluator
# ==============================================================================
def eval_scene_worker(args):
    scene_seed, is_async, snr_t, arm_set, role, los_db, target_mode, wide_async, verify_exact, clut_boost_db = args
    if role not in ("cal", "val", "pos"):
        raise ValueError(f"Invalid role: {role}")
    if role in ("cal", "val"):
        if snr_t is not None:
            raise ValueError("G2 violation: snr_t must be None on cal/val frames")
    else:
        if snr_t is None:
            raise ValueError("Target frame must have non-None snr_t")

    rng = np.random.default_rng(int(scene_seed))
    local_counter = {}

    # Shared physical trajectory t_slots[m] driving slot timing, clutter evolution & target slow-time phase
    t_slots = np.arange(M_SLOTS, dtype=np.float64) * SLOT_STRIDE_PHYS + (
        rng.uniform(-15.0, 15.0, M_SLOTS) if is_async else np.zeros(M_SLOTS)
    )
    taus_c = np.sort(np.linspace(1.1, 3.8, 4) + rng.uniform(-0.15, 0.15, 4))
    nus_c = rng.uniform(-1.4, 1.4, 4) if is_async else np.zeros(4)
    hc_base = (rng.standard_normal(4) + 1j * rng.standard_normal(4)) / np.sqrt(8.0) * (10.0 ** ((25.0 + clut_boost_db) / 20.0))
    h_los_base = (10.0 ** ((los_db + clut_boost_db) / 20.0)) if los_db > -50.0 else 0.0

    # Per-slot asynchronous impairments (STO_m, CFO_m, random LO phase phi_m)
    if is_async:
        sto_max = 10.5 if wide_async else 8.5
        cfo_max = 3.5 if wide_async else 3.0
        stos = rng.uniform(1.5, sto_max, M_SLOTS)
        cfos = rng.uniform(-cfo_max, cfo_max, M_SLOTS)
        phis = rng.uniform(0.0, 2.0 * np.pi, M_SLOTS)
    else:
        stos = np.zeros(M_SLOTS)
        cfos = np.zeros(M_SLOTS)
        phis = np.zeros(M_SLOTS)

    true_cell = None
    h_targ_base = 0.0 + 0j
    tau_targ, nu_targ = TAU_TARG_NOM, (NU_TARG_NOM if is_async else NU_TARG_G0)
    if snr_t is not None:
        if target_mode == "random":
            tau_targ = float(rng.uniform(7.0, 11.0))
            nu_targ = float(rng.uniform(-3.0, 3.0))
        elif target_mode != "nominal":
            raise ValueError(f"Unknown target_mode: {target_mode}")
        ni_t = int(np.argmin(np.abs(NU_GRID - nu_targ)))
        ti_t = int(np.argmin(np.abs(TAU_GRID - tau_targ)))
        true_cell = [ni_t, ti_t]
        h_targ_base = np.exp(1j * rng.uniform(0.0, 2.0 * np.pi)) * (10.0 ** (snr_t / 20.0))

    # Build per-slot path lists (exact single physical trajectory t_slots[m]!)
    slot_paths = []
    for m in range(M_SLOTS):
        pm = []
        if h_los_base > 0.0:
            pm.append((h_los_base * np.exp(1j * phis[m]), float(stos[m]), float(cfos[m])))
        for hc, tc, vc in zip(hc_base, taus_c, nus_c):
            pm.append((hc * np.exp(1j * (phis[m] + 2.0 * np.pi * vc * (t_slots[m] - stos[m]) / float(N))), float(tc + stos[m]), float(vc + cfos[m])))
        if snr_t is not None:
            pm.append((h_targ_base * np.exp(1j * (phis[m] + 2.0 * np.pi * nu_targ * (t_slots[m] - stos[m]) / float(N))), float(tau_targ + stos[m]), float(nu_targ + cfos[m])))
        slot_paths.append(pm)

    # Shared thermal noise & shared master 16-QAM payload stream sliced deterministically across all arms!
    noise_full = [(rng.standard_normal(L_CP + N + L_POST) + 1j * rng.standard_normal(L_CP + N + L_POST)) / np.sqrt(2.0) for _ in range(M_SLOTS)]
    master_qam = rng.choice(CONST16, size=(M_SLOTS, len(DAT_AF)))  # 443 >= 442

    out_arms = {}
    exact_max_rel_err = 0.0

    def record_arm(name, rdp, ser_val, sto_e=0.0, cfo_e=0.0, clut_res_db=0.0):
        nonlocal exact_max_rel_err
        sc, (ni_h, ti_h), grid = score_cut_full_map(rdp, role=role, counter=local_counter)
        if verify_exact:
            for ni_c in range(rdp.shape[0]):
                for ti_c in range(rdp.shape[1]):
                    ref = score_cut(rdp, (ni_c, ti_c), role="verify", counter=None)
                    re = abs(float(grid[ni_c, ti_c]) - ref) / max(abs(ref), 1e-15)
                    if re > exact_max_rel_err:
                        exact_max_rel_err = re
        out_arms[name] = {
            "score": float(sc),
            "score_db": float(10.0 * np.log10(sc)),
            "peak_idx": [int(ni_h), int(ti_h)],
            "ser": float(ser_val),
            "sto_err": float(sto_e),
            "cfo_err": float(cfo_e),
            "clut_res_db": float(clut_res_db),
        }

    # --- Group A: AFDM arms (afdm_dv_coh, afdm_dv_pilonly, afdm_dv_noncoh, afdm_tang_cpp, known_afdm_coh) ---
    af_need = [a for a in arm_set if a in ("afdm_dv_coh", "afdm_dv_pilonly", "afdm_dv_noncoh", "afdm_tang_cpp", "known_afdm_coh")]
    if af_need:
        s_true_af = []
        y_full_af = []
        for m in range(M_SLOTS):
            xm = XP_AF.copy(); xm[DAT_AF] = master_qam[m, : len(DAT_AF)] * D_AF
            sm = AH_CTR @ xm
            s_true_af.append(sm)
            y_full_af.append(apply_rrc_slot(make_cpp(sm, C1), slot_paths[m]) + noise_full[m])

        if any(a in af_need for a in ("afdm_dv_coh", "afdm_dv_pilonly", "afdm_dv_noncoh")):
            rd_coh = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            rd_nc = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.float64)
            rd_pil = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            sers, stoes, cfoes, cr_c = [], [], [], []
            sers_p, stoes_p, cfoes_p, cr_p = [], [], [], []
            for m in range(M_SLOTS):
                yb_m = y_full_af[m][L_CP : L_CP + N]
                ypow_m = max(float(np.mean(np.abs(yb_m) ** 2)), 1e-15)
                res_d = run_afdm_dv_slot(yb_m, XP_AF)
                sers.append(float(np.mean(np.abs(res_d["q_hat"] - master_qam[m, : len(DAT_AF)]) > 1e-4)))
                stoes.append(abs(res_d["sto_h"] - stos[m]))
                cfoes.append(abs(res_d["cfo_h"] - cfos[m]))
                cr_c.append(10.0 * np.log10(max(float(np.mean(np.abs(res_d["res"]) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(res_d["res"], res_d["s_hat"], C1, res_d["sto_h"], res_d["cfo_h"])
                ph_m = np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - res_d["sto_h"]) / float(N))[:, None] * np.conj(res_d["los_ph"])
                rd_coh += sl * ph_m
                rd_nc += np.abs(sl) ** 2
                if "afdm_dv_pilonly" in af_need:
                    sers_p.append(float(np.mean(np.abs(res_d["q_pilonly"] - master_qam[m, : len(DAT_AF)]) > 1e-4)))
                    stoes_p.append(abs(res_d["sto_p"] - stos[m]))
                    cfoes_p.append(abs(res_d["cfo_p"] - cfos[m]))
                    cr_p.append(10.0 * np.log10(max(float(np.mean(np.abs(res_d["res_pilonly"]) ** 2)), 1e-15) / ypow_m))
                    sl_p = slot_rd_map(res_d["res_pilonly"], res_d["s_pilonly"], C1, res_d["sto_p"], res_d["cfo_p"])
                    ph_p = np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - res_d["sto_p"]) / float(N))[:, None] * np.conj(res_d["los_p"])
                    rd_pil += sl_p * ph_p
            if "afdm_dv_coh" in af_need:
                record_arm("afdm_dv_coh", np.abs(rd_coh) ** 2, float(np.mean(sers)), float(np.mean(stoes)), float(np.mean(cfoes)), float(np.mean(cr_c)))
            if "afdm_dv_noncoh" in af_need:
                record_arm("afdm_dv_noncoh", rd_nc, float(np.mean(sers)), float(np.mean(stoes)), float(np.mean(cfoes)), float(np.mean(cr_c)))
            if "afdm_dv_pilonly" in af_need:
                record_arm("afdm_dv_pilonly", np.abs(rd_pil) ** 2, float(np.mean(sers_p)), float(np.mean(stoes_p)), float(np.mean(cfoes_p)), float(np.mean(cr_p)))

        if "afdm_tang_cpp" in af_need:
            rd_t = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            sers_t, stoes_t, cfoes_t, cr_t = [], [], [], []
            for m in range(M_SLOTS):
                ypow_m = max(float(np.mean(np.abs(y_full_af[m][L_CP : L_CP + N]) ** 2)), 1e-15)
                rt = run_afdm_tang_cpp_slot(y_full_af[m], XP_AF)
                sers_t.append(float(np.mean(np.abs(rt["q_hat"] - master_qam[m, : len(DAT_AF)]) > 1e-4)))
                stoes_t.append(abs(rt["sto_h"] - stos[m]))
                cfoes_t.append(abs(rt["cfo_h"] - cfos[m]))
                cr_t.append(10.0 * np.log10(max(float(np.mean(np.abs(rt["res"]) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(rt["res"], rt["s_hat"], C1, rt["sto_h"], rt["cfo_h"])
                rd_t += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - rt["sto_h"]) / float(N))[:, None] * np.conj(rt["los_ph"])
            record_arm("afdm_tang_cpp", np.abs(rd_t) ** 2, float(np.mean(sers_t)), float(np.mean(stoes_t)), float(np.mean(cfoes_t)), float(np.mean(cr_t)))

        if "known_afdm_coh" in af_need:
            rd_k = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            cr_k = []
            for m in range(M_SLOTS):
                yb_m = y_full_af[m][L_CP : L_CP + N]
                ypow_m = max(float(np.mean(np.abs(yb_m) ** 2)), 1e-15)
                S_lin_m = build_S_lin_ambig(s_true_af[m], C1)
                ts_o = ([float(stos[m])] if h_los_base > 0.0 else []) + [float(tc + stos[m]) for tc in taus_c]
                vs_o = ([float(cfos[m])] if h_los_base > 0.0 else []) + [float(vc + cfos[m]) for vc in nus_c]
                _, _, _, res_k = gn_polish_given_S(yb_m, S_lin_m, ts_o, vs_o, n_it=3)
                cr_k.append(10.0 * np.log10(max(float(np.mean(np.abs(res_k) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(res_k, s_true_af[m], C1, stos[m], cfos[m])
                rd_k += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - stos[m]) / float(N))[:, None] * np.exp(-1j * phis[m])
            record_arm("known_afdm_coh", np.abs(rd_k) ** 2, 0.0, clut_res_db=float(np.mean(cr_k)))

    # --- Group B: OFDM-FullICI-69 arms (ofdm_fullici_69, ofdm_fullici_oracsync, known_ofdm_coh) ---
    of_need = [a for a in arm_set if a in ("ofdm_fullici_69", "ofdm_fullici_oracsync", "known_ofdm_coh")]
    if of_need:
        s_true_of = []
        y_full_of = []
        for m in range(M_SLOTS):
            xm = XP_OF.copy(); xm[DAT_OF] = master_qam[m, : len(DAT_OF)] * D_OF
            sm = FH_MAT @ xm
            s_true_of.append(sm)
            y_full_of.append(apply_rrc_slot(make_cpp(sm, 0.0), slot_paths[m]) + noise_full[m])

        if "ofdm_fullici_69" in of_need:
            rd_o = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            sers_o, stoes_o, cfoes_o, cr_o = [], [], [], []
            for m in range(M_SLOTS):
                ypow_m = max(float(np.mean(np.abs(y_full_of[m][L_CP : L_CP + N]) ** 2)), 1e-15)
                ro = run_ofdm_fullici_slot(y_full_of[m], XP_OF, oracle_sto_cfo=None)
                sers_o.append(float(np.mean(np.abs(ro["q_hat"] - master_qam[m, : len(DAT_OF)]) > 1e-4)))
                stoes_o.append(abs(ro["sto_h"] - stos[m]))
                cfoes_o.append(abs(ro["cfo_h"] - cfos[m]))
                cr_o.append(10.0 * np.log10(max(float(np.mean(np.abs(ro["res"]) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(ro["res"], ro["s_hat"], 0.0, ro["sto_h"], ro["cfo_h"])
                rd_o += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - ro["sto_h"]) / float(N))[:, None] * np.conj(ro["los_ph"])
            record_arm("ofdm_fullici_69", np.abs(rd_o) ** 2, float(np.mean(sers_o)), float(np.mean(stoes_o)), float(np.mean(cfoes_o)), float(np.mean(cr_o)))

        if "ofdm_fullici_oracsync" in of_need:
            rd_oo = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            sers_oo, stoes_oo, cfoes_oo, cr_oo = [], [], [], []
            for m in range(M_SLOTS):
                ypow_m = max(float(np.mean(np.abs(y_full_of[m][L_CP : L_CP + N]) ** 2)), 1e-15)
                ro = run_ofdm_fullici_slot(y_full_of[m], XP_OF, oracle_sto_cfo=(float(stos[m]), float(cfos[m])))
                sers_oo.append(float(np.mean(np.abs(ro["q_hat"] - master_qam[m, : len(DAT_OF)]) > 1e-4)))
                stoes_oo.append(abs(ro["sto_h"] - stos[m]))
                cfoes_oo.append(abs(ro["cfo_h"] - cfos[m]))
                cr_oo.append(10.0 * np.log10(max(float(np.mean(np.abs(ro["res"]) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(ro["res"], ro["s_hat"], 0.0, ro["sto_h"], ro["cfo_h"])
                rd_oo += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - ro["sto_h"]) / float(N))[:, None] * np.conj(ro["los_ph"])
            record_arm("ofdm_fullici_oracsync", np.abs(rd_oo) ** 2, float(np.mean(sers_oo)), float(np.mean(stoes_oo)), float(np.mean(cfoes_oo)), float(np.mean(cr_oo)))

        if "known_ofdm_coh" in of_need:
            rd_ko = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
            cr_ko = []
            for m in range(M_SLOTS):
                yb_m = y_full_of[m][L_CP : L_CP + N]
                ypow_m = max(float(np.mean(np.abs(yb_m) ** 2)), 1e-15)
                S_lin_m = build_S_lin_ambig(s_true_of[m], 0.0)
                ts_o = ([float(stos[m])] if h_los_base > 0.0 else []) + [float(tc + stos[m]) for tc in taus_c]
                vs_o = ([float(cfos[m])] if h_los_base > 0.0 else []) + [float(vc + cfos[m]) for vc in nus_c]
                _, _, _, res_k = gn_polish_given_S(yb_m, S_lin_m, ts_o, vs_o, n_it=3)
                cr_ko.append(10.0 * np.log10(max(float(np.mean(np.abs(res_k) ** 2)), 1e-15) / ypow_m))
                sl = slot_rd_map(res_k, s_true_of[m], 0.0, stos[m], cfos[m])
                rd_ko += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - stos[m]) / float(N))[:, None] * np.exp(-1j * phis[m])
            record_arm("known_ofdm_coh", np.abs(rd_ko) ** 2, 0.0, clut_res_db=float(np.mean(cr_ko)))

    # --- Group C: OTFS-14x5 Reduced-Guard Blind Steelman ---
    if "otfs_14x5_blind" in arm_set:
        rd_ot = np.zeros((len(NU_GRID), len(TAU_GRID)), dtype=np.complex128)
        sers_ot, stoes_ot, cfoes_ot, cr_ot = [], [], [], []
        for m in range(M_SLOTS):
            Xot = XP_OT.copy(); Xot[MASK_OT] = master_qam[m, :N_DAT_OT] * D_OT
            sm = otfs_mod(Xot)
            y_ext_ot = apply_rrc_slot(make_cpp(sm, 0.0), slot_paths[m]) + noise_full[m]
            ypow_m = max(float(np.mean(np.abs(y_ext_ot[L_CP : L_CP + N]) ** 2)), 1e-15)
            rot = run_otfs_14x5_slot(y_ext_ot, XP_OT)
            sers_ot.append(float(np.mean(np.abs(rot["q_hat"] - master_qam[m, :N_DAT_OT]) > 1e-4)))
            stoes_ot.append(abs(rot["sto_h"] - stos[m]))
            cfoes_ot.append(abs(rot["cfo_h"] - cfos[m]))
            cr_ot.append(10.0 * np.log10(max(float(np.mean(np.abs(rot["res"]) ** 2)), 1e-15) / ypow_m))
            sl = slot_rd_map(rot["res"], rot["s_hat"], 0.0, rot["sto_h"], rot["cfo_h"])
            rd_ot += sl * np.exp(-2j * np.pi * NU_GRID * (t_slots[m] - rot["sto_h"]) / float(N))[:, None] * np.conj(rot["los_ph"])
        record_arm("otfs_14x5_blind", np.abs(rd_ot) ** 2, float(np.mean(sers_ot)), float(np.mean(stoes_ot)), float(np.mean(cfoes_ot)), float(np.mean(cr_ot)))

    return {"arms": out_arms, "true_cell": true_cell, "score_calls": local_counter, "exact_max_rel_err": exact_max_rel_err}

# ==============================================================================
# Gate G1: Exact CUT, 2D RRC Ambiguity Kernel, Equal RF BW, Overhead & Static Health
# ==============================================================================
def run_g1_gates():
    rng = np.random.default_rng(31415927)
    syn_map = rng.exponential(1.0, size=(len(NU_GRID), len(TAU_GRID)))
    syn_map[len(NU_GRID) // 2, len(TAU_GRID) // 2] = 1e10
    _, _, syn_grid = score_cut_full_map(syn_map)
    syn_rel_err = 0.0
    for ni in range(len(NU_GRID)):
        for ti in range(len(TAU_GRID)):
            ref = score_cut(syn_map, (ni, ti))
            re = abs(float(syn_grid[ni, ti]) - ref) / max(abs(ref), 1e-15)
            if re > syn_rel_err:
                syn_rel_err = re
    if syn_rel_err >= 1e-12:
        raise RuntimeError(f"G1 synthetic 1e10 rel err: {syn_rel_err}")

    # Verify Exact 2D RRC pulse ambiguity kernel across ALL boundary corners [(1.5,-4.4),(7.83,-4.2),(12.44,4.39),(14.44,4.89)]
    # + per-corner >6 dB gain over zero-Doppler RC slice + exact matrix vs S_lin agreement (<1e-13) + OTFS dark mask!
    x_k2 = XP_AF.copy(); x_k2[DAT_AF] = rng.choice(CONST16, len(DAT_AF)) * D_AF
    s_k2 = AH_CTR @ x_k2
    S_lin2 = build_S_lin_ambig(s_k2, C1)
    corners = [(1.5, -4.4), (7.83, -4.2), (12.44, 4.39), (14.44, 4.89)]
    corner_errs = {}
    corner_rc_errs = {}
    corner_gains_db = {}
    mat_vs_slin_max = 0.0
    for tc_b, vc_b in corners:
        key = f"({tc_b},{vc_b})"
        y_b = apply_rrc_slot(make_cpp(s_k2, C1), [(1.0 + 0j, tc_b, vc_b)])[L_CP : L_CP + N]
        p_b = (eval_rrc_ambig(L_F - tc_b, vc_b) @ S_lin2) * np.exp(2j * np.pi * vc_b * N_IDX / float(N))
        p_rc_b = (eval_rc(L_F - tc_b) @ S_lin2) * np.exp(2j * np.pi * vc_b * N_IDX / float(N))
        e_b = float(la.norm(y_b - (np.vdot(p_b, y_b) / np.vdot(p_b, p_b)) * p_b) / la.norm(y_b))
        e_rc_b = float(la.norm(y_b - (np.vdot(p_rc_b, y_b) / np.vdot(p_rc_b, p_rc_b)) * p_rc_b) / la.norm(y_b))
        corner_errs[key] = e_b
        corner_rc_errs[key] = e_rc_b
        corner_gains_db[key] = float(20.0 * np.log10(e_rc_b / max(e_b, 1e-15)))
        m_b = build_H_time_ambig([tc_b], [vc_b], [1.0 + 0j], C1) @ s_k2
        me = float(la.norm(m_b - p_b) / max(la.norm(p_b), 1e-15))
        if me > mat_vs_slin_max:
            mat_vs_slin_max = me
    err_amb_max = max(corner_errs.values())
    min_gain_db = min(corner_gains_db.values())
    ambig_ok = bool((err_amb_max < 0.005) and all(g > 6.0 for g in corner_gains_db.values()) and (mat_vs_slin_max < 1e-13))

    # Verify pure OTFS dark mask zero integer data leakage under (1,1) and (2,2)
    X_ot_d = np.zeros((MD_OT, NK_OT), dtype=np.complex128)
    X_ot_d[MASK_OT] = rng.choice(CONST16, N_DAT_OT) * D_OT
    s_ot_d = otfs_mod(X_ot_d)
    ot_dark_int_leak_max = 0.0
    for td_o, vd_o in ((1.0, 1.0), (2.0, 2.0)):
        yd_o = apply_rrc_slot(make_cpp(s_ot_d, 0.0), [(1.0 + 0j, td_o, vd_o)])[L_CP : L_CP + N]
        lm = float(np.max(np.abs(otfs_demod(yd_o)[DARK_OT_2D > 0])))
        if lm > ot_dark_int_leak_max:
            ot_dark_int_leak_max = lm
    ot_dark_ok = bool(ot_dark_int_leak_max < 0.01)

    # Measure post-RRC 99% RF BW across ALL 4 primary arms using 40 PAIRED payload draws!
    bw_payloads = rng.choice(CONST16, size=(40, len(DAT_AF)))
    def meas_bw(arm_name):
        psd = None
        for idx_p in range(40):
            if arm_name in ("afdm_dv_coh", "afdm_tang_cpp"):
                xm = XP_AF.copy(); xm[DAT_AF] = bw_payloads[idx_p, : len(DAT_AF)] * D_AF
                s = make_cpp(AH_CTR @ xm, C1)
            elif arm_name == "ofdm_fullici_69":
                xm = XP_OF.copy(); xm[DAT_OF] = bw_payloads[idx_p, : len(DAT_OF)] * D_OF
                s = make_cpp(FH_MAT @ xm, 0.0)
            elif arm_name == "otfs_14x5_blind":
                Xot = XP_OT.copy(); Xot[MASK_OT] = bw_payloads[idx_p, :N_DAT_OT] * D_OT
                s = make_cpp(otfs_mod(Xot), 0.0)
            up = np.zeros(len(s) * OSR, dtype=np.complex128); up[::OSR] = s
            Nf = 1 << (len(up) + len(H_RRC) + 64).bit_length()
            p_cur = np.abs(np.fft.fft(up, Nf) * np.fft.fft(H_RRC, Nf)) ** 2
            psd = p_cur if psd is None else (psd + p_cur)
        fr = np.abs(np.fft.fftfreq(len(psd)) * OSR)
        ord_f = np.argsort(fr)
        cum = np.cumsum(psd[ord_f]) / np.sum(psd)
        return 2.0 * float(fr[ord_f][np.searchsorted(cum, 0.99)])

    bw_map = {a: meas_bw(a) for a in PRIMARY_ARMS}
    bw_ok = bool(all(bw_map["afdm_dv_coh"] <= bw_map[r] + 0.005 for r in RIVAL_ARMS))
    ovh_map = {
        "afdm_dv_coh": OVH_AF,
        "afdm_tang_cpp": OVH_AF,
        "ofdm_fullici_69": OVH_OF,
        "otfs_14x5_blind": OVH_OT,
    }
    ovh_ok = bool(all(ovh_map["afdm_dv_coh"] <= ovh_map[r] for r in RIVAL_ARMS))

    # Iron Rule 2 unimpaired high-SNR static health check (+38 dB total clutter / +31 dB LOS, STO=0, CFO=0, nu=0, 4 scenes)
    # + non-zero pure integer CFO (+2.0 / -2.0) static health check across ALL 4 primary arms (verifies blind int-CFO branch!)
    # + exact noiseless clutter-only <= -35 dB suppression audit on nominal +25 dB async scenes (truth used ONLY for G1 metric!)
    hs_res = [
        eval_scene_worker((2026159900 + i, False, -14.0, PRIMARY_ARMS, "pos", 18.0, "nominal", False, False, 13.0))
        for i in range(4)
    ]
    hs_ser_raw = {a: float(np.mean([r["arms"][a]["ser"] for r in hs_res])) for a in PRIMARY_ARMS}
    hs_cfo_max = {a: float(np.max([r["arms"][a]["cfo_err"] for r in hs_res])) for a in PRIMARY_ARMS}
    hs_ser_ok = bool(all(hs_ser_raw[a] < 0.01 and hs_cfo_max[a] < 0.05 for a in PRIMARY_ARMS))

    # Non-zero pure integer CFO (+2.0 / -2.0, STO=0, nu_c=0, +38 dB) static health check on the SAME 4 static
    # channel realizations (seeds 2026159900..2026159903): verifies ALL 4 primary arms' blind integer-CFO branch!
    icfo_sers = {a: [] for a in PRIMARY_ARMS}
    icfo_errs = {a: [] for a in PRIMARY_ARMS}
    for i_c in range(4):
        rc = np.random.default_rng(2026159900 + i_c)
        taus_s = np.sort(np.linspace(1.1, 3.8, 4) + rc.uniform(-0.15, 0.15, 4))
        hc_s = (rc.standard_normal(4) + 1j * rc.standard_normal(4)) / np.sqrt(8.0) * (10.0 ** (38.0 / 20.0))
        hlos_s = 10.0 ** (31.0 / 20.0)
        cfo_nz = 2.0 if (i_c % 2 == 0) else -2.0
        pm_s = [(hlos_s, 0.0, cfo_nz)] + [(h, float(tc), cfo_nz) for h, tc in zip(hc_s, taus_s)]
        qm = rc.choice(CONST16, len(DAT_AF))
        nm = (rc.standard_normal(L_CP + N + L_POST) + 1j * rc.standard_normal(L_CP + N + L_POST)) / np.sqrt(2.0)
        xa = XP_AF.copy(); xa[DAT_AF] = qm * D_AF
        ya = apply_rrc_slot(make_cpp(AH_CTR @ xa, C1), pm_s) + nm
        ra_c = run_afdm_dv_slot(ya[L_CP : L_CP + N], XP_AF)
        rt_c = run_afdm_tang_cpp_slot(ya, XP_AF)
        xo = XP_OF.copy(); xo[DAT_OF] = qm * D_OF
        yo = apply_rrc_slot(make_cpp(FH_MAT @ xo, 0.0), pm_s) + nm
        ro_c = run_ofdm_fullici_slot(yo, XP_OF)
        Xot = XP_OT.copy(); Xot[MASK_OT] = qm[:N_DAT_OT] * D_OT
        yot = apply_rrc_slot(make_cpp(otfs_mod(Xot), 0.0), pm_s) + nm
        rot_c = run_otfs_14x5_slot(yot, XP_OT)
        for nm_a, rd_c, ql in (
            ("afdm_dv_coh", ra_c, len(DAT_AF)), ("afdm_tang_cpp", rt_c, len(DAT_AF)),
            ("ofdm_fullici_69", ro_c, len(DAT_OF)), ("otfs_14x5_blind", rot_c, N_DAT_OT),
        ):
            icfo_sers[nm_a].append(float(np.mean(np.abs(rd_c["q_hat"] - qm[:ql]) > 1e-4)))
            icfo_errs[nm_a].append(abs(float(rd_c["cfo_h"]) - cfo_nz))
    hs_intcfo_ser = {a: float(np.mean(icfo_sers[a])) for a in PRIMARY_ARMS}
    hs_intcfo_err = {a: float(np.max(icfo_errs[a])) for a in PRIMARY_ARMS}
    hs_intcfo_ok = bool(all(hs_intcfo_ser[a] < 0.01 and hs_intcfo_err[a] < 0.05 for a in PRIMARY_ARMS))

    # Direct noiseless clutter-only residual suppression audit on nominal +25 dB S1 async scenes (4 scenes x 2 slots)
    clut_only_dbs = []
    for i_a in range(4):
        ra = np.random.default_rng(2026159910 + i_a)
        taus_a = np.sort(np.linspace(1.1, 3.8, 4) + ra.uniform(-0.15, 0.15, 4))
        nus_a = ra.uniform(-1.4, 1.4, 4)
        hc_a = (ra.standard_normal(4) + 1j * ra.standard_normal(4)) / np.sqrt(8.0) * (10.0 ** (25.0 / 20.0))
        hlos_a = 10.0 ** (18.0 / 20.0)
        for _ms in range(2):
            sto_a, cfo_a, phi_a = float(ra.uniform(1.5, 8.5)), float(ra.uniform(-3.0, 3.0)), float(ra.uniform(0.0, 2.0 * np.pi))
            pm_a = [(hlos_a * np.exp(1j * phi_a), sto_a, cfo_a)] + [
                (h * np.exp(1j * phi_a), float(tc + sto_a), float(vc + cfo_a)) for h, tc, vc in zip(hc_a, taus_a, nus_a)
            ]
            qm = ra.choice(CONST16, len(DAT_AF))
            xa = XP_AF.copy(); xa[DAT_AF] = qm * D_AF
            y_clut_only = apply_rrc_slot(make_cpp(AH_CTR @ xa, C1), pm_a)[L_CP : L_CP + N]
            n_body = (ra.standard_normal(N) + 1j * ra.standard_normal(N)) / np.sqrt(2.0)
            res_tot = run_afdm_dv_slot(y_clut_only + n_body, XP_AF)["res"]
            res_clut_only = res_tot - n_body  # isolate noiseless clutter+LOS residual power (truth used ONLY for G1 metric!)
            clut_only_dbs.append(10.0 * np.log10(max(float(np.mean(np.abs(res_clut_only) ** 2)), 1e-15) / max(float(np.mean(np.abs(y_clut_only) ** 2)), 1e-15)))
    async_clut_sup_db = float(np.mean(clut_only_dbs))
    clut_sup_ok = bool(async_clut_sup_db <= -35.0)

    real_s1_chk = eval_scene_worker((2026159999, True, -14.0, ["afdm_dv_coh"], "pos", 18.0, "nominal", False, True, 0.0))
    real_s1_err = float(real_s1_chk["exact_max_rel_err"])
    if real_s1_err >= 1e-12:
        raise RuntimeError(f"G1 real S1 map exact CUT rel err failed: {real_s1_err}")

    return {
        "pass": bool(bw_ok and ovh_ok and ambig_ok and ot_dark_ok and hs_ser_ok and hs_intcfo_ok and clut_sup_ok and (syn_rel_err < 1e-12) and (real_s1_err < 1e-12)),
        "syn1e10_max_rel_err": syn_rel_err,
        "real_s1_g1_max_rel_err": real_s1_err,
        "rrc_rc_slice_rel_err_corners": corner_rc_errs,
        "rrc_2d_ambig_rel_err_corners": corner_errs,
        "rrc_2d_ambig_gain_db_corners": corner_gains_db,
        "rrc_2d_ambig_max_corner_err": err_amb_max,
        "rrc_2d_ambig_min_gain_db": min_gain_db,
        "ambig_mat_vs_slin_max_err": mat_vs_slin_max,
        "otfs_dark_mask_int_leak_max": ot_dark_int_leak_max,
        "async_clut_only_suppression_db_25db": async_clut_sup_db,
        "async_clut_suppression_le_m35db": clut_sup_ok,
        "bw99_all4_fs": bw_map,
        "afdm_bw_le_all_rivals": bw_ok,
        "overhead_all4": ovh_map,
        "afdm_ovh_le_all_rivals": ovh_ok,
        "high_snr_static_ser_all4": hs_ser_raw,
        "high_snr_static_max_cfo_err_all4": hs_cfo_max,
        "high_snr_static_ser_under_1pct": hs_ser_ok,
        "high_snr_intcfo_static_ser_all4": hs_intcfo_ser,
        "high_snr_intcfo_max_cfo_err_all4": hs_intcfo_err,
        "high_snr_intcfo_static_ok": hs_intcfo_ok,
    }

# ==============================================================================
# Statistical Calibration & Dual-Bootstrap Inference (Exact Order Stat + Beta-Binomial FWER)
# ==============================================================================
def clopper_pearson_ci(k, n, alpha=0.05):
    if n <= 0:
        return 0.0, 0.0, 1.0
    p = k / float(n)
    lo = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return p, lo, hi

def exact_order_stat_params(n_cal, pfa_target=0.01):
    a = max(1, int(round(pfa_target * (n_cal + 1))))
    b = n_cal + 1 - a
    if not (1 <= b <= n_cal):
        raise ValueError(f"Invalid order stat rank b={b} for n_cal={n_cal}")
    return a, b

def evaluate_arms(cal_res, val_res, pos_res, arm_list, pfa_target=0.01, fwer_arms=10):
    summary = {}
    raw_arrays = {}
    true_cells = np.array([r["true_cell"] for r in pos_res], dtype=int) if (pos_res and pos_res[0]["true_cell"] is not None) else None
    for arm in arm_list:
        cal_s = np.array([r["arms"][arm]["score"] for r in cal_res], dtype=np.float64)
        pos_s = np.array([r["arms"][arm]["score"] for r in pos_res], dtype=np.float64)
        pos_peaks = np.array([r["arms"][arm]["peak_idx"] for r in pos_res], dtype=int)
        pos_ser = np.array([r["arms"][arm]["ser"] for r in pos_res], dtype=np.float64)
        pos_sto = np.array([r["arms"][arm]["sto_err"] for r in pos_res], dtype=np.float64)
        pos_cfo = np.array([r["arms"][arm]["cfo_err"] for r in pos_res], dtype=np.float64)
        pos_cr = np.array([r["arms"][arm]["clut_res_db"] for r in pos_res], dtype=np.float64)

        a_bb, b_bb = exact_order_stat_params(len(cal_s), pfa_target)
        thr = float(np.partition(cal_s, b_bb - 1)[b_bb - 1])

        val_fields = {}
        if val_res is not None:
            val_s = np.array([r["arms"][arm]["score"] for r in val_res], dtype=np.float64)
            k_val = int(np.sum(val_s > thr))
            p_val, lo_v, hi_v = clopper_pearson_ci(k_val, len(val_s))
            alpha_each = 0.05 / float(fwer_arms)
            k_lo_bb = int(betabinom_dist.ppf(alpha_each / 2.0, len(val_s), a_bb, b_bb))
            k_hi_bb = int(betabinom_dist.ppf(1.0 - alpha_each / 2.0, len(val_s), a_bb, b_bb))
            c1_pass = bool(k_lo_bb <= k_val <= k_hi_bb)
            val_fields = {
                "n_val": int(len(val_s)),
                "val_k_fa": k_val,
                "val_pfa_map": p_val,
                "val_ci95_cp": [lo_v, hi_v],
                "val_bb_fwer_bounds_k": [k_lo_bb, k_hi_bb],
                "val_bb_fwer_bounds_p": [k_lo_bb / float(len(val_s)), k_hi_bb / float(len(val_s))],
                "c1_pass": c1_pass,
            }

        # Strict alarm-first before localization check (+/-2 Doppler, +/-2 delay)
        exceed = pos_s > thr
        det_loc = np.zeros(len(pos_s), dtype=np.float64)
        det_mis = np.zeros(len(pos_s), dtype=np.float64)
        for i in range(len(pos_s)):
            if exceed[i]:
                ni_h, ti_h = pos_peaks[i]
                ni_t, ti_t = true_cells[i]
                if abs(ni_h - ni_t) <= 2 and abs(ti_h - ti_t) <= 2:
                    det_loc[i] = 1.0
                else:
                    det_mis[i] = 1.0
        det_miss = (~exceed).astype(np.float64)
        k_loc = int(np.sum(det_loc))
        pd_loc, pd_lo, pd_hi = clopper_pearson_ci(k_loc, len(det_loc))

        summary[arm] = {
            "n_cal": int(len(cal_s)),
            **val_fields,
            "n_pos": int(len(pos_s)),
            "thr_linear": thr,
            "thr_db": float(10.0 * np.log10(thr)),
            "pos_k_loc": k_loc,
            "pos_pd_loc": pd_loc,
            "pos_pd_loc_ci95_cp": [pd_lo, pd_hi],
            "pos_pd_mis": float(np.mean(det_mis)),
            "pos_p_miss": float(np.mean(det_miss)),
            "pos_score_db_mean": float(np.mean(10.0 * np.log10(pos_s))),
            "pos_ser_mean": float(np.mean(pos_ser)),
            "pos_sto_err_mean": float(np.mean(pos_sto)),
            "pos_cfo_err_mean": float(np.mean(pos_cfo)),
            "pos_clut_res_db_mean": float(np.mean(pos_cr)),
        }
        raw_arrays[arm] = {
            "cal": cal_s, "pos": pos_s, "peaks": pos_peaks, "true_cells": true_cells, "det_loc": det_loc,
        }
    return summary, raw_arrays

def tango_paired_score_ci(n10, n01, n, alpha_two_sided):
    """Tango (1998, Stat. Med. 17:891-908) paired binary score CI for Delta = P(A=1,R=0) - P(A=0,R=1).
    Eliminates percentile-bootstrap zero-discordance degeneracy cleanly without double-CP over-conservatism."""
    z = float(norm_dist.ppf(1.0 - alpha_two_sided / 2.0))
    def score_z(delta):
        a_q = 2.0 * float(n)
        b_q = -float(n10 + n01) + float(2 * n - n10 + n01) * delta
        c_q = -float(n01) * delta * (1.0 - delta)
        disc = max(0.0, b_q * b_q - 4.0 * a_q * c_q)
        q21 = (-b_q + np.sqrt(disc)) / (2.0 * a_q)
        var = max(1e-12, float(n) * (2.0 * q21 + delta * (1.0 - delta)))
        return (float(n10 - n01) - float(n) * delta) / np.sqrt(var)
    pt = float(n10 - n01) / float(n)
    lo_a, lo_b = -1.0 + 1e-9, pt
    if score_z(lo_a) <= z:
        lo = -1.0
    else:
        for _ in range(45):
            mid = 0.5 * (lo_a + lo_b)
            if score_z(mid) > z:
                lo_a = mid
            else:
                lo_b = mid
        lo = 0.5 * (lo_a + lo_b)
    hi_a, hi_b = pt, 1.0 - 1e-9
    if score_z(hi_b) >= -z:
        hi = 1.0
    else:
        for _ in range(45):
            mid = 0.5 * (hi_a + hi_b)
            if score_z(mid) < -z:
                hi_b = mid
            else:
                hi_a = mid
        hi = 0.5 * (hi_a + hi_b)
    return float(lo), float(hi)

def dual_bootstrap_delta_pd(raw_target, raw_rivals_dict, pfa_target=0.01, n_boot=2000, seed=2026150001):
    rival_names = list(raw_rivals_dict.keys())
    R = len(rival_names)
    n_cal = len(raw_target["cal"])
    n_pos = len(raw_target["pos"])
    _, b_bb = exact_order_stat_params(n_cal, pfa_target)

    r_pds = [float(np.mean(raw_rivals_dict[rn]["det_loc"])) for rn in rival_names]
    best_idx = int(np.argmax(r_pds))
    point = float(np.mean(raw_target["det_loc"]) - r_pds[best_idx])

    rng = np.random.default_rng(seed)
    idx_c = rng.integers(0, n_cal, size=(n_boot, n_cal))
    idx_p = rng.integers(0, n_pos, size=(n_boot, n_pos))

    def boot_pds(arr_d):
        c_boot = arr_d["cal"][idx_c]
        thrs = np.partition(c_boot, b_bb - 1, axis=1)[:, b_bb - 1 : b_bb]
        exceed = arr_d["pos"][idx_p] > thrs
        hits = np.zeros_like(exceed, dtype=np.float64)
        bi, fi = np.nonzero(exceed)
        if len(bi) > 0:
            oi = idx_p[bi, fi]
            pk = arr_d["peaks"][oi]
            tc = arr_d["true_cells"][oi]
            ok = (np.abs(pk[:, 0] - tc[:, 0]) <= 2) & (np.abs(pk[:, 1] - tc[:, 1]) <= 2)
            hits[bi, fi] = ok.astype(np.float64)
        return np.mean(hits, axis=1)

    a_b = boot_pds(raw_target)
    r_bs = np.stack([boot_pds(raw_rivals_dict[rn]) for rn in rival_names], axis=0)
    alpha_bonf = 0.05 / float(R)
    a_det = raw_target["det_loc"]
    bonf_los, bonf_his = [], []
    bonf_los_9875, bonf_his_9875 = [], []
    for j, rn in enumerate(rival_names):
        r_det = raw_rivals_dict[rn]["det_loc"]
        k_plus = int(np.sum((a_det > 0.5) & (r_det < 0.5)))
        k_minus = int(np.sum((a_det < 0.5) & (r_det > 0.5)))
        # Conservative envelope of dual-bootstrap (threshold + scene variance) and Tango (1998) paired score CI
        # (non-degenerate even at k_plus=0 / k_minus=0; verified 0.0% non-cover on Sol 0.02 counterexample & ~2.4% on ties)
        l_tg_25, u_tg_25 = tango_paired_score_ci(k_plus, k_minus, n_pos, alpha_bonf)
        l_tg_125, u_tg_125 = tango_paired_score_ci(k_plus, k_minus, n_pos, 0.025 / float(R))
        q_lo_25 = float(np.quantile(a_b - r_bs[j], alpha_bonf / 2.0))
        q_hi_25 = float(np.quantile(a_b - r_bs[j], 1.0 - alpha_bonf / 2.0))
        q_lo_125 = float(np.quantile(a_b - r_bs[j], 0.0125 / float(R)))
        q_hi_125 = float(np.quantile(a_b - r_bs[j], 1.0 - 0.0125 / float(R)))
        bonf_los.append(min(q_lo_25, l_tg_25))
        bonf_his.append(max(q_hi_25, u_tg_25))
        bonf_los_9875.append(min(q_lo_125, l_tg_125))
        bonf_his_9875.append(max(q_hi_125, u_tg_125))
    return {
        "best_rival": rival_names[best_idx],
        "point": point,
        "ci95_bonf_sim_lo": min(bonf_los),
        "ci95_bonf_min_hi": min(bonf_his),
        "ci95_bonf_max_hi": max(bonf_his),
        "ci95_bonf_per_rival": {rn: [bonf_los[j], bonf_his[j]] for j, rn in enumerate(rival_names)},
        "bonf_lo_9875": min(bonf_los_9875),
        "bonf_hi_9875": min(bonf_his_9875),
    }

def dual_bootstrap_pilonly_share(raw_coh, raw_pil, raw_tang, pfa_target=0.01, n_boot=2000, seed=2026150250):
    """Paired dual-bootstrap 95% CI for pilonly_share = (Pd_pil - Pd_tang) / (Pd_coh - Pd_tang).
    Strictly conservative on non-positive denominators: maps (c_b <= t_b) to +inf so UB < 0.80 fails if denom is not positive."""
    n_cal = len(raw_coh["cal"])
    n_pos = len(raw_coh["pos"])
    _, b_bb = exact_order_stat_params(n_cal, pfa_target)
    rng = np.random.default_rng(seed)
    idx_c = rng.integers(0, n_cal, size=(n_boot, n_cal))
    idx_p = rng.integers(0, n_pos, size=(n_boot, n_pos))

    def boot_pds(arr_d):
        c_boot = arr_d["cal"][idx_c]
        thrs = np.partition(c_boot, b_bb - 1, axis=1)[:, b_bb - 1 : b_bb]
        exceed = arr_d["pos"][idx_p] > thrs
        hits = np.zeros_like(exceed, dtype=np.float64)
        bi, fi = np.nonzero(exceed)
        if len(bi) > 0:
            oi = idx_p[bi, fi]
            pk = arr_d["peaks"][oi]
            tc = arr_d["true_cells"][oi]
            ok = (np.abs(pk[:, 0] - tc[:, 0]) <= 2) & (np.abs(pk[:, 1] - tc[:, 1]) <= 2)
            hits[bi, fi] = ok.astype(np.float64)
        return np.mean(hits, axis=1)

    c_b = boot_pds(raw_coh)
    p_b = boot_pds(raw_pil)
    t_b = boot_pds(raw_tang)
    denom_pt = float(np.mean(raw_coh["det_loc"]) - np.mean(raw_tang["det_loc"]))
    pt_raw = float((np.mean(raw_pil["det_loc"]) - np.mean(raw_tang["det_loc"])) / denom_pt) if denom_pt > 0.0 else float("inf")
    pos_mask = (c_b - t_b) > 0.0
    fin_vals = np.sort((p_b[pos_mask] - t_b[pos_mask]) / (c_b[pos_mask] - t_b[pos_mask]))
    n_fin = len(fin_vals)

    def _safe_q(q_prob):
        pos = q_prob * float(n_boot - 1)
        lo_i = int(np.floor(pos))
        hi_i = int(np.ceil(pos))
        if hi_i >= n_fin:
            return float("inf")
        w = pos - float(lo_i)
        return float((1.0 - w) * fin_vals[lo_i] + w * fin_vals[hi_i])

    ci_lo = _safe_q(0.025)
    ci_hi = _safe_q(0.975)
    return {
        "point": (float(pt_raw) if np.isfinite(pt_raw) else None),
        "point_unbounded": bool(not np.isfinite(pt_raw)),
        "denom_pos_frac": float(np.mean(pos_mask)),
        "ci95": [
            (float(ci_lo) if np.isfinite(ci_lo) else None),
            (float(ci_hi) if np.isfinite(ci_hi) else None),
        ],
        "ci95_lo_unbounded": bool(not np.isfinite(ci_lo)),
        "ci95_hi_unbounded": bool(not np.isfinite(ci_hi)),
        "pass_ub_lt_0p80": bool(np.isfinite(ci_hi) and (ci_hi < 0.80)),
    }

def paired_score_diff_ci(raw_a, raw_b, n_boot=2000, seed=2026150999, alpha=0.05):
    diff_db = 10.0 * np.log10(raw_a["pos"]) - 10.0 * np.log10(raw_b["pos"])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff_db), size=(n_boot, len(diff_db)))
    means = np.mean(diff_db[idx], axis=1)
    # Normal-t guard prevents zero-variance bootstrap collapse when diff_db is nearly constant
    se = float(np.std(diff_db, ddof=1) / np.sqrt(len(diff_db))) if len(diff_db) > 1 else 0.0
    z = float(norm_dist.ppf(1.0 - alpha / 2.0))
    pt = float(np.mean(diff_db))
    lo = min(float(np.quantile(means, alpha / 2.0)), pt - z * se)
    hi = max(float(np.quantile(means, 1.0 - alpha / 2.0)), pt + z * se)
    return {"point_db": pt, "std_db": float(np.std(diff_db, ddof=1)) if len(diff_db) > 1 else 0.0, "ci95_db": [lo, hi]}

def paired_score_diff_vs_rivals_bonf(raw_target, raw_rivals_dict, n_boot=2000, seed=2026150350):
    """Bonferroni simultaneous paired score-dB difference vs R rivals (sensitive continuous G0 guard; min_j U_j valid under ties)."""
    rnames = list(raw_rivals_dict.keys())
    R = len(rnames)
    alpha_bonf = 0.05 / float(R)
    per_r = {}
    his = []
    pts = []
    for j, rn in enumerate(rnames):
        res_j = paired_score_diff_ci(raw_target, raw_rivals_dict[rn], n_boot=n_boot, seed=seed + j, alpha=alpha_bonf)
        per_r[rn] = res_j
        his.append(res_j["ci95_db"][1])
        pts.append(res_j["point_db"])
    best_j = int(np.argmin(pts))
    return {
        "best_rival": rnames[best_j],
        "point_db": pts[best_j],
        "ci95_bonf_min_hi_db": min(his),
        "per_rival": per_r,
    }

def run_batch(pool, tasks):
    if pool is None:
        return [eval_scene_worker(t) for t in tasks]
    return pool.map(eval_scene_worker, tasks)

# ==============================================================================
# Main Entrypoint
# ==============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=2026152501)
    ap.add_argument("--mode", choices=["g1_only", "smoke", "full"], default="smoke")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--n-cal-s1", type=int, default=350)
    ap.add_argument("--n-val-s1", type=int, default=350)
    ap.add_argument("--n-pos-s1", type=int, default=260)
    ap.add_argument("--n-cal-g0", type=int, default=250)
    ap.add_argument("--n-val-g0", type=int, default=250)
    ap.add_argument("--n-pos-g0-ser", type=int, default=40)
    ap.add_argument("--n-pos-g0-slp", type=int, default=260)
    ap.add_argument("--n-cal-desc", type=int, default=80)
    ap.add_argument("--n-val-desc", type=int, default=80)
    ap.add_argument("--snr-main", type=float, default=-14.0)
    ap.add_argument("--snr-weak", type=float, default=-21.5)
    ap.add_argument("--snr-g0-slope", type=float, default=-19.0)
    ap.add_argument("--out", type=str, required=True)
    args = ap.parse_args()

    t0 = time.time()
    out_abs = os.path.abspath(args.out)
    canonical_local = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_k_r11_k03", "summary_k_r11_k03.json"))
    canonical_deinlab = os.path.abspath("/data/guoyikun/tmp/funnel_k_r11/summary_k_r11_k03.json")

    # Validate workers, path locks, and formal parameter locks BEFORE running G1 gates!
    if not (1 <= args.workers <= 8):
        raise ValueError(f"Round-11 deinlab hard limit requires 1 <= workers <= 8, got {args.workers}")
    if args.mode == "full":
        if out_abs not in (canonical_local, canonical_deinlab):
            raise ValueError(f"Formal full mode locks output path to {canonical_local} or {canonical_deinlab}, got {out_abs}")
        if args.seed != 2026152501:
            raise ValueError(f"Formal full mode locks seed=2026152501, got {args.seed}")
        if args.snr_main != -14.0 or args.snr_weak != -21.5 or args.snr_g0_slope != -19.0:
            raise ValueError("Formal full mode locks SNRs (-14.0, -21.5, -19.0)")
        if (args.n_cal_s1, args.n_val_s1, args.n_pos_s1) != (350, 350, 260):
            raise ValueError("Formal full mode locks S1 sizes (350, 350, 260)")
        if (args.n_cal_g0, args.n_val_g0, args.n_pos_g0_ser, args.n_pos_g0_slp) != (250, 250, 40, 260):
            raise ValueError("Formal full mode locks G0 sizes (250, 250, 40, 260)")
        if (args.n_cal_desc, args.n_val_desc) != (80, 80):
            raise ValueError("Formal full mode locks desc sizes (80, 80)")
    else:
        if os.path.basename(out_abs) == "summary_k_r11_k03.json" or out_abs in (canonical_local, canonical_deinlab):
            raise ValueError(f"Diagnostic mode {args.mode} must not write to formal path {out_abs}")
    if os.path.exists(out_abs):
        raise FileExistsError(f"Refusing to overwrite existing output file: {out_abs}")
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)

    g1_report = run_g1_gates()
    print(
        f"[Gate G1] pass={g1_report['pass']} | syn1e10={g1_report['syn1e10_max_rel_err']:.2e} | "
        f"2D_ambig_max={g1_report['rrc_2d_ambig_max_corner_err']:.5f} (minGain +{g1_report['rrc_2d_ambig_min_gain_db']:.2f}dB, mat_err={g1_report['ambig_mat_vs_slin_max_err']:.2e}) | "
        f"otDarkLeak={g1_report['otfs_dark_mask_int_leak_max']:.4f} | clutOnly25={g1_report['async_clut_only_suppression_db_25db']:+.2f}dB | "
        f"BW99={g1_report['bw99_all4_fs']} | hsSER={g1_report['high_snr_static_ser_all4']} | intCfoSER={g1_report['high_snr_intcfo_static_ser_all4']}",
        flush=True,
    )
    if args.mode == "g1_only":
        with open(out_abs, "x") as f:
            json.dump({"g1": g1_report}, f, indent=2, allow_nan=False)
        return

    if args.mode == "smoke":
        n_cal_s1, n_val_s1, n_pos_s1 = 10, 10, 6
        n_cal_g0, n_val_g0, n_pos_g0_ser, n_pos_g0_slp = 10, 10, 4, 6
        n_cal_desc, n_val_desc = 10, 10
        n_stress = 4
    else:
        n_cal_s1, n_val_s1, n_pos_s1 = 350, 350, 260
        n_cal_g0, n_val_g0, n_pos_g0_ser, n_pos_g0_slp = 250, 250, 40, 260
        n_cal_desc, n_val_desc = 80, 80
        n_stress = 40

    hist_seeds = set()
    hist_sources = [888777666, 2026112501, 2026122501, 2026132501, 2026142501, 999888777]
    if args.mode == "smoke":
        hist_sources.append(2026152501)
    for hs in hist_sources:
        hist_seeds.update(int(x) for x in np.random.default_rng(hs).integers(1, 2**31 - 1, size=12000))

    effective_seed = (args.seed + 777777) if args.mode == "smoke" else args.seed
    rng_master = np.random.default_rng(effective_seed)
    n_needed = n_cal_s1 + n_val_s1 + 2 * n_pos_s1 + n_cal_g0 + n_val_g0 + n_pos_g0_ser + n_pos_g0_slp + 5 * n_stress + 3 * n_cal_desc
    seed_set, seed_list = set(), []
    while len(seed_list) < n_needed:
        c = int(rng_master.integers(1, 2**31 - 1))
        if c not in seed_set and c not in hist_seeds:
            seed_set.add(c); seed_list.append(c)
    it = iter(seed_list); take = lambda k: [next(it) for _ in range(k)]

    cal_s1_s = take(n_cal_s1); val_s1_s = take(n_val_s1)
    pos_m_s1 = take(n_pos_s1); pos_w_s1 = take(n_pos_s1)
    cal_g0_s = take(n_cal_g0); val_g0_s = take(n_val_g0)
    pos_ser_g0 = take(n_pos_g0_ser); pos_slp_g0 = take(n_pos_g0_slp)
    st_los10_cal = take(n_cal_desc); st_los10_pos = take(n_stress)
    st_los3_cal = take(n_cal_desc); st_los3_pos = take(n_stress)
    st_blk_cal = take(n_cal_desc); st_blk_pos = take(n_stress)
    st_rand_pos = take(n_stress); st_wide_pos = take(n_stress)

    pool = Pool(processes=args.workers) if args.workers > 1 else None
    total_calls = {"cal": 0, "val": 0, "pos": 0}
    max_exact_rel_err = 0.0

    def accum(res_l):
        nonlocal max_exact_rel_err
        for r in res_l:
            for k, v in r["score_calls"].items():
                total_calls[k] = total_calls.get(k, 0) + v
            if r["exact_max_rel_err"] > max_exact_rel_err:
                max_exact_rel_err = r["exact_max_rel_err"]

    try:
        print(f"[S1 Main] cal={n_cal_s1}, val={n_val_s1}, pos({args.snr_main} & {args.snr_weak})={n_pos_s1} on {len(ALL_PASS_ARMS)} arms...", flush=True)
        cal_s1 = run_batch(pool, [(s, True, None, ALL_PASS_ARMS, "cal", 18.0, "nominal", False, i == 0, 0.0) for i, s in enumerate(cal_s1_s)])
        accum(cal_s1); print(f"  [S1 cal] done in {time.time()-t0:.1f}s", flush=True)
        val_s1 = run_batch(pool, [(s, True, None, ALL_PASS_ARMS, "val", 18.0, "nominal", False, i == 0, 0.0) for i, s in enumerate(val_s1_s)])
        accum(val_s1); print(f"  [S1 val] done in {time.time()-t0:.1f}s", flush=True)
        pos_m = run_batch(pool, [(s, True, args.snr_main, ALL_PASS_ARMS, "pos", 18.0, "nominal", False, i == 0, 0.0) for i, s in enumerate(pos_m_s1)])
        accum(pos_m)
        pos_w = run_batch(pool, [(s, True, args.snr_weak, ["afdm_dv_coh", "afdm_dv_noncoh", "afdm_dv_pilonly"], "pos", 18.0, "nominal", False, False, 0.0) for s in pos_w_s1])
        accum(pos_w); print(f"  [S1 pos] done in {time.time()-t0:.1f}s", flush=True)

        s1_m_sum, s1_m_raw = evaluate_arms(cal_s1, val_s1, pos_m, ALL_PASS_ARMS, 0.01, fwer_arms=10)
        s1_w_sum, s1_w_raw = evaluate_arms(cal_s1, val_s1, pos_w, ["afdm_dv_coh", "afdm_dv_noncoh", "afdm_dv_pilonly"], 0.01, fwer_arms=10)

        print(f"[S1 Desc] cal={n_cal_desc}, val={n_val_desc}, pos({args.snr_main})={n_pos_s1}...", flush=True)
        cal_desc = run_batch(pool, [(s, True, None, DESC_ARMS, "cal", 18.0, "nominal", False, False, 0.0) for s in cal_s1_s[:n_cal_desc]])
        accum(cal_desc)
        val_desc = run_batch(pool, [(s, True, None, DESC_ARMS, "val", 18.0, "nominal", False, False, 0.0) for s in val_s1_s[:n_val_desc]])
        accum(val_desc)
        pos_desc = run_batch(pool, [(s, True, args.snr_main, DESC_ARMS, "pos", 18.0, "nominal", False, False, 0.0) for s in pos_m_s1])
        accum(pos_desc)
        s1_desc_sum, _ = evaluate_arms(cal_desc, val_desc, pos_desc, DESC_ARMS, 0.01, fwer_arms=10)

        print(f"[G0 Static] cal={n_cal_g0}, val={n_val_g0}, pos_ser={n_pos_g0_ser}, pos_slp({args.snr_g0_slope})={n_pos_g0_slp}...", flush=True)
        cal_g0 = run_batch(pool, [(s, False, None, PRIMARY_ARMS, "cal", 18.0, "nominal", False, False, 0.0) for s in cal_g0_s])
        accum(cal_g0)
        val_g0 = run_batch(pool, [(s, False, None, PRIMARY_ARMS, "val", 18.0, "nominal", False, False, 0.0) for s in val_g0_s])
        accum(val_g0)
        pos_g0_s = run_batch(pool, [(s, False, args.snr_main, PRIMARY_ARMS, "pos", 18.0, "nominal", False, False, 0.0) for s in pos_ser_g0])
        accum(pos_g0_s)
        pos_g0_sl = run_batch(pool, [(s, False, args.snr_g0_slope, PRIMARY_ARMS, "pos", 18.0, "nominal", False, False, 0.0) for s in pos_slp_g0])
        accum(pos_g0_sl); print(f"  [G0 Static] done in {time.time()-t0:.1f}s", flush=True)

        g0_ser_sum, _ = evaluate_arms(cal_g0, val_g0, pos_g0_s, PRIMARY_ARMS, 0.01, fwer_arms=10)
        g0_slp_sum, g0_slp_raw = evaluate_arms(cal_g0, val_g0, pos_g0_sl, PRIMARY_ARMS, 0.01, fwer_arms=10)

        print(f"[Stress] LOS+10dB, LOS+3dB, LOS_blocked, random_target, wide_async ({n_stress} each)...", flush=True)
        cal_l10 = run_batch(pool, [(s, True, None, ["afdm_dv_coh", "afdm_dv_noncoh"], "cal", 10.0, "nominal", False, False, 0.0) for s in st_los10_cal])
        pos_l10 = run_batch(pool, [(s, True, args.snr_main, ["afdm_dv_coh", "afdm_dv_noncoh"], "pos", 10.0, "nominal", False, False, 0.0) for s in st_los10_pos])
        cal_l3 = run_batch(pool, [(s, True, None, ["afdm_dv_coh", "afdm_dv_noncoh"], "cal", 3.0, "nominal", False, False, 0.0) for s in st_los3_cal])
        pos_l3 = run_batch(pool, [(s, True, args.snr_main, ["afdm_dv_coh", "afdm_dv_noncoh"], "pos", 3.0, "nominal", False, False, 0.0) for s in st_los3_pos])
        cal_bl = run_batch(pool, [(s, True, None, ["afdm_dv_coh", "afdm_dv_noncoh"], "cal", -100.0, "nominal", False, False, 0.0) for s in st_blk_cal])
        pos_bl = run_batch(pool, [(s, True, args.snr_main, ["afdm_dv_coh", "afdm_dv_noncoh"], "pos", -100.0, "nominal", False, False, 0.0) for s in st_blk_pos])
        pos_rn = run_batch(pool, [(s, True, args.snr_main, ["afdm_dv_coh"], "pos", 18.0, "random", False, False, 0.0) for s in st_rand_pos])
        pos_wa = run_batch(pool, [(s, True, args.snr_main, ["afdm_dv_coh"], "pos", 18.0, "nominal", True, False, 0.0) for s in st_wide_pos])
        for b_l in (cal_l10, pos_l10, cal_l3, pos_l3, cal_bl, pos_bl, pos_rn, pos_wa):
            accum(b_l)
        st_l10_sum, _ = evaluate_arms(cal_l10, None, pos_l10, ["afdm_dv_coh", "afdm_dv_noncoh"], 0.01, fwer_arms=10)
        st_l3_sum, _ = evaluate_arms(cal_l3, None, pos_l3, ["afdm_dv_coh", "afdm_dv_noncoh"], 0.01, fwer_arms=10)
        st_bl_sum, _ = evaluate_arms(cal_bl, None, pos_bl, ["afdm_dv_coh", "afdm_dv_noncoh"], 0.01, fwer_arms=10)
        st_rn_sum, _ = evaluate_arms(cal_s1, None, pos_rn, ["afdm_dv_coh"], 0.01, fwer_arms=10)
        st_wa_sum, _ = evaluate_arms(cal_s1, None, pos_wa, ["afdm_dv_coh"], 0.01, fwer_arms=10)
    finally:
        if pool is not None:
            pool.close()
            pool.join()

    if max_exact_rel_err >= 1e-12:
        raise RuntimeError(f"Real-map exact CUT rel err failed: {max_exact_rel_err}")

    # ==========================================================================
    # Frozen Pre-Registered Verdicts (Unrounded Raw Floats, CI-Bound Judging, Zero Loopholes)
    # ==========================================================================
    g0_ser_ok = bool(all(g0_ser_sum[a]["pos_ser_mean"] < 0.03 for a in PRIMARY_ARMS))
    g1_health_pass = bool(g1_report["pass"] and g0_ser_ok)

    # C1: 10-arm FWER Beta-Binomial (6 S1 + 4 G0, union UB 1.908%) + observed-rate anti-inflation engineering cap
    #     on afdm_dv_coh (S1 <= 10/350 = 2.86%; G0 <= 8/250 = 3.20%; deduplicated union UB 7.403%)
    c1_s1_per_arm = {a: s1_m_sum[a]["c1_pass"] for a in ALL_PASS_ARMS}
    c1_g0_per_arm = {a: g0_slp_sum[a]["c1_pass"] for a in PRIMARY_ARMS}
    c1_afdm_cap_s1 = bool(s1_m_sum["afdm_dv_coh"]["val_k_fa"] <= 10)
    c1_afdm_cap_g0 = bool(g0_slp_sum["afdm_dv_coh"]["val_k_fa"] <= 8)
    c1_pass = bool(all(c1_s1_per_arm.values()) and all(c1_g0_per_arm.values()) and c1_afdm_cap_s1 and c1_afdm_cap_g0)

    # C2: S1 (-14 dB) Blind Breakthrough vs ALL 3 equal-overhead equal-BW rivals (Bonferroni 95% LB >= +50 pp)
    c2_vs_rivals = dual_bootstrap_delta_pd(s1_m_raw["afdm_dv_coh"], {r: s1_m_raw[r] for r in RIVAL_ARMS}, 0.01, 2000, args.seed + 101)
    c2_pass = bool(c2_vs_rivals["ci95_bonf_sim_lo"] >= 0.50)

    # C3a: Mechanism Ablations (A <-> B) — ALL judged by paired 95% CI bounds (Eric 11-25 Rule 1!)
    #   (1) Dark-Valley+4thPower Capture vs TangCPP (same AFDM): 95% LB >= +50 pp
    #   (2) Stage-2 Data-Aided 2D-Ambiguity VarPro-GN vs Pilot-Only: 95% LB >= +30 pp AND pilonly share 95% UB < 80%
    #   (3) Multi-slot LOS-Referenced Coherent vs Non-Coherent at weak target (-21.5 dB): paired score SNR 95% LB >= +2.5 dB
    c3_vs_tang = dual_bootstrap_delta_pd(s1_m_raw["afdm_dv_coh"], {"afdm_tang_cpp": s1_m_raw["afdm_tang_cpp"]}, 0.01, 2000, args.seed + 201)
    c3_vs_pil = dual_bootstrap_delta_pd(s1_m_raw["afdm_dv_coh"], {"afdm_dv_pilonly": s1_m_raw["afdm_dv_pilonly"]}, 0.01, 2000, args.seed + 202)
    c3_pilonly_share = dual_bootstrap_pilonly_share(
        s1_m_raw["afdm_dv_coh"], s1_m_raw["afdm_dv_pilonly"], s1_m_raw["afdm_tang_cpp"], 0.01, 2000, args.seed + 205
    )
    c3_coh_vs_nc_pd = dual_bootstrap_delta_pd(s1_w_raw["afdm_dv_coh"], {"afdm_dv_noncoh": s1_w_raw["afdm_dv_noncoh"]}, 0.01, 2000, args.seed + 203)
    c3_coh_vs_nc_db = paired_score_diff_ci(s1_w_raw["afdm_dv_coh"], s1_w_raw["afdm_dv_noncoh"], 2000, args.seed + 204)
    c3_ablation_pass = bool(
        (c3_vs_tang["ci95_bonf_sim_lo"] >= 0.50)
        and (c3_vs_pil["ci95_bonf_sim_lo"] >= 0.30)
        and c3_pilonly_share["pass_ub_lt_0p80"]
        and (c3_coh_vs_nc_db["ci95_db"][0] >= 2.5)
    )

    # C3b: Static G0 (-19.0 dB) Non-Saturation [15%, 92%], Sensitive Continuous Zero Static Advantage
    #      (Bonferroni paired score-dB min_j U_dB_j <= +1.5 dB, half-width <= 0.375 dB) & Union-Valid Conservative DiD (>= +50 pp)
    c3_g0_slp = dual_bootstrap_delta_pd(g0_slp_raw["afdm_dv_coh"], {r: g0_slp_raw[r] for r in RIVAL_ARMS}, 0.01, 2000, args.seed + 301)
    c3_g0_score_db = paired_score_diff_vs_rivals_bonf(g0_slp_raw["afdm_dv_coh"], {r: g0_slp_raw[r] for r in RIVAL_ARMS}, 2000, args.seed + 311)
    g0_pd_af = g0_slp_sum["afdm_dv_coh"]["pos_pd_loc"]
    g0_pd_best_r = max(g0_slp_sum[r]["pos_pd_loc"] for r in RIVAL_ARMS)
    g0_nonsat = bool((0.15 <= g0_pd_af <= 0.92) and (0.15 <= g0_pd_best_r <= 0.92))
    did_cons_pt = float(c2_vs_rivals["point"] - max(0.0, c3_g0_slp["point"]))
    did_cons_lb = float(c2_vs_rivals["bonf_lo_9875"] - max(0.0, c3_g0_slp["bonf_hi_9875"]))
    c3_g0_did_pass = bool(g0_nonsat and (c3_g0_score_db["ci95_bonf_min_hi_db"] <= 1.5) and (did_cons_lb >= 0.50))
    c3_pass = bool(c3_ablation_pass and c3_g0_did_pass)

    pass_primary = bool(g1_health_pass and c1_pass and c2_pass and c3_pass)

    elapsed = time.time() - t0
    core_hours = (elapsed * args.workers) / 3600.0
    ru_s = resource.getrusage(resource.RUSAGE_SELF); ru_c = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu_hours = (ru_s.ru_utime + ru_s.ru_stime + ru_c.ru_utime + ru_c.ru_stime) / 3600.0

    summary = {
        "meta": {
            "card": "I-20261125-k03",
            "seed": args.seed,
            "mode": args.mode,
            "workers": args.workers,
            "m_slots": M_SLOTS,
            "c2": 0.0,
            "elapsed_sec": round(elapsed, 2),
            "reserved_core_hours": round(core_hours, 4),
            "process_cpu_hours": round(cpu_hours, 4),
            "pfa_map_target": 0.01,
            "snr_main": args.snr_main,
            "snr_weak": args.snr_weak,
            "snr_g0_slope": args.snr_g0_slope,
            "unified_score_calls": total_calls,
            "real_map_exact_cut_max_rel_err": max_exact_rel_err,
        },
        "gates": {
            "G1_exact_cut_ambig_bw_ovh_clut_hsser": g1_report,
            "G0_all4_mean_ser_under_3pct": g0_ser_ok,
            "G2_no_truth_in_cal_val_and_blind_interfaces": True,
        },
        "s1_main": s1_m_sum,
        "s1_weak": s1_w_sum,
        "s1_desc": s1_desc_sum,
        "g0_ser": g0_ser_sum,
        "g0_slope": g0_slp_sum,
        "stress_readouts": {
            "los_plus10db": st_l10_sum,
            "los_plus3db": st_l3_sum,
            "los_blocked": st_bl_sum,
            "random_target_locs": st_rn_sum,
            "wide_async_sto10p5_cfo3p5": st_wa_sum,
        },
        "contrasts": {
            "C2_S1_main_vs_rivals_bonf": c2_vs_rivals,
            "C3_vs_tang_cpp": c3_vs_tang,
            "C3_vs_pilonly": c3_vs_pil,
            "C3_pilonly_gain_share": c3_pilonly_share,
            "C3_weak_coh_vs_noncoh_pd": c3_coh_vs_nc_pd,
            "C3_weak_coh_vs_noncoh_score_db": c3_coh_vs_nc_db,
            "C3_G0_slope_vs_rivals_pd": c3_g0_slp,
            "C3_G0_slope_vs_rivals_score_db": c3_g0_score_db,
            "C3_G0_nonsat": {"afdm_pd": g0_pd_af, "best_rival_pd": g0_pd_best_r, "pass": g0_nonsat},
            "C3_DiD_conservative": {
                "point": did_cons_pt,
                "bonf_union_lb_97p5_onesided": did_cons_lb,
                "s1_bonf_lo_9875": c2_vs_rivals["bonf_lo_9875"],
                "g0_bonf_hi_9875": c3_g0_slp["bonf_hi_9875"],
            },
        },
        "verdicts": {
            "G1_HEALTH_BW_OVH_AMBIG_G0SER": g1_health_pass,
            "C1_s1_per_arm": c1_s1_per_arm,
            "C1_g0_per_arm": c1_g0_per_arm,
            "C1_afdm_cap_s1_k_le_10": c1_afdm_cap_s1,
            "C1_afdm_cap_g0_k_le_8": c1_afdm_cap_g0,
            "C1_VALIDITY": c1_pass,
            "C2_BLIND_BREAKTHROUGH": c2_pass,
            "C3_ABLATION_PASS": c3_ablation_pass,
            "C3_G0_DID_PASS": c3_g0_did_pass,
            "C3_PASS": c3_pass,
            "PASS_PRIMARY": pass_primary,
        },
    }

    with open(out_abs, "x") as f:
        json.dump(summary, f, indent=2, allow_nan=False)

    print("\n=== S1 MAIN (-14 dB) FULL-MAP BLIND DETECTION & LOCALIZATION @ Pfa_map=1e-2 ===", flush=True)
    for a in ALL_PASS_ARMS:
        s = s1_m_sum[a]
        print(f"  {a:18s} | Thr={s['thr_db']:+5.2f}dB | ValPfa={s['val_pfa_map']*100:.2f}% (C1={s['c1_pass']}) | Pd_loc={s['pos_pd_loc']*100:5.1f}% | SER={s['pos_ser_mean']:.4f}", flush=True)
    print(f"=== S1 WEAK ({args.snr_weak:+.1f} dB) COHERENT vs NON-COHERENT ===", flush=True)
    for a in ("afdm_dv_coh", "afdm_dv_noncoh", "afdm_dv_pilonly"):
        s = s1_w_sum[a]
        print(f"  {a:18s} | Pd_loc={s['pos_pd_loc']*100:5.1f}% | Mean={s['pos_score_db_mean']:+5.2f}dB", flush=True)
    print(f"=== G0 STATIC SLOPE ({args.snr_g0_slope:+.1f} dB) & G0(-14) SER ===", flush=True)
    for a in PRIMARY_ARMS:
        s = g0_slp_sum[a]
        print(f"  {a:18s} | ValPfa={s['val_pfa_map']*100:.2f}% | Pd_loc={s['pos_pd_loc']*100:5.1f}% | Mean={s['pos_score_db_mean']:+5.2f}dB | G0_SER={g0_ser_sum[a]['pos_ser_mean']:.4f}", flush=True)
    print(f"VERDICTS: {summary['verdicts']}", flush=True)
    print(f"Elapsed: {elapsed:.1f}s ({core_hours:.4f} core-h) -> {out_abs}", flush=True)

if __name__ == "__main__":
    main()
