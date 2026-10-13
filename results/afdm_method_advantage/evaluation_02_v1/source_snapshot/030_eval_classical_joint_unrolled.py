"""
eval_classical_joint_unrolled.py

NOTE (audit 2026-04-24): this is a general SNR-sweep smoke test, NOT the thesis
headline eval. The §3 Table 3 / headline BER numbers come from
paired_learned_eval.py with --refine-rounds 2 --cand-topm 96
--defer-prune-until-final --protect-added 2 (the F2-P refresh-pool deployment).
See REPRODUCTION.md for the per-row script → CLI → JSON mapping.

SNR-sweep comparator.  On identical channels, runs up to five receivers and
reports BER + NMSE:

  (1) Perfect-CSI MMSE      — theoretical lower bound
  (2) LS + MMSE             — baseline channel estimator
  (3) OMP + MMSE            — sparse channel estimator
  (4) Classical joint (NumPy, T=5)                          — serial teacher
  (5) Classical-joint-unrolled (torch, fixed hparams)        — identity check
  (6) Classical-joint-unrolled + learned heads (checkpoint)  — learned student

Optionally also:
  (7) CurrentJoint (afdm_joint_unrolled.JointSparseUnrolledReceiver)

Writes:
  results.json  — per-SNR per-method BER / NMSE means + stds
  results.md    — markdown table
  figures/ber_curve.png     (optional, if matplotlib available)
  figures/nmse_curve.png
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Dict, List

import numpy as np
import torch

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# Fast torch BP: monkey-patch the numpy reference with the vectorized torch
# port so `mp_mode='bp'` doesn't fall back to slow Python loops.  Must happen
# BEFORE importing joint_omp_mp_iterative.
from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch as _bp_torch


def _fast_bp_numpy_shim(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
                        damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return _bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                     threshold=threshold, damp=damp,
                     device=dev, return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp_numpy_shim

from afdm_sp_joint_unrolled.afdm_baselines import (
    joint_omp_mp_iterative,
    construct_sensing_matrix,
    omp_sparse,
    reconstruct_H_from_omp,
)
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig,
    ClassicalJointUnrolled,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (
    QPSK,
    _bits_of_symbol,
    _ber,
    _nmse,
    _ls_channel_estimate,
    _mmse_equalize,
    _make_system_variable_N,
)


METHODS = [
    'perfect_csi_mmse',
    'ls_mmse',
    'omp_mmse',
    'classical_joint_numpy',
    'classical_joint_unrolled_identity',
    'classical_joint_unrolled_learned',
]


def _eval_one_frame(sys_obj, snr_db: int, rng: np.random.Generator,
                    module_identity: 'ClassicalJointUnrolled',
                    module_learned: 'ClassicalJointUnrolled' = None,
                    device='cpu',
                    mp_mode: str = 'pic', pic_damp: float = 0.5
                    ) -> Dict[str, Dict[str, float]]:
    N = sys_obj.N_total
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK

    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    H_true, _, _ = sys_obj.generate_channel_matrix()
    p_actual = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
    sparsity = max(p_actual, int(sys_obj.P_paths))

    data_idx = rng.integers(0, 4, size=N)
    data_qam = QPSK[data_idx]
    bits_true = np.zeros(2 * N, dtype=np.float32)
    bits_true[:N] = (data_qam.real < 0).astype(np.float32)
    bits_true[N:] = (data_qam.imag < 0).astype(np.float32)

    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y_clean = H_true @ x_sp
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    y_daft = y_clean + np.sqrt(sigma2) * noise

    out: Dict[str, Dict[str, float]] = {}

    # (1) Perfect CSI MMSE
    y_pcsi = y_daft - H_true @ pilot_scaled
    x_pcsi = _mmse_equalize(H_true, y_pcsi, sigma2, P_d) / np.sqrt(P_d)
    out['perfect_csi_mmse'] = dict(ber=_ber(_bits_of_symbol(x_pcsi, N), bits_true),
                                    nmse=float('nan'))

    # (2) LS + MMSE
    Phi = construct_sensing_matrix(N, pilot_scaled, sys_obj.c1, sys_obj.c2,
                                   sys_obj.l_max_cap, sys_obj.k_max_cap)
    lam = 1e-2 * (sigma2 + P_d) * N
    h_ls = _ls_channel_estimate(y_daft, Phi, lam)
    H_ls = reconstruct_H_from_omp(N, h_ls, sys_obj.k_max_cap, sys_obj.l_max_cap,
                                  sys_obj.c1, sys_obj.c2, threshold=0.0)
    y_ls = y_daft - H_ls @ pilot_scaled
    x_ls = _mmse_equalize(H_ls, y_ls, sigma2, P_d) / np.sqrt(P_d)
    out['ls_mmse'] = dict(ber=_ber(_bits_of_symbol(x_ls, N), bits_true),
                          nmse=_nmse(H_ls, H_true))

    # (3) OMP + MMSE
    h_omp, _ = omp_sparse(y_daft, Phi, sparsity)
    H_omp = reconstruct_H_from_omp(N, h_omp, sys_obj.k_max_cap, sys_obj.l_max_cap,
                                   sys_obj.c1, sys_obj.c2, threshold=0.0)
    y_omp = y_daft - H_omp @ pilot_scaled
    x_omp = _mmse_equalize(H_omp, y_omp, sigma2, P_d) / np.sqrt(P_d)
    out['omp_mmse'] = dict(ber=_ber(_bits_of_symbol(x_omp, N), bits_true),
                           nmse=_nmse(H_omp, H_true))

    # (4) Classical joint (NumPy; BP path uses torch BP via monkey-patch)
    x_joint, H_joint = joint_omp_mp_iterative(
        y_daft, pilot_scaled, N, sys_obj.c1, sys_obj.c2,
        sys_obj.l_max_cap, sys_obj.k_max_cap,
        sigma2, const_data, n_paths=sparsity, n_outer_iter=5,
        rho=rho, pic_iter=20, pic_damp=float(pic_damp), mp_mode=str(mp_mode),
        gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1,
        k_leak=2, update_sigma2=True, phase_convention='python',
    )
    x_joint_n = x_joint / np.sqrt(P_d)
    out['classical_joint_numpy'] = dict(ber=_ber(_bits_of_symbol(x_joint_n, N), bits_true),
                                        nmse=_nmse(H_joint, H_true))

    # (5) Classical-joint-unrolled identity (no heads, hard decisions)
    cdtype = module_identity.cfg.dtype
    rdtype = module_identity.cfg.rdtype
    y_t = torch.tensor(y_daft, dtype=cdtype, device=device)
    pilot_t = torch.tensor(pilot_scaled, dtype=cdtype, device=device)
    const_t = torch.tensor(const_data, dtype=cdtype, device=device)
    sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=device)
    module_identity.cfg.n_paths = sparsity
    with torch.no_grad():
        mid_out = module_identity(y_t, pilot_t, sigma2_t, const_t)
    x_id = mid_out['x_soft'].cpu().numpy() / np.sqrt(P_d)
    out['classical_joint_unrolled_identity'] = dict(
        ber=_ber(_bits_of_symbol(x_id, N), bits_true),
        nmse=_nmse(mid_out['H_est'].cpu().numpy(), H_true))

    # (6) Classical-joint-unrolled learned (soft decisions + heads)
    if module_learned is not None:
        module_learned.cfg.n_paths = sparsity
        with torch.no_grad():
            ml_out = module_learned(y_t, pilot_t, sigma2_t, const_t)
        x_l = ml_out['x_soft'].cpu().numpy() / np.sqrt(P_d)
        out['classical_joint_unrolled_learned'] = dict(
            ber=_ber(_bits_of_symbol(x_l, N), bits_true),
            nmse=_nmse(ml_out['H_est'].cpu().numpy(), H_true))

    return out


_VARIANT_HEADS = {
    'A':     ('scalars', 'strategy', 'symbol_refiner'),
    'B1':    ('per_iter_refiner',),
    'B2':    ('iter_residual_selector',),
    'B1B2':  ('per_iter_refiner', 'iter_residual_selector'),
    'C1':    ('off_support_corr',),
    'C2-rel': ('cand_active_rel',),
    'all':   ('scalars', 'strategy', 'symbol_refiner',
              'per_iter_refiner', 'iter_residual_selector'),
}


def _load_module(cfg: 'ClassicalJointConfig', ckpt_path: str = None,
                  variant: str = 'B1B2') -> 'ClassicalJointUnrolled':
    heads = _VARIANT_HEADS.get(variant, ()) if ckpt_path else ()
    module = ClassicalJointUnrolled(
        cfg, learnable_heads=heads,
        use_soft_decisions=(ckpt_path is not None),
    )
    if ckpt_path:
        state = torch.load(ckpt_path, map_location='cpu')
        # Tolerate extra/missing keys (e.g. old checkpoints) with strict=False.
        missing, unexpected = module.load_state_dict(state['state_dict'], strict=False)
        if missing or unexpected:
            print(f"[eval] NOTE: state_dict missing={len(missing)} unexpected={len(unexpected)}")
        print(f"[eval] loaded learned checkpoint from {ckpt_path} (variant={variant})")
    module.eval()
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=256)
    ap.add_argument('--v-mean', type=float, default=None,
                    help='Override UWA v_mean (m/s) to pick kappa-clean setup.')
    ap.add_argument('--device', type=str, default='auto',
                    choices=['auto', 'cpu', 'cuda'])
    ap.add_argument('--cdtype', type=str, default='complex128',
                    choices=['complex128', 'complex64'])
    ap.add_argument('--variant', type=str, default='B1B2',
                    choices=list(_VARIANT_HEADS.keys()),
                    help='Variant used when training the ckpt.')
    ap.add_argument('--snr-list', nargs='+', type=int,
                    default=[0, 5, 10, 15, 20, 25, 30])
    ap.add_argument('--frames-per-snr', type=int, default=100)
    ap.add_argument('--ckpt', type=str, default=None,
                    help='Optional path to learned checkpoint.  If omitted, '
                         'only identity + NumPy baselines are reported.')
    ap.add_argument('--seed', type=int, default=9999)
    ap.add_argument('--mp-mode', type=str, default='pic', choices=['pic', 'bp'])
    ap.add_argument('--pic-damp', type=float, default=0.5,
                    help='MP damping; applies to both PIC and BP paths.')
    ap.add_argument('--p-paths', type=int, default=10,
                    help='UWA physical multipath count (set 5 to match MATLAB).')
    ap.add_argument('--tau-spread', type=float, default=None,
                    help='Override channel tau_spread (s). Default 10e-3.')
    ap.add_argument('--out-dir', type=str,
                    default=str(HERE / 'outputs_classical_joint_unrolled_eval'))
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    if args.tau_spread is not None:
        sys_obj.tau_spread = float(args.tau_spread)
        print(f"[eval] tau_spread override → {sys_obj.tau_spread*1e3:.2f} ms")
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    if args.v_mean is not None:
        sys_obj.v_mean = float(args.v_mean)
        v_max_ms = float(sys_obj.v_mean) + 3.0 * float(getattr(sys_obj, 'v_std', 0.5))
        d_max_norm = v_max_ms * float(sys_obj.fc) / (
            float(sys_obj.c_sound) * float(sys_obj.fs))
        sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_max_norm)), 1)
        K = 2 * sys_obj.k_max_cap + 1
        sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
        sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
        sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
        print(f"[eval] v_mean override → v={sys_obj.v_mean:.1f} m/s  "
              f"k_max_cap={sys_obj.k_max_cap}")

    if args.cdtype == 'complex64':
        cdtype = torch.complex64; rdtype = torch.float32
    else:
        cdtype = torch.complex128; rdtype = torch.float64
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    cfg = ClassicalJointConfig(
        N=int(sys_obj.N_total), l_max=int(sys_obj.l_max_cap),
        k_max=int(sys_obj.k_max_cap),
        c1=float(sys_obj.c1), c2=float(sys_obj.c2),
        n_outer_iter=5, pic_iter=20, rho=float(sys_obj.rho),
        pic_damp=float(args.pic_damp), mp_mode=str(args.mp_mode),
        n_paths=int(sys_obj.P_paths),
        dtype=cdtype, rdtype=rdtype,
        early_stop=True,   # match NumPy for identity check
    )
    module_identity = _load_module(cfg, None).to(device)
    module_learned = (_load_module(cfg, args.ckpt, variant=args.variant).to(device)
                      if args.ckpt else None)
    print(f"[eval] device={device} cdtype={cdtype}")

    rng_master = np.random.default_rng(args.seed)
    agg: Dict[int, Dict[str, Dict[str, List[float]]]] = {}
    t0 = time.time()

    for snr in args.snr_list:
        agg[int(snr)] = {m: dict(ber=[], nmse=[]) for m in METHODS}
        for fi in range(args.frames_per_snr):
            seed_fi = int(rng_master.integers(0, 2 ** 31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            r = _eval_one_frame(sys_obj, int(snr), rng,
                                module_identity, module_learned, device=device,
                                mp_mode=args.mp_mode, pic_damp=args.pic_damp)
            for m in METHODS:
                if m in r:
                    agg[int(snr)][m]['ber'].append(r[m]['ber'])
                    agg[int(snr)][m]['nmse'].append(r[m]['nmse'])
            if fi % 10 == 0:
                elapsed = time.time() - t0
                have = {k: r[k]['ber'] for k in r}
                print(f"[snr={snr:2d} fi={fi:3d}] " +
                      "  ".join(f"{k}={v:.3e}" for k, v in have.items()) +
                      f"  [{elapsed:.0f}s]", flush=True)

    # Aggregate to mean/std
    summary: Dict[str, Dict[str, Dict[str, float]]] = {}
    for snr, d in agg.items():
        summary[str(snr)] = {}
        for m, stats in d.items():
            bers = np.asarray(stats['ber']) if stats['ber'] else None
            nmse = np.asarray([v for v in stats['nmse'] if np.isfinite(v)]) if stats['nmse'] else None
            if bers is None or bers.size == 0:
                continue
            summary[str(snr)][m] = dict(
                ber_mean=float(bers.mean()), ber_std=float(bers.std()),
                nmse_mean_db=(float(10 * np.log10(nmse.mean() + 1e-30))
                              if nmse is not None and nmse.size > 0 else None),
                n=int(bers.size),
            )

    (out_dir / "results.json").write_text(json.dumps(summary, indent=2, default=float))

    # Markdown table
    md = [f"# classical_joint_unrolled eval — N={args.n_total}  frames/SNR={args.frames_per_snr}",
          ""]
    md.append("## BER (mean)")
    methods_present = sorted({m for d in summary.values() for m in d.keys()})
    md.append("| SNR | " + " | ".join(methods_present) + " |")
    md.append("|---:|" + "|".join(["---:"] * len(methods_present)) + "|")
    for snr in args.snr_list:
        row = [f"{snr} dB"]
        for m in methods_present:
            v = summary[str(snr)].get(m, {})
            row.append(f"{v.get('ber_mean', float('nan')):.3e}")
        md.append("| " + " | ".join(row) + " |")

    md.append("")
    md.append("## NMSE (dB)")
    md.append("| SNR | " + " | ".join(methods_present) + " |")
    md.append("|---:|" + "|".join(["---:"] * len(methods_present)) + "|")
    for snr in args.snr_list:
        row = [f"{snr} dB"]
        for m in methods_present:
            v = summary[str(snr)].get(m, {})
            n = v.get('nmse_mean_db')
            row.append(f"{n:+.2f}" if n is not None else "–")
        md.append("| " + " | ".join(row) + " |")

    md_path = out_dir / "results.md"
    md_path.write_text("\n".join(md))
    print("\n".join(md))

    # Figures (optional)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig_dir = out_dir / 'figures'
        fig_dir.mkdir(exist_ok=True)

        plt.figure(figsize=(6, 4.5))
        snrs = [int(s) for s in args.snr_list]
        for m in methods_present:
            ys = [summary[str(s)].get(m, {}).get('ber_mean', float('nan')) for s in snrs]
            plt.semilogy(snrs, ys, marker='o', label=m)
        plt.grid(True, which='both', alpha=0.3)
        plt.xlabel('SNR (dB)')
        plt.ylabel('BER')
        plt.title(f'N={args.n_total}  {args.frames_per_snr} frames/SNR')
        plt.legend(fontsize=7)
        plt.tight_layout()
        plt.savefig(fig_dir / 'ber_curve.png', dpi=160)
        plt.close()

        plt.figure(figsize=(6, 4.5))
        for m in methods_present:
            ys = [summary[str(s)].get(m, {}).get('nmse_mean_db') for s in snrs]
            ys = [v for v in ys if v is not None]
            if ys and len(ys) == len(snrs):
                plt.plot(snrs, ys, marker='o', label=m)
        plt.grid(True, alpha=0.3)
        plt.xlabel('SNR (dB)')
        plt.ylabel('NMSE (dB)')
        plt.title(f'Channel NMSE — N={args.n_total}')
        plt.legend(fontsize=7)
        plt.tight_layout()
        plt.savefig(fig_dir / 'nmse_curve.png', dpi=160)
        plt.close()
        print(f"[eval] figures written to {fig_dir}")
    except ImportError:
        print("[eval] matplotlib not available, skipping figures")


if __name__ == '__main__':
    main()
