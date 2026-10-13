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
from typing import Optional, Dict, Any, Tuple, List, Callable

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from afdm_sp_joint_unrolled.mp_detect_bp_torch import mp_detect_bp_torch
from .physical_stride import physical_stride


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
    # cand_active_rel head dimensions; defaults preserve canonical 1041-param head
    cand_pair_hidden: int = 16
    cand_scorer_hidden: int = 16


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
    stride = physical_stride(N, c1)
    Q = (l_max + 1) * K
    q_arr = torch.arange(N, device=device, dtype=torch.float64)

    Phi = torch.zeros((N, Q), dtype=cdtype, device=device)

    col = 0
    for l in range(l_max + 1):
        l_sq = float(l) ** 2
        l_f = float(l)
        for k in range(-k_max, k_max + 1):
            delta = l * stride + k
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


def omp_sparse_torch(y: torch.Tensor, Phi: torch.Tensor, sparsity: int, *, path_observer=None,
                     lstsq_driver=None
                     ) -> Tuple[torch.Tensor, List[int]]:
    """Torch OMP — mirrors ``afdm_baselines.omp_sparse``.

    Returns ``(h_est, support)`` where support indices are detached (support
    selection is inherently argmax-based).  The returned gains use
    ``torch.linalg.lstsq`` which *is* differentiable w.r.t. ``y``.
    An explicit driver is a recorded numerical condition, not a fallback.
    """
    if lstsq_driver not in (None,'gels','gelsy','gelsd','gelss'):
        raise ValueError('unknown explicit least-squares driver')
    if Phi.device.type == 'cuda' and lstsq_driver not in (None,'gels'):
        raise ValueError('CUDA least-squares supports only gels')
    solve_options = {} if lstsq_driver is None else {'driver':lstsq_driver}
    Q = Phi.shape[1]
    residual = y.clone()
    support: List[int] = []
    Phi_H = Phi.conj().T

    y_norm = torch.linalg.vector_norm(y)
    if path_observer is not None:
        path_observer([], y.new_empty(0), residual)

    for _ in range(sparsity):
        correlations = (Phi_H @ residual).abs()       # (Q,)
        for idx in support:
            correlations[idx] = 0.0
        new_idx = int(torch.argmax(correlations).item())
        support.append(new_idx)

        Phi_S = Phi[:, support]                        # (N, s)
        # lstsq is differentiable
        sol = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
        residual = y - Phi_S @ sol
        if path_observer is not None:
            path_observer(list(support), sol, residual)

        if torch.linalg.vector_norm(residual) < 1e-10 * y_norm:
            break

    h_est = torch.zeros(Q, dtype=y.dtype, device=y.device)
    if support:
        Phi_S = Phi[:, support]
        gains_final = torch.linalg.lstsq(Phi_S, y.unsqueeze(-1), **solve_options).solution.squeeze(-1)
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
    stride = physical_stride(N, c1)

    P = int(support_delays.numel())
    for p in range(P):
        l_p = int(support_delays[p].item())
        k_p = int(support_dopplers[p].item())
        g = gains_S[p]
        delta = l_p * stride + k_p
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
    stride = physical_stride(N, c1)
    P = int(support_delays.numel())
    A = torch.zeros((N, P), dtype=cdtype, device=device)

    for p in range(P):
        l_p = int(support_delays[p].item())
        k_p = int(support_dopplers[p].item())
        delta = l_p * stride + k_p
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


def fixed_nomination_cap(active_cap, k_leak, k_max):
    """Conservative cap using the existing cluster expansion, without pruning it."""
    width = min(2*k_leak+1,2*k_max+1)
    if not isinstance(active_cap,int) or width<=0 or active_cap<width:
        raise ValueError('active cap must be an integer large enough for one cluster')
    return active_cap//width


def resolve_receiver_capacity(shell, active_cap, k_leak, k_max):
    """Resolve receiver nomination/extension without changing the generator."""
    if shell == 'direct40':
        if type(active_cap) is not int or active_cap != 40:
            raise ValueError('direct40 requires registered active capacity 40')
        return 40, 0
    if shell != 'legacy':
        raise ValueError('unknown receiver shell')
    nomination = (None if active_cap is None else
                  fixed_nomination_cap(active_cap, k_leak, k_max))
    return nomination, k_leak


def data_uncertainty_gram(N, delays, dopplers, variance, c1, c2, k_max,
                          cdtype=torch.complex128):
    """Exact Q_ij=tr(D_i^H D_j diag(v)) for integer AFDM operators.

    Distinct circular displacements are orthogonal for every diagonal v.
    Aliased displacements require a weighted phase Gram, not a diagonal ridge.
    """
    if variance.shape != (N,) or not torch.isfinite(variance).all() or (variance < 0).any():
        raise ValueError('data variance must be finite, nonnegative and length N')
    P = delays.numel()
    offsets = (delays*physical_stride(N, c1)+dopplers) % N
    Q = variance.sum().to(cdtype)*torch.eye(P,dtype=cdtype,device=variance.device)
    unique,counts = torch.unique(offsets,return_counts=True)
    if bool((counts>1).any()):
        phases = build_A_for_DALS_torch(N,delays,dopplers,
                    torch.ones(N,dtype=cdtype,device=variance.device),c1,c2,k_max,cdtype)
        n = torch.arange(N,device=variance.device)
        for delta in unique[counts>1]:
            ids = torch.where(offsets==delta)[0]
            phi = phases[(n+delta)%N][:,ids]
            block = phi.conj().T @ (variance[:,None]*phi)
            Q[ids[:,None],ids[None,:]] = block
    return Q


def residual_data_covariance(H, variance, sigma2):
    """Already-scaled symbol variance: no additional (1-rho) factor."""
    if (variance.shape != (H.shape[1],) or not torch.isfinite(variance).all()
            or (variance<0).any() or not torch.isfinite(sigma2).all() or sigma2<=0):
        raise ValueError('invalid residual covariance variance or noise power')
    C = (H*variance[None,:]) @ H.conj().T
    return C + sigma2*torch.eye(H.shape[0],dtype=H.dtype,device=H.device)


