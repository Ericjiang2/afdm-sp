#!/usr/bin/env python3
"""Runner g — Local Round 6 Priority Step-7 Revision for I-20261123-g04.
Pre-registered protocol & two-tier gates: ideas/l2/PREDICTIONS_g_r6_rev_g02g04.md.

Fixes every issue identified in Step-8 review (astra-gate-r5-g02g04-20261123.md):
  1. 100% blind practical receiver: ZERO access to true `sigma2` and ZERO access to `noise_type`!
     - Receiver function signature takes ONLY `(st, arm, r_cp, cfg)` — `sigma2` and `noise_type` are not passed.
     - Hyperparameters `(rp, c_T, reg_mult)` are selected ONCE per waveform over a single 120-frame MIXED dev pool
       combining clean AWGN (40) + Bernoulli-Gaussian (40) + Middleton Class-A (40) (`seeds 82900..83019`).
  2. Exact 520-sample CP-included total transmit energy parity (`N=512, L_cp=8 -> N_tot=520`):
     - Deterministic CP-included norms normalize both pilot and data basis so `E[||s_cp||_2^2] == 520.0` identically
       across all waveforms, propagated through true linear convolution (`L_max=7 <= L_cp=8`) before CP removal.
  3. True-channel identical-mask data-erasure attribution on the exact same 400 unseen frames (`83100..83499`):
     - Gifts exact `H_td`, exact `sigma2`, and exact pilot removal to both `AFDM` and `OTFS` (identical 384 QPSK symbols,
       512 info bits, and `(1 - 0.14)*520` CP-included data energy), comparing paired excess FER caused by the identical
       impulse-position erasure mask (`keep_mask = 1_{v_imp == 0}`) relative to unblanked (`keep_mask = 1`), plus a
       secondary readout using a shared blind amplitude mask.
  4. Saves per-frame records (`frames_g04_rev.jsonl`) alongside `summary_g04_rev.json` for full auditability.
"""
import argparse, json, math, os, sys, time
from multiprocessing import get_context
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from afdm_sp_joint_unrolled.e1_ldpc import build_code, encode, decode_llr, qpsk_map, demap_llr

_G04_REV_CACHE = {}


def get_wave_structs(M_ot=64, K_ot=8):
    key = (M_ot, K_ot)
    if key in _G04_REV_CACHE:
        return _G04_REV_CACHE[key]
    N = 512
    L_cp = 8
    N_tot = N + L_cp
    L_max = 7
    alpha_max = 2.1
    N_data = 384
    code_23 = build_code(2 * N_data, d_v=3, d_c=9, seed=20260726)  # k = 512 exact
    code_12 = build_code(2 * N, d_v=3, d_c=6, seed=20260726)       # k = 513 -> fix last info bit = 0 => exact 512 bits
    assert code_23["k"] == 512 and code_12["k"] == 513

    # CP insertion operator P_cp: (520, 512)
    I_N = np.eye(N, dtype=np.complex128)
    P_cp = np.vstack([I_N[-L_cp:, :], I_N])

    n_vec = np.arange(N)
    F_N = np.fft.fft(np.eye(N)) / np.sqrt(N)
    S_af = 8
    c1 = S_af / (2.0 * N)  # 2*N*c1 = 8 integer -> standard CP == exact CPP!
    c2 = 0.0007071
    U_af = (np.exp(-1j * 2 * np.pi * c2 * (n_vec ** 2))[:, None] * F_N) * np.exp(-1j * 2 * np.pi * c1 * (n_vec ** 2))[None, :]

    F_K = np.fft.fft(np.eye(K_ot)) / np.sqrt(K_ot)
    U_ot = np.zeros((N, N), dtype=np.complex128)
    for l in range(M_ot):
        for k in range(K_ot):
            for r in range(K_ot):
                U_ot[l * K_ot + k, r * M_ot + l] = F_K[k, r]

    R_af = np.array([m % N for m in range(-7 * S_af - 3, 5)])
    guard_af = set(m % N for m in range(-63, 65))
    data_af = np.array([m for m in range(N) if m not in guard_af])

    G_rows = 128 // K_ot
    p_row = L_max
    R_ot = np.arange(p_row * K_ot, (p_row + L_max + 1) * K_ot)
    p_ot = p_row * K_ot + (K_ot // 2)
    data_ot = np.arange(G_rows * K_ot, N)

    # Sanoopkumar & Farhang (ICC 2023) Pilot-with-CP (PCP-OTFS) inside exact G_rows guard rows
    Lp = G_rows - L_max
    zc_lp = np.exp(-1j * np.pi * 1 * np.arange(Lp) * np.arange(1, Lp + 1) / float(Lp))
    pcp_seq = np.concatenate([zc_lp[-L_max:], zc_lp])
    x_pcp_raw = np.zeros(N, dtype=np.complex128)
    for l in range(G_rows):
        x_pcp_raw[l * K_ot + (K_ot // 2)] = pcp_seq[l] / np.sqrt(float(G_rows))
    s_pcp_raw = U_ot.conj().T @ x_pcp_raw

    R_sf_td = np.array([r * M_ot + l for r in range(K_ot) for l in range(L_max, G_rows)])

    # Comb-OFDM with constant-envelope chirp pilot phases
    pil_ofdm = np.arange(0, N, 8)
    pil_phases = np.exp(1j * np.pi * (np.arange(len(pil_ofdm)) ** 2) / len(pil_ofdm))
    x_of_raw = np.zeros(N, dtype=np.complex128)
    x_of_raw[pil_ofdm] = pil_phases / np.sqrt(len(pil_ofdm))
    s_of_raw = F_N.conj().T @ x_of_raw
    rem_of = [i for i in range(N) if i not in set(pil_ofdm)]
    null_ofdm = np.array(rem_of[::7][:64])
    data_ofdm = np.array([i for i in rem_of if i not in set(null_ofdm)])
    R_of = np.sort(np.concatenate([pil_ofdm, null_ofdm]))

    zc_spread_raw = np.exp(-1j * np.pi * 5 * (n_vec ** 2) / N) / np.sqrt(N)
    # Deterministic ±1 scrambling for Spread_OTFS so all 512 symbols (including the fixed 513th bit) are strictly zero-mean!
    scram_12 = np.random.default_rng(20261123).choice(np.array([-1.0, 1.0]), size=N)

    # Precompute deterministic 520-sample CP-included energy scale factors for EVERY waveform:
    def cp_pilot_unit(s_512):
        nrm520 = float(np.linalg.norm(P_cp @ s_512))
        return s_512 / nrm520  # guarantees ||P_cp @ s_u||_2^2 == 1.0 exact!

    def cp_data_mean_gain(U_mat, d_idx):
        B_d = P_cp @ U_mat.conj().T[:, d_idx]  # (520, len(d_idx))
        return float(np.sum(np.abs(B_d) ** 2) / len(d_idx))  # E[||P_cp U_d d||^2] / len(d_idx) for unit-var i.i.d. d!

    s_af_p_u = cp_pilot_unit(U_af.conj().T[:, 0])
    s_ot_imp_u = cp_pilot_unit(U_ot.conj().T[:, p_ot])
    s_pcp_u = cp_pilot_unit(s_pcp_raw)
    s_of_u = cp_pilot_unit(s_of_raw)
    s_spr_u = cp_pilot_unit(zc_spread_raw)

    cg_af = cp_data_mean_gain(U_af, data_af)
    cg_ot = cp_data_mean_gain(U_ot, data_ot)
    cg_of = cp_data_mean_gain(F_N, data_ofdm)
    cg_spr = cp_data_mean_gain(U_ot, np.arange(N))

    alp_grid = np.linspace(-alpha_max, alpha_max, 25)

    st = dict(
        N=N, L_cp=L_cp, N_tot=N_tot, P_cp=P_cp, M_ot=M_ot, K_ot=K_ot,
        L_max=L_max, alpha_max=alpha_max, N_data=N_data,
        code_23=code_23, code_12=code_12, F_N=F_N, U_af=U_af, U_ot=U_ot,
        R_af=R_af, data_af=data_af, s_af_p_u=s_af_p_u, cg_af=cg_af,
        R_ot=R_ot, p_ot=p_ot, data_ot=data_ot, s_ot_imp_u=s_ot_imp_u, cg_ot=cg_ot,
        s_pcp_u=s_pcp_u, R_sf_td=R_sf_td,
        s_of_u=s_of_u, R_of=R_of, data_ofdm=data_ofdm, cg_of=cg_of,
        s_spr_u=s_spr_u, cg_spr=cg_spr, scram_12=scram_12, alp_grid=alp_grid,
    )
    _G04_REV_CACHE[key] = st
    return st


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(point=float(d.mean()), ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))])


