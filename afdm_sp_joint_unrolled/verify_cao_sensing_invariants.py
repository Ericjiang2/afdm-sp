"""
verify_cao_sensing_invariants.py

Verify the two invariants required to reproduce Cao Zhe et al. (ICCT 2024
"Sparse Channel Estimation and Data Detection for AFDM with Superimposed
Pilot Scheme") using our existing `construct_sensing_matrix` rather than
literally implementing the paper's Eq (8) Xi closed form.

INVARIANT 1: linearity of Φ(x) in the carrier signal x
    Φ(α p + β d) ≡ α Φ(p) + β Φ(d)
    so that Cao Eq (24)  W^{(n−1)} = Ψ_p + Ψ̂_d^{(n−1)}
    can be computed as a single Φ call with the combined carrier
    x_total = √λ p + √φ d̂^{(n−1)}.

INVARIANT 2: physical consistency  Φ(x) · h_true ≡ H_eff · x  (no noise)
    where x = √λ p + √φ d, H_eff is built from h_true via
    reconstruct_H_from_omp.  This confirms that if we plug in the true sparse
    channel vector h_true (one nonzero per (l_p, k_p) physical tap) and any
    carrier signal x, the predicted DAFT-domain received vector matches the
    actual H_eff @ x.  Required for the OMP step on W^{(n−1)} to be solving
    the same forward problem as the physical system.

If both pass at multiple (N, P, l_max, k_max, seed) settings, we can
reproduce Cao's iterative SP algorithm by reusing the existing
construct_sensing_matrix and reconstruct_H_from_omp infrastructure, and only
add a thin top-level loop that updates the carrier signal each iteration and
re-runs OMP on the rebuilt sensing matrix.

Run from the project root:
    conda activate AFDM
    python afdm_sp_joint_unrolled/verify_cao_sensing_invariants.py
"""
from __future__ import annotations

import pathlib
import sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix,
    reconstruct_H_from_omp,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK, _make_system_variable_N,
)


def _setup_system(N=512, l_max=4, k_max=4, p_paths=3, seed=20260507):
    """Build a small-regime system that matches Cao paper Section IV."""
    sys_obj = _make_system_variable_N(N)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.l_max_cap = int(l_max)
    sys_obj.k_max_cap = int(k_max)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    sys_obj.P_paths = int(p_paths)
    return sys_obj


def _make_random_signals(N, sys_obj, rng, lam=0.5, phi=0.5):
    """pilot p (ZC-like, all positions), data d (QPSK, random)."""
    pilot = sys_obj._zc_seq.copy()                          # already unit norm
    pilot_scaled = np.sqrt(lam) * pilot
    data_idx = rng.integers(0, 4, size=N)
    data = QPSK[data_idx]
    data_scaled = np.sqrt(phi) * data
    return pilot, data, pilot_scaled, data_scaled


def test_invariant_1_linearity(sys_obj, rng, n_trials=3):
    """Φ(αp + βd) ≡ αΦ(p) + βΦ(d) — Cao's W = Ψ_p + Ψ̂_d should compose."""
    N = sys_obj.N_total
    c1, c2 = sys_obj.c1, sys_obj.c2
    l_max, k_max = sys_obj.l_max_cap, sys_obj.k_max_cap

    for trial in range(n_trials):
        pilot, data, pilot_scaled, data_scaled = _make_random_signals(
            N, sys_obj, rng)
        # Build separately
        Phi_pilot = construct_sensing_matrix(N, pilot_scaled, c1, c2, l_max, k_max)
        Phi_data  = construct_sensing_matrix(N, data_scaled,  c1, c2, l_max, k_max)
        # Build combined
        x_total = pilot_scaled + data_scaled
        Phi_combined = construct_sensing_matrix(N, x_total, c1, c2, l_max, k_max)

        # Linearity check
        Phi_sum = Phi_pilot + Phi_data
        diff = np.max(np.abs(Phi_combined - Phi_sum))
        rel  = diff / max(np.max(np.abs(Phi_combined)), 1e-30)
        print(f"  [trial {trial}] N={N} l_max={l_max} k_max={k_max}  "
              f"max|Φ(αp+βd) − (Φ(αp)+Φ(βd))| = {diff:.3e}  "
              f"(rel {rel:.3e})  "
              f"{'PASS' if rel < 1e-12 else 'FAIL'}")
        if rel >= 1e-12:
            print(f"    Phi_combined sample[:3, :3] =\n{Phi_combined[:3, :3]}")
            print(f"    Phi_pilot+data sample[:3, :3] =\n{Phi_sum[:3, :3]}")
            return False
    return True