def soft_gain_update(A, y, previous, regularization, *, Q=None, C=None, sigma2=None):
    """One frozen proximal gain objective; Q and covariance are separate arms."""
    if Q is not None and C is not None:
        raise ValueError('joint uncertainty and covariance objectives are not registered')
    if C is None:
        AhA = A.conj().T @ A
        Ahy = A.conj().T @ y
    else:
        if sigma2 is None or not torch.isfinite(sigma2).all() or sigma2<=0:
            raise ValueError('weighted gain update requires positive noise power')
        L = torch.linalg.cholesky(C)
        solved = torch.cholesky_solve(torch.cat((A,y[:,None]),dim=1),L)
        AhA = sigma2*(A.conj().T @ solved[:,:-1])
        Ahy = sigma2*(A.conj().T @ solved[:,-1])
    if Q is not None:
        AhA = AhA + Q
    I = torch.eye(A.shape[1],dtype=A.dtype,device=A.device)
    rhs = Ahy + regularization.to(A.dtype)*previous
    return torch.linalg.solve(AhA+regularization.to(A.dtype)*I,rhs)


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
                        constellation: torch.Tensor, observer=None, *,
                        temperature=1., return_variance=False):
    """Soft (posterior-mean) QPSK decision — differentiable.

    For each symbol we treat the input as a Gaussian observation with
    per-symbol variance ``v_n = sigma2 / max(HH_diag_n, 1e-10)`` and compute
    E[x | x_soft, v_n] with a uniform prior over the QPSK constellation.
    This is the same rule used inside ``QPSKPosterior`` but written directly
    on the (N,) complex layout used here.
    """
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('soft feedback temperature must be positive and finite')
    # (N, M) squared distance
    v_n = sigma2 / torch.clamp(HH_diag.real, min=1e-10)              # (N,)
    diff = x_soft.unsqueeze(-1) - constellation.view(1, -1)          # (N, M)
    d2 = diff.real.pow(2) + diff.imag.pow(2)                         # (N, M)
    logp = -d2 / torch.clamp(v_n.unsqueeze(-1), min=1e-12)           # (N, M)
    logp = logp - logp.max(dim=-1, keepdim=True).values
    if temperature != 1.:
        logp = logp / temperature
    p = torch.softmax(logp, dim=-1)                                  # (N, M)
    # mu = sum_s p(s) * s
    mu = (p * constellation.view(1, -1)).sum(dim=-1)                 # (N,) complex
    if observer is not None:
        observer({key:value.detach().clone() for key,value in dict(
            logits=logp, probabilities=p, mean=mu, input_variance=v_n,
            constellation=constellation).items()})
    if return_variance:
        variance = (p * (constellation.view(1,-1)-mu.unsqueeze(-1)).abs().square()).sum(-1)
        return mu.to(x_soft.dtype), variance
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


