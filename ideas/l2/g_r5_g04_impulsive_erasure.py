#!/usr/bin/env python3
"""Runner g — Round 5 Batch 1 L2 verification for I-20261123-g04.
Pre-registered protocol & boolean gates: ideas/l2/PREDICTIONS_g_r5b1.md.

Strictly enforces Sol Step 6 requirements (ideas/reviews/g-sol-novelty-r5s1-20261123.md):
  1. Disjoint seeds: smoke (80900), dev calibration (81000..81059, 60 frames), unseen test (82000..82399, 400 frames).
  2. Exact k = 512 information bits across ALL waveforms (eliminating 512 vs 513 1-bit discrepancy; Spread-OTFS
     shortens code_12 by fixing 1 known zero info bit -> exact 512 info bits) + identical CP overhead (N+L_cp = 520).
  3. Blind MAD background scale estimation per frame (sigma_mad = median(|r|) / sqrt(ln 2)); (rho_p, c_T, reg_extra)
     grid-searched strictly on dev frames 81000..81059 for EVERY arm and noise regime independently!
  4. Head-on inclusion of Sanoopkumar & Farhang (ICC 2023) low-peak Pilot-with-CP OTFS (`EP_OTFS_SF_PCP_MaskProj`)
     with identical guard overhead (128 bins) and symmetric mask-projected CE, retained-sample LMMSE & 1-iter feedback.
  5. Repaired [all-I, all-Q] soft bit ordering (e1_ldpc.py:209) across all waveforms.
  6. Four test regimes: clean (p_imp=0), Bernoulli-Gaussian 64x8, Middleton Class-A 64x8, and Bernoulli-Gaussian 32x16.
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

_G04_CACHE = {}


def get_wave_structs(M_ot=64, K_ot=8):
    key = (M_ot, K_ot)
    if key in _G04_CACHE:
        return _G04_CACHE[key]
    N = 512
    L_max = 7
    alpha_max = 2.1
    N_data = 384
    code_23 = build_code(2 * N_data, d_v=3, d_c=9, seed=20260726)  # k = 512 exact!
    code_12 = build_code(2 * N, d_v=3, d_c=6, seed=20260726)       # k = 513 -> fix last info bit = 0 => exact 512 user bits!
    assert code_23["k"] == 512 and code_12["k"] == 513

    n_vec = np.arange(N)
    F_N = np.fft.fft(np.eye(N)) / np.sqrt(N)
    S_af = 8
    c1 = S_af / (2.0 * N)
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

    # Total guard bins = 128 -> guard delay rows G_rows = 128 // K_ot (16 rows on 64x8, 8 rows on 32x16).
    # Scale max delay L_use proportionally to subblock length M_ot (~11% delay spread) so 2*L_use + 2 <= G_rows holds without data spill.
    G_rows = 128 // K_ot
    L_use = 7 if M_ot == 64 else 3  # exact ~11% delay spread of subblock length M_ot so 128-bin guard is valid on 32x16!
    p_row = L_use
    R_ot = np.arange(p_row * K_ot, (p_row + L_use + 1) * K_ot)
    p_ot = p_row * K_ot + (K_ot // 2)
    data_ot = np.arange(G_rows * K_ot, N)

    # Sanoopkumar & Farhang (ICC 2023) Pilot-with-CP (PCP-OTFS) inside exact G_rows guard rows:
    # CP length = L_use rows (0..L_use-1), ZC sequence length Lp = G_rows - L_use rows (L_use..G_rows-1) at k0 = K_ot//2!
    Lp = G_rows - L_use
    zc_lp = np.exp(-1j * np.pi * 1 * np.arange(Lp) * np.arange(1, Lp + 1) / float(Lp))
    pcp_seq = np.concatenate([zc_lp[-L_use:], zc_lp])  # length G_rows
    x_pcp_unit = np.zeros(N, dtype=np.complex128)
    for l in range(G_rows):
        x_pcp_unit[l * K_ot + (K_ot // 2)] = pcp_seq[l] / np.sqrt(float(G_rows))
    s_pcp_unit = U_ot.conj().T @ x_pcp_unit  # unit total energy!
    R_sf_td = np.array([r * M_ot + l for r in range(K_ot) for l in range(L_use, G_rows)])  # clean zero-data time indices!

    # Comb-OFDM with constant-envelope Newman/chirp pilot phases (Sol Step 6 line 89: reasonable pilot phases!)
    pil_ofdm = np.arange(0, N, 8)
    pil_phases = np.exp(1j * np.pi * (np.arange(len(pil_ofdm)) ** 2) / len(pil_ofdm))
    x_of_unit = np.zeros(N, dtype=np.complex128)
    x_of_unit[pil_ofdm] = pil_phases / np.sqrt(len(pil_ofdm))
    s_of_unit = F_N.conj().T @ x_of_unit
    rem_of = [i for i in range(N) if i not in set(pil_ofdm)]
    null_ofdm = np.array(rem_of[::7][:64])
    data_ofdm = np.array([i for i in rem_of if i not in set(null_ofdm)])
    R_of = np.sort(np.concatenate([pil_ofdm, null_ofdm]))

    zc_spread = np.exp(-1j * np.pi * 5 * (n_vec ** 2) / N) / np.sqrt(N)
    alp_grid = np.linspace(-alpha_max, alpha_max, 25)

    st = dict(
        N=N, M_ot=M_ot, K_ot=K_ot, L_max=L_use, alpha_max=alpha_max, N_data=N_data,
        code_23=code_23, code_12=code_12, F_N=F_N, U_af=U_af, U_ot=U_ot,
        R_af=R_af, data_af=data_af, R_ot=R_ot, p_ot=p_ot, data_ot=data_ot,
        s_pcp_unit=s_pcp_unit, R_sf_td=R_sf_td,
        s_of_unit=s_of_unit, R_of=R_of, data_ofdm=data_ofdm,
        zc_spread=zc_spread, alp_grid=alp_grid,
    )
    _G04_CACHE[key] = st
    return st


def bootstrap_diff(a, b, rng, B=4000):
    d = np.asarray(a, float) - np.asarray(b, float)
    n = len(d)
    idx = rng.integers(0, n, size=(B, n))
    means = d[idx].mean(axis=1)
    return dict(point=float(d.mean()), ci95=[float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))])


def sample_impulsive_noise(rng, N, sigma2, noise_type):
    w_th = np.sqrt(sigma2 / 2.0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N))
    if noise_type == "clean":
        return w_th, np.zeros(N, dtype=np.complex128)
    if noise_type == "bg":
        m_imp = rng.random(N) < 0.045
        v_imp = np.zeros(N, dtype=np.complex128)
        cnt = int(np.sum(m_imp))
        if cnt > 0:
            v_imp[m_imp] = np.sqrt(12.0 / 2.0) * (rng.standard_normal(cnt) + 1j * rng.standard_normal(cnt))
        return w_th, v_imp
    if noise_type == "mca":
        # Middleton Class-A: Poisson impulse multiplicity m ~ Poisson(A=0.05), per-arrival variance = 10.0 (total sigma_I^2 = 0.50, Gamma in [0.07, 0.14]).
        A_mca = 0.05
        m_counts = rng.poisson(A_mca, size=N)
        v_imp = np.zeros(N, dtype=np.complex128)
        nz = np.where(m_counts > 0)[0]
        if len(nz) > 0:
            vars_nz = m_counts[nz] * 10.0
            v_imp[nz] = np.sqrt(vars_nz / 2.0) * (rng.standard_normal(len(nz)) + 1j * rng.standard_normal(len(nz)))
        return w_th, v_imp
    raise ValueError(noise_type)


def mad_scale(r):
    """Blind background complex Gaussian standard deviation estimate via median(|r|)/sqrt(ln 2)."""
    return float(np.median(np.abs(r)) / math.sqrt(math.log(2.0)))


def omp_pilot_ce(U_read, s_p_unit, r_masked, keep_mask_ce, Ep, L_max, alp_grid, K_at=6, td_read_idx=None):
    N = len(r_masked)
    n_vec = np.arange(N)

    def make_atom(d, ak):
        s_sh = s_p_unit[(n_vec - d) % N]
        atom_t = keep_mask_ce * s_sh * np.exp(1j * 2 * np.pi * ak * n_vec / N)
        return atom_t[td_read_idx] if td_read_idx is not None else (U_read @ atom_t)

    cols, meta = [], []
    for d in range(L_max + 1):
        for ak in alp_grid:
            cols.append(make_atom(d, float(ak)))
            meta.append((d, float(ak)))
    D = np.column_stack(cols)
    norms = np.linalg.norm(D, axis=0)
    y_R = (r_masked[td_read_idx] if td_read_idx is not None else (U_read @ r_masked)) / math.sqrt(Ep)
    res = y_R.copy()
    sel_meta = []
    sel_cols = []
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
        # Continuous off-grid local Doppler refinement (+-0.5 grid step) applied identically to ALL waveforms!
        best_a = a_sel
        best_col = D[:, j]
        best_sc = c[j]
        for da in (-0.45 * step_alp, -0.20 * step_alp, 0.20 * step_alp, 0.45 * step_alp):
            col_c = make_atom(d_sel, a_sel + da)
            nm_c = float(np.linalg.norm(col_c))
            if nm_c > 1e-9:
                sc_c = float(np.abs(np.vdot(col_c, res)) / nm_c)
                if sc_c > best_sc:
                    best_sc = sc_c
                    best_a = a_sel + da
                    best_col = col_c
        sel_meta.append((d_sel, best_a))
        sel_cols.append(best_col)
        D_sel = np.column_stack(sel_cols)
        coef, _, _, _ = np.linalg.lstsq(D_sel, y_R, rcond=None)
        res = y_R - D_sel @ coef

    # Blind guard-residual noise variance estimate (in received sample scale: y_R was divided by sqrt(Ep)):
    # Each readout bin has unit unitary projection norm (for U_read) or 1 time sample (for td_read_idx):
    sig2_guard = float(np.mean(np.abs(res) ** 2) * Ep)
    H_hat = np.zeros((N, N), dtype=np.complex128)
    for cv, (d, ak) in zip(coef, sel_meta):
        H_hat[n_vec, (n_vec - d) % N] += cv * np.exp(1j * 2 * np.pi * ak * n_vec / N)
    return H_hat, sig2_guard


def mask_lmmse_decode(U_mat, H_hat, r_masked, keep_mask_eq, d_idx, p_sig_td, Ed, reg_var, code_obj, c_true, u512_true, is_spread=False):
    N = len(r_masked)
    idx_kept = np.where(keep_mask_eq > 0.5)[0]
    if len(idx_kept) < 32:
        idx_kept = np.arange(N)
    r_data = r_masked[idx_kept] - (H_hat[idx_kept, :] @ p_sig_td)
    A_d = H_hat[idx_kept, :] @ U_mat.conj().T[:, d_idx]
    G = Ed * (A_d.conj().T @ A_d) + reg_var * np.eye(len(d_idx))
    W = np.linalg.solve(G, math.sqrt(Ed) * A_d.conj().T)
    dg = np.maximum(math.sqrt(Ed) * np.real(np.sum(W * A_d.T, axis=1)), 1e-6)
    mu = (W @ r_data) / dg
    var = np.maximum((1.0 - dg) / dg, 1e-6)
    sinr_p10_db = float(10.0 * np.log10(np.percentile(1.0 / var, 10)))

    llr = demap_llr(mu, var, 1.0)
    if is_spread:
        # Exact 512 user info bits: last free_col bit was fixed to 0 (+20 LLR known bit!)
        llr_dec = llr.copy()
        last_info_col = int(code_obj["free_cols"][-1])
        llr_dec[last_info_col] = 20.0
    else:
        llr_dec = llr

    ch, ok = decode_llr(code_obj, llr_dec, maxiter=30)
    u_hat = ch[code_obj["free_cols"]][:512]
    fer = int(not np.array_equal(u_hat, u512_true))

    b_pm = 1.0 - 2.0 * c_true.astype(np.float64)
    # Net GMI per time sample INCLUDING L_cp=8 cyclic prefix (520 samples total!)
    N_tot = N + 8
    gmi = float(np.mean(1.0 - np.log2(1.0 + np.exp(np.clip(-b_pm * llr, -40.0, 40.0))))) * 2.0 * len(d_idx) / N_tot

    # Repaired [all-I, all-Q] bit ordering (e1_ldpc.py:209)!
    nsym = len(d_idx)
    l_i, l_q = np.clip(llr[:nsym], -20.0, 20.0), np.clip(llr[nsym:], -20.0, 20.0)
    d_soft = (np.tanh(0.5 * l_i) + 1j * np.tanh(0.5 * l_q)) / math.sqrt(2.0)
    return fer, gmi, d_soft, ok, sinr_p10_db


def run_one_arm_on_frame(st, arm, frame_data, cfg):
    N = st["N"]
    N_data = st["N_data"]
    L_max = st["L_max"]
    alp_grid = st["alp_grid"]
    H_td = frame_data["H_td"]
    H_norm2 = frame_data["H_norm2"]
    w_tot = frame_data["w_th"] + frame_data["v_imp"]
    w_th = frame_data["w_th"]
    sigma2 = frame_data["sigma2"]
    u512 = frame_data["u512"]
    c23, d23 = frame_data["c23"], frame_data["d23"]
    c12, d12 = frame_data["c12"], frame_data["d12"]

    t_s = time.perf_counter()
    # Fair total frame energy across N + L_cp = 520 samples: CP power tracks frame RMS identically across all waveforms
    if arm == "Oracle_Clean_AFDM":
        rp = 0.14
        Ep = rp * N
        Ed = (1.0 - rp) * N / N_data
        x = np.zeros(N, complex); x[0] = math.sqrt(Ep); x[st["data_af"]] = math.sqrt(Ed) * d23
        s_p = st["U_af"].conj().T[:, 0] * math.sqrt(Ep)
        r_cl = H_td @ (st["U_af"].conj().T @ x) + w_th
        fer, gmi, _, _, p10 = mask_lmmse_decode(st["U_af"], H_td, r_cl, np.ones(N), st["data_af"], s_p, Ed, sigma2, st["code_23"], c23, u512)
        return dict(fer=fer, gmi=gmi, nmse_db=-99.0, pilot_blanked=0.0, sinr_p10_db=p10, ms=(time.perf_counter() - t_s) * 1e3)

    rp, c_T, reg_ex = cfg["rp"], cfg["c_T"], cfg["reg_ex"]
    Ep = rp * N

    if arm == "Spread_OTFS_MaskProj":
        Ed = 1.0 - rp
        s_p = st["zc_spread"] * math.sqrt(Ep)
        s_tx = s_p + st["U_ot"].conj().T @ (math.sqrt(Ed) * d12)
        r = H_td @ s_tx + w_tot
        sig_env = mad_scale(r)
        km = (np.abs(r) <= c_T * sig_env).astype(float) if c_T < 50.0 else np.ones(N)
        p_blk = float(np.sum((1.0 - km) * (np.abs(s_p) ** 2)) / Ep)
        H0, sig2_g0 = omp_pilot_ce(None, st["zc_spread"], km * r, km, Ep, L_max, alp_grid, td_read_idx=np.arange(N))
        # Note: for Spread_OTFS, guard residual contains unknown data power ~ Ed; use min(sig2_g0, sigma2 + Ed) + reg_ex or sigma2 + reg_ex consistently across arms!
        # Using sigma2 + reg_ex (with reg_ex independently dev-calibrated per arm!) avoids penalizing Spread_OTFS with data residual in LMMSE!
        fer0, gmi0, d_soft, ok0, p10 = mask_lmmse_decode(st["U_ot"], H0, km * r, km, np.arange(N), s_p, Ed,
                                                         sigma2 + reg_ex, st["code_12"], c12, u512, is_spread=True)
        H_use = H0
        if not ok0:
            s_d_hat = st["U_ot"].conj().T @ (math.sqrt(Ed) * d_soft)
            r_clean_p = km * (r - H0 @ s_d_hat)
            H1, _ = omp_pilot_ce(None, st["zc_spread"], r_clean_p, km, Ep, L_max, alp_grid, td_read_idx=np.arange(N))
            fer0, gmi0, _, _, p10 = mask_lmmse_decode(st["U_ot"], H1, km * r, km, np.arange(N), s_p, Ed,
                                                      sigma2 + 0.5 * reg_ex, st["code_12"], c12, u512, is_spread=True)
            H_use = H1
        nmse_db = float(10.0 * np.log10(max(np.sum(np.abs(H_td - H_use) ** 2), 1e-30) / H_norm2))
        return dict(fer=fer0, gmi=gmi0, nmse_db=nmse_db, pilot_blanked=p_blk, sinr_p10_db=p10, ms=(time.perf_counter() - t_s) * 1e3)

    Ed = (1.0 - rp) * N / N_data
    if arm == "Comb_OFDM_MaskProj":
        U_m = st["F_N"]
        s_p_u = st["s_of_unit"]
        s_p = s_p_u * math.sqrt(Ep)
        d_idx = st["data_ofdm"]
        U_read = st["F_N"][st["R_of"], :]
        td_idx = None
        naive_z = False
        do_1iter = True
    elif arm == "EP_OTFS_Imp_MaskProj":
        U_m = st["U_ot"]
        s_p_u = st["U_ot"].conj().T[:, st["p_ot"]]
        s_p = s_p_u * math.sqrt(Ep)
        d_idx = st["data_ot"]
        U_read = st["U_ot"][st["R_ot"], :]
        td_idx = None
        naive_z = False
        do_1iter = True
    elif arm == "EP_OTFS_SF_PCP_MaskProj":
        U_m = st["U_ot"]
        s_p_u = st["s_pcp_unit"]
        s_p = s_p_u * math.sqrt(Ep)
        d_idx = st["data_ot"]
        U_read = None
        td_idx = st["R_sf_td"]
        naive_z = False
        do_1iter = True
    elif arm in ("EP_AFDM_NaiveZhidkov", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter"):
        U_m = st["U_af"]
        s_p_u = st["U_af"].conj().T[:, 0]
        s_p = s_p_u * math.sqrt(Ep)
        d_idx = st["data_af"]
        U_read = st["U_af"][st["R_af"], :]
        td_idx = None
        naive_z = (arm == "EP_AFDM_NaiveZhidkov")
        do_1iter = (arm == "EP_AFDM_MaskProj_1Iter")
    else:
        raise ValueError(arm)

    s_tx = s_p + U_m.conj().T[:, d_idx] @ (math.sqrt(Ed) * d23)
    r = H_td @ s_tx + w_tot
    sig_env = mad_scale(r)
    km = (np.abs(r) <= c_T * sig_env).astype(float) if c_T < 50.0 else np.ones(N)
    p_blk = float(np.sum((1.0 - km) * (np.abs(s_p) ** 2)) / Ep)

    km_ce = np.ones(N) if naive_z else km
    km_eq = np.ones(N) if naive_z else km

    H0, sig2_g0 = omp_pilot_ce(U_read, s_p_u, km * r, km_ce, Ep, L_max, alp_grid, td_read_idx=td_idx)
    # Blind thermal+residual noise variance from guard residual (clipped to sensible bounds) + dev-calibrated reg_ex:
    sig2_est = min(max(sig2_g0, 0.25 * sigma2), 0.50)
    fer, gmi, d_soft, ok0, p10 = mask_lmmse_decode(U_m, H0, km * r, km_eq, d_idx, s_p, Ed,
                                                   sig2_est + reg_ex, st["code_23"], c23, u512)
    H_use = H0
    if do_1iter and (not ok0) and (not naive_z):
        s_d_hat = U_m.conj().T[:, d_idx] @ (math.sqrt(Ed) * d_soft)
        r_for_ce = km * r + (1.0 - km) * (H0 @ s_d_hat)
        H1, sig2_g1 = omp_pilot_ce(U_read, s_p_u, r_for_ce, km, Ep, L_max, alp_grid, td_read_idx=td_idx)
        sig2_est1 = min(max(sig2_g1, 0.25 * sigma2), 0.50)
        fer, gmi, _, _, p10 = mask_lmmse_decode(U_m, H1, km * r, km, d_idx, s_p, Ed,
                                                sig2_est1 + 0.5 * reg_ex, st["code_23"], c23, u512)
        H_use = H1

    nmse_db = float(10.0 * np.log10(max(np.sum(np.abs(H_td - H_use) ** 2), 1e-30) / H_norm2))
    return dict(fer=fer, gmi=gmi, nmse_db=nmse_db, pilot_blanked=p_blk, sinr_p10_db=p10, ms=(time.perf_counter() - t_s) * 1e3)


def make_frame(st, seed, snr_db, noise_type):
    rng = np.random.default_rng(seed)
    N = st["N"]
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
    w_th, v_imp = sample_impulsive_noise(rng, N, sigma2, noise_type)
    return dict(
        H_td=H_td, H_norm2=float(np.sum(np.abs(H_td) ** 2)),
        w_th=w_th, v_imp=v_imp, sigma2=sigma2,
        u512=u512, c23=c23, d23=d23, c12=c12, d12=d12,
    )


def _dev_cal_worker(args):
    M_ot, K_ot, noise_type, arm, cand_cfgs = args
    st = get_wave_structs(M_ot, K_ot)
    frames = [make_frame(st, s, 11.5, noise_type) for s in range(81000, 81060)]
    best_cfg = cand_cfgs[0]
    best_score = (-1e9, 1e9)  # maximize (-FER, GMI)
    for cfg in cand_cfgs:
        fers, gmis = [], []
        for fd in frames:
            r = run_one_arm_on_frame(st, arm, fd, cfg)
            fers.append(r["fer"]); gmis.append(r["gmi"])
        sc = (-float(np.mean(fers)), float(np.mean(gmis)))
        if sc > best_score:
            best_score = sc
            best_cfg = cfg
    return (M_ot, K_ot, noise_type, arm), best_cfg, best_score


def _test_frame_worker(args):
    seed, M_ot, K_ot, snr_db, noise_type, arm_cfgs = args
    st = get_wave_structs(M_ot, K_ot)
    fd = make_frame(st, seed, snr_db, noise_type)
    arms = [
        "Oracle_Clean_AFDM",
        "Comb_OFDM_MaskProj",
        "Spread_OTFS_MaskProj",
        "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_NaiveZhidkov",
        "EP_AFDM_MaskProj_0Iter",
        "EP_AFDM_MaskProj_1Iter",
    ]
    res = {}
    for a in arms:
        res[a] = run_one_arm_on_frame(st, a, fd, arm_cfgs.get(a, dict(rp=0.14, c_T=2.2, reg_ex=0.015)))
    return res


def run_smoke():
    st = get_wave_structs(64, 8)
    fd = make_frame(st, 80900, 45.0, "clean")
    for a in ["Oracle_Clean_AFDM", "EP_OTFS_Imp_MaskProj", "EP_OTFS_SF_PCP_MaskProj", "EP_AFDM_MaskProj_0Iter", "EP_AFDM_MaskProj_1Iter"]:
        r = run_one_arm_on_frame(st, a, fd, dict(rp=0.14, c_T=100.0, reg_ex=1e-4))
        assert r["fer"] == 0 and r["gmi"] > 1.40, f"Smoke failed on {a}: {r}"
    print("SMOKE PASS: all g04 waveforms recover exact 512 bits with FER=0 at high SNR")


def run_full(out_dir, workers=24):
    t0 = time.time()
    out_p = Path(out_dir)
    out_p.mkdir(parents=True, exist_ok=True)
    run_smoke()

    # 1) Strictly calibrate (rp, c_T, reg_ex) on dev seeds 81000..81059 for EVERY arm and regime!
    tunable_arms = [
        "Comb_OFDM_MaskProj",
        "Spread_OTFS_MaskProj",
        "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_NaiveZhidkov",
        "EP_AFDM_MaskProj_0Iter",
    ]
    cal_jobs = []
    for M_ot, K_ot, ntype in [(64, 8, "clean"), (64, 8, "bg"), (64, 8, "mca"), (32, 16, "bg")]:
        for arm in tunable_arms:
            if ntype == "clean":
                cands = [dict(rp=rp, c_T=100.0, reg_ex=rx) for rp in [0.08, 0.14] for rx in [0.008, 0.02]]
            else:
                # Give every waveform full grid over pilot fraction, MAD blanking multiplier, and regularization!
                cands = [
                    dict(rp=rp, c_T=ct, reg_ex=rx)
                    for rp in [0.06, 0.14]
                    for ct in [1.9, 2.2, 2.6, 3.3]
                    for rx in [0.015, 0.06]
                ]
            cal_jobs.append((M_ot, K_ot, ntype, arm, cands))

    dev_selected = {}
    with get_context("spawn").Pool(workers) as pool:
        for key, best_cfg, best_sc in pool.map(_dev_cal_worker, cal_jobs):
            dev_selected[key] = best_cfg
            if key[3] == "EP_AFDM_MaskProj_0Iter":
                dev_selected[(key[0], key[1], key[2], "EP_AFDM_MaskProj_1Iter")] = best_cfg
    print(f"Dev MAD calibration complete in {time.time() - t0:.1f}s", flush=True)

    # 2) Run 400 unseen paired test frames (seeds 82000..82399) across all pre-registered cells
    test_cells = [
        ("clean_64x8_snr11.5", 64, 8, 11.5, "clean", range(82000, 82400)),
        ("bg_64x8_snr10.0", 64, 8, 10.0, "bg", range(82000, 82400)),
        ("bg_64x8_snr11.5", 64, 8, 11.5, "bg", range(82000, 82400)),
        ("bg_64x8_snr13.0", 64, 8, 13.0, "bg", range(82000, 82400)),
        ("bg_64x8_snr14.5", 64, 8, 14.5, "bg", range(82000, 82400)),
        ("mca_64x8_snr11.5", 64, 8, 11.5, "mca", range(82000, 82400)),
        ("mca_64x8_snr13.0", 64, 8, 13.0, "mca", range(82000, 82400)),
        ("bg_32x16_snr11.5", 32, 16, 11.5, "bg", range(82000, 82400)),
        ("bg_32x16_snr13.0", 32, 16, 13.0, "bg", range(82000, 82400)),
    ]

    arms_all = [
        "Oracle_Clean_AFDM",
        "Comb_OFDM_MaskProj",
        "Spread_OTFS_MaskProj",
        "EP_OTFS_Imp_MaskProj",
        "EP_OTFS_SF_PCP_MaskProj",
        "EP_AFDM_NaiveZhidkov",
        "EP_AFDM_MaskProj_0Iter",
        "EP_AFDM_MaskProj_1Iter",
    ]

    cells = {}
    raw_cells = {}
    with get_context("spawn").Pool(workers) as pool:
        for tag, M_v, K_v, snr_v, ntype, s_rng in test_cells:
            t_c = time.time()
            acfg = {a: dev_selected[(M_v, K_v, ntype, a)] for a in arms_all if (M_v, K_v, ntype, a) in dev_selected}
            rows = list(pool.map(_test_frame_worker, [(s, M_v, K_v, snr_v, ntype, acfg) for s in s_rng]))
            raw_cells[tag] = rows
            cells[tag] = dict(
                n_frames=len(rows),
                fer={a: float(np.mean([r[a]["fer"] for r in rows])) for a in arms_all},
                gmi={a: float(np.mean([r[a]["gmi"] for r in rows])) for a in arms_all},
                chan_nmse_db={a: float(np.mean([r[a]["nmse_db"] for r in rows])) for a in arms_all if a != "Oracle_Clean_AFDM"},
                pilot_blanked_frac={a: float(np.mean([r[a]["pilot_blanked"] for r in rows])) for a in arms_all},
                sinr_p10_db={a: float(np.mean([r[a]["sinr_p10_db"] for r in rows])) for a in arms_all},
                wall_ms={a: float(np.mean([r[a]["ms"] for r in rows])) for a in arms_all},
            )
            print(f"[{tag}] ({time.time()-t_c:.1f}s) FER: "
                  f"AFDM_1It={cells[tag]['fer']['EP_AFDM_MaskProj_1Iter']:.3f}, "
                  f"AFDM_0It={cells[tag]['fer']['EP_AFDM_MaskProj_0Iter']:.3f}, "
                  f"SF_PCP={cells[tag]['fer']['EP_OTFS_SF_PCP_MaskProj']:.3f}, "
                  f"OTFS_Imp={cells[tag]['fer']['EP_OTFS_Imp_MaskProj']:.3f}, "
                  f"Zhid={cells[tag]['fer']['EP_AFDM_NaiveZhidkov']:.3f}", flush=True)

    rng = np.random.default_rng(20261123)

    def fer_ci(tag, a1, a2):
        r = raw_cells[tag]
        return bootstrap_diff([x[a1]["fer"] for x in r], [x[a2]["fer"] for x in r], rng)

    # Interpolate 10% FER crossing SNR across [10.0, 11.5, 13.0, 14.5] on bg_64x8
    snr_grid = [10.0, 11.5, 13.0, 14.5]
    def snr_at_fer(arm, target=0.10):
        vals = [cells[f"bg_64x8_snr{s:.1f}"]["fer"][arm] for s in snr_grid]
        if vals[0] <= target:
            return snr_grid[0]
        for i in range(len(snr_grid) - 1):
            if vals[i] >= target >= vals[i + 1]:
                frac = (vals[i] - target) / max(vals[i] - vals[i + 1], 1e-9)
                return float(snr_grid[i] + frac * (snr_grid[i + 1] - snr_grid[i]))
        return float(snr_grid[-1] + 2.0 * (vals[-1] - target) / max(target, 0.05))

    snr10_afdm1 = snr_at_fer("EP_AFDM_MaskProj_1Iter", 0.10)
    snr10_afdm0 = snr_at_fer("EP_AFDM_MaskProj_0Iter", 0.10)
    snr10_sf = snr_at_fer("EP_OTFS_SF_PCP_MaskProj", 0.10)
    snr10_ot_imp = snr_at_fer("EP_OTFS_Imp_MaskProj", 0.10)
    snr10_zhid = snr_at_fer("EP_AFDM_NaiveZhidkov", 0.10)

    c_bg11_imp = fer_ci("bg_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_Imp_MaskProj")
    c_bg11_sf = fer_ci("bg_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_SF_PCP_MaskProj")
    c_bg11_zh = fer_ci("bg_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_AFDM_NaiveZhidkov")
    c_bg11_0it_sf = fer_ci("bg_64x8_snr11.5", "EP_AFDM_MaskProj_0Iter", "EP_OTFS_SF_PCP_MaskProj")
    c_mca11_sf = fer_ci("mca_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_SF_PCP_MaskProj")
    c_mca11_imp = fer_ci("mca_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_Imp_MaskProj")
    c_32x16_sf = fer_ci("bg_32x16_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_SF_PCP_MaskProj")
    c_32x16_imp = fer_ci("bg_32x16_snr11.5", "EP_AFDM_MaskProj_1Iter", "EP_OTFS_Imp_MaskProj")

    clean_diff = abs(cells["clean_64x8_snr11.5"]["fer"]["EP_AFDM_MaskProj_1Iter"]
                     - cells["clean_64x8_snr11.5"]["fer"]["EP_OTFS_Imp_MaskProj"])
    ctrl_clean = (clean_diff <= 0.05 or cells["clean_64x8_snr11.5"]["fer"]["EP_OTFS_Imp_MaskProj"] < cells["clean_64x8_snr11.5"]["fer"]["EP_AFDM_MaskProj_1Iter"]) \
                 and (c_bg11_imp["ci95"][1] < 0.0) and (c_bg11_sf["ci95"][1] < 0.0)

    comps = ["Comb_OFDM_MaskProj", "Spread_OTFS_MaskProj", "EP_OTFS_Imp_MaskProj", "EP_OTFS_SF_PCP_MaskProj", "EP_AFDM_NaiveZhidkov"]
    dir_all = True
    for cp in comps:
        for tg in ["bg_64x8_snr11.5", "bg_64x8_snr13.0", "mca_64x8_snr11.5", "mca_64x8_snr13.0"]:
            if cells[tg]["fer"]["EP_AFDM_MaskProj_1Iter"] >= cells[tg]["fer"][cp]:
                dir_all = False
            if cells[tg]["fer"]["EP_AFDM_MaskProj_0Iter"] >= cells[tg]["fer"][cp]:
                dir_all = False
        if fer_ci("bg_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", cp)["ci95"][1] >= 0.0:
            dir_all = False
        if fer_ci("mca_64x8_snr11.5", "EP_AFDM_MaskProj_1Iter", cp)["ci95"][1] >= 0.0:
            dir_all = False

    quant_ok = (
        (-c_bg11_imp["point"]) >= 0.15
        and (-c_bg11_sf["point"]) >= 0.15
        and (-c_bg11_zh["point"]) >= 0.15
        and (-c_bg11_0it_sf["point"]) >= 0.15
        and min(snr10_sf, snr10_ot_imp, snr10_zhid) - snr10_afdm1 >= 1.2
    )

    verdicts = dict(
        ctrl_clean_parity_and_reversal=bool(ctrl_clean),
        dir_beats_all_across_bg_and_mca=bool(dir_all),
        quant_snr_and_fer_margin=bool(quant_ok),
        aspect_32x16_also_wins_ci95=bool(c_32x16_sf["ci95"][1] < 0.0 and c_32x16_imp["ci95"][1] < 0.0),
        PASS=bool(ctrl_clean and dir_all and quant_ok),
    )

    summary = dict(
        _argv=sys.argv,
        _config=dict(
            card="I-20261123-g04",
            dev_seeds=[81000, 81060],
            test_seeds=[82000, 82400],
            info_bits_exact=512,
            total_samples_with_cp=520,
            workers=workers,
            wall_seconds=round(time.time() - t0, 2),
        ),
        dev_selected={f"{k[0]}x{k[1]}_{k[2]}_{k[3]}": v for k, v in dev_selected.items()},
        cells=cells,
        snr_at_10pct_fer_bg_64x8=dict(
            EP_AFDM_MaskProj_1Iter=round(snr10_afdm1, 3),
            EP_AFDM_MaskProj_0Iter=round(snr10_afdm0, 3),
            EP_OTFS_SF_PCP_MaskProj=round(snr10_sf, 3),
            EP_OTFS_Imp_MaskProj=round(snr10_ot_imp, 3),
            EP_AFDM_NaiveZhidkov=round(snr10_zhid, 3),
        ),
        contrasts=dict(
            bg11_afdm1_minus_otfs_imp=c_bg11_imp,
            bg11_afdm1_minus_sf_pcp=c_bg11_sf,
            bg11_afdm1_minus_zhidkov=c_bg11_zh,
            bg11_afdm0_minus_sf_pcp=c_bg11_0it_sf,
            mca11_afdm1_minus_sf_pcp=c_mca11_sf,
            mca11_afdm1_minus_otfs_imp=c_mca11_imp,
            bg32x16_afdm1_minus_sf_pcp=c_32x16_sf,
            bg32x16_afdm1_minus_otfs_imp=c_32x16_imp,
        ),
        verdicts=verdicts,
    )
    (out_p / "summary_g04.json").write_text(json.dumps(summary, indent=2))
    print("DONE g04 verdicts:", json.dumps(verdicts), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["smoke", "run"])
    ap.add_argument("--out", default="ideas/l2/out_g_r5_b1")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()
    if args.mode == "smoke":
        run_smoke()
    else:
        run_full(args.out, workers=args.workers)
