"""
verify_joint_unrolled.py

Compare the new sparse joint unrolled receiver against:
  - classical joint OMP+MP baseline
  - optional EP baseline
  - optional OAMP baseline
  - optional LMMSE E2E baseline
"""

from __future__ import annotations

import argparse
import pathlib
import pickle
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_joint_unrolled.afdm_joint_unrolled import build_joint_unrolled_model
from afdm_sp_joint_unrolled.verify_oamp import _make_system, _sync_l_max_cap, ber_qpsk

def _load_joint_model(sys_obj, ckpt_path: pathlib.Path, device,
                      num_outer_iters: int, num_mp_layers: int,
                      max_active_atoms: int,
                      k_leak: int):
    k_factor, k_max, l_max_grid, width_grid, _pad = sys_obj._get_2d_grid_params()
    input_dim = l_max_grid * width_grid * 2 + 4
    data_pos = sys_obj.generate_pilot_frame()[4]
    ce_backbone = sys_obj.build_dnn_model_full(input_dim)
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
        num_outer_iters=num_outer_iters,
        num_mp_layers=num_mp_layers,
        max_active_atoms=max_active_atoms,
        k_leak=k_leak,
        ce_backbone=ce_backbone,
    ).to(device)
    model.load_state_dict(torch.load(str(ckpt_path), map_location=device))
    model.eval()
    return model, data_pos


