"""
train_joint_param.py

Train the Stage-6 param-learned joint receiver.

v1 keeps the classical sparse joint skeleton fixed and learns only
per-iteration lambda / alpha / beta.
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import random
import sys
import time

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.afdm_joint_param import (
    VALID_PARAM_SETS,
    build_param_joint_model,
    compute_param_joint_loss,
    extract_data_block,
)
from afdm_joint_param_unrolled.prepare_teacher_sparse import make_system_n512, _load_stats


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


def _align_data_tensor(t: torch.Tensor, data_pos: torch.Tensor, n_total: int) -> torch.Tensor:
    if t.shape[1] == 2 * data_pos.numel():
        return t
    if t.shape[1] == 2 * n_total:
        return extract_data_block(t, data_pos)
    raise ValueError(
        f"Unexpected tensor width={t.shape[1]} for n_total={n_total}, n_data={data_pos.numel()}"
    )


def _load_raw_labels(
    raw_path: pathlib.Path,
    snr_list: list[int] | None = None,
    frames_per_snr: int | None = None,
) -> dict:
    raw = np.load(raw_path, allow_pickle=False)
    if "snr_db" in raw.files:
        snr_db = torch.from_numpy(raw["snr_db"].astype(np.float32)).reshape(-1)
    else:
        if snr_list is None or frames_per_snr is None:
            raise RuntimeError(
                "raw labels 缺少 snr_db，且未提供 snr_list/frames_per_snr 用于重建。"
            )
        total = int(raw["X_features"].shape[0])
        expected = int(len(snr_list) * frames_per_snr)
        if total != expected:
            raise RuntimeError(
                f"raw labels 缺少 snr_db，且无法按当前配置重建：frames={total}, expected={expected}"
            )
        snr_db = torch.from_numpy(
            np.repeat(np.asarray(snr_list, dtype=np.float32), frames_per_snr)
        ).reshape(-1)
    return {
        "X_features": torch.from_numpy(raw["X_features"].astype(np.float32)),
        "y_received": torch.from_numpy(raw["y_received"].astype(np.float32)),
        "x_pilot_frames": torch.from_numpy(raw["x_pilot_frames"].astype(np.float32)),
        "x_data_true": torch.from_numpy(raw["x_data_true"].astype(np.float32)),
        "bits_true": torch.from_numpy(raw["bits_true"].astype(np.float32)),
        "sigma_w2": torch.from_numpy(raw["sigma_w2"].astype(np.float32)),
        "snr_db": snr_db,
        "data_positions": torch.from_numpy(raw["data_positions"].astype(np.int64)),
    }


def _load_teacher_cache(cache_path: pathlib.Path) -> dict:
    cache = torch.load(cache_path, map_location="cpu", weights_only=False)
    return {
        "X_features": cache["X_features"].float(),
        "y_received": cache["y_received"].float(),
        "x_pilot_frames": cache["x_pilot_frames"].float(),
        "x_data_true": cache["x_data_true"].float(),
        "bits_true": cache["bits_true"].float(),
        "sigma_w2": cache["sigma_w2"].float(),
        "snr_db": cache["snr_db"].float().reshape(-1),
        "data_positions": cache["data_positions"].long(),
    }


def _qpsk_bits_and_block(x_c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x_block = np.concatenate([x_c.real, x_c.imag]).astype(np.float32)
    bits = np.concatenate(
        [
            (x_c.real < 0.0).astype(np.float32),
            (x_c.imag < 0.0).astype(np.float32),
        ]
    )
    return bits, x_block


def _generate_online_dataset(
    sys_obj,
    snr_list: list[int],
    frames_per_snr: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    qpsk = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2.0)
    n = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(n, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms

    feat_list = []
    y_list = []
    xp_list = []
    x_true_list = []
    bits_list = []
    sigma_list = []
    snr_out = []

    for snr_db in snr_list:
        for _ in range(int(frames_per_snr)):
            max_speed = rng.uniform(5.0, sys_obj.max_speed_kmh)
            channel_type = rng.choice(["EPA", "EVA"])
            _, h_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym = qpsk[rng.integers(0, 4, size=n)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full = x_data_sc + x_p_tpl
            s = sys_obj.afdm_modulation(x_full)
            r, _ = sys_obj.add_awgn(h_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feat = sys_obj.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feat / float(sys_obj.global_std_X or 1.0)).astype(np.float32))
            y_list.append(np.concatenate([y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate([x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))

            x_data_use = x_data_sc[data_pos]
            bits, x_block = _qpsk_bits_and_block(x_data_use)
            x_true_list.append(x_block)
            bits_list.append(bits)
            sigma_list.append(np.array([10.0 ** (-snr_db / 10.0)], dtype=np.float32))
            snr_out.append(np.float32(snr_db))

    return {
        "X_features": torch.from_numpy(np.stack(feat_list).astype(np.float32)),
        "y_received": torch.from_numpy(np.stack(y_list).astype(np.float32)),
        "x_pilot_frames": torch.from_numpy(np.stack(xp_list).astype(np.float32)),
        "x_data_true": torch.from_numpy(np.stack(x_true_list).astype(np.float32)),
        "bits_true": torch.from_numpy(np.stack(bits_list).astype(np.float32)),
        "sigma_w2": torch.from_numpy(np.stack(sigma_list).astype(np.float32)),
        "snr_db": torch.from_numpy(np.asarray(snr_out, dtype=np.float32)),
        "data_positions": torch.from_numpy(np.asarray(data_pos, dtype=np.int64)),
    }


def _load_dataset(
    dataset_source: str,
    raw_labels: pathlib.Path,
    teacher_cache: pathlib.Path,
    sys_obj,
    snr_list: list[int],
    frames_per_snr: int,
    seed: int,
) -> tuple[dict, str]:
    errors = []
    order = ["raw_labels", "teacher_cache", "online"] if dataset_source == "auto" else [dataset_source]
    for source in order:
        try:
            if source == "raw_labels":
                return _load_raw_labels(
                    raw_labels,
                    snr_list=snr_list,
                    frames_per_snr=frames_per_snr,
                ), source
            if source == "teacher_cache":
                return _load_teacher_cache(teacher_cache), source
            if source == "online":
                return _generate_online_dataset(sys_obj, snr_list, frames_per_snr, seed), source
            raise ValueError(f"Unsupported dataset source: {source}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")
    raise RuntimeError("Failed to load training dataset:\n  " + "\n  ".join(errors))


def _subset_by_snr(
    data: dict,
    snr_list: list[int],
    frames_per_snr: int,
    seed: int,
) -> dict:
    snr = data["snr_db"].reshape(-1).cpu().numpy()
    rng = np.random.default_rng(seed)
    keep_ids = []
    for snr_db in snr_list:
        idx = np.where(np.isclose(snr, float(snr_db)))[0]
        if idx.size == 0:
            continue
        rng.shuffle(idx)
        keep_ids.append(idx[: min(idx.size, int(frames_per_snr))])
    if not keep_ids:
        raise RuntimeError(f"No samples matched snr_list={snr_list}")
    ids = np.concatenate(keep_ids, axis=0)
    ids_t = torch.from_numpy(np.asarray(ids, dtype=np.int64))
    subset = {}
    for key, value in data.items():
        if key == "data_positions":
            subset[key] = value.clone()
        else:
            subset[key] = value[ids_t]
    return subset


def _split_train_val(snr_db: torch.Tensor, val_split: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    snr_np = snr_db.reshape(-1).cpu().numpy()
    rng = np.random.default_rng(seed)
    train_ids = []
    val_ids = []
    for snr_val in sorted(set(float(x) for x in snr_np.tolist())):
        idx = np.where(np.isclose(snr_np, snr_val))[0]
        rng.shuffle(idx)
        if idx.size <= 1:
            train_ids.append(idx)
            continue
        n_val = int(round(idx.size * val_split))
        n_val = min(max(n_val, 1), idx.size - 1)
        val_ids.append(idx[:n_val])
        train_ids.append(idx[n_val:])
    train_idx = np.concatenate(train_ids, axis=0) if train_ids else np.empty((0,), dtype=np.int64)
    val_idx = np.concatenate(val_ids, axis=0) if val_ids else np.empty((0,), dtype=np.int64)
    return train_idx, val_idx


def _make_loaders(
    data: dict,
    batch_size: int,
    val_batch_size: int,
    val_split: float,
    num_workers: int,
    seed: int,
    n_total: int,
) -> tuple[DataLoader, DataLoader, torch.Tensor]:
    data_pos = data["data_positions"].long()
    x_true = _align_data_tensor(data["x_data_true"].float(), data_pos, n_total)
    bits_true = _align_data_tensor(data["bits_true"].float(), data_pos, n_total)
    dataset = TensorDataset(
        data["X_features"].float(),
        data["y_received"].float(),
        data["x_pilot_frames"].float(),
        data["sigma_w2"].float(),
        x_true,
        bits_true,
        data["snr_db"].float().reshape(-1, 1),
    )
    train_idx, val_idx = _split_train_val(data["snr_db"], val_split=val_split, seed=seed)
    train_ds = torch.utils.data.Subset(dataset, train_idx.tolist())
    val_ds = torch.utils.data.Subset(dataset, val_idx.tolist()) if val_idx.size > 0 else train_ds
    loader_kw = {
        "num_workers": int(num_workers),
        "pin_memory": torch.cuda.is_available(),
    }
    if num_workers > 0:
        loader_kw["persistent_workers"] = True
    tr_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, **loader_kw)
    va_loader = DataLoader(val_ds, batch_size=val_batch_size, shuffle=False, **loader_kw)
    return tr_loader, va_loader, data_pos


def _to_device_batch(batch, device):
    return tuple(x.to(device, non_blocking=True) for x in batch)


def _masked_mean(values: torch.Tensor, mask: torch.Tensor) -> float:
    if values.numel() == 0 or not bool(mask.any().item()):
        return float("nan")
    return float(values[mask].mean().item())


def _artifact_stem(learned_param_set: str) -> str:
    return f"param_joint_{learned_param_set}"


def _epoch_pass(
    model,
    loader,
    device,
    optimizer=None,
    lambda_sym: float = 0.1,
    deep_supervision: float = 0.0,
    grad_clip: float = 1.0,
):
    train_mode = optimizer is not None
    model.train(mode=train_mode)
    loss_sum = 0.0
    bits_sum = 0.0
    sym_sum = 0.0
    ber_sum = 0.0
    count = 0
    lam_all = []
    alpha_all = []
    beta_all = []
    snr_all = []

    for batch in loader:
        feat, y_recv, x_pil, sigma, x_true, bits_true, snr_db = _to_device_batch(batch, device)
        with torch.set_grad_enabled(train_mode):
            out = model(feat, y_recv, x_pil, sigma)
            loss, stats = compute_param_joint_loss(
                out,
                bits_true=bits_true,
                x_data_true=x_true,
                lambda_sym=lambda_sym,
                deep_supervision=deep_supervision,
            )
            if train_mode:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                if grad_clip > 0.0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                optimizer.step()

        bsz = int(bits_true.shape[0])
        loss_sum += float(stats["loss"].item()) * bsz
        bits_sum += float(stats["bits"].item()) * bsz
        sym_sum += float(stats["sym"].item()) * bsz
        ber_sum += float(stats["ber"].item()) * bsz
        count += bsz

        with torch.no_grad():
            lam = out["param_history"]["lambda_ls"].mean(dim=1).squeeze(-1).detach().cpu()
            alpha = out["param_history"]["alpha"].mean(dim=1).squeeze(-1).detach().cpu()
            beta = out["param_history"]["beta"].mean(dim=1).squeeze(-1).detach().cpu()
            lam_all.append(lam)
            alpha_all.append(alpha)
            beta_all.append(beta)
            snr_all.append(snr_db.reshape(-1).detach().cpu())

    lam_all = torch.cat(lam_all, dim=0) if lam_all else torch.empty(0)
    alpha_all = torch.cat(alpha_all, dim=0) if alpha_all else torch.empty(0)
    beta_all = torch.cat(beta_all, dim=0) if beta_all else torch.empty(0)
    snr_all = torch.cat(snr_all, dim=0) if snr_all else torch.empty(0)
    low_mask = snr_all <= 10.0
    high_mask = snr_all >= 20.0

    metrics = {
        "loss": loss_sum / max(count, 1),
        "bits": bits_sum / max(count, 1),
        "sym": sym_sum / max(count, 1),
        "ber": ber_sum / max(count, 1),
        "lambda_mean": float(lam_all.mean().item()) if lam_all.numel() else float("nan"),
        "alpha_mean": float(alpha_all.mean().item()) if alpha_all.numel() else float("nan"),
        "beta_mean": float(beta_all.mean().item()) if beta_all.numel() else float("nan"),
        "lambda_low": _masked_mean(lam_all, low_mask),
        "lambda_high": _masked_mean(lam_all, high_mask),
        "alpha_low": _masked_mean(alpha_all, low_mask),
        "alpha_high": _masked_mean(alpha_all, high_mask),
        "beta_low": _masked_mean(beta_all, low_mask),
        "beta_high": _masked_mean(beta_all, high_mask),
        "n_samples": count,
    }
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train the Stage-6 param-learned joint receiver")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--joint-dir", type=str, default=str(here / "outputs_joint_param"))
    parser.add_argument(
        "--stats",
        type=str,
        default=str(legacy_root / "outputs_n512" / "global_stats.pkl"),
    )
    parser.add_argument(
        "--raw-labels",
        type=str,
        default=str(legacy_root / "outputs_joint_unrolled" / "teacher_labels" / "teacher_all_snr_traj.npz"),
    )
    parser.add_argument(
        "--teacher-cache",
        type=str,
        default=str(legacy_root / "outputs_joint_unrolled" / "teacher_sparse_traj_cache.pt"),
    )
    parser.add_argument(
        "--dataset-source",
        type=str,
        default="auto",
        choices=["auto", "raw_labels", "teacher_cache", "online"],
    )
    parser.add_argument("--frames-per-snr", type=int, default=20)
    parser.add_argument("--snr-list", nargs="+", type=int, default=[5, 10, 15, 20, 25])
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--val-batch-size", type=int, default=64)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument(
        "--learned-param-set",
        type=str,
        default="lambda_alpha_beta",
        choices=list(VALID_PARAM_SETS),
    )
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--lambda-sym", type=float, default=0.1)
    parser.add_argument("--deep-supervision", type=float, default=0.0)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tf32", action="store_true")
    args = parser.parse_args()

    _set_seed(args.seed)
    _maybe_enable_tf32(args.tf32)

    out_dir = pathlib.Path(args.joint_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats_path = pathlib.Path(args.stats)
    sys_obj = _load_stats(make_system_n512(), stats_path)
    device = sys_obj._pt_device() if hasattr(sys_obj, "_pt_device") else torch.device("cuda" if torch.cuda.is_available() else "cpu")

    data, dataset_source = _load_dataset(
        dataset_source=args.dataset_source,
        raw_labels=pathlib.Path(args.raw_labels),
        teacher_cache=pathlib.Path(args.teacher_cache),
        sys_obj=sys_obj,
        snr_list=list(args.snr_list),
        frames_per_snr=int(args.frames_per_snr),
        seed=args.seed,
    )
    data = _subset_by_snr(data, list(args.snr_list), int(args.frames_per_snr), seed=args.seed)
    tr_loader, va_loader, data_pos = _make_loaders(
        data=data,
        batch_size=args.batch_size,
        val_batch_size=args.val_batch_size,
        val_split=args.val_split,
        num_workers=args.num_workers,
        seed=args.seed,
        n_total=sys_obj.N_total,
    )

    model = build_param_joint_model(
        input_dim=int(data["X_features"].shape[1]),
        n_total=sys_obj.N_total,
        c1=sys_obj.c1,
        c2=sys_obj.c2,
        l_max_cap=sys_obj.l_max_cap,
        k_max_cap=sys_obj.k_max_cap,
        data_positions=data_pos,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        use_strategy_net=True,
        learned_param_set=args.learned_param_set,
    ).to(device)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable, lr=args.lr) if trainable else None

    n_trainable = sum(p.numel() for p in trainable)
    print("Param-Learned Joint Receiver")
    print(f"  dataset_source={dataset_source}")
    print(f"  device={device}  frames={int(data['X_features'].shape[0])}")
    print(f"  learned_param_set={args.learned_param_set}")
    print(f"  trainable_params={n_trainable}")
    print(
        f"  snr={list(args.snr_list)}  outer_iters={args.num_outer_iters}  "
        f"mp_layers={args.num_mp_layers}  max_active={args.max_active_atoms}"
    )

    history = {"train": [], "val": [], "config": vars(args), "dataset_source": dataset_source}
    best_state = None
    best_val = float("inf")
    best_epoch = 0

    start_all = time.time()
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_stats = _epoch_pass(
            model,
            tr_loader,
            device=device,
            optimizer=optimizer,
            lambda_sym=args.lambda_sym,
            deep_supervision=args.deep_supervision,
            grad_clip=args.grad_clip,
        )
        with torch.no_grad():
            val_stats = _epoch_pass(
                model,
                va_loader,
                device=device,
                optimizer=None,
                lambda_sym=args.lambda_sym,
                deep_supervision=args.deep_supervision,
                grad_clip=args.grad_clip,
            )
        dt = time.time() - t0

        history["train"].append(train_stats)
        history["val"].append(val_stats)
        if val_stats["loss"] < best_val:
            best_val = val_stats["loss"]
            best_epoch = epoch
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}

        print(
            f"  Epoch [{epoch:>2}/{args.epochs}]  "
            f"tr_loss={train_stats['loss']:.3e}  va_loss={val_stats['loss']:.3e}  "
            f"ber={train_stats['ber']:.4f}/{val_stats['ber']:.4f}  "
            f"lam={train_stats['lambda_mean']:.3e}/{val_stats['lambda_mean']:.3e}  "
            f"alpha={train_stats['alpha_mean']:.3f}/{val_stats['alpha_mean']:.3f}  "
            f"beta={train_stats['beta_mean']:.3f}/{val_stats['beta_mean']:.3f}  "
            f"lamL/H={train_stats['lambda_low']:.3e}/{train_stats['lambda_high']:.3e}|"
            f"{val_stats['lambda_low']:.3e}/{val_stats['lambda_high']:.3e}  "
            f"alphaL/H={train_stats['alpha_low']:.3f}/{train_stats['alpha_high']:.3f}|"
            f"{val_stats['alpha_low']:.3f}/{val_stats['alpha_high']:.3f}  "
            f"betaL/H={train_stats['beta_low']:.3f}/{train_stats['beta_high']:.3f}|"
            f"{val_stats['beta_low']:.3f}/{val_stats['beta_high']:.3f}  "
            f"{dt:.1f}s/ep"
        )

    artifact_stem = _artifact_stem(args.learned_param_set)
    ckpt_path = out_dir / f"{artifact_stem}.pt"
    if best_state is not None:
        torch.save(best_state, ckpt_path)
        if args.learned_param_set == "lambda_alpha_beta":
            torch.save(best_state, out_dir / "param_joint_model.pt")
    results_path = out_dir / f"{artifact_stem}_results.pkl"
    with open(results_path, "wb") as f:
        pickle.dump(
            {
                "history": history,
                "best_epoch": best_epoch,
                "best_val_loss": best_val,
                "dataset_source": dataset_source,
                "learned_param_set": args.learned_param_set,
                "elapsed_s": time.time() - start_all,
            },
            f,
        )
    if args.learned_param_set == "lambda_alpha_beta":
        with open(out_dir / "param_joint_results.pkl", "wb") as f:
            pickle.dump(
                {
                    "history": history,
                    "best_epoch": best_epoch,
                    "best_val_loss": best_val,
                    "dataset_source": dataset_source,
                    "learned_param_set": args.learned_param_set,
                    "elapsed_s": time.time() - start_all,
                },
                f,
            )
    print(f"  checkpoint -> {ckpt_path}")
    print(f"  results -> {results_path}")
    print(
        "  Verify: python -m afdm_joint_param_unrolled.verify_joint_param "
        f"--learned-param-set {args.learned_param_set}"
    )


if __name__ == "__main__":
    main()
