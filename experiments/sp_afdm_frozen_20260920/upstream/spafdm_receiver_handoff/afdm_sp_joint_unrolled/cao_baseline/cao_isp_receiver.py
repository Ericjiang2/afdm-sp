"""
cao_isp_receiver.py — Reproduction of Cao Zhe et al. 2024 ICCT
"Sparse Channel Estimation and Data Detection for AFDM with
Superimposed Pilot Scheme" (DOI: 10.1109/ICCT62411.2024.10946599).

Two parameterizations are exposed (basis='ours' | 'paper') because the
column-equivalence test at cao_basis_equivalence.py shows that our
construct_sensing_matrix and Cao's literal Eq (8) Ξ closed form yield
DIFFERENT per-column phase patterns (carrier x indexing matches, but the
c2*(t² − r²) vs c2*(r² − r_in²) terms differ). Both are valid AFDM sensing
matrices in different rotated coordinate systems; OMP recovers the same
physical-tap support; H_eff reconstruction differs in basis but represents
the same physical channel. We expose both so the user can verify
statistical BER equivalence head-to-head.

Algorithm (Cao Eq 18, 22-31):

  iter 0:
    Ψ_p = build_sensing(N, √λ p, ...)               # pilot-only
    OMP(y, Ψ_p, sparsity=P) → ĥ^(0), support^(0)
    Ĥ_eff^(0) = reconstruct(ĥ^(0))
    y_d = y − √λ Ĥ_eff^(0) @ p
    σ²_d^(0) = Σβ_h φ + σ²                          # Eq 21
    d̂^(0) = MP(y_d, Ĥ_eff^(0), σ²_d^(0))

  iter n (1..max_iter):
    x_total^(n−1) = √λ p + √φ d̂^(n−1)              # Eq 24 carrier
    W^(n−1) = build_sensing(N, x_total^(n−1), ...)
    OMP(y, W^(n−1), sparsity=P) → ĥ^(n), support^(n)
    Ĥ_eff^(n) = reconstruct(ĥ^(n))
    y_d = y − √λ Ĥ_eff^(n) @ p
    σ²_d^(n) = (2 Σβ_h φ + σ²) / N + σ²              # Eq 31 approx
    d̂^(n) = MP(y_d, Ĥ_eff^(n), σ²_d^(n))
    if ||ĥ^(n) − ĥ^(n−1)||_2 ≤ tol: break

Reused project utilities:
  - construct_sensing_matrix (afdm_baselines)        — for basis='ours'
  - omp_sparse                                        — both bases
  - reconstruct_H_from_omp                            — for basis='ours'
  - mp_detect_bp_torch                                — both bases (data detection)

Local additions:
  - build_sensing_matrix_paper (Cao Eq 8 closed form) — for basis='paper'
  - reconstruct_H_paper       (Cao Eq 9 H_eff)        — for basis='paper'
"""
from __future__ import annotations

import pathlib
import sys
from typing import Optional

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix,
    omp_sparse,
    reconstruct_H_from_omp,
)
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch  # noqa: E402


# =====================================================================
# Basis B — literal Cao Eq (8) Ξ closed form
# =====================================================================

def _build_xi_matrix(N, c1, c2):
    """Cao Eq (below 10): Ξ ∈ C^{N×N} closed-form construction.

    Ξ(p, q) = exp(j (2π/N)[N c_1 ε² − t ε + N c_2 (t² − p²)])
    where  t = ⟨p + q⟩_N
           ε = ⌊((⟨t − p + N c_1 − 1/2⟩_N + 1/2) / (2 N c_1))⌋

    Returns Xi (N, N) complex.
    """
    Nc1, Nc2 = N * c1, N * c2
    two_Nc1 = 2 * Nc1
    p_arr = np.arange(N, dtype=np.float64)
    Xi = np.zeros((N, N), dtype=complex)
    for q in range(N):
        t_arr = (p_arr + q) % N
        a = (t_arr - p_arr + Nc1 - 0.5) % N
        epsilon = np.floor((a + 0.5) / two_Nc1).astype(np.float64)
        phase_arg = (2.0 * np.pi / N) * (Nc1 * (epsilon ** 2)
                                          - t_arr * epsilon
                                          + Nc2 * (t_arr ** 2 - p_arr ** 2))
        Xi[:, q] = np.exp(1j * phase_arg)
    return Xi


