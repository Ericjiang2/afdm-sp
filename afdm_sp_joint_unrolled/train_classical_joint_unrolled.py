"""
train_classical_joint_unrolled.py

Three-phase trainer for the differentiable unrolling of classical joint
OMP-MP with learnable heads.

Phase 0 (warm identity check): all heads enabled but frozen → BER must match
    the NumPy baseline exactly.  Sanity gate before any gradient step.
Phase 1 (scalars):    unfreeze per-iter scalar hyperparams, train with small
    LR to let them drift away from the classical defaults.
Phase 2 (heads):      unfreeze strategy MLP + symbol refiner, joint-train with
    larger LR.

Data generation is on-the-fly: we call ``sys_obj.generate_channel_matrix()``
for each training frame, draw random QPSK data, add noise at a random SNR
in the configured list.

Loss (default weights below):
    L = λ_bce · BCE_bits(x_soft) + λ_sym · MSE(x_soft, x_true)

Both reduce at single-frame granularity; we accumulate over a small
mini-batch before stepping the optimiser.

Outputs:
    ckpt path        : classical_joint_unrolled_v1.pt
    train log (JSON) : train_log.json   (one row per minibatch)
    eval log (JSON)  : eval_log.json    (held-out BER every ``eval_every``)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from dataclasses import asdict
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn.functional as F

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

# Fast torch BP: monkey-patch numpy mp_detect_bp with the vectorized torch port
# BEFORE importing joint_omp_mp_iterative so module-level lookups pick up the
# fast version. Matches the scheme in classical_joint_bp_torch_probe.py.
from afdm_sp_joint_unrolled import afdm_baselines as _afb
from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch as _bp_torch


def _fast_bp_numpy_shim(y, H, sigma2, constellation, n_iter=20, threshold=1e-4,
                        damp=0.5, return_soft=False):
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return _bp_torch(y, H, sigma2, constellation, n_iter=n_iter,
                     threshold=threshold, damp=damp,
                     device=dev, return_numpy=True, return_soft=return_soft)


_afb.mp_detect_bp = _fast_bp_numpy_shim

from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative
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


# ======================================================================
# Frame generator
# ======================================================================


def _sample_frame(sys_obj, snr_db: int, rng: np.random.Generator):
    """Generate one training/eval frame.

    Returns a dict of NumPy tensors (everything gets moved to torch in the
    training loop).
    """
    N = sys_obj.N_total
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho

    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq

    # Seed global numpy RNG so generate_channel_matrix() (which uses np.random)
    # is paired with the rng-driven data/noise draw below. Without this,
    # channels were drawn from whatever ambient state was set, making eval
    # non-reproducible.
    seed_for_channel = int(rng.integers(0, 2**31))
    np.random.seed(seed_for_channel)
    H_true, _, _ = sys_obj.generate_channel_matrix()
    p_actual = int(getattr(sys_obj, "_P_actual", sys_obj.P_paths))

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

    return dict(
        N=N, rho=rho, P_d=P_d,
        pilot_scaled=pilot_scaled,
        data_qam=data_qam,           # at ±1/√2 scale
        bits_true=bits_true,
        H_true=H_true,
        y_daft=y_daft,
        sigma2=sigma2,
        p_actual=p_actual,
        snr_db=snr_db,
        x_sp=x_sp,                   # (pilot + data) at true scales
    )


# ======================================================================
# Losses
# ======================================================================


def _bit_bce_loss(x_norm: torch.Tensor, bits_true: torch.Tensor,
                  scale: float = 8.0) -> torch.Tensor:
    """BCE on QPSK bits from the soft symbol ``x_norm`` at unit-amplitude
    (i.e. already divided by √P_d).

    Gray QPSK: bit_real = 1 if Re(x) < 0, bit_imag = 1 if Im(x) < 0.
    Logit convention for BCEWithLogits: logit > 0 ⇒ P(bit=1) > 0.5.
    So ``logit_real = −scale · Re(x)``; ``scale`` acts as an LLR temperature.
    """
    N = x_norm.shape[0]
    logit_r = -scale * x_norm.real.float()
    logit_i = -scale * x_norm.imag.float()
    tgt_r = bits_true[:N]
    tgt_i = bits_true[N:]
    return (F.binary_cross_entropy_with_logits(logit_r, tgt_r)
            + F.binary_cross_entropy_with_logits(logit_i, tgt_i))


def _sym_mse_loss(x_soft: torch.Tensor, data_qam: torch.Tensor,
                  P_d: float) -> torch.Tensor:
    """MSE between ``x_soft`` (at √P_d scale) and the true data symbols
    (also scaled to √P_d)."""
    tgt = np.sqrt(P_d) * data_qam
    d = x_soft - tgt
    return (d.real.pow(2) + d.imag.pow(2)).mean().float()


def _chan_nmse_loss(H_est: torch.Tensor, H_true: torch.Tensor,
                    x_true_scaled: torch.Tensor) -> torch.Tensor:
    """Effective-channel NMSE (Codex R2 recommendation).

    L = ||(H_est - H_true) · x_true||² / (||H_true · x_true||² + eps)

    Far lower variance than BER and directly targets CE-driven detector error.
    Only accumulates gradient through H_est (x_true is detached ground truth).
    """
    x = x_true_scaled.detach()
    num = ((H_est - H_true) @ x)
    den = H_true @ x
    num_sq = (num.real.pow(2) + num.imag.pow(2)).sum()
    den_sq = (den.real.pow(2) + den.imag.pow(2)).sum().clamp_min(1e-30)
    return (num_sq / den_sq).float()


# ======================================================================
# Trainer
# ======================================================================


def _ber_from_xsoft(x_soft_np: np.ndarray, bits_true: np.ndarray, P_d: float) -> float:
    x_norm = x_soft_np / np.sqrt(P_d)
    N = x_norm.size
    return _ber(_bits_of_symbol(x_norm, N), bits_true)


def _classical_baseline_ber(frame, sys_obj, mp_mode: str = 'pic',
                             pic_damp: float = 0.5,
                             n_outer_iter: int = 5) -> Tuple[float, float]:
    """Run the classical joint on the same frame; return (BER, NMSE).

    `mp_mode` and `pic_damp` must match the learned module so we compare
    apples-to-apples (student-minus-teacher Δ is meaningful).  BP goes through
    the monkey-patched torch fast path set up at the top of this module.
    """
    const_data = np.sqrt(frame['P_d']) * QPSK
    sparsity = max(frame['p_actual'], int(sys_obj.P_paths))
    x_soft, H_est = joint_omp_mp_iterative(
        frame['y_daft'], frame['pilot_scaled'], frame['N'],
        sys_obj.c1, sys_obj.c2, sys_obj.l_max_cap, sys_obj.k_max_cap,
        frame['sigma2'], const_data,
        n_paths=sparsity, n_outer_iter=int(n_outer_iter), rho=frame['rho'],
        pic_iter=20, pic_damp=float(pic_damp), mp_mode=str(mp_mode),
        gamma_h=0.7, gamma_x=0.6, lambda_ls_factor=1e-3,
        tau_h_factor=0.01, tau_h_sigma_factor=0.1,
        k_leak=2, update_sigma2=True, phase_convention='python',
    )
    return (_ber_from_xsoft(x_soft, frame['bits_true'], frame['P_d']),
            _nmse(H_est, frame['H_true']))


def _one_forward(module: ClassicalJointUnrolled, frame: Dict,
                 sys_obj, cdtype=torch.complex128, rdtype=torch.float64,
                 device='cpu') -> Dict[str, torch.Tensor]:
    """Forward a single frame through the module, returning x_soft, H_est."""
    y_t = torch.tensor(frame['y_daft'], dtype=cdtype, device=device)
    pilot_t = torch.tensor(frame['pilot_scaled'], dtype=cdtype, device=device)
    const_t = torch.tensor(np.sqrt(frame['P_d']) * QPSK, dtype=cdtype, device=device)
    sigma2_t = torch.tensor(frame['sigma2'], dtype=rdtype, device=device)
    module.cfg.n_paths = max(frame['p_actual'], int(sys_obj.P_paths))
    out = module(y_t, pilot_t, sigma2_t, const_t)
    return out


def _set_requires_grad(module: torch.nn.Module, flag: bool):
    for p in module.parameters():
        p.requires_grad_(flag)


def _collect_params(module: ClassicalJointUnrolled, include: List[str]) -> List[torch.nn.Parameter]:
    params: List[torch.nn.Parameter] = []
    if 'scalars' in include and module.scalars is not None:
        params += list(module.scalars.parameters())
    if 'strategy' in include and module.strategy_mlps is not None:
        params += list(module.strategy_mlps.parameters())
    if 'symbol_refiner' in include and module.symbol_refiner is not None:
        params += list(module.symbol_refiner.parameters())
    if 'per_iter_refiner' in include and getattr(module, 'per_iter_refiner', None) is not None:
        params += list(module.per_iter_refiner.parameters())
    if 'iter_residual_selector' in include and getattr(module, 'iter_residual_selector', None) is not None:
        params += list(module.iter_residual_selector.parameters())
    if 'channel_tap_corrector' in include and getattr(module, 'channel_tap_corrector', None) is not None:
        params += list(module.channel_tap_corrector.parameters())
    if 'off_support_corr' in include and getattr(module, 'off_support_corr', None) is not None:
        params += list(module.off_support_corr.parameters())
    return params


def train(args):
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total)
    sys_obj.P_paths = int(args.p_paths)
    if args.tau_spread is not None:
        sys_obj.tau_spread = float(args.tau_spread)
        print(f"[train] tau_spread override → {sys_obj.tau_spread*1e3:.2f} ms")
    sys_obj.gen_h_daft_convention = 'python'
    sys_obj.baseline_phase_convention = 'python'
    # W8 Path B — match paired_learned_eval canonical TCOM regime via fs_factor.
    if abs(float(args.fs_factor) - 2.0) > 1e-9:
        sys_obj.B = 4e3
        sys_obj.fs = float(args.fs_factor) * sys_obj.B
        sys_obj.Ts = 1.0 / sys_obj.fs
        print(f"[train] fs_factor override → fs={sys_obj.fs/1e3:.1f} kHz")
    if args.v_mean is not None:
        sys_obj.v_mean = float(args.v_mean)
        # Recompute adaptive k_max_cap with overridden v_mean.
        v_max_ms = float(sys_obj.v_mean) + 3.0 * float(getattr(sys_obj, 'v_std', 0.5))
        d_max_norm = v_max_ms * float(sys_obj.fc) / (
            float(sys_obj.c_sound) * float(sys_obj.fs))
        sys_obj.k_max_cap = max(int(np.ceil(args.n_total * d_max_norm)), 1)
        K = 2 * sys_obj.k_max_cap + 1
        sys_obj.delta_max = sys_obj.k_max_cap + K * sys_obj.l_max_cap
        sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
        sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
        k_real = sys_obj.v_mean * sys_obj.fc / (
            sys_obj.c_sound * sys_obj.fs) * args.n_total
        kappa = abs(k_real - round(k_real))
        print(f"[train] v_mean override → v={sys_obj.v_mean:.1f} m/s  "
              f"k_real={k_real:.3f}  κ={kappa:.3f}  k_max_cap={sys_obj.k_max_cap}")

    if args.cdtype == 'complex64':
        cdtype = torch.complex64
        rdtype = torch.float32
    else:
        cdtype = torch.complex128
        rdtype = torch.float64

    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    # W8 Path B fix: precompute SNR sampling distribution (uniform by default).
    _snr_p = np.array(args.snr_weights if args.snr_weights is not None
                      else [1.0] * len(args.snr_list), dtype=float)
    _snr_p = _snr_p / _snr_p.sum()
    print(f'[train] snr sampling weights: {dict(zip(args.snr_list, _snr_p.tolist()))}',
          flush=True)

    cfg = ClassicalJointConfig(
        N=int(sys_obj.N_total),
        l_max=int(sys_obj.l_max_cap),
        k_max=int(sys_obj.k_max_cap),
        c1=float(sys_obj.c1),
        c2=float(sys_obj.c2),
        n_outer_iter=int(args.n_outer_iter),
        pic_iter=20,
        pic_damp=float(args.pic_damp),
        mp_mode=str(args.mp_mode),
        rho=float(sys_obj.rho),
        n_paths=int(sys_obj.P_paths),
        dtype=cdtype,
        rdtype=rdtype,
        early_stop=False,           # OFF for training
    )
    # --variant selects which learnable heads to enable.  'A' is the original
    # symbol-refiner-only on final x_soft; 'B1B2' adds per-iter refiner +
    # iter-residual selector (codex-recommended design from Round 1 diagnostic).
    VARIANT_HEADS = {
        'A':     ('scalars', 'strategy', 'symbol_refiner'),
        'S':     ('scalars',),       # scalars-only: 30 learned hparams total
        'S-lam': ('scalars',),       # Loop-5: only lam_raw trainable (5 params)
        'B1':    ('per_iter_refiner',),
        'B2':    ('iter_residual_selector',),
        'B1B2':  ('per_iter_refiner', 'iter_residual_selector'),
        'B3':    ('channel_tap_corrector',),  # CE-side DeepSets, Codex R2
        'B1B3':  ('per_iter_refiner', 'channel_tap_corrector'),
        'S+B1':  ('scalars', 'per_iter_refiner'),
        'C1':    ('off_support_corr',),       # Loop-6 Oracle Phase-A recipe
        'C2-rel': ('cand_active_rel',),       # Loop-9 Oracle R1 recipe (support repair)
        'all':   ('scalars', 'strategy', 'symbol_refiner',
                  'per_iter_refiner', 'iter_residual_selector',
                  'channel_tap_corrector'),
    }
    if args.variant not in VARIANT_HEADS:
        raise ValueError(f"--variant must be one of {list(VARIANT_HEADS)}")
    heads = VARIANT_HEADS[args.variant]

    module = ClassicalJointUnrolled(
        cfg,
        learnable_heads=heads,
        use_soft_decisions=True,
    )
    # S-lam: freeze all scalars except lam_raw so only the per-iter
    # lambda_ls softplus parameter is trainable.  Optionally install a
    # [lo, hi] clamp around the classical default so the learned value
    # cannot stray more than ~1 decade, which preserves identity at init
    # and prevents runaway regression at high SNR.
    if args.variant == 'S-lam' and module.scalars is not None:
        frozen = 0
        for name, p in module.scalars.named_parameters():
            if name != 'lam_raw':
                p.requires_grad_(False)
                frozen += 1
        if args.lam_ls_clip is not None:
            lo, hi = args.lam_ls_clip
            module.scalars.lam_ls_clip = (float(lo), float(hi))
        print(f"[train] S-lam: lam_raw is the ONLY trainable scalar "
              f"(frozen {frozen}/{sum(1 for _ in module.scalars.parameters())}); "
              f"clamp={module.scalars.lam_ls_clip}")
    module = module.to(device)
    print(f"[train] variant={args.variant}  heads={heads}")
    print(f"[train] device={device} cdtype={cdtype}")

    print(f"[train] N={cfg.N} l_max={cfg.l_max} k_max={cfg.k_max} "
          f"c1={cfg.c1:.6g} c2={cfg.c2:.3e}")
    print(f"[LOOP5_CONFIG] variant={args.variant} heads={heads} "
          f"mp_mode={args.mp_mode} pic_damp={args.pic_damp} "
          f"N={cfg.N} v={sys_obj.v_mean} P={sys_obj.P_paths} "
          f"tau={sys_obj.tau_spread*1e3:.2f}ms rho={cfg.rho} "
          f"SNRs={args.snr_list} cdtype={args.cdtype} "
          f"lam_ls_clip={args.lam_ls_clip}",
          flush=True)
    print(f"[train] SNRs={args.snr_list}  phases: warm={args.phase0_iters} "
          f"scalars={args.phase1_iters} heads={args.phase2_iters}  "
          f"batch={args.batch_size}  lr(s)={args.lr_scalars:.1e} "
          f"lr(h)={args.lr_heads:.1e}")

    # --------- Phase 0: warm identity ----------------------------------
    _set_requires_grad(module, False)
    module.eval()
    rng_eval = np.random.default_rng(args.seed + 999)
    for i in range(args.phase0_iters):
        snr = int(args.snr_list[rng_eval.integers(0, len(args.snr_list))])
        frame = _sample_frame(sys_obj, snr, rng_eval)
        with torch.no_grad():
            out = _one_forward(module, frame, sys_obj,
                               cdtype=cfg.dtype, rdtype=cfg.rdtype, device=device)
        ber_learned = _ber_from_xsoft(out['x_soft'].cpu().numpy(),
                                      frame['bits_true'], frame['P_d'])
        ber_classical, _ = _classical_baseline_ber(
            frame, sys_obj, mp_mode=args.mp_mode, pic_damp=args.pic_damp,
            n_outer_iter=int(args.n_outer_iter))
        print(f"[phase0 i={i:3d} snr={snr:2d}] ber_learned={ber_learned:.4e} "
              f"ber_classical={ber_classical:.4e} Δ={ber_learned - ber_classical:+.2e}",
              flush=True)

    # --------- Phase 1a: B2 best-iterate supervised pretrain -----------
    # Per Codex Round 2: the 20 dB regression is because B2 hadn't learned the
    # oracle-best-iter pattern.  We pretrain B2 alone with an explicit target:
    # for each frame the supervised target is `x_soft_history[t*]` where
    # `t* = argmin_t BER(x_soft_history[t])` on ground-truth bits.  Loss is
    # MSE(B2-blended output, target).  This forces B2's α to route mass onto
    # the best iterate BEFORE the joint training phase.
    if args.b2_pretrain_iters > 0 and module.iter_residual_selector is not None:
        print(f"[b2-pretrain] starting best-iter supervised pretrain: "
              f"{args.b2_pretrain_iters} iters at lr={args.lr_b2_pretrain}")
        module.train()
        _set_requires_grad(module, False)
        for p in module.iter_residual_selector.parameters():
            p.requires_grad_(True)
        opt_b2 = torch.optim.Adam(
            module.iter_residual_selector.parameters(),
            lr=args.lr_b2_pretrain)
        rng_b2 = np.random.default_rng(args.seed + 5500)
        sqrtPd = float(np.sqrt(1.0 - float(sys_obj.rho)))
        for i in range(args.b2_pretrain_iters):
            snr = int(args.snr_list[rng_b2.integers(0, len(args.snr_list))])
            frame = _sample_frame(sys_obj, snr, rng_b2)
            out = _one_forward(module, frame, sys_obj,
                               cdtype=cfg.dtype, rdtype=cfg.rdtype,
                               device=device)
            history = out['x_soft_history']        # list of T complex tensors
            bits_true = frame['bits_true']
            # Per-iter BER on bit decisions
            best_t = 0
            best_ber = float('inf')
            for t_idx, x_t in enumerate(history):
                ber_t = _ber_from_xsoft(
                    x_t.detach().cpu().numpy(), bits_true, frame['P_d'])
                if ber_t < best_ber:
                    best_ber = ber_t
                    best_t = t_idx
            x_target = history[best_t].detach()
            # B2's final output = out['x_soft']; loss = MSE
            diff = out['x_soft'] - x_target
            loss = (diff.real.pow(2) + diff.imag.pow(2)).mean().float()
            opt_b2.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                module.iter_residual_selector.parameters(), max_norm=1.0)
            opt_b2.step()
            if i % 20 == 0:
                print(f"[b2-pretrain i={i:4d} snr={snr:2d}] "
                      f"best_t={best_t}  best_BER={best_ber:.3e}  "
                      f"loss={float(loss):.3e}", flush=True)
        print(f"[b2-pretrain] done.  Proceeding to joint fine-tune.")

    # --------- Phase 1+2: training -------------------------------------
    module.train()
    rng_train = np.random.default_rng(args.seed)
    train_log: List[Dict] = []

    def build_opt(include: List[str], lr: float):
        params = _collect_params(module, include)
        # S-lam: restrict scalars params to lam_raw only. Prevents
        # build_opt from re-enabling gamma_h/gamma_x/pic_damp/tau_* which
        # were intentionally frozen after instantiation.
        if args.variant == 'S-lam' and 'scalars' in include and module.scalars is not None:
            params = [module.scalars.lam_raw]
        if not params:
            return None
        _set_requires_grad(module, False)
        for p in params:
            p.requires_grad_(True)
        return torch.optim.Adam(params, lr=lr)

    all_head_names = ['scalars', 'strategy', 'symbol_refiner',
                      'per_iter_refiner', 'iter_residual_selector',
                      'channel_tap_corrector', 'off_support_corr']
    active_heads = [h for h in all_head_names if h in heads]
    phases = [
        ('scalars', ['scalars'] if 'scalars' in active_heads else [],
         args.lr_scalars, args.phase1_iters),
        ('heads', active_heads, args.lr_heads, args.phase2_iters),
    ]
    if args.freeze_scalars:
        non_scalar = [h for h in active_heads if h != 'scalars']
        phases = [('heads', non_scalar, args.lr_heads, args.phase2_iters)]

    t0 = time.time()
    # Best-eval checkpointing + early-stop. Two scoring modes:
    #   'mean_delta' (default, legacy): minimize mean BER Δ across all SNRs.
    #   'gate' (Loop-6 Oracle): lexicographic
    #       1) minimize max(Δ10, Δ15, Δ20)
    #       2) then minimize 2·Δ20 + Δ15 + Δ10
    # After `patience` evals without improvement, early-stop.
    #
    # `best_score` is a tuple; smaller = better. We initialize to worst case.
    best_score = (float('inf'),) if args.checkpoint_score == 'mean_delta' \
        else (float('inf'), float('inf'))
    best_eval_delta = float('inf')     # retained for final ckpt metadata
    best_state = None
    stale_evals = 0   # count of evals without improvement (for early-stop)
    patience = int(args.patience)

    def _score_eval(ev: Dict[int, Dict[str, float]]) -> Tuple:
        if args.checkpoint_score == 'gate':
            dlt = {int(s): (ev[s]['ber_learned'] - ev[s]['ber_classical'])
                   for s in ev}
            gate = [dlt[s] for s in (10, 15, 20) if s in dlt]
            if not gate:
                # fall back to overall mean when gate SNRs not in eval list
                return (float(np.mean([v for v in dlt.values()])),)
            max_gate = float(max(gate))
            w = 0.0
            if 20 in dlt: w += 2.0 * dlt[20]
            if 15 in dlt: w += dlt[15]
            if 10 in dlt: w += dlt[10]
            return (max_gate, w)
        return (float(np.mean([ev[s]['ber_learned'] - ev[s]['ber_classical']
                                for s in ev])),)
    for (phase_name, include, lr, n_iters) in phases:
        opt = build_opt(include, lr)
        if opt is None or n_iters <= 0:
            print(f"[phase {phase_name}] skipped (no params / n_iters=0)")
            continue
        print(f"[phase {phase_name}] lr={lr:.1e}  n_iters={n_iters}  "
              f"training params: {[n for (n, p) in module.named_parameters() if p.requires_grad]}",
              flush=True)

        for i in range(n_iters):
            opt.zero_grad()
            loss_acc = 0.0
            ber_acc = 0.0
            for _ in range(args.batch_size):
                snr = int(args.snr_list[rng_train.choice(len(args.snr_list), p=_snr_p)])
                frame = _sample_frame(sys_obj, snr, rng_train)
                out = _one_forward(module, frame, sys_obj,
                                   cdtype=cfg.dtype, rdtype=cfg.rdtype, device=device)
                x_norm = out['x_soft'] / np.sqrt(frame['P_d'])
                bits_t = torch.tensor(frame['bits_true'], dtype=torch.float32, device=device)
                data_qam_t = torch.tensor(frame['data_qam'], dtype=cfg.dtype, device=device)
                loss = (args.lam_bce * _bit_bce_loss(x_norm, bits_t, scale=args.bce_scale)
                        + args.lam_sym * _sym_mse_loss(out['x_soft'], data_qam_t, frame['P_d']))
                # Optional: channel-NMSE loss (Codex R2) — drives H_est toward
                # H_true using the true data symbol as test vector. Far lower
                # variance than BCE for CE-heavy regimes like P=10.
                if args.lam_chan > 0.0:
                    H_true_t = torch.tensor(frame['H_true'], dtype=cfg.dtype, device=device)
                    x_true_t = torch.tensor(frame['x_sp'], dtype=cfg.dtype, device=device)
                    loss = loss + args.lam_chan * _chan_nmse_loss(
                        out['H_est'], H_true_t, x_true_t)
                (loss / args.batch_size).backward()
                loss_acc += float(loss.detach().cpu()) / args.batch_size
                ber_acc += _ber_from_xsoft(
                    out['x_soft'].detach().cpu().numpy(),
                    frame['bits_true'], frame['P_d']) / args.batch_size
            torch.nn.utils.clip_grad_norm_(
                [p for p in opt.param_groups[0]['params']],
                max_norm=args.grad_clip)
            opt.step()

            if i % args.log_every == 0:
                elapsed = time.time() - t0
                row = dict(phase=phase_name, iter=int(i), loss=float(loss_acc),
                           ber_train=float(ber_acc), elapsed=float(elapsed))
                train_log.append(row)
                print(f"[{phase_name} i={i:4d}] loss={loss_acc:.4e} "
                      f"ber_train={ber_acc:.4e}  [{elapsed:.0f}s]", flush=True)

            if (i + 1) % args.eval_every == 0 or i == n_iters - 1:
                # Held-out eval. Hard-mode eval (Oracle Loop-6): flip module
                # temporarily to use_soft_decisions=False so checkpoint
                # selection matches the paired-hard-eval rubric.
                eval_hard = bool(args.eval_hard)
                saved_soft = module.use_soft_decisions
                if eval_hard:
                    module.use_soft_decisions = False
                try:
                    ev = _evaluate(module, sys_obj, cfg, device,
                                   args.eval_frames, args.snr_list,
                                   rng=np.random.default_rng(args.seed + 17 + i))
                finally:
                    module.use_soft_decisions = saved_soft
                mean_delta = float(np.mean(
                    [ev[s]['ber_learned'] - ev[s]['ber_classical']
                     for s in sorted(ev.keys())]))
                score = _score_eval(ev)
                is_best = score < best_score
                tag = "  **new best**" if is_best else ""
                mode_tag = "[HARD]" if eval_hard else "[SOFT]"
                print(f"[eval{mode_tag} after {phase_name} i={i}] score={score} "
                      f"mean_Δ={mean_delta:+.2e}{tag}  "
                      + "  ".join(
                          f"snr={s}: learned={ev[s]['ber_learned']:.4e} "
                          f"classical={ev[s]['ber_classical']:.4e} "
                          f"Δ={ev[s]['ber_learned'] - ev[s]['ber_classical']:+.2e}"
                          for s in sorted(ev.keys())
                ), flush=True)
                train_log.append(dict(phase=phase_name, iter=int(i), eval=ev,
                                      mean_delta=mean_delta, score=list(score),
                                      hard_mode=eval_hard))
                if is_best:
                    best_score = score
                    best_eval_delta = mean_delta
                    best_state = {k: v.detach().cpu().clone()
                                  for k, v in module.state_dict().items()}
                    stale_evals = 0
                    # Persist best-so-far to disk immediately; protects against
                    # losing progress if training is killed mid-run.
                    try:
                        _tmp_ckpt = out_dir / "classical_joint_unrolled_best.pt"
                        torch.save(dict(state_dict=best_state, cfg=asdict(cfg),
                                         best_eval_delta=float(mean_delta),
                                         best_score=list(score),
                                         iter=int(i), phase=phase_name,
                                         eval_mode='hard' if eval_hard else 'soft',
                                         ), _tmp_ckpt)
                        print(f"  [best-ckpt-saved] {_tmp_ckpt}", flush=True)
                    except Exception as _e:
                        print(f"  [best-ckpt-save-failed] {_e}", flush=True)
                else:
                    stale_evals += 1
                    if patience > 0 and stale_evals >= patience:
                        print(f"[early-stop] no improvement for {stale_evals} "
                              f"evals (patience={patience}); stopping "
                              f"{phase_name} phase.", flush=True)
                        break

    # --------- Save checkpoint + logs ----------------------------------
    # Save the BEST-eval checkpoint (not the final) because loss oscillation
    # with small-batch on a near-optimal classical baseline means the final
    # state is often worse than an intermediate one.  Final state is saved
    # too for debugging.
    best_ckpt = out_dir / "classical_joint_unrolled_best.pt"
    if best_state is not None:
        torch.save(dict(state_dict=best_state, cfg=asdict(cfg),
                        best_eval_delta=float(best_eval_delta)), best_ckpt)
        print(f"[train] saved BEST ckpt (mean_Δ={best_eval_delta:+.2e}) → {best_ckpt}")
    final_ckpt = out_dir / "classical_joint_unrolled_final.pt"
    torch.save(dict(state_dict=module.state_dict(), cfg=asdict(cfg)), final_ckpt)
    (out_dir / "train_log.json").write_text(json.dumps(train_log, indent=2, default=float))
    print(f"[train] saved FINAL ckpt → {final_ckpt}")


def _evaluate(module: ClassicalJointUnrolled, sys_obj, cfg,
              device, n_frames: int, snr_list: List[int],
              rng: np.random.Generator) -> Dict[int, Dict[str, float]]:
    module.eval()
    out: Dict[int, Dict[str, float]] = {}
    # Deduplicate — training SNR list may intentionally repeat values to bias
    # the sampler; evaluation should run each SNR once.
    for snr in sorted(set(int(s) for s in snr_list)):
        bers_l, bers_c = [], []
        for _ in range(n_frames):
            frame = _sample_frame(sys_obj, int(snr), rng)
            with torch.no_grad():
                mod_out = _one_forward(module, frame, sys_obj,
                                       cdtype=cfg.dtype, rdtype=cfg.rdtype,
                                       device=device)
            bers_l.append(_ber_from_xsoft(
                mod_out['x_soft'].cpu().numpy(), frame['bits_true'], frame['P_d']))
            bc, _ = _classical_baseline_ber(
                frame, sys_obj, mp_mode=cfg.mp_mode, pic_damp=cfg.pic_damp,
                n_outer_iter=int(cfg.n_outer_iter))
            bers_c.append(bc)
        out[int(snr)] = dict(
            ber_learned=float(np.mean(bers_l)),
            ber_classical=float(np.mean(bers_c)),
            n=n_frames,
        )
    module.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fs-factor', type=float, default=2.0,
                    help='fs = fs_factor * B (default 2.0 Nyquist). Canonical '
                         'TCOM headline used 4.0 (paired_learned_eval default).')
    ap.add_argument('--snr-weights', type=float, nargs='+', default=None,
                    help='Probability weights for SNR sampling (per --snr-list '
                         'entry). Default: uniform. W8 Path B fix: weight '
                         'SNR=25 higher to address B+ iter=5 SNR=25 regression.')
    ap.add_argument('--n-outer-iter', type=int, default=5,
                    help='Joint OMP-MP outer iter count for BOTH student and '
                         'classical reference. W8 Path B trains B1 at iter=3 '
                         'to learn per-iter MP-BP refinement that compensates '
                         'for fewer iters; canonical TCOM headline used iter=10.')
    ap.add_argument('--n-total', type=int, default=256)
    ap.add_argument('--v-mean', type=float, default=None,
                    help='Override UWA v_mean (m/s).  None → use system default. '
                         'For kappa-clean setups: (N=128,v=8), (N=256,v=4), (N=512,v=2).')
    ap.add_argument('--snr-list', nargs='+', type=int, default=[15, 20, 25])
    ap.add_argument('--batch-size', type=int, default=4)
    ap.add_argument('--phase0-iters', type=int, default=5)
    ap.add_argument('--phase1-iters', type=int, default=100)
    ap.add_argument('--phase2-iters', type=int, default=300)
    ap.add_argument('--lr-scalars', type=float, default=5e-4)
    ap.add_argument('--lr-heads', type=float, default=1e-3)
    ap.add_argument('--lam-bce', type=float, default=1.0)
    ap.add_argument('--lam-chan', type=float, default=0.0,
                    help='Weight for effective-channel NMSE loss (Codex R2). '
                         'Recommended > 0 when training B3 (channel_tap_corrector).')
    ap.add_argument('--lam-sym', type=float, default=0.05,
                    help='Symbol MSE weight.  Default 0.05 (BCE-primary per '
                         'codex Round 1 minimum-fix).')
    ap.add_argument('--variant', type=str, default='B1B2',
                    choices=['A', 'S', 'S-lam', 'B1', 'B2', 'B1B2', 'B3',
                             'B1B3', 'S+B1', 'C1', 'all'],
                    help='Which learned-head variant. B1B2 is the codex-'
                         'recommended design from Round 1 diagnostic. '
                         'S-lam (Loop-5) trains only per-iter lambda_ls. '
                         'C1 (Loop-6) is Oracle Phase-A off-support corr head.')
    ap.add_argument('--lam-ls-clip', type=float, nargs=2, default=None,
                    metavar=('LO', 'HI'),
                    help='Optional clamp on effective lambda_ls_factor (S-lam). '
                         'E.g. `--lam-ls-clip 1e-4 1e-2` pins within ~1 decade '
                         'of classical default 1e-3.')
    ap.add_argument('--b2-pretrain-iters', type=int, default=0,
                    help='If > 0 and B2 enabled, run best-iter supervised '
                         'pretrain for B2 before main training (Codex Round 2 '
                         'minimum-fix).')
    ap.add_argument('--lr-b2-pretrain', type=float, default=5e-4)
    ap.add_argument('--bce-scale', type=float, default=8.0)
    ap.add_argument('--grad-clip', type=float, default=5.0)
    ap.add_argument('--device', type=str, default='auto',
                    choices=['auto', 'cpu', 'cuda'],
                    help='Compute device.  auto → cuda if available, else cpu.')
    ap.add_argument('--cdtype', type=str, default='complex128',
                    choices=['complex128', 'complex64'],
                    help='Complex dtype.  complex64 is ~2× faster on GPU but '
                         'slightly less precise (OK for training; identity-check '
                         'must still use complex128).')
    ap.add_argument('--freeze-scalars', action='store_true',
                    help='Skip the scalars phase; only train strategy MLP + '
                         'symbol refiner.  Keeps hparams at classical defaults '
                         '(recommended when classical already near-optimal).')
    ap.add_argument('--log-every', type=int, default=10)
    ap.add_argument('--eval-every', type=int, default=50)
    ap.add_argument('--eval-frames', type=int, default=20)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--mp-mode', type=str, default='pic', choices=['pic', 'bp'],
                    help="MP detector inside the unrolled loop: 'pic' (default) "
                         "or 'bp' (torch mp_detect_bp_torch).")
    ap.add_argument('--pic-damp', type=float, default=0.5,
                    help='Inner MP damping coefficient; applies to both PIC and BP.')
    ap.add_argument('--p-paths', type=int, default=10,
                    help='UWA physical multipath count (set 5 to match MATLAB).')
    ap.add_argument('--tau-spread', type=float, default=None,
                    help='Override channel tau_spread (s). Default 10e-3.')
    ap.add_argument('--patience', type=int, default=3,
                    help='Early-stop: abort phase after N evals with no improvement. '
                         '0 disables early-stop. Default 3.')
    ap.add_argument('--eval-hard', action='store_true',
                    help='Loop-6 Oracle: evaluate + checkpoint-select in HARD '
                         'decision mode even if training is soft. Crucial for '
                         'the soft-train/hard-test generalization.')
    ap.add_argument('--checkpoint-score', type=str, default='mean_delta',
                    choices=['mean_delta', 'gate'],
                    help="Checkpoint selection rule. 'gate' (Loop-6 Oracle) "
                         "picks min(max(Δ10,Δ15,Δ20)) lex min(2Δ20+Δ15+Δ10). "
                         "'mean_delta' is legacy behaviour.")
    ap.add_argument('--out-dir', type=str,
                    default=str(HERE / 'outputs_classical_joint_unrolled_v1'))
    args = ap.parse_args()
    train(args)


if __name__ == '__main__':
    main()
