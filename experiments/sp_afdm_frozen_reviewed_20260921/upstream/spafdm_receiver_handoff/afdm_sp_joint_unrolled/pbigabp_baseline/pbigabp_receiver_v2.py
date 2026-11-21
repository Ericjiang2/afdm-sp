"""
pbigabp_receiver_v2.py — faithful per-edge PBiGaBP for SP-AFDM.

Reproduces Ranasinghe et al. IEEE TWC 24(2):1602-1619 Feb 2025 (arXiv 2405.16945)
Algorithm 1 with Eq 27-50 verbatim. Per-edge bipartite messages (NOT collapsed).

Per-edge data structure:
  x_msg[n, p]   : per-edge symbol estimate; x_{n, q_p(n)} sent to receive node n
  x_var_msg[n,p]: per-edge symbol variance
  h_msg[n, p]   : per-edge channel estimate; h_p as seen at receive node n
  h_var_msg[n,p]: per-edge channel variance

Sparse exploit: γ_{p:n,m} is nonzero only at m = q_p(n) = (n - δ_p) mod N for AFDM.
So the (n, p) edge ↔ (n, m=q_p(n)) edge — both indexed by the same (n, p) pair.

Eq 33 / Eq 36 variance has 5 terms; terms 1/2/4 are leave-one-out sums over paths
(precomputed accumulators A1/A2/A4 minus per-edge contribution). Term 3 = N_0.
Term 5 differs: Eq 33 uses E_S, Eq 36 uses σ²_h (Bayesian symmetric structure).

Eq 39 / Eq 41 belief: combines messages over q≠n receive-node sums via
total-minus-leave-out. For x: scatter-add over m=q_p(n). For h: simple sum over n.

SP-frame integration (per Codex review):
  x_m = √ρ·zc[m] + √(1-ρ)·d[m] where d is unit-energy QPSK
  Init: x_msg[n, p] = √ρ·zc[q_p(n)], σ²_x[n, p] = (1-ρ)
  Soft replica operates on u = x - √ρ·zc[m], c_x = √((1-ρ)/2)
  Final: x̂_m combines all (n', p') with q_{p'}(n') = m via precision-weighted sum,
         then decode QPSK on u_m = (x̂_m - √ρ·zc[m]) / √(1-ρ)

Final h_p (per Codex): NOT plain average. Precision-weighted combine over n,
then apply σ²_h prior (Bayesian shrinkage).
"""
from __future__ import annotations

import numpy as np


# =====================================================================
# AFDM virtual-tap dictionary helpers
# =====================================================================

def build_path_table(N: int, l_max: int, k_max: int, c1: float, c2: float):
    """Precompute AFDM virtual-tap dictionary metadata.

    Returns paths (list of dicts), Q (int), K (int = 2*k_max+1).
    Each path entry: idx, l, k, delta, q_of_n[N], phase_of_n[N].
    AFDM convention: γ_{p:n,m} nonzero only at m = q_p(n) = (n-δ) mod N
    with phase exp(j2π[-c1·l² + c2·(n²-q²) - l·q/N]).
    """
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    n_arr = np.arange(N, dtype=np.float64)
    paths = []
    for l in range(l_max + 1):
        for k_off in range(K):
            k = k_off - k_max
            delta = l * K + k
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
# Faithful per-edge PBiGaBP
# =====================================================================