def build_sensing_matrix_paper(N, x, c1, c2, l_max=None, k_max=None,
                                Xi_cached: Optional[np.ndarray] = None):
    """Cao Eq (12): Ψ[i][p] = Ξ(p, i) · x[⟨p − i⟩_N]. Returns Psi (N, N) complex.

    Ξ depends only on (N, c1, c2); pass Xi_cached to avoid recomputation
    across iterations of the receiver.
    """
    Xi = _build_xi_matrix(N, c1, c2) if Xi_cached is None else Xi_cached
    p_arr = np.arange(N, dtype=np.int64)
    Psi = np.zeros((N, N), dtype=complex)
    for i in range(N):
        r_in = (p_arr - i) % N
        Psi[:, i] = Xi[:, i] * x[r_in]
    return Psi


def reconstruct_H_paper(N, h_sparse, Xi_cached: np.ndarray):
    """Cao Eq (9) form, with the (p − q) cyclic-shift convention.

    NOTE on direction (2026-05-07 sign-convention diagnostic):
    The strict literal Eq (9) reading would give H_paper[r, q] = h[(q−r) mod N]
    · Ξ(r, (q−r) mod N), but that places non-zero entries on the OPPOSITE
    cyclic diagonal from our simulator's Π convention (forward shift in
    `generate_channel_matrix` and `reconstruct_H_from_omp`).  Empirically
    (cao_baseline/diag_paper_h_eff_v2.py 8-combination sign-search), the
    closest match to simulator H_true · x is obtained with the (p − q)
    convention, i.e. mirroring Eq (12) Ψ[i][p] = Ξ(p, i) · x[(p − i) mod N]
    via the substitution i = (p − q) mod N.  This still does NOT match at
    machine precision (cos_sim ≈ 0.64 vs 1.0), because the underlying Ξ
    closed-form phase from Eq (8) and our simulator's chirp / DAFT phase
    differ in the c1 coefficient sign and the t ε vs l n cross-term.  Use
    this reconstruction only for paper-basis OMP downstream (sparse-recovery
    representation in Cao's basis); BER will differ from `basis='ours'`.

    Returns H (N, N) complex such that for any sparse h indexed over Cao's
    loc-domain, H @ x is the paper-basis prediction of y.
    """
    p_arr = np.arange(N, dtype=np.int64)
    H = np.zeros((N, N), dtype=complex)
    for q in range(N):
        i_arr = (p_arr - q) % N    # CHANGED: was (q - p_arr); see docstring
        h_at = h_sparse[i_arr]
        Xi_at = Xi_cached[p_arr, i_arr]
        H[:, q] = Xi_at * h_at
    return H


# =====================================================================
# Bridge: convert support indices between (l, k) ours and loc_i paper
# =====================================================================

def loc_to_lk(loc_i: int, K: int, k_max: int, N: int):
    """Recover (l, k) from Cao's loc_i = ⟨k + K l⟩_N.

    Returns (l, k) for the unique (l, k) with l ∈ [0, l_max] and
    k ∈ [-k_max, k_max] satisfying loc_i ≡ k + K l (mod N).
    """
    # Try the natural decomposition first: loc = K*l + (k+k_max), with
    # column index col = K*l + (k+k_max) ∈ [0, (l_max+1)*K - 1].
    # Cao's loc_i = ⟨k + K l⟩_N. For small loc_i (< N), this gives:
    # if loc_i < N/2: l = ⌊(loc_i + N c_1) / (2 N c_1)⌋ = ⌊(loc_i + K/2) / K⌋
    # k = loc_i - K * l
    if loc_i < 0:
        loc_i = (loc_i + N) % N
    # Test if loc_i has natural decomposition (no mod-N wrap):
    # loc_i = K*l + k where k ∈ [-k_max, k_max], l ∈ [0, ...]
    # First try: l = round(loc_i / K), k = loc_i - K*l, must have |k| ≤ k_max
    l_est = int(round(loc_i / K))
    k_est = loc_i - K * l_est
    if -k_max <= k_est <= k_max:
        return l_est, k_est
    # Try mod-N wrap: loc_i' = loc_i - N (negative), find (l, k) with k = loc_i' - K*l
    loc_alt = loc_i - N
    l_alt = int(round(loc_alt / K))
    k_alt = loc_alt - K * l_alt
    if -k_max <= k_alt <= k_max:
        return l_alt, k_alt
    # Fallback: invalid loc — return -1
    return -1, 0


# =====================================================================
# Cao ISP receiver — main entry, basis-toggleable
# =====================================================================

def _bp_detect(y_d: np.ndarray, H_eff: np.ndarray, sigma2_d: float,
                constellation: np.ndarray, n_iter: int = 20,
                damp: float = 0.5) -> np.ndarray:
    """Wrap mp_detect_bp_torch as a hard-decision detector for compatibility
    with the receiver flow."""
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y_d, H_eff, sigma2_d, constellation,
                               n_iter=n_iter, threshold=1e-4, damp=damp,
                               device=dev, return_numpy=True, return_soft=False)