class SupportProposalRejected(ValueError):
    """A numerically invalid proposal must return to the common baseline."""


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
        # Step 3 B-reduced (feature ablation). Set to one of:
        #   'all'           — no masking (default)
        #   'no-residual-mf'— zero u[..., 0:2] (log_mf, margin)
        #   'no-pair-coh'   — zero v[..., 0:2] (coh, log_alpha_coh)
        self._feature_mask = 'all'
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
        # Step 3 B-reduced feature ablation
        if self._feature_mask == 'no-residual-mf':
            u = u.clone(); u[..., 0:2] = 0.0
        elif self._feature_mask == 'no-pair-coh':
            v = v.clone(); v[..., 0:2] = 0.0
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
                         tau: float = 0.0, stable: bool = False) -> torch.Tensor:
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
        if stable:
            topi = torch.argsort(pos_logits, descending=True, stable=True)[:k]
        else:
            _, topi = torch.topk(pos_logits, k=k, sorted=True)
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
        score_override: Optional[Callable] = None,
        tau_override: Optional[float] = None,
        capacity_observer: Optional[Callable] = None,
        frozen_candidates: Optional[List[List[int]]] = None,
        stable_selection: bool = False,
        proposal_covariance: Optional[torch.Tensor] = None,
        proposal_observer: Optional[Callable] = None,
    ) -> Tuple[List[int], torch.Tensor]:
        """F2-P entry point. Implements Oracle R1 Loop-11 recipe.

        ``score_override``: optional callable (Phi, y_daft, S, cand_cols, sigma2)
        -> logits aligned to ``cand_cols``. When given, replaces the learned
        head scorer at the per-round ranking step while leaving the entire
        refine / defer-prune / protect-added / final-prune machinery byte-
        identical. Used by Gate A to plug manual scorers (white-Λ, pure-geom,
        genie-Λ, achievable-Λ) into the SAME F2-P loop as the headline.
        ``tau_override``: per-scorer commit threshold for ``select_additions``;
        when None the learned ``tau_for_sigma2`` is used (head default). For
        logΛ scorers pass 0.0; for fixed-top-k robustness pass -inf.

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
        if frozen_candidates is not None:
            if len(frozen_candidates) != n_rounds or score_override is None:
                raise ValueError('one frozen pool per round and explicit scorer required')
            for pool in frozen_candidates:
                if len(set(pool)) != len(pool) or any(type(i) is not int or i < 0 or i >= Phi.shape[1] for i in pool):
                    raise ValueError('frozen pools require unique in-range integer IDs')
        if stable_selection and (n_rounds > 2 or self._protect_added > n_paths):
            raise ValueError('registered proposal requires <=2 rounds and feasible protection')

        def check_proposal_rank(columns, stage):
            if proposal_covariance is None:
                return
            from afdm_sp_joint_unrolled.projected_gls import projected_add_statistics
            fit = projected_add_statistics(y_daft, Phi, proposal_covariance, columns, [])
            if not fit['valid_current']:
                raise SupportProposalRejected('proposal_rank_'+stage)

        for rr in range(n_rounds):
            if len(S) == 0:
                if proposal_observer is not None:
                    proposal_observer(dict(stage='stop', round=rr, reason='empty_support'))
                break
            check_proposal_rank(S, 'current')
            Phi_S = Phi[:, S]
            g_ls = torch.linalg.lstsq(Phi_S, y_daft.unsqueeze(-1)).solution.squeeze(-1)
            if frozen_candidates is None:
                feats = self.build_features(
                    Phi, y_daft, S, g_ls, sigma2, l_max, k_max,
                    top_m_override=cand_topm,
                )
                cand_cols = feats.get('cand_cols',
                                     torch.zeros(0, dtype=torch.long, device=device))
                frozen_count = int(cand_cols.numel())
            else:
                pool = frozen_candidates[rr]
                frozen_count = len(pool)
                cand_cols = torch.tensor([i for i in pool if i not in S], dtype=torch.long, device=device)
            if proposal_observer is not None:
                proposal_observer(dict(stage='pool', round=rr, support=list(S),
                                       frozen_count=frozen_count, candidate_ids=cand_cols.tolist()))
            if cand_cols.numel() == 0:
                if proposal_observer is not None:
                    proposal_observer(dict(stage='stop', round=rr, reason='empty_pool'))
                break
            if score_override is not None:
                logits = score_override(Phi, y_daft, S, cand_cols, sigma2)
            else:
                logits = self.score(feats['u'], feats['v'])
            if stable_selection and (logits.ndim != 1 or logits.shape != cand_cols.shape or
                                     bool(torch.isnan(logits).any() or torch.isposinf(logits).any())):
                raise ValueError('invalid aligned proposal scores')
            tau = (self.tau_for_sigma2(sigma2)
                   if tau_override is None else float(tau_override))
            adds = self.select_additions(logits, cand_cols, tau=float(tau), stable=stable_selection)
            if adds.numel() == 0:
                if proposal_observer is not None:
                    proposal_observer(dict(stage='stop', round=rr, reason='no_selected_candidates'))
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
            if capacity_observer is not None:
                capacity_observer(list(S), rr, n_paths + n_rounds * self.k_add_max)
            if proposal_observer is not None:
                proposal_observer(dict(stage='union', round=rr, selected_ids=adds.tolist(), support=list(S)))
            check_proposal_rank(S, 'union')
            # Deferred-prune: if disabled, prune to n_paths between rounds
            # (legacy intra-round prune behaviour, but F2-P expects
            # defer_prune=True so this path mostly stays inactive).
            if not defer_prune and len(S) > n_paths:
                Phi_U = Phi[:, S]
                g_u = torch.linalg.lstsq(
                    Phi_U, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                if stable_selection:
                    topi = torch.argsort(g_u.abs(), descending=True, stable=True)[:n_paths]
                else:
                    _, topi = torch.topk(g_u.abs(), k=n_paths, sorted=False)
                topi_sorted, _ = torch.sort(topi)
                S = [S[int(i.item())] for i in topi_sorted]

        # Final pilot-LS on augmented support
        if len(S) == 0:
            return S, torch.zeros(0, dtype=cdtype, device=device)
        check_proposal_rank(S, 'pre_prune')
        Phi_S_full = Phi[:, S]
        g_full = torch.linalg.lstsq(
            Phi_S_full, y_daft.unsqueeze(-1)).solution.squeeze(-1)

        if len(S) <= n_paths:
            if proposal_observer is not None:
                proposal_observer(dict(stage='final_prune', protected_ids=[], pruned_ids=[], support=list(S)))
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
            if stable_selection:
                topi = torch.argsort(gains_np, descending=True, stable=True)[:n_to_pick]
            else:
                _, topi = torch.topk(gains_np, k=n_to_pick, sorted=False)
            kept_non_protect = [int(np_tensor[int(i.item())].item()) for i in topi]
        else:
            kept_non_protect = []
        keep_pos = sorted(set(protect_pos) | set(kept_non_protect))
        kept_S = [S[i] for i in keep_pos]
        if proposal_observer is not None:
            proposal_observer(dict(stage='final_prune', protected_ids=[i for i in S if i in protect_cols],
                                   pruned_ids=[i for i in S if i not in kept_S], support=list(kept_S)))
        check_proposal_rank(kept_S, 'final_prune')
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
            self.cand_active_rel = CandidateActiveRelationHead(
                pair_hidden=cfg.cand_pair_hidden,
                scorer_hidden=cfg.cand_scorer_hidden,
            )
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
                diagnostic_support_override: Optional[Callable] = None,
                diagnostic_channel_override: Optional[Callable] = None,
                diagnostic_data_override: Optional[Callable] = None,
                diagnostic_support_observer: Optional[Callable] = None,
                diagnostic_soft_observer: Optional[Callable] = None,
                dals_temperature: float = 1.,
                dals_mode: str = 'mean',
                dals_strength: float = 1.,
                active_support_cap: Optional[int] = None,
                receiver_extension: Optional[int] = None,
                enable_support_repair: bool = True,
                support_transaction: Optional[Callable] = None,
                transaction_observer: Optional[Callable] = None,
                diagnostic_dals_observer: Optional[Callable] = None,
                diagnostic_graph_observer: Optional[Callable] = None,
                diagnostic_proposal_observer: Optional[Callable] = None,
                initial_estimator: Optional[Callable] = None,
                code_feedback=None,
                diagnostic_code_symbols=None,
                one_shot_true_data_ce=None,
                bp_schedule=None,
                outer_iteration_limit=None,
                ce_update_iterations=None,
                dals_start_iteration=1,
                ce_support_exchange=None,
                detector=None,
                retain_siso_states=False,
                bp_edge_projection=None,
                outer_bp_graph=None,
                channel_representation=None,
                dals_prior=None,
                ) -> Dict[str, torch.Tensor]:
        """Run the full T-iteration joint OMP-MP unrolling.

        Returns a dict with keys: ``x_soft`` (N, complex), ``H_est`` (N, N
        complex), ``sigma2_final`` (scalar), ``support_delays``,
        ``support_dopplers``, ``gains`` (final iter).

        ``diagnostic_*_override`` are offline counterfactual interfaces, never
        deployment inputs. They replace respectively the initial support action,
        the channel supplied to BP, or only the data fed into DA-LS. None keeps
        the original arithmetic path; truth-bearing callbacks belong exclusively
        to explicitly labelled diagnostic runs.
        """
        if dals_prior is not None:
            from .dirichlet_gain_prior import DirichletGainPrior
            if (type(dals_prior) is not DirichletGainPrior or dals_mode != 'mean'
                    or self.channel_tap_corrector is not None or self.off_support_corr is not None
                    or enable_support_repair or ce_support_exchange is not None
                    or channel_representation is not None or support_transaction is not None
                    or any(x is not None for x in (oracle_support, diagnostic_support_override,
                        diagnostic_channel_override, diagnostic_data_override, diagnostic_code_symbols))):
                raise ValueError('fixed discrete prior requires unrepaired observed-only mean CE')
            dals_prior.begin()
        if initial_estimator is not None and (not callable(initial_estimator) or enable_support_repair
                or oracle_support is not None or diagnostic_support_override is not None
                or support_transaction is not None):
            raise ValueError('initial estimator requires unrepaired receiver without support overrides')
        if not math.isfinite(dals_temperature) or dals_temperature <= 0:
            raise ValueError('DA-LS temperature must be positive and finite')
        if dals_temperature != 1. and not self.use_soft_decisions:
            raise ValueError('DA-LS temperature requires soft decisions')
        if dals_mode not in ('mean','jsoft','zero_ridge','proximal','covariance','covariance_uniform'):
            raise ValueError('unknown DA-LS working objective')
        if (isinstance(dals_strength, bool) or not math.isfinite(dals_strength) or dals_strength < 0
                or (dals_mode not in ('zero_ridge','proximal') and dals_strength != 1.)):
            raise ValueError('normalized strength is nonnegative and only changes ridge/proximal controls')
        if dals_mode != 'mean' and (not self.use_soft_decisions or diagnostic_data_override is not None):
            raise ValueError('variance feedback requires finite soft moments and no truth override')
        if diagnostic_dals_observer is not None and (not callable(diagnostic_dals_observer) or not self.use_soft_decisions):
            raise ValueError('DA-LS state observer requires callable and soft decisions')
        if active_support_cap is not None and (type(active_support_cap) is not int or active_support_cap<1):
            raise ValueError('active support cap must be a positive integer')
        if receiver_extension is not None and (type(receiver_extension) is not int or receiver_extension < 0):
            raise ValueError('receiver extension must be a nonnegative integer')
        if type(enable_support_repair) is not bool:
            raise ValueError('support repair switch must be boolean')
        if support_transaction is not None:
            if (not callable(support_transaction) or not enable_support_repair or
                    active_support_cap is None or oracle_support is not None or
                    any(hook is not None for hook in (diagnostic_support_override,
                        diagnostic_channel_override, diagnostic_data_override))):
                raise ValueError('support transaction requires fixed capacity and no oracle overrides')
        cfg = self.cfg
        cdtype = cfg.dtype
        rdtype = cfg.rdtype
        device = y_daft.device
        N = cfg.N
        stride = physical_stride(N, cfg.c1)
        if channel_representation is not None:
            from .fixed_basis_receiver import FixedBasisRepresentation
            if (type(channel_representation) is not FixedBasisRepresentation
                    or enable_support_repair or not self.use_soft_decisions or cfg.mp_mode!='bp'
                    or dals_mode!='mean' or dals_temperature!=1. or return_trajectory
                    or any(option is not None for option in (Phi,oracle_support,initial_estimator,
                        diagnostic_support_override,diagnostic_channel_override,diagnostic_data_override,
                        diagnostic_support_observer,diagnostic_dals_observer,diagnostic_proposal_observer,
                        support_transaction,transaction_observer,active_support_cap,receiver_extension,
                        code_feedback,diagnostic_code_symbols,ce_support_exchange,detector,outer_bp_graph,bp_edge_projection))
                    or any(head is not None for head in (self.strategy_mlps,self.symbol_refiner,
                        self.per_iter_refiner,self.iter_residual_selector,self.channel_tap_corrector,self.off_support_corr))
                    or getattr(self,'_early_exit_gate',None) is not None or cfg.early_stop):
                raise ValueError('fixed basis requires the plain uncoded soft BP/mean-CE receiver')
            channel_representation.validate(cfg,y_daft)
        outer_iterations=cfg.n_outer_iter if outer_iteration_limit is None else outer_iteration_limit
        if type(outer_iterations) is not int or not 1<=outer_iterations<=cfg.n_outer_iter:
            raise ValueError('outer iteration limit must lie within the configured loop')
        ce_iterations=tuple(range(1,outer_iterations)) if ce_update_iterations is None else ce_update_iterations
        if (not isinstance(ce_iterations,(tuple,list)) or
                any(type(i) is not int or not 1<=i<outer_iterations for i in ce_iterations)
                or list(ce_iterations)!=sorted(set(ce_iterations))):
            raise ValueError('CE updates must be distinct increasing valid outer iterations')
        if (type(dals_start_iteration) is not int or dals_start_iteration < 1 or
                (dals_start_iteration != 1 and
                 (dals_mode == 'mean' or dals_start_iteration >= outer_iterations))):
            raise ValueError('delayed CE objective requires a valid non-mean activation iteration')
        if detector not in (None, 'siso_mmse') or type(retain_siso_states) is not bool:
            raise ValueError('unknown detector or invalid SISO retention flag')
        if retain_siso_states and detector != 'siso_mmse':
            raise ValueError('SISO state retention requires SISO detector')
        if bp_edge_projection not in (None, 'qpsk_tanh') or (bp_edge_projection is not None and
                (detector is not None or cfg.rho != .5 or cfg.mp_mode != 'bp')):
            raise ValueError('QPSK projection requires the amplitude-.5 BP receiver')
        projection_kwargs = {} if bp_edge_projection is None else {'edge_projection': bp_edge_projection}
        if outer_bp_graph not in (None, 'integer'):
            raise ValueError('unknown outer BP graph representation')
        if outer_bp_graph is not None and (detector is not None or cfg.mp_mode != 'bp'
                or self.off_support_corr is not None or ce_support_exchange is not None
                or oracle_support is not None or diagnostic_support_override is not None
                or diagnostic_channel_override is not None
                or not math.isfinite(cfg.bp_threshold) or cfg.bp_threshold <= 0):
            raise ValueError('integer BP graph requires fixed observed support without extra channel paths')
        siso_calls, siso_states = [], []
        if detector == 'siso_mmse':
            if (device.type != 'cpu' or cfg.rho != .5 or not self.use_soft_decisions or cfg.mp_mode != 'bp'
                    or bp_schedule is not None or diagnostic_code_symbols is not None
                    or code_feedback is None or not code_feedback.enabled):
                raise ValueError('SISO outer chain requires CPU soft inference, active feedback, and no BP schedule')
            from .supplement_siso_mmse import siso_mmse_torch
        outer_bp_iterations = cfg.pic_iter
        schedule_calls = []
        completed_ce_solves = 0
        if bp_schedule is not None:
            from .supplement_feedback_schedule import UniformBPSchedule
            if type(bp_schedule) is not UniformBPSchedule or cfg.mp_mode != 'bp':
                raise ValueError('explicit uniform BP schedule requires BP mode')
            outer_bp_iterations = bp_schedule.outer_bp_iterations
        feedback_active = code_feedback is not None and code_feedback.enabled
        if feedback_active:
            if (cfg.mp_mode != 'bp' or not self.use_soft_decisions or
                    dals_mode not in ('mean','jsoft','zero_ridge','proximal') or
                    any(h is not None for h in (oracle_support, diagnostic_support_override,
                        diagnostic_channel_override, diagnostic_data_override))):
                raise ValueError('code feedback requires soft BP and no truth overrides')
            code_feedback.begin(N, outer_iterations, device)
        feedback_consumer = code_feedback
        stop_policy = feedback_active and code_feedback.stop_on_valid_codeword
        if stop_policy and (return_trajectory or cfg.early_stop or ce_support_exchange is not None or
                any(x is not None for x in (self.per_iter_refiner, self.iter_residual_selector,
                    self.symbol_refiner, getattr(self, '_early_exit_gate', None)))):
            raise ValueError('checkpoint stop requires the plain receiver without trajectory or alternative stopping/refinement')
        if diagnostic_code_symbols is not None:
            from .supplement_feedback_diagnostic import DiagnosticCodeSymbols
            if (type(diagnostic_code_symbols) is not DiagnosticCodeSymbols or code_feedback is not None or
                    cfg.mp_mode != 'bp' or not self.use_soft_decisions or dals_mode != 'mean' or
                    any(h is not None for h in (oracle_support, diagnostic_support_override,
                        diagnostic_channel_override, diagnostic_data_override, support_transaction))):
                raise ValueError('explicit symbol diagnostic requires isolated mean-CE route')
            diagnostic_code_symbols.begin(N, cfg.n_outer_iter, device)
            feedback_consumer = diagnostic_code_symbols.feedback
            feedback_active = feedback_consumer is not None
            if feedback_active:
                feedback_consumer.begin(N, cfg.n_outer_iter, device)
        if one_shot_true_data_ce is not None:
            from .one_shot_true_data_ce import OneShotTrueDataCE
            if (type(one_shot_true_data_ce) is not OneShotTrueDataCE or
                    diagnostic_code_symbols is not None or not feedback_active or
                    dals_mode != 'mean' or 1 not in ce_iterations or
                    channel_representation is not None or ce_support_exchange is not None or
                    any(h is not None for h in (oracle_support, diagnostic_support_override,
                        diagnostic_channel_override, diagnostic_data_override,
                        support_transaction))):
                raise ValueError('one-shot true data CE requires isolated legal mean-CE feedback')
            one_shot_true_data_ce.begin(N, outer_iterations, cfg.n_outer_iter, ce_iterations,
                code_feedback, dals_mode, device)
        if ce_support_exchange is not None:
            from .light_gap_support_exchange import CodeSupportExchange
            if (type(ce_support_exchange) is not CodeSupportExchange or code_feedback is None or
                    not feedback_active or code_feedback.control != 'legal' or code_feedback.consumer != 'both' or
                    dals_mode != 'jsoft' or enable_support_repair or support_transaction is not None or
                    diagnostic_code_symbols is not None or self.off_support_corr is not None or
                    self.channel_tap_corrector is not None):
                raise ValueError('discrete exchange requires isolated legal-code JSOFT and no learned support/correction hooks')
            ce_support_exchange.begin(cfg,ce_iterations,dals_start_iteration)
        K = 2 * cfg.k_max + 1
        Q = (cfg.l_max + 1) * K
        if channel_representation is not None:
            Q = (cfg.l_max+1)*channel_representation.geometry.q
        P_data = 1.0 - cfg.rho
        extension = cfg.k_leak if receiver_extension is None else receiver_extension
        capacity_trace = []
        transaction_result = None

        def check_capacity(columns, stage, iteration, limit=None):
            if active_support_cap is None:
                return
            columns = [int(i) for i in columns]
            if len(set(columns)) != len(columns) or any(i < 0 or i >= Q for i in columns):
                raise ValueError('capacity requires unique in-range support columns')
            limit = active_support_cap if limit is None else limit
            if len(columns) > limit:
                raise ValueError('support exceeds the registered active capacity')
            capacity_trace.append(dict(stage=stage, outer_iter=iteration,
                                       unique_count=len(columns), limit=limit,
                                       atom_ids=columns))

        def observe_temporary(columns, iteration, limit):
            check_capacity(columns, 'temporary', iteration, limit)

        def checked_diagnostic(value, reference, label):
            if (not isinstance(value, torch.Tensor) or value.shape != reference.shape
                    or value.dtype != reference.dtype or value.device != reference.device
                    or not torch.isfinite(value).all()):
                raise ValueError(f'diagnostic {label}: invalid shape, dtype, device or finite values')
            return value

        def soft_observer(stage, iteration):
            if diagnostic_soft_observer is None:
                return None
            return lambda payload: diagnostic_soft_observer(
                dict(stage=stage,outer_iter=iteration,**payload))

        if Phi is None and channel_representation is None:
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
        support_basis_indices = torch.zeros(0, dtype=torch.long, device=device)
        integer_indices = None
        integer_support = None
        integer_graph_calls = []
        prev_resnorm = torch.tensor(float('inf'), dtype=rdtype, device=device)

        traj: List[Dict[str, Any]] = []
        # B1/B2 bookkeeping: snapshot x_soft and resnorm at the end of each
        # outer iter so that IterResidualSelector can combine them.
        x_soft_history: List[torch.Tensor] = []
        resnorm_history: List[torch.Tensor] = []

        for t in range(outer_iterations):
            hp = self._scalars_for(t)
            hp = self._apply_strategy(t, hp, sigma2_eff,
                                      prev_resnorm,
                                      int(support_delays.numel()), Q)

            # ---- (A) channel estimation update ---------------------------
            if t == 0 and channel_representation is not None:
                support_delays,support_basis_indices,gains_S = channel_representation.initialize(y_daft,x_pilot_scaled)
            elif t == 0:
                if oracle_support is not None and len(oracle_support) > 0:
                    if active_support_cap is not None and any(
                            type(i) is not int and not isinstance(i, np.integer) for i in oracle_support):
                        raise ValueError('capacity requires integer support columns')
                    support_idx = list(int(i) for i in oracle_support)
                    check_capacity(support_idx, 'initial', t)
                    if diagnostic_support_override is not None or diagnostic_support_observer is not None or support_transaction is not None:
                        raw_support_idx = list(support_idx)
                    Phi_S = Phi[:, support_idx]
                    gains_on_support = torch.linalg.lstsq(
                        Phi_S, y_daft.unsqueeze(-1)).solution.squeeze(-1)
                    h_omp = torch.zeros(Q, dtype=cdtype, device=device)
                    for col_i, gv in zip(support_idx, gains_on_support):
                        h_omp[col_i] = gv
                else:
                    if initial_estimator is None:
                        h_omp, support_idx = omp_sparse_torch(y_daft, Phi, cfg.n_paths)
                    else:
                        h_omp, support_idx = initial_estimator(y_daft, Phi, cfg.n_paths, sigma2_eff)
                        if (h_omp.shape != (Q,) or h_omp.dtype != cdtype or h_omp.device != device
                                or not torch.isfinite(h_omp).all()
                                or any(type(i) is not int or not 0 <= i < Q for i in support_idx)
                                or len(set(support_idx)) != len(support_idx)):
                            raise ValueError('invalid initial estimator output')
                    check_capacity(support_idx, 'initial', t)
                    if diagnostic_support_override is not None or diagnostic_support_observer is not None or support_transaction is not None:
                        raw_support_idx = list(support_idx)

                    # C2-rel (cand_active_rel): learned support-repair hook
                    # inserted AFTER raw OMP and BEFORE cluster expansion.
                    # Zero-init (bias=-8) makes this a no-op at initialization.
                    if self.cand_active_rel is not None and enable_support_repair and support_transaction is None:
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
                                    score_override=getattr(
                                        self.cand_active_rel,
                                        '_gateA_scorer', None),
                                    tau_override=getattr(
                                        self.cand_active_rel,
                                        '_gateA_tau', None),
                                    capacity_observer=observe_temporary if active_support_cap is not None else None,
                                    proposal_observer=diagnostic_proposal_observer,
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

                if diagnostic_support_override is not None:
                    selected, diagnostic_gains = diagnostic_support_override(
                        Phi, y_daft, raw_support_idx, list(support_idx), h_omp, sigma2_eff)
                    if (not isinstance(selected, (list, tuple)) or not selected
                            or any(not isinstance(i, (int, np.integer)) for i in selected)
                            or len(set(selected)) != len(selected)
                            or any(i < 0 or i >= Q for i in selected)):
                        raise ValueError('diagnostic support: expected unique in-range integer columns')
                    support_idx = list(selected)
                    diagnostic_gains = checked_diagnostic(
                        diagnostic_gains, h_omp[support_idx], 'support gains')
                    h_omp = torch.zeros_like(h_omp)
                    h_omp[support_idx] = diagnostic_gains

                if support_transaction is None:
                    support_delays, support_dopplers, gains_S = expand_cluster_support(
                        support_idx, cfg.k_max, extension, h_omp, Q)
                else:
                    transaction_result = support_transaction(
                        Phi, y_daft, list(raw_support_idx), sigma2_eff,
                        cfg.k_max, extension, active_support_cap, observe_temporary)
                    if not transaction_result['valid_current']:
                        raise SupportProposalRejected(transaction_result['reason'])
                    committed = transaction_result['committed']
                    support_idx = list(committed['nomination_ids'])
                    support_delays = committed['support_delays'].clone()
                    support_dopplers = committed['support_dopplers'].clone()
                    gains_S = committed['gains'].clone()
                    if (gains_S.dtype != cdtype or gains_S.device != y_daft.device or
                            support_delays.dtype != torch.long or support_dopplers.dtype != torch.long or
                            support_delays.device != y_daft.device or support_dopplers.device != y_daft.device or
                            gains_S.ndim != 1 or
                            gains_S.shape != support_delays.shape or
                            support_dopplers.shape != support_delays.shape or
                            not bool(torch.isfinite(gains_S).all())):
                        raise ValueError('invalid committed transaction gain contract')
                    actual_ids = (support_delays*K+support_dopplers+cfg.k_max).tolist()
                    if actual_ids != committed['active_ids']:
                        raise ValueError('committed support/gain ID order mismatch')
                    check_capacity(actual_ids, 'transaction_commit', t)
                    if transaction_observer is not None:
                        transaction_observer(dict(stage='committed', active_ids=actual_ids,
                                                  gains=gains_S.detach().clone()))
                if active_support_cap is not None and support_delays.numel()>active_support_cap:
                    raise ValueError('expanded support exceeds the registered active capacity')
                if diagnostic_support_observer is not None:
                    diagnostic_support_observer(
                        raw_support_idx, list(support_idx), support_delays, support_dopplers)

                if dals_prior is not None:
                    dals_prior.initialize(N, support_delays, support_dopplers, gains_S)

            elif t in ce_iterations:
                active_dals_mode = dals_mode if t >= dals_start_iteration else 'mean'
                # DA-LS: build A on current support + hard-decision symbol estimate
                dals_payload = {}
                dals_soft_observer = soft_observer('dals_feedback',t)
                if diagnostic_dals_observer is not None:
                    existing_observer = dals_soft_observer
                    def capture_dals(payload):
                        dals_payload.update({key:value.detach().clone() for key,value in payload.items()})
                        if existing_observer is not None:
                            existing_observer(payload)
                    dals_soft_observer = capture_dals
                if feedback_active:
                    x_hard_scaled, data_variance = feedback_consumer.ce(t)
                    x_hard_scaled = x_hard_scaled.to(y_daft.dtype)
                elif self.use_soft_decisions:
                    # Use soft expectation for stable gradient.
                    HH_diag_cur = (H_hat.abs().pow(2)).sum(dim=0)
                    feedback = _qpsk_soft_decision(
                        x_soft_scaled, HH_diag_cur, sigma2_eff, constellation_data,
                        observer=dals_soft_observer,temperature=dals_temperature,
                        return_variance=active_dals_mode!='mean')
                    if active_dals_mode == 'mean':
                        x_hard_scaled = feedback
                    else:
                        x_hard_scaled, data_variance = feedback
                else:
                    x_hard_scaled = _qpsk_hard_decision(
                        x_soft_scaled, constellation_data)

                if diagnostic_data_override is not None:
                    x_hard_scaled = checked_diagnostic(
                        diagnostic_data_override(x_hard_scaled, t),
                        x_hard_scaled, 'data feedback')
                if diagnostic_code_symbols is not None:
                    x_hard_scaled = diagnostic_code_symbols.replace(t, x_hard_scaled, int(support_delays.numel()))
                if one_shot_true_data_ce is not None and t == 1:
                    x_hard_scaled = one_shot_true_data_ce.replace(
                        t, x_hard_scaled, data_variance, int(support_delays.numel()))
                x_total = x_pilot_scaled + x_hard_scaled
                num_paths = int(support_delays.numel())
                if num_paths > 0:
                    lambda_ls = torch.clamp(
                        hp['lambda_ls_factor'] * sigma2_eff, min=1e-6)
                    if ce_support_exchange is not None and t == ce_support_exchange.iteration:
                        support_delays,support_dopplers,gains_S = ce_support_exchange.apply(
                            cfg,y_daft,x_pilot_scaled,x_hard_scaled,data_variance,
                            support_delays,support_dopplers,gains_S,lambda_ls)
                        H_hat_active = ce_support_exchange.prune_memory(H_hat_active,cfg.k_max)
                        check_capacity((support_delays*K+support_dopplers+cfg.k_max).tolist(),'code_exchange',t)
                    if channel_representation is None:
                        A_total = build_A_for_DALS_torch(
                            N, support_delays, support_dopplers, x_total,
                            cfg.c1, cfg.c2, cfg.k_max, cdtype=cdtype)
                    else:
                        A_total = channel_representation.design(x_total)
                    base_regularization = lambda_ls
                    uncertainty = {}
                    if active_dals_mode == 'jsoft':
                        uncertainty['Q'] = data_uncertainty_gram(
                            N,support_delays,support_dopplers,data_variance,
                            cfg.c1,cfg.c2,cfg.k_max,cdtype)
                    elif active_dals_mode in ('zero_ridge','proximal'):
                        # Same dimensionless strength, different centers. A
                        # zero-centered term must never add Q @ g_old to rhs.
                        penalty = dals_strength*A_total.abs().square().sum()/num_paths
                        if active_dals_mode == 'zero_ridge':
                            uncertainty['Q'] = penalty.to(cdtype)*torch.eye(
                                num_paths,dtype=cdtype,device=device)
                        else:
                            lambda_ls = lambda_ls+penalty
                    elif active_dals_mode in ('covariance','covariance_uniform'):
                        if active_dals_mode == 'covariance_uniform':
                            uniform_variance = (constellation_data-constellation_data.mean()).abs().square().mean()
                            data_variance = torch.full_like(data_variance, uniform_variance)
                        uncertainty.update(C=residual_data_covariance(H_hat,data_variance,sigma2_eff),
                                           sigma2=sigma2_eff)
                    if dals_prior is not None:
                        uncertainty['Q'] = dals_prior.penalty(A_total, support_delays, support_dopplers)
                    if diagnostic_dals_observer is not None:
                        if feedback_active:
                            # This consumer has discrete feedback moments, not the
                            # Gaussian surrogate payload of _qpsk_soft_decision.
                            finite_variance = data_variance
                            moment_audit = dict(moment_source='code_feedback.ce',
                                feedback_moments_source=feedback_consumer.moments_source)
                        else:
                            p = dals_payload['probabilities']
                            finite_variance = (p*(constellation_data[None,:]-dals_payload['mean'][:,None]).abs().square()).sum(-1)
                            moment_audit = dict(
                                working_gaussian_variance=dals_payload['input_variance'].detach().clone(),
                                probabilities=p.detach().clone())
                        state = {key:value.detach().clone() for key,value in dict(
                            A=A_total,y=y_daft,g_previous=gains_S,H=H_hat,
                            mu=x_hard_scaled,finite_variance=finite_variance,
                            sigma2=sigma2_eff,regularization=lambda_ls,
                            base_regularization=base_regularization,
                            constellation=constellation_data,
                            support_delays=support_delays,
                            support_dopplers=support_dopplers).items()}
                        state.update(moment_audit)
                        true_data_ce = one_shot_true_data_ce is not None and t == 1
                        if (diagnostic_code_symbols is not None and t == diagnostic_code_symbols.checkpoint + 1
                                or true_data_ce):
                            # Original probabilities/variance describe the proposal,
                            # never the deterministic symbol actually used in A.
                            state['pre_override_moment_audit'] = dict(moment_audit,
                                finite_variance=state['finite_variance'])
                            for key in moment_audit:
                                state.pop(key)
                            state['finite_variance'] = torch.zeros_like(finite_variance)
                            state.update(moment_source=('true_data_ce' if true_data_ce else 'true_symbols_oracle'),
                                         variance_used_by_CE=False)
                        state.update(outer_iter=t, mode=active_dals_mode,requested_mode=dals_mode,
                                     start_iteration=dals_start_iteration,
                                     normalized_strength=dals_strength,
                                     covariance_frozen_within_solve=True,
                                    oracle_mean=diagnostic_data_override is not None or
                                        (diagnostic_code_symbols is not None and t == diagnostic_code_symbols.checkpoint + 1) or
                                        true_data_ce)
                        if 'C' in uncertainty:
                            state.update(consumed_variance=data_variance.detach().clone(),
                                         covariance=uncertainty['C'].detach().clone())
                        if 'Q' in uncertainty:
                            state['Q'] = uncertainty['Q'].detach().clone()
                    g_new = soft_gain_update(A_total,y_daft,gains_S,lambda_ls,**uncertainty)
                    completed_ce_solves += 1
                    if diagnostic_dals_observer is not None:
                        state['g_solution'] = g_new.detach().clone()
                        diagnostic_dals_observer(state)
                    if diagnostic_code_symbols is not None:
                        diagnostic_code_symbols.consume(t, A_total)
                    if one_shot_true_data_ce is not None and t == 1:
                        one_shot_true_data_ce.consume(t, A_total)
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
            if channel_representation is None:
                H_new = reconstruct_H_torch(
                    N, support_delays, support_dopplers, gains_S,
                    cfg.c1, cfg.c2, cfg.k_max, cdtype=cdtype)
            else:
                H_new = channel_representation.channel(gains_S)
            if t == 0 and support_transaction is not None and transaction_observer is not None:
                transaction_observer(dict(stage='t0_reconstruction',
                    active_ids=(support_delays*K+support_dopplers+cfg.k_max).tolist(),
                    gains=gains_S.detach().clone(), H=H_new.detach().clone()))
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
            if ce_support_exchange is not None and t == ce_support_exchange.iteration:
                ce_support_exchange.consume(H_hat,gains_S,gamma_h,hp['tau_h_factor'],
                    hp['tau_h_sigma_factor'],sigma2_eff)

            if diagnostic_channel_override is not None:
                H_hat = checked_diagnostic(
                    diagnostic_channel_override(H_hat, support_delays, support_dopplers, t),
                    H_hat, 'channel')

            # ---- (B) MP detection ----------------------------------------
            H_bp = H_hat
            if outer_bp_graph == 'integer':
                current_support = torch.stack((support_delays, support_dopplers))
                if integer_indices is None:
                    integer_support = current_support.clone()
                    # Aliased atoms may share a displacement. H_hat already
                    # contains their summed values, so store each entry once.
                    delta = torch.unique((support_delays*stride+support_dopplers) % N)
                    cols = torch.arange(N, device=device)[:, None].expand(N, delta.numel())
                    rows = (cols+delta[None, :]) % N
                    flat = torch.sort((rows*N+cols).reshape(-1)).values
                    integer_indices = torch.stack((flat//N, flat%N))
                elif not torch.equal(current_support, integer_support):
                    raise ValueError('integer BP graph support changed after layout construction')
                # Zero initialization, fixed-support reconstruction, damping
                # and pointwise masks cannot introduce entries off this layout.
                H_bp = torch.sparse_coo_tensor(integer_indices,
                    H_hat[integer_indices[0], integer_indices[1]], (N, N),
                    device=device, is_coalesced=True)
                if diagnostic_graph_observer is not None and not torch.equal(H_bp.to_dense(), H_hat):
                    raise ValueError('integer BP layout omitted an actual channel entry')
                integer_graph_calls.append(dict(outer_iter=t, candidate_entries=H_bp._nnz(),
                    complete_matrix_verified=diagnostic_graph_observer is not None))
            if active_support_cap is not None:
                columns = (support_delays * K + support_dopplers + cfg.k_max).tolist()
                check_capacity(columns, 'outer', t)
            y_data = y_daft - H_hat @ x_pilot_scaled
            if t == 0 and support_transaction is not None and transaction_observer is not None:
                transaction_observer(dict(stage='t0_bp_input', H=H_hat.detach().clone(),
                                          y_data=y_data.detach().clone()))
            pic_damp = hp['pic_damp'].to(rdtype)
            graph_observer = (None if diagnostic_graph_observer is None else
                              lambda payload: diagnostic_graph_observer(dict(stage='outer_bp', outer_iter=t, **payload)))
            count_kwargs = {}
            if bp_schedule is not None:
                def count_edges(edges):
                    schedule_calls.append(dict(outer_iter=t,requested_iterations=outer_bp_iterations,
                        executed_iterations=outer_bp_iterations if edges else 0, edges=edges))
                count_kwargs['edge_count_observer'] = count_edges
            if detector == 'siso_mmse':
                payload, siso = siso_mmse_torch(y_data, H_hat, sigma2_eff,
                                              constellation_data, feedback_consumer.prior)
                feedback_consumer.capture(payload)
                x_mp = payload['posterior_mean'].to(y_data.dtype)
                siso_calls.append(dict(outer_iter=t, **{k: siso[k] for k in
                    ('linear_solves', 'linear_rhs', 'factorization_dimension', 'linear_relative_residual')}))
                if retain_siso_states:
                    siso_states.append(dict(outer_iter=t, y=y_data.detach().clone(),
                        H=H_hat.detach().clone(), sigma2=float(sigma2_eff.detach()), **siso))
            elif cfg.mp_mode == 'bp':
                # Vectorized Gaussian BP on the sparse H graph. In soft mode
                # we return the posterior mean (differentiable); in eval/hard
                # mode we keep the hard nearest-constellation projection.
                if self.use_soft_decisions:
                    feedback_kwargs = ({'code_prior': feedback_consumer.prior, 'message_observer': feedback_consumer.capture}
                                       if feedback_active else {})
                    _, mu_post, _ = mp_detect_bp_torch(
                        y_data, H_bp, sigma2_eff, constellation_data,
                        n_iter=outer_bp_iterations, threshold=cfg.bp_threshold,
                        damp=pic_damp, return_numpy=False, return_soft=True, graph_observer=graph_observer,
                        **count_kwargs, **projection_kwargs, **feedback_kwargs)
                    x_mp = mu_post.to(y_data.dtype)
                else:
                    x_mp = mp_detect_bp_torch(
                        y_data, H_bp, sigma2_eff, constellation_data,
                        n_iter=outer_bp_iterations, threshold=cfg.bp_threshold,
                        damp=pic_damp, return_numpy=False,
                        return_soft=False, graph_observer=graph_observer, **count_kwargs, **projection_kwargs).to(y_data.dtype)
            else:
                x_mp = mp_detect_pic_torch(
                    y_data, H_hat, sigma2_eff, constellation_data,
                    n_iter=cfg.pic_iter, damp=pic_damp,
                    hard_decision=not self.use_soft_decisions)

            if feedback_active:
                feedback_consumer.after_detection(t)
                if stop_policy and feedback_consumer.stop_result is not None:
                    # This codeword has already been decoded. No later CE,
                    # detector, noise update or terminal decoder is needed.
                    x_soft_scaled = feedback_consumer.moments[0].to(cdtype)
                    x_soft_history.append(x_soft_scaled.clone())
                    break

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
                        x_soft_scaled, HH_diag_cur, sigma2_eff, constellation_data,
                        observer=soft_observer('noise_feedback',t))
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

            # W8 Path A — learned early-exit gate hook. Activated at runtime
            # by setting self._early_exit_gate to a dict {weights, bias, mu,
            # sigma, threshold, min_iter}. Features built from resnorm_history
            # + x_soft_history (already accumulated). Auto-detects v1 (4-dim)
            # vs v2 (6-dim) gate by len(weights). v2 adds hard-decision flip
            # rate + ||x_soft[t]-x_soft[t-1]||_2 (direct BER-convergence
            # proxies that resnorm-only v1 lacked).
            _ee_gate = getattr(self, '_early_exit_gate', None)
            if _ee_gate is not None and t >= int(_ee_gate.get('min_iter', 2)):
                _res_t = float(curr_resnorm.cpu().item())
                _res_tm1 = float(resnorm_history[-2].cpu().item())
                _res_0 = float(resnorm_history[0].cpu().item())
                _max_iter = cfg.n_outer_iter
                _feat = [
                    float(np.log(_res_t + 1e-30)),
                    float((_res_tm1 - _res_t) / max(_res_tm1, 1e-30)),
                    float(t / _max_iter),
                    float(_res_t / max(_res_0, 1e-30)),
                ]
                _n_feat = len(_ee_gate['weights'])
                if _n_feat >= 6:
                    # v2: flip rate + x_soft_delta (need hard decision of cur
                    # vs prev x_soft).
                    _x_cur = x_soft_history[-1]
                    _x_prev = x_soft_history[-2]
                    _b_cur = _qpsk_hard_decision(_x_cur, constellation_data)
                    _b_prev = _qpsk_hard_decision(_x_prev, constellation_data)
                    _flip_rate = float((_b_cur != _b_prev).to(rdtype).mean()
                                       .cpu().item())
                    _xdelta = float((_x_cur - _x_prev).abs().pow(2).sum()
                                    .sqrt().cpu().item())
                    _feat.extend([
                        float(np.log(_flip_rate + 1e-6)),
                        float(np.log(_xdelta + 1e-12)),
                    ])
                _mu = _ee_gate['mu']; _sigma = _ee_gate['sigma']
                _z = _ee_gate['bias']
                for _i in range(_n_feat):
                    _z += ((_feat[_i] - _mu[_i]) / _sigma[_i]) * _ee_gate['weights'][_i]
                _p_continue = 1.0 / (1.0 + float(np.exp(-max(min(_z, 30), -30))))
                if _p_continue < float(_ee_gate.get('threshold', 0.5)):
                    break

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
        if channel_representation is not None:
            del out['support_dopplers']
            out['support_basis_indices'] = support_basis_indices
            out['channel_representation'] = channel_representation.result()
        if stop_policy:
            out['checkpoint_stop'] = feedback_consumer.stop_result
            out['completed_outer_detections'] = t+1
            out['x_soft_stage'] = ('checkpoint_code_posterior' if feedback_consumer.stop_result is not None
                                   else 'normal_final_symbol_state')
        if outer_bp_graph is not None:
            out['integer_graph_calls'] = integer_graph_calls
        if detector == 'siso_mmse':
            out['siso_calls'] = siso_calls
            if retain_siso_states:
                out['siso_states'] = siso_states
        if return_trajectory:
            out['trajectory'] = traj
        if active_support_cap is not None:
            columns = (support_delays * K + support_dopplers + cfg.k_max).tolist()
            check_capacity(columns, 'final', len(x_soft_history) - 1)
            out['capacity_trace'] = capacity_trace
        if transaction_result is not None:
            out['support_transaction'] = transaction_result
        if bp_schedule is not None:
            out['bp_schedule'] = dict(outer_bp_iterations=outer_bp_iterations,calls=schedule_calls,
                completed_ce_solves=completed_ce_solves,
                outer_iterations=(t+1 if stop_policy else outer_iterations),
                scope='completed outer BP calls; empty graph executes zero iterations; graph audit overhead included')
        if outer_iteration_limit is not None or ce_update_iterations is not None:
            out['iteration_schedule']=dict(outer_iterations=len(x_soft_history),
                ce_update_iterations=list(ce_iterations),
                scope='omitted DA-LS solves only; channel damping, BP and noise updates still run')
        if ce_support_exchange is not None:
            if ce_support_exchange.record is None:raise RuntimeError('registered support exchange was not consumed')
            out['support_exchange']=ce_support_exchange.record
        if diagnostic_code_symbols is not None:
            diagnostic_code_symbols.finish()
        if one_shot_true_data_ce is not None:
            one_shot_true_data_ce.finish()
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
