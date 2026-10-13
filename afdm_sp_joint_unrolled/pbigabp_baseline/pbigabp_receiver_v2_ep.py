"""
pbigabp_receiver_v2_ep.py — EP-frame variant of v2 for paper-faithful reproduction.

Paper Fig 4 setup: single pilot at m_0 + null guard of (B-1) positions + (N-B) data
symbols. Pilot and guard positions have σ²_x = 0 (known/frozen), data positions
get standard QPSK soft replica.

Reuses v2's per-edge bipartite BP machinery; differs only in:
  - init: x_msg[n, p] = x_init[q_p(n)] (pilot at m_0, zero at guards/data)
          x_var_msg[n, p] = x_var_init[q_p(n)] (0 at pilot+guard, E_S at data)
  - per-iter freeze: pilot+guard positions never update; only data positions get
    soft replica + damping
  - final decoding: only at data positions
"""
from __future__ import annotations

import numpy as np

from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver_v2 import (
    build_path_table,
)


def pbigabp_receiver_v2_ep(
    y: np.ndarray,
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    pilot_value: complex,             # scalar pilot value at m_0
    pilot_idx: int,                   # m_0 (single pilot position)
    guard_idx: np.ndarray,            # 1-D int array of null-guard positions
    data_idx: np.ndarray,             # 1-D int array of data positions
    sigma2: float,
    sigma2_h: float = 1.0,
    E_S: float = 1.0,
    beta_x: float = 0.3,
    beta_h: float = 0.3,
    i_max: int = 40,
    eps_tol: float = 1e-4,
    return_trajectory: bool = False,
):
    """SISO per-edge PBiGaBP, EP frame (single pilot + null guard + data)."""
    assert y.shape == (N,)
    paths, Q, K = build_path_table(N, l_max, k_max, c1, c2)
    P = Q
    phase_np = np.zeros((N, P), dtype=np.complex128)
    q_np = np.zeros((N, P), dtype=np.int64)
    for p_meta in paths:
        p = p_meta['idx']
        phase_np[:, p] = p_meta['phase_of_n']
        q_np[:, p] = p_meta['q_of_n']

    c_x = float(np.sqrt(E_S / 2.0))   # QPSK soft-replica magnitude

    # Per-position init: pilot at m_0, zero elsewhere; variance E_S at data, 0 at pilot+guard
    x_init = np.zeros(N, dtype=np.complex128)
    x_init[pilot_idx] = pilot_value
    x_var_init = np.zeros(N, dtype=np.float64)
    x_var_init[data_idx] = E_S

    # Per-position update mask: True at data positions (variable), False at pilot+guard (frozen)
    update_mask_pos = np.zeros(N, dtype=bool)
    update_mask_pos[data_idx] = True

    # Project to per-edge (N, P) via q_p(n) = m
    x_msg = x_init[q_np].astype(np.complex128)               # (N, P)
    x_var_msg = x_var_init[q_np].astype(np.float64)          # (N, P)
    update_mask_edge = update_mask_pos[q_np]                  # (N, P) bool

    # Channel init: zero-mean Bayesian
    h_msg = np.zeros((N, P), dtype=np.complex128)
    h_var_msg = np.full((N, P), sigma2_h, dtype=np.float64)

    h_msg_prev = h_msg.copy()
    h_var_msg_prev = h_var_msg.copy()
    x_msg_prev = x_msg.copy()
    x_var_msg_prev = x_var_msg.copy()

    eps_safe = 1e-30
    iter_done = 0
    converged = False
    traj = [] if return_trajectory else None

    for it in range(1, i_max + 1):
        iter_done = it

        # Snapshot OLD state (synchronous BP)
        h_msg_old = h_msg
        h_var_msg_old = h_var_msg
        x_msg_old = x_msg
        x_var_msg_old = x_var_msg

        contrib = phase_np * x_msg_old
        weighted = h_msg_old * contrib
        z_total = weighted.sum(axis=1)
        x_abs2 = np.abs(x_msg_old) ** 2
        h_abs2 = np.abs(h_msg_old) ** 2
        A1 = (h_var_msg_old * x_abs2).sum(axis=1)
        A2 = (x_var_msg_old * h_abs2).sum(axis=1)
        A4 = (h_var_msg_old * x_var_msg_old).sum(axis=1)

        # ===========================================================
        # CHANNEL ESTIMATION (Eq 35-37, 41, 47-50)
        # ===========================================================
        y_tilde_h = y[:, None] - z_total[:, None] + weighted
        sigma_h_tilde = (
            (A1[:, None] - h_var_msg_old * x_abs2)
            + (A2[:, None] - x_var_msg_old * h_abs2)
            + sigma2
            + (A4[:, None] - h_var_msg_old * x_var_msg_old)
            + sigma2_h * x_var_msg_old
        )
        sigma_h_tilde = np.maximum(sigma_h_tilde, eps_safe)

        prec_h = x_abs2 / sigma_h_tilde
        weighted_h = np.conj(contrib) * y_tilde_h / sigma_h_tilde
        total_prec_h = prec_h.sum(axis=0)
        total_w_h = weighted_h.sum(axis=0)
        prec_extr_h = np.maximum(total_prec_h[None, :] - prec_h, eps_safe)
        sigma_h_post_var = 1.0 / prec_extr_h
        h_tilde = sigma_h_post_var * (total_w_h[None, :] - weighted_h)

        denom_h = sigma_h_post_var + sigma2_h
        h_post_mean = sigma2_h * h_tilde / denom_h
        h_post_var = sigma2_h * sigma_h_post_var / denom_h

        h_msg_new = beta_h * h_post_mean + (1.0 - beta_h) * h_msg_prev
        h_var_msg_new = beta_h * h_post_var + (1.0 - beta_h) * h_var_msg_prev

        # ===========================================================
        # DATA ESTIMATION (Eq 30, 32, 33, 39, 44-46) — only at data positions
        # ===========================================================
        y_tilde_x = y[:, None] - z_total[:, None] + weighted
        sigma_x_tilde = (
            (A1[:, None] - h_var_msg_old * x_abs2)
            + (A2[:, None] - x_var_msg_old * h_abs2)
            + sigma2
            + (A4[:, None] - h_var_msg_old * x_var_msg_old)
            + E_S * h_var_msg_old
        )
        sigma_x_tilde = np.maximum(sigma_x_tilde, eps_safe)

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

        # QPSK soft replica (Eq 44) — for EP, the data part is x itself (no pilot subtract)
        denom_u = np.maximum(sigma_x_post_var, 1e-12)
        arg_re = np.clip(2.0 * c_x * np.real(x_tilde_pre) / denom_u, -50.0, 50.0)
        arg_im = np.clip(2.0 * c_x * np.imag(x_tilde_pre) / denom_u, -50.0, 50.0)
        tanh_re = np.tanh(arg_re)
        tanh_im = np.tanh(arg_im)
        x_post_data = c_x * (tanh_re + 1j * tanh_im)
        x_var_post_data = c_x ** 2 * ((1.0 - tanh_re ** 2) + (1.0 - tanh_im ** 2))

        # Freeze pilot+guard positions; only update data positions
        x_msg_post = np.where(update_mask_edge, x_post_data, x_msg_old)
        x_var_msg_post = np.where(update_mask_edge, x_var_post_data, x_var_msg_old)

        x_msg_new = beta_x * x_msg_post + (1.0 - beta_x) * x_msg_prev
        x_var_msg_new = beta_x * x_var_msg_post + (1.0 - beta_x) * x_var_msg_prev

        # Re-freeze pilot+guard after damping (in case prev had drifted)
        x_msg_new = np.where(update_mask_edge, x_msg_new, x_msg_old)
        x_var_msg_new = np.where(update_mask_edge, x_var_msg_new, x_var_msg_old)

        # Commit
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
                              h_var_mean=float(np.mean(h_var_msg)),
                              x_var_mean=float(np.mean(x_var_msg))))
        if rel_change < eps_tol and it > 1:
            converged = True
            break

    # Final h_p extraction: precision-weighted combine over n + prior shrinkage
    h_post_final_prec = (1.0 / np.maximum(h_var_msg, eps_safe)).sum(axis=0)
    h_post_final_w = (h_msg / np.maximum(h_var_msg, eps_safe)).sum(axis=0)
    h_post_final_var_pre = 1.0 / np.maximum(h_post_final_prec, eps_safe)
    h_post_final_mean_pre = h_post_final_var_pre * h_post_final_w
    h_p = sigma2_h * h_post_final_mean_pre / (h_post_final_var_pre + sigma2_h)

    # Final x_m at data positions
    x_total_prec_m = np.zeros(N, dtype=np.float64)
    x_total_w_m = np.zeros(N, dtype=np.complex128)
    inv_xv = 1.0 / np.maximum(x_var_msg, eps_safe)
    np.add.at(x_total_prec_m, q_np.ravel(), inv_xv.ravel())
    np.add.at(x_total_w_m, q_np.ravel(), (x_msg * inv_xv).ravel())
    x_post_var_m = 1.0 / np.maximum(x_total_prec_m, eps_safe)
    x_post_mean_m = x_post_var_m * x_total_w_m

    # Decode QPSK on data positions
    d_hat_full = np.zeros(N, dtype=np.complex128)
    d_re = np.where(np.real(x_post_mean_m[data_idx]) >= 0, 1.0, -1.0) / np.sqrt(2.0)
    d_im = np.where(np.imag(x_post_mean_m[data_idx]) >= 0, 1.0, -1.0) / np.sqrt(2.0)
    d_hat_full[data_idx] = d_re + 1j * d_im

    # Reconstruct H_eff
    H_eff = np.zeros((N, N), dtype=np.complex128)
    n_idx = np.arange(N)
    for p in range(P):
        if abs(h_p[p]) < 1e-12:
            continue
        H_eff[n_idx, q_np[:, p]] += h_p[p] * phase_np[:, p]

    return dict(
        d_hat=d_hat_full,
        H_eff=H_eff,
        h_hat=h_p,
        iter_done=iter_done,
        converged=bool(converged),
        x_hat=x_post_mean_m,
        trajectory=traj,
    )