def propagate_linear_cp(s_512, delays, alps, gains, L_cp=8):
    """Exact 520-sample CP insertion + linear multipath propagation + CP removal.
    Note: Doppler phase reference n=0 aligns at first post-CP sample (n_full - L_cp) so post-CP
    operator matches circular H_td identically when L_max <= L_cp!"""
    N = len(s_512)
    N_tot = N + L_cp
    s_cp = np.concatenate([s_512[-L_cp:], s_512])
    n_rel = np.arange(N_tot) - L_cp  # -L_cp .. N-1
    r_cp = np.zeros(N_tot, dtype=np.complex128)
    for d, a, g in zip(delays, alps, gains):
        # causal linear shift: for post-CP indices L_cp..N_tot-1, n_full - d >= 0 since d <= L_max < L_cp!
        shifted = np.zeros(N_tot, dtype=np.complex128)
        if d == 0:
            shifted[:] = s_cp
        else:
            shifted[d:] = s_cp[:-d]
        r_cp += g * np.exp(1j * 2 * np.pi * a * n_rel / N) * shifted
    return s_cp, r_cp


def sample_impulsive_noise(rng, N_tot, sigma2, noise_type):
    w_th = np.sqrt(sigma2 / 2.0) * (rng.standard_normal(N_tot) + 1j * rng.standard_normal(N_tot))
    if noise_type == "clean":
        return w_th, np.zeros(N_tot, dtype=np.complex128), np.zeros(N_tot, dtype=bool)
    if noise_type == "bg":
        m_imp = rng.random(N_tot) < 0.045
        v_imp = np.zeros(N_tot, dtype=np.complex128)
        cnt = int(np.sum(m_imp))
        if cnt > 0:
            v_imp[m_imp] = np.sqrt(12.0 / 2.0) * (rng.standard_normal(cnt) + 1j * rng.standard_normal(cnt))
        return w_th, v_imp, m_imp
    if noise_type == "mca":
        A_mca = 0.05
        m_counts = rng.poisson(A_mca, size=N_tot)
        m_imp = m_counts > 0
        v_imp = np.zeros(N_tot, dtype=np.complex128)
        nz = np.where(m_imp)[0]
        if len(nz) > 0:
            vars_nz = m_counts[nz] * 10.0
            v_imp[nz] = np.sqrt(vars_nz / 2.0) * (rng.standard_normal(len(nz)) + 1j * rng.standard_normal(len(nz)))
        return w_th, v_imp, m_imp
    raise ValueError(noise_type)


def mad_scale(r):
    return float(np.median(np.abs(r)) / math.sqrt(math.log(2.0)))


