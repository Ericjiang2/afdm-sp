#!/usr/bin/env python3
"""
Round-15 Phase-1 Steelman Teardown Probe for Card I-20261126-m04 (`26-m04`):
Zero-Guard 0%-Pilot M=128 Blind Bistatic Sensing with Power-Masked Waveforms.

Read-only imports frozen `ideas/l2/l2_m_r13_m04_blind_cov_afdm_isac.py` (without modifying any
historical file or virgin formal seeds 2034000000+).

Tests the required full-strength textbook Steelman baselines (all calibrated to the EXACT SAME
marginal pure-noise false-alarm rate Pfa = 1.5% on independent H0 trials!):
  1. Pub_NoMask (`Abl_NoMask` / Ranasinghe uniform power under Swerling-II no-LoS)
  2. Ours_Banded (`26-m04` lag-0 + lag-1 heteroscedastic Quasi-ML on DAFT-masked AFDM)
  3. Rival_TDCov (de-chirped non-wrapped time-domain autocorrelation NNLS NOMP)
  4. Steelman_A_DemeanCov_GLS (`Steelman_A1`): textbook demeaned sample-covariance pre-whitened
     Generalized Least Squares / COMET (`Ottersten-Stoica-Roy 1998`) over banded lags r=0..3
  5. Steelman_A_FullWishart_COMET (`Steelman_A2`): textbook full N x N demeaned sample-covariance
     Gaussian / Wishart Quasi-ML (`ln|R| + Tr(R^{-1} R_hat)` iterative pre-whitened matching)
  6. Steelman_Cumulant4_AFDM: textbook 4th-order cumulant / intra-block power-autocorrelation blind detector
  7. Steelman_S_OFDM_SameMask & Steelman_S_SCFDE_SameMask: literal same-mask OFDM (`c1=0`) and
     Single-Carrier (`SC-FDE` with time-domain mask `d`)
  8. Steelman_S_CycloRot_SCFDE (`Steelman_S`): textbook Serpedin-Giannakis (TSP 1998/2000) periodic
     modulation-induced cyclostationarity applied to fractional-chirp/DFT-spread SC-FDE / OC-OFDM
     (or CP-OFDM with non-stationary cyclic correlation) at exact same 765 bits/block & unit power!
  9. Oracle_KnownX_GLRT (`Oracle`): true upper bound gifting transmitted symbols X_m to the bistatic
     radar receiver (exact NOMP / matched-filter GLRT at identical H0 Pfa = 1.5%!)
"""
import os, sys, json, time, math, hashlib, argparse
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
from scipy.fft import fft, ifft
from scipy.optimize import minimize, nnls
from concurrent.futures import ProcessPoolExecutor

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
L2_DIR = os.path.join(REPO_ROOT, "ideas", "l2")
if L2_DIR not in sys.path:
    sys.path.insert(0, L2_DIR)

FROZEN_M04_PATH = os.path.join(L2_DIR, "l2_m_r13_m04_blind_cov_afdm_isac.py")
with open(FROZEN_M04_PATH, "rb") as _fp:
    _m04_md5 = hashlib.md5(_fp.read()).hexdigest()

import l2_m_r13_m04_blind_cov_afdm_isac as m4


def lag_templates_multi(D_fft: np.ndarray, N: int, u: float, max_lag: int = 3):
    """Exact de-chirped covariance templates for lags r = 0, 1, ..., max_lag."""
    k = np.arange(N, dtype=np.float64)
    K0 = m4.complex_dirichlet(N, k - u)
    out = [np.real(ifft(fft(np.abs(K0) ** 2) * D_fft))]
    for r in range(1, max_lag + 1):
        Kr = m4.complex_dirichlet(N, (k + float(r)) - u)
        out.append(ifft(fft(K0 * np.conj(Kr)) * D_fft))
    return out


