#!/usr/bin/env python
"""Loop-13 BER-vs-outer-iteration probe.

For one (or a few) representative SNRs, sweep the joint-OMP/MP outer loop
iteration count and record the mean BER for:

  - Classical BP (joint_omp_mp_iterative, numpy via torch monkey-patch)
  - Learned C2-rel F2-P (ClassicalJointUnrolled with trained heads)

Emits results.json + convergence.png (thin lines).

Usage (remote):
    python afdm_sp_joint_unrolled/loop13_iter_convergence_probe.py \
        --n-total 1024 --v-mean 2.0 --p-paths 8 --tau-spread 0.010 \
        --rho 0.5 --snr-list 15 20 --iters 1 2 3 4 5 6 7 \
        --frames-per-iter 100 --seed 20260425 \
        --ckpt afdm_sp_joint_unrolled/outputs_loop9_c2rel_train/ckpt_c2rel_force_topk.pt \
        --out afdm_sp_joint_unrolled/outputs_loop13_iter_convergence
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
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
             damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                               threshold=threshold, damp=damp, device=dev,
                               return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _make_system_variable_N, QPSK, _bits_of_symbol)


VARIANT_HEADS = ('cand_active_rel',)  # C2-rel only


def _build_system(args):
    sys_obj = _make_system_variable_N(args.n_total)
    # Apply oversampling BEFORE recomputing k_max_cap: fs_factor = 1.0 -> Nyquist
    # (fs = 2B, matches 2B baseline); fs_factor = 2.0 -> 4B oversampling.
    sys_obj.fs = float(sys_obj.fs) * float(args.fs_factor)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.rho = float(args.rho)
    sys_obj.v_mean = float(args.v_mean)
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    # l_max_cap also depends on fs via tau_spread * fs; rebuild it.
    sys_obj.l_max_cap = max(int(np.ceil(sys_obj.tau_spread * sys_obj.fs)), 1)
    v_max = sys_obj.v_mean + 3.0 * 0.5
    d_norm = v_max * sys_obj.fc / (sys_obj.c_sound * sys_obj.fs)
    sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_norm)), 1)
    K = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    return sys_obj


def _make_learned_module(args, sys_obj, cfg_base):
    module = ClassicalJointUnrolled(cfg_base, learnable_heads=VARIANT_HEADS,
                                     use_soft_decisions=False)
    ckpt = torch.load(args.ckpt, map_location=cfg_base.device,
                      weights_only=False)
    sd = ckpt.get('state_dict') or ckpt.get('module') or ckpt
    module.load_state_dict(sd)
    module = module.to(cfg_base.device).eval()
    # Apply F2-P: refine-rounds=2, cand-topm=96, defer-prune, protect-added=2
    module.cand_active_rel.set_refine_config(
        refine_rounds=2, cand_topm=96,
        defer_prune=True, protect_added=2)
    return module


def _run_classical_numpy(sys_obj, args, snr, iters, rng_master):
    """Return {iter: ber} for classical joint_omp_mp_iterative (numpy)."""
    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    results = {}
    # For each iter count, run fresh frames (independent seeds)
    for n_out in iters:
        errs = bits = 0
        t_iter = time.time()
        for fi in range(args.frames_per_iter):
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi); rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
            data_idx = rng.integers(0, 4, size=args.n_total)
            data_qam = QPSK[data_idx]
            bits_true = np.concatenate([
                (data_qam.real < 0).astype(np.float32),
                (data_qam.imag < 0).astype(np.float32)])
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total) +
                     1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = H_true @ x_sp + np.sqrt(sigma2) * noise
            x_c, _ = joint_omp_mp_iterative(
                y_daft, pilot_scaled, args.n_total,
                sys_obj.c1, sys_obj.c2,
                sys_obj.l_max_cap, sys_obj.k_max_cap,
                sigma2, const_data, n_paths=sparsity,
                n_outer_iter=n_out, rho=rho,
                pic_iter=20, pic_damp=0.5, mp_mode='bp',
                gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
                tau_h_factor=0.01, tau_h_sigma_factor=0.1,
                threshold_mp=1e-4, k_leak=2, update_sigma2=True,
                phase_convention='python', eps_stop_rel=-1.0)
            b_c = _bits_of_symbol(x_c / np.sqrt(P_d), args.n_total)
            errs += int((b_c != bits_true).sum())
            bits += 2 * args.n_total
        ber = errs / max(bits, 1)
        dt = time.time() - t_iter
        print(f"  [cls snr={snr} iter={n_out}] ber={ber:.3e} "
              f"(errs={errs}/{bits}) [{dt:.0f}s]", flush=True)
        results[int(n_out)] = dict(ber=float(ber), errs=int(errs),
                                    bits=int(bits))
    return results


def _run_learned(module, sys_obj, cfg, args, snr, iters, rng_master, const_t,
                  x_pil_t, cdtype, rdtype):
    """Return {iter: ber} for the learned module (torch)."""
    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    results = {}
    for n_out in iters:
        errs = bits = 0
        t_iter = time.time()
        # ClassicalJointUnrolled instantiated heads for cfg_base.n_outer_iter;
        # setting cfg.n_outer_iter <= that still works (forward loops t ∈
        # range(cfg.n_outer_iter)). Above that, head indexing overflows, so
        # we cap at the built ckpt size (5).
        if int(n_out) > cfg.n_outer_iter:
            print(f"  [lrn snr={snr} iter={n_out}] skipping — exceeds "
                  f"ckpt's n_outer_iter={cfg.n_outer_iter}", flush=True)
            continue
        # Mutate runtime outer-loop count.
        orig_n_outer = cfg.n_outer_iter
        cfg.n_outer_iter = int(n_out)
        for fi in range(args.frames_per_iter):
            seed_fi = int(rng_master.integers(0, 2**31))
            np.random.seed(seed_fi); rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
            data_idx = rng.integers(0, 4, size=args.n_total)
            data_qam = QPSK[data_idx]
            bits_true = np.concatenate([
                (data_qam.real < 0).astype(np.float32),
                (data_qam.imag < 0).astype(np.float32)])
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total) +
                     1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = H_true @ x_sp + np.sqrt(sigma2) * noise
            y_t = torch.tensor(y_daft, dtype=cdtype, device=cfg.device)
            sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=cfg.device)
            module.cfg.n_paths = sparsity
            with torch.no_grad():
                out_l = module(y_t, x_pil_t, sigma2_t, const_t)
            x_l = out_l['x_soft'].cpu().numpy()
            b_l = _bits_of_symbol(x_l / np.sqrt(P_d), args.n_total)
            errs += int((b_l != bits_true).sum())
            bits += 2 * args.n_total
        cfg.n_outer_iter = orig_n_outer
        ber = errs / max(bits, 1)
        dt = time.time() - t_iter
        print(f"  [lrn snr={snr} iter={n_out}] ber={ber:.3e} "
              f"(errs={errs}/{bits}) [{dt:.0f}s]", flush=True)
        results[int(n_out)] = dict(ber=float(ber), errs=int(errs),
                                    bits=int(bits))
    return results


def _plot(results, out_path, args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    colors = ['tab:blue', 'tab:red', 'tab:green', 'tab:purple']
    style_cls = dict(linestyle='-', linewidth=1.3, marker='o', markersize=4)
    style_lrn = dict(linestyle='--', linewidth=1.3, marker='^', markersize=4)
    for i, snr in enumerate(args.snr_list):
        c_cls = colors[i % len(colors)]
        cls = results['classical'][str(snr)]
        if cls:
            iters_cls = sorted(int(k) for k in cls)
            ax.plot(iters_cls, [cls[str(k)]['ber'] for k in iters_cls],
                    color=c_cls, label=f'Classical BP (SNR={snr} dB)',
                    **style_cls)
        lrn = results['learned'][str(snr)]
        if lrn:
            iters_lrn = sorted(int(k) for k in lrn)
            ax.plot(iters_lrn, [lrn[str(k)]['ber'] for k in iters_lrn],
                    color=c_cls, label=f'Learned C2-rel F2-P (SNR={snr} dB)',
                    **style_lrn)
    ax.set_yscale('log')
    ax.set_xlabel('Outer iteration count')
    ax.set_ylabel('BER (log scale)')
    ax.set_title('Loop-13 BER vs outer-iteration count '
                 '(classical BP vs learned C2-rel F2-P)')
    ax.grid(True, which='both', alpha=0.3, linewidth=0.6)
    ax.legend(fontsize=8, loc='best')
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"[saved] {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--rho', type=float, default=0.5)
    ap.add_argument('--snr-list', nargs='+', type=int, default=[20])
    ap.add_argument('--iters', nargs='+', type=int,
                    default=[1, 2, 3, 4, 5, 6, 7])
    ap.add_argument('--frames-per-iter', type=int, default=100)
    ap.add_argument('--seed', type=int, default=20260425)
    ap.add_argument('--fs-factor', type=float, default=1.0,
                    help='Oversampling relative to Nyquist. 1.0=fs=2B (default); '
                         '2.0=fs=4B oversampling.')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sys_obj = _build_system(args)
    cdtype = torch.complex64
    rdtype = torch.float32
    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode='bp', pic_damp=0.5, n_paths=int(sys_obj.P_paths),
        n_outer_iter=5, pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype,
        device='cuda' if torch.cuda.is_available() else 'cpu',
    )
    module = _make_learned_module(args, sys_obj, cfg)
    rho = float(sys_obj.rho); P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    const_t = torch.tensor(const_data, dtype=cdtype, device=cfg.device)
    x_pil_t = torch.tensor(pilot_scaled, dtype=cdtype, device=cfg.device)
    Q_dict = (2 * sys_obj.k_max_cap + 1) * sys_obj.l_max_cap
    print(f"[LOOP13_ITER_CONFIG] N={args.n_total} v={sys_obj.v_mean} "
          f"P={sys_obj.P_paths} tau={sys_obj.tau_spread*1e3:.2f}ms "
          f"rho={sys_obj.rho} fs_factor={args.fs_factor:.2f} "
          f"fs={sys_obj.fs:.0f} l_max={sys_obj.l_max_cap} "
          f"k_max={sys_obj.k_max_cap} Q={Q_dict} "
          f"SNRs={args.snr_list} iters={args.iters} "
          f"frames/iter={args.frames_per_iter} seed={args.seed}",
          flush=True)

    all_results = {'classical': {}, 'learned': {}, '_config': {
        'N': args.n_total, 'v_mean': args.v_mean, 'P_paths': int(sys_obj.P_paths),
        'tau_spread_ms': sys_obj.tau_spread * 1e3, 'rho': sys_obj.rho,
        'fs_factor': float(args.fs_factor), 'fs': float(sys_obj.fs),
        'l_max': int(sys_obj.l_max_cap), 'k_max': int(sys_obj.k_max_cap),
        'Q_dict': int(Q_dict),
        'snrs': list(args.snr_list), 'iters': list(args.iters),
        'frames_per_iter': args.frames_per_iter, 'seed': args.seed,
        'ckpt': args.ckpt,
    }}
    for snr in args.snr_list:
        # Use SAME seed sequence for classical and learned so frames are paired.
        rng_cls = np.random.default_rng(args.seed + 10 * snr)
        rng_lrn = np.random.default_rng(args.seed + 10 * snr)
        print(f"[snr={snr}] running classical...", flush=True)
        all_results['classical'][str(snr)] = _run_classical_numpy(
            sys_obj, args, snr, args.iters, rng_cls)
        print(f"[snr={snr}] running learned...", flush=True)
        all_results['learned'][str(snr)] = _run_learned(
            module, sys_obj, cfg, args, snr, args.iters, rng_lrn,
            const_t, x_pil_t, cdtype, rdtype)

    # Convert int keys to str for json
    def _strkeys(d):
        if isinstance(d, dict):
            return {str(k): _strkeys(v) for k, v in d.items()}
        return d
    (out / 'results.json').write_text(
        json.dumps(_strkeys(all_results), indent=2))
    _plot(_strkeys(all_results), out / 'convergence.png', args)
    print(f'[done] wrote {out}')


if __name__ == '__main__':
    main()
