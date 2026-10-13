"""
cao_basis_equivalence.py

Verify that two parameterizations of the AFDM SP-AFDM sensing matrix produce
identical columns at every valid (l, k) tap.

Version A — "ours": construct_sensing_matrix(N, x, c1, c2, l_max, k_max)
    Column index: col(l, k) = l * K + (k + k_max),  K = 2 k_max + 1.
    Column entry: Phi[r, col(l,k)] = exp(j 2π[−c_1 l² + c_2 (r² − r_in²) − l r_in / N]) · x[r_in]
    where r_in = (r − δ) mod N,  δ = l*K + k.

Version B — "paper" (Cao Eq 8 / Eq 12-13):
    Column index: i ∈ [0, N − 1], i.e. loc_i = ⟨k + 2 N c_1 l⟩_N = ⟨k + K l⟩_N.
    Column entry: Psi[r, i] = Ξ(r, i) · x[⟨r − i⟩_N]
    where  t  = ⟨r + i⟩_N
           ε  = ⌊((⟨t − r + N c_1 − 1/2⟩_N + 1/2) / (2 N c_1))⌋   (recovered delay l)
           Ξ(r, i) = exp(j (2π/N)[N c_1 ε² − t ε + N c_2 (t² − r²)])

If for every valid (l, k):
    our_Phi[:, col(l, k)]  ≡  cao_Psi[:, loc(l, k)]
(or differs by at most a per-column global phase), then OMP/MP/H reconstruction
results are identical up to support reindexing → identical BER.

If they differ structurally, we need both versions in the receiver.
"""
from __future__ import annotations

import pathlib
import sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.afdm_baselines import construct_sensing_matrix  # noqa: E402
from afdm_sp_joint_unrolled.run_classical_baselines_python import _make_system_variable_N, QPSK  # noqa: E402


def build_sensing_matrix_paper(N, x, c1, c2, l_max, k_max):
    """Cao Eq (8) / (12)-(13) literal closed-form sensing matrix.

    Builds the FULL N × N matrix Ψ where column i corresponds to channel
    residue index loc_i = i. Returns Psi (N, N) complex.

    Per the paper, only the loc(l, k) = ⟨k + K l⟩_N indices for (l, k) in the
    valid range are physically meaningful; other columns correspond to wrapped
    delays > l_max or Dopplers > k_max and would (in noise-free) yield zero
    correlation with y.
    """
    K = 2 * k_max + 1
    Nc1 = N * c1
    two_Nc1 = 2 * Nc1
    Nc2 = N * c2

    Psi = np.zeros((N, N), dtype=complex)
    r_arr = np.arange(N, dtype=np.float64)
    inv_N = 1.0 / N

    for i in range(N):
        # t = ⟨r + i⟩_N
        t_arr = (r_arr + i) % N
        # ε = ⌊((⟨t − r + Nc1 − 1/2⟩_N + 1/2) / (2 Nc1))⌋
        # = recovered delay l from loc_i = i
        # In numpy, ⟨a⟩_N for non-integer a is mod-N to [0, N)
        a = (t_arr - r_arr + Nc1 - 0.5) % N
        epsilon = np.floor((a + 0.5) / two_Nc1).astype(np.int64)
        # Ξ(r, i) phase
        phase_arg = (Nc1 * (epsilon ** 2)
                     - t_arr * epsilon
                     + Nc2 * (t_arr ** 2 - r_arr ** 2)) * (2.0 * np.pi / N)
        Xi_col = np.exp(1j * phase_arg)
        # Carrier x[⟨r − i⟩_N]
        r_in = (r_arr.astype(np.int64) - i) % N
        Psi[:, i] = Xi_col * x[r_in]

    return Psi


def loc_of(l, k, K, N):
    """Compute Cao's loc_i = ⟨k + K l⟩_N for a (l, k) tap."""
    return (int(k) + K * int(l)) % N


