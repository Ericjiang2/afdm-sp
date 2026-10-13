"""
diag_paper_h_eff.py

Direct test: does reconstruct_H_paper(h_true_paper) act on x like the
simulator's H_true? If not, find the right convention (sign of mod-N
shift, conjugation, etc.) by enumeration.

Approach:
  1. Generate a single physical channel via simulator → H_true
  2. Build h_true_paper sparse over loc_i = ⟨k + K l⟩_N for each phys tap
  3. Try several candidate formulas for H_paper[r, q]:
     A: h[(q - r) mod N] · Ξ(r, (q - r) mod N)    (my current)
     B: h[(r - q) mod N] · Ξ(r, (r - q) mod N)    (sign flip)
     C: h[(q - r) mod N] · Ξ(r, (q - r) mod N).conj()
     D: h[(r - q) mod N] · Ξ(r, (r - q) mod N).conj()
  4. For each candidate, compute pred_y = H_cand @ x_total, compare
     against H_true @ x_total. The right one will match (up to noise-free
     equality).

Run from project root:
    python afdm_sp_joint_unrolled/cao_baseline/diag_paper_h_eff.py
"""
from __future__ import annotations

import pathlib
import sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.cao_baseline.cao_isp_receiver import _build_xi_matrix  # noqa: E402
from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK, _make_system_variable_N,
)


def make_h_paper_A(N, support_locs, gains, Xi):
    """h[(q-r) mod N] · Ξ(r, (q-r) mod N)"""
    h = np.zeros(N, dtype=complex)
    for loc, g in zip(support_locs, gains):
        h[loc] = h[loc] + g
    H = np.zeros((N, N), dtype=complex)
    p_arr = np.arange(N, dtype=np.int64)
    for q in range(N):
        i_arr = (q - p_arr) % N
        H[:, q] = Xi[p_arr, i_arr] * h[i_arr]
    return H


def make_h_paper_B(N, support_locs, gains, Xi):
    """h[(r-q) mod N] · Ξ(r, (r-q) mod N)"""
    h = np.zeros(N, dtype=complex)
    for loc, g in zip(support_locs, gains):
        h[loc] = h[loc] + g
    H = np.zeros((N, N), dtype=complex)
    p_arr = np.arange(N, dtype=np.int64)
    for q in range(N):
        i_arr = (p_arr - q) % N
        H[:, q] = Xi[p_arr, i_arr] * h[i_arr]
    return H


def make_h_paper_C(N, support_locs, gains, Xi):
    """h[(q-r) mod N] · Ξ(r, (q-r) mod N).conj()"""
    h = np.zeros(N, dtype=complex)
    for loc, g in zip(support_locs, gains):
        h[loc] = h[loc] + g
    H = np.zeros((N, N), dtype=complex)
    p_arr = np.arange(N, dtype=np.int64)
    for q in range(N):
        i_arr = (q - p_arr) % N
        H[:, q] = np.conj(Xi[p_arr, i_arr]) * h[i_arr]
    return H


def make_h_paper_D(N, support_locs, gains, Xi):
    """h[(r-q) mod N] · Ξ(r, (r-q) mod N).conj()"""
    h = np.zeros(N, dtype=complex)
    for loc, g in zip(support_locs, gains):
        h[loc] = h[loc] + g
    H = np.zeros((N, N), dtype=complex)
    p_arr = np.arange(N, dtype=np.int64)
    for q in range(N):
        i_arr = (p_arr - q) % N
        H[:, q] = np.conj(Xi[p_arr, i_arr]) * h[i_arr]
    return H


def main():
    print("=" * 70)
    print("Diagnose H_paper reconstruction sign/conjugate convention")
    print("=" * 70)

    rng = np.random.default_rng(20260507)
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
    print(f"  N={N}, c1={c1:.6g}, c2={c2:.3e}, K={K}")

    Xi = _build_xi_matrix(N, c1, c2)

    # Generate one physical channel
    np.random.seed(int(rng.integers(0, 2**31)))
    H_true, _, cp = sys_obj.generate_channel_matrix()
    l_i = np.asarray(cp['l_i'], dtype=int)
    k_int = np.round(cp['k_real']).astype(int)
    l_i = np.clip(l_i, 0, sys_obj.l_max_cap)
    k_int = np.clip(k_int, -sys_obj.k_max_cap, sys_obj.k_max_cap)
    g_i = np.asarray(cp['g_i'], dtype=complex)

    # Build loc indices
    locs = [(int(k) + K * int(l)) % N for l, k in zip(l_i, k_int)]
    print(f"  physical taps:")
    for l, k, g, loc in zip(l_i, k_int, g_i, locs):
        print(f"    (l={l:3d}, k={k:+d}, |g|={abs(g):.3f})  loc={loc}")

    # Random carrier
    pilot = sys_obj._zc_seq.copy()
    data = QPSK[rng.integers(0, 4, size=N)]
    x = np.sqrt(0.5) * pilot + np.sqrt(0.5) * data

    y_true = H_true @ x

    candidates = [
        ("A: h[(q-r) mod N], Ξ no conj",    make_h_paper_A),
        ("B: h[(r-q) mod N], Ξ no conj",    make_h_paper_B),
        ("C: h[(q-r) mod N], Ξ conj",       make_h_paper_C),
        ("D: h[(r-q) mod N], Ξ conj",       make_h_paper_D),
    ]
    for name, fn in candidates:
        H_cand = fn(N, locs, g_i, Xi)
        y_cand = H_cand @ x
        diff = np.max(np.abs(y_cand - y_true))
        rel = diff / max(np.max(np.abs(y_true)), 1e-30)
        # Also check the matched relative correlation
        cos_sim = np.abs(np.vdot(y_cand, y_true)) / (
            np.linalg.norm(y_cand) * np.linalg.norm(y_true) + 1e-30)
        print(f"  {name:40s}  max|H_cand·x − H_true·x| = {diff:.3e}  "
              f"rel = {rel:.3e}  cos_sim = {cos_sim:.4f}")


if __name__ == '__main__':
    main()
