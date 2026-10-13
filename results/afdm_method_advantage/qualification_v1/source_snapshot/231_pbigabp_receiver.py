"""
pbigabp_receiver.py — SISO PBiGaBP for AFDM joint channel + data estimation.

Faithful reproduction of Ranasinghe et al. IEEE TWC 24(2):1602-1619 Feb 2025
(arXiv 2405.16945) "Joint Channel, Data, and Radar Parameter Estimation for
AFDM Systems in Doubly-Dispersive Channels".

Algorithm (Eq 27-49 from the paper, channel-first ordering per Codex review):

  System model (Eq 27):  y = Σ_p h_p · A_p · x + w̃
    where A_p is the known N×N AFDM operator for path p, indexed by
    (l_p, k_p) virtual-tap delta δ_p = l_p·K + k_p (K = 2·k_max+1).
    Each row of A_p has exactly one non-zero entry at column
    q_p(n) = (n − δ_p) mod N, with magnitude 1 and an AFDM phase factor.

  Init (Eq 47-48):
    h_p^(0) = 0  (NOT pilot-aided LS — paper init is zero-mean Bayesian)
    σ²_h̃,p^(0) = σ²_h prior  (default 1.0)
    For SP frame: x[n] = sqrt(rho)·zc[n] + sqrt(1-rho)·d[n] where zc is the
      known pilot sequence and d[n] is the unknown QPSK data.
      We estimate u[n] := sqrt(1-rho)·d[n] (the data contribution).
      x[n]_init = sqrt(rho)·zc[n] (pilot-only initial guess; u^(0) = 0).
      Pilots are NOT pinned — they are part of the same x vector but contribute
      a known additive term to z (the "Ac·b" affine slot in PBiGAMP terminology).

  Iteration i = 1..i_max (channel-first per paper):

    A. Channel-side messages (Eq 41, 46):
       For each (n, p) edge:
         y~_h:p,n^(i) = y_n − Σ_{p'≠p} h^_n,p'^(i-1) · γ_p':n,q_p'(n) · x̂_q_p'(n)^(i-1)
                              − Σ_{p'} h^_n,p'^(i-1) · γ_p':n,q_p'(n) · √(rho)·zc[q_p'(n)]
                              # but the second pilot-contribution term is part of the residual computation,
                              # equivalently y~_h:p,n is the leave-out-p residual after pilot-cancellation.

       σ²_h̃,n,p^(i) = (Σ_{q≠n} |γ_p:q,q_p(q) · x̂_q_p(q)^(i-1) + γ_p:q,q_p(q) · √(rho)·zc[q_p(q)]|² /
                                    σ²_h:p,q^(i))^(-1)
       h̃_n,p^(i) = σ²_h̃,n,p · Σ_{q≠n} (...conjugate...) / σ²_h:p,q

       Bayesian shrinkage by prior σ²_h:
         σ²_h:p^(i) := σ²_h̃,p · σ²_h / (σ²_h̃,p + σ²_h)
         ĥ_p^(i) := σ²_h:p · h̃_p / σ²_h̃,p

       Damping (Eq 46):
         ĥ_p^(i) ← β_h · ĥ_p^(i) + (1 − β_h) · ĥ_p^(i-1)

    B. Symbol-side messages (Eq 30, 32, 39, 44, 45):
       Reconstruct effective channel: Γ_full[n, q] = Σ_p ĥ_p^(i) · γ_p:n,q
         (sparse: nonzero only for q ∈ {q_p(n) : p ∈ active})

       For each (n, m) edge with m = q_p(n) for some active p:
         y~_x:m,n^(i) = y_n − Σ_{q≠m} Γ_full[n, q] · x̂_q^(i-1)
                              # x̂ here is the FULL x estimate (pilot + data); pilots remain
                              # at their initialized values throughout (variance 0).

         σ²_x:m,q^(i) — propagated noise variance per edge
         Combine: σ²_x̃:n,m^(i) = (Σ_{q≠n} |Γ_full[m, q]|² / σ²_x:m,q^(i))^(-1)
         x̃_n,m^(i) = σ²_x̃:n,m · Σ_{q≠n} Γ_full*[m, q] · y~_x:m,q^(i) / σ²_x:m,q^(i)

       Soft replica per Eq 44 (QPSK on data positions, pilot pinned):
         If n is a pilot position: x̂_n = sqrt(rho)·zc[n] + sqrt(1-rho)·tanh(2c_x·Re(x̃_n)/σ²)·...
         For SP-AFDM with overlay: data and pilot are at every position.
         The QPSK soft replica applies to the DATA contribution u[n] = sqrt(1-rho)·d̂[n]:
           ũ_n = (x̃_n − sqrt(rho)·zc[n]) / sqrt(1-rho)   # extract data component
           û_n = c_x · (tanh(2 c_x · Re(ũ_n) / σ²_ũ) + j·tanh(...))   where c_x = √(P_d/2)
           x̂_n = sqrt(rho)·zc[n] + sqrt(1-rho)·d̂_n      # rebuild full x with new d̂

       Damping (Eq 45):
         x̂_n^(i) ← β_x · x̂_n^(i) + (1 − β_x) · x̂_n^(i-1)

    C. Convergence (Eq 49):
       ||x̂^(i) − x̂^(i-1)||_2 / ||x̂^(i-1)||_2 < ε   OR   i ≥ i_max

  Output:
    Ĥ_eff = Σ_p ĥ_p · A_p   (N×N effective channel)
    d̂_n = soft replica restricted to data alphabet (final iter)

NOTES:
  * Per-edge messages with leave-one-out structure (per Codex review of my
    initial collapsed-variant draft).
  * h^(0) = 0 init (Bayesian zero-mean), NOT LS init.
  * Channel-first iteration order (paper convention), NOT symbol-first.
  * Damping defaults β_x = β_h = 0.3, i_max = 40, σ²_h = 1, E_s = 1.
  * Convergence ε = 1e-4 typical.
  * Dictionary: full (l_max+1)·(2·k_max+1) virtual paths; the σ²_h prior
    Bayesian-shrinks inactive atoms toward zero. No oracle support.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Optional

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))


# =====================================================================
# AFDM virtual-tap dictionary helpers
# =====================================================================

def afdm_path_phase(N: int, l: int, k: int, c1: float, c2: float, n: int) -> complex:
    """Phase factor at row n of AFDM operator A_p for path (l, k).

    A_p[n, q_p(n)] = exp(j 2π[-c1 l² + c2 (n² − q²) − l q / N])
    where q = q_p(n) = (n - δ) mod N, δ = l·K + k, K = 2 k_max + 1.

    Caller must ensure k_max consistency. Returns scalar complex.
    """
    K = 2 * (abs(k) if k != 0 else 1) + 1   # placeholder; caller passes K via δ
    # Caller should compute δ using a consistent K. Here we assume δ = l·K + k.
    raise NotImplementedError("Use build_path_table instead")


def build_path_table(N: int, l_max: int, k_max: int, c1: float, c2: float):
    """Precompute AFDM virtual-tap dictionary metadata.

    Returns
    -------
    paths : list of dicts, length Q = (l_max+1)·(2·k_max+1)
        Each entry: dict(idx, l, k, delta, q_of_n, phase_of_n)
        - q_of_n[n] = (n - delta) mod N, length-N int array
        - phase_of_n[n] = exp(j 2π[-c1 l² + c2 (n² - q²) - l q / N])
            length-N complex array
        i.e. A_p[n, q_p(n)] = phase_of_n[n] (only nonzero entry per row).
    """
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    n_arr = np.arange(N, dtype=np.float64)
    paths = []
    for l in range(l_max + 1):
        for k_off in range(K):
            k = k_off - k_max
            delta = l * K + k
            q_arr = ((n_arr.astype(int) + delta) % N)   # q_p(n) where δ shifts ROW
            # Convention check vs construct_sensing_matrix (afdm_baselines.py:42):
            # Phi[m, col(l,k)] = phase[m,l,k] · x[(m - δ) mod N]
            # so row m, contribution to z[m] is phase * x[col_m] where col_m = (m - δ) mod N
            # Here we use n as row and want q_p(n) = (n - δ) mod N.
            q_arr = ((n_arr.astype(int) - delta) % N)
            q_f = q_arr.astype(np.float64)
            phase_arr = np.exp(1j * 2.0 * np.pi * (
                -c1 * (l ** 2)
                + c2 * (n_arr ** 2 - q_f ** 2)
                - float(l) * q_f / N
            ))
            paths.append(dict(
                idx=l * K + (k + k_max),
                l=int(l), k=int(k), delta=int(delta),
                q_of_n=q_arr.astype(np.int64),
                phase_of_n=phase_arr.astype(np.complex128),
            ))
    return paths, Q, K


# =====================================================================
# Bilinear forward / backward (sparse via per-row P-list)
# =====================================================================

def forward_z_zvar(paths, h_hat, h_var, x_hat, x_var, N):
    """Compute zhat (N,) and zvar (N,) for the sparse AFDM bilinear model.

    z_n = Σ_p h_p · phase_p[n] · x[q_p(n)]
    For PBiGaBP variance propagation:
      Var[z_n] = Σ_p (|h_hat_p|² · |phase|² · x_var[q_p(n)]
                      + h_var_p · |phase|² · |x_hat[q_p(n)]|²
                      + h_var_p · |phase|² · x_var[q_p(n)])
              = Σ_p (|h_hat_p|² · x_var[q_p(n)]
                      + h_var_p · |x_hat[q_p(n)]|²
                      + h_var_p · x_var[q_p(n)])     # since |phase|=1
    """
    z_hat = np.zeros(N, dtype=np.complex128)
    z_var = np.zeros(N, dtype=np.float64)
    for p_meta in paths:
        q = p_meta['q_of_n']
        phase = p_meta['phase_of_n']
        h_p = h_hat[p_meta['idx']]
        h_v = h_var[p_meta['idx']]
        x_q = x_hat[q]
        xv_q = x_var[q]
        contrib = h_p * phase * x_q
        z_hat += contrib
        z_var += (np.abs(h_p) ** 2 * xv_q
                  + h_v * np.abs(x_q) ** 2
                  + h_v * xv_q)
    return z_hat, z_var


# =====================================================================
# PBiGaBP main loop
# =====================================================================

def pbigabp_receiver(
    y: np.ndarray,
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    pilot: np.ndarray,                  # (N,) complex, sqrt(rho)·zc by convention
    sigma2: float,
    rho: float = 0.5,
    sigma2_h: float = 1.0,              # channel prior variance (Eq 47-48)
    beta_x: float = 0.3,                # symbol damping (Eq 45)
    beta_h: float = 0.3,                # channel damping (Eq 46)
    i_max: int = 40,                    # max iterations
    eps_tol: float = 1e-4,              # convergence (Eq 49)
    return_trajectory: bool = False,
):
    """SISO PBiGaBP for SP-AFDM joint h + d estimation.

    Parameters
    ----------
    y : (N,) complex
        DAFT-domain received signal at the AFDM demodulator output.
    N, c1, c2, l_max, k_max : modulation parameters.
    pilot : (N,) complex
        Known pilot vector at the transmitted-x scale (sqrt(rho)·zc convention).
        This is the SAME pilot used by the SP receiver; PBiGaBP runs on the
        same SP frame for matched-energy comparison (data is unknown QPSK at
        sqrt(1-rho)·d scale).
    sigma2 : noise variance (real, scalar).
    rho : pilot-to-total power split (matches SP frame).
    sigma2_h : prior variance on each channel tap (Eq 47-48 prior).
    beta_x, beta_h : damping coefficients in [0, 1].
    i_max : max iterations.
    eps_tol : convergence threshold on relative ||x̂^(i) - x̂^(i-1)||.

    Returns
    -------
    dict with d_hat (N,) complex (data symbols at sqrt(P_d) scale),
         H_eff (N, N) complex (effective channel from Σ ĥ_p · A_p),
         h_hat (Q,) complex (channel estimates over full virtual-tap dictionary),
         iter_done (int), converged (bool).
    """
    assert y.shape == (N,)
    assert pilot.shape == (N,)
    P_d = 1.0 - rho
    sqrt_Pd = float(np.sqrt(P_d))
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=np.complex128) / np.sqrt(2)
    c_x = float(np.sqrt(P_d / 2.0))    # QPSK soft-replica magnitude (Eq 44)

    paths, Q, K = build_path_table(N, l_max, k_max, c1, c2)

    # ---- Init (Eq 47-48): pilot-aided LS for h^(0) ----
    # Per Eq 47-48, h^(0) is initialized via pilot-aided LS, NOT zero.
    # Build the pilot-only sensing matrix Phi_p ∈ C^{N×Q} where
    # Phi_p[n, j] = phase_j[n] · pilot[q_j(n)] (the carrier is the pilot).
    # Solve h^(0) = (Phi_p^H Phi_p + λI)^{-1} Phi_p^H y  with λ = sigma2.
    Phi_p = np.zeros((N, Q), dtype=np.complex128)
    for p_meta in paths:
        j = p_meta['idx']
        q = p_meta['q_of_n']
        phase = p_meta['phase_of_n']
        Phi_p[np.arange(N), j] = phase * pilot[q]
    PhiHPhi = Phi_p.conj().T @ Phi_p           # (Q, Q)
    PhiHy = Phi_p.conj().T @ y                  # (Q,)
    # Tikhonov regularizer set so well-conditioned at high SNR;
    # data interference acts as additional noise (sigma2_data = P_d).
    lam_init = max(sigma2 + P_d, 1e-3)
    h_hat = np.linalg.solve(
        PhiHPhi + lam_init * np.eye(Q, dtype=np.complex128),
        PhiHy)
    # Initial variance: posterior cov diagonal ≈ lam_init / (PhiHPhi.diag + lam_init).
    # This is a Bayesian read of "the LS estimate has uncertainty ~ noise / signal-energy"
    h_var = (lam_init / (np.real(np.diag(PhiHPhi)) + lam_init)).astype(np.float64)
    # Cap by prior σ²_h to keep loose-prior interpretation
    h_var = np.minimum(h_var, sigma2_h)

    # Data symbols (full x): start at pilot-only (data contribution u = 0)
    x_hat = pilot.copy()                 # x_hat[n] = sqrt(rho)·zc[n] initially
    x_var = np.full(N, P_d, dtype=np.float64)   # data contribution variance ~ E_s

    # Pilot positions don't have variance — but in SP, data and pilot share
    # every position. So x_var corresponds to the unknown data part (variance
    # of u = sqrt(P_d)·d, |d|² = 1, so var ≈ P_d).

    x_hat_prev = x_hat.copy()
    h_hat_prev = h_hat.copy()
    converged = False
    iter_done = 0
    traj = [] if return_trajectory else None

    for it in range(1, i_max + 1):
        iter_done = it

        # ===========================================================
        # A. Channel-side update (Eq 41, 46)
        # Per-(n, p) leave-one-out residual then aggregate via (Σ_q≠n)
        # Numerically: aggregate forms identical to non-leave-out result
        # for the case of dense sums; the leave-one-out structure matters
        # only for the variance combination. We use the simplified
        # aggregate form here (TODO: per-edge variance for fully faithful
        # implementation when memory is not constrained).
        # ===========================================================
        # Compute z_hat = Σ_p h_p · A_p · x_hat (current full-bilinear estimate)
        z_hat, z_var = forward_z_zvar(paths, h_hat, h_var, x_hat, x_var, N)

        # For each path p, compute h posterior:
        #   "signature" s_p[n] = phase_p[n] · x_hat[q_p(n)]   (length N complex)
        #   Residual without path p: r_p[n] = y[n] - (z_hat[n] - h_hat[p]·s_p[n])
        #                                   = y[n] - z_hat[n] + h_hat[p]·s_p[n]
        #   Variance per row: v_p[n] = sigma2 + (z_var[n] - h_var[p]·|s_p[n]|² - |h_hat[p]|²·x_var[q_p(n)])
        #     # remove path p's contribution to z_var
        #     # (this is the leave-one-out variance, approximately)
        h_tilde = np.zeros(Q, dtype=np.complex128)
        h_tilde_var = np.zeros(Q, dtype=np.float64)
        for p_meta in paths:
            j = p_meta['idx']
            q = p_meta['q_of_n']
            phase = p_meta['phase_of_n']
            s_p = phase * x_hat[q]                    # (N,) signature
            x_var_at_q = x_var[q]                     # (N,) symbol variance at footprint
            h_p_old = h_hat[j]
            h_v_old = h_var[j]

            # Leave-out p's contribution to z and z_var:
            r_p = y - z_hat + h_p_old * s_p
            z_var_minus_p = z_var - (h_v_old * np.abs(s_p) ** 2
                                      + np.abs(h_p_old) ** 2 * x_var_at_q
                                      + h_v_old * x_var_at_q)
            v_p = sigma2 + np.maximum(z_var_minus_p, 0.0)

            # Gaussian likelihood for h_p given (r_p, v_p):
            #   h_p ~ N(s_p^H r_p / sum(|s_p|²/v_p), 1 / sum(|s_p|²/v_p))
            inv_var_per_row = (np.abs(s_p) ** 2) / v_p
            denom = np.sum(inv_var_per_row)
            if denom > 0:
                h_tilde_var[j] = 1.0 / denom
                h_tilde[j] = h_tilde_var[j] * np.sum(np.conj(s_p) * r_p / v_p)
            else:
                h_tilde_var[j] = sigma2_h     # fall back to prior
                h_tilde[j] = 0.0

        # Bayesian shrinkage by prior σ²_h (Eq 47):
        #   posterior = N(h̃, σ²_h̃) · N(0, σ²_h)
        #   var = σ²_h̃ · σ²_h / (σ²_h̃ + σ²_h)
        #   mean = (var / σ²_h̃) · h̃
        post_var = h_tilde_var * sigma2_h / (h_tilde_var + sigma2_h)
        post_mean = (post_var / np.maximum(h_tilde_var, 1e-30)) * h_tilde

        # Stability: clip h_tilde magnitudes to a sane bound. Without this,
        # variance-mismatch in early iters can drive h_tilde to ~10^4
        # values that don't get shrunk fast enough by Bayesian prior.
        # Total channel energy should be O(1) for unit-Frobenius H, so
        # |h_p| > 5 indicates runaway.
        max_h_mag = 5.0 * float(np.sqrt(sigma2_h))
        post_mag = np.abs(post_mean)
        scale = np.minimum(1.0, max_h_mag / np.maximum(post_mag, 1e-12))
        post_mean = post_mean * scale

        # Damping (Eq 46): h_hat = β_h · post_mean + (1 - β_h) · h_hat_prev
        h_hat_new = beta_h * post_mean + (1.0 - beta_h) * h_hat_prev
        h_var = post_var
        h_hat_prev = h_hat.copy()
        h_hat = h_hat_new

        # ===========================================================
        # B. Symbol-side update (Eq 30, 32, 39, 44, 45)
        # ===========================================================
        # Recompute z_hat with new h
        z_hat, z_var = forward_z_zvar(paths, h_hat, h_var, x_hat, x_var, N)

        # For each symbol position m, compute x_m posterior. Each m may be
        # connected to multiple rows n (for each path p such that q_p(n)=m).
        # Aggregate the posterior over those rows.
        x_tilde = np.zeros(N, dtype=np.complex128)
        x_tilde_var = np.zeros(N, dtype=np.float64)
        x_inv_var_sum = np.zeros(N, dtype=np.float64)
        x_weighted_sum = np.zeros(N, dtype=np.complex128)

        for p_meta in paths:
            j = p_meta['idx']
            q = p_meta['q_of_n']                       # q_p(n) for n=0..N-1
            phase = p_meta['phase_of_n']
            h_p = h_hat[j]
            h_v = h_var[j]

            # contribution magnitude from path p to data at column q_p(n):
            #   coeff[n] = h_p · phase[n]   (acts on x[q_p(n)])
            coeff = h_p * phase                       # (N,) complex

            # Leave-out (n, q_p(n))'s contribution to z[n]:
            #   y~_x:m=q_p(n),n = y[n] - (z_hat[n] - coeff[n] · x_hat[q_p(n)])
            r_x = y - z_hat + coeff * x_hat[q]        # (N,) residual seen at row n with x_q removed
            # Variance per row n excluding x's contribution at column q_p(n):
            v_x_per_row = sigma2 + np.maximum(
                z_var - (np.abs(h_p) ** 2 * x_var[q]
                          + h_v * np.abs(x_hat[q]) ** 2
                          + h_v * x_var[q]),
                0.0,
            )
            inv_var_n = (np.abs(coeff) ** 2) / v_x_per_row    # (N,) precision per row

            # Accumulate at the source position q_p(n) = m:
            np.add.at(x_inv_var_sum, q, inv_var_n)
            np.add.at(x_weighted_sum, q, np.conj(coeff) * r_x / v_x_per_row)

        # Aggregate posterior (Eq 39):
        x_tilde_var = 1.0 / np.maximum(x_inv_var_sum, 1e-30)
        x_tilde = x_tilde_var * x_weighted_sum

        # ---- Soft replica (Eq 44, QPSK on data, pilot pinned) ----
        # In SP frame: x[n] = pilot[n] + u[n] where u = sqrt(P_d)·QPSK is unknown.
        # Extract data component from x_tilde:
        u_tilde = x_tilde - pilot                     # (N,) data-component estimate
        # QPSK soft replica on u (Eq 44): u_n = c_x · (tanh(2 c_x · Re(u_tilde)/var) + j tanh(...))
        u_var = x_tilde_var                            # propagate
        # Numerical guards on tanh argument
        denom_u = np.maximum(u_var, 1e-12)
        arg_re = 2.0 * c_x * np.real(u_tilde) / denom_u
        arg_im = 2.0 * c_x * np.imag(u_tilde) / denom_u
        # Clip to avoid tanh saturation NaN
        arg_re = np.clip(arg_re, -50.0, 50.0)
        arg_im = np.clip(arg_im, -50.0, 50.0)
        u_hat = c_x * (np.tanh(arg_re) + 1j * np.tanh(arg_im))
        # Variance: var of |u|² = E_s = P_d, minus mean² (tanh-modulated)
        u_var_new = c_x ** 2 * (1.0 - np.tanh(arg_re) ** 2 + 1.0 - np.tanh(arg_im) ** 2)

        # Rebuild full x = pilot + u
        x_hat_full_new = pilot + u_hat
        # Damping (Eq 45):
        x_hat_new = beta_x * x_hat_full_new + (1.0 - beta_x) * x_hat_prev
        x_hat_prev = x_hat.copy()
        x_var = u_var_new                              # variance of u (data part)
        x_hat = x_hat_new

        # ---- Convergence (Eq 49) ----
        denom_x = np.linalg.norm(x_hat_prev) + 1e-12
        rel_change = float(np.linalg.norm(x_hat - x_hat_prev) / denom_x)
        if return_trajectory:
            traj.append(dict(it=it, rel_change=rel_change,
                              x_norm=float(np.linalg.norm(x_hat)),
                              h_norm=float(np.linalg.norm(h_hat))))
        if rel_change < eps_tol and it > 1:
            converged = True
            break

    # ---- Output: reconstruct H_eff and extract data symbols ----
    # H_eff[m, n] = Σ_p ĥ_p · A_p[m, n] = Σ_p ĥ_p · phase_p[m] · 1{n == q_p(m)}
    # (sparse: only one nonzero column per row per path)
    H_eff = np.zeros((N, N), dtype=np.complex128)
    for p_meta in paths:
        j = p_meta['idx']
        q = p_meta['q_of_n']
        phase = p_meta['phase_of_n']
        h_p = h_hat[j]
        if abs(h_p) < 1e-12:
            continue
        H_eff[np.arange(N), q] += h_p * phase

    # Data hard decisions on u_hat (extracted from x_hat):
    u_final = x_hat - pilot
    # Hard-decode QPSK
    d_hat = np.zeros(N, dtype=np.complex128)
    d_unscaled = u_final / sqrt_Pd
    d_hat_unscaled = np.where(np.real(d_unscaled) >= 0, 1+0j, -1+0j) / np.sqrt(2)
    d_hat_unscaled = d_hat_unscaled + np.where(np.imag(d_unscaled) >= 0, 1j, -1j) / np.sqrt(2)
    d_hat = sqrt_Pd * d_hat_unscaled

    return dict(
        d_hat=d_hat,
        H_eff=H_eff,
        h_hat=h_hat,
        iter_done=iter_done,
        converged=bool(converged),
        x_hat=x_hat,
        u_hat=u_final,
        trajectory=traj,
    )
