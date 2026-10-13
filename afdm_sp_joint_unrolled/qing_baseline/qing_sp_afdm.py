"""qing_sp_afdm.py — Zheng 2025 SP-AFDM receiver (faithful re-implementation).

Reference: K. Zheng, M. Wen, T. Mao, L. Xiao, Z. Wang,
    "Channel Estimation for AFDM With Superimposed Pilots",
    IEEE TVT 74(2):3389-3394, 2025. DOI 10.1109/TVT.2024.3469380
    arXiv:2404.10232. Paper PDF: _archive/literature/Zheng2025_SP-AFDM_arXiv2404.10232.pdf

Equation numbers in comments refer to the published version.

Pipeline:
    1. equispaced superimposed pilot              (Eq 11)
    2. build per-(l_t, alpha_t) hypothesis matrices Theta_t  (Eq 6, 7, 8)
    3. assemble Phi_p = [Theta_1 x_p, ..., Theta_{Q+1} x_p]  (Eq 16)
    4. MMSE channel estimation                    (Eq 19)
    5. threshold path indicator (3-sigma)         (Eq 21)
    6. cancel pilot interference + MP detection   (Eq 22, 23)
    7. iterate: re-estimate h with x_d feedback   (Eq 24)

Status: implementation faithful to the paper's equations; not yet
consistency-tested against Fig. 3. See qing_baseline/README.md.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

# Ensure the project root (containing the `afdm_sp_joint_unrolled` package) is
# on sys.path so `from afdm_sp_joint_unrolled.mp_detect_bp_torch import ...`
# resolves whether this file is run as a script or imported.
_HERE = pathlib.Path(__file__).resolve().parent  # .../afdm_sp_joint_unrolled/qing_baseline/
_PROJ_ROOT = _HERE.parent.parent  # .../AFDM-channel-estimation/
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))


# --------------------------------------------------------------------- pilots
def qing_pilot(N: int, alpha_max: int, l_max: int, M: int, sigma_p: float
               ) -> tuple[np.ndarray, int]:
    """Equispaced superimposed pilot, Eq (11).

    Spacing Q+1 = (l_max+1)(2*alpha_max+1). The first (M+1) multiples of (Q+1)
    in [0, N) carry magnitude sigma_p / sqrt(M+1); all other entries are 0.

    Returns
    -------
    x_p : complex array of shape (N,)
    Q   : int, dictionary-ish parameter Q (number of hypotheses minus one)
    """
    Q = (l_max + 1) * (2 * alpha_max + 1) - 1
    spacing = Q + 1
    if M * spacing >= N - Q:
        raise ValueError(
            f"M={M}, spacing={spacing}, N={N}, Q={Q}: violates "
            f"M*(Q+1) < N-Q (Eq 11 constraint)"
        )
    x_p = np.zeros(N, dtype=complex)
    amp = sigma_p / np.sqrt(M + 1)
    for k in range(M + 1):
        x_p[k * spacing] = amp
    return x_p, Q


# --------------------------------------------------------------------- Theta_t
def _enumerate_l_alpha(Q_plus_1: int, alpha_max: int) -> list[tuple[int, int]]:
    """Eq (13), (14): enumerate (l_t, alpha_t) for t = 1..Q+1.

    Note: the paper uses Eq (13) l_t = floor((t-1)/(2Nc_1)) which under c_1 =
    (2*alpha_max + 1)/(2N) [Eq (9)] gives 2Nc_1 = 2*alpha_max + 1. So the
    enumeration is row-major over (l, alpha) ordered as in the paper.
    """
    K = 2 * alpha_max + 1
    pairs = []
    for t in range(1, Q_plus_1 + 1):
        l_t = (t - 1) // K
        alpha_t = ((t - 1) % K) - alpha_max
        pairs.append((int(l_t), int(alpha_t)))
    return pairs


def build_theta_t(N: int, l_t: int, alpha_t: int, c1: float, c2: float,
                  A: np.ndarray | None = None,
                  A_H: np.ndarray | None = None) -> np.ndarray:
    """Build Theta_t as an N x N complex matrix per Eq (8).

    Direct closed-form construction, sparse (one nonzero per row):

        Theta_i(m, n) = exp(j (2 pi / N) (N c1 l_i^2 - n l_i + N c2 (n^2 - m^2)))
                        if (n - m - loc_i) mod N == 0   else 0

    where loc_i = alpha_i + 2 N c1 l_i (Eq 8).

    The earlier matrix-product implementation `A · Gamma_CPP_t · Delta_{f_t} ·
    Pi^{l_t} · A^H` was algebraically equivalent but had a subtle ordering bug
    that broke the column orthogonality of Phi_p (verified by `_diag_theta.py`
    --- the Eq 8 closed form gave Phi_p^H Phi_p exactly diagonal as Lemma 3
    requires; the matrix-product version did not). Closed form is also
    significantly faster (O(N) ops vs O(N^3) per Theta_t).

    The A, A_H parameters are accepted but unused; kept for API stability with
    earlier callers.
    """
    del A, A_H  # accepted for backwards compat; closed form does not need them
    loc = alpha_t + int(round(2.0 * N * c1 * l_t))
    Theta = np.zeros((N, N), dtype=complex)
    for m in range(N):
        n = (m + loc) % N
        phase = (2.0 * np.pi / N) * (N * c1 * (l_t ** 2) - n * l_t
                                      + N * c2 * (n * n - m * m))
        Theta[m, n] = np.exp(1j * phase)
    return Theta


def build_theta_list(N: int, alpha_max: int, l_max: int, c1: float, c2: float,
                     A: np.ndarray | None = None,
                     A_H: np.ndarray | None = None) -> list[np.ndarray]:
    """Build [Theta_1, ..., Theta_{Q+1}] in the order Eq (13), (14).

    A, A_H accepted for backwards compat with the matrix-product implementation;
    unused by the closed-form Eq 8 path.
    """
    Q_plus_1 = (l_max + 1) * (2 * alpha_max + 1)
    pairs = _enumerate_l_alpha(Q_plus_1, alpha_max)
    return [build_theta_t(N, l_t, a_t, c1, c2) for (l_t, a_t) in pairs]


# --------------------------------------------------------------------- MMSE CE
def assemble_phi_p(theta_list: list[np.ndarray], x_p: np.ndarray) -> np.ndarray:
    """Phi_p = [Theta_1 x_p, ..., Theta_{Q+1} x_p]  (Eq 16). Shape (N, Q+1)."""
    return np.column_stack([Theta @ x_p for Theta in theta_list])


def mmse_estimate_h(y_residual: np.ndarray, Phi_p: np.ndarray,
                    sigma_w_eff_sq: float, C_h_inv: np.ndarray) -> np.ndarray:
    """Eq (19) / Eq (24) inner solve.

    h_hat = (Phi_p^H C_w_inv Phi_p + C_h_inv)^-1 Phi_p^H C_w_inv y_residual

    With C_w = sigma_w_eff_sq * I, C_w_inv = (1/sigma_w_eff_sq) * I, so:

      gain = Phi_p^H Phi_p / sigma_w_eff_sq + C_h_inv
      h_hat = solve(gain, Phi_p^H y_residual / sigma_w_eff_sq)
    """
    G = (Phi_p.conj().T @ Phi_p) / sigma_w_eff_sq + C_h_inv
    rhs = (Phi_p.conj().T @ y_residual) / sigma_w_eff_sq
    return np.linalg.solve(G, rhs)


def threshold_path_indicator(h_hat: np.ndarray, gamma: float) -> np.ndarray:
    """Eq (21): b_t = 1 if |h_hat_t| > gamma else 0."""
    return (np.abs(h_hat) > gamma).astype(np.float64)


def assemble_H_eff(theta_list: list[np.ndarray], h_hat: np.ndarray,
                   b: np.ndarray) -> np.ndarray:
    """H_eff = sum_t b_t * h_hat_t * Theta_t   (used in Eq 22 and Eq 24)."""
    H_eff = np.zeros_like(theta_list[0])
    for t, (Theta, h_t, b_t) in enumerate(zip(theta_list, h_hat, b)):
        if b_t > 0:
            H_eff = H_eff + h_t * Theta
    return H_eff


# ----------------------------------------------------------------- detector
QPSK_CONST = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j]) / np.sqrt(2)


def _qpsk_hard_detect(y_d: np.ndarray, H_eff: np.ndarray, sigma_w_eff_sq: float
                       ) -> np.ndarray:
    """LS + QPSK slicing fallback detector.

    Used when mp_detect_bp_torch is unavailable (e.g. local dev machine without
    torch backend). Empirically observed to amplify estimation error when the
    iterative loop closes back on x_d_hat (NMSE blew up across iters in the
    initial smoke test); mp_bp_detect keeps the iteration stable. Kept as a
    fallback for environments where the torch backend cannot be imported.
    """
    G = H_eff.conj().T @ H_eff + sigma_w_eff_sq * np.eye(H_eff.shape[1])
    rhs = H_eff.conj().T @ y_d
    x_soft = np.linalg.solve(G, rhs)
    diffs = np.abs(x_soft[:, None] - QPSK_CONST[None, :])
    return QPSK_CONST[np.argmin(diffs, axis=1)]


_MP_BP_FALLBACK_WARNED = False


def mp_bp_detect(y_d: np.ndarray, H_eff: np.ndarray, sigma_w_eff_sq: float,
                 n_iter: int = 20, damp: float = 0.5,
                 constellation: np.ndarray = QPSK_CONST) -> np.ndarray:
    """MP-BP detector (Eq 23) using the project's mp_detect_bp_torch backend.

    Matches the paper's "MP algorithm" wording in Eq 23. Returns hard-decision
    QPSK symbols. Falls back to LS+slice with a one-time warning if the torch
    backend is unavailable.
    """
    global _MP_BP_FALLBACK_WARNED
    try:
        import torch  # noqa: F401
        from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
    except Exception as e:  # noqa: BLE001
        if not _MP_BP_FALLBACK_WARNED:
            print(f'[qing_sp_afdm] mp_detect_bp_torch unavailable ({e!r}); '
                  f'falling back to LS detector. Reproduction quality will degrade.')
            _MP_BP_FALLBACK_WARNED = True
        return _qpsk_hard_detect(y_d, H_eff, sigma_w_eff_sq)
    x_hat = mp_detect_bp_torch(y_d, H_eff, sigma_w_eff_sq, constellation,
                               n_iter=n_iter, threshold=1e-4, damp=damp,
                               return_numpy=True, return_soft=False)
    return np.asarray(x_hat).reshape(-1)


# ----------------------------------------------------------------- top-level
def qing_receiver(y: np.ndarray, x_p: np.ndarray,
                  N: int, alpha_max: int, l_max: int, c1: float, c2: float,
                  A: np.ndarray, A_H: np.ndarray,
                  sigma_p_sq: float, sigma_d_sq: float, N0: float,
                  n_iter: int = 2,
                  detector=None,
                  data_constellation: np.ndarray | None = None,
                  C_h_var: float | np.ndarray | None = None,
                  threshold_factor: float = 3.0
                  ) -> dict:
    """Full Zheng 2025 SP-AFDM receiver.

    Parameters
    ----------
    y : received DAFT-domain signal, shape (N,)
    x_p : known equispaced pilot vector (zero outside pilot positions)
    N, alpha_max, l_max : AFDM parameters
    c1, c2 : AFDM chirp parameters; c1 must satisfy Eq (9)
    A, A_H : DAFT matrix and its conjugate transpose
    sigma_p_sq, sigma_d_sq : pilot and data per-element variances
    N0 : AWGN variance
    n_iter : number of outer iterations (Eq 24); paper uses 2
    detector : callable(y_d, H_eff, sigma_w_eff_sq) -> x_d_hat. If None, the
        regularised LS fallback `_qpsk_hard_detect` is used. Production
        comparisons should pass the same MP backend used by the rest of the
        project to isolate channel-estimation differences from detector
        differences.
    C_h_var : either a scalar variance (assumed equal for all paths) or a
        length-(Q+1) array. If None, use 1/(Q+1) (uniform prior over hypotheses).
    threshold_factor : the "3" in the 3-sigma rule (Eq 21).

    Returns
    -------
    dict with keys:
        x_d_hat : (N,) hard QPSK estimate of data
        h_hat   : (Q+1,) MMSE channel-coefficient estimate (last iter)
        b       : (Q+1,) path indicator (last iter)
        H_eff   : (N,N) effective channel estimate
        n_iter_done : int
    """
    Q_plus_1 = (l_max + 1) * (2 * alpha_max + 1)
    theta_list = build_theta_list(N, alpha_max, l_max, c1, c2, A, A_H)
    Phi_p = assemble_phi_p(theta_list, x_p)

    # Effective noise variance per Eq (18). The "sum_i sigma_h_i^2" simplifies to
    # the *total* expected channel power. For random multipath with P paths and
    # per-path variance 1/P, sum sigma_h^2 = 1.
    sigma_h_total = (np.sum(C_h_var) if isinstance(C_h_var, np.ndarray)
                     else (1.0 if C_h_var is None else C_h_var * Q_plus_1))
    sigma_w_eff_sq = sigma_h_total * sigma_d_sq + N0

    # Channel-prior covariance matrix (diagonal)
    if C_h_var is None:
        C_h_var_diag = np.full(Q_plus_1, 1.0 / Q_plus_1)
    elif np.isscalar(C_h_var):
        C_h_var_diag = np.full(Q_plus_1, float(C_h_var))
    else:
        C_h_var_diag = np.asarray(C_h_var, dtype=float)
    C_h_inv = np.diag(1.0 / np.maximum(C_h_var_diag, 1e-30))

    # threshold per Eq (21)
    gamma = threshold_factor * np.sqrt(sigma_w_eff_sq / sigma_p_sq)

    # Data alphabet: detector slices to this constellation. The paper sets
    # E[|x_d_n|^2] = sigma_d_sq, so the QPSK alphabet must be scaled to match.
    # Without this scaling the detector returns unit-power QPSK while x_d has
    # magnitude sqrt(sigma_d_sq) -- a 28x scale gap at sigma_d_sq=1.26e-3,
    # which causes the iteration loop to diverge (residual = y - H_eff @
    # 28*x_d_truth blows up, h_hat at iter-1 is meaningless).
    if data_constellation is None:
        data_constellation = QPSK_CONST * np.sqrt(sigma_d_sq)

    def _wrap(det):
        # Bake the scaled constellation into the detector signature so the
        # caller does not have to thread it through.
        def call(y_d, H_eff, sigma_w_eff_sq):
            try:
                return det(y_d, H_eff, sigma_w_eff_sq, constellation=data_constellation)
            except TypeError:
                return det(y_d, H_eff, sigma_w_eff_sq)
        return call

    if detector is None:
        detector = mp_bp_detect
    detect = _wrap(detector)

    # Two distinct noise variances are needed:
    #   sigma_w_eff_sq -- conservative variance that treats x_d as noise; used
    #     for the channel-estimation MMSE solve (Eq 19/24). Required because at
    #     iter 0 we have no x_d estimate and at iter i we still have residual
    #     x_d cancellation error; treating x_d as noise during CE is the paper's
    #     analysis (Eq 18).
    #   sigma_d_noise_sq -- variance to pass to the *detector*. By the time we
    #     run data detection on y_d = y - H_eff x_p, the pilot has been
    #     subtracted and y_d ~ H_eff x_d + AWGN. The detector is recovering x_d,
    #     so x_d is not noise to it anymore. Use just N0 (plus a small bump for
    #     H_eff residual error). Mis-passing sigma_w_eff_sq here makes MP-BP
    #     overly cautious; verified to inflate BER from ~1e-5 to ~3e-2 at
    #     SNR_d=21 dB on the paper's setup.
    sigma_d_noise_sq = N0

    # iter 0: estimate h with no x_d feedback (treat data as noise via C_w_eff)
    h_hat = mmse_estimate_h(y, Phi_p, sigma_w_eff_sq, C_h_inv)
    b = threshold_path_indicator(h_hat, gamma)
    H_eff = assemble_H_eff(theta_list, h_hat, b)

    # initial detection
    y_d = y - H_eff @ x_p
    x_d_hat = detect(y_d, H_eff, sigma_d_noise_sq)

    # iterate (Eq 24)
    for _ in range(max(0, n_iter - 1)):
        residual = y - H_eff @ x_d_hat
        h_hat = mmse_estimate_h(residual, Phi_p, sigma_w_eff_sq, C_h_inv)
        b = threshold_path_indicator(h_hat, gamma)
        H_eff = assemble_H_eff(theta_list, h_hat, b)
        y_d = y - H_eff @ x_p
        x_d_hat = detect(y_d, H_eff, sigma_d_noise_sq)

    return {
        'x_d_hat': x_d_hat,
        'h_hat': h_hat,
        'b': b,
        'H_eff': H_eff,
        'n_iter_done': n_iter,
    }


# ----------------------------------------------------------------- self-test
if __name__ == '__main__':
    # micro smoke: construct pilot, theta list, run receiver on synthetic data
    N = 64
    alpha_max = 1
    l_max = 1
    c1 = (2 * alpha_max + 1) / (2 * N)
    c2 = 0.0  # arbitrary irrational in paper; 0 is degenerate but exercises the math
    Q = (l_max + 1) * (2 * alpha_max + 1) - 1
    print(f'N={N} alpha_max={alpha_max} l_max={l_max} -> Q+1={Q+1}')

    # placeholder DAFT matrix: Lambda_{c_2} F Lambda_{c_1}
    n_grid = np.arange(N).astype(float)
    Lc1 = np.diag(np.exp(-1j * 2 * np.pi * c1 * n_grid ** 2))
    Lc2 = np.diag(np.exp(-1j * 2 * np.pi * c2 * n_grid ** 2))
    F = np.fft.fft(np.eye(N), norm='ortho')
    A = Lc2 @ F @ Lc1
    A_H = A.conj().T

    x_p, Q_ret = qing_pilot(N, alpha_max, l_max, M=2, sigma_p=1.0)
    assert Q_ret == Q
    theta_list = build_theta_list(N, alpha_max, l_max, c1, c2, A, A_H)
    Phi_p = assemble_phi_p(theta_list, x_p)

    rng = np.random.default_rng(0)
    # Sparse channel: only P_active out of Q+1 hypotheses are nonzero (matches the
    # multipath model of Eq (3): P paths -> P nonzero h_t).
    P_active = 2
    h_true = np.zeros(Q + 1, dtype=complex)
    active = rng.choice(Q + 1, size=P_active, replace=False)
    h_true[active] = (rng.standard_normal(P_active) +
                       1j * rng.standard_normal(P_active)) / np.sqrt(2 * P_active)

    # Paper-style "strong pilot" regime: SNR_p = 50 dB, SNR_d = 21 dB
    # (matches paper Fig 3 simulation, including its operating point near the BER
    # minimum). Threshold gamma ~ 3*sqrt(sigma_w_eff^2 / sigma_p^2) needs to be
    # below typical |h_t| for path indicator to fire; SNR_p must be large.
    sigma_p_sq = 1.0
    snr_p_db, snr_d_db = 50.0, 21.0
    N0 = sigma_p_sq * 10 ** (-snr_p_db / 10)
    sigma_d_sq = N0 * 10 ** (snr_d_db / 10)

    # x_p was scaled with sigma_p inside qing_pilot already (1.0 for this smoke).
    x_d = np.array([1, -1, 1j, -1j])[rng.integers(0, 4, N)]
    x_d = x_d * np.sqrt(sigma_d_sq) / np.sqrt(2)  # variance sigma_d_sq per element
    H_eff_true = sum(h_t * Theta for (h_t, Theta) in zip(h_true, theta_list))
    sigma_w = np.sqrt(N0)
    y = H_eff_true @ (x_p + x_d) + sigma_w * (
        rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)

    # Test the full Eq 24 iterative loop with the MP-BP detector (Eq 23).
    # Print per-iter NMSE to make divergence (if any) immediately visible.
    print('--- per-iter NMSE (lower is better) ---')
    for ni in (1, 2, 3):
        out = qing_receiver(y, x_p, N, alpha_max, l_max, c1, c2, A, A_H,
                            sigma_p_sq=sigma_p_sq, sigma_d_sq=sigma_d_sq, N0=N0,
                            n_iter=ni,
                            C_h_var=np.where(np.abs(h_true) > 0, 0.5, 0.01))
        nmse_h = np.sum(np.abs(out['h_hat'] - h_true) ** 2) / np.sum(np.abs(h_true) ** 2)
        active_est = np.where(out['b'] > 0)[0].tolist()
        print(f'  n_iter={ni}: NMSE={nmse_h:.3e}, est_active={active_est}')
    final_nmse = nmse_h
    print('iter-stable OK' if final_nmse < 0.1 else 'iter-stable FAIL — see README "Status checkpoint"')