def main():
    print("=" * 70)
    print("Column equivalence test: ours vs Cao Eq (8) literal closed form")
    print("=" * 70)

    rng = np.random.default_rng(20260507)
    regimes = [
        ("Cao Fig 3 regime",        dict(N=512,  l_max=4,   k_max=4,  p_paths=3)),
        ("Our UWA small N",         dict(N=128,  l_max=20,  k_max=2,  p_paths=4)),
        ("Our UWA full N",          dict(N=1024, l_max=160, k_max=2,  p_paths=8)),
    ]

    all_pass = True
    for name, kw in regimes:
        print(f"\n— {name}: {kw} —")
        sys_obj = _make_system_variable_N(kw['N'])
        sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
        sys_obj.l_max_cap = int(kw['l_max'])
        sys_obj.k_max_cap = int(kw['k_max'])
        K = 2 * sys_obj.k_max_cap + 1
        sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
        sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
        sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

        N = sys_obj.N_total
        c1, c2 = sys_obj.c1, sys_obj.c2
        l_max, k_max = sys_obj.l_max_cap, sys_obj.k_max_cap

        # Random carrier signal
        pilot = sys_obj._zc_seq.copy()
        x = pilot * 0.5 + (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(8)

        # Build both sensing matrices
        ours = construct_sensing_matrix(N, x, c1, c2, l_max, k_max)
        paper = build_sensing_matrix_paper(N, x, c1, c2, l_max, k_max)
        print(f"  ours shape  = {ours.shape}  (Q = (l_max+1)·K)")
        print(f"  paper shape = {paper.shape}  (Cao N × N)")

        # Compare each valid (l, k) column
        n_match = 0
        n_phase_match = 0
        n_diff = 0
        max_abs_diff = 0.0
        max_phase_diff = 0.0
        first_failure = None
        for l in range(l_max + 1):
            for k in range(-k_max, k_max + 1):
                our_col = l * K + (k + k_max)
                cao_loc = loc_of(l, k, K, N)
                ours_v  = ours[:, our_col]
                paper_v = paper[:, cao_loc]
                # Direct equality check
                d_abs = np.max(np.abs(ours_v - paper_v))
                d_rel = d_abs / max(np.max(np.abs(ours_v)), 1e-30)
                if d_rel < 1e-12:
                    n_match += 1
                    continue
                # Equality up to per-column global phase?
                # ratio = ours_v / paper_v  (where paper_v ≠ 0)
                mask = np.abs(paper_v) > 1e-12
                if mask.any():
                    ratio = ours_v[mask] / paper_v[mask]
                    # All ratios should be the same complex number if differ by phase
                    rstd = np.std(ratio) / max(np.mean(np.abs(ratio)), 1e-30)
                    rmean = np.mean(ratio)
                    if rstd < 1e-10 and abs(np.abs(rmean) - 1.0) < 1e-9:
                        n_phase_match += 1
                        max_phase_diff = max(max_phase_diff, abs(np.angle(rmean)))
                        continue
                # Real difference
                n_diff += 1
                if first_failure is None:
                    first_failure = (l, k, our_col, cao_loc, d_abs, d_rel)
                max_abs_diff = max(max_abs_diff, d_abs)

        Q = (l_max + 1) * K
        total = Q
        print(f"  bit-exact equal:           {n_match}/{total}")
        print(f"  equal-up-to-global-phase:  {n_phase_match}/{total}  (max angle: {max_phase_diff:.3e} rad)")
        print(f"  structurally different:    {n_diff}/{total}  (max abs diff: {max_abs_diff:.3e})")
        if first_failure:
            l, k, oc, cl, da, dr = first_failure
            print(f"  first failure: (l={l}, k={k}, our_col={oc}, cao_loc={cl}) "
                  f"abs_diff={da:.3e} rel_diff={dr:.3e}")
            print(f"    ours_v[:5]  = {ours[:5, oc]}")
            print(f"    paper_v[:5] = {paper[:5, cl]}")
        regime_pass = (n_diff == 0)
        print(f"  → {'PASS' if regime_pass else 'FAIL'}")
        if not regime_pass:
            all_pass = False

    print("\n" + "=" * 70)
    print(f"OVERALL: {'ALL PASS' if all_pass else 'FAIL'}")
    print("=" * 70)


if __name__ == '__main__':
    main()
