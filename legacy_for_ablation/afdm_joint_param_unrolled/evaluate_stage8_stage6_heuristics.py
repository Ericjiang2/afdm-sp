"""
evaluate_stage8_stage6_heuristics.py

Stage-8 follow-up:
  - fixed heuristic profiles for Stage6 fixed
  - coarse 2D alpha x sigma-inflation sweep
  - expanded best-constant sweep across multiple seeds
  - sigma-only plateau confirmation around best-constant
  - two-stage sigma schedule v1
  - outer-iteration layered oracle around best-constant
  - outer-loop trace summaries for key profiles
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.diagnose_joint_heuristics import (
    SharedBatch,
    _ber_from_output,
    _generate_shared_batches,
)
from afdm_joint_param_unrolled.verify_joint_param import _load_param_model
from afdm_joint_param_unrolled.verify_oamp import _make_system, _sync_l_max_cap


def _artifact_stem(param_set: str) -> str:
    return f"param_joint_{param_set}"


def _load_stage6_fixed_model(
    sys_obj,
    joint_dir: pathlib.Path,
    device: torch.device,
    num_outer_iters: int,
    num_mp_layers: int,
    max_active_atoms: int,
    k_leak: int,
    learned_param_set: str,
):
    ckpt = joint_dir / f"{_artifact_stem(learned_param_set)}.pt"
    if not ckpt.exists() and learned_param_set == "lambda_alpha_beta":
        ckpt = joint_dir / "param_joint_model.pt"
    if not ckpt.exists():
        raise FileNotFoundError(f"Missing {ckpt}")
    model, data_pos = _load_param_model(
        sys_obj=sys_obj,
        ckpt_path=ckpt,
        device=device,
        num_outer_iters=num_outer_iters,
        num_mp_layers=num_mp_layers,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        learned_param_set=learned_param_set,
    )
    return model, np.asarray(data_pos, dtype=np.int64), ckpt


def _frame_ber_array(x_true: np.ndarray, x_hat_block: np.ndarray, data_pos: np.ndarray) -> np.ndarray:
    bers = [
        _ber_from_output(x_true[i], x_hat_block[i], data_pos)
        for i in range(x_true.shape[0])
    ]
    return np.asarray(bers, dtype=np.float64)


def _slice_shared_batch(batch: SharedBatch, start: int, end: int) -> SharedBatch:
    return SharedBatch(
        x_feat=batch.x_feat[start:end],
        y_recv=batch.y_recv[start:end],
        x_pil=batch.x_pil[start:end],
        sigma=batch.sigma[start:end],
        x_true=batch.x_true[start:end],
        speeds=batch.speeds[start:end],
        channel_types=batch.channel_types[start:end],
    )


def _block_to_complex_torch(x_block: torch.Tensor) -> torch.Tensor:
    n = x_block.shape[-1] // 2
    real = x_block[..., :n]
    imag = x_block[..., n:]
    return torch.complex(real, imag)


def _align_truth_complex(
    x_true_full: np.ndarray,
    det_block: torch.Tensor,
    data_pos: np.ndarray,
) -> torch.Tensor:
    x_true = torch.as_tensor(x_true_full, device=det_block.device)
    n_det = int(det_block.shape[-1] // 2)
    if x_true.shape[-1] == n_det:
        return x_true
    if n_det == int(data_pos.size):
        data_idx = torch.as_tensor(data_pos, device=det_block.device, dtype=torch.long)
        return x_true.index_select(1, data_idx)
    raise ValueError(
        f"Cannot align truth with detector output: x_true_width={x_true.shape[-1]}, "
        f"det_width={n_det}, n_data={data_pos.size}"
    )


def _evaluate_stage6_profile(
    model,
    batch: SharedBatch,
    data_pos: np.ndarray,
    overrides: dict[str, Any] | None,
    eval_batch_size: int,
    collect_traces: bool = False,
    collect_frame_calibration: bool = False,
):
    num_frames = int(batch.x_true.shape[0])
    chunk_size = max(1, int(eval_batch_size))
    total_ber = 0.0
    total_support = 0.0
    total_seed = 0.0
    total_sigma_eff = 0.0
    trace_accum: list[dict[str, float]] | None = None
    calib_accum: list[dict[str, float]] | None = None
    frame_cal_rows: list[dict[str, Any]] | None = [] if collect_frame_calibration else None
    need_stage_pass = bool(collect_traces or frame_cal_rows is not None)

    with torch.no_grad():
        for start in range(0, num_frames, chunk_size):
            end = min(start + chunk_size, num_frames)
            sub = _slice_shared_batch(batch, start, end)
            out = model.diagnose(sub.x_feat, sub.y_recv, sub.x_pil, sub.sigma, diagnostic_overrides=overrides)
            x_hat = out["final_detection"].detach().cpu().numpy()
            frame_ber = _frame_ber_array(sub.x_true, x_hat, data_pos)
            weight = end - start
            total_ber += float(frame_ber.mean()) * weight
            total_support += float(out["support_stats"]["support_count"].detach().float().mean().cpu().item()) * weight
            total_seed += float(out["support_stats"]["seed_count"].detach().float().mean().cpu().item()) * weight
            total_sigma_eff += float(out["stage_history"][-1]["sigma_eff"].detach().float().mean().cpu().item()) * weight

            if need_stage_pass:
                if trace_accum is None:
                    if collect_traces:
                        trace_accum = [
                            {
                                "ber": 0.0,
                                "residual_energy_mean": 0.0,
                                "sigma_eff_mean": 0.0,
                                "vx_mean": 0.0,
                                "channel_update_norm": 0.0,
                                "sic_weight_mean": 0.0,
                                "vx_recal_gain_mean": 0.0,
                            }
                            for _ in out["stage_history"]
                        ]
                    calib_accum = [
                        {
                            "vx_mean": 0.0,
                            "sym_err_mean": 0.0,
                            "calibration_ratio": 0.0,
                            "detector_sigma_mean": 0.0,
                            "empirical_residual_var": 0.0,
                            "sigma_gap_ratio": 0.0,
                            "post_sic_residual_energy": 0.0,
                            "sigma_ls_mean": 0.0,
                            "channel_update_norm": 0.0,
                            "sic_weight_mean": 0.0,
                            "vx_recal_gain_mean": 0.0,
                        }
                        for _ in out["stage_history"]
                    ]
                prev_h = None
                for t, stage in enumerate(out["stage_history"]):
                    stage_det = stage["detection"].detach().cpu().numpy()
                    if collect_traces and trace_accum is not None:
                        ber_t = float(_frame_ber_array(sub.x_true, stage_det, data_pos).mean())
                        trace_accum[t]["ber"] += ber_t * weight
                        trace_accum[t]["residual_energy_mean"] += _mean_stage_metric(stage, "residual_energy") * weight
                        trace_accum[t]["sigma_eff_mean"] += _mean_stage_metric(stage, "sigma_eff") * weight
                        trace_accum[t]["vx_mean"] += _mean_stage_metric(stage, "v_x") * weight
                        trace_accum[t]["channel_update_norm"] += _channel_update_norm(prev_h, stage["H_flat"]) * weight
                        trace_accum[t]["sic_weight_mean"] += _mean_stage_metric(stage, "sic_weight_mean") * weight
                        trace_accum[t]["vx_recal_gain_mean"] += _mean_stage_metric(stage, "vx_recal_gain_mean") * weight

                    det = stage["detection"].detach().float()
                    det_complex = _block_to_complex_torch(det)
                    x_true_block = _align_truth_complex(sub.x_true, det, data_pos)
                    sym_err = (det_complex - x_true_block).abs().square().mean(dim=-1, keepdim=True)
                    vx_mean = stage["v_x"].detach().float().mean(dim=-1, keepdim=True)
                    detector_sigma_mean = stage["detector_sigma"].detach().float().mean(dim=-1, keepdim=True)
                    sigma_ls_mean = stage["sigma_ls"].detach().float().mean(dim=-1, keepdim=True)
                    residual_energy = stage["residual_energy"].detach().float()
                    if calib_accum is not None:
                        calib_accum[t]["vx_mean"] += float(vx_mean.mean().cpu().item()) * weight
                        calib_accum[t]["sym_err_mean"] += float(sym_err.mean().cpu().item()) * weight
                        calib_accum[t]["calibration_ratio"] += float(
                            (sym_err.mean() / vx_mean.mean().clamp_min(1e-8)).cpu().item()
                        ) * weight
                        calib_accum[t]["detector_sigma_mean"] += float(detector_sigma_mean.mean().cpu().item()) * weight
                        calib_accum[t]["empirical_residual_var"] += float(residual_energy.mean().cpu().item()) * weight
                        calib_accum[t]["sigma_gap_ratio"] += float(
                            (residual_energy.mean() / detector_sigma_mean.mean().clamp_min(1e-8)).cpu().item()
                        ) * weight
                        calib_accum[t]["post_sic_residual_energy"] += float(residual_energy.mean().cpu().item()) * weight
                        calib_accum[t]["sigma_ls_mean"] += float(sigma_ls_mean.mean().cpu().item()) * weight
                        calib_accum[t]["channel_update_norm"] += _channel_update_norm(prev_h, stage["H_flat"]) * weight
                        calib_accum[t]["sic_weight_mean"] += _mean_stage_metric(stage, "sic_weight_mean") * weight
                        calib_accum[t]["vx_recal_gain_mean"] += _mean_stage_metric(stage, "vx_recal_gain_mean") * weight
                    if frame_cal_rows is not None:
                        frame_ber_t = _frame_ber_array(sub.x_true, stage_det, data_pos)
                        channel_update_norm_t = _channel_update_norm_tensor(prev_h, stage["H_flat"]).detach().float().reshape(-1)
                        detector_sigma_flat = detector_sigma_mean.detach().float().reshape(-1)
                        sigma_ls_flat = sigma_ls_mean.detach().float().reshape(-1)
                        residual_flat = residual_energy.detach().float().reshape(-1)
                        sym_err_flat = sym_err.detach().float().reshape(-1)
                        vx_flat = vx_mean.detach().float().reshape(-1)
                        sic_weight_flat = stage["sic_weight_mean"].detach().float().reshape(-1)
                        vx_recal_gain_flat = stage["vx_recal_gain_mean"].detach().float().reshape(-1)
                        sigma_eff_flat = stage["sigma_eff"].detach().float().reshape(-1)
                        for local_idx in range(end - start):
                            frame_cal_rows.append(
                                {
                                    "frame_idx": int(start + local_idx),
                                    "outer_iter": int(t),
                                    "ber": float(frame_ber_t[local_idx]),
                                    "sym_err_mean": float(sym_err_flat[local_idx].cpu().item()),
                                    "vx_mean": float(vx_flat[local_idx].cpu().item()),
                                    "rho": float(sym_err_flat[local_idx].cpu().item() / max(vx_flat[local_idx].cpu().item(), 1e-8)),
                                    "empirical_residual_var": float(residual_flat[local_idx].cpu().item()),
                                    "detector_sigma_mean": float(detector_sigma_flat[local_idx].cpu().item()),
                                    "eta": float(residual_flat[local_idx].cpu().item() / max(detector_sigma_flat[local_idx].cpu().item(), 1e-8)),
                                    "channel_update_norm": float(channel_update_norm_t[local_idx].cpu().item()),
                                    "sigma_eff_mean": float(sigma_eff_flat[local_idx].cpu().item()),
                                    "sigma_ls_mean": float(sigma_ls_flat[local_idx].cpu().item()),
                                    "residual_energy_mean": float(residual_flat[local_idx].cpu().item()),
                                    "sic_weight_mean": float(sic_weight_flat[local_idx].cpu().item()),
                                    "vx_recal_gain_mean": float(vx_recal_gain_flat[local_idx].cpu().item()),
                                }
                            )
                    prev_h = stage["H_flat"]

    result = {
        "ber": total_ber / max(num_frames, 1),
        "support_count_mean": total_support / max(num_frames, 1),
        "seed_count_mean": total_seed / max(num_frames, 1),
        "final_sigma_eff_mean": total_sigma_eff / max(num_frames, 1),
    }
    if collect_traces and trace_accum is not None:
        result["trace_history"] = [
            {k: float(v / max(num_frames, 1)) for k, v in stage.items()}
            for stage in trace_accum
        ]
        result["calibration_history"] = [
            {k: float(v / max(num_frames, 1)) for k, v in stage.items()}
            for stage in (calib_accum or [])
        ]
    if frame_cal_rows is not None:
        result["frame_calibration_rows"] = frame_cal_rows
    return result


def _mean_stage_metric(stage: dict[str, torch.Tensor], key: str) -> float:
    tensor = stage[key]
    return float(tensor.detach().float().mean().cpu().item())


def _channel_update_norm(
    h_prev: torch.Tensor | None,
    h_curr: torch.Tensor,
) -> float:
    if h_prev is None:
        return float("nan")
    prev = h_prev.detach().float()
    curr = h_curr.detach().float()
    diff = (curr - prev).norm(dim=-1)
    denom = prev.norm(dim=-1).clamp_min(1e-8)
    return float((diff / denom).mean().cpu().item())


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


def _write_csv(path: pathlib.Path, rows: list[dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _set_seed(seed: int):
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))


def _parse_float_grid(values: list[str] | None, default: list[float]) -> list[float]:
    if not values:
        return list(default)
    return [float(v) for v in values]


def _parse_int_grid(values: list[str] | None, default: list[int]) -> list[int]:
    if not values:
        return list(default)
    return [int(v) for v in values]


def _build_batches(
    sys_obj,
    device: torch.device,
    snr_list: list[int],
    frames: int,
    seed: int,
) -> dict[int, SharedBatch]:
    _set_seed(seed)
    batches, _data_pos = _generate_shared_batches(
        sys_obj=sys_obj,
        device=device,
        snr_list=snr_list,
        frames=frames,
    )
    del _data_pos
    return batches


def _make_profile_rows(
    model,
    batches: dict[int, SharedBatch],
    data_pos: np.ndarray,
    snr_list: list[int],
    profile_defs: list[tuple[str, dict[str, float]]],
    seed: int,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[int, float]]:
    rows: list[dict[str, Any]] = []
    baseline_by_snr: dict[int, float] = {}
    for profile_name, overrides in profile_defs:
        for snr_db in snr_list:
            stats = _evaluate_stage6_profile(
                model,
                batches[int(snr_db)],
                data_pos,
                overrides,
                eval_batch_size=eval_batch_size,
            )
            ber = float(stats["ber"])
            if profile_name == "baseline":
                baseline_by_snr[int(snr_db)] = ber
            rows.append(
                {
                    "seed": int(seed),
                    "profile": profile_name,
                    "snr_db": int(snr_db),
                    "ber": ber,
                    "alpha": float(overrides["alpha"]),
                    "sigma_inflation": float(overrides["detector_sigma_inflation"]),
                    "support_count_mean": float(stats["support_count_mean"]),
                    "seed_count_mean": float(stats["seed_count_mean"]),
                    "final_sigma_eff_mean": float(stats["final_sigma_eff_mean"]),
                }
            )
    return rows, baseline_by_snr


def _surface_rows(
    model,
    batches: dict[int, SharedBatch],
    data_pos: np.ndarray,
    snr_list: list[int],
    alpha_grid: list[float],
    sigma_grid: list[float],
    baseline_by_snr: dict[int, float],
    seed: int,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    best_by_snr: dict[str, dict[str, Any]] = {}
    for snr_db in snr_list:
        batch = batches[int(snr_db)]
        best_row = None
        for alpha in alpha_grid:
            for sigma_inflation in sigma_grid:
                overrides = {
                    "alpha": float(alpha),
                    "detector_sigma_inflation": float(sigma_inflation),
                }
                stats = _evaluate_stage6_profile(
                    model,
                    batch,
                    data_pos,
                    overrides,
                    eval_batch_size=eval_batch_size,
                )
                ber = float(stats["ber"])
                row = {
                    "seed": int(seed),
                    "snr_db": int(snr_db),
                    "alpha": float(alpha),
                    "sigma_inflation": float(sigma_inflation),
                    "candidate_ber": ber,
                    "anchor_ber": baseline_by_snr[int(snr_db)],
                    "rel_improvement": float((baseline_by_snr[int(snr_db)] - ber) / max(baseline_by_snr[int(snr_db)], 1e-12)),
                }
                rows.append(row)
                if best_row is None or ber < float(best_row["candidate_ber"]):
                    best_row = row
        assert best_row is not None
        best_by_snr[str(int(snr_db))] = dict(best_row)
    return rows, best_by_snr


def _best_constant_from_rows(rows: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[tuple[float, float], list[float]] = {}
    for row in rows:
        key = (float(row["alpha"]), float(row["sigma_inflation"]))
        grouped.setdefault(key, []).append(float(row["candidate_ber"]))
    best_key = min(grouped.keys(), key=lambda k: float(np.mean(grouped[k])))
    return {
        "alpha": float(best_key[0]),
        "sigma_inflation": float(best_key[1]),
        "mean_ber": float(np.mean(grouped[best_key])),
    }


def _sigma_only_rows(
    model,
    batches: dict[int, SharedBatch],
    data_pos: np.ndarray,
    snr_list: list[int],
    fixed_alpha: float,
    sigma_grid: list[float],
    baseline_by_snr: dict[int, float],
    seed: int,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    best_by_snr: dict[str, dict[str, Any]] = {}
    sigma_to_bers: dict[float, list[float]] = {float(s): [] for s in sigma_grid}
    for snr_db in snr_list:
        batch = batches[int(snr_db)]
        best_row = None
        for sigma_inflation in sigma_grid:
            overrides = {
                "alpha": float(fixed_alpha),
                "detector_sigma_inflation": float(sigma_inflation),
            }
            stats = _evaluate_stage6_profile(
                model,
                batch,
                data_pos,
                overrides,
                eval_batch_size=eval_batch_size,
            )
            ber = float(stats["ber"])
            sigma_to_bers[float(sigma_inflation)].append(ber)
            row = {
                "seed": int(seed),
                "snr_db": int(snr_db),
                "alpha": float(fixed_alpha),
                "sigma_inflation": float(sigma_inflation),
                "candidate_ber": ber,
                "anchor_ber": baseline_by_snr[int(snr_db)],
                "rel_improvement": float((baseline_by_snr[int(snr_db)] - ber) / max(baseline_by_snr[int(snr_db)], 1e-12)),
            }
            rows.append(row)
            if best_row is None or ber < float(best_row["candidate_ber"]):
                best_row = row
        assert best_row is not None
        best_by_snr[str(int(snr_db))] = dict(best_row)
    sigma_mean_ber = {
        str(float(sigma)): float(np.mean(vals)) if vals else float("nan")
        for sigma, vals in sigma_to_bers.items()
    }
    return rows, best_by_snr, sigma_mean_ber


def _best_sigma_from_rows(rows: list[dict[str, Any]], fixed_alpha: float) -> dict[str, float]:
    grouped: dict[float, list[float]] = {}
    for row in rows:
        sigma = float(row["sigma_inflation"])
        grouped.setdefault(sigma, []).append(float(row["candidate_ber"]))
    best_sigma = min(grouped.keys(), key=lambda s: float(np.mean(grouped[s])))
    return {
        "alpha": float(fixed_alpha),
        "sigma_inflation": float(best_sigma),
        "mean_ber": float(np.mean(grouped[best_sigma])),
    }


def _iterlayer_grid(alpha_star: float, sigma_star: float) -> tuple[list[float], list[float]]:
    alpha_grid = sorted(
        {
            round(max(0.90, alpha_star - 0.05), 6),
            round(alpha_star, 6),
            round(min(0.999, alpha_star + 0.01), 6),
        }
    )
    sigma_grid = sorted(
        {
            round(max(1.0, sigma_star / 2.0), 6),
            round(sigma_star, 6),
            round(min(12.0, sigma_star * 1.5), 6),
        }
    )
    return alpha_grid, sigma_grid


def _evaluate_sigma_schedule_rows(
    model,
    batches: dict[int, SharedBatch],
    data_pos: np.ndarray,
    snr_list: list[int],
    sigma_only_best_by_snr: dict[str, dict[str, Any]],
    num_outer_iters: int,
    fixed_alpha: float,
    sigma_early_grid: list[float],
    sigma_late_grid: list[float],
    seed: int,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    best_json: dict[str, dict[str, Any]] = {}
    for snr_db in snr_list:
        best_const = sigma_only_best_by_snr[str(int(snr_db))]
        batch = batches[int(snr_db)]
        best_row = None
        for sigma_early in sigma_early_grid:
            for sigma_late in sigma_late_grid:
                overrides = {
                    "alpha": [float(fixed_alpha)] * max(num_outer_iters, 1),
                    "detector_sigma_inflation": [float(sigma_early), float(sigma_early)] + [float(sigma_late)] * max(num_outer_iters - 2, 0),
                }
                stats = _evaluate_stage6_profile(
                    model,
                    batch,
                    data_pos,
                    overrides,
                    eval_batch_size=eval_batch_size,
                )
                ber = float(stats["ber"])
                row = {
                    "seed": int(seed),
                    "snr_db": int(snr_db),
                    "alpha": float(fixed_alpha),
                    "sigma_early": float(sigma_early),
                    "sigma_late": float(sigma_late),
                    "candidate_ber": ber,
                    "sigma_only_best_ber": float(best_const["candidate_ber"]),
                    "rel_improvement_over_sigma_only_best": float(
                        (float(best_const["candidate_ber"]) - ber) / max(float(best_const["candidate_ber"]), 1e-12)
                    ),
                }
                rows.append(row)
                if best_row is None or ber < float(best_row["candidate_ber"]):
                    best_row = row
        assert best_row is not None
        best_json[str(int(snr_db))] = dict(best_row)
    return rows, best_json


def _evaluate_iterlayer_rows(
    model,
    batches: dict[int, SharedBatch],
    data_pos: np.ndarray,
    snr_list: list[int],
    best_by_snr: dict[str, dict[str, Any]],
    num_outer_iters: int,
    seed: int,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    best_json: dict[str, dict[str, Any]] = {}
    for snr_db in snr_list:
        best_const = best_by_snr[str(int(snr_db))]
        alpha_grid, sigma_grid = _iterlayer_grid(float(best_const["alpha"]), float(best_const["sigma_inflation"]))
        batch = batches[int(snr_db)]
        best_row = None
        for alpha_1 in alpha_grid:
            for sigma_1 in sigma_grid:
                for alpha_late in alpha_grid:
                    for sigma_late in sigma_grid:
                        overrides = {
                            "alpha": [float(alpha_1)] + [float(alpha_late)] * max(num_outer_iters - 1, 0),
                            "detector_sigma_inflation": [float(sigma_1)] + [float(sigma_late)] * max(num_outer_iters - 1, 0),
                        }
                        stats = _evaluate_stage6_profile(
                            model,
                            batch,
                            data_pos,
                            overrides,
                            eval_batch_size=eval_batch_size,
                        )
                        ber = float(stats["ber"])
                        row = {
                            "seed": int(seed),
                            "snr_db": int(snr_db),
                            "alpha_1": float(alpha_1),
                            "sigma_1": float(sigma_1),
                            "alpha_late": float(alpha_late),
                            "sigma_late": float(sigma_late),
                            "candidate_ber": ber,
                            "best_constant_ber": float(best_const["candidate_ber"]),
                            "rel_improvement_over_best_constant": float(
                                (float(best_const["candidate_ber"]) - ber) / max(float(best_const["candidate_ber"]), 1e-12)
                            ),
                        }
                        rows.append(row)
                        if best_row is None or ber < float(best_row["candidate_ber"]):
                            best_row = row
        assert best_row is not None
        best_json[str(int(snr_db))] = dict(best_row)
    return rows, best_json


def _collect_profile_diagnostics(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    profile_defs: list[tuple[str, dict[str, Any]]],
    seeds: list[int],
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    trace_rows: list[dict[str, Any]] = []
    calib_rows: list[dict[str, Any]] = []
    for seed in seeds:
        batches = seed_batches[int(seed)]
        for profile_name, overrides in profile_defs:
            for snr_db in snr_list:
                local_overrides = dict(overrides)
                if "vx_recalibration_learned_payload" in local_overrides:
                    local_overrides["vx_recalibration_learned_snr_db"] = float(snr_db)
                stats = _evaluate_stage6_profile(
                    model,
                    batches[int(snr_db)],
                    data_pos,
                    local_overrides,
                    eval_batch_size=eval_batch_size,
                    collect_traces=True,
                )
                for t, (trace_stage, calib_stage) in enumerate(zip(stats["trace_history"], stats["calibration_history"])):
                    trace_rows.append(
                        {
                            "seed": int(seed),
                            "profile": profile_name,
                            "snr_db": int(snr_db),
                            "outer_iter": int(t),
                            "ber": float(trace_stage["ber"]),
                            "residual_energy_mean": float(trace_stage["residual_energy_mean"]),
                            "sigma_eff_mean": float(trace_stage["sigma_eff_mean"]),
                            "vx_mean": float(trace_stage["vx_mean"]),
                            "channel_update_norm": float(trace_stage["channel_update_norm"]),
                            "sic_weight_mean": float(trace_stage["sic_weight_mean"]),
                            "vx_recal_gain_mean": float(trace_stage["vx_recal_gain_mean"]),
                        }
                    )
                    calib_rows.append(
                        {
                            "seed": int(seed),
                            "profile": profile_name,
                            "snr_db": int(snr_db),
                            "outer_iter": int(t),
                            "ber": float(trace_stage["ber"]),
                            "sym_err_mean": float(calib_stage["sym_err_mean"]),
                            "vx_mean": float(calib_stage["vx_mean"]),
                            "rho": float(calib_stage["calibration_ratio"]),
                            "empirical_residual_var": float(calib_stage["empirical_residual_var"]),
                            "detector_sigma_mean": float(calib_stage["detector_sigma_mean"]),
                            "eta": float(calib_stage["sigma_gap_ratio"]),
                            "channel_update_norm": float(calib_stage["channel_update_norm"]),
                            "sigma_eff_mean": float(trace_stage["sigma_eff_mean"]),
                            "sigma_ls_mean": float(calib_stage["sigma_ls_mean"]),
                            "residual_energy_mean": float(trace_stage["residual_energy_mean"]),
                            "post_sic_residual_energy": float(calib_stage["post_sic_residual_energy"]),
                            "sic_weight_mean": float(calib_stage["sic_weight_mean"]),
                            "vx_recal_gain_mean": float(calib_stage["vx_recal_gain_mean"]),
                        }
                    )
    return trace_rows, calib_rows


def _collect_profile_frame_calibration(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    profile_defs: list[tuple[str, dict[str, Any]]],
    seeds: list[int],
    eval_batch_size: int,
) -> list[dict[str, Any]]:
    frame_rows: list[dict[str, Any]] = []
    for seed in seeds:
        batches = seed_batches[int(seed)]
        for profile_name, overrides in profile_defs:
            for snr_db in snr_list:
                local_overrides = dict(overrides)
                if "vx_recalibration_learned_payload" in local_overrides:
                    local_overrides["vx_recalibration_learned_snr_db"] = float(snr_db)
                stats = _evaluate_stage6_profile(
                    model,
                    batches[int(snr_db)],
                    data_pos,
                    local_overrides,
                    eval_batch_size=eval_batch_size,
                    collect_traces=False,
                    collect_frame_calibration=True,
                )
                for row in stats.get("frame_calibration_rows", []):
                    frame_rows.append(
                        {
                            "seed": int(seed),
                            "profile": str(profile_name),
                            "snr_db": int(snr_db),
                            **row,
                        }
                    )
    return frame_rows


def _best_pair_from_rows(
    rows: list[dict[str, Any]],
    key_names: tuple[str, str],
) -> dict[str, float]:
    grouped: dict[tuple[float, float], list[float]] = {}
    for row in rows:
        key = (float(row[key_names[0]]), float(row[key_names[1]]))
        grouped.setdefault(key, []).append(float(row["candidate_ber"]))
    best_key = min(grouped.keys(), key=lambda k: float(np.mean(grouped[k])))
    return {
        key_names[0]: float(best_key[0]),
        key_names[1]: float(best_key[1]),
        "mean_ber": float(np.mean(grouped[best_key])),
    }


def _evaluate_sigma_early_fix_rows(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    seeds: list[int],
    num_outer_iters: int,
    sigma_early_grid: list[float],
    sigma_late_grid: list[float],
    fixed_best_by_seed: dict[str, dict[int, float]],
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, float], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    best_by_seed: dict[str, dict[str, Any]] = {}
    avg_gain_by_seed: dict[str, float] = {}
    for seed in seeds:
        seed_rows: list[dict[str, Any]] = []
        best_by_snr: dict[str, Any] = {}
        for snr_db in snr_list:
            best_row = None
            for sigma_early in sigma_early_grid:
                for sigma_late in sigma_late_grid:
                    overrides = {
                        "alpha": [1.0] * max(num_outer_iters, 1),
                        "detector_sigma_inflation": [float(sigma_early)] + [float(sigma_late)] * max(num_outer_iters - 1, 0),
                    }
                    stats = _evaluate_stage6_profile(
                        model,
                        seed_batches[int(seed)][int(snr_db)],
                        data_pos,
                        overrides,
                        eval_batch_size=eval_batch_size,
                    )
                    ber = float(stats["ber"])
                    row = {
                        "seed": int(seed),
                        "snr_db": int(snr_db),
                        "sigma_early": float(sigma_early),
                        "sigma_late": float(sigma_late),
                        "candidate_ber": ber,
                        "fixed_best_ber": float(fixed_best_by_seed[str(int(seed))][int(snr_db)]),
                        "rel_improvement_over_fixed_best": float(
                            (float(fixed_best_by_seed[str(int(seed))][int(snr_db)]) - ber)
                            / max(float(fixed_best_by_seed[str(int(seed))][int(snr_db)]), 1e-12)
                        ),
                    }
                    rows.append(row)
                    seed_rows.append(row)
                    if best_row is None or ber < float(best_row["candidate_ber"]):
                        best_row = row
            assert best_row is not None
            best_by_snr[str(int(snr_db))] = dict(best_row)
        best_by_seed[str(int(seed))] = best_by_snr
        avg_gain_by_seed[str(int(seed))] = float(
            np.mean([float(x["rel_improvement_over_fixed_best"]) for x in best_by_snr.values()])
        )
    best_global = _best_pair_from_rows(rows, ("sigma_early", "sigma_late"))
    return rows, best_by_seed, avg_gain_by_seed, best_global


def _evaluate_residual_aware_rows(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    seeds: list[int],
    c0_grid: list[float],
    cr_grid: list[float],
    fixed_best_by_seed: dict[str, dict[int, float]],
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, float], dict[str, float]]:
    rows: list[dict[str, Any]] = []
    best_by_seed: dict[str, dict[str, Any]] = {}
    avg_gain_by_seed: dict[str, float] = {}
    for seed in seeds:
        best_by_snr: dict[str, Any] = {}
        for snr_db in snr_list:
            best_row = None
            for c0 in c0_grid:
                for cr in cr_grid:
                    overrides = {
                        "alpha": 1.0,
                        "detector_sigma_c0": float(c0),
                        "detector_sigma_cr": float(cr),
                    }
                    stats = _evaluate_stage6_profile(
                        model,
                        seed_batches[int(seed)][int(snr_db)],
                        data_pos,
                        overrides,
                        eval_batch_size=eval_batch_size,
                    )
                    ber = float(stats["ber"])
                    row = {
                        "seed": int(seed),
                        "snr_db": int(snr_db),
                        "c0": float(c0),
                        "cr": float(cr),
                        "candidate_ber": ber,
                        "fixed_best_ber": float(fixed_best_by_seed[str(int(seed))][int(snr_db)]),
                        "rel_improvement_over_fixed_best": float(
                            (float(fixed_best_by_seed[str(int(seed))][int(snr_db)]) - ber)
                            / max(float(fixed_best_by_seed[str(int(seed))][int(snr_db)]), 1e-12)
                        ),
                    }
                    rows.append(row)
                    if best_row is None or ber < float(best_row["candidate_ber"]):
                        best_row = row
            assert best_row is not None
            best_by_snr[str(int(snr_db))] = dict(best_row)
        best_by_seed[str(int(seed))] = best_by_snr
        avg_gain_by_seed[str(int(seed))] = float(
            np.mean([float(x["rel_improvement_over_fixed_best"]) for x in best_by_snr.values()])
        )
    best_global = _best_pair_from_rows(rows, ("c0", "cr"))
    return rows, best_by_seed, avg_gain_by_seed, best_global


def _profile_summary_md(
    rows: list[dict[str, Any]],
    profile_defs: list[tuple[str, dict[str, float]]],
) -> str:
    lines = [
        "# Stage8 Stage6 Heuristic Profiles",
        "",
        "## Profiles",
        "",
    ]
    for name, overrides in profile_defs:
        lines.append(f"- `{name}`: `{overrides}`")
    lines.extend(["", "## BER", ""])
    by_profile: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_profile.setdefault(str(row["profile"]), []).append(row)
    for profile, items in by_profile.items():
        lines.append(f"### {profile}")
        lines.append("")
        for item in sorted(items, key=lambda x: int(x["snr_db"])):
            lines.append(
                f"- `{item['snr_db']} dB`: ber=`{item['ber']:.4e}`, "
                f"support_mean=`{item['support_count_mean']:.2f}`, "
                f"sigma_eff_mean=`{item['final_sigma_eff_mean']:.4e}`"
            )
        lines.append("")
    return "\n".join(lines)


def _surface_summary_md(
    best_by_snr: dict[str, dict[str, Any]],
    alpha_span: float,
    sigma_unique_count: int,
    alpha95_sigma4_gap: float,
    verdict: str,
) -> str:
    lines = [
        "# Stage8 Alpha-Sigma Surface Summary",
        "",
        "## Best By SNR",
        "",
    ]
    for snr_key, item in sorted(best_by_snr.items(), key=lambda kv: int(kv[0])):
        lines.append(
            f"- `{snr_key} dB`: alpha=`{item['alpha']:.2f}`, sigma_inflation=`{item['sigma_inflation']:.2f}`, "
            f"ber=`{item['candidate_ber']:.4e}`, rel_improve=`{item['rel_improvement']:.3%}`"
        )
    lines.extend(
        [
            "",
            "## Decision Metrics",
            "",
            f"- alpha_span: `{alpha_span:.3f}`",
            f"- sigma_unique_count: `{sigma_unique_count}`",
            f"- alpha95_sigma4_gap_to_best: `{alpha95_sigma4_gap:.3%}`",
            "",
            "## Verdict",
            "",
        ]
    )
    if verdict == "fixed":
        lines.append(
            "- Recommendation: keep fixing heuristics first. "
            "`alpha` behaves like a fixed-anchor correction after sigma calibration."
        )
    else:
        lines.append(
            "- Recommendation: move to a state-dependent local alpha gate. "
            "A fixed alpha is not sufficient after sigma calibration."
        )
    return "\n".join(lines)


def _expanded_summary_md(
    seed_best: dict[str, dict[str, dict[str, Any]]],
    edge_summary: dict[str, Any],
    consistent_region: bool,
) -> str:
    lines = [
        "# Stage8 Expanded Best-Constant Summary",
        "",
        "## Best By Seed And SNR",
        "",
    ]
    for seed_key, best_by_snr in seed_best.items():
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(best_by_snr.items(), key=lambda kv: int(kv[0])):
            edge = edge_summary["by_seed"][seed_key][snr_key]
            lines.append(
                f"- `{snr_key} dB`: alpha=`{item['alpha']:.3f}`, sigma=`{item['sigma_inflation']:.2f}`, "
                f"ber=`{item['candidate_ber']:.4e}`, on_edge=`{edge}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Aggregate",
            "",
            f"- any_edge_hit: `{edge_summary['any_edge_hit']}`",
            f"- consistent_best_region: `{consistent_region}`",
            "",
            "## Interpretation",
            "",
        ]
    )
    if edge_summary["any_edge_hit"]:
        lines.append("- Verdict: `A. 仍撞边界 -> 继续 fixed retune`")
    elif consistent_region:
        lines.append("- Verdict: expanded best-constant has stabilized into an interior region.")
    else:
        lines.append("- Verdict: interior optimum exists, but cross-seed stability is still weak.")
    return "\n".join(lines)


def _sigma_only_summary_md(
    best_by_snr: dict[str, dict[str, Any]],
    sigma_mean_ber: dict[str, float],
    sigma_grid: list[float],
) -> str:
    lines = [
        "# Stage8 Sigma-Only Plateau Summary",
        "",
        "## Best By SNR",
        "",
    ]
    for snr_key, item in sorted(best_by_snr.items(), key=lambda kv: int(kv[0])):
        lines.append(
            f"- `{snr_key} dB`: alpha=`{item['alpha']:.4f}`, sigma=`{item['sigma_inflation']:.2f}`, "
            f"ber=`{item['candidate_ber']:.4e}`, rel_improve=`{item['rel_improvement']:.3%}`"
        )
    lines.extend(["", "## Mean BER By Sigma", ""])
    sigma_vals = [float(s) for s in sigma_grid]
    for sigma in sigma_vals:
        lines.append(f"- sigma=`{sigma:.2f}`: mean_ber=`{float(sigma_mean_ber[str(float(sigma))]):.4e}`")
    lines.extend(["", "## Interpretation", ""])
    best_sigmas = [float(x["sigma_inflation"]) for x in best_by_snr.values()]
    if all(np.isclose(s, max(sigma_vals)) for s in best_sigmas):
        lines.append("- Verdict: `sigma` 最优值仍在扫描上边界，平台尚未被严格坐实。")
    else:
        lines.append("- Verdict: `sigma` 最优值已进入扫描内部区域，可视为接近平台。")
    lines.append("- 检查 calibration 曲线与 residual proxy，判断大 sigma 是否已经进入过保守区。")
    return "\n".join(lines)


def _iterlayer_summary_md(
    best_constant_global: dict[str, dict[str, float]],
    iterlayer_best: dict[str, dict[str, dict[str, Any]]],
    avg_improvement_by_seed: dict[str, float],
    consistent_gate_gain: bool,
    verdict: str,
) -> str:
    lines = [
        "# Stage8 Iter-Layered Oracle Summary",
        "",
        "## Best-Constant Reference",
        "",
    ]
    for seed_key, item in best_constant_global.items():
        lines.append(
            f"- seed `{seed_key}`: alpha=`{item['alpha']:.3f}`, sigma=`{item['sigma_inflation']:.2f}`, "
            f"mean_ber=`{item['mean_ber']:.4e}`"
        )
    lines.extend(["", "## Iter-Layered Best By Seed And SNR", ""])
    for seed_key, best_by_snr in iterlayer_best.items():
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(best_by_snr.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: "
                f"(alpha1, sigma1)=(`{item['alpha_1']:.3f}`, `{item['sigma_1']:.2f}`), "
                f"(alpha_late, sigma_late)=(`{item['alpha_late']:.3f}`, `{item['sigma_late']:.2f}`), "
                f"rel_gain_vs_best_constant=`{item['rel_improvement_over_best_constant']:.3%}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Aggregate",
            "",
        ]
    )
    for seed_key, gain in avg_improvement_by_seed.items():
        lines.append(f"- seed `{seed_key}` average gain vs best-constant: `{gain:.3%}`")
    lines.append(f"- consistent_gate_gain: `{consistent_gate_gain}`")
    lines.extend(["", "## Verdict", ""])
    if verdict == "gate":
        lines.append("- Verdict: `C. iter-layered oracle 明显优于 best-constant -> 进入 local alpha/sigma gate 设计`")
    else:
        lines.append("- Verdict: iter-layered oracle does not justify a learned gate yet; keep best-constant as the main candidate baseline.")
    return "\n".join(lines)


def _sigma_schedule_summary_md(
    sigma_only_global_by_seed: dict[str, dict[str, float]],
    schedule_best_by_seed: dict[str, dict[str, dict[str, Any]]],
    avg_improvement_by_seed: dict[str, float],
    success: bool,
) -> str:
    lines = [
        "# Stage8 Sigma Schedule v1 Summary",
        "",
        "## Sigma-Only Reference",
        "",
    ]
    for seed_key, item in sigma_only_global_by_seed.items():
        lines.append(
            f"- seed `{seed_key}`: alpha=`{item['alpha']:.4f}`, sigma=`{item['sigma_inflation']:.2f}`, "
            f"mean_ber=`{item['mean_ber']:.4e}`"
        )
    lines.extend(["", "## Best By Seed And SNR", ""])
    for seed_key, best_by_snr in schedule_best_by_seed.items():
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(best_by_snr.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: sigma_early=`{item['sigma_early']:.2f}`, "
                f"sigma_late=`{item['sigma_late']:.2f}`, "
                f"rel_gain_vs_sigma_only=`{item['rel_improvement_over_sigma_only_best']:.3%}`"
            )
        lines.append("")
    lines.extend(["## Aggregate", ""])
    for seed_key, gain in avg_improvement_by_seed.items():
        lines.append(f"- seed `{seed_key}` average gain vs sigma-only best: `{gain:.3%}`")
    lines.extend(["", "## Verdict", ""])
    if success:
        lines.append("- Verdict: `sigma schedule v1` 已明显优于 `sigma-only best`，值得进入 uncertainty model 公式化修正。")
    else:
        lines.append("- Verdict: 全局 sigma 常数已足够强，当前不急着做时变 sigma 模型。")
    return "\n".join(lines)


def _fixed_best_summary_md(
    rows: list[dict[str, Any]],
    alpha: float,
    sigma: float,
) -> str:
    lines = [
        "# Stage9 Stage6 Fixed-Best Summary",
        "",
        f"- fixed_best = `(alpha={alpha:.4f}, sigma={sigma:.2f})`",
        "",
        "## BER By Seed / SNR",
        "",
    ]
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["snr_db"]), []).append(row)
    for snr_db, items in sorted(grouped.items()):
        mean_ber = float(np.mean([float(x["ber"]) for x in items]))
        lines.append(f"- `{snr_db} dB`: mean_ber=`{mean_ber:.4e}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This profile is the current strongest fixed reference for Stage6 uncertainty-model experiments.",
        ]
    )
    return "\n".join(lines)


def _calibration_dataset_summary_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage9 Calibration Dataset Summary",
        "",
        "## Aggregate By Profile",
        "",
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["profile"]), []).append(row)
    for profile, items in sorted(grouped.items()):
        rho_vals = [float(x["rho"]) for x in items]
        eta_vals = [float(x["eta"]) for x in items]
        lines.append(
            f"- `{profile}`: mean_rho=`{np.mean(rho_vals):.3f}`, "
            f"mean_eta=`{np.mean(eta_vals):.3f}`"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `rho = sym_err / v_x` near `1` means detector posterior variance is better calibrated.",
            "- `eta = empirical_residual_var / detector_sigma` near `1` means detector-used sigma better matches the observed residual scale.",
        ]
    )
    return "\n".join(lines)


def _sigma_early_fix_summary_md(
    fixed_best_mean_ber: float,
    best_by_seed: dict[str, dict[str, Any]],
    avg_gain_by_seed: dict[str, float],
    best_global: dict[str, float],
    success: bool,
) -> str:
    lines = [
        "# Stage9 Sigma Early-Fix Summary",
        "",
        f"- fixed_best mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- best_global `(sigma_early, sigma_late)=({best_global['sigma_early']:.2f}, {best_global['sigma_late']:.2f})`, "
        f"mean_ber=`{best_global['mean_ber']:.4e}`",
        "",
        "## Best By Seed / SNR",
        "",
    ]
    for seed_key, items in sorted(best_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(items.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: sigma_early=`{item['sigma_early']:.2f}`, "
                f"sigma_late=`{item['sigma_late']:.2f}`, "
                f"rel_gain_vs_fixed_best=`{item['rel_improvement_over_fixed_best']:.3%}`"
            )
        lines.append("")
    lines.extend(["## Aggregate", ""])
    for seed_key, gain in sorted(avg_gain_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"- seed `{seed_key}` avg gain vs fixed_best: `{gain:.3%}`")
    lines.extend(["", "## Verdict", ""])
    if success:
        lines.append("- Verdict: early-only sigma correction is strong enough to replace the current fixed-best baseline.")
    else:
        lines.append("- Verdict: early-only sigma correction is not yet strong enough to replace the fixed-best baseline.")
    return "\n".join(lines)


def _residual_aware_sigma_summary_md(
    fixed_best_mean_ber: float,
    best_by_seed: dict[str, dict[str, Any]],
    avg_gain_by_seed: dict[str, float],
    best_global: dict[str, float],
    success: bool,
) -> str:
    lines = [
        "# Stage9 Residual-Aware Sigma v2 Summary",
        "",
        f"- fixed_best mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- best_global `(c0, cr)=({best_global['c0']:.3f}, {best_global['cr']:.3f})`, "
        f"mean_ber=`{best_global['mean_ber']:.4e}`",
        "",
        "## Best By Seed / SNR",
        "",
    ]
    for seed_key, items in sorted(best_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(items.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: c0=`{item['c0']:.3f}`, cr=`{item['cr']:.3f}`, "
                f"rel_gain_vs_fixed_best=`{item['rel_improvement_over_fixed_best']:.3%}`"
            )
        lines.append("")
    lines.extend(["## Aggregate", ""])
    for seed_key, gain in sorted(avg_gain_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"- seed `{seed_key}` avg gain vs fixed_best: `{gain:.3%}`")
    lines.extend(["", "## Verdict", ""])
    if success:
        lines.append("- Verdict: residual-aware sigma v2 stably beats the fixed-best baseline and is the main detector uncertainty-model candidate.")
    else:
        lines.append("- Verdict: residual-aware sigma v2 has not yet stably replaced the fixed-best baseline.")
    return "\n".join(lines)


def _fit_vx_recalibration_coeffs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_iter: dict[int, list[float]] = {}
    for row in rows:
        outer_iter = int(row["outer_iter"])
        vx_mean = max(float(row["vx_mean"]), 1e-8)
        sym_err_mean = float(row["sym_err_mean"])
        by_iter.setdefault(outer_iter, []).append(sym_err_mean / vx_mean)
    coeffs_by_iter: dict[str, float] = {}
    for outer_iter, vals in sorted(by_iter.items()):
        coeff = float(np.median(np.asarray(vals, dtype=np.float64)))
        coeffs_by_iter[str(int(outer_iter))] = float(np.clip(coeff, 0.25, 64.0))
    coeff_list = [coeffs_by_iter[str(i)] for i in sorted(int(k) for k in coeffs_by_iter.keys())]
    return {
        "coeffs_by_iter": coeffs_by_iter,
        "coeff_list": coeff_list,
    }


def _fit_vx_recalibration_affine_coeffs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_iter: dict[int, list[tuple[float, float]]] = {}
    for row in rows:
        outer_iter = int(row["outer_iter"])
        by_iter.setdefault(outer_iter, []).append(
            (float(row["vx_mean"]), float(row["sym_err_mean"]))
        )
    a_by_iter: dict[str, float] = {}
    b_by_iter: dict[str, float] = {}
    a_list: list[float] = []
    b_list: list[float] = []
    for outer_iter, pairs in sorted(by_iter.items()):
        x = np.asarray([max(vx, 1e-8) for vx, _ in pairs], dtype=np.float64)
        y = np.asarray([max(sym, 0.0) for _, sym in pairs], dtype=np.float64)
        design = np.stack([x, np.ones_like(x)], axis=1)
        sol, *_ = np.linalg.lstsq(design, y, rcond=None)
        a_ols = float(sol[0])
        b_ols = float(sol[1])
        ratio_med = float(np.median(y / x))
        y_med = float(np.median(y))
        blend = 0.35
        a_t = float(np.clip((1.0 - blend) * 1.0 + blend * a_ols, 0.25, 16.0))
        a_t = float(np.clip(0.5 * a_t + 0.5 * np.clip(ratio_med, 0.25, 16.0), 0.25, 16.0))
        b_cap = max(1e-4, 0.5 * y_med)
        b_t = float(np.clip(blend * max(b_ols, 0.0), 0.0, b_cap))
        a_by_iter[str(int(outer_iter))] = a_t
        b_by_iter[str(int(outer_iter))] = b_t
        a_list.append(a_t)
        b_list.append(b_t)
    return {
        "a_by_iter": a_by_iter,
        "b_by_iter": b_by_iter,
        "a_list": a_list,
        "b_list": b_list,
    }


def _fit_vx_recalibration_clipped_coeffs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_iter: dict[int, list[dict[str, float]]] = {}
    for row in rows:
        outer_iter = int(row["outer_iter"])
        by_iter.setdefault(outer_iter, []).append(
            {
                "vx_mean": float(row["vx_mean"]),
                "sym_err_mean": float(row["sym_err_mean"]),
            }
        )
    scale_by_iter: dict[str, float] = {}
    vmin_by_iter: dict[str, float] = {}
    vmax_by_iter: dict[str, float] = {}
    scale_list: list[float] = []
    vmin_list: list[float] = []
    vmax_list: list[float] = []
    for outer_iter, items in sorted(by_iter.items()):
        vx_vals = np.asarray([max(x["vx_mean"], 1e-8) for x in items], dtype=np.float64)
        sym_vals = np.asarray([max(x["sym_err_mean"], 0.0) for x in items], dtype=np.float64)
        scale_raw = float(np.median(sym_vals / vx_vals))
        scale_t = float(np.clip(0.5 * 1.0 + 0.5 * scale_raw, 0.25, 32.0))
        scaled_vals = np.clip(scale_t * vx_vals, 1e-4, 2.0)
        vmin_t = float(np.clip(np.percentile(scaled_vals, 10.0), 1e-4, 2.0))
        vmax_t = float(np.clip(np.percentile(scaled_vals, 90.0), 1e-4, 2.0))
        min_span = max(5e-4, 0.10 * float(np.median(scaled_vals)))
        vmax_t = max(vmax_t, vmin_t + min_span)
        vmax_t = float(np.clip(vmax_t, 1e-4, 2.0))
        if vmax_t <= vmin_t:
            vmax_t = min(2.0, vmin_t + min_span)
        scale_by_iter[str(int(outer_iter))] = scale_t
        vmin_by_iter[str(int(outer_iter))] = vmin_t
        vmax_by_iter[str(int(outer_iter))] = vmax_t
        scale_list.append(scale_t)
        vmin_list.append(vmin_t)
        vmax_list.append(vmax_t)
    return {
        "scale_by_iter": scale_by_iter,
        "vmin_by_iter": vmin_by_iter,
        "vmax_by_iter": vmax_by_iter,
        "scale_list": scale_list,
        "vmin_list": vmin_list,
        "vmax_list": vmax_list,
    }


def _vx_recalibration_coeffs_summary_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Stage11 VX Recalibration v1 Coefficients",
        "",
        "## Per-Iteration Scale",
        "",
    ]
    for iter_key, coeff in payload["coeffs_by_iter"].items():
        lines.append(f"- iter `{iter_key}`: c_t=`{float(coeff):.4f}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Coefficients are fitted from `fixed_best` calibration data using the median `sym_err_mean / vx_mean` per iteration.",
            "- Values are clipped into `[0.25, 64]` and then applied as `v_x_cal = clip(c_t * v_x, 1e-4, 2.0)`.",
        ]
    )
    return "\n".join(lines)


def _vx_recalibration_affine_coeffs_summary_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Stage11 VX Recalibration v2 Affine Coefficients",
        "",
        "## Per-Iteration Affine Parameters",
        "",
    ]
    for iter_key in payload["a_by_iter"].keys():
        lines.append(
            f"- iter `{iter_key}`: a_t=`{float(payload['a_by_iter'][iter_key]):.4f}`, "
            f"b_t=`{float(payload['b_by_iter'][iter_key]):.4f}`"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Affine parameters are fitted from `fixed_best` calibration data using an identity-biased per-iteration affine fit from `vx_mean` to `sym_err_mean`.",
            "- The fit is intentionally conservative: `a_t` is kept away from zero and `b_t` is capped so the calibrated output preserves sample-level ordering instead of collapsing to a per-iteration constant.",
            "- The calibrated form is `v_x' = clamp(a_t * v_x + b_t, 1e-4, 2.0)`.",
        ]
    )
    return "\n".join(lines)


def _vx_recalibration_clipped_coeffs_summary_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Stage11 VX Recalibration v2 Clipped Coefficients",
        "",
        "## Per-Iteration Clipped Parameters",
        "",
    ]
    for iter_key in payload["scale_by_iter"].keys():
        lines.append(
            f"- iter `{iter_key}`: c_t=`{float(payload['scale_by_iter'][iter_key]):.4f}`, "
            f"vmin_t=`{float(payload['vmin_by_iter'][iter_key]):.4f}`, "
            f"vmax_t=`{float(payload['vmax_by_iter'][iter_key]):.4f}`"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Clipped parameters are fitted from `fixed_best` calibration data using a conservative median scale and quantiles of the scaled `v_x` distribution.",
            "- The clipping interval is forced to keep a non-zero span, so this variant acts as a boundary correction instead of collapsing each iteration to a fixed constant.",
            "- The calibrated form is `v_x' = clip(c_t * v_x, vmin_t, vmax_t)`.",
        ]
    )
    return "\n".join(lines)


def _task_aware_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    iter0_vals = [float(r["rho"]) for r in rows if int(r["outer_iter"]) == 0]
    late_vals = [float(r["rho"]) for r in rows if int(r["outer_iter"]) in {1, 2, 3, 4}]
    iter0_rho = float(np.mean(iter0_vals)) if iter0_vals else float("nan")
    late_rho_mean = float(np.mean(late_vals)) if late_vals else float("nan")
    early_optimism = max(iter0_rho - 1.0, 0.0) if iter0_rho == iter0_rho else float("nan")
    late_over = float(np.mean([max(1.0 - x, 0.0) for x in late_vals])) if late_vals else float("nan")
    task_score = early_optimism + late_over if early_optimism == early_optimism and late_over == late_over else float("nan")
    return {
        "iter0_rho": iter0_rho,
        "late_rho_mean": late_rho_mean,
        "early_optimism_score": early_optimism,
        "late_overconservatism_score": late_over,
        "task_balanced_score": task_score,
    }


def _task_risk_metrics(
    rows: list[dict[str, Any]],
    *,
    frame_rows: list[dict[str, Any]] | None = None,
    late_iters: tuple[int, ...] = (2, 3, 4),
    w0: float = 0.5,
    w1: float = 1.0,
    w2: float = 2.0,
) -> dict[str, float]:
    late_iter_set = {int(x) for x in late_iters}
    iter0_vals = [float(r["rho"]) for r in rows if int(r["outer_iter"]) == 0]
    late_vals = [float(r["rho"]) for r in rows if int(r["outer_iter"]) in late_iter_set]
    iter4_vals = [float(r["rho"]) for r in rows if int(r["outer_iter"]) == 4]
    iter0_rho = float(np.mean(iter0_vals)) if iter0_vals else float("nan")
    late_rho_mean = float(np.mean(late_vals)) if late_vals else float("nan")
    iter4_rho = float(np.mean(iter4_vals)) if iter4_vals else float("nan")
    early_optimism = max(iter0_rho - 1.0, 0.0) if iter0_rho == iter0_rho else float("nan")
    late_optimism_vals = [max(x - 1.0, 0.0) for x in late_vals]
    late_over_vals = [max(1.0 - x, 0.0) for x in late_vals]
    late_optimism = float(np.mean(late_optimism_vals)) if late_optimism_vals else float("nan")
    late_over = float(np.mean(late_over_vals)) if late_over_vals else float("nan")
    frame_worst_late_optimism = _frame_worst_late_optimism_from_rows(frame_rows or [], late_iters=late_iters)
    frame_term = 0.0 if frame_worst_late_optimism != frame_worst_late_optimism else float(frame_worst_late_optimism)
    if early_optimism == early_optimism and late_optimism == late_optimism and late_over == late_over:
        task_risk = (
            float(w0) * early_optimism
            + float(w1) * late_over
            + float(w2) * late_optimism
            + 2.0 * frame_term
        )
    else:
        task_risk = float("nan")

    return {
        "iter0_rho": iter0_rho,
        "late_rho_mean": late_rho_mean,
        "iter4_rho": iter4_rho,
        "iter4_optimism": max(iter4_rho - 1.0, 0.0) if iter4_rho == iter4_rho else float("nan"),
        "early_optimism_score": early_optimism,
        "late_overconservatism_score": late_over,
        "late_optimism_score": late_optimism,
        "frame_worst_late_optimism": frame_worst_late_optimism,
        "frame_row_count": float(len(frame_rows or [])),
        "task_risk_score": task_risk,
    }


def _rank_alignment_score(
    ber_map: dict[str, float],
    metric_map: dict[str, float],
) -> tuple[int, list[str], list[str]]:
    ber_order = sorted(ber_map.keys(), key=lambda k: float(ber_map[k]))
    metric_order = sorted(metric_map.keys(), key=lambda k: float(metric_map[k]))
    ber_rank = {name: idx for idx, name in enumerate(ber_order)}
    metric_rank = {name: idx for idx, name in enumerate(metric_order)}
    score = -sum(abs(int(ber_rank[name]) - int(metric_rank[name])) for name in ber_map.keys())
    return int(score), ber_order, metric_order


def _read_csv_rows(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def _load_saved_payload(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Required payload artifact is missing: {path}")
    blob = torch.load(path, map_location="cpu")
    payload = blob.get("payload") if isinstance(blob, dict) else None
    if not isinstance(payload, dict):
        raise RuntimeError(f"Artifact does not contain a valid payload: {path}")
    return payload


def _frame_worst_late_optimism_from_rows(
    frame_rows: list[dict[str, Any]],
    late_iters: tuple[int, ...] = (2, 3, 4),
) -> float:
    if not frame_rows:
        return float("nan")
    late_iter_set = {int(x) for x in late_iters}
    worst_by_frame: dict[tuple[int, int, int], float] = {}
    for row in frame_rows:
        iter_idx = int(row["outer_iter"])
        if iter_idx not in late_iter_set:
            continue
        key = (int(row["seed"]), int(row["snr_db"]), int(row["frame_idx"]))
        val = max(float(row["rho"]) - 1.0, 0.0)
        worst_by_frame[key] = max(float(worst_by_frame.get(key, 0.0)), float(val))
    if not worst_by_frame:
        return float("nan")
    return float(np.mean(list(worst_by_frame.values())))


def _stage13_metric_audit_summary_md(
    *,
    ber_map: dict[str, float],
    old_metric_map: dict[str, float],
    new_metric_map: dict[str, float],
    new_detail_map: dict[str, dict[str, float]],
) -> str:
    old_score, ber_order, old_order = _rank_alignment_score(ber_map, old_metric_map)
    new_score, _, new_order = _rank_alignment_score(ber_map, new_metric_map)
    learned_after_v1 = int(new_order.index("learned")) > int(new_order.index("v1")) if "learned" in new_order and "v1" in new_order else False
    lines = [
        "# Stage13 Metric Audit Summary",
        "",
        "## Final BER Order",
        "",
        f"- order=`{' > '.join(ber_order)}`",
        "",
        "## Metric Ranking Comparison",
        "",
        f"- old_task_balanced_score_order=`{' > '.join(old_order)}`",
        f"- old_alignment_score=`{old_score}`",
        f"- new_task_risk_score_order=`{' > '.join(new_order)}`",
        f"- new_alignment_score=`{new_score}`",
        "",
        "## Per-Profile Risk Metrics",
        "",
    ]
    for name in ber_map.keys():
        detail = new_detail_map[name]
        lines.append(
            f"- `{name}`: final_mean_ber=`{ber_map[name]:.4e}`, iter0_rho=`{detail['iter0_rho']:.3f}`, "
            f"late_rho_mean=`{detail['late_rho_mean']:.3f}`, iter4_rho=`{detail['iter4_rho']:.3f}`, "
            f"late_optimism=`{detail['late_optimism_score']:.3f}`, frame_worst_late_optimism=`{detail['frame_worst_late_optimism']:.3f}`, "
            f"frame_rows=`{int(detail['frame_row_count'])}`, task_risk_score=`{detail['task_risk_score']:.3f}`"
        )
    lines.extend(["", "## Verdict", ""])
    if new_score > old_score:
        lines.append("- Verdict: new `task_risk_score` better matches the true BER ranking and corrects the old score's late-optimism bias.")
    elif learned_after_v1:
        lines.append("- Verdict: new `task_risk_score` is worth keeping because it explicitly fixes the key Stage12/13 failure mode: it ranks `v1` ahead of the learned variant by penalizing late optimism more heavily.")
    else:
        lines.append("- Verdict: new `task_risk_score` still does not separate `v1` from the learned variant strongly enough, so it should not replace the old score yet.")
    return "\n".join(lines)


def _stage12_recalibration_summary_md(
    *,
    title: str,
    variant_label: str,
    fixed_best_mean_ber: float,
    v1_mean_ber: float,
    variant_mean_ber: float,
    fixed_best_cal: list[dict[str, Any]],
    v1_cal: list[dict[str, Any]],
    variant_cal: list[dict[str, Any]],
    train_info: dict[str, Any] | None = None,
) -> str:
    fixed_metrics = _task_aware_metrics(fixed_best_cal)
    v1_metrics = _task_aware_metrics(v1_cal)
    variant_metrics = _task_aware_metrics(variant_cal)
    variant_gain = (fixed_best_mean_ber - variant_mean_ber) / max(fixed_best_mean_ber, 1e-12)
    variant_vs_v1 = (v1_mean_ber - variant_mean_ber) / max(v1_mean_ber, 1e-12)
    lines = [
        title,
        "",
        f"- fixed_best final_mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- fixed_best+vx_recalibration_v1 final_mean_ber=`{v1_mean_ber:.4e}`",
        f"- {variant_label} final_mean_ber=`{variant_mean_ber:.4e}`",
        f"- rel_gain_vs_fixed_best=`{variant_gain:.3%}`",
        f"- rel_gain_vs_v1=`{variant_vs_v1:.3%}`",
        "",
        "## Task-Aware Calibration",
        "",
        f"- fixed_best: iter0_rho=`{fixed_metrics['iter0_rho']:.3f}`, late_rho_mean=`{fixed_metrics['late_rho_mean']:.3f}`, early_optimism=`{fixed_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{fixed_metrics['late_overconservatism_score']:.3f}`, task_balanced_score=`{fixed_metrics['task_balanced_score']:.3f}`",
        f"- fixed_best+vx_recalibration_v1: iter0_rho=`{v1_metrics['iter0_rho']:.3f}`, late_rho_mean=`{v1_metrics['late_rho_mean']:.3f}`, early_optimism=`{v1_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{v1_metrics['late_overconservatism_score']:.3f}`, task_balanced_score=`{v1_metrics['task_balanced_score']:.3f}`",
        f"- {variant_label}: iter0_rho=`{variant_metrics['iter0_rho']:.3f}`, late_rho_mean=`{variant_metrics['late_rho_mean']:.3f}`, early_optimism=`{variant_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{variant_metrics['late_overconservatism_score']:.3f}`, task_balanced_score=`{variant_metrics['task_balanced_score']:.3f}`",
        "",
        "## Aggregate Calibration",
        "",
        f"- fixed_best: mean_rho=`{float(np.mean([float(r['rho']) for r in fixed_best_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in fixed_best_cal])):.3f}`",
        f"- fixed_best+vx_recalibration_v1: mean_rho=`{float(np.mean([float(r['rho']) for r in v1_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in v1_cal])):.3f}`",
        f"- {variant_label}: mean_rho=`{float(np.mean([float(r['rho']) for r in variant_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in variant_cal])):.3f}`",
    ]
    if train_info is not None:
        lines.extend(
            [
                "",
                "## Training",
                "",
                f"- best_epoch=`{int(train_info['best_epoch'])}`",
                f"- train_loss=`{float(train_info['train_loss']):.6f}`",
                f"- val_loss=`{float(train_info['val_loss']):.6f}`",
                f"- mean_learned_scale=`{float(train_info['mean_scale']):.3f}`",
                f"- scale_range=`{float(train_info['min_scale']):.3f}` to `{float(train_info['max_scale']):.3f}`",
            ]
        )
    lines.extend(["", "## Verdict", ""])
    if (
        variant_mean_ber <= v1_mean_ber + 1e-12
        and variant_metrics["task_balanced_score"] < v1_metrics["task_balanced_score"] - 1e-6
        and ((variant_mean_ber - fixed_best_mean_ber) / max(fixed_best_mean_ber, 1e-12)) <= 0.02
    ):
        lines.append(f"- Verdict: `{variant_label}` improves the task-aware calibration/BER tradeoff and becomes the new main recalibration candidate.")
    else:
        lines.append(f"- Verdict: `vx recalibration v1` remains the incumbent; `{variant_label}` does not improve the task-aware calibration/BER tradeoff enough to replace it.")
    return "\n".join(lines)


def _stage13_recalibration_summary_md(
    *,
    title: str,
    variant_label: str,
    fixed_best_mean_ber: float,
    v1_mean_ber: float,
    variant_mean_ber: float,
    fixed_best_cal: list[dict[str, Any]],
    v1_cal: list[dict[str, Any]],
    variant_cal: list[dict[str, Any]],
    fixed_best_frame_rows: list[dict[str, Any]] | None = None,
    v1_frame_rows: list[dict[str, Any]] | None = None,
    variant_frame_rows: list[dict[str, Any]] | None = None,
    train_info: dict[str, Any] | None = None,
) -> str:
    frame_groups = {
        "fixed_best": fixed_best_frame_rows or [],
        "v1": v1_frame_rows or [],
        "variant": variant_frame_rows or [],
    }
    missing = [name for name, rows in frame_groups.items() if not rows]
    if missing:
        raise RuntimeError(f"Stage13 summary requires non-empty frame rows for: {', '.join(missing)}")
    fixed_metrics = _task_risk_metrics(fixed_best_cal, frame_rows=fixed_best_frame_rows)
    v1_metrics = _task_risk_metrics(v1_cal, frame_rows=v1_frame_rows)
    variant_metrics = _task_risk_metrics(variant_cal, frame_rows=variant_frame_rows)
    for name, metrics in [("fixed_best", fixed_metrics), ("v1", v1_metrics), ("variant", variant_metrics)]:
        if metrics["frame_worst_late_optimism"] != metrics["frame_worst_late_optimism"]:
            raise RuntimeError(f"Stage13 summary computed NaN frame_worst_late_optimism for {name}")
    variant_gain = (fixed_best_mean_ber - variant_mean_ber) / max(fixed_best_mean_ber, 1e-12)
    variant_vs_v1 = (v1_mean_ber - variant_mean_ber) / max(v1_mean_ber, 1e-12)
    lines = [
        title,
        "",
        f"- fixed_best final_mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- fixed_best+vx_recalibration_v1 final_mean_ber=`{v1_mean_ber:.4e}`",
        f"- {variant_label} final_mean_ber=`{variant_mean_ber:.4e}`",
        f"- rel_gain_vs_fixed_best=`{variant_gain:.3%}`",
        f"- rel_gain_vs_v1=`{variant_vs_v1:.3%}`",
        f"- frame_row_counts: fixed_best=`{len(fixed_best_frame_rows or [])}`, v1=`{len(v1_frame_rows or [])}`, variant=`{len(variant_frame_rows or [])}`",
        "",
        "## Task Risk",
        "",
        f"- fixed_best: iter0_rho=`{fixed_metrics['iter0_rho']:.3f}`, late_rho_mean=`{fixed_metrics['late_rho_mean']:.3f}`, iter4_rho=`{fixed_metrics['iter4_rho']:.3f}`, early_optimism=`{fixed_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{fixed_metrics['late_overconservatism_score']:.3f}`, late_optimism=`{fixed_metrics['late_optimism_score']:.3f}`, frame_worst_late_optimism=`{fixed_metrics['frame_worst_late_optimism']:.3f}`, task_risk_score=`{fixed_metrics['task_risk_score']:.3f}`",
        f"- fixed_best+vx_recalibration_v1: iter0_rho=`{v1_metrics['iter0_rho']:.3f}`, late_rho_mean=`{v1_metrics['late_rho_mean']:.3f}`, iter4_rho=`{v1_metrics['iter4_rho']:.3f}`, early_optimism=`{v1_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{v1_metrics['late_overconservatism_score']:.3f}`, late_optimism=`{v1_metrics['late_optimism_score']:.3f}`, frame_worst_late_optimism=`{v1_metrics['frame_worst_late_optimism']:.3f}`, task_risk_score=`{v1_metrics['task_risk_score']:.3f}`",
        f"- {variant_label}: iter0_rho=`{variant_metrics['iter0_rho']:.3f}`, late_rho_mean=`{variant_metrics['late_rho_mean']:.3f}`, iter4_rho=`{variant_metrics['iter4_rho']:.3f}`, early_optimism=`{variant_metrics['early_optimism_score']:.3f}`, late_overconservatism=`{variant_metrics['late_overconservatism_score']:.3f}`, late_optimism=`{variant_metrics['late_optimism_score']:.3f}`, frame_worst_late_optimism=`{variant_metrics['frame_worst_late_optimism']:.3f}`, task_risk_score=`{variant_metrics['task_risk_score']:.3f}`",
        "",
        "## Aggregate Calibration",
        "",
        f"- fixed_best: mean_rho=`{float(np.mean([float(r['rho']) for r in fixed_best_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in fixed_best_cal])):.3f}`",
        f"- fixed_best+vx_recalibration_v1: mean_rho=`{float(np.mean([float(r['rho']) for r in v1_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in v1_cal])):.3f}`",
        f"- {variant_label}: mean_rho=`{float(np.mean([float(r['rho']) for r in variant_cal])):.3f}`, mean_eta=`{float(np.mean([float(r['eta']) for r in variant_cal])):.3f}`",
    ]
    if train_info is not None:
        lines.extend(
            [
                "",
                "## Training",
                "",
                f"- best_epoch=`{int(train_info['best_epoch'])}`",
                f"- train_loss=`{float(train_info['train_loss']):.6f}`",
                f"- val_loss=`{float(train_info['val_loss']):.6f}`",
                f"- mean_anchor_scale=`{float(train_info['mean_scale']):.3f}`",
                f"- scale_range=`{float(train_info['min_scale']):.3f}` to `{float(train_info['max_scale']):.3f}`",
                f"- residual_delta_range=`{float(train_info['min_delta']):.3f}` to `{float(train_info['max_delta']):.3f}`",
                f"- train_late_optimism_mean=`{float(train_info['train_late_optimism_mean']):.6f}`",
                f"- val_late_optimism_mean=`{float(train_info['val_late_optimism_mean']):.6f}`",
                f"- train_frame_worst_late_optimism=`{float(train_info['train_frame_worst_late_optimism']):.6f}`",
                f"- val_frame_worst_late_optimism=`{float(train_info['val_frame_worst_late_optimism']):.6f}`",
                f"- train_v1_distill_loss=`{float(train_info['train_v1_distill_loss']):.6f}`",
                f"- val_v1_distill_loss=`{float(train_info['val_v1_distill_loss']):.6f}`",
                f"- train_iter4_optimism_mean=`{float(train_info['train_iter4_optimism_mean']):.6f}`",
                f"- val_iter4_optimism_mean=`{float(train_info['val_iter4_optimism_mean']):.6f}`",
                f"- train_iter4_optimism_barrier=`{float(train_info['train_iter4_optimism_barrier']):.6f}`",
                f"- val_iter4_optimism_barrier=`{float(train_info['val_iter4_optimism_barrier']):.6f}`",
            ]
        )
    lines.extend(["", "## Verdict", ""])
    if (
        variant_mean_ber <= v1_mean_ber + 1e-12
        and variant_metrics["task_risk_score"] < v1_metrics["task_risk_score"] - 1e-6
        and variant_metrics["late_optimism_score"] <= v1_metrics["late_optimism_score"] + 1e-6
        and variant_metrics["frame_worst_late_optimism"] <= v1_metrics["frame_worst_late_optimism"] + 1e-6
        and variant_metrics["iter4_optimism"] <= v1_metrics["iter4_optimism"] + 1e-6
    ):
        lines.append(f"- Verdict: `{variant_label}` improves on `v1` without re-introducing late optimism and becomes the new main recalibration candidate.")
    else:
        lines.append(f"- Verdict: `vx recalibration v1` remains the incumbent; `{variant_label}` does not beat it on BER-risk tradeoff without re-introducing late optimism.")
    return '\n'.join(lines)


def _frame_calibration_dataset_summary_md(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
) -> str:
    def _split_stats(rows: list[dict[str, Any]]) -> tuple[float, float]:
        if not rows:
            return float("nan"), float("nan")
        return (
            float(np.mean([float(r["rho"]) for r in rows])),
            float(np.mean([float(r["vx_mean"]) for r in rows])),
        )

    train_rho, train_vx = _split_stats(train_rows)
    val_rho, val_vx = _split_stats(val_rows)
    return "\n".join(
        [
            "# Stage12 Frame-Level Calibration Dataset Summary",
            "",
            f"- train_rows=`{len(train_rows)}`",
            f"- val_rows=`{len(val_rows)}`",
            f"- train_mean_rho=`{train_rho:.3f}`, train_mean_vx=`{train_vx:.4e}`",
            f"- val_mean_rho=`{val_rho:.3f}`, val_mean_vx=`{val_vx:.4e}`",
            "",
            "## Interpretation",
            "",
            "- Dataset is exported from the `fixed_best` path at `seed × snr × frame_idx × outer_iter` granularity.",
            "- It is intended only for output-side learned recalibration and does not change the detector internal sigma path.",
        ]
    )


class _TinyOutputRecalibrationMLP(nn.Module):
    def __init__(self, input_dim: int = 10, hidden_dim: int = 16):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, 1)
        nn.init.zeros_(self.fc2.weight)
        nn.init.zeros_(self.fc2.bias)

    def forward(self, feat: torch.Tensor) -> torch.Tensor:
        return self.fc2(F.silu(self.fc1(feat)))


def _collect_frame_calibration_dataset(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    seeds: list[int],
    fixed_best_alpha: float,
    fixed_best_sigma: float,
    eval_batch_size: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    overrides = {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}
    for seed in seeds:
        for snr_db in snr_list:
            stats = _evaluate_stage6_profile(
                model,
                seed_batches[int(seed)][int(snr_db)],
                data_pos,
                overrides,
                eval_batch_size=eval_batch_size,
                collect_traces=True,
                collect_frame_calibration=True,
            )
            for row in stats.get("frame_calibration_rows", []):
                rows.append(
                    {
                        "seed": int(seed),
                        "snr_db": int(snr_db),
                        **row,
                    }
                )
    return rows


def _frame_rows_to_tensors(
    rows: list[dict[str, Any]],
    num_outer_iters: int,
    device: torch.device,
    *,
    base_scale_list: list[float] | None = None,
    residual_log_bound_list: list[float] | None = None,
    iter0_weight: float = 2.0,
) -> dict[str, torch.Tensor]:
    feat_list: list[list[float]] = []
    vx_list: list[float] = []
    sym_list: list[float] = []
    weight_list: list[float] = []
    base_scale_vals: list[float] = []
    residual_bound_vals: list[float] = []
    iter_idx_vals: list[int] = []
    for row in rows:
        iter_idx = int(row["outer_iter"])
        onehot = [0.0] * int(num_outer_iters)
        onehot[iter_idx] = 1.0
        feat = onehot + [
            float(np.log(max(float(row["vx_mean"]), 1e-8))),
            float(np.log(max(float(row["residual_energy_mean"]), 1e-8))),
            float(np.log(max(float(row["detector_sigma_mean"]), 1e-8))),
            float(np.log(max(float(row["channel_update_norm"]), 1e-8))),
            float(row["snr_db"]) / 30.0,
        ]
        base_scale_t = 1.0
        if base_scale_list:
            base_scale_t = float(base_scale_list[min(iter_idx, len(base_scale_list) - 1)])
            feat.append(float(np.log(max(base_scale_t, 1e-8))))
        feat_list.append(feat)
        vx_list.append(max(float(row["vx_mean"]), 1e-8))
        sym_list.append(max(float(row["sym_err_mean"]), 1e-8))
        weight_list.append(float(iter0_weight) if iter_idx == 0 else 1.0)
        base_scale_vals.append(base_scale_t)
        if residual_log_bound_list:
            residual_bound_vals.append(float(residual_log_bound_list[min(iter_idx, len(residual_log_bound_list) - 1)]))
        else:
            residual_bound_vals.append(0.0)
        iter_idx_vals.append(iter_idx)
    out = {
        "feat": torch.as_tensor(feat_list, dtype=torch.float32, device=device),
        "vx": torch.as_tensor(vx_list, dtype=torch.float32, device=device).reshape(-1, 1),
        "sym": torch.as_tensor(sym_list, dtype=torch.float32, device=device).reshape(-1, 1),
        "weight": torch.as_tensor(weight_list, dtype=torch.float32, device=device).reshape(-1, 1),
        "iter_idx": torch.as_tensor(iter_idx_vals, dtype=torch.long, device=device).reshape(-1, 1),
    }
    if base_scale_list:
        out["base_scale"] = torch.as_tensor(base_scale_vals, dtype=torch.float32, device=device).reshape(-1, 1)
    if residual_log_bound_list:
        out["residual_log_bound"] = torch.as_tensor(residual_bound_vals, dtype=torch.float32, device=device).reshape(-1, 1)
    return out


def _learned_scale_from_raw(raw: torch.Tensor) -> torch.Tensor:
    return torch.exp(float(np.log(16.0)) * torch.tanh(raw))


def _anchored_learned_scale_from_raw(
    raw: torch.Tensor,
    base_scale: torch.Tensor,
    residual_log_bound: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    delta = residual_log_bound * torch.tanh(raw)
    scale = base_scale * torch.exp(delta)
    return scale, delta


def _learned_recalibration_loss(
    raw: torch.Tensor,
    vx: torch.Tensor,
    sym: torch.Tensor,
    weight: torch.Tensor,
    id_reg: float,
) -> torch.Tensor:
    scale = _learned_scale_from_raw(raw)
    pred = torch.log((scale * vx).clamp_min(1e-8))
    target = torch.log(sym.clamp_min(1e-8))
    huber = F.smooth_l1_loss(pred, target, reduction="none")
    weighted = (weight * huber).mean()
    reg = float(id_reg) * torch.square(torch.log(scale.clamp_min(1e-8))).mean()
    return weighted + reg


def _anchored_learned_recalibration_loss(
    raw: torch.Tensor,
    *,
    base_scale: torch.Tensor,
    residual_log_bound: torch.Tensor,
    vx: torch.Tensor,
    sym: torch.Tensor,
    weight: torch.Tensor,
    iter_idx: torch.Tensor,
    anchor_reg: float,
    late_optimism_barrier: float,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    scale, delta = _anchored_learned_scale_from_raw(raw, base_scale, residual_log_bound)
    pred_log = torch.log((scale * vx).clamp_min(1e-8))
    target_log = torch.log(sym.clamp_min(1e-8))
    huber = F.smooth_l1_loss(pred_log, target_log, reduction="none")
    calibration = (weight * huber).mean()
    anchor = (weight * delta.square()).mean()
    late_mask = (iter_idx >= 2).to(dtype=pred_log.dtype)
    iter4_mask = (iter_idx >= 4).to(dtype=pred_log.dtype)
    late_optimism = torch.relu(pred_log - target_log)
    late_barrier = (weight * late_mask * late_optimism.square()).mean()
    iter4_barrier = (weight * iter4_mask * late_optimism.square()).mean()
    teacher_log = torch.log((base_scale * vx).clamp_min(1e-8))
    distill_elem = F.smooth_l1_loss(pred_log, teacher_log, reduction="none")
    distill_weight = torch.where(
        iter_idx >= 4,
        torch.full_like(pred_log, 3.0),
        torch.where(
            iter_idx >= 2,
            torch.full_like(pred_log, 1.25),
            torch.where(iter_idx >= 1, torch.ones_like(pred_log), torch.full_like(pred_log, 0.25)),
        ),
    )
    v1_distill = (weight * distill_weight * distill_elem).mean()
    total = (
        0.5 * calibration
        + float(anchor_reg) * anchor
        + float(late_optimism_barrier) * late_barrier
        + 6.0 * iter4_barrier
        + 1.0 * v1_distill
    )
    return total, {
        "scale": scale.detach(),
        "delta": delta.detach(),
        "calibration": calibration.detach(),
        "anchor_reg": anchor.detach(),
        "v1_distill_loss": v1_distill.detach(),
        "late_optimism_barrier": late_barrier.detach(),
        "iter4_optimism_barrier": iter4_barrier.detach(),
        "late_optimism_mean": (late_mask * late_optimism).sum().detach()
        / late_mask.sum().clamp_min(1.0).detach(),
        "iter4_optimism_mean": (iter4_mask * late_optimism).sum().detach()
        / iter4_mask.sum().clamp_min(1.0).detach(),
    }


def _payload_from_learned_model(
    model: _TinyOutputRecalibrationMLP,
    num_outer_iters: int,
) -> dict[str, Any]:
    return {
        "iter_onehot_dim": int(num_outer_iters),
        "scale_log_bound": float(np.log(16.0)),
        "w1": model.fc1.weight.detach().cpu(),
        "b1": model.fc1.bias.detach().cpu(),
        "w2": model.fc2.weight.detach().cpu(),
        "b2": model.fc2.bias.detach().cpu(),
    }


def _payload_from_anchor_learned_model(
    model: _TinyOutputRecalibrationMLP,
    *,
    num_outer_iters: int,
    base_scale_list: list[float],
    residual_log_bound_list: list[float],
) -> dict[str, Any]:
    return {
        "iter_onehot_dim": int(num_outer_iters),
        "residual_mode": "log_residual",
        "include_log_base_scale": True,
        "base_scale_list": [float(x) for x in base_scale_list],
        "residual_log_bound_list": [float(x) for x in residual_log_bound_list],
        "w1": model.fc1.weight.detach().cpu(),
        "b1": model.fc1.bias.detach().cpu(),
        "w2": model.fc2.weight.detach().cpu(),
        "b2": model.fc2.bias.detach().cpu(),
    }


def _train_learned_output_recalibration(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    *,
    num_outer_iters: int,
    device: torch.device,
    epochs: int = 300,
    patience: int = 40,
    lr: float = 1e-2,
    id_reg: float = 1e-3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    train_tensors = _frame_rows_to_tensors(train_rows, num_outer_iters, device)
    val_tensors = _frame_rows_to_tensors(val_rows or train_rows, num_outer_iters, device)
    model = _TinyOutputRecalibrationMLP(input_dim=int(train_tensors["feat"].shape[-1]), hidden_dim=16).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=float(lr))
    best_state: dict[str, torch.Tensor] | None = None
    best_val = float("inf")
    best_epoch = -1
    stale = 0
    for epoch in range(int(epochs)):
        model.train()
        opt.zero_grad(set_to_none=True)
        raw = model(train_tensors["feat"])
        loss = _learned_recalibration_loss(raw, train_tensors["vx"], train_tensors["sym"], train_tensors["weight"], id_reg)
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            val_raw = model(val_tensors["feat"])
            val_loss = _learned_recalibration_loss(val_raw, val_tensors["vx"], val_tensors["sym"], val_tensors["weight"], id_reg)
        val_loss_float = float(val_loss.detach().cpu().item())
        if val_loss_float < best_val - 1e-6:
            best_val = val_loss_float
            best_epoch = int(epoch)
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= int(patience):
                break
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        train_raw = model(train_tensors["feat"])
        val_raw = model(val_tensors["feat"])
        train_loss = _learned_recalibration_loss(train_raw, train_tensors["vx"], train_tensors["sym"], train_tensors["weight"], id_reg)
        val_loss = _learned_recalibration_loss(val_raw, val_tensors["vx"], val_tensors["sym"], val_tensors["weight"], id_reg)
        train_scale = _learned_scale_from_raw(train_raw)
    payload = _payload_from_learned_model(model, num_outer_iters)
    train_info = {
        "best_epoch": int(best_epoch),
        "train_loss": float(train_loss.detach().cpu().item()),
        "val_loss": float(val_loss.detach().cpu().item()),
        "mean_scale": float(train_scale.mean().detach().cpu().item()),
        "min_scale": float(train_scale.min().detach().cpu().item()),
        "max_scale": float(train_scale.max().detach().cpu().item()),
    }
    return payload, train_info


def _train_anchored_output_recalibration(
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    *,
    num_outer_iters: int,
    base_scale_list: list[float],
    residual_log_bound_list: list[float],
    device: torch.device,
    epochs: int = 300,
    patience: int = 40,
    lr: float = 1e-2,
    anchor_reg: float = 1e-2,
    late_optimism_barrier: float = 2.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    train_tensors = _frame_rows_to_tensors(
        train_rows,
        num_outer_iters,
        device,
        base_scale_list=base_scale_list,
        residual_log_bound_list=residual_log_bound_list,
        iter0_weight=1.25,
    )
    val_tensors = _frame_rows_to_tensors(
        val_rows or train_rows,
        num_outer_iters,
        device,
        base_scale_list=base_scale_list,
        residual_log_bound_list=residual_log_bound_list,
        iter0_weight=1.25,
    )
    train_late_weight = (train_tensors["iter_idx"] >= 2).to(train_tensors["weight"].dtype) * 0.5 + 1.0
    val_late_weight = (val_tensors["iter_idx"] >= 2).to(val_tensors["weight"].dtype) * 0.5 + 1.0
    train_tensors["weight"] = train_tensors["weight"] * train_late_weight
    val_tensors["weight"] = val_tensors["weight"] * val_late_weight
    model = _TinyOutputRecalibrationMLP(input_dim=int(train_tensors["feat"].shape[-1]), hidden_dim=16).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=float(lr))
    best_state: dict[str, torch.Tensor] | None = None
    best_val = float("inf")
    best_epoch = -1
    stale = 0
    for epoch in range(int(epochs)):
        model.train()
        opt.zero_grad(set_to_none=True)
        raw = model(train_tensors["feat"])
        loss, _ = _anchored_learned_recalibration_loss(
            raw,
            base_scale=train_tensors["base_scale"],
            residual_log_bound=train_tensors["residual_log_bound"],
            vx=train_tensors["vx"],
            sym=train_tensors["sym"],
            weight=train_tensors["weight"],
            iter_idx=train_tensors["iter_idx"],
            anchor_reg=anchor_reg,
            late_optimism_barrier=late_optimism_barrier,
        )
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            val_raw = model(val_tensors["feat"])
            val_loss, _ = _anchored_learned_recalibration_loss(
                val_raw,
                base_scale=val_tensors["base_scale"],
                residual_log_bound=val_tensors["residual_log_bound"],
                vx=val_tensors["vx"],
                sym=val_tensors["sym"],
                weight=val_tensors["weight"],
                iter_idx=val_tensors["iter_idx"],
                anchor_reg=anchor_reg,
                late_optimism_barrier=late_optimism_barrier,
            )
        val_loss_float = float(val_loss.detach().cpu().item())
        if val_loss_float < best_val - 1e-6:
            best_val = val_loss_float
            best_epoch = int(epoch)
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= int(patience):
                break
    assert best_state is not None
    model.load_state_dict(best_state)
    model.eval()

    def _frame_worst_late_from_rows(rows: list[dict[str, Any]], late_optimism: torch.Tensor) -> float:
        worst_by_frame: dict[tuple[int, int, int], float] = {}
        flat = late_optimism.detach().cpu().reshape(-1).tolist()
        for row, val in zip(rows, flat):
            iter_idx = int(row["outer_iter"])
            if iter_idx < 2:
                continue
            key = (int(row["seed"]), int(row["snr_db"]), int(row["frame_idx"]))
            worst_by_frame[key] = max(float(worst_by_frame.get(key, 0.0)), float(val))
        if not worst_by_frame:
            return 0.0
        return float(np.mean(list(worst_by_frame.values())))

    with torch.no_grad():
        train_raw = model(train_tensors["feat"])
        train_loss, train_aux = _anchored_learned_recalibration_loss(
            train_raw,
            base_scale=train_tensors["base_scale"],
            residual_log_bound=train_tensors["residual_log_bound"],
            vx=train_tensors["vx"],
            sym=train_tensors["sym"],
            weight=train_tensors["weight"],
            iter_idx=train_tensors["iter_idx"],
            anchor_reg=anchor_reg,
            late_optimism_barrier=late_optimism_barrier,
        )
        val_raw = model(val_tensors["feat"])
        val_loss, val_aux = _anchored_learned_recalibration_loss(
            val_raw,
            base_scale=val_tensors["base_scale"],
            residual_log_bound=val_tensors["residual_log_bound"],
            vx=val_tensors["vx"],
            sym=val_tensors["sym"],
            weight=val_tensors["weight"],
            iter_idx=val_tensors["iter_idx"],
            anchor_reg=anchor_reg,
            late_optimism_barrier=late_optimism_barrier,
        )
    payload = _payload_from_anchor_learned_model(
        model,
        num_outer_iters=num_outer_iters,
        base_scale_list=base_scale_list,
        residual_log_bound_list=residual_log_bound_list,
    )
    train_pred_log = torch.log((train_aux["scale"] * train_tensors["vx"]).clamp_min(1e-8))
    train_target_log = torch.log(train_tensors["sym"].clamp_min(1e-8))
    train_late_optimism = torch.relu(train_pred_log - train_target_log) * (train_tensors["iter_idx"] >= 2).to(train_pred_log.dtype)
    val_pred_log = torch.log((val_aux["scale"] * val_tensors["vx"]).clamp_min(1e-8))
    val_target_log = torch.log(val_tensors["sym"].clamp_min(1e-8))
    val_late_optimism = torch.relu(val_pred_log - val_target_log) * (val_tensors["iter_idx"] >= 2).to(val_pred_log.dtype)
    train_info = {
        "best_epoch": int(best_epoch),
        "train_loss": float(train_loss.detach().cpu().item()),
        "val_loss": float(val_loss.detach().cpu().item()),
        "mean_scale": float(train_aux["scale"].mean().cpu().item()),
        "min_scale": float(train_aux["scale"].min().cpu().item()),
        "max_scale": float(train_aux["scale"].max().cpu().item()),
        "mean_delta": float(train_aux["delta"].mean().cpu().item()),
        "min_delta": float(train_aux["delta"].min().cpu().item()),
        "max_delta": float(train_aux["delta"].max().cpu().item()),
        "train_late_optimism_mean": float(train_aux["late_optimism_mean"].cpu().item()),
        "val_late_optimism_mean": float(val_aux["late_optimism_mean"].cpu().item()),
        "train_frame_worst_late_optimism": _frame_worst_late_from_rows(train_rows, train_late_optimism),
        "val_frame_worst_late_optimism": _frame_worst_late_from_rows(val_rows or train_rows, val_late_optimism),
        "train_v1_distill_loss": float(train_aux["v1_distill_loss"].cpu().item()),
        "val_v1_distill_loss": float(val_aux["v1_distill_loss"].cpu().item()),
        "train_iter4_optimism_mean": float(train_aux["iter4_optimism_mean"].cpu().item()),
        "val_iter4_optimism_mean": float(val_aux["iter4_optimism_mean"].cpu().item()),
        "train_iter4_optimism_barrier": float(train_aux["iter4_optimism_barrier"].cpu().item()),
        "val_iter4_optimism_barrier": float(val_aux["iter4_optimism_barrier"].cpu().item()),
    }
    return payload, train_info


def _iter_mean_metric(rows: list[dict[str, Any]], key: str, iter_ids: set[int]) -> float:
    vals = [float(r[key]) for r in rows if int(r["outer_iter"]) in iter_ids]
    if not vals:
        return float("nan")
    return float(np.mean(vals))


def _vx_variant_passes_stage11(
    fixed_best_mean_ber: float,
    v1_mean_ber: float,
    fixed_best_cal: list[dict[str, Any]],
    v1_cal: list[dict[str, Any]],
    variant_mean_ber: float,
    variant_cal: list[dict[str, Any]],
) -> bool:
    def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return float("nan")
        return float(np.mean([float(r[key]) for r in rows]))

    if not variant_cal or variant_mean_ber != variant_mean_ber:
        return False
    if ((variant_mean_ber - fixed_best_mean_ber) / max(fixed_best_mean_ber, 1e-12)) > 0.02:
        return False
    if variant_mean_ber > v1_mean_ber + 1e-12:
        return False
    fixed_eta = _mean_metric(fixed_best_cal, "eta")
    variant_eta = _mean_metric(variant_cal, "eta")
    if variant_eta <= 0.0 or fixed_eta <= 0.0:
        return False
    if not (0.5 * fixed_eta <= variant_eta <= 2.0 * fixed_eta):
        return False
    v1_gap = abs(_mean_metric(v1_cal, "rho") - 1.0)
    variant_gap = abs(_mean_metric(variant_cal, "rho") - 1.0)
    if variant_gap >= v1_gap:
        return False
    late_v1_gap = abs(_iter_mean_metric(v1_cal, "rho", {2, 3, 4}) - 1.0)
    late_variant_gap = abs(_iter_mean_metric(variant_cal, "rho", {2, 3, 4}) - 1.0)
    return late_variant_gap <= late_v1_gap + 0.05


def _load_existing_best_json(out_dir: pathlib.Path, filename: str) -> dict[str, Any] | None:
    path = out_dir / filename
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _final_mean_ber_from_trace_rows(
    trace_rows: list[dict[str, Any]],
    profile_name: str,
    final_outer_iter: int,
) -> float:
    vals = [
        float(r["ber"])
        for r in trace_rows
        if str(r["profile"]) == profile_name and int(r["outer_iter"]) == int(final_outer_iter)
    ]
    if not vals:
        return float("nan")
    return float(np.mean(vals))


def _final_ber_by_seed_snr_from_trace_rows(
    trace_rows: list[dict[str, Any]],
    profile_name: str,
    final_outer_iter: int,
) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for row in trace_rows:
        if str(row["profile"]) != profile_name or int(row["outer_iter"]) != int(final_outer_iter):
            continue
        out.setdefault(str(int(row["seed"])), {})[int(row["snr_db"])] = float(row["ber"])
    return out


def _evaluate_uncertainty_aware_sic_rows(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    seeds: list[int],
    fixed_best_by_seed: dict[str, dict[int, float]],
    vx_recal_by_seed: dict[str, dict[int, float]],
    coeff_list: list[float],
    sic_kappa_grid: list[float],
    fixed_best_alpha: float,
    fixed_best_sigma: float,
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, float], dict[str, float] | None]:
    rows: list[dict[str, Any]] = []
    best_by_seed: dict[str, dict[str, Any]] = {}
    avg_gain_by_seed: dict[str, float] = {}
    global_grouped: dict[float, list[float]] = {}
    for seed in seeds:
        seed_key = str(int(seed))
        batches = seed_batches[int(seed)]
        best_snr_rows: dict[str, Any] = {}
        for snr_db in snr_list:
            batch = batches[int(snr_db)]
            best_row = None
            for kappa in sic_kappa_grid:
                overrides = {
                    "alpha": float(fixed_best_alpha),
                    "detector_sigma_inflation": float(fixed_best_sigma),
                    "vx_recalibration_scale": list(coeff_list),
                    "sic_uncertainty_kappa": float(kappa),
                    "sic_uncertainty_mode": "inv_linear",
                }
                stats = _evaluate_stage6_profile(
                    model,
                    batch,
                    data_pos,
                    overrides,
                    eval_batch_size=eval_batch_size,
                )
                ber = float(stats["ber"])
                global_grouped.setdefault(float(kappa), []).append(ber)
                fixed_ref = float(fixed_best_by_seed[seed_key][int(snr_db)])
                v1_ref = float(vx_recal_by_seed[seed_key][int(snr_db)])
                row = {
                    "seed": int(seed),
                    "snr_db": int(snr_db),
                    "sic_kappa": float(kappa),
                    "candidate_ber": ber,
                    "fixed_best_ber": fixed_ref,
                    "vx_recal_v1_ber": v1_ref,
                    "rel_improvement_over_fixed_best": float((fixed_ref - ber) / max(fixed_ref, 1e-12)),
                    "rel_improvement_over_vx_recal_v1": float((v1_ref - ber) / max(v1_ref, 1e-12)),
                }
                rows.append(row)
                if best_row is None or ber < float(best_row["candidate_ber"]):
                    best_row = row
            assert best_row is not None
            best_snr_rows[str(int(snr_db))] = dict(best_row)
        best_by_seed[seed_key] = best_snr_rows
        avg_gain_by_seed[seed_key] = float(
            np.mean([float(x["rel_improvement_over_fixed_best"]) for x in best_snr_rows.values()])
        )
    if not global_grouped:
        return rows, best_by_seed, avg_gain_by_seed, None
    best_kappa = min(global_grouped.keys(), key=lambda k: float(np.mean(global_grouped[k])))
    best_global = {
        "sic_kappa": float(best_kappa),
        "mean_ber": float(np.mean(global_grouped[best_kappa])),
    }
    return rows, best_by_seed, avg_gain_by_seed, best_global


def _evaluate_uncertainty_skip_freeze_rows(
    model,
    seed_batches: dict[int, dict[int, SharedBatch]],
    data_pos: np.ndarray,
    snr_list: list[int],
    seeds: list[int],
    fixed_best_by_seed: dict[str, dict[int, float]],
    source_by_seed: dict[str, dict[int, float]],
    source_overrides: dict[str, Any],
    skip_quantile_grid: list[float],
    eval_batch_size: int,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, float], dict[str, float] | None]:
    rows: list[dict[str, Any]] = []
    best_by_seed: dict[str, dict[str, Any]] = {}
    avg_gain_by_seed: dict[str, float] = {}
    global_grouped: dict[float, list[float]] = {}
    for seed in seeds:
        seed_key = str(int(seed))
        best_snr_rows: dict[str, Any] = {}
        for snr_db in snr_list:
            batch = seed_batches[int(seed)][int(snr_db)]
            best_row = None
            for quantile in skip_quantile_grid:
                overrides = dict(source_overrides)
                overrides["sic_skip_quantile"] = float(quantile)
                overrides["sic_skip_mode"] = "hard_quantile"
                stats = _evaluate_stage6_profile(
                    model,
                    batch,
                    data_pos,
                    overrides,
                    eval_batch_size=eval_batch_size,
                )
                ber = float(stats["ber"])
                global_grouped.setdefault(float(quantile), []).append(ber)
                fixed_ref = float(fixed_best_by_seed[seed_key][int(snr_db)])
                source_ref = float(source_by_seed[seed_key][int(snr_db)])
                row = {
                    "seed": int(seed),
                    "snr_db": int(snr_db),
                    "skip_quantile": float(quantile),
                    "candidate_ber": ber,
                    "fixed_best_ber": fixed_ref,
                    "source_ber": source_ref,
                    "rel_improvement_over_fixed_best": float((fixed_ref - ber) / max(fixed_ref, 1e-12)),
                    "rel_improvement_over_source": float((source_ref - ber) / max(source_ref, 1e-12)),
                }
                rows.append(row)
                if best_row is None or ber < float(best_row["candidate_ber"]):
                    best_row = row
            assert best_row is not None
            best_snr_rows[str(int(snr_db))] = dict(best_row)
        best_by_seed[seed_key] = best_snr_rows
        avg_gain_by_seed[seed_key] = float(
            np.mean([float(x["rel_improvement_over_fixed_best"]) for x in best_snr_rows.values()])
        )
    if not global_grouped:
        return rows, best_by_seed, avg_gain_by_seed, None
    best_quantile = min(global_grouped.keys(), key=lambda q: float(np.mean(global_grouped[q])))
    best_global = {
        "skip_quantile": float(best_quantile),
        "mean_ber": float(np.mean(global_grouped[best_quantile])),
    }
    return rows, best_by_seed, avg_gain_by_seed, best_global


def _vx_recalibration_summary_md(
    title: str,
    variant_label: str,
    fixed_best_mean_ber: float,
    variant_mean_ber: float,
    baseline_cal: list[dict[str, Any]],
    fixed_best_cal: list[dict[str, Any]],
    variant_cal: list[dict[str, Any]],
    v1_cal: list[dict[str, Any]] | None = None,
    v1_mean_ber: float | None = None,
) -> str:
    def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return float("nan")
        return float(np.mean([float(r[key]) for r in rows]))

    lines = [
        title,
        "",
        f"- fixed_best final_mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- {variant_label} final_mean_ber=`{variant_mean_ber:.4e}`",
        "",
        "## Aggregate Calibration",
        "",
        f"- baseline: mean_rho=`{_mean_metric(baseline_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(baseline_cal, 'eta'):.3f}`",
        f"- fixed_best: mean_rho=`{_mean_metric(fixed_best_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(fixed_best_cal, 'eta'):.3f}`",
    ]
    if v1_cal is not None:
        lines.append(
            f"- fixed_best+vx_recalibration_v1: mean_rho=`{_mean_metric(v1_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(v1_cal, 'eta'):.3f}`"
        )
    lines.append(
        f"- {variant_label}: mean_rho=`{_mean_metric(variant_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(variant_cal, 'eta'):.3f}`"
    )
    ber_drop = (variant_mean_ber - fixed_best_mean_ber) / max(fixed_best_mean_ber, 1e-12)
    fixed_rho_gap = abs(_mean_metric(fixed_best_cal, "rho") - 1.0)
    recal_rho_gap = abs(_mean_metric(variant_cal, "rho") - 1.0)
    v1_rho_gap = abs(_mean_metric(v1_cal, "rho") - 1.0) if v1_cal is not None else float("nan")
    late_variant_gap = abs(_iter_mean_metric(variant_cal, "rho", {2, 3, 4}) - 1.0)
    late_v1_gap = abs(_iter_mean_metric(v1_cal, "rho", {2, 3, 4}) - 1.0) if v1_cal is not None else float("nan")
    lines.extend(["", "## Verdict", ""])
    if v1_cal is None and ber_drop <= 0.02 and recal_rho_gap < fixed_rho_gap:
        lines.append(f"- Verdict: `{variant_label}` keeps final BER within tolerance and improves posterior-uncertainty calibration relative to `fixed_best`.")
    elif (
        v1_cal is not None
        and v1_mean_ber is not None
        and _vx_variant_passes_stage11(
            fixed_best_mean_ber=fixed_best_mean_ber,
            v1_mean_ber=v1_mean_ber,
            fixed_best_cal=fixed_best_cal,
            v1_cal=v1_cal,
            variant_mean_ber=variant_mean_ber,
            variant_cal=variant_cal,
        )
    ):
        lines.append(f"- Verdict: `{variant_label}` improves calibration over `vx recalibration v1` without materially harming final BER.")
    else:
        if v1_cal is not None:
            lines.append(
                f"- Verdict: `vx recalibration v1` remains the incumbent output-side calibration; `{variant_label}` is either not closer to `rho=1` than v1 or sacrifices too much stability."
            )
            lines.append(
                f"- Comparison detail: v1 `|rho-1|={v1_rho_gap:.3f}`, variant `|rho-1|={recal_rho_gap:.3f}`, late-gap(v1)={late_v1_gap:.3f}, late-gap(variant)={late_variant_gap:.3f}`."
            )
        else:
            lines.append(f"- Verdict: `fixed_best` remains the strongest baseline; `{variant_label}` does not yet justify replacing it.")
    return "\n".join(lines)


def _uncertainty_skip_freeze_summary_md(
    source_label: str,
    fixed_best_mean_ber: float,
    source_mean_ber: float,
    best_by_seed: dict[str, dict[str, Any]],
    avg_gain_by_seed: dict[str, float],
    best_global: dict[str, float],
    fixed_best_cal: list[dict[str, Any]],
    source_cal: list[dict[str, Any]],
    skip_cal: list[dict[str, Any]],
    source_trace: list[dict[str, Any]],
    skip_trace: list[dict[str, Any]],
) -> str:
    def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return float("nan")
        return float(np.mean([float(r[key]) for r in rows]))

    def _iter_mean(rows: list[dict[str, Any]], profile: str, iter_ids: set[int]) -> float:
        vals = [float(r["ber"]) for r in rows if str(r["profile"]) == profile and int(r["outer_iter"]) in iter_ids]
        if not vals:
            return float("nan")
        return float(np.mean(vals))

    skip_mean_ber = float(best_global["mean_ber"])
    rel_vs_fixed = float((fixed_best_mean_ber - skip_mean_ber) / max(fixed_best_mean_ber, 1e-12))
    rel_vs_source = float((source_mean_ber - skip_mean_ber) / max(source_mean_ber, 1e-12))
    early_src = _iter_mean(source_trace, source_label, {0, 1})
    early_skip = _iter_mean(skip_trace, f"{source_label}_uncertainty_skip_freeze", {0, 1})
    late_src = _iter_mean(source_trace, source_label, {2, 3, 4})
    late_skip = _iter_mean(skip_trace, f"{source_label}_uncertainty_skip_freeze", {2, 3, 4})
    keep_vals = [float(r["sic_weight_mean"]) for r in skip_cal] if skip_cal else []
    keep_mean = float(np.mean(keep_vals)) if keep_vals else float("nan")
    keep_min = float(np.min(keep_vals)) if keep_vals else float("nan")
    keep_max = float(np.max(keep_vals)) if keep_vals else float("nan")

    lines = [
        "# Stage11 Uncertainty Skip/Freeze Probe Summary",
        "",
        f"- source_profile=`{source_label}`",
        f"- fixed_best final_mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- {source_label} final_mean_ber=`{source_mean_ber:.4e}`",
        f"- best_global `(skip_quantile)=({best_global['skip_quantile']:.4f})`, final_mean_ber=`{skip_mean_ber:.4e}`",
        f"- rel_gain_vs_fixed_best=`{rel_vs_fixed:.3%}`",
        f"- rel_gain_vs_source=`{rel_vs_source:.3%}`",
        "",
        "## Best By Seed / SNR",
        "",
    ]
    for seed_key, items in sorted(best_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(items.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: skip_quantile=`{item['skip_quantile']:.4f}`, "
                f"rel_gain_vs_fixed_best=`{item['rel_improvement_over_fixed_best']:.3%}`, "
                f"rel_gain_vs_source=`{item['rel_improvement_over_source']:.3%}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Aggregate Calibration",
            "",
            f"- fixed_best: mean_rho=`{_mean_metric(fixed_best_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(fixed_best_cal, 'eta'):.3f}`",
            f"- {source_label}: mean_rho=`{_mean_metric(source_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(source_cal, 'eta'):.3f}`",
            f"- {source_label}+skip_freeze: mean_rho=`{_mean_metric(skip_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(skip_cal, 'eta'):.3f}`",
            f"- keep_ratio_mean=`{keep_mean:.3f}` (range=`{keep_min:.3f}` to `{keep_max:.3f}`)",
            "",
            "## Trace Comparison",
            "",
            f"- early_iters_gain_vs_source=`{((early_src - early_skip) / max(early_src, 1e-12)) if early_src == early_src and early_skip == early_skip else float('nan'):.3%}`",
            f"- late_iters_gain_vs_source=`{((late_src - late_skip) / max(late_src, 1e-12)) if late_src == late_src and late_skip == late_skip else float('nan'):.3%}`",
            "",
            "## Verdict",
            "",
        ]
    )
    if rel_vs_source > 0.01 and _mean_metric(skip_cal, "rho") <= _mean_metric(source_cal, "rho") + 0.25:
        lines.append("- Verdict: skip/freeze is a viable next uncertainty consumer; it improves BER without the systematic under-cancellation seen in amplitude weighting.")
    else:
        lines.append("- Verdict: uncertainty appears more useful as an interface/calibration signal than as a direct outer-loop control input; keep skip/freeze as a small probe, not a new mainline.")
    return "\n".join(lines)


def _uncertainty_aware_sic_summary_md(
    fixed_best_mean_ber: float,
    vx_recal_v1_mean_ber: float,
    best_by_seed: dict[str, dict[str, Any]],
    avg_gain_by_seed: dict[str, float],
    best_global: dict[str, float],
    fixed_best_cal: list[dict[str, Any]],
    vx_recal_v1_cal: list[dict[str, Any]],
    sic_cal: list[dict[str, Any]],
    vx_recal_v1_trace: list[dict[str, Any]],
    sic_trace: list[dict[str, Any]],
) -> str:
    def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return float("nan")
        return float(np.mean([float(r[key]) for r in rows]))

    def _iter_mean(rows: list[dict[str, Any]], profile: str, iter_ids: set[int]) -> float:
        vals = [float(r["ber"]) for r in rows if str(r["profile"]) == profile and int(r["outer_iter"]) in iter_ids]
        if not vals:
            return float("nan")
        return float(np.mean(vals))

    sic_mean_ber = float(best_global["mean_ber"])
    rel_vs_fixed = float((fixed_best_mean_ber - sic_mean_ber) / max(fixed_best_mean_ber, 1e-12))
    rel_vs_v1 = float((vx_recal_v1_mean_ber - sic_mean_ber) / max(vx_recal_v1_mean_ber, 1e-12))
    early_v1 = _iter_mean(vx_recal_v1_trace, "fixed_best_vx_recalibration_v1", {0, 1})
    early_sic = _iter_mean(sic_trace, "fixed_best_vx_recalibration_v1_uncertainty_aware_sic", {0, 1})
    late_v1 = _iter_mean(vx_recal_v1_trace, "fixed_best_vx_recalibration_v1", {2, 3, 4})
    late_sic = _iter_mean(sic_trace, "fixed_best_vx_recalibration_v1_uncertainty_aware_sic", {2, 3, 4})
    early_gain = float((early_v1 - early_sic) / max(early_v1, 1e-12)) if early_v1 == early_v1 and early_sic == early_sic else float("nan")
    late_gain = float((late_v1 - late_sic) / max(late_v1, 1e-12)) if late_v1 == late_v1 and late_sic == late_sic else float("nan")
    sic_weight_vals = [float(r["sic_weight_mean"]) for r in sic_cal] if sic_cal else []
    sic_weight_mean = float(np.mean(sic_weight_vals)) if sic_weight_vals else float("nan")
    sic_weight_min = float(np.min(sic_weight_vals)) if sic_weight_vals else float("nan")
    sic_weight_max = float(np.max(sic_weight_vals)) if sic_weight_vals else float("nan")

    lines = [
        "# Stage10 Uncertainty-Aware SIC Summary",
        "",
        f"- fixed_best final_mean_ber=`{fixed_best_mean_ber:.4e}`",
        f"- fixed_best+vx_recalibration_v1 final_mean_ber=`{vx_recal_v1_mean_ber:.4e}`",
        f"- best_global `(sic_kappa)=({best_global['sic_kappa']:.4f})`, final_mean_ber=`{sic_mean_ber:.4e}`",
        f"- rel_gain_vs_fixed_best=`{rel_vs_fixed:.3%}`",
        f"- rel_gain_vs_vx_recal_v1=`{rel_vs_v1:.3%}`",
        "",
        "## Best By Seed / SNR",
        "",
    ]
    for seed_key, items in sorted(best_by_seed.items(), key=lambda kv: int(kv[0])):
        lines.append(f"### seed={seed_key}")
        lines.append("")
        for snr_key, item in sorted(items.items(), key=lambda kv: int(kv[0])):
            lines.append(
                f"- `{snr_key} dB`: kappa=`{item['sic_kappa']:.4f}`, "
                f"rel_gain_vs_fixed_best=`{item['rel_improvement_over_fixed_best']:.3%}`, "
                f"rel_gain_vs_vx_recal_v1=`{item['rel_improvement_over_vx_recal_v1']:.3%}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Aggregate Calibration",
            "",
            f"- fixed_best: mean_rho=`{_mean_metric(fixed_best_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(fixed_best_cal, 'eta'):.3f}`",
            f"- fixed_best+vx_recalibration_v1: mean_rho=`{_mean_metric(vx_recal_v1_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(vx_recal_v1_cal, 'eta'):.3f}`",
            f"- fixed_best+vx_recalibration_v1+uncertainty_aware_sic: mean_rho=`{_mean_metric(sic_cal, 'rho'):.3f}`, mean_eta=`{_mean_metric(sic_cal, 'eta'):.3f}`",
            f"- best_kappa mean_sic_weight=`{sic_weight_mean:.3f}` (range=`{sic_weight_min:.3f}` to `{sic_weight_max:.3f}`)",
            "",
            "## Trace Comparison",
            "",
            f"- early_iters_gain_vs_v1=`{early_gain:.3%}`",
            f"- late_iters_gain_vs_v1=`{late_gain:.3%}`",
            "",
            "## Verdict",
            "",
        ]
    )
    if rel_vs_fixed > 0.03 and rel_vs_v1 > 0.02 and _mean_metric(sic_cal, "rho") < _mean_metric(fixed_best_cal, "rho"):
        lines.append("- Verdict: uncertainty-aware SIC converts calibrated uncertainty into stable BER gains; next step should enter uncertainty-aware refit weighting.")
    else:
        lines.append("- Verdict: uncertainty-aware SIC does not yet deliver a stable enough BER gain; keep this as the first outer-loop use probe and decide next whether to try refit weighting.")
    return "\n".join(lines)


def _calibration_summary_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage8 Detector Calibration Summary",
        "",
        "## Aggregate",
        "",
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["profile"]), int(row["snr_db"])), []).append(row)
    for (profile, snr_db), items in sorted(grouped.items()):
        ratios = [float(x["calibration_ratio"]) for x in items]
        lines.append(
            f"- `{profile} / {snr_db} dB`: "
            f"mean(sym_err/vx)=`{np.mean(ratios):.3f}`"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `sym_err / v_x > 1` means the detector is underestimating true symbol uncertainty.",
        ]
    )
    return "\n".join(lines)


def _calibration_curves_summary_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage8 Detector Calibration Curves Summary",
        "",
        "## By Profile / SNR / Iteration",
        "",
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["profile"]), int(row["snr_db"])), []).append(row)
    for (profile, snr_db), items in sorted(grouped.items()):
        lines.append(f"### {profile} / {snr_db} dB")
        lines.append("")
        for item in sorted(items, key=lambda x: int(x["outer_iter"])):
            lines.append(
                f"- iter `{item['outer_iter']}`: "
                f"vx=`{item['vx_mean']:.4e}`, "
                f"sym_err=`{item['sym_err_mean']:.4e}`, "
                f"ratio=`{item['calibration_ratio']:.3f}`"
            )
        lines.append("")
    first_iters = [float(r["calibration_ratio"]) for r in rows if int(r["outer_iter"]) <= 1]
    late_iters = [float(r["calibration_ratio"]) for r in rows if int(r["outer_iter"]) >= 2]
    lines.extend(
        [
            "## Aggregate",
            "",
            f"- mean calibration ratio at iter `0-1`: `{np.mean(first_iters) if first_iters else float('nan'):.3f}`",
            f"- mean calibration ratio at iter `2+`: `{np.mean(late_iters) if late_iters else float('nan'):.3f}`",
            "",
            "## Interpretation",
            "",
            "- `sym_err / v_x > 1` means posterior variance is too optimistic.",
            "- If early-iter ratios are larger than late-iter ratios, miscalibration is front-loaded in the outer loop.",
        ]
    )
    return "\n".join(lines)


def _sigma_residual_summary_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage8 Detector Sigma-Residual Summary",
        "",
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["profile"]), int(row["snr_db"])), []).append(row)
    for (profile, snr_db), items in sorted(grouped.items()):
        lines.append(f"## {profile} / {snr_db} dB")
        lines.append("")
        for item in sorted(items, key=lambda x: int(x["outer_iter"])):
            lines.append(
                f"- iter `{item['outer_iter']}`: "
                f"detector_sigma=`{item['detector_sigma_mean']:.4e}`, "
                f"emp_residual=`{item['empirical_residual_var']:.4e}`, "
                f"ratio=`{item['sigma_gap_ratio']:.3f}`, "
                f"vx=`{item['vx_mean']:.4e}`, "
                f"sym_err=`{item['sym_err_mean']:.4e}`"
            )
        lines.append("")
    return "\n".join(lines)


def _residual_proxies_summary_md(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Stage8 Detector Residual Proxy Summary",
        "",
        "## By Profile / SNR / Iteration",
        "",
    ]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["profile"]), int(row["snr_db"])), []).append(row)
    for (profile, snr_db), items in sorted(grouped.items()):
        lines.append(f"### {profile} / {snr_db} dB")
        lines.append("")
        for item in sorted(items, key=lambda x: int(x["outer_iter"])):
            lines.append(
                f"- iter `{item['outer_iter']}`: "
                f"sigma_gap=`{item['sigma_gap_ratio']:.3f}`, "
                f"post_sic_residual=`{item['post_sic_residual_energy']:.4e}`, "
                f"channel_update_norm=`{item['channel_update_norm']:.4e}`, "
                f"sigma_ls=`{item['sigma_ls_mean']:.4e}`, "
                f"residual_energy=`{item['residual_energy_mean']:.4e}`"
            )
        lines.append("")
    first_iters = [float(r["sigma_gap_ratio"]) for r in rows if int(r["outer_iter"]) <= 1]
    late_iters = [float(r["sigma_gap_ratio"]) for r in rows if int(r["outer_iter"]) >= 2]
    lines.extend(
        [
            "## Aggregate",
            "",
            f"- mean sigma gap ratio at iter `0-1`: `{np.mean(first_iters) if first_iters else float('nan'):.3f}`",
            f"- mean sigma gap ratio at iter `2+`: `{np.mean(late_iters) if late_iters else float('nan'):.3f}`",
            "",
            "## Interpretation",
            "",
            "- `empirical_residual_var / detector_sigma > 1` means detector-used sigma is too small.",
            "- Compare `post_sic_residual_energy`, `channel_update_norm`, and `sigma_ls_mean` to judge whether inflation is mainly covering SIC residual or channel-mismatch-driven uncertainty.",
        ]
    )
    return "\n".join(lines)


def _trace_summary_md(rows: list[dict[str, Any]], best_constant_meta: dict[str, float] | None, gate_enabled: bool) -> str:
    lines = [
        "# Stage8 Stage6 Outer-Loop Traces",
        "",
        "## Profiles",
        "",
        "- `baseline = (alpha=0.70, sigma=1.0)`",
        "- `hand_fix = (alpha=0.95, sigma=4.0)`",
    ]
    if best_constant_meta is not None:
        lines.append(
            f"- `best_constant_expanded = (alpha={best_constant_meta['alpha']:.3f}, sigma={best_constant_meta['sigma_inflation']:.2f})`"
        )
    if gate_enabled:
        lines.append("- `iter_layered_best = layered constant by outer iteration`")
    lines.append("")
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["profile"]), int(row["snr_db"])), []).append(row)
    for (profile, snr_db), items in sorted(grouped.items()):
        lines.append(f"## {profile} / {snr_db} dB")
        lines.append("")
        for item in sorted(items, key=lambda x: int(x["outer_iter"])):
            lines.append(
                f"- iter `{item['outer_iter']}`: ber=`{item['ber']:.4e}`, "
                f"residual=`{item['residual_energy_mean']:.4e}`, "
                f"sigma_eff=`{item['sigma_eff_mean']:.4e}`, "
                f"v_x=`{item['vx_mean']:.4e}`, "
                f"channel_update_norm=`{item['channel_update_norm']}`"
            )
        lines.append("")
    return "\n".join(lines)


def _is_on_edge(alpha: float, sigma: float, alpha_grid: list[float], sigma_grid: list[float]) -> bool:
    return (
        np.isclose(alpha, min(alpha_grid))
        or np.isclose(alpha, max(alpha_grid))
        or np.isclose(sigma, min(sigma_grid))
        or np.isclose(sigma, max(sigma_grid))
    )


def _seed_region_consistency(seed_best: dict[str, dict[str, dict[str, Any]]]) -> bool:
    if len(seed_best) < 2:
        return True
    seed_keys = sorted(seed_best.keys())
    ref_key = seed_keys[0]
    for snr_key in seed_best[ref_key].keys():
        ref_alpha = float(seed_best[ref_key][snr_key]["alpha"])
        ref_sigma = float(seed_best[ref_key][snr_key]["sigma_inflation"])
        for other_key in seed_keys[1:]:
            cur_alpha = float(seed_best[other_key][snr_key]["alpha"])
            cur_sigma = float(seed_best[other_key][snr_key]["sigma_inflation"])
            if abs(ref_alpha - cur_alpha) > 0.02 or abs(ref_sigma - cur_sigma) > 2.0:
                return False
    return True


def _load_existing_best_constant(
    out_dir: pathlib.Path,
    primary_seed: int,
) -> dict[str, float] | None:
    for name in ("stage6_alpha_sigma_seed_compare_v3.json", "stage6_alpha_sigma_seed_compare_v2.json"):
        seed_compare_path = out_dir / name
        if not seed_compare_path.exists():
            continue
        with open(seed_compare_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        best_global = payload.get("best_constant_global_by_seed") or {}
        item = best_global.get(str(int(primary_seed)))
        if item:
            return {
                "alpha": float(item["alpha"]),
                "sigma_inflation": float(item["sigma_inflation"]),
                "mean_ber": float(item.get("mean_ber", float("nan"))),
            }
    return None


def main():
    parser = argparse.ArgumentParser(description="Stage8 Stage6 heuristic best-constant-first evaluation")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--joint-dir", type=str, default=str(here / "outputs_joint_param_ablation"))
    parser.add_argument("--baseline-dir", type=str, default=str(legacy_root / "outputs_n512"))
    parser.add_argument("--out-dir", type=str, default=str(here / "outputs_stage8_stage6_heuristics"))
    parser.add_argument("--frames", type=int, default=1000)
    parser.add_argument("--snr", nargs="+", type=int, default=[15, 20, 25])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", nargs="*", default=None)
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument("--eval-batch-size", type=int, default=64)
    parser.add_argument("--learned-param-set", type=str, default="fixed")
    parser.add_argument("--alpha-grid", nargs="*", default=None)
    parser.add_argument("--sigma-inflation-grid", nargs="*", default=None)
    parser.add_argument("--expanded-alpha-grid", nargs="*", default=None)
    parser.add_argument("--expanded-sigma-inflation-grid", nargs="*", default=None)
    parser.add_argument("--expanded-alpha-grid-v2", nargs="*", default=None)
    parser.add_argument("--expanded-sigma-inflation-grid-v2", nargs="*", default=None)
    parser.add_argument("--expanded-alpha-grid-v3", nargs="*", default=None)
    parser.add_argument("--expanded-sigma-inflation-grid-v3", nargs="*", default=None)
    parser.add_argument("--run-sigma-only-plateau", type=int, default=1)
    parser.add_argument("--fixed-alpha-for-sigma-only", type=float, default=1.0)
    parser.add_argument("--sigma-only-grid", nargs="*", default=None)
    parser.add_argument("--run-sigma-schedule-v1", type=int, default=1)
    parser.add_argument("--sigma-early-grid", nargs="*", default=None)
    parser.add_argument("--sigma-late-grid", nargs="*", default=None)
    parser.add_argument("--run-iter-layered", type=int, default=1)
    parser.add_argument("--run-calibration-diagnosis", type=int, default=1)
    parser.add_argument("--run-calibration-curves", type=int, default=1)
    parser.add_argument("--run-expanded-v3", type=int, default=1)
    parser.add_argument("--run-fixed-best-export", type=int, default=1)
    parser.add_argument("--run-sigma-early-fix", type=int, default=1)
    parser.add_argument("--run-residual-aware-sigma-v2", type=int, default=1)
    parser.add_argument("--run-vx-recalibration-v1", type=int, default=1)
    parser.add_argument("--run-vx-recalibration-v2-affine", type=int, default=1)
    parser.add_argument("--run-vx-recalibration-v2-clipped", type=int, default=1)
    parser.add_argument("--run-vx-recalibration-v3-hybrid", type=int, default=0)
    parser.add_argument("--run-frame-calibration-dataset-export", type=int, default=0)
    parser.add_argument("--calibration-train-seeds", nargs="*", default=None)
    parser.add_argument("--calibration-val-seeds", nargs="*", default=None)
    parser.add_argument("--run-vx-recalibration-learned", type=int, default=0)
    parser.add_argument("--run-stage13-metric-audit", type=int, default=0)
    parser.add_argument("--stage12-reference-dir", type=str, default="")
    parser.add_argument("--run-vx-recalibration-learned-anchor", type=int, default=0)
    parser.add_argument("--learned-recalibration-epochs", type=int, default=300)
    parser.add_argument("--learned-recalibration-patience", type=int, default=40)
    parser.add_argument("--learned-recalibration-lr", type=float, default=1e-2)
    parser.add_argument("--learned-recalibration-id-reg", type=float, default=1e-3)
    parser.add_argument("--run-uncertainty-aware-sic", type=int, default=0)
    parser.add_argument("--sic-kappa-grid", nargs="*", default=None)
    parser.add_argument("--run-skip-freeze-probe", type=int, default=0)
    parser.add_argument("--skip-freeze-quantile-grid", nargs="*", default=None)
    parser.add_argument("--c0-grid", nargs="*", default=None)
    parser.add_argument("--cr-grid", nargs="*", default=None)
    parser.add_argument("--trace-calibration-only", type=int, default=0)
    parser.add_argument("--trace-best-alpha", type=float, default=None)
    parser.add_argument("--trace-best-sigma-inflation", type=float, default=None)
    args = parser.parse_args()

    snr_list = [int(x) for x in args.snr]
    primary_seed = int(args.seed)
    seeds = _parse_int_grid(args.seeds, [42, 123, 314])
    if primary_seed not in seeds:
        seeds = [primary_seed] + [s for s in seeds if s != primary_seed]
    alpha_grid = _parse_float_grid(args.alpha_grid, [0.70, 0.85, 0.90, 0.95, 0.98])
    sigma_grid = _parse_float_grid(args.sigma_inflation_grid, [1.0, 2.0, 3.0, 4.0, 6.0])
    expanded_alpha_grid = _parse_float_grid(args.expanded_alpha_grid, [0.95, 0.98, 0.99, 0.995, 0.999])
    expanded_sigma_grid = _parse_float_grid(args.expanded_sigma_inflation_grid, [4.0, 6.0, 8.0, 10.0, 12.0])
    expanded_alpha_grid_v2 = _parse_float_grid(args.expanded_alpha_grid_v2, [0.98, 0.99, 0.995, 0.999, 0.9995])
    expanded_sigma_grid_v2 = _parse_float_grid(args.expanded_sigma_inflation_grid_v2, [12.0, 16.0, 20.0, 24.0])
    expanded_alpha_grid_v3 = _parse_float_grid(args.expanded_alpha_grid_v3, [0.999, 0.9995, 0.9999])
    expanded_sigma_grid_v3 = _parse_float_grid(args.expanded_sigma_inflation_grid_v3, [16.0, 20.0, 24.0, 32.0])
    sigma_only_grid = _parse_float_grid(args.sigma_only_grid, [16.0, 20.0, 24.0, 32.0])
    sigma_early_grid = _parse_float_grid(args.sigma_early_grid, [8.0, 12.0, 16.0, 20.0, 24.0])
    sigma_late_grid = _parse_float_grid(args.sigma_late_grid, [1.0, 2.0, 4.0, 8.0, 12.0])
    sic_kappa_grid = _parse_float_grid(args.sic_kappa_grid, [0.0, 0.5, 1.0, 2.0, 4.0])
    skip_freeze_quantile_grid = _parse_float_grid(args.skip_freeze_quantile_grid, [0.90, 0.95, 0.99])
    c0_grid = _parse_float_grid(args.c0_grid, [1.0, 2.0, 4.0, 8.0])
    cr_grid = _parse_float_grid(args.cr_grid, [0.25, 0.5, 1.0, 2.0, 4.0])
    calibration_train_seeds = _parse_int_grid(args.calibration_train_seeds, [11, 17, 23, 29, 31, 37, 43, 47])
    calibration_val_seeds = _parse_int_grid(args.calibration_val_seeds, [53, 59])

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    joint_dir = pathlib.Path(args.joint_dir)
    baseline_dir = pathlib.Path(args.baseline_dir)

    _set_seed(primary_seed)
    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, baseline_dir)
    sys_obj.k_leak = args.k_leak
    device = sys_obj._pt_device()

    model, data_pos, ckpt = _load_stage6_fixed_model(
        sys_obj=sys_obj,
        joint_dir=joint_dir,
        device=device,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.learned_param_set,
    )
    print(f"  Stage6 fixed loaded from {ckpt}")

    all_batch_seeds = list(dict.fromkeys(seeds + calibration_train_seeds + calibration_val_seeds))
    seed_batches_all = {
        int(seed): _build_batches(
            sys_obj=sys_obj,
            device=device,
            snr_list=snr_list,
            frames=args.frames,
            seed=int(seed),
        )
        for seed in all_batch_seeds
    }
    seed_batches = {int(seed): seed_batches_all[int(seed)] for seed in seeds}
    calibration_seed_batches = {
        int(seed): seed_batches_all[int(seed)]
        for seed in list(dict.fromkeys(calibration_train_seeds + calibration_val_seeds))
    }

    profile_defs = [
        ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
        ("alpha95", {"alpha": 0.95, "detector_sigma_inflation": 1.0}),
        ("sigma4", {"alpha": 0.70, "detector_sigma_inflation": 4.0}),
        ("alpha95_sigma4", {"alpha": 0.95, "detector_sigma_inflation": 4.0}),
    ]

    primary_best_constant: dict[str, float] | None = None
    sigma_only_primary_best: dict[str, float] | None = None
    sigma_only_best_by_seed: dict[str, dict[str, dict[str, Any]]] = {}
    sigma_only_global_by_seed: dict[str, dict[str, float]] = {}
    sigma_schedule_rows: list[dict[str, Any]] = []
    sigma_schedule_best_by_seed: dict[str, dict[str, dict[str, Any]]] = {}
    sigma_schedule_avg_gain_by_seed: dict[str, float] = {}
    sigma_schedule_success = False
    iterlayer_verdict = "fixed"
    iterlayer_rows: list[dict[str, Any]] = []
    iterlayer_best_by_seed: dict[str, dict[str, dict[str, Any]]] = {}

    if int(args.trace_calibration_only):
        loaded_best = _load_existing_best_constant(out_dir, primary_seed)
        if args.trace_best_alpha is not None and args.trace_best_sigma_inflation is not None:
            primary_best_constant = {
                "alpha": float(args.trace_best_alpha),
                "sigma_inflation": float(args.trace_best_sigma_inflation),
                "mean_ber": float("nan"),
            }
        elif loaded_best is not None:
            primary_best_constant = loaded_best
        else:
            raise FileNotFoundError(
                "trace-calibration-only requires either existing "
                "`stage6_alpha_sigma_seed_compare_v2.json` in out-dir or explicit "
                "`--trace-best-alpha/--trace-best-sigma-inflation`."
            )
    else:

        print("\n==> Fixed profiles (primary seed)")
        profile_rows, baseline_by_snr = _make_profile_rows(
            model=model,
            batches=seed_batches[primary_seed],
            data_pos=data_pos,
            snr_list=snr_list,
            profile_defs=profile_defs,
            seed=primary_seed,
            eval_batch_size=args.eval_batch_size,
        )
        for row in profile_rows:
            print(f"  {row['profile']} / {row['snr_db']} dB: ber={row['ber']:.4e}")
        _write_csv(out_dir / "stage6_heuristic_profiles.csv", profile_rows)
        with open(out_dir / "stage6_heuristic_profiles_summary.md", "w", encoding="utf-8") as f:
            f.write(_profile_summary_md(profile_rows, profile_defs) + "\n")

        print("\n==> Coarse alpha x sigma surface (primary seed)")
        coarse_rows, coarse_best_by_snr = _surface_rows(
        model=model,
        batches=seed_batches[primary_seed],
        data_pos=data_pos,
        snr_list=snr_list,
        alpha_grid=alpha_grid,
        sigma_grid=sigma_grid,
        baseline_by_snr=baseline_by_snr,
        seed=primary_seed,
        eval_batch_size=args.eval_batch_size,
    )
        for snr_key, item in sorted(coarse_best_by_snr.items(), key=lambda kv: int(kv[0])):
            print(
                f"  {snr_key} dB: best alpha={item['alpha']:.2f}, "
                f"sigma={item['sigma_inflation']:.2f}, ber={item['candidate_ber']:.4e}"
            )
        _write_csv(out_dir / "stage6_alpha_sigma_surface.csv", coarse_rows)
        with open(out_dir / "stage6_alpha_sigma_best_by_snr.json", "w", encoding="utf-8") as f:
            json.dump(coarse_best_by_snr, f, indent=2, ensure_ascii=False)

        profile_alpha95_sigma4 = {
        int(row["snr_db"]): float(row["ber"])
        for row in profile_rows
        if row["profile"] == "alpha95_sigma4"
    }
        coarse_alphas = [float(item["alpha"]) for item in coarse_best_by_snr.values()]
        coarse_sigmas = [float(item["sigma_inflation"]) for item in coarse_best_by_snr.values()]
        alpha_span = max(coarse_alphas) - min(coarse_alphas)
        sigma_unique_count = len(set(coarse_sigmas))
        alpha95_sigma4_gap = float(
            np.mean(
                [
                    max(profile_alpha95_sigma4[int(snr_db)] - float(coarse_best_by_snr[str(int(snr_db))]["candidate_ber"]), 0.0)
                    / max(float(coarse_best_by_snr[str(int(snr_db))]["candidate_ber"]), 1e-12)
                    for snr_db in snr_list
                ]
            )
        )
        coarse_verdict = "fixed" if alpha_span <= 0.05 and alpha95_sigma4_gap <= 0.05 else "gate"
        with open(out_dir / "stage6_alpha_sigma_summary.md", "w", encoding="utf-8") as f:
            f.write(
                _surface_summary_md(
                    best_by_snr=coarse_best_by_snr,
                    alpha_span=alpha_span,
                    sigma_unique_count=sigma_unique_count,
                    alpha95_sigma4_gap=alpha95_sigma4_gap,
                    verdict=coarse_verdict,
                )
                + "\n"
            )

        print("\n==> Expanded best-constant sweep (multi-seed)")
        expanded_rows: list[dict[str, Any]] = []
        expanded_seed_best: dict[str, dict[str, dict[str, Any]]] = {}
        expanded_seed_global: dict[str, dict[str, float]] = {}
        edge_summary = {"any_edge_hit": False, "by_seed": {}}
        for seed in seeds:
            batches = seed_batches[int(seed)]
            seed_profile_rows, seed_baseline = _make_profile_rows(
                model=model,
                batches=batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=[("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0})],
                seed=int(seed),
                eval_batch_size=args.eval_batch_size,
            )
            del seed_profile_rows
            seed_rows, seed_best = _surface_rows(
                model=model,
                batches=batches,
                data_pos=data_pos,
                snr_list=snr_list,
                alpha_grid=expanded_alpha_grid,
                sigma_grid=expanded_sigma_grid,
                baseline_by_snr=seed_baseline,
                seed=int(seed),
                eval_batch_size=args.eval_batch_size,
            )
            expanded_rows.extend(seed_rows)
            expanded_seed_best[str(int(seed))] = seed_best
            expanded_seed_global[str(int(seed))] = _best_constant_from_rows(seed_rows)
            edge_summary["by_seed"][str(int(seed))] = {}
            for snr_key, item in seed_best.items():
                is_edge = _is_on_edge(
                    alpha=float(item["alpha"]),
                    sigma=float(item["sigma_inflation"]),
                    alpha_grid=expanded_alpha_grid,
                    sigma_grid=expanded_sigma_grid,
                )
                edge_summary["by_seed"][str(int(seed))][snr_key] = bool(is_edge)
                edge_summary["any_edge_hit"] = bool(edge_summary["any_edge_hit"] or is_edge)
            print(
                f"  seed={seed}: global best alpha={expanded_seed_global[str(int(seed))]['alpha']:.3f}, "
                f"sigma={expanded_seed_global[str(int(seed))]['sigma_inflation']:.2f}, "
                f"mean_ber={expanded_seed_global[str(int(seed))]['mean_ber']:.4e}"
            )
        consistent_region = _seed_region_consistency(expanded_seed_best)
        _write_csv(out_dir / "stage6_alpha_sigma_surface_expanded.csv", expanded_rows)
        with open(out_dir / "stage6_alpha_sigma_best_by_snr_expanded.json", "w", encoding="utf-8") as f:
            json.dump(expanded_seed_best, f, indent=2, ensure_ascii=False)
        with open(out_dir / "stage6_alpha_sigma_seed_compare.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_by_seed": expanded_seed_best,
                    "best_constant_global_by_seed": expanded_seed_global,
                    "edge_summary": edge_summary,
                    "consistent_best_region": consistent_region,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        with open(out_dir / "stage6_alpha_sigma_summary_expanded.md", "w", encoding="utf-8") as f:
            f.write(_expanded_summary_md(expanded_seed_best, edge_summary, consistent_region) + "\n")

        print("\n==> Expanded best-constant sweep v2 (multi-seed)")
        expanded_rows_v2: list[dict[str, Any]] = []
        expanded_seed_best_v2: dict[str, dict[str, dict[str, Any]]] = {}
        expanded_seed_global_v2: dict[str, dict[str, float]] = {}
        edge_summary_v2 = {"any_edge_hit": False, "by_seed": {}}
        for seed in seeds:
            seed = int(seed)
            batches = seed_batches[seed]
            seed_profile_rows, seed_baseline = _make_profile_rows(
                model=model,
                batches=batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=[("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0})],
                seed=seed,
                eval_batch_size=args.eval_batch_size,
            )
            del seed_profile_rows
            seed_rows, seed_best = _surface_rows(
                model=model,
                batches=batches,
                data_pos=data_pos,
                snr_list=snr_list,
                alpha_grid=expanded_alpha_grid_v2,
                sigma_grid=expanded_sigma_grid_v2,
                baseline_by_snr=seed_baseline,
                seed=seed,
                eval_batch_size=args.eval_batch_size,
            )
            expanded_rows_v2.extend(seed_rows)
            expanded_seed_best_v2[str(seed)] = seed_best
            expanded_seed_global_v2[str(seed)] = _best_constant_from_rows(seed_rows)
            edge_summary_v2["by_seed"][str(seed)] = {}
            for snr_key, item in seed_best.items():
                is_edge = _is_on_edge(
                    alpha=float(item["alpha"]),
                    sigma=float(item["sigma_inflation"]),
                    alpha_grid=expanded_alpha_grid_v2,
                    sigma_grid=expanded_sigma_grid_v2,
                )
                edge_summary_v2["by_seed"][str(seed)][snr_key] = bool(is_edge)
                edge_summary_v2["any_edge_hit"] = bool(edge_summary_v2["any_edge_hit"] or is_edge)
            print(
                f"  seed={seed}: global best v2 alpha={expanded_seed_global_v2[str(seed)]['alpha']:.4f}, "
                f"sigma={expanded_seed_global_v2[str(seed)]['sigma_inflation']:.2f}, "
                f"mean_ber={expanded_seed_global_v2[str(seed)]['mean_ber']:.4e}"
            )
        consistent_region_v2 = _seed_region_consistency(expanded_seed_best_v2)
        _write_csv(out_dir / "stage6_alpha_sigma_surface_expanded_v2.csv", expanded_rows_v2)
        with open(out_dir / "stage6_alpha_sigma_best_by_snr_expanded_v2.json", "w", encoding="utf-8") as f:
            json.dump(expanded_seed_best_v2, f, indent=2, ensure_ascii=False)
        with open(out_dir / "stage6_alpha_sigma_seed_compare_v2.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_by_seed": expanded_seed_best_v2,
                    "best_constant_global_by_seed": expanded_seed_global_v2,
                    "edge_summary": edge_summary_v2,
                    "consistent_best_region": consistent_region_v2,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        with open(out_dir / "stage6_alpha_sigma_summary_expanded_v2.md", "w", encoding="utf-8") as f:
            f.write(_expanded_summary_md(expanded_seed_best_v2, edge_summary_v2, consistent_region_v2) + "\n")
        reference_best_by_seed = expanded_seed_best_v2
        reference_best_global = expanded_seed_global_v2
        reference_edge_summary = edge_summary_v2
        primary_best_constant = expanded_seed_global_v2[str(primary_seed)]

        if int(args.run_expanded_v3):
            print("\n==> Expanded best-constant sweep v3 (multi-seed)")
            expanded_rows_v3: list[dict[str, Any]] = []
            expanded_seed_best_v3: dict[str, dict[str, dict[str, Any]]] = {}
            expanded_seed_global_v3: dict[str, dict[str, float]] = {}
            edge_summary_v3 = {"any_edge_hit": False, "by_seed": {}}
            for seed in seeds:
                seed = int(seed)
                batches = seed_batches[seed]
                seed_profile_rows, seed_baseline = _make_profile_rows(
                    model=model,
                    batches=batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    profile_defs=[("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0})],
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                del seed_profile_rows
                seed_rows, seed_best = _surface_rows(
                    model=model,
                    batches=batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    alpha_grid=expanded_alpha_grid_v3,
                    sigma_grid=expanded_sigma_grid_v3,
                    baseline_by_snr=seed_baseline,
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                expanded_rows_v3.extend(seed_rows)
                expanded_seed_best_v3[str(seed)] = seed_best
                expanded_seed_global_v3[str(seed)] = _best_constant_from_rows(seed_rows)
                edge_summary_v3["by_seed"][str(seed)] = {}
                for snr_key, item in seed_best.items():
                    is_edge = _is_on_edge(
                        alpha=float(item["alpha"]),
                        sigma=float(item["sigma_inflation"]),
                        alpha_grid=expanded_alpha_grid_v3,
                        sigma_grid=expanded_sigma_grid_v3,
                    )
                    edge_summary_v3["by_seed"][str(seed)][snr_key] = bool(is_edge)
                    edge_summary_v3["any_edge_hit"] = bool(edge_summary_v3["any_edge_hit"] or is_edge)
                print(
                    f"  seed={seed}: global best v3 alpha={expanded_seed_global_v3[str(seed)]['alpha']:.4f}, "
                    f"sigma={expanded_seed_global_v3[str(seed)]['sigma_inflation']:.2f}, "
                    f"mean_ber={expanded_seed_global_v3[str(seed)]['mean_ber']:.4e}"
                )
            consistent_region_v3 = _seed_region_consistency(expanded_seed_best_v3)
            _write_csv(out_dir / "stage6_alpha_sigma_surface_expanded_v3.csv", expanded_rows_v3)
            with open(out_dir / "stage6_alpha_sigma_best_by_snr_expanded_v3.json", "w", encoding="utf-8") as f:
                json.dump(expanded_seed_best_v3, f, indent=2, ensure_ascii=False)
            with open(out_dir / "stage6_alpha_sigma_seed_compare_v3.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "best_by_seed": expanded_seed_best_v3,
                        "best_constant_global_by_seed": expanded_seed_global_v3,
                        "edge_summary": edge_summary_v3,
                        "consistent_best_region": consistent_region_v3,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            with open(out_dir / "stage6_alpha_sigma_summary_expanded_v3.md", "w", encoding="utf-8") as f:
                f.write(_expanded_summary_md(expanded_seed_best_v3, edge_summary_v3, consistent_region_v3) + "\n")
            reference_best_by_seed = expanded_seed_best_v3
            reference_best_global = expanded_seed_global_v3
            reference_edge_summary = edge_summary_v3
            primary_best_constant = expanded_seed_global_v3[str(primary_seed)]

        if int(args.run_sigma_only_plateau):
            print("\n==> Sigma-only plateau sweep (multi-seed)")
            sigma_only_rows: list[dict[str, Any]] = []
            sigma_only_mean_by_seed: dict[str, dict[str, float]] = {}
            for seed in seeds:
                seed = int(seed)
                batches = seed_batches[seed]
                seed_profile_rows, seed_baseline = _make_profile_rows(
                    model=model,
                    batches=batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    profile_defs=[("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0})],
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                del seed_profile_rows
                seed_rows, seed_best, sigma_mean_ber = _sigma_only_rows(
                    model=model,
                    batches=batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    fixed_alpha=float(args.fixed_alpha_for_sigma_only),
                    sigma_grid=sigma_only_grid,
                    baseline_by_snr=seed_baseline,
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                sigma_only_rows.extend(seed_rows)
                sigma_only_best_by_seed[str(seed)] = seed_best
                sigma_only_global_by_seed[str(seed)] = _best_sigma_from_rows(seed_rows, float(args.fixed_alpha_for_sigma_only))
                sigma_only_mean_by_seed[str(seed)] = sigma_mean_ber
                print(
                    f"  seed={seed}: sigma-only best alpha={sigma_only_global_by_seed[str(seed)]['alpha']:.4f}, "
                    f"sigma={sigma_only_global_by_seed[str(seed)]['sigma_inflation']:.2f}, "
                    f"mean_ber={sigma_only_global_by_seed[str(seed)]['mean_ber']:.4e}"
                )
            sigma_only_primary_best = sigma_only_global_by_seed[str(primary_seed)]
            _write_csv(out_dir / "stage6_sigma_only_plateau.csv", sigma_only_rows)
            with open(out_dir / "stage6_sigma_only_best_by_snr.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "best_by_seed": sigma_only_best_by_seed,
                        "best_constant_global_by_seed": sigma_only_global_by_seed,
                        "sigma_mean_ber_by_seed": sigma_only_mean_by_seed,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            with open(out_dir / "stage6_sigma_only_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _sigma_only_summary_md(
                        best_by_snr=sigma_only_best_by_seed[str(primary_seed)],
                        sigma_mean_ber=sigma_only_mean_by_seed[str(primary_seed)],
                        sigma_grid=sigma_only_grid,
                    )
                    + "\n"
                )

        if int(args.run_sigma_schedule_v1):
            print("\n==> Sigma schedule v1 (multi-seed)")
            for seed in seeds:
                seed = int(seed)
                if str(seed) not in sigma_only_best_by_seed:
                    continue
                rows_seed, best_seed = _evaluate_sigma_schedule_rows(
                    model=model,
                    batches=seed_batches[seed],
                    data_pos=data_pos,
                    snr_list=snr_list,
                    sigma_only_best_by_snr=sigma_only_best_by_seed[str(seed)],
                    num_outer_iters=args.num_outer_iters,
                    fixed_alpha=float(args.fixed_alpha_for_sigma_only),
                    sigma_early_grid=sigma_early_grid,
                    sigma_late_grid=sigma_late_grid,
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                sigma_schedule_rows.extend(rows_seed)
                sigma_schedule_best_by_seed[str(seed)] = best_seed
                avg_gain = float(np.mean([float(x["rel_improvement_over_sigma_only_best"]) for x in best_seed.values()]))
                sigma_schedule_avg_gain_by_seed[str(seed)] = avg_gain
                print(f"  seed={seed}: sigma-schedule v1 avg gain vs sigma-only best = {avg_gain:.3%}")
            sigma_schedule_success = all(g > 0.05 for g in sigma_schedule_avg_gain_by_seed.values()) and len(sigma_schedule_avg_gain_by_seed) > 0
            _write_csv(out_dir / "stage6_sigma_schedule_v1_surface.csv", sigma_schedule_rows)
            with open(out_dir / "stage6_sigma_schedule_v1_best.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "sigma_only_global_by_seed": sigma_only_global_by_seed,
                        "sigma_schedule_best_by_seed": sigma_schedule_best_by_seed,
                        "avg_improvement_by_seed": sigma_schedule_avg_gain_by_seed,
                        "success": sigma_schedule_success,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            with open(out_dir / "stage6_sigma_schedule_v1_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _sigma_schedule_summary_md(
                        sigma_only_global_by_seed=sigma_only_global_by_seed,
                        schedule_best_by_seed=sigma_schedule_best_by_seed,
                        avg_improvement_by_seed=sigma_schedule_avg_gain_by_seed,
                        success=sigma_schedule_success,
                    )
                    + "\n"
                )

        avg_improvement_by_seed: dict[str, float] = {}
        consistent_gate_gain = False
        iterlayer_verdict = "fixed"
        if int(args.run_iter_layered):
            print("\n==> Iter-layered oracle around expanded best-constant")
            for seed in seeds:
                seed = int(seed)
                rows_seed, best_seed = _evaluate_iterlayer_rows(
                    model=model,
                    batches=seed_batches[seed],
                    data_pos=data_pos,
                    snr_list=snr_list,
                    best_by_snr=reference_best_by_seed[str(seed)],
                    num_outer_iters=args.num_outer_iters,
                    seed=seed,
                    eval_batch_size=args.eval_batch_size,
                )
                iterlayer_rows.extend(rows_seed)
                iterlayer_best_by_seed[str(seed)] = best_seed
                avg_gain = float(np.mean([float(x["rel_improvement_over_best_constant"]) for x in best_seed.values()]))
                avg_improvement_by_seed[str(seed)] = avg_gain
                print(f"  seed={seed}: iter-layered avg gain vs best-constant = {avg_gain:.3%}")
            consistent_gate_gain = all(gain > 0.10 for gain in avg_improvement_by_seed.values()) and len(avg_improvement_by_seed) > 0
            iterlayer_verdict = "gate" if consistent_gate_gain else "fixed"
            _write_csv(out_dir / "stage6_alpha_sigma_iterlayer_surface.csv", iterlayer_rows)
            with open(out_dir / "stage6_alpha_sigma_iterlayer_best.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "best_constant_global_by_seed": reference_best_global,
                        "iterlayer_best_by_seed": iterlayer_best_by_seed,
                        "avg_improvement_by_seed": avg_improvement_by_seed,
                        "consistent_gate_gain": consistent_gate_gain,
                        "verdict": iterlayer_verdict,
                        "reference_edge_hit": bool(reference_edge_summary["any_edge_hit"]),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            with open(out_dir / "stage6_alpha_sigma_iterlayer_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _iterlayer_summary_md(
                        best_constant_global=reference_best_global,
                        iterlayer_best=iterlayer_best_by_seed,
                        avg_improvement_by_seed=avg_improvement_by_seed,
                        consistent_gate_gain=consistent_gate_gain,
                        verdict=iterlayer_verdict,
                    )
                    + "\n"
                )

    print("\n==> Outer-loop traces (primary seed)")
    active_best_constant = sigma_only_primary_best if sigma_only_primary_best is not None else primary_best_constant
    assert active_best_constant is not None
    trace_profiles = [
        ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
        ("hand_fix", {"alpha": 0.95, "detector_sigma_inflation": 4.0}),
        (
            "sigma_only_best" if sigma_only_primary_best is not None else "best_constant_expanded_v3",
            {
                "alpha": float(active_best_constant["alpha"]),
                "detector_sigma_inflation": float(active_best_constant["sigma_inflation"]),
            },
        ),
    ]
    if iterlayer_verdict == "gate" and str(primary_seed) in iterlayer_best_by_seed:
        global_iter_rows = iterlayer_rows if iterlayer_rows else []
        best_global = None
        for row in global_iter_rows:
            if int(row["seed"]) != primary_seed:
                continue
            if best_global is None or float(row["candidate_ber"]) < float(best_global["candidate_ber"]):
                best_global = row
        if best_global is not None:
            trace_profiles.append(
                (
                    "iter_layered_best",
                    {
                        "alpha": [float(best_global["alpha_1"])] + [float(best_global["alpha_late"])] * max(args.num_outer_iters - 1, 0),
                        "detector_sigma_inflation": [float(best_global["sigma_1"])] + [float(best_global["sigma_late"])] * max(args.num_outer_iters - 1, 0),
                    },
                )
            )
    trace_rows: list[dict[str, Any]] = []
    for profile_name, overrides in trace_profiles:
        for snr_db in snr_list:
            stats = _evaluate_stage6_profile(
                model,
                seed_batches[primary_seed][int(snr_db)],
                data_pos,
                overrides,
                eval_batch_size=args.eval_batch_size,
                collect_traces=True,
            )
            for t, stage in enumerate(stats["trace_history"]):
                trace_rows.append(
                    {
                        "seed": int(primary_seed),
                        "profile": profile_name,
                        "snr_db": int(snr_db),
                        "outer_iter": int(t),
                        "ber": float(stage["ber"]),
                        "residual_energy_mean": float(stage["residual_energy_mean"]),
                        "sigma_eff_mean": float(stage["sigma_eff_mean"]),
                        "vx_mean": float(stage["vx_mean"]),
                        "channel_update_norm": float(stage["channel_update_norm"]),
                    }
                )
            print(f"  {profile_name} / {snr_db} dB: traced {len(stats['trace_history'])} iters")
    _write_csv(out_dir / "stage6_outerloop_traces.csv", trace_rows)
    with open(out_dir / "stage6_outerloop_traces_summary.md", "w", encoding="utf-8") as f:
        f.write(
            _trace_summary_md(
                rows=trace_rows,
                best_constant_meta=active_best_constant,
                gate_enabled=iterlayer_verdict == "gate",
            )
            + "\n"
        )

    run_calibration_outputs = bool(int(args.run_calibration_diagnosis) or int(args.run_calibration_curves))
    if run_calibration_outputs:
        print("\n==> Detector calibration diagnosis")
        calib_profiles = [
            ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
            ("hand_fix", {"alpha": 0.95, "detector_sigma_inflation": 4.0}),
            (
                "sigma_only_best" if sigma_only_primary_best is not None else "best_constant_expanded_v3",
                {
                    "alpha": float(active_best_constant["alpha"]),
                    "detector_sigma_inflation": float(active_best_constant["sigma_inflation"]),
                },
            ),
        ]
        calib_rows: list[dict[str, Any]] = []
        sigma_rows: list[dict[str, Any]] = []
        for profile_name, overrides in calib_profiles:
            for snr_db in snr_list:
                stats = _evaluate_stage6_profile(
                    model,
                    seed_batches[primary_seed][int(snr_db)],
                    data_pos,
                    overrides,
                    eval_batch_size=args.eval_batch_size,
                    collect_traces=True,
                )
                for t, stage in enumerate(stats["calibration_history"]):
                    base = {
                        "seed": int(primary_seed),
                        "profile": profile_name,
                        "snr_db": int(snr_db),
                        "outer_iter": int(t),
                    }
                    calib_rows.append(
                        {
                            **base,
                            "vx_mean": float(stage["vx_mean"]),
                            "sym_err_mean": float(stage["sym_err_mean"]),
                            "calibration_ratio": float(stage["calibration_ratio"]),
                        }
                    )
                    sigma_rows.append(
                        {
                            **base,
                            "detector_sigma_mean": float(stage["detector_sigma_mean"]),
                            "empirical_residual_var": float(stage["empirical_residual_var"]),
                            "sigma_gap_ratio": float(stage["sigma_gap_ratio"]),
                            "post_sic_residual_energy": float(stage["post_sic_residual_energy"]),
                            "channel_update_norm": float(stage["channel_update_norm"]),
                            "sigma_ls_mean": float(stage["sigma_ls_mean"]),
                            "vx_mean": float(stage["vx_mean"]),
                            "sym_err_mean": float(stage["sym_err_mean"]),
                        }
                    )
        _write_csv(out_dir / "stage6_detector_calibration.csv", calib_rows)
        with open(out_dir / "stage6_detector_calibration_summary.md", "w", encoding="utf-8") as f:
            f.write(_calibration_summary_md(calib_rows) + "\n")
        _write_csv(out_dir / "stage6_detector_calibration_curves.csv", calib_rows)
        with open(out_dir / "stage6_detector_calibration_curves_summary.md", "w", encoding="utf-8") as f:
            f.write(_calibration_curves_summary_md(calib_rows) + "\n")
        _write_csv(out_dir / "stage6_detector_sigma_residual.csv", sigma_rows)
        with open(out_dir / "stage6_detector_sigma_residual_summary.md", "w", encoding="utf-8") as f:
            f.write(_sigma_residual_summary_md(sigma_rows) + "\n")
        residual_proxy_rows = []
        for row in sigma_rows:
            residual_proxy_rows.append(
                {
                    "seed": row["seed"],
                    "profile": row["profile"],
                    "snr_db": row["snr_db"],
                    "outer_iter": row["outer_iter"],
                    "detector_sigma_mean": row["detector_sigma_mean"],
                    "empirical_residual_var": row["empirical_residual_var"],
                    "sigma_gap_ratio": row["sigma_gap_ratio"],
                    "post_sic_residual_energy": row["post_sic_residual_energy"],
                    "channel_update_norm": row["channel_update_norm"],
                    "sigma_ls_mean": row["sigma_ls_mean"],
                    "residual_energy_mean": row["empirical_residual_var"],
                }
            )
        _write_csv(out_dir / "stage6_detector_residual_proxies.csv", residual_proxy_rows)
        with open(out_dir / "stage6_detector_residual_proxies_summary.md", "w", encoding="utf-8") as f:
            f.write(_residual_proxies_summary_md(residual_proxy_rows) + "\n")

    fixed_best_alpha = 1.0
    fixed_best_sigma = 16.0
    fixed_best_summary_rows: list[dict[str, Any]] = []
    fixed_best_trace_rows: list[dict[str, Any]] = []
    fixed_best_calib_rows: list[dict[str, Any]] = []
    fixed_best_by_seed: dict[str, dict[int, float]] = {}
    sigma_early_fix_rows: list[dict[str, Any]] = []
    sigma_early_fix_best_by_seed: dict[str, dict[str, Any]] = {}
    sigma_early_fix_avg_gain_by_seed: dict[str, float] = {}
    sigma_early_fix_best_global: dict[str, float] | None = None
    residual_v2_rows: list[dict[str, Any]] = []
    residual_v2_best_by_seed: dict[str, dict[str, Any]] = {}
    residual_v2_avg_gain_by_seed: dict[str, float] = {}
    residual_v2_best_global: dict[str, float] | None = None
    calibration_dataset_rows: list[dict[str, Any]] = []
    coeff_payload: dict[str, Any] | None = None
    vx_recal_trace_rows: list[dict[str, Any]] = []
    vx_recal_cal_rows: list[dict[str, Any]] = []
    vx_recal_v1_by_seed: dict[str, dict[int, float]] = {}

    if int(args.run_fixed_best_export):
        print("\n==> Stage9 fixed-best export")
        fixed_profile_defs = [("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma})]
        for seed in seeds:
            seed_rows, _seed_baseline_unused = _make_profile_rows(
                model=model,
                batches=seed_batches[int(seed)],
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=fixed_profile_defs,
                seed=int(seed),
                eval_batch_size=args.eval_batch_size,
            )
            fixed_best_summary_rows.extend(seed_rows)
            fixed_best_by_seed[str(int(seed))] = {
                int(row["snr_db"]): float(row["ber"])
                for row in seed_rows
            }
        fixed_best_trace_rows, fixed_best_calib_rows = _collect_profile_diagnostics(
            model=model,
            seed_batches=seed_batches,
            data_pos=data_pos,
            snr_list=snr_list,
            profile_defs=fixed_profile_defs,
            seeds=seeds,
            eval_batch_size=args.eval_batch_size,
        )
        _write_csv(out_dir / "stage6_fixed_best_traces.csv", fixed_best_trace_rows)
        _write_csv(out_dir / "stage6_fixed_best_calibration.csv", fixed_best_calib_rows)
        with open(out_dir / "stage6_fixed_best_summary.md", "w", encoding="utf-8") as f:
            f.write(_fixed_best_summary_md(fixed_best_summary_rows, fixed_best_alpha, fixed_best_sigma) + "\n")

    fixed_best_mean_ber = float(np.mean([float(r["ber"]) for r in fixed_best_summary_rows])) if fixed_best_summary_rows else float("nan")
    coeff_payload: dict[str, Any] | None = None
    vx_recal_v1_by_seed: dict[str, dict[int, float]] = {}
    vx_recal_mean_ber = float("nan")
    baseline_rows: list[dict[str, Any]] = []
    fixed_rows: list[dict[str, Any]] = []
    recal_rows: list[dict[str, Any]] = []
    affine_payload: dict[str, Any] | None = None
    affine_mean_ber = float("nan")
    affine_rows: list[dict[str, Any]] = []
    affine_trace_rows: list[dict[str, Any]] = []
    affine_success = False
    clipped_payload: dict[str, Any] | None = None
    clipped_mean_ber = float("nan")
    clipped_rows: list[dict[str, Any]] = []
    clipped_trace_rows: list[dict[str, Any]] = []
    clipped_success = False
    hybrid_v3_mean_ber = float("nan")
    hybrid_v3_rows: list[dict[str, Any]] = []
    hybrid_v3_trace_rows: list[dict[str, Any]] = []

    if fixed_best_calib_rows and any(
        [
            int(args.run_vx_recalibration_v1),
            int(args.run_vx_recalibration_v2_affine),
            int(args.run_vx_recalibration_v2_clipped),
            int(args.run_vx_recalibration_v3_hybrid),
            int(args.run_vx_recalibration_learned),
            int(args.run_vx_recalibration_learned_anchor),
            int(args.run_skip_freeze_probe),
        ]
    ):
        coeff_payload = _fit_vx_recalibration_coeffs(fixed_best_calib_rows)
    if fixed_best_calib_rows and any([int(args.run_vx_recalibration_v2_affine), int(args.run_vx_recalibration_v3_hybrid)]):
        affine_payload = _fit_vx_recalibration_affine_coeffs(fixed_best_calib_rows)
    if fixed_best_calib_rows and int(args.run_vx_recalibration_v2_clipped):
        clipped_payload = _fit_vx_recalibration_clipped_coeffs(fixed_best_calib_rows)

    if int(args.run_sigma_early_fix) and fixed_best_by_seed:
        print("\n==> Stage9 sigma early-fix")
        sigma_early_fix_rows, sigma_early_fix_best_by_seed, sigma_early_fix_avg_gain_by_seed, sigma_early_fix_best_global = _evaluate_sigma_early_fix_rows(
            model=model,
            seed_batches=seed_batches,
            data_pos=data_pos,
            snr_list=snr_list,
            seeds=seeds,
            num_outer_iters=args.num_outer_iters,
            sigma_early_grid=sigma_early_grid,
            sigma_late_grid=sigma_late_grid,
            fixed_best_by_seed=fixed_best_by_seed,
            eval_batch_size=args.eval_batch_size,
        )
        sigma_early_fix_success = (
            sigma_early_fix_best_global is not None
            and fixed_best_mean_ber == fixed_best_mean_ber
            and float(sigma_early_fix_best_global["mean_ber"]) < 0.95 * fixed_best_mean_ber
        )
        _write_csv(out_dir / "stage6_sigma_early_fix_surface.csv", sigma_early_fix_rows)
        with open(out_dir / "stage6_sigma_early_fix_best.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_by_seed": sigma_early_fix_best_by_seed,
                    "avg_improvement_by_seed": sigma_early_fix_avg_gain_by_seed,
                    "best_global": sigma_early_fix_best_global,
                    "success": sigma_early_fix_success,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        with open(out_dir / "stage6_sigma_early_fix_summary.md", "w", encoding="utf-8") as f:
            f.write(
                _sigma_early_fix_summary_md(
                    fixed_best_mean_ber=fixed_best_mean_ber,
                    best_by_seed=sigma_early_fix_best_by_seed,
                    avg_gain_by_seed=sigma_early_fix_avg_gain_by_seed,
                    best_global=sigma_early_fix_best_global or {"sigma_early": float("nan"), "sigma_late": float("nan"), "mean_ber": float("nan")},
                    success=bool(sigma_early_fix_success),
                )
                + "\n"
            )

    if int(args.run_residual_aware_sigma_v2) and fixed_best_by_seed:
        print("\n==> Stage9 residual-aware sigma v2")
        residual_v2_rows, residual_v2_best_by_seed, residual_v2_avg_gain_by_seed, residual_v2_best_global = _evaluate_residual_aware_rows(
            model=model,
            seed_batches=seed_batches,
            data_pos=data_pos,
            snr_list=snr_list,
            seeds=seeds,
            c0_grid=c0_grid,
            cr_grid=cr_grid,
            fixed_best_by_seed=fixed_best_by_seed,
            eval_batch_size=args.eval_batch_size,
        )
        residual_v2_success = (
            residual_v2_best_global is not None
            and fixed_best_mean_ber == fixed_best_mean_ber
            and float(residual_v2_best_global["mean_ber"]) < 0.95 * fixed_best_mean_ber
        )
        _write_csv(out_dir / "stage6_residual_aware_sigma_v2_surface.csv", residual_v2_rows)
        with open(out_dir / "stage6_residual_aware_sigma_v2_best.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "best_by_seed": residual_v2_best_by_seed,
                    "avg_improvement_by_seed": residual_v2_avg_gain_by_seed,
                    "best_global": residual_v2_best_global,
                    "success": residual_v2_success,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        with open(out_dir / "stage6_residual_aware_sigma_v2_summary.md", "w", encoding="utf-8") as f:
            f.write(
                _residual_aware_sigma_summary_md(
                    fixed_best_mean_ber=fixed_best_mean_ber,
                    best_by_seed=residual_v2_best_by_seed,
                    avg_gain_by_seed=residual_v2_avg_gain_by_seed,
                    best_global=residual_v2_best_global or {"c0": float("nan"), "cr": float("nan"), "mean_ber": float("nan")},
                    success=bool(residual_v2_success),
                )
                + "\n"
            )

    compare_profiles: list[tuple[str, dict[str, Any]]] = []
    if fixed_best_by_seed:
        compare_profiles.extend(
            [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
            ]
        )
        if sigma_early_fix_best_global is not None:
            compare_profiles.append(
                (
                    "sigma_early_fix_best",
                    {
                        "alpha": [1.0] * max(args.num_outer_iters, 1),
                        "detector_sigma_inflation": [float(sigma_early_fix_best_global["sigma_early"])]
                        + [float(sigma_early_fix_best_global["sigma_late"])] * max(args.num_outer_iters - 1, 0),
                    },
                )
            )
        if residual_v2_best_global is not None:
            compare_profiles.append(
                (
                    "residual_aware_sigma_v2_best",
                    {
                        "alpha": 1.0,
                        "detector_sigma_c0": float(residual_v2_best_global["c0"]),
                        "detector_sigma_cr": float(residual_v2_best_global["cr"]),
                    },
                )
            )
        _trace_unused, calibration_dataset_rows = _collect_profile_diagnostics(
            model=model,
            seed_batches=seed_batches,
            data_pos=data_pos,
            snr_list=snr_list,
            profile_defs=compare_profiles,
            seeds=seeds,
            eval_batch_size=args.eval_batch_size,
        )
        _write_csv(out_dir / "stage6_calibration_dataset.csv", calibration_dataset_rows)
        with open(out_dir / "stage6_calibration_dataset_summary.md", "w", encoding="utf-8") as f:
            f.write(_calibration_dataset_summary_md(calibration_dataset_rows) + "\n")

    if int(args.run_vx_recalibration_v1) and fixed_best_calib_rows:
        print("\n==> Stage9 vx recalibration v1")
        assert coeff_payload is not None
        with open(out_dir / "stage6_vx_recalibration_coeffs.json", "w", encoding="utf-8") as f:
            json.dump(coeff_payload, f, indent=2, ensure_ascii=False)
        with open(out_dir / "stage6_vx_recalibration_coeffs_summary.md", "w", encoding="utf-8") as f:
            f.write(_vx_recalibration_coeffs_summary_md(coeff_payload) + "\n")

        vx_recal_profiles = [
            ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
            ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
            (
                "fixed_best_vx_recalibration_v1",
                {
                    "alpha": fixed_best_alpha,
                    "detector_sigma_inflation": fixed_best_sigma,
                    "vx_recalibration_scale": coeff_payload["coeff_list"],
                },
            ),
        ]

        vx_recal_trace_rows, vx_recal_cal_rows = _collect_profile_diagnostics(
            model=model,
            seed_batches=seed_batches,
            data_pos=data_pos,
            snr_list=snr_list,
            profile_defs=vx_recal_profiles,
            seeds=seeds,
            eval_batch_size=args.eval_batch_size,
        )
        _write_csv(out_dir / "stage6_vx_recalibration_v1_traces.csv", vx_recal_trace_rows)
        _write_csv(out_dir / "stage6_vx_recalibration_v1_calibration.csv", vx_recal_cal_rows)
        vx_recal_v1_by_seed = _final_ber_by_seed_snr_from_trace_rows(
            vx_recal_trace_rows,
            "fixed_best_vx_recalibration_v1",
            args.num_outer_iters - 1,
        )

        baseline_rows = [r for r in vx_recal_cal_rows if str(r["profile"]) == "baseline"]
        fixed_rows = [r for r in vx_recal_cal_rows if str(r["profile"]) == "fixed_best"]
        recal_rows = [r for r in vx_recal_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
        vx_recal_mean_ber = _final_mean_ber_from_trace_rows(
            vx_recal_trace_rows,
            "fixed_best_vx_recalibration_v1",
            args.num_outer_iters - 1,
        )
        with open(out_dir / "stage6_vx_recalibration_v1_summary.md", "w", encoding="utf-8") as f:
            f.write(
                _vx_recalibration_summary_md(
                    title="# Stage11 VX Recalibration v1 Summary",
                    variant_label="fixed_best+vx_recalibration_v1",
                    fixed_best_mean_ber=fixed_best_mean_ber,
                    variant_mean_ber=vx_recal_mean_ber,
                    baseline_cal=baseline_rows,
                    fixed_best_cal=fixed_rows,
                    variant_cal=recal_rows,
                )
                    + "\n"
                )

        if int(args.run_uncertainty_aware_sic) and vx_recal_v1_by_seed:
            print("\n==> Stage10 uncertainty-aware SIC")
            sic_rows, sic_best_by_seed, sic_avg_gain_by_seed, sic_best_global = _evaluate_uncertainty_aware_sic_rows(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                seeds=seeds,
                fixed_best_by_seed=fixed_best_by_seed,
                vx_recal_by_seed=vx_recal_v1_by_seed,
                coeff_list=coeff_payload["coeff_list"],
                sic_kappa_grid=sic_kappa_grid,
                fixed_best_alpha=fixed_best_alpha,
                fixed_best_sigma=fixed_best_sigma,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage6_uncertainty_aware_sic_surface.csv", sic_rows)
            with open(out_dir / "stage6_uncertainty_aware_sic_best.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "best_by_seed": sic_best_by_seed,
                        "avg_improvement_by_seed": sic_avg_gain_by_seed,
                        "best_global": sic_best_global,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            if sic_best_global is not None:
                sic_profiles = [
                    ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                    ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                    (
                        "fixed_best_vx_recalibration_v1",
                        {
                            "alpha": fixed_best_alpha,
                            "detector_sigma_inflation": fixed_best_sigma,
                            "vx_recalibration_scale": coeff_payload["coeff_list"],
                        },
                    ),
                    (
                        "fixed_best_vx_recalibration_v1_uncertainty_aware_sic",
                        {
                            "alpha": fixed_best_alpha,
                            "detector_sigma_inflation": fixed_best_sigma,
                            "vx_recalibration_scale": coeff_payload["coeff_list"],
                            "sic_uncertainty_kappa": float(sic_best_global["sic_kappa"]),
                            "sic_uncertainty_mode": "inv_linear",
                        },
                    ),
                ]
                sic_trace_rows, sic_cal_rows = _collect_profile_diagnostics(
                    model=model,
                    seed_batches=seed_batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    profile_defs=sic_profiles,
                    seeds=seeds,
                    eval_batch_size=args.eval_batch_size,
                )
                _write_csv(out_dir / "stage6_uncertainty_aware_sic_traces.csv", sic_trace_rows)
                _write_csv(out_dir / "stage6_uncertainty_aware_sic_calibration.csv", sic_cal_rows)
                fixed_rows = [r for r in sic_cal_rows if str(r["profile"]) == "fixed_best"]
                v1_rows = [r for r in sic_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
                sic_best_rows = [r for r in sic_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1_uncertainty_aware_sic"]
                with open(out_dir / "stage6_uncertainty_aware_sic_summary.md", "w", encoding="utf-8") as f:
                    f.write(
                        _uncertainty_aware_sic_summary_md(
                            fixed_best_mean_ber=fixed_best_mean_ber,
                            vx_recal_v1_mean_ber=vx_recal_mean_ber,
                            best_by_seed=sic_best_by_seed,
                            avg_gain_by_seed=sic_avg_gain_by_seed,
                            best_global=sic_best_global,
                            fixed_best_cal=fixed_rows,
                            vx_recal_v1_cal=v1_rows,
                            sic_cal=sic_best_rows,
                            vx_recal_v1_trace=sic_trace_rows,
                            sic_trace=sic_trace_rows,
                        )
                        + "\n"
                    )

        if int(args.run_vx_recalibration_v2_affine):
            print("\n==> Stage11 vx recalibration v2 affine")
            assert affine_payload is not None
            with open(out_dir / "stage6_vx_recalibration_v2_affine_coeffs.json", "w", encoding="utf-8") as f:
                json.dump(affine_payload, f, indent=2, ensure_ascii=False)
            with open(out_dir / "stage6_vx_recalibration_v2_affine_coeffs_summary.md", "w", encoding="utf-8") as f:
                f.write(_vx_recalibration_affine_coeffs_summary_md(affine_payload) + "\n")

            affine_profiles = [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_v2_affine",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_affine_a": affine_payload["a_list"],
                        "vx_recalibration_affine_b": affine_payload["b_list"],
                    },
                ),
            ]
            affine_trace_rows, affine_cal_rows = _collect_profile_diagnostics(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=affine_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage6_vx_recalibration_v2_affine_traces.csv", affine_trace_rows)
            _write_csv(out_dir / "stage6_vx_recalibration_v2_affine_calibration.csv", affine_cal_rows)
            affine_rows = [r for r in affine_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v2_affine"]
            affine_mean_ber = _final_mean_ber_from_trace_rows(
                affine_trace_rows,
                "fixed_best_vx_recalibration_v2_affine",
                args.num_outer_iters - 1,
            )
            with open(out_dir / "stage6_vx_recalibration_v2_affine_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _vx_recalibration_summary_md(
                        title="# Stage11 VX Recalibration v2 Affine Summary",
                        variant_label="fixed_best+vx_recalibration_v2_affine",
                        fixed_best_mean_ber=fixed_best_mean_ber,
                        variant_mean_ber=affine_mean_ber,
                        baseline_cal=baseline_rows,
                        fixed_best_cal=fixed_rows,
                        variant_cal=affine_rows,
                        v1_cal=recal_rows,
                        v1_mean_ber=vx_recal_mean_ber,
                    )
                    + "\n"
                )
            affine_success = _vx_variant_passes_stage11(
                fixed_best_mean_ber=fixed_best_mean_ber,
                v1_mean_ber=vx_recal_mean_ber,
                fixed_best_cal=fixed_rows,
                v1_cal=recal_rows,
                variant_mean_ber=affine_mean_ber,
                variant_cal=affine_rows,
            )

        if int(args.run_vx_recalibration_v2_clipped):
            print("\n==> Stage11 vx recalibration v2 clipped")
            assert clipped_payload is not None
            with open(out_dir / "stage6_vx_recalibration_v2_clipped_coeffs.json", "w", encoding="utf-8") as f:
                json.dump(clipped_payload, f, indent=2, ensure_ascii=False)
            with open(out_dir / "stage6_vx_recalibration_v2_clipped_coeffs_summary.md", "w", encoding="utf-8") as f:
                f.write(_vx_recalibration_clipped_coeffs_summary_md(clipped_payload) + "\n")

            clipped_profiles = [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_v2_clipped",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_clip_scale": clipped_payload["scale_list"],
                        "vx_recalibration_clip_min": clipped_payload["vmin_list"],
                        "vx_recalibration_clip_max": clipped_payload["vmax_list"],
                    },
                ),
            ]
            clipped_trace_rows, clipped_cal_rows = _collect_profile_diagnostics(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=clipped_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage6_vx_recalibration_v2_clipped_traces.csv", clipped_trace_rows)
            _write_csv(out_dir / "stage6_vx_recalibration_v2_clipped_calibration.csv", clipped_cal_rows)
            clipped_rows = [r for r in clipped_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v2_clipped"]
            clipped_mean_ber = _final_mean_ber_from_trace_rows(
                clipped_trace_rows,
                "fixed_best_vx_recalibration_v2_clipped",
                args.num_outer_iters - 1,
            )
            with open(out_dir / "stage6_vx_recalibration_v2_clipped_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _vx_recalibration_summary_md(
                        title="# Stage11 VX Recalibration v2 Clipped Summary",
                        variant_label="fixed_best+vx_recalibration_v2_clipped",
                        fixed_best_mean_ber=fixed_best_mean_ber,
                        variant_mean_ber=clipped_mean_ber,
                        baseline_cal=baseline_rows,
                        fixed_best_cal=fixed_rows,
                        variant_cal=clipped_rows,
                        v1_cal=recal_rows,
                        v1_mean_ber=vx_recal_mean_ber,
                    )
                    + "\n"
                )
            clipped_success = _vx_variant_passes_stage11(
                fixed_best_mean_ber=fixed_best_mean_ber,
                v1_mean_ber=vx_recal_mean_ber,
                fixed_best_cal=fixed_rows,
                v1_cal=recal_rows,
                variant_mean_ber=clipped_mean_ber,
                variant_cal=clipped_rows,
            )

        if int(args.run_vx_recalibration_v3_hybrid) and coeff_payload is not None and affine_payload is not None:
            print("\n==> Stage12 vx recalibration v3 hybrid")
            num_iters = max(int(args.num_outer_iters), 1)
            hybrid_scale = [1.0] * num_iters
            hybrid_affine_a = [1.0] * num_iters
            hybrid_affine_b = [0.0] * num_iters
            coeff_list = list(coeff_payload["coeff_list"])
            a_list = list(affine_payload["a_list"])
            b_list = list(affine_payload["b_list"])
            if num_iters > 0 and a_list:
                hybrid_affine_a[0] = float(a_list[0])
            if num_iters > 0 and b_list:
                hybrid_affine_b[0] = float(b_list[0])
            for t in range(1, num_iters):
                src_idx = min(t, len(coeff_list) - 1)
                hybrid_scale[t] = float(coeff_list[src_idx])

            hybrid_profiles = [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_v3_hybrid",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": hybrid_scale,
                        "vx_recalibration_affine_a": hybrid_affine_a,
                        "vx_recalibration_affine_b": hybrid_affine_b,
                    },
                ),
            ]
            hybrid_v3_trace_rows, hybrid_v3_cal_rows = _collect_profile_diagnostics(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=hybrid_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage12_vx_recalibration_v3_hybrid_traces.csv", hybrid_v3_trace_rows)
            _write_csv(out_dir / "stage12_vx_recalibration_v3_hybrid_calibration.csv", hybrid_v3_cal_rows)
            hybrid_v3_rows = [r for r in hybrid_v3_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v3_hybrid"]
            hybrid_v3_mean_ber = _final_mean_ber_from_trace_rows(
                hybrid_v3_trace_rows,
                "fixed_best_vx_recalibration_v3_hybrid",
                args.num_outer_iters - 1,
            )
            hybrid_v1_mean_ber = _final_mean_ber_from_trace_rows(
                hybrid_v3_trace_rows,
                "fixed_best_vx_recalibration_v1",
                args.num_outer_iters - 1,
            )
            hybrid_fixed_rows = [r for r in hybrid_v3_cal_rows if str(r["profile"]) == "fixed_best"]
            hybrid_v1_rows = [r for r in hybrid_v3_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
            with open(out_dir / "stage12_vx_recalibration_v3_hybrid_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _stage12_recalibration_summary_md(
                        title="# Stage12 VX Recalibration v3 Hybrid Summary",
                        variant_label="fixed_best+vx_recalibration_v3_hybrid",
                        fixed_best_mean_ber=fixed_best_mean_ber,
                        v1_mean_ber=hybrid_v1_mean_ber,
                        variant_mean_ber=hybrid_v3_mean_ber,
                        fixed_best_cal=hybrid_fixed_rows,
                        v1_cal=hybrid_v1_rows,
                        variant_cal=hybrid_v3_rows,
                    )
                    + "\n"
                )

        frame_train_rows: list[dict[str, Any]] = []
        frame_val_rows: list[dict[str, Any]] = []
        if (int(args.run_frame_calibration_dataset_export) and not int(args.run_vx_recalibration_learned_anchor)) or int(args.run_vx_recalibration_learned):
            print("\n==> Stage12 frame-level calibration dataset export")
            frame_rows_all = _collect_frame_calibration_dataset(
                model=model,
                seed_batches=calibration_seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                seeds=list(dict.fromkeys(calibration_train_seeds + calibration_val_seeds)),
                fixed_best_alpha=fixed_best_alpha,
                fixed_best_sigma=fixed_best_sigma,
                eval_batch_size=args.eval_batch_size,
            )
            train_seed_set = {int(x) for x in calibration_train_seeds}
            val_seed_set = {int(x) for x in calibration_val_seeds}
            frame_train_rows = [r for r in frame_rows_all if int(r["seed"]) in train_seed_set]
            frame_val_rows = [r for r in frame_rows_all if int(r["seed"]) in val_seed_set]
            _write_csv(out_dir / "stage12_frame_calibration_dataset_train.csv", frame_train_rows)
            _write_csv(out_dir / "stage12_frame_calibration_dataset_val.csv", frame_val_rows)
            with open(out_dir / "stage12_frame_calibration_dataset_summary.md", "w", encoding="utf-8") as f:
                f.write(_frame_calibration_dataset_summary_md(frame_train_rows, frame_val_rows) + "\n")

        if int(args.run_vx_recalibration_learned):
            print("\n==> Stage12 learned output recalibration")
            if not frame_train_rows:
                raise RuntimeError("Learned recalibration requested, but frame-level train dataset is empty.")
            if coeff_payload is None:
                raise RuntimeError("Learned recalibration requested, but vx_recalibration_v1 coeffs are unavailable.")
            learned_payload, learned_train_info = _train_learned_output_recalibration(
                frame_train_rows,
                frame_val_rows,
                num_outer_iters=args.num_outer_iters,
                device=device,
                epochs=args.learned_recalibration_epochs,
                patience=args.learned_recalibration_patience,
                lr=args.learned_recalibration_lr,
                id_reg=args.learned_recalibration_id_reg,
            )
            torch.save(
                {
                    "payload": learned_payload,
                    "train_info": learned_train_info,
                    "train_seeds": calibration_train_seeds,
                    "val_seeds": calibration_val_seeds,
                },
                out_dir / "stage12_vx_recalibration_learned_model.pt",
            )
            learned_profiles = [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_learned",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_learned_payload": learned_payload,
                    },
                ),
            ]
            learned_trace_rows, learned_cal_rows = _collect_profile_diagnostics(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=learned_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage12_vx_recalibration_learned_traces.csv", learned_trace_rows)
            _write_csv(out_dir / "stage12_vx_recalibration_learned_calibration.csv", learned_cal_rows)
            learned_rows = [r for r in learned_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_learned"]
            learned_mean_ber = _final_mean_ber_from_trace_rows(
                learned_trace_rows,
                "fixed_best_vx_recalibration_learned",
                args.num_outer_iters - 1,
            )
            learned_v1_mean_ber = _final_mean_ber_from_trace_rows(
                learned_trace_rows,
                "fixed_best_vx_recalibration_v1",
                args.num_outer_iters - 1,
            )
            learned_fixed_rows = [r for r in learned_cal_rows if str(r["profile"]) == "fixed_best"]
            learned_v1_rows = [r for r in learned_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
            with open(out_dir / "stage12_vx_recalibration_learned_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _stage12_recalibration_summary_md(
                        title="# Stage12 Learned Output Recalibration Summary",
                        variant_label="fixed_best+learned_output_recalibration",
                        fixed_best_mean_ber=fixed_best_mean_ber,
                        v1_mean_ber=learned_v1_mean_ber,
                        variant_mean_ber=learned_mean_ber,
                        fixed_best_cal=learned_fixed_rows,
                        v1_cal=learned_v1_rows,
                        variant_cal=learned_rows,
                        train_info=learned_train_info,
                    )
                    + "\n"
                )

        if int(args.run_stage13_metric_audit):
            print("\n==> Stage13 metric audit")
            ref_dir = pathlib.Path(args.stage12_reference_dir) if str(args.stage12_reference_dir).strip() else (pathlib.Path(__file__).resolve().parent / "outputs_stage12_vxrecal_hybrid_learned")
            if not ref_dir.exists():
                raise RuntimeError(f"Stage13 metric audit requested, but reference dir does not exist: {ref_dir}")
            if coeff_payload is None or not fixed_best_calib_rows:
                raise RuntimeError("Stage13 metric audit requires fixed_best calibration rows and vx recalibration v1 coeffs.")

            audit_v1_cal_rows = _read_csv_rows(ref_dir / "stage6_vx_recalibration_v1_calibration.csv")
            audit_v1_trace_rows = _read_csv_rows(ref_dir / "stage6_vx_recalibration_v1_traces.csv")
            audit_hybrid_cal_rows = _read_csv_rows(ref_dir / "stage12_vx_recalibration_v3_hybrid_calibration.csv")
            audit_hybrid_trace_rows = _read_csv_rows(ref_dir / "stage12_vx_recalibration_v3_hybrid_traces.csv")
            audit_learned_cal_rows = _read_csv_rows(ref_dir / "stage12_vx_recalibration_learned_calibration.csv")
            audit_learned_trace_rows = _read_csv_rows(ref_dir / "stage12_vx_recalibration_learned_traces.csv")
            if not audit_v1_cal_rows or not audit_v1_trace_rows or not audit_hybrid_cal_rows or not audit_hybrid_trace_rows or not audit_learned_cal_rows or not audit_learned_trace_rows:
                raise RuntimeError(f"Stage13 metric audit requested, but Stage12 reference artifacts are incomplete under: {ref_dir}")

            final_iter = int(args.num_outer_iters) - 1
            ber_map = {
                "fixed_best": _final_mean_ber_from_trace_rows(audit_v1_trace_rows, "fixed_best", final_iter),
                "v1": _final_mean_ber_from_trace_rows(audit_v1_trace_rows, "fixed_best_vx_recalibration_v1", final_iter),
                "hybrid_v3": _final_mean_ber_from_trace_rows(audit_hybrid_trace_rows, "fixed_best_vx_recalibration_v3_hybrid", final_iter),
                "learned": _final_mean_ber_from_trace_rows(audit_learned_trace_rows, "fixed_best_vx_recalibration_learned", final_iter),
            }
            profile_rows_map = {
                "fixed_best": [r for r in audit_v1_cal_rows if str(r["profile"]) == "fixed_best"],
                "v1": [r for r in audit_v1_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"],
                "hybrid_v3": [r for r in audit_hybrid_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v3_hybrid"],
                "learned": [r for r in audit_learned_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_learned"],
            }
            audit_affine_payload = affine_payload or _fit_vx_recalibration_affine_coeffs(fixed_best_calib_rows)
            num_iters = max(int(args.num_outer_iters), 1)
            hybrid_scale = [1.0] * num_iters
            hybrid_affine_a = [1.0] * num_iters
            hybrid_affine_b = [0.0] * num_iters
            coeff_list = list(coeff_payload["coeff_list"])
            a_list = list(audit_affine_payload["a_list"])
            b_list = list(audit_affine_payload["b_list"])
            if num_iters > 0 and a_list:
                hybrid_affine_a[0] = float(a_list[0])
            if num_iters > 0 and b_list:
                hybrid_affine_b[0] = float(b_list[0])
            for t in range(1, num_iters):
                src_idx = min(t, len(coeff_list) - 1)
                hybrid_scale[t] = float(coeff_list[src_idx])
            stage12_learned_payload = _load_saved_payload(ref_dir / "stage12_vx_recalibration_learned_model.pt")
            audit_profiles = [
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_v3_hybrid",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": hybrid_scale,
                        "vx_recalibration_affine_a": hybrid_affine_a,
                        "vx_recalibration_affine_b": hybrid_affine_b,
                    },
                ),
                (
                    "fixed_best_vx_recalibration_learned",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_learned_payload": stage12_learned_payload,
                    },
                ),
            ]
            audit_frame_rows = _collect_profile_frame_calibration(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=audit_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            audit_frame_rows_map = {
                "fixed_best": [r for r in audit_frame_rows if str(r["profile"]) == "fixed_best"],
                "v1": [r for r in audit_frame_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"],
                "hybrid_v3": [r for r in audit_frame_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v3_hybrid"],
                "learned": [r for r in audit_frame_rows if str(r["profile"]) == "fixed_best_vx_recalibration_learned"],
            }
            missing_frame_profiles = [name for name, rows in audit_frame_rows_map.items() if not rows]
            if missing_frame_profiles:
                raise RuntimeError(
                    "Stage13 metric audit could not collect frame-level rows for: "
                    + ", ".join(missing_frame_profiles)
                )
            old_metric_map = {
                name: float(_task_aware_metrics(rows)["task_balanced_score"])
                for name, rows in profile_rows_map.items()
            }
            new_detail_map = {
                name: _task_risk_metrics(rows, frame_rows=audit_frame_rows_map.get(name))
                for name, rows in profile_rows_map.items()
            }
            bad_metric_profiles = [
                name
                for name, metrics in new_detail_map.items()
                if metrics["frame_worst_late_optimism"] != metrics["frame_worst_late_optimism"]
            ]
            if bad_metric_profiles:
                raise RuntimeError(
                    "Stage13 metric audit produced NaN frame_worst_late_optimism for: "
                    + ", ".join(bad_metric_profiles)
                )
            new_metric_map = {
                name: float(metrics["task_risk_score"])
                for name, metrics in new_detail_map.items()
            }
            with open(out_dir / "stage13_metric_audit_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _stage13_metric_audit_summary_md(
                        ber_map=ber_map,
                        old_metric_map=old_metric_map,
                        new_metric_map=new_metric_map,
                        new_detail_map=new_detail_map,
                    )
                    + "\n"
                )

        stage13_frame_train_rows: list[dict[str, Any]] = []
        stage13_frame_val_rows: list[dict[str, Any]] = []
        if int(args.run_frame_calibration_dataset_export) or int(args.run_vx_recalibration_learned_anchor):
            print("\n==> Stage13 frame-level calibration dataset export")
            stage13_frame_rows_all = _collect_frame_calibration_dataset(
                model=model,
                seed_batches=calibration_seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                seeds=list(dict.fromkeys(calibration_train_seeds + calibration_val_seeds)),
                fixed_best_alpha=fixed_best_alpha,
                fixed_best_sigma=fixed_best_sigma,
                eval_batch_size=args.eval_batch_size,
            )
            train_seed_set = {int(x) for x in calibration_train_seeds}
            val_seed_set = {int(x) for x in calibration_val_seeds}
            stage13_frame_train_rows = [r for r in stage13_frame_rows_all if int(r["seed"]) in train_seed_set]
            stage13_frame_val_rows = [r for r in stage13_frame_rows_all if int(r["seed"]) in val_seed_set]
            _write_csv(out_dir / "stage13_frame_calibration_dataset_train.csv", stage13_frame_train_rows)
            _write_csv(out_dir / "stage13_frame_calibration_dataset_val.csv", stage13_frame_val_rows)
            with open(out_dir / "stage13_frame_calibration_dataset_summary.md", "w", encoding="utf-8") as f:
                f.write(_frame_calibration_dataset_summary_md(stage13_frame_train_rows, stage13_frame_val_rows).replace("Stage12", "Stage13") + "\n")

        if int(args.run_vx_recalibration_learned_anchor):
            print("\n==> Stage13 anchored learned output recalibration")
            if not stage13_frame_train_rows:
                raise RuntimeError("Anchored learned recalibration requested, but frame-level train dataset is empty.")
            if coeff_payload is None:
                raise RuntimeError("Anchored learned recalibration requested, but vx_recalibration_v1 coeffs are unavailable.")
            base_scale_list = [float(x) for x in coeff_payload["coeff_list"]]
            num_iters = max(int(args.num_outer_iters), 1)
            residual_log_bound_list = []
            for t in range(num_iters):
                if t == 0:
                    residual_log_bound_list.append(float(np.log(2.0)))
                elif t >= 4:
                    residual_log_bound_list.append(float(np.log(1.10)))
                else:
                    residual_log_bound_list.append(float(np.log(1.25)))
            learned_anchor_payload, learned_anchor_train_info = _train_anchored_output_recalibration(
                stage13_frame_train_rows,
                stage13_frame_val_rows,
                num_outer_iters=args.num_outer_iters,
                base_scale_list=base_scale_list,
                residual_log_bound_list=residual_log_bound_list,
                device=device,
                epochs=args.learned_recalibration_epochs,
                patience=args.learned_recalibration_patience,
                lr=args.learned_recalibration_lr,
                anchor_reg=1e-2,
                late_optimism_barrier=3.0,
            )
            torch.save(
                {
                    "payload": learned_anchor_payload,
                    "train_info": learned_anchor_train_info,
                    "train_seeds": calibration_train_seeds,
                    "val_seeds": calibration_val_seeds,
                },
                out_dir / "stage13_vx_recalibration_learned_anchor_model.pt",
            )
            learned_anchor_profiles = [
                ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                (
                    "fixed_best_vx_recalibration_v1",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_scale": coeff_payload["coeff_list"],
                    },
                ),
                (
                    "fixed_best_vx_recalibration_learned_anchor",
                    {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_learned_payload": learned_anchor_payload,
                    },
                ),
            ]
            anchor_trace_rows, anchor_cal_rows = _collect_profile_diagnostics(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=learned_anchor_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            anchor_frame_rows = _collect_profile_frame_calibration(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                profile_defs=learned_anchor_profiles,
                seeds=seeds,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage13_vx_recalibration_learned_anchor_traces.csv", anchor_trace_rows)
            _write_csv(out_dir / "stage13_vx_recalibration_learned_anchor_calibration.csv", anchor_cal_rows)
            anchor_rows = [r for r in anchor_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_learned_anchor"]
            anchor_mean_ber = _final_mean_ber_from_trace_rows(
                anchor_trace_rows,
                "fixed_best_vx_recalibration_learned_anchor",
                args.num_outer_iters - 1,
            )
            anchor_v1_mean_ber = _final_mean_ber_from_trace_rows(
                anchor_trace_rows,
                "fixed_best_vx_recalibration_v1",
                args.num_outer_iters - 1,
            )
            anchor_fixed_rows = [r for r in anchor_cal_rows if str(r["profile"]) == "fixed_best"]
            anchor_v1_rows = [r for r in anchor_cal_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
            anchor_fixed_frame_rows = [r for r in anchor_frame_rows if str(r["profile"]) == "fixed_best"]
            anchor_v1_frame_rows = [r for r in anchor_frame_rows if str(r["profile"]) == "fixed_best_vx_recalibration_v1"]
            anchor_variant_frame_rows = [r for r in anchor_frame_rows if str(r["profile"]) == "fixed_best_vx_recalibration_learned_anchor"]
            missing_anchor_frame_groups = [
                name
                for name, rows in {
                    "fixed_best": anchor_fixed_frame_rows,
                    "v1": anchor_v1_frame_rows,
                    "learned_anchor": anchor_variant_frame_rows,
                }.items()
                if not rows
            ]
            if missing_anchor_frame_groups:
                raise RuntimeError(
                    "Stage13 anchored summary could not collect frame-level rows for: "
                    + ", ".join(missing_anchor_frame_groups)
                )
            with open(out_dir / "stage13_vx_recalibration_learned_anchor_summary.md", "w", encoding="utf-8") as f:
                f.write(
                    _stage13_recalibration_summary_md(
                        title="# Stage13 Anchored Learned Output Recalibration Summary",
                        variant_label="fixed_best+learned_output_recalibration_v2_anchor",
                        fixed_best_mean_ber=fixed_best_mean_ber,
                        v1_mean_ber=anchor_v1_mean_ber,
                        variant_mean_ber=anchor_mean_ber,
                        fixed_best_cal=anchor_fixed_rows,
                        v1_cal=anchor_v1_rows,
                        variant_cal=anchor_rows,
                        fixed_best_frame_rows=anchor_fixed_frame_rows,
                        v1_frame_rows=anchor_v1_frame_rows,
                        variant_frame_rows=anchor_variant_frame_rows,
                        train_info=learned_anchor_train_info,
                    )
                    + "\n"
                )

        if int(args.run_skip_freeze_probe) and vx_recal_v1_by_seed:
            print("\n==> Stage11 uncertainty skip/freeze probe")
            source_profile_name = "fixed_best_vx_recalibration_v1"
            source_overrides: dict[str, Any] = {
                "alpha": fixed_best_alpha,
                "detector_sigma_inflation": fixed_best_sigma,
                "vx_recalibration_scale": coeff_payload["coeff_list"],
            }
            source_by_seed = vx_recal_v1_by_seed
            source_mean_ber = vx_recal_mean_ber
            source_rows = recal_rows
            if affine_success and affine_payload is not None:
                source_profile_name = "fixed_best_vx_recalibration_v2_affine"
                source_overrides = {
                    "alpha": fixed_best_alpha,
                    "detector_sigma_inflation": fixed_best_sigma,
                    "vx_recalibration_affine_a": affine_payload["a_list"],
                    "vx_recalibration_affine_b": affine_payload["b_list"],
                }
                source_by_seed = _final_ber_by_seed_snr_from_trace_rows(
                    affine_trace_rows,
                    source_profile_name,
                    args.num_outer_iters - 1,
                )
                source_mean_ber = affine_mean_ber
                source_rows = affine_rows
            if clipped_success and clipped_payload is not None:
                clipped_by_seed = _final_ber_by_seed_snr_from_trace_rows(
                    clipped_trace_rows,
                    "fixed_best_vx_recalibration_v2_clipped",
                    args.num_outer_iters - 1,
                )
                if (
                    not affine_success
                    or clipped_mean_ber < source_mean_ber - 1e-12
                    or (
                        clipped_mean_ber <= source_mean_ber + 1e-12
                        and abs(_iter_mean_metric(clipped_rows, "rho", {0, 1, 2, 3, 4}) - 1.0)
                        < abs(_iter_mean_metric(source_rows, "rho", {0, 1, 2, 3, 4}) - 1.0)
                    )
                ):
                    source_profile_name = "fixed_best_vx_recalibration_v2_clipped"
                    source_overrides = {
                        "alpha": fixed_best_alpha,
                        "detector_sigma_inflation": fixed_best_sigma,
                        "vx_recalibration_clip_scale": clipped_payload["scale_list"],
                        "vx_recalibration_clip_min": clipped_payload["vmin_list"],
                        "vx_recalibration_clip_max": clipped_payload["vmax_list"],
                    }
                    source_by_seed = clipped_by_seed
                    source_mean_ber = clipped_mean_ber
                    source_rows = clipped_rows

            skip_rows, skip_best_by_seed, skip_avg_gain_by_seed, skip_best_global = _evaluate_uncertainty_skip_freeze_rows(
                model=model,
                seed_batches=seed_batches,
                data_pos=data_pos,
                snr_list=snr_list,
                seeds=seeds,
                fixed_best_by_seed=fixed_best_by_seed,
                source_by_seed=source_by_seed,
                source_overrides=source_overrides,
                skip_quantile_grid=skip_freeze_quantile_grid,
                eval_batch_size=args.eval_batch_size,
            )
            _write_csv(out_dir / "stage6_uncertainty_skip_freeze_surface.csv", skip_rows)
            with open(out_dir / "stage6_uncertainty_skip_freeze_best.json", "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "source_profile": source_profile_name,
                        "best_by_seed": skip_best_by_seed,
                        "avg_improvement_by_seed": skip_avg_gain_by_seed,
                        "best_global": skip_best_global,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            if skip_best_global is not None:
                skip_profiles = [
                    ("baseline", {"alpha": 0.70, "detector_sigma_inflation": 1.0}),
                    ("fixed_best", {"alpha": fixed_best_alpha, "detector_sigma_inflation": fixed_best_sigma}),
                    (source_profile_name, source_overrides),
                    (
                        f"{source_profile_name}_uncertainty_skip_freeze",
                        {
                            **source_overrides,
                            "sic_skip_quantile": float(skip_best_global["skip_quantile"]),
                            "sic_skip_mode": "hard_quantile",
                        },
                    ),
                ]
                skip_trace_rows, skip_cal_rows = _collect_profile_diagnostics(
                    model=model,
                    seed_batches=seed_batches,
                    data_pos=data_pos,
                    snr_list=snr_list,
                    profile_defs=skip_profiles,
                    seeds=seeds,
                    eval_batch_size=args.eval_batch_size,
                )
                _write_csv(out_dir / "stage6_uncertainty_skip_freeze_traces.csv", skip_trace_rows)
                _write_csv(out_dir / "stage6_uncertainty_skip_freeze_calibration.csv", skip_cal_rows)
                skip_best_rows = [
                    r for r in skip_cal_rows if str(r["profile"]) == f"{source_profile_name}_uncertainty_skip_freeze"
                ]
                source_cal_rows = [r for r in skip_cal_rows if str(r["profile"]) == source_profile_name]
                with open(out_dir / "stage6_uncertainty_skip_freeze_summary.md", "w", encoding="utf-8") as f:
                    f.write(
                        _uncertainty_skip_freeze_summary_md(
                            source_label=source_profile_name,
                            fixed_best_mean_ber=fixed_best_mean_ber,
                            source_mean_ber=source_mean_ber,
                            best_by_seed=skip_best_by_seed,
                            avg_gain_by_seed=skip_avg_gain_by_seed,
                            best_global=skip_best_global,
                            fixed_best_cal=fixed_rows,
                            source_cal=source_cal_rows,
                            skip_cal=skip_best_rows,
                            source_trace=skip_trace_rows,
                            skip_trace=skip_trace_rows,
                        )
                        + "\n"
                    )

    print("\n==> Saved artifacts")
    artifact_names = [
        "stage6_heuristic_profiles.csv",
        "stage6_heuristic_profiles_summary.md",
        "stage6_alpha_sigma_surface.csv",
        "stage6_alpha_sigma_best_by_snr.json",
        "stage6_alpha_sigma_summary.md",
        "stage6_alpha_sigma_surface_expanded.csv",
        "stage6_alpha_sigma_best_by_snr_expanded.json",
        "stage6_alpha_sigma_summary_expanded.md",
        "stage6_alpha_sigma_seed_compare.json",
        "stage6_alpha_sigma_surface_expanded_v2.csv",
        "stage6_alpha_sigma_best_by_snr_expanded_v2.json",
        "stage6_alpha_sigma_summary_expanded_v2.md",
        "stage6_alpha_sigma_seed_compare_v2.json",
        "stage6_alpha_sigma_surface_expanded_v3.csv",
        "stage6_alpha_sigma_best_by_snr_expanded_v3.json",
        "stage6_alpha_sigma_summary_expanded_v3.md",
        "stage6_alpha_sigma_seed_compare_v3.json",
        "stage6_sigma_only_plateau.csv",
        "stage6_sigma_only_best_by_snr.json",
        "stage6_sigma_only_summary.md",
        "stage6_sigma_schedule_v1_surface.csv",
        "stage6_sigma_schedule_v1_best.json",
        "stage6_sigma_schedule_v1_summary.md",
        "stage6_outerloop_traces.csv",
        "stage6_outerloop_traces_summary.md",
        "stage6_alpha_sigma_iterlayer_surface.csv",
        "stage6_alpha_sigma_iterlayer_best.json",
        "stage6_alpha_sigma_iterlayer_summary.md",
        "stage6_detector_calibration.csv",
        "stage6_detector_calibration_summary.md",
        "stage6_detector_calibration_curves.csv",
        "stage6_detector_calibration_curves_summary.md",
        "stage6_detector_sigma_residual.csv",
        "stage6_detector_sigma_residual_summary.md",
        "stage6_detector_residual_proxies.csv",
        "stage6_detector_residual_proxies_summary.md",
        "stage6_fixed_best_summary.md",
        "stage6_fixed_best_traces.csv",
        "stage6_fixed_best_calibration.csv",
        "stage6_calibration_dataset.csv",
        "stage6_calibration_dataset_summary.md",
        "stage6_sigma_early_fix_surface.csv",
        "stage6_sigma_early_fix_best.json",
        "stage6_sigma_early_fix_summary.md",
        "stage6_residual_aware_sigma_v2_surface.csv",
        "stage6_residual_aware_sigma_v2_best.json",
        "stage6_residual_aware_sigma_v2_summary.md",
        "stage6_vx_recalibration_coeffs.json",
        "stage6_vx_recalibration_coeffs_summary.md",
        "stage6_vx_recalibration_v1_traces.csv",
        "stage6_vx_recalibration_v1_calibration.csv",
        "stage6_vx_recalibration_v1_summary.md",
        "stage6_vx_recalibration_v2_affine_coeffs.json",
        "stage6_vx_recalibration_v2_affine_coeffs_summary.md",
        "stage6_vx_recalibration_v2_affine_traces.csv",
        "stage6_vx_recalibration_v2_affine_calibration.csv",
        "stage6_vx_recalibration_v2_affine_summary.md",
        "stage6_vx_recalibration_v2_clipped_coeffs.json",
        "stage6_vx_recalibration_v2_clipped_coeffs_summary.md",
        "stage6_vx_recalibration_v2_clipped_traces.csv",
        "stage6_vx_recalibration_v2_clipped_calibration.csv",
        "stage6_vx_recalibration_v2_clipped_summary.md",
        "stage12_vx_recalibration_v3_hybrid_traces.csv",
        "stage12_vx_recalibration_v3_hybrid_calibration.csv",
        "stage12_vx_recalibration_v3_hybrid_summary.md",
        "stage12_frame_calibration_dataset_train.csv",
        "stage12_frame_calibration_dataset_val.csv",
        "stage12_frame_calibration_dataset_summary.md",
        "stage12_vx_recalibration_learned_model.pt",
        "stage12_vx_recalibration_learned_traces.csv",
        "stage12_vx_recalibration_learned_calibration.csv",
        "stage12_vx_recalibration_learned_summary.md",
        "stage13_metric_audit_summary.md",
        "stage13_frame_calibration_dataset_train.csv",
        "stage13_frame_calibration_dataset_val.csv",
        "stage13_frame_calibration_dataset_summary.md",
        "stage13_vx_recalibration_learned_anchor_model.pt",
        "stage13_vx_recalibration_learned_anchor_traces.csv",
        "stage13_vx_recalibration_learned_anchor_calibration.csv",
        "stage13_vx_recalibration_learned_anchor_summary.md",
        "stage6_uncertainty_aware_sic_surface.csv",
        "stage6_uncertainty_aware_sic_best.json",
        "stage6_uncertainty_aware_sic_traces.csv",
        "stage6_uncertainty_aware_sic_calibration.csv",
        "stage6_uncertainty_aware_sic_summary.md",
        "stage6_uncertainty_skip_freeze_surface.csv",
        "stage6_uncertainty_skip_freeze_best.json",
        "stage6_uncertainty_skip_freeze_traces.csv",
        "stage6_uncertainty_skip_freeze_calibration.csv",
        "stage6_uncertainty_skip_freeze_summary.md",
    ]
    for name in artifact_names:
        path = out_dir / name
        if path.exists():
            print(f"  {path}")


if __name__ == "__main__":
    main()
