"""Diagnostic: trace per-iter state of qing_receiver to locate divergence.

Replicates the receiver loop manually with verbose logging of every quantity
that could be drifting. Uses the same micro setup as qing_sp_afdm.__main__
(N=64, P_active=2, SNR_p=50/SNR_d=21 dB).
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent))

from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
    QPSK_CONST,
    assemble_H_eff,
    assemble_phi_p,
    build_theta_list,
    mmse_estimate_h,
    mp_bp_detect,
    qing_pilot,
    threshold_path_indicator,
)


def _norm(x):
    return float(np.linalg.norm(x))


def main():
    N = 64
    alpha_max = 1
    l_max = 1
    c1 = (2 * alpha_max + 1) / (2 * N)
    c2 = 0.0
    Q = (l_max + 1) * (2 * alpha_max + 1) - 1

    n_grid = np.arange(N).astype(float)
    Lc1 = np.diag(np.exp(-1j * 2 * np.pi * c1 * n_grid ** 2))
    Lc2 = np.diag(np.exp(-1j * 2 * np.pi * c2 * n_grid ** 2))
    F = np.fft.fft(np.eye(N), norm='ortho')
    A = Lc2 @ F @ Lc1
    A_H = A.conj().T

    rng = np.random.default_rng(0)
    P_active = 2
    h_true = np.zeros(Q + 1, dtype=complex)
    active = rng.choice(Q + 1, size=P_active, replace=False)
    h_true[active] = (rng.standard_normal(P_active) +
                       1j * rng.standard_normal(P_active)) / np.sqrt(2 * P_active)

    sigma_p_sq = 1.0
    snr_p_db, snr_d_db = 50.0, 21.0
    N0 = sigma_p_sq * 10 ** (-snr_p_db / 10)
    sigma_d_sq = N0 * 10 ** (snr_d_db / 10)

    x_p, _ = qing_pilot(N, alpha_max, l_max, M=2, sigma_p=np.sqrt(sigma_p_sq))
    theta_list = build_theta_list(N, alpha_max, l_max, c1, c2, A, A_H)
    Phi_p = assemble_phi_p(theta_list, x_p)

    x_d = QPSK_CONST[rng.integers(0, 4, N)] * np.sqrt(sigma_d_sq)
    H_eff_true = sum(h_t * Theta for (h_t, Theta) in zip(h_true, theta_list))
    sigma_w = np.sqrt(N0)
    noise = sigma_w * (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
    y = H_eff_true @ (x_p + x_d) + noise

    sigma_h_total = 1.0
    sigma_w_eff_sq = sigma_h_total * sigma_d_sq + N0
    print(f'N0={N0:.3e}  sigma_d_sq={sigma_d_sq:.3e}  '
          f'sigma_w_eff_sq={sigma_w_eff_sq:.3e}  '
          f'gamma=3*sqrt({sigma_w_eff_sq:.3e}/{sigma_p_sq})={3*np.sqrt(sigma_w_eff_sq/sigma_p_sq):.3e}')
    print(f'true_active={sorted(active.tolist())}  |h_true|={np.abs(h_true)}')
    print(f'||y||={_norm(y):.3e}  ||x_d||={_norm(x_d):.3e}  ||noise||={_norm(noise):.3e}')

    C_h_var = np.where(np.abs(h_true) > 0, 0.5, 0.01)
    C_h_inv = np.diag(1.0 / np.maximum(C_h_var, 1e-30))
    gamma = 3.0 * np.sqrt(sigma_w_eff_sq / sigma_p_sq)

    # iter 0
    h_hat = mmse_estimate_h(y, Phi_p, sigma_w_eff_sq, C_h_inv)
    b = threshold_path_indicator(h_hat, gamma)
    H_eff = assemble_H_eff(theta_list, h_hat, b)
    err_h = _norm(h_hat - h_true)
    print(f'\n--- iter 0 (initial MMSE) ---')
    print(f'  h_hat magnitude: {np.abs(h_hat)}')
    print(f'  h_hat - h_true norm: {err_h:.3e}')
    print(f'  active passing gamma={gamma:.3e}: {np.where(b > 0)[0].tolist()}')
    print(f'  |H_eff|_F: {np.linalg.norm(H_eff, "fro"):.3e}  (true: {np.linalg.norm(H_eff_true, "fro"):.3e})')

    y_d = y - H_eff @ x_p
    print(f'  ||y_d|| = {_norm(y_d):.3e}  (expected ~ ||H_eff_true x_d + noise|| = {_norm(H_eff_true @ x_d + noise):.3e})')
    x_d_hat = mp_bp_detect(y_d, H_eff, sigma_w_eff_sq)
    err_x = _norm(x_d_hat - x_d)
    print(f'  ||x_d_hat - x_d|| = {err_x:.3e}  (||x_d|| = {_norm(x_d):.3e})')
    print(f'  bit-mismatch fraction: {np.mean(np.abs(x_d_hat - x_d) > 1e-6):.2%}')

    # iter 1
    print(f'\n--- iter 1 (Eq 24) ---')
    residual = y - H_eff @ x_d_hat
    expected_residual = H_eff_true @ x_p + noise + (H_eff_true - H_eff) @ x_d_hat + H_eff_true @ (x_d - x_d_hat)
    print(f'  ||residual|| = {_norm(residual):.3e}  (decomposition expected: {_norm(expected_residual):.3e})')
    print(f'  || H_eff_true x_p || = {_norm(H_eff_true @ x_p):.3e}')
    print(f'  || (H_eff_true - H_eff) x_d_hat || = {_norm((H_eff_true - H_eff) @ x_d_hat):.3e}')
    print(f'  || H_eff_true (x_d - x_d_hat) || = {_norm(H_eff_true @ (x_d - x_d_hat)):.3e}')

    h_hat_1 = mmse_estimate_h(residual, Phi_p, sigma_w_eff_sq, C_h_inv)
    err_h_1 = _norm(h_hat_1 - h_true)
    b_1 = threshold_path_indicator(h_hat_1, gamma)
    print(f'  h_hat_1 magnitude: {np.abs(h_hat_1)}')
    print(f'  h_hat_1 - h_true norm: {err_h_1:.3e}')
    print(f'  active passing gamma={gamma:.3e}: {np.where(b_1 > 0)[0].tolist()}')

    # Compare: what would mmse_estimate_h give if we used the "ideal" residual
    # = H_eff_true @ x_p + noise (perfect data cancellation)?
    ideal_residual = H_eff_true @ x_p + noise
    h_hat_ideal = mmse_estimate_h(ideal_residual, Phi_p, sigma_w_eff_sq, C_h_inv)
    print(f'\n  [oracle] if residual = H_eff_true x_p + noise (perfect cancel):')
    print(f'  h_hat_oracle - h_true norm: {_norm(h_hat_ideal - h_true):.3e}')
    print(f'  h_hat_oracle magnitude: {np.abs(h_hat_ideal)}')


if __name__ == '__main__':
    main()
