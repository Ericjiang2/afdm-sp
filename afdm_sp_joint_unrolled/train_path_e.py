"""train_path_e.py — Train E0/E1/E2/E3 end-to-end ladder.

Adapted from train_path_c.py with proper hparams (Xavier init handled in
model; cosine LR + warmup; larger batch; more iters). Uses BCE-on-bits +
optional NMSE-on-H_est for E2/E3.

Usage::

    conda activate AFDM && \\
      python afdm_sp_joint_unrolled/train_path_e.py \\
        --model e0 --n-total 1024 --snr-list 20 \\
        --iters 3000 --batch 8 --lr 1e-4 --warmup 200 \\
        --out-dir afdm_sp_joint_unrolled/outputs_e0_smoke
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time
from typing import Dict, List

import numpy as np
import torch
import torch.nn.functional as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from afdm_sp_joint_unrolled.afdm_baselines import (  # noqa: E402
    joint_omp_mp_iterative, construct_sensing_matrix, omp_sparse,
)
from afdm_sp_joint_unrolled.run_classical_baselines_python import (  # noqa: E402
    QPSK, _bits_of_symbol, _ber, _make_system_variable_N,
)
from afdm_sp_joint_unrolled.path_e_models import (  # noqa: E402
    FixedTransformerReceiver,
    DaftAwareTransformerReceiver,
    OtfsModularReceiver,
    AutoencoderJointTxRx,
    HybridOMPRefiner,
    TwoHeadCENet,
    UnrolledOMPNet,
    count_params,
)


def _sample_frame(sys_obj, snr: int, rng, cdtype, device, args,
                   want_omp_warmstart: bool = False):
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho
    H_true, _, _ = sys_obj.generate_channel_matrix()
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

    # Optionally precompute classical-OMP dense DD-grid target as a label for
    # CENet supervision (warm-start positive control).
    h_omp_dd = None
    if want_omp_warmstart:
        sparsity = max(int(getattr(sys_obj, '_P_actual', sys_obj.P_paths)),
                       int(sys_obj.P_paths))
        Phi = construct_sensing_matrix(
            sys_obj.N_total, pilot_scaled, sys_obj.c1, sys_obj.c2,
            sys_obj.l_max_cap, sys_obj.k_max_cap)
        h_vec, _ = omp_sparse(y_daft, Phi, sparsity)
        # Reshape h_vec (Q,) into dense (L, K) DD grid for CENet supervision.
        L = sys_obj.l_max_cap + 1
        K = 2 * sys_obj.k_max_cap + 1
        # Q indexing: col = l * K + (k + k_max), with k_idx ∈ [0, K-1]
        h_omp_dd = h_vec.reshape(L, K)

    return dict(
        y_daft=torch.tensor(y_daft, dtype=cdtype, device=device),
        x_pilot=torch.tensor(pilot_scaled, dtype=cdtype, device=device),
        sigma2=torch.tensor(sigma2, dtype=rdtype, device=device),
        const=torch.tensor(np.sqrt(P_d) * QPSK, dtype=cdtype, device=device),
        data_qam=data_qam, bits_true=bits_true,
        P_d=float(P_d), N=int(args.n_total),
        H_true=H_true,
        x_sp=x_sp,
        h_omp_dd=h_omp_dd,
    )


def _bce_loss(x_hat: torch.Tensor, bits_true_np: np.ndarray, P_d: float,
              scale: float = 8.0) -> torch.Tensor:
    N = x_hat.shape[0]
    x_norm = x_hat / float(np.sqrt(P_d))
    bits_true_t = torch.from_numpy(bits_true_np).to(x_hat.device)
    logits = torch.cat([-x_norm.real.float() * scale,
                         -x_norm.imag.float() * scale])
    return F.binary_cross_entropy_with_logits(logits, bits_true_t.float()).double()


def _sym_mse(x_hat: torch.Tensor, data_qam_np: np.ndarray,
             P_d: float) -> torch.Tensor:
    target = torch.tensor(data_qam_np, dtype=x_hat.dtype, device=x_hat.device)
    target_scaled = target * float(np.sqrt(P_d))
    diff = x_hat - target_scaled
    return (diff.real.pow(2) + diff.imag.pow(2)).mean().double()


def _channel_nmse(H_est: torch.Tensor, H_true_np: np.ndarray,
                   x_sp_np: np.ndarray) -> torch.Tensor:
    """Effective-channel NMSE supervised by ground-truth H_true.
    L = ||(H_est - H_true) · x_sp||² / ||H_true · x_sp||²
    Lower variance than full Frobenius NMSE and directly targets the
    "channel applied to transmitted signal" error which drives detection.
    """
    device = H_est.device
    cdtype = H_est.dtype
    rdtype = H_est.real.dtype
    H_true_t = torch.tensor(H_true_np, dtype=cdtype, device=device)
    x_sp_t = torch.tensor(x_sp_np, dtype=cdtype, device=device)
    num = (H_est - H_true_t) @ x_sp_t
    den = H_true_t @ x_sp_t
    num_sq = (num.real.pow(2) + num.imag.pow(2)).sum()
    den_sq = (den.real.pow(2) + den.imag.pow(2)).sum().clamp_min(1e-30)
    return (num_sq / den_sq).to(rdtype).double()


def _deep_supervision_nmse(g_dd_history, h_recon, H_true_np, x_sp_np,
                            decay: float = 1.0,
                            last_k: int = 0) -> torch.Tensor:
    """Path G/G3: Deep supervision via per-iter NMSE-on-H_true.

    For each intermediate g_dd^(k), reconstruct H_eff^(k) via the analytical
    chirp h_recon and supervise NMSE against H_true. Later iters get higher
    weight: w_k = decay^(K-1-k). decay=1.0 → uniform, decay<1 → late-iter
    weighted, decay>1 → early-iter weighted.

    G3 addition: last_k > 0 restricts DS to only the LAST `last_k` iterations.
    Motivated by Path G null result — early iters have g_dd^(k) ≈ 0 so NMSE^(k)
    ≈ 1 is constant noise that drowns out BCE gradient. Late iters (k=K-3..K-1)
    are where g_dd has structure and DS signal is informative.

    Reference: ISTA-Net++ / deep-supervision survey — adds intermediate-layer
    supervision to smooth credit assignment in unrolled networks, attacks the
    late-iter loss oscillation symptom.
    """
    if not g_dd_history:
        return torch.zeros((), dtype=torch.float64)
    K = len(g_dd_history)
    if last_k > 0 and last_k < K:
        g_dd_history = g_dd_history[-last_k:]
        K = last_k
    # Compute weights w_k normalised to sum=1
    weights = [decay ** (K - 1 - k) for k in range(K)]
    w_sum = sum(weights)
    weights = [w / w_sum for w in weights]
    # Pre-compute H_true · x_sp denominator once
    device = g_dd_history[0].device
    cdtype = g_dd_history[0].dtype
    rdtype = g_dd_history[0].real.dtype
    H_true_t = torch.tensor(H_true_np, dtype=cdtype, device=device)
    x_sp_t = torch.tensor(x_sp_np, dtype=cdtype, device=device)
    den = H_true_t @ x_sp_t
    den_sq = (den.real.pow(2) + den.imag.pow(2)).sum().clamp_min(1e-30)
    total = torch.zeros((), dtype=torch.float64, device=device)
    for k, g_dd_k in enumerate(g_dd_history):
        H_k = h_recon(g_dd_k)
        num = (H_k - H_true_t) @ x_sp_t
        num_sq = (num.real.pow(2) + num.imag.pow(2)).sum()
        nmse_k = (num_sq / den_sq).to(rdtype).double()
        total = total + weights[k] * nmse_k
    return total


def _ber_one_frame(x_hat_np: np.ndarray, bits_true: np.ndarray,
                   P_d: float, N: int) -> float:
    x_norm = x_hat_np / float(np.sqrt(P_d))
    bits = np.concatenate([(x_norm.real < 0).astype(np.float32),
                           (x_norm.imag < 0).astype(np.float32)])
    return float((bits != bits_true).mean())


def _classical_baseline_ber(frame, sys_obj, n_outer_iter=10):
    const_data = np.sqrt(frame['P_d']) * QPSK
    sparsity = max(int(getattr(sys_obj, '_P_actual', sys_obj.P_paths)),
                    int(sys_obj.P_paths))
    x_soft, _ = joint_omp_mp_iterative(
        frame['y_daft'].cpu().numpy() if isinstance(frame['y_daft'], torch.Tensor) else frame['y_daft'],
        frame['x_pilot'].cpu().numpy() if isinstance(frame['x_pilot'], torch.Tensor) else frame['x_pilot'],
        frame['N'], sys_obj.c1, sys_obj.c2, sys_obj.l_max_cap, sys_obj.k_max_cap,
        float(frame['sigma2'].cpu()) if isinstance(frame['sigma2'], torch.Tensor) else frame['sigma2'],
        const_data, n_paths=sparsity, n_outer_iter=n_outer_iter,
        rho=frame['P_d'] is not None and (1 - frame['P_d']) or 0.5,
        pic_iter=20, pic_damp=0.5, mp_mode='bp',
        gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1,
        k_leak=2, update_sigma2=True, phase_convention='python',
    )
    return _ber_one_frame(x_soft, frame['bits_true'], frame['P_d'], frame['N'])


def build_model(args, sys_obj, cdtype, rdtype, device):
    if args.model == 'e0':
        return FixedTransformerReceiver(
            N=int(args.n_total), d_model=int(args.d_model),
            nhead=int(args.nhead), num_layers=int(args.num_layers),
            dim_ff=int(args.dim_ff)).to(device)
    if args.model == 'e1':
        return DaftAwareTransformerReceiver(
            N=int(args.n_total), d_model=int(args.d_model),
            nhead=int(args.nhead), num_layers=int(args.num_layers),
            dim_ff=int(args.dim_ff)).to(device)
    if args.model == 'e2':
        return OtfsModularReceiver(
            N=int(args.n_total),
            l_max=int(sys_obj.l_max_cap),
            k_max=int(sys_obj.k_max_cap),
            base_ch=int(args.base_ch),
            use_threshold=bool(args.use_threshold),
            c1=float(sys_obj.c1), c2=float(sys_obj.c2),
            cdtype=cdtype).to(device)
    if args.model == 'e3':
        return AutoencoderJointTxRx(
            N=int(args.n_total),
            l_max=int(sys_obj.l_max_cap),
            k_max=int(sys_obj.k_max_cap),
            base_ch=int(args.base_ch),
            rho=float(sys_obj.rho),
            use_threshold=bool(args.use_threshold),
            c1=float(sys_obj.c1), c2=float(sys_obj.c2),
            cdtype=cdtype).to(device)
    if args.model == 'pathA':
        rho = float(sys_obj.rho)
        pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
        return HybridOMPRefiner(
            N=int(args.n_total),
            l_max=int(sys_obj.l_max_cap),
            k_max=int(sys_obj.k_max_cap),
            x_pilot=pilot_scaled,
            c1=float(sys_obj.c1), c2=float(sys_obj.c2),
            hidden=int(args.path_a_hidden),
            cdtype=cdtype).to(device)
    if args.model == 'pathB':
        rho = float(sys_obj.rho)
        pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
        return TwoHeadCENet(
            N=int(args.n_total),
            l_max=int(sys_obj.l_max_cap),
            k_max=int(sys_obj.k_max_cap),
            x_pilot=pilot_scaled,
            c1=float(sys_obj.c1), c2=float(sys_obj.c2),
            hidden=int(args.path_a_hidden),
            cdtype=cdtype).to(device)
    if args.model == 'pathF':
        rho = float(sys_obj.rho)
        pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
        return UnrolledOMPNet(
            N=int(args.n_total),
            l_max=int(sys_obj.l_max_cap),
            k_max=int(sys_obj.k_max_cap),
            x_pilot=pilot_scaled,
            c1=float(sys_obj.c1), c2=float(sys_obj.c2),
            K=int(args.path_f_iters),
            hidden=int(args.path_a_hidden),
            untied=bool(args.path_f_untied),
            use_attention=bool(args.path_f_attention),
            attn_heads=int(args.path_f_attn_heads),
            use_softsort_topk=bool(args.path_f_softsort),
            softsort_k=int(args.softsort_k),
            cdtype=cdtype).to(device)
    raise ValueError(f'unknown model {args.model}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model',
                    choices=['e0', 'e1', 'e2', 'e3', 'pathA', 'pathB', 'pathF'],
                    required=True)
    ap.add_argument('--path-a-hidden', type=int, default=64,
                    help='Path A/B/F: MLP refiner hidden width.')
    ap.add_argument('--path-f-iters', type=int, default=10,
                    help='Path F: number of unrolled OMP-like iterations.')
    ap.add_argument('--path-f-untied', action='store_true',
                    help='Path F: per-iter MLP (untied) vs shared MLP across K.')
    ap.add_argument('--path-f-attention', action='store_true',
                    help='Path J: enable self-attention over DD bins between '
                         'encoder MLP and decoder linear (cross-bin interaction).')
    ap.add_argument('--path-f-attn-heads', type=int, default=4,
                    help='Path J: number of attention heads (default 4).')
    ap.add_argument('--path-f-softsort', action='store_true',
                    help='Path H: enable softsort-relaxed top-K support '
                         'proposal at training, hard top-K at inference. '
                         'Structurally enforces sparsity instead of relying '
                         'on MLP to output ≈0 at inactive bins.')
    ap.add_argument('--softsort-k', type=int, default=10,
                    help='Path H: number of bins selected per iter (K_top). '
                         'Default 10 (= P_paths). Each iter applies top-K '
                         'mask to delta, so g_dd is structurally K-sparse.')
    ap.add_argument('--softsort-tau-init', type=float, default=1.0,
                    help='Path H: initial sigmoid temperature for soft top-K. '
                         'Higher → softer mask. Annealed linearly to tau_final.')
    ap.add_argument('--softsort-tau-final', type=float, default=0.05,
                    help='Path H: final sigmoid temperature at iter=iters. '
                         'Lower → harder mask. Anneal: 1.0 → 0.05 default.')
    ap.add_argument('--n-total', type=int, default=1024)
    ap.add_argument('--fs-factor', type=float, default=4.0)
    ap.add_argument('--v-mean', type=float, default=2.0)
    ap.add_argument('--p-paths', type=int, default=8)
    ap.add_argument('--tau-spread', type=float, default=0.010)
    ap.add_argument('--snr-list', type=int, nargs='+', default=[20])
    # E0/E1 hyperparams
    ap.add_argument('--d-model', type=int, default=128)
    ap.add_argument('--nhead', type=int, default=4)
    ap.add_argument('--num-layers', type=int, default=4)
    ap.add_argument('--dim-ff', type=int, default=512)
    # E2/E3 hyperparams
    ap.add_argument('--base-ch', type=int, default=32)
    ap.add_argument('--use-threshold', action='store_true',
                    help='E2/E3: enable ThresholdNet for SP pilot/data magnitude '
                         'separation (OTFS-SP paper-style).')
    # Training
    ap.add_argument('--iters', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=8)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--warmup', type=int, default=200)
    ap.add_argument('--lr-min', type=float, default=1e-6)
    ap.add_argument('--lam-bce', type=float, default=1.0)
    ap.add_argument('--lam-sym', type=float, default=0.5)
    ap.add_argument('--lam-h-nmse', type=float, default=0.0,
                    help='Weight on channel-NMSE supervised by H_true. '
                         '>0 enables E2/E3 OTFS-paper-style supervised CE '
                         'pretraining + joint training. Recommended 1.0 for '
                         'phase 1 (CE-only pretrain), 0.1 for phase 2.')
    ap.add_argument('--pretrain-iters', type=int, default=0,
                    help='If > 0, run NMSE-only pretraining for this many iters '
                         '(lam_bce=lam_sym=0, lam_h_nmse=1) before joint phase.')
    ap.add_argument('--lam-gdd-mse', type=float, default=0.0,
                    help='Weight on MSE(g_dd_pred, g_dd_omp) — supervised '
                         'distillation from classical OMP output as warm-start '
                         'signal. >0 enables positive-control "warm-start unlocks "'
                         '"E2E learning?" test.')
    # Path G: deep supervision + EMA
    ap.add_argument('--deep-supervision', action='store_true',
                    help='Path G: enable per-iter NMSE-on-H_true supervision '
                         'across all unrolled iterations (Path F only). '
                         'Smooths credit assignment in unrolled net.')
    ap.add_argument('--ds-weight', type=float, default=0.5,
                    help='Overall weight on deep-supervision NMSE loss '
                         'added to total loss when --deep-supervision is set.')
    ap.add_argument('--ds-decay', type=float, default=1.0,
                    help='Geometric weight decay across iters: '
                         'w_k = decay^(K-1-k). 1.0=uniform, <1 emphasises late '
                         'iters, >1 emphasises early iters.')
    ap.add_argument('--ds-last-k', type=int, default=0,
                    help='G3: if >0, only apply DS to the LAST `ds_last_k` '
                         'unrolled iterations (e.g. 3 → only k=K-3..K-1). '
                         '0 = supervise all iters. Mitigates noise from early '
                         'iters where g_dd^(k) ≈ 0 and NMSE^(k) ≈ 1 constant.')
    ap.add_argument('--ema-decay', type=float, default=0.0,
                    help='Path G: EMA decay for SWA-style weight averaging. '
                         '0=disabled, recommended 0.999 to stabilise late-iter '
                         'oscillation. Eval uses EMA shadow weights.')
    ap.add_argument('--bce-scale', type=float, default=8.0)
    ap.add_argument('--grad-clip', type=float, default=5.0)
    ap.add_argument('--eval-every', type=int, default=200)
    ap.add_argument('--eval-frames', type=int, default=30)
    ap.add_argument('--print-every', type=int, default=10,
                    help='Print iter log every N iters.')
    ap.add_argument('--skip-init-eval', action='store_true',
                    help='Skip the eval at iter=0 (which calls slow NumPy '
                         'classical baseline). Useful for fast iteration.')
    ap.add_argument('--skip-classical-baseline', action='store_true',
                    help='Skip NumPy classical OMP+MP baseline in eval (it is '
                         'slow at N=1024 iter=10 BP). Only report learned BER.')
    ap.add_argument('--cdtype', choices=['complex64', 'complex128'],
                    default='complex64')
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--device', default='auto')
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

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
    device = torch.device('cuda' if (args.device == 'auto'
                                       and torch.cuda.is_available())
                          else args.device)

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    model = build_model(args, sys_obj, cdtype, rdtype, device)
    nparams = count_params(model)
    print(f'[train_path_e] model={args.model}  params={nparams}  '
          f'device={device}  N={args.n_total}  c1={sys_obj.c1:.6g} '
          f'c2={sys_obj.c2:.3e}', flush=True)

    # Path G: EMA wrapper (used for eval). 0.0 → disabled.
    ema_model = None
    if float(args.ema_decay) > 0.0:
        ema_decay = float(args.ema_decay)
        ema_avg_fn = (lambda avg, p, n: ema_decay * avg + (1 - ema_decay) * p)
        ema_model = torch.optim.swa_utils.AveragedModel(
            model, avg_fn=ema_avg_fn)
        # Also average buffers (Phi, col_norm_sq) so EMA model has correct state
        ema_model.use_buffers = True
        print(f'[train_path_e] EMA enabled  decay={ema_decay}', flush=True)
    if bool(args.deep_supervision):
        print(f'[train_path_e] Deep supervision enabled  '
              f'ds_weight={args.ds_weight}  ds_decay={args.ds_decay}',
              flush=True)

    optim = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(args.lr), weight_decay=1e-5)
    # Cosine LR with linear warmup
    def lr_at(step):
        if step < args.warmup:
            return float(args.lr) * (step + 1) / max(args.warmup, 1)
        # Cosine from lr → lr_min over (iters - warmup) steps
        prog = (step - args.warmup) / max(args.iters - args.warmup, 1)
        prog = min(max(prog, 0.0), 1.0)
        cosine = 0.5 * (1.0 + math.cos(math.pi * prog))
        return float(args.lr_min) + (float(args.lr) - float(args.lr_min)) * cosine

    rng_train = np.random.default_rng(args.seed + 100)
    rng_eval = np.random.default_rng(args.seed + 9999)
    log: List[Dict] = []
    best_score = float('inf')

    t_start = time.time()
    for it in range(int(args.iters)):
        cur_lr = lr_at(it)
        for pg in optim.param_groups:
            pg['lr'] = cur_lr

        model.train()
        loss_acc = torch.zeros((), device=device, dtype=torch.float32)
        ber_acc = []
        # Path H: linearly anneal softsort temperature τ over training.
        if bool(args.path_f_softsort):
            prog = it / max(int(args.iters) - 1, 1)
            prog = min(max(prog, 0.0), 1.0)
            cur_softsort_tau = (float(args.softsort_tau_init) +
                                (float(args.softsort_tau_final) -
                                 float(args.softsort_tau_init)) * prog)
        else:
            cur_softsort_tau = 1.0
        fwd_kwargs = dict(c1=float(sys_obj.c1), c2=float(sys_obj.c2))
        if args.model == 'pathF' and bool(args.path_f_softsort):
            fwd_kwargs['softsort_tau'] = cur_softsort_tau
        for _ in range(int(args.batch)):
            snr = int(args.snr_list[rng_train.integers(0, len(args.snr_list))])
            want_omp = float(args.lam_gdd_mse) > 0
            frame = _sample_frame(sys_obj, snr, rng_train, cdtype, device, args,
                                   want_omp_warmstart=want_omp)
            out = model(frame['y_daft'], frame['x_pilot'], frame['sigma2'],
                        frame['const'], **fwd_kwargs)
            x_hat = out['x_soft']
            # Pretrain phase: only NMSE-on-H_true; main phase: BCE+MSE (+ NMSE)
            in_pretrain = it < int(args.pretrain_iters)
            if in_pretrain:
                lam_bce = 0.0
                lam_sym = 0.0
                lam_h_nmse = 1.0
            else:
                lam_bce = float(args.lam_bce)
                lam_sym = float(args.lam_sym)
                lam_h_nmse = float(args.lam_h_nmse)
            bce = _bce_loss(x_hat, frame['bits_true'], frame['P_d'],
                             scale=args.bce_scale) if lam_bce > 0 else \
                  torch.zeros((), dtype=torch.float64, device=device)
            mse = _sym_mse(x_hat, frame['data_qam'], frame['P_d']) if lam_sym > 0 else \
                  torch.zeros((), dtype=torch.float64, device=device)
            if lam_h_nmse > 0 and out.get('H_est') is not None:
                nmse_h = _channel_nmse(out['H_est'], frame['H_true'], frame['x_sp'])
            else:
                nmse_h = torch.zeros((), dtype=torch.float64, device=device)
            # Path G: deep-supervision NMSE on per-iter g_dd_history.
            if bool(args.deep_supervision) and out.get('g_dd_history') is not None \
                    and hasattr(model, 'h_recon'):
                ds_nmse = _deep_supervision_nmse(
                    out['g_dd_history'], model.h_recon,
                    frame['H_true'], frame['x_sp'],
                    decay=float(args.ds_decay),
                    last_k=int(args.ds_last_k))
            else:
                ds_nmse = torch.zeros((), dtype=torch.float64, device=device)
            # g_dd warm-start MSE (positive control) — magnitude-weighted to
            # avoid the "predict zero" degenerate minimum on sparse targets.
            # Bins with |target| above threshold get 100× more weight, so
            # the 10/515 active bins dominate the gradient instead of being
            # drowned out by 505 "should be zero" bins.
            if float(args.lam_gdd_mse) > 0 and frame.get('h_omp_dd') is not None \
                    and out.get('g_dd') is not None:
                tgt = torch.tensor(frame['h_omp_dd'], dtype=out['g_dd'].dtype,
                                    device=out['g_dd'].device)
                diff = out['g_dd'] - tgt
                err_sq = diff.real.pow(2) + diff.imag.pow(2)
                # Weight: active bins (|tgt| > 1e-3) get 100×, dead bins 1×
                active_mask = (tgt.abs() > 1e-3).to(err_sq.dtype)
                weight = 1.0 + 100.0 * active_mask
                gdd_mse = ((err_sq * weight).sum() / weight.sum()).double()
            else:
                gdd_mse = torch.zeros((), dtype=torch.float64, device=device)
            ds_lam = float(args.ds_weight) if bool(args.deep_supervision) else 0.0
            l = (lam_bce * bce + lam_sym * mse + lam_h_nmse * nmse_h
                 + float(args.lam_gdd_mse) * gdd_mse
                 + ds_lam * ds_nmse).float()
            loss_acc = loss_acc + l
            ber_acc.append(_ber_one_frame(x_hat.detach().cpu().numpy(),
                                           frame['bits_true'], frame['P_d'],
                                           frame['N']))
        loss_acc = loss_acc / args.batch
        optim.zero_grad(set_to_none=True)
        loss_acc.backward()
        torch.nn.utils.clip_grad_norm_(
            [p for p in model.parameters() if p.requires_grad],
            max_norm=float(args.grad_clip))
        optim.step()
        # Path G: EMA update — only after the LR warmup so shadow weights
        # don't get poisoned by the initial random-ish optimisation phase.
        if ema_model is not None and it >= int(args.warmup):
            ema_model.update_parameters(model)

        if (it + 1) % max(1, int(args.print_every)) == 0:
            elapsed = time.time() - t_start
            print(f'[it={it+1:5d}/{args.iters}] lr={cur_lr:.2e}  '
                  f'loss={float(loss_acc):.4f}  ber={np.mean(ber_acc):.4e}  '
                  f'[{elapsed:.0f}s]', flush=True)

        do_eval = (it + 1) % args.eval_every == 0
        if not args.skip_init_eval and it == 0:
            do_eval = True
        if do_eval:
            # Eval pass: sample frames + (optional) classical baseline.
            # Path G: if EMA enabled and past warmup, eval with EMA shadow
            # weights; otherwise eval the live model.
            use_ema = (ema_model is not None and it >= int(args.warmup))
            eval_model = ema_model if use_ema else model
            eval_model.eval()
            eval_ber_e = []
            eval_ber_c = []
            with torch.no_grad():
                for _ in range(args.eval_frames):
                    snr = int(args.snr_list[rng_eval.integers(0, len(args.snr_list))])
                    frame = _sample_frame(sys_obj, snr, rng_eval, cdtype, device, args)
                    # Eval uses hard top-K (model.eval() inside forward branch);
                    # softsort_tau ignored in eval mode but pass through fwd_kwargs
                    # for symmetric call semantics.
                    out = eval_model(frame['y_daft'], frame['x_pilot'], frame['sigma2'],
                                frame['const'], **fwd_kwargs)
                    eval_ber_e.append(_ber_one_frame(
                        out['x_soft'].cpu().numpy(), frame['bits_true'],
                        frame['P_d'], frame['N']))
                    if not args.skip_classical_baseline:
                        eval_ber_c.append(_classical_baseline_ber(
                            frame, sys_obj, n_outer_iter=10))
                    else:
                        eval_ber_c.append(float('nan'))
            mean_e = float(np.mean(eval_ber_e))
            mean_c = float(np.nanmean(eval_ber_c)) if not args.skip_classical_baseline else float('nan')
            log.append({'iter': it + 1, 'lr': cur_lr,
                         'loss': float(loss_acc), 'train_ber': float(np.mean(ber_acc)),
                         'eval_ber_learned': mean_e, 'eval_ber_classical': mean_c,
                         'rel_delta_pct': (mean_e - mean_c) / max(mean_c, 1e-30) * 100,
                         'elapsed_s': time.time() - t_start})
            print(f'  >> EVAL it={it+1}  learned_ber={mean_e:.4e}  '
                  f'classical_ber={mean_c:.4e}  ΔBER={(mean_e - mean_c)/max(mean_c, 1e-30)*100:+.2f}%%',
                  flush=True)
            if mean_e < best_score:
                best_score = mean_e
                ckpt = {'state_dict': model.state_dict(),
                         'iter': it + 1, 'eval_ber': mean_e,
                         'eval_used_ema': bool(use_ema),
                         'classical_ber': mean_c, 'args': vars(args)}
                if ema_model is not None:
                    ckpt['ema_state_dict'] = ema_model.state_dict()
                torch.save(ckpt, out_dir / f'best_{args.model}.pt')

    # Save final log
    with open(out_dir / 'train_log.json', 'w') as f:
        json.dump({'_argv': sys.argv, '_config': vars(args),
                    'best_eval_ber': best_score, 'log': log}, f, indent=2)
    print(f'[done] best_eval_ber={best_score:.4e}  log -> {out_dir}/train_log.json',
          flush=True)


if __name__ == '__main__':
    main()