def cao_isp_receiver(
    y: np.ndarray,
    pilot: np.ndarray,            # un-scaled pilot vector (e.g. ZC sequence, |p|=1)
    *,
    N: int,
    c1: float,
    c2: float,
    l_max: int,
    k_max: int,
    P: int,                       # OMP sparsity (number of physical paths)
    sigma2: float,                # noise variance σ²
    constellation: np.ndarray,    # data alphabet (NOT scaled by √φ; raw)
    lam: float = 0.5,             # pilot power λ
    phi: float = 0.5,             # data  power φ  (λ + φ = 1)
    sum_betas: float = 1.0,       # Σ_i β_h_i; default 1 for unit total channel power
    basis: str = 'ours',          # 'ours' or 'paper'
    max_iter: int = 10,
    tol: float = 1e-6,
    return_trajectory: bool = False,
):
    """Run Cao 2024 ISP receiver. Returns dict with 'd_hat', 'h_hat', 'H_eff',
    'iter_done', and optional 'trajectory' (per-iter h, support, BER if true
    bits supplied — not yet wired)."""
    assert basis in ('ours', 'paper'), f"unknown basis {basis}"
    assert pilot.shape == (N,)
    assert y.shape == (N,)

    pilot_scaled = np.sqrt(lam) * pilot
    sqrt_phi = np.sqrt(phi)

    # Cache Ξ for paper basis (depends only on N, c1, c2)
    Xi_cache = _build_xi_matrix(N, c1, c2) if basis == 'paper' else None

    # Constellation scaled by √φ for the data subspace (Cao's d has power φ)
    const_scaled = sqrt_phi * constellation

    K = 2 * k_max + 1
    Q = (l_max + 1) * K  # ours-basis dictionary size
    h_dim = N if basis == 'paper' else Q

    def _build_sensing(x_carrier: np.ndarray) -> np.ndarray:
        if basis == 'ours':
            return construct_sensing_matrix(N, x_carrier, c1, c2, l_max, k_max)
        else:
            return build_sensing_matrix_paper(N, x_carrier, c1, c2,
                                              l_max=l_max, k_max=k_max,
                                              Xi_cached=Xi_cache)

    def _reconstruct_H(h_sparse: np.ndarray) -> np.ndarray:
        if basis == 'ours':
            return reconstruct_H_from_omp(N, h_sparse, k_max, l_max, c1, c2,
                                           threshold=0.0)
        else:
            return reconstruct_H_paper(N, h_sparse, Xi_cache)

    traj = [] if return_trajectory else None

    # ---- Iter 0: Cao Eq 18 (pilot-only sensing, OMP, MP detect) ----
    Phi_p = _build_sensing(pilot_scaled)
    h_hat, support = omp_sparse(y, Phi_p, P)
    H_eff = _reconstruct_H(h_hat)
    y_d = y - H_eff @ pilot_scaled
    sigma2_d = sum_betas * phi + sigma2                                 # Eq 21
    d_hat = _bp_detect(y_d, H_eff, sigma2_d, const_scaled)
    iter_done = 0
    h_prev = h_hat.copy()
    if traj is not None:
        traj.append(dict(iter=0, h=h_hat.copy(), support=list(support),
                          sigma2_d=sigma2_d))

    # ---- Iter n: Cao Eq 24, 28, 30, 31 (data-aided sensing matrix) ----
    for n in range(1, max_iter + 1):
        # Eq 24: Cao's d̂ has power φ (paper assumes E{|d_n|²}=φ). Here d_hat
        # comes from MP detector that returned hard decisions in the SCALED
        # alphabet (√φ · QPSK). So d_hat already incorporates √φ. We add the
        # pilot at √λ scale and use as the new carrier directly.
        x_total = pilot_scaled + d_hat              # carrier for W^(n-1)
        W = _build_sensing(x_total)
        h_hat, support = omp_sparse(y, W, P)
        H_eff = _reconstruct_H(h_hat)
        y_d = y - H_eff @ pilot_scaled
        sigma2_d = (2.0 * sum_betas * phi + sigma2) / N + sigma2          # Eq 31
        d_hat = _bp_detect(y_d, H_eff, sigma2_d, const_scaled)
        iter_done = n
        if traj is not None:
            traj.append(dict(iter=n, h=h_hat.copy(), support=list(support),
                              sigma2_d=sigma2_d))
        # Cao termination: ||ĥ^(n) − ĥ^(n−1)|| ≤ 1e-6
        # h vectors are over the same dictionary across iters within the same
        # basis (ours: Q = (l_max+1)K; paper: N), so the norm is well-defined.
        delta = np.linalg.norm(h_hat - h_prev)
        if delta <= tol:
            break
        h_prev = h_hat.copy()

    out = dict(d_hat=d_hat, h_hat=h_hat, H_eff=H_eff, iter_done=iter_done,
                support=list(support), basis=basis)
    if traj is not None:
        out['trajectory'] = traj
    return out


