"""
diagnose_joint_heuristics.py

Stage-8 diagnostic driver:
  - runs shared-batch oracle sweeps on Stage6 fixed and TradParam fixed
  - measures residual utilization on already-trained full models
  - exports csv/json/md artifacts to rank which heuristic is actually worth learning
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.afdm_joint_param import VALID_PARAM_SETS
from afdm_joint_param_unrolled.afdm_traditional_param import VALID_TRAD_PARAM_SETS
from afdm_joint_param_unrolled.verify_joint_param import _ber_from_output, _load_param_model
from afdm_joint_param_unrolled.verify_oamp import _make_system, _sync_l_max_cap
from afdm_joint_param_unrolled.verify_traditional_param import _load_traditional_model


POSITIVE_SCALE_GRID = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 4.0]
DAMP_GRID = [0.10, 0.30, 0.50, 0.70, 0.85, 0.95]
K_LEAK_GRID = [0, 1, 2, 3, 4]
TAU_H_FACTOR_GRID = [0.0, 0.0025, 0.005, 0.01, 0.02]
TAU_H_SIGMA_FACTOR_GRID = [0.0, 0.05, 0.1, 0.2]
SEED_MULT_GRID = [0.5, 1.0, 2.0]
EXPAND_MULT_GRID = [0.25, 0.5, 1.0, 2.0]


@dataclass
class SharedBatch:
    x_feat: torch.Tensor
    y_recv: torch.Tensor
    x_pil: torch.Tensor
    sigma: torch.Tensor
    x_true: np.ndarray
    speeds: np.ndarray
    channel_types: np.ndarray


def _stage6_artifact_stem(param_set: str) -> str:
    return f"param_joint_{param_set}"


def _traditional_artifact_stem(param_set: str) -> str:
    return f"traditional_param_{param_set}"


def _load_json_safe(value: Any) -> Any:
    if torch.is_tensor(value):
        if value.numel() == 1:
            return float(value.detach().cpu().item())
        return value.detach().cpu().tolist()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _mean_std(arr: np.ndarray) -> tuple[float, float]:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.size == 0:
        return float("nan"), float("nan")
    return float(arr.mean()), float(arr.std(ddof=0))


def _rel_improvement(anchor_ber: float, cand_ber: float) -> float:
    denom = max(anchor_ber, 1e-12)
    return float((anchor_ber - cand_ber) / denom)


def _format_override_label(override: dict[str, Any]) -> str:
    parts = []
    for key, value in override.items():
        if isinstance(value, float):
            parts.append(f"{key}={value:g}")
        else:
            parts.append(f"{key}={value}")
    return ",".join(parts)


def _candidate_families_stage6() -> dict[str, dict[str, Any]]:
    return {
        "lambda_global": {
            "kind": "scale",
            "candidates": [
                {"label": f"{scale:g}x", "value": float(scale), "overrides": {"lambda_scale": float(scale)}}
                for scale in POSITIVE_SCALE_GRID
            ],
        },
        "alpha": {
            "kind": "damping",
            "candidates": [
                {"label": f"{value:.2f}", "value": float(value), "overrides": {"alpha": float(value)}}
                for value in DAMP_GRID
            ],
        },
        "beta": {
            "kind": "damping",
            "candidates": [
                {"label": f"{value:.2f}", "value": float(value), "overrides": {"beta": float(value)}}
                for value in DAMP_GRID
            ],
        },
        "sigma_inflation": {
            "kind": "scale",
            "candidates": [
                {
                    "label": f"{scale:g}x",
                    "value": float(scale),
                    "overrides": {"detector_sigma_inflation": float(scale)},
                }
                for scale in POSITIVE_SCALE_GRID
            ],
        },
        "k_leak": {
            "kind": "discrete",
            "candidates": [
                {"label": str(v), "value": int(v), "overrides": {"k_leak": int(v)}}
                for v in K_LEAK_GRID
            ],
        },
        "lambda_group": {
            "kind": "pair",
            "candidates": [
                {
                    "label": f"seed={seed_mult:g},expand={expand_mult:g}",
                    "value": [float(seed_mult), float(expand_mult)],
                    "overrides": {
                        "seed_mult": float(seed_mult),
                        "expand_mult": float(expand_mult),
                    },
                }
                for seed_mult in SEED_MULT_GRID
                for expand_mult in EXPAND_MULT_GRID
            ],
        },
    }


def _candidate_families_traditional() -> dict[str, dict[str, Any]]:
    return {
        "lambda_global": {
            "kind": "scale",
            "candidates": [
                {
                    "label": f"{scale:g}x",
                    "value": float(scale),
                    "overrides": {"lambda_factor_scale": float(scale)},
                }
                for scale in POSITIVE_SCALE_GRID
            ],
        },
        "gamma_h": {
            "kind": "damping",
            "candidates": [
                {"label": f"{value:.2f}", "value": float(value), "overrides": {"gamma_h": float(value)}}
                for value in DAMP_GRID
            ],
        },
        "gamma_x": {
            "kind": "damping",
            "candidates": [
                {"label": f"{value:.2f}", "value": float(value), "overrides": {"gamma_x": float(value)}}
                for value in DAMP_GRID
            ],
        },
        "pic_damp": {
            "kind": "damping",
            "candidates": [
                {"label": f"{value:.2f}", "value": float(value), "overrides": {"pic_damp": float(value)}}
                for value in DAMP_GRID
            ],
        },
        "sigma_inflation": {
            "kind": "scale",
            "candidates": [
                {
                    "label": f"{scale:g}x",
                    "value": float(scale),
                    "overrides": {"detector_sigma_inflation": float(scale)},
                }
                for scale in POSITIVE_SCALE_GRID
            ],
        },
        "k_leak": {
            "kind": "discrete",
            "candidates": [
                {"label": str(v), "value": int(v), "overrides": {"k_leak": int(v)}}
                for v in K_LEAK_GRID
            ],
        },
        "tau_h_factor": {
            "kind": "discrete",
            "candidates": [
                {"label": f"{value:g}", "value": float(value), "overrides": {"tau_h_factor": float(value)}}
                for value in TAU_H_FACTOR_GRID
            ],
        },
        "tau_h_sigma_factor": {
            "kind": "discrete",
            "candidates": [
                {"label": f"{value:g}", "value": float(value), "overrides": {"tau_h_sigma_factor": float(value)}}
                for value in TAU_H_SIGMA_FACTOR_GRID
            ],
        },
        "lambda_group": {
            "kind": "pair",
            "candidates": [
                {
                    "label": f"seed={seed_mult:g},expand={expand_mult:g}",
                    "value": [float(seed_mult), float(expand_mult)],
                    "overrides": {
                        "seed_mult": float(seed_mult),
                        "expand_mult": float(expand_mult),
                    },
                }
                for seed_mult in SEED_MULT_GRID
                for expand_mult in EXPAND_MULT_GRID
            ],
        },
    }


def _load_stage6_model(
    sys_obj,
    out_dir: pathlib.Path,
    device: torch.device,
    num_outer_iters: int,
    num_mp_layers: int,
    max_active_atoms: int,
    k_leak: int,
    learned_param_set: str,
):
    ckpt = out_dir / f"{_stage6_artifact_stem(learned_param_set)}.pt"
    if not ckpt.exists() and learned_param_set == "lambda_alpha_beta":
        ckpt = out_dir / "param_joint_model.pt"
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


def _load_traditional_model_wrapper(
    sys_obj,
    out_dir: pathlib.Path,
    device: torch.device,
    num_outer_iters: int,
    pic_iters: int,
    max_active_atoms: int,
    k_leak: int,
    learned_param_set: str,
):
    ckpt = out_dir / f"{_traditional_artifact_stem(learned_param_set)}.pt"
    if not ckpt.exists() and learned_param_set == "classical_full":
        ckpt = out_dir / "traditional_param_model.pt"
    if not ckpt.exists():
        raise FileNotFoundError(f"Missing {ckpt}")
    model, data_pos = _load_traditional_model(
        sys_obj=sys_obj,
        ckpt_path=ckpt,
        device=device,
        num_outer_iters=num_outer_iters,
        pic_iters=pic_iters,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        learned_param_set=learned_param_set,
    )
    return model, np.asarray(data_pos, dtype=np.int64), ckpt


def _generate_shared_batches(
    sys_obj,
    device: torch.device,
    snr_list: list[int],
    frames: int,
) -> tuple[dict[int, SharedBatch], np.ndarray]:
    k_factor, k_max, l_max_grid, width_grid, _pad = sys_obj._get_2d_grid_params()
    del k_factor, k_max, l_max_grid, width_grid, _pad
    n = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(n, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms
    qpsk = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2.0)

    batches: dict[int, SharedBatch] = {}
    for snr_db in snr_list:
        sigma_w = 10.0 ** (-snr_db / 20.0)
        sigma_w2 = sigma_w ** 2
        feat_list = []
        y_list = []
        xp_list = []
        x_true_list = []
        speed_list = []
        channel_list = []
        for _ in range(frames):
            max_speed = np.random.uniform(5.0, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(["EPA", "EVA"])
            _, h_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym = qpsk[np.random.randint(0, 4, n)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full = x_data_sc + x_p_tpl
            s = sys_obj.afdm_modulation(x_full)
            r, _ = sys_obj.add_awgn(h_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feat = sys_obj.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feat / float(sys_obj.global_std_X or 1.0)).astype(np.float32))
            y_list.append(np.concatenate([y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate([x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc.astype(np.complex64))
            speed_list.append(float(max_speed))
            channel_list.append(str(channel_type))

        batches[int(snr_db)] = SharedBatch(
            x_feat=torch.from_numpy(np.stack(feat_list)).to(device),
            y_recv=torch.from_numpy(np.stack(y_list)).to(device),
            x_pil=torch.from_numpy(np.stack(xp_list)).to(device),
            sigma=torch.full((frames, 1), sigma_w2, dtype=torch.float32, device=device),
            x_true=np.stack(x_true_list),
            speeds=np.asarray(speed_list, dtype=np.float32),
            channel_types=np.asarray(channel_list, dtype=object),
        )
    return batches, np.asarray(data_pos, dtype=np.int64)


def _frame_ber_array(x_true: np.ndarray, x_hat_block: np.ndarray, data_pos: np.ndarray) -> np.ndarray:
    bers = [
        _ber_from_output(x_true[i], x_hat_block[i], data_pos)
        for i in range(x_true.shape[0])
    ]
    return np.asarray(bers, dtype=np.float64)


def _evaluate_stage6(
    model,
    batch: SharedBatch,
    data_pos: np.ndarray,
    overrides: dict[str, Any] | None,
):
    with torch.no_grad():
        out = model.diagnose(batch.x_feat, batch.y_recv, batch.x_pil, batch.sigma, diagnostic_overrides=overrides)
    x_hat = out["final_detection"].detach().cpu().numpy()
    frame_ber = _frame_ber_array(batch.x_true, x_hat, data_pos)
    return out, frame_ber


def _evaluate_traditional(
    model,
    batch: SharedBatch,
    data_pos: np.ndarray,
    overrides: dict[str, Any] | None,
):
    with torch.no_grad():
        out = model.diagnose(batch.x_feat, batch.y_recv, batch.x_pil, batch.sigma, diagnostic_overrides=overrides)
    x_hat = out["final_detection"].detach().cpu().numpy()
    frame_ber = _frame_ber_array(batch.x_true, x_hat, data_pos)
    return out, frame_ber


def _speed_bins(speeds: np.ndarray) -> tuple[np.ndarray, float]:
    median = float(np.median(speeds))
    bins = np.where(speeds <= median, "low", "high")
    return bins.astype(object), median


def _support_bins(support_count: np.ndarray) -> tuple[np.ndarray, float]:
    median = float(np.median(support_count))
    bins = np.where(support_count <= median, "low", "high")
    return bins.astype(object), median


def _condition_rows(
    scaffold: str,
    family: str,
    candidate_label: str,
    candidate_value: Any,
    snr_db: int,
    frame_ber: np.ndarray,
    anchor_ber: np.ndarray,
    support_count: np.ndarray,
    seed_count: np.ndarray,
    speeds: np.ndarray,
    channel_types: np.ndarray,
) -> list[dict[str, Any]]:
    speed_bin_arr, speed_median = _speed_bins(speeds)
    support_bin_arr, support_median = _support_bins(support_count)
    rows = []
    keys = sorted(set(channel_types.tolist()))
    keys_with_all = [("ALL", "ALL", "ALL")] + [
        (channel, speed_bin, support_bin)
        for channel in keys
        for speed_bin in ("low", "high")
        for support_bin in ("low", "high")
    ]

    for channel_type, speed_bin, support_bin in keys_with_all:
        mask = np.ones_like(frame_ber, dtype=bool)
        if channel_type != "ALL":
            mask &= (channel_types == channel_type)
        if speed_bin != "ALL":
            mask &= (speed_bin_arr == speed_bin)
        if support_bin != "ALL":
            mask &= (support_bin_arr == support_bin)
        if not bool(mask.any()):
            continue
        cand_mean = float(frame_ber[mask].mean())
        anchor_mean = float(anchor_ber[mask].mean())
        rows.append(
            {
                "scaffold": scaffold,
                "family": family,
                "candidate_label": candidate_label,
                "candidate_value": json.dumps(_load_json_safe(candidate_value), ensure_ascii=False),
                "snr_db": int(snr_db),
                "channel_type": channel_type,
                "speed_bin": speed_bin,
                "support_bin": support_bin,
                "num_frames": int(mask.sum()),
                "anchor_ber": anchor_mean,
                "candidate_ber": cand_mean,
                "rel_improvement": _rel_improvement(anchor_mean, cand_mean),
                "support_count_mean": float(support_count[mask].mean()),
                "seed_count_mean": float(seed_count[mask].mean()),
                "speed_median_kmh": speed_median,
                "support_median": support_median,
            }
        )
    return rows


def _variation_flag(kind: str, optimum_values: list[Any]) -> tuple[bool, dict[str, Any]]:
    compact = []
    for value in optimum_values:
        if isinstance(value, list):
            compact.append(tuple(float(v) for v in value))
        else:
            compact.append(float(value) if isinstance(value, (int, float)) else value)
    unique_values = list(dict.fromkeys(compact))
    if len(unique_values) <= 1:
        return False, {"unique_count": len(unique_values)}

    if kind == "scale":
        nums = [float(v) for v in unique_values]
        ratio = max(nums) / max(min(nums), 1e-12)
        return bool(ratio > 1.5), {"unique_count": len(unique_values), "max_min_ratio": ratio}
    if kind == "damping":
        nums = [float(v) for v in unique_values]
        span = max(nums) - min(nums)
        return bool(span > 0.05), {"unique_count": len(unique_values), "span": span}
    return True, {"unique_count": len(unique_values)}


def _rank_family(
    family_name: str,
    family_kind: str,
    family_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    by_snr: dict[int, list[dict[str, Any]]] = {}
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in family_rows:
        if row["channel_type"] == "ALL" and row["speed_bin"] == "ALL" and row["support_bin"] == "ALL":
            by_snr.setdefault(int(row["snr_db"]), []).append(row)
        cond_key = f"{row['snr_db']}|{row['channel_type']}|{row['speed_bin']}|{row['support_bin']}"
        by_condition.setdefault(cond_key, []).append(row)

    best_by_snr = {}
    improvements = []
    target_improvements = []
    for snr_db, rows in sorted(by_snr.items()):
        best = min(rows, key=lambda r: r["candidate_ber"])
        improvement = float(best["rel_improvement"])
        best_by_snr[int(snr_db)] = {
            "candidate_label": best["candidate_label"],
            "candidate_value": json.loads(best["candidate_value"]),
            "anchor_ber": best["anchor_ber"],
            "candidate_ber": best["candidate_ber"],
            "rel_improvement": improvement,
        }
        improvements.append(improvement)
        if int(snr_db) in {15, 20}:
            target_improvements.append(improvement)

    optimum_values = []
    for rows in by_condition.values():
        best = min(rows, key=lambda r: r["candidate_ber"])
        optimum_values.append(json.loads(best["candidate_value"]))

    variation_ok, variation_meta = _variation_flag(family_kind, optimum_values)
    avg_improvement = float(np.mean(improvements)) if improvements else 0.0
    max_target_improvement = float(np.max(target_improvements)) if target_improvements else 0.0
    worth_learning = bool(
        max_target_improvement > 0.10
        and avg_improvement > 0.05
        and variation_ok
    )
    return {
        "family": family_name,
        "kind": family_kind,
        "best_by_snr": best_by_snr,
        "avg_improvement": avg_improvement,
        "max_target_improvement": max_target_improvement,
        "variation_ok": variation_ok,
        "variation_meta": variation_meta,
        "worth_learning": worth_learning,
    }


def _residual_utilization_rows(
    scaffold: str,
    snr_db: int,
    out: dict[str, Any],
    speeds: np.ndarray,
    channel_types: np.ndarray,
) -> list[dict[str, Any]]:
    support_count = out["support_stats"]["support_count"].detach().cpu().numpy().reshape(-1)
    seed_count = out["support_stats"]["seed_count"].detach().cpu().numpy().reshape(-1)
    speed_bin_arr, speed_median = _speed_bins(speeds)
    support_bin_arr, support_median = _support_bins(support_count)

    param_hist = out["param_history"]
    anchor_hist = out["diagnostics"]["param_anchor_history"]
    delta_hist = out["diagnostics"]["param_delta_history"]
    stage_count = next(iter(param_hist.values())).shape[1]

    rows = []
    keys_with_all = [("ALL", "ALL", "ALL")] + [
        (channel, speed_bin, support_bin)
        for channel in sorted(set(channel_types.tolist()))
        for speed_bin in ("low", "high")
        for support_bin in ("low", "high")
    ]

    for stage_idx in range(stage_count):
        for channel_type, speed_bin, support_bin in keys_with_all:
            mask = np.ones_like(support_count, dtype=bool)
            if channel_type != "ALL":
                mask &= (channel_types == channel_type)
            if speed_bin != "ALL":
                mask &= (speed_bin_arr == speed_bin)
            if support_bin != "ALL":
                mask &= (support_bin_arr == support_bin)
            if not bool(mask.any()):
                continue

            row = {
                "scaffold": scaffold,
                "snr_db": int(snr_db),
                "stage_idx": int(stage_idx),
                "channel_type": channel_type,
                "speed_bin": speed_bin,
                "support_bin": support_bin,
                "num_frames": int(mask.sum()),
                "support_count_mean": float(support_count[mask].mean()),
                "seed_count_mean": float(seed_count[mask].mean()),
                "speed_median_kmh": speed_median,
                "support_median": support_median,
            }
            for key, tensor in param_hist.items():
                actual = tensor[:, stage_idx].detach().cpu().numpy().reshape(-1)
                anchor = anchor_hist[key][:, stage_idx].detach().cpu().numpy().reshape(-1)
                delta = delta_hist[key][:, stage_idx].detach().cpu().numpy().reshape(-1)
                abs_mean, abs_std = _mean_std(np.abs(delta[mask]))
                row[f"{key}_mean"] = float(actual[mask].mean())
                row[f"{key}_anchor_mean"] = float(anchor[mask].mean())
                row[f"{key}_delta_abs_mean"] = abs_mean
                row[f"{key}_delta_abs_std"] = abs_std
            rows.append(row)
    return rows


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


def _build_summary_md(
    out_dir: pathlib.Path,
    config: dict[str, Any],
    baseline_summary: dict[str, Any],
    rankings: dict[str, list[dict[str, Any]]],
    winner: dict[str, Any] | None,
) -> str:
    lines = [
        "# Stage 8 Diagnostic Summary",
        "",
        "## Config",
        "",
        f"- frames_per_snr: `{config['frames']}`",
        f"- snr_list: `{config['snr']}`",
        f"- seed: `{config['seed']}`",
        f"- candidate_families: `{config['candidate_families']}`",
        "",
        "## Fixed Baselines",
        "",
    ]
    for scaffold, rows in baseline_summary.items():
        lines.append(f"### {scaffold}")
        lines.append("")
        for snr_db, info in sorted(rows.items()):
            lines.append(
                f"- `{snr_db} dB`: anchor_BER=`{info['anchor_ber']:.4e}`, "
                f"support_mean=`{info['support_count_mean']:.2f}`, seed_mean=`{info['seed_count_mean']:.2f}`"
            )
        lines.append("")

    for scaffold, items in rankings.items():
        lines.append(f"## Ranking: {scaffold}")
        lines.append("")
        if not items:
            lines.append("- No candidate families evaluated.")
            lines.append("")
            continue
        for item in items[:5]:
            lines.append(
                f"- `{item['family']}`: avg_improve=`{item['avg_improvement']:.3%}`, "
                f"max_target=`{item['max_target_improvement']:.3%}`, "
                f"variation_ok=`{item['variation_ok']}`, worth_learning=`{item['worth_learning']}`"
            )
        lines.append("")

    lines.append("## Verdict")
    lines.append("")
    if winner is None:
        lines.append(
            "- No candidate satisfied the worth-learning thresholds. Current recommendation: "
            "do not add another learned scalar/module yet; move to structural modeling."
        )
    else:
        lines.append(
            f"- Top candidate: `{winner['scaffold']} / {winner['family']}`"
        )
        lines.append(
            f"- Average improvement: `{winner['avg_improvement']:.3%}`, "
            f"target improvement: `{winner['max_target_improvement']:.3%}`"
        )
        if winner["family"] == "k_leak":
            lines.append("- Next module candidate: support-side leakage-cluster aware support rule.")
        elif winner["family"] == "lambda_group":
            lines.append("- Next module candidate: refit-side group-wise / reliability-aware ridge.")
        elif winner["family"] == "sigma_inflation":
            lines.append("- Next module candidate: detector-side variance inflation / confidence calibration.")
        else:
            lines.append("- Next module candidate: outer-loop local trust gate / damping correction.")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for name in (
        "oracle_sweep_stage6.csv",
        "oracle_sweep_traditional.csv",
        "residual_utilization_stage6.csv",
        "residual_utilization_traditional.csv",
        "candidate_ranking.json",
    ):
        lines.append(f"- `{out_dir / name}`")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Stage-8 oracle sweep + heuristic breakpoint diagnosis")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--stage6-dir", type=str, default=str(here / "outputs_joint_param_ablation"))
    parser.add_argument("--traditional-dir", type=str, default=str(here / "outputs_traditional_param"))
    parser.add_argument("--baseline-dir", type=str, default=str(legacy_root / "outputs_n512"))
    parser.add_argument("--out-dir", type=str, default=str(here / "outputs_joint_heuristic_diagnosis"))
    parser.add_argument("--frames", type=int, default=200)
    parser.add_argument("--snr", nargs="+", type=int, default=[15, 20, 25])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--pic-iters", type=int, default=15)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument("--stage6-fixed-set", type=str, default="fixed", choices=list(VALID_PARAM_SETS))
    parser.add_argument("--stage6-full-set", type=str, default="lambda_alpha_beta", choices=list(VALID_PARAM_SETS))
    parser.add_argument("--traditional-fixed-set", type=str, default="fixed", choices=list(VALID_TRAD_PARAM_SETS))
    parser.add_argument("--traditional-full-set", type=str, default="classical_full", choices=list(VALID_TRAD_PARAM_SETS))
    parser.add_argument(
        "--candidate-families",
        nargs="*",
        default=None,
        help="Optional subset of families to run, e.g. lambda_global k_leak sigma_inflation",
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage6_dir = pathlib.Path(args.stage6_dir)
    traditional_dir = pathlib.Path(args.traditional_dir)
    baseline_dir = pathlib.Path(args.baseline_dir)

    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, baseline_dir)
    sys_obj.k_leak = args.k_leak
    device = sys_obj._pt_device()

    stage6_fixed, data_pos, stage6_fixed_ckpt = _load_stage6_model(
        sys_obj=sys_obj,
        out_dir=stage6_dir,
        device=device,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.stage6_fixed_set,
    )
    stage6_full, data_pos_full, stage6_full_ckpt = _load_stage6_model(
        sys_obj=sys_obj,
        out_dir=stage6_dir,
        device=device,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.stage6_full_set,
    )
    traditional_fixed, trad_pos, trad_fixed_ckpt = _load_traditional_model_wrapper(
        sys_obj=sys_obj,
        out_dir=traditional_dir,
        device=device,
        num_outer_iters=args.num_outer_iters,
        pic_iters=args.pic_iters,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.traditional_fixed_set,
    )
    traditional_full, trad_pos_full, trad_full_ckpt = _load_traditional_model_wrapper(
        sys_obj=sys_obj,
        out_dir=traditional_dir,
        device=device,
        num_outer_iters=args.num_outer_iters,
        pic_iters=args.pic_iters,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.traditional_full_set,
    )
    if not (np.array_equal(data_pos, trad_pos) and np.array_equal(data_pos, data_pos_full) and np.array_equal(data_pos, trad_pos_full)):
        raise RuntimeError("Loaded models use inconsistent data positions")

    print(f"  Stage6 fixed loaded from {stage6_fixed_ckpt}")
    print(f"  Stage6 full loaded from {stage6_full_ckpt}")
    print(f"  Trad fixed loaded from {trad_fixed_ckpt}")
    print(f"  Trad full loaded from {trad_full_ckpt}")

    batches, data_pos = _generate_shared_batches(
        sys_obj=sys_obj,
        device=device,
        snr_list=list(args.snr),
        frames=int(args.frames),
    )

    all_stage6 = _candidate_families_stage6()
    all_traditional = _candidate_families_traditional()
    selected = set(args.candidate_families or sorted(set(all_stage6) | set(all_traditional)))

    baseline_summary: dict[str, dict[int, Any]] = {"stage6_fixed": {}, "traditional_fixed": {}}
    oracle_rows_stage6: list[dict[str, Any]] = []
    oracle_rows_traditional: list[dict[str, Any]] = []
    residual_rows_stage6: list[dict[str, Any]] = []
    residual_rows_traditional: list[dict[str, Any]] = []

    stage6_family_rows: dict[str, list[dict[str, Any]]] = {}
    trad_family_rows: dict[str, list[dict[str, Any]]] = {}

    stage6_baseline_runs = {}
    trad_baseline_runs = {}

    print("\n==> Baseline fixed passes")
    for snr_db, batch in batches.items():
        out_stage6, ber_stage6 = _evaluate_stage6(stage6_fixed, batch, data_pos, overrides={})
        out_trad, ber_trad = _evaluate_traditional(traditional_fixed, batch, data_pos, overrides={})
        support_stage6 = out_stage6["support_stats"]["support_count"].detach().cpu().numpy().reshape(-1)
        seed_stage6 = out_stage6["support_stats"]["seed_count"].detach().cpu().numpy().reshape(-1)
        support_trad = out_trad["support_stats"]["support_count"].detach().cpu().numpy().reshape(-1)
        seed_trad = out_trad["support_stats"]["seed_count"].detach().cpu().numpy().reshape(-1)

        baseline_summary["stage6_fixed"][int(snr_db)] = {
            "anchor_ber": float(ber_stage6.mean()),
            "support_count_mean": float(support_stage6.mean()),
            "seed_count_mean": float(seed_stage6.mean()),
        }
        baseline_summary["traditional_fixed"][int(snr_db)] = {
            "anchor_ber": float(ber_trad.mean()),
            "support_count_mean": float(support_trad.mean()),
            "seed_count_mean": float(seed_trad.mean()),
        }
        stage6_baseline_runs[int(snr_db)] = (out_stage6, ber_stage6)
        trad_baseline_runs[int(snr_db)] = (out_trad, ber_trad)

        out_stage6_full, _ = _evaluate_stage6(stage6_full, batch, data_pos, overrides={})
        out_trad_full, _ = _evaluate_traditional(traditional_full, batch, data_pos, overrides={})
        residual_rows_stage6.extend(
            _residual_utilization_rows(
                scaffold="stage6_full",
                snr_db=int(snr_db),
                out=out_stage6_full,
                speeds=batch.speeds,
                channel_types=batch.channel_types,
            )
        )
        residual_rows_traditional.extend(
            _residual_utilization_rows(
                scaffold="traditional_full",
                snr_db=int(snr_db),
                out=out_trad_full,
                speeds=batch.speeds,
                channel_types=batch.channel_types,
            )
        )
        print(
            f"  SNR {snr_db} dB: Stage6 fixed={ber_stage6.mean():.4e}, "
            f"Trad fixed={ber_trad.mean():.4e}"
        )

    print("\n==> Stage6 oracle sweep")
    for family_name, family_spec in all_stage6.items():
        if family_name not in selected:
            continue
        rows = []
        for candidate in family_spec["candidates"]:
            label = candidate["label"]
            overrides = candidate["overrides"]
            print(f"  Stage6 / {family_name} / {label}")
            for snr_db, batch in batches.items():
                _out, cand_ber = _evaluate_stage6(stage6_fixed, batch, data_pos, overrides=overrides)
                base_out, base_ber = stage6_baseline_runs[int(snr_db)]
                support_count = base_out["support_stats"]["support_count"].detach().cpu().numpy().reshape(-1)
                seed_count = base_out["support_stats"]["seed_count"].detach().cpu().numpy().reshape(-1)
                rows.extend(
                    _condition_rows(
                        scaffold="stage6_fixed",
                        family=family_name,
                        candidate_label=label,
                        candidate_value=candidate["value"],
                        snr_db=int(snr_db),
                        frame_ber=cand_ber,
                        anchor_ber=base_ber,
                        support_count=support_count,
                        seed_count=seed_count,
                        speeds=batch.speeds,
                        channel_types=batch.channel_types,
                    )
                )
        stage6_family_rows[family_name] = rows
        oracle_rows_stage6.extend(rows)

    print("\n==> Traditional oracle sweep")
    for family_name, family_spec in all_traditional.items():
        if family_name not in selected:
            continue
        rows = []
        for candidate in family_spec["candidates"]:
            label = candidate["label"]
            overrides = candidate["overrides"]
            print(f"  Trad / {family_name} / {label}")
            for snr_db, batch in batches.items():
                _out, cand_ber = _evaluate_traditional(traditional_fixed, batch, data_pos, overrides=overrides)
                base_out, base_ber = trad_baseline_runs[int(snr_db)]
                support_count = base_out["support_stats"]["support_count"].detach().cpu().numpy().reshape(-1)
                seed_count = base_out["support_stats"]["seed_count"].detach().cpu().numpy().reshape(-1)
                rows.extend(
                    _condition_rows(
                        scaffold="traditional_fixed",
                        family=family_name,
                        candidate_label=label,
                        candidate_value=candidate["value"],
                        snr_db=int(snr_db),
                        frame_ber=cand_ber,
                        anchor_ber=base_ber,
                        support_count=support_count,
                        seed_count=seed_count,
                        speeds=batch.speeds,
                        channel_types=batch.channel_types,
                    )
                )
        trad_family_rows[family_name] = rows
        oracle_rows_traditional.extend(rows)

    stage6_rankings = [
        _rank_family(name, all_stage6[name]["kind"], rows)
        for name, rows in stage6_family_rows.items()
    ]
    stage6_rankings.sort(
        key=lambda x: (x["worth_learning"], x["avg_improvement"], x["max_target_improvement"]),
        reverse=True,
    )
    trad_rankings = [
        _rank_family(name, all_traditional[name]["kind"], rows)
        for name, rows in trad_family_rows.items()
    ]
    trad_rankings.sort(
        key=lambda x: (x["worth_learning"], x["avg_improvement"], x["max_target_improvement"]),
        reverse=True,
    )

    winner = None
    combined = (
        [{"scaffold": "stage6_fixed", **item} for item in stage6_rankings]
        + [{"scaffold": "traditional_fixed", **item} for item in trad_rankings]
    )
    worthy = [item for item in combined if item["worth_learning"]]
    if worthy:
        worthy.sort(
            key=lambda x: (
                x["avg_improvement"],
                x["max_target_improvement"],
                1.0 if x["scaffold"] == "stage6_fixed" else 0.0,
            ),
            reverse=True,
        )
        winner = worthy[0]

    _write_csv(out_dir / "oracle_sweep_stage6.csv", oracle_rows_stage6)
    _write_csv(out_dir / "oracle_sweep_traditional.csv", oracle_rows_traditional)
    _write_csv(out_dir / "residual_utilization_stage6.csv", residual_rows_stage6)
    _write_csv(out_dir / "residual_utilization_traditional.csv", residual_rows_traditional)

    ranking_payload = {
        "config": {
            "frames": int(args.frames),
            "snr": [int(s) for s in args.snr],
            "seed": int(args.seed),
            "candidate_families": sorted(selected),
            "stage6_fixed_set": args.stage6_fixed_set,
            "stage6_full_set": args.stage6_full_set,
            "traditional_fixed_set": args.traditional_fixed_set,
            "traditional_full_set": args.traditional_full_set,
        },
        "baseline_summary": baseline_summary,
        "stage6_rankings": stage6_rankings,
        "traditional_rankings": trad_rankings,
        "winner": winner,
    }
    with open(out_dir / "candidate_ranking.json", "w", encoding="utf-8") as f:
        json.dump(ranking_payload, f, indent=2, ensure_ascii=False, default=_load_json_safe)

    summary_md = _build_summary_md(
        out_dir=out_dir,
        config=ranking_payload["config"],
        baseline_summary=baseline_summary,
        rankings={
            "stage6_fixed": stage6_rankings,
            "traditional_fixed": trad_rankings,
        },
        winner=winner,
    )
    with open(out_dir / "diagnostic_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md)

    print("\n==> Saved artifacts")
    print(f"  {out_dir / 'oracle_sweep_stage6.csv'}")
    print(f"  {out_dir / 'oracle_sweep_traditional.csv'}")
    print(f"  {out_dir / 'residual_utilization_stage6.csv'}")
    print(f"  {out_dir / 'residual_utilization_traditional.csv'}")
    print(f"  {out_dir / 'candidate_ranking.json'}")
    print(f"  {out_dir / 'diagnostic_summary.md'}")


if __name__ == "__main__":
    main()