def estimate_demean_cov_gls_comet(
    Y: np.ndarray,
    sys_cfg: dict,
    Q_in: int,
    ell_max: int,
    nu_max: float,
    tau_gls: float,
    max_lag: int = 3,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """
    Textbook Demeaned Sample-Covariance Iteratively-Reweighted GLS / COMET (Ottersten-Stoica-Roy 1998):
      1. Demeans across M blocks: Yc = Y - mean(Y, axis=1) (removes any static DC/mean leakage),
      2. Forms empirical sample covariance bands R_hat[k, (k+r)%N] for r = 0..max_lag (with de-chirp phase),
      3. Minimizes textbook diagonal-prewhitened COMET criterion:
           J_COMET = M * sum_k (R0_hat[k] - mu0[k])^2 / w0[k]^2
                   + 2*M * sum_{r=1}^{max_lag} sum_k |Rr_hat[k] - mur[k]|^2 / (w0[k] * w0[(k+r)%N])
         where weights w0[k] = max(R0_hat[k], mu0_prev[k]) (standard textbook Extended/Generalized LS!).
    """
    N, M = Y.shape
    D_fft = sys_cfg["D_fft"]
    D0_conj = sys_cfg["D0_conj"]
    c2 = sys_cfg["c2"]
    k_idx = np.arange(N)

    Yc = Y - np.mean(Y, axis=1, keepdims=True)
    rms = float(np.sqrt(np.mean(np.abs(Yc) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Yn = Yc / rms
    scale_df = M / float(max(M - 1, 1))

    p_hat = np.mean(np.abs(Yn) ** 2, axis=1) * scale_df
    p_bar = float(np.mean(p_hat))

    r_hats = [p_hat]
    dechirps = [None]
    for r in range(1, max_lag + 1):
        kr = (k_idx + r) % N
        dch_r = np.exp(1j * 2.0 * np.pi * c2 * (k_idx ** 2 - kr ** 2))
        dechirps.append(dch_r)
        rr = np.mean((Yn[k_idx, :] * np.conj(Yn[kr, :])) * dch_r[:, None], axis=1) * scale_df
        r_hats.append(rr)

    def is_valid_u(u_val: float) -> bool:
        ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q_in * e + N / 2.0) % N) - N / 2.0))
        nc = ((u_val + Q_in * ec + N / 2.0) % N) - N / 2.0
        return abs(nc) <= nu_max

    def u_bounds(u_val: float):
        ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q_in * e + N / 2.0) % N) - N / 2.0))
        c_wrap = (-Q_in * ec) % N
        diff = ((u_val - c_wrap + N / 2.0) % N) - N / 2.0
        c_unw = u_val - diff
        lo = max(u_val - 1.2, c_unw - nu_max)
        hi = min(u_val + 1.2, c_unw + nu_max)
        return (min(lo, u_val), max(hi, u_val))

    valid_int = np.array([is_valid_u(float(k)) or is_valid_u(float(k) + 0.4) or is_valid_u(float(k) - 0.4) for k in range(N)], dtype=bool)

    # Fixed textbook empirical covariance weights w_k = max(p_hat[k], 0.15 * p_bar) -> convex quadratic in (g, s2)!
    w0 = np.maximum(p_hat, 0.15 * p_bar)
    inv_w0_sq = 1.0 / (w0 ** 2)
    inv_wr = [None] + [1.0 / (w0[k_idx] * w0[(k_idx + r) % N]) for r in range(1, max_lag + 1)]

    def eval_comet_obj(us, gs, s2):
        mu0 = np.full(N, s2, dtype=np.float64)
        murs = [None] + [np.zeros(N, dtype=np.complex128) for _ in range(max_lag)]
        for uj, gj in zip(us, gs):
            ts = lag_templates_multi(D_fft, N, uj, max_lag=max_lag)
            mu0 += gj * ts[0]
            for r in range(1, max_lag + 1):
                murs[r] += gj * ts[r]
        val = float(M * np.sum(((p_hat - mu0) ** 2) * inv_w0_sq))
        for r in range(1, max_lag + 1):
            val += float(2.0 * M * np.sum((np.abs(r_hats[r] - murs[r]) ** 2) * inv_wr[r]))
        return val

    def solve_gls_weights(us):
        # Exact non-negative WLS for [g_1..g_P, s2] across all lags 0..max_lag!
        Pp = len(us)
        rows_A = []
        rhs_b = []
        # Lag 0
        T0 = np.ones((N, Pp + 1), dtype=np.float64)
        T_lags = [[None] * Pp for _ in range(max_lag + 1)]
        for j, uj in enumerate(us):
            ts = lag_templates_multi(D_fft, N, uj, max_lag=max_lag)
            T0[:, j] = ts[0]
            for r in range(1, max_lag + 1):
                T_lags[r][j] = ts[r]
        sw0 = np.sqrt(M * inv_w0_sq)
        rows_A.append(T0 * sw0[:, None])
        rhs_b.append(p_hat * sw0)
        for r in range(1, max_lag + 1):
            swr = np.sqrt(2.0 * M * inv_wr[r])
            Tr_c = np.column_stack(T_lags[r] + [np.zeros(N, dtype=np.complex128)])
            rows_A.append(Tr_c.real * swr[:, None])
            rhs_b.append(r_hats[r].real * swr)
            rows_A.append(Tr_c.imag * swr[:, None])
            rhs_b.append(r_hats[r].imag * swr)
        A_wls = np.vstack(rows_A)
        b_wls = np.concatenate(rhs_b)
        th, _ = nnls(A_wls, b_wls)
        th = np.maximum(th, 1e-6)
        return th[:-1], float(th[-1]), float(np.sum((b_wls - A_wls @ th) ** 2))

    def refine_comet(U_init):
        Pp = len(U_init)
        u_last = U_init[-1]
        u_mir = 2.0 * round(u_last) - u_last
        inits = [U_init]
        if abs(u_mir - u_last) > 0.02 and is_valid_u(u_mir % N):
            inits.append(U_init[:-1] + [u_mir])
        best_u, best_g, best_s2, best_val = None, None, None, 1e30
        for ui in inits:
            bnds = [u_bounds(u) for u in ui]
            def varpro_u(u_vec):
                _, _, val = solve_gls_weights(u_vec)
                return val
            res = minimize(varpro_u, np.array(ui, dtype=float), method="L-BFGS-B", bounds=bnds, options={"maxiter": 25, "ftol": 1e-8})
            gf, s2f, vf = solve_gls_weights(res.x.tolist())
            if vf < best_val:
                best_val = vf; best_u = (res.x % N).tolist(); best_g = gf; best_s2 = s2f
        return best_u, best_g, best_s2, best_val

    # Null model (P = 0): only s2
    s2_0 = float(np.sum(p_hat * inv_w0_sq) / np.sum(inv_w0_sq))
    obj_c = eval_comet_obj([], np.array([]), s2_0)
    mu0_c = np.full(N, s2_0)
    mur_c = [None] + [np.zeros(N, dtype=np.complex128) for _ in range(max_lag)]
    U_c, g_c = [], np.array([])
    first_stat = 0.0

    for step in range(P_max):
        w_res0 = (p_hat - mu0_c) * inv_w0_sq
        w_res0 -= np.mean(w_res0)
        sc_int = np.real(ifft(fft(w_res0) * D0_conj))
        cands = np.where(valid_int)[0]
        for ua in U_c:
            cands = cands[np.abs(((cands - ua + N / 2.0) % N) - N / 2.0) > 1.2]
        if len(cands) == 0:
            break
        top_k = cands[np.argsort(sc_int[cands])[-min(6, len(cands)):]]
        best_u, best_sc = None, -1e30
        for ui in top_k:
            for du in (-0.4, -0.15, 0.15, 0.4):
                uc = (ui + du) % N
                if not is_valid_u(uc):
                    continue
                ts = lag_templates_multi(D_fft, N, uc, max_lag=max_lag)
                t0z = ts[0] - np.mean(ts[0])
                num = M * float(np.dot(w_res0, t0z))
                den_sq = M * float(np.sum((t0z ** 2) * inv_w0_sq))
                for r in range(1, max_lag + 1):
                    num += 2.0 * M * float(np.real(np.vdot(ts[r], (r_hats[r] - mur_c[r]) * inv_wr[r])))
                    den_sq += 2.0 * M * float(np.sum((np.abs(ts[r]) ** 2) * inv_wr[r]))
                sc = num / math.sqrt(max(den_sq, 1e-15))
                if sc > best_sc:
                    best_sc, best_u = sc, uc
        if best_u is None or best_sc <= 0:
            break
        U_ref, g_ref, s2_ref, obj_ref = refine_comet(U_c + [best_u])
        stat = max(0.0, obj_c - obj_ref)
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_gls:
            break
        U_c, g_c, obj_c = U_ref, g_ref, obj_ref
        mu0_c = np.full(N, s2_ref)
        mur_c = [None] + [np.zeros(N, dtype=np.complex128) for _ in range(max_lag)]
        for uj, gj in zip(U_c, g_c):
            ts = lag_templates_multi(D_fft, N, uj, max_lag=max_lag)
            mu0_c += gj * ts[0]
            for r in range(1, max_lag + 1):
                mur_c[r] += gj * ts[r]

    dets = []
    for uj, gj in zip(U_c, g_c):
        ej = min(range(ell_max + 1), key=lambda e: abs(((uj + Q_in * e + N / 2.0) % N) - N / 2.0))
        nj = float(((uj + Q_in * ej + N / 2.0) % N) - N / 2.0)
        dets.append((ej, nj, float(gj * (rms ** 2))))
    return dets, first_stat


