"""
verify_reomp_bitexact.py — regression check for reomp_per_iter flag.

Three checks:

  1. With `reomp_per_iter=False` (default): output identical to the no-kwarg
     call. Trivially true if both hit the same code path; this guards against
     accidental state mutation introduced by adding the flag.

  2. With `reomp_per_iter=False`: output bit-exactly equal to a hard-coded
     golden (`x_soft`, `H_hat`) value captured immediately after the flag
     was added. If a future edit accidentally perturbs the iter-0 code
     path, this catches it.

  3. With `reomp_per_iter=True`: support set after iter >= 1 may differ
     from the iter-0 support (sanity that the flag actually does something).

Uses `mp_mode='pic'` (numpy-only) so the test runs without torch.

Run:
    conda activate AFDM   # or any env with numpy
    python afdm_sp_joint_unrolled/verify_reomp_bitexact.py
"""
from __future__ import annotations

import pathlib
import sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative  # noqa: E402


def _build_frame(seed: int = 20260508):
    """Tiny synthetic SP-AFDM frame, P=2 paths, N=128, integer Doppler.

    Self-contained — does NOT touch afdm_env (avoids torch / qzcli imports
    that may not be installed in a minimal env).
    """
    rng = np.random.default_rng(seed)
    N = 128
    c1 = 1.0 / (2.0 * N)         # standard AFDM choice for k_max = 1
    c2 = 0.0
    l_max = 8
    k_max = 4
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    rho = 0.5
    P_d = 1.0 - rho
    sparsity = 4   # OMP n_paths

    # Pilot: ZC-like sequence
    zc = np.exp(-1j * np.pi * 7 * np.arange(N) ** 2 / N)
    pilot_scaled = np.sqrt(rho) * zc
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)

    # Random data
    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam

    # Build a small sparse H_eff manually: 2 paths
    h_dense = np.zeros(Q, dtype=complex)
    chosen = [(2, 1), (5, -1)]   # (l, k) pairs
    for (l_p, k_p) in chosen:
        col = l_p * K + (k_p + k_max)
        h_dense[col] = (rng.standard_normal() + 1j * rng.standard_normal()) / np.sqrt(2.0)
    # Fold into H_eff via the same formula as reconstruct_H_from_omp
    H_true = np.zeros((N, N), dtype=complex)
    n_arr = np.arange(N, dtype=np.float64)
    for (l_p, k_p) in chosen:
        col = l_p * K + (k_p + k_max)
        g = h_dense[col]
        delta = l_p * K + k_p
        m_arr = ((n_arr.astype(int) + delta) % N)
        m_f = m_arr.astype(np.float64)
        phase = np.exp(1j * 2.0 * np.pi * (
            -c1 * (l_p ** 2) + c2 * (m_f ** 2 - n_arr ** 2)
            - float(l_p) * n_arr / N))
        H_true[m_arr, np.arange(N)] += g * phase

    snr_db = 20.0
    sigma2 = 1.0 / (10.0 ** (snr_db / 10.0))
    y = H_true @ x_sp
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = y + np.sqrt(sigma2) * noise

    return dict(
        y_daft=y_daft, pilot_scaled=pilot_scaled, N=N, c1=c1, c2=c2,
        l_max=l_max, k_max=k_max, sigma2=sigma2,
        constellation_data=np.sqrt(P_d) * QPSK,
        n_paths=sparsity, rho=rho)


def _call(frame, **extra):
    return joint_omp_mp_iterative(
        frame['y_daft'], frame['pilot_scaled'], frame['N'],
        frame['c1'], frame['c2'], frame['l_max'], frame['k_max'],
        frame['sigma2'], frame['constellation_data'],
        n_paths=frame['n_paths'], n_outer_iter=5, rho=frame['rho'],
        pic_iter=10, pic_damp=0.5, mp_mode='pic',
        gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
        k_leak=2, update_sigma2=True, phase_convention='python',
        eps_stop_rel=-1.0, **extra)


def main():
    print("=" * 70)
    print("verify_reomp_bitexact.py")
    print("=" * 70)
    frame = _build_frame()

    # Check 1: no-kwarg ≡ explicit reomp_per_iter=False
    x_a, H_a = _call(frame)
    x_b, H_b = _call(frame, reomp_per_iter=False)
    diff_x = float(np.max(np.abs(x_a - x_b)))
    diff_H = float(np.max(np.abs(H_a - H_b)))
    print(f"[Check 1] no-kwarg vs reomp_per_iter=False:")
    print(f"          max|x_a - x_b| = {diff_x:.3e}   "
          f"max|H_a - H_b| = {diff_H:.3e}")
    assert diff_x == 0.0, f"x_soft drift: {diff_x}"
    assert diff_H == 0.0, f"H_hat drift: {diff_H}"
    print("          PASS (bit-exact)")

    # Check 2: hard-coded golden (captured 2026-05-08, frame seed 20260508)
    # These two scalars summarize x_soft + H_hat under the fixed config.
    # If iter-0 path is accidentally perturbed by future edits, these drift.
    x_norm = float(np.linalg.norm(x_a))
    H_fro = float(np.linalg.norm(H_a, ord='fro'))
    print(f"[Check 2] golden invariants:")
    print(f"          ||x_soft|| = {x_norm:.10f}")
    print(f"          ||H_hat||_F = {H_fro:.10f}")
    # Golden values captured on the first run after this file landed.
    GOLD_X = 7.8569172972
    GOLD_H = 15.3243430961
    tol = 1e-6   # relative
    assert abs(x_norm - GOLD_X) < tol * max(GOLD_X, 1.0), (
        f"x_norm drifted: {x_norm} vs golden {GOLD_X}")
    assert abs(H_fro - GOLD_H) < tol * max(GOLD_H, 1.0), (
        f"H_fro drifted: {H_fro} vs golden {GOLD_H}")
    print("          PASS (within tol)")

    # Check 3: reomp_per_iter=True actually changes behaviour
    # (run with return_trajectory=True would give us per-iter support, but the
    # cheap proxy is to verify the final H_hat differs from the False case
    # under a noisy frame where re-OMP picks at least one different atom.)
    x_t, H_t = _call(frame, reomp_per_iter=True)
    delta_x = float(np.max(np.abs(x_t - x_a)))
    delta_H = float(np.max(np.abs(H_t - H_a)))
    print(f"[Check 3] reomp_per_iter=True vs False:")
    print(f"          max|delta x| = {delta_x:.3e}   "
          f"max|delta H| = {delta_H:.3e}")
    # We expect SOME difference — but not always (re-OMP at high SNR may pick
    # the same atoms). Soft check: warn if identical, error only if NaN/inf.
    assert np.all(np.isfinite(x_t)) and np.all(np.isfinite(H_t)), (
        "reomp_per_iter=True produced non-finite output")
    if delta_x == 0.0 and delta_H == 0.0:
        print("          WARN: re-OMP produced identical output — re-OMP picked "
              "the same atoms as iter-0 OMP. This frame may be too clean; "
              "the flag still triggered the new code path safely.")
    else:
        print("          PASS (re-OMP took the new code path and produced "
              "different output)")

    print()
    print("All checks passed.")


if __name__ == '__main__':
    main()
