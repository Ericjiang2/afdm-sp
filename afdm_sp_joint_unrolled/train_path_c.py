#!/usr/bin/env python
"""W8 Path C trainer — unified for C1 SimplestC / C2 Transformer / C3 HybridC.

On-the-fly SP-frame generation (same convention as paired_learned_eval +
train_classical_joint_unrolled). Loss = lam_bce*BCE_bits + lam_sym*MSE.

Usage:
  python train_path_c.py --model c1 --n-outer-iter-bootstrap 1 \
    --n-total 1024 --fs-factor 4.0 --v-mean 2.0 --p-paths 8 \
    --tau-spread 0.010 --snr-list 15 20 25 --iters 1500 --batch 4 \
    --out-dir afdm_sp_joint_unrolled/outputs_pathc_c1
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
import torch.nn.functional as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# Monkey-patch fast BP
from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch as _bp_torch


def _fast_bp_numpy_shim(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
                        damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return _bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                     threshold=threshold, damp=damp,
                     device=dev, return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp_numpy_shim

from afdm_sp_joint_unrolled.classical_joint_unrolled import (
    ClassicalJointConfig, ClassicalJointUnrolled)
from afdm_sp_joint_unrolled.eval_classical_joint_unrolled import (
    _make_system_variable_N, QPSK, _bits_of_symbol)
from afdm_sp_joint_unrolled.path_c_models import (
    SimplestC, TransformerReceiver, HybridC, count_params)


# ----------------------------------------------------------------------
# Frame generation + loss helpers
# ----------------------------------------------------------------------
def _sample_frame(sys_obj, snr: int, rng, cdtype, device, args):
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    H_true, _, _ = sys_obj.generate_channel_matrix()
    sparsity = int(getattr(sys_obj, '_P_actual', sys_obj.P_paths))
    data_idx = rng.integers(0, 4, size=args.n_total)
    data_qam = QPSK[data_idx]
    bits_true = np.concatenate(
        [(data_qam.real < 0).astype(np.float32),
         (data_qam.imag < 0).astype(np.float32)])
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    x_sp = pilot_scaled + np.sqrt(P_d) * data_qam
    y = H_true @ x_sp
    sigma2 = 1.0 / (10 ** (snr / 10.0))
    noise = (rng.standard_normal(args.n_total) +
             1j * rng.standard_normal(args.n_total)) / np.sqrt(2.0)
    y_daft = y + np.sqrt(sigma2) * noise
    rdtype = torch.float32 if cdtype == torch.complex64 else torch.float64
    return dict(
        y_daft=torch.tensor(y_daft, dtype=cdtype, device=device),
        x_pilot=torch.tensor(pilot_scaled, dtype=cdtype, device=device),
        sigma2=torch.tensor(sigma2, dtype=rdtype, device=device),
        const=torch.tensor(np.sqrt(P_d) * QPSK, dtype=cdtype, device=device),
        data_qam=data_qam, bits_true=bits_true,
        P_d=float(P_d), N=int(args.n_total),
    )


def _bits_from_xhat(x_hat: torch.Tensor, P_d: float, N: int) -> torch.Tensor:
    x_norm = x_hat / float(np.sqrt(P_d))
    # bit 1 if real < 0; bit 2 if imag < 0
    bits = torch.cat([(x_norm.real < 0).float(),
                      (x_norm.imag < 0).float()])
    return bits


def _loss_one_frame(out: Dict, frame: Dict, args) -> torch.Tensor:
    x_hat = out['x_soft']
    P_d = frame['P_d']
    N = frame['N']
    bits_true_t = torch.from_numpy(frame['bits_true']).to(x_hat.device)
    # BCE-bits: use signed soft real/imag as logits, normalized by P_d.
    x_norm = x_hat / float(np.sqrt(P_d))
    # Targets: bit=1 if Re<0 (or Im<0); soft logit = -Re*scale (so logit>0 when Re<0)
    scale = float(args.bce_scale)
    logits = torch.cat([-x_norm.real * scale, -x_norm.imag * scale])
    bce = F.binary_cross_entropy_with_logits(logits.float(),
                                              bits_true_t.float()).double()
    # MSE on symbol vs ground-truth QPSK (in pre-Pd scale)
    target = torch.tensor(frame['data_qam'], dtype=x_hat.dtype,
                          device=x_hat.device)
    target_scaled = target * float(np.sqrt(P_d))
    diff = x_hat - target_scaled
    mse = (diff.real.pow(2) + diff.imag.pow(2)).mean().double()
    return (float(args.lam_bce) * bce + float(args.lam_sym) * mse).float()


def _ber_one_frame(x_hat_np: np.ndarray, bits_true: np.ndarray,
                   P_d: float, N: int) -> float:
    x_norm = x_hat_np / float(np.sqrt(P_d))
    bits = np.concatenate([(x_norm.real < 0).astype(np.float32),
                           (x_norm.imag < 0).astype(np.float32)])
    return float((bits != bits_true).mean())


# ----------------------------------------------------------------------
# Model builder
# ----------------------------------------------------------------------
def build_model(args, sys_obj, cdtype, rdtype, device):
    cfg = ClassicalJointConfig(
        N=int(sys_obj.N_total),
        l_max=int(sys_obj.l_max_cap),
        k_max=int(sys_obj.k_max_cap),
        c1=float(sys_obj.c1), c2=float(sys_obj.c2),
        n_outer_iter=int(args.n_outer_iter_bootstrap),
        pic_iter=20, pic_damp=float(args.pic_damp),
        mp_mode=str(args.mp_mode),
        rho=float(sys_obj.rho), n_paths=int(sys_obj.P_paths),
        dtype=cdtype, rdtype=rdtype, early_stop=False,
    )
    if args.model == 'c1':
        bootstrap = ClassicalJointUnrolled(cfg, learnable_heads=(),
                                            use_soft_decisions=True)
        model = SimplestC(bootstrap, base_ch=int(args.base_ch))
    elif args.model == 'c2':
        model = TransformerReceiver(N=int(args.n_total),
                                     d_model=int(args.d_model),
                                     nhead=int(args.nhead),
                                     num_layers=int(args.num_layers),
                                     dim_ff=int(args.dim_ff))
    elif args.model == 'c3':
        bootstrap = ClassicalJointUnrolled(cfg, learnable_heads=(),
                                            use_soft_decisions=True)
        model = HybridC(bootstrap, hidden=int(args.hidden),
                        depth=int(args.depth))
    else:
        raise ValueError(f'unknown model {args.model}')
    return model.to(device)


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', choices=['c1', 'c2', 'c3'], required=True)
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--mp-mode', default='bp')
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--snr-list', type=int, nargs='+', default=[15, 20, 25])
    ap.add_argument('--n-outer-iter-bootstrap', type=int, default=1,
                    help='C1/C3 only: number of MP-BP iters in bootstrap.')
    # C1 / C3 hyperparams
    ap.add_argument('--base-ch', type=int, default=32, help='C1 UNet1D base.')
    ap.add_argument('--hidden', type=int, default=64, help='C3 NN-MP hidden.')
    ap.add_argument('--depth', type=int, default=4, help='C3 NN-MP depth.')
    # C2 hyperparams
    ap.add_argument('--d-model', type=int, default=128)
    ap.add_argument('--nhead', type=int, default=4)
    ap.add_argument('--num-layers', type=int, default=4)
    ap.add_argument('--dim-ff', type=int, default=512)
    # Training
    ap.add_argument('--iters', type=int, default=1500)
    ap.add_argument('--batch', type=int, default=4)
    ap.add_argument('--lr', type=float, default=5e-4)
    ap.add_argument('--lam-bce', type=float, default=1.0)
    ap.add_argument('--lam-sym', type=float, default=0.05)
    ap.add_argument('--bce-scale', type=float, default=8.0)
    ap.add_argument('--grad-clip', type=float, default=5.0)
    ap.add_argument('--eval-every', type=int, default=100)
    ap.add_argument('--eval-frames', type=int, default=20)
    ap.add_argument('--patience', type=int, default=10)
    ap.add_argument('--cdtype', choices=['complex64', 'complex128'],
                    default='complex64')
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--device', default='auto')
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # System (mirror paired_learned_eval canonical setup)
    sys_obj = _make_system_variable_N(args.n_total, rho=0.5)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.tau_spread = float(args.tau_spread)
    sys_obj.gen_h_daft_convention = sys_obj.baseline_phase_convention = 'python'
    sys_obj.v_mean = float(args.v_mean)
    if abs(float(args.fs_factor) - 2.0) > 1e-9:
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

    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    model = build_model(args, sys_obj, cdtype, rdtype, device)
    n_params = count_params(model)
    print(f'[train_path_c] model={args.model}  params={n_params}  '
          f'device={device}  N={args.n_total}', flush=True)

    optim = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(args.lr), weight_decay=1e-5)

    rng_train = np.random.default_rng(args.seed + 100)
    rng_eval = np.random.default_rng(args.seed + 9999)
    log: List[Dict] = []
    best_score = float('inf')
    best_state = None
    patience_left = int(args.patience)

    t_start = time.time()
    for it in range(int(args.iters)):
        model.train()
        # Accumulate loss over batch
        loss_acc = torch.zeros((), device=device, dtype=torch.float32)
        ber_acc = []
        for _ in range(int(args.batch)):
            snr = int(args.snr_list[rng_train.integers(0, len(args.snr_list))])
            frame = _sample_frame(sys_obj, snr, rng_train, cdtype, device,
                                   args)
            out = model(frame['y_daft'], frame['x_pilot'],
                        frame['sigma2'], frame['const'])
            loss = _loss_one_frame(out, frame, args)
            loss_acc = loss_acc + loss
            ber_acc.append(_ber_one_frame(
                out['x_soft'].detach().cpu().numpy(),
                frame['bits_true'], frame['P_d'], frame['N']))
        loss_mean = loss_acc / float(args.batch)
        optim.zero_grad()
        loss_mean.backward()
        torch.nn.utils.clip_grad_norm_(
            [p for p in model.parameters() if p.requires_grad],
            max_norm=float(args.grad_clip))
        optim.step()
        if it % 20 == 0:
            print(f'[it={it:5d}] loss={float(loss_mean):.4e} '
                  f'ber_train={np.mean(ber_acc):.4e}  '
                  f'[{time.time()-t_start:.0f}s]', flush=True)
        log.append(dict(it=it, loss=float(loss_mean),
                        ber_train=float(np.mean(ber_acc))))
        # Eval
        if (it + 1) % int(args.eval_every) == 0 or (it + 1) == int(args.iters):
            model.eval()
            bers_per_snr: Dict[int, List[float]] = {s: []
                                                     for s in args.snr_list}
            with torch.no_grad():
                for ef in range(int(args.eval_frames)):
                    for snr in args.snr_list:
                        frame = _sample_frame(sys_obj, snr, rng_eval, cdtype,
                                               device, args)
                        out = model(frame['y_daft'], frame['x_pilot'],
                                    frame['sigma2'], frame['const'])
                        bers_per_snr[snr].append(_ber_one_frame(
                            out['x_soft'].detach().cpu().numpy(),
                            frame['bits_true'], frame['P_d'], frame['N']))
            mean_ber_per_snr = {s: float(np.mean(bers_per_snr[s]))
                                 for s in args.snr_list}
            score = float(np.mean(list(mean_ber_per_snr.values())))
            print(f'[eval it={it+1}] score={score:.4e}  ' +
                  '  '.join(f'snr={s}: {b:.3e}'
                            for s, b in mean_ber_per_snr.items()),
                  flush=True)
            log[-1]['eval'] = mean_ber_per_snr
            if score < best_score - 1e-6:
                best_score = score
                best_state = {k: v.detach().cpu().clone()
                              for k, v in model.state_dict().items()
                              if 'bootstrap' not in k}
                patience_left = int(args.patience)
                # Save best
                ckpt = dict(
                    model=args.model,
                    state_dict=best_state,
                    args=vars(args),
                    best_score=float(best_score),
                    iter=int(it + 1),
                    n_params=int(n_params),
                )
                torch.save(ckpt, out_dir / 'ckpt_best.pt')
                print(f'  ★ best score → {out_dir/"ckpt_best.pt"}',
                      flush=True)
            else:
                patience_left -= 1
                if patience_left <= 0:
                    print(f'[early stop] patience exhausted at it={it+1}',
                          flush=True)
                    break

    # Final ckpt
    final_state = {k: v.detach().cpu().clone()
                   for k, v in model.state_dict().items()
                   if 'bootstrap' not in k}
    final_ckpt = dict(
        model=args.model,
        state_dict=final_state,
        args=vars(args),
        best_score=float(best_score),
        n_params=int(n_params),
    )
    torch.save(final_ckpt, out_dir / 'ckpt_final.pt')
    (out_dir / 'train_log.json').write_text(json.dumps(log, indent=2))
    print(f'[train_path_c] done. best_score={best_score:.4e}  '
          f'wall={time.time()-t_start:.0f}s', flush=True)


if __name__ == '__main__':
    main()