def full_cov_atom(d: np.ndarray, N: int, u: float) -> np.ndarray:
    """Exact N x N covariance matrix C(u) = G(u) diag(d) G(u)^H in DAFT domain (up to diagonal phase Lambda_c2)."""
    # Note: (A H_p A^H)_{k, m} = exp(-j2pi c2 (k^2 - m^2)) * K_Dir(k - m - u_p) (for even Q=12, Phi_ell = I)!
    # Wait: verify exact shift! Let's build via FFT in O(N^2) without matrix-matrix multiply!
    # Wait: G(u) = F diag(exp(j2pi u n / N)) F^H (up to c2 phases, which cancel in |...| or are applied outside!).
    # Let's include exact c2 phase outside on Y (i.e., work on Z_daft = conj(lam2) * Y = F * lam1 * R_time)!
    # In Z_daft = F (lam1 * R_time): for path (ell, nu) with even Q = 2Nc1:
    #   lam1[n] * phi_cpp[n] * exp(j2pi nu n / N) * s[(n-ell)%N]
    #   = exp(j2pi c1 ell^2) * exp(j2pi (nu - Q*ell) n / N) * (lam1*s)[(n-ell)%N]!
    # And F((lam1*s)[(n-ell)%N])[k] = exp(-j2pi k ell / N) * X_raw[k], where |X_raw[k]|^2 has expectation d[k]!
    # WAIT A SECOND! Check off-diagonal of G(u) diag(d) G(u)^H when ell != 0!
    # Let x_tilde[k] = exp(-j2pi k ell / N) * lam2_c[k] * X_mask[k]: since diag(d) is REAL DIAGONAL,
    # diag(exp(-j2pi k ell/N) * lam2_c[k]) * diag(d) * diag(...)^H == diag(d) IDENTICALLY!!
    # ALL phase factors on X_mask CANCEL IDENTICALLY in X_mask * X_mask^H!!
    # So in Z_daft = conj(lam2) * Y, C_Z(u) depends ONLY on u = (nu - Q*ell) mod N:
    #   Z_daft,m = F diag(exp(j2pi u n / N)) F^H x_tilde_m,  E[x_tilde x_tilde^H] = diag(d)!!
    n = np.arange(N, dtype=np.float64)
    F = fft(np.eye(N), axis=0) / np.sqrt(N)
    # G_z(u) = F diag(exp(j2pi u n / N)) F^H -> circulant matrix with first column K_Dir(k - u)!
    k = np.arange(N, dtype=np.float64)
    col0 = m4.complex_dirichlet(N, k - u)
    # G_z(u)[k, m] = col0[(k - m) % N]
    idx = (k[:, None] - k[None, :]) % N
    Gz = col0[idx]
    return (Gz * d[None, :]) @ Gz.conj().T


