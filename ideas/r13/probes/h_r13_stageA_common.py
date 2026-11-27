import sys
import numpy as np


def build_daft_matrices(N: int, c1: float, c2: float):
    n = np.arange(N, dtype=np.float64)
    m = np.arange(N, dtype=np.float64)
    lc1 = np.exp(-1j * 2.0 * np.pi * c1 * (n ** 2))
    lc2 = np.exp(-1j * 2.0 * np.pi * c2 * (m ** 2))
    F = np.fft.fft(np.eye(N, dtype=np.complex128), axis=0) / np.sqrt(N)
    A = (lc2[:, None] * F) * lc1[None, :]
    return A, lc1, lc2, F


def daft_col(X: np.ndarray, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    N = lc1.shape[0]
    tmp = lc1[:, None] * X if X.ndim == 2 else lc1 * X
    f = np.fft.fft(tmp, axis=0) / np.sqrt(N)
    return (lc2[:, None] * f) if X.ndim == 2 else (lc2 * f)


def idaft_col(S: np.ndarray, lc1: np.ndarray, lc2: np.ndarray) -> np.ndarray:
    N = lc1.shape[0]
    tmp = np.conj(lc2)[:, None] * S if S.ndim == 2 else np.conj(lc2) * S
    f = np.fft.ifft(tmp, axis=0) * np.sqrt(N)
    return (np.conj(lc1)[:, None] * f) if S.ndim == 2 else (np.conj(lc1) * f)


def td_path_matrix(N: int, c1: float, ell: int, nu: float) -> np.ndarray:
    """Exact time-domain path operator T(ell, nu) = Delta(nu) @ Psi_CPP(ell) after CPP removal."""
    n = np.arange(N, dtype=np.int64)
    col = (n - ell) % N
    cpp = np.where(
        n < ell,
        np.exp(-1j * 2.0 * np.pi * c1 * (N * N - 2.0 * N * (ell - n))),
        1.0 + 0.0j,
    )
    dop = np.exp(1j * 2.0 * np.pi * nu * n / float(N))
    T = np.zeros((N, N), dtype=np.complex128)
    T[n, col] = dop * cpp
    return T


def daft_path_matrix(A: np.ndarray, c1: float, ell: int, nu: float) -> np.ndarray:
    T = td_path_matrix(A.shape[0], c1, ell, nu)
    return A @ T @ A.conj().T


def ula_steering(Nt: int, theta_deg: float, unit_norm: bool = False) -> np.ndarray:
    idx = np.arange(Nt, dtype=np.float64)
    v = np.exp(-1j * np.pi * idx * np.sin(np.deg2rad(theta_deg)))
    if unit_norm:
        v = v / np.sqrt(float(Nt))
    return v


def wideband_td_aperture_op(N: int, Nt: int, theta_deg: float, eta_bw: float) -> np.ndarray:
    """
    Returns array of shape (Nt, N, N) or frequency-domain diagonal response H_wb[nt, kc]
    for physical centered DFT bins kc in [-N/2, ..., N/2-1].
    In centered DFT order (fftshift), f_k / f_c = 1 + (kc / N) * eta_bw.
    """
    kc = np.fft.ifftshift(np.arange(-N // 2, N // 2, dtype=np.float64))
    idx = np.arange(Nt, dtype=np.float64)[:, None]
    freq_scale = 1.0 + (kc[None, :] / float(N)) * eta_bw
    return np.exp(-1j * np.pi * idx * freq_scale * np.sin(np.deg2rad(theta_deg)))


def build_wideband_user_channel(A: np.ndarray, F_dft: np.ndarray, c1: float, Nt: int, paths: list, eta_bw: float) -> np.ndarray:
    """Exact DAFT-domain channel H_k in C^{N x (N*Nt)} (precoder index m*Nt + nt)."""
    N = A.shape[0]
    H_k = np.zeros((N, N * Nt), dtype=np.complex128)
    FAH = F_dft @ A.conj().T
    AFH = A @ F_dft.conj().T
    for alpha_p, ell_p, nu_p, theta_p in paths:
        E_p = daft_path_matrix(A, c1, ell_p, nu_p)
        if abs(eta_bw) < 1e-15:
            a_conj = np.conj(ula_steering(Nt, theta_p, unit_norm=False))
            H_k += np.kron(alpha_p * E_p, a_conj[None, :])
        else:
            A_wb_conj = np.conj(wideband_td_aperture_op(N, Nt, theta_p, eta_bw))
            for nt in range(Nt):
                M_nt = (AFH * A_wb_conj[nt, :][None, :]) @ FAH
                H_k[:, nt::Nt] += (alpha_p * E_p) @ M_nt
    return H_k


def qam16_alphabet() -> np.ndarray:
    pts = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float64)
    grid = (pts[:, None] + 1j * pts[None, :]).ravel() / np.sqrt(10.0)
    return grid


def qpsk_alphabet() -> np.ndarray:
    return np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j], dtype=np.complex128) / np.sqrt(2.0)