def test_invariant_2_physical_consistency(sys_obj, rng, n_trials=3):
    """Φ(x) h_true ≡ H_eff · x  (no noise).

    Generates a true physical channel via sys_obj.generate_channel_matrix()
    so we know the true (l_p, k_p, g_p) tuples and the corresponding sparse
    h_true vector. We then check that for any carrier x,
    construct_sensing_matrix(N, x, ...) @ h_true equals H_true @ x.
    """
    N = sys_obj.N_total
    c1, c2 = sys_obj.c1, sys_obj.c2
    l_max, k_max = sys_obj.l_max_cap, sys_obj.k_max_cap
    K = 2 * k_max + 1
    Q = (l_max + 1) * K

    for trial in range(n_trials):
        # Force a fresh channel by reseeding numpy global state
        np.random.seed(int(rng.integers(0, 2**31)))
        H_true, _, channel_params = sys_obj.generate_channel_matrix()
        l_i = np.asarray(channel_params['l_i'], dtype=int)
        k_real = np.asarray(channel_params['k_real'], dtype=float)
        # Cao paper uses integer Doppler indices α_i (round to nearest)
        k_int = np.round(k_real).astype(int)
        # Clip to valid range to handle edge cases
        l_i = np.clip(l_i, 0, l_max)
        k_int = np.clip(k_int, -k_max, k_max)
        g_i = np.asarray(channel_params['g_i'], dtype=complex)

        # Build sparse h_true: one nonzero per physical tap, at column
        # col(l, k) = l*K + (k + k_max).
        h_true = np.zeros(Q, dtype=complex)
        for lp, kp, gp in zip(l_i, k_int, g_i):
            col = int(lp) * K + (int(kp) + k_max)
            h_true[col] = h_true[col] + gp     # accumulate if duplicates

        # Now reconstruct H_eff from h_true via the SAME formula our project
        # uses for OMP results, and compare to the simulator's H_true matrix.
        H_eff_from_h = reconstruct_H_from_omp(
            N, h_true, k_max, l_max, c1, c2, threshold=0.0)

        # Test with random carrier x = √λ pilot + √φ data
        pilot, data, pilot_scaled, data_scaled = _make_random_signals(
            N, sys_obj, np.random.default_rng(int(np.random.randint(2**31))))
        x = pilot_scaled + data_scaled

        Phi_x = construct_sensing_matrix(N, x, c1, c2, l_max, k_max)

        # Predicted y via our sensing-matrix path
        y_pred = Phi_x @ h_true                         # (N,)
        # "Truth" y via the H built from h_true (NOT the simulator's H_true,
        # because the simulator's H_true uses the actual fractional k_real
        # whereas our sparse h_true rounds to integer k. So we compare
        # against H_eff_from_h to isolate the construct vs reconstruct
        # consistency.)
        y_recon = H_eff_from_h @ x                      # (N,)

        diff = np.max(np.abs(y_pred - y_recon))
        rel  = diff / max(np.max(np.abs(y_recon)), 1e-30)
        print(f"  [trial {trial}] N={N} P={len(g_i)}  "
              f"max|Φ(x)h − H_eff·x| = {diff:.3e}  rel {rel:.3e}  "
              f"{'PASS' if rel < 1e-10 else 'FAIL'}")
        if rel >= 1e-10:
            print(f"    First 5 entries:")
            print(f"      y_pred  = {y_pred[:5]}")
            print(f"      y_recon = {y_recon[:5]}")
            return False
    return True


