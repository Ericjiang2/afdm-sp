"""
diagnose_convention.py — verify pbigabp_receiver.build_path_table convention
matches the AFDM simulator's generate_channel_matrix output.

Smoke test passes on synthetic 2-path channel (NMSE -37 dB), but PBiGaBP
gives BER ~30% on the real eval frame. Hypothesis: my path_table phase /
delta convention disagrees with sys_obj.generate_channel_matrix.

This diagnostic projects a real H_true onto the path-table basis and
reconstructs. If the reconstruction NMSE is << 0 dB, the convention matches.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (  # noqa: E402
    _make_system_variable_N, QPSK,
)
from afdm_sp_joint_unrolled.pbigabp_baseline.pbigabp_receiver import (  # noqa: E402
    build_path_table,
)


def main():
    sys_obj = _make_system_variable_N(1024)
    sys_obj.P_paths = 8
    sys_obj.tau_spread = 0.010
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = "python"
    sys_obj.v_mean = 2.0
    sys_obj.B = 4e3
    sys_obj.fs = 4 * sys_obj.B
    sys_obj.Ts = 1.0 / sys_obj.fs
    v_max = sys_obj.v_mean + 1.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(1024 * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

    print(f"Setup: l_max={sys_obj.l_max_cap}, k_max={sys_obj.k_max_cap}, "
          f"c1={sys_obj.c1:.6f}, c2={sys_obj.c2:.6e}")

    np.random.seed(20260419)
    H_true, _, _ = sys_obj.generate_channel_matrix()
    fro = np.linalg.norm(H_true, ord='fro')
    print(f"H_true Fro norm: {fro:.3f} (expected ~sqrt(N)={np.sqrt(1024):.3f})")

    paths, Q, K2 = build_path_table(
        1024, sys_obj.l_max_cap, sys_obj.k_max_cap, sys_obj.c1, sys_obj.c2)
    print(f"Q = {Q}, K = {K2}")
    h_proj = np.zeros(Q, dtype=complex)
    energy_per_path = np.zeros(Q, dtype=float)
    for p in paths:
        j = p['idx']
        q = p['q_of_n']
        phase = p['phase_of_n']
        # Each path j projects H_true[n, q_p(n)] onto phase[n]
        # If only path j is active, H_true[n, q_p(n)] = h_j * phase_j[n]
        # so h_j = mean over n of H_true[n, q_p(n)] / phase[n]
        proj = H_true[np.arange(1024), q] / phase
        h_proj[j] = np.mean(proj)
        energy_per_path[j] = np.sum(np.abs(proj) ** 2)

    print()
    print("Top-10 paths by |h_proj|:")
    top = np.argsort(-np.abs(h_proj))[:10]
    for t in top:
        l_idx = t // K2
        k_idx = (t % K2) - sys_obj.k_max_cap
        print(f"  j={t:4d}  l={l_idx:3d}  k={k_idx:+3d}  "
              f"|h_proj|={np.abs(h_proj[t]):.4f}  "
              f"energy={energy_per_path[t]:.2f}")

    H_recon = np.zeros((1024, 1024), dtype=complex)
    for p in paths:
        j = p['idx']
        q = p['q_of_n']
        phase = p['phase_of_n']
        H_recon[np.arange(1024), q] += h_proj[j] * phase
    nmse = ((np.abs(H_recon - H_true) ** 2).sum()
            / (np.abs(H_true) ** 2).sum())
    print()
    print(f"Path-table-reconstruct NMSE: {nmse:.3e} "
          f"({10*np.log10(nmse):+.2f} dB)")
    if nmse < 1e-3:
        print("  CONVENTION MATCH (NMSE < -30 dB)")
    elif nmse < 1.0:
        print("  PARTIAL MATCH (some convention mismatch)")
    else:
        print("  CONVENTION MISMATCH (NMSE > 0 dB) — bug in build_path_table!")

    # Cross-check: use the existing reconstruct_H_from_omp helper (the canonical
    # AFDM formula used by Cao & DRCE) on h_proj — this should give the same
    # reconstruction (or different if my convention differs from canonical)
    from afdm_sp_joint_unrolled.afdm_baselines import reconstruct_H_from_omp
    H_recon_canon = reconstruct_H_from_omp(
        1024, h_proj, sys_obj.k_max_cap, sys_obj.l_max_cap,
        sys_obj.c1, sys_obj.c2, threshold=0.0)
    nmse_canon = ((np.abs(H_recon_canon - H_true) ** 2).sum()
                   / (np.abs(H_true) ** 2).sum())
    print(f"reconstruct_H_from_omp NMSE: {nmse_canon:.3e} "
          f"({10*np.log10(nmse_canon):+.2f} dB)")
    if nmse_canon < 1e-3:
        print("  CANONICAL HELPER MATCHES SIMULATOR — h_proj is correct")
    diff_recon = ((np.abs(H_recon - H_recon_canon) ** 2).sum()
                   / (np.abs(H_recon_canon) ** 2).sum() + 1e-30)
    print(f"path_table vs reconstruct_H_from_omp NMSE: {diff_recon:.3e} "
          f"({10*np.log10(diff_recon):+.2f} dB)")


if __name__ == '__main__':
    main()