def nearest_symbol_ser(z_est: np.ndarray, d_true: np.ndarray, alphabet: np.ndarray) -> float:
    zf = z_est.ravel()
    df = d_true.ravel()
    dist = np.abs(zf[:, None] - alphabet[None, :])
    idx_hat = np.argmin(dist, axis=1)
    idx_true = np.argmin(np.abs(df[:, None] - alphabet[None, :]), axis=1)
    return float(np.mean(idx_hat != idx_true))


def solve_qcqp_dual_1d(Tw: np.ndarray, B_rhs: np.ndarray, a_vec: np.ndarray, w_ref: np.ndarray,
                       gamma_s: float, p_max: float) -> np.ndarray:
    """
    Exact KKT solver for single-sector / dominant-sector MM subproblem (Liu & Schober 2607 Eq. 46):
      min_W  sum_m w_m^H Tw_m w_m - 2 Re(b_m^H w_m)   (or full coupled vector w)
      s.t.   2 Re(g_lin^H w) - c_ref >= gamma_s,   ||w||^2 <= p_max
    Here Tw is (D, D) Hermitian PSD, B_rhs is (D, M_streams), a_vec is (D, M_streams) stacked linear minorant.
    Wait: in Eq. (45), gi_tilde(W; Wref) = sum_{stream s} (2 Re(w_s^H G_i w_s^ref) - w_s^{ref H} G_i w_s^ref),
    where G_i = I_N kron (a_i a_i^H). Notice every stream s shares the SAME Tw!
    """
    D, M = B_rhs.shape
    H_sym = 0.5 * (Tw + Tw.conj().T) + 1e-10 * np.eye(D)
    eigvals, U = np.linalg.eigh(H_sym)
    eigvals = np.maximum(eigvals, 1e-10)

    # Linear sensing direction per stream: d_sens[:, s] = a_vec[:, s] (= G_i w_ref[:, s])
    c_ref = float(np.real(np.sum(np.conj(w_ref) * a_vec)))
    rhs_req = 0.5 * (gamma_s + c_ref)

    UB = U.conj().T @ B_rhs        # (D, M)
    UA = U.conj().T @ a_vec        # (D, M)

    def eval_w_from_mu_lam(mu: float, lam: float):
        denom = (eigvals + np.maximum(lam, 1e-11))[:, None]
        UW = (UB + mu * UA) / denom
        return UW

    def power_for_lam(mu: float, lam: float) -> float:
        UW = eval_w_from_mu_lam(mu, lam)
        return float(np.sum(np.abs(UW) ** 2))

    def solve_opt_lam(mu: float):
        if power_for_lam(mu, 1e-11) <= p_max:
            return 1e-11, eval_w_from_mu_lam(mu, 1e-11)
        lo, hi = 1e-11, 1.0
        while power_for_lam(mu, hi) > p_max:
            hi *= 4.0
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            if power_for_lam(mu, mid) > p_max:
                lo = mid
            else:
                hi = mid
        return hi, eval_w_from_mu_lam(mu, hi)

    def sens_lhs(mu: float) -> float:
        _, UW = solve_opt_lam(mu)
        return float(np.real(np.sum(np.conj(UA) * UW)))

    if gamma_s <= 1e-12 or sens_lhs(0.0) >= rhs_req:
        _, UW = solve_opt_lam(0.0)
        return U @ UW

    mu_lo, mu_hi = 0.0, 1.0
    for _ in range(30):
        if sens_lhs(mu_hi) >= rhs_req:
            break
        mu_hi *= 3.0
    for _ in range(44):
        mu_mid = 0.5 * (mu_lo + mu_hi)
        if sens_lhs(mu_mid) < rhs_req:
            mu_lo = mu_mid
        else:
            mu_hi = mu_mid
    _, UW = solve_opt_lam(mu_hi)
    return U @ UW