# =====================================================================
# Smoke test: run both bases on the same channel/data/noise, compare BER
# =====================================================================

def _test_dual_basis():
    """Compare 'ours' vs 'paper' on identical inputs over multiple frames.
    Expected: support recovers the same physical taps; BER statistically
    equivalent (not bit-exact)."""
    from afdm_sp_joint_unrolled.run_classical_baselines_python import (
        QPSK, _ber, _bits_of_symbol, _make_system_variable_N,
    )

    # Cao Fig 3 regime: N=512, l_max=4, k_max=4, P=3, BPSK or QPSK, λ=0.5
    sys_obj = _make_system_variable_N(512)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.l_max_cap = 4
    sys_obj.k_max_cap = 4
    sys_obj.P_paths = 3
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

    N = sys_obj.N_total
    c1, c2 = sys_obj.c1, sys_obj.c2
    l_max, k_max = sys_obj.l_max_cap, sys_obj.k_max_cap
    P = sys_obj.P_paths
    lam, phi = 0.5, 0.5

    rng_master = np.random.default_rng(20260507)

    print(f"[smoke] Cao Fig 3 regime: N={N}, l_max={l_max}, k_max={k_max}, P={P}")
    print(f"[smoke] λ={lam}, φ={phi}, basis ∈ {{ours, paper}}")
    print()
    print("  SNR  |   ours BER     |   paper BER    |  support overlap | n_frames")
    print("  -----+----------------+----------------+------------------+----------")

    for snr_db in [12, 15, 18, 21]:
        sigma2 = phi / (10 ** (snr_db / 10.0))   # SNR_d = φ/σ², per Cao Sec IV
        n_frames = 30
        errs_ours = errs_paper = 0
        bits_total = 0
        n_support_match = 0
        for fi in range(n_frames):
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            H_true, _, cp = sys_obj.generate_channel_matrix()
            data_idx = rng.integers(0, 4, size=N)
            data = QPSK[data_idx]
            bits_true = np.concatenate([(data.real < 0).astype(np.float32),
                                          (data.imag < 0).astype(np.float32)])
            x = np.sqrt(lam) * sys_obj._zc_seq + np.sqrt(phi) * data
            noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
            y = H_true @ x + np.sqrt(sigma2) * noise

            # Run both bases
            res_o = cao_isp_receiver(
                y, sys_obj._zc_seq, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
                P=P, sigma2=sigma2, constellation=QPSK,
                lam=lam, phi=phi, basis='ours', max_iter=10)
            res_p = cao_isp_receiver(
                y, sys_obj._zc_seq, N=N, c1=c1, c2=c2, l_max=l_max, k_max=k_max,
                P=P, sigma2=sigma2, constellation=QPSK,
                lam=lam, phi=phi, basis='paper', max_iter=10)

            # Decode bits — both d_hat are √φ·QPSK scale; un-scale before slicing
            b_o = _bits_of_symbol(res_o['d_hat'] / np.sqrt(phi), N)
            b_p = _bits_of_symbol(res_p['d_hat'] / np.sqrt(phi), N)
            errs_ours  += int((b_o != bits_true).sum())
            errs_paper += int((b_p != bits_true).sum())
            bits_total += 2 * N

            # Support overlap: convert paper's loc_i → (l,k) → ours col
            sup_o = set(int(s) for s in res_o['support'])
            sup_p_translated = set()
            for loc in res_p['support']:
                l_r, k_r = loc_to_lk(int(loc), K, k_max, N)
                if l_r >= 0 and l_r <= l_max and abs(k_r) <= k_max:
                    sup_p_translated.add(l_r * K + (k_r + k_max))
            overlap = len(sup_o & sup_p_translated) / max(len(sup_o), 1)
            if overlap > 0.5:
                n_support_match += 1

        ber_o = errs_ours / max(bits_total, 1)
        ber_p = errs_paper / max(bits_total, 1)
        print(f"  {snr_db:3d}  |  {ber_o:.4e}    |  {ber_p:.4e}    |  "
              f"{n_support_match}/{n_frames} ({100*n_support_match/n_frames:.0f}%)  "
              f"|  {n_frames}")


if __name__ == '__main__':
    _test_dual_basis()
