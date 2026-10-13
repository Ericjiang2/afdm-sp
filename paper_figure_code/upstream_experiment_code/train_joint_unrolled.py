"""
train_joint_unrolled.py

Train the model-driven sparse joint receiver in three stages:
  1. support/gain warmup on trajectory teacher iter-0
  2. detector warmup with teacher-forced sparse state
  3. short joint fine-tuning with partial teacher forcing
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import random
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch.utils.data import DataLoader, Sampler, TensorDataset

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_joint_unrolled.afdm_joint_unrolled import (
    build_joint_unrolled_model,
    compute_joint_unrolled_loss,
    extract_data_block,
    ber_from_detection,
)
from afdm_sp_joint_unrolled.prepare_teacher_sparse import (
    load_or_prepare_teacher_cache,
    make_system_n512,
    _load_stats,
)


def _set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _maybe_enable_tf32(enable: bool):
    if not enable or not torch.cuda.is_available():
        return
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    torch.set_float32_matmul_precision("high")


def _align_data_tensor(t: torch.Tensor, data_pos: torch.Tensor,
                       n_total: int) -> torch.Tensor:
    if t.shape[1] == 2 * data_pos.numel():
        return t
    if t.shape[1] == 2 * n_total:
        return extract_data_block(t, data_pos)
    raise ValueError(
        f"Unexpected tensor width={t.shape[1]} for n_total={n_total}, "
        f"n_data={data_pos.numel()}"
    )


def _to_device_batch(batch, device):
    return tuple(x.to(device, non_blocking=True) for x in batch)


class _ContrastiveBatchSampler(Sampler[list[int]]):
    def __init__(self, low_idx: np.ndarray, high_idx: np.ndarray,
                 batch_size: int, seed: int):
        if batch_size % 2 != 0:
            raise ValueError("contrastive batch_size 必须是偶数")
        self.low_idx = np.asarray(low_idx, dtype=np.int64)
        self.high_idx = np.asarray(high_idx, dtype=np.int64)
        self.batch_size = int(batch_size)
        self.seed = int(seed)
        self.epoch = 0

    def __len__(self) -> int:
        half = self.batch_size // 2
        return min(len(self.low_idx) // half, len(self.high_idx) // half)

    def __iter__(self):
        half = self.batch_size // 2
        rng = np.random.default_rng(self.seed + self.epoch)
        self.epoch += 1
        low = rng.permutation(self.low_idx)
        high = rng.permutation(self.high_idx)
        n_batches = len(self)
        for batch_id in range(n_batches):
            lo = low[batch_id * half:(batch_id + 1) * half]
            hi = high[batch_id * half:(batch_id + 1) * half]
            batch = np.concatenate([lo, hi], axis=0)
            rng.shuffle(batch)
            yield batch.tolist()


def _make_loaders(cache: dict, batch_size: int, val_batch_size: int,
                  val_split: float, num_workers: int, seed: int,
                  keep_snr: list[int] | None = None,
                  exact_contrastive: bool = False):
    required = [
        "support_teacher_iter",
        "seed_teacher_iter",
        "gain_teacher_iter",
        "cluster_mask_teacher_iter",
        "leakage_teacher_iter",
        "mu_x_teacher_iter",
        "var_x_teacher_iter",
        "llr_teacher_iter",
    ]
    missing = [key for key in required if key not in cache]
    if missing:
        raise RuntimeError(
            "teacher 粒度不足：当前 cache 缺少 trajectory 字段 "
            f"{missing}。请重新生成 trajectory-aware teacher cache。"
        )

    x_feat = cache["X_features"].float()
    y_recv = cache["y_received"].float()
    x_pil = cache["x_pilot_frames"].float()
    x_true = cache["x_data_true"].float()
    bits_true = cache["bits_true"].float()
    sigma = cache["sigma_w2"].float()
    snr_db = cache["snr_db"].float().reshape(-1)
    mu_t = cache["mu_x_teacher_iter"].float()
    var_t = cache["var_x_teacher_iter"].float()
    llr_t = cache["llr_teacher_iter"].float()
    support_t = cache["support_teacher_iter"].float()
    seed_t = cache["seed_teacher_iter"].float()
    gain_t = cache["gain_teacher_iter"].float()
    cluster_t = cache["cluster_mask_teacher_iter"].float()
    leakage_t = cache["leakage_teacher_iter"].float()
    data_pos = cache["data_positions"].long()
    n_total = int(cache["meta"]["n_total"])

    x_true = _align_data_tensor(x_true, data_pos, n_total)
    bits_true = _align_data_tensor(bits_true, data_pos, n_total)
    mu_t = torch.stack([
        _align_data_tensor(mu_t[:, t], data_pos, n_total)
        for t in range(mu_t.shape[1])
    ], dim=1)
    var_t = torch.stack([
        _align_data_tensor(var_t[:, t], data_pos, n_total)
        for t in range(var_t.shape[1])
    ], dim=1)
    llr_t = torch.stack([
        _align_data_tensor(llr_t[:, t], data_pos, n_total)
        for t in range(llr_t.shape[1])
    ], dim=1)

    n = x_feat.shape[0]
    idx = np.arange(n)
    if keep_snr:
        keep_vals = np.asarray(keep_snr, dtype=np.float32)
        idx = idx[np.isin(snr_db.cpu().numpy(), keep_vals)]
    if idx.size == 0:
        raise RuntimeError(f"没有样本匹配 keep_snr={keep_snr}")
    rng = np.random.default_rng(seed)
    rng.shuffle(idx)
    n_val = max(1, int(round(n * val_split)))
    val_idx = idx[:n_val]
    tr_idx = idx[n_val:]

    def _slice(ids):
        ids_t = torch.from_numpy(np.asarray(ids, dtype=np.int64))
        return (
            x_feat[ids_t], y_recv[ids_t], x_pil[ids_t], sigma[ids_t],
            x_true[ids_t], bits_true[ids_t], mu_t[ids_t], var_t[ids_t],
            llr_t[ids_t], support_t[ids_t], seed_t[ids_t], gain_t[ids_t],
            cluster_t[ids_t], leakage_t[ids_t], snr_db[ids_t],
        )

    loader_kw = {
        "num_workers": num_workers,
        "pin_memory": torch.cuda.is_available(),
    }
    if num_workers > 0:
        loader_kw["persistent_workers"] = True

    if exact_contrastive and keep_snr and len(keep_snr) == 2:
        low_snr, high_snr = [float(v) for v in keep_snr]
        low_all = idx[np.isclose(snr_db[idx].cpu().numpy(), low_snr)]
        high_all = idx[np.isclose(snr_db[idx].cpu().numpy(), high_snr)]
        if low_all.size == 0 or high_all.size == 0:
            raise RuntimeError("contrastive hard_finetune 需要同时包含 low/high SNR 样本")
        rng = np.random.default_rng(seed)
        rng.shuffle(low_all)
        rng.shuffle(high_all)
        low_val_n = max(1, int(round(low_all.size * val_split)))
        high_val_n = max(1, int(round(high_all.size * val_split)))
        low_val, low_tr = low_all[:low_val_n], low_all[low_val_n:]
        high_val, high_tr = high_all[:high_val_n], high_all[high_val_n:]
        tr_ids = np.concatenate([low_tr, high_tr], axis=0)
        val_ids = np.concatenate([low_val, high_val], axis=0)
        tr_ds = TensorDataset(*_slice(tr_ids))
        va_ds = TensorDataset(*_slice(val_ids))
        low_local = np.arange(len(low_tr), dtype=np.int64)
        high_local = np.arange(len(low_tr), len(tr_ids), dtype=np.int64)
        batch_sampler = _ContrastiveBatchSampler(low_local, high_local, batch_size, seed)
        tr_loader = DataLoader(tr_ds, batch_sampler=batch_sampler, **loader_kw)
    else:
        tr_ds = TensorDataset(*_slice(tr_idx))
        va_ds = TensorDataset(*_slice(val_idx))
        tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True, **loader_kw)

    va_loader = DataLoader(va_ds, batch_size=val_batch_size, shuffle=False, **loader_kw)
    return tr_loader, va_loader


def _phase_weight_config(
    phase_name: str,
    receiver_variant: str = "baseline",
    detector_prior_variant: str = "baseline",
):
    is_distill_iter0 = detector_prior_variant == "distill_sd_v1"
    if phase_name == "support_warmup":
        return dict(
            lambda_bits=0.0,
            lambda_kd=0.0,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.0,
            lambda_leakage_profile=0.0,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.0,
            lambda_vx=0.0,
            lambda_gain=0.5,
            lambda_obs=0.2,
            lambda_sym=0.0,
        )
    if phase_name == "prior_warmup":
        return dict(
            lambda_bits=0.0,
            lambda_kd=0.0,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.0,
            lambda_leakage_profile=0.0,
            lambda_pnp_delta=0.05,
            lambda_pnp_identity=0.02,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.0,
            lambda_det_prior_vx=0.0,
            lambda_det_prior_identity=0.0,
            lambda_vx=0.15,
            lambda_gain=0.4,
            lambda_obs=0.15,
            lambda_sym=0.0,
        )
    if phase_name == "detector_prior_distill_warmup":
        return dict(
            lambda_bits=0.0,
            lambda_kd=0.0,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.0,
            lambda_leakage_profile=0.0,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=1.0,
            lambda_det_prior_sym=0.0,
            lambda_det_prior_vx=0.0,
            lambda_det_prior_identity=0.0,
            lambda_vx=0.05,
            lambda_gain=0.10,
            lambda_obs=0.05,
            lambda_sym=0.05,
        )
    if phase_name == "detector_prior_warmup":
        return dict(
            lambda_bits=0.0,
            lambda_kd=0.3,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.0,
            lambda_leakage_profile=0.0,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.45,
            lambda_det_prior_vx=0.20,
            lambda_det_prior_identity=0.16,
            lambda_vx=0.08,
            lambda_gain=0.15,
            lambda_obs=0.08,
            lambda_sym=0.10,
        )
    if phase_name == "leakage_warmup":
        return dict(
            lambda_bits=0.0,
            lambda_kd=0.0,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.3,
            lambda_leakage_profile=0.2,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.0,
            lambda_det_prior_vx=0.0,
            lambda_det_prior_identity=0.0,
            lambda_vx=0.0,
            lambda_gain=0.4,
            lambda_obs=0.15,
            lambda_sym=0.0,
        )
    if phase_name == "detector_warmup":
        if is_distill_iter0:
            return dict(
                lambda_bits=0.0,
                lambda_kd=0.6,
                lambda_seed=0.02,
                lambda_support=0.02,
                lambda_cluster_mask=0.0,
                lambda_leakage_profile=0.0,
                lambda_pnp_delta=0.0,
                lambda_pnp_identity=0.0,
                lambda_det_prior_delta=0.6,
                lambda_det_prior_sym=0.0,
                lambda_det_prior_vx=0.0,
                lambda_det_prior_identity=0.0,
                lambda_vx=0.05,
                lambda_gain=0.15,
                lambda_obs=0.05,
                lambda_sym=0.20,
            )
        if receiver_variant == "pnp_prior":
            return dict(
                lambda_bits=0.0,
                lambda_kd=1.0,
                lambda_seed=0.02,
                lambda_support=0.02,
                lambda_cluster_mask=0.0,
                lambda_leakage_profile=0.0,
                lambda_pnp_delta=0.03,
                lambda_pnp_identity=0.015,
                lambda_det_prior_delta=0.0,
                lambda_det_prior_sym=0.10,
                lambda_det_prior_vx=0.06,
                lambda_det_prior_identity=0.08,
                lambda_vx=0.10,
                lambda_gain=0.2,
                lambda_obs=0.05,
                lambda_sym=0.5,
            )
        return dict(
            lambda_bits=0.0,
            lambda_kd=1.0,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.15,
            lambda_leakage_profile=0.1,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.10,
            lambda_det_prior_vx=0.05,
            lambda_det_prior_identity=0.08,
            lambda_vx=0.05,
            lambda_gain=0.2,
            lambda_obs=0.05,
            lambda_sym=0.5,
        )
    if phase_name == "hard_finetune":
        if is_distill_iter0:
            return dict(
                lambda_bits=0.9,
                lambda_kd=0.2,
                lambda_seed=0.0,
                lambda_support=0.0,
                lambda_cluster_mask=0.0,
                lambda_leakage_profile=0.0,
                lambda_pnp_delta=0.0,
                lambda_pnp_identity=0.0,
                lambda_det_prior_delta=0.25,
                lambda_det_prior_sym=0.0,
                lambda_det_prior_vx=0.0,
                lambda_det_prior_identity=0.0,
                lambda_vx=0.05,
                lambda_gain=0.30,
                lambda_obs=0.10,
                lambda_sym=0.05,
            )
        if receiver_variant == "pnp_prior":
            return dict(
                lambda_bits=0.9,
                lambda_kd=0.3,
                lambda_seed=0.0,
                lambda_support=0.0,
                lambda_cluster_mask=0.0,
                lambda_leakage_profile=0.0,
                lambda_pnp_delta=0.02,
                lambda_pnp_identity=0.02,
                lambda_det_prior_delta=0.0,
                lambda_det_prior_sym=0.08,
                lambda_det_prior_vx=0.04,
                lambda_det_prior_identity=0.08,
                lambda_vx=0.05,
                lambda_gain=0.35,
                lambda_obs=0.12,
                lambda_sym=0.05,
            )
        return dict(
            lambda_bits=0.9,
            lambda_kd=0.3,
            lambda_seed=0.0,
            lambda_support=0.0,
            lambda_cluster_mask=0.08,
            lambda_leakage_profile=0.05,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.08,
            lambda_det_prior_vx=0.04,
            lambda_det_prior_identity=0.08,
            lambda_vx=0.05,
            lambda_gain=0.35,
            lambda_obs=0.12,
            lambda_sym=0.05,
        )
    if is_distill_iter0:
        return dict(
            lambda_bits=0.4,
            lambda_kd=0.4,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.1,
            lambda_leakage_profile=0.08,
            lambda_pnp_delta=0.0,
            lambda_pnp_identity=0.0,
            lambda_det_prior_delta=0.4,
            lambda_det_prior_sym=0.0,
            lambda_det_prior_vx=0.0,
            lambda_det_prior_identity=0.0,
            lambda_vx=0.05,
            lambda_gain=0.3,
            lambda_obs=0.08,
            lambda_sym=0.05,
        )
    if receiver_variant == "pnp_prior":
        return dict(
            lambda_bits=0.6,
            lambda_kd=0.6,
            lambda_seed=0.02,
            lambda_support=0.02,
            lambda_cluster_mask=0.0,
            lambda_leakage_profile=0.0,
            lambda_pnp_delta=0.02,
            lambda_pnp_identity=0.02,
            lambda_det_prior_delta=0.0,
            lambda_det_prior_sym=0.06,
            lambda_det_prior_vx=0.03,
            lambda_det_prior_identity=0.06,
            lambda_vx=0.08,
            lambda_gain=0.3,
            lambda_obs=0.1,
            lambda_sym=0.05,
        )
    return dict(
        lambda_bits=0.6,
        lambda_kd=0.6,
        lambda_seed=0.02,
        lambda_support=0.02,
        lambda_cluster_mask=0.1,
        lambda_leakage_profile=0.08,
        lambda_pnp_delta=0.0,
        lambda_pnp_identity=0.0,
        lambda_det_prior_delta=0.0,
        lambda_det_prior_sym=0.06,
        lambda_det_prior_vx=0.03,
        lambda_det_prior_identity=0.06,
        lambda_vx=0.05,
        lambda_gain=0.3,
        lambda_obs=0.1,
        lambda_sym=0.05,
    )


def _phase_runtime_config(phase_name: str):
    if phase_name == "support_warmup":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 0.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": 1,
            "eval_outer_iters": 1,
            "freeze_mode": "support",
            "select_best_on": "free",
        }
    if phase_name == "leakage_warmup":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 0.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": 1,
            "eval_outer_iters": 1,
            "freeze_mode": "leakage",
            "select_best_on": "free",
        }
    if phase_name == "prior_warmup":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 0.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": 1,
            "eval_outer_iters": 1,
            "freeze_mode": "prior",
            "select_best_on": "free",
        }
    if phase_name == "detector_prior_warmup":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 0.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": None,
            "eval_outer_iters": None,
            "freeze_mode": "detector_prior",
            "select_best_on": "free",
        }
    if phase_name == "detector_prior_distill_warmup":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 0.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": None,
            "eval_outer_iters": None,
            "freeze_mode": "detector_prior_distill",
            "select_best_on": "free",
        }
    if phase_name == "detector_warmup":
        return {
            "teacher_force_start": 0.3,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 1.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": None,
            "eval_outer_iters": None,
            "freeze_mode": "detector",
            "select_best_on": "oracle",
        }
    if phase_name == "hard_finetune":
        return {
            "teacher_force_start": 0.0,
            "teacher_force_end": 0.0,
            "eval_teacher_force_oracle": 1.0,
            "eval_teacher_force_free": 0.0,
            "max_outer_iters": None,
            "eval_outer_iters": None,
            "freeze_mode": "joint",
            "select_best_on": "free",
        }
    return {
        "teacher_force_start": 0.2,
        "teacher_force_end": 0.0,
        "eval_teacher_force_oracle": 1.0,
        "eval_teacher_force_free": 0.0,
        "max_outer_iters": None,
        "eval_outer_iters": None,
        "freeze_mode": "joint",
        "select_best_on": "free",
    }


def _set_phase_trainability(model, phase_name: str,
                            epoch: int | None = None,
                            total_epochs: int | None = None):
    def _enable_detector_prior_v2_heads_only() -> None:
        refiner = getattr(model, "detector_prior_refiner", None)
        if refiner is None:
            return
        for p in refiner.parameters():
            p.requires_grad = False
        for head_name in ("delta_x_head", "delta_v_head"):
            head = getattr(refiner, head_name, None)
            if head is not None:
                for p in head.parameters():
                    p.requires_grad = True

    def _enable_detector_prior_distill_v1() -> None:
        refiner = getattr(model, "detector_prior_refiner", None)
        if refiner is None:
            return
        for p in refiner.parameters():
            p.requires_grad = False
        for mod_name in ("stem", "stem_bn", "blocks", "delta_x_head"):
            mod = getattr(refiner, mod_name, None)
            if mod is not None:
                for p in mod.parameters():
                    p.requires_grad = True
        head = getattr(refiner, "delta_v_head", None)
        if head is not None:
            for p in head.parameters():
                p.requires_grad = False

    for p in model.parameters():
        p.requires_grad = False

    if phase_name == "support_warmup":
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "analytic_support_scalars"

    if phase_name == "prior_warmup":
        if getattr(model, "receiver_variant", "baseline") == "pnp_prior":
            if hasattr(model.proposal, "mlp"):
                for p in model.proposal.mlp.parameters():
                    p.requires_grad = True
            for head_name in ("seed_head", "support_head", "gain_head", "norm"):
                mod = getattr(model.proposal, head_name, None)
                if mod is not None:
                    for p in mod.parameters():
                        p.requires_grad = True
            if getattr(model, "pnp_denoiser", None) is not None:
                for p in model.pnp_denoiser.parameters():
                    p.requires_grad = True
            if hasattr(model, "pnp_mix_raw"):
                model.pnp_mix_raw.requires_grad = True
            if getattr(model, "pnp_mix_controller", None) is not None:
                for p in model.pnp_mix_controller.parameters():
                    p.requires_grad = True
        if hasattr(model, "uncert_scale_raw"):
            model.uncert_scale_raw.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "proposal_pnp_prior" if getattr(model, "receiver_variant", "baseline") == "pnp_prior" else "uncertainty_adapter"

    if phase_name == "detector_prior_warmup":
        if getattr(model, "detector_prior_refiner", None) is not None:
            if getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v1":
                for p in model.detector_prior_refiner.parameters():
                    p.requires_grad = True
            elif getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v2":
                _enable_detector_prior_v2_heads_only()
        if hasattr(model, "detector_prior_gamma_raw"):
            model.detector_prior_gamma_raw.requires_grad = True
        if getattr(model, "detector_prior_gamma_controller", None) is not None:
            for p in model.detector_prior_gamma_controller.parameters():
                p.requires_grad = True
        if hasattr(model, "uncert_scale_raw") and getattr(model, "uncertainty_variant", "baseline") != "baseline":
            model.uncert_scale_raw.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "detector_pnp_prior"

    if phase_name == "detector_prior_distill_warmup":
        if getattr(model, "detector_prior_variant", "baseline") == "distill_sd_v1":
            _enable_detector_prior_distill_v1()
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "detector_prior_distill"

    if phase_name == "leakage_warmup":
        if hasattr(model.proposal, "mlp"):
            for p in model.proposal.mlp.parameters():
                p.requires_grad = True
        for head_name in ("seed_head", "support_head", "gain_head", "norm"):
            mod = getattr(model.proposal, head_name, None)
            if mod is not None:
                for p in mod.parameters():
                    p.requires_grad = True
        if getattr(model, "leakage_refiner", None) is not None:
            for p in model.leakage_refiner.parameters():
                p.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "proposal_leakage"

    if phase_name == "detector_warmup":
        for detector in model.detectors:
            for p in detector.parameters():
                p.requires_grad = True
        if getattr(model, "leakage_refiner", None) is not None:
            for p in model.leakage_refiner.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_denoiser", None) is not None:
            for p in model.pnp_denoiser.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_mix_controller", None) is not None:
            for p in model.pnp_mix_controller.parameters():
                p.requires_grad = True
        if hasattr(model, "pnp_mix_raw"):
            model.pnp_mix_raw.requires_grad = True
        if hasattr(model, "uncert_scale_raw"):
            model.uncert_scale_raw.requires_grad = True
        if getattr(model, "detector_prior_refiner", None) is not None:
            if getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v1":
                for p in model.detector_prior_refiner.parameters():
                    p.requires_grad = True
            elif getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v2":
                _enable_detector_prior_v2_heads_only()
            elif getattr(model, "detector_prior_variant", "baseline") == "distill_sd_v1":
                _enable_detector_prior_distill_v1()
        if hasattr(model, "detector_prior_gamma_raw") and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            model.detector_prior_gamma_raw.requires_grad = True
        if getattr(model, "detector_prior_gamma_controller", None) is not None and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            for p in model.detector_prior_gamma_controller.parameters():
                p.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "detectors_scalars"

    if phase_name == "joint_finetune" and epoch is not None and total_epochs is not None:
        for detector in model.detectors:
            for p in detector.parameters():
                p.requires_grad = True
        if getattr(model, "leakage_refiner", None) is not None:
            for p in model.leakage_refiner.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_denoiser", None) is not None:
            for p in model.pnp_denoiser.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_mix_controller", None) is not None:
            for p in model.pnp_mix_controller.parameters():
                p.requires_grad = True
        if hasattr(model, "pnp_mix_raw"):
            model.pnp_mix_raw.requires_grad = True
        if hasattr(model, "uncert_scale_raw"):
            model.uncert_scale_raw.requires_grad = True
        if getattr(model, "detector_prior_refiner", None) is not None:
            if getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v1":
                for p in model.detector_prior_refiner.parameters():
                    p.requires_grad = True
            elif getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v2":
                _enable_detector_prior_v2_heads_only()
            elif getattr(model, "detector_prior_variant", "baseline") == "distill_sd_v1":
                _enable_detector_prior_distill_v1()
        if hasattr(model, "detector_prior_gamma_raw") and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            model.detector_prior_gamma_raw.requires_grad = True
        if getattr(model, "detector_prior_gamma_controller", None) is not None and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            for p in model.detector_prior_gamma_controller.parameters():
                p.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "joint_fixed_support"

    if phase_name == "hard_finetune":
        for detector in model.detectors:
            for p in detector.parameters():
                p.requires_grad = True
        if getattr(model, "leakage_refiner", None) is not None:
            for p in model.leakage_refiner.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_denoiser", None) is not None:
            for p in model.pnp_denoiser.parameters():
                p.requires_grad = True
        if getattr(model, "pnp_mix_controller", None) is not None:
            for p in model.pnp_mix_controller.parameters():
                p.requires_grad = True
        if hasattr(model, "pnp_mix_raw"):
            model.pnp_mix_raw.requires_grad = True
        if hasattr(model, "uncert_scale_raw"):
            model.uncert_scale_raw.requires_grad = True
        if getattr(model, "detector_prior_refiner", None) is not None:
            if getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v1":
                for p in model.detector_prior_refiner.parameters():
                    p.requires_grad = True
            elif getattr(model, "detector_prior_variant", "baseline") == "pnp_sd_v2":
                _enable_detector_prior_v2_heads_only()
            elif getattr(model, "detector_prior_variant", "baseline") == "distill_sd_v1":
                _enable_detector_prior_distill_v1()
        if hasattr(model, "detector_prior_gamma_raw") and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            model.detector_prior_gamma_raw.requires_grad = True
        if getattr(model, "detector_prior_gamma_controller", None) is not None and getattr(model, "detector_prior_variant", "baseline") != "distill_sd_v1":
            for p in model.detector_prior_gamma_controller.parameters():
                p.requires_grad = True
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
        ):
            getattr(model, name).requires_grad = True
        for mlp in model.strategy_mlps:
            for p in mlp.parameters():
                p.requires_grad = True
        return "hard_dual_regime"

    for p in model.parameters():
        p.requires_grad = True
    return "all"


def _joint_optimizer(model, lr: float,
                     strategy_lr: float | None = None,
                     scalar_lr: float | None = None):
    strategy_lr = float(strategy_lr if strategy_lr is not None else lr)
    scalar_lr = float(scalar_lr if scalar_lr is not None else lr)
    detector_params = [
        p for detector in model.detectors for p in detector.parameters()
    ]
    scalar_params = [
        getattr(model, name)
        for name in (
            "gain_damp_raw",
            "sigma_mix_raw",
            "pnp_mix_raw",
            "uncert_scale_raw",
            "detector_prior_gamma_raw",
        )
    ]
    strategy_params = [
        p for mlp in model.strategy_mlps for p in mlp.parameters()
    ]
    param_groups = [
        {"params": detector_params, "lr": lr, "weight_decay": 1e-4},
        {"params": scalar_params, "lr": scalar_lr, "weight_decay": 0.0},
        {"params": strategy_params, "lr": strategy_lr, "weight_decay": 1e-5},
    ]
    if getattr(model, "leakage_refiner", None) is not None:
        leakage_params = [p for p in model.leakage_refiner.parameters() if p.requires_grad]
        if leakage_params:
            param_groups.append({"params": leakage_params, "lr": lr, "weight_decay": 1e-4})
    if getattr(model, "pnp_denoiser", None) is not None:
        pnp_params = [p for p in model.pnp_denoiser.parameters() if p.requires_grad]
        if pnp_params:
            param_groups.append({"params": pnp_params, "lr": lr, "weight_decay": 1e-4})
    if getattr(model, "pnp_mix_controller", None) is not None:
        ctrl_params = [p for p in model.pnp_mix_controller.parameters() if p.requires_grad]
        if ctrl_params:
            param_groups.append({"params": ctrl_params, "lr": lr, "weight_decay": 1e-4})
    if getattr(model, "detector_prior_refiner", None) is not None:
        det_prior_params = [p for p in model.detector_prior_refiner.parameters() if p.requires_grad]
        if det_prior_params:
            param_groups.append({"params": det_prior_params, "lr": lr, "weight_decay": 1e-4})
    if getattr(model, "detector_prior_gamma_controller", None) is not None:
        gamma_ctrl_params = [p for p in model.detector_prior_gamma_controller.parameters() if p.requires_grad]
        if gamma_ctrl_params:
            param_groups.append({"params": gamma_ctrl_params, "lr": lr, "weight_decay": 1e-4})
    return torch.optim.AdamW(param_groups)


def _teacher_kwargs_for_phase(phase_name: str, support_t: torch.Tensor,
                              seed_t: torch.Tensor, gain_t: torch.Tensor,
                              mu_t: torch.Tensor,
                              var_t: torch.Tensor, llr_t: torch.Tensor) -> dict[str, torch.Tensor | None]:
    if phase_name == "support_warmup":
        return {
            "teacher_support_iter": support_t,
            "teacher_seed_iter": seed_t,
            "teacher_gain_iter": None,
            "teacher_mu_iter": None,
            "teacher_var_iter": None,
            "teacher_llr_iter": None,
        }
    return {
        "teacher_support_iter": support_t,
        "teacher_seed_iter": seed_t,
        "teacher_gain_iter": gain_t,
        "teacher_mu_iter": mu_t,
        "teacher_var_iter": var_t,
        # Keep teacher LLR only as supervision target, not as detector input.
        "teacher_llr_iter": None,
    }


def _regime_strategy_stats(out: dict[str, torch.Tensor], snr_db: torch.Tensor) -> dict[str, float]:
    history = out.get("history", [])
    if not history:
        return {}
    snr = snr_db.reshape(-1).float()
    all_mask = torch.ones_like(snr, dtype=torch.bool)
    low_mask = torch.isclose(snr, snr.new_tensor(5.0))
    high_mask = torch.isclose(snr, snr.new_tensor(25.0))

    def _stage_mean(key: str, mask: torch.Tensor) -> float:
        vals = []
        for stage in history:
            if key not in stage:
                continue
            stage_val = stage[key].float().reshape(stage[key].shape[0], -1).mean(dim=1)
            if bool(mask.any().item()):
                vals.append(float(stage_val[mask].mean().detach().cpu()))
        if not vals:
            return 0.0
        return float(np.mean(vals))

    return {
        "lambda_low": _stage_mean("lambda_ls", low_mask),
        "lambda_high": _stage_mean("lambda_ls", high_mask),
        "sigma_mix_low": _stage_mean("sigma_mix", low_mask),
        "sigma_mix_high": _stage_mean("sigma_mix", high_mask),
        "sic_beta_low": _stage_mean("sic_beta", low_mask),
        "sic_beta_high": _stage_mean("sic_beta", high_mask),
    }


def _run_epoch(model, loader, optimizer, scaler, device, amp_enabled, loss_cfg,
               training: bool, teacher_force: float, max_outer_iters: int | None,
               phase_name: str):
    model.train(training)
    total_loss = 0.0
    total_ber = 0.0
    total_items = 0
    total_stats = None

    for batch in loader:
        (x_feat, y_recv, x_pil, sigma, x_true, bits_true,
         mu_t, var_t, llr_t, support_t, seed_t, gain_t,
         cluster_t, leakage_t, snr_db) = _to_device_batch(batch, device)

        with torch.amp.autocast("cuda", enabled=amp_enabled):
            teacher_kwargs = _teacher_kwargs_for_phase(
                phase_name=phase_name,
                support_t=support_t,
                seed_t=seed_t,
                gain_t=gain_t,
                mu_t=mu_t,
                var_t=var_t,
                llr_t=llr_t,
            )
            out = model(
                x_feat, y_recv, x_pil, sigma,
                **teacher_kwargs,
                teacher_force=teacher_force,
                max_outer_iters=max_outer_iters,
            )

        loss, _stats = compute_joint_unrolled_loss(
            out=out,
            y_received=y_recv,
            bits_true=bits_true,
            x_data_true=x_true,
            support_teacher_iter=support_t,
            seed_teacher_iter=seed_t,
            gain_teacher_iter=gain_t,
            cluster_mask_teacher_iter=cluster_t,
            leakage_teacher_iter=leakage_t,
            llr_teacher_iter=llr_t,
            mu_teacher_iter=mu_t,
            var_teacher_iter=var_t,
            snr_db=snr_db,
            **loss_cfg,
        )
        regime_stats = _regime_strategy_stats(out, snr_db)
        for key, val in regime_stats.items():
            _stats[key] = loss.new_tensor(val)

        if training:
            optimizer.zero_grad(set_to_none=True)
            if scaler is not None:
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                optimizer.step()

        batch_size = x_feat.shape[0]
        total_items += batch_size
        total_loss += float(loss.detach().cpu()) * batch_size
        total_ber += float(ber_from_detection(x_true, out["final_detection"]).detach().cpu()) * batch_size
        if total_stats is None:
            total_stats = {k: 0.0 for k in _stats.keys()}
        for key, val in _stats.items():
            total_stats[key] += float(val.detach().cpu()) * batch_size

    denom = max(total_items, 1)
    mean_stats = {k: v / denom for k, v in (total_stats or {}).items()}
    return total_loss / denom, total_ber / denom, mean_stats


def _fit_phase(model, train_loader, val_loader, device, phase_name: str,
               epochs: int, lr: float, amp_enabled: bool):
    if epochs <= 0:
        return [], None
    phase_cfg = _phase_runtime_config(phase_name)

    if phase_name == "joint_finetune":
        optimizer = _joint_optimizer(model, lr)
    elif phase_name == "hard_finetune":
        _set_phase_trainability(model, phase_name, epoch=1, total_epochs=epochs)
        optimizer = _joint_optimizer(model, lr, strategy_lr=1e-3, scalar_lr=lr)
    else:
        _set_phase_trainability(model, phase_name, epoch=1, total_epochs=epochs)
        params = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=4
    )
    scaler = torch.amp.GradScaler("cuda", enabled=amp_enabled) if device.type == "cuda" else None
    loss_cfg = _phase_weight_config(
        phase_name,
        receiver_variant=model.receiver_variant,
        detector_prior_variant=getattr(model, "detector_prior_variant", "baseline"),
    )

    hist = []
    best_val = float("inf")
    best_state = None
    t0 = time.time()
    for epoch in range(1, epochs + 1):
        train_mode = _set_phase_trainability(model, phase_name, epoch=epoch, total_epochs=epochs)
        if epochs <= 1:
            teacher_force = phase_cfg["teacher_force_end"]
        else:
            alpha = (epoch - 1) / max(epochs - 1, 1)
            teacher_force = (
                (1.0 - alpha) * phase_cfg["teacher_force_start"] +
                alpha * phase_cfg["teacher_force_end"]
            )
        tr_loss, tr_ber, tr_stats = _run_epoch(
            model, train_loader, optimizer, scaler, device,
            amp_enabled, loss_cfg, training=True,
            teacher_force=teacher_force,
            max_outer_iters=phase_cfg["max_outer_iters"],
            phase_name=phase_name,
        )
        va_oracle_loss, va_oracle_ber, va_oracle_stats = _run_epoch(
            model, val_loader, None, None, device,
            amp_enabled, loss_cfg, training=False,
            teacher_force=phase_cfg["eval_teacher_force_oracle"],
            max_outer_iters=phase_cfg["eval_outer_iters"],
            phase_name=phase_name,
        )
        va_free_loss, va_free_ber, va_free_stats = _run_epoch(
            model, val_loader, None, None, device,
            amp_enabled, loss_cfg, training=False,
            teacher_force=phase_cfg["eval_teacher_force_free"],
            max_outer_iters=phase_cfg["eval_outer_iters"],
            phase_name=phase_name,
        )
        best_mode = phase_cfg["select_best_on"]
        if best_mode == "oracle":
            main_val_loss = va_oracle_loss
            main_val_ber = va_oracle_ber
        else:
            main_val_loss = va_free_loss
            main_val_ber = va_free_ber
        scheduler.step(main_val_loss)
        lr_now = float(optimizer.param_groups[0]["lr"])
        hist.append({
            "loss": tr_loss,
            "val_loss": main_val_loss,
            "ber": tr_ber,
            "val_ber": main_val_ber,
            "val_oracle_loss": va_oracle_loss,
            "val_oracle_ber": va_oracle_ber,
            "val_free_loss": va_free_loss,
            "val_free_ber": va_free_ber,
            "lr": lr_now,
            "teacher_force": teacher_force,
            "train_stats": tr_stats,
            "val_oracle_stats": va_oracle_stats,
            "val_free_stats": va_free_stats,
        })

        if main_val_loss < best_val:
            best_val = main_val_loss
            best_state = {
                "model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                "val_loss": main_val_loss,
                "val_mode": best_mode,
                "phase": phase_name,
                "epoch": epoch,
            }

        elapsed = time.time() - t0
        eta = (elapsed / epoch) * max(epochs - epoch, 0)
        if phase_name == "support_warmup":
            extra = (
                f"  seed={tr_stats.get('seed', 0.0):.3e}/{va_oracle_stats.get('seed', 0.0):.3e}"
                f"  seedR={tr_stats.get('seed_recall', 0.0):.3f}/{va_oracle_stats.get('seed_recall', 0.0):.3f}"
                f"  supp={tr_stats.get('support', 0.0):.3e}/{va_oracle_stats.get('support', 0.0):.3e}"
                f"  suppR={tr_stats.get('support_recall', 0.0):.3f}/{va_oracle_stats.get('support_recall', 0.0):.3f}"
                f"  suppP={tr_stats.get('support_precision', 0.0):.3f}/{va_oracle_stats.get('support_precision', 0.0):.3f}"
                f"  gain={tr_stats.get('gain', 0.0):.3e}/{va_oracle_stats.get('gain', 0.0):.3e}"
            )
        elif phase_name == "leakage_warmup":
            extra = (
                f"  seed={tr_stats.get('seed', 0.0):.3e}/{va_free_stats.get('seed', 0.0):.3e}"
                f"  suppR={tr_stats.get('support_recall', 0.0):.3f}/{va_free_stats.get('support_recall', 0.0):.3f}"
                f"  cl={tr_stats.get('cluster_mask', 0.0):.3e}/{va_free_stats.get('cluster_mask', 0.0):.3e}"
                f"  clR={tr_stats.get('cluster_recall', 0.0):.3f}/{va_free_stats.get('cluster_recall', 0.0):.3f}"
                f"  clP={tr_stats.get('cluster_precision', 0.0):.3f}/{va_free_stats.get('cluster_precision', 0.0):.3f}"
                f"  leak={tr_stats.get('leakage_profile', 0.0):.3e}/{va_free_stats.get('leakage_profile', 0.0):.3e}"
                f"  gain={tr_stats.get('gain', 0.0):.3e}/{va_free_stats.get('gain', 0.0):.3e}"
            )
        elif phase_name == "prior_warmup":
            extra = (
                f"  seed={tr_stats.get('seed', 0.0):.3e}/{va_free_stats.get('seed', 0.0):.3e}"
                f"  suppR={tr_stats.get('support_recall', 0.0):.3f}/{va_free_stats.get('support_recall', 0.0):.3f}"
                f"  pnp={tr_stats.get('pnp_delta', 0.0):.3e}/{va_free_stats.get('pnp_delta', 0.0):.3e}"
                f"  pnpI={tr_stats.get('pnp_identity', 0.0):.3e}/{va_free_stats.get('pnp_identity', 0.0):.3e}"
                f"  pnpN={tr_stats.get('pnp_delta_norm', 0.0):.3e}/{va_free_stats.get('pnp_delta_norm', 0.0):.3e}"
                f"  vx={tr_stats.get('vx', 0.0):.3e}/{va_free_stats.get('vx', 0.0):.3e}"
                f"  gain={tr_stats.get('gain', 0.0):.3e}/{va_free_stats.get('gain', 0.0):.3e}"
            )
        elif phase_name in {"detector_prior_warmup", "detector_prior_distill_warmup"}:
            extra = (
                f"  kd={tr_stats.get('kd', 0.0):.3e}/{va_free_stats.get('kd', 0.0):.3e}"
                f"  dDt={tr_stats.get('det_prior_delta', 0.0):.3e}/{va_free_stats.get('det_prior_delta', 0.0):.3e}"
                f"  dSym={tr_stats.get('det_prior_sym', 0.0):.3e}/{va_free_stats.get('det_prior_sym', 0.0):.3e}"
                f"  dVx={tr_stats.get('det_prior_vx', 0.0):.3e}/{va_free_stats.get('det_prior_vx', 0.0):.3e}"
                f"  dId={tr_stats.get('det_prior_identity', 0.0):.3e}/{va_free_stats.get('det_prior_identity', 0.0):.3e}"
                f"  dN={tr_stats.get('det_prior_delta_norm', 0.0):.3e}/{va_free_stats.get('det_prior_delta_norm', 0.0):.3e}"
                f"  dG={tr_stats.get('det_prior_gamma', 0.0):.3f}/{va_free_stats.get('det_prior_gamma', 0.0):.3f}"
                f"  vx={tr_stats.get('vx', 0.0):.3e}/{va_free_stats.get('vx', 0.0):.3e}"
            )
        elif phase_name == "detector_warmup":
            extra = (
                f"  kd={tr_stats.get('kd', 0.0):.3e}/{va_oracle_stats.get('kd', 0.0):.3e}"
                f"  sym={tr_stats.get('sym', 0.0):.3e}/{va_oracle_stats.get('sym', 0.0):.3e}"
                f"  seed={tr_stats.get('seed', 0.0):.3e}/{va_oracle_stats.get('seed', 0.0):.3e}"
                f"  seedR={tr_stats.get('seed_recall', 0.0):.3f}/{va_oracle_stats.get('seed_recall', 0.0):.3f}"
                f"  cl={tr_stats.get('cluster_mask', 0.0):.3e}/{va_oracle_stats.get('cluster_mask', 0.0):.3e}"
                f"  leak={tr_stats.get('leakage_profile', 0.0):.3e}/{va_oracle_stats.get('leakage_profile', 0.0):.3e}"
                f"  pnp={tr_stats.get('pnp_delta', 0.0):.3e}/{va_oracle_stats.get('pnp_delta', 0.0):.3e}"
                f"  dSym={tr_stats.get('det_prior_sym', 0.0):.3e}/{va_oracle_stats.get('det_prior_sym', 0.0):.3e}"
                f"  dN={tr_stats.get('det_prior_delta_norm', 0.0):.3e}/{va_oracle_stats.get('det_prior_delta_norm', 0.0):.3e}"
                f"  vx={tr_stats.get('vx', 0.0):.3e}/{va_oracle_stats.get('vx', 0.0):.3e}"
            )
        else:
            extra = (
                f"  bits={tr_stats.get('bits', 0.0):.3e}/{va_free_stats.get('bits', 0.0):.3e}"
                f"  kd={tr_stats.get('kd', 0.0):.3e}/{va_free_stats.get('kd', 0.0):.3e}"
                f"  seed={tr_stats.get('seed', 0.0):.3e}/{va_free_stats.get('seed', 0.0):.3e}"
                f"  seedR={tr_stats.get('seed_recall', 0.0):.3f}/{va_free_stats.get('seed_recall', 0.0):.3f}"
                f"  suppR={tr_stats.get('support_recall', 0.0):.3f}/{va_free_stats.get('support_recall', 0.0):.3f}"
                f"  suppP={tr_stats.get('support_precision', 0.0):.3f}/{va_free_stats.get('support_precision', 0.0):.3f}"
                f"  clR={tr_stats.get('cluster_recall', 0.0):.3f}/{va_free_stats.get('cluster_recall', 0.0):.3f}"
                f"  clP={tr_stats.get('cluster_precision', 0.0):.3f}/{va_free_stats.get('cluster_precision', 0.0):.3f}"
                f"  leak={tr_stats.get('leakage_profile', 0.0):.3e}/{va_free_stats.get('leakage_profile', 0.0):.3e}"
                f"  pnp={tr_stats.get('pnp_delta', 0.0):.3e}/{va_free_stats.get('pnp_delta', 0.0):.3e}"
                f"  pnpI={tr_stats.get('pnp_identity', 0.0):.3e}/{va_free_stats.get('pnp_identity', 0.0):.3e}"
                f"  dSym={tr_stats.get('det_prior_sym', 0.0):.3e}/{va_free_stats.get('det_prior_sym', 0.0):.3e}"
                f"  dN={tr_stats.get('det_prior_delta_norm', 0.0):.3e}/{va_free_stats.get('det_prior_delta_norm', 0.0):.3e}"
                f"  vx={tr_stats.get('vx', 0.0):.3e}/{va_free_stats.get('vx', 0.0):.3e}"
            )
        val_stats_ref = va_oracle_stats if best_mode == "oracle" else va_free_stats
        strategy_extra = (
            f"  lam={tr_stats.get('lambda_ls', 0.0):.3e}/{val_stats_ref.get('lambda_ls', 0.0):.3e}"
            f"  smix={tr_stats.get('sigma_mix', 0.0):.3f}/{val_stats_ref.get('sigma_mix', 0.0):.3f}"
            f"  sic={tr_stats.get('sic_beta', 0.0):.3e}/{val_stats_ref.get('sic_beta', 0.0):.3e}"
            f"  side={tr_stats.get('side_reg', 0.0):.3e}/{val_stats_ref.get('side_reg', 0.0):.3e}"
            f"  pnpMix={tr_stats.get('pnp_mix', 0.0):.3f}/{val_stats_ref.get('pnp_mix', 0.0):.3f}"
            f"  pnpLam={tr_stats.get('pnp_lambda', 0.0):.3f}/{val_stats_ref.get('pnp_lambda', 0.0):.3f}"
            f"  pnpGap={tr_stats.get('pnp_identity_gap', 0.0):.3e}/{val_stats_ref.get('pnp_identity_gap', 0.0):.3e}"
            f"  uScale={tr_stats.get('uncert_scale', 0.0):.3f}/{val_stats_ref.get('uncert_scale', 0.0):.3f}"
            f"  dGam={tr_stats.get('det_prior_gamma', 0.0):.3f}/{val_stats_ref.get('det_prior_gamma', 0.0):.3f}"
            f"  vxM={tr_stats.get('vx_mean', 0.0):.3e}/{val_stats_ref.get('vx_mean', 0.0):.3e}"
            f"  vxR={tr_stats.get('vx_recal_mean', 0.0):.3e}/{val_stats_ref.get('vx_recal_mean', 0.0):.3e}"
            f"  lamL/H={tr_stats.get('lambda_low', 0.0):.3e}/{tr_stats.get('lambda_high', 0.0):.3e}|{val_stats_ref.get('lambda_low', 0.0):.3e}/{val_stats_ref.get('lambda_high', 0.0):.3e}"
            f"  smixL/H={tr_stats.get('sigma_mix_low', 0.0):.3f}/{tr_stats.get('sigma_mix_high', 0.0):.3f}|{val_stats_ref.get('sigma_mix_low', 0.0):.3f}/{val_stats_ref.get('sigma_mix_high', 0.0):.3f}"
            f"  sicL/H={tr_stats.get('sic_beta_low', 0.0):.3e}/{tr_stats.get('sic_beta_high', 0.0):.3e}|{val_stats_ref.get('sic_beta_low', 0.0):.3e}/{val_stats_ref.get('sic_beta_high', 0.0):.3e}"
        )
        print(
            f"  {phase_name.capitalize()} [{epoch:>3}/{epochs}]  "
            f"loss={tr_loss:.3e}  val({best_mode})={main_val_loss:.3e}  "
            f"ber[o/f]={va_oracle_ber:.4f}/{va_free_ber:.4f}  "
            f"lr={lr_now:.1e}  tf={teacher_force:.2f}  "
            f"mode={train_mode}  "
            f"{elapsed/epoch:.0f}s/ep  ETA {eta/60:.1f}m"
            f"{extra}"
            f"{strategy_extra}",
            flush=True,
        )

    if best_state is not None:
        model.load_state_dict(best_state["model"])
    return hist, best_state


def _plot_histories(save_png: pathlib.Path, warmup_hist, finetune_hist):
    plt.figure(figsize=(10, 4))
    ax1 = plt.subplot(1, 2, 1)
    offset = 0
    for hist, label in [(warmup_hist, "warmup"), (finetune_hist, "finetune")]:
        xs = np.arange(offset, offset + len(hist))
        ax1.plot(xs, [h["loss"] for h in hist], label=f"{label} train")
        ax1.plot(xs, [h["val_loss"] for h in hist], "--", label=f"{label} val")
        offset += len(hist)
    ax1.set_title("Loss")
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8)

    ax2 = plt.subplot(1, 2, 2)
    offset = 0
    for hist, label in [(warmup_hist, "warmup"), (finetune_hist, "finetune")]:
        xs = np.arange(offset, offset + len(hist))
        ax2.plot(xs, [h["ber"] for h in hist], label=f"{label} train")
        ax2.plot(xs, [h["val_ber"] for h in hist], "--", label=f"{label} val")
        offset += len(hist)
    ax2.set_title("BER")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(save_png, dpi=200, bbox_inches="tight")
    plt.close()


def main():
    here = pathlib.Path(__file__).parent
    parser = argparse.ArgumentParser(
        description="Train the sparse model-driven joint unrolled receiver"
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(here / "outputs_joint_unrolled"),
    )
    parser.add_argument(
        "--teacher-cache",
        type=str,
        default=str(here / "outputs_joint_unrolled" / "teacher_sparse_traj_cache.pt"),
    )
    parser.add_argument(
        "--raw-teacher",
        type=str,
        default=str(here / "outputs_joint_unrolled" / "teacher_labels" / "teacher_all_snr_traj.npz"),
    )
    parser.add_argument(
        "--stats",
        type=str,
        default=str(here / "outputs_n512" / "global_stats.pkl"),
    )
    parser.add_argument(
        "--ce-ckpt",
        type=str,
        default=str(here / "outputs_n512" / "dnn_ce_model.pt"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--val-batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--support-epochs", type=int, default=0)
    parser.add_argument("--leakage-epochs", type=int, default=4)
    parser.add_argument("--prior-epochs", type=int, default=1)
    parser.add_argument("--detector-prior-epochs", type=int, default=1)
    parser.add_argument("--detector-epochs", type=int, default=6)
    parser.add_argument("--joint-epochs", type=int, default=8)
    parser.add_argument("--hard-epochs", type=int, default=4)
    parser.add_argument("--support-lr", type=float, default=2e-3)
    parser.add_argument("--detector-lr", type=float, default=5e-4)
    parser.add_argument("--joint-lr", type=float, default=5e-4)
    parser.add_argument("--hard-lr", type=float, default=2e-4)
    parser.add_argument("--snr-list", nargs="+", type=int, default=[5, 10, 15, 20, 25])
    parser.add_argument("--hard-snr-list", nargs="+", type=int, default=[5, 25])
    parser.add_argument("--frames-per-snr", type=int, default=200)
    parser.add_argument("--rho", type=float, default=0.5)
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument(
        "--receiver-variant",
        choices=["baseline", "leakage_aware", "patch_aggregator", "pnp_prior"],
        default="baseline",
    )
    parser.add_argument(
        "--uncertainty-variant",
        choices=["baseline", "vx_recal_v1"],
        default="baseline",
    )
    parser.add_argument(
        "--detector-prior-variant",
        choices=["baseline", "pnp_sd_v1", "pnp_sd_v2", "distill_sd_v1"],
        default="baseline",
    )
    parser.add_argument(
        "--support-consumption",
        choices=["soft", "hard_hybrid"],
        default="soft",
        help="How leakage cluster_prob is consumed before active_set_refit.",
    )
    parser.add_argument(
        "--hard-mask-threshold",
        type=float,
        default=0.6,
        help="Threshold for seed-preserving hard-hybrid support expansion.",
    )
    parser.add_argument(
        "--hard-mask-topk",
        type=int,
        default=1,
        help="Per-anchor top-k expansion cap for hard-hybrid support consumption.",
    )
    parser.add_argument(
        "--disable-gain-delta",
        action="store_true",
        help="Keep leakage cluster weighting but disable learned gain_delta updates.",
    )
    parser.add_argument(
        "--pnp-lambda-max",
        type=float,
        default=0.25,
    )
    parser.add_argument("--detector-prior-gamma-max", type=float, default=0.20)
    parser.add_argument("--force-teacher", action="store_true")
    parser.add_argument("--enable-tf32", action="store_true", default=False)
    parser.add_argument(
        "--awgn-reference",
        choices=["adaptive", "fixed"],
        default="adaptive",
        help="AWGN noise-variance convention passed down to teacher generation.",
    )
    parser.add_argument(
        "--resume-ckpt",
        type=str,
        default="",
        help="Optional path to an existing joint_unrolled_model.pt to warm-start the receiver.",
    )
    args = parser.parse_args()

    _set_seed(args.seed)
    _maybe_enable_tf32(args.enable_tf32)

    if args.detector_prior_variant == "distill_sd_v1" and args.hard_epochs > 0:
        print(
            "  note: disabling hard_finetune for distill_sd_v1 to preserve the"
            " iter-0 cosine objective and avoid the unstable 5/25 dB dual-regime phase"
        )
        args.hard_epochs = 0

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    teacher_cache = load_or_prepare_teacher_cache(
        cache_path=pathlib.Path(args.teacher_cache),
        raw_npz_path=pathlib.Path(args.raw_teacher),
        stats_path=pathlib.Path(args.stats),
        snr_list=args.snr_list,
        frames_per_snr=args.frames_per_snr,
        rho=args.rho,
        force_generate=args.force_teacher,
        batch_size=max(64, args.val_batch_size),
        awgn_reference=args.awgn_reference,
    )
    cache = torch.load(teacher_cache, map_location="cpu", weights_only=False)

    sys_obj = _load_stats(make_system_n512(rho=args.rho), pathlib.Path(args.stats))
    device = sys_obj._pt_device()
    use_amp = device.type == "cuda"
    print(f"  device={device}  amp={use_amp}  tf32={args.enable_tf32}")

    k_factor, k_max, l_max_grid, width_grid, _pad_size = sys_obj._get_2d_grid_params()
    input_dim = l_max_grid * width_grid * 2 + 4
    data_pos = cache["data_positions"].numpy()

    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
    ce_ckpt = pathlib.Path(args.ce_ckpt)
    if ce_ckpt.exists():
        ce_backbone.load_state_dict(torch.load(ce_ckpt, map_location="cpu"))
        print(f"  CE backbone loaded from {ce_ckpt}")
    else:
        print(f"  CE checkpoint not found, training from scratch: {ce_ckpt}")

    model = build_joint_unrolled_model(
        input_dim=input_dim,
        n_total=sys_obj.N_total,
        c1=sys_obj.c1,
        c2=sys_obj.c2,
        l_max_cap=sys_obj.l_max_cap,
        k_max_cap=sys_obj.k_max_cap,
        data_positions=data_pos,
        grid_l_max=l_max_grid,
        grid_w=width_grid,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        ce_backbone=ce_backbone,
        use_hybrid_support_init=True,
        freeze_support_after_init=True,
        receiver_variant=args.receiver_variant,
        uncertainty_variant=args.uncertainty_variant,
        detector_prior_variant=args.detector_prior_variant,
        disable_gain_delta=args.disable_gain_delta,
        support_consumption=args.support_consumption,
        hard_mask_threshold=args.hard_mask_threshold,
        hard_mask_topk=args.hard_mask_topk,
        pnp_lambda_max=args.pnp_lambda_max,
        detector_prior_gamma_max=args.detector_prior_gamma_max,
    ).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  JointUnrolledReceiver params={n_params:,}")

    if args.resume_ckpt:
        resume_path = pathlib.Path(args.resume_ckpt)
        if not resume_path.exists():
            raise FileNotFoundError(f"--resume-ckpt not found: {resume_path}")
        state = torch.load(resume_path, map_location=device, weights_only=False)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        missing, unexpected = model.load_state_dict(state, strict=False)
        print(f"  Resumed JointUnrolledReceiver from {resume_path}")
        if missing:
            print(f"    missing keys: {len(missing)} (first 5: {missing[:5]})")
        if unexpected:
            print(f"    unexpected keys: {len(unexpected)} (first 5: {unexpected[:5]})")

    tr_loader, va_loader = _make_loaders(
        cache=cache,
        batch_size=args.batch_size,
        val_batch_size=args.val_batch_size,
        val_split=args.val_split,
        num_workers=args.num_workers,
        seed=args.seed,
    )
    hard_tr_loader = None
    hard_va_loader = None
    if args.hard_epochs > 0:
        hard_tr_loader, hard_va_loader = _make_loaders(
            cache=cache,
            batch_size=args.batch_size,
            val_batch_size=args.val_batch_size,
            val_split=args.val_split,
            num_workers=args.num_workers,
            seed=args.seed,
            keep_snr=args.hard_snr_list,
            exact_contrastive=sorted(args.hard_snr_list) == [5, 25],
        )

    print("\n" + "█" * 72)
    print("  SPARSE JOINT UNROLLED RECEIVER TRAINING")
    print("█" * 72)
    print(f"  Variant: {args.receiver_variant}")
    print(f"  Uncertainty variant: {args.uncertainty_variant}")
    print(f"  Detector prior variant: {args.detector_prior_variant}")
    print(f"  Disable gain_delta: {args.disable_gain_delta}")
    print(
        f"  Support consumption: {args.support_consumption}"
        f"  (tau={args.hard_mask_threshold:.3f}, topk={args.hard_mask_topk})"
    )
    print(f"  PnP lambda max: {args.pnp_lambda_max:.3f}")
    print(f"  Detector-prior gamma max: {args.detector_prior_gamma_max:.3f}")
    print(f"  Support warmup: {args.support_epochs} ep, lr={args.support_lr:.1e}, batch={args.batch_size}")
    if args.receiver_variant == "pnp_prior" or args.uncertainty_variant != "baseline":
        print(f"  Prior warmup: {args.prior_epochs} ep, lr={args.support_lr:.1e}")
    else:
        print(f"  Leakage warmup: {args.leakage_epochs} ep, lr={args.support_lr:.1e}")
    if args.detector_prior_variant != "baseline":
        warmup_label = (
            "Detector-prior distill warmup"
            if args.detector_prior_variant == "distill_sd_v1"
            else "Detector-prior warmup"
        )
        print(f"  {warmup_label}: {args.detector_prior_epochs} ep, lr={args.detector_lr:.1e}")
    print(f"  Detector warmup: {args.detector_epochs} ep, lr={args.detector_lr:.1e}")
    print(f"  Joint finetune: {args.joint_epochs} ep, lr={args.joint_lr:.1e}")
    print(f"  Hard finetune: {args.hard_epochs} ep, lr={args.hard_lr:.1e}, snr={args.hard_snr_list}")
    print(f"  OMP init: max_active_atoms={args.max_active_atoms}, k_leak={args.k_leak}")

    support_hist, support_best = _fit_phase(
        model, tr_loader, va_loader, device, "support_warmup",
        args.support_epochs, args.support_lr, use_amp,
    )
    use_prior_phase = (args.receiver_variant == "pnp_prior") or (args.uncertainty_variant != "baseline")
    prior_phase_name = "prior_warmup" if use_prior_phase else "leakage_warmup"
    prior_phase_epochs = args.prior_epochs if use_prior_phase else args.leakage_epochs
    prior_hist, prior_best = _fit_phase(
        model, tr_loader, va_loader, device, prior_phase_name,
        prior_phase_epochs, args.support_lr, use_amp,
    )
    detector_prior_phase_name = (
        "detector_prior_distill_warmup"
        if args.detector_prior_variant == "distill_sd_v1"
        else "detector_prior_warmup"
    )
    detector_prior_hist, detector_prior_best = _fit_phase(
        model, tr_loader, va_loader, device, detector_prior_phase_name,
        args.detector_prior_epochs if args.detector_prior_variant != "baseline" else 0,
        args.detector_lr, use_amp,
    )
    detector_hist, detector_best = _fit_phase(
        model, tr_loader, va_loader, device, "detector_warmup",
        args.detector_epochs, args.detector_lr, use_amp,
    )
    joint_hist, joint_best = _fit_phase(
        model, tr_loader, va_loader, device, "joint_finetune",
        args.joint_epochs, args.joint_lr, use_amp,
    )
    hard_hist, hard_best = _fit_phase(
        model, hard_tr_loader, hard_va_loader, device, "hard_finetune",
        args.hard_epochs, args.hard_lr, use_amp,
    )

    ckpt_path = out_dir / "joint_unrolled_model.pt"
    torch.save(model.state_dict(), ckpt_path)
    hist_path = out_dir / "joint_unrolled_results.pkl"
    with open(hist_path, "wb") as f:
        pickle.dump({
            "support_warmup": support_hist,
            "prior_warmup": prior_hist if prior_phase_name == "prior_warmup" else [],
            "leakage_warmup": prior_hist if prior_phase_name == "leakage_warmup" else [],
            "detector_prior_warmup": detector_prior_hist,
            "detector_prior_distill_warmup": detector_prior_hist if detector_prior_phase_name == "detector_prior_distill_warmup" else [],
            "detector_warmup": detector_hist,
            "joint_finetune": joint_hist,
            "hard_finetune": hard_hist,
            "support_best": support_best,
            "prior_best": prior_best if prior_phase_name == "prior_warmup" else None,
            "leakage_best": prior_best if prior_phase_name == "leakage_warmup" else None,
            "detector_prior_best": detector_prior_best,
            "detector_best": detector_best,
            "joint_best": joint_best,
            "hard_best": hard_best,
            "teacher_cache": str(teacher_cache),
            "receiver_variant": args.receiver_variant,
            "uncertainty_variant": args.uncertainty_variant,
            "detector_prior_variant": args.detector_prior_variant,
            "disable_gain_delta": args.disable_gain_delta,
            "support_consumption": args.support_consumption,
            "hard_mask_threshold": args.hard_mask_threshold,
            "hard_mask_topk": args.hard_mask_topk,
            "prior_epochs": args.prior_epochs,
            "pnp_lambda_max": args.pnp_lambda_max,
            "detector_prior_epochs": args.detector_prior_epochs,
            "detector_prior_gamma_max": args.detector_prior_gamma_max,
        }, f)
    plot_path = out_dir / "joint_unrolled_training_curves.png"
    _plot_histories(plot_path, support_hist + prior_hist + detector_hist + joint_hist, hard_hist)

    print(f"\n  Joint checkpoint -> {ckpt_path}")
    print(f"  Curves -> {plot_path}")
    print(f"  Results -> {hist_path}")
    print("  Verify: python -m afdm_sp_joint_unrolled.verify_joint_unrolled")


if __name__ == "__main__":
    main()
