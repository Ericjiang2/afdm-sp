"""
diag_paper_h_eff_v2.py — exhaustive sign-convention search.

Three independent sign / conjugation toggles in Cao Eq (8) closed form:

  toggle A: t = (p + i) mod N        vs  t = (p − i) mod N
  toggle B: H[p, q] uses h[(q-p) mod N] vs h[(p-q) mod N]
  toggle C: Ξ is taken as-is             vs  conjugated

8 combinations total. For each, build H_cand from a known physical channel
(simulator's true taps and gains), and check whether H_cand @ x ≡ H_true @ x.
The right combination matches at machine precision.
"""
from __future__ import annotations

import pathlib
import sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK, _make_system_variable_N,
)


def build_xi(N, c1, c2, t_sign='+'):
    """Build Ξ(p, q) with t = (p + sign*q) mod N."""
    sign = +1 if t_sign == '+' else -1
    Nc1 = N * c1
    Nc2 = N * c2
    two_Nc1 = 2 * Nc1
    p_arr = np.arange(N, dtype=np.float64)
    Xi = np.zeros((N, N), dtype=complex)
    for q in range(N):
        t_arr = (p_arr + sign * q) % N
        a = (t_arr - p_arr + Nc1 - 0.5) % N
        epsilon = np.floor((a + 0.5) / two_Nc1).astype(np.float64)
        phase_arg = (2.0 * np.pi / N) * (Nc1 * (epsilon ** 2)
                                          - t_arr * epsilon
                                          + Nc2 * (t_arr ** 2 - p_arr ** 2))
        Xi[:, q] = np.exp(1j * phase_arg)
    return Xi


def make_h_paper(N, support_locs, gains, Xi, h_sign='q-p', conj=False):
    """Build H[p, q] = h[idx] · Xi[p, idx] (or conj)
    where idx = (q-p) mod N (h_sign='q-p') or (p-q) mod N (h_sign='p-q').
    """
    h = np.zeros(N, dtype=complex)
    for loc, g in zip(support_locs, gains):
        h[loc] = h[loc] + g
    H = np.zeros((N, N), dtype=complex)
    p_arr = np.arange(N, dtype=np.int64)
    for q in range(N):
        if h_sign == 'q-p':
            i_arr = (q - p_arr) % N
        else:
            i_arr = (p_arr - q) % N
        Xi_at = Xi[p_arr, i_arr]
        if conj:
            Xi_at = np.conj(Xi_at)
        H[:, q] = Xi_at * h[i_arr]
    return H


def main():
    print("=" * 70)
    print("Exhaustive sign-convention search (8 combinations)")
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

    np.random.seed(int(rng.integers(0, 2**31)))
    H_true, _, cp = sys_obj.generate_channel_matrix()
    l_i = np.asarray(cp['l_i'], dtype=int)
    k_int = np.round(cp['k_real']).astype(int)
    l_i = np.clip(l_i, 0, sys_obj.l_max_cap)
    k_int = np.clip(k_int, -sys_obj.k_max_cap, sys_obj.k_max_cap)
    g_i = np.asarray(cp['g_i'], dtype=complex)
    locs = [(int(k) + K * int(l)) % N for l, k in zip(l_i, k_int)]
    print(f"  taps: {[(int(l), int(k), abs(g), int(loc)) for l, k, g, loc in zip(l_i, k_int, g_i, locs)]}")

    pilot = sys_obj._zc_seq.copy()
    data = QPSK[rng.integers(0, 4, size=N)]
    x = np.sqrt(0.5) * pilot + np.sqrt(0.5) * data
    y_true = H_true @ x
    print()

    print(f"  {'t_sign':<8} {'h_sign':<8} {'conj':<6} {'max|y_cand−y_true|':<24} {'rel':<12} {'cos_sim':<10}")
    print(f"  {'-'*8} {'-'*8} {'-'*6} {'-'*24} {'-'*12} {'-'*10}")
    best = None
    for t_sign in ('+', '-'):
        Xi = build_xi(N, c1, c2, t_sign=t_sign)
        for h_sign in ('q-p', 'p-q'):
            for conj in (False, True):
                H_cand = make_h_paper(N, locs, g_i, Xi, h_sign=h_sign, conj=conj)
                y_cand = H_cand @ x
                diff = np.max(np.abs(y_cand - y_true))
                rel = diff / max(np.max(np.abs(y_true)), 1e-30)
                cos_sim = np.abs(np.vdot(y_cand, y_true)) / (
                    np.linalg.norm(y_cand) * np.linalg.norm(y_true) + 1e-30)
                tag = 'PASS' if rel < 1e-10 else ('GOOD' if cos_sim > 0.99 else '')
                print(f"  {t_sign:<8} {h_sign:<8} {str(conj):<6} {diff:<24.3e} {rel:<12.3e} {cos_sim:<10.4f} {tag}")
                if best is None or cos_sim > best[3]:
                    best = (t_sign, h_sign, conj, cos_sim, rel)
    print()
    print(f"  Best combination: t_sign={best[0]} h_sign={best[1]} conj={best[2]}")
    print(f"  cos_sim={best[3]:.4f}  rel_diff={best[4]:.3e}")


if __name__ == '__main__':
    main()
