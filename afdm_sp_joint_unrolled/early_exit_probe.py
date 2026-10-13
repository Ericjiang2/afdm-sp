#!/usr/bin/env python
"""Early-exit probe — record per-outer-iter x_hat trajectory + BER.

W8 Path A Phase 0. Determines whether early-exit is feasible by measuring
how many frames "converge" (BER matches final iter=10 BER) by intermediate
iter counts.

For each frame at SNR ∈ {15, 20, 25}:
  - Build frame identically to paired_learned_eval (sys_obj.generate_channel_matrix
    → ZC pilot + QPSK data + noise, seed-master controlled).
  - Run ClassicalJointUnrolled with cfg.n_outer_iter = max_iter (default 10),
    with canonical C2-rel ckpt (head fires once at t=0 as architecturally
    documented).
  - Pull out_l['x_soft_history']: list of length max_iter, each a (N,) complex
    tensor snapshot at end of outer iter t.
  - Pull out_l['resnorm_history']: list of length max_iter, each a scalar.
  - For each t, compute bit-error count by hard-decision QPSK on x_soft_t.

Output JSON to <out>/trajectory.json:
  {
    "meta": { ckpt, snr_list, frames_per_snr, max_iter, n_total, ... },
    "per_frame": [
      { snr, frame_idx, err_per_iter (max_iter,), resnorm_per_iter (max_iter,),
        bits_total }, ...
    ],
    "summary_per_snr": { snr: {
       avg_err_per_iter: [10 floats],
       frames_converged_by_iter: [10 ints]  # count w/ err_t == err_final
       frames_strictly_converged_by_iter: [10 ints]  # count w/ err_t <= err_final
    }}
  }

Usage (server, after scp):
  python afdm_sp_joint_unrolled/early_exit_probe.py \
      --ckpt afdm_sp_joint_unrolled/outputs_canonical_grid_s20260507/ckpt_c2rel.pt.force_topk \
      --snr-list 15 20 25 --frames-per-snr 200 --max-iter 10 \
      --out afdm_sp_joint_unrolled/outputs_early_exit_probe_v0
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


def _fast_bp(y, H, sigma2, constellation, n_iter=20, threshold=1e-4, damp=0.5,
             return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return mp_detect_bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                               threshold=threshold, damp=damp, device=dev,
                               return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _make_system_variable_N, QPSK, _bits_of_symbol)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ckpt', required=True)
    ap.add_argument('--variant', default='C2-rel')
    ap.add_argument('--mp-mode', default='bp')
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--snr-list', type=int, nargs='+', default=[15, 20, 25])
    ap.add_argument('--frames-per-snr', type=int, default=200)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--seed', type=int, default=20260423)
    ap.add_argument('--cdtype', choices=['complex64', 'complex128'],
                    default='complex64')
    ap.add_argument('--max-iter', type=int, default=10,
                    help='Receiver outer iter count for trajectory extraction.')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # System setup verbatim from paired_learned_eval (lines 327-344) so
    # trajectory is bit-exact with canonical TCOM eval regime.
    sys_obj = _make_system_variable_N(args.n_total, rho=0.5)
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

    cdtype = torch.complex64 if args.cdtype == 'complex64' else torch.complex128
    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64

    # Peek ckpt for head dims (for non-default pair_hidden / scorer_hidden)
    _ckpt_peek = torch.load(args.ckpt, map_location='cpu', weights_only=False)
    _head_config = _ckpt_peek.get('head_config') or {}
    _pair_h = int(_head_config.get('pair_hidden', 16))
    _scorer_h = int(_head_config.get('scorer_hidden', 16))

    cfg = ClassicalJointConfig(
        N=args.n_total, l_max=sys_obj.l_max_cap, k_max=sys_obj.k_max_cap,
        c1=sys_obj.c1, c2=sys_obj.c2, rho=float(sys_obj.rho),
        mp_mode=args.mp_mode, pic_damp=args.pic_damp,
        n_paths=int(sys_obj.P_paths),
        n_outer_iter=int(args.max_iter), pic_iter=20, update_sigma2=True,
        early_stop=False, eps_stop_rel=-1.0,
        dtype=cdtype, rdtype=rdtype,
        device='cuda' if torch.cuda.is_available() else 'cpu',
        cand_pair_hidden=_pair_h, cand_scorer_hidden=_scorer_h,
    )
    # Hard-coded C2-rel head only (consistent with canonical TCOM ckpt).
    heads = ('cand_active_rel',)
    module = ClassicalJointUnrolled(cfg, learnable_heads=heads,
                                     use_soft_decisions=True)
    sd = _ckpt_peek.get('state_dict') or _ckpt_peek.get('module') or _ckpt_peek
    module.load_state_dict(sd)
    module = module.to(cfg.device).eval()
    print(f'[probe] loaded {args.ckpt} variant={args.variant} '
          f'max_iter={args.max_iter}', flush=True)

    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    const_data = np.sqrt(P_d) * QPSK
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    const_t = torch.tensor(const_data, dtype=cdtype, device=cfg.device)
    x_pil_t = torch.tensor(pilot_scaled, dtype=cdtype, device=cfg.device)

    per_frame_records = []
    summary = {}
    t_start = time.time()
    rng_master = np.random.default_rng(args.seed)
    for snr in args.snr_list:
        err_per_iter_accum = np.zeros(args.max_iter, dtype=np.int64)
        n_converged_by_iter = np.zeros(args.max_iter, dtype=np.int64)
        n_strict_by_iter = np.zeros(args.max_iter, dtype=np.int64)
        for fi in range(args.frames_per_snr):
            seed_fi = int(rng_master.integers(0, 2 ** 31))
            np.random.seed(seed_fi)
            rng = np.random.default_rng(seed_fi)
            H_true, _, _ = sys_obj.generate_channel_matrix()
            sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
            data_idx = rng.integers(0, 4, size=args.n_total)
            data_qam = QPSK[data_idx]
            bits_true = np.concatenate(
                [(data_qam.real < 0).astype(np.float32),
                 (data_qam.imag < 0).astype(np.float32)])
            x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
            y = H_true @ x_sp
            sigma2 = 1.0 / (10 ** (snr / 10.0))
            noise = (rng.standard_normal(args.n_total)
                     + 1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
            y_daft = y + np.sqrt(sigma2) * noise

            y_t = torch.tensor(y_daft, dtype=cdtype, device=cfg.device)
            sigma2_t = torch.tensor(sigma2, dtype=rdtype, device=cfg.device)
            module.cfg.n_paths = sparsity

            with torch.no_grad():
                out_l = module(y_t, x_pil_t, sigma2_t, const_t)

            x_hist = out_l['x_soft_history']    # list[max_iter] complex(N,)
            r_hist = out_l['resnorm_history']    # list[max_iter] scalar

            err_per_iter = []
            res_per_iter = []
            flip_per_iter = []         # v2: hard-decision flip rate (direct BER-convergence proxy)
            xdelta_per_iter = []       # v2: ||x_soft[t] - x_soft[t-1]||_2 (continuous-state delta)
            b_prev = None
            x_prev = None
            for t in range(args.max_iter):
                x_t = x_hist[t].cpu().numpy()
                b_t = _bits_of_symbol(x_t / np.sqrt(P_d), args.n_total)
                e_t = int((b_t != bits_true).sum())
                r_t = float(r_hist[t].cpu().item())
                if t == 0:
                    flip_t = 0.0
                    delta_t = 0.0
                else:
                    flip_t = float((b_t != b_prev).mean())
                    delta_t = float(np.linalg.norm(x_t - x_prev))
                err_per_iter.append(e_t)
                res_per_iter.append(r_t)
                flip_per_iter.append(flip_t)
                xdelta_per_iter.append(delta_t)
                b_prev = b_t
                x_prev = x_t

            # Convergence flags relative to final iter
            err_final = err_per_iter[-1]
            for t in range(args.max_iter):
                err_per_iter_accum[t] += err_per_iter[t]
                if err_per_iter[t] == err_final:
                    n_converged_by_iter[t] += 1
                if err_per_iter[t] <= err_final:
                    n_strict_by_iter[t] += 1

            per_frame_records.append(dict(
                snr=int(snr), frame_idx=int(fi), seed=seed_fi,
                err_per_iter=err_per_iter,
                resnorm_per_iter=res_per_iter,
                flip_rate_per_iter=flip_per_iter,
                x_soft_delta_per_iter=xdelta_per_iter,
                bits_total=int(len(bits_true)),
            ))

        n_frames = args.frames_per_snr
        summary[str(snr)] = dict(
            n_frames=int(n_frames),
            avg_err_per_iter=[float(x) / n_frames
                              for x in err_per_iter_accum],
            frames_converged_by_iter=[int(x) for x in n_converged_by_iter],
            frames_strictly_converged_by_iter=[int(x) for x in n_strict_by_iter],
            converged_frac_by_iter=[float(x) / n_frames
                                     for x in n_converged_by_iter],
        )
        elapsed = time.time() - t_start
        print(f'[snr={snr}] frames={n_frames} '
              f'avg_err_iter[0/4/9]={summary[str(snr)]["avg_err_per_iter"][0]:.2f}/'
              f'{summary[str(snr)]["avg_err_per_iter"][4]:.2f}/'
              f'{summary[str(snr)]["avg_err_per_iter"][9]:.2f} '
              f'conv@iter5={summary[str(snr)]["converged_frac_by_iter"][4]:.2f} '
              f't={elapsed:.0f}s', flush=True)

    meta = dict(
        ckpt=args.ckpt, variant=args.variant, mp_mode=args.mp_mode,
        pic_damp=args.pic_damp, p_paths=args.p_paths,
        tau_spread=args.tau_spread, n_total=args.n_total,
        v_mean=args.v_mean, fs_factor=args.fs_factor,
        snr_list=args.snr_list, frames_per_snr=args.frames_per_snr,
        max_iter=args.max_iter, seed=args.seed, cdtype=args.cdtype,
        _argv=list(sys.argv),
    )
    output = dict(meta=meta, summary_per_snr=summary,
                  per_frame=per_frame_records)
    out_json = out_dir / 'trajectory.json'
    out_json.write_text(json.dumps(output, indent=2))
    print(f'[probe] wrote {out_json}  ({len(per_frame_records)} frames total, '
          f'{time.time()-t_start:.0f}s wall)', flush=True)


if __name__ == '__main__':
    main()
