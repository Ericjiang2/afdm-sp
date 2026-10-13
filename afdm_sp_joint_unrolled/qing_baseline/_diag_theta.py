"""Verify Theta_t matrix-product construction matches Eq (8) closed form.

Eq (8): Theta_i(m,n) = exp(j 2pi/N (N c1 l_i^2 - n l_i + N c2 (n^2 - m^2)))
                     * delta((n - m - loc_i) mod N)
       where loc_i = alpha_i + 2 N c1 l_i.
"""
import pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
    build_theta_t, _enumerate_l_alpha,
)


def build_theta_t_eq8(N, l_t, alpha_t, c1, c2):
    """Direct implementation of Eq (8). Returns N x N complex sparse-ish matrix."""
    loc = alpha_t + int(round(2 * N * c1 * l_t))
    Theta = np.zeros((N, N), dtype=complex)
    for m in range(N):
        for n in range(N):
            if (n - m - loc) % N == 0:
                phase = (2 * np.pi / N) * (
                    N * c1 * (l_t ** 2) - n * l_t + N * c2 * (n ** 2 - m ** 2)
                )
                Theta[m, n] = np.exp(1j * phase)
    return Theta


def main():
    N = 64  # smaller for speed
    alpha_max, l_max = 2, 1
    c1 = (2 * alpha_max + 1) / (2 * N)
    c2 = 1.0 / (4.0 * N)

    n_grid = np.arange(N).astype(float)
    Lc1 = np.diag(np.exp(-1j * 2 * np.pi * c1 * n_grid ** 2))
    Lc2 = np.diag(np.exp(-1j * 2 * np.pi * c2 * n_grid ** 2))
    F = np.fft.fft(np.eye(N), norm='ortho')
    A = Lc2 @ F @ Lc1
    A_H = A.conj().T

    Q_plus_1 = (l_max + 1) * (2 * alpha_max + 1)
    pairs = _enumerate_l_alpha(Q_plus_1, alpha_max)
    print(f'N={N}  Q+1={Q_plus_1}  c1={c1:.4f} ({2*N*c1}/2N)')
    print(f'(l, alpha) pairs: {pairs}')

    max_diff = 0.0
    for t_idx, (l_t, alpha_t) in enumerate(pairs):
        Theta_mat = build_theta_t(N, l_t, alpha_t, c1, c2, A, A_H)
        Theta_eq8 = build_theta_t_eq8(N, l_t, alpha_t, c1, c2)
        diff = np.max(np.abs(Theta_mat - Theta_eq8))
        max_diff = max(max_diff, diff)
        # Also check row sparsity of Eq 8 form
        nnz_per_row = (np.abs(Theta_eq8) > 1e-12).sum(axis=1)
        print(f't={t_idx + 1}: (l={l_t}, alpha={alpha_t})  '
              f'loc={alpha_t + 2*N*c1*l_t:.1f}  '
              f'max|matrix - eq8| = {diff:.3e}  '
              f'eq8 nnz/row = {nnz_per_row.min()}-{nnz_per_row.max()}  '
              f'matrix |F| = {np.linalg.norm(Theta_mat, "fro"):.3e}  '
              f'eq8 |F| = {np.linalg.norm(Theta_eq8, "fro"):.3e}')
    print(f'\noverall max |matrix - eq8| = {max_diff:.3e}')

    # Check orthogonality directly using both
    from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
        qing_pilot, assemble_phi_p,
    )
    M = 5  # Q+1 = 10 -> spacing 10 -> M*10 < N-Q so M up to (N-Q)/10 - 1 ~ 5
    x_p, _ = qing_pilot(N, alpha_max, l_max, M=M, sigma_p=1.0)
    print(f'\npilot positions: {np.where(np.abs(x_p) > 0)[0]}')
    # Build Phi_p with each method
    theta_list_mat = [build_theta_t(N, l, a, c1, c2, A, A_H) for (l, a) in pairs]
    theta_list_eq8 = [build_theta_t_eq8(N, l, a, c1, c2) for (l, a) in pairs]
    Phi_mat = assemble_phi_p(theta_list_mat, x_p)
    Phi_eq8 = assemble_phi_p(theta_list_eq8, x_p)
    G_mat = Phi_mat.conj().T @ Phi_mat
    G_eq8 = Phi_eq8.conj().T @ Phi_eq8
    print(f'Phi_mat^H Phi_mat: diag={np.real(np.diag(G_mat)).round(3)}')
    print(f'Phi_mat^H Phi_mat: off-diag |F| = {np.linalg.norm(G_mat - np.diag(np.diag(G_mat))):.3e}')
    print(f'Phi_eq8^H Phi_eq8: diag={np.real(np.diag(G_eq8)).round(3)}')
    print(f'Phi_eq8^H Phi_eq8: off-diag |F| = {np.linalg.norm(G_eq8 - np.diag(np.diag(G_eq8))):.3e}')


if __name__ == '__main__':
    main()