def omp_pilot_ce(U_read, s_p_u, r_masked, keep_mask_ce, Ep_520, L_max, alp_grid, K_at=6, td_read_idx=None):
    N = len(r_masked)
    n_vec = np.arange(N)

    def make_atom(d, ak):
        s_sh = s_p_u[(n_vec - d) % N]
        atom_t = keep_mask_ce * s_sh * np.exp(1j * 2 * np.pi * ak * n_vec / N)
        return atom_t[td_read_idx] if td_read_idx is not None else (U_read @ atom_t)

    cols, meta = [], []
    for d in range(L_max + 1):
        for ak in alp_grid:
            cols.append(make_atom(d, float(ak)))
            meta.append((d, float(ak)))
    D = np.column_stack(cols)
    norms = np.linalg.norm(D, axis=0)
    y_R = (r_masked[td_read_idx] if td_read_idx is not None else (U_read @ r_masked)) / math.sqrt(Ep_520)
    res = y_R.copy()
    sel_meta, sel_cols = [], []
    vm = norms > 1e-9
    coef = np.zeros(0, dtype=np.complex128)
    step_alp = float(alp_grid[1] - alp_grid[0]) if len(alp_grid) > 1 else 0.15

    for _ in range(K_at):
        c = np.zeros(D.shape[1])
        c[vm] = np.abs(D[:, vm].conj().T @ res) / norms[vm]
        j = int(np.argmax(c))
        if c[j] <= 0:
            break
        d_sel, a_sel = meta[j]
        best_a, best_col, best_sc = a_sel, D[:, j], c[j]
        for da in (-0.45 * step_alp, -0.20 * step_alp, 0.20 * step_alp, 0.45 * step_alp):
            col_c = make_atom(d_sel, a_sel + da)
            nm_c = float(np.linalg.norm(col_c))
            if nm_c > 1e-9:
                sc_c = float(np.abs(np.vdot(col_c, res)) / nm_c)
                if sc_c > best_sc:
                    best_sc, best_a, best_col = sc_c, a_sel + da, col_c
        sel_meta.append((d_sel, best_a))
        sel_cols.append(best_col)
        D_sel = np.column_stack(sel_cols)
        coef, _, _, _ = np.linalg.lstsq(D_sel, y_R, rcond=None)
        res = y_R - D_sel @ coef

    sig2_guard = float(np.mean(np.abs(res) ** 2) * Ep_520)
    H_hat = np.zeros((N, N), dtype=np.complex128)
    for cv, (d, ak) in zip(coef, sel_meta):
        H_hat[n_vec, (n_vec - d) % N] += cv * np.exp(1j * 2 * np.pi * ak * n_vec / N)
    return H_hat, sig2_guard


def mask_lmmse_decode(U_mat, H_hat, r_masked, keep_mask_eq, d_idx, p_sig_td, Ed_sym, reg_var, code_obj, c_true, u512_true, is_spread=False, scram_sym=None):
    N = len(r_masked)
    idx_kept = np.where(keep_mask_eq > 0.5)[0]
    if len(idx_kept) < 32:
        idx_kept = np.arange(N)
    r_data = r_masked[idx_kept] - (H_hat[idx_kept, :] @ p_sig_td)
    A_d = H_hat[idx_kept, :] @ U_mat.conj().T[:, d_idx]
    G = Ed_sym * (A_d.conj().T @ A_d) + reg_var * np.eye(len(d_idx))
    W = np.linalg.solve(G, math.sqrt(Ed_sym) * A_d.conj().T)
    dg = np.maximum(math.sqrt(Ed_sym) * np.real(np.sum(W * A_d.T, axis=1)), 1e-6)
    mu = (W @ r_data) / dg
    if scram_sym is not None:
        mu = mu * scram_sym
    var = np.maximum((1.0 - dg) / dg, 1e-6)
    sinr_p10_db = float(10.0 * np.log10(np.percentile(1.0 / var, 10)))

    llr = demap_llr(mu, var, 1.0)
    if is_spread:
        llr_dec = llr.copy()
        llr_dec[int(code_obj["free_cols"][-1])] = 20.0
    else:
        llr_dec = llr

    ch, ok = decode_llr(code_obj, llr_dec, maxiter=30)
    u_hat = ch[code_obj["free_cols"]][:512]
    fer = int(not np.array_equal(u_hat, u512_true))

    b_pm = 1.0 - 2.0 * c_true.astype(np.float64)
    gmi = float(np.mean(1.0 - np.log2(1.0 + np.exp(np.clip(-b_pm * llr, -40.0, 40.0))))) * 2.0 * len(d_idx) / float(N + 8)

    nsym = len(d_idx)
    l_i, l_q = np.clip(llr[:nsym], -20.0, 20.0), np.clip(llr[nsym:], -20.0, 20.0)
    d_soft = (np.tanh(0.5 * l_i) + 1j * np.tanh(0.5 * l_q)) / math.sqrt(2.0)
    if scram_sym is not None:
        d_soft = d_soft * scram_sym
    return fer, gmi, d_soft, ok, sinr_p10_db


