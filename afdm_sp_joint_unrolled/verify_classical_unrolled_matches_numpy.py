"""
verify_classical_unrolled_matches_numpy.py

Identity-check harness for ``ClassicalJointUnrolled``.  On N=512 frames at
three SNRs with the same channel / pilot / noise realisation, runs both the
NumPy baseline (``afdm_baselines.joint_omp_mp_iterative``) and the torch
unrolling (``ClassicalJointUnrolled`` with ``use_soft_decisions=False`` and no
learnable heads) and asserts:

  - ``|BER_torch − BER_numpy| < 1e-4``  for each SNR
  - ``‖x_soft_torch − x_soft_numpy‖ / ‖x_soft_numpy‖ < 1e-5``  per frame
  - ``‖H_torch − H_numpy‖_F / ‖H_numpy‖_F < 1e-5``  per frame

Usage::

    conda activate AFDM && \\
      python afdm_sp_joint_unrolled/verify_classical_unrolled_matches_numpy.py \\
        --n-total 512 --snr-list 15 20 25 --frames 30
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix,
    joint_omp_mp_iterative,
)
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig,
    ClassicalJointUnrolled,
    construct_sensing_matrix_torch,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (
    QPSK,
    _bits_of_symbol,
    _ber,
    _nmse,
    _make_system_variable_N,
)
from afdm_sp_joint_unrolled.verify_oamp import _make_system


def _setup_system(n_total: int, p_paths: int = 10):
    sys_obj = _make_system_variable_N(n_total) if n_total else _make_system()
    sys_obj.P_paths = int(p_paths)
    sys_obj.gen_h_daft_convention = "python"
    sys_obj.baseline_phase_convention = "python"
    return sys_obj


def _one_frame(sys_obj, snr_db: int, rng: np.random.Generator,
               torch_module: ClassicalJointUnrolled,
               mp_mode: str = 'pic'):
    """Run one paired frame and return deviation metrics."""
    N = sys_obj.N_total
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK

    pilot_base = sys_obj._zc_seq
    pilot_scaled = np.sqrt(rho) * pilot_base

    # Same channel for both paths.
    H_eff_true, _, _ = sys_obj.generate_channel_matrix()
    p_actual = int(getattr(sys_obj, "_P_actual", sys_obj.P_paths))
    sparsity = max(p_actual, int(sys_obj.P_paths))

    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    bits_true = np.zeros(2 * N, dtype=np.float32)
    bits_true[:N] = (data_qam.real < 0).astype(np.float32)
    bits_true[N:] = (data_qam.imag < 0).astype(np.float32)

    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y_clean = H_eff_true @ x_sp
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = y_clean + np.sqrt(sigma2) * noise

    # ---- NumPy baseline --------------------------------------------------
    x_soft_np, H_np = joint_omp_mp_iterative(
        y_daft, pilot_scaled, N,
        sys_obj.c1, sys_obj.c2,
        sys_obj.l_max_cap, sys_obj.k_max_cap,
        sigma2, const_data,
        n_paths=sparsity,
        n_outer_iter=5,
        rho=rho,
        pic_iter=20,
        pic_damp=0.5,
        mp_mode=mp_mode,
        gamma_h=0.7, gamma_x=0.6,
        lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1,
        k_leak=2, eps_stop_rel=1e-3,
        update_sigma2=True,
        phase_convention='python',
    )
    # NumPy returns x_soft at data scale (√P_d·QPSK).  Normalise to |QPSK| to
    # BER-demod.
    x_np_norm = x_soft_np / np.sqrt(P_d)
    ber_np = _ber(_bits_of_symbol(x_np_norm, N), bits_true)

    # ---- Torch port (identity mode) -------------------------------------
    y_t = torch.tensor(y_daft, dtype=torch.complex128)
    pilot_t = torch.tensor(pilot_scaled, dtype=torch.complex128)
    const_t = torch.tensor(const_data, dtype=torch.complex128)
    sigma2_t = torch.tensor(sigma2, dtype=torch.float64)

    # Update n_paths in cfg to match this frame's sparsity.
    torch_module.cfg.n_paths = sparsity

    with torch.no_grad():
        out = torch_module(y_t, pilot_t, sigma2_t, const_t)
    x_torch = out['x_soft'].cpu().numpy()
    H_torch = out['H_est'].cpu().numpy()

    x_torch_norm = x_torch / np.sqrt(P_d)
    ber_t = _ber(_bits_of_symbol(x_torch_norm, N), bits_true)

    # Deviations
    x_rel_err = np.linalg.norm(x_torch - x_soft_np) / max(np.linalg.norm(x_soft_np), 1e-30)
    H_rel_err = np.linalg.norm(H_torch - H_np, 'fro') / max(np.linalg.norm(H_np, 'fro'), 1e-30)
    return dict(
        ber_np=ber_np, ber_t=ber_t, ber_diff=abs(ber_t - ber_np),
        x_rel_err=float(x_rel_err), H_rel_err=float(H_rel_err),
        p_actual=p_actual,
        nmse_np=_nmse(H_np, H_eff_true),
        nmse_t=_nmse(H_torch, H_eff_true),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=512)
    ap.add_argument('--p-paths', type=int, default=10)
    ap.add_argument('--mp-mode', type=str, default='pic', choices=('pic', 'bp'))
    ap.add_argument('--snr-list', nargs='+', type=int, default=[15, 20, 25])
    ap.add_argument('--frames', type=int, default=30)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--ber-tol', type=float, default=1e-4)
    ap.add_argument('--rel-tol', type=float, default=1e-5)
    ap.add_argument('--with-heads', action='store_true',
                    help='Enable all learnable heads at zero-init and confirm '
                         'the untrained model still matches NumPy bit-exactly.')
    args = ap.parse_args()

    sys_obj = _setup_system(args.n_total, p_paths=args.p_paths)
    print(f"[verify] N={sys_obj.N_total} l_max={sys_obj.l_max_cap} "
          f"k_max={sys_obj.k_max_cap} c1={sys_obj.c1:.6g} c2={sys_obj.c2:.3e}")

    cfg = ClassicalJointConfig(
        N=int(sys_obj.N_total),
        l_max=int(sys_obj.l_max_cap),
        k_max=int(sys_obj.k_max_cap),
        c1=float(sys_obj.c1),
        c2=float(sys_obj.c2),
        n_outer_iter=5,
        pic_iter=20,
        rho=float(sys_obj.rho),
        n_paths=int(sys_obj.P_paths),
        dtype=torch.complex128,
        rdtype=torch.float64,
        early_stop=True,   # match NumPy semantics
        mp_mode=args.mp_mode,
    )
    heads = ('scalars', 'strategy', 'symbol_refiner') if args.with_heads else ()
    module = ClassicalJointUnrolled(cfg, learnable_heads=heads,
                                    use_soft_decisions=False)
    # Keep MLP/CNN params in float32 (standard).  The main complex-pipeline
    # tensors are explicitly cast to complex128 / float64 inside forward().
    if args.with_heads:
        print(f"[verify] identity-with-heads: all {len(heads)} heads enabled at "
              f"zero-init; output must still match NumPy bit-exactly.")

    rng_master = np.random.default_rng(args.seed)
    all_ok = True
    t0 = time.time()
    for snr in args.snr_list:
        worst_x = 0.0
        worst_H = 0.0
        worst_ber = 0.0
        ber_np_list, ber_t_list = [], []
        nmse_np_list, nmse_t_list = [], []
        for fi in range(args.frames):
            seed_fi = int(rng_master.integers(0, 2 ** 31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            r = _one_frame(sys_obj, snr, rng, module, mp_mode=args.mp_mode)
            ber_np_list.append(r['ber_np'])
            ber_t_list.append(r['ber_t'])
            nmse_np_list.append(r['nmse_np'])
            nmse_t_list.append(r['nmse_t'])
            worst_x = max(worst_x, r['x_rel_err'])
            worst_H = max(worst_H, r['H_rel_err'])
            worst_ber = max(worst_ber, r['ber_diff'])
            elapsed = time.time() - t0
            print(f"[snr={snr:2d} fi={fi:3d}] ber_np={r['ber_np']:.4e} "
                  f"ber_t={r['ber_t']:.4e} Δ={r['ber_diff']:.2e} "
                  f"x_rel={r['x_rel_err']:.2e} H_rel={r['H_rel_err']:.2e} "
                  f"Pact={r['p_actual']} [{elapsed:.0f}s]", flush=True)

        ber_np_mean = float(np.mean(ber_np_list))
        ber_t_mean = float(np.mean(ber_t_list))
        nmse_np_mean = 10 * np.log10(np.mean(nmse_np_list) + 1e-30)
        nmse_t_mean = 10 * np.log10(np.mean(nmse_t_list) + 1e-30)
        ok = (worst_x < args.rel_tol
              and worst_H < args.rel_tol
              and worst_ber < args.ber_tol)
        tag = "PASS" if ok else "FAIL"
        print(f"[SUMMARY snr={snr}] {tag}  "
              f"ber_np={ber_np_mean:.4e} ber_t={ber_t_mean:.4e}  "
              f"nmse_np={nmse_np_mean:+.2f}dB nmse_t={nmse_t_mean:+.2f}dB  "
              f"worst x_rel={worst_x:.2e} H_rel={worst_H:.2e} "
              f"BER_Δ={worst_ber:.2e}")
        all_ok = all_ok and ok

    print("=" * 70)
    print("OVERALL: " + ("PASS" if all_ok else "FAIL"))
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
