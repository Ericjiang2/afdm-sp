"""
verify_omp_extended.py — sanity checks for omp_extended_k* baseline.

Three checks:

  1. OMP-(P+0) bit-exact ≡ baseline OMP-P
     If the routing via `oracle_support=...` introduces any distortion (LS
     numerics, ordering effects, etc.), this catches it. Should produce
     identical (BER, NMSE, x_soft, H_hat) to the native baseline.

  2. OMP-(P+K) support is a SUPERSET of OMP-P support
     `omp_sparse` is greedy and deterministic, so the first P selections
     from OMP-(P+K) MUST equal OMP-P's selections (in order).

  3. Inspect the K extra atoms picked by OMP-(P+K)
     Decode each extra column index → (l, k) and compare against:
       (a) the simulator's true physical taps (l_p, round(k_p_real))
       (b) the Dirichlet-expanded sidelobes around physical taps
       (c) atoms that look like data-leakage (high correlation but no
           physical-channel basis)
     This is the mechanism check for "OMP picks data-leakage atoms".

Run from the project root (locally or remotely):
    conda activate AFDM
    python afdm_sp_joint_unrolled/verify_omp_extended.py \
        --snr 15 --frame-idx 0 --k-extra 4 --seed 20260419
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import numpy as np
import torch

# Resolve project root from this file's location so it works both locally and
# on the deinlab remote without hard-coding an absolute path.
HERE = pathlib.Path(__file__).resolve().parent  # .../afdm_sp_joint_unrolled/
REPO_DIR = HERE.parent                            # .../AFDM-channel-estimation/
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled import afdm_baselines as _afb  # noqa: E402
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch  # noqa: E402


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
             damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                               threshold=threshold, damp=damp, device=dev,
                               return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    construct_sensing_matrix,
    joint_omp_mp_iterative,
    omp_sparse,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK, _bits_of_symbol, _ber, _nmse, _make_system_variable_N,
)


def setup_system(n_total=1024, v_mean=2.0, p_paths=8, fs_factor=2.0,
                  rho=None):
    sys_obj = _make_system_variable_N(n_total)
    sys_obj.fs = float(sys_obj.fs) * float(fs_factor)
    sys_obj.P_paths = int(p_paths)
    sys_obj.v_mean = float(v_mean)
    if rho is not None:
        sys_obj.rho = float(rho)
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    sys_obj.l_max_cap = max(int(np.ceil(sys_obj.tau_spread * sys_obj.fs)), 1)
    v_max = float(sys_obj.v_mean) + 3.0 * float(getattr(sys_obj, 'v_std', 0.5))
    d_max = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(n_total * d_max)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    return sys_obj


def gen_one_frame(sys_obj, snr_db, frame_idx, master_seed):
    """Reproduce the same frame the headroom probe used at this index."""
    rng_master = np.random.default_rng(master_seed)
    # Burn through prior frames within the same SNR.
    seed_fi = None
    for _ in range(frame_idx + 1):
        seed_fi = int(rng_master.integers(0, 2 ** 31))
    np.random.seed(seed_fi)
    rng = np.random.default_rng(seed_fi)

    N = sys_obj.N_total
    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    H_true, _, channel_params = sys_obj.generate_channel_matrix()
    sys_obj._last_channel_params = channel_params

    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    bits_true = np.zeros(2 * N, dtype=np.float32)
    bits_true[:N] = (data_qam.real < 0).astype(np.float32)
    bits_true[N:] = (data_qam.imag < 0).astype(np.float32)

    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = H_true @ x_sp + np.sqrt(sigma2) * noise
    return dict(
        y_daft=y_daft, pilot_scaled=pilot_scaled, data_qam=data_qam,
        bits_true=bits_true, H_true=H_true, sigma2=sigma2,
        const_data=const_data, channel_params=channel_params,
        rho=rho, P_d=P_d, N=N,
    )


def common_kwargs(sys_obj, sigma2, sparsity, rho, const_data):
    return dict(
        N=sys_obj.N_total, c1=sys_obj.c1, c2=sys_obj.c2,
        l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        sigma2=sigma2, constellation_data=const_data,
        n_paths=sparsity, n_outer_iter=5, rho=rho,
        pic_iter=20, pic_damp=0.5, mp_mode='bp',
        gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1,
        k_leak=2, update_sigma2=True, phase_convention='python',
    )


def run_baseline(frame, sys_obj, sparsity):
    kw = common_kwargs(sys_obj, frame['sigma2'], sparsity, frame['rho'],
                        frame['const_data'])
    x_soft, H_hat = joint_omp_mp_iterative(
        frame['y_daft'], frame['pilot_scaled'], **kw)
    return x_soft, H_hat


def run_via_oracle_support(frame, sys_obj, support, sparsity_for_kw):
    kw = common_kwargs(sys_obj, frame['sigma2'], sparsity_for_kw,
                        frame['rho'], frame['const_data'])
    x_soft, H_hat = joint_omp_mp_iterative(
        frame['y_daft'], frame['pilot_scaled'], **kw,
        oracle_support=support)
    return x_soft, H_hat


def decode_lk(idx, k_max, K):
    l = idx // K
    k = (idx % K) - k_max
    return l, k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snr', type=int, default=15)
    ap.add_argument('--frame-idx', type=int, default=0)
    ap.add_argument('--k-extra', type=int, default=4)
    ap.add_argument('--seed', type=int, default=20260419)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--fs-factor', type=float, default=2.0)
    args = ap.parse_args()

    sys_obj = setup_system(args.n_total, args.v_mean, args.p_paths,
                            args.fs_factor)
    K = 2 * sys_obj.k_max_cap + 1
    print(f"[setup] N={sys_obj.N_total} P={sys_obj.P_paths} "
          f"l_max={sys_obj.l_max_cap} k_max={sys_obj.k_max_cap} K={K}")

    # Generate the same frame the production probe would produce.
    frame = gen_one_frame(sys_obj, args.snr, args.frame_idx, args.seed)
    p_actual = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
    sparsity = max(p_actual, int(sys_obj.P_paths))
    print(f"[frame] snr={args.snr}dB idx={args.frame_idx} "
          f"sparsity(P)={sparsity}")
    cp = frame['channel_params']
    l_phys = np.asarray(cp['l_i'], dtype=int)
    k_real_phys = np.asarray(cp['k_real'], dtype=float)
    k_round_phys = np.round(k_real_phys).astype(int)
    g_phys = np.asarray(cp['g_i'], dtype=complex)
    phys_pairs = list(zip(l_phys.tolist(), k_round_phys.tolist(),
                           np.abs(g_phys).tolist()))
    phys_pairs.sort(key=lambda r: -r[2])
    print(f"[phys taps (l, k_round, |g|)] sorted by gain:")
    for lp, kp, gp in phys_pairs[:args.p_paths + args.k_extra]:
        print(f"    (l={lp:3d}, k={kp:+d}, |g|={gp:.4f})")

    # Build sensing matrix
    Phi = construct_sensing_matrix(
        sys_obj.N_total, frame['pilot_scaled'], sys_obj.c1, sys_obj.c2,
        sys_obj.l_max_cap, sys_obj.k_max_cap)
    Q = Phi.shape[1]
    print(f"[Phi] shape={Phi.shape}  Q={Q}")

    # ---- (1) Run OMP-P externally and OMP-(P+K) externally ----
    _, sup_P = omp_sparse(frame['y_daft'], Phi, sparsity)
    _, sup_PK = omp_sparse(frame['y_daft'], Phi, sparsity + args.k_extra)
    print(f"\n[OMP-P  support]  size={len(sup_P)}  cols={sup_P}")
    print(f"[OMP-PK support]  size={len(sup_PK)}  cols={sup_PK}")

    # ---- Check: OMP-PK first P columns == OMP-P columns ----
    superset_ok = (sup_PK[:sparsity] == sup_P)
    print(f"\n[CHECK 2: OMP-PK[:P] == OMP-P]  {'PASS' if superset_ok else 'FAIL'}")
    extras = sup_PK[sparsity:]
    print(f"[K-extras (OMP-PK[P:])]  cols={extras}")
    print(f"[K-extras decoded (l, k)]:")
    for i, idx in enumerate(extras):
        l, k = decode_lk(idx, sys_obj.k_max_cap, K)
        # Classify: is this an integer-Doppler main lobe (l, k) of a phys tap?
        # Or a ±1 Doppler sidelobe? Or unrelated?
        is_main = any(lp == l and kp == k for lp, kp, _ in phys_pairs)
        is_sidelobe = any(lp == l and abs(kp - k) <= 2 and kp != k
                           for lp, kp, _ in phys_pairs)
        is_delay_sidelobe = any(abs(lp - l) <= 2 and lp != l and kp == k
                                 for lp, kp, _ in phys_pairs)
        tag = (
            'MAIN_LOBE' if is_main else
            'DOPPLER_SIDELOBE_pm2' if is_sidelobe else
            'DELAY_SIDELOBE_pm2' if is_delay_sidelobe else
            'UNRELATED'
        )
        print(f"    extra[{i}]: col={idx:4d}  (l={l:3d}, k={k:+d})  → {tag}")

    # ---- (2) BIT-EXACT TEST: OMP-(P+0) via oracle_support ≡ baseline ----
    print(f"\n[CHECK 3: bit-exact omp_extended_k0 vs baseline]")
    x_base, H_base = run_baseline(frame, sys_obj, sparsity)
    # Now run via the omp_extended_k0 codepath (external OMP-P + oracle_support)
    x_k0, H_k0 = run_via_oracle_support(frame, sys_obj, sup_P, sparsity)

    diff_x = float(np.max(np.abs(x_base - x_k0)))
    diff_H = float(np.max(np.abs(H_base - H_k0)))
    print(f"    max|x_base - x_k0| = {diff_x:.3e}")
    print(f"    max|H_base - H_k0| = {diff_H:.3e}")
    bit_exact = (diff_x < 1e-9 and diff_H < 1e-9)
    print(f"    {'PASS (bit-exact)' if bit_exact else 'FAIL — routing introduces drift'}")

    ber_base = _ber(_bits_of_symbol(x_base / np.sqrt(frame['P_d']), frame['N']),
                     frame['bits_true'])
    ber_k0 = _ber(_bits_of_symbol(x_k0 / np.sqrt(frame['P_d']), frame['N']),
                   frame['bits_true'])
    nmse_base_db = 10 * np.log10(_nmse(H_base, frame['H_true']))
    nmse_k0_db = 10 * np.log10(_nmse(H_k0, frame['H_true']))
    print(f"    BER  base={ber_base:.6e}  k0={ber_k0:.6e}")
    print(f"    NMSE base={nmse_base_db:.3f}  k0={nmse_k0_db:.3f}")

    # ---- (3) Show what omp_extended_k4 produces vs baseline on this frame ----
    print(f"\n[CHECK 4: BER comparison this frame]")
    x_kK, H_kK = run_via_oracle_support(frame, sys_obj, sup_PK,
                                          sparsity + args.k_extra)
    ber_kK = _ber(_bits_of_symbol(x_kK / np.sqrt(frame['P_d']), frame['N']),
                   frame['bits_true'])
    nmse_kK_db = 10 * np.log10(_nmse(H_kK, frame['H_true']))
    print(f"    BER  base={ber_base:.6e}  k{args.k_extra}={ber_kK:.6e}")
    print(f"    NMSE base={nmse_base_db:.3f}  k{args.k_extra}={nmse_kK_db:.3f}")
    print(f"    delta = {ber_kK - ber_base:+.3e}")

    print("\n[summary]")
    print(f"  Check 2 superset: {'PASS' if superset_ok else 'FAIL'}")
    print(f"  Check 3 bit-exact k0 vs baseline: "
          f"{'PASS' if bit_exact else 'FAIL'}")
    print(f"  Check 4 mechanism: K-extras above; UNRELATED count = "
          f"{sum(1 for i in extras if not any(lp == decode_lk(i, sys_obj.k_max_cap, K)[0] and abs(kp - decode_lk(i, sys_obj.k_max_cap, K)[1]) <= 2 for lp, kp, _ in phys_pairs))}/{len(extras)}")


if __name__ == '__main__':
    main()
