"""
afdm_joint_param.py

Stage-6 lightweight joint receiver:
  - OMP init + support expansion
  - fixed support across outer iterations
  - data-aided ridge refit
  - sparse MP detector
  - learn only lambda / alpha / beta per iteration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .afdm_joint_unrolled import (
    SparseAtomBank,
    SparseMPDetector,
    block_to_complex,
    complex_to_block,
    embed_data_block,
    extract_data_block,
    ber_from_detection,
)


VALID_PARAM_SETS = (
    "fixed",
    "lambda_only",
    "alpha_beta_only",
    "lambda_alpha_beta",
)


def _inv_softplus(value: float) -> float:
    value = float(max(value, 1e-8))
    return float(np.log(np.expm1(value)))


def _as_override_tensor(
    value: Any,
    ref: torch.Tensor,
    *,
    clamp_min: float | None = None,
    clamp_max: float | None = None,
) -> torch.Tensor:
    if torch.is_tensor(value):
        out = value.to(device=ref.device, dtype=ref.dtype)
    else:
        out = torch.as_tensor(value, device=ref.device, dtype=ref.dtype)
    if out.numel() == 1:
        out = out.reshape(1, 1).expand_as(ref)
    else:
        out = out.reshape_as(ref)
    if clamp_min is not None or clamp_max is not None:
        lo = clamp_min if clamp_min is not None else float("-inf")
        hi = clamp_max if clamp_max is not None else float("inf")
        out = out.clamp(min=lo, max=hi)
    return out


def _select_iter_override(value: Any, iter_idx: int) -> Any:
    if torch.is_tensor(value):
        if value.ndim == 0:
            return value
        if value.shape[0] <= iter_idx:
            raise IndexError(f"Override schedule length={value.shape[0]} < iter_idx={iter_idx + 1}")
        return value[iter_idx]
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return value.item()
        if value.shape[0] <= iter_idx:
            raise IndexError(f"Override schedule length={value.shape[0]} < iter_idx={iter_idx + 1}")
        return value[iter_idx]
    if isinstance(value, (list, tuple)):
        if len(value) <= iter_idx:
            raise IndexError(f"Override schedule length={len(value)} < iter_idx={iter_idx + 1}")
        return value[iter_idx]
    return value


def _expand_symbol_weight_to_block(weight_sym: torch.Tensor, n_data: int, ref: torch.Tensor) -> torch.Tensor:
    if weight_sym.shape[-1] == 2 * n_data:
        return weight_sym.to(device=ref.device, dtype=ref.dtype)
    if weight_sym.shape[-1] == n_data:
        return torch.cat([weight_sym, weight_sym], dim=-1).to(device=ref.device, dtype=ref.dtype)
    if weight_sym.numel() == 1:
        return weight_sym.reshape(1, 1).expand_as(ref).to(device=ref.device, dtype=ref.dtype)
    raise ValueError(
        f"Cannot expand symbol reliability weight with shape={tuple(weight_sym.shape)} "
        f"to ref shape={tuple(ref.shape)} for n_data={n_data}."
    )


def _extract_symbol_variance(v_prev: torch.Tensor | None, n_data: int, ref: torch.Tensor) -> torch.Tensor:
    if v_prev is None:
        return torch.ones((ref.shape[0], n_data), device=ref.device, dtype=ref.dtype)
    if v_prev.shape[-1] == 2 * n_data:
        return 0.5 * (v_prev[:, :n_data] + v_prev[:, n_data:]).to(device=ref.device, dtype=ref.dtype)
    if v_prev.shape[-1] == n_data:
        return v_prev.to(device=ref.device, dtype=ref.dtype)
    raise ValueError(
        f"Unexpected v_prev shape={tuple(v_prev.shape)} for n_data={n_data}. "
        "Expected block variance with n_data or 2*n_data entries."
    )


def _compute_sic_weight_block(
    v_prev: torch.Tensor | None,
    n_data: int,
    ref: torch.Tensor,
    kappa_t: torch.Tensor | None,
) -> tuple[torch.Tensor, torch.Tensor]:
    if (v_prev is None) or (kappa_t is None):
        weight_block = torch.ones_like(ref)
    else:
        v_sym = _extract_symbol_variance(v_prev, n_data, ref)
        weight_sym = 1.0 / (1.0 + kappa_t * v_sym.float().clamp_min(1e-8))
        weight_block = _expand_symbol_weight_to_block(weight_sym, n_data, ref)
    weight_mean = weight_block.detach().float().mean(dim=-1, keepdim=True)
    return weight_block, weight_mean


def _compute_skip_freeze_weight_block(
    v_prev: torch.Tensor | None,
    n_data: int,
    ref: torch.Tensor,
    quantile_t: torch.Tensor | None,
) -> tuple[torch.Tensor, torch.Tensor]:
    if (v_prev is None) or (quantile_t is None):
        weight_block = torch.ones_like(ref)
    else:
        v_sym = _extract_symbol_variance(v_prev, n_data, ref).float().clamp_min(1e-8)
        q_sym = quantile_t
        if q_sym.shape[-1] == 2 * n_data:
            q_sym = 0.5 * (q_sym[:, :n_data] + q_sym[:, n_data:])
        elif q_sym.shape[-1] not in (1, n_data):
            raise ValueError(
                f"Unexpected sic_skip_quantile shape={tuple(q_sym.shape)} for n_data={n_data}. "
                "Expected scalar, n_data, or 2*n_data entries."
            )
        q_sym = q_sym.clamp(0.0, 1.0)
        if q_sym.shape[-1] == 1:
            thresholds = torch.quantile(v_sym, q=float(q_sym[0, 0].detach().cpu().item()), dim=-1, keepdim=True)
        else:
            scalar_q = q_sym.mean(dim=-1, keepdim=True)
            thresholds = torch.quantile(
                v_sym,
                q=float(scalar_q[0, 0].detach().cpu().item()),
                dim=-1,
                keepdim=True,
            )
        keep_sym = (v_sym <= thresholds).to(dtype=ref.dtype)
        weight_block = _expand_symbol_weight_to_block(keep_sym, n_data, ref)
    weight_mean = weight_block.detach().float().mean(dim=-1, keepdim=True)
    return weight_block, weight_mean


def _channel_update_norm_tensor(
    h_prev: torch.Tensor | None,
    h_curr: torch.Tensor,
) -> torch.Tensor:
    if h_prev is None:
        return torch.zeros((h_curr.shape[0], 1), device=h_curr.device, dtype=h_curr.dtype)
    prev = h_prev.detach().float()
    curr = h_curr.detach().float()
    diff = (curr - prev).norm(dim=-1, keepdim=True)
    denom = prev.norm(dim=-1, keepdim=True).clamp_min(1e-8)
    return diff / denom


def _payload_tensor(value: Any, ref: torch.Tensor) -> torch.Tensor:
    if torch.is_tensor(value):
        return value.to(device=ref.device, dtype=ref.dtype)
    return torch.as_tensor(value, device=ref.device, dtype=ref.dtype)


def _compute_learned_vx_scale(
    payload: dict[str, Any],
    *,
    iter_idx: int,
    num_outer_iters: int,
    v_x: torch.Tensor,
    residual_energy: torch.Tensor,
    detector_sigma: torch.Tensor,
    channel_update_norm: torch.Tensor,
    snr_db: float,
) -> torch.Tensor:
    def _select_iter_scalar(value: Any, default: float) -> float:
        if value is None:
            return float(default)
        if torch.is_tensor(value):
            flat = value.detach().cpu().reshape(-1)
            if flat.numel() == 0:
                return float(default)
            return float(flat[min(int(iter_idx), int(flat.numel()) - 1)].item())
        if isinstance(value, (list, tuple)):
            if not value:
                return float(default)
            return float(value[min(int(iter_idx), len(value) - 1)])
        return float(value)

    batch_size = int(v_x.shape[0])
    dtype = v_x.dtype
    device = v_x.device
    iter_dim = int(payload.get("iter_onehot_dim", num_outer_iters))
    iter_indices = torch.full((batch_size,), int(iter_idx), device=device, dtype=torch.long)
    iter_onehot = F.one_hot(iter_indices, num_classes=iter_dim).to(dtype=dtype)
    vx_mean = v_x.detach().float().mean(dim=-1, keepdim=True).clamp_min(1e-8)
    residual_mean = residual_energy.detach().float().reshape(-1, 1).clamp_min(1e-8)
    detector_sigma_mean = detector_sigma.detach().float().reshape(-1, 1).clamp_min(1e-8)
    channel_update = channel_update_norm.detach().float().reshape(-1, 1).clamp_min(1e-8)
    snr_feat = torch.full((batch_size, 1), float(snr_db) / 30.0, device=device, dtype=torch.float32)
    feat_parts = [
        iter_onehot.float(),
        torch.log(vx_mean),
        torch.log(residual_mean),
        torch.log(detector_sigma_mean),
        torch.log(channel_update),
        snr_feat,
    ]

    base_scale_t = None
    if "base_scale_list" in payload:
        base_scale_scalar = _select_iter_scalar(payload.get("base_scale_list"), 1.0)
        base_scale_t = torch.full((batch_size, 1), base_scale_scalar, device=device, dtype=torch.float32)
        if bool(payload.get("include_log_base_scale", True)):
            feat_parts.append(torch.log(base_scale_t.clamp_min(1e-8)))

    feat = torch.cat(feat_parts, dim=-1)
    w1 = _payload_tensor(payload["w1"], feat)
    b1 = _payload_tensor(payload["b1"], feat)
    w2 = _payload_tensor(payload["w2"], feat)
    b2 = _payload_tensor(payload["b2"], feat)
    hid = F.silu(F.linear(feat, w1, b1))
    raw = F.linear(hid, w2, b2)

    if str(payload.get("residual_mode", "")) == "log_residual":
        if base_scale_t is None:
            base_scale_t = torch.ones((batch_size, 1), device=device, dtype=torch.float32)
        residual_bound_scalar = _select_iter_scalar(payload.get("residual_log_bound_list"), 0.0)
        residual_bound_t = torch.full((batch_size, 1), residual_bound_scalar, device=device, dtype=torch.float32)
        delta = residual_bound_t * torch.tanh(raw)
        scale = base_scale_t * torch.exp(delta)
    else:
        log_bound = float(payload.get("scale_log_bound", np.log(16.0)))
        scale = torch.exp(float(log_bound) * torch.tanh(raw))
    return scale.to(device=device, dtype=dtype)


class ParamStrategyNet(nn.Module):
    """
    Shared tiny strategy net.

    It predicts residual offsets around classical anchors so the model starts
    close to the hand-tuned baseline instead of learning from scratch.
    """

    def __init__(
        self,
        hidden_dim: int = 32,
        lambda_factor_init: float = 1e-3,
        alpha_init: float = 0.7,
        beta_init: float = 0.995,
        use_residual_net: bool = True,
        learned_param_set: str = "lambda_alpha_beta",
    ):
        super().__init__()
        if learned_param_set not in VALID_PARAM_SETS:
            raise ValueError(
                f"Unsupported learned_param_set={learned_param_set}. "
                f"Expected one of {VALID_PARAM_SETS}."
            )
        self.use_residual_net = bool(use_residual_net)
        self.learned_param_set = str(learned_param_set)
        self.net = nn.Sequential(
            nn.Linear(5, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 3),
        )
        final = self.net[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

        self.register_buffer(
            "anchor_raw",
            torch.tensor(
                [
                    _inv_softplus(lambda_factor_init),
                    float(np.log(alpha_init / max(1.0 - alpha_init, 1e-6))),
                    float(np.log(beta_init / max(1.0 - beta_init, 1e-6))),
                ],
                dtype=torch.float32,
            ),
        )
        if self.learned_param_set == "fixed":
            mask = torch.tensor([0.0, 0.0, 0.0], dtype=torch.float32)
        elif self.learned_param_set == "lambda_only":
            mask = torch.tensor([1.0, 0.0, 0.0], dtype=torch.float32)
        elif self.learned_param_set == "alpha_beta_only":
            mask = torch.tensor([0.0, 1.0, 1.0], dtype=torch.float32)
        else:
            mask = torch.tensor([1.0, 1.0, 1.0], dtype=torch.float32)
        self.register_buffer("learn_mask", mask)

    def forward(self, feat: torch.Tensor, sigma_eff: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = feat.float()
        sigma_eff = sigma_eff.float().reshape(-1, 1).clamp_min(1e-8)
        anchor_raw = self.anchor_raw.reshape(1, 3).to(feat.device, feat.dtype)
        delta = torch.zeros_like(anchor_raw).expand(feat.shape[0], -1)
        if self.use_residual_net and self.learned_param_set != "fixed":
            delta = self.net(feat)
        mask = self.learn_mask.reshape(1, 3).to(feat.device, feat.dtype)
        raw = anchor_raw + mask * delta
        lambda_ls = sigma_eff * F.softplus(raw[:, 0:1]) + 1e-4
        alpha = torch.sigmoid(raw[:, 1:2])
        beta = torch.sigmoid(raw[:, 2:3])
        return {
            "raw": raw,
            "anchor_raw": anchor_raw.expand(feat.shape[0], -1),
            "delta": delta,
            "lambda_ls": lambda_ls,
            "alpha": alpha,
            "beta": beta,
        }


@dataclass
class ParamJointLossStats:
    loss: torch.Tensor
    bits: torch.Tensor
    sym: torch.Tensor
    ber: torch.Tensor


class ParamLearnedJointReceiver(nn.Module):
    def __init__(
        self,
        n_total: int,
        c1: float,
        c2: float,
        l_max_cap: int,
        k_max_cap: int,
        data_positions: np.ndarray | torch.Tensor,
        num_outer_iters: int = 5,
        num_mp_layers: int = 6,
        max_active_atoms: int = 25,
        k_leak: int = 2,
        sigma_update_blend: float = 0.7,
        use_strategy_net: bool = True,
        learned_param_set: str = "lambda_alpha_beta",
    ):
        super().__init__()
        if learned_param_set not in VALID_PARAM_SETS:
            raise ValueError(
                f"Unsupported learned_param_set={learned_param_set}. "
                f"Expected one of {VALID_PARAM_SETS}."
            )
        self.n_total = int(n_total)
        self.max_active_atoms = int(max_active_atoms)
        self.num_outer_iters = int(num_outer_iters)
        self.sigma_update_blend = float(np.clip(sigma_update_blend, 0.0, 1.0))
        self.learned_param_set = str(learned_param_set)
        self.c1 = float(c1)
        self.c2 = float(c2)

        data_pos_arr = np.asarray(data_positions, dtype=np.int64)
        self.n_data = int(data_pos_arr.size)
        self.register_buffer("data_pos", torch.from_numpy(data_pos_arr))

        self.atom_bank = SparseAtomBank(
            n_total=n_total,
            c1=c1,
            c2=c2,
            l_max=l_max_cap,
            k_max=k_max_cap,
            k_leak=k_leak,
        )
        self.detectors = nn.ModuleList(
            [
                SparseMPDetector(
                    n_total=n_total,
                    data_positions=data_pos_arr,
                    num_layers=num_mp_layers,
                )
                for _ in range(self.num_outer_iters)
            ]
        )
        for detector in self.detectors:
            detector.requires_grad_(False)

        self.strategy_net = ParamStrategyNet(
            use_residual_net=use_strategy_net,
            learned_param_set=self.learned_param_set,
        )
        if self.learned_param_set == "fixed":
            self.strategy_net.requires_grad_(False)

    def _make_atom_bank(self, k_leak_override: int | None, device: torch.device) -> SparseAtomBank:
        k_leak_use = self.atom_bank.k_leak if k_leak_override is None else int(max(k_leak_override, 0))
        if k_leak_use == self.atom_bank.k_leak:
            return self.atom_bank
        bank = SparseAtomBank(
            n_total=self.atom_bank.n_total,
            c1=self.c1,
            c2=self.c2,
            l_max=self.atom_bank.l_max,
            k_max=self.atom_bank.k_max,
            k_leak=k_leak_use,
        )
        return bank.to(device)

    def _expand_group_param(
        self,
        value: Any,
        ref: torch.Tensor,
        default: float,
    ) -> torch.Tensor:
        if value is None:
            return torch.full_like(ref, float(default))
        return _as_override_tensor(value, ref, clamp_min=1e-6)

    def _support_masks(self, support_mask: torch.Tensor, seed_mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        seed_part = (seed_mask > 0.5).float()
        expanded_part = ((support_mask > 0.5).float() - seed_part).clamp_min(0.0)
        return seed_part, expanded_part

    def _group_ridge_refit(
        self,
        y_flat: torch.Tensor,
        x_total_flat: torch.Tensor,
        support_mask: torch.Tensor,
        seed_mask: torch.Tensor,
        gain_prior_flat: torch.Tensor,
        lambda_ls: torch.Tensor,
        alpha: torch.Tensor,
        seed_mult: torch.Tensor,
        expand_mult: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)
        q = self.atom_bank.num_atoms
        gain_prior_c = torch.complex(
            gain_prior_flat[:, :q].float(),
            gain_prior_flat[:, q:].float(),
        )
        gain_out = torch.zeros_like(gain_prior_c)
        sigma_ls = y_flat.new_zeros(y_flat.shape[0], 1)

        for b in range(y_flat.shape[0]):
            idx = torch.nonzero(support_mask[b] > 0.5, as_tuple=False).squeeze(-1)
            if idx.numel() == 0:
                idx = torch.argmax(support_mask[b], dim=-1, keepdim=True)
            seed_sel = (seed_mask[b, idx] > 0.5).float()
            expand_sel = ((support_mask[b, idx] > 0.5).float() - seed_sel).clamp_min(0.0)
            reg_diag = lambda_ls[b, 0] * (
                seed_mult[b, 0] * seed_sel + expand_mult[b, 0] * expand_sel
            )
            A = self.atom_bank._build_dictionary_single(x_c[b], idx)
            prior_sel = gain_prior_c[b, idx]
            g_ls = self.atom_bank._small_complex_ls(
                A,
                y_c[b],
                float(lambda_ls[b, 0].detach().cpu()),
                prior_sel=prior_sel,
                reg_diag=reg_diag,
            )
            alpha_b = alpha[b, 0].to(g_ls.real.dtype)
            g_new = (1.0 - alpha_b) * prior_sel + alpha_b * g_ls
            gain_out[b, idx] = g_new
            residual = y_c[b] - A @ g_new
            sigma_ls[b, 0] = residual.abs().square().mean().real.float()

        gain_flat = complex_to_block(gain_out)
        h_flat = self.atom_bank.reconstruct(gain_flat, support_weight=support_mask)
        return {
            "gain_flat": gain_flat,
            "H_flat": h_flat,
            "sigma_ls": sigma_ls,
        }

    def _strategy_features(
        self,
        sigma_eff: torch.Tensor,
        residual_energy_prev: torch.Tensor,
        support_mask: torch.Tensor,
        v_prev: torch.Tensor | None,
        iter_idx: int,
    ) -> torch.Tensor:
        sigma_feat = torch.log(sigma_eff.float().clamp_min(1e-8))
        residual_feat = torch.log(residual_energy_prev.float().clamp_min(1e-8))
        support_ratio = support_mask.float().mean(dim=-1, keepdim=True).clamp(0.0, 1.0)
        if v_prev is None:
            vx_feat = torch.full_like(sigma_feat, 0.5)
        else:
            vx_feat = v_prev.float().mean(dim=-1, keepdim=True).clamp_min(1e-6)
        iter_denom = max(self.num_outer_iters - 1, 1)
        iter_frac = sigma_feat.new_full((sigma_feat.shape[0], 1), float(iter_idx) / float(iter_denom))
        return torch.cat([sigma_feat, residual_feat, support_ratio, vx_feat, iter_frac], dim=-1)

    def _ridge_refit_single(
        self,
        y_c: torch.Tensor,
        x_total_c: torch.Tensor,
        support_idx: torch.Tensor,
        prior_sel_c: torch.Tensor,
        lambda_ls: torch.Tensor,
        alpha: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if support_idx.numel() <= 0:
            raise ValueError("support_idx cannot be empty")

        A_c = self.atom_bank._build_dictionary_single(x_total_c, support_idx)
        work_device = A_c.device
        if work_device.type == "mps":
            A_c = A_c.cpu()
            y_c = y_c.cpu()
            prior_sel_c = prior_sel_c.cpu()
            lambda_ls = lambda_ls.cpu()
            alpha = alpha.cpu()

        a_r = A_c.real.float()
        a_i = A_c.imag.float()
        top = torch.cat([a_r, -a_i], dim=-1)
        bot = torch.cat([a_i, a_r], dim=-1)
        A = torch.cat([top, bot], dim=0)

        y = torch.cat([y_c.real.float(), y_c.imag.float()], dim=0)
        prior_r = torch.cat([prior_sel_c.real.float(), prior_sel_c.imag.float()], dim=0)

        k2 = A.shape[1]
        eye = torch.eye(k2, dtype=A.dtype, device=A.device)
        lam = lambda_ls.reshape(()).to(A.dtype).clamp_min(1e-6)
        lhs = A.transpose(0, 1) @ A + lam * eye
        rhs = A.transpose(0, 1) @ y + lam * prior_r
        g_ls_r = torch.linalg.solve(lhs, rhs)

        alpha_s = alpha.reshape(()).to(g_ls_r.dtype)
        g_new_r = (1.0 - alpha_s) * prior_r + alpha_s * g_ls_r
        k = support_idx.numel()
        g_new_c = torch.complex(g_new_r[:k], g_new_r[k:])
        residual = y_c - A_c @ g_new_c
        sigma_ls = residual.abs().square().mean().real.float()
        if work_device.type == "mps":
            g_new_c = g_new_c.to(work_device)
            sigma_ls = sigma_ls.to(work_device)
        return g_new_c, sigma_ls

    def _fixed_support_refit(
        self,
        y_flat: torch.Tensor,
        x_total_flat: torch.Tensor,
        support_mask: torch.Tensor,
        gain_prior_flat: torch.Tensor,
        lambda_ls: torch.Tensor,
        alpha: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        y_c = block_to_complex(y_flat)
        x_c = block_to_complex(x_total_flat)
        q = self.atom_bank.num_atoms
        gain_prior_c = torch.complex(
            gain_prior_flat[:, :q].float(),
            gain_prior_flat[:, q:].float(),
        )
        gain_out = torch.zeros_like(gain_prior_c)
        sigma_ls = y_flat.new_zeros(y_flat.shape[0], 1)

        for b in range(y_flat.shape[0]):
            idx = torch.nonzero(support_mask[b] > 0.5, as_tuple=False).squeeze(-1)
            if idx.numel() == 0:
                idx = torch.argmax(support_mask[b], dim=-1, keepdim=True)
            g_new_c, sigma_b = self._ridge_refit_single(
                y_c=y_c[b],
                x_total_c=x_c[b],
                support_idx=idx,
                prior_sel_c=gain_prior_c[b, idx],
                lambda_ls=lambda_ls[b, 0],
                alpha=alpha[b, 0],
            )
            gain_out[b, idx] = g_new_c
            sigma_ls[b, 0] = sigma_b

        gain_flat = complex_to_block(gain_out)
        h_flat = self.atom_bank.reconstruct(gain_flat, support_weight=support_mask)
        return {
            "gain_flat": gain_flat,
            "H_flat": h_flat,
            "sigma_ls": sigma_ls,
        }

    def forward(
        self,
        inp_feat: torch.Tensor,
        inp_y: torch.Tensor,
        inp_xp: torch.Tensor,
        inp_sigma: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        del inp_feat  # v1 intentionally keeps the receiver model-driven.

        sigma_eff = inp_sigma.float().reshape(-1, 1)
        init = self.atom_bank.omp_init_support(
            y_flat=inp_y,
            x_total_flat=inp_xp,
            max_active_atoms=self.max_active_atoms,
            lambda_ls=1e-3,
        )
        support_mask = init["hard_mask"].detach()
        seed_mask = init["seed_mask"].detach()
        gain_prev = init["gain_flat"]

        mu_prev = None
        v_prev = None
        llr_prev = None
        residual_energy_prev = block_to_complex(inp_y).abs().square().mean(dim=-1, keepdim=True)

        history: list[dict[str, torch.Tensor]] = []
        lambda_hist = []
        alpha_hist = []
        beta_hist = []

        for t in range(self.num_outer_iters):
            feat_t = self._strategy_features(
                sigma_eff=sigma_eff,
                residual_energy_prev=residual_energy_prev,
                support_mask=support_mask,
                v_prev=v_prev,
                iter_idx=t,
            )
            strat_t = self.strategy_net(feat_t, sigma_eff=sigma_eff)
            lambda_t = strat_t["lambda_ls"]
            alpha_t = strat_t["alpha"]
            beta_t = strat_t["beta"]

            if mu_prev is None:
                x_total_refit = inp_xp
            else:
                x_fb = beta_t * mu_prev
                x_total_refit = inp_xp + embed_data_block(x_fb, self.n_total, self.data_pos)

            refit_t = self._fixed_support_refit(
                y_flat=inp_y,
                x_total_flat=x_total_refit,
                support_mask=support_mask,
                gain_prior_flat=gain_prev,
                lambda_ls=lambda_t,
                alpha=alpha_t,
            )
            gain_prev = refit_t["gain_flat"]
            h_flat = refit_t["H_flat"]

            detector = self.detectors[t]
            if mu_prev is None:
                x_hat, v_x, llr = detector([h_flat, inp_y, inp_xp, sigma_eff])
            else:
                x_hat, v_x, llr = detector([h_flat, inp_y, inp_xp, sigma_eff, mu_prev, v_prev])

            x_total_hat = inp_xp + embed_data_block(x_hat, self.n_total, self.data_pos)
            y_hat = self.atom_bank.block_matvec(h_flat, x_total_hat)
            res_c = block_to_complex(inp_y - y_hat)
            residual_energy = res_c.abs().square().mean(dim=-1, keepdim=True)
            sigma_eff = (
                self.sigma_update_blend * sigma_eff
                + (1.0 - self.sigma_update_blend) * refit_t["sigma_ls"]
            )

            history.append(
                {
                    "detection": x_hat,
                    "v_x": v_x,
                    "llr": llr,
                    "H_flat": h_flat,
                    "gain_flat": gain_prev,
                    "sigma_eff": sigma_eff,
                    "sigma_ls": refit_t["sigma_ls"],
                    "residual_energy": residual_energy,
                    "lambda_ls": lambda_t,
                    "alpha": alpha_t,
                    "beta": beta_t,
                }
            )
            lambda_hist.append(lambda_t)
            alpha_hist.append(alpha_t)
            beta_hist.append(beta_t)
            mu_prev = x_hat
            v_prev = v_x
            llr_prev = llr
            residual_energy_prev = residual_energy

        final = history[-1]
        support_count = support_mask.sum(dim=-1, keepdim=True)
        seed_count = seed_mask.sum(dim=-1, keepdim=True)
        _seed_part, expanded_only_mask = self._support_masks(support_mask, seed_mask)
        expanded_count = expanded_only_mask.sum(dim=-1, keepdim=True)
        return {
            "final_detection": final["detection"],
            "final_llr": final["llr"],
            "final_vx": final["v_x"],
            "final_H_flat": final["H_flat"],
            "stage_history": history,
            "param_history": {
                "lambda_ls": torch.stack(lambda_hist, dim=1),
                "alpha": torch.stack(alpha_hist, dim=1),
                "beta": torch.stack(beta_hist, dim=1),
            },
            "support_stats": {
                "support_mask": support_mask,
                "seed_mask": seed_mask,
                "expanded_only_mask": expanded_only_mask,
                "support_ratio": support_count / float(self.atom_bank.num_atoms),
                "support_count": support_count,
                "seed_count": seed_count,
                "expanded_count": expanded_count,
                "k_leak_used": int(self.atom_bank.k_leak),
            },
            "learned_param_set": self.learned_param_set,
        }

    @torch.no_grad()
    def diagnose(
        self,
        inp_feat: torch.Tensor,
        inp_y: torch.Tensor,
        inp_xp: torch.Tensor,
        inp_sigma: torch.Tensor,
        diagnostic_overrides: dict[str, Any] | None = None,
    ) -> dict[str, torch.Tensor]:
        del inp_feat

        overrides = dict(diagnostic_overrides or {})
        k_leak_override = overrides.get("k_leak")
        atom_bank = self._make_atom_bank(k_leak_override, inp_y.device)

        sigma_eff = inp_sigma.float().reshape(-1, 1)
        init = atom_bank.omp_init_support(
            y_flat=inp_y,
            x_total_flat=inp_xp,
            max_active_atoms=self.max_active_atoms,
            lambda_ls=1e-3,
        )
        support_mask = init["hard_mask"].detach()
        seed_mask = init["seed_mask"].detach()
        gain_prev = init["gain_flat"]

        mu_prev = None
        v_prev = None
        residual_energy_prev = block_to_complex(inp_y).abs().square().mean(dim=-1, keepdim=True)

        history: list[dict[str, torch.Tensor]] = []
        lambda_hist = []
        alpha_hist = []
        beta_hist = []
        anchor_lambda_hist = []
        anchor_alpha_hist = []
        anchor_beta_hist = []
        detector_sigma_hist = []
        sic_weight_hist = []
        vx_recal_gain_hist = []

        for t in range(self.num_outer_iters):
            feat_t = self._strategy_features(
                sigma_eff=sigma_eff,
                residual_energy_prev=residual_energy_prev,
                support_mask=support_mask,
                v_prev=v_prev,
                iter_idx=t,
            )
            strat_t = self.strategy_net(feat_t, sigma_eff=sigma_eff)

            anchor_raw = strat_t["anchor_raw"]
            anchor_lambda = sigma_eff * F.softplus(anchor_raw[:, 0:1]) + 1e-4
            anchor_alpha = torch.sigmoid(anchor_raw[:, 1:2])
            anchor_beta = torch.sigmoid(anchor_raw[:, 2:3])

            lambda_t = strat_t["lambda_ls"]
            alpha_t = strat_t["alpha"]
            beta_t = strat_t["beta"]

            if "lambda_scale" in overrides:
                lambda_t = lambda_t * _as_override_tensor(
                    _select_iter_override(overrides["lambda_scale"], t),
                    lambda_t,
                    clamp_min=1e-6,
                )
            if "lambda_ls" in overrides:
                lambda_t = _as_override_tensor(
                    _select_iter_override(overrides["lambda_ls"], t),
                    lambda_t,
                    clamp_min=1e-6,
                )
            if "alpha" in overrides:
                alpha_t = _as_override_tensor(
                    _select_iter_override(overrides["alpha"], t),
                    alpha_t,
                    clamp_min=0.0,
                    clamp_max=1.0,
                )
            if "beta" in overrides:
                beta_t = _as_override_tensor(
                    _select_iter_override(overrides["beta"], t),
                    beta_t,
                    clamp_min=0.0,
                    clamp_max=1.0,
                )

            sigma_blend = float(
                _select_iter_override(overrides.get("sigma_update_blend", self.sigma_update_blend), t)
            )

            detector_sigma = sigma_eff
            if ("detector_sigma_c0" in overrides) or ("detector_sigma_cr" in overrides):
                sigma_base = inp_sigma.float().reshape(-1, 1)
                c0_t = _as_override_tensor(
                    _select_iter_override(overrides.get("detector_sigma_c0", 1.0), t),
                    detector_sigma,
                    clamp_min=0.0,
                )
                cr_t = _as_override_tensor(
                    _select_iter_override(overrides.get("detector_sigma_cr", 0.0), t),
                    detector_sigma,
                    clamp_min=0.0,
                )
                detector_sigma = (c0_t * sigma_base + cr_t * residual_energy_prev).clamp_min(1e-6)
            elif "detector_sigma_inflation" in overrides:
                detector_sigma = detector_sigma * _as_override_tensor(
                    _select_iter_override(overrides["detector_sigma_inflation"], t),
                    detector_sigma,
                    clamp_min=1e-6,
                )

            sic_weight_mean = torch.ones_like(beta_t)
            if mu_prev is None:
                x_total_refit = inp_xp
            else:
                mu_fb = mu_prev
                has_sic_weight = "sic_uncertainty_kappa" in overrides
                has_skip_freeze = "sic_skip_quantile" in overrides
                if has_sic_weight and has_skip_freeze:
                    raise ValueError("Use either `sic_uncertainty_kappa` or `sic_skip_quantile`, not both.")
                if has_sic_weight:
                    sic_mode = str(overrides.get("sic_uncertainty_mode", "inv_linear"))
                    if sic_mode != "inv_linear":
                        raise ValueError(f"Unsupported sic_uncertainty_mode={sic_mode}. Expected 'inv_linear'.")
                    kappa_t = _as_override_tensor(
                        _select_iter_override(overrides["sic_uncertainty_kappa"], t),
                        beta_t,
                        clamp_min=0.0,
                    )
                    weight_block, sic_weight_mean = _compute_sic_weight_block(
                        v_prev=v_prev,
                        n_data=self.n_data,
                        ref=mu_prev,
                        kappa_t=kappa_t,
                    )
                    mu_fb = weight_block * mu_prev
                elif has_skip_freeze:
                    skip_mode = str(overrides.get("sic_skip_mode", "hard_quantile"))
                    if skip_mode != "hard_quantile":
                        raise ValueError(f"Unsupported sic_skip_mode={skip_mode}. Expected 'hard_quantile'.")
                    skip_q_t = _as_override_tensor(
                        _select_iter_override(overrides["sic_skip_quantile"], t),
                        beta_t,
                        clamp_min=0.0,
                        clamp_max=1.0,
                    )
                    weight_block, sic_weight_mean = _compute_skip_freeze_weight_block(
                        v_prev=v_prev,
                        n_data=self.n_data,
                        ref=mu_prev,
                        quantile_t=skip_q_t,
                    )
                    mu_fb = weight_block * mu_prev
                x_fb = beta_t * mu_fb
                x_total_refit = inp_xp + embed_data_block(x_fb, self.n_total, self.data_pos)

            if ("seed_mult" in overrides) or ("expand_mult" in overrides):
                seed_mult = self._expand_group_param(
                    _select_iter_override(overrides.get("seed_mult"), t),
                    lambda_t,
                    1.0,
                )
                expand_mult = self._expand_group_param(
                    _select_iter_override(overrides.get("expand_mult"), t),
                    lambda_t,
                    1.0,
                )
                refit_t = self._group_ridge_refit(
                    y_flat=inp_y,
                    x_total_flat=x_total_refit,
                    support_mask=support_mask,
                    seed_mask=seed_mask,
                    gain_prior_flat=gain_prev,
                    lambda_ls=lambda_t,
                    alpha=alpha_t,
                    seed_mult=seed_mult,
                    expand_mult=expand_mult,
                )
            else:
                refit_t = self._fixed_support_refit(
                    y_flat=inp_y,
                    x_total_flat=x_total_refit,
                    support_mask=support_mask,
                    gain_prior_flat=gain_prev,
                    lambda_ls=lambda_t,
                    alpha=alpha_t,
                )
            gain_prev = refit_t["gain_flat"]
            h_flat = refit_t["H_flat"]
            channel_update_norm = _channel_update_norm_tensor(
                history[-1]["H_flat"] if history else None,
                h_flat,
            )

            detector = self.detectors[t]
            if mu_prev is None:
                x_hat, v_x, llr = detector([h_flat, inp_y, inp_xp, detector_sigma])
            else:
                x_hat, v_x, llr = detector([h_flat, inp_y, inp_xp, detector_sigma, mu_prev, v_prev])
            v_x_raw = v_x
            vx_recal_gain_mean = torch.ones_like(beta_t)

            if "vx_recalibration_scale" in overrides:
                v_x = _as_override_tensor(
                    _select_iter_override(overrides["vx_recalibration_scale"], t),
                    v_x,
                    clamp_min=0.25,
                    clamp_max=64.0,
                ) * v_x
                v_x = v_x.clamp_min(1e-4).clamp_max(2.0)
            if ("vx_recalibration_affine_a" in overrides) or ("vx_recalibration_affine_b" in overrides):
                a_t = _as_override_tensor(
                    _select_iter_override(overrides.get("vx_recalibration_affine_a", 1.0), t),
                    v_x,
                    clamp_min=1e-6,
                )
                b_t = _as_override_tensor(
                    _select_iter_override(overrides.get("vx_recalibration_affine_b", 0.0), t),
                    v_x,
                    clamp_min=0.0,
                )
                v_x = a_t * v_x + b_t
                v_x = v_x.clamp_min(1e-4).clamp_max(2.0)
            if any(k in overrides for k in ("vx_recalibration_clip_scale", "vx_recalibration_clip_min", "vx_recalibration_clip_max")):
                c_t = _as_override_tensor(
                    _select_iter_override(overrides.get("vx_recalibration_clip_scale", 1.0), t),
                    v_x,
                    clamp_min=0.25,
                    clamp_max=64.0,
                )
                vmin_t = _as_override_tensor(
                    _select_iter_override(overrides.get("vx_recalibration_clip_min", 1e-4), t),
                    v_x,
                    clamp_min=1e-4,
                    clamp_max=2.0,
                )
                vmax_t = _as_override_tensor(
                    _select_iter_override(overrides.get("vx_recalibration_clip_max", 2.0), t),
                    v_x,
                    clamp_min=1e-4,
                    clamp_max=2.0,
                )
                vmax_t = torch.maximum(vmax_t, vmin_t + 1e-6)
                v_x = torch.clamp(c_t * v_x, min=vmin_t, max=vmax_t)
            if "vx_recalibration_learned_payload" in overrides:
                payload = overrides["vx_recalibration_learned_payload"]
                snr_db = float(overrides.get("vx_recalibration_learned_snr_db", 0.0))
                learned_scale = _compute_learned_vx_scale(
                    payload,
                    iter_idx=t,
                    num_outer_iters=self.num_outer_iters,
                    v_x=v_x,
                    residual_energy=residual_energy_prev,
                    detector_sigma=detector_sigma,
                    channel_update_norm=channel_update_norm,
                    snr_db=snr_db,
                )
                v_x = torch.clamp(learned_scale * v_x, min=1e-4, max=2.0)
            raw_mean = v_x_raw.detach().float().mean(dim=-1, keepdim=True).clamp_min(1e-8)
            calib_mean = v_x.detach().float().mean(dim=-1, keepdim=True)
            vx_recal_gain_mean = calib_mean / raw_mean

            x_total_hat = inp_xp + embed_data_block(x_hat, self.n_total, self.data_pos)
            y_hat = self.atom_bank.block_matvec(h_flat, x_total_hat)
            res_c = block_to_complex(inp_y - y_hat)
            residual_energy = res_c.abs().square().mean(dim=-1, keepdim=True)
            sigma_eff = (
                sigma_blend * sigma_eff
                + (1.0 - sigma_blend) * refit_t["sigma_ls"]
            )

            history.append(
                {
                    "detection": x_hat,
                    "v_x": v_x,
                    "llr": llr,
                    "H_flat": h_flat,
                    "gain_flat": gain_prev,
                    "sigma_eff": sigma_eff,
                    "sigma_ls": refit_t["sigma_ls"],
                    "residual_energy": residual_energy,
                    "lambda_ls": lambda_t,
                    "alpha": alpha_t,
                    "beta": beta_t,
                    "anchor_lambda_ls": anchor_lambda,
                    "anchor_alpha": anchor_alpha,
                    "anchor_beta": anchor_beta,
                    "detector_sigma": detector_sigma,
                    "sic_weight_mean": sic_weight_mean,
                    "vx_recal_gain_mean": vx_recal_gain_mean,
                }
            )
            lambda_hist.append(lambda_t)
            alpha_hist.append(alpha_t)
            beta_hist.append(beta_t)
            anchor_lambda_hist.append(anchor_lambda)
            anchor_alpha_hist.append(anchor_alpha)
            anchor_beta_hist.append(anchor_beta)
            detector_sigma_hist.append(detector_sigma)
            sic_weight_hist.append(sic_weight_mean)
            vx_recal_gain_hist.append(vx_recal_gain_mean)
            mu_prev = x_hat
            v_prev = v_x
            residual_energy_prev = residual_energy

        final = history[-1]
        support_count = support_mask.sum(dim=-1, keepdim=True)
        seed_count = seed_mask.sum(dim=-1, keepdim=True)
        seed_part, expanded_only_mask = self._support_masks(support_mask, seed_mask)
        expanded_count = expanded_only_mask.sum(dim=-1, keepdim=True)
        return {
            "final_detection": final["detection"],
            "final_llr": final["llr"],
            "final_vx": final["v_x"],
            "final_H_flat": final["H_flat"],
            "stage_history": history,
            "param_history": {
                "lambda_ls": torch.stack(lambda_hist, dim=1),
                "alpha": torch.stack(alpha_hist, dim=1),
                "beta": torch.stack(beta_hist, dim=1),
            },
            "support_stats": {
                "support_mask": support_mask,
                "seed_mask": seed_mask,
                "expanded_only_mask": expanded_only_mask,
                "support_ratio": support_count / float(self.atom_bank.num_atoms),
                "support_count": support_count,
                "seed_count": seed_count,
                "expanded_count": expanded_count,
                "k_leak_used": int(atom_bank.k_leak),
            },
            "diagnostics": {
                "param_anchor_history": {
                    "lambda_ls": torch.stack(anchor_lambda_hist, dim=1),
                    "alpha": torch.stack(anchor_alpha_hist, dim=1),
                    "beta": torch.stack(anchor_beta_hist, dim=1),
                },
                "param_delta_history": {
                    "lambda_ls": torch.stack(lambda_hist, dim=1) - torch.stack(anchor_lambda_hist, dim=1),
                    "alpha": torch.stack(alpha_hist, dim=1) - torch.stack(anchor_alpha_hist, dim=1),
                    "beta": torch.stack(beta_hist, dim=1) - torch.stack(anchor_beta_hist, dim=1),
                },
                "detector_sigma_history": torch.stack(detector_sigma_hist, dim=1),
                "sic_weight_history": torch.stack(sic_weight_hist, dim=1),
                "vx_recal_gain_history": torch.stack(vx_recal_gain_hist, dim=1),
                "seed_mask": seed_part,
                "expanded_only_mask": expanded_only_mask,
                "overrides": {
                    k: ("<learned_payload>" if k == "vx_recalibration_learned_payload" else v)
                    for k, v in overrides.items()
                },
            },
            "learned_param_set": self.learned_param_set,
        }


def compute_param_joint_loss(
    out: dict[str, torch.Tensor],
    bits_true: torch.Tensor,
    x_data_true: torch.Tensor,
    lambda_sym: float = 0.1,
    deep_supervision: float = 0.0,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    bits_true = bits_true.float()
    x_data_true = x_data_true.float()

    final_llr = out["final_llr"].float()
    final_det = out["final_detection"].float()
    loss_bits = F.binary_cross_entropy_with_logits(final_llr, bits_true)
    loss_sym = F.mse_loss(final_det, x_data_true)

    if deep_supervision > 0.0 and out["stage_history"]:
        aux_bits = bits_true.new_zeros(())
        aux_sym = bits_true.new_zeros(())
        aux_count = 0
        for stage in out["stage_history"][:-1]:
            aux_bits = aux_bits + F.binary_cross_entropy_with_logits(stage["llr"].float(), bits_true)
            aux_sym = aux_sym + F.mse_loss(stage["detection"].float(), x_data_true)
            aux_count += 1
        if aux_count > 0:
            aux_bits = aux_bits / aux_count
            aux_sym = aux_sym / aux_count
            loss_bits = loss_bits + deep_supervision * aux_bits
            loss_sym = loss_sym + deep_supervision * aux_sym

    total = loss_bits + float(lambda_sym) * loss_sym
    ber = ber_from_detection(x_data_true, final_det)
    stats = {
        "loss": total.detach(),
        "bits": loss_bits.detach(),
        "sym": loss_sym.detach(),
        "ber": ber.detach(),
    }
    return total, stats


def build_param_joint_model(
    input_dim: int,
    n_total: int,
    c1: float,
    c2: float,
    l_max_cap: int,
    k_max_cap: int,
    data_positions: np.ndarray | torch.Tensor,
    num_outer_iters: int = 5,
    num_mp_layers: int = 6,
    max_active_atoms: int = 25,
    k_leak: int = 2,
    use_strategy_net: bool = True,
    learned_param_set: str = "lambda_alpha_beta",
) -> ParamLearnedJointReceiver:
    del input_dim
    return ParamLearnedJointReceiver(
        n_total=n_total,
        c1=c1,
        c2=c2,
        l_max_cap=l_max_cap,
        k_max_cap=k_max_cap,
        data_positions=data_positions,
        num_outer_iters=num_outer_iters,
        num_mp_layers=num_mp_layers,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        use_strategy_net=use_strategy_net,
        learned_param_set=learned_param_set,
    )


__all__ = [
    "ParamLearnedJointReceiver",
    "ParamStrategyNet",
    "VALID_PARAM_SETS",
    "build_param_joint_model",
    "compute_param_joint_loss",
    "extract_data_block",
    "ber_from_detection",
]
