"""
drce_receiver.py — SISO instantiation of Yin et al. 2024 DRCE for AFDM.

Yin Haoran, Wei Xizhang, Tang Yanqun, et al., "Diagonally Reconstructed Channel
Estimation for MIMO-AFDM with Inter-Doppler Interference in Doubly Selective
Channels", IEEE TWC vol 23 no 10 pp 14066-14079, 2024 (arXiv 2206.12822).

This is a SISO drop of the MIMO algorithm in §IV — antenna indices removed.
Algorithm in plain words (Yin Eq 21-26):

  1. Embedded-pilot frame:
     - x[m0] = pilot_symbol  (single impulse, |pilot|=1)
     - x[m]  = 0  for m in obs_idx \\ {m0}  (guard zero-fill, width 2*N_g+1)
     - x[m]  = sqrt(P_d) * data_qam[m]  for m in data_pos  (scaled QPSK)

  2. Channel observation (under the EP guard hypothesis: data leakage into
     obs_idx is negligible because the guard catches the channel's max
     delay-Doppler spread):
        y[obs_idx] ≈ M(m0) @ h_lk + noise[obs_idx]
     where M(m0) = construct_sensing_matrix(N, x_pilot_impulse, c1, c2,
                                             l_max, k_max)[obs_idx, :]
     and h_lk is the (l_max+1)*(2*k_max+1) sparse vector of (l, k) tap gains.

  3. Closed-form Tikhonov LS (DRCE's "diagonal reconstruction" — direct
     inversion exploiting the AFDM phase structure; in the SISO low-Q case
     a Q-dimensional solve is fine):
        h_lk = (M^H M + lam*I)^{-1} M^H y_obs

  4. Reconstruct H_eff via the standard AFDM formula (same helper used by the
     OMP receivers):
        H_eff = reconstruct_H_from_omp(N, h_lk, k_max, l_max, c1, c2)

  5. Detect data on the data_pos positions after subtracting the pilot leak:
        y_data_clean = y[data_pos] - H_eff[data_pos, m0] * pilot_symbol
        H_dd = H_eff[data_pos, data_pos]
        d_hat = mp_detect_bp(y_data_clean, H_dd, sigma2, constellation)

This is a fair SISO instantiation of DRCE: closed-form LS, OMP-free, EPA-only.
The original paper's contribution is the "diagonal reconstruction" derivation
that avoids the full Q-dim solve in the MIMO case; for SISO with Q on the
order of (l_max+1)*(2*k_max+1) the direct solve cost is negligible. We follow
Yin Eq 25 in spirit by exploiting the AFDM phase structure via M(m0), i.e.
the per-pilot-position dictionary slice rather than a generic LS over all of
y. This gives the algorithm-level invariant that captures DRCE's classical
Dirichlet-leakage handling without re-deriving the explicit closed form.

Reused project utilities:
  - construct_sensing_matrix (afdm_baselines)
  - reconstruct_H_from_omp   (afdm_baselines)
  - mp_detect_bp_torch        (data detection — torch GPU path)
"""
from __future__ import annotations

import pathlib
import sys
from typing import Optional

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix,
    reconstruct_H_from_omp,
)


# =====================================================================
# EP-frame helper
# =====================================================================

def min_required_Ng(l_max: int, k_max: int) -> int:
    """Minimum guard half-width such that obs_idx (length 2*N_g+1) covers
    all virtual-tap delta = l*K + k positions (l ∈ [0, l_max], k ∈ [-k_max,
    k_max], K = 2*k_max+1). Below this, some columns of the DRCE sensing
    matrix M are identically zero and the LS becomes underdetermined,
    silently failing to estimate those (l, k) coefficients.

    Required: N_g >= max delta = l_max * K + k_max where K = 2*k_max+1.
    """
    K = 2 * k_max + 1
    return l_max * K + k_max