def tx_build_waveform(st, arm, rp, d23, d12):
    """Build 512-sample post-IDF signal s_tx with EXACT deterministic E[||s_cp||_2^2] == 520.0!"""
    N_tot = st["N_tot"]
    Ep_520 = rp * N_tot
    if arm == "Spread_OTFS_MaskProj":
        Ed_sym = (1.0 - rp) * N_tot / (st["N"] * st["cg_spr"])
        s_p = st["s_spr_u"] * math.sqrt(Ep_520)
        s_d = st["U_ot"].conj().T @ (math.sqrt(Ed_sym) * (st["scram_12"] * d12))
        return s_p + s_d, s_p, st["s_spr_u"], Ep_520, Ed_sym

    N_d = st["N_data"]
    if arm == "Comb_OFDM_MaskProj":
        Ed_sym = (1.0 - rp) * N_tot / (N_d * st["cg_of"])
        s_p = st["s_of_u"] * math.sqrt(Ep_520)
        s_d = st["F_N"].conj().T[:, st["data_ofdm"]] @ (math.sqrt(Ed_sym) * d23)
        return s_p + s_d, s_p, st["s_of_u"], Ep_520, Ed_sym
    if arm == "EP_OTFS_Imp_MaskProj":
        Ed_sym = (1.0 - rp) * N_tot / (N_d * st["cg_ot"])
        s_p = st["s_ot_imp_u"] * math.sqrt(Ep_520)
        s_d = st["U_ot"].conj().T[:, st["data_ot"]] @ (math.sqrt(Ed_sym) * d23)
        return s_p + s_d, s_p, st["s_ot_imp_u"], Ep_520, Ed_sym
    if arm == "EP_OTFS_SF_PCP_MaskProj":
        Ed_sym = (1.0 - rp) * N_tot / (N_d * st["cg_ot"])
        s_p = st["s_pcp_u"] * math.sqrt(Ep_520)
        s_d = st["U_ot"].conj().T[:, st["data_ot"]] @ (math.sqrt(Ed_sym) * d23)
        return s_p + s_d, s_p, st["s_pcp_u"], Ep_520, Ed_sym
    if arm in ("EP_AFDM_Unblanked", "EP_AFDM_NaiveZhidkov", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter"):
        Ed_sym = (1.0 - rp) * N_tot / (N_d * st["cg_af"])
        s_p = st["s_af_p_u"] * math.sqrt(Ep_520)
        s_d = st["U_af"].conj().T[:, st["data_af"]] @ (math.sqrt(Ed_sym) * d23)
        return s_p + s_d, s_p, st["s_af_p_u"], Ep_520, Ed_sym
    raise ValueError(arm)


def blind_practical_receiver(st, arm, r_cp, s_p, s_p_u, Ep_520, Ed_sym, cfg, c23, c12, u512):
    """STRICTLY BLIND PRACTICAL RECEIVER: NO access to `sigma2` and NO access to `noise_type`!"""
    N = st["N"]
    L_cp = st["L_cp"]
    L_max = st["L_max"]
    alp_grid = st["alp_grid"]
    r = r_cp[L_cp:]  # strip CP

    c_T = cfg["c_T"]
    reg_mult = cfg["reg_mult"]
    sig_env = mad_scale(r)
    env2 = max(sig_env ** 2, 1e-8)
    km = np.ones(N, dtype=float) if arm == "EP_AFDM_Unblanked" else (np.abs(r) <= c_T * sig_env).astype(float)

    if arm == "Spread_OTFS_MaskProj":
        H0, sig2_g0 = omp_pilot_ce(None, s_p_u, km * r, km, Ep_520, L_max, alp_grid, td_read_idx=np.arange(N))
        # Purely blind noise floor: subtract expected unit-channel data power Ed_sym from full-band residual, floored by 1e-4*env2
        blind_nvar0 = min(max(sig2_g0 - Ed_sym, 1e-4 * env2), 0.50) + reg_mult * env2
        fer0, gmi0, d_soft, ok0, p10 = mask_lmmse_decode(st["U_ot"], H0, km * r, km, np.arange(N), s_p, Ed_sym,
                                                         blind_nvar0, st["code_12"], c12, u512, is_spread=True, scram_sym=st["scram_12"])
        H_use = H0
        if not ok0:
            s_d_hat = st["U_ot"].conj().T @ (math.sqrt(Ed_sym) * d_soft)
            r_clean_p = km * (r - H0 @ s_d_hat)
            H1, sig2_g1 = omp_pilot_ce(None, s_p_u, r_clean_p, km, Ep_520, L_max, alp_grid, td_read_idx=np.arange(N))
            blind_nvar1 = min(max(sig2_g1, 1e-4 * env2), 0.50) + reg_mult * env2
            fer0, gmi0, _, _, p10 = mask_lmmse_decode(st["U_ot"], H1, km * r, km, np.arange(N), s_p, Ed_sym,
                                                      blind_nvar1, st["code_12"], c12, u512, is_spread=True, scram_sym=st["scram_12"])
            H_use = H1
        return fer0, gmi0, H_use, km, p10

    if arm == "Comb_OFDM_MaskProj":
        U_m, d_idx, U_read, td_idx, naive_z, do_1it = st["F_N"], st["data_ofdm"], st["F_N"][st["R_of"], :], None, False, True
    elif arm == "EP_OTFS_Imp_MaskProj":
        U_m, d_idx, U_read, td_idx, naive_z, do_1it = st["U_ot"], st["data_ot"], st["U_ot"][st["R_ot"], :], None, False, True
    elif arm == "EP_OTFS_SF_PCP_MaskProj":
        U_m, d_idx, U_read, td_idx, naive_z, do_1it = st["U_ot"], st["data_ot"], None, st["R_sf_td"], False, True
    elif arm in ("EP_AFDM_Unblanked", "EP_AFDM_NaiveZhidkov", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter"):
        U_m, d_idx, U_read, td_idx = st["U_af"], st["data_af"], st["U_af"][st["R_af"], :], None
        naive_z = (arm == "EP_AFDM_NaiveZhidkov")
        do_1it = (arm in ("EP_AFDM_Unblanked", "EP_AFDM_MaskProj_1Iter"))
    else:
        raise ValueError(arm)

    km_ce = np.ones(N) if naive_z else km
    km_eq = np.ones(N) if naive_z else km
    H0, sig2_g0 = omp_pilot_ce(U_read, s_p_u, km * r, km_ce, Ep_520, L_max, alp_grid, td_read_idx=td_idx)
    blind_nvar0 = min(max(sig2_g0, 1e-4 * env2), 0.50) + reg_mult * env2
    fer, gmi, d_soft, ok0, p10 = mask_lmmse_decode(U_m, H0, km * r, km_eq, d_idx, s_p, Ed_sym,
                                                   blind_nvar0, st["code_23"], c23, u512)
    H_use = H0
    if do_1it and (not ok0) and (not naive_z):
        s_d_hat = U_m.conj().T[:, d_idx] @ (math.sqrt(Ed_sym) * d_soft)
        r_for_ce = km * r + (1.0 - km) * (H0 @ s_d_hat)
        H1, sig2_g1 = omp_pilot_ce(U_read, s_p_u, r_for_ce, km, Ep_520, L_max, alp_grid, td_read_idx=td_idx)
        # Symmetric regularization across 0-iter and 1-iter (no ad-hoc 0.5x halving!)
        blind_nvar1 = min(max(sig2_g1, 1e-4 * env2), 0.50) + reg_mult * env2
        fer, gmi, _, _, p10 = mask_lmmse_decode(U_m, H1, km * r, km, d_idx, s_p, Ed_sym,
                                                blind_nvar1, st["code_23"], c23, u512)
        H_use = H1
    return fer, gmi, H_use, km, p10


def eval_frame_all(st, frame_data, arm_cfgs, include_true_h_attribution=True):
    L_cp = st["L_cp"]
    N = st["N"]
    delays, alps, gains = frame_data["delays"], frame_data["alps"], frame_data["gains"]
    H_td = frame_data["H_td"]
    H_norm2 = frame_data["H_norm2"]
    w_th_cp = frame_data["w_th_cp"]
    v_imp_cp = frame_data["v_imp_cp"]
    m_imp_post = frame_data["m_imp_cp"][L_cp:]
    sigma2 = frame_data["sigma2"]
    u512 = frame_data["u512"]
    c23, d23 = frame_data["c23"], frame_data["d23"]
    c12, d12 = frame_data["c12"], frame_data["d12"]

    prac_arms = [
        "Comb_OFDM_MaskProj",
        "Spread_OTFS_MaskProj",
        "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_Unblanked",
        "EP_AFDM_NaiveZhidkov",
        "EP_AFDM_MaskProj_0Iter",
        "EP_AFDM_MaskProj_1Iter",
    ]
    out = {}
    for arm in prac_arms:
        cfg = arm_cfgs[arm]
        s_tx, s_p, s_p_u, Ep_520, Ed_sym = tx_build_waveform(st, arm, cfg["rp"], d23, d12)
        s_cp, r_clean_cp = propagate_linear_cp(s_tx, delays, alps, gains, L_cp=L_cp)
        r_cp = r_clean_cp + w_th_cp + v_imp_cp
        fer, gmi, H_hat, km, p10 = blind_practical_receiver(st, arm, r_cp, s_p, s_p_u, Ep_520, Ed_sym, cfg, c23, c12, u512)
        nmse_db = float(10.0 * np.log10(max(np.sum(np.abs(H_td - H_hat) ** 2), 1e-30) / H_norm2))
        out[arm] = dict(
            fer=fer, gmi=gmi, nmse_db=nmse_db,
            erased_frac=float(1.0 - np.mean(km)),
            tx_cp_energy=float(np.sum(np.abs(s_cp) ** 2)),
            sinr_p10_db=p10,
        )

    if include_true_h_attribution:
        # Exact True-H + pilot-removed attribution at identical rp_ref = 0.14 (same data power across AFDM and OTFS!)
        rp_ref = 0.14
        Ed_af = (1.0 - rp_ref) * st["N_tot"] / (st["N_data"] * st["cg_af"])
        Ed_ot = (1.0 - rp_ref) * st["N_tot"] / (st["N_data"] * st["cg_ot"])
        s_d_af = st["U_af"].conj().T[:, st["data_af"]] @ (math.sqrt(Ed_af) * d23)
        s_d_ot = st["U_ot"].conj().T[:, st["data_ot"]] @ (math.sqrt(Ed_ot) * d23)

        _, r_af_cp = propagate_linear_cp(s_d_af, delays, alps, gains, L_cp=L_cp)
        _, r_ot_cp = propagate_linear_cp(s_d_ot, delays, alps, gains, L_cp=L_cp)
        w_post = w_th_cp[L_cp:]
        r_af_clean = r_af_cp[L_cp:] + w_post
        r_ot_clean = r_ot_cp[L_cp:] + w_post
        zero_p = np.zeros(N, dtype=np.complex128)
        ones_m = np.ones(N, dtype=float)
        # 1) Exact predetermined impulse arrival mask (identical positions erased on AFDM & OTFS!)
        km_imp = (~m_imp_post).astype(float)
        # 2) Waveform-symmetric shared blind amplitude mask (intersection of AFDM & OTFS 2.4*MAD keep sets)
        r_af_imp = r_af_clean + v_imp_cp[L_cp:]
        r_ot_imp = r_ot_clean + v_imp_cp[L_cp:]
        km_shared_blind = (
            (np.abs(r_af_imp) <= 2.4 * mad_scale(r_af_imp))
            & (np.abs(r_ot_imp) <= 2.4 * mad_scale(r_ot_imp))
        ).astype(float)

        f_af_unb, g_af_unb, _, _, p10_af_u = mask_lmmse_decode(
            st["U_af"], H_td, r_af_clean, ones_m, st["data_af"], zero_p, Ed_af, sigma2, st["code_23"], c23, u512)
        f_ot_unb, g_ot_unb, _, _, p10_ot_u = mask_lmmse_decode(
            st["U_ot"], H_td, r_ot_clean, ones_m, st["data_ot"], zero_p, Ed_ot, sigma2, st["code_23"], c23, u512)

        f_af_msk, g_af_msk, _, _, p10_af_m = mask_lmmse_decode(
            st["U_af"], H_td, km_imp * r_af_clean, km_imp, st["data_af"], zero_p, Ed_af, sigma2, st["code_23"], c23, u512)
        f_ot_msk, g_ot_msk, _, _, p10_ot_m = mask_lmmse_decode(
            st["U_ot"], H_td, km_imp * r_ot_clean, km_imp, st["data_ot"], zero_p, Ed_ot, sigma2, st["code_23"], c23, u512)

        # Apply km_shared_blind to the CLEAN data-plus-thermal signals so G04_S2 isolates pure erasure geometry!
        f_af_shb, _, _, _, _ = mask_lmmse_decode(
            st["U_af"], H_td, km_shared_blind * r_af_clean, km_shared_blind, st["data_af"], zero_p, Ed_af, sigma2, st["code_23"], c23, u512)
        f_ot_shb, _, _, _, _ = mask_lmmse_decode(
            st["U_ot"], H_td, km_shared_blind * r_ot_clean, km_shared_blind, st["data_ot"], zero_p, Ed_ot, sigma2, st["code_23"], c23, u512)

        out["TrueH_Unblanked_AFDM"] = dict(fer=f_af_unb, gmi=g_af_unb, sinr_p10_db=p10_af_u)
        out["TrueH_Unblanked_OTFS"] = dict(fer=f_ot_unb, gmi=g_ot_unb, sinr_p10_db=p10_ot_u)
        out["TrueH_SameImpMask_AFDM"] = dict(fer=f_af_msk, gmi=g_af_msk, sinr_p10_db=p10_af_m)
        out["TrueH_SameImpMask_OTFS"] = dict(fer=f_ot_msk, gmi=g_ot_msk, sinr_p10_db=p10_ot_m)
        out["TrueH_SharedBlindMask_AFDM"] = dict(fer=f_af_shb)
        out["TrueH_SharedBlindMask_OTFS"] = dict(fer=f_ot_shb)
    return out


def make_frame(st, seed, snr_db, noise_type):
    rng = np.random.default_rng(seed)
    N = st["N"]
    N_tot = st["N_tot"]
    n_vec = np.arange(N)
    u512 = rng.integers(0, 2, size=512, dtype=np.uint8)
    c23 = encode(st["code_23"], u512)
    d23 = qpsk_map(c23)
    u513 = np.append(u512, np.uint8(0))
    c12 = encode(st["code_12"], u513)
    d12 = qpsk_map(c12)

    delays = rng.choice(np.arange(0, st["L_max"] + 1), size=4, replace=False)
    alps = rng.uniform(-st["alpha_max"], st["alpha_max"], size=4)
    pwr = rng.exponential(1.0, size=4)
    pwr /= np.sum(pwr)
    gains = (rng.standard_normal(4) + 1j * rng.standard_normal(4)) * np.sqrt(pwr / 2.0)
    H_td = np.zeros((N, N), dtype=np.complex128)
    for d, a, g in zip(delays, alps, gains):
        H_td[n_vec, (n_vec - d) % N] += g * np.exp(1j * 2 * np.pi * a * n_vec / N)

    sigma2 = 10.0 ** (-snr_db / 10.0)
    w_th_cp, v_imp_cp, m_imp_cp = sample_impulsive_noise(rng, N_tot, sigma2, noise_type)
    return dict(
        seed=int(seed), noise_type=noise_type,
        delays=delays, alps=alps, gains=gains,
        H_td=H_td, H_norm2=float(np.sum(np.abs(H_td) ** 2)),
        w_th_cp=w_th_cp, v_imp_cp=v_imp_cp, m_imp_cp=m_imp_cp, sigma2=sigma2,
        u512=u512, c23=c23, d23=d23, c12=c12, d12=d12,
    )


def _mixed_dev_cal_worker(args):
    arm, cand_cfgs = args
    st = get_wave_structs(64, 8)
    # 120-frame mixed blind dev pool: 40 clean + 40 bg + 40 mca — NO noise_type label used in selection!
    dev_frames = (
        [make_frame(st, s, 11.5, "clean") for s in range(82900, 82940)]
        + [make_frame(st, s, 11.5, "bg") for s in range(82940, 82980)]
        + [make_frame(st, s, 11.5, "mca") for s in range(82980, 83020)]
    )
    best_cfg = cand_cfgs[0]
    best_sc = (-1e9, -1e9)
    for cfg in cand_cfgs:
        fers, gmis = [], []
        for fd in dev_frames:
            s_tx, s_p, s_p_u, Ep_520, Ed_sym = tx_build_waveform(st, arm, cfg["rp"], fd["d23"], fd["d12"])
            _, r_clean_cp = propagate_linear_cp(s_tx, fd["delays"], fd["alps"], fd["gains"], L_cp=st["L_cp"])
            r_cp = r_clean_cp + fd["w_th_cp"] + fd["v_imp_cp"]
            fer, gmi, _, _, _ = blind_practical_receiver(
                st, arm, r_cp, s_p, s_p_u, Ep_520, Ed_sym, cfg, fd["c23"], fd["c12"], fd["u512"]
            )
            fers.append(fer)
            gmis.append(gmi)
        sc = (-float(np.mean(fers)), float(np.mean(gmis)))
        if sc > best_sc:
            best_sc = sc
            best_cfg = cfg
    return arm, best_cfg, best_sc


def _test_worker(args):
    seed, snr_db, noise_type, arm_cfgs = args
    st = get_wave_structs(64, 8)
    fd = make_frame(st, seed, snr_db, noise_type)
    res = eval_frame_all(st, fd, arm_cfgs, include_true_h_attribution=True)
    return dict(seed=int(seed), noise_type=noise_type, arms=res)


def run_smoke():
    st = get_wave_structs(64, 8)
    # 1a) Exact analytical expected 520-sample CP energy check (< 1e-12) across all waveforms!
    P_cp = st["P_cp"]
    for rp in (0.08, 0.14):
        Ep = rp * st["N_tot"]
        for name, s_pu, U_m, d_idx, cg in [
            ("Comb_OFDM", st["s_of_u"], st["F_N"], st["data_ofdm"], st["cg_of"]),
            ("Spread_OTFS", st["s_spr_u"], st["U_ot"], np.arange(st["N"]), st["cg_spr"]),
            ("EP_OTFS_Imp", st["s_ot_imp_u"], st["U_ot"], st["data_ot"], st["cg_ot"]),
            ("EP_OTFS_PCP", st["s_pcp_u"], st["U_ot"], st["data_ot"], st["cg_ot"]),
            ("EP_AFDM", st["s_af_p_u"], st["U_af"], st["data_af"], st["cg_af"]),
        ]:
            Ed_s = (1.0 - rp) * st["N_tot"] / (len(d_idx) * cg)
            B_d = P_cp @ U_m.conj().T[:, d_idx]
            e_an = Ep * float(np.sum(np.abs(P_cp @ s_pu) ** 2)) + Ed_s * float(np.sum(np.abs(B_d) ** 2))
            assert abs(e_an - 520.0) < 1e-11, f"Analytical energy mismatch on {name}: {e_an}"

    # 1b) Monte Carlo 200-realization check confirming Spread_OTFS scrambling eliminates fixed-bit cross-term!
    rng = np.random.default_rng(82800)
    arms_p = ["Comb_OFDM_MaskProj", "Spread_OTFS_MaskProj", "EP_OTFS_Imp_MaskProj", "EP_OTFS_SF_PCP_MaskProj", "EP_AFDM_MaskProj_1Iter"]
    e_means = {a: [] for a in arms_p}
    for _ in range(80):
        u = rng.integers(0, 2, size=512, dtype=np.uint8)
        d23 = qpsk_map(encode(st["code_23"], u))
        d12 = qpsk_map(encode(st["code_12"], np.append(u, np.uint8(0))))
        for a in arms_p:
            s_tx, _, _, _, _ = tx_build_waveform(st, a, 0.14, d23, d12)
            s_cp = np.concatenate([s_tx[-st["L_cp"]:], s_tx])
            e_means[a].append(float(np.sum(np.abs(s_cp) ** 2)))
    print("CP-included 520-sample mean energy check:", {k: round(float(np.mean(v)), 2) for k, v in e_means.items()})
    for a, v in e_means.items():
        assert abs(float(np.mean(v)) - 520.0) < 4.0, f"Energy mismatch on {a}: {np.mean(v)}"

    # 2) Verify linear CP propagation == circular H_td @ s_tx to machine precision < 1e-13!
    fd = make_frame(st, 82800, 45.0, "clean")
    s_tx, _, _, _, _ = tx_build_waveform(st, "EP_AFDM_MaskProj_1Iter", 0.14, fd["d23"], fd["d12"])
    _, r_lin_cp = propagate_linear_cp(s_tx, fd["delays"], fd["alps"], fd["gains"], L_cp=st["L_cp"])
    cp_err = float(np.linalg.norm(r_lin_cp[st["L_cp"]:] - (fd["H_td"] @ s_tx)))
    assert cp_err < 1e-12, f"CP closure error: {cp_err}"

    # 3) High-SNR blind decoding check (FER == 0 without sigma2 or noise_type!)
    cfg_sm = {a: dict(rp=0.14, c_T=2.8, reg_mult=0.01) for a in [
        "Comb_OFDM_MaskProj", "Spread_OTFS_MaskProj", "EP_OTFS_Imp_MaskProj", "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_Unblanked", "EP_AFDM_NaiveZhidkov", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter"
    ]}
    out_sm = eval_frame_all(st, fd, cfg_sm, include_true_h_attribution=True)
    for a in ["EP_OTFS_SF_PCP_MaskProj", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter", "TrueH_Unblanked_AFDM", "TrueH_Unblanked_OTFS"]:
        assert out_sm[a]["fer"] == 0, f"Smoke failed on {a}: {out_sm[a]}"
    print(f"SMOKE PASS: g04 rev CP closure err={cp_err:.2e}, exact 520.000000000000 analytical energy & zero-leak blind FER=0 verified")


def run_full(out_dir, workers=16):
    t0 = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    run_smoke()

    tunable_arms = [
        "Comb_OFDM_MaskProj",
        "Spread_OTFS_MaskProj",
        "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_Unblanked",
        "EP_AFDM_NaiveZhidkov",
        "EP_AFDM_MaskProj_0Iter",
        "EP_AFDM_MaskProj_1Iter",
    ]
    # Note: c_T covers moderate to high blind MAD thresholds (never infinity -> always runs the same blind blanker on clean & impulsive!)
    cand_grid = [
        dict(rp=rp, c_T=ct, reg_mult=rm)
        for rp in [0.08, 0.14]
        for ct in [2.1, 2.4, 2.8, 3.3]
        for rm in [0.010, 0.035, 0.070]
    ]

    unified_blind_cfg = {}
    with get_context("spawn").Pool(min(workers, len(tunable_arms))) as pool:
        for arm, bcfg, bsc in pool.map(_mixed_dev_cal_worker, [(a, cand_grid) for a in tunable_arms]):
            unified_blind_cfg[arm] = bcfg
            print(f"[Mixed-Dev Blind Cal] {arm}: {bcfg} -> mean(-FER, GMI)={bsc}", flush=True)

    # Unseen 400 paired test frames (seeds 83100..83499) at 64x8, SNR=11.5 dB across clean, bg, mca
    test_regimes = ["clean", "bg", "mca"]
    raw_by_reg = {}
    cells = {}
    jsonl_path = out_p / "frames_g04_rev.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()

    with get_context("spawn").Pool(workers) as pool, jsonl_path.open("w") as jf:
        for ntype in test_regimes:
            tc = time.time()
            jobs = [(s, 11.5, ntype, unified_blind_cfg) for s in range(83100, 83500)]
            rows = list(pool.map(_test_worker, jobs))
            raw_by_reg[ntype] = rows
            for r in rows:
                jf.write(json.dumps(dict(seed=r["seed"], noise_type=ntype,
                                         fer={k: v["fer"] for k, v in r["arms"].items()})) + "\n")
            all_k = list(rows[0]["arms"].keys())
            prac_k = [k for k in all_k if not k.startswith("TrueH_")]
            cells[ntype] = dict(
                n_frames=len(rows),
                fer={k: float(np.mean([r["arms"][k]["fer"] for r in rows])) for k in all_k},
                err_counts={k: int(np.sum([r["arms"][k]["fer"] for r in rows])) for k in all_k},
                gmi={k: float(np.mean([r["arms"][k]["gmi"] for r in rows])) for k in all_k if "gmi" in rows[0]["arms"][k]},
                chan_nmse_db={k: float(np.mean([r["arms"][k]["nmse_db"] for r in rows])) for k in prac_k},
                erased_frac={k: float(np.mean([r["arms"][k]["erased_frac"] for r in rows])) for k in prac_k},
                tx_cp_energy_mean={k: float(np.mean([r["arms"][k]["tx_cp_energy"] for r in rows])) for k in prac_k},
                sinr_p10_db={k: float(np.mean([r["arms"][k]["sinr_p10_db"] for r in rows])) for k in all_k if "sinr_p10_db" in rows[0]["arms"][k]},
            )
            print(f"[64x8 11.5dB {ntype}] ({time.time()-tc:.1f}s) FER: "
                  f"AFDM_1It={cells[ntype]['fer']['EP_AFDM_MaskProj_1Iter']:.4f} ({cells[ntype]['err_counts']['EP_AFDM_MaskProj_1Iter']}/400), "
                  f"AFDM_0It={cells[ntype]['fer']['EP_AFDM_MaskProj_0Iter']:.4f}, "
                  f"PCP_OTFS={cells[ntype]['fer']['EP_OTFS_SF_PCP_MaskProj']:.4f} ({cells[ntype]['err_counts']['EP_OTFS_SF_PCP_MaskProj']}/400) | "
                  f"TrueH(unb->impMask): AFDM {cells[ntype]['fer']['TrueH_Unblanked_AFDM']:.4f}->{cells[ntype]['fer']['TrueH_SameImpMask_AFDM']:.4f}, "
                  f"OTFS {cells[ntype]['fer']['TrueH_Unblanked_OTFS']:.4f}->{cells[ntype]['fer']['TrueH_SameImpMask_OTFS']:.4f}", flush=True)

    rng_bs = np.random.default_rng(20261123)

    def prac_diff(ntype, opp, ref="EP_AFDM_MaskProj_1Iter"):
        rows = raw_by_reg[ntype]
        # positive = opponent has HIGHER FER than ref (AFDM wins!)
        return bootstrap_diff([r["arms"][opp]["fer"] for r in rows], [r["arms"][ref]["fer"] for r in rows], rng_bs)

    def excess_erase_diff(ntype, mask_kind="SameImpMask"):
        rows = raw_by_reg[ntype]
        # dFER_erase(OTFS) - dFER_erase(AFDM) on identical frames, true H_td, identical mask!
        d_ot = [r["arms"][f"TrueH_{mask_kind}_OTFS"]["fer"] - r["arms"]["TrueH_Unblanked_OTFS"]["fer"] for r in rows]
        d_af = [r["arms"][f"TrueH_{mask_kind}_AFDM"]["fer"] - r["arms"]["TrueH_Unblanked_AFDM"]["fer"] for r in rows]
        return bootstrap_diff(d_ot, d_af, rng_bs)

    opps = [
        "Comb_OFDM_MaskProj", "Spread_OTFS_MaskProj", "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj", "EP_AFDM_Unblanked", "EP_AFDM_NaiveZhidkov"
    ]
    prac_contrasts = {nt: {op: prac_diff(nt, op) for op in opps} for nt in ["bg", "mca"]}
    prac_0it_vs_pcp = {nt: prac_diff(nt, "EP_OTFS_SF_PCP_MaskProj", ref="EP_AFDM_MaskProj_0Iter") for nt in ["bg", "mca"]}
    attr_imp_mask = {nt: excess_erase_diff(nt, "SameImpMask") for nt in ["bg", "mca"]}
    attr_shared_blind = {nt: excess_erase_diff(nt, "SharedBlindMask") for nt in ["bg", "mca"]}

    # Exact integer error-count comparisons on n=400 (20 errors == exact 5.0 pp; immune to float rounding!)
    clean_err_gap = abs(cells["clean"]["err_counts"]["EP_AFDM_MaskProj_1Iter"] - cells["clean"]["err_counts"]["EP_OTFS_Imp_MaskProj"])
    pcp_err_diff = {
        nt: cells[nt]["err_counts"]["EP_OTFS_SF_PCP_MaskProj"] - cells[nt]["err_counts"]["EP_AFDM_MaskProj_1Iter"]
        for nt in ["bg", "mca"]
    }
    attr_err_diff = {
        nt: int(sum(
            (r["arms"]["TrueH_SameImpMask_OTFS"]["fer"] - r["arms"]["TrueH_Unblanked_OTFS"]["fer"])
            - (r["arms"]["TrueH_SameImpMask_AFDM"]["fer"] - r["arms"]["TrueH_Unblanked_AFDM"]["fer"])
            for r in raw_by_reg[nt]
        ))
        for nt in ["bg", "mca"]
    }
    g04_p1 = (
        clean_err_gap <= 20
        and all(cells[nt]["err_counts"][op] > cells[nt]["err_counts"]["EP_AFDM_MaskProj_1Iter"] for nt in ["bg", "mca"] for op in opps)
        and all(pcp_err_diff[nt] >= 20 for nt in ["bg", "mca"])
        and all(prac_contrasts[nt]["EP_OTFS_SF_PCP_MaskProj"]["ci95"][0] > 0.0 for nt in ["bg", "mca"])
    )
    g04_p2 = (
        all(attr_err_diff[nt] >= 20 for nt in ["bg", "mca"])
        and all(attr_imp_mask[nt]["ci95"][0] > 0.0 for nt in ["bg", "mca"])
    )

    verdicts = dict(
        G04_P1_blind_cp520_practical_advantage=bool(g04_p1),
        G04_P2_trueH_same_mask_data_attribution=bool(g04_p2),
        PASS_PRIMARY=bool(g04_p1 and g04_p2),
    )
    scope_readouts = dict(
        G04_S1_afdm0iter_beats_pcp=prac_0it_vs_pcp,
        G04_S2_trueH_shared_blind_mask_excess_fer=attr_shared_blind,
    )

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            card="I-20261123-g04",
            revision="Round 6 Step-7 controlled blind + true-H attribution slice",
            mixed_dev_seeds=[82900, 83020],
            test_seeds=[83100, 83500],
            grid="64x8",
            snr_db=11.5,
            cp_samples=8,
            total_samples=520,
            blind_zero_sigma2_zero_label=True,
            workers=workers,
            wall_seconds=round(time.time() - t0, 2),
        ),
        unified_blind_dev_selected=unified_blind_cfg,
        cells=cells,
        practical_contrasts_opp_minus_afdm1=prac_contrasts,
        trueH_same_imp_mask_excess_fer_otfs_minus_afdm=attr_imp_mask,
        scope_readouts=scope_readouts,
        verdicts=verdicts,
    )
    (out_p / "summary_g04_rev.json").write_text(json.dumps(summary, indent=2))
    print("DONE g04_rev verdicts:", json.dumps(verdicts), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "run"])
    ap.add_argument("--out", default="ideas/l2/out_g_r6_rev")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke()
    else:
        run_full(args.out, workers=args.workers)
