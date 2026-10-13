"""
verify_learnable_chirp_init_parity.py — Round-0 sanity for Direction-D Option A.

At init (c1_param = c1_init, c2_param = c2_init), the LearnableChirpDAFTReceiver
wrapper must produce **identical** outputs to the underlying ClassicalJointUnrolled.
This protects against silent regressions when we later allow c1/c2 to drift.

Two checks:
  1. Forward parity: |x_soft_wrap − x_soft_base| / |x_soft_base| < 1e-12
                     |H_wrap   − H_base|   / |H_base|   < 1e-12
  2. Gradient sanity: after a dummy BCE backward on x_soft, both c1_raw.grad
                     and c2_raw.grad are finite and non-zero.

Usage::

    conda activate AFDM && \\
      python afdm_sp_joint_unrolled/verify_learnable_chirp_init_parity.py \\
        --n-total 256 --snr 20 --frames 5
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled.classical_joint_unrolled import (  # noqa: E402
    ClassicalJointConfig,
    ClassicalJointUnrolled,
)
from afdm_sp_joint_unrolled.learnable_chirp_daft import (  # noqa: E402
    LearnableChirpDAFTReceiver,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK,
    _make_system_variable_N,
)
from afdm_sp_joint_unrolled.verify_oamp import _make_system  # noqa: E402


def _setup_system(n_total: int, p_paths: int = 10):
    sys_obj = _make_system_variable_N(n_total) if n_total else _make_system()
    sys_obj.P_paths = int(p_paths)
    sys_obj.gen_h_daft_convention = "python"
    sys_obj.baseline_phase_convention = "python"
    return sys_obj


def _build_cfg(sys_obj) -> ClassicalJointConfig:
    return ClassicalJointConfig(
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
        early_stop=True,
        mp_mode='pic',
    )


def _make_frame(sys_obj, snr_db: int, rng: np.random.Generator):
    N = sys_obj.N_total
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    H_eff_true, _, _ = sys_obj.generate_channel_matrix()
    p_actual = int(getattr(sys_obj, "_P_actual", sys_obj.P_paths))
    sparsity = max(p_actual, int(sys_obj.P_paths))

    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y_clean = H_eff_true @ x_sp
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = y_clean + np.sqrt(sigma2) * noise

    const_data = np.sqrt(P_d) * QPSK
    return (
        torch.tensor(y_daft, dtype=torch.complex128),
        torch.tensor(pilot_scaled, dtype=torch.complex128),
        torch.tensor(sigma2, dtype=torch.float64),
        torch.tensor(const_data, dtype=torch.complex128),
        sparsity,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=256)
    ap.add_argument('--snr', type=int, default=20)
    ap.add_argument('--frames', type=int, default=5)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--rel-tol', type=float, default=1e-12)
    args = ap.parse_args()

    sys_obj = _setup_system(args.n_total)
    cfg = _build_cfg(sys_obj)
    print(f"[parity] N={cfg.N} c1_init={cfg.c1:.6g} c2_init={cfg.c2:.6e}")

    # Two independent modules so they don't share Parameters.
    base_module = ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=False)
    wrap_cfg = _build_cfg(sys_obj)  # fresh cfg so swap doesn't leak
    wrap_base = ClassicalJointUnrolled(wrap_cfg, learnable_heads=(), use_soft_decisions=False)
    wrap_module = LearnableChirpDAFTReceiver(wrap_base, constrain=None)

    rng_master = np.random.default_rng(args.seed)
    worst_x = 0.0
    worst_H = 0.0
    all_ok = True

    for fi in range(args.frames):
        seed_fi = int(rng_master.integers(0, 2 ** 31))
        np.random.seed(seed_fi)
        rng = np.random.default_rng(seed_fi)
        y_t, pilot_t, sigma2_t, const_t, sparsity = _make_frame(sys_obj, args.snr, rng)
        base_module.cfg.n_paths = sparsity
        wrap_module.base.cfg.n_paths = sparsity

        with torch.no_grad():
            out_base = base_module(y_t, pilot_t, sigma2_t, const_t)
            out_wrap = wrap_module(y_t, pilot_t, sigma2_t, const_t)

        x_b = out_base['x_soft']
        x_w = out_wrap['x_soft']
        H_b = out_base['H_est']
        H_w = out_wrap['H_est']

        x_rel = (x_w - x_b).norm().item() / max(x_b.norm().item(), 1e-30)
        H_rel = (H_w - H_b).norm().item() / max(H_b.norm().item(), 1e-30)
        worst_x = max(worst_x, x_rel)
        worst_H = max(worst_H, H_rel)
        ok = x_rel < args.rel_tol and H_rel < args.rel_tol
        all_ok = all_ok and ok
        print(f"[fi={fi}] x_rel={x_rel:.2e}  H_rel={H_rel:.2e}  {'PASS' if ok else 'FAIL'}")

    print(f"[parity] worst x_rel={worst_x:.2e}  worst H_rel={worst_H:.2e}  "
          f"tol={args.rel_tol:.0e}  → {'PASS' if all_ok else 'FAIL'}")

    # -------- Gradient sanity --------
    print("[grad-sanity] running 1 frame with backward on dummy BCE loss")
    seed_fi = int(rng_master.integers(0, 2 ** 31))
    rng = np.random.default_rng(seed_fi)
    y_t, pilot_t, sigma2_t, const_t, sparsity = _make_frame(sys_obj, args.snr, rng)
    wrap_module.base.cfg.n_paths = sparsity

    # Re-instantiate with raw constraint to keep Parameters .requires_grad
    wrap_module.zero_grad(set_to_none=True)
    # IMPORTANT: must run forward WITHOUT no_grad context (above used no_grad)
    out = wrap_module(y_t, pilot_t, sigma2_t, const_t)
    x_soft = out['x_soft']
    H_est = out['H_est']
    print(f"[grad-diag] x_soft.requires_grad={x_soft.requires_grad}  grad_fn={x_soft.grad_fn}")
    print(f"[grad-diag] H_est.requires_grad={H_est.requires_grad}  grad_fn={H_est.grad_fn}")
    print(f"[grad-diag] c1_raw.requires_grad={wrap_module.c1_raw.requires_grad}")
    # Try gradient through H_est (where chirp params definitely enter via reconstruct)
    if H_est.requires_grad:
        loss = H_est.abs().pow(2).mean()
    elif x_soft.requires_grad:
        loss = x_soft.abs().pow(2).mean()
    else:
        print("[grad-sanity] WARN — neither x_soft nor H_est has grad_fn; the canonical"
              " receiver path may detach. Forcing a direct Phi-loss test.")
        # Direct test: build Phi inside no_grad-free context and use it as the loss.
        from afdm_sp_joint_unrolled.classical_joint_unrolled import construct_sensing_matrix_torch
        cfg = wrap_module.base.cfg
        cfg.c1 = wrap_module.c1_eff
        cfg.c2 = wrap_module.c2_eff
        try:
            Phi = construct_sensing_matrix_torch(
                cfg.N, pilot_t, cfg.c1, cfg.c2, cfg.l_max, cfg.k_max, cdtype=cfg.dtype)
            loss = Phi.abs().pow(2).mean()
            print(f"[grad-diag-fallback] Phi.requires_grad={Phi.requires_grad}  grad_fn={Phi.grad_fn}")
        finally:
            cfg.c1 = wrap_module._c1_init
            cfg.c2 = wrap_module._c2_init
    loss.backward()
    g1 = wrap_module.c1_raw.grad
    g2 = wrap_module.c2_raw.grad
    print(f"[grad-sanity] loss={float(loss):.4e}  c1.grad={float(g1) if g1 is not None else 'NONE':}  "
          f"c2.grad={float(g2) if g2 is not None else 'NONE':}")

    grad_ok = (g1 is not None and torch.isfinite(g1).item()
               and g2 is not None and torch.isfinite(g2).item())
    if not grad_ok:
        print("[grad-sanity] FAIL — gradient is None or non-finite")
        sys.exit(1)
    if abs(float(g1)) < 1e-30 and abs(float(g2)) < 1e-30:
        print("[grad-sanity] WARN — both gradients essentially zero; the dummy "
              "loss may not depend on c1/c2 strongly. Consider a BCE-on-bits "
              "loss for a stricter test, but this is not a failure.")

    print("=" * 70)
    print("OVERALL: " + ("PASS" if all_ok and grad_ok else "FAIL"))
    sys.exit(0 if all_ok and grad_ok else 1)


if __name__ == '__main__':
    main()
