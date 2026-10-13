"""
train_traditional_param.py

Train the Stage-7 strict-traditional param-learned joint receiver.
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import sys
import time

import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.afdm_traditional_param import (
    VALID_TRAD_PARAM_SETS,
    build_traditional_param_model,
    compute_traditional_param_loss,
)
from afdm_joint_param_unrolled.prepare_teacher_sparse import make_system_n512, _load_stats
from afdm_joint_param_unrolled.train_joint_param import (
    _load_dataset,
    _make_loaders,
    _masked_mean,
    _maybe_enable_tf32,
    _set_seed,
    _subset_by_snr,
    _to_device_batch,
)


def _artifact_stem(learned_param_set: str) -> str:
    return f"traditional_param_{learned_param_set}"


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
    gh_all = []
    gx_all = []
    pd_all = []
    snr_all = []

    for batch in loader:
        feat, y_recv, x_pil, sigma, x_true, bits_true, snr_db = _to_device_batch(batch, device)
        with torch.set_grad_enabled(train_mode):
            out = model(feat, y_recv, x_pil, sigma)
            loss, stats = compute_traditional_param_loss(
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
            hist = out["param_history"]
            lam = hist["lambda_ls"].mean(dim=1).squeeze(-1).detach().cpu()
            gh = hist["gamma_h"].mean(dim=1).squeeze(-1).detach().cpu()
            gx = hist["gamma_x"].mean(dim=1).squeeze(-1).detach().cpu()
            pd = hist["pic_damp"].mean(dim=1).squeeze(-1).detach().cpu()
            lam_all.append(lam)
            gh_all.append(gh)
            gx_all.append(gx)
            pd_all.append(pd)
            snr_all.append(snr_db.reshape(-1).detach().cpu())

    lam_all = torch.cat(lam_all, dim=0) if lam_all else torch.empty(0)
    gh_all = torch.cat(gh_all, dim=0) if gh_all else torch.empty(0)
    gx_all = torch.cat(gx_all, dim=0) if gx_all else torch.empty(0)
    pd_all = torch.cat(pd_all, dim=0) if pd_all else torch.empty(0)
    snr_all = torch.cat(snr_all, dim=0) if snr_all else torch.empty(0)
    low_mask = snr_all <= 10.0
    high_mask = snr_all >= 20.0

    metrics = {
        "loss": loss_sum / max(count, 1),
        "bits": bits_sum / max(count, 1),
        "sym": sym_sum / max(count, 1),
        "ber": ber_sum / max(count, 1),
        "lambda_mean": float(lam_all.mean().item()) if lam_all.numel() else float("nan"),
        "gamma_h_mean": float(gh_all.mean().item()) if gh_all.numel() else float("nan"),
        "gamma_x_mean": float(gx_all.mean().item()) if gx_all.numel() else float("nan"),
        "pic_damp_mean": float(pd_all.mean().item()) if pd_all.numel() else float("nan"),
        "lambda_low": _masked_mean(lam_all, low_mask),
        "lambda_high": _masked_mean(lam_all, high_mask),
        "gamma_h_low": _masked_mean(gh_all, low_mask),
        "gamma_h_high": _masked_mean(gh_all, high_mask),
        "gamma_x_low": _masked_mean(gx_all, low_mask),
        "gamma_x_high": _masked_mean(gx_all, high_mask),
        "pic_damp_low": _masked_mean(pd_all, low_mask),
        "pic_damp_high": _masked_mean(pd_all, high_mask),
        "n_samples": count,
    }
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Train the Stage-7 strict-traditional param joint receiver")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--traditional-dir", type=str, default=str(here / "outputs_traditional_param"))
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
    parser.add_argument("--pic-iters", type=int, default=15)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument(
        "--learned-param-set",
        type=str,
        default="classical_full",
        choices=list(VALID_TRAD_PARAM_SETS),
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

    out_dir = pathlib.Path(args.traditional_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats_path = pathlib.Path(args.stats)
    sys_obj = _load_stats(make_system_n512(), stats_path)
    device = sys_obj._pt_device() if hasattr(sys_obj, "_pt_device") else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

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

    model = build_traditional_param_model(
        input_dim=int(data["X_features"].shape[1]),
        n_total=sys_obj.N_total,
        c1=sys_obj.c1,
        c2=sys_obj.c2,
        l_max_cap=sys_obj.l_max_cap,
        k_max_cap=sys_obj.k_max_cap,
        rho=sys_obj.rho,
        data_positions=data_pos,
        num_outer_iters=args.num_outer_iters,
        pic_iters=args.pic_iters,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        use_strategy_net=True,
        learned_param_set=args.learned_param_set,
    ).to(device)

    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(trainable, lr=args.lr) if trainable else None
    n_trainable = sum(p.numel() for p in trainable)
    print("Traditional Param-Joint Receiver")
    print(f"  dataset_source={dataset_source}")
    print(f"  device={device}  frames={int(data['X_features'].shape[0])}")
    print(f"  learned_param_set={args.learned_param_set}")
    print(f"  trainable_params={n_trainable}")
    print(
        f"  snr={list(args.snr_list)}  outer_iters={args.num_outer_iters}  "
        f"pic_iters={args.pic_iters}  max_active={args.max_active_atoms}"
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
            f"gh={train_stats['gamma_h_mean']:.3f}/{val_stats['gamma_h_mean']:.3f}  "
            f"gx={train_stats['gamma_x_mean']:.3f}/{val_stats['gamma_x_mean']:.3f}  "
            f"pd={train_stats['pic_damp_mean']:.3f}/{val_stats['pic_damp_mean']:.3f}  "
            f"lamL/H={train_stats['lambda_low']:.3e}/{train_stats['lambda_high']:.3e}|"
            f"{val_stats['lambda_low']:.3e}/{val_stats['lambda_high']:.3e}  "
            f"ghL/H={train_stats['gamma_h_low']:.3f}/{train_stats['gamma_h_high']:.3f}|"
            f"{val_stats['gamma_h_low']:.3f}/{val_stats['gamma_h_high']:.3f}  "
            f"gxL/H={train_stats['gamma_x_low']:.3f}/{train_stats['gamma_x_high']:.3f}|"
            f"{val_stats['gamma_x_low']:.3f}/{val_stats['gamma_x_high']:.3f}  "
            f"pdL/H={train_stats['pic_damp_low']:.3f}/{train_stats['pic_damp_high']:.3f}|"
            f"{val_stats['pic_damp_low']:.3f}/{val_stats['pic_damp_high']:.3f}  "
            f"{dt:.1f}s/ep"
        )

    artifact_stem = _artifact_stem(args.learned_param_set)
    ckpt_path = out_dir / f"{artifact_stem}.pt"
    if best_state is not None:
        torch.save(best_state, ckpt_path)
        if args.learned_param_set == "classical_full":
            torch.save(best_state, out_dir / "traditional_param_model.pt")
    results_path = out_dir / f"{artifact_stem}_results.pkl"
    payload = {
        "history": history,
        "best_epoch": best_epoch,
        "best_val_loss": best_val,
        "dataset_source": dataset_source,
        "learned_param_set": args.learned_param_set,
        "elapsed_s": time.time() - start_all,
    }
    with open(results_path, "wb") as f:
        pickle.dump(payload, f)
    if args.learned_param_set == "classical_full":
        with open(out_dir / "traditional_param_results.pkl", "wb") as f:
            pickle.dump(payload, f)
    print(f"  checkpoint -> {ckpt_path}")
    print(f"  results -> {results_path}")
    print(
        "  Verify: python -m afdm_joint_param_unrolled.verify_traditional_param "
        f"--learned-param-set {args.learned_param_set}"
    )


if __name__ == "__main__":
    main()
