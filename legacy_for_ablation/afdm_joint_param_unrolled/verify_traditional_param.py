"""
verify_traditional_param.py

Verify the Stage-7 strict-traditional param receiver against the classical
JointOMPMP baseline and optional OAMP/LMMSE baselines.
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.afdm_traditional_param import (
    VALID_TRAD_PARAM_SETS,
    build_traditional_param_model,
)
from afdm_joint_param_unrolled.verify_oamp import _make_system, _sync_l_max_cap, ber_qpsk


def _block_to_complex_np(x_block: np.ndarray) -> np.ndarray:
    n = x_block.shape[-1] // 2
    return x_block[..., :n] + 1j * x_block[..., n:]


def _ber_from_output(x_true_full: np.ndarray, x_hat_block: np.ndarray, data_pos: np.ndarray) -> float:
    x_hat_c = _block_to_complex_np(np.asarray(x_hat_block))
    if x_hat_c.shape[-1] == x_true_full.shape[-1]:
        return ber_qpsk(x_true_full, x_hat_c)
    if x_hat_c.shape[-1] == data_pos.size:
        return ber_qpsk(x_true_full[data_pos], x_hat_c)
    raise ValueError(
        f"Unexpected output width: x_true={x_true_full.shape[-1]}, x_hat={x_hat_c.shape[-1]}"
    )


def _artifact_stem(learned_param_set: str) -> str:
    return f"traditional_param_{learned_param_set}"


def _load_traditional_model(
    sys_obj,
    ckpt_path: pathlib.Path,
    device,
    num_outer_iters: int,
    pic_iters: int,
    max_active_atoms: int,
    k_leak: int,
    learned_param_set: str,
):
    k_factor, k_max, l_max_grid, width_grid, _pad = sys_obj._get_2d_grid_params()
    del k_factor, k_max, l_max_grid, width_grid, _pad
    _, _pilot_pos, _pilot_syms, _guard_pos, data_pos = sys_obj.generate_pilot_frame()
    model = build_traditional_param_model(
        input_dim=0,
        n_total=sys_obj.N_total,
        c1=sys_obj.c1,
        c2=sys_obj.c2,
        l_max_cap=sys_obj.l_max_cap,
        k_max_cap=sys_obj.k_max_cap,
        rho=sys_obj.rho,
        data_positions=data_pos,
        num_outer_iters=num_outer_iters,
        pic_iters=pic_iters,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        use_strategy_net=True,
        learned_param_set=learned_param_set,
    ).to(device)
    state = torch.load(str(ckpt_path), map_location=device)
    model.load_state_dict(state)
    model.eval()
    return model, np.asarray(data_pos, dtype=np.int64)


def main():
    parser = argparse.ArgumentParser(description="Verify the Stage-7 strict-traditional param joint receiver")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--traditional-dir", type=str, default=str(here / "outputs_traditional_param"))
    parser.add_argument("--baseline-dir", type=str, default=str(legacy_root / "outputs_n512"))
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--snr", nargs="+", type=int, default=[15, 20, 25])
    parser.add_argument("--seed", type=int, default=42)
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
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    traditional_dir = pathlib.Path(args.traditional_dir)
    baseline_dir = pathlib.Path(args.baseline_dir)
    artifact_stem = _artifact_stem(args.learned_param_set)
    ckpt_path = traditional_dir / f"{artifact_stem}.pt"
    if not ckpt_path.exists() and args.learned_param_set == "classical_full":
        ckpt_path = traditional_dir / "traditional_param_model.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Missing {ckpt_path}")

    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, baseline_dir)
    sys_obj.k_leak = args.k_leak
    device = sys_obj._pt_device()

    model, data_pos = _load_traditional_model(
        sys_obj=sys_obj,
        ckpt_path=ckpt_path,
        device=device,
        num_outer_iters=args.num_outer_iters,
        pic_iters=args.pic_iters,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.learned_param_set,
    )
    print(f"  traditional model loaded from {ckpt_path}")
    print(
        f"  verify config: seed={args.seed}, frames={args.frames}, "
        f"outer_iters={args.num_outer_iters}, pic_iters={args.pic_iters}, "
        f"learned_param_set={args.learned_param_set}"
    )

    k_factor, k_max, l_max_grid, width_grid, _pad = sys_obj._get_2d_grid_params()
    del k_factor, k_max, _pad
    input_dim = l_max_grid * width_grid * 2 + 4
    n = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(n, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms
    qpsk = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2.0)

    oamp_model = None
    oamp_ckpt = baseline_dir / "oamp_e2e_model.pt"
    if oamp_ckpt.exists():
        ce_oa = sys_obj.build_dnn_model_full(input_dim)
        oamp_model, _ = sys_obj.build_e2e_oamp_model(input_dim, data_pos, ce_backbone=ce_oa, num_oamp_layers=4)
        oamp_model.load_state_dict(torch.load(str(oamp_ckpt), map_location=device))
        oamp_model.eval().to(device)
        print(f"  OAMP baseline loaded from {oamp_ckpt}")

    lmmse_model = None
    e2e_ckpt = baseline_dir / "e2e_model.pt"
    ce_ckpt = baseline_dir / "dnn_ce_model.pt"
    if e2e_ckpt.exists() and ce_ckpt.exists():
        ce_lm = sys_obj.build_dnn_model_full(input_dim)
        ce_lm.load_state_dict(torch.load(str(ce_ckpt), map_location=device))
        lmmse_model, _ = sys_obj.build_e2e_model(input_dim, data_pos, ce_backbone=ce_lm)
        lmmse_model.load_state_dict(torch.load(str(e2e_ckpt), map_location=device))
        lmmse_model.eval().to(device)
        print(f"  LMMSE baseline loaded from {e2e_ckpt}")

    print("\n" + "═" * 120)
    print("  Traditional Param-Joint Verification")
    print("═" * 120)
    hdr = (
        f"{'SNR(dB)':>8}  {'Frames':>6}  {'JointOMPMP':>12}  {'TradParam':>12}  "
        f"{'OAMP':>12}  {'LMMSE':>12}"
    )
    print(hdr)
    print("─" * len(hdr))

    results = {}
    for snr_db in args.snr:
        sigma_w = 10.0 ** (-snr_db / 20.0)
        sigma_w2 = sigma_w ** 2
        feat_list = []
        y_list = []
        xp_list = []
        x_true_list = []
        y_complex = []
        for _ in range(args.frames):
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
            x_true_list.append(x_data_sc)
            y_complex.append(y_daft)

        x_feat = torch.from_numpy(np.stack(feat_list)).to(device)
        y_recv = torch.from_numpy(np.stack(y_list)).to(device)
        x_pil = torch.from_numpy(np.stack(xp_list)).to(device)
        sigma = torch.full((args.frames, 1), sigma_w2, dtype=torch.float32, device=device)

        with torch.no_grad():
            out_trad = model(x_feat, y_recv, x_pil, sigma)
        x_hat_trad = out_trad["final_detection"].cpu().numpy()
        ber_trad = float(
            np.mean(
                [
                    _ber_from_output(x_true_list[i], x_hat_trad[i], data_pos)
                    for i in range(args.frames)
                ]
            )
        )
        lam_mean = float(out_trad["param_history"]["lambda_ls"].mean().cpu().item())
        gh_mean = float(out_trad["param_history"]["gamma_h"].mean().cpu().item())
        gx_mean = float(out_trad["param_history"]["gamma_x"].mean().cpu().item())
        pd_mean = float(out_trad["param_history"]["pic_damp"].mean().cpu().item())

        ber_joint = []
        for i in range(args.frames):
            x_hat_np, _h_est = sys_obj.joint_iterative_detect(
                y_complex[i],
                x_p_tpl,
                data_pos,
                sigma_w2,
                n_outer=args.num_outer_iters,
            )
            ber_joint.append(
                _ber_from_output(
                    x_true_list[i],
                    np.concatenate([x_hat_np.real, x_hat_np.imag]),
                    data_pos,
                )
            )
        ber_joint = float(np.mean(ber_joint))

        ber_oamp = float("nan")
        if oamp_model is not None:
            try:
                with torch.no_grad():
                    out_oamp = oamp_model(x_feat, y_recv, x_pil, sigma)
                x_hat_oamp = out_oamp["detection"].cpu().numpy()
                ber_oamp = float(
                    np.mean(
                        [
                            _ber_from_output(x_true_list[i], x_hat_oamp[i], data_pos)
                            for i in range(args.frames)
                        ]
                    )
                )
            except RuntimeError as exc:
                print(f"  OAMP baseline skipped after runtime failure: {exc}")
                oamp_model = None

        ber_lmmse = float("nan")
        if lmmse_model is not None:
            try:
                with torch.no_grad():
                    out_lm = lmmse_model(x_feat, y_recv, x_pil, sigma)
                x_hat_lm = out_lm["detection"].cpu().numpy()
                ber_lmmse = float(
                    np.mean(
                        [
                            _ber_from_output(x_true_list[i], x_hat_lm[i], data_pos)
                            for i in range(args.frames)
                        ]
                    )
                )
            except RuntimeError as exc:
                print(f"  LMMSE baseline skipped after runtime failure: {exc}")
                lmmse_model = None

        print(
            f"{snr_db:>8}  {args.frames:>6}  {ber_joint:>12.4e}  {ber_trad:>12.4e}  "
            f"{ber_oamp:>12.4e}  {ber_lmmse:>12.4e}"
        )
        print(
            f"            params: lambda={lam_mean:.3e}  gamma_h={gh_mean:.3f}  "
            f"gamma_x={gx_mean:.3f}  pic_damp={pd_mean:.3f}"
        )
        results[int(snr_db)] = {
            "frames": int(args.frames),
            "ber_joint": ber_joint,
            "ber_traditional_param": ber_trad,
            "ber_oamp": ber_oamp,
            "ber_lmmse": ber_lmmse,
            "lambda_mean": lam_mean,
            "gamma_h_mean": gh_mean,
            "gamma_x_mean": gx_mean,
            "pic_damp_mean": pd_mean,
        }

    print("═" * 120)
    artifact_stem = _artifact_stem(args.learned_param_set)
    result_path = traditional_dir / f"{artifact_stem}_verify_results.pkl"
    with open(result_path, "wb") as f:
        pickle.dump(
            {
                "results": results,
                "config": vars(args),
                "learned_param_set": args.learned_param_set,
            },
            f,
        )
    if args.learned_param_set == "classical_full":
        with open(traditional_dir / "traditional_param_verify_results.pkl", "wb") as f:
            pickle.dump(
                {
                    "results": results,
                    "config": vars(args),
                    "learned_param_set": args.learned_param_set,
                },
                f,
            )
    print(f"\n  results -> {result_path}")


if __name__ == "__main__":
    main()