def main():
    parser = argparse.ArgumentParser(
        description="Verify the sparse joint unrolled receiver against baselines"
    )
    here = pathlib.Path(__file__).parent
    parser.add_argument(
        "--joint-dir", type=str,
        default=str(here / "outputs_joint_unrolled"),
    )
    parser.add_argument(
        "--baseline-dir", type=str,
        default=str(here / "outputs_n512"),
    )
    parser.add_argument("--frames", type=int, default=100)
    parser.add_argument("--snr", nargs="+", type=int, default=[5, 10, 15, 20, 25])
    parser.add_argument("--num-outer-iters", type=int, default=5)
    parser.add_argument("--num-mp-layers", type=int, default=6)
    parser.add_argument("--max-active-atoms", type=int, default=25)
    parser.add_argument("--k-leak", type=int, default=2)
    args = parser.parse_args()

    joint_dir = pathlib.Path(args.joint_dir)
    baseline_dir = pathlib.Path(args.baseline_dir)
    joint_ckpt = joint_dir / "joint_unrolled_model.pt"
    if not joint_ckpt.exists():
        raise FileNotFoundError(f"Missing {joint_ckpt}")

    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, baseline_dir)
    sys_obj.k_leak = args.k_leak
    device = sys_obj._pt_device()

    joint_model, data_pos = _load_joint_model(
        sys_obj, joint_ckpt, device,
        num_outer_iters=args.num_outer_iters,
        num_mp_layers=args.num_mp_layers,
        max_active_atoms=args.max_active_atoms,
        k_leak=args.k_leak,
    )
    print(f"  joint model loaded from {joint_ckpt}")
    print(f"  verify config: frames={args.frames}, k_leak={args.k_leak}")

    k_factor, k_max, l_max_grid, width_grid, _pad = sys_obj._get_2d_grid_params()
    input_dim = l_max_grid * width_grid * 2 + 4
    n = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(n, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms
    qpsk = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2)

    ep_model = None
    ep_enabled = False
    ep_ckpt = baseline_dir / "ep_e2e_model.pt"
    if ep_ckpt.exists():
        ce_ep = sys_obj.build_dnn_model_full(input_dim)
        ep_model, _ = sys_obj.build_e2e_ep_model(input_dim, data_pos, ce_backbone=ce_ep, num_ep_layers=4)
        ep_model.load_state_dict(torch.load(str(ep_ckpt), map_location=device))
        ep_model.eval().to(device)
        ep_enabled = True
        print(f"  EP baseline loaded from {ep_ckpt}")

    oamp_model = None
    oamp_enabled = False
    oamp_ckpt = baseline_dir / "oamp_e2e_model.pt"
    if oamp_ckpt.exists():
        ce_oa = sys_obj.build_dnn_model_full(input_dim)
        oamp_model, _ = sys_obj.build_e2e_oamp_model(input_dim, data_pos, ce_backbone=ce_oa, num_oamp_layers=4)
        oamp_model.load_state_dict(torch.load(str(oamp_ckpt), map_location=device))
        oamp_model.eval().to(device)
        oamp_enabled = True
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

    print("\n" + "═" * 118)
    print("  Joint-Unrolled Verification")
    print("═" * 118)
    hdr = (
        f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {'OAMP_BER':>12}  {'EP_BER':>12}  "
        f"{'JointOMPMP':>12}  {'NewModel':>12}"
    )
    print(hdr)
    print("─" * len(hdr))

    results = {}
    for snr_db in args.snr:
        sigma_w = 10 ** (-snr_db / 20.0)
        sigma_w2 = sigma_w ** 2

        feat_list = []
        y_list = []
        xp_list = []
        x_true_list = []
        y_complex = []
        for _ in range(args.frames):
            max_speed = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(["EPA", "EVA"])
            _, h_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym = qpsk[np.random.randint(0, 4, n)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full = x_data_sc + x_p_tpl
            s = sys_obj.afdm_modulation(x_full)
            r, _ = sys_obj.add_awgn(h_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feat = sys_obj.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feat / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate([y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate([x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)
            y_complex.append(y_daft)

        x_feat = torch.from_numpy(np.stack(feat_list)).to(device)
        y_recv = torch.from_numpy(np.stack(y_list)).to(device)
        x_pil = torch.from_numpy(np.stack(xp_list)).to(device)
        sigma = torch.full((args.frames, 1), sigma_w2, dtype=torch.float32, device=device)

        with torch.no_grad():
            out_joint = joint_model(x_feat, y_recv, x_pil, sigma)
        x_hat_joint = out_joint["final_detection"].cpu().numpy()
        ber_joint_model = float(np.mean([
            ber_qpsk(x_true_list[i], x_hat_joint[i, :n] + 1j * x_hat_joint[i, n:])
            for i in range(args.frames)
        ]))

        ber_joint_baseline = []
        for i in range(args.frames):
            x_hat_np, _h_est = sys_obj.joint_iterative_detect(
                y_complex[i], x_p_tpl, data_pos, sigma_w2, n_outer=args.num_outer_iters
            )
            ber_joint_baseline.append(ber_qpsk(x_true_list[i], x_hat_np))
        ber_joint_baseline = float(np.mean(ber_joint_baseline))

        ber_oamp = float("nan")
        if oamp_model is not None and oamp_enabled:
            try:
                with torch.no_grad():
                    out_oamp = oamp_model(x_feat, y_recv, x_pil, sigma)
                x_hat_oamp = out_oamp["detection"].cpu().numpy()
                ber_oamp = float(np.mean([
                    ber_qpsk(x_true_list[i], x_hat_oamp[i, :n] + 1j * x_hat_oamp[i, n:])
                    for i in range(args.frames)
                ]))
            except RuntimeError as exc:
                oamp_enabled = False
                print(f"  OAMP baseline skipped after runtime failure: {exc}")

        ber_ep = float("nan")
        if ep_model is not None and ep_enabled:
            try:
                with torch.no_grad():
                    out_ep = ep_model(x_feat, y_recv, x_pil, sigma)
                x_hat_ep = out_ep["detection"].cpu().numpy()
                ber_ep = float(np.mean([
                    ber_qpsk(x_true_list[i], x_hat_ep[i, :n] + 1j * x_hat_ep[i, n:])
                    for i in range(args.frames)
                ]))
            except RuntimeError as exc:
                ep_enabled = False
                print(f"  EP baseline skipped after runtime failure: {exc}")

        ber_lmmse = float("nan")
        if lmmse_model is not None:
            with torch.no_grad():
                out_lm = lmmse_model(x_feat, y_recv, x_pil, sigma)
            x_hat_lm = out_lm["detection"].cpu().numpy()
            ber_lmmse = float(np.mean([
                ber_qpsk(x_true_list[i], x_hat_lm[i, :n] + 1j * x_hat_lm[i, n:])
                for i in range(args.frames)
            ]))

        results[snr_db] = {
            "ber_lmmse": ber_lmmse,
            "ber_oamp": ber_oamp,
            "ber_ep": ber_ep,
            "ber_joint_baseline": ber_joint_baseline,
            "ber_joint_model": ber_joint_model,
        }
        print(
            f"  {snr_db:>8}  {ber_lmmse:12.4e}  {ber_oamp:12.4e}  {ber_ep:12.4e}  "
            f"{ber_joint_baseline:12.4e}  {ber_joint_model:12.4e}"
        )

    print("═" * 118)
    out_path = joint_dir / "joint_unrolled_verify_results.pkl"
    with open(out_path, "wb") as f:
        pickle.dump(results, f)
    print(f"\n  results -> {out_path}")
    if 25 in results:
        print(
            f"  25dB target: baseline={results[25]['ber_joint_baseline']:.4e}  "
            f"new={results[25]['ber_joint_model']:.4e}"
        )


if __name__ == "__main__":
    main()