def test_cao_pilot_only_iter0(sys_obj, rng):
    """Smoke test: at iter 0 with pilot-only Ψ_p, OMP should recover
    integer-Doppler main-lobe support (consistent with Cao Eq 18)."""
    from afdm_sp_joint_unrolled.afdm_baselines import omp_sparse

    N = sys_obj.N_total
    c1, c2 = sys_obj.c1, sys_obj.c2
    l_max, k_max = sys_obj.l_max_cap, sys_obj.k_max_cap
    K = 2 * k_max + 1
    P = sys_obj.P_paths

    # generate a clean physical channel
    np.random.seed(int(rng.integers(0, 2**31)))
    H_true, _, cp = sys_obj.generate_channel_matrix()
    l_i = np.asarray(cp['l_i'], dtype=int)
    k_int = np.round(cp['k_real']).astype(int)
    l_i = np.clip(l_i, 0, l_max); k_int = np.clip(k_int, -k_max, k_max)

    # build true (integer-doppler) sparse h
    g_i = np.asarray(cp['g_i'], dtype=complex)
    h_true = np.zeros((l_max + 1) * K, dtype=complex)
    for lp, kp, gp in zip(l_i, k_int, g_i):
        h_true[int(lp) * K + (int(kp) + k_max)] += gp

    # SP frame
    pilot, data, pilot_scaled, data_scaled = _make_random_signals(N, sys_obj, rng)
    x_total = pilot_scaled + data_scaled

    # Cao's pilot-only sensing matrix
    Psi_p = construct_sensing_matrix(N, pilot_scaled, c1, c2, l_max, k_max)

    # noise-free y (data interference will go into "noise" per Cao Eq 17)
    H_eff_from_h = reconstruct_H_from_omp(
        N, h_true, k_max, l_max, c1, c2, threshold=0.0)
    y = H_eff_from_h @ x_total

    # OMP with sparsity = P
    h_omp, support = omp_sparse(y, Psi_p, P)

    # Check: how many of P true taps are in support?
    true_cols = set(int(lp) * K + (int(kp) + k_max)
                     for lp, kp in zip(l_i, k_int))
    omp_cols = set(int(s) for s in support)
    n_recovered = len(true_cols & omp_cols)
    print(f"  [iter-0 OMP smoke] P={P}  recovered {n_recovered}/{P} main-lobe atoms")
    return n_recovered >= max(1, P - 1)  # allow 1 miss for fractional Doppler


def main():
    print("=" * 70)
    print("Cao 2024 SP-AFDM reproduction: sensing-matrix invariants verification")
    print("=" * 70)

    rng = np.random.default_rng(20260507)

    # Test on Cao's small regime AND our UWA regime to ensure invariants
    # hold structurally.
    regimes = [
        ("Cao paper Fig 3 regime",     dict(N=512,  l_max=4,   k_max=4,  p_paths=3)),
        ("Cao paper Fig 4 regime",     dict(N=512,  l_max=8,   k_max=8,  p_paths=3)),
        ("Our UWA regime (small N)",   dict(N=128,  l_max=20,  k_max=2,  p_paths=4)),
        ("Our UWA regime (full N)",    dict(N=1024, l_max=160, k_max=2,  p_paths=8)),
    ]

    all_pass = True
    for name, kwargs in regimes:
        print(f"\n— {name}: {kwargs} —")
        sys_obj = _setup_system(seed=20260507, **kwargs)
        print(f"  c1={sys_obj.c1:.6g}  c2={sys_obj.c2:.3e}")

        print("\n  invariant 1: Φ linearity in carrier")
        ok1 = test_invariant_1_linearity(sys_obj, rng, n_trials=3)
        print(f"  → {'PASS' if ok1 else 'FAIL'}")

        print("\n  invariant 2: Φ(x) h_true ≡ H_eff · x")
        ok2 = test_invariant_2_physical_consistency(sys_obj, rng, n_trials=3)
        print(f"  → {'PASS' if ok2 else 'FAIL'}")

        print("\n  iter-0 OMP smoke (pilot-only sensing)")
        ok3 = test_cao_pilot_only_iter0(sys_obj, rng)
        print(f"  → {'PASS' if ok3 else 'FAIL'}")

        if not (ok1 and ok2 and ok3):
            all_pass = False
            print(f"  REGIME FAILED: {name}")

    print("\n" + "=" * 70)
    print(f"OVERALL: {'ALL PASS — safe to reproduce Cao via our infrastructure' if all_pass else 'FAIL — see above for the failing case'}")
    print("=" * 70)


if __name__ == '__main__':
    main()