def pbigabp_receiver_v2(
    y: np.ndarray,
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    pilot: np.ndarray,                  # (N,) complex, sqrt(rho)·zc convention
    sigma2: float,
    rho: float = 0.5,
    sigma2_h: float = 1.0,
    beta_x: float = 0.3,
    beta_h: float = 0.3,
    i_max: int = 40,
    eps_tol: float = 1e-4,
    return_trajectory: bool = False,
):
    """SISO per-edge PBiGaBP for SP-AFDM joint h + d estimation.

    See module docstring for paper-equation correspondence. Returns dict with
    d_hat (N,) complex, H_eff (N,N) complex, h_hat (Q,), iter_done, converged.
    """
    assert y.shape == (N,)
    assert pilot.shape == (N,)

    # Build path table and (N, P) lookup arrays
    paths, Q, K = build_path_table(N, l_max, k_max, c1, c2)
    P = Q
    phase_np = np.zeros((N, P), dtype=np.complex128)
    q_np = np.zeros((N, P), dtype=np.int64)
    for p_meta in paths:
        p = p_meta['idx']
        phase_np[:, p] = p_meta['phase_of_n']
        q_np[:, p] = p_meta['q_of_n']

    # SP-frame parameters
    P_d = 1.0 - rho
    sqrt_Pd = float(np.sqrt(P_d))
    c_x = float(np.sqrt(P_d / 2.0))   # QPSK soft-replica magnitude (Eq 44)
    E_S = 1.0                          # total per-symbol energy (ρ + (1-ρ))

    # ---- Init per Algorithm 1 ----
    # x_msg[n, p] = pilot at column m = q_p(n) (data part u^(0) = 0)
    pilot_at_m = pilot[q_np]                                 # (N, P)
    x_msg = pilot_at_m.copy()                                # √ρ · zc[q_p(n)]
    x_var_msg = np.full((N, P), P_d, dtype=np.float64)       # data variance E_S = 1-ρ
    # h_msg[n, p] = 0, h_var[n, p] = σ²_h prior
    h_msg = np.zeros((N, P), dtype=np.complex128)
    h_var_msg = np.full((N, P), sigma2_h, dtype=np.float64)

    # Damping memory (initial = current)
    h_msg_prev = h_msg.copy()
    h_var_msg_prev = h_var_msg.copy()
    x_msg_prev = x_msg.copy()
    x_var_msg_prev = x_var_msg.copy()

    converged = False
    iter_done = 0
    traj = [] if return_trajectory else None

    eps_safe = 1e-30

    for it in range(1, i_max + 1):
        iter_done = it

        # ------------------------------------------------------------
        # Snapshot iter-start state (BP synchronous: both updates use
        # h^(i-1), x^(i-1) per Eq 30/32/33/35/36 explicit (i-1) refs)
        # ------------------------------------------------------------
        h_msg_old = h_msg
        h_var_msg_old = h_var_msg
        x_msg_old = x_msg
        x_var_msg_old = x_var_msg

        # Forward at (n, p) from OLD state
        contrib = phase_np * x_msg_old                        # (N, P)
        weighted = h_msg_old * contrib                         # (N, P)
        z_total = weighted.sum(axis=1)                         # (N,)
        x_abs2 = np.abs(x_msg_old) ** 2                        # (N, P)
        h_abs2 = np.abs(h_msg_old) ** 2                        # (N, P)
        A1 = (h_var_msg_old * x_abs2).sum(axis=1)              # (N,)
        A2 = (x_var_msg_old * h_abs2).sum(axis=1)              # (N,)
        A4 = (h_var_msg_old * x_var_msg_old).sum(axis=1)       # (N,)

        # ============================================================
        # CHANNEL ESTIMATION (Algorithm 1 lines 1-6)
        # ============================================================
        y_tilde_h = y[:, None] - z_total[:, None] + weighted   # Eq 35
        sigma_h_tilde = (
            (A1[:, None] - h_var_msg_old * x_abs2)             # term 1
            + (A2[:, None] - x_var_msg_old * h_abs2)           # term 2
            + sigma2                                             # term 3
            + (A4[:, None] - h_var_msg_old * x_var_msg_old)    # term 4
            + sigma2_h * x_var_msg_old                          # term 5 (σ²_h prior)
        )
        sigma_h_tilde = np.maximum(sigma_h_tilde, eps_safe)

        prec_h = x_abs2 / sigma_h_tilde                        # (N, P)
        weighted_h = np.conj(contrib) * y_tilde_h / sigma_h_tilde
        total_prec_h = prec_h.sum(axis=0)
        total_w_h = weighted_h.sum(axis=0)
        prec_extr_h = np.maximum(total_prec_h[None, :] - prec_h, eps_safe)
        sigma_h_post_var = 1.0 / prec_extr_h
        h_tilde = sigma_h_post_var * (total_w_h[None, :] - weighted_h)

        denom_h = sigma_h_post_var + sigma2_h
        h_post_mean = sigma2_h * h_tilde / denom_h            # Eq 47
        h_post_var = sigma2_h * sigma_h_post_var / denom_h    # Eq 48

        h_msg_new = beta_h * h_post_mean + (1.0 - beta_h) * h_msg_prev      # Eq 49
        h_var_msg_new = beta_h * h_post_var + (1.0 - beta_h) * h_var_msg_prev  # Eq 50

        # ============================================================
        # DATA ESTIMATION (Algorithm 1 lines 7-12) — uses OLD h, x
        # ============================================================
        y_tilde_x = y[:, None] - z_total[:, None] + weighted   # Eq 30 (same as ỹ_h structurally)
        sigma_x_tilde = (
            (A1[:, None] - h_var_msg_old * x_abs2)             # term 1
            + (A2[:, None] - x_var_msg_old * h_abs2)           # term 2
            + sigma2                                             # term 3
            + (A4[:, None] - h_var_msg_old * x_var_msg_old)    # term 4
            + E_S * h_var_msg_old                               # term 5 (E_S, NOT σ²_h)
        )
        sigma_x_tilde = np.maximum(sigma_x_tilde, eps_safe)

        # γ̃_{x:m=q_p(n), q=n} = h_msg_old[n, p] · phase[n, p]  (Eq 32 uses ĥ^(i-1))
        prec_x = h_abs2 / sigma_x_tilde
        weighted_x = np.conj(h_msg_old * phase_np) * y_tilde_x / sigma_x_tilde

        flat_m = q_np.ravel()
        total_prec_x_per_m = np.zeros(N, dtype=np.float64)
        total_w_x_per_m = np.zeros(N, dtype=np.complex128)
        np.add.at(total_prec_x_per_m, flat_m, prec_x.ravel())
        np.add.at(total_w_x_per_m, flat_m, weighted_x.ravel())

        prec_extr_x = np.maximum(total_prec_x_per_m[q_np] - prec_x, eps_safe)
        sigma_x_post_var = 1.0 / prec_extr_x
        x_tilde_pre = sigma_x_post_var * (total_w_x_per_m[q_np] - weighted_x)

        u_tilde = x_tilde_pre - pilot_at_m
        denom_u = np.maximum(sigma_x_post_var, 1e-12)
        arg_re = np.clip(2.0 * c_x * np.real(u_tilde) / denom_u, -50.0, 50.0)
        arg_im = np.clip(2.0 * c_x * np.imag(u_tilde) / denom_u, -50.0, 50.0)
        tanh_re = np.tanh(arg_re)
        tanh_im = np.tanh(arg_im)
        u_hat = c_x * (tanh_re + 1j * tanh_im)
        u_var_new = c_x ** 2 * ((1.0 - tanh_re ** 2) + (1.0 - tanh_im ** 2))

        x_msg_post = pilot_at_m + u_hat
        x_var_msg_post = u_var_new

        x_msg_new = beta_x * x_msg_post + (1.0 - beta_x) * x_msg_prev      # Eq 45
        x_var_msg_new = beta_x * x_var_msg_post + (1.0 - beta_x) * x_var_msg_prev  # Eq 46

        # ------------------------------------------------------------
        # Commit BOTH at end of iter (synchronous schedule)
        # ------------------------------------------------------------
        h_msg_prev = h_msg_old
        h_var_msg_prev = h_var_msg_old
        x_msg_prev = x_msg_old
        x_var_msg_prev = x_var_msg_old
        h_msg = h_msg_new
        h_var_msg = h_var_msg_new
        x_msg = x_msg_new
        x_var_msg = x_var_msg_new

        denom_norm = np.linalg.norm(x_msg_prev) + 1e-12
        rel_change = float(np.linalg.norm(x_msg - x_msg_prev) / denom_norm)
        if return_trajectory:
            traj.append(dict(it=it, rel_change=rel_change,
                              x_norm=float(np.linalg.norm(x_msg)),
                              h_norm=float(np.linalg.norm(h_msg)),
                              h_var_mean=float(np.mean(h_var_msg)),
                              x_var_mean=float(np.mean(x_var_msg))))
        if rel_change < eps_tol and it > 1:
            converged = True
            break

    # ============================================================
    # FINAL EXTRACTION
    # ============================================================
    # h_p marginal: precision-weighted combine over n + Bayesian prior
    h_post_final_prec = (1.0 / np.maximum(h_var_msg, eps_safe)).sum(axis=0)   # (P,)
    h_post_final_w = (h_msg / np.maximum(h_var_msg, eps_safe)).sum(axis=0)    # (P,)
    h_post_final_var_pre = 1.0 / np.maximum(h_post_final_prec, eps_safe)
    h_post_final_mean_pre = h_post_final_var_pre * h_post_final_w
    # Apply σ²_h prior shrinkage
    h_p = sigma2_h * h_post_final_mean_pre / (h_post_final_var_pre + sigma2_h)

    # x_m marginal: precision-weighted combine over (n, p) with q_p(n)=m
    x_total_prec_m = np.zeros(N, dtype=np.float64)
    x_total_w_m = np.zeros(N, dtype=np.complex128)
    inv_xv = 1.0 / np.maximum(x_var_msg, eps_safe)
    np.add.at(x_total_prec_m, q_np.ravel(), inv_xv.ravel())
    np.add.at(x_total_w_m, q_np.ravel(), (x_msg * inv_xv).ravel())
    x_post_var_m = 1.0 / np.maximum(x_total_prec_m, eps_safe)
    x_post_mean_m = x_post_var_m * x_total_w_m                # (N,)

    # Decode QPSK on data part u_m = (x_m - √ρ·zc[m]) / √(1-ρ)
    u_final = (x_post_mean_m - pilot) / sqrt_Pd               # unit-energy QPSK
    d_re = np.where(np.real(u_final) >= 0, 1.0, -1.0) / np.sqrt(2.0)
    d_im = np.where(np.imag(u_final) >= 0, 1.0, -1.0) / np.sqrt(2.0)
    d_hat = sqrt_Pd * (d_re + 1j * d_im)

    # Reconstruct H_eff[n, m] = Σ_p ĥ_p · phase_p[n] · 1{m = q_p(n)}
    H_eff = np.zeros((N, N), dtype=np.complex128)
    n_idx = np.arange(N)
    for p in range(P):
        if abs(h_p[p]) < 1e-12:
            continue
        H_eff[n_idx, q_np[:, p]] += h_p[p] * phase_np[:, p]

    return dict(
        d_hat=d_hat,
        H_eff=H_eff,
        h_hat=h_p,
        iter_done=iter_done,
        converged=bool(converged),
        x_hat=x_post_mean_m,
        u_hat=u_final,
        trajectory=traj,
    )