def build_ep_frame(
    N: int,
    m0: int,
    N_g: int,
    pilot_unit: complex,
    data_qam: np.ndarray,
    rho: float = 0.5,
) -> dict:
    """Construct an embedded-pilot (EPA) AFDM frame at matched-energy
    parity with an SP frame at the same rho.

    SP-frame convention (afdm_env.generate_pilot_frame):
      x[m] = sqrt(rho)*zc[m] + sqrt(1-rho)*data[m]
      |x|^2 average per subcarrier = rho + (1-rho) = 1
      Total pilot energy = rho*N (spread); total data energy = (1-rho)*N.

    EP-frame convention (this function — concentrates pilot at m0):
      x[m0] = sqrt(rho*N) * pilot_unit       (concentrated impulse)
      x[obs_idx \\ {m0}] = 0                  (zero-fill guard)
      x[data_pos] = sqrt((1-rho)*N/n_data) * data_qam[data_pos]
      Total pilot energy = rho*N (matches SP);
      Total data energy = (1-rho)*N (matches SP);
      Total frame energy = N (matches SP).

    The matched-energy parity lets us pair an EP frame against an SP frame at
    the same total per-frame transmit energy, which is the fair comparison
    for "EP advantage isolation". The pilot at m0 has |x[m0]|^2 = rho*N (a
    large impulse value at the standard rho=0.5, e.g. ~16 at N=512), giving
    DRCE its working pilot SNR.

    Returns dict with x_frame, m0, obs_idx, data_pos, pilot_value (the
    boosted pilot at m0), data_scaling (the per-data-symbol amplitude),
    pilot_unit (informational; the unit-norm input).

    Parameters
    ----------
    N : int
        Frame length (must equal the modulation N).
    m0 : int
        Pilot subcarrier index.
    N_g : int
        Guard half-width (so guard window is 2*N_g+1 samples wide).
    pilot_unit : complex
        Unit-norm pilot symbol; |pilot_unit| should be 1 (e.g. 1+0j).
        The actual pilot impulse is sqrt(rho*N) * pilot_unit.
    data_qam : (N,) complex
        Unit-norm data symbols (e.g. QPSK / sqrt(2), |data|^2 = 1). Only
        data_qam[data_pos] is used.
    rho : float, default 0.5
        Pilot-to-total power ratio. Must match the SP frame's rho for fair
        matched-energy parity.
    """
    assert 0 <= m0 < N, f"m0={m0} out of range [0, {N})"
    assert N_g >= 0, f"N_g={N_g} must be non-negative"
    assert 0.0 < rho < 1.0, f"rho={rho} must be in (0, 1)"
    obs_offsets = np.arange(-N_g, N_g + 1)
    obs_idx = ((m0 + obs_offsets) % N).astype(np.int64)
    obs_set = set(obs_idx.tolist())
    data_pos = np.array([m for m in range(N) if m not in obs_set],
                         dtype=np.int64)

    n_data = len(data_pos)
    if n_data == 0:
        raise ValueError(f"N_g={N_g} too large; no data positions left")

    pilot_value = np.sqrt(rho * N) * pilot_unit          # |pilot_value|^2 = rho*N
    data_scaling = float(np.sqrt((1.0 - rho) * N / n_data))

    x_frame = np.zeros(N, dtype=complex)
    x_frame[m0] = pilot_value
    x_frame[data_pos] = data_scaling * data_qam[data_pos]
    return dict(
        x_frame=x_frame, m0=int(m0), obs_idx=obs_idx, data_pos=data_pos,
        pilot_value=complex(pilot_value),
        data_scaling=float(data_scaling),
        pilot_unit=complex(pilot_unit),
        rho=float(rho),
    )


# =====================================================================
# Default detector (mp_detect_bp_torch wrapper, Cao-style)
# =====================================================================

def _bp_detect(y_d, H_eff, sigma2, constellation, n_iter=20, damp=0.5):
    """Lazy import of torch detector so the module can be imported without
    torch installed (falls back to numpy mp_detect_pic on numpy-only env)."""
    try:
        import torch
        from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
        dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return mp_detect_bp_torch(
            y_d, H_eff, sigma2, constellation,
            n_iter=n_iter, threshold=1e-4, damp=damp,
            device=dev, return_numpy=True, return_soft=False)
    except ImportError:
        from afdm_sp_joint_unrolled.afdm_baselines import mp_detect_pic
        return mp_detect_pic(y_d, H_eff, sigma2, constellation,
                              n_iter=n_iter, damp=damp)


# =====================================================================
# DRCE receiver
# =====================================================================

