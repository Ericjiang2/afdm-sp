"""
verify_ep.py — Standalone verification script for EP-Net E2E detector.

Compares E2EEPModel (EP-Net) vs OAMP-Net (optional) vs E2EModel (LMMSE)
across SNR [5,10,15,20,25] dB.
"""
import argparse
import pathlib
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_joint_unrolled.verify_oamp import _make_system, _sync_l_max_cap, ber_qpsk


def main():
    parser = argparse.ArgumentParser(
        description='Verify EP-Net vs OAMP-Net vs LMMSE E2E detector')
    parser.add_argument('--ckpt', type=str,
                        default='afdm_sp_joint_unrolled/outputs_n512',
                        help='Checkpoint directory containing ep_e2e_model.pt')
    parser.add_argument('--frames', type=int, default=100,
                        help='Test frames per SNR point  (default: 100)')
    parser.add_argument('--snr', nargs='+', type=int,
                        default=[5, 10, 15, 20, 25],
                        help='SNR list in dB  (default: 5 10 15 20 25)')
    args = parser.parse_args()

    ckpt_dir = pathlib.Path(args.ckpt)
    ep_ckpt = ckpt_dir / 'ep_e2e_model.pt'
    oamp_ckpt = ckpt_dir / 'oamp_e2e_model.pt'
    e2e_ckpt = ckpt_dir / 'e2e_model.pt'
    ce_ckpt = ckpt_dir / 'dnn_ce_model.pt'

    if not ep_ckpt.exists():
        print(f"ERROR: {ep_ckpt} not found.\n"
              f"Train an EP baseline before running verify_ep.py.")
        sys.exit(1)

    sys_obj = _make_system()
    sys_obj = _sync_l_max_cap(sys_obj, ckpt_dir)
    print(f"  global_std_y={sys_obj.global_std_y:.6f}  "
          f"global_std_X={sys_obj.global_std_X:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    N = sys_obj.N_total
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(N, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms
    device = sys_obj._pt_device()

    ce_ep = sys_obj.build_dnn_model_full(input_dim)
    ep_model, _ = sys_obj.build_e2e_ep_model(
        input_dim, data_pos, ce_backbone=ce_ep, num_ep_layers=4)
    ep_model.load_state_dict(torch.load(str(ep_ckpt), map_location='cpu'))
    ep_model.eval().to(device)
    print(f"  EP model loaded from {ep_ckpt}")

    oamp_model = None
    if oamp_ckpt.exists():
        ce_oamp = sys_obj.build_dnn_model_full(input_dim)
        oamp_model, _ = sys_obj.build_e2e_oamp_model(
            input_dim, data_pos, ce_backbone=ce_oamp, num_oamp_layers=4)
        oamp_model.load_state_dict(torch.load(str(oamp_ckpt), map_location='cpu'))
        oamp_model.eval().to(device)
        print(f"  OAMP model loaded from {oamp_ckpt}")
    else:
        print("  (oamp_e2e_model.pt not found — skipping OAMP baseline)")

    lmmse_model = None
    if e2e_ckpt.exists() and ce_ckpt.exists():
        ce_lm = sys_obj.build_dnn_model_full(input_dim)
        ce_lm.load_state_dict(torch.load(str(ce_ckpt), map_location='cpu'))
        lmmse_model, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_lm)
        lmmse_model.load_state_dict(torch.load(str(e2e_ckpt), map_location='cpu'))
        lmmse_model.eval().to(device)
        print(f"  LMMSE E2E baseline loaded from {e2e_ckpt}")
    else:
        print("  (LMMSE baseline not found — will show EP/OAMP results only)")

    rho = sys_obj.rho
    qpsk = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)

    print(f"\n  Evaluating {len(args.snr)} SNR points x {args.frames} frames each")
    print("\n" + "═" * 92)
    print("  EP-Net Verification    (vs OAMP-Net and LMMSE E2E baseline)")
    print("═" * 92)
    hdr = (f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {'OAMP_BER':>12}  {'EP_BER':>12}  "
           f"{'LMMSE_vx':>11}  {'OAMP_vx':>11}  {'EP_vx':>11}")
    print(hdr)
    print("─" * len(hdr))

    results = {}
    for snr_db in args.snr:
        sigma_w = 10 ** (-snr_db / 20.0)
        sw2 = sigma_w ** 2

        feat_list = []
        y_list = []
        xp_list = []
        x_true_list = []
        for _ in range(args.frames):
            max_speed = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(['EPA', 'EVA'])
            _, H_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym = qpsk[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full = x_data_sc + x_p_tpl

            s = sys_obj.afdm_modulation(x_full)
            r, _ = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feats = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feats / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate([y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate([x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)

        Xf = torch.from_numpy(np.vstack(feat_list)).to(device)
        Yr = torch.from_numpy(np.vstack(y_list)).to(device)
        Xp = torch.from_numpy(np.vstack(xp_list)).to(device)
        Sw = torch.full((len(feat_list), 1), sw2, dtype=torch.float32, device=device)

        with torch.no_grad():
            out_ep = ep_model(Xf, Yr, Xp, Sw)
        xh_ep = out_ep['detection'].cpu().numpy()
        vx_ep = float(out_ep['v_x'].mean().cpu())
        ep_bers = []
        for fi, x_d in enumerate(x_true_list):
            xh = xh_ep[fi]
            xh_c = (xh[:N] + 1j * xh[N:])[:len(x_d)]
            ep_bers.append(ber_qpsk(x_d, xh_c))
        mean_ep_ber = float(np.mean(ep_bers))

        mean_oamp_ber = float('nan')
        vx_oamp = float('nan')
        if oamp_model is not None:
            with torch.no_grad():
                out_oamp = oamp_model(Xf, Yr, Xp, Sw)
            xh_oamp = out_oamp['detection'].cpu().numpy()
            vx_oamp = float(out_oamp['v_x'].mean().cpu())
            oamp_bers = []
            for fi, x_d in enumerate(x_true_list):
                xh = xh_oamp[fi]
                xh_c = (xh[:N] + 1j * xh[N:])[:len(x_d)]
                oamp_bers.append(ber_qpsk(x_d, xh_c))
            mean_oamp_ber = float(np.mean(oamp_bers))

        mean_lmmse_ber = float('nan')
        vx_lmmse = float('nan')
        if lmmse_model is not None:
            with torch.no_grad():
                out_lm = lmmse_model(Xf, Yr, Xp, Sw)
            xh_lm = out_lm['detection'].cpu().numpy()
            vx_lmmse = float(out_lm['v_x'].mean().cpu())
            lmmse_bers = []
            for fi, x_d in enumerate(x_true_list):
                xh = xh_lm[fi]
                xh_c = (xh[:N] + 1j * xh[N:])[:len(x_d)]
                lmmse_bers.append(ber_qpsk(x_d, xh_c))
            mean_lmmse_ber = float(np.mean(lmmse_bers))

        results[snr_db] = {
            'ber_ep': mean_ep_ber, 'vx_ep': vx_ep,
            'ber_oamp': mean_oamp_ber, 'vx_oamp': vx_oamp,
            'ber_lmmse': mean_lmmse_ber, 'vx_lmmse': vx_lmmse,
        }
        print(f"  {snr_db:>8}  {mean_lmmse_ber:12.4e}  {mean_oamp_ber:12.4e}  "
              f"{mean_ep_ber:12.4e}  {vx_lmmse:11.5f}  {vx_oamp:11.5f}  {vx_ep:11.5f}")

    print("═" * 92)
    ber_25 = results.get(25, {}).get('ber_ep', 1.0)
    print()
    print(f"  EP BER @ 25dB = {ber_25:.4e}")
    print("  Compare this against OAMP on the same checkpoint set before moving to Turbo+EP.")


if __name__ == '__main__':
    main()
