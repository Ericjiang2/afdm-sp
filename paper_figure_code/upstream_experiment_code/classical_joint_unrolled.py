"""
classical_joint_unrolled.py

Faithful differentiable unrolling of the classical joint OMP-MP iterative
receiver defined in ``afdm_baselines.py::joint_omp_mp_iterative``.

Design contract
---------------
1. **Identity mode** — with ``use_soft_decisions=False`` and all learnable heads
   frozen at classical defaults (γ_h=0.7, γ_x=0.6, λ_ls_factor=1e-3, τ_rel=0.01,
   τ_σ=0.1, pic_damp=0.5, pic_iter=20, T=5), ``ClassicalJointUnrolled`` must
   produce outputs numerically identical (within float64 round-off) to the
   NumPy baseline on the same inputs.
2. **Training mode** — with ``use_soft_decisions=True`` and learnable heads
   enabled, the module is end-to-end differentiable.  Hard-decision branches in
   DA-LS and PIC are replaced by soft expectations from the QPSK posterior, so
   gradients flow through the entire T-iteration unroll.
3. **Unbatched-in-forward** — the inner loops operate on a single frame
   (``B=1``).  External training code iterates frames and accumulates loss, or
   uses ``torch.vmap`` for light batching if desired.  This keeps the OMP
   support-set logic straightforward (per-frame variable support sizes).

See ``verify_classical_unrolled_matches_numpy.py`` for the identity-check
harness and ``train_classical_joint_unrolled.py`` for the DNN fine-tuning
trainer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch


# ======================================================================
# 0. Dataclass config
# ======================================================================


@dataclass
class ClassicalJointConfig:
    """Static configuration for the unrolled receiver."""

    N: int = 512
    l_max: int = 50
    k_max: int = 2
    c1: float = 0.0
    c2: float = 0.0
    n_outer_iter: int = 5
    pic_iter: int = 20
    pic_damp: float = 0.5
    gamma_h: float = 0.7
    gamma_x: float = 0.6
    lambda_ls_factor: float = 1e-3
    tau_h_factor: float = 0.01
    tau_h_sigma_factor: float = 0.1
    k_leak: int = 2
    n_paths: int = 10            # OMP sparsity
    rho: float = 0.5
    eps_stop_rel: float = 1e-3
    update_sigma2: bool = True
    early_stop: bool = False     # OFF for training, ON for identity check
    mp_mode: str = 'pic'         # 'pic' | 'bp'  (BP uses mp_detect_bp_torch)
    bp_threshold: float = 1e-4   # BP-only: edge threshold on |H|
    dtype: torch.dtype = torch.complex128
    rdtype: torch.dtype = torch.float64
    device: str = "cpu"


# ======================================================================
# 1. Pure-function torch helpers (match NumPy step-for-step)
# ======================================================================


def _phase_c(angle: torch.Tensor, cdtype: torch.dtype) -> torch.Tensor:
    """exp(j·angle), complex output."""
    return torch.complex(torch.cos(angle), torch.sin(angle)).to(cdtype)


def construct_sensing_matrix_torch(N: int, x_pilot: torch.Tensor,
                                   c1: float, c2: float,
                                   l_max: int, k_max: int,
                                   cdtype: torch.dtype = torch.complex128) -> torch.Tensor:
    """Mirrors ``afdm_baselines.construct_sensing_matrix`` (Python convention)."""
    device = x_pilot.device
    K = 2 * k_max + 1
    Q = (l_max + 1) * K
    q_arr = torch.arange(N, device=device, dtype=torch.float64)

    Phi = torch.zeros((N, Q), dtype=cdtype, device=device)

    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        l_f = float(l)
        for k in range(-k_max, k_max + 1):
            delta = l * K + k
            p_arr = ((q_arr - delta) % N).to(torch.long)
            p_f = p_arr.to(torch.float64)
            angle = 2.0 * math.pi * (
                -c1 * l_sq
                + c2 * (q_arr.pow(2) - p_f.pow(2))
                - l_f * p_f / N
            )
            Phi[:, col] = _phase_c(angle, cdtype) * x_pilot[p_arr].to(cdtype)
            col += 1

    return Phi


def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int
                     ) -> Tuple[torch.Tensor, List[int]]:
    """Torch OMP — mirrors ``afdm_baselines.omp_sparse``.

    Returns ``(h_est, support)`` where support indices are detached (support
    selection is inherently argmax-based).  The returned gains use
    ``torch.linalg.lstsq`` which *is* differentiable w.r.t. ``y``.
    """
    Q = Phi.shape[1]
    residual = y.clone()
    support: List[int] = []
    Phi_H = Phi.conj().T

    y_norm = torch.linalg.vector_norm(y)

    for _ in range(sparsity):
        correlations = (Phi_H @ residual).abs()       # (Q,)
        for idx in support:
            correlations[idx] = 0.0
        new_idx = int(torch.argmax(correlations).item())
        support.append(new_idx)

        Phi_S = Phi[:, support]                        # (N, s)
        # lstsq is differentiable
        sol = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1)).solution.squeeze(-1)
        residual = y - Phi_S @ sol

        if torch.linalg.vector_norm(residual) < 1e-10 * y_norm:
            break

    h_est = torch.zeros(Q, dtype=y.dtype, device=y.device)
    if support:
        Phi_S = Phi[:, support]
        gains_final = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1)).solution.squeeze(-1)
        for i, idx in enumerate(support):
            h_est[idx] = gains_final[i]

    return h_est, support


def reconstruct_H_torch(N: int,
                        support_delays: torch.Tensor,
                        support_dopplers: torch.Tensor,
                        gains_S: torch.Tensor,
                        c1: float, c2: float, k_max: int,
                        cdtype: torch.dtype = torch.complex128) -> torch.Tensor:
    """Mirrors ``afdm_baselines.joint_omp_mp_iterative`` inline H reconstruction
    (Python convention).

    ``support_delays[p]``, ``support_dopplers[p]``, ``gains_S[p]`` define a
    single path.  Loop is over a (typically small) support so Python-level
    iteration is fine; everything inside is torch so gradients flow through
    ``gains_S``.
    """
    device = gains_S.device
    n_arr = torch.arange(N, device=device, dtype=torch.float64)
    cols = torch.arange(N, device=device, dtype=torch.long)
    H_new = torch.zeros((N, N), dtype=cdtype, device=device)
    K = 2 * k_max + 1

    P = int(support_delays.numel())
    for p in range(P):
        l_p = int(support_delays[p].item())
        k_p = int(support_dopplers[p].item())
        g = gains_S[p]
        delta = l_p * K + k_p
        m_arr = ((n_arr.to(torch.long) + delta) % N).to(torch.long)
        m_f = m_arr.to(torch.float64)
        angle = 2.0 * math.pi * (
            -c1 * (l_p ** 2)
            + c2 * (m_f.pow(2) - n_arr.pow(2))
            - float(l_p) * n_arr / N
        )
        phase = _phase_c(angle, cdtype)
        H_new = H_new.index_put_((m_arr, cols),
                                 H_new[m_arr, cols] + g * phase,
                                 accumulate=False)
    return H_new


def build_A_for_DALS_torch(N: int,
                           support_delays: torch.Tensor,
                           support_dopplers: torch.Tensor,
                           x_total: torch.Tensor,
                           c1: float, c2: float, k_max: int,
                           cdtype: torch.dtype = torch.complex128) -> torch.Tensor:
    """Build (N, P) DA-LS matrix A where A[:, p] is the column induced by
    path (l_p, k_p) acting on x_total = x_pilot + x_hard."""
    device = x_total.device
    n_arr = torch.arange(N, device=device, dtype=torch.float64)
    K = 2 * k_max + 1
    P = int(support_delays.numel())
    A = torch.zeros((N, P), dtype=cdtype, device=device)

    for p in range(P):
        l_p = int(support_delays[p].item())
        k_p = int(support_dopplers[p].item())
        delta = l_p * K + k_p
        m_arr = ((n_arr.to(torch.long) + delta) % N).to(torch.long)
        m_f = m_arr.to(torch.float64)
        angle = 2.0 * math.pi * (
            -c1 * (l_p ** 2)
            + c2 * (m_f.pow(2) - n_arr.pow(2))
            - float(l_p) * n_arr / N
        )
        phase = _phase_c(angle, cdtype)
        col_val = phase * x_total.to(cdtype)
        a_col = torch.zeros(N, dtype=cdtype, device=device)
        # a_col[m_arr] = col_val    (NumPy version is non-aggregating assignment)
        a_col[m_arr] = col_val
        A[:, p] = a_col
    return A


def _qpsk_hard_decision(x_soft: torch.Tensor, constellation: torch.Tensor) -> torch.Tensor:
    """Nearest-constellation per element.

    ``x_soft`` : (..., N) complex
    ``constellation`` : (M,) complex
    Returns (..., N) complex with entries in ``constellation``.
    """
    # Shape gymnastics to allow batched or single-frame inputs.
    orig_shape = x_soft.shape
    flat = x_soft.reshape(-1)                             # (B·N,)
    diff = flat.unsqueeze(-1) - constellation.view(1, -1)  # (B·N, M)
    d2 = diff.real.pow(2) + diff.imag.pow(2)
    idx = torch.argmin(d2, dim=-1)                        # (B·N,)
    out = constellation[idx].reshape(orig_shape)
    return out.to(x_soft.dtype)


def mp_detect_pic_torch(y_data: torch.Tensor, H: torch.Tensor, sigma2: torch.Tensor,
                        constellation: torch.Tensor,
                        n_iter: int, damp: torch.Tensor,
                        hard_decision: bool = True) -> torch.Tensor:
    """Mirrors ``afdm_baselines.mp_detect_pic``.

    ``sigma2`` must be a **real** scalar (float32/float64 tensor or float).
    ``damp`` is a real scalar.  ``y_data``, ``H`` are complex.
    """
    HH_diag = (H.abs().pow(2)).sum(dim=0)                      # (N,) real
    rdtype = HH_diag.dtype
    if not torch.is_tensor(sigma2):
        sigma2_r = torch.tensor(float(sigma2), dtype=rdtype, device=HH_diag.device)
    else:
        sigma2_r = sigma2.to(rdtype)
    if not torch.is_tensor(damp):
        damp_r = torch.tensor(float(damp), dtype=rdtype, device=HH_diag.device)
    else:
        damp_r = damp.to(rdtype)

    inv_denom = 1.0 / torch.clamp(HH_diag + sigma2_r, min=1e-30)  # (N,) real

    x_mf = (H.conj().T @ y_data) * inv_denom                     # (N,) complex (complex·real)
    if hard_decision:
        x_hat = _qpsk_hard_decision(x_mf, constellation)
    else:
        x_hat = _qpsk_soft_decision(x_mf, HH_diag, sigma2_r, constellation)

    for _ in range(n_iter):
        r = y_data - H @ x_hat
        x_new = x_hat + (H.conj().T @ r) * inv_denom
        if hard_decision:
            x_hard = _qpsk_hard_decision(x_new, constellation)
        else:
            x_hard = _qpsk_soft_decision(x_new, HH_diag, sigma2_r, constellation)
        x_hat = damp_r * x_hard + (1.0 - damp_r) * x_hat

    if hard_decision:
        return _qpsk_hard_decision(x_hat, constellation)
    else:
        return x_hat


def _qpsk_soft_decision(x_soft: torch.Tensor, HH_diag: torch.Tensor,
                        sigma2: torch.Tensor,
                        constellation: torch.Tensor) -> torch.Tensor:
    """Soft (posterior-mean) QPSK decision — differentiable.

    For each symbol we treat the input as a Gaussian observation with
    per-symbol variance ``v_n = sigma2 / max(HH_diag_n, 1e-10)`` and compute
    E[x | x_soft, v_n] with a uniform prior over the QPSK constellation.
    This is the same rule used inside ``QPSKPosterior`` but written directly
    on the (N,) complex layout used here.
    """
    # (N, M) squared distance
    v_n = sigma2 / torch.clamp(HH_diag.real, min=1e-10)              # (N,)
    diff = x_soft.unsqueeze(-1) - constellation.view(1, -1)          # (N, M)
    d2 = diff.real.pow(2) + diff.imag.pow(2)                         # (N, M)
    logp = -d2 / torch.clamp(v_n.unsqueeze(-1), min=1e-12)           # (N, M)
    logp = logp - logp.max(dim=-1, keepdim=True).values
    p = torch.softmax(logp, dim=-1)                                  # (N, M)
    # mu = sum_s p(s) * s
    mu = (p * constellation.view(1, -1)).sum(dim=-1)                 # (N,) complex
    return mu.to(x_soft.dtype)


# ======================================================================
# 2. Cluster-support expansion (discrete, no gradient)
# ======================================================================


def expand_cluster_support(support_idx: List[int], k_max: int, k_leak: int,
                           gains: torch.Tensor, Q: int):
    """Mirrors the cluster-expansion block inside ``joint_omp_mp_iterative``.

    For every selected column we add the ±k_leak Doppler neighbours with zero
    gain; duplicates are merged by summing gains.  Returns
    ``(support_delays, support_dopplers, gains_merged)`` as CPU long / complex
    tensors on the same device as ``gains``.
    """
    device = gains.device
    K = 2 * k_max + 1

    # Decode column indices
    exp_delays: List[int] = []
    exp_dopplers: List[int] = []
    exp_gains: List[torch.Tensor] = []

    for i, idx in enumerate(support_idx):
        l_dec = idx // K
        k_dec = (idx % K) - k_max
        g_i = gains[idx]
        for m in range(-k_leak, k_leak + 1):
            k_new = k_dec + m
            if abs(k_new) > k_max:
                continue
            exp_delays.append(l_dec)
            exp_dopplers.append(k_new)
            exp_gains.append(g_i if m == 0 else torch.zeros_like(g_i))

    if not exp_delays:
        return (torch.zeros(0, dtype=torch.long, device=device),
                torch.zeros(0, dtype=torch.long, device=device),
                torch.zeros(0, dtype=gains.dtype, device=device))

    # Merge duplicate (l, k) pairs by summing gains.
    pair_key = [(d, k) for d, k in zip(exp_delays, exp_dopplers)]
    uniq: Dict[Tuple[int, int], torch.Tensor] = {}
    for key, g in zip(pair_key, exp_gains):
        uniq[key] = uniq.get(key, torch.zeros_like(g)) + g

    keys = sorted(uniq.keys())
    delays = torch.tensor([k[0] for k in keys], dtype=torch.long, device=device)
    dopplers = torch.tensor([k[1] for k in keys], dtype=torch.long, device=device)
    gains_merged = torch.stack([uniq[k] for k in keys])
    return delays, dopplers, gains_merged


# ======================================================================
# 3. Learnable heads
# ======================================================================


class StrategyMLP(nn.Module):
    """Per-iteration 4 → 16 → 3 MLP producing multiplicative nudges on
    (λ_ls_factor, γ_x, pic_damp).  Output is small and centred at zero so the
    untrained model matches the classical defaults exactly."""

    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4, 16),
            nn.GELU(),
            nn.Linear(16, 3),
        )
        # Init last layer to ~0 so default output multipliers ≈ 1.
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, feats: torch.Tensor) -> torch.Tensor:
        # feats: (4,)  → nudges: (3,)
        # Clamp so nudges stay in [~0.5, ~2]
        raw = self.net(feats)
        return torch.tanh(raw) * 0.5           # multiplier = 1 + out ∈ [0.5, 1.5]


class SymbolRefiner(nn.Module):
    """Tiny 1D CNN (kernel=5) over (Re(x_soft), Im(x_soft), Re(r_data),
    Im(r_data), |h_col_energy|) → 2-channel delta added to x_soft before the
    final hard decision.  Initialised to produce zero delta."""

    def __init__(self, hidden: int = 16):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(5, hidden, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden, hidden, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden, 2, kernel_size=1),
        )
        # Zero-init last conv so the head is identity at start.
        nn.init.zeros_(self.conv[-1].weight)
        nn.init.zeros_(self.conv[-1].bias)

    def forward(self, x_soft_c: torch.Tensor, r_data_c: torch.Tensor,
                h_col_energy: torch.Tensor) -> torch.Tensor:
        # Inputs are (N,) complex or float; we build (1, 5, N) feature.
        conv_dtype = next(self.conv.parameters()).dtype
        feat = torch.stack([
            x_soft_c.real.to(conv_dtype),
            x_soft_c.imag.to(conv_dtype),
            r_data_c.real.to(conv_dtype),
            r_data_c.imag.to(conv_dtype),
            h_col_energy.to(conv_dtype),
        ], dim=0).unsqueeze(0)                  # (1, 5, N)
        delta = self.conv(feat).squeeze(0)      # (2, N)
        return torch.complex(delta[0], delta[1])


class PerIterSymbolRefiner(nn.Module):
    """B1 — a per-outer-iter symbol refiner.  One tiny CNN per outer iter t;
    the selected CNN runs inside the iter-t loop on ``(x_mp_t, residual_t,
    |h_col|²_t)`` and outputs ``Δx_t`` added to x_mp_t **before** symbol
    damping.  Zero-init produces identity (Δ=0) at start.

    Targets oracle_x headroom (DA-LS data noise): better x at iter-t →
    cleaner DA-LS input at iter (t+1) → better H next iter.
    """

    def __init__(self, n_iters: int = 5, hidden: int = 12):
        super().__init__()
        self.convs = nn.ModuleList([
            nn.Sequential(
                nn.Conv1d(5, hidden, kernel_size=5, padding=2),
                nn.GELU(),
                nn.Conv1d(hidden, 2, kernel_size=1),
            ) for _ in range(n_iters)
        ])
        for seq in self.convs:
            nn.init.zeros_(seq[-1].weight)
            nn.init.zeros_(seq[-1].bias)

    def forward(self, t: int, x_mp_c: torch.Tensor, r_data_c: torch.Tensor,
                h_col_energy: torch.Tensor) -> torch.Tensor:
        conv = self.convs[t]
        conv_dtype = next(conv.parameters()).dtype
        feat = torch.stack([
            x_mp_c.real.to(conv_dtype),
            x_mp_c.imag.to(conv_dtype),
            r_data_c.real.to(conv_dtype),
            r_data_c.imag.to(conv_dtype),
            h_col_energy.to(conv_dtype),
        ], dim=0).unsqueeze(0)                  # (1, 5, N)
        delta = conv(feat).squeeze(0)           # (2, N)
        return torch.complex(delta[0], delta[1])


class IterResidualSelector(nn.Module):
    """B2 — additive-residual iteration selector.

    Final output parametrised as::

        x_final = x_soft[T-1] + Σ_{t<T-1} α_t (x_soft[t] - x_soft[T-1])

    with α_t = sigmoid(MLP_t(sigma2, iter_idx/T, log|r_t|)).  At zero-init the
    MLP produces α_t = 0 (via zero last layer + pre-bias that puts sigmoid in
    the 0 regime — here we just use α = tanh(raw) so α=0 at raw=0).  Identity
    at init → matches classical exactly (only the final iterate). Training can
    shift mass toward earlier iters when later iters overshoot.

    Targets iter-5 overshoot headroom (#1 at 20 dB).
    """

    def __init__(self, n_iters: int = 5, hidden: int = 8):
        super().__init__()
        self.n_iters = n_iters
        self.mlps = nn.ModuleList([
            nn.Sequential(
                nn.Linear(3, hidden),
                nn.GELU(),
                nn.Linear(hidden, 1),
            ) for _ in range(n_iters - 1)
        ])
        for m in self.mlps:
            nn.init.zeros_(m[-1].weight)
            nn.init.zeros_(m[-1].bias)

    def forward(self, x_soft_list, sigma2: torch.Tensor,
                resnorms) -> torch.Tensor:
        if len(self.mlps) == 0 or len(x_soft_list) < 2:
            return x_soft_list[-1]
        mlp = self.mlps[0]
        mlp_dtype = next(mlp.parameters()).dtype
        mlp_device = next(mlp.parameters()).device

        x_base = x_soft_list[-1]                                   # (N,) complex
        sigma_log = sigma2.to(device=mlp_device, dtype=mlp_dtype
                              ).clamp_min(1e-30).log().clamp(min=-30, max=30)

        out = x_base.clone()
        for t in range(len(self.mlps)):
            r = resnorms[t] if t < len(resnorms) else resnorms[-1]
            r_log = r.to(device=mlp_device, dtype=mlp_dtype
                         ).clamp_min(1e-30).log().clamp(min=-30, max=30)
            feat = torch.stack([
                sigma_log,
                torch.tensor(float(t) / max(self.n_iters - 1, 1),
                             dtype=mlp_dtype, device=mlp_device),
                r_log,
            ])
            alpha = torch.tanh(self.mlps[t](feat))                # (1,) in (-1, 1), = 0 at init
            alpha_c = torch.complex(alpha.to(x_base.real.dtype),
                                    torch.zeros_like(alpha).to(x_base.real.dtype))
            delta = (x_soft_list[t] - x_base).to(x_base.dtype)
            out = out + alpha_c * delta
        return out


class ChannelTapCorrector(nn.Module):
    """CE-side residual head (B3, Codex Round-2 recommendation).

    Runs inside each outer iter immediately AFTER DA-LS solves for ``gains_S``
    (the complex tap coefficient vector of length ``P_actual``), before
    ``reconstruct_H_torch`` materialises H_hat.  The head consumes per-tap
    features and outputs a small additive correction ``Δg_i`` that modifies
    each ``gains_S[i]`` to close the bias in DA-LS caused by hard-decision
    symbol noise at high-path-count / fractional-Doppler regimes.

    Features per active tap i (after Dirichlet cluster expansion)::

        [Re(g_i), Im(g_i), |g_i|,
         Re(c_i), Im(c_i), |c_i|,      # c_i = A[:, i]^H · r  (residual projection)
         l_i / l_max,                  # delay index normalized
         k_i / k_max,                  # Doppler index normalized
         t / (T-1),                    # iter index normalized
         log sigma2,
         log ||r||^2 ]                 # 11 features

    DeepSets-style:
        encoder  : 11 -> hidden -> hidden                 (SiLU)
        mean-pool over active taps                         -> context (hidden,)
        decoder  : concat(enc, context) -> hidden -> 2    (SiLU)

    Output scaling: ``Δg_i = scale * tanh( out_i )`` to prevent blow-up.
    Zero-init final decoder layer keeps Δg_i = 0 at start (identity).
    """

    def __init__(self, n_iters: int = 5, hidden: int = 32,
                 init_scale: float = 0.1):
        super().__init__()
        self.n_iters = n_iters
        self.init_scale = float(init_scale)
        # One head shared across iters but conditioned on iter via feature.
        self.encoder = nn.Sequential(
            nn.Linear(11, hidden),
            nn.SiLU(),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(2 * hidden, hidden),
            nn.SiLU(),
            nn.Linear(hidden, 2),
        )
        # Zero-init final linear so at init Δg_i = 0.
        nn.init.zeros_(self.decoder[-1].weight)
        nn.init.zeros_(self.decoder[-1].bias)

    def forward(self,
                gains_S: torch.Tensor,              # (P,) complex
                residual_proj: torch.Tensor,        # (P,) complex  A^H r
                support_delays: torch.Tensor,       # (P,) long
                support_dopplers: torch.Tensor,     # (P,) long
                sigma2: torch.Tensor,               # scalar real
                resnorm: torch.Tensor,              # scalar real
                t: int, T: int,
                l_max: int, k_max: int) -> torch.Tensor:
        P = gains_S.numel()
        if P == 0:
            return torch.zeros_like(gains_S)
        enc_dtype = next(self.encoder.parameters()).dtype
        enc_device = next(self.encoder.parameters()).device

        g = gains_S
        c = residual_proj

        def _abs(x):
            return x.abs().to(enc_dtype)

        feats_list = [
            g.real.to(enc_dtype), g.imag.to(enc_dtype), _abs(g),
            c.real.to(enc_dtype), c.imag.to(enc_dtype), _abs(c),
            (support_delays.to(enc_dtype) / max(l_max, 1)),
            (support_dopplers.to(enc_dtype) / max(k_max, 1)),
        ]
        feats = torch.stack(feats_list, dim=1)  # (P, 8)

        sigma_log = sigma2.to(enc_device, enc_dtype).clamp_min(1e-30).log().clamp(-30, 30)
        r_log = resnorm.to(enc_device, enc_dtype).clamp_min(1e-30).log().clamp(-30, 30)
        t_norm = torch.tensor(float(t) / max(T - 1, 1), device=enc_device, dtype=enc_dtype)

        scalar_feats = torch.stack([t_norm, sigma_log, r_log])   # (3,)
        scalar_feats = scalar_feats.unsqueeze(0).expand(P, -1)   # (P, 3)

        x = torch.cat([feats, scalar_feats], dim=1)              # (P, 11)
        h = self.encoder(x)                                      # (P, hidden)
        pooled = h.mean(dim=0, keepdim=True).expand_as(h)        # (P, hidden)
        dec_in = torch.cat([h, pooled], dim=1)                   # (P, 2*hidden)
        raw = self.decoder(dec_in)                               # (P, 2)
        delta = self.init_scale * torch.tanh(raw)
        delta_c = torch.complex(delta[:, 0], delta[:, 1])
        return delta_c.to(gains_S.dtype)


class OffSupportCorrelationHead(nn.Module):
    """C1 — CE-side add-a-path correction head (Oracle Loop-6 Phase-A recipe).

    Motivation. Under hard-decision operation, the active-support residual
    projection ``A_active^H r`` is numerically dead (near zero at LS optimum).
    The missed signal sits on OFF-support atoms of the data-matched sensing
    dictionary. This head picks the top-M off-support candidate atoms by
    |Φ_det^H r|, computes a physics-based provisional gain for each
    (b_j = c_j / (||a_j||² + λ_ls)), and learns a small multiplicative
    scaling via a shared MLP.

    Forward flow (called from ``ClassicalJointUnrolled.forward`` at t>=1,
    immediately after DA-LS and before ``reconstruct_H_torch``):

        x_hd_det   = hard_qpsk(x_soft.detach())
        A_full_det = sensing_matrix(x_pilot + x_hd_det)            # detached
        r_det      = y - A_active @ g_new.detach()                 # detached
        c_full     = A_full_det^H r_det                            # detached
        mask active columns, take top M by |c_full|                 # detached
        b_j        = c_j / (||a_j||² + λ_ls)                       # detached
        feats_j    = [Re(b_j), Im(b_j), |b_j|, log|c_j|,
                      l_j/l_max, k_j/k_max, d_nn,
                      t/(T-1), log σ²_eff, log ||r_det||²,
                      detector margin]                              # 11 feats
        α_j        = MLP(feats_j)                                   # LEARNABLE
        Δg_j       = 0.5 * tanh(α_j) * b_j
        H_corr     = reconstruct_H(candidate (l_j,k_j), Δg_j)
        H_new      = H_active + H_corr

    Zero-init last MLP layer → Δg_j = 0 at init → identity w.r.t. the
    classical receiver. Gradient flows ONLY through α_j (b_j, r_det, A_full,
    and active-support g_new are all detached), so the head cannot perturb
    the LS solve itself.
    """

    def __init__(self, n_iters: int = 5, hidden: int = 32,
                 top_m: int = 12, delta_scale: float = 0.5):
        super().__init__()
        self.n_iters = n_iters
        self.top_m = int(top_m)
        self.delta_scale = float(delta_scale)
        self.mlp = nn.Sequential(
            nn.Linear(11, hidden),
            nn.SiLU(),
            nn.Linear(hidden, hidden),
            nn.SiLU(),
            nn.Linear(hidden, 1),
        )
        # Zero-init final layer so α_j = 0 at init ⇒ Δg_j = 0.
        nn.init.zeros_(self.mlp[-1].weight)
        nn.init.zeros_(self.mlp[-1].bias)

    def propose_candidates(self, Phi_full: torch.Tensor, r_det: torch.Tensor,
                           active_cols_set: set,
                           lambda_ls: float,
                           ) -> Tuple[torch.Tensor, torch.Tensor,
                                       torch.Tensor, torch.Tensor]:
        """Returns (cand_col_idx, c_cand, b_cand, col_sqnorms).

        All returned tensors are DETACHED from the autograd graph.
        """
        with torch.no_grad():
            # (Q,) complex projections and per-column squared norms.
            c_full = Phi_full.conj().T @ r_det          # (Q,)
            col_norms_sq = (Phi_full.abs() ** 2).sum(dim=0)  # (Q,) real
            mag = c_full.abs()
            # Mask active columns.
            if active_cols_set:
                active_idx = torch.tensor(sorted(list(active_cols_set)),
                                          dtype=torch.long, device=mag.device)
                mag.index_fill_(0, active_idx, -1.0)
            topk = min(self.top_m, int((mag > 0).sum().item()))
            if topk <= 0:
                return (torch.zeros(0, dtype=torch.long, device=mag.device),
                        torch.zeros(0, dtype=c_full.dtype, device=mag.device),
                        torch.zeros(0, dtype=c_full.dtype, device=mag.device),
                        torch.zeros(0, dtype=col_norms_sq.dtype, device=mag.device))
            vals, idxs = torch.topk(mag, k=topk, sorted=False)
            c_cand = c_full[idxs]
            cn_cand = col_norms_sq[idxs].clamp_min(1e-12)
            b_cand = c_cand / (cn_cand.to(c_full.dtype) + float(lambda_ls))
        return idxs, c_cand, b_cand, cn_cand

    def forward(self,
                b_cand: torch.Tensor,         # (M,) complex, detached
                c_cand: torch.Tensor,         # (M,) complex, detached
                cand_col_idx: torch.Tensor,   # (M,) long
                support_delays: torch.Tensor, # (P_act,) long
                support_dopplers: torch.Tensor, # (P_act,) long
                k_max: int,
                l_max: int,
                sigma2: torch.Tensor,
                r_norm_sq: torch.Tensor,
                detector_margin: torch.Tensor,
                t: int, T: int) -> torch.Tensor:
        """Return Δg_cand (M,) complex with gradient through the MLP only."""
        K = 2 * k_max + 1
        if cand_col_idx.numel() == 0:
            return torch.zeros(0, dtype=b_cand.dtype, device=b_cand.device)
        mlp_dtype = next(self.mlp.parameters()).dtype
        mlp_device = next(self.mlp.parameters()).device

        # Decode (l_j, k_j) from column index (matches expand_cluster_support)
        l_j = cand_col_idx // K
        k_j = (cand_col_idx % K) - k_max

        # Nearest-active distance in (l,k) space.
        if support_delays.numel() > 0:
            # (M, P_act) L1 distance in (l, k) grid.
            dl = (l_j.unsqueeze(1) - support_delays.unsqueeze(0)).abs().to(mlp_dtype)
            dk = (k_j.unsqueeze(1) - support_dopplers.unsqueeze(0)).abs().to(mlp_dtype)
            d_lk = (dl + dk).min(dim=1).values             # (M,)
        else:
            d_lk = torch.full((cand_col_idx.numel(),), float(l_max + k_max),
                              dtype=mlp_dtype, device=mlp_device)

        b_re = b_cand.real.to(mlp_dtype)
        b_im = b_cand.imag.to(mlp_dtype)
        b_ab = b_cand.abs().to(mlp_dtype)
        log_c = c_cand.abs().clamp_min(1e-30).log().to(mlp_dtype)
        l_norm = (l_j.to(mlp_dtype) / max(l_max, 1))
        k_norm = (k_j.to(mlp_dtype) / max(k_max, 1))
        d_nn = d_lk / max(l_max + k_max, 1)
        t_norm = torch.full_like(b_re, float(t) / max(T - 1, 1))
        log_sigma = sigma2.to(mlp_device, mlp_dtype).clamp_min(1e-30).log().clamp(-30, 30)
        log_rnorm = r_norm_sq.to(mlp_device, mlp_dtype).clamp_min(1e-30).log().clamp(-30, 30)
        dm = detector_margin.to(mlp_device, mlp_dtype).clamp_min(-30).clamp_max(30)

        scalar_feats = torch.stack([log_sigma, log_rnorm, dm])    # (3,)
        scalar_feats = scalar_feats.unsqueeze(0).expand(b_re.numel(), -1)

        feats = torch.stack([b_re, b_im, b_ab, log_c,
                              l_norm, k_norm, d_nn, t_norm], dim=1)  # (M, 8)
        feats = torch.cat([feats, scalar_feats], dim=1)              # (M, 11)
        alpha = self.mlp(feats).squeeze(-1)                         # (M,)
        alpha_c = torch.complex(alpha.to(b_cand.real.dtype),
                                torch.zeros_like(alpha).to(b_cand.real.dtype))
        delta_g = self.delta_scale * torch.tanh(alpha_c.real).to(b_cand.dtype) * b_cand
        # Note: tanh on real alpha; complex scaling via b_cand.
        return delta_g


class CandidateActiveRelationHead(nn.Module):
    """C2-rel — Loop-9 support-repair head.

    Per Oracle GPT-5.4-pro Loop-9 Round-1 recipe (2026-04-22):
      - Insert ONCE at t==0, AFTER omp_sparse_torch, BEFORE expand_cluster_support.
      - Build candidate set: top-M off-support atoms by PRE-LS pilot MF `|Phi^H y|`.
      - Per-candidate feature u_j (7-dim): log|phi_j^H y|, margin_to_Pth_OMP_pick,
          l_j/l_max, k_j/k_max, d_l_nn/l_max, d_k_nn/k_max, log sigma2.
      - Per-pair v_{j,s} (6-dim) for each s in raw S_omp: coh_js,
          log(|alpha_s|*coh_js+eps), dl/l_max, dk/k_max, 1{dl=0}, 1{|dk|<=2}.
      - pair MLP 6->16->16 SiLU, max + mean pool over s -> 32-dim.
      - scorer MLP (7+16+16=39)->16->1 SiLU, zero-init final weights, bias=-8.
      - Inference: add candidates with logit > 0, cap at K_add_max.
      - Union support, pilot-only LS, prune back to P by |gain|, refit LS.

    Identity-at-init: final scorer bias = -8 and zero-init final weight -> no
    candidate scores above 0 -> no augmentation -> classical OMP path unchanged.

    Training: cached supervised. Labels y_j=1 iff j in (S_oracle \\ S_omp).
    Loss = BCE_miss + 0.5 * rank_loss(pos > hard_neg). No gradient through LS or BP.
    """

    def __init__(self, top_m: int = 48, k_add_max: int = 4,
                 pair_hidden: int = 16, scorer_hidden: int = 16,
                 logit_bias_init: float = -8.0):
        super().__init__()
        self.top_m = int(top_m)
        self.k_add_max = int(k_add_max)
        # Safety-valve toggles (Loop-10). Defaults preserve Loop-9 behaviour
        # so no existing ckpt eval changes until enabled via setter.
        self._safe_swap = False
        self._safe_swap_eps_r = 0.01       # relative residual reduction threshold
        self._safe_swap_k_cap = None        # override k_add_max if set
        self._safe_swap_gain_margin = 0.0   # require |g_new| >= (1+margin)*min(|g_omp|)
        # F1 (Loop-10 visibility probe): skip prune-by-|gain| after union-LS so
        # the full |S_omp|+K_add support enters DA-LS. Keeps all learned adds
        # (prune step was evicting some useful candidates whose gains happened
        # to be lower than OMP picks).
        self._no_prune_after_union = False
        # F2-P (Loop-11 Oracle R1 recipe): multi-round refinement +
        # refresh-pool + defer-prune-until-final + protect-top-r-adds.
        # Defaults preserve Loop-10 single-pass behaviour.
        self._refine_rounds = 0          # 0 = current Loop-9/10 single pass
        self._cand_topm_override = None  # if set, overrides self.top_m
        self._defer_prune = False        # only prune after the last round
        self._protect_added = 0          # force-keep top-r learned adds at final prune
        # Pair MLP over 6-d pair features; layer 2 outputs pair_hidden-d embed.
        self.pair_mlp = nn.Sequential(
            nn.Linear(6, pair_hidden),
            nn.SiLU(),
            nn.Linear(pair_hidden, pair_hidden),
            nn.SiLU(),
        )
        # Scorer MLP over [u_j (7) || max_pool (pair_hidden) || mean_pool (pair_hidden)].
        scorer_in = 7 + 2 * pair_hidden
        self.scorer = nn.Sequential(
            nn.Linear(scorer_in, scorer_hidden),
            nn.SiLU(),
            nn.Linear(scorer_hidden, 1),
        )
        # Zero-init final weights; set bias to -8 so at init every logit = -8 < 0
        # -> no candidate is added -> bit-exact classical support.
        nn.init.zeros_(self.scorer[-1].weight)
        nn.init.constant_(self.scorer[-1].bias, float(logit_bias_init))
        self._scorer_dim = scorer_in
        self._pair_hidden = pair_hidden

    def build_features(
        self,
        Phi: torch.Tensor,          # (N, Q) complex
        y_daft: torch.Tensor,       # (N,) complex
        support_idx: List[int],     # raw OMP picks (len = P)
        g_ls: torch.Tensor,         # (P,) complex — LS gains on raw OMP support
        sigma2: torch.Tensor,       # scalar real
        l_max: int, k_max: int,
        top_m_override: Optional[int] = None,  # F2-P: refresh-pool with bigger M
    ) -> Dict[str, torch.Tensor]:
        """Compute u_j (M,7), v_{j,s} (M,P,6), and cand_cols (M,). All detached.

        Returns empty (M=0) dict when P==0 or no valid off-support candidates.
        """
        device = Phi.device
        K_per_l = 2 * k_max + 1
        Q = Phi.shape[1]
        P = len(support_idx)
        top_m_eff = int(top_m_override) if top_m_override is not None else self.top_m
        with torch.no_grad():
            Phi_H = Phi.conj().T
            phi_proj_y = Phi_H @ y_daft                       # (Q,) complex
            phi_proj_y_abs = phi_proj_y.abs()                 # (Q,) real

            # Mask out active support
            mag = phi_proj_y_abs.clone()
            if P > 0:
                idx_tensor = torch.tensor(support_idx, dtype=torch.long,
                                           device=device)
                mag.index_fill_(0, idx_tensor, -1.0)
            pos_count = int((mag > 0).sum().item())
            topM = min(top_m_eff, pos_count)
            if topM <= 0 or P == 0:
                empty = torch.zeros(0, dtype=torch.long, device=device)
                return dict(cand_cols=empty)

            topv, topi = torch.topk(mag, k=topM, sorted=False)
            # Sort descending for determinism
            order = torch.argsort(-topv)
            cand_cols = topi[order].to(torch.long)             # (M,)

            # ---- Candidate-local u_j (M, 7) ------------------------------
            l_c = (cand_cols // K_per_l).to(torch.long)
            k_c = (cand_cols % K_per_l).to(torch.long) - k_max
            log_mf = phi_proj_y_abs[cand_cols].clamp_min(1e-30).log()
            # Margin vs P-th OMP pick (last raw OMP pick)
            log_margin_ref = phi_proj_y_abs[support_idx[-1]].clamp_min(1e-30).log()
            margin = log_mf - log_margin_ref

            # Nearest-active distance in (l, k)
            supp_tensor = torch.tensor(support_idx, dtype=torch.long,
                                        device=device)
            l_s = (supp_tensor // K_per_l).to(torch.long)
            k_s = (supp_tensor % K_per_l).to(torch.long) - k_max
            dl_mat = (l_c.unsqueeze(1) - l_s.unsqueeze(0)).abs()  # (M, P)
            dk_mat = (k_c.unsqueeze(1) - k_s.unsqueeze(0)).abs()  # (M, P)
            d_sum = dl_mat + dk_mat
            j_nn = d_sum.argmin(dim=1)
            rng = torch.arange(dl_mat.shape[0], device=device)
            d_l_nn = dl_mat[rng, j_nn]
            d_k_nn = dk_mat[rng, j_nn]

            log_sig = sigma2.clamp_min(1e-30).log()
            feat_dtype = torch.float32
            u = torch.stack([
                log_mf.to(feat_dtype),
                margin.to(feat_dtype),
                l_c.to(feat_dtype) / max(l_max, 1),
                k_c.to(feat_dtype) / max(k_max, 1),
                d_l_nn.to(feat_dtype) / max(l_max, 1),
                d_k_nn.to(feat_dtype) / max(k_max, 1),
                log_sig.to(feat_dtype).expand(topM),
            ], dim=1)                                                 # (M, 7)

            # ---- Pair features v_{j,s} (M, P, 6) -------------------------
            phi_c = Phi[:, cand_cols]                                 # (N, M)
            phi_s = Phi[:, supp_tensor]                               # (N, P)
            col_norms_all = torch.linalg.vector_norm(Phi, dim=0)       # (Q,)
            cand_norms = col_norms_all[cand_cols].clamp_min(1e-30)     # (M,)
            supp_norms = col_norms_all[supp_tensor].clamp_min(1e-30)   # (P,)
            gram = phi_c.conj().T @ phi_s                              # (M, P) complex
            coh = gram.abs() / (cand_norms.unsqueeze(1) * supp_norms.unsqueeze(0))
            alpha_mag = g_ls.abs().to(coh.dtype)                       # (P,)
            alpha_coh = alpha_mag.unsqueeze(0) * coh                   # (M, P)
            log_alpha_coh = alpha_coh.clamp_min(1e-30).log()
            dl_n = dl_mat.to(feat_dtype) / max(l_max, 1)
            dk_n = dk_mat.to(feat_dtype) / max(k_max, 1)
            ind_dl0 = (dl_mat == 0).to(feat_dtype)
            ind_dk_le2 = (dk_mat <= 2).to(feat_dtype)
            v = torch.stack([coh.to(feat_dtype),
                              log_alpha_coh.to(feat_dtype),
                              dl_n, dk_n, ind_dl0, ind_dk_le2],
                             dim=-1)                                    # (M, P, 6)
        return dict(u=u, v=v, cand_cols=cand_cols)

    def score(self, u: torch.Tensor, v: torch.Tensor,
              mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Forward pass over precomputed features.
        u: (..., M, 7) float
        v: (..., M, P, 6) float
        mask: optional (..., M, P) bool, True for real pair entries, False for
            padded. If None, all entries are treated as real.
        Returns logits (..., M).
        """
        e = self.pair_mlp(v)                                           # (..., M, P, H)
        if mask is not None:
            # Broadcast mask to embedding dim.
            m = mask.unsqueeze(-1)                                      # (..., M, P, 1)
            # Max-pool: replace padded with -inf so they never win.
            very_neg = torch.finfo(e.dtype).min / 4
            e_max = torch.where(m, e, torch.full_like(e, very_neg))
            pool_max = e_max.max(dim=-2).values                         # (..., M, H)
            # Mean-pool: sum over real entries / count of real entries.
            e_sum = torch.where(m, e, torch.zeros_like(e)).sum(dim=-2)
            denom = mask.float().sum(dim=-1, keepdim=False).clamp_min(1.0)
            pool_mean = e_sum / denom.unsqueeze(-1)
        else:
            pool_max = e.max(dim=-2).values                            # (..., M, H)
            pool_mean = e.mean(dim=-2)                                 # (..., M, H)
        feats = torch.cat([u, pool_max, pool_mean], dim=-1)             # (..., M, 7+2H)
        logits = self.scorer(feats).squeeze(-1)                         # (..., M)
        return logits

    @torch.no_grad()
    def select_additions(self, logits: torch.Tensor,
                         cand_cols: torch.Tensor,
                         tau: float = 0.0) -> torch.Tensor:
        """Return columns with logit > tau, capped at k_add_max (sorted by logit).

        tau is the commit threshold (Loop-9 Round-3: SNR-adaptive via lookup).
        """
        if logits.numel() == 0:
            return torch.zeros(0, dtype=torch.long, device=cand_cols.device)
        positive_mask = logits > float(tau)
        if not positive_mask.any():
            return torch.zeros(0, dtype=torch.long, device=cand_cols.device)
        pos_logits = logits[positive_mask]
        pos_cols = cand_cols[positive_mask]
        k = min(self.k_add_max, pos_logits.numel())
        topv, topi = torch.topk(pos_logits, k=k, sorted=True)
        return pos_cols[topi]

    @torch.no_grad()
    def apply_sequential_add_test(
        self,
        Phi: torch.Tensor,
        y_daft: torch.Tensor,
        support_idx: List[int],
        logits: torch.Tensor,
        cand_cols: torch.Tensor,
        residual_reduction_threshold: float = 0.01,
        k_add_cap: Optional[int] = None,
        gain_margin: float = 0.0,
    ) -> Tuple[List[int], torch.Tensor]:
        """Sequential add-and-test (Loop-9 Oracle R3 safety valve).

        Start from the OMP support; walk candidates in descending logit order;
        for each one, tentatively add to support and refit pilot-only LS; keep
        only if residual norm reduces by at least
        ``residual_reduction_threshold`` (relative). Stop when k_add_cap
        accepted. Gains on the final support are returned.

        This is self-regulating across SNR: at very high SNR the OMP residual
        is already tiny so very few candidates meet the threshold; at low SNR
        the threshold is easy to clear so the head augments aggressively.

        Returns:
            final_support: List[int] — support indices (OMP ∪ accepted additions)
            g_final: torch.Tensor (len(final_support),) complex — LS gains
        """
        device = Phi.device
        cdtype = Phi.dtype
        S = [int(i) for i in support_idx]

        Phi_S = Phi[:, S]
        g_S = torch.linalg.lstsq(Phi_S, y_daft.unsqueeze(-1)).solution.squeeze(-1)
        r = y_daft - Phi_S @ g_S
        r_norm2 = float((r.conj() * r).real.sum().item())
        r_norm2 = max(r_norm2, 1e-30)

        k_cap = int(self.k_add_max if k_add_cap is None else k_add_cap)
        if k_cap <= 0 or logits.numel() == 0:
            return S, g_S

        # Descending logit order over candidates; skip any already in S (shouldn't
        # happen since candidates are top-M off-support by construction, but be
        # defensive).
        order = torch.argsort(logits, descending=True)
        added = 0
        for idx in order.tolist():
            if added >= k_cap:
                break
            col = int(cand_cols[idx].item())
            if col in S:
                continue
            S_new = S + [col]
            Phi_Snew = Phi[:, S_new]
            g_new = torch.linalg.lstsq(
                Phi_Snew, y_daft.unsqueeze(-1)).solution.squeeze(-1)
            r_new = y_daft - Phi_Snew @ g_new
            r_new_norm2 = float((r_new.conj() * r_new).real.sum().item())
            # Test (a): relative residual reduction >= eps_r.
            residual_ok = (r_new_norm2 < r_norm2 *
                           (1.0 - float(residual_reduction_threshold)))
            # Test (b): new atom's |gain| beats weakest OMP atom's |gain| by
            # (1 + gain_margin). Only enforced when gain_margin > 0.
            gain_ok = True
            if gain_margin > 0.0 and len(support_idx) > 0:
                n_omp = len(support_idx)
                g_omp_new = g_new[:n_omp]       # refit OMP gains
                g_cand = g_new[-1]              # candidate gain (last added)
                weakest_omp = g_omp_new.abs().min().item()
                gain_ok = (g_cand.abs().item() >=
                           weakest_omp * (1.0 + float(gain_margin)))
            if residual_ok and gain_ok:
                S = S_new
                r_norm2 = max(r_new_norm2, 1e-30)
                g_S = g_new
                added += 1
            else:
                # Stop at first reject — later candidates have lower logit so
                # they are less likely to help. This matches classical greedy
                # forward-selection OMP stop rule.
                break
        return S, g_S

    def tau_for_sigma2(self, sigma2: torch.Tensor) -> float:
        """Lookup tau from SNR. Loop-9 R3 Oracle R2 recipe: 4-knot table
        indexed by integer SNR in dB (10/15/20/25) with linear interpolation
        clipped to [snr_knots[0], snr_knots[-1]] outside.

        If self.tau_lookup is unset, defaults to 0.0 (classical threshold).
        """
        lookup = getattr(self, '_tau_lookup', None)
        if lookup is None:
            return 0.0
        snr_db = float(-10.0 * torch.log10(sigma2.clamp_min(1e-30)).item())
        snrs = sorted(lookup.keys())
        if snr_db <= snrs[0]:
            return float(lookup[snrs[0]])
        if snr_db >= snrs[-1]:
            return float(lookup[snrs[-1]])
        for i in range(len(snrs) - 1):
            if snrs[i] <= snr_db <= snrs[i + 1]:
                t0 = float(lookup[snrs[i]])
                t1 = float(lookup[snrs[i + 1]])
                w = (snr_db - snrs[i]) / max(snrs[i + 1] - snrs[i], 1e-9)
                return t0 + w * (t1 - t0)
        return 0.0

    def set_tau_lookup(self, lookup):
        """Install an SNR-dB -> tau table. Use None to disable."""
        if lookup is None:
            self._tau_lookup = None
        else:
            self._tau_lookup = {int(k): float(v) for k, v in lookup.items()}

    def set_safe_swap(
        self,
        enabled: bool = True,
        eps_r: float = 0.01,
        k_cap: Optional[int] = None,
        gain_margin: float = 0.0,
    ):
        """Enable sequential add-and-test safety valve (Loop-10 / Oracle R1).

        When enabled, the inference path walks candidates in descending logit
        order and tentatively adds each one to the OMP support; it keeps the
        add only if BOTH:
          (a) pilot residual norm reduces by >= ``eps_r`` fraction (e.g.
              ``eps_r=1e-3`` = 0.1 % relative reduction), AND
          (b) the new atom's |gain| exceeds the weakest OMP atom's |gain|
              by at least (1 + gain_margin) multiplier.
        Stops at first reject or when ``k_cap`` (defaults to ``k_add_max``)
        accepted. OMP atoms are always kept.

        At high SNR (low noise, OMP already solved), ``eps_r`` is hard to
        clear so nothing is added -> head becomes no-op. At low SNR the
        threshold is easy to clear -> additions happen. Self-regulating.

        Set ``enabled=False`` to revert to the Loop-9 force-topk / union-then-
        prune-by-|gain| behavior.
        """
        self._safe_swap = bool(enabled)
        self._safe_swap_eps_r = float(eps_r)
        self._safe_swap_k_cap = int(k_cap) if k_cap is not None else None
        self._safe_swap_gain_margin = float(gain_margin)

    def set_refine_config(
        self,
        refine_rounds: int = 0,
        cand_topm: Optional[int] = None,
        defer_prune: bool = False,
        protect_added: int = 0,
    ):
        """Configure F2-P recipe (Loop-11 Oracle R1 top-1 pick).

        F2-P combines four ideas attacking the one-shot union-then-prune
        bottleneck identified by Oracle:

        1. ``refine_rounds=2``  — after the initial OMP pick + first C2-rel
           proposal, re-run feature build / scoring on the augmented support so
           the second-round candidate pool excludes round-1's picks (refresh-
           pool). This broadens effective coverage of the off-support atoms.
        2. ``cand_topm=96``    — bigger candidate pool per round to attack the
           "candidate-set bottleneck" hypothesis (mechanism #1 in Oracle R1 Q3).
        3. ``defer_prune``     — skip prune-by-|gain| between rounds; only
           prune (back to ``cfg.n_paths``) once at the very end. Avoids
           evicting a useful learned add before round-2 has a chance to use it.
        4. ``protect_added``   — at the final prune, force-keep the top-r
           learned additions (ranked by their score logit) regardless of |gain|.
           Directly attacks mechanism #2 in Oracle R1 Q3.

        Defaults preserve the Loop-9/10 single-pass behaviour.
        """
        self._refine_rounds = int(refine_rounds)
        self._cand_topm_override = int(cand_topm) if cand_topm is not None else None
        self._defer_prune = bool(defer_prune)
        self._protect_added = int(protect_added)

    @torch.no_grad()
    def apply_f2p_refinement(
        self,
        Phi: torch.Tensor,           # (N, Q) complex
        y_daft: torch.Tensor,        # (N,) complex
        support_idx: List[int],      # raw OMP picks (size cfg.n_paths)
        sigma2: torch.Tensor,        # scalar real
        l_max: int,
        k_max: int,
        n_paths: int,                # final support cap = cfg.n_paths
    ) -> Tuple[List[int], torch.Tensor]:
        """F2-P entry point. Implements Oracle R1 Loop-11 recipe.

        Returns:
            final_support: List[int] — pruned support of size <= n_paths
            g_final: torch.Tensor (len(final_support),) complex — pilot LS gains
        """
        device = Phi.device
        cdtype = Phi.dtype
        S = list(int(i) for i in support_idx)
        added_hist: List[Tuple[int, float]] = []  # (col, logit)

        n_rounds = max(int(self._refine_rounds), 1)
        cand_topm = self._cand_topm_override if self._cand_topm_override is not None else self.top_m
        defer_prune = bool(self._defer_prune)

        for rr in range(n_rounds):
            if len(S) == 0:
                break
            Phi_S = Phi[:, S]
            g_ls = torch.linalg.lstsq(Phi_S, y_daft.unsqueeze(-1)).solution.squeeze(-1)
            feats = self.build_features(
                Phi, y_daft, S, g_ls, sigma2, l_max, k_max,
                top_m_override=cand_topm,
            )
            cand_cols = feats.get('cand_cols',
                                   torch.zeros(0, dtype=torch.long, device=device))
            if cand_cols.numel() == 0:
                break
            logits = self.score(feats['u'], feats['v'])
            tau = self.tau_for_sigma2(sigma2)
            adds = self.select_additions(logits, cand_cols, tau=float(tau))
            if adds.numel() == 0:
                break
            # Track per-add logit for final protect-set ranking
            S_set = set(S)
            for a in adds.tolist():
                if a in S_set:
                    continue
                m = (cand_cols == a).nonzero(as_tuple=True)[0]
                lg = float(logits[m[0]].item()) if m.numel() > 0 else float('nan')
                added_hist.append((int(a), lg))
                S.append(int(a))
                S_set.add(int(a))
            # Deferred-prune: if disabled, prune to n_paths between rounds
            # (legacy intra-round prune behaviour, but F2-P expects
            # defer_prune=True so this path mostly stays inactive).
            if not defer_prune and len(S) > n_paths:
                Phi_U = Phi[:, S]
                g_u = torch.linalg.lstsq(
                    Phi_U, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                _, topi = torch.topk(g_u.abs(), k=n_paths, sorted=False)
                topi_sorted, _ = torch.sort(topi)
                S = [S[int(i.item())] for i in topi_sorted]

        # Final pilot-LS on augmented support
        if len(S) == 0:
            return S, torch.zeros(0, dtype=cdtype, device=device)
        Phi_S_full = Phi[:, S]
        g_full = torch.linalg.lstsq(
            Phi_S_full, y_daft.unsqueeze(-1)).solution.squeeze(-1)

        if len(S) <= n_paths:
            return S, g_full

        # Final prune with optional protect-top-r-added
        protect_cols = set()
        if self._protect_added > 0 and added_hist:
            ranked = sorted(added_hist, key=lambda t: -t[1])
            for col, _ in ranked:
                if col in S and col not in protect_cols:
                    protect_cols.add(col)
                if len(protect_cols) >= self._protect_added:
                    break

        # Indices in S of protected and non-protected positions
        protect_pos = [i for i, c in enumerate(S) if c in protect_cols]
        non_protect_pos = [i for i, c in enumerate(S) if c not in protect_cols]
        n_to_pick = max(0, n_paths - len(protect_pos))
        if n_to_pick > 0 and len(non_protect_pos) > 0:
            np_tensor = torch.tensor(non_protect_pos, dtype=torch.long, device=device)
            gains_np = g_full[np_tensor].abs()
            n_to_pick = min(n_to_pick, np_tensor.numel())
            _, topi = torch.topk(gains_np, k=n_to_pick, sorted=False)
            kept_non_protect = [int(np_tensor[int(i.item())].item()) for i in topi]
        else:
            kept_non_protect = []
        keep_pos = sorted(set(protect_pos) | set(kept_non_protect))
        kept_S = [S[i] for i in keep_pos]
        Phi_K = Phi[:, kept_S]
        g_kept = torch.linalg.lstsq(
            Phi_K, y_daft.unsqueeze(-1)).solution.squeeze(-1)
        return kept_S, g_kept


class LearnableScalars(nn.Module):
    """Per-iteration softplus / sigmoid-reparameterised scalar hparams.

    ``T`` is the number of outer iterations.  For each iteration we keep
    (γ_h, γ_x, λ_ls_factor, τ_rel, τ_σ, pic_damp) initialised to classical
    defaults.  ``.as_floats(t)`` returns a dict of floats for iteration t
    with appropriate activations so the values stay in their natural ranges.

    Optional safety clamp on ``lambda_ls_factor`` (``lam_ls_clip``) bounds
    deviation from classical default (1e-3) to within ~1 decade; the classical
    default sits inside the interval so identity at init is preserved.
    """

    def __init__(self, T: int, defaults: ClassicalJointConfig,
                 lam_ls_clip: Optional[Tuple[float, float]] = None):
        super().__init__()
        self.T = T
        self._inv_sigmoid = lambda v: math.log(v / (1.0 - v))
        self._inv_softplus = lambda v: math.log(math.expm1(v))
        self.lam_ls_clip = lam_ls_clip  # (lo, hi) or None

        # Ranges: γ_h, γ_x, pic_damp ∈ (0, 1) → sigmoid
        #         λ_ls_factor, τ_rel, τ_σ ∈ (0, ∞) → softplus
        gamma_h_raw = torch.full((T,), self._inv_sigmoid(defaults.gamma_h))
        gamma_x_raw = torch.full((T,), self._inv_sigmoid(defaults.gamma_x))
        pic_damp_raw = torch.full((T,), self._inv_sigmoid(defaults.pic_damp))
        lam_raw = torch.full((T,), self._inv_softplus(defaults.lambda_ls_factor))
        tau_rel_raw = torch.full((T,), self._inv_softplus(defaults.tau_h_factor))
        tau_sig_raw = torch.full((T,), self._inv_softplus(defaults.tau_h_sigma_factor))

        self.gamma_h_raw = nn.Parameter(gamma_h_raw)
        self.gamma_x_raw = nn.Parameter(gamma_x_raw)
        self.pic_damp_raw = nn.Parameter(pic_damp_raw)
        self.lam_raw = nn.Parameter(lam_raw)
        self.tau_rel_raw = nn.Parameter(tau_rel_raw)
        self.tau_sig_raw = nn.Parameter(tau_sig_raw)

    def for_iter(self, t: int) -> Dict[str, torch.Tensor]:
        lam = F.softplus(self.lam_raw[t])
        if self.lam_ls_clip is not None:
            lo, hi = self.lam_ls_clip
            lam = torch.clamp(lam, min=float(lo), max=float(hi))
        return dict(
            gamma_h=torch.sigmoid(self.gamma_h_raw[t]),
            gamma_x=torch.sigmoid(self.gamma_x_raw[t]),
            pic_damp=torch.sigmoid(self.pic_damp_raw[t]),
            lambda_ls_factor=lam,
            tau_h_factor=F.softplus(self.tau_rel_raw[t]),
            tau_h_sigma_factor=F.softplus(self.tau_sig_raw[t]),
        )


# ======================================================================
# 4. Main receiver
# ======================================================================


class ClassicalJointUnrolled(nn.Module):
    """Differentiable unrolling of ``joint_omp_mp_iterative``.

    Parameters
    ----------
    cfg : ClassicalJointConfig
    learnable_heads : tuple of str, any subset of
        ``('scalars', 'strategy', 'symbol_refiner')``.  Empty tuple gives a
        pure torch replica of the NumPy baseline.

    Forward inputs / outputs — see ``forward``.
    """

    def __init__(self, cfg: ClassicalJointConfig,
                 learnable_heads: Tuple[str, ...] = (),
                 use_soft_decisions: bool = False):
        super().__init__()
        self.cfg = cfg
        self.use_soft_decisions = use_soft_decisions
        self.learnable_heads = set(learnable_heads)

        if 'scalars' in self.learnable_heads:
            self.scalars = LearnableScalars(cfg.n_outer_iter, cfg)
        else:
            self.scalars = None

        if 'strategy' in self.learnable_heads:
            self.strategy_mlps = nn.ModuleList(
                [StrategyMLP() for _ in range(cfg.n_outer_iter)])
        else:
            self.strategy_mlps = None

        if 'symbol_refiner' in self.learnable_heads:
            self.symbol_refiner = SymbolRefiner()
        else:
            self.symbol_refiner = None

        if 'per_iter_refiner' in self.learnable_heads:
            self.per_iter_refiner = PerIterSymbolRefiner(
                n_iters=cfg.n_outer_iter)
        else:
            self.per_iter_refiner = None

        if 'iter_residual_selector' in self.learnable_heads:
            self.iter_residual_selector = IterResidualSelector(
                n_iters=cfg.n_outer_iter)
        else:
            self.iter_residual_selector = None

        if 'channel_tap_corrector' in self.learnable_heads:
            self.channel_tap_corrector = ChannelTapCorrector(
                n_iters=cfg.n_outer_iter)
        else:
            self.channel_tap_corrector = None

        if 'off_support_corr' in self.learnable_heads:
            self.off_support_corr = OffSupportCorrelationHead(
                n_iters=cfg.n_outer_iter)
        else:
            self.off_support_corr = None

        if 'cand_active_rel' in self.learnable_heads:
            self.cand_active_rel = CandidateActiveRelationHead()
        else:
            self.cand_active_rel = None

    # -- accessors for per-iter scalars (support both fixed and learned) ----

    def _scalars_for(self, t: int) -> Dict[str, torch.Tensor]:
        """Get per-iteration hyperparams as torch tensors."""
        cfg = self.cfg
        device = next(self.parameters()).device if len(list(self.parameters())) > 0 else torch.device(cfg.device)
        if self.scalars is not None:
            return self.scalars.for_iter(t)
        # Fixed defaults as 0-d tensors (no grad)
        mk = lambda v: torch.tensor(v, dtype=cfg.rdtype, device=device)
        return dict(
            gamma_h=mk(cfg.gamma_h),
            gamma_x=mk(cfg.gamma_x),
            pic_damp=mk(cfg.pic_damp),
            lambda_ls_factor=mk(cfg.lambda_ls_factor),
            tau_h_factor=mk(cfg.tau_h_factor),
            tau_h_sigma_factor=mk(cfg.tau_h_sigma_factor),
        )

    def _apply_strategy(self, t: int, hp: Dict[str, torch.Tensor],
                         sigma2: torch.Tensor, resnorm: torch.Tensor,
                         support_size: int, Q: int) -> Dict[str, torch.Tensor]:
        if self.strategy_mlps is None:
            return hp
        mlp_param = next(self.strategy_mlps[t].parameters())
        mlp_dtype = mlp_param.dtype
        mlp_device = mlp_param.device
        # Sanitize: replace ±inf (e.g. prev_resnorm = inf at t=0) with finite
        # clamps so they don't propagate through the MLP as 0·inf = NaN.
        sigma_feat = sigma2.to(device=mlp_device, dtype=mlp_dtype).clamp_min(1e-30).log().clamp(min=-30.0, max=30.0)
        resnorm_on_mlp = resnorm.to(device=mlp_device, dtype=mlp_dtype)
        resnorm_finite = torch.where(
            torch.isfinite(resnorm_on_mlp),
            resnorm_on_mlp,
            torch.tensor(1e20, dtype=mlp_dtype, device=mlp_device),
        )
        resnorm_feat = resnorm_finite.clamp_min(1e-30).log().clamp(min=-30.0, max=30.0)
        feats = torch.stack([
            sigma_feat,
            resnorm_feat,
            torch.tensor(float(t) / max(self.cfg.n_outer_iter - 1, 1),
                         dtype=mlp_dtype, device=mlp_device),
            torch.tensor(float(support_size) / max(Q, 1),
                         dtype=mlp_dtype, device=mlp_device),
        ])
        nudge = self.strategy_mlps[t](feats)         # (3,), each in [-0.5, 0.5]
        mult = 1.0 + nudge                            # (3,) in [0.5, 1.5]
        return dict(
            gamma_h=hp['gamma_h'],
            gamma_x=hp['gamma_x'] * mult[1].to(hp['gamma_x'].dtype),
            pic_damp=hp['pic_damp'] * mult[2].to(hp['pic_damp'].dtype),
            lambda_ls_factor=hp['lambda_ls_factor'] * mult[0].to(hp['lambda_ls_factor'].dtype),
            tau_h_factor=hp['tau_h_factor'],
            tau_h_sigma_factor=hp['tau_h_sigma_factor'],
        )

    # -- main forward -------------------------------------------------------

    def forward(self,
                y_daft: torch.Tensor,                 # (N,) complex
                x_pilot_scaled: torch.Tensor,         # (N,) complex
                sigma2: torch.Tensor,                 # scalar real
                constellation_data: torch.Tensor,     # (M,) complex
                Phi: Optional[torch.Tensor] = None,   # precomputed (N, Q); else built internally
                oracle_support: Optional[List[int]] = None,
                return_trajectory: bool = False,
                ) -> Dict[str, torch.Tensor]:
        """Run the full T-iteration joint OMP-MP unrolling.

        Returns a dict with keys: ``x_soft`` (N, complex), ``H_est`` (N, N
        complex), ``sigma2_final`` (scalar), ``support_delays``,
        ``support_dopplers``, ``gains`` (final iter).
        """
        cfg = self.cfg
        cdtype = cfg.dtype
        rdtype = cfg.rdtype
        device = y_daft.device
        N = cfg.N
        K = 2 * cfg.k_max + 1
        Q = (cfg.l_max + 1) * K
        P_data = 1.0 - cfg.rho

        if Phi is None:
            Phi = construct_sensing_matrix_torch(
                N, x_pilot_scaled, cfg.c1, cfg.c2, cfg.l_max, cfg.k_max,
                cdtype=cdtype)

        sigma2_eff = sigma2.to(rdtype).clone()
        H_hat = torch.zeros((N, N), dtype=cdtype, device=device)
        # C1: track the LS-active estimate separately from H_hat so that the
        # add-a-path correction at iter t does NOT leak through the γ_h damping
        # into iter t+1. H_hat = H_hat_active + H_corr (per-iter replace).
        H_hat_active = torch.zeros((N, N), dtype=cdtype, device=device)
        x_soft_scaled = torch.zeros(N, dtype=cdtype, device=device)
        gains_S = torch.zeros(0, dtype=cdtype, device=device)
        support_delays = torch.zeros(0, dtype=torch.long, device=device)
        support_dopplers = torch.zeros(0, dtype=torch.long, device=device)
        prev_resnorm = torch.tensor(float('inf'), dtype=rdtype, device=device)

        traj: List[Dict[str, Any]] = []
        # B1/B2 bookkeeping: snapshot x_soft and resnorm at the end of each
        # outer iter so that IterResidualSelector can combine them.
        x_soft_history: List[torch.Tensor] = []
        resnorm_history: List[torch.Tensor] = []

        for t in range(cfg.n_outer_iter):
            hp = self._scalars_for(t)
            hp = self._apply_strategy(t, hp, sigma2_eff,
                                      prev_resnorm,
                                      int(support_delays.numel()), Q)

            # ---- (A) channel estimation update ---------------------------
            if t == 0:
                if oracle_support is not None and len(oracle_support) > 0:
                    support_idx = list(int(i) for i in oracle_support)
                    Phi_S = Phi[:, support_idx]
                    gains_on_support = torch.linalg.lstsq(
                        Phi_S, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                    h_omp = torch.zeros(Q, dtype=cdtype, device=device)
                    for col_i, gv in zip(support_idx, gains_on_support):
                        h_omp[col_i] = gv
                else:
                    h_omp, support_idx = omp_sparse_torch(y_daft, Phi, cfg.n_paths)

                    # C2-rel (cand_active_rel): learned support-repair hook
                    # inserted AFTER raw OMP and BEFORE cluster expansion.
                    # Zero-init (bias=-8) makes this a no-op at initialization.
                    if self.cand_active_rel is not None:
                        # Early short-circuit: if the SNR-specific tau is huge
                        # (>= 100), no candidate can ever clear the commit
                        # threshold, so the head is guaranteed to be a no-op.
                        # Skipping the extra LS + feature compute preserves
                        # bit-exact parity with the (heads=()) torch-ref arm
                        # on GPU (cuBLAS reductions are not deterministic
                        # across differing op sequences, so even a no-op head
                        # can perturb subsequent DA-LS by O(1) bits at ultra-
                        # low BER).
                        _tau_pre = self.cand_active_rel.tau_for_sigma2(sigma2_eff)
                        _safe_swap_on = getattr(
                            self.cand_active_rel, '_safe_swap', False)
                        if _tau_pre >= 100.0 and not _safe_swap_on:
                            Phi_S_raw = None
                            g_ls_raw = None
                            feats = {'cand_cols': torch.zeros(0, device=device, dtype=torch.long)}
                        else:
                            Phi_S_raw = Phi[:, support_idx]
                            g_ls_raw = torch.linalg.lstsq(
                                Phi_S_raw, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                            feats = self.cand_active_rel.build_features(
                                Phi, y_daft, support_idx, g_ls_raw, sigma2_eff,
                                cfg.l_max, cfg.k_max)
                        # F2-P (Loop-11 Oracle R1 top-1): multi-round +
                        # refresh-pool + defer-prune + protect-added. Routed
                        # before the legacy single-pass logic so it cleanly
                        # produces (h_omp, support_idx). Skipped if safe-swap
                        # is also requested (incompatible interfaces).
                        _refine_n = int(getattr(self.cand_active_rel,
                                                 '_refine_rounds', 0))
                        _safe_swap_on_pre = bool(getattr(self.cand_active_rel,
                                                          '_safe_swap', False))
                        if _refine_n >= 1 and not _safe_swap_on_pre:
                            new_support, g_new = (
                                self.cand_active_rel.apply_f2p_refinement(
                                    Phi, y_daft, support_idx, sigma2_eff,
                                    cfg.l_max, cfg.k_max, cfg.n_paths,
                                )
                            )
                            h_omp = torch.zeros(Q, dtype=cdtype, device=device)
                            for col_i, gv in zip(new_support, g_new):
                                h_omp[col_i] = gv
                            support_idx = list(new_support)
                            # Skip the legacy single-pass branches below.
                            feats = {'cand_cols': torch.zeros(0,
                                                               device=device,
                                                               dtype=torch.long)}
                        if feats.get('cand_cols', torch.zeros(0)).numel() > 0:
                            logits = self.cand_active_rel.score(
                                feats['u'], feats['v'])
                            tau_val = self.cand_active_rel.tau_for_sigma2(
                                sigma2_eff)
                            if getattr(self.cand_active_rel, '_safe_swap', False):
                                # Loop-10 safety valve: sequential add-and-test
                                # on raw OMP support. All OMP atoms kept;
                                # candidates added only if pilot residual
                                # reduces by >= eps_r AND candidate's |gain|
                                # beats weakest OMP atom by (1 + gain_margin).
                                # Self-regulating across SNR.
                                new_support, g_new = (
                                    self.cand_active_rel.apply_sequential_add_test(
                                        Phi, y_daft, support_idx,
                                        logits, feats['cand_cols'],
                                        residual_reduction_threshold=(
                                            self.cand_active_rel._safe_swap_eps_r),
                                        k_add_cap=(
                                            self.cand_active_rel._safe_swap_k_cap),
                                        gain_margin=getattr(
                                            self.cand_active_rel,
                                            '_safe_swap_gain_margin', 0.0),
                                    )
                                )
                                h_omp = torch.zeros(Q, dtype=cdtype, device=device)
                                for col_i, gv in zip(new_support, g_new):
                                    h_omp[col_i] = gv
                                support_idx = new_support
                            else:
                                # Loop-9 behavior: force-topk + union + prune by
                                # |gain| + refit.
                                adds = self.cand_active_rel.select_additions(
                                    logits, feats['cand_cols'], tau=tau_val)
                                if adds.numel() > 0:
                                    union = list(support_idx) + [int(a.item())
                                                                  for a in adds]
                                    seen = set(); union_unique = []
                                    for idx in union:
                                        if idx not in seen:
                                            union_unique.append(idx); seen.add(idx)
                                    Phi_U = Phi[:, union_unique]
                                    g_u = torch.linalg.lstsq(
                                        Phi_U, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                                    if getattr(self.cand_active_rel,
                                               '_no_prune_after_union', False):
                                        # F1: keep the full |S_omp|+K_add support.
                                        h_omp = torch.zeros(Q, dtype=cdtype,
                                                             device=device)
                                        for col_i, gv in zip(union_unique, g_u):
                                            h_omp[col_i] = gv
                                        support_idx = list(union_unique)
                                    else:
                                        keep = min(cfg.n_paths, len(union_unique))
                                        _, topi = torch.topk(g_u.abs(), k=keep,
                                                              sorted=False)
                                        topi_sorted, _ = torch.sort(topi)
                                        pruned_idx = [union_unique[int(i.item())]
                                                      for i in topi_sorted]
                                        Phi_P = Phi[:, pruned_idx]
                                        g_pruned = torch.linalg.lstsq(
                                            Phi_P, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                                        h_omp = torch.zeros(Q, dtype=cdtype,
                                                             device=device)
                                        for col_i, gv in zip(pruned_idx, g_pruned):
                                            h_omp[col_i] = gv
                                        support_idx = pruned_idx

                # Cluster-expand ±k_leak and merge.
                support_delays, support_dopplers, gains_S = expand_cluster_support(
                    support_idx, cfg.k_max, cfg.k_leak, h_omp, Q)

            else:
                # DA-LS: build A on current support + hard-decision symbol estimate
                if self.use_soft_decisions:
                    # Use soft expectation for stable gradient.
                    HH_diag_cur = (H_hat.abs().pow(2)).sum(dim=0)
                    x_hard_scaled = _qpsk_soft_decision(
                        x_soft_scaled, HH_diag_cur, sigma2_eff, constellation_data)
                else:
                    x_hard_scaled = _qpsk_hard_decision(
                        x_soft_scaled, constellation_data)

                x_total = x_pilot_scaled + x_hard_scaled
                num_paths = int(support_delays.numel())
                if num_paths > 0:
                    A_total = build_A_for_DALS_torch(
                        N, support_delays, support_dopplers, x_total,
                        cfg.c1, cfg.c2, cfg.k_max, cdtype=cdtype)
                    lambda_ls = torch.clamp(
                        hp['lambda_ls_factor'] * sigma2_eff, min=1e-6)
                    AhA = A_total.conj().T @ A_total
                    Ahy = A_total.conj().T @ y_daft
                    I = torch.eye(num_paths, dtype=cdtype, device=device)
                    rhs = (Ahy + lambda_ls.to(cdtype) * gains_S)
                    g_new = torch.linalg.solve(
                        AhA + lambda_ls.to(cdtype) * I, rhs)
                    gains_S = g_new

                    # B3 — CE-side ChannelTapCorrector: add a small residual
                    # correction to the DA-LS tap vector, conditioned on the
                    # per-tap residual projection c = A^H (y - A g_new).
                    if self.channel_tap_corrector is not None:
                        y_resid = y_daft - A_total @ g_new
                        c_proj = A_total.conj().T @ y_resid  # (P,) complex
                        r_norm = (y_resid.abs().pow(2)).sum().to(rdtype)
                        delta_g = self.channel_tap_corrector(
                            gains_S, c_proj,
                            support_delays, support_dopplers,
                            sigma2_eff, r_norm,
                            t, cfg.n_outer_iter,
                            cfg.l_max, cfg.k_max)
                        gains_S = gains_S + delta_g

            # C1 — OffSupportCorrelationHead: add-a-path correction on
            # inactive atoms using data-matched sensing residual projection.
            # Built AFTER DA-LS (gains_S is final for this iter) and BEFORE
            # H reconstruction so H_new = H_active + H_corr.
            cand_delta_g = None
            cand_col_idx = None
            if (self.off_support_corr is not None
                    and support_delays.numel() > 0
                    and t >= 1):
                # Detached hard-aligned data vector and full data-matched
                # sensing matrix. Detach so MLP gradient does not flow
                # through the hard-decision or through the LS solve.
                x_hd_det = _qpsk_hard_decision(
                    x_soft_scaled.detach(), constellation_data).detach()
                x_full_det = (x_pilot_scaled + x_hd_det).detach()
                Phi_full = construct_sensing_matrix_torch(
                    N, x_full_det, cfg.c1, cfg.c2, cfg.l_max, cfg.k_max,
                    cdtype=cdtype).detach()
                g_new_det = gains_S.detach()
                # r_det uses A_total from DA-LS solve (active-only columns):
                r_det = (y_daft - A_total @ g_new_det).detach()
                K = 2 * cfg.k_max + 1
                active_cols_set = set()
                for d_i, k_i in zip(support_delays.tolist(),
                                     support_dopplers.tolist()):
                    active_cols_set.add(int(d_i) * K + (int(k_i) + cfg.k_max))
                lambda_ls_val = float(
                    hp['lambda_ls_factor']
                    * torch.clamp(sigma2_eff, min=1e-12))
                idxs, c_cand, b_cand, col_sqnorms = \
                    self.off_support_corr.propose_candidates(
                        Phi_full, r_det, active_cols_set, lambda_ls_val)
                if idxs.numel() > 0:
                    # Detector margin: mean (|Re|,|Im|) min of current soft.
                    x_abs = x_soft_scaled.detach()
                    dm = torch.minimum(x_abs.real.abs(),
                                        x_abs.imag.abs()).mean().to(rdtype)
                    r_norm_det = (r_det.abs().pow(2)).sum().to(rdtype)
                    delta_g_cand = self.off_support_corr(
                        b_cand, c_cand, idxs,
                        support_delays, support_dopplers,
                        cfg.k_max, cfg.l_max,
                        sigma2_eff, r_norm_det, dm,
                        t, cfg.n_outer_iter)
                    cand_delta_g = delta_g_cand
                    cand_col_idx = idxs

            # ---- reconstruct H and damp (ACTIVE-SUPPORT ESTIMATE) -------
            H_new = reconstruct_H_torch(
                N, support_delays, support_dopplers, gains_S,
                cfg.c1, cfg.c2, cfg.k_max, cdtype=cdtype)
            gamma_h = hp['gamma_h'].to(cdtype)
            H_hat_active = (1.0 - gamma_h) * H_hat_active + gamma_h * H_new

            # Sparsification on H_hat_active only (kills noise taps on the
            # active support; MUST NOT touch C1 add-a-path corrections).
            max_h = H_hat_active.abs().max()
            if max_h > 0:
                tau_rel = hp['tau_h_factor'].to(rdtype) * max_h.to(rdtype)
                tau_sigma = hp['tau_h_sigma_factor'].to(rdtype) * sigma2_eff.sqrt()
                tau = torch.maximum(tau_rel, tau_sigma)
                if self.use_soft_decisions:
                    # Soft mask for gradient flow; temperature β controls crispness.
                    beta = 0.02 * tau.clamp_min(1e-12)
                    mask = torch.sigmoid((H_hat_active.abs() - tau) / beta)
                    H_hat_active = H_hat_active * mask.to(cdtype)
                else:
                    mask = (H_hat_active.abs() >= tau)
                    H_hat_active = torch.where(mask, H_hat_active,
                                                torch.zeros_like(H_hat_active))

            # C1 — per-iter learned add-a-path correction. NOT accumulated
            # across outer iters (only this iter's contribution matters for
            # the current detector step).  Zero-init → H_corr = 0 → identity.
            H_corr = torch.zeros_like(H_hat_active)
            if cand_delta_g is not None and cand_col_idx is not None \
                    and cand_col_idx.numel() > 0:
                K = 2 * cfg.k_max + 1
                cand_l = (cand_col_idx // K).to(torch.long)
                cand_k = ((cand_col_idx % K).to(torch.long)) - cfg.k_max
                H_corr = reconstruct_H_torch(
                    N, cand_l, cand_k, cand_delta_g,
                    cfg.c1, cfg.c2, cfg.k_max, cdtype=cdtype)

            # Total channel estimate fed to the detector = active + learned.
            H_hat = H_hat_active + H_corr

            # ---- (B) MP detection ----------------------------------------
            y_data = y_daft - H_hat @ x_pilot_scaled
            pic_damp = hp['pic_damp'].to(rdtype)
            if cfg.mp_mode == 'bp':
                # Vectorized Gaussian BP on the sparse H graph. In soft mode
                # we return the posterior mean (differentiable); in eval/hard
                # mode we keep the hard nearest-constellation projection.
                if self.use_soft_decisions:
                    _, mu_post, _ = mp_detect_bp_torch(
                        y_data, H_hat, sigma2_eff, constellation_data,
                        n_iter=cfg.pic_iter, threshold=cfg.bp_threshold,
                        damp=pic_damp, return_numpy=False, return_soft=True)
                    x_mp = mu_post.to(y_data.dtype)
                else:
                    x_mp = mp_detect_bp_torch(
                        y_data, H_hat, sigma2_eff, constellation_data,
                        n_iter=cfg.pic_iter, threshold=cfg.bp_threshold,
                        damp=pic_damp, return_numpy=False,
                        return_soft=False).to(y_data.dtype)
            else:
                x_mp = mp_detect_pic_torch(
                    y_data, H_hat, sigma2_eff, constellation_data,
                    n_iter=cfg.pic_iter, damp=pic_damp,
                    hard_decision=not self.use_soft_decisions)

            # B1 — PerIterSymbolRefiner: inject CNN Δx BEFORE symbol damping.
            # Zero-init identity → at start, Δx = 0 so x_mp is unchanged.
            if self.per_iter_refiner is not None:
                HH_diag_t = (H_hat.abs().pow(2)).sum(dim=0).to(rdtype)
                residual_t = y_daft - H_hat @ (x_pilot_scaled + x_mp)
                delta_x = self.per_iter_refiner(
                    t, x_mp, residual_t, HH_diag_t)
                x_mp = x_mp + delta_x.to(x_mp.dtype)

            gamma_x = hp['gamma_x'].to(cdtype)
            x_soft_scaled = (1.0 - gamma_x) * x_soft_scaled + gamma_x * x_mp

            # B2 — snapshot x_soft and residual at the end of each outer iter
            # so IterResidualSelector can blend them.
            x_soft_history.append(x_soft_scaled.clone())

            # ---- (C) adaptive noise estimate -----------------------------
            if cfg.update_sigma2 and t > 0:
                if self.use_soft_decisions:
                    HH_diag_cur = (H_hat.abs().pow(2)).sum(dim=0)
                    x_hard_res = _qpsk_soft_decision(
                        x_soft_scaled, HH_diag_cur, sigma2_eff, constellation_data)
                else:
                    x_hard_res = _qpsk_hard_decision(
                        x_soft_scaled, constellation_data)
                res = y_daft - H_hat @ (x_pilot_scaled + x_hard_res)
                sigma2_new = (res.abs().pow(2)).sum().to(rdtype) / N
                sigma2_eff = 0.7 * sigma2_eff + 0.3 * torch.clamp(sigma2_new, min=1e-12)

            # ---- (D) early stop ------------------------------------------
            # Match NumPy: always compute current residual norm (using hard
            # decision) for tracking; honour early stop only when enabled.
            x_hard_stop = _qpsk_hard_decision(x_soft_scaled, constellation_data)
            res_stop = y_daft - H_hat @ (x_pilot_scaled + x_hard_stop)
            curr_resnorm = (res_stop.abs().pow(2)).sum().to(rdtype)
            resnorm_history.append(curr_resnorm.clone())

            if return_trajectory:
                traj.append(dict(
                    iter=t,
                    x_soft=x_soft_scaled.detach().clone(),
                    H_est=H_hat.detach().clone(),
                    sigma2=sigma2_eff.detach().clone(),
                    resnorm=curr_resnorm.detach().clone(),
                ))

            if cfg.early_stop and torch.isfinite(prev_resnorm):
                rel_improve = (prev_resnorm - curr_resnorm) / torch.clamp(curr_resnorm, min=1e-12)
                if (rel_improve >= 0) and (rel_improve < cfg.eps_stop_rel):
                    break
            prev_resnorm = curr_resnorm

        # B2 — IterResidualSelector blends per-iter x_soft around the last
        # iterate.  At zero-init, α_t = 0 → x_final = x_soft_history[-1]
        # (matches classical), so identity check still passes.
        if self.iter_residual_selector is not None and len(x_soft_history) >= 2:
            x_soft_scaled = self.iter_residual_selector(
                x_soft_history, sigma2_eff, resnorm_history)

        # ---- optional symbol refinement on the final estimate -------------
        if self.symbol_refiner is not None:
            HH_diag = (H_hat.abs().pow(2)).sum(dim=0)
            r_data = y_daft - H_hat @ (x_pilot_scaled + x_soft_scaled)
            delta = self.symbol_refiner(x_soft_scaled, r_data, HH_diag)
            x_soft_scaled = x_soft_scaled + delta.to(x_soft_scaled.dtype)

        out: Dict[str, torch.Tensor] = dict(
            x_soft=x_soft_scaled,
            H_est=H_hat,
            sigma2_final=sigma2_eff,
            support_delays=support_delays,
            support_dopplers=support_dopplers,
            gains=gains_S,
            # Expose per-iter snapshots so best-iter supervised pretraining
            # can pick the oracle-best iter as target.  Each entry is a
            # complex (N,) tensor with grad still attached to the receiver.
            x_soft_history=x_soft_history,
            resnorm_history=resnorm_history,
        )
        if return_trajectory:
            out['trajectory'] = traj
        return out


# ======================================================================
# 5. Convenience builder — mirrors afdm_baselines behaviour
# ======================================================================


def build_classical_joint_unrolled(N: int, l_max: int, k_max: int,
                                   c1: float, c2: float, **kwargs
                                   ) -> ClassicalJointUnrolled:
    cfg = ClassicalJointConfig(
        N=N, l_max=l_max, k_max=k_max, c1=float(c1), c2=float(c2),
        **{k: v for k, v in kwargs.items() if k in ClassicalJointConfig.__dataclass_fields__}
    )
    learnable = kwargs.get('learnable_heads', ())
    soft = kwargs.get('use_soft_decisions', False)
    return ClassicalJointUnrolled(cfg, learnable_heads=learnable,
                                  use_soft_decisions=soft)


__all__ = [
    'ClassicalJointConfig',
    'ClassicalJointUnrolled',
    'OffSupportCorrelationHead',
    'build_classical_joint_unrolled',
    'construct_sensing_matrix_torch',
    'omp_sparse_torch',
    'reconstruct_H_torch',
    'mp_detect_pic_torch',
]
