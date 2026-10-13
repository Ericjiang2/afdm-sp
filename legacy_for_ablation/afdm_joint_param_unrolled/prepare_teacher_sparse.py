"""
prepare_teacher_sparse.py

Prepare sparse teacher targets for the model-driven unrolled receiver.

The raw teacher labels come from the strong joint OMP+MP baseline and already
contain per-iteration sparse support/gain states and soft symbol posteriors.
This script validates that trajectory-rich teacher export and converts it into
a compact cache used by the joint sparse unrolled receiver.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import pickle
import sys
from typing import Any

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_joint_unrolled.afdm_env import AFDMEnvMixin
from afdm_sp_joint_unrolled.afdm_models import AFDMModelsMixin
from afdm_sp_joint_unrolled.afdm_trainer import AFDMTrainerMixin
from afdm_sp_joint_unrolled.afdm_baselines import AFDMBaselinesMixin


class AFDMSystem(AFDMEnvMixin, AFDMModelsMixin, AFDMTrainerMixin, AFDMBaselinesMixin):
    pass


TRAJ_RAW_KEYS = (
    "support_teacher_iter",
    "seed_teacher_iter",
    "gain_teacher_iter",
    "mu_x_teacher_iter",
    "var_x_teacher_iter",
    "llr_teacher_iter",
    "sigma_teacher_iter",
    "residual_teacher_iter",
    "iter_used_teacher",
)

TRAJ_CACHE_KEYS = TRAJ_RAW_KEYS + (
    "X_features",
    "y_received",
    "x_pilot_frames",
    "x_data_true",
    "bits_true",
    "sigma_w2",
    "snr_db",
    "data_positions",
)


def make_system_n512(rho: float = 0.5) -> AFDMSystem:
    sys_obj = AFDMSystem(N=16, M=32, rho=rho)
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    new_lmax = max(new_lmax, 15)
    sys_obj.l_max_cap = new_lmax
    sys_obj.k_max_cap = 2
    k_factor = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + k_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1
    )
    sys_obj.P_paths = 5
    sys_obj.use_frac_doppler = True
    sys_obj.k_leak = 2
    sys_obj.frac_prune_rel_thres = 0.01
    return sys_obj


def _load_stats(sys_obj: AFDMSystem, stats_path: pathlib.Path) -> AFDMSystem:
    if stats_path.exists():
        with open(stats_path, "rb") as f:
            stats = pickle.load(f)
        sys_obj.global_std_X = stats.get("std_X", 1.0)
        sys_obj.global_std_y = stats.get("std_y", 1.0)
    return sys_obj


def _concat_batches(batches: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    combined = {
        key: np.concatenate([b[key] for b in batches], axis=0)
        for key in batches[0].keys() if key != "data_positions"
    }
    combined["data_positions"] = batches[0]["data_positions"]
    return combined


def generate_raw_teacher_dataset(
        raw_npz_path: pathlib.Path,
        stats_path: pathlib.Path,
        snr_list: list[int],
        frames_per_snr: int,
        rho: float = 0.5,
        mp_mode: str = "bp",
        seed: int = 42) -> pathlib.Path:
    from afdm_sp_joint_unrolled.generate_teacher_labels import generate_for_snr

    np.random.seed(seed)
    sys_obj = _load_stats(make_system_n512(rho=rho), stats_path)
    raw_npz_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generating raw teacher dataset")
    print(f"  out={raw_npz_path}")
    print(f"  snr={snr_list}  frames_per_snr={frames_per_snr}")
    batches = []
    for snr_db in snr_list:
        print(f"  SNR={snr_db}dB", flush=True)
        batches.append(generate_for_snr(
            sys_obj,
            snr_db=snr_db,
            n_frames=frames_per_snr,
            mp_mode=mp_mode,
            save_H=False,
            n_outer=5,
            pic_iter=15,
            pic_damp=0.5,
        ))

    combined = _concat_batches(batches)
    np.savez_compressed(raw_npz_path, **combined)
    print(f"  raw teacher saved -> {raw_npz_path}")
    print(f"  total frames={combined['X_features'].shape[0]}")
    return raw_npz_path


def _missing_raw_keys(raw: Any) -> list[str]:
    return [key for key in TRAJ_RAW_KEYS if key not in raw.files]


def _load_cache_if_valid(cache_path: pathlib.Path) -> dict[str, Any] | None:
    if not cache_path.exists():
        return None
    cache = torch.load(cache_path, map_location="cpu", weights_only=False)
    missing = [key for key in TRAJ_CACHE_KEYS if key not in cache]
    meta = cache.get("meta", {})
    if missing or int(meta.get("cache_version", 0)) < 4:
        return None
    return cache


def build_sparse_cache(
        raw_npz_path: pathlib.Path,
        cache_path: pathlib.Path,
        stats_path: pathlib.Path,
        rho: float = 0.5,
        batch_size: int = 256,
        snr_list: list[int] | None = None,
        frames_per_snr: int | None = None) -> pathlib.Path:
    sys_obj = _load_stats(make_system_n512(rho=rho), stats_path)
    raw = np.load(raw_npz_path, allow_pickle=False)
    missing = _missing_raw_keys(raw)
    if missing:
        raise RuntimeError(
            "teacher 粒度不足：raw teacher 缺少轨迹字段 "
            f"{missing}。请使用新版 generate_teacher_labels/prepare_teacher_sparse "
            "重新生成 trajectory-aware teacher。"
        )

    data_positions = torch.from_numpy(raw["data_positions"].astype(np.int64))
    support_iter = torch.from_numpy(raw["support_teacher_iter"].astype(np.float32))
    seed_iter = torch.from_numpy(raw["seed_teacher_iter"].astype(np.float32))
    gain_iter = torch.from_numpy(raw["gain_teacher_iter"].astype(np.float32))
    mu_iter = torch.from_numpy(raw["mu_x_teacher_iter"].astype(np.float32))
    var_iter = torch.from_numpy(raw["var_x_teacher_iter"].astype(np.float32))
    llr_iter = torch.from_numpy(raw["llr_teacher_iter"].astype(np.float32))

    if "snr_db" in raw.files:
        snr_db = torch.from_numpy(raw["snr_db"].astype(np.float32))
    else:
        if snr_list is None or frames_per_snr is None:
            raise RuntimeError(
                "raw teacher 缺少 snr_db，且未提供 snr_list/frames_per_snr 用于重建。"
            )
        total = int(raw["X_features"].shape[0])
        expected = int(len(snr_list) * frames_per_snr)
        if total != expected:
            raise RuntimeError(
                f"无法从旧 raw teacher 推断 snr_db：frames={total}, expected={expected}"
            )
        snr_db = torch.from_numpy(
            np.repeat(np.asarray(snr_list, dtype=np.float32), frames_per_snr)[:, None]
        )

    cache: dict[str, Any] = {
        "X_features": torch.from_numpy(raw["X_features"].astype(np.float32)),
        "y_received": torch.from_numpy(raw["y_received"].astype(np.float32)),
        "x_pilot_frames": torch.from_numpy(raw["x_pilot_frames"].astype(np.float32)),
        "x_data_true": torch.from_numpy(raw["x_data_true"].astype(np.float32)),
        "bits_true": torch.from_numpy(raw["bits_true"].astype(np.float32)),
        "sigma_w2": torch.from_numpy(raw["sigma_w2"].astype(np.float32)),
        "snr_db": snr_db,
        "mu_x_teacher": torch.from_numpy(raw["mu_x_teacher"].astype(np.float32)),
        "var_x_teacher": torch.from_numpy(raw["var_x_teacher"].astype(np.float32)),
        "llr_teacher": torch.from_numpy(raw["llr_teacher"].astype(np.float32)),
        "data_positions": data_positions,
        "support_teacher": support_iter[:, -1].clone(),
        "seed_teacher": seed_iter[:, -1].clone(),
        "gain_teacher": gain_iter[:, -1].clone(),
        "support_teacher_iter": support_iter,
        "seed_teacher_iter": seed_iter,
        "gain_teacher_iter": gain_iter,
        "mu_x_teacher_iter": mu_iter,
        "var_x_teacher_iter": var_iter,
        "llr_teacher_iter": llr_iter,
        "sigma_teacher_iter": torch.from_numpy(raw["sigma_teacher_iter"].astype(np.float32)),
        "residual_teacher_iter": torch.from_numpy(raw["residual_teacher_iter"].astype(np.float32)),
        "iter_used_teacher": torch.from_numpy(raw["iter_used_teacher"].astype(np.int32)),
        "early_stop_teacher": torch.from_numpy(raw["early_stop_teacher"].astype(np.float32))
        if "early_stop_teacher" in raw.files else None,
        "meta": {
            "cache_version": 4,
            "n_total": sys_obj.N_total,
            "l_max_cap": sys_obj.l_max_cap,
            "k_max_cap": sys_obj.k_max_cap,
            "rho": sys_obj.rho,
            "c1": sys_obj.c1,
            "c2": sys_obj.c2,
            "snr_list": list(snr_list) if snr_list is not None else None,
            "frames_per_snr": int(frames_per_snr) if frames_per_snr is not None else None,
            "global_std_X": float(sys_obj.global_std_X or 1.0),
            "global_std_y": float(sys_obj.global_std_y or 1.0),
        },
    }
    if cache["early_stop_teacher"] is None:
        del cache["early_stop_teacher"]

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(cache, cache_path)
    print(f"Sparse teacher cache saved -> {cache_path}")
    print(f"  frames={cache['X_features'].shape[0]}")
    print(f"  num_atoms={cache['support_teacher'].shape[1]}")
    print(f"  outer_iters={cache['support_teacher_iter'].shape[1]}")
    return cache_path


def load_or_prepare_teacher_cache(
        cache_path: pathlib.Path,
        raw_npz_path: pathlib.Path,
        stats_path: pathlib.Path,
        snr_list: list[int],
        frames_per_snr: int,
        rho: float = 0.5,
        force_generate: bool = False,
        batch_size: int = 256) -> pathlib.Path:
    if not force_generate:
        valid_cache = _load_cache_if_valid(cache_path)
        if valid_cache is not None:
            print(f"Using existing sparse teacher cache: {cache_path}")
            return cache_path
        if cache_path.exists():
            print(f"Existing cache is outdated or lacks trajectory keys, rebuilding: {cache_path}")

    if force_generate or not raw_npz_path.exists():
        generate_raw_teacher_dataset(
            raw_npz_path=raw_npz_path,
            stats_path=stats_path,
            snr_list=snr_list,
            frames_per_snr=frames_per_snr,
            rho=rho,
        )
    else:
        raw = np.load(raw_npz_path, allow_pickle=False)
        missing = _missing_raw_keys(raw)
        if missing:
            raise RuntimeError(
                "teacher 粒度不足：raw teacher 缺少轨迹字段 "
                f"{missing}。请删除旧 npz 或使用 --force-generate 重新生成。"
            )

    return build_sparse_cache(
        raw_npz_path=raw_npz_path,
        cache_path=cache_path,
        stats_path=stats_path,
        rho=rho,
        batch_size=batch_size,
        snr_list=snr_list,
        frames_per_snr=frames_per_snr,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Prepare sparse teacher cache for the joint unrolled receiver"
    )
    here = pathlib.Path(__file__).parent
    parser.add_argument(
        "--raw-teacher",
        type=str,
        default=str(here / "outputs_joint_unrolled" / "teacher_labels" / "teacher_all_snr_traj.npz"),
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=str(here / "outputs_joint_unrolled" / "teacher_sparse_traj_cache.pt"),
    )
    parser.add_argument(
        "--stats",
        type=str,
        default=str(here / "outputs_n512" / "global_stats.pkl"),
    )
    parser.add_argument("--snr-list", nargs="+", type=int, default=[5, 10, 15, 20, 25])
    parser.add_argument("--frames-per-snr", type=int, default=200)
    parser.add_argument("--rho", type=float, default=0.5)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--force-generate", action="store_true")
    args = parser.parse_args()

    load_or_prepare_teacher_cache(
        cache_path=pathlib.Path(args.cache),
        raw_npz_path=pathlib.Path(args.raw_teacher),
        stats_path=pathlib.Path(args.stats),
        snr_list=args.snr_list,
        frames_per_snr=args.frames_per_snr,
        rho=args.rho,
        force_generate=args.force_generate,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
