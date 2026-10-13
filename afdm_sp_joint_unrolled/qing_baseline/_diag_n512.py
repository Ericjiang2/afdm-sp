"""One-frame diagnostic at N=512 to figure out why consistency test BER is flat."""
import pathlib
import sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
    QPSK_CONST, build_theta_list, qing_pilot, qing_receiver, assemble_phi_p,
)

N = 512
alpha_max, l_max, P = 2, 1, 3
M = 15
c1 = (2 * alpha_max + 1) / (2 * N)
c2 = 1.0 / (4.0 * N)
n_grid = np.arange(N).astype(float)
Lc1 = np.diag(np.exp(-1j * 2 * np.pi * c1 * n_grid ** 2))
Lc2 = np.diag(np.exp(-1j * 2 * np.pi * c2 * n_grid ** 2))
F = np.fft.fft(np.eye(N), norm='ortho')
A = Lc2 @ F @ Lc1
A_H = A.conj().T

N0 = 1.0
snr_p, snr_d = 50.0, 21.0
sigma_p_sq = N0 * 10 ** (snr_p / 10)
sigma_d_sq = N0 * 10 ** (snr_d / 10)
print(f'sigma_p_sq={sigma_p_sq:.3e}  sigma_d_sq={sigma_d_sq:.3e}  N0={N0}')

x_p, _ = qing_pilot(N, alpha_max, l_max, M=M, sigma_p=np.sqrt(sigma_p_sq))
print(f'||x_p||^2 = {(np.abs(x_p) ** 2).sum():.3e}  vs expected sigma_p_sq={sigma_p_sq:.3e}')
print(f'x_p nonzero positions: {np.where(np.abs(x_p) > 0)[0][:8]} ...')
print(f'x_p amp at pilot: {np.abs(x_p[0]):.3e}  vs expected {np.sqrt(sigma_p_sq / (M + 1)):.3e}')

theta_list = build_theta_list(N, alpha_max, l_max, c1, c2, A, A_H)
Phi_p = assemble_phi_p(theta_list, x_p)
norm_F = float(np.linalg.norm(Phi_p, 'fro'))
print(f'Phi_p shape: {Phi_p.shape}  ||Phi_p||_F = {norm_F:.3e}')

G = Phi_p.conj().T @ Phi_p
print(f'Phi_p^H Phi_p diag (should be ~equal per Eq 20): {np.real(np.diag(G))}')
off_diag_norm = float(np.linalg.norm(G - np.diag(np.diag(G))))
print(f'Phi_p^H Phi_p off-diag norm (should be ~0): {off_diag_norm:.3e}')

rng = np.random.default_rng(42)
choice = rng.choice(10, size=P, replace=False)
h_true = np.zeros(10, dtype=complex)
h_true[choice] = (rng.standard_normal(P) + 1j * rng.standard_normal(P)) / np.sqrt(2 * P)
print(f'h_true active: {sorted(choice.tolist())}, |h_true| = {np.abs(h_true)}')

H_eff_true = sum(h_t * Theta for h_t, Theta in zip(h_true, theta_list))
print(f'||H_eff_true||_F = {np.linalg.norm(H_eff_true, "fro"):.3e}')

data_idx = rng.integers(0, 4, N)
x_d = QPSK_CONST[data_idx] * np.sqrt(sigma_d_sq)
noise = np.sqrt(N0) * (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2)
y = H_eff_true @ (x_p + x_d) + noise
print(f'||y|| = {np.linalg.norm(y):.3e}')
print(f'||H_eff_true x_p|| = {np.linalg.norm(H_eff_true @ x_p):.3e}')
print(f'||H_eff_true x_d|| = {np.linalg.norm(H_eff_true @ x_d):.3e}')
print(f'||noise|| = {np.linalg.norm(noise):.3e}')

out = qing_receiver(y, x_p, N, alpha_max, l_max, c1, c2, A, A_H,
                    sigma_p_sq=sigma_p_sq, sigma_d_sq=sigma_d_sq, N0=N0, n_iter=2)
print(f'h_hat |.| = {np.abs(out["h_hat"])}')
nmse_h = float(np.sum(np.abs(out['h_hat'] - h_true) ** 2) / np.sum(np.abs(h_true) ** 2))
print(f'NMSE_h = {nmse_h:.3e}')
print(f'b active: {np.where(out["b"] > 0)[0].tolist()}')

xdh = out['x_d_hat']
print(f'||x_d|| = {np.linalg.norm(x_d):.3e}, ||x_d_hat|| = {np.linalg.norm(xdh):.3e}')
print(f'||x_d_hat - x_d|| = {np.linalg.norm(xdh - x_d):.3e}')
err_re = int((np.sign(x_d.real) != np.sign(xdh.real)).sum())
err_im = int((np.sign(x_d.imag) != np.sign(xdh.imag)).sum())
print(f'bit-flip count: re={err_re}, im={err_im}, total={err_re + err_im}/{2 * N} = BER {(err_re + err_im) / (2 * N):.3e}')
