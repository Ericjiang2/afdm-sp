"""
train_learnable_chirp_smoke.py — W8 Direction-D Round-0 Option A smoke.

Train **scalar c1, c2** end-to-end via BCE on bits; baseline = Bemani-analytic
c1/c2 (no learning). After training, evaluate on held-out frames and report:
  - learned (c1, c2) and their relative deviation from Bemani init
  - paired BER (learned chirp vs Bemani chirp) with McNemar p-value
  - decision: kill / continue per tcom_plan/W8D_learnable_daft_design.md gates

Reuses helpers from train_classical_joint_unrolled.py for data sampling and
loss definitions; the only new piece is the LearnableChirpDAFTReceiver wrap.

Usage::

    conda activate AFDM && \\
      python afdm_sp_joint_unrolled/train_learnable_chirp_smoke.py \\
        --n-total 512 --snr 20 --train-frames 1000 --eval-frames 200 \\
        --epochs 50 --batch-size 8 --lr-chirp 1e-4 \\
        --out-dir outputs_w8d_round0_smoke
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time

import numpy as np
import torch
import torch.nn.functional as F

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
    _bits_of_symbol,
    _ber,
    _make_system_variable_N,
)
from afdm_sp_joint_unrolled.train_classical_joint_unrolled import (  # noqa: E402
    _sample_frame,
    _one_forward,
    _ber_from_xsoft,
    _classical_baseline_ber,
    _bit_bce_loss,
)


def _mcnemar_paired(b_a: np.ndarray, b_b: np.ndarray):
    """McNemar test for two paired bit-error sequences (b_a, b_b in {0,1}^M).
    Returns (n01, n10, p_two_sided, rel_change_pct).
    n01 = b_a correct, b_b wrong; n10 = b_a wrong, b_b correct.
    rel_change = (errs_b - errs_a) / errs_a · 100 (negative ⇒ b improved).
    Continuity correction."""
    err_a = (b_a != 0).astype(int)
    err_b = (b_b != 0).astype(int)
    n01 = int(np.sum((err_a == 0) & (err_b == 1)))
    n10 = int(np.sum((err_a == 1) & (err_b == 0)))
    if n01 + n10 == 0:
        p = 1.0
    else:
        chi2 = (abs(n01 - n10) - 1.0) ** 2 / (n01 + n10)
        # chi2 with 1 dof; survival = exp(-chi2/2) * (1 + ...) — use scipy if avail.
        try:
            from scipy.stats import chi2 as _chi2
            p = float(1.0 - _chi2.cdf(chi2, df=1))
        except ImportError:
            p = float(math.exp(-chi2 / 2.0))
    errs_a = int(err_a.sum())
    errs_b = int(err_b.sum())
    rel = (errs_b - errs_a) / max(errs_a, 1) * 100.0
    return n01, n10, p, rel, errs_a, errs_b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n-total', type=int, default=512)
    ap.add_argument('--p-paths', type=int, default=10)
    ap.add_argument('--snr', type=int, default=20)
    ap.add_argument('--train-frames', type=int, default=1000)
    ap.add_argument('--eval-frames', type=int, default=200)
    ap.add_argument('--epochs', type=int, default=50)
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--lr-chirp', type=float, default=1e-4,
                    help='Base lr; if --per-param-lr-scale > 0, the actual per-param '
                         'lr is c_init * scale for each chirp scalar.')
    ap.add_argument('--per-param-lr-scale', type=float, default=0.0,
                    help='If > 0, set lr_c_i = c_i_init * scale (init-relative lr). '
                         'Default 0 means use a single --lr-chirp for both params. '
                         'Recommended: 1e-3 to 1e-5 for relative-magnitude SGD.')
    ap.add_argument('--bce-scale', type=float, default=8.0)
    ap.add_argument('--nmse-weight', type=float, default=0.5,
                    help='Weight on auxiliary H_est NMSE loss; 0 = BCE only.')
    ap.add_argument('--n-outer-iter', type=int, default=5)
    ap.add_argument('--mp-mode', type=str, default='pic', choices=('pic', 'bp'))
    ap.add_argument('--pic-damp', type=float, default=0.5)
    ap.add_argument('--constrain', type=str, default=None,
                    choices=(None, 'relative_tanh'))
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--device', type=str, default='auto')
    ap.add_argument('--cdtype', type=str, default='complex128',
                    choices=('complex128', 'complex64'))
    ap.add_argument('--out-dir', type=str, required=True)
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    cdtype = torch.complex128 if args.cdtype == 'complex128' else torch.complex64
    rdtype = torch.float64 if args.cdtype == 'complex128' else torch.float32

    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    c1_init = float(sys_obj.c1)
    c2_init = float(sys_obj.c2)
    print(f"[smoke] N={args.n_total}  Bemani c1_init={c1_init:.6g}  "
          f"c2_init={c2_init:.6e}  device={device}", flush=True)

    cfg = ClassicalJointConfig(
        N=int(sys_obj.N_total),
        l_max=int(sys_obj.l_max_cap),
        k_max=int(sys_obj.k_max_cap),
        c1=c1_init, c2=c2_init,
        n_outer_iter=int(args.n_outer_iter),
        pic_iter=20, pic_damp=float(args.pic_damp),
        mp_mode=str(args.mp_mode),
        rho=float(sys_obj.rho),
        n_paths=int(sys_obj.P_paths),
        dtype=cdtype, rdtype=rdtype,
        early_stop=False,                 # OFF for training
    )
    base = ClassicalJointUnrolled(cfg, learnable_heads=(), use_soft_decisions=True)
    module = LearnableChirpDAFTReceiver(base, c1_init=c1_init, c2_init=c2_init,
                                         constrain=args.constrain).to(device)
    print(f"[smoke] trainable params: {sum(p.numel() for p in module.parameters() if p.requires_grad)} "
          f"(should be 2 for Option A)", flush=True)

    if args.per_param_lr_scale > 0:
        lr_c1 = float(args.per_param_lr_scale) * abs(c1_init)
        lr_c2 = float(args.per_param_lr_scale) * abs(c2_init)
        print(f"[smoke] per-param lr: lr_c1={lr_c1:.3e}  lr_c2={lr_c2:.3e} "
              f"(scale={args.per_param_lr_scale})", flush=True)
        optim = torch.optim.Adam([
            {'params': [module.c1_raw], 'lr': lr_c1},
            {'params': [module.c2_raw], 'lr': lr_c2},
        ])
    else:
        optim = torch.optim.Adam([module.c1_raw, module.c2_raw], lr=float(args.lr_chirp))
    rng_train = np.random.default_rng(args.seed)
    rng_eval = np.random.default_rng(args.seed + 99999)

    # Pre-generate eval frames so train/eval share the same channel realisations
    # across the learned-vs-classical comparison.
    eval_frames = []
    eval_seeds = []
    for _ in range(args.eval_frames):
        # Use a deterministic seed for each frame so classical and learned see
        # the SAME channel+noise+data realisation.
        eval_seeds.append(int(rng_eval.integers(0, 2 ** 31)))
    for s in eval_seeds:
        np.random.seed(s)
        rng = np.random.default_rng(s)
        eval_frames.append(_sample_frame(sys_obj, args.snr, rng))

    train_log = []
    iters_per_epoch = max(1, args.train_frames // args.batch_size)
    print(f"[smoke] training: {args.epochs} epochs × {iters_per_epoch} iters/epoch "
          f"× batch {args.batch_size}  → ~{args.epochs * iters_per_epoch * args.batch_size} "
          f"frames seen total", flush=True)

    t_start = time.time()
    for epoch in range(args.epochs):
        module.train()
        loss_acc, bce_acc, nmse_acc, n_acc = 0.0, 0.0, 0.0, 0
        for it in range(iters_per_epoch):
            optim.zero_grad(set_to_none=True)
            loss = torch.zeros((), dtype=rdtype, device=device, requires_grad=False)
            for _ in range(args.batch_size):
                seed_fi = int(rng_train.integers(0, 2 ** 31))
                np.random.seed(seed_fi)
                rng = np.random.default_rng(seed_fi)
                frame = _sample_frame(sys_obj, args.snr, rng)
                out = _one_forward(module, frame, sys_obj,
                                    cdtype=cdtype, rdtype=rdtype, device=device)
                # BCE on bits via soft x_soft (use_soft_decisions=True ⇒ grad flows).
                P_d_t = torch.tensor(frame['P_d'], dtype=rdtype, device=device)
                x_norm = out['x_soft'] / P_d_t.sqrt()
                bits_true_t = torch.tensor(frame['bits_true'], dtype=rdtype, device=device)
                bce = _bit_bce_loss(x_norm, bits_true_t, scale=args.bce_scale)
                if args.nmse_weight > 0:
                    H_true_t = torch.tensor(frame['H_true'], dtype=cdtype, device=device)
                    x_true_t = torch.tensor(frame['x_sp'], dtype=cdtype, device=device)
                    nmse = ((out['H_est'] - H_true_t) @ x_true_t)
                    den = H_true_t @ x_true_t
                    nmse = (nmse.real.pow(2) + nmse.imag.pow(2)).sum() / \
                           (den.real.pow(2) + den.imag.pow(2)).sum().clamp_min(1e-30)
                    nmse_acc += float(nmse.detach().cpu())
                else:
                    nmse = torch.zeros((), dtype=rdtype, device=device)
                frame_loss = bce + args.nmse_weight * nmse.to(rdtype)
                # Scale by batch_size; accumulate gradient
                (frame_loss / args.batch_size).backward()
                loss_acc += float(frame_loss.detach().cpu()) / args.batch_size
                bce_acc += float(bce.detach().cpu()) / args.batch_size
                n_acc += 1
            # Clip gradient for chirp params — tiny lr but chirp phase is
            # highly sensitive to c1 (l² scaling can amplify gradients).
            torch.nn.utils.clip_grad_norm_([module.c1_raw, module.c2_raw], max_norm=1e-3)
            optim.step()
        snap = module.current_chirp()
        elapsed = time.time() - t_start
        print(f"[ep {epoch+1:3d}/{args.epochs}] loss={loss_acc/iters_per_epoch:.4e}  "
              f"bce={bce_acc/iters_per_epoch:.4e}  nmse={nmse_acc/max(n_acc,1):.4e}  "
              f"c1={snap['c1']:.6g} (Δ={snap['c1_rel_dev']*100:+.3f}%)  "
              f"c2={snap['c2']:.6e} (Δ={snap['c2_rel_dev']*100:+.3f}%)  "
              f"[{elapsed:.0f}s]", flush=True)
        train_log.append({
            'epoch': epoch + 1,
            'loss': loss_acc / iters_per_epoch,
            'bce': bce_acc / iters_per_epoch,
            'nmse': nmse_acc / max(n_acc, 1),
            'c1': snap['c1'],
            'c2': snap['c2'],
            'c1_rel_dev': snap['c1_rel_dev'],
            'c2_rel_dev': snap['c2_rel_dev'],
        })

    # ============== Eval: paired BER (learned chirp vs Bemani chirp) =========
    print('[eval] running paired BER on held-out frames ...', flush=True)
    module.eval()
    bits_pred_learned = []
    bits_pred_classical = []
    bits_true_all = []
    for fi, frame in enumerate(eval_frames):
        # Learned chirp path
        with torch.no_grad():
            out = _one_forward(module, frame, sys_obj, cdtype=cdtype,
                               rdtype=rdtype, device=device)
        x_norm = out['x_soft'].cpu().numpy() / np.sqrt(frame['P_d'])
        bits_learned = _bits_of_symbol(x_norm, frame['N'])
        # Classical Bemani path (uses sys_obj.c1, sys_obj.c2 — i.e. init values)
        ber_classical_frame, _ = _classical_baseline_ber(
            frame, sys_obj, mp_mode=args.mp_mode,
            pic_damp=args.pic_damp, n_outer_iter=int(args.n_outer_iter))
        # For McNemar we need per-bit predictions for both paths. Easier: recompute classical bits.
        # _classical_baseline_ber returns BER, not bits; redo here.
        from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
        const_data = np.sqrt(frame['P_d']) * QPSK
        sparsity = max(frame['p_actual'], int(sys_obj.P_paths))
        x_cls, _ = joint_omp_mp_iterative(
            frame['y_daft'], frame['pilot_scaled'], frame['N'],
            c1_init, c2_init, sys_obj.l_max_cap, sys_obj.k_max_cap,
            frame['sigma2'], const_data,
            n_paths=sparsity, n_outer_iter=int(args.n_outer_iter),
            rho=frame['rho'], pic_iter=20, pic_damp=float(args.pic_damp),
            mp_mode=str(args.mp_mode), gamma_h=0.7, gamma_x=0.6,
            lambda_ls_factor=1e-3, tau_h_factor=0.01, tau_h_sigma_factor=0.1,
            k_leak=2, update_sigma2=True, phase_convention='python',
        )
        bits_classical = _bits_of_symbol(x_cls / np.sqrt(frame['P_d']), frame['N'])
        bits_pred_learned.append((bits_learned != frame['bits_true']).astype(int))
        bits_pred_classical.append((bits_classical != frame['bits_true']).astype(int))
        bits_true_all.append(frame['bits_true'])
        if (fi + 1) % 25 == 0:
            print(f'  ... frame {fi+1}/{args.eval_frames}', flush=True)

    bits_err_learned = np.concatenate(bits_pred_learned)
    bits_err_classical = np.concatenate(bits_pred_classical)

    n01, n10, p, rel, errs_cls, errs_lrn = _mcnemar_paired(
        bits_err_classical, bits_err_learned)
    ber_cls = errs_cls / bits_err_classical.size
    ber_lrn = errs_lrn / bits_err_learned.size
    snap = module.current_chirp()

    summary = {
        '_argv': sys.argv,
        '_config': vars(args),
        'c1_init': c1_init,
        'c2_init': c2_init,
        'c1_learned': snap['c1'],
        'c2_learned': snap['c2'],
        'c1_rel_dev': snap['c1_rel_dev'],
        'c2_rel_dev': snap['c2_rel_dev'],
        'ber_classical_bemani': ber_cls,
        'ber_learned_chirp': ber_lrn,
        'errs_classical': errs_cls,
        'errs_learned': errs_lrn,
        'rel_change_pct': rel,
        'mcnemar_n01': n01,
        'mcnemar_n10': n10,
        'mcnemar_p': p,
        'train_log': train_log,
    }
    with open(out_dir / 'results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    torch.save({'c1_raw': module.c1_raw.detach().cpu(),
                'c2_raw': module.c2_raw.detach().cpu(),
                'c1_init': c1_init, 'c2_init': c2_init,
                'constrain': args.constrain},
               out_dir / 'chirp_params.pt')

    print('=' * 70)
    print(f"Round-0 Option A smoke RESULT ({args.eval_frames} frames @ SNR={args.snr}):")
    print(f"  c1: init={c1_init:.6g} → learned={snap['c1']:.6g}  "
          f"|Δ|/c1_init = {abs(snap['c1_rel_dev'])*100:.3f}%")
    print(f"  c2: init={c2_init:.6e} → learned={snap['c2']:.6e}  "
          f"|Δ|/c2_init = {abs(snap['c2_rel_dev'])*100:.3f}%")
    print(f"  BER:  classical(Bemani)={ber_cls:.4e}  learned={ber_lrn:.4e}  "
          f"Δ={rel:+.2f}%  McNemar p={p:.3e}  (n01={n01}, n10={n10})")
    # Decision boundaries from W8D design doc
    delta_c1 = abs(snap['c1_rel_dev']) * 100
    if delta_c1 < 0.1 and abs(rel) < 5:
        verdict = 'KILL — Bemani c1* robust to our regime; write §IV-H negative result'
    elif delta_c1 >= 0.5 and rel <= -5:
        verdict = 'CONTINUE — promote to full eval + Round 1 (A\')'
    elif rel > 0:
        verdict = 'KILL — learned chirp WORSE than Bemani; do not pursue'
    else:
        verdict = 'AMBIGUOUS — run constrained-c1 ablation to disambiguate'
    print(f"  Verdict: {verdict}")
    print('=' * 70)


if __name__ == '__main__':
    main()
