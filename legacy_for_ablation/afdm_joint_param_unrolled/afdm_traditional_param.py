"""
afdm_traditional_param.py

Stage-7 strict-traditional param-learned joint receiver:
  - classical OMP init from the legacy JointOMPMP baseline
  - fixed support across outer iterations
  - data-aided ridge LS with gain prior
  - classical PIC detector with symbol/channel damping
  - learn only classical scalar hyper-parameters
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from .afdm_baselines import construct_sensing_matrix, omp_sparse
from .afdm_joint_param import compute_param_joint_loss
from .afdm_joint_unrolled import (
    SparseAtomBank,
    ber_from_detection,
    block_to_complex,
    complex_to_block,
    embed_data_block,
    extract_data_block,
)


VALID_TRAD_PARAM_SETS = (
    "fixed",
    "lambda_only",
    "damping_only",
    "classical_full",
)


def _inv_softplus(value: float) -> float:
    value = float(max(value, 1e-8))
    return float(np.log(np.expm1(value)))


def _inv_sigmoid(value: float) -> float:
    value = float(np.clip(value, 1e-6, 1.0 - 1e-6))
    return float(np.log(value / (1.0 - value)))


def _complex_sign(x: torch.Tensor, scale: float) -> torch.Tensor:
    scale_t = torch.as_tensor(scale, dtype=x.real.dtype, device=x.device)
    real = torch.where(x.real >= 0.0, scale_t, -scale_t)
    imag = torch.where(x.imag >= 0.0, scale_t, -scale_t)
    return torch.complex(real, imag)


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


class TraditionalStrategyNet(nn.Module):
    """
    Shared tiny strategy net that only tunes classical scalar hyper-parameters.
    """

    def __init__(
        self,
        hidden_dim: int = 32,
        lambda_factor_init: float = 1e-3,
        gamma_h_init: float = 0.7,
        gamma_x_init: float = 0.6,
        pic_damp_init: float = 0.5,
        use_residual_net: bool = True,
        learned_param_set: str = "classical_full",
    ):
        super().__init__()
        if learned_param_set not in VALID_TRAD_PARAM_SETS:
            raise ValueError(
                f"Unsupported learned_param_set={learned_param_set}. "
                f"Expected one of {VALID_TRAD_PARAM_SETS}."
            )
        self.use_residual_net = bool(use_residual_net)
        self.learned_param_set = str(learned_param_set)
        self.net = nn.Sequential(
            nn.Linear(5, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, 4),
        )
        final = self.net[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

        self.register_buffer(
            "anchor_raw",
            torch.tensor(
                [
                    _inv_softplus(lambda_factor_init),
                    _inv_sigmoid(gamma_h_init),
                    _inv_sigmoid(gamma_x_init),
                    _inv_sigmoid(pic_damp_init),
                ],
                dtype=torch.float32,
            ),
        )
        if self.learned_param_set == "fixed":
            mask = torch.tensor([0.0, 0.0, 0.0, 0.0], dtype=torch.float32)
        elif self.learned_param_set == "lambda_only":
            mask = torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float32)
        elif self.learned_param_set == "damping_only":
            mask = torch.tensor([0.0, 1.0, 1.0, 1.0], dtype=torch.float32)
        else:
            mask = torch.tensor([1.0, 1.0, 1.0, 1.0], dtype=torch.float32)
        self.register_buffer("learn_mask", mask)

    def forward(self, feat: torch.Tensor) -> dict[str, torch.Tensor]:
        feat = feat.float()
        anchor_raw = self.anchor_raw.reshape(1, 4).to(feat.device, feat.dtype)
        delta = torch.zeros_like(anchor_raw).expand(feat.shape[0], -1)
        if self.use_residual_net and self.learned_param_set != "fixed":
            delta = self.net(feat)
        mask = self.learn_mask.reshape(1, 4).to(feat.device, feat.dtype)
        raw = anchor_raw + mask * delta
        lambda_factor = F.softplus(raw[:, 0:1])
        gamma_h = torch.sigmoid(raw[:, 1:2])
        gamma_x = torch.sigmoid(raw[:, 2:3])
        pic_damp = torch.sigmoid(raw[:, 3:4])
        return {
            "raw": raw,
            "anchor_raw": anchor_raw.expand(feat.shape[0], -1),
            "delta": delta,
            "lambda_factor": lambda_factor,
            "gamma_h": gamma_h,
            "gamma_x": gamma_x,
            "pic_damp": pic_damp,
        }


@dataclass
class TraditionalParamLossStats:
    loss: torch.Tensor
    bits: torch.Tensor
    sym: torch.Tensor
    ber: torch.Tensor


class TraditionalParamJointReceiver(nn.Module):
    def __init__(
        self,
        n_total: int,
        c1: float,
        c2: float,
        l_max_cap: int,
        k_max_cap: int,
        rho: float,
        data_positions: np.ndarray | torch.Tensor,
        num_outer_iters: int = 5,
        pic_iters: int = 15,
        max_active_atoms: int = 25,
        k_leak: int = 2,
        sigma_update_blend: float = 0.7,
        tau_h_factor: float = 0.01,
        tau_h_sigma_factor: float = 0.1,
        use_strategy_net: bool = True,
        learned_param_set: str = "classical_full",
    ):
        super().__init__()
        if learned_param_set not in VALID_TRAD_PARAM_SETS:
            raise ValueError(
                f"Unsupported learned_param_set={learned_param_set}. "
                f"Expected one of {VALID_TRAD_PARAM_SETS}."
            )
        self.n_total = int(n_total)
        self.num_outer_iters = int(num_outer_iters)
        self.pic_iters = int(pic_iters)
        self.max_active_atoms = int(max_active_atoms)
        self.sigma_update_blend = float(np.clip(sigma_update_blend, 0.0, 1.0))
        self.tau_h_factor = float(max(tau_h_factor, 0.0))
        self.tau_h_sigma_factor = float(max(tau_h_sigma_factor, 0.0))
        self.learned_param_set = str(learned_param_set)
        self.k_span = 2 * int(k_max_cap) + 1
        self.omp_n_paths = max(1, min(
            int(max_active_atoms + max(1, 2 * k_leak + 1) - 1) // max(1, 2 * k_leak + 1),
            (int(l_max_cap) + 1) * self.k_span,
        ))
        self.lambda_factor_anchor = 1e-3

        data_pos_arr = np.asarray(data_positions, dtype=np.int64)
        self.n_data = int(data_pos_arr.size)
        self.register_buffer("data_pos", torch.from_numpy(data_pos_arr))
        self.symbol_scale = float(np.sqrt(max(1.0 - rho, 1e-8)) / np.sqrt(2.0))

        self.atom_bank = SparseAtomBank(
            n_total=n_total,
            c1=c1,
            c2=c2,
            l_max=l_max_cap,
            k_max=k_max_cap,
            k_leak=k_leak,
        )
        self.c1 = float(c1)
        self.c2 = float(c2)

        self.strategy_net = TraditionalStrategyNet(
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
            if v_prev.shape[1] == 2 * self.n_data:
                v_sym = 0.5 * (v_prev[:, :self.n_data] + v_prev[:, self.n_data:])
            else:
                v_sym = v_prev
            vx_feat = v_sym.float().mean(dim=-1, keepdim=True).clamp_min(1e-6)
        iter_denom = max(self.num_outer_iters - 1, 1)
        iter_frac = sigma_feat.new_full(
            (sigma_feat.shape[0], 1), float(iter_idx) / float(iter_denom)
        )
        return torch.cat([sigma_feat, residual_feat, support_ratio, vx_feat, iter_frac], dim=-1)

    def _build_pilot_sensing(self, x_pilot_c: np.ndarray) -> np.ndarray:
        return construct_sensing_matrix(
            self.n_total,
            x_pilot_c,
            self.c1,
            self.c2,
            self.atom_bank.l_max,
            self.atom_bank.k_max,
        )

    def _traditional_omp_init(
        self,
        y_flat: torch.Tensor,
        x_pilot_flat: torch.Tensor,
        atom_bank: SparseAtomBank | None = None,
    ) -> dict[str, torch.Tensor]:
        bank = atom_bank if atom_bank is not None else self.atom_bank
        y_c = block_to_complex(y_flat)
        x_p_c = block_to_complex(x_pilot_flat)
        bsz = y_flat.shape[0]
        q = bank.num_atoms
        hard_mask = y_flat.new_zeros(bsz, q)
        seed_mask = y_flat.new_zeros(bsz, q)
        gain_out = torch.zeros(bsz, q, dtype=torch.complex64, device=y_flat.device)

        for b in range(bsz):
            phi = self._build_pilot_sensing(x_p_c[b].detach().cpu().numpy())
            h_omp, support_idx = omp_sparse(
                y_c[b].detach().cpu().numpy(),
                phi,
                self.omp_n_paths,
            )
            seed_ids: list[int] = []
            exp_delays: list[int] = []
            exp_dopplers: list[int] = []
            exp_gains: list[complex] = []
            for idx in support_idx:
                g = h_omp[idx]
                l_dec = idx // bank.k_span
                k_dec = (idx % bank.k_span) - bank.k_max
                seed_ids.append(int(idx))
                for shift in range(-bank.k_leak, bank.k_leak + 1):
                    k_new = k_dec + shift
                    if abs(k_new) > bank.k_max:
                        continue
                    exp_delays.append(int(l_dec))
                    exp_dopplers.append(int(k_new))
                    exp_gains.append(g if shift == 0 else 0.0)

            if seed_ids:
                seed_mask[b, seed_ids] = 1.0
            if exp_delays:
                pairs = np.column_stack([exp_delays, exp_dopplers])
                gains_arr = np.asarray(exp_gains, dtype=np.complex64)
                unique_pairs, inverse = np.unique(pairs, axis=0, return_inverse=True)
                merged_gains = np.zeros(len(unique_pairs), dtype=np.complex64)
                np.add.at(merged_gains, inverse, gains_arr)
                for (delay_idx, doppler_idx), gain_val in zip(unique_pairs, merged_gains):
                    atom_idx = int(delay_idx) * bank.k_span + (int(doppler_idx) + bank.k_max)
                    hard_mask[b, atom_idx] = 1.0
                    gain_out[b, atom_idx] = torch.as_tensor(gain_val, dtype=torch.complex64, device=y_flat.device)

            if bool(hard_mask[b].sum().item() <= 0.5):
                fallback = bank.omp_init_support(
                    y_flat[b:b + 1],
                    x_pilot_flat[b:b + 1],
                    max_active_atoms=self.max_active_atoms,
                    lambda_ls=self.lambda_factor_anchor,
                )
                hard_mask[b:b + 1] = fallback["hard_mask"]
                seed_mask[b:b + 1] = fallback["seed_mask"]
                gain_out[b:b + 1] = torch.complex(
                    fallback["gain_flat"][:, :q],
                    fallback["gain_flat"][:, q:],
                )

        gain_flat = complex_to_block(gain_out)
        return {
            "hard_mask": hard_mask,
            "seed_mask": seed_mask,
            "gain_flat": gain_flat,
        }

    def _group_ridge_refit(
        self,
        y_flat: torch.Tensor,
        x_total_flat: torch.Tensor,
        support_mask: torch.Tensor,
        seed_mask: torch.Tensor,
        gain_prior_flat: torch.Tensor,
        lambda_ls: torch.Tensor,
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
            g_new_c = self.atom_bank._small_complex_ls(
                A,
                y_c[b],
                float(lambda_ls[b, 0].detach().cpu()),
                prior_sel=prior_sel,
                reg_diag=reg_diag,
            )
            gain_out[b, idx] = g_new_c
            residual = y_c[b] - A @ g_new_c
            sigma_ls[b, 0] = residual.abs().square().mean().real.float()

        gain_flat = complex_to_block(gain_out)
        h_flat = self.atom_bank.reconstruct(gain_flat, support_weight=support_mask)
        return {
            "gain_flat": gain_flat,
            "H_flat": h_flat,
            "sigma_ls": sigma_ls,
        }

    def _ridge_refit_single(
        self,
        y_c: torch.Tensor,
        x_total_c: torch.Tensor,
        support_idx: torch.Tensor,
        prior_sel_c: torch.Tensor,
        lambda_ls: torch.Tensor,
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
        g_new_r = torch.linalg.solve(lhs, rhs)

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

    def _hard_feedback(self, x_c: torch.Tensor) -> torch.Tensor:
        hard = _complex_sign(x_c, self.symbol_scale)
        if self.training:
            return x_c + (hard - x_c).detach()
        return hard

    def _apply_channel_sparsify(
        self,
        h_flat: torch.Tensor,
        sigma_eff: torch.Tensor,
    ) -> torch.Tensor:
        return self._apply_channel_sparsify_with_params(
            h_flat=h_flat,
            sigma_eff=sigma_eff,
            tau_h_factor=self.tau_h_factor,
            tau_h_sigma_factor=self.tau_h_sigma_factor,
        )

    def _apply_channel_sparsify_with_params(
        self,
        h_flat: torch.Tensor,
        sigma_eff: torch.Tensor,
        tau_h_factor: float,
        tau_h_sigma_factor: float,
    ) -> torch.Tensor:
        n = self.n_total
        h_r = h_flat[:, :n * n].reshape(-1, n, n)
        h_i = h_flat[:, n * n:].reshape(-1, n, n)
        h_c = torch.complex(h_r, h_i)
        max_h = h_c.abs().amax(dim=(1, 2), keepdim=True)
        tau_rel = float(tau_h_factor) * max_h
        tau_sigma = float(tau_h_sigma_factor) * torch.sqrt(sigma_eff.float().clamp_min(1e-12)).reshape(-1, 1, 1)
        tau = torch.maximum(tau_rel, tau_sigma)
        h_c = torch.where(h_c.abs() < tau, torch.zeros_like(h_c), h_c)
        return complex_to_block(h_c.reshape(h_c.shape[0], -1))

    def _pic_detect(
        self,
        h_flat: torch.Tensor,
        y_flat: torch.Tensor,
        xp_flat: torch.Tensor,
        sigma_eff: torch.Tensor,
        pic_damp: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        n = self.n_total
        h_r = h_flat[:, :n * n].reshape(-1, n, n)
        h_i = h_flat[:, n * n:].reshape(-1, n, n)
        h_c = torch.complex(h_r, h_i)
        y_c = block_to_complex(y_flat)
        xp_c = block_to_complex(xp_flat)
        h_d = h_c[:, :, self.data_pos]
        work_device = h_d.device
        if work_device.type == "mps":
            h_c = h_c.cpu()
            y_c = y_c.cpu()
            xp_c = xp_c.cpu()
            h_d = h_d.cpu()
            sigma_eff = sigma_eff.cpu()
            pic_damp = pic_damp.cpu()

        y_data = y_c - torch.bmm(h_c, xp_c.unsqueeze(-1)).squeeze(-1)
        h_power = h_d.abs().square().sum(dim=1).clamp_min(1e-10)
        sigma_sym = sigma_eff.float().reshape(-1, 1)
        inv_denom = 1.0 / (h_power + sigma_sym)

        x_mf = torch.bmm(h_d.conj().transpose(1, 2), y_data.unsqueeze(-1)).squeeze(-1)
        x_mf = x_mf * inv_denom
        x_hat = self._hard_feedback(x_mf)
        damp = pic_damp.float().reshape(-1, 1)

        for _ in range(self.pic_iters):
            r = y_data - torch.bmm(h_d, x_hat.unsqueeze(-1)).squeeze(-1)
            x_new = x_hat + torch.bmm(h_d.conj().transpose(1, 2), r.unsqueeze(-1)).squeeze(-1) * inv_denom
            x_hard = self._hard_feedback(x_new)
            x_hat = damp * x_hard + (1.0 - damp) * x_hat

        var_sym = sigma_sym / h_power.clamp_min(1e-10)
        if work_device.type == "mps":
            x_hat = x_hat.to(work_device)
            var_sym = var_sym.to(work_device)
        return x_hat, var_sym

    def _llr_from_detection(
        self,
        x_c: torch.Tensor,
        var_sym: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        var_cmp = (0.5 * var_sym).clamp_min(1e-6)
        llr_r = 2.0 * x_c.real.float() / var_cmp
        llr_i = 2.0 * x_c.imag.float() / var_cmp
        llr = torch.cat([llr_r, llr_i], dim=-1)
        v_flat = torch.cat([var_sym.float(), var_sym.float()], dim=-1)
        return llr, v_flat

    def forward(
        self,
        inp_feat: torch.Tensor,
        inp_y: torch.Tensor,
        inp_xp: torch.Tensor,
        inp_sigma: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        del inp_feat

        sigma_eff = inp_sigma.float().reshape(-1, 1)
        init = self._traditional_omp_init(inp_y, inp_xp)
        support_mask = init["hard_mask"].detach()
        seed_mask = init["seed_mask"].detach()
        gain_prev = init["gain_flat"]

        h_hat = inp_y.new_zeros(inp_y.shape[0], 2 * self.n_total * self.n_total)
        x_soft_prev = torch.zeros(
            inp_y.shape[0],
            self.n_data,
            dtype=torch.complex64,
            device=inp_y.device,
        )
        v_prev = None
        residual_energy_prev = block_to_complex(inp_y).abs().square().mean(dim=-1, keepdim=True)

        history: list[dict[str, torch.Tensor]] = []
        lambda_factor_hist = []
        lambda_hist = []
        gamma_h_hist = []
        gamma_x_hist = []
        pic_damp_hist = []

        for t in range(self.num_outer_iters):
            feat_t = self._strategy_features(
                sigma_eff=sigma_eff,
                residual_energy_prev=residual_energy_prev,
                support_mask=support_mask,
                v_prev=v_prev,
                iter_idx=t,
            )
            strat_t = self.strategy_net(feat_t)
            lambda_factor_t = strat_t["lambda_factor"]
            gamma_h_t = strat_t["gamma_h"]
            gamma_x_t = strat_t["gamma_x"]
            pic_damp_t = strat_t["pic_damp"]
            lambda_ls_t = (lambda_factor_t * sigma_eff).clamp_min(1e-6)

            if t == 0:
                x_total_refit = inp_xp
            else:
                x_fb_hard = self._hard_feedback(x_soft_prev)
                x_total_refit = inp_xp + embed_data_block(
                    complex_to_block(x_fb_hard), self.n_total, self.data_pos
                )

            refit_t = self._fixed_support_refit(
                y_flat=inp_y,
                x_total_flat=x_total_refit,
                support_mask=support_mask,
                gain_prior_flat=gain_prev,
                lambda_ls=lambda_ls_t,
            )
            gain_prev = refit_t["gain_flat"]
            h_new = refit_t["H_flat"]
            h_hat = (1.0 - gamma_h_t) * h_hat + gamma_h_t * h_new
            h_hat = self._apply_channel_sparsify(h_hat, sigma_eff)

            x_mp_c, var_sym = self._pic_detect(
                h_flat=h_hat,
                y_flat=inp_y,
                xp_flat=inp_xp,
                sigma_eff=sigma_eff,
                pic_damp=pic_damp_t,
            )
            x_soft_prev = (1.0 - gamma_x_t) * x_soft_prev + gamma_x_t * x_mp_c

            x_hard_stop = self._hard_feedback(x_soft_prev)
            x_total_stop = inp_xp + embed_data_block(
                complex_to_block(x_hard_stop), self.n_total, self.data_pos
            )
            y_hat = self.atom_bank.block_matvec(h_hat, x_total_stop)
            residual_c = block_to_complex(inp_y - y_hat)
            sigma_new = residual_c.abs().square().mean(dim=-1, keepdim=True)
            sigma_eff = (
                self.sigma_update_blend * sigma_eff
                + (1.0 - self.sigma_update_blend) * sigma_new
            )
            residual_energy_prev = sigma_new

            llr_t, v_flat = self._llr_from_detection(x_soft_prev, var_sym)
            det_t = complex_to_block(x_soft_prev)
            history.append(
                {
                    "detection": det_t,
                    "v_x": v_flat,
                    "llr": llr_t,
                    "H_flat": h_hat,
                    "gain_flat": gain_prev,
                    "sigma_eff": sigma_eff,
                    "sigma_ls": refit_t["sigma_ls"],
                    "residual_energy": residual_energy_prev,
                    "lambda_factor": lambda_factor_t,
                    "lambda_ls": lambda_ls_t,
                    "gamma_h": gamma_h_t,
                    "gamma_x": gamma_x_t,
                    "pic_damp": pic_damp_t,
                }
            )
            lambda_factor_hist.append(lambda_factor_t)
            lambda_hist.append(lambda_ls_t)
            gamma_h_hist.append(gamma_h_t)
            gamma_x_hist.append(gamma_x_t)
            pic_damp_hist.append(pic_damp_t)
            v_prev = v_flat

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
                "lambda_factor": torch.stack(lambda_factor_hist, dim=1),
                "lambda_ls": torch.stack(lambda_hist, dim=1),
                "gamma_h": torch.stack(gamma_h_hist, dim=1),
                "gamma_x": torch.stack(gamma_x_hist, dim=1),
                "pic_damp": torch.stack(pic_damp_hist, dim=1),
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
        atom_bank = self._make_atom_bank(overrides.get("k_leak"), inp_y.device)
        sigma_eff = inp_sigma.float().reshape(-1, 1)
        init = self._traditional_omp_init(inp_y, inp_xp, atom_bank=atom_bank)
        support_mask = init["hard_mask"].detach()
        seed_mask = init["seed_mask"].detach()
        gain_prev = init["gain_flat"]

        h_hat = inp_y.new_zeros(inp_y.shape[0], 2 * self.n_total * self.n_total)
        x_soft_prev = torch.zeros(
            inp_y.shape[0],
            self.n_data,
            dtype=torch.complex64,
            device=inp_y.device,
        )
        v_prev = None
        residual_energy_prev = block_to_complex(inp_y).abs().square().mean(dim=-1, keepdim=True)

        history: list[dict[str, torch.Tensor]] = []
        lambda_factor_hist = []
        lambda_hist = []
        gamma_h_hist = []
        gamma_x_hist = []
        pic_damp_hist = []
        anchor_lambda_factor_hist = []
        anchor_lambda_hist = []
        anchor_gamma_h_hist = []
        anchor_gamma_x_hist = []
        anchor_pic_damp_hist = []
        detector_sigma_hist = []

        sigma_blend = float(overrides.get("sigma_update_blend", self.sigma_update_blend))
        tau_h_factor = float(overrides.get("tau_h_factor", self.tau_h_factor))
        tau_h_sigma_factor = float(overrides.get("tau_h_sigma_factor", self.tau_h_sigma_factor))

        for t in range(self.num_outer_iters):
            feat_t = self._strategy_features(
                sigma_eff=sigma_eff,
                residual_energy_prev=residual_energy_prev,
                support_mask=support_mask,
                v_prev=v_prev,
                iter_idx=t,
            )
            strat_t = self.strategy_net(feat_t)
            anchor_raw = strat_t["anchor_raw"]
            anchor_lambda_factor = F.softplus(anchor_raw[:, 0:1])
            anchor_gamma_h = torch.sigmoid(anchor_raw[:, 1:2])
            anchor_gamma_x = torch.sigmoid(anchor_raw[:, 2:3])
            anchor_pic_damp = torch.sigmoid(anchor_raw[:, 3:4])

            lambda_factor_t = strat_t["lambda_factor"]
            gamma_h_t = strat_t["gamma_h"]
            gamma_x_t = strat_t["gamma_x"]
            pic_damp_t = strat_t["pic_damp"]

            if "lambda_factor_scale" in overrides:
                lambda_factor_t = lambda_factor_t * _as_override_tensor(
                    overrides["lambda_factor_scale"],
                    lambda_factor_t,
                    clamp_min=1e-6,
                )
            if "lambda_factor" in overrides:
                lambda_factor_t = _as_override_tensor(
                    overrides["lambda_factor"],
                    lambda_factor_t,
                    clamp_min=1e-6,
                )
            if "gamma_h" in overrides:
                gamma_h_t = _as_override_tensor(overrides["gamma_h"], gamma_h_t, clamp_min=0.0, clamp_max=1.0)
            if "gamma_x" in overrides:
                gamma_x_t = _as_override_tensor(overrides["gamma_x"], gamma_x_t, clamp_min=0.0, clamp_max=1.0)
            if "pic_damp" in overrides:
                pic_damp_t = _as_override_tensor(overrides["pic_damp"], pic_damp_t, clamp_min=0.0, clamp_max=1.0)

            lambda_ls_t = (lambda_factor_t * sigma_eff).clamp_min(1e-6)
            anchor_lambda_ls = (anchor_lambda_factor * sigma_eff).clamp_min(1e-6)

            if t == 0:
                x_total_refit = inp_xp
            else:
                x_fb_hard = self._hard_feedback(x_soft_prev)
                x_total_refit = inp_xp + embed_data_block(
                    complex_to_block(x_fb_hard), self.n_total, self.data_pos
                )

            if ("seed_mult" in overrides) or ("expand_mult" in overrides):
                seed_mult = self._expand_group_param(overrides.get("seed_mult"), lambda_ls_t, 1.0)
                expand_mult = self._expand_group_param(overrides.get("expand_mult"), lambda_ls_t, 1.0)
                refit_t = self._group_ridge_refit(
                    y_flat=inp_y,
                    x_total_flat=x_total_refit,
                    support_mask=support_mask,
                    seed_mask=seed_mask,
                    gain_prior_flat=gain_prev,
                    lambda_ls=lambda_ls_t,
                    seed_mult=seed_mult,
                    expand_mult=expand_mult,
                )
            else:
                refit_t = self._fixed_support_refit(
                    y_flat=inp_y,
                    x_total_flat=x_total_refit,
                    support_mask=support_mask,
                    gain_prior_flat=gain_prev,
                    lambda_ls=lambda_ls_t,
                )
            gain_prev = refit_t["gain_flat"]
            h_new = refit_t["H_flat"]
            h_hat = (1.0 - gamma_h_t) * h_hat + gamma_h_t * h_new
            h_hat = self._apply_channel_sparsify_with_params(
                h_flat=h_hat,
                sigma_eff=sigma_eff,
                tau_h_factor=tau_h_factor,
                tau_h_sigma_factor=tau_h_sigma_factor,
            )

            detector_sigma = sigma_eff
            if "detector_sigma_inflation" in overrides:
                detector_sigma = detector_sigma * _as_override_tensor(
                    overrides["detector_sigma_inflation"],
                    detector_sigma,
                    clamp_min=1e-6,
                )

            x_mp_c, var_sym = self._pic_detect(
                h_flat=h_hat,
                y_flat=inp_y,
                xp_flat=inp_xp,
                sigma_eff=detector_sigma,
                pic_damp=pic_damp_t,
            )
            x_soft_prev = (1.0 - gamma_x_t) * x_soft_prev + gamma_x_t * x_mp_c

            x_hard_stop = self._hard_feedback(x_soft_prev)
            x_total_stop = inp_xp + embed_data_block(
                complex_to_block(x_hard_stop), self.n_total, self.data_pos
            )
            y_hat = self.atom_bank.block_matvec(h_hat, x_total_stop)
            residual_c = block_to_complex(inp_y - y_hat)
            sigma_new = residual_c.abs().square().mean(dim=-1, keepdim=True)
            sigma_eff = (
                sigma_blend * sigma_eff
                + (1.0 - sigma_blend) * sigma_new
            )
            residual_energy_prev = sigma_new

            llr_t, v_flat = self._llr_from_detection(x_soft_prev, var_sym)
            det_t = complex_to_block(x_soft_prev)
            history.append(
                {
                    "detection": det_t,
                    "v_x": v_flat,
                    "llr": llr_t,
                    "H_flat": h_hat,
                    "gain_flat": gain_prev,
                    "sigma_eff": sigma_eff,
                    "sigma_ls": refit_t["sigma_ls"],
                    "residual_energy": residual_energy_prev,
                    "lambda_factor": lambda_factor_t,
                    "lambda_ls": lambda_ls_t,
                    "gamma_h": gamma_h_t,
                    "gamma_x": gamma_x_t,
                    "pic_damp": pic_damp_t,
                    "anchor_lambda_factor": anchor_lambda_factor,
                    "anchor_lambda_ls": anchor_lambda_ls,
                    "anchor_gamma_h": anchor_gamma_h,
                    "anchor_gamma_x": anchor_gamma_x,
                    "anchor_pic_damp": anchor_pic_damp,
                    "detector_sigma": detector_sigma,
                }
            )
            lambda_factor_hist.append(lambda_factor_t)
            lambda_hist.append(lambda_ls_t)
            gamma_h_hist.append(gamma_h_t)
            gamma_x_hist.append(gamma_x_t)
            pic_damp_hist.append(pic_damp_t)
            anchor_lambda_factor_hist.append(anchor_lambda_factor)
            anchor_lambda_hist.append(anchor_lambda_ls)
            anchor_gamma_h_hist.append(anchor_gamma_h)
            anchor_gamma_x_hist.append(anchor_gamma_x)
            anchor_pic_damp_hist.append(anchor_pic_damp)
            detector_sigma_hist.append(detector_sigma)
            v_prev = v_flat

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
                "lambda_factor": torch.stack(lambda_factor_hist, dim=1),
                "lambda_ls": torch.stack(lambda_hist, dim=1),
                "gamma_h": torch.stack(gamma_h_hist, dim=1),
                "gamma_x": torch.stack(gamma_x_hist, dim=1),
                "pic_damp": torch.stack(pic_damp_hist, dim=1),
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
                    "lambda_factor": torch.stack(anchor_lambda_factor_hist, dim=1),
                    "lambda_ls": torch.stack(anchor_lambda_hist, dim=1),
                    "gamma_h": torch.stack(anchor_gamma_h_hist, dim=1),
                    "gamma_x": torch.stack(anchor_gamma_x_hist, dim=1),
                    "pic_damp": torch.stack(anchor_pic_damp_hist, dim=1),
                },
                "param_delta_history": {
                    "lambda_factor": torch.stack(lambda_factor_hist, dim=1) - torch.stack(anchor_lambda_factor_hist, dim=1),
                    "lambda_ls": torch.stack(lambda_hist, dim=1) - torch.stack(anchor_lambda_hist, dim=1),
                    "gamma_h": torch.stack(gamma_h_hist, dim=1) - torch.stack(anchor_gamma_h_hist, dim=1),
                    "gamma_x": torch.stack(gamma_x_hist, dim=1) - torch.stack(anchor_gamma_x_hist, dim=1),
                    "pic_damp": torch.stack(pic_damp_hist, dim=1) - torch.stack(anchor_pic_damp_hist, dim=1),
                },
                "detector_sigma_history": torch.stack(detector_sigma_hist, dim=1),
                "seed_mask": seed_part,
                "expanded_only_mask": expanded_only_mask,
                "overrides": {
                    k: v for k, v in overrides.items()
                },
            },
            "learned_param_set": self.learned_param_set,
        }


def build_traditional_param_model(
    input_dim: int,
    n_total: int,
    c1: float,
    c2: float,
    l_max_cap: int,
    k_max_cap: int,
    rho: float,
    data_positions: np.ndarray | torch.Tensor,
    num_outer_iters: int = 5,
    pic_iters: int = 15,
    max_active_atoms: int = 25,
    k_leak: int = 2,
    use_strategy_net: bool = True,
    learned_param_set: str = "classical_full",
) -> TraditionalParamJointReceiver:
    del input_dim
    return TraditionalParamJointReceiver(
        n_total=n_total,
        c1=c1,
        c2=c2,
        l_max_cap=l_max_cap,
        k_max_cap=k_max_cap,
        rho=rho,
        data_positions=data_positions,
        num_outer_iters=num_outer_iters,
        pic_iters=pic_iters,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        use_strategy_net=use_strategy_net,
        learned_param_set=learned_param_set,
    )


compute_traditional_param_loss = compute_param_joint_loss


__all__ = [
    "TraditionalParamJointReceiver",
    "TraditionalStrategyNet",
    "TraditionalParamLossStats",
    "VALID_TRAD_PARAM_SETS",
    "build_traditional_param_model",
    "compute_traditional_param_loss",
    "extract_data_block",
    "ber_from_detection",
]
