"""
afdm_joint_unrolled.py

Model-driven sparse joint receiver aimed at surpassing the classical
joint OMP + MP baseline without reverting to a dense CE -> dense H ->
generic detector pipeline.

The design choices are intentionally close to the strong baseline:
  - sparse atom support over (delay, Doppler) paths
  - data-aided LS style gain update from the observation
  - iterative sparse MP-style detector
  - teacher distillation on LLR / soft symbols
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .afdm_layers import QPSKPosterior
from .afdm_models import CEBackbone


def block_to_complex(x_flat: torch.Tensor) -> torch.Tensor:
    n = x_flat.shape[1] // 2
    return torch.complex(x_flat[:, :n].float(), x_flat[:, n:].float())


def complex_to_block(x_c: torch.Tensor) -> torch.Tensor:
    return torch.cat([x_c.real.float(), x_c.imag.float()], dim=-1)


def embed_data_block(x_data_flat: torch.Tensor, n_total: int,
                     data_pos: torch.Tensor) -> torch.Tensor:
    if x_data_flat is None:
        raise ValueError("x_data_flat cannot be None")
    bsz = x_data_flat.shape[0]
    n_data = data_pos.numel()
    out = x_data_flat.new_zeros(bsz, 2 * n_total)
    out[:, data_pos] = x_data_flat[:, :n_data]
    out[:, n_total + data_pos] = x_data_flat[:, n_data:]
    return out


def extract_data_block(x_full_flat: torch.Tensor, data_pos: torch.Tensor) -> torch.Tensor:
    n_total = x_full_flat.shape[1] // 2
    return torch.cat([x_full_flat[:, data_pos],
                      x_full_flat[:, n_total + data_pos]], dim=-1)


def ber_from_detection(x_true: torch.Tensor, x_hat: torch.Tensor) -> torch.Tensor:
    n = x_true.shape[1] // 2
    bit0_true = (x_true[:, :n] < 0).float()
    bit1_true = (x_true[:, n:] < 0).float()
    bit0_hat = (x_hat[:, :n] < 0).float()
    bit1_hat = (x_hat[:, n:] < 0).float()
    return 0.5 * (
        (bit0_true != bit0_hat).float().mean() +
        (bit1_true != bit1_hat).float().mean()
    )


@dataclass
class SparseTargetBatch:
    support_teacher: torch.Tensor
    gain_teacher: torch.Tensor
    mu_teacher_full: torch.Tensor


def _stage_tensor(tensor: torch.Tensor | None, idx: int) -> torch.Tensor | None:
    if tensor is None:
        return None
    if tensor.dim() >= 3:
        return tensor[:, min(idx, tensor.shape[1] - 1)]
    return tensor


def _collapse_support_delay(tensor: torch.Tensor,
                            num_delays: int,
                            k_span: int,
                            use_logits: bool = False) -> torch.Tensor:
    tensor = tensor.reshape(tensor.shape[0], num_delays, k_span)
    if use_logits:
        return tensor.amax(dim=-1)
    return tensor.amax(dim=-1)


def _expand_delay_logits(delay_logits: torch.Tensor, k_span: int) -> torch.Tensor:
    return delay_logits.unsqueeze(-1).expand(-1, -1, k_span).reshape(delay_logits.shape[0], -1)


def _derive_seed_teacher(stage_support_t: torch.Tensor | None,
                         stage_gain_t: torch.Tensor | None,
                         num_delays: int,
                         k_span: int) -> torch.Tensor | None:
    if stage_support_t is None:
        return None
    support_grid = stage_support_t.reshape(stage_support_t.shape[0], num_delays, k_span)
    if stage_gain_t is not None:
        q = num_delays * k_span
        gain_r = stage_gain_t[:, :q].reshape(stage_gain_t.shape[0], num_delays, k_span)
        gain_i = stage_gain_t[:, q:].reshape(stage_gain_t.shape[0], num_delays, k_span)
        score_grid = torch.sqrt(gain_r.square() + gain_i.square() + 1e-8)
    else:
        score_grid = support_grid

    seed_grid = torch.zeros_like(support_grid)
    active_rows = support_grid.amax(dim=-1) > 0.0
    top_idx = score_grid.argmax(dim=-1, keepdim=True)
    seed_grid.scatter_(-1, top_idx, 1.0)
    seed_grid = seed_grid * active_rows.unsqueeze(-1).float()
    return seed_grid.reshape(stage_support_t.shape[0], -1)


def _weighted_focal_bce_with_logits(
        logits: torch.Tensor,
        targets: torch.Tensor,
        min_pos_weight: float = 1.0,
        max_pos_weight: float = 20.0,
        gamma: float = 1.5) -> torch.Tensor:
    targets = targets.float()
    with torch.no_grad():
        pos = targets.sum().clamp_min(1.0)
        neg = (targets.numel() - targets.sum()).clamp_min(1.0)
        pos_weight = (neg / pos).clamp(min=min_pos_weight, max=max_pos_weight)
    bce = F.binary_cross_entropy_with_logits(
        logits, targets, reduction="none", pos_weight=pos_weight
    )
    if gamma <= 0.0:
        return bce.mean()
    prob = torch.sigmoid(logits)
    pt = prob * targets + (1.0 - prob) * (1.0 - targets)
    focal = (1.0 - pt).clamp_min(1e-6).pow(gamma)
    return (bce * focal).mean()


def _masked_weighted_focal_bce_with_logits(
        logits: torch.Tensor,
        targets: torch.Tensor,
        mask: torch.Tensor | None = None,
        min_pos_weight: float = 1.0,
        max_pos_weight: float = 20.0,
        gamma: float = 1.5) -> torch.Tensor:
    if mask is None:
        return _weighted_focal_bce_with_logits(
            logits, targets,
            min_pos_weight=min_pos_weight,
            max_pos_weight=max_pos_weight,
            gamma=gamma,
        )
    mask = mask.float()
    denom = mask.sum().clamp_min(1.0)
    targets = targets.float()
    with torch.no_grad():
        pos = (targets * mask).sum().clamp_min(1.0)
        neg = (mask.sum() - (targets * mask).sum()).clamp_min(1.0)
        pos_weight = (neg / pos).clamp(min=min_pos_weight, max=max_pos_weight)
    bce = F.binary_cross_entropy_with_logits(
        logits, targets, reduction="none", pos_weight=pos_weight
    )
    if gamma > 0.0:
        prob = torch.sigmoid(logits)
        pt = prob * targets + (1.0 - prob) * (1.0 - targets)
        bce = bce * (1.0 - pt).clamp_min(1e-6).pow(gamma)
    return (bce * mask).sum() / denom


def _seed_topk_recall(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    with torch.no_grad():
        bsz = logits.shape[0]
        recall = logits.new_zeros(())
        for b in range(bsz):
            k = int(targets[b].sum().item())
            if k <= 0:
                recall = recall + logits.new_tensor(1.0)
                continue
            pred_idx = torch.topk(logits[b], k=min(k, logits.shape[1]), dim=-1).indices
            pred_mask = torch.zeros_like(targets[b])
            pred_mask[pred_idx] = 1.0
            tp = (pred_mask * targets[b]).sum()
            recall = recall + tp / targets[b].sum().clamp_min(1.0)
        return recall / max(bsz, 1)


def _seed_targets_to_delay_center(
        seed_targets: torch.Tensor,
        num_delays: int,
        k_span: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    seed_grid = seed_targets.reshape(seed_targets.shape[0], num_delays, k_span)
    delay_active = (seed_grid.amax(dim=-1) > 0.5).float()
    center_idx = seed_grid.argmax(dim=-1)
    return delay_active, center_idx, delay_active > 0.5


def _binary_recall_precision_from_logits(
        logits: torch.Tensor,
        targets: torch.Tensor,
        threshold: float = 0.5) -> tuple[torch.Tensor, torch.Tensor]:
    with torch.no_grad():
        pred = (torch.sigmoid(logits) >= threshold).float()
        tp = (pred * targets).sum(dim=-1)
        recall = tp / targets.sum(dim=-1).clamp_min(1.0)
        precision = tp / pred.sum(dim=-1).clamp_min(1.0)
        return recall.mean(), precision.mean()


def _binary_recall_precision_from_logits_masked(
        logits: torch.Tensor,
        targets: torch.Tensor,
        mask: torch.Tensor | None,
        threshold: float = 0.5) -> tuple[torch.Tensor, torch.Tensor]:
    if mask is None:
        return _binary_recall_precision_from_logits(logits, targets, threshold=threshold)
    with torch.no_grad():
        pred = ((torch.sigmoid(logits) >= threshold).float()) * mask.float()
        masked_targets = targets.float() * mask.float()
        tp = (pred * masked_targets).sum(dim=-1)
        recall = tp / masked_targets.sum(dim=-1).clamp_min(1.0)
        precision = tp / pred.sum(dim=-1).clamp_min(1.0)
        return recall.mean(), precision.mean()


def _flat_gain_abs(gain_flat: torch.Tensor, q: int) -> torch.Tensor:
    return torch.sqrt(
        gain_flat[:, :q].float().square() + gain_flat[:, q:].float().square() + 1e-8
    )


def _row_normalize_flat(tensor: torch.Tensor,
                        num_delays: int,
                        k_span: int,
                        eps: float = 1e-6) -> torch.Tensor:
    grid = tensor.reshape(tensor.shape[0], num_delays, k_span)
    denom = grid.sum(dim=-1, keepdim=True).clamp_min(eps)
    return (grid / denom).reshape(tensor.shape[0], -1)


class SparseAtomBank(nn.Module):
    """
    Sparse AFDM atom bank for (delay, Doppler) path atoms.

    Each atom contributes exactly one non-zero per input column, so we store
    only row indices and phases. This keeps the model aligned with the sparse
    classical baseline instead of materializing a dense atom basis.
    """

    def __init__(self, n_total: int, c1: float, c2: float,
                 l_max: int, k_max: int, k_leak: int = 2):
        super().__init__()
        self.n_total = int(n_total)
        self.l_max = int(l_max)
        self.k_max = int(k_max)
        self.k_leak = int(max(k_leak, 0))
        self.k_span = 2 * self.k_max + 1
        self.num_atoms = (self.l_max + 1) * (2 * self.k_max + 1)

        rows = []
        flat_idx = []
        phase_r = []
        phase_i = []
        delays = []
        dopplers = []

        n_arr = np.arange(self.n_total, dtype=np.float64)
        col_arr = np.arange(self.n_total, dtype=np.int64)
        for l_idx in range(self.l_max + 1):
            for k_idx in range(-self.k_max, self.k_max + 1):
                delta = l_idx * (2 * self.k_max + 1) + k_idx
                row_idx = ((n_arr.astype(np.int64) + delta) % self.n_total)
                row_f = row_idx.astype(np.float64)
                phase = np.exp(1j * 2.0 * np.pi * (
                    -c1 * (l_idx ** 2)
                    + c2 * (row_f ** 2 - n_arr ** 2)
                    - float(l_idx) * n_arr / self.n_total
                ))
                rows.append(row_idx)
                flat_idx.append(row_idx * self.n_total + col_arr)
                phase_r.append(np.real(phase).astype(np.float32))
                phase_i.append(np.imag(phase).astype(np.float32))
                delays.append(l_idx)
                dopplers.append(k_idx)

        self.register_buffer("row_idx", torch.from_numpy(np.stack(rows).astype(np.int64)))
        self.register_buffer("flat_idx", torch.from_numpy(np.stack(flat_idx).astype(np.int64)))
        self.register_buffer("phase_r", torch.from_numpy(np.stack(phase_r).astype(np.float32)))
        self.register_buffer("phase_i", torch.from_numpy(np.stack(phase_i).astype(np.float32)))
        self.register_buffer("delays", torch.from_numpy(np.array(delays, dtype=np.int64)))
        self.register_buffer("dopplers", torch.from_numpy(np.array(dopplers, dtype=np.int64)))

    def _default_seed_count(self, max_active_atoms: int) -> int:
        cluster_sz = max(1, 2 * self.k_leak + 1)
        return max(1, min(
            (int(max_active_atoms) + cluster_sz - 1) // cluster_sz,
            self.num_atoms,
        ))

    def seed_cluster_indices(self, seed_idx: int) -> list[int]:
        l_idx = int(seed_idx) // self.k_span
        k_idx = int(seed_idx) % self.k_span
        k_lo = max(0, k_idx - self.k_leak)
        k_hi = min(self.k_span, k_idx + self.k_leak + 1)
        base = l_idx * self.k_span
        return [base + k for k in range(k_lo, k_hi)]

    def ls_estimate(self, y_flat: torch.Tensor, x_total_flat: torch.Tensor) -> torch.Tensor:
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)

        # (B, Q, N) gather along atom-dependent row permutations.
        y_atom = y_c[:, self.row_idx]
        x_atom = x_c.unsqueeze(1)
        phase_c = torch.complex(self.phase_r, self.phase_i).unsqueeze(0)
        numer = (y_atom * torch.conj(phase_c * x_atom)).sum(dim=-1)
        denom = x_atom.abs().square().sum(dim=-1).clamp_min(1e-6)
        gains = numer / denom
        return complex_to_block(gains)

    def _expand_seed_mask(self, seed_mask: torch.Tensor) -> torch.Tensor:
        if self.k_leak <= 0:
            return seed_mask
        bsz = seed_mask.shape[0]
        grid = seed_mask.reshape(bsz, self.l_max + 1, self.k_span)
        expanded = torch.zeros_like(grid)
        for shift in range(-self.k_leak, self.k_leak + 1):
            if shift == 0:
                expanded = torch.maximum(expanded, grid)
                continue
            src_start = max(0, -shift)
            src_end = self.k_span - max(0, shift)
            dst_start = max(0, shift)
            dst_end = self.k_span - max(0, -shift)
            expanded[:, :, dst_start:dst_end] = torch.maximum(
                expanded[:, :, dst_start:dst_end],
                grid[:, :, src_start:src_end],
            )
        return expanded.reshape(bsz, -1)

    def _select_hard_support(self, support_score: torch.Tensor,
                             max_active_atoms: int,
                             num_seeds: int | None = None) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        bsz, q = support_score.shape
        if num_seeds is None:
            n_seeds = self._default_seed_count(max_active_atoms)
        else:
            n_seeds = max(1, min(int(num_seeds), q))
        work = support_score.reshape(bsz, self.l_max + 1, self.k_span).clone()
        seed_mask = torch.zeros_like(support_score)

        for b in range(bsz):
            chosen = 0
            while chosen < n_seeds:
                flat_idx = int(work[b].reshape(-1).argmax().item())
                l_idx = flat_idx // self.k_span
                k_idx = flat_idx % self.k_span
                if not torch.isfinite(work[b, l_idx, k_idx]):
                    break
                atom_idx = l_idx * self.k_span + k_idx
                seed_mask[b, atom_idx] = 1.0
                k_lo = max(0, k_idx - self.k_leak)
                k_hi = min(self.k_span, k_idx + self.k_leak + 1)
                work[b, l_idx, k_lo:k_hi] = float("-inf")
                chosen += 1

        hard_mask = self._expand_seed_mask(seed_mask)
        st_mask = hard_mask + support_score - support_score.detach()
        return hard_mask, st_mask, seed_mask

    @torch.amp.autocast("cuda", enabled=False)
    def omp_init_support(self,
                         y_flat: torch.Tensor,
                         x_total_flat: torch.Tensor,
                         max_active_atoms: int = 25,
                         lambda_ls: float = 1e-4) -> dict[str, torch.Tensor]:
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)
        bsz = y_flat.shape[0]
        q = self.num_atoms
        n_seeds = self._default_seed_count(max_active_atoms)
        phase_c_all = torch.complex(self.phase_r, self.phase_i)

        seed_mask = y_flat.new_zeros(bsz, q)
        hard_mask = y_flat.new_zeros(bsz, q)
        gain_out = torch.zeros(bsz, q, dtype=torch.complex64, device=y_flat.device)

        for b in range(bsz):
            residual = y_c[b]
            work_mask = torch.ones(q, dtype=torch.bool, device=y_flat.device)
            selected_seed: list[int] = []

            for _ in range(n_seeds):
                residual_atom = residual[self.row_idx]
                numer = (residual_atom * torch.conj(phase_c_all * x_c[b].unsqueeze(0))).sum(dim=-1)
                denom = x_c[b].abs().square().sum().clamp_min(1e-6)
                score = numer.abs() / denom
                score = torch.where(work_mask, score, torch.full_like(score, -1.0))
                atom_idx = int(score.argmax().item())
                if score[atom_idx] <= 0:
                    break
                selected_seed.append(atom_idx)
                l_idx = atom_idx // self.k_span
                k_idx = atom_idx % self.k_span
                k_lo = max(0, k_idx - self.k_leak)
                k_hi = min(self.k_span, k_idx + self.k_leak + 1)
                work_mask[l_idx * self.k_span + k_lo:l_idx * self.k_span + k_hi] = False

                seed_tmp = y_flat.new_zeros(1, q)
                seed_tmp[0, selected_seed] = 1.0
                support_tmp = self._expand_seed_mask(seed_tmp)[0]
                idx = torch.nonzero(support_tmp > 0.5, as_tuple=False).squeeze(-1)
                if idx.numel() == 0:
                    continue
                A = self._build_dictionary_single(x_c[b], idx)
                g_sel = self._small_complex_ls(A, y_c[b], lambda_ls)
                residual = y_c[b] - A @ g_sel

            if selected_seed:
                seed_mask[b, selected_seed] = 1.0
            else:
                pilot_score = self.ls_estimate(
                    y_flat[b:b + 1], x_total_flat[b:b + 1]
                )
                fallback_mask, _, fallback_seed = self._select_hard_support(
                    torch.log1p(torch.sqrt(
                        pilot_score[:, :q].square() + pilot_score[:, q:].square() + 1e-8
                    )),
                    max_active_atoms=max_active_atoms,
                    num_seeds=n_seeds,
                )
                seed_mask[b:b + 1] = fallback_seed
                hard_mask[b:b + 1] = fallback_mask
                continue

            hard_mask[b:b + 1] = self._expand_seed_mask(seed_mask[b:b + 1])
            idx = torch.nonzero(hard_mask[b] > 0.5, as_tuple=False).squeeze(-1)
            A = self._build_dictionary_single(x_c[b], idx)
            g_sel = self._small_complex_ls(A, y_c[b], lambda_ls)
            gain_out[b, idx] = g_sel

        gain_flat = complex_to_block(gain_out)
        return {
            "hard_mask": hard_mask,
            "seed_mask": seed_mask,
            "gain_flat": gain_flat,
        }

    @torch.amp.autocast("cuda", enabled=False)
    def refine_support_once(self,
                            seed_mask: torch.Tensor,
                            support_mask: torch.Tensor,
                            score: torch.Tensor,
                            y_flat: torch.Tensor,
                            x_total_flat: torch.Tensor,
                            gain_prior_flat: torch.Tensor | None = None,
                            max_active_atoms: int = 25,
                            lambda_ls: float = 1e-3,
                            rel_margin: float = 0.01,
                            max_swaps: int = 2,
                            top_candidates: int = 4) -> tuple[torch.Tensor, torch.Tensor]:
        bsz, q = seed_mask.shape
        cluster_sz = max(1, 2 * self.k_leak + 1)
        max_seeds = max(1, min((int(max_active_atoms) + cluster_sz - 1) // cluster_sz, q))
        seed_new = seed_mask.clone()
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)
        if gain_prior_flat is None:
            gain_prior_c = torch.zeros(
                bsz, q, dtype=torch.complex64, device=y_flat.device
            )
        else:
            gain_prior_c = torch.complex(
                gain_prior_flat[:, :q].float(),
                gain_prior_flat[:, q:].float(),
            )

        def _support_objective(batch_idx: int, trial_seed: torch.Tensor) -> float:
            trial_support = self._expand_seed_mask(trial_seed.unsqueeze(0))[0]
            idx = torch.nonzero(trial_support > 0.5, as_tuple=False).squeeze(-1)
            if idx.numel() == 0:
                return float("inf")
            A = self._build_dictionary_single(x_c[batch_idx], idx)
            prior_sel = gain_prior_c[batch_idx, idx]
            g_sel = self._small_complex_ls(A, y_c[batch_idx], lambda_ls, prior_sel=prior_sel)
            residual = y_c[batch_idx] - A @ g_sel
            return float(residual.abs().square().mean().real.item())

        for b in range(bsz):
            cur_seed = seed_new[b]
            cur_idx = torch.nonzero(cur_seed > 0.5, as_tuple=False).squeeze(-1)
            if cur_idx.numel() == 0:
                continue
            cur_obj = _support_objective(b, cur_seed)

            for _ in range(max_swaps):
                work = score[b].clone()
                work[self._expand_seed_mask(cur_seed.unsqueeze(0))[0] > 0.5] = float("-inf")
                cand_k = min(top_candidates, int(torch.isfinite(work).sum().item()))
                if cand_k <= 0:
                    break
                cand_scores, cand_indices = torch.topk(work, k=cand_k)

                cur_idx = torch.nonzero(cur_seed > 0.5, as_tuple=False).squeeze(-1)
                cur_scores = score[b, cur_idx]
                weakest_order = torch.argsort(cur_scores)
                weakest_candidates = cur_idx[weakest_order[: min(2, cur_idx.numel())]]
                best_seed = None
                best_obj = cur_obj

                for cand_score, cand_idx_t in zip(cand_scores, cand_indices):
                    cand_idx = int(cand_idx_t.item())
                    if not np.isfinite(float(cand_score.item())):
                        continue
                    trial_drop = [None] if cur_idx.numel() < max_seeds else [
                        int(idx.item()) for idx in weakest_candidates
                    ]
                    for drop_idx in trial_drop:
                        trial_seed = cur_seed.clone()
                        if drop_idx is not None:
                            trial_seed[drop_idx] = 0.0
                        trial_seed[cand_idx] = 1.0
                        trial_obj = _support_objective(b, trial_seed)
                        if trial_obj < best_obj:
                            best_obj = trial_obj
                            best_seed = trial_seed

                if best_seed is None:
                    break
                improvement = (cur_obj - best_obj) / max(abs(cur_obj), 1e-8)
                if improvement < rel_margin:
                    break
                cur_seed = best_seed
                cur_obj = best_obj

            seed_new[b] = cur_seed

        support_new = self._expand_seed_mask(seed_new)
        return support_new, seed_new

    def _build_dictionary_single(self, x_total_c: torch.Tensor,
                                 atom_idx: torch.Tensor) -> torch.Tensor:
        n = self.n_total
        k = int(atom_idx.numel())
        A = torch.zeros(n, k, dtype=torch.complex64, device=x_total_c.device)
        phase_all = torch.complex(self.phase_r[atom_idx], self.phase_i[atom_idx])
        row_all = self.row_idx[atom_idx]
        for j in range(k):
            col = torch.zeros(n, dtype=torch.complex64, device=x_total_c.device)
            col[row_all[j]] = phase_all[j] * x_total_c
            A[:, j] = col
        return A

    def _small_complex_ls(self, A: torch.Tensor, y: torch.Tensor,
                          lambda_ls: float,
                          prior_sel: torch.Tensor | None = None,
                          reg_diag: torch.Tensor | None = None) -> torch.Tensor:
        lambda_ls = float(lambda_ls)
        # Tiny complex GEMM/solve is unstable on some CUDA/MPS stacks.
        # Move the whole least-squares micro-kernel to CPU and copy the result back.
        if A.device.type in {"cuda", "mps"}:
            work_A = A.cpu()
            work_y = y.cpu()
            work_prior = prior_sel.cpu() if prior_sel is not None else None
            work_reg = reg_diag.cpu() if reg_diag is not None else None
            lhs = work_A.conj().transpose(0, 1) @ work_A
            rhs = work_A.conj().transpose(0, 1) @ work_y
            if work_reg is None:
                lhs = lhs + lambda_ls * torch.eye(lhs.shape[0], dtype=lhs.dtype, device=lhs.device)
            else:
                lhs = lhs + torch.diag(work_reg.to(lhs.dtype))
            if work_prior is not None:
                if work_reg is None:
                    rhs = rhs + lambda_ls * work_prior
                else:
                    rhs = rhs + work_reg.to(rhs.dtype) * work_prior
            return torch.linalg.solve(lhs, rhs).to(A.device)

        lhs = A.conj().transpose(0, 1) @ A
        rhs = A.conj().transpose(0, 1) @ y
        if reg_diag is None:
            lhs = lhs + lambda_ls * torch.eye(lhs.shape[0], dtype=lhs.dtype, device=lhs.device)
        else:
            lhs = lhs + torch.diag(reg_diag.to(lhs.dtype))
        if prior_sel is not None:
            if reg_diag is None:
                rhs = rhs + lambda_ls * prior_sel
            else:
                rhs = rhs + reg_diag.to(rhs.dtype) * prior_sel
        return torch.linalg.solve(lhs, rhs)

    @torch.amp.autocast("cuda", enabled=False)
    def active_set_refit(self,
                         y_flat: torch.Tensor,
                         x_total_flat: torch.Tensor,
                         support_score: torch.Tensor,
                         gain_prior_flat: torch.Tensor | None = None,
                         sigma_eff: torch.Tensor | None = None,
                         fixed_support_mask: torch.Tensor | None = None,
                         fixed_seed_mask: torch.Tensor | None = None,
                         max_active_atoms: int = 25,
                         lambda_ls: float | torch.Tensor = 1e-3,
                         beta_gain: float | torch.Tensor = 0.7,
                         lmmse_side_scale: float | torch.Tensor = 1.0) -> dict[str, torch.Tensor]:
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)
        q = self.num_atoms
        support_score = support_score.float()
        if fixed_support_mask is None:
            hard_mask, st_mask, seed_mask = self._select_hard_support(
                support_score=support_score,
                max_active_atoms=max_active_atoms,
            )
        else:
            st_mask = fixed_support_mask.float()
            hard_mask = (st_mask > 0.5).float()
            if fixed_seed_mask is None:
                seed_mask = hard_mask
            else:
                seed_mask = fixed_seed_mask.float()
            if bool((hard_mask.sum(dim=-1) <= 0.5).any().item()):
                fallback_mask, _, fallback_seed = self._select_hard_support(
                    support_score=support_score,
                    max_active_atoms=max_active_atoms,
                )
                empty_rows = (hard_mask.sum(dim=-1, keepdim=True) <= 0.5).float()
                hard_mask = empty_rows * fallback_mask + (1.0 - empty_rows) * hard_mask
                st_mask = empty_rows * fallback_mask + (1.0 - empty_rows) * st_mask
                seed_mask = empty_rows * fallback_seed + (1.0 - empty_rows) * seed_mask

        if gain_prior_flat is None:
            gain_prior_c = torch.zeros(
                y_flat.shape[0], q, dtype=torch.complex64, device=y_flat.device
            )
        else:
            gain_prior_c = torch.complex(
                gain_prior_flat[:, :q].float(),
                gain_prior_flat[:, q:].float(),
            )

        bsz = y_flat.shape[0]
        def _expand_param(param) -> torch.Tensor:
            if not torch.is_tensor(param):
                return y_flat.new_full((bsz, 1), float(param))
            p = param.float().to(y_flat.device)
            if p.numel() == 1:
                return p.reshape(1, 1).expand(bsz, 1)
            return p.reshape(bsz, 1)

        lambda_ls_t = _expand_param(lambda_ls)
        beta_gain_t = _expand_param(beta_gain)
        lmmse_side_t = _expand_param(lmmse_side_scale)

        gain_out = torch.zeros_like(gain_prior_c)
        sigma_ls = y_flat.new_zeros(y_flat.shape[0], 1)
        support_conf = hard_mask.clone()

        for b in range(y_flat.shape[0]):
            idx = torch.nonzero(hard_mask[b] > 0.5, as_tuple=False).squeeze(-1)
            if idx.numel() == 0:
                idx = torch.argmax(support_score[b], dim=-1, keepdim=True)
            A = self._build_dictionary_single(x_c[b], idx)
            prior_sel = gain_prior_c[b, idx]
            seed_sel = seed_mask[b, idx].float()
            side_sel = 1.0 - seed_sel
            lambda_b = float(lambda_ls_t[b, 0].detach().cpu())
            beta_b = float(beta_gain_t[b, 0].detach().cpu())
            side_b = float(lmmse_side_t[b, 0].detach().cpu())
            reg_diag = lambda_b * (1.0 + side_b * side_sel)
            g_ls = self._small_complex_ls(
                A, y_c[b], lambda_b, prior_sel=prior_sel, reg_diag=reg_diag
            )
            g_new = (1.0 - beta_b) * prior_sel + beta_b * g_ls
            gain_out[b, idx] = g_new
            residual = y_c[b] - A @ g_new
            sigma_ls[b, 0] = residual.abs().square().mean().real.float()

        gain_flat = complex_to_block(gain_out)
        return {
            "gain_flat": gain_flat,
            "hard_mask": hard_mask,
            "st_mask": st_mask,
            "seed_mask": seed_mask,
            "sigma_ls": sigma_ls,
            "support_conf": support_conf,
        }

    def project_teacher_support(self, y_flat: torch.Tensor,
                                x_total_teacher_flat: torch.Tensor) -> SparseTargetBatch:
        gain_teacher = self.ls_estimate(y_flat, x_total_teacher_flat)
        q = self.num_atoms
        gr = gain_teacher[:, :q]
        gi = gain_teacher[:, q:]
        g_abs = torch.sqrt(gr.square() + gi.square() + 1e-8)
        g_norm = g_abs / g_abs.amax(dim=1, keepdim=True).clamp_min(1e-6)
        return SparseTargetBatch(
            support_teacher=g_norm.clamp(0.0, 1.0),
            gain_teacher=gain_teacher,
            mu_teacher_full=x_total_teacher_flat,
        )

    def reconstruct(self, gain_flat: torch.Tensor,
                    support_weight: torch.Tensor | None = None) -> torch.Tensor:
        q = self.num_atoms
        gr = gain_flat[:, :q]
        gi = gain_flat[:, q:]
        if support_weight is not None:
            gr = gr * support_weight
            gi = gi * support_weight

        h_r = (
            gr.unsqueeze(-1) * self.phase_r.unsqueeze(0) -
            gi.unsqueeze(-1) * self.phase_i.unsqueeze(0)
        )
        h_i = (
            gr.unsqueeze(-1) * self.phase_i.unsqueeze(0) +
            gi.unsqueeze(-1) * self.phase_r.unsqueeze(0)
        )

        bsz = gain_flat.shape[0]
        h_r_flat = gain_flat.new_zeros(bsz, self.n_total * self.n_total)
        h_i_flat = gain_flat.new_zeros(bsz, self.n_total * self.n_total)
        scatter_idx = self.flat_idx.reshape(1, -1).expand(bsz, -1)
        h_r_flat.scatter_add_(1, scatter_idx, h_r.reshape(bsz, -1))
        h_i_flat.scatter_add_(1, scatter_idx, h_i.reshape(bsz, -1))
        return torch.cat([h_r_flat, h_i_flat], dim=-1)

    def block_matvec(self, h_flat: torch.Tensor, x_flat: torch.Tensor) -> torch.Tensor:
        n = self.n_total
        hr = h_flat[:, :n * n].reshape(-1, n, n)
        hi = h_flat[:, n * n:].reshape(-1, n, n)
        xr = x_flat[:, :n].unsqueeze(-1)
        xi = x_flat[:, n:].unsqueeze(-1)
        yr = (torch.bmm(hr, xr) - torch.bmm(hi, xi)).squeeze(-1)
        yi = (torch.bmm(hr, xi) + torch.bmm(hi, xr)).squeeze(-1)
        return torch.cat([yr, yi], dim=-1)


class SparseSupportProposal(nn.Module):
    def __init__(self, ce_backbone: CEBackbone, grid_dim: int,
                 aux_dim: int, num_atoms: int, num_delays: int,
                 hidden_dim: int = 512):
        super().__init__()
        self.backbone = ce_backbone
        self.grid_dim = int(grid_dim)
        self.aux_dim = int(aux_dim)
        self.num_atoms = int(num_atoms)
        self.num_delays = int(num_delays)

        in_dim = self.grid_dim + self.aux_dim
        self.norm = nn.LayerNorm(in_dim)
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.seed_head = nn.Linear(hidden_dim, num_atoms)
        self.support_head = nn.Linear(hidden_dim, num_delays)
        self.gain_head = nn.Linear(hidden_dim, 2 * num_atoms)
        nn.init.constant_(self.seed_head.bias, -2.0)
        nn.init.constant_(self.support_head.bias, -2.0)

    def forward(self, inp_feat: torch.Tensor) -> dict[str, torch.Tensor]:
        h_sc = self.backbone(inp_feat)
        aux = inp_feat[:, self.grid_dim:self.grid_dim + self.aux_dim]
        feat = self.mlp(self.norm(torch.cat([h_sc, aux], dim=-1)))
        center_logit = self.seed_head(feat)
        support_logit = self.support_head(feat)
        gain_flat = self.gain_head(feat)
        return {
            "channel_init": h_sc,
            "center_logit": center_logit,
            "support_logit": support_logit,
            "gain_flat": gain_flat,
        }


class LeakageClusterRefiner(nn.Module):
    """
    Lightweight anchored refiner that predicts cluster weights and gain
    residuals on the (delay, Doppler) atom grid.
    """

    def __init__(self, num_delays: int, k_span: int,
                 in_channels: int = 9, hidden_channels: int = 64,
                 n_res: int = 3):
        super().__init__()
        self.num_delays = int(num_delays)
        self.k_span = int(k_span)
        self.stem = nn.Conv2d(in_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False)
        self.stem_bn = nn.BatchNorm2d(hidden_channels, momentum=0.01)
        self.blocks = nn.ModuleList()
        for _ in range(n_res):
            self.blocks.append(nn.ModuleDict({
                "conv1": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn1": nn.BatchNorm2d(hidden_channels, momentum=0.01),
                "conv2": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn2": nn.BatchNorm2d(hidden_channels, momentum=0.01),
            }))
        self.cluster_head = nn.Conv2d(hidden_channels, 1, (1, 1))
        self.gain_head = nn.Conv2d(hidden_channels, 2, (1, 1))
        nn.init.constant_(self.cluster_head.bias, -1.5)
        nn.init.zeros_(self.gain_head.bias)

    def forward(self, feat: torch.Tensor) -> dict[str, torch.Tensor]:
        x = F.relu(self.stem_bn(self.stem(feat)))
        for block in self.blocks:
            sc = x
            x = F.relu(block["bn1"](block["conv1"](x)))
            x = block["bn2"](block["conv2"](x))
            x = F.relu(x + sc)
        cluster_logit = self.cluster_head(x).reshape(feat.shape[0], -1)
        gain_delta_2 = self.gain_head(x)
        gain_delta = torch.cat([
            gain_delta_2[:, 0].reshape(feat.shape[0], -1),
            gain_delta_2[:, 1].reshape(feat.shape[0], -1),
        ], dim=-1)
        return {
            "cluster_logit": cluster_logit,
            "gain_delta": gain_delta,
        }


class LeakagePatchAggregator(nn.Module):
    """
    Anchored local patch refiner that predicts channel-evidence / cluster
    heatmaps on the (delay, Doppler) atom grid without directly touching gain.
    """

    def __init__(self, num_delays: int, k_span: int,
                 in_channels: int = 9, hidden_channels: int = 64,
                 n_res: int = 3):
        super().__init__()
        self.num_delays = int(num_delays)
        self.k_span = int(k_span)
        self.stem = nn.Conv2d(in_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False)
        self.stem_bn = nn.BatchNorm2d(hidden_channels, momentum=0.01)
        self.blocks = nn.ModuleList()
        for _ in range(n_res):
            self.blocks.append(nn.ModuleDict({
                "conv1": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn1": nn.BatchNorm2d(hidden_channels, momentum=0.01),
                "conv2": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn2": nn.BatchNorm2d(hidden_channels, momentum=0.01),
            }))
        self.patch_head = nn.Conv2d(hidden_channels, 1, (1, 1))
        nn.init.constant_(self.patch_head.bias, -1.0)

    def forward(self, feat: torch.Tensor) -> dict[str, torch.Tensor]:
        x = F.relu(self.stem_bn(self.stem(feat)))
        for block in self.blocks:
            sc = x
            x = F.relu(block["bn1"](block["conv1"](x)))
            x = block["bn2"](block["conv2"](x))
            x = F.relu(x + sc)
        patch_logit = self.patch_head(x).reshape(feat.shape[0], -1)
        return {
            "patch_logit": patch_logit,
        }


class GainGridPnPDenoiser(nn.Module):
    """
    Lightweight post-refit denoiser that operates on the sparse gain grid and
    predicts a conservative residual update for active atoms only.
    """

    def __init__(self, num_delays: int, k_span: int,
                 in_channels: int = 9, hidden_channels: int = 64,
                 n_res: int = 3):
        super().__init__()
        self.num_delays = int(num_delays)
        self.k_span = int(k_span)
        self.stem = nn.Conv2d(in_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False)
        self.stem_bn = nn.BatchNorm2d(hidden_channels, momentum=0.01)
        self.blocks = nn.ModuleList()
        for _ in range(n_res):
            self.blocks.append(nn.ModuleDict({
                "conv1": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn1": nn.BatchNorm2d(hidden_channels, momentum=0.01),
                "conv2": nn.Conv2d(hidden_channels, hidden_channels, (3, 3), padding=(1, 1), bias=False),
                "bn2": nn.BatchNorm2d(hidden_channels, momentum=0.01),
            }))
        self.delta_head = nn.Conv2d(hidden_channels, 2, (1, 1))
        nn.init.zeros_(self.delta_head.weight)
        nn.init.zeros_(self.delta_head.bias)

    def forward(self, feat: torch.Tensor) -> dict[str, torch.Tensor]:
        x = F.relu(self.stem_bn(self.stem(feat)))
        for block in self.blocks:
            sc = x
            x = F.relu(block["bn1"](block["conv1"](x)))
            x = block["bn2"](block["conv2"](x))
            x = F.relu(x + sc)
        delta_2 = self.delta_head(x)
        delta_gain_flat = torch.cat([
            delta_2[:, 0].reshape(feat.shape[0], -1),
            delta_2[:, 1].reshape(feat.shape[0], -1),
        ], dim=-1)
        return {
            "delta_gain_flat": delta_gain_flat,
        }


class PnPMixController(nn.Module):
    """
    Tiny condition-aware controller for the conservative PnP residual strength.
    """

    def __init__(self, input_dim: int = 5, hidden_dim: int = 12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )
        final = self.net[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

    def forward(self, feat: torch.Tensor) -> torch.Tensor:
        return self.net(feat.float())


class DetectorPosteriorPnPRefiner(nn.Module):
    """
    Lightweight detector-side posterior refiner operating on per-symbol features.
    It outputs bounded residuals for the soft symbol mean and a conservative
    log-variance shift.
    """

    def __init__(self, in_channels: int = 9, hidden_channels: int = 48,
                 n_res: int = 2):
        super().__init__()
        self.stem = nn.Conv1d(in_channels, hidden_channels, kernel_size=1, bias=False)
        self.stem_bn = nn.BatchNorm1d(hidden_channels, momentum=0.01)
        self.blocks = nn.ModuleList()
        for _ in range(n_res):
            self.blocks.append(nn.ModuleDict({
                "conv1": nn.Conv1d(hidden_channels, hidden_channels, kernel_size=1, bias=False),
                "bn1": nn.BatchNorm1d(hidden_channels, momentum=0.01),
                "conv2": nn.Conv1d(hidden_channels, hidden_channels, kernel_size=1, bias=False),
                "bn2": nn.BatchNorm1d(hidden_channels, momentum=0.01),
            }))
        self.delta_x_head = nn.Conv1d(hidden_channels, 2, kernel_size=1)
        self.delta_v_head = nn.Conv1d(hidden_channels, 1, kernel_size=1)
        self.reset_delta_heads_zero()

    def reset_delta_heads_zero(self) -> None:
        nn.init.zeros_(self.delta_x_head.weight)
        nn.init.zeros_(self.delta_x_head.bias)
        nn.init.zeros_(self.delta_v_head.weight)
        nn.init.zeros_(self.delta_v_head.bias)

    def reset_delta_heads_small_random(self, std: float = 1e-3) -> None:
        nn.init.normal_(self.delta_x_head.weight, mean=0.0, std=float(std))
        nn.init.zeros_(self.delta_x_head.bias)
        nn.init.normal_(self.delta_v_head.weight, mean=0.0, std=float(std))
        nn.init.zeros_(self.delta_v_head.bias)

    def forward(self, feat: torch.Tensor) -> dict[str, torch.Tensor]:
        x = F.relu(self.stem_bn(self.stem(feat.float())))
        for block in self.blocks:
            sc = x
            x = F.relu(block["bn1"](block["conv1"](x)))
            x = block["bn2"](block["conv2"](x))
            x = F.relu(x + sc)
        delta_x = self.delta_x_head(x)
        delta_v = self.delta_v_head(x)
        return {
            "delta_x": delta_x,
            "delta_v": delta_v,
        }


class DetectorPriorGammaController(nn.Module):
    """
    Tiny state-aware controller for detector-side posterior refinement strength.
    """

    def __init__(self, input_dim: int = 4, hidden_dim: int = 12):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 1),
        )
        final = self.net[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

    def forward(self, feat: torch.Tensor) -> torch.Tensor:
        return self.net(feat.float())


def _make_detector_prior_teacher_gamma_schedule(num_outer_iters: int) -> torch.Tensor:
    base = [0.20, 0.15, 0.10, 0.05, 0.02]
    sched = [base[min(t, len(base) - 1)] for t in range(int(num_outer_iters))]
    return torch.tensor(sched, dtype=torch.float32)


class SparseMPLayer(nn.Module):
    def __init__(self):
        super().__init__()
        self.step_raw = nn.Parameter(torch.tensor(0.0))
        self.damp_raw = nn.Parameter(torch.tensor(0.0))
        self.noise_scale_raw = nn.Parameter(torch.tensor(-1.0))
        self.interf_mix_raw = nn.Parameter(torch.tensor(-1.0))
        self.var_floor_raw = nn.Parameter(torch.tensor(-4.0))

    @torch.amp.autocast("cuda", enabled=False)
    def forward(self, y_d_c: torch.Tensor, h_d_c: torch.Tensor,
                mu_prev: torch.Tensor, v_prev: torch.Tensor,
                sigma2: torch.Tensor, qpsk_post: QPSKPosterior,
                llr_a_sym: torch.Tensor | None = None):
        sigma2 = sigma2.view(-1, 1).float()
        step = F.softplus(self.step_raw) + 0.1
        damp = torch.sigmoid(self.damp_raw)
        noise_scale = F.softplus(self.noise_scale_raw) + 0.05
        interf_mix = torch.sigmoid(self.interf_mix_raw)
        var_floor = F.softplus(self.var_floor_raw) + 1e-4

        h_abs2 = h_d_c.abs().square()
        col_pow = h_abs2.sum(dim=1).clamp_min(1e-6)
        residual = y_d_c - torch.bmm(h_d_c, mu_prev.unsqueeze(-1)).squeeze(-1)
        mf = torch.bmm(
            h_d_c.transpose(-2, -1).conj(), residual.unsqueeze(-1)
        ).squeeze(-1)
        z = mu_prev + step * mf / col_pow

        interf_all = torch.bmm(
            h_abs2.transpose(-2, -1), v_prev.unsqueeze(-1)
        ).squeeze(-1)
        self_term = col_pow * v_prev
        interf = (interf_all - self_term).clamp_min(0.0)
        tau = noise_scale * sigma2 / col_pow + interf_mix * interf / col_pow.square()
        tau = tau.clamp_min(var_floor)

        mu_post, v_post, llr = qpsk_post(
            torch.stack([z.real, z.imag], dim=-1),
            tau.unsqueeze(-1),
            llr_a=llr_a_sym,
        )
        mu_post_c = torch.complex(mu_post[..., 0], mu_post[..., 1])
        v_post_s = v_post.squeeze(-1)
        mu_next = (1.0 - damp) * mu_prev + damp * mu_post_c
        v_next = (1.0 - damp) * v_prev + damp * v_post_s
        return mu_next, v_next, llr


class SparseMPDetector(nn.Module):
    """
    Sparse-graph flavored iterative detector. It keeps the same public
    contract as the existing soft detectors:
      [H, y, xp, sigma] or [H, y, xp, sigma, mu0, v0, llr_a]
    """

    _INV_SQRT2 = float(1.0 / np.sqrt(2.0))

    def __init__(self, n_total: int, data_positions: np.ndarray | torch.Tensor,
                 num_layers: int = 6):
        super().__init__()
        self.n_total = int(n_total)
        data_pos_arr = np.asarray(data_positions, dtype=np.int64)
        self.n_data = int(data_pos_arr.size)
        self.register_buffer("data_pos", torch.from_numpy(data_pos_arr))
        self.noise_floor = nn.Parameter(torch.tensor(-3.0))
        self.layers = nn.ModuleList([SparseMPLayer() for _ in range(num_layers)])
        self.qpsk_post = QPSKPosterior()

    def _prior_from_llr(self, llr_a_flat: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        n = self.n_data
        llr = torch.stack([llr_a_flat[:, :n], llr_a_flat[:, n:]], dim=-1)
        mu = -torch.tanh(llr * 0.5) * self._INV_SQRT2
        var = (0.5 - mu.square()).mean(dim=-1).clamp_min(1e-3)
        return torch.complex(mu[..., 0], mu[..., 1]), var

    @torch.amp.autocast("cuda", enabled=False)
    def forward(self, inputs):
        if len(inputs) == 4:
            h_flat, y_flat, xp_flat, sigma_w2 = inputs
            mu_init_flat = None
            v_init_flat = None
            llr_a_flat = None
        elif len(inputs) == 6:
            (h_flat, y_flat, xp_flat, sigma_w2,
             mu_init_flat, v_init_flat) = inputs
            llr_a_flat = None
        elif len(inputs) == 7:
            (h_flat, y_flat, xp_flat, sigma_w2,
             mu_init_flat, v_init_flat, llr_a_flat) = inputs
        else:
            raise ValueError(
                "SparseMPDetector expects 4, 6, or 7 inputs, got "
                f"{len(inputs)}")

        n = self.n_total
        h_flat = h_flat.float()
        y_flat = y_flat.float()
        xp_flat = xp_flat.float()
        sigma_w2 = sigma_w2.float()

        h_r = h_flat[:, :n * n].reshape(-1, n, n)
        h_i = h_flat[:, n * n:].reshape(-1, n, n)
        h_c = torch.complex(h_r, h_i)
        h_d_c = h_c[:, :, self.data_pos]

        y_c = block_to_complex(y_flat)
        xp_c = block_to_complex(xp_flat)
        hxp = torch.bmm(h_c, xp_c.unsqueeze(-1)).squeeze(-1)
        y_d_c = y_c - hxp
        sigma2 = sigma_w2.squeeze(-1) + F.softplus(self.noise_floor) * 0.1

        if mu_init_flat is not None:
            mu_prev = torch.complex(mu_init_flat[:, :self.n_data].float(),
                                    mu_init_flat[:, self.n_data:].float())
            if v_init_flat.shape[1] == 2 * self.n_data:
                v_prev = 0.5 * (
                    v_init_flat[:, :self.n_data].float() +
                    v_init_flat[:, self.n_data:].float()
                )
            else:
                v_prev = v_init_flat.float()
            v_prev = v_prev.clamp_min(1e-3)
        elif llr_a_flat is not None:
            mu_prev, v_prev = self._prior_from_llr(llr_a_flat.float())
        else:
            bsz = h_flat.shape[0]
            mu_prev = torch.zeros(bsz, self.n_data,
                                  dtype=torch.complex64, device=h_flat.device)
            v_prev = torch.full((bsz, self.n_data), 0.5,
                                dtype=torch.float32, device=h_flat.device)

        llr_a_sym = None
        if llr_a_flat is not None:
            llr_a_sym = torch.stack([
                llr_a_flat[:, :self.n_data].float(),
                llr_a_flat[:, self.n_data:].float(),
            ], dim=-1)

        llr_last = None
        for layer in self.layers:
            mu_prev, v_prev, llr_last = layer(
                y_d_c, h_d_c, mu_prev, v_prev, sigma2, self.qpsk_post, llr_a_sym
            )

        if llr_last is None:
            raise RuntimeError("SparseMPDetector produced no output")
        x_hat = torch.cat([mu_prev.real.float(), mu_prev.imag.float()], dim=-1)
        v_flat = torch.cat([v_prev, v_prev], dim=-1)
        llr_flat = torch.cat([llr_last[..., 0], llr_last[..., 1]], dim=-1)
        return x_hat, v_flat, llr_flat


class IterationStrategy(nn.Module):
    def __init__(self, hidden_dim: int = 16, output_dim: int = 4):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )
        final = self.net[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

    def forward(self, state_feat: torch.Tensor) -> torch.Tensor:
        return self.net(state_feat.float())


class JointSparseUnrolledReceiver(nn.Module):
    def __init__(self, proposal_net: SparseSupportProposal,
                 atom_bank: SparseAtomBank,
                 n_total: int,
                 data_positions: np.ndarray | torch.Tensor,
                 num_outer_iters: int = 5,
                 num_mp_layers: int = 6,
                 max_active_atoms: int = 25,
                 use_hybrid_support_init: bool = True,
                 freeze_support_after_init: bool = True,
                 receiver_variant: str = "baseline",
                 uncertainty_variant: str = "baseline",
                 detector_prior_variant: str = "baseline",
                 disable_gain_delta: bool = False,
                 support_consumption: str = "soft",
                 hard_mask_threshold: float = 0.6,
                 hard_mask_topk: int = 1,
                 pnp_lambda_max: float = 0.25,
                 detector_prior_gamma_max: float = 0.20,
                 oracle_probe_mode: str = "identity",
                 oracle_alpha: float = 0.0,
                 oracle_conf_threshold: float = 1.5):
        super().__init__()
        self.n_total = int(n_total)
        self.atom_bank = atom_bank
        self.max_active_atoms = int(max_active_atoms)
        data_pos_arr = np.asarray(data_positions, dtype=np.int64)
        self.n_data = int(data_pos_arr.size)
        self.register_buffer("data_pos", torch.from_numpy(data_pos_arr))

        self.proposal = proposal_net
        self.detectors = nn.ModuleList([
            SparseMPDetector(n_total, data_pos_arr, num_layers=num_mp_layers)
            for _ in range(num_outer_iters)
        ])
        self.strategy_mlps = nn.ModuleList([
            IterationStrategy(hidden_dim=16)
            for _ in range(num_outer_iters)
        ])
        self.num_outer_iters = int(num_outer_iters)
        self.use_hybrid_support_init = bool(use_hybrid_support_init)
        self.freeze_support_after_init = bool(freeze_support_after_init)
        self.receiver_variant = str(receiver_variant).lower()
        self.uncertainty_variant = str(uncertainty_variant).lower()
        self.detector_prior_variant = str(detector_prior_variant).lower()
        self.disable_gain_delta = bool(disable_gain_delta)
        self.support_consumption = str(support_consumption).lower()
        self.hard_mask_threshold = float(hard_mask_threshold)
        self.hard_mask_topk = int(max(hard_mask_topk, 0))
        self.pnp_lambda_max = float(max(pnp_lambda_max, 0.0))
        self.detector_prior_gamma_max = float(max(detector_prior_gamma_max, 0.0))
        self.oracle_probe_mode = str(oracle_probe_mode).lower()
        self.oracle_alpha = float(max(oracle_alpha, 0.0))
        self.oracle_conf_threshold = float(max(oracle_conf_threshold, 0.0))
        if self.receiver_variant not in {"baseline", "leakage_aware", "patch_aggregator", "pnp_prior"}:
            raise ValueError(f"Unsupported receiver_variant={receiver_variant!r}")
        if self.uncertainty_variant not in {"baseline", "vx_recal_v1"}:
            raise ValueError(f"Unsupported uncertainty_variant={uncertainty_variant!r}")
        if self.detector_prior_variant not in {"baseline", "pnp_sd_v1", "pnp_sd_v2", "distill_sd_v1", "distill_sd_v1_neg", "oracle_probe"}:
            raise ValueError(f"Unsupported detector_prior_variant={detector_prior_variant!r}")
        if self.oracle_probe_mode not in {"identity", "mu_blend", "confidence_gated_mu_blend"}:
            raise ValueError(f"Unsupported oracle_probe_mode={oracle_probe_mode!r}")
        if self.support_consumption not in {"soft", "hard_hybrid"}:
            raise ValueError(f"Unsupported support_consumption={support_consumption!r}")
        if self.receiver_variant == "patch_aggregator" and self.support_consumption != "hard_hybrid":
            raise ValueError("patch_aggregator currently requires support_consumption='hard_hybrid'")
        self.leakage_refiner = (
            LeakageClusterRefiner(
                num_delays=self.atom_bank.l_max + 1,
                k_span=self.atom_bank.k_span,
            )
            if self.receiver_variant == "leakage_aware" else None
        )
        self.patch_aggregator = (
            LeakagePatchAggregator(
                num_delays=self.atom_bank.l_max + 1,
                k_span=self.atom_bank.k_span,
            )
            if self.receiver_variant == "patch_aggregator" else None
        )
        self.pnp_denoiser = (
            GainGridPnPDenoiser(
                num_delays=self.atom_bank.l_max + 1,
                k_span=self.atom_bank.k_span,
            )
            if self.receiver_variant == "pnp_prior" else None
        )
        self.pnp_mix_controller = (
            PnPMixController(input_dim=5, hidden_dim=12)
            if self.receiver_variant == "pnp_prior" else None
        )
        self.detector_prior_refiner = (
            DetectorPosteriorPnPRefiner(in_channels=9, hidden_channels=48, n_res=2)
            if self.detector_prior_variant in {"pnp_sd_v1", "pnp_sd_v2", "distill_sd_v1"} else None
        )
        if self.detector_prior_variant in {"pnp_sd_v2", "distill_sd_v1"} and self.detector_prior_refiner is not None:
            self.detector_prior_refiner.reset_delta_heads_small_random(std=1e-3)
        self.detector_prior_gamma_controller = (
            DetectorPriorGammaController(input_dim=4, hidden_dim=12)
            if self.detector_prior_variant == "pnp_sd_v2" else None
        )
        self.register_buffer(
            "detector_prior_teacher_gamma_schedule",
            _make_detector_prior_teacher_gamma_schedule(num_outer_iters),
        )

        self.support_blend_raw = nn.Parameter(torch.full((num_outer_iters,), -0.2))
        self.score_damp_raw = nn.Parameter(torch.full((num_outer_iters,), 0.0))
        self.gain_damp_raw = nn.Parameter(torch.full((num_outer_iters,), 0.0))
        self.proposal_gain_mix_raw = nn.Parameter(torch.full((num_outer_iters,), -0.2))
        self.prune_raw = nn.Parameter(torch.full((num_outer_iters,), 0.35))
        self.temp_raw = nn.Parameter(torch.full((num_outer_iters,), -0.2))
        self.sigma_mix_raw = nn.Parameter(torch.full((num_outer_iters,), 0.0))
        self.lambda_ls_raw = nn.Parameter(torch.full((num_outer_iters,), -6.0))
        self.lmmse_side_raw = nn.Parameter(torch.full((num_outer_iters,), -0.7))
        self.sic_beta_raw = nn.Parameter(torch.full((num_outer_iters,), 0.0))
        pnp_init_frac = float(np.clip(
            0.15 / max(self.pnp_lambda_max, 1e-6),
            0.05, 0.95,
        ))
        self.pnp_mix_raw = nn.Parameter(
            torch.full((num_outer_iters,), float(np.log(pnp_init_frac / (1.0 - pnp_init_frac))))
        )
        self.uncert_scale_raw = nn.Parameter(torch.zeros(num_outer_iters))
        gamma_sched = []
        for t in range(num_outer_iters):
            if num_outer_iters <= 1:
                target_gamma = 0.08
            else:
                frac = float(t) / float(num_outer_iters - 1)
                target_gamma = 0.10 - 0.05 * frac
            target_frac = float(np.clip(
                target_gamma / max(self.detector_prior_gamma_max, 1e-6),
                0.05, 0.95,
            ))
            gamma_sched.append(float(np.log(target_frac / (1.0 - target_frac))))
        self.detector_prior_gamma_raw = nn.Parameter(torch.tensor(gamma_sched, dtype=torch.float32))

    def _strategy_params(self, t: int, sigma_eff: torch.Tensor,
                         v_prev: torch.Tensor | None,
                         res_energy_prev: torch.Tensor) -> dict[str, torch.Tensor]:
        sigma_scalar = sigma_eff.reshape(-1, 1).float().clamp_min(1e-8)
        sigma_feat = torch.clamp(
            torch.log10(sigma_scalar.squeeze(-1)) / 2.0,
            min=-1.0, max=1.0,
        )
        if v_prev is None:
            vx_mean = torch.full_like(sigma_feat, 0.5)
        else:
            vx_mean = v_prev.float().mean(dim=-1).clamp_min(1e-6)
        vx_feat = torch.clamp(vx_mean / 0.5, min=0.0, max=2.0) - 1.0
        res_feat = torch.clamp(
            torch.log10(res_energy_prev.float().clamp_min(1e-8)) / 2.0,
            min=-1.0, max=1.0,
        )
        state_feat = torch.stack([sigma_feat, vx_feat, res_feat], dim=-1)
        strategy_out = self.strategy_mlps[t](state_feat)

        scale_lambda = F.softplus(strategy_out[:, 0:1]) + 1e-4
        base_sigma_mix_logit = self.sigma_mix_raw[t].reshape(1, 1).float().to(sigma_eff.device)
        sigma_mix = torch.sigmoid(base_sigma_mix_logit + strategy_out[:, 1:2])
        sic_beta = F.softplus(strategy_out[:, 2:3]) + 0.1
        side_reg = F.softplus(strategy_out[:, 3:4]) + 1e-4
        lambda_ls = sigma_scalar * scale_lambda
        return {
            "lambda_ls": lambda_ls,
            "sigma_mix": sigma_mix,
            "sic_beta": sic_beta,
            "side_reg": side_reg,
        }

    def _build_leakage_features(self,
                                phys_score: torch.Tensor,
                                prior_seed_prob: torch.Tensor,
                                prior_support_prob: torch.Tensor,
                                omp_seed_mask: torch.Tensor,
                                omp_support_mask: torch.Tensor,
                                gain_prev: torch.Tensor,
                                gain_ls: torch.Tensor,
                                sigma_eff: torch.Tensor,
                                residual_energy: torch.Tensor) -> torch.Tensor:
        bsz = phys_score.shape[0]
        num_delays = self.atom_bank.l_max + 1
        k_span = self.atom_bank.k_span
        q = self.atom_bank.num_atoms

        def _to_grid(flat: torch.Tensor) -> torch.Tensor:
            return flat.reshape(bsz, 1, num_delays, k_span)

        sigma_grid = sigma_eff.reshape(bsz, 1, 1, 1).float().expand(-1, 1, num_delays, k_span)
        residual_grid = residual_energy.reshape(bsz, 1, 1, 1).float().expand(-1, 1, num_delays, k_span)
        gain_prev_abs = _flat_gain_abs(gain_prev, q)
        gain_ls_abs = _flat_gain_abs(gain_ls, q)
        return torch.cat([
            _to_grid(phys_score.float()),
            _to_grid(prior_seed_prob.float()),
            _to_grid(prior_support_prob.float()),
            _to_grid(omp_seed_mask.float()),
            _to_grid(omp_support_mask.float()),
            _to_grid(gain_prev_abs.float()),
            _to_grid(gain_ls_abs.float()),
            sigma_grid,
            residual_grid,
        ], dim=1)

    def _build_pnp_features(self,
                            gain_refit: torch.Tensor,
                            support_used: torch.Tensor,
                            support_seed: torch.Tensor,
                            prior_seed_prob: torch.Tensor,
                            prior_support_prob: torch.Tensor,
                            sigma_eff: torch.Tensor,
                            residual_energy: torch.Tensor) -> torch.Tensor:
        bsz = gain_refit.shape[0]
        num_delays = self.atom_bank.l_max + 1
        k_span = self.atom_bank.k_span
        q = self.atom_bank.num_atoms

        def _to_grid(flat: torch.Tensor) -> torch.Tensor:
            return flat.reshape(bsz, 1, num_delays, k_span)

        gain_r = gain_refit[:, :q].float()
        gain_i = gain_refit[:, q:].float()
        gain_abs = _flat_gain_abs(gain_refit, q).float()
        sigma_grid = sigma_eff.reshape(bsz, 1, 1, 1).float().expand(-1, 1, num_delays, k_span)
        residual_grid = residual_energy.reshape(bsz, 1, 1, 1).float().expand(-1, 1, num_delays, k_span)
        return torch.cat([
            _to_grid(gain_r),
            _to_grid(gain_i),
            _to_grid(gain_abs),
            _to_grid(support_used.float()),
            _to_grid(support_seed.float()),
            _to_grid(prior_seed_prob.float()),
            _to_grid(prior_support_prob.float()),
            sigma_grid,
            residual_grid,
        ], dim=1)

    def _build_pnp_mix_features(self,
                                t: int,
                                sigma_eff: torch.Tensor,
                                residual_energy: torch.Tensor,
                                v_prev: torch.Tensor | None,
                                support_used: torch.Tensor) -> torch.Tensor:
        bsz = sigma_eff.shape[0]
        if self.num_outer_iters <= 1:
            iter_feat = sigma_eff.new_zeros(bsz)
        else:
            iter_feat = sigma_eff.new_full((bsz,), float(t) / float(self.num_outer_iters - 1))
        sigma_feat = torch.clamp(
            torch.log10(sigma_eff.reshape(-1).float().clamp_min(1e-8)) / 2.0,
            min=-1.0, max=1.0,
        )
        res_feat = torch.clamp(
            torch.log10(residual_energy.reshape(-1).float().clamp_min(1e-8)) / 2.0,
            min=-1.0, max=1.0,
        )
        if v_prev is None:
            vx_mean = sigma_eff.new_full((bsz,), 0.5)
        else:
            vx_mean = v_prev.float().mean(dim=-1).clamp_min(1e-6)
        vx_feat = torch.clamp(vx_mean / 0.5, min=0.0, max=2.0) - 1.0
        support_density = support_used.float().mean(dim=-1).clamp(0.0, 1.0)
        density_feat = 2.0 * support_density - 1.0
        return torch.stack([iter_feat, sigma_feat, res_feat, vx_feat, density_feat], dim=-1)

    def _build_detector_prior_features(self,
                                       x_hat: torch.Tensor,
                                       v_x: torch.Tensor,
                                       llr: torch.Tensor,
                                       residual_data: torch.Tensor,
                                       t: int,
                                       sigma_eff: torch.Tensor) -> torch.Tensor:
        n_d = self.n_data
        x_r = x_hat[:, :n_d].float()
        x_i = x_hat[:, n_d:].float()
        llr_r = llr[:, :n_d].float()
        llr_i = llr[:, n_d:].float()
        res_r = residual_data[:, :n_d].float()
        res_i = residual_data[:, n_d:].float()
        if v_x.shape[1] == 2 * n_d:
            v_sym = 0.5 * (v_x[:, :n_d].float() + v_x[:, n_d:].float())
        else:
            v_sym = v_x.float()
        sigma_feat = sigma_eff.reshape(-1, 1).float().expand(-1, n_d)
        if self.num_outer_iters <= 1:
            iter_feat = sigma_feat.new_zeros(sigma_feat.shape)
        else:
            iter_feat = sigma_feat.new_full(
                sigma_feat.shape, float(t) / float(self.num_outer_iters - 1)
            )
        return torch.stack([
            x_r, x_i,
            llr_r, llr_i,
            res_r, res_i,
            torch.log(v_sym.clamp_min(1e-6)),
            torch.log(sigma_feat.clamp_min(1e-8)),
            iter_feat,
        ], dim=1)

    def _build_detector_prior_gamma_features(self,
                                             t: int,
                                             v_x: torch.Tensor,
                                             llr: torch.Tensor,
                                             residual_energy: torch.Tensor) -> torch.Tensor:
        bsz = residual_energy.shape[0]
        if self.num_outer_iters <= 1:
            iter_feat = residual_energy.new_zeros(bsz)
        else:
            iter_feat = residual_energy.new_full((bsz,), float(t) / float(self.num_outer_iters - 1))
        n_d = self.n_data
        if v_x.shape[1] == 2 * n_d:
            v_sym = 0.5 * (v_x[:, :n_d].float() + v_x[:, n_d:].float())
        else:
            v_sym = v_x.float()
        vx_mean = v_sym.mean(dim=-1).clamp_min(1e-6)
        vx_feat = torch.clamp(torch.log10(vx_mean) / 2.0, min=-1.0, max=1.0)
        res_feat = torch.clamp(
            torch.log10(residual_energy.reshape(-1).float().clamp_min(1e-8)) / 2.0,
            min=-1.0, max=1.0,
        )
        llr_mag = 0.5 * (
            llr[:, :n_d].float().abs().mean(dim=-1) +
            llr[:, n_d:].float().abs().mean(dim=-1)
        )
        conf_feat = torch.clamp(llr_mag / 4.0, min=0.0, max=2.0) - 1.0
        return torch.stack([iter_feat, vx_feat, res_feat, conf_feat], dim=-1)

    def _cluster_prob_to_hard_mask(self,
                                   cluster_prob: torch.Tensor,
                                   seed_mask: torch.Tensor,
                                   support_mask: torch.Tensor) -> dict[str, torch.Tensor]:
        bsz = cluster_prob.shape[0]
        num_delays = self.atom_bank.l_max + 1
        k_span = self.atom_bank.k_span
        tau = float(self.hard_mask_threshold)
        topk = int(self.hard_mask_topk)

        cluster_grid = cluster_prob.reshape(bsz, num_delays, k_span).float()
        seed_grid = seed_mask.reshape(bsz, num_delays, k_span).float()
        support_grid = support_mask.reshape(bsz, num_delays, k_span).float()

        hard_grid = seed_grid.clone()
        expand_grid = torch.zeros_like(seed_grid)
        expand_count_grid = torch.zeros_like(seed_grid)

        if topk > 0:
            for b in range(bsz):
                seed_pos = torch.nonzero(seed_grid[b] > 0.5, as_tuple=False)
                for pos in seed_pos:
                    l_idx = int(pos[0].item())
                    k_idx = int(pos[1].item())
                    k_lo = max(0, k_idx - self.atom_bank.k_leak)
                    k_hi = min(k_span, k_idx + self.atom_bank.k_leak + 1)

                    cand_scores = cluster_grid[b, l_idx, k_lo:k_hi]
                    cand_support = support_grid[b, l_idx, k_lo:k_hi] > 0.5
                    cand_seed = seed_grid[b, l_idx, k_lo:k_hi] > 0.5
                    cand_mask = (cand_scores > tau) & cand_support & (~cand_seed)
                    cand_idx = torch.nonzero(cand_mask, as_tuple=False).squeeze(-1)
                    if cand_idx.numel() <= 0:
                        continue

                    if cand_idx.numel() > topk:
                        cand_vals = cand_scores[cand_idx]
                        sel = torch.topk(cand_vals, k=topk, dim=0).indices
                        cand_idx = cand_idx[sel]

                    abs_idx = cand_idx + k_lo
                    expand_grid[b, l_idx, abs_idx] = 1.0
                    expand_count_grid[b, l_idx, k_idx] = float(abs_idx.numel())

        expand_grid = torch.minimum(expand_grid, support_grid)
        hard_grid = torch.maximum(seed_grid, expand_grid)
        hard_grid = torch.minimum(torch.maximum(hard_grid, seed_grid), support_grid)
        expand_grid = torch.clamp(hard_grid - seed_grid, min=0.0, max=1.0)

        return {
            "cluster_hard_mask": hard_grid.reshape(bsz, -1),
            "cluster_expand_mask": expand_grid.reshape(bsz, -1),
            "cluster_expand_count": expand_count_grid.reshape(bsz, -1),
        }

    def forward(self, inp_feat: torch.Tensor, inp_y: torch.Tensor,
                inp_xp: torch.Tensor, inp_sigma: torch.Tensor,
                teacher_support_iter: torch.Tensor | None = None,
                teacher_seed_iter: torch.Tensor | None = None,
                teacher_gain_iter: torch.Tensor | None = None,
                teacher_mu_iter: torch.Tensor | None = None,
                teacher_var_iter: torch.Tensor | None = None,
                teacher_llr_iter: torch.Tensor | None = None,
        teacher_force: float = 0.0,
        max_outer_iters: int | None = None) -> dict[str, torch.Tensor]:
        prop = self.proposal(inp_feat)
        prior_center_logit = prop["center_logit"]
        prior_support_logit = prop["support_logit"]
        prior_seed_logit = prior_center_logit + _expand_delay_logits(
            prior_support_logit, self.atom_bank.k_span
        )
        prior_gain = prop["gain_flat"]

        q = self.atom_bank.num_atoms
        if self.use_hybrid_support_init:
            omp_init = self.atom_bank.omp_init_support(
                y_flat=inp_y,
                x_total_flat=inp_xp,
                max_active_atoms=self.max_active_atoms,
            )
            fixed_support_base = omp_init["hard_mask"].detach()
            fixed_seed_base = omp_init["seed_mask"].detach()
            gain_prev = omp_init["gain_flat"].detach()
            seed_score_prev = fixed_support_base
        else:
            fixed_support_base = None
            fixed_seed_base = None
            seed_score_prev = prior_seed_logit
            gain_prev = prior_gain
        mu_prev = None
        v_prev = None
        llr_prev = None
        sigma_eff = inp_sigma.float()
        res_energy_prev = block_to_complex(inp_y).abs().square().mean(dim=-1)
        history = []
        num_iters = self.num_outer_iters if max_outer_iters is None else min(
            self.num_outer_iters, int(max_outer_iters)
        )

        for t in range(num_iters):
            detector = self.detectors[t]
            teacher_support_t = _stage_tensor(teacher_support_iter, t)
            teacher_support_delay_t = None
            if teacher_support_t is not None:
                teacher_support_delay_t = _collapse_support_delay(
                    teacher_support_t,
                    num_delays=self.atom_bank.l_max + 1,
                    k_span=self.atom_bank.k_span,
                )
            teacher_seed_t = _stage_tensor(teacher_seed_iter, t)
            teacher_gain_t = _stage_tensor(teacher_gain_iter, t)
            teacher_mu_prev = _stage_tensor(teacher_mu_iter, t - 1) if t > 0 else None
            teacher_var_prev = _stage_tensor(teacher_var_iter, t - 1) if t > 0 else None
            teacher_llr_prev = _stage_tensor(teacher_llr_iter, t - 1) if t > 0 else None
            strategy = self._strategy_params(t, sigma_eff, v_prev, res_energy_prev)
            lambda_ls_t = strategy["lambda_ls"]
            sigma_mix_t = strategy["sigma_mix"]
            sic_beta_t = strategy["sic_beta"]
            side_reg_t = strategy["side_reg"]

            if mu_prev is None:
                x_total = inp_xp
            else:
                mu_ref = mu_prev
                v_ref = v_prev
                if teacher_mu_prev is not None and teacher_force > 0.0:
                    mu_ref = (1.0 - teacher_force) * mu_prev + teacher_force * teacher_mu_prev
                if teacher_var_prev is not None and teacher_force > 0.0:
                    if v_ref is None:
                        v_ref = teacher_var_prev
                    else:
                        v_ref = (1.0 - teacher_force) * v_prev + teacher_force * teacher_var_prev
                if self.use_hybrid_support_init and v_ref is not None:
                    n_d = self.n_data
                    if v_ref.shape[1] == 2 * n_d:
                        v_sym = 0.5 * (v_ref[:, :n_d] + v_ref[:, n_d:])
                    else:
                        v_sym = v_ref
                    gamma = (1.0 - sic_beta_t * v_sym.float()).clamp(0.0, 1.0)
                    mu_ref = torch.cat([
                        mu_ref[:, :n_d] * gamma,
                        mu_ref[:, n_d:] * gamma,
                    ], dim=-1)
                x_total = inp_xp + embed_data_block(mu_ref, self.n_total, self.data_pos)

            gain_score = self.atom_bank.ls_estimate(inp_y, x_total)
            phys_score = torch.log1p(torch.sqrt(
                gain_score[:, :q].square() + gain_score[:, q:].square() + 1e-8
            ))

            if self.use_hybrid_support_init:
                lambda_ls_mean = float(lambda_ls_t.mean().detach().cpu())
                if t == 0 or not self.freeze_support_after_init:
                    omp_init = self.atom_bank.omp_init_support(
                        y_flat=inp_y,
                        x_total_flat=x_total,
                        max_active_atoms=self.max_active_atoms,
                        lambda_ls=lambda_ls_mean,
                    )
                    fixed_support_base = omp_init["hard_mask"].detach()
                    fixed_seed_base = omp_init["seed_mask"].detach()
                    if t == 0:
                        gain_prev = omp_init["gain_flat"].detach()
                    elif not self.freeze_support_after_init:
                        fixed_support_base, fixed_seed_base = self.atom_bank.refine_support_once(
                            seed_mask=fixed_seed_base,
                            support_mask=fixed_support_base,
                            score=phys_score,
                            y_flat=inp_y,
                            x_total_flat=x_total,
                            gain_prior_flat=gain_prev,
                            max_active_atoms=self.max_active_atoms,
                            lambda_ls=lambda_ls_mean,
                        )
                        fixed_support_base = fixed_support_base.detach()
                        fixed_seed_base = fixed_seed_base.detach()
                temp = F.softplus(self.temp_raw[t]) + 0.1
                seed_logit = prior_seed_logit / temp
                support_logit = prior_support_logit / temp
                seed_prob = torch.sigmoid(seed_logit)
                support_prob = torch.sigmoid(support_logit)
                support_for_refit = fixed_support_base
                seed_for_refit = fixed_seed_base
            else:
                mix_support = torch.sigmoid(self.support_blend_raw[t])
                damp_score = torch.sigmoid(self.score_damp_raw[t])
                seed_score_target = mix_support * prior_seed_logit + (1.0 - mix_support) * phys_score
                seed_score_prev = (1.0 - damp_score) * seed_score_prev + damp_score * seed_score_target

                temp = F.softplus(self.temp_raw[t]) + 0.1
                seed_logit = (seed_score_prev - self.prune_raw[t]) / temp
                seed_prob = torch.sigmoid(seed_logit)
                support_logit = prior_support_logit / temp
                support_prob = torch.sigmoid(support_logit)
                support_for_refit = seed_prob
                seed_for_refit = seed_prob
            support_prob_atom = _expand_delay_logits(support_prob, self.atom_bank.k_span)
            cluster_logit = None
            cluster_prob = None
            cluster_hard_mask = None
            cluster_expand_mask = None
            cluster_expand_count = None
            patch_logit = None
            patch_prob = None
            patch_hard_mask = None
            patch_expand_mask = None
            patch_expand_count = None
            gain_delta = None
            pnp_delta = None
            pnp_mix = None
            pnp_lambda = None
            pnp_identity_gap = None
            gain_refit_raw = None
            gain_pnp = None
            h_refit_flat = None
            h_pnp_flat = None
            detection_raw = None
            detector_prior_delta = None
            detector_prior_gamma = None
            detector_prior_gamma_eff = None
            detector_prior_gamma_iter = None
            detector_prior_gamma_state = None
            detector_prior_identity_gap = None
            refined_vx = None
            support_anchor = fixed_support_base if self.use_hybrid_support_init else None
            if teacher_seed_t is None and teacher_support_t is not None:
                teacher_seed_t = _derive_seed_teacher(
                    stage_support_t=teacher_support_t,
                    stage_gain_t=teacher_gain_t,
                    num_delays=self.atom_bank.l_max + 1,
                    k_span=self.atom_bank.k_span,
                )
            if teacher_force > 0.0:
                if (not self.use_hybrid_support_init) and teacher_seed_t is not None:
                    seed_for_refit = (
                        (1.0 - teacher_force) * seed_for_refit +
                        teacher_force * teacher_seed_t
                    )
                elif (not self.use_hybrid_support_init) and teacher_support_t is not None:
                    seed_for_refit = (
                        (1.0 - teacher_force) * seed_for_refit +
                        teacher_force * teacher_support_t
                    )
                if (not self.use_hybrid_support_init) and teacher_support_t is not None:
                    support_for_refit = (
                        (1.0 - teacher_force) * support_for_refit +
                        teacher_force * teacher_support_t
                    )

            if teacher_support_delay_t is not None and teacher_force > 0.0:
                support_prob = (
                    (1.0 - teacher_force) * support_prob +
                    teacher_force * teacher_support_delay_t
                )
                support_prob_atom = _expand_delay_logits(support_prob, self.atom_bank.k_span)

            if self.use_hybrid_support_init:
                gain_prior = gain_prev
                if fixed_support_base is not None and fixed_seed_base is not None:
                    feat_leak = self._build_leakage_features(
                        phys_score=phys_score,
                        prior_seed_prob=seed_prob,
                        prior_support_prob=support_prob_atom,
                        omp_seed_mask=fixed_seed_base,
                        omp_support_mask=fixed_support_base,
                        gain_prev=gain_prev,
                        gain_ls=gain_score,
                        sigma_eff=sigma_eff,
                        residual_energy=res_energy_prev,
                    )
                    anchor_mask = fixed_support_base.float()
                    seed_mask_anchor = fixed_seed_base.float()

                    if self.receiver_variant == "leakage_aware" and self.leakage_refiner is not None:
                        leak_out = self.leakage_refiner(feat_leak)
                        cluster_logit_raw = leak_out["cluster_logit"]
                        neg_fill = torch.full_like(cluster_logit_raw, -12.0)
                        cluster_logit = torch.where(anchor_mask > 0.5, cluster_logit_raw, neg_fill)
                        cluster_prob = torch.sigmoid(cluster_logit) * anchor_mask
                        cluster_prob = torch.maximum(cluster_prob, seed_mask_anchor)
                        cluster_prob = torch.minimum(cluster_prob, anchor_mask)
                        if self.support_consumption == "hard_hybrid":
                            hard_out = self._cluster_prob_to_hard_mask(
                                cluster_prob=cluster_prob,
                                seed_mask=seed_mask_anchor,
                                support_mask=anchor_mask,
                            )
                            cluster_hard_mask = hard_out["cluster_hard_mask"]
                            cluster_expand_mask = hard_out["cluster_expand_mask"]
                            cluster_expand_count = hard_out["cluster_expand_count"]
                            support_for_refit = cluster_hard_mask.float()
                        else:
                            support_for_refit = cluster_prob
                        seed_for_refit = seed_mask_anchor
                        anchor_2q = torch.cat([anchor_mask, anchor_mask], dim=-1)
                        gain_delta = leak_out["gain_delta"] * anchor_2q
                        gain_prior = gain_prev if self.disable_gain_delta else (gain_prev + gain_delta)
                    elif self.receiver_variant == "patch_aggregator" and self.patch_aggregator is not None:
                        patch_out = self.patch_aggregator(feat_leak)
                        patch_logit_raw = patch_out["patch_logit"]
                        neg_fill = torch.full_like(patch_logit_raw, -12.0)
                        patch_logit = torch.where(anchor_mask > 0.5, patch_logit_raw, neg_fill)
                        patch_prob = torch.sigmoid(patch_logit) * anchor_mask
                        patch_prob = torch.maximum(patch_prob, seed_mask_anchor)
                        patch_prob = torch.minimum(patch_prob, anchor_mask)
                        hard_out = self._cluster_prob_to_hard_mask(
                            cluster_prob=patch_prob,
                            seed_mask=seed_mask_anchor,
                            support_mask=anchor_mask,
                        )
                        patch_hard_mask = hard_out["cluster_hard_mask"]
                        patch_expand_mask = hard_out["cluster_expand_mask"]
                        patch_expand_count = hard_out["cluster_expand_count"]
                        support_for_refit = patch_hard_mask.float()
                        seed_for_refit = seed_mask_anchor
                        gain_prior = gain_prev

                        # Preserve existing training/diagnostic plumbing by aliasing patch
                        # outputs onto the legacy cluster_* fields.
                        cluster_logit = patch_logit
                        cluster_prob = patch_prob
                        cluster_hard_mask = patch_hard_mask
                        cluster_expand_mask = patch_expand_mask
                        cluster_expand_count = patch_expand_count
            else:
                mix_gain = torch.sigmoid(self.proposal_gain_mix_raw[t])
                gain_prior = mix_gain * prior_gain + (1.0 - mix_gain) * gain_prev
            gain_damp = torch.sigmoid(self.gain_damp_raw[t])
            refit = self.atom_bank.active_set_refit(
                y_flat=inp_y,
                x_total_flat=x_total,
                support_score=support_for_refit,
                gain_prior_flat=gain_prior,
                sigma_eff=sigma_eff,
                fixed_support_mask=support_for_refit if self.use_hybrid_support_init else None,
                fixed_seed_mask=seed_for_refit if self.use_hybrid_support_init else None,
                max_active_atoms=self.max_active_atoms,
                lambda_ls=lambda_ls_t,
                beta_gain=gain_damp,
                lmmse_side_scale=side_reg_t,
            )
            gain_refit = refit["gain_flat"]
            if self.use_hybrid_support_init and self.receiver_variant == "baseline":
                support_mask = refit["hard_mask"]
            else:
                support_mask = refit["st_mask"]
            if (not self.use_hybrid_support_init) and teacher_support_t is not None and teacher_force > 0.0:
                support_mask = (1.0 - teacher_force) * support_mask + teacher_force * teacher_support_t
            gain_refit_raw = gain_refit
            h_refit_flat = self.atom_bank.reconstruct(gain_refit_raw, support_weight=support_mask)

            if self.receiver_variant == "pnp_prior" and self.pnp_denoiser is not None:
                feat_pnp = self._build_pnp_features(
                    gain_refit=gain_refit_raw,
                    support_used=support_mask,
                    support_seed=refit["seed_mask"],
                    prior_seed_prob=seed_prob,
                    prior_support_prob=support_prob_atom,
                    sigma_eff=sigma_eff,
                    residual_energy=res_energy_prev,
                )
                pnp_out = self.pnp_denoiser(feat_pnp)
                raw_delta = pnp_out["delta_gain_flat"]
                ctrl_feat = self._build_pnp_mix_features(
                    t=t,
                    sigma_eff=sigma_eff,
                    residual_energy=res_energy_prev,
                    v_prev=v_prev,
                    support_used=support_mask,
                )
                support_mask_2q = torch.cat([support_mask, support_mask], dim=-1)
                gain_abs = _flat_gain_abs(gain_refit_raw, q)
                gain_scale_2q = torch.cat([gain_abs, gain_abs], dim=-1).float()
                base_mix_logit = self.pnp_mix_raw[t].reshape(1, 1).float().to(gain_refit_raw.device)
                ctrl_logit = self.pnp_mix_controller(ctrl_feat)
                iter_frac = ctrl_feat[:, 0:1]
                sigma_feat = ctrl_feat[:, 1:2]
                res_feat = ctrl_feat[:, 2:3]
                iter_bias = 1.25 * iter_frac
                high_snr_bias = 0.85 * torch.relu(-sigma_feat - 0.10)
                low_res_bias = 0.65 * torch.relu(-res_feat - 0.10)
                gated_logit = base_mix_logit + ctrl_logit - iter_bias - high_snr_bias - low_res_bias
                pnp_lambda = self.pnp_lambda_max * torch.sigmoid(gated_logit)
                pnp_mix = pnp_lambda
                pnp_delta = torch.tanh(raw_delta) * (gain_scale_2q + 1e-4)
                pnp_delta = pnp_delta * support_mask_2q
                gain_pnp = gain_refit_raw + pnp_lambda * pnp_delta
                pnp_identity_gap = (
                    (gain_pnp - gain_refit_raw).float().norm(dim=-1) /
                    gain_refit_raw.float().norm(dim=-1).clamp_min(1e-6)
                )
                h_pnp_flat = self.atom_bank.reconstruct(gain_pnp, support_weight=support_mask)
                gain_model = gain_pnp
                h_model = h_pnp_flat
            else:
                gain_model = gain_refit_raw
                h_model = h_refit_flat
                gain_pnp = None
                h_pnp_flat = None

            if (not self.use_hybrid_support_init) and teacher_gain_t is not None and teacher_force > 0.0:
                gain_prev = (1.0 - teacher_force) * gain_model + teacher_force * teacher_gain_t
                h_flat = self.atom_bank.reconstruct(gain_prev, support_weight=support_mask)
            else:
                gain_prev = gain_model
                h_flat = h_model
            if mu_prev is None:
                x_hat, v_x, llr = detector([h_flat, inp_y, inp_xp, sigma_eff])
            else:
                mu_init = mu_prev
                v_init = v_prev
                if teacher_mu_prev is not None and teacher_force > 0.0:
                    mu_init = (1.0 - teacher_force) * mu_prev + teacher_force * teacher_mu_prev
                if teacher_var_prev is not None and teacher_force > 0.0:
                    v_init = (1.0 - teacher_force) * v_prev + teacher_force * teacher_var_prev
                x_hat, v_x, llr = detector(
                    [h_flat, inp_y, inp_xp, sigma_eff, mu_init, v_init]
                )
            detection_raw = x_hat
            v_x_raw = v_x
            if self.uncertainty_variant == "vx_recal_v1":
                uncert_scale = torch.exp(self.uncert_scale_raw[t]).reshape(1, 1).float().to(v_x.device)
                v_x = v_x_raw * uncert_scale
            else:
                uncert_scale = torch.ones(1, 1, dtype=torch.float32, device=v_x.device)
            v_x = v_x.clamp_min(1e-6)
            refined_vx = v_x
            if self.detector_prior_variant in {"pnp_sd_v1", "pnp_sd_v2", "distill_sd_v1"} and self.detector_prior_refiner is not None:
                x_total_hat_raw = inp_xp + embed_data_block(detection_raw, self.n_total, self.data_pos)
                y_hat_raw = self.atom_bank.block_matvec(h_flat, x_total_hat_raw)
                residual_raw = inp_y - y_hat_raw
                residual_data = extract_data_block(residual_raw, self.data_pos)
                det_feat = self._build_detector_prior_features(
                    x_hat=detection_raw,
                    v_x=v_x,
                    llr=llr,
                    residual_data=residual_data,
                    t=t,
                    sigma_eff=sigma_eff,
                )
                det_out = self.detector_prior_refiner(det_feat)
                n_d = self.n_data
                delta_x_r = det_out["delta_x"][:, 0, :].float()
                delta_x_i = det_out["delta_x"][:, 1, :].float()
                delta_x_flat = torch.cat([delta_x_r, delta_x_i], dim=-1)
                if self.detector_prior_variant == "distill_sd_v1":
                    gamma_iter = self.detector_prior_teacher_gamma_schedule[min(
                        t, int(self.detector_prior_teacher_gamma_schedule.numel()) - 1
                    )].reshape(1, 1).float().to(v_x.device)
                    gamma_state = torch.ones_like(gamma_iter)
                else:
                    gamma_iter = torch.sigmoid(
                        self.detector_prior_gamma_raw[t].reshape(1, 1).float().to(v_x.device)
                    )
                    if self.detector_prior_variant == "pnp_sd_v2" and self.detector_prior_gamma_controller is not None:
                        gamma_feat = self._build_detector_prior_gamma_features(
                            t=t,
                            v_x=v_x,
                            llr=llr,
                            residual_energy=residual_raw[:, :self.n_total].float().square().mean(dim=-1, keepdim=False)
                            + residual_raw[:, self.n_total:].float().square().mean(dim=-1, keepdim=False),
                        )
                        gamma_state_logit = self.detector_prior_gamma_controller(gamma_feat)
                        iter_frac = gamma_feat[:, 0:1]
                        res_feat = gamma_feat[:, 2:3]
                        conf_feat = gamma_feat[:, 3:4]
                        late_bias = 1.25 * iter_frac
                        conf_bias = 0.90 * torch.relu(conf_feat + 0.10)
                        low_res_bias = 0.80 * torch.relu(-res_feat - 0.10)
                        gamma_state = torch.sigmoid(gamma_state_logit - late_bias - conf_bias - low_res_bias)
                    else:
                        gamma_state = torch.ones_like(gamma_iter)
                gamma_t = gamma_iter if self.detector_prior_variant == "distill_sd_v1" else (
                    self.detector_prior_gamma_max * gamma_iter * gamma_state
                )
                scale_x = torch.sqrt(v_x.clamp_min(1e-6))
                detector_prior_delta = gamma_t * torch.tanh(delta_x_flat) * scale_x
                # Negate delta for distill_sd_v1_neg variant (learnability probe showed direction inversion issue)
                if self.detector_prior_variant == "distill_sd_v1_neg":
                    detector_prior_delta = -detector_prior_delta
                x_hat = detection_raw + detector_prior_delta
                if self.detector_prior_variant == "distill_sd_v1":
                    refined_vx = v_x
                else:
                    delta_v = det_out["delta_v"][:, 0, :].float()
                    delta_v = torch.clamp(delta_v, min=-0.75, max=0.75)
                    if v_x.shape[1] == 2 * n_d:
                        v_sym = 0.5 * (v_x[:, :n_d] + v_x[:, n_d:])
                    else:
                        v_sym = v_x
                    v_scale = torch.exp(torch.clamp(gamma_t * delta_v, min=-0.75, max=0.75))
                    v_sym_refined = (v_sym * v_scale).clamp_min(1e-6)
                    refined_vx = torch.cat([v_sym_refined, v_sym_refined], dim=-1)
                detector_prior_gamma = gamma_t
                detector_prior_gamma_eff = gamma_t
                detector_prior_gamma_iter = gamma_iter
                detector_prior_gamma_state = gamma_state
                detector_prior_identity_gap = (
                    (x_hat - detection_raw).float().norm(dim=-1) /
                    detection_raw.float().norm(dim=-1).clamp_min(1e-6)
                )
            elif self.detector_prior_variant == "oracle_probe":
                stage_mu_t = _stage_tensor(teacher_mu_iter, t)
                alpha = float(self.oracle_alpha)
                if stage_mu_t is None or self.oracle_probe_mode == "identity" or alpha <= 0.0:
                    detector_prior_delta = torch.zeros_like(detection_raw)
                    detector_prior_gamma = torch.zeros_like(detection_raw)
                    detector_prior_gamma_eff = detector_prior_gamma
                    detector_prior_gamma_iter = detector_prior_gamma
                    detector_prior_gamma_state = detector_prior_gamma
                    detector_prior_identity_gap = torch.zeros(
                        detection_raw.shape[0], dtype=torch.float32, device=detection_raw.device
                    )
                    x_hat = detection_raw
                    refined_vx = v_x
                else:
                    teacher_mu_now = stage_mu_t.float()
                    gamma_iter = torch.full_like(detection_raw, alpha)
                    if self.oracle_probe_mode == "mu_blend":
                        gamma_state = torch.ones_like(detection_raw)
                    else:
                        gamma_state = (llr.float().abs() < self.oracle_conf_threshold).float()
                    gamma_eff = gamma_iter * gamma_state
                    detector_prior_delta = gamma_eff * (teacher_mu_now - detection_raw)
                    x_hat = detection_raw + detector_prior_delta
                    refined_vx = v_x
                    detector_prior_gamma = gamma_eff
                    detector_prior_gamma_eff = gamma_eff
                    detector_prior_gamma_iter = gamma_iter
                    detector_prior_gamma_state = gamma_state
                    detector_prior_identity_gap = (
                        (x_hat - detection_raw).float().norm(dim=-1) /
                        detection_raw.float().norm(dim=-1).clamp_min(1e-6)
                    )
            else:
                detector_prior_delta = torch.zeros_like(detection_raw)
                detector_prior_gamma = torch.zeros(1, 1, dtype=torch.float32, device=detection_raw.device)
                detector_prior_gamma_eff = detector_prior_gamma
                detector_prior_gamma_iter = detector_prior_gamma
                detector_prior_gamma_state = detector_prior_gamma
                detector_prior_identity_gap = torch.zeros(detection_raw.shape[0], dtype=torch.float32, device=detection_raw.device)

            x_total_hat = inp_xp + embed_data_block(x_hat, self.n_total, self.data_pos)
            y_hat = self.atom_bank.block_matvec(h_flat, x_total_hat)
            res_c = block_to_complex(inp_y - y_hat)
            sigma_new = res_c.abs().square().mean(dim=-1, keepdim=True)
            sigma_eff = sigma_mix_t * sigma_eff + (1.0 - sigma_mix_t) * sigma_new
            res_energy_prev = res_c.abs().square().mean(dim=-1)

            history.append({
                "detection": x_hat,
                "detection_raw": detection_raw,
                "v_x": refined_vx,
                "v_x_raw": v_x_raw,
                "v_x_cal": v_x,
                "v_x_refined": refined_vx,
                "uncert_scale": uncert_scale,
                "bits": llr,
                "seed_logit": seed_logit,
                "center_logit": prior_center_logit,
                "support_logit": support_logit,
                "support_seed_prob": seed_prob,
                "support": support_prob,
                "support_seed": refit["seed_mask"],
                "support_active": refit["hard_mask"],
                "support_used": support_mask,
                "support_anchor": support_anchor,
                "cluster_logit": cluster_logit,
                "cluster_prob": cluster_prob,
                "cluster_hard_mask": cluster_hard_mask,
                "cluster_expand_mask": cluster_expand_mask,
                "cluster_expand_count": cluster_expand_count,
                "patch_logit": patch_logit,
                "patch_prob": patch_prob,
                "patch_hard_mask": patch_hard_mask,
                "patch_expand_mask": patch_expand_mask,
                "patch_expand_count": patch_expand_count,
                "gain_refit_raw": gain_refit_raw,
                "gain_pnp": gain_pnp,
                "gain_flat": gain_prev,
                "gain_refit": gain_refit,
                "gain_delta": gain_delta,
                "h_refit_flat": h_refit_flat,
                "h_pnp_flat": h_pnp_flat,
                "pnp_delta": pnp_delta,
                "pnp_mix": pnp_mix,
                "pnp_lambda": pnp_lambda,
                "pnp_identity_gap": pnp_identity_gap,
                "detector_prior_delta": detector_prior_delta,
                "detector_prior_gamma": detector_prior_gamma,
                "detector_prior_gamma_eff": detector_prior_gamma_eff,
                "detector_prior_gamma_iter": detector_prior_gamma_iter,
                "detector_prior_gamma_state": detector_prior_gamma_state,
                "detector_prior_identity_gap": detector_prior_identity_gap,
                "detector_prior_target_gamma": detector_prior_gamma_iter,
                "H_flat": h_flat,
                "y_hat": y_hat,
                "sigma_eff": sigma_eff,
                "sigma_ls": refit["sigma_ls"],
                "lambda_ls": lambda_ls_t,
                "sigma_mix": sigma_mix_t,
                "sic_beta": sic_beta_t,
                "side_reg": side_reg_t,
            })
            mu_prev = x_hat
            v_prev = refined_vx
            llr_prev = llr

        final = history[-1]
        return {
            "channel_init": prop["channel_init"],
            "prior_center_logit": prior_center_logit,
            "prior_seed_logit": prior_seed_logit,
            "prior_support_logit": prior_support_logit,
            "prior_gain_flat": prior_gain,
            "final_detection": final["detection"],
            "final_vx": final["v_x"],
            "final_bits": final["bits"],
            "final_support": final["support_used"],
            "final_support_anchor": final.get("support_anchor"),
            "final_cluster_prob": final.get("cluster_prob"),
            "final_cluster_hard_mask": final.get("cluster_hard_mask"),
            "final_cluster_expand_mask": final.get("cluster_expand_mask"),
            "final_cluster_expand_count": final.get("cluster_expand_count"),
            "final_patch_prob": final.get("patch_prob"),
            "final_patch_hard_mask": final.get("patch_hard_mask"),
            "final_patch_expand_mask": final.get("patch_expand_mask"),
            "final_patch_expand_count": final.get("patch_expand_count"),
            "final_gain_refit_raw": final.get("gain_refit_raw"),
            "final_gain_pnp": final.get("gain_pnp"),
            "final_h_refit_flat": final.get("h_refit_flat"),
            "final_h_pnp_flat": final.get("h_pnp_flat"),
            "final_pnp_delta": final.get("pnp_delta"),
            "final_pnp_mix": final.get("pnp_mix"),
            "final_pnp_lambda": final.get("pnp_lambda"),
            "final_pnp_identity_gap": final.get("pnp_identity_gap"),
            "final_detector_prior_delta": final.get("detector_prior_delta"),
            "final_detector_prior_gamma": final.get("detector_prior_gamma"),
            "final_detector_prior_gamma_eff": final.get("detector_prior_gamma_eff"),
            "final_detector_prior_gamma_iter": final.get("detector_prior_gamma_iter"),
            "final_detector_prior_gamma_state": final.get("detector_prior_gamma_state"),
            "final_detector_prior_identity_gap": final.get("detector_prior_identity_gap"),
            "final_gain_flat": final["gain_flat"],
            "final_H_flat": final["H_flat"],
            "k_span": self.atom_bank.k_span,
            "num_delays": self.atom_bank.l_max + 1,
            "receiver_variant": self.receiver_variant,
            "uncertainty_variant": self.uncertainty_variant,
            "detector_prior_variant": self.detector_prior_variant,
            "disable_gain_delta": self.disable_gain_delta,
            "support_consumption": self.support_consumption,
            "hard_mask_threshold": self.hard_mask_threshold,
            "hard_mask_topk": self.hard_mask_topk,
            "pnp_lambda_max": self.pnp_lambda_max,
            "detector_prior_gamma_max": self.detector_prior_gamma_max,
            "detector_prior_teacher_gamma_schedule": self.detector_prior_teacher_gamma_schedule.detach().cpu(),
            "oracle_probe_mode": self.oracle_probe_mode,
            "oracle_alpha": self.oracle_alpha,
            "oracle_conf_threshold": self.oracle_conf_threshold,
            "history": history,
        }


def derive_sparse_teacher_targets(atom_bank: SparseAtomBank,
                                  y_received: torch.Tensor,
                                  x_pilot_frames: torch.Tensor,
                                  mu_teacher: torch.Tensor,
                                  data_positions: torch.Tensor,
                                  n_total: int) -> SparseTargetBatch:
    mu_teacher_full = embed_data_block(mu_teacher, n_total, data_positions)
    x_total_teacher = x_pilot_frames + mu_teacher_full
    return atom_bank.project_teacher_support(y_received, x_total_teacher)


def compute_joint_unrolled_loss(
        out: dict[str, torch.Tensor],
        y_received: torch.Tensor,
        bits_true: torch.Tensor,
        x_data_true: torch.Tensor,
        support_teacher: torch.Tensor | None = None,
        gain_teacher: torch.Tensor | None = None,
        llr_teacher: torch.Tensor | None = None,
        mu_teacher: torch.Tensor | None = None,
        support_teacher_iter: torch.Tensor | None = None,
        seed_teacher_iter: torch.Tensor | None = None,
        gain_teacher_iter: torch.Tensor | None = None,
        cluster_mask_teacher_iter: torch.Tensor | None = None,
        leakage_teacher_iter: torch.Tensor | None = None,
        llr_teacher_iter: torch.Tensor | None = None,
        mu_teacher_iter: torch.Tensor | None = None,
        var_teacher_iter: torch.Tensor | None = None,
        snr_db: torch.Tensor | None = None,
        lambda_bits: float = 1.0,
        lambda_kd: float = 0.5,
        lambda_seed: float = 0.2,
        lambda_support: float = 0.2,
        lambda_cluster_mask: float = 0.0,
        lambda_leakage_profile: float = 0.0,
        lambda_pnp_delta: float = 0.0,
        lambda_pnp_identity: float = 0.0,
        lambda_det_prior_delta: float = 0.0,
        lambda_det_prior_sym: float = 0.0,
        lambda_det_prior_vx: float = 0.0,
        lambda_det_prior_identity: float = 0.0,
        lambda_vx: float = 0.0,
        lambda_gain: float = 0.2,
        lambda_obs: float = 0.05,
        lambda_sym: float = 0.1):
    history = out["history"]
    if not history:
        raise ValueError("history cannot be empty")
    k_span = int(out.get("k_span", 1))
    num_delays = int(out.get("num_delays", 1))

    stage_w = torch.linspace(
        0.5, 1.0, steps=len(history), device=bits_true.device, dtype=bits_true.dtype
    )
    stage_w = stage_w / stage_w.sum()

    loss_bits = bits_true.new_tensor(0.0)
    loss_kd = bits_true.new_tensor(0.0)
    loss_seed = bits_true.new_tensor(0.0)
    loss_support = bits_true.new_tensor(0.0)
    loss_cluster_mask = bits_true.new_tensor(0.0)
    loss_leakage_profile = bits_true.new_tensor(0.0)
    loss_pnp_delta = bits_true.new_tensor(0.0)
    loss_pnp_identity = bits_true.new_tensor(0.0)
    loss_det_prior_delta = bits_true.new_tensor(0.0)
    loss_det_prior_sym = bits_true.new_tensor(0.0)
    loss_det_prior_vx = bits_true.new_tensor(0.0)
    loss_det_prior_identity = bits_true.new_tensor(0.0)
    loss_vx = bits_true.new_tensor(0.0)
    loss_gain = bits_true.new_tensor(0.0)
    loss_obs = bits_true.new_tensor(0.0)
    loss_sym = bits_true.new_tensor(0.0)
    seed_recall = bits_true.new_tensor(0.0)
    support_recall = bits_true.new_tensor(0.0)
    support_precision = bits_true.new_tensor(0.0)
    cluster_recall = bits_true.new_tensor(0.0)
    cluster_precision = bits_true.new_tensor(0.0)
    strat_lambda = bits_true.new_tensor(0.0)
    strat_sigma_mix = bits_true.new_tensor(0.0)
    strat_sic_beta = bits_true.new_tensor(0.0)
    strat_side = bits_true.new_tensor(0.0)
    pnp_mix_mean = bits_true.new_tensor(0.0)
    pnp_lambda_mean = bits_true.new_tensor(0.0)
    pnp_delta_norm = bits_true.new_tensor(0.0)
    pnp_identity_gap_mean = bits_true.new_tensor(0.0)
    det_prior_delta_norm = bits_true.new_tensor(0.0)
    det_prior_gamma_mean = bits_true.new_tensor(0.0)
    vx_mean = bits_true.new_tensor(0.0)
    vx_recal_mean = bits_true.new_tensor(0.0)
    uncert_scale_mean = bits_true.new_tensor(0.0)
    bits_true = bits_true.float()
    x_data_true = x_data_true.float()
    y_received = y_received.float()

    for stage_idx, (weight, stage) in enumerate(zip(stage_w, history)):
        stage_support_t = _stage_tensor(support_teacher_iter, stage_idx)
        stage_seed_t = _stage_tensor(seed_teacher_iter, stage_idx)
        stage_gain_t = _stage_tensor(gain_teacher_iter, stage_idx)
        stage_cluster_t = _stage_tensor(cluster_mask_teacher_iter, stage_idx)
        stage_leakage_t = _stage_tensor(leakage_teacher_iter, stage_idx)
        stage_llr_t = _stage_tensor(llr_teacher_iter, stage_idx)
        stage_mu_t = _stage_tensor(mu_teacher_iter, stage_idx)
        stage_var_t = _stage_tensor(var_teacher_iter, stage_idx)
        if stage_support_t is None:
            stage_support_t = support_teacher
        if stage_gain_t is None:
            stage_gain_t = gain_teacher
        if stage_cluster_t is None:
            stage_cluster_t = stage_support_t
        if stage_llr_t is None:
            stage_llr_t = llr_teacher
        if stage_mu_t is None:
            stage_mu_t = mu_teacher
        if stage_support_t is not None:
            stage_support_t = stage_support_t.float()
        if stage_gain_t is not None:
            stage_gain_t = stage_gain_t.float()
        if stage_cluster_t is not None:
            stage_cluster_t = stage_cluster_t.float()
        if stage_leakage_t is not None:
            stage_leakage_t = stage_leakage_t.float()
        if stage_llr_t is not None:
            stage_llr_t = stage_llr_t.float()
        if stage_mu_t is not None:
            stage_mu_t = stage_mu_t.float()
        if stage_var_t is not None:
            stage_var_t = stage_var_t.float()

        teacher_prob = None
        if stage_llr_t is not None:
            teacher_prob = torch.sigmoid(stage_llr_t).detach()

        gain_weight = None
        if stage_support_t is not None:
            gain_weight = torch.cat([stage_support_t, stage_support_t], dim=-1).detach()
        if stage_seed_t is None:
            stage_seed_t = _derive_seed_teacher(
                stage_support_t=stage_support_t,
                stage_gain_t=stage_gain_t,
                num_delays=num_delays,
                k_span=k_span,
            )
        delay_active_t = None
        center_idx_t = None
        center_mask_t = None
        if stage_seed_t is not None:
            delay_active_t, center_idx_t, center_mask_t = _seed_targets_to_delay_center(
                stage_seed_t.float(), num_delays=num_delays, k_span=k_span
            )

        target_symbol = stage_mu_t if stage_mu_t is not None else x_data_true
        stage_bits = stage["bits"].float()
        stage_det = stage["detection"].float()
        stage_seed_logit = stage.get("seed_logit", stage["support_logit"]).float()
        stage_center_logit = stage.get("center_logit", stage_seed_logit).float()
        stage_support_logit = stage["support_logit"].float()
        stage_gain_flat = stage["gain_flat"].float()
        stage_gain_refit_raw = stage.get("gain_refit_raw")
        stage_pnp_delta = stage.get("pnp_delta")
        stage_pnp_lambda = stage.get("pnp_lambda")
        stage_pnp_identity_gap = stage.get("pnp_identity_gap")
        stage_support_used = stage.get("support_used")
        stage_vx_raw = stage.get("v_x_raw", stage.get("v_x"))
        stage_vx_cal = stage.get("v_x_cal", stage.get("v_x"))
        stage_vx_refined = stage.get("v_x_refined", stage.get("v_x"))
        stage_uncert_scale = stage.get("uncert_scale")
        stage_detection_raw = stage.get("detection_raw")
        stage_det_prior_delta = stage.get("detector_prior_delta")
        stage_det_prior_gamma = stage.get("detector_prior_gamma")
        stage_det_prior_target_gamma = stage.get("detector_prior_target_gamma")
        stage_y_hat = stage["y_hat"].float()
        stage_cluster_logit = stage.get("cluster_logit")
        stage_cluster_prob = stage.get("cluster_prob")
        stage_support_anchor = stage.get("support_anchor")
        if stage_cluster_logit is not None:
            stage_cluster_logit = stage_cluster_logit.float()
        if stage_cluster_prob is not None:
            stage_cluster_prob = stage_cluster_prob.float()
        if stage_support_anchor is not None:
            stage_support_anchor = stage_support_anchor.float()
        if stage_gain_refit_raw is not None:
            stage_gain_refit_raw = stage_gain_refit_raw.float()
        if stage_pnp_delta is not None:
            stage_pnp_delta = stage_pnp_delta.float()
        if stage_support_used is not None:
            stage_support_used = stage_support_used.float()
        if stage_vx_raw is not None:
            stage_vx_raw = stage_vx_raw.float()
        if stage_vx_cal is not None:
            stage_vx_cal = stage_vx_cal.float()
        if stage_uncert_scale is not None:
            stage_uncert_scale = stage_uncert_scale.float()
        if stage_det_prior_target_gamma is not None:
            stage_det_prior_target_gamma = stage_det_prior_target_gamma.float()
        if stage_pnp_lambda is not None:
            stage_pnp_lambda = stage_pnp_lambda.float()
        if stage_pnp_identity_gap is not None:
            stage_pnp_identity_gap = stage_pnp_identity_gap.float()
        loss_bits = loss_bits + weight * F.binary_cross_entropy_with_logits(
            stage_bits, bits_true
        )
        if teacher_prob is not None:
            loss_kd = loss_kd + weight * F.binary_cross_entropy_with_logits(
                stage_bits, teacher_prob
            )
        if stage_seed_t is not None and center_mask_t is not None:
            stage_seed_t = stage_seed_t.float()
            center_logits = stage_center_logit.reshape(stage_center_logit.shape[0], num_delays, k_span)
            if bool(center_mask_t.any().item()):
                center_loss = F.cross_entropy(
                    center_logits[center_mask_t],
                    center_idx_t[center_mask_t],
                )
                loss_seed = loss_seed + weight * center_loss
            seed_recall = seed_recall + weight * _seed_topk_recall(stage_seed_logit, stage_seed_t)
        if delay_active_t is not None:
            loss_support = loss_support + weight * _weighted_focal_bce_with_logits(
                stage_support_logit, delay_active_t
            )
            rec, prec = _binary_recall_precision_from_logits(
                stage_support_logit, delay_active_t
            )
            support_recall = support_recall + weight * rec
            support_precision = support_precision + weight * prec
        if stage_cluster_logit is not None and stage_cluster_t is not None:
            cluster_target = stage_cluster_t
            cluster_mask = stage_support_anchor
            loss_cluster_mask = loss_cluster_mask + weight * _masked_weighted_focal_bce_with_logits(
                stage_cluster_logit,
                cluster_target,
                mask=cluster_mask,
            )
            rec, prec = _binary_recall_precision_from_logits_masked(
                stage_cluster_logit,
                cluster_target,
                mask=cluster_mask,
            )
            cluster_recall = cluster_recall + weight * rec
            cluster_precision = cluster_precision + weight * prec
        if stage_cluster_prob is not None and stage_leakage_t is not None:
            pred_profile = _row_normalize_flat(stage_cluster_prob, num_delays=num_delays, k_span=k_span)
            target_profile = _row_normalize_flat(stage_leakage_t, num_delays=num_delays, k_span=k_span)
            row_active = (
                target_profile.reshape(target_profile.shape[0], num_delays, k_span)
                .sum(dim=-1, keepdim=True) > 0.0
            ).float().expand(-1, -1, k_span).reshape(target_profile.shape[0], -1)
            if stage_support_anchor is not None:
                row_active = row_active * (
                    stage_support_anchor.reshape(stage_support_anchor.shape[0], num_delays, k_span)
                    .amax(dim=-1, keepdim=True).float()
                    .expand(-1, -1, k_span)
                    .reshape(stage_support_anchor.shape[0], -1)
                )
            denom = row_active.sum().clamp_min(1.0)
            leakage_err = F.smooth_l1_loss(
                pred_profile, target_profile, reduction="none"
            )
            loss_leakage_profile = loss_leakage_profile + weight * (
                (leakage_err * row_active).sum() / denom
            )
        if stage_gain_t is not None:
            gain_err = F.smooth_l1_loss(
                stage_gain_flat, stage_gain_t, reduction="none"
            )
            if gain_weight is not None:
                gain_err = gain_err * (0.25 + gain_weight)
            loss_gain = loss_gain + weight * gain_err.mean()
        if stage_gain_t is not None and stage_gain_refit_raw is not None and stage_pnp_delta is not None:
            pnp_target = stage_gain_t - stage_gain_refit_raw
            if stage_support_used is not None:
                pnp_mask = torch.cat([stage_support_used, stage_support_used], dim=-1).detach()
            else:
                pnp_mask = torch.ones_like(stage_pnp_delta)
            denom = pnp_mask.sum().clamp_min(1.0)
            pnp_err = F.smooth_l1_loss(stage_pnp_delta, pnp_target, reduction="none")
            loss_pnp_delta = loss_pnp_delta + weight * ((pnp_err * pnp_mask).sum() / denom)
            pnp_delta_norm = pnp_delta_norm + weight * (
                (stage_pnp_delta.abs() * pnp_mask).sum() / denom
            )
        if stage_gain_refit_raw is not None and stage_support_used is not None:
            gain_delta_now = stage_gain_flat - stage_gain_refit_raw
            high_snr_mask = None
            if snr_db is not None:
                high_snr_mask = (snr_db.reshape(-1, 1).float() >= 20.0).float()
            late_weight = 1.0 if stage_idx >= max(len(history) - 2, 0) else 0.0
            if high_snr_mask is not None and late_weight > 0.0:
                ident_mask = torch.cat([stage_support_used, stage_support_used], dim=-1) * high_snr_mask
                ident_denom = ident_mask.sum().clamp_min(1.0)
                ident_err = F.smooth_l1_loss(
                    gain_delta_now,
                    torch.zeros_like(gain_delta_now),
                    reduction="none",
                )
                loss_pnp_identity = loss_pnp_identity + weight * late_weight * (
                    (ident_err * ident_mask).sum() / ident_denom
                )
        if stage_var_t is not None and stage_vx_cal is not None:
            vx_err = F.smooth_l1_loss(
                torch.log(stage_vx_cal.clamp_min(1e-6)),
                torch.log(stage_var_t.clamp_min(1e-6)),
                reduction="mean",
            )
            loss_vx = loss_vx + weight * vx_err
        if stage_detection_raw is not None:
            stage_detection_raw = stage_detection_raw.float()
        if stage_det_prior_delta is not None:
            stage_det_prior_delta = stage_det_prior_delta.float()
            det_prior_delta_norm = det_prior_delta_norm + weight * stage_det_prior_delta.abs().mean()
        if stage_det_prior_gamma is not None:
            stage_det_prior_gamma = stage_det_prior_gamma.float()
            det_prior_gamma_mean = det_prior_gamma_mean + weight * stage_det_prior_gamma.mean()
        if stage_mu_t is not None and stage_detection_raw is not None and stage_det_prior_delta is not None:
            if stage_vx_cal is not None:
                delta_scale = torch.sqrt(stage_vx_cal.detach().clamp_min(1e-6))
            elif stage_vx_refined is not None:
                delta_scale = torch.sqrt(stage_vx_refined.detach().clamp_min(1e-6))
            elif stage_vx_raw is not None:
                delta_scale = torch.sqrt(stage_vx_raw.detach().clamp_min(1e-6))
            else:
                delta_scale = torch.ones_like(stage_det_prior_delta)
            if stage_det_prior_target_gamma is not None:
                delta_gamma = stage_det_prior_target_gamma
            else:
                delta_gamma = torch.ones_like(stage_det_prior_delta)
            delta_target_raw = delta_gamma * (stage_mu_t.detach() - stage_detection_raw.detach())
            delta_target = torch.clamp(
                delta_target_raw / delta_scale.clamp_min(1e-6),
                min=-1.0,
                max=1.0,
            ) * delta_scale
            # distill_sd_v2: iter-0-only cosine loss (learnability probe showed later iters not learnable)
            if stage_idx == 0:
                # Normalize both prediction and target for cosine loss
                pred_norm = stage_det_prior_delta / (stage_det_prior_delta.norm(dim=-1, keepdim=True) + 1e-8)
                tgt_norm = delta_target / (delta_target.norm(dim=-1, keepdim=True) + 1e-8)
                cosine = (pred_norm * tgt_norm).sum(dim=-1).mean()
                loss_det_prior_delta = loss_det_prior_delta + weight * (1.0 - cosine)
            # For later iterations, no distill loss (targets not learnable per probe)
        if stage_mu_t is not None and stage_detection_raw is not None:
            loss_det_prior_sym = loss_det_prior_sym + weight * F.mse_loss(stage_det, stage_mu_t)
            if stage_idx >= max(len(history) - 2, 0) and snr_db is not None:
                high_snr_mask_sym = (snr_db.reshape(-1, 1).float() >= 20.0).float()
                ident_err_sym = F.smooth_l1_loss(
                    stage_det,
                    stage_detection_raw,
                    reduction="none",
                )
                denom_sym = high_snr_mask_sym.expand_as(ident_err_sym).sum().clamp_min(1.0)
                loss_det_prior_identity = loss_det_prior_identity + weight * (
                    (ident_err_sym * high_snr_mask_sym.expand_as(ident_err_sym)).sum() / denom_sym
                )
        if stage_var_t is not None and stage_vx_refined is not None:
            stage_vx_refined = stage_vx_refined.float()
            loss_det_prior_vx = loss_det_prior_vx + weight * F.smooth_l1_loss(
                torch.log(stage_vx_refined.clamp_min(1e-6)),
                torch.log(stage_var_t.clamp_min(1e-6)),
                reduction="mean",
            )
        loss_obs = loss_obs + weight * F.mse_loss(stage_y_hat, y_received)
        loss_sym = loss_sym + weight * F.mse_loss(stage_det, target_symbol)
        if "lambda_ls" in stage:
            strat_lambda = strat_lambda + weight * stage["lambda_ls"].float().mean()
        if "sigma_mix" in stage:
            strat_sigma_mix = strat_sigma_mix + weight * stage["sigma_mix"].float().mean()
        if "sic_beta" in stage:
            strat_sic_beta = strat_sic_beta + weight * stage["sic_beta"].float().mean()
        if "side_reg" in stage:
            strat_side = strat_side + weight * stage["side_reg"].float().mean()
        elif "lmmse_side" in stage:
            strat_side = strat_side + weight * stage["lmmse_side"].float().mean()
        if "pnp_mix" in stage and stage["pnp_mix"] is not None:
            pnp_mix_mean = pnp_mix_mean + weight * stage["pnp_mix"].float().mean()
        if stage_pnp_lambda is not None:
            pnp_lambda_mean = pnp_lambda_mean + weight * stage_pnp_lambda.mean()
        if stage_pnp_identity_gap is not None:
            pnp_identity_gap_mean = pnp_identity_gap_mean + weight * stage_pnp_identity_gap.mean()
        if stage_vx_raw is not None:
            vx_mean = vx_mean + weight * stage_vx_raw.mean()
        if stage_vx_cal is not None:
            vx_recal_mean = vx_recal_mean + weight * stage_vx_cal.mean()
        if stage_uncert_scale is not None:
            uncert_scale_mean = uncert_scale_mean + weight * stage_uncert_scale.mean()

    total = (
        lambda_bits * loss_bits +
        lambda_kd * loss_kd +
        lambda_seed * loss_seed +
        lambda_support * loss_support +
        lambda_cluster_mask * loss_cluster_mask +
        lambda_leakage_profile * loss_leakage_profile +
        lambda_pnp_delta * loss_pnp_delta +
        lambda_pnp_identity * loss_pnp_identity +
        lambda_det_prior_delta * loss_det_prior_delta +
        lambda_det_prior_sym * loss_det_prior_sym +
        lambda_det_prior_vx * loss_det_prior_vx +
        lambda_det_prior_identity * loss_det_prior_identity +
        lambda_vx * loss_vx +
        lambda_gain * loss_gain +
        lambda_obs * loss_obs +
        lambda_sym * loss_sym
    )
    stats = {
        "loss": total.detach(),
        "bits": loss_bits.detach(),
        "kd": loss_kd.detach(),
        "seed": loss_seed.detach(),
        "seed_recall": seed_recall.detach(),
        "support": loss_support.detach(),
        "support_recall": support_recall.detach(),
        "support_precision": support_precision.detach(),
        "cluster_mask": loss_cluster_mask.detach(),
        "cluster_recall": cluster_recall.detach(),
        "cluster_precision": cluster_precision.detach(),
        "leakage_profile": loss_leakage_profile.detach(),
        "pnp_delta": loss_pnp_delta.detach(),
        "pnp_identity": loss_pnp_identity.detach(),
        "det_prior_delta": loss_det_prior_delta.detach(),
        "det_prior_sym": loss_det_prior_sym.detach(),
        "det_prior_vx": loss_det_prior_vx.detach(),
        "det_prior_identity": loss_det_prior_identity.detach(),
        "pnp_mix": pnp_mix_mean.detach(),
        "pnp_lambda": pnp_lambda_mean.detach(),
        "pnp_identity_gap": pnp_identity_gap_mean.detach(),
        "pnp_delta_norm": pnp_delta_norm.detach(),
        "det_prior_delta_norm": det_prior_delta_norm.detach(),
        "det_prior_gamma": det_prior_gamma_mean.detach(),
        "vx": loss_vx.detach(),
        "vx_mean": vx_mean.detach(),
        "vx_recal_mean": vx_recal_mean.detach(),
        "uncert_scale": uncert_scale_mean.detach(),
        "gain": loss_gain.detach(),
        "obs": loss_obs.detach(),
        "sym": loss_sym.detach(),
        "lambda_ls": strat_lambda.detach(),
        "sigma_mix": strat_sigma_mix.detach(),
        "sic_beta": strat_sic_beta.detach(),
        "side_reg": strat_side.detach(),
    }
    return total, stats


def build_joint_unrolled_model(
        input_dim: int,
        n_total: int,
        c1: float,
        c2: float,
        l_max_cap: int,
        k_max_cap: int,
        data_positions: np.ndarray | torch.Tensor,
        grid_l_max: int,
        grid_w: int,
        aux_dim: int = 4,
        num_outer_iters: int = 5,
        num_mp_layers: int = 6,
        max_active_atoms: int = 25,
        k_leak: int = 2,
        ce_backbone: CEBackbone | None = None,
        use_hybrid_support_init: bool = True,
        freeze_support_after_init: bool = True,
        receiver_variant: str = "baseline",
        uncertainty_variant: str = "baseline",
        detector_prior_variant: str = "baseline",
        disable_gain_delta: bool = False,
        support_consumption: str = "soft",
        hard_mask_threshold: float = 0.6,
        hard_mask_topk: int = 1,
        pnp_lambda_max: float = 0.25,
        detector_prior_gamma_max: float = 0.20,
        oracle_probe_mode: str = "identity",
        oracle_alpha: float = 0.0,
        oracle_conf_threshold: float = 1.5) -> JointSparseUnrolledReceiver:
    if ce_backbone is None:
        ce_backbone = CEBackbone(grid_l_max, grid_w, aux_dim=aux_dim)
    else:
        ce_backbone = copy.deepcopy(ce_backbone)

    atom_bank = SparseAtomBank(
        n_total=n_total,
        c1=c1,
        c2=c2,
        l_max=l_max_cap,
        k_max=k_max_cap,
        k_leak=k_leak,
    )
    proposal = SparseSupportProposal(
        ce_backbone=ce_backbone,
        grid_dim=2 * grid_l_max * grid_w,
        aux_dim=aux_dim,
        num_atoms=atom_bank.num_atoms,
        num_delays=atom_bank.l_max + 1,
    )
    return JointSparseUnrolledReceiver(
        proposal_net=proposal,
        atom_bank=atom_bank,
        n_total=n_total,
        data_positions=data_positions,
        num_outer_iters=num_outer_iters,
        num_mp_layers=num_mp_layers,
        max_active_atoms=max_active_atoms,
        use_hybrid_support_init=use_hybrid_support_init,
        freeze_support_after_init=freeze_support_after_init,
        receiver_variant=receiver_variant,
        uncertainty_variant=uncertainty_variant,
        detector_prior_variant=detector_prior_variant,
        disable_gain_delta=disable_gain_delta,
        support_consumption=support_consumption,
        hard_mask_threshold=hard_mask_threshold,
        hard_mask_topk=hard_mask_topk,
        pnp_lambda_max=pnp_lambda_max,
        detector_prior_gamma_max=detector_prior_gamma_max,
        oracle_probe_mode=oracle_probe_mode,
        oracle_alpha=oracle_alpha,
        oracle_conf_threshold=oracle_conf_threshold,
    )