def verify_common_redline1() -> dict:
    N = 64
    c1 = 2.37 / (2.0 * N)  # intentionally non-integer 2*N*c1 to test full CPP phase!
    c2 = 1.0 / (2.0 * N)
    A, lc1, lc2, _ = build_daft_matrices(N, c1, c2)
    unitary_err = float(np.linalg.norm(A @ A.conj().T - np.eye(N)))

    rng = np.random.default_rng(20261126)
    S = (rng.standard_normal((N, 3)) + 1j * rng.standard_normal((N, 3))) / np.sqrt(2.0)
    fast_daft_err = float(np.linalg.norm(daft_col(S, lc1, lc2) - A @ S))
    fast_idaft_err = float(np.linalg.norm(idaft_col(S, lc1, lc2) - A.conj().T @ S))

    # Two-block continuous CPP convolution vs daft_path_matrix
    Ncpp = 12
    ell = 7
    nu = 0.63
    s_af = S[:, 0]
    x_td = idaft_col(s_af, lc1, lc2)
    k_cpp = np.arange(-Ncpp, 0, dtype=np.int64)
    cpp_seg = x_td[N + k_cpp] * np.exp(-1j * 2.0 * np.pi * c1 * (N * N + 2.0 * N * k_cpp))
    tx_full = np.concatenate([cpp_seg, x_td])
    n = np.arange(N, dtype=np.int64)
    rx_td = tx_full[Ncpp + n - ell] * np.exp(1j * 2.0 * np.pi * nu * n / float(N))
    y_conv = daft_col(rx_td, lc1, lc2)
    E_mat = daft_path_matrix(A, c1, ell, nu)
    y_op = E_mat @ s_af
    cpp_conv_err = float(np.linalg.norm(y_conv - y_op))

    # Shift peak verification for integer Doppler and integer 2*N*c1
    c1_int = 3.0 / (2.0 * N)
    A_int, _, _, _ = build_daft_matrices(N, c1_int, c2)
    E_int = daft_path_matrix(A_int, c1_int, ell=4, nu=1.0)
    imp = np.zeros(N, dtype=np.complex128)
    imp[10] = 1.0
    out = np.abs(E_int @ imp)
    peak_bin = int(np.argmax(out))
    # Expected peak: n -> n-4 with +j2pi*1*n/N: check exact peak concentration == 1.0
    peak_err = float(abs(out[peak_bin] - 1.0))

    assert unitary_err < 1e-12
    assert fast_daft_err < 1e-12
    assert fast_idaft_err < 1e-12
    assert cpp_conv_err < 1e-12
    assert peak_err < 1e-12
    return {
        "unitary_err": unitary_err,
        "fast_daft_err": fast_daft_err,
        "fast_idaft_err": fast_idaft_err,
        "cpp_conv_err": cpp_conv_err,
        "peak_err": peak_err,
        "peak_bin_from_10": peak_bin,
    }


if __name__ == "__main__":
    res = verify_common_redline1()
    print("COMMON REDLINE1 PASS:", res)
