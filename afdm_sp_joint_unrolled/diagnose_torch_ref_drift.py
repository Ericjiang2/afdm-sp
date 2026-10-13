"""
diagnose_torch_ref_drift.py — find where NumPy classical and torch-ref diverge.

Reproduces the first ~50 frames of the canonical paired_learned_eval setup at
SNR=25 (seed 20260419, P=8, v=2, N=1024, fs=4B, mp_mode=bp, --use-hard) and
records per-frame:
  - bit error count for NumPy classical
  - bit error count for torch-ref (ClassicalJointUnrolled, heads=(), hard)
  - max |x_c - x_tref|
  - max |H_c - H_tref|

This identifies the first divergent frame; subsequent drill-down into
classical_joint_unrolled.py vs joint_omp_mp_iterative iteration dynamics
should target that frame's seed.

Run on deinlab (needs torch):
    conda activate AFDM
    python afdm_sp_joint_unrolled/diagnose_torch_ref_drift.py --max-frames 50
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
REPO_DIR = HERE.parent
sys.path.insert(0, str(REPO_DIR))

from afdm_sp_joint_unrolled import afdm_baselines as _afb  # noqa: E402
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch  # noqa: E402


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
             damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(
        y, H, sigma2, constellation, n_iter=n_iter, threshold=threshold,
        damp=damp, device=dev, return_numpy=True, return_soft=return_soft)


# Monkey-patch: torch BP path (matches paired_learned_eval)
_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative  # noqa: E402
from afdm_sp_joint_unrolled.classical_joint_unrolled import (  # noqa: E402
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (  # noqa: E402
    _make_system_variable_N, QPSK, _bits_of_symbol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snr', type=int, default=25)
    ap.add_argument('--seed', type=int, default=20260419)
    ap.add_argument('--max-frames', type=int, default=50)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--mp-mode', choices=['pic', 'bp'], default='bp')
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--cdtype', choices=['complex128', 'complex64'],
                    default='complex64')
    ap.add_argument('--out', type=pathlib.Path,
                    default=HERE / 'outputs_diag_drift' / 'frame_diffs.json')
    args = ap.parse_args()

    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
    rdtype = torch.float32 if args.cdtype == 'complex64' else torch.float64

    # Mirror paired_learned_eval sys_obj setup exactly
    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(args.v_mean)
    if abs(args.fs_factor - 2.0) > 1e-9:
        sys_obj.B = 4e3
        sys_obj.fs = float(args.fs_factor) * sys_obj.B
        sys_obj.Ts = 1.0 / sys_obj.fs
    v_max = sys_obj.v_mean + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()

    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    # ClassicalJointUnrolled mirroring paired_learned_eval module_ref.
    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=rho,
        mp_mode=args.mp_mode, pic_damp=args.pic_damp,
        n_paths=int(sys_obj.P_paths),
        n_outer_iter=5, pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype,
        device=('cuda' if torch.cuda.is_available() else 'cpu'),
    )
    module_ref = ClassicalJointUnrolled(
        cfg, learnable_heads=(), use_soft_decisions=False)
    module_ref = module_ref.to(cfg.device).eval()

    const_t = torch.tensor(const_data, dtype=cdtype, device=cfg.device)
    x_pil_t = torch.tensor(pilot_scaled, dtype=cdtype, device=cfg.device)

    snr = args.snr
    sigma2 = 1.0 / (10.0 ** (snr / 10.0))
    rng_master = np.random.default_rng(args.seed)
    diff_records = []
    diverged_first_at = None
    t0 = time.time()

    for fi in range(args.max_frames):
        seed_fi = int(rng_master.integers(0, 2**31))
        np.random.seed(seed_fi)
        rng = np.random.default_rng(seed_fi)
        H_true, _, _ = sys_obj.generate_channel_matrix()
        sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
        data_idx = rng.integers(0, 4, size=args.n_total)
        data_qam = QPSK[data_idx]
        bits_true = np.concatenate([
            (data_qam.real < 0).astype(np.float32),
            (data_qam.imag < 0).astype(np.float32),
        ])
        x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
        y = H_true @ x_sp
        noise = (rng.standard_normal(args.n_total)
                 + 1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
        y_daft = y + np.sqrt(sigma2) * noise

        x_c, H_c = joint_omp_mp_iterative(
            y_daft, pilot_scaled, args.n_total, sys_obj.c1, sys_obj.c2,
            sys_obj.l_max_cap, sys_obj.k_max_cap,
            sigma2, const_data, n_paths=sparsity, n_outer_iter=5, rho=rho,
            pic_iter=20, pic_damp=args.pic_damp, mp_mode=args.mp_mode,
            gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
            tau_h_factor=0.01, tau_h_sigma_factor=0.1, threshold_mp=1e-4,
            k_leak=2, update_sigma2=True, phase_convention='python',
            eps_stop_rel=-1.0)
        b_c = _bits_of_symbol(x_c / np.sqrt(P_d), args.n_total)
        ec = int((b_c != bits_true).sum())
        nc = ((np.abs(H_c - H_true) ** 2).sum()
              / (np.abs(H_true) ** 2).sum())

        y_t = torch.tensor(y_daft, dtype=cdtype, device=cfg.device)
        sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=cfg.device)
        module_ref.cfg.n_paths = sparsity
        with torch.no_grad():
            out_tref = module_ref(y_t, x_pil_t, sigma2_t, const_t)
        x_tref = out_tref['x_soft'].cpu().numpy()
        H_tref = out_tref['H_est'].cpu().numpy()
        b_tref = _bits_of_symbol(x_tref / np.sqrt(P_d), args.n_total)
        etref = int((b_tref != bits_true).sum())
        ntref = ((np.abs(H_tref - H_true) ** 2).sum()
                 / (np.abs(H_true) ** 2).sum())

        diff_x = float(np.max(np.abs(x_c - x_tref)))
        diff_H = float(np.max(np.abs(H_c - H_tref)))
        bit_diff = int((b_c != b_tref).sum())

        rec = dict(
            fi=fi, seed_fi=int(seed_fi),
            errs_classical=ec, errs_torch_ref=etref,
            nmse_c_db=float(10*np.log10(nc + 1e-30)) if nc > 0 else None,
            nmse_tref_db=float(10*np.log10(ntref + 1e-30)) if ntref > 0 else None,
            diff_x_max=diff_x, diff_H_max=diff_H,
            bit_diff=bit_diff,
        )
        diff_records.append(rec)

        if (diff_x > 1e-6 or diff_H > 1e-6) and diverged_first_at is None:
            diverged_first_at = fi
        marker = ''
        if bit_diff > 0:
            marker = ' *** BITS DIFFER ***'
        if (diff_x > 1e-6 or diff_H > 1e-6) and bit_diff == 0:
            marker = ' (numerics drift, no bit flip)'
        if fi % 5 == 0 or marker:
            print(f"  fi={fi:3d}  cls={ec:3d}  tref={etref:3d}  "
                  f"|Δx|={diff_x:.3e}  |ΔH|={diff_H:.3e}  "
                  f"bit_diff={bit_diff}{marker}  [{time.time()-t0:.0f}s]",
                  flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        'config': dict(snr=snr, seed=args.seed, max_frames=args.max_frames,
                        n_total=args.n_total, v_mean=args.v_mean,
                        p_paths=args.p_paths, tau_spread=args.tau_spread,
                        fs_factor=args.fs_factor, mp_mode=args.mp_mode,
                        pic_damp=args.pic_damp, cdtype=args.cdtype),
        'diverged_first_at': diverged_first_at,
        'frames': diff_records,
    }, indent=2))
    print()
    print(f"Wrote {args.out}")
    n_div = sum(1 for r in diff_records
                if r['diff_x_max'] > 1e-6 or r['diff_H_max'] > 1e-6)
    n_bit_div = sum(1 for r in diff_records if r['bit_diff'] > 0)
    print(f"Frames with numerics drift: {n_div}/{len(diff_records)}")
    print(f"Frames where bits differ:    {n_bit_div}/{len(diff_records)}")
    if diverged_first_at is not None:
        first = diff_records[diverged_first_at]
        print(f"First divergent frame: fi={diverged_first_at}, "
              f"seed_fi={first['seed_fi']}, |Δx|={first['diff_x_max']:.3e}, "
              f"|ΔH|={first['diff_H_max']:.3e}, "
              f"bit_diff={first['bit_diff']}")


if __name__ == '__main__':
    main()
