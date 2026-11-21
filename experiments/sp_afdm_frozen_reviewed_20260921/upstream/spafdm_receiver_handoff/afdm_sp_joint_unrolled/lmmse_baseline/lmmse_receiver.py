"""
lmmse_receiver.py — closed-form LMMSE channel estimator + MP-BP data detection
for SP-AFDM. Vanilla "complexity-class reference" baseline.

Algorithm (n_iter=1, vanilla LMMSE):
  1. Build pilot-only sensing matrix Φ_p ∈ ℂ^{N×Q} where the carrier is the
     pilot vector (data treated as Gaussian noise with variance E_d = 1-ρ).
  2. Tikhonov LMMSE on the pilot-only model:
        ĥ = (Φ_p^H Φ_p + λI)^(-1) Φ_p^H y
     with λ = (σ² + E_d) / σ²_h (regularizer = noise+data-interference / prior).
     Equivalent to MAP estimate under h ~ CN(0, σ²_h I), w ~ CN(0, λ·σ²_h I).
  3. Reconstruct H_eff = reconstruct_H_from_omp(N, ĥ, k_max, l_max, c1, c2).
  4. MP-BP data detection on the SP frame, removing pilot contribution:
        y' = y - H_eff · pilot
        d̂ = MP-BP(y', H_eff · √(1-ρ), σ², QPSK_constellation)
     where the data-channel is H_eff scaled by √(1-ρ).

Optional iterative-IC variant (n_iter > 1):
  After step 4, rebuild Φ on the data-aided carrier x_total = pilot + √(1-ρ)·d̂_hard,
  re-fit LMMSE, redo data detection. This mirrors Cao 2024's re-OMP loop but with
  LMMSE replacing OMP. Default n_iter=1 (vanilla single-shot).

Complexity:
  Per outer iter: O(NQ²) for Φ_p^H Φ_p + O(Q³) for matrix solve. For our regime
  (N=1024, Q=515): Q³ ≈ 1.4e8 vs OMP+MP's ~4e6. ~35× slower per frame.
  Supports the abstract claim "avoid cubic per-frame cost".
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix, mp_detect_bp, reconstruct_H_from_omp,
)


def lmmse_sp_receiver(
    y: np.ndarray,
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    pilot: np.ndarray,                    # (N,) complex; sqrt(rho)·zc convention
    sigma2: float,
    rho: float = 0.5,
    sigma2_h: float = 1.0,                # channel prior variance
    n_iter: int = 1,                      # outer iterations. n_iter=1 is vanilla textbook LMMSE
                                            # (the "cubic-cost reference"). n_iter>1 enables Cao-style
                                            # IC, but at production large-Q (e.g. Q=515) the IC
                                            # residual is too noisy and iteration DESTABILIZES
                                            # (n_iter=3 BER 44% > n_iter=1 BER 29% at our SP-AFDM-UWA
                                            # regime). Use n_iter=1 unless verifying small-Q regime.
    bp_n_iter: int = 20,                  # MP-BP inner iterations
    bp_damp: float = 0.5,                 # MP-BP damping
    bp_threshold: float = 1e-4,           # MP-BP edge-pruning threshold
    constellation: np.ndarray = None,     # default: unit-energy QPSK
    return_diagnostics: bool = False,
):
    """SP-AFDM LMMSE channel estimator + MP-BP data detector.

    Parameters
    ----------
    y : (N,) complex
        DAFT-domain received signal.
    pilot : (N,) complex
        Pilot vector at sqrt(rho)·zc scale (matches paired_learned_eval convention).
    sigma2 : noise variance.
    rho : pilot-to-total power split (matches SP frame).
    sigma2_h : prior variance per virtual-tap; controls Tikhonov regularizer.
    n_iter : outer iterations. n_iter=1 is vanilla LMMSE (textbook).
    bp_n_iter, bp_damp, bp_threshold : MP-BP detector hyperparameters.
    constellation : detection constellation. Default unit-energy QPSK.

    Returns
    -------
    dict with d_hat (N,) complex (data symbols at sqrt(P_d) scale),
         H_eff (N, N), h_hat (Q,), n_iter_used (int).
    """
    assert y.shape == (N,)
    assert pilot.shape == (N,)
    P_d = 1.0 - rho
    sqrt_Pd = float(np.sqrt(P_d))
    Q = (l_max + 1) * (2 * k_max + 1)

    if constellation is None:
        # Unit-energy QPSK at the data-symbol level (before sqrt(P_d) scaling)
        constellation = np.array(
            [1+1j, 1-1j, -1+1j, -1-1j], dtype=np.complex128) / np.sqrt(2.0)

    # ---- Iter 0: pilot-only LMMSE ----
    Phi = construct_sensing_matrix(N, pilot, c1, c2, l_max, k_max)  # (N, Q)
    # Effective noise = thermal noise + data interference variance
    # |x[m]|² = ρ (pilot) + (1-ρ) · |d|² (data) ≈ ρ + (1-ρ) on average.
    # Pilot-only LMMSE treats data part as Gaussian noise with variance (1-ρ) · |h|².
    # Conservative regularizer:
    sigma2_eff_init = sigma2 + P_d   # data-interference per symbol absorbed into noise
    lam = sigma2_eff_init / max(sigma2_h, 1e-12)
    PhiHPhi = Phi.conj().T @ Phi
    PhiHy = Phi.conj().T @ y
    A = PhiHPhi + lam * np.eye(Q, dtype=np.complex128)
    h_hat = np.linalg.solve(A, PhiHy)
    H_eff = reconstruct_H_from_omp(N, h_hat, k_max, l_max, c1, c2, threshold=0.0)

    diag_iter = []
    d_hat_unit = np.zeros(N, dtype=np.complex128)

    for it in range(n_iter):
        if it >= 1:
            # IC variant: rebuild Phi using data-aided carrier
            x_total = pilot + sqrt_Pd * d_hat_unit       # (N,) complex; pilot+data soft
            Phi = construct_sensing_matrix(N, x_total, c1, c2, l_max, k_max)
            PhiHPhi = Phi.conj().T @ Phi
            PhiHy = Phi.conj().T @ y
            # After IC, data variance shrinks (we know x̂); use smaller regularizer
            lam = sigma2 / max(sigma2_h, 1e-12)
            A = PhiHPhi + lam * np.eye(Q, dtype=np.complex128)
            h_hat = np.linalg.solve(A, PhiHy)
            H_eff = reconstruct_H_from_omp(
                N, h_hat, k_max, l_max, c1, c2, threshold=0.0)

        # MP-BP data detection
        # Subtract pilot contribution: y' = y - H_eff @ pilot
        # Data channel: H_eff scaled by sqrt(P_d) (data carrier is sqrt(P_d)*d)
        y_prime = y - H_eff @ pilot
        H_data = sqrt_Pd * H_eff
        d_hat_unit = mp_detect_bp(
            y_prime, H_data, sigma2,
            constellation, n_iter=bp_n_iter, damp=bp_damp,
            threshold=bp_threshold)

        if return_diagnostics:
            nmse = float((np.abs(H_eff @ pilot - (y - sqrt_Pd * H_eff @ d_hat_unit))**2).mean())
            diag_iter.append(dict(it=it, residual_norm=float(np.linalg.norm(y - H_eff @ (pilot + sqrt_Pd * d_hat_unit))),
                                    h_norm=float(np.linalg.norm(h_hat))))

    # Output: d_hat at sqrt(P_d) scale (matches mp_detect_bp_torch / paired_learned_eval)
    d_hat = sqrt_Pd * d_hat_unit

    return dict(
        d_hat=d_hat,
        H_eff=H_eff,
        h_hat=h_hat,
        n_iter_used=n_iter,
        diagnostics=diag_iter if return_diagnostics else None,
    )