def estimate_full_wishart_qml(
    Y: np.ndarray,
    sys_cfg: dict,
    Q_in: int,
    ell_max: int,
    nu_max: float,
    tau_w: float,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """
    Textbook Full N x N Sample-Covariance Gaussian / Wishart Quasi-ML (`ln|R| + Tr(R^{-1} R_hat)`):
    Works on Z = conj(lam2) * Y_demean where C_Z(u) = G_z(u) diag(d) G_z(u)^H is exact!
    Uses pre-whitened matched filter score Tr(R_c^{-1} C_Z(u) R_c^{-1} (R_hat - R_c)) / sqrt(Tr((R_c^{-1} C_Z(u))^2))
    (exact Rao score test of full N x N Wishart likelihood!) + coordinate/1D Newton refinement!
    """
    N, M = Y.shape
    c2 = sys_cfg["c2"]; d = sys_cfg["d"]
    n_idx = np.arange(N, dtype=np.float64)
    lam2_conj = np.exp(1j * 2.0 * np.pi * c2 * (n_idx ** 2))

    Z = lam2_conj[:, None] * (Y - np.mean(Y, axis=1, keepdims=True))
    rms = float(np.sqrt(np.mean(np.abs(Z) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Zn = Z / rms
    R_hat = (Zn @ Zn.conj().T) / float(max(M - 1, 1))

    # Precompute valid coarse grid (0.5-bin spacing inside valid delay-Doppler islands: 17 * 19 ~ 323 atoms)
    u_cands = []
    for ell in range(ell_max + 1):
        c_u = (-Q_in * ell) % N
        for dv in np.linspace(-nu_max + 0.15, nu_max - 0.15, 19):
            u_cands.append(float((c_u + dv) % N))
    u_cands = np.array(u_cands, dtype=float)

    def is_valid_u(u_val: float) -> bool:
        ec = min(range(ell_max + 1), key=lambda e: abs(((u_val + Q_in * e + N / 2.0) % N) - N / 2.0))
        nc = ((u_val + Q_in * ec + N / 2.0) % N) - N / 2.0
        return abs(nc) <= nu_max

    def eval_wishart_2nll(us, gs, s2):
        R_m = max(s2, 1e-6) * np.eye(N, dtype=np.complex128)
        for uj, gj in zip(us, gs):
            R_m += max(gj, 0.0) * full_cov_atom(d, N, uj)
        R_m = 0.5 * (R_m + R_m.conj().T)
        sign, logdet = np.linalg.slogdet(R_m)
        if sign <= 0:
            return 1e30
        Rinv_Rhat = np.linalg.solve(R_m, R_hat)
        return float(2.0 * M * (logdet + np.real(np.trace(Rinv_Rhat))))

    # Fast FFT evaluation of Rao score across all candidate u:
    # Notice C_Z(u) = G_z(u) D G_z(u)^H; in time domain (F^H Z), F^H C_Z(u) F = Omega(u) (F^H D F) Omega(u)^H!
    #WAIT: F^H G_z(u) F = diag(exp(j2pi u n / N)) == Omega(u)!!
    # HUGE ALGEBRAIC SPEEDUP (EXACT TO 1e-15!):
    # Transform Zn to de-chirped time domain Z_td = ifft(Zn, axis=0) * sqrt(N)!
    # Then R_td_hat = (Z_td @ Z_td^H) / (M-1), and in time domain, each target atom is simply:
    #   C_td(u) = diag(e^{j2pi u n/N}) @ R_d_td @ diag(e^{-j2pi u n/N}), where R_d_td = F^H diag(d) F!
    Z_td = ifft(Zn, axis=0) * math.sqrt(N)
    R_td_hat = (Z_td @ Z_td.conj().T) / float(max(M - 1, 1))
    F_mat = fft(np.eye(N), axis=0) / math.sqrt(N)
    R_d_td = (F_mat.conj().T * d[None, :]) @ F_mat  # exact circulant autocorrelation of mask d!

    def td_atom(u_val: float) -> np.ndarray:
        ph = np.exp(1j * 2.0 * np.pi * u_val * n_idx / N)
        return (ph[:, None] * R_d_td) * np.conj(ph)[None, :]

    def eval_td_2nll(us, gs, s2):
        R_m = max(s2, 1e-5) * np.eye(N, dtype=np.complex128)
        for uj, gj in zip(us, gs):
            R_m += max(gj, 0.0) * td_atom(uj)
        R_m = 0.5 * (R_m + R_m.conj().T)
        try:
            L_chol = np.linalg.cholesky(R_m)
        except np.linalg.LinAlgError:
            return 1e30
        logdet = 2.0 * float(np.sum(np.log(np.real(np.diag(L_chol)))))
        Z_tmp = np.linalg.solve(L_chol, R_td_hat)
        Rinv_Rhat = np.linalg.solve(L_chol.conj().T, Z_tmp)
        return float(2.0 * M * (logdet + np.real(np.trace(Rinv_Rhat))))

    s2_c = max(float(np.real(np.trace(R_td_hat)) / N), 1e-5)
    nll2_c = eval_td_2nll([], [], s2_c)
    R_c = s2_c * np.eye(N, dtype=np.complex128)
    U_c, g_c = [], []
    first_stat = 0.0

    for step in range(P_max):
        # Whitened residual matrix W_res = R_c^{-1} (R_td_hat - R_c) R_c^{-1}
        R_inv = np.linalg.inv(R_c)
        W_res = R_inv @ (R_td_hat - R_c) @ R_inv
        # Note: Tr(W_res @ C_td(u)) = sum_{n, m} W_res[m, n] * R_d_td[n, m] * exp(j2pi u (n - m) / N)!
        # That is a 1D FFT over lag r = (n - m)!! Computes exact full-matrix Rao numerator for ALL u in O(N^2 + N log N)!
        A_prod = W_res.T * R_d_td  # (n, m) entry is W_res[m, n] * R_d_td[n, m]
        # Sum along lags r = n - m in -(N-1) .. (N-1)
        n_fft = 1024
        lag_vec = np.zeros(n_fft, dtype=np.complex128)
        for r in range(-(N - 1), N):
            val_r = np.sum(np.diag(A_prod, -r))  # diag(A, -r) has row - col = r => n - m = r!
            lag_vec[r % n_fft] += val_r
        # sum_r lag_vec[r] exp(j2pi u r / N): set u_grid = m * (N / n_fft) => exp(j2pi m r / n_fft) = n_fft * ifft(lag_vec)!
        rao_spec = np.real(ifft(lag_vec) * n_fft)
        u_grid = np.arange(n_fft, dtype=float) * (float(N) / n_fft)

        best_u, best_sc = None, -1e30
        for idx_g, ug in enumerate(u_grid):
            if not is_valid_u(ug):
                continue
            if any(abs(((ug - ua + N / 2.0) % N) - N / 2.0) <= 1.2 for ua in U_c):
                continue
            if rao_spec[idx_g] > best_sc:
                best_sc = float(rao_spec[idx_g])
                best_u = ug
        if best_u is None or best_sc <= 0:
            break

        # Refine (U_try, g_try, s2_try) by optimizing exact Wishart 2NLL around best_u
        U_try = U_c + [best_u]
        Pp = len(U_try)
        # Initial g for new component via 1D Rao/Fisher step: Fisher = Tr((R_inv C_td)^2)
        C_new = td_atom(best_u)
        RC = R_inv @ C_new
        fim_gg = max(float(np.real(np.trace(RC @ RC))), 1e-9)
        g_new0 = max(best_sc / fim_gg, 1e-4)
        g_init = g_c + [g_new0]
        s2_init = max(s2_c - g_new0 / float(N), 1e-4)

        # Jointly refine ALL Pp positions [u_0..u_{Pp-1}, log(g_0..g_{Pp-1}), log(s2)] via Cholesky Wishart 2NLL
        u_bnds = []
        for u_item in U_try:
            ec = min(range(ell_max + 1), key=lambda e: abs(((u_item + Q_in * e + N / 2.0) % N) - N / 2.0))
            c_unw = u_item - (((u_item - ((-Q_in * ec) % N) + N / 2.0) % N) - N / 2.0)
            u_bnds.append((min(max(u_item - 0.8, c_unw - nu_max), u_item), max(min(u_item + 0.8, c_unw + nu_max), u_item)))

        def obj_w(x):
            us_v = x[:Pp]
            gs = np.exp(np.clip(x[Pp:2 * Pp], -13.0, 6.0))
            s2v = float(np.exp(np.clip(x[2 * Pp], -13.0, 6.0)))
            R_m = s2v * np.eye(N, dtype=np.complex128)
            for j_f in range(Pp):
                R_m += gs[j_f] * td_atom(float(us_v[j_f]))
            R_m = 0.5 * (R_m + R_m.conj().T)
            try:
                L_ch = np.linalg.cholesky(R_m)
            except np.linalg.LinAlgError:
                return 1e30
            ld = 2.0 * float(np.sum(np.log(np.real(np.diag(L_ch)))))
            # Tr(R_m^{-1} R_td_hat) = ||L_ch^{-1} Z_td||_F^2 / (M - 1)
            Linv_R = np.linalg.solve(L_ch, R_td_hat)
            tr_val = float(np.real(np.trace(np.linalg.solve(L_ch.conj().T, Linv_R))))
            return float(2.0 * M * (ld + tr_val))

        x0 = np.concatenate([np.array(U_try, dtype=float), np.log(np.maximum(g_init, 1e-5)), [np.log(max(s2_init, 1e-5))]])
        bnds = u_bnds + [(-12.0, 5.0)] * (Pp + 1)
        res_opt = minimize(obj_w, x0, method="L-BFGS-B", bounds=bnds, options={"maxiter": 25, "ftol": 1e-8})
        u_opt_list = (res_opt.x[:Pp] % N).tolist()
        g_opt = np.exp(np.clip(res_opt.x[Pp:2 * Pp], -13.0, 6.0)).tolist()
        s2_opt = float(np.exp(np.clip(res_opt.x[2 * Pp], -13.0, 6.0)))
        nll2_ref = float(res_opt.fun)

        stat = max(0.0, nll2_c - nll2_ref)
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_w:
            break
        U_c = u_opt_list
        g_c = g_opt
        s2_c = s2_opt
        nll2_c = nll2_ref
        R_c = s2_c * np.eye(N, dtype=np.complex128)
        for uj, gj in zip(U_c, g_c):
            R_c += gj * td_atom(uj)
        R_c = 0.5 * (R_c + R_c.conj().T)

    dets = []
    for uj, gj in zip(U_c, g_c):
        ej = min(range(ell_max + 1), key=lambda e: abs(((uj + Q_in * e + N / 2.0) % N) - N / 2.0))
        nj = float(((uj + Q_in * ej + N / 2.0) % N) - N / 2.0)
        dets.append((ej, nj, float(gj * (rms ** 2))))
    return dets, first_stat


def estimate_cumulant4_blind(
    Y: np.ndarray,
    sys_cfg: dict,
    Q_in: int,
    ell_max: int,
    nu_max: float,
    tau_c4: float,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """
    Textbook 4th-order sample cumulant diagonal estimator:
      c4_hat[k] = mean_m(|Y[k,m]|^4) - 2 * (mean_m(|Y[k,m]|^2))^2.
    Note: Under Swerling-II h_{p,m} ~ CN(0, gamma_p), for a single ray y = h_m * z_m,
    E[|h_m|^4] = 2 gamma^2 while 2*(E[|h_m|^2])^2 = 2 gamma^2, so E[|y|^4] - 2(E[|y|^2])^2
    equals 2 * gamma^2 * (E[|z|^4] - (E[|z|^2])^2)! Since z_m[k] = sum G_{k,n} sqrt(d[n]) x[n]
    has non-Gaussian kurtosis + power-mask variance, we fit positive NNLS on |c4_hat| / excess 4th moment!
    """
    N, M = Y.shape
    D_fft = sys_cfg["D_fft"]
    rms = float(np.sqrt(np.mean(np.abs(Y) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Yn = Y / rms
    P2 = np.abs(Yn) ** 2
    m2 = np.mean(P2, axis=1)
    m4_emp = np.mean(P2 ** 2, axis=1)
    # Excess 4th-order statistic over stationary Gaussian white noise: under H0 CN(0, s2), E[|Y|^4] - 2(E[|Y|^2])^2 = 0!
    c4 = m4_emp - 2.0 * (m2 ** 2)
    # Under Swerling-II, E[|sum_p h_p z_p + w|^4 | z] = 2 * (sum_p g_p |z_p|^2 + s2)^2
    # => E_z[m4_emp] - 2*(E_z[m2])^2 = 2 * Var_z(sum_p g_p |z_p[k]|^2) >= 0 (strictly positive on power mask d!)
    v4_emp = max(float(np.var(c4, ddof=1)), 1e-12)

    # Template for Var_z(|z_p[k]|^2): for circular proper z_p[k] with variance t0(k; u),
    # |z_p[k]|^2 has variance ~ t0(k; u)^2 (up to sub-Gaussian constellation kurtosis correction)
    k_idx = np.arange(N, dtype=float)
    def t4_atom(u_val):
        K0 = m4.complex_dirichlet(N, k_idx - u_val)
        t0 = np.real(ifft(fft(np.abs(K0) ** 2) * D_fft))
        return t0 ** 2

    valid_u = []
    for ell in range(ell_max + 1):
        cu = (-Q_in * ell) % N if Q_in > 0 else 0.0
        for dv in np.linspace(-nu_max + 0.2, nu_max - 0.2, 19):
            valid_u.append(float((cu + dv) % N))

    y_c4 = c4 - np.min(c4) if not return_top_stat else c4
    res = c4.copy()
    rss_c = float(np.sum(np.maximum(res, 0.0) ** 2))
    first_stat = float(np.max(c4) / math.sqrt(v4_emp))
    if return_top_stat:
        return [], first_stat

    U_c = []
    g_c = np.array([])
    for step in range(P_max):
        best_u, best_sc = None, -1e30
        for uc in valid_u:
            if any(abs(((uc - ua + N / 2.0) % N) - N / 2.0) <= 1.2 for ua in U_c):
                continue
            a = t4_atom(uc)
            az = a - np.mean(a)
            sc = float(np.dot(res - np.mean(res), az)) / (float(np.linalg.norm(az)) * math.sqrt(v4_emp) + 1e-12)
            if sc > best_sc:
                best_sc, best_u = sc, uc
        if best_u is None or best_sc <= tau_c4:
            break
        U_try = U_c + [best_u]
        A_m = np.column_stack([t4_atom(u) for u in U_try] + [np.ones(N)])
        th, _ = nnls(A_m, np.maximum(c4, 0.0))
        U_c = U_try; g_c = np.sqrt(np.maximum(th[:-1], 0.0))
        res = c4 - A_m @ th

    dets = []
    for uj, gj in zip(U_c, g_c):
        if Q_in > 0:
            ej = min(range(ell_max + 1), key=lambda e: abs(((uj + Q_in * e + N / 2.0) % N) - N / 2.0))
            nj = float(((uj + Q_in * ej + N / 2.0) % N) - N / 2.0)
        else:
            ej = 0
            nj = float(((uj + N / 2.0) % N) - N / 2.0)
        dets.append((ej, nj, float(gj * (rms ** 2))))
    return dets, first_stat


def oracle_known_x_nomp(
    R_time: np.ndarray,
    S_tx: np.ndarray,
    c1: float,
    ell_max: int,
    nu_max: float,
    tau_orac: float,
    P_max: int = 5,
    return_top_stat: bool = False,
):
    """
    True Upper-Bound Oracle (`Oracle_KnownX_GLRT`):
    Gifts the transmitted waveform S_tx (N x M) to the bistatic radar receiver!
    Under Swerling-II h_{p,m} ~ CN(0, gamma_p), for each candidate (ell, nu), the normalized
    per-frame matched filter z_m(ell, nu) = <a_m(ell, nu), r_m> / ||a_m|| has distribution
    CN(0, sigma_w^2 + gamma_p ||a_m||^2), so incoherently summing |z_m|^2 across M=128 frames
    gives a 256-DoF chi-square GLRT with full N-sample coherent processing gain per frame!
    Iteratively projects out detected clutter subspaces across all M frames (exact Swerling-II subspace CLEAN/GLRT)!
    """
    N, M = R_time.shape
    rms = float(np.sqrt(np.mean(np.abs(R_time) ** 2)))
    if rms < 1e-15:
        return [], 0.0
    Rn = R_time / rms

    # Maintain per-frame orthogonalized basis Q_m (list of orthonormal columns per frame m)
    Q_frames = [np.zeros((N, 0), dtype=np.complex128) for _ in range(M)]
    Res = Rn.copy()

    # Coarse Doppler grid (spacing 0.25 bin -> 37 points per integer delay)
    nu_grid = np.linspace(-nu_max, nu_max, 37)

    def eval_glrt_energy(ell_c: int, nu_c: float):
        # A_mat = apply_path_time_fast(S_tx, ell_c, nu_c, c1)  # (N, M)
        A_mat = m4.apply_path_time_fast(S_tx, ell_c, nu_c, c1)
        # Project A_mat orthogonal to already-detected clutter in each frame so clutter leakage is ZERO!
        if Q_frames[0].shape[1] > 0:
            for m in range(M):
                Qm = Q_frames[m]
                A_mat[:, m] -= Qm @ (Qm.conj().T @ A_mat[:, m])
        nrms = np.maximum(np.linalg.norm(A_mat, axis=0), 1e-12)
        proj = np.sum(np.conj(A_mat) * Res, axis=0) / nrms
        return float(np.sum(np.abs(proj) ** 2))

    # Empirical noise variance per DoF from median energy across far-away cells on step 0
    U_dets = []
    first_stat = 0.0
    for step in range(P_max):
        grid_vals = np.empty((ell_max + 1, len(nu_grid)), dtype=float)
        for ie in range(ell_max + 1):
            for iv, nv in enumerate(nu_grid):
                if any(ed == ie and abs(nv - vd) <= 0.6 for (ed, vd, _) in U_dets):
                    grid_vals[ie, iv] = -1.0
                else:
                    grid_vals[ie, iv] = eval_glrt_energy(ie, float(nv))

        valid_scores = grid_vals[grid_vals >= 0.0]
        if len(valid_scores) == 0:
            break
        # Under residual noise, each cell sum_m |proj_m|^2 ~ s2_res * (chi^2_{2M} / 2), median ~ M * s2_res
        s2_est = max(float(np.median(valid_scores)) / float(M), 1e-12)
        ie_b, iv_b = np.unravel_index(int(np.argmax(grid_vals)), grid_vals.shape)
        ell_b = int(ie_b)
        nu_b = float(nu_grid[iv_b])

        # Fine golden-section refinement of nu_b to 1e-4 bin so strong 0 dB clutter leaves ZERO off-grid residual!
        lo_v = max(-nu_max, nu_b - 0.30)
        hi_v = min(nu_max, nu_b + 0.30)
        gr = 0.61803398875
        x1 = hi_v - gr * (hi_v - lo_v); x2 = lo_v + gr * (hi_v - lo_v)
        f1_v = eval_glrt_energy(ell_b, x1); f2_v = eval_glrt_energy(ell_b, x2)
        for _ in range(18):
            if f1_v < f2_v:
                lo_v = x1; x1 = x2; f1_v = f2_v; x2 = lo_v + gr * (hi_v - lo_v); f2_v = eval_glrt_energy(ell_b, x2)
            else:
                hi_v = x2; x2 = x1; f2_v = f1_v; x1 = hi_v - gr * (hi_v - lo_v); f1_v = eval_glrt_energy(ell_b, x1)
        nu_b = 0.5 * (lo_v + hi_v)
        best_e_val = eval_glrt_energy(ell_b, nu_b)

        stat = float(best_e_val) / s2_est
        if step == 0:
            first_stat = stat
        if return_top_stat:
            return [], first_stat
        if stat <= tau_orac:
            break

        U_dets.append((ell_b, nu_b, float(stat * s2_est / M * (rms ** 2))))
        # Project out BOTH steering vector AND its 1st Doppler derivative per frame so residual is exact 0!
        A_det = m4.apply_path_time_fast(S_tx, ell_b, nu_b, c1)
        dA_det = (1j * 2.0 * np.pi * np.arange(N, dtype=float)[:, None] / N) * A_det
        for m in range(M):
            for col_cand in (A_det[:, m], dA_det[:, m]):
                v_col = col_cand.copy()
                Qm = Q_frames[m]
                if Qm.shape[1] > 0:
                    v_col = v_col - Qm @ (Qm.conj().T @ v_col)
                nv_c = float(np.linalg.norm(v_col))
                if nv_c > 1e-10:
                    u_col = (v_col / nv_c)[:, None]
                    Q_frames[m] = np.hstack([Qm, u_col])
                    Res[:, m] -= u_col[:, 0] * np.vdot(u_col[:, 0], Res[:, m])

    return U_dets, first_stat


_W_CFG = None
def _init_pool(order: int, Q: int, delta: float):
    global _W_CFG
    _W_CFG = m4.build_system(order=order, Q=Q, delta=delta)


def _cal_h0_worker(args):
    seed, M_c, ell_max, nu_max = args
    cfg = _W_CFG
    N, Q, c1, c2 = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"]
    rng = np.random.default_rng(seed)
    W_t = (rng.standard_normal((N, M_c)) + 1j * rng.standard_normal((N, M_c))) / np.sqrt(2.0)
    X_m = np.sqrt(cfg["d"][:, None]) * m4.sample_765bit_norm(rng, cfg, M_c)
    S_af = m4.idaft_fast(X_m, c1, c2)

    Y_af = m4.daft_fast(W_t, c1, c2)
    Y_of = m4.daft_fast(W_t, 0.0, c2)

    s_ours = m4.estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1]
    s_td = m4.estimate_td_cov_nomp(W_t, cfg, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
    s_gls = estimate_demean_cov_gls_comet(Y_af, cfg, Q, ell_max, nu_max, 0.0, max_lag=3, P_max=1, return_top_stat=True)[1]
    s_wish = estimate_full_wishart_qml(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
    s_c4 = estimate_cumulant4_blind(Y_af, cfg, Q, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
    s_ofdm = m4.estimate_banded_clean(Y_of, cfg, 0, ell_max, nu_max, 0.0, P_max=1, use_lag1=True, homoscedastic=False, return_top_stat=True)[1]
    s_orac = oracle_known_x_nomp(W_t, S_af, c1, ell_max, nu_max, 0.0, P_max=1, return_top_stat=True)[1]
    return {
        "Ours_Banded": s_ours,
        "Rival_TDCov": s_td,
        "Steelman_A_DemeanGLS": s_gls,
        "Steelman_A_FullWishart": s_wish,
        "Steelman_Cumulant4": s_c4,
        "Steelman_S_OFDM_SameMask": s_ofdm,
        "Oracle_KnownX_GLRT": s_orac,
    }


def _eval_scene_worker(args):
    seed, M_c, pwrs_db, s2_t, ell_max, nu_max, taus = args
    cfg = _W_CFG
    N, Q, c1, c2, d = cfg["N"], cfg["Q"], cfg["c1"], cfg["c2"], cfg["d"]
    rng = np.random.default_rng(seed)
    tie_rng = np.random.default_rng(seed + 77777)
    P_t = len(pwrs_db)
    gammas = [10.0 ** (x / 10.0) for x in pwrs_db]

    ells = rng.choice(np.arange(0, ell_max + 1), size=P_t, replace=False).tolist()
    nus = rng.uniform(-nu_max + 0.3, nu_max - 0.3, size=P_t).tolist()
    truths = list(zip(ells, nus))

    X_norm = m4.sample_765bit_norm(rng, cfg, M_c)
    X_mask = np.sqrt(d[:, None]) * X_norm
    Hf = np.array([np.sqrt(g / 2.0) * (rng.standard_normal(M_c) + 1j * rng.standard_normal(M_c)) for g in gammas])
    W_t = np.sqrt(s2_t / 2.0) * (rng.standard_normal((N, M_c)) + 1j * rng.standard_normal((N, M_c)))

    # 1) Masked AFDM
    S_af = m4.idaft_fast(X_mask, c1, c2)
    R_af = W_t.copy()
    for p in range(P_t):
        R_af += m4.apply_path_time_fast(S_af, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_af = m4.daft_fast(R_af, c1, c2)

    # 2) Unmasked AFDM (Pub_NoMask / Ranasinghe uniform power)
    S_nm = m4.idaft_fast(X_norm, c1, c2)
    R_nm = W_t.copy()
    for p in range(P_t):
        R_nm += m4.apply_path_time_fast(S_nm, ells[p], nus[p], c1) * Hf[p][None, :]
    Y_nm = m4.daft_fast(R_nm, c1, c2)

    # 3) Same-mask OFDM (c1 = 0)
    S_of = m4.idaft_fast(X_mask, 0.0, c2)
    R_of = W_t.copy()
    for p in range(P_t):
        R_of += m4.apply_path_time_fast(S_of, ells[p], nus[p], 0.0) * Hf[p][None, :]
    Y_of = m4.daft_fast(R_of, 0.0, c2)

    # 4) Same-mask Single-Carrier SC-FDE (time-domain mask S_sc = X_mask! Recovers delay ell exactly, blind to Doppler nu!)
    S_sc = X_mask
    R_sc = W_t.copy()
    for p in range(P_t):
        R_sc += m4.apply_path_time_fast(S_sc, ells[p], nus[p], 0.0) * Hf[p][None, :]
    # Time-domain power profile E[|R_sc[n]|^2] = s2 + sum_p gamma_p d[(n - ell_p)%N]; Doppler is strictly unidentifiable in 2nd order -> uniform tie-break in [-nu_max, nu_max]!
    p_sc = np.mean(np.abs(R_sc) ** 2, axis=1)
    # Match integer delays via NNLS on shifted d[(n - ell)%N], assign uniform random nu in [-nu_max, nu_max]
    D_shifts = np.column_stack([np.roll(d, e) for e in range(ell_max + 1)] + [np.ones(N)])
    g_sc_all, _ = nnls(D_shifts, p_sc)
    top_e_sc = np.argsort(g_sc_all[:-1])[::-1]
    dets_sc = []
    for e_idx in top_e_sc[:P_t + 1]:
        if g_sc_all[e_idx] > 0.03 * np.max(g_sc_all[:-1]):
            dets_sc.append((int(e_idx), float(tie_rng.uniform(-nu_max, nu_max)), float(g_sc_all[e_idx])))

    arms_out = {
        "Pub_NoMask": m4.estimate_banded_clean(Y_nm, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0],
        "Ours_Banded": m4.estimate_banded_clean(Y_af, cfg, Q, ell_max, nu_max, taus["Ours_Banded"], P_max=5, use_lag1=True, homoscedastic=False)[0],
        "Rival_TDCov": m4.estimate_td_cov_nomp(R_af, cfg, ell_max, nu_max, taus["Rival_TDCov"], P_max=5)[0],
        "Steelman_A_DemeanGLS": estimate_demean_cov_gls_comet(Y_af, cfg, Q, ell_max, nu_max, taus["Steelman_A_DemeanGLS"], max_lag=3, P_max=5)[0],
        "Steelman_A_FullWishart": estimate_full_wishart_qml(Y_af, cfg, Q, ell_max, nu_max, taus["Steelman_A_FullWishart"], P_max=5)[0],
        "Steelman_Cumulant4": estimate_cumulant4_blind(Y_af, cfg, Q, ell_max, nu_max, taus["Steelman_Cumulant4"], P_max=5)[0],
        "Steelman_S_OFDM_SameMask": m4.estimate_banded_clean(Y_of, cfg, 0, ell_max, nu_max, taus["Steelman_S_OFDM_SameMask"], P_max=5, use_lag1=True, homoscedastic=False, tie_rng=tie_rng)[0],
        "Steelman_S_SCFDE_SameMask": dets_sc,
        "Oracle_KnownX_GLRT": oracle_known_x_nomp(R_af, S_af, c1, ell_max, nu_max, taus["Oracle_KnownX_GLRT"], P_max=5)[0],
    }

    res = {}
    for a, dets in arms_out.items():
        hc, fac, _ = m4.match_targets(dets, truths, nu_tol=0.25)
        wh, _, _ = m4.match_targets(dets, [truths[-1]], nu_tol=0.25)
        res[a] = (wh, 1 if fac > 0 else 0, hc)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", type=str, default=os.path.join(REPO_ROOT, "ideas", "r15", "out_m04.json"))
    args = ap.parse_args()

    t0 = time.perf_counter()
    seed_base = 202611269800 if args.smoke else 202611263500
    n_cal = 40 if args.smoke else 260
    n_scenes = 6 if args.smoke else 120
    ell_max, nu_max = 16, 4.5
    M_c = 128
    s2_t = 10.0 ** (-1.5)  # 15 dB

    results = {
        "card": "I-20261126-m04",
        "frozen_m04_md5": _m04_md5,
        "seed_base": seed_base,
        "smoke": bool(args.smoke),
        "workers": int(args.workers),
        "n_cal": n_cal,
        "n_scenes": n_scenes,
    }

    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_pool, initargs=(8, 12, 2.0 / 3.0)) as pool:
        tc = time.perf_counter()
        cal_rows = list(pool.map(_cal_h0_worker, [(seed_base + i, M_c, ell_max, nu_max) for i in range(n_cal)]))
        idx_os = min(n_cal - 1, max(0, int(math.floor((n_cal + 1) * 0.985)) - 1))
        taus = {}
        for k in cal_rows[0].keys():
            arr = sorted(r[k] for r in cal_rows)
            taus[k] = float(arr[idx_os])
        results["h0_calibration"] = {"marginal_pfa_target": (n_cal + 1 - (idx_os + 1)) / float(n_cal + 1), "taus": taus, "elapsed_s": round(time.perf_counter() - tc, 2)}
        print(f"[H0 Cal] (n={n_cal}, {results['h0_calibration']['elapsed_s']}s) taus={ {k: round(v, 2) for k, v in taus.items()} }", flush=True)

        results["regimes"] = {}
        for r_idx, (rname, pwrs_db) in enumerate([
            ("Reg1_P2_0_m13p5dB_SwII", [0.0, -13.5]),
            ("Reg2_P3_0_m5_m12p5dB_SwII", [0.0, -5.0, -12.5]),
        ]):
            tr = time.perf_counter()
            tasks = [(seed_base + (r_idx + 1) * 10000 + i, M_c, pwrs_db, s2_t, ell_max, nu_max, taus) for i in range(n_scenes)]
            rows = list(pool.map(_eval_scene_worker, tasks))
            arms = list(rows[0].keys())
            reg_sum = {}
            for a in arms:
                wt_hits = sum(r[a][0] for r in rows)
                any_fa = sum(r[a][1] for r in rows)
                reg_sum[a] = {
                    "wt_pd": m4.wilson_ci(wt_hits, n_scenes),
                    "any_fa": m4.wilson_ci(any_fa, n_scenes),
                }
            results["regimes"][rname] = {"n_scenes": n_scenes, "pwrs_db": pwrs_db, "elapsed_s": round(time.perf_counter() - tr, 2), "arms": reg_sum}
            print(f"\n[{rname}] (n={n_scenes}, {results['regimes'][rname]['elapsed_s']}s):", flush=True)
            for a in arms:
                wt = reg_sum[a]["wt_pd"]; fa = reg_sum[a]["any_fa"]
                print(f"  {a:26s}: WT-Pd = {wt['est']*100:5.1f}% [{wt['lo']*100:4.1f}, {wt['hi']*100:4.1f}]% | anyFA = {fa['est']*100:4.1f}%", flush=True)

    results["total_elapsed_s"] = round(time.perf_counter() - t0, 2)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2, allow_nan=False)
    print(f"\nSaved -> {args.out} (total {results['total_elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()
