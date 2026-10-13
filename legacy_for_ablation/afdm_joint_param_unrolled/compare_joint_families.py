"""
compare_joint_families.py

Unified verification for:
  - classical JointOMPMP
  - Stage-7 strict-traditional param joint
  - Stage-6 scaffold param joint
  - optional OAMP/LMMSE references
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_joint_param_unrolled.afdm_joint_param import VALID_PARAM_SETS
from afdm_joint_param_unrolled.afdm_traditional_param import VALID_TRAD_PARAM_SETS
from afdm_joint_param_unrolled.verify_joint_param import _ber_from_output, _load_param_model
from afdm_joint_param_unrolled.verify_oamp import _make_system, _sync_l_max_cap
from afdm_joint_param_unrolled.verify_traditional_param import _load_traditional_model


def _stage6_artifact_stem(learned_param_set: str) -> str:
    return f"param_joint_{learned_param_set}"


def _traditional_artifact_stem(learned_param_set: str) -> str:
    return f"traditional_param_{learned_param_set}"


def main():
    parser = argparse.ArgumentParser(description="Compare JointOMPMP, TradParamJoint, and Stage6ParamJoint")
    here = pathlib.Path(__file__).parent
    legacy_root = here.parent / "afdm_sp_joint_unrolled"
    parser.add_argument("--stage6-dir", type=str, default=str(here / "outputs_joint_param_ablation"))
    parser.add_argument("--traditional-dir", type=str, default=str(here / "outputs_traditional_param"))
    parser.add_argument("--baseline-dir", type=str, default=str(legacy_root / "outputs_n512"))
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--snr", nargs="+", type=int, default=[15, 20, 25])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--pic-iters", type=int, default=15)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    parser.add_argument(
        "--stage6-param-set",
        type=str,
        default="lambda_alpha_beta",
        choices=list(VALID_PARAM_SETS),
    )
    parser.add_argument(
        "--traditional-param-set",
        type=str,
        default="classical_full",
        choices=list(VALID_TRAD_PARAM_SETS),
    )
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    stage6_dir = pathlib.Path(args.stage6_dir)
    traditional_dir = pathlib.Path(args.traditional_dir)
    baseline_dir = pathlib.Path(args.baseline_dir)
    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, baseline_dir)
    sys_obj.k_leak = args.k_leak
    device = sys_obj._pt_device()

    stage6_ckpt = stage6_dir / f"{_stage6_artifact_stem(args.stage6_param_set)}.pt"
    if not stage6_ckpt.exists() and args.stage6_param_set == "lambda_alpha_beta":
        stage6_ckpt = stage6_dir / "param_joint_model.pt"
    if not stage6_ckpt.exists():
        raise FileNotFoundError(f"Missing {stage6_ckpt}")
    stage6_model, data_pos = _load_param_model(
        sys_obj=sys_obj,
        ckpt_path=stage6_ckpt,
        device=device,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.stage6_param_set,
    )

    trad_ckpt = traditional_dir / f"{_traditional_artifact_stem(args.traditional_param_set)}.pt"
    if not trad_ckpt.exists() and args.traditional_param_set == "classical_full":
        trad_ckpt = traditional_dir / "traditional_param_model.pt"
    if not trad_ckpt.exists():
        raise FileNotFoundError(f"Missing {trad_ckpt}")
    trad_model, trad_data_pos = _load_traditional_model(
        sys_obj=sys_obj,
        ckpt_path=trad_ckpt,
        device=device,
        num_outer_iters=args.num_outer_iters,
        pic_iters=args.pic_iters,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
        learned_param_set=args.traditional_param_set,
    )
    if not np.array_equal(data_pos, trad_data_pos):
        raise RuntimeError("Stage6 and traditional models use different data positions")

    print(f"  stage6 model loaded from {stage6_ckpt}")
    print(f"  traditional model loaded from {trad_ckpt}")
    print(
        f"  compare config: seed={args.seed}, frames={args.frames}, "
        f"outer_iters={args.num_outer_iters}, mp_layers={args.num_mp_layers}, "
        f"pic_iters={args.pic_iters}"
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

    print("\n" + "═" * 136)
    print("  Joint Family Comparison")
    print("═" * 136)
    hdr = (
        f"{'SNR(dB)':>8}  {'Frames':>6}  {'JointOMPMP':>12}  {'TradParam':>12}  "
        f"{'Stage6':>12}  {'OAMP':>12}  {'LMMSE':>12}"
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
            out_stage6 = stage6_model(x_feat, y_recv, x_pil, sigma)
            out_trad = trad_model(x_feat, y_recv, x_pil, sigma)

        x_hat_stage6 = out_stage6["final_detection"].cpu().numpy()
        x_hat_trad = out_trad["final_detection"].cpu().numpy()
        ber_stage6 = float(np.mean([
            _ber_from_output(x_true_list[i], x_hat_stage6[i], data_pos)
            for i in range(args.frames)
        ]))
        ber_trad = float(np.mean([
            _ber_from_output(x_true_list[i], x_hat_trad[i], data_pos)
            for i in range(args.frames)
        ]))

        ber_joint = []
        for i in range(args.frames):
            x_hat_np, _h_est = sys_obj.joint_iterative_detect(
                y_complex[i],
                x_p_tpl,
                data_pos,
                sigma_w2,
                n_outer=args.num_outer_iters,
            )
            ber_joint.append(_ber_from_output(
                x_true_list[i],
                np.concatenate([x_hat_np.real, x_hat_np.imag]),
                data_pos,
            ))
        ber_joint = float(np.mean(ber_joint))

        ber_oamp = float("nan")
        if oamp_model is not None:
            try:
                with torch.no_grad():
                    out_oamp = oamp_model(x_feat, y_recv, x_pil, sigma)
                x_hat_oamp = out_oamp["detection"].cpu().numpy()
                ber_oamp = float(np.mean([
                    _ber_from_output(x_true_list[i], x_hat_oamp[i], data_pos)
                    for i in range(args.frames)
                ]))
            except RuntimeError as exc:
                print(f"  OAMP baseline skipped after runtime failure: {exc}")
                oamp_model = None

        ber_lmmse = float("nan")
        if lmmse_model is not None:
            try:
                with torch.no_grad():
                    out_lm = lmmse_model(x_feat, y_recv, x_pil, sigma)
                x_hat_lm = out_lm["detection"].cpu().numpy()
                ber_lmmse = float(np.mean([
                    _ber_from_output(x_true_list[i], x_hat_lm[i], data_pos)
                    for i in range(args.frames)
                ]))
            except RuntimeError as exc:
                print(f"  LMMSE baseline skipped after runtime failure: {exc}")
                lmmse_model = None

        print(
            f"{snr_db:>8}  {args.frames:>6}  {ber_joint:>12.4e}  {ber_trad:>12.4e}  "
            f"{ber_stage6:>12.4e}  {ber_oamp:>12.4e}  {ber_lmmse:>12.4e}"
        )
        print(
            f"            trad: lambda={float(out_trad['param_history']['lambda_ls'].mean().cpu().item()):.3e}  "
            f"gh={float(out_trad['param_history']['gamma_h'].mean().cpu().item()):.3f}  "
            f"gx={float(out_trad['param_history']['gamma_x'].mean().cpu().item()):.3f}  "
            f"pd={float(out_trad['param_history']['pic_damp'].mean().cpu().item()):.3f}"
        )
        print(
            f"            s6  : lambda={float(out_stage6['param_history']['lambda_ls'].mean().cpu().item()):.3e}  "
            f"alpha={float(out_stage6['param_history']['alpha'].mean().cpu().item()):.3f}  "
            f"beta={float(out_stage6['param_history']['beta'].mean().cpu().item()):.3f}"
        )
        results[int(snr_db)] = {
            "frames": int(args.frames),
            "ber_joint": ber_joint,
            "ber_traditional_param": ber_trad,
            "ber_stage6_param": ber_stage6,
            "ber_oamp": ber_oamp,
            "ber_lmmse": ber_lmmse,
            "traditional_param_set": args.traditional_param_set,
            "stage6_param_set": args.stage6_param_set,
        }

    print("═" * 136)
    result_path = traditional_dir / "joint_family_compare_results.pkl"
    with open(result_path, "wb") as f:
        pickle.dump(
            {
                "results": results,
                "config": vars(args),
            },
            f,
        )
    print(f"\n  results -> {result_path}")


if __name__ == "__main__":
    main()