def drce_receiver(
    y: np.ndarray,
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    m0: int,
    N_g: int,
    pilot_value: complex,
    sigma2: float,
    constellation: np.ndarray,
    rho: float = 0.5,
    lam_tikh: Optional[float] = None,
    detector_iter: int = 20,
    detector_damp: float = 0.5,
    l_max_drce: Optional[int] = None,
    k_max_drce: Optional[int] = None,
):
    """SISO DRCE receiver for an EPA-frame AFDM signal.

    Parameters
    ----------
    y : (N,) complex
        DAFT-domain received signal at the AFDM demodulator output.
    N, c1, c2, l_max, k_max : modulation parameters of the underlying SP
        system. The system dictionary is Q = (l_max+1)*(2*k_max+1).
    m0, N_g : EP frame parameters (must match the build_ep_frame call).
    pilot_value : complex
        The full pilot impulse value at m0 (already boosted by sqrt(rho*N)).
        I.e. the value returned in the `pilot_value` field of build_ep_frame.
    sigma2 : float; noise variance.
    constellation : (M,) complex; UN-scaled alphabet (e.g. unit-norm QPSK).
    rho : float, default 0.5; matches the EP-frame rho. Used to derive
        data scaling sqrt((1-rho)*N/n_data) for detector alphabet scaling.
    lam_tikh : float; Tikhonov regularisation. None → 1e-3 * sigma2.
    l_max_drce, k_max_drce : optional int
        Truncated dictionary used by DRCE only. If smaller than the system
        (l_max, k_max), DRCE estimates fewer (l, k) atoms and reconstructs
        H_eff from that smaller subset. Useful when the system l_max is so
        large that the EP guard 2*N_g+1 cannot fit in N (e.g. UWA-AFDM at
        N=1024 with l_max=102 requires N_g >= 922 > N//2). Caller should
        choose (l_max_drce, k_max_drce) such that
        2 * (l_max_drce*K_drce + k_max_drce) + 1 <= N. Defaults to system
        (l_max, k_max).

    Returns
    -------
    dict with d_hat (N,) complex (zero-filled at obs_idx; data only at
        data_pos, scaled by data_scaling per build_ep_frame), H_eff (N, N)
        complex, h_hat (Q_drce,) complex, m0, obs_idx, data_pos,
        data_scaling, l_max_drce, k_max_drce.
    """
    assert y.shape == (N,)
    if l_max_drce is None:
        l_max_drce = l_max
    if k_max_drce is None:
        k_max_drce = k_max
    K_drce = 2 * k_max_drce + 1
    Q_drce = (l_max_drce + 1) * K_drce

    Ng_required = min_required_Ng(l_max_drce, k_max_drce)
    if N_g < Ng_required:
        import warnings
        warnings.warn(
            f"DRCE: N_g={N_g} is below the minimum guard half-width "
            f"l_max_drce*K_drce + k_max_drce = {Ng_required} for "
            f"(l_max_drce={l_max_drce}, k_max_drce={k_max_drce}). Some "
            f"columns of the sensing matrix will be identically zero; "
            f"those (l, k) coefficients cannot be estimated. NMSE will "
            f"be poor.",
            stacklevel=2)

    obs_offsets = np.arange(-N_g, N_g + 1)
    obs_idx = ((m0 + obs_offsets) % N).astype(np.int64)
    obs_set = set(obs_idx.tolist())
    data_pos = np.array([m for m in range(N) if m not in obs_set],
                         dtype=np.int64)

    # ---- 1. Build the pilot-impulse sensing slice M(m0) on the DRCE
    #         dictionary (l_max_drce, k_max_drce). At system l_max with no
    #         truncation (default), this is the full Phi; otherwise a smaller
    #         (l_max+1)*(2*k_max+1) -dim dictionary is used. ----
    # Carrier x_pilot has the boosted pilot value at m0 only.
    x_pilot_impulse = np.zeros(N, dtype=complex)
    x_pilot_impulse[m0] = pilot_value
    Phi_full = construct_sensing_matrix(N, x_pilot_impulse, c1, c2,
                                         l_max_drce, k_max_drce)
    M = Phi_full[obs_idx, :]                     # (2*N_g+1, Q_drce)
    y_obs = y[obs_idx]                            # (2*N_g+1,)

    # ---- 2. Closed-form Tikhonov LS (Yin Eq 25 spirit) ----
    if lam_tikh is None:
        lam_tikh = 1e-3 * float(sigma2)
    MhM = M.conj().T @ M
    Mhy = M.conj().T @ y_obs
    h_hat = np.linalg.solve(
        MhM + lam_tikh * np.eye(Q_drce, dtype=complex), Mhy)

    # ---- 3. Reconstruct H_eff via the standard AFDM phase formula. We use
    #         the DRCE dictionary (l_max_drce, k_max_drce); H_eff is still
    #         N×N but only the (l, k) ∈ DRCE-dictionary contributions are
    #         present. Long-delay taps beyond l_max_drce are missed. ----
    H_eff = reconstruct_H_from_omp(N, h_hat, k_max_drce, l_max_drce, c1, c2,
                                    threshold=0.0)

    # ---- 4. Data detection on the data positions (subtract pilot leak) ----
    pilot_leak = H_eff[:, m0] * pilot_value       # (N,)
    y_data_clean = y[data_pos] - pilot_leak[data_pos]
    H_dd = H_eff[np.ix_(data_pos, data_pos)]
    n_data = len(data_pos)
    data_scaling = float(np.sqrt((1.0 - rho) * N / n_data))
    const_scaled = data_scaling * constellation
    d_hat_data = _bp_detect(y_data_clean, H_dd, sigma2, const_scaled,
                             n_iter=detector_iter, damp=detector_damp)
    # Embed back into a length-N vector (zeros at obs_idx)
    d_hat = np.zeros(N, dtype=complex)
    d_hat[data_pos] = d_hat_data

    return dict(
        d_hat=d_hat, H_eff=H_eff, h_hat=h_hat,
        m0=int(m0), obs_idx=obs_idx, data_pos=data_pos,
        data_scaling=data_scaling, pilot_value=complex(pilot_value),
        l_max_drce=int(l_max_drce), k_max_drce=int(k_max_drce),
    )
