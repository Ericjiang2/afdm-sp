"""
verify_oamp.py — Standalone verification script for OAMP-Net E2E detector.

Compares E2EOAMPModel (OAMP-Net) vs E2EModel (LMMSE) across SNR [5,10,15,20,25] dB.

Metrics:
  BER       : bit error rate from hard decisions on x_hat
  mean_v_x  : mean posterior variance (should stay > 0 at high SNR)

Acceptance criteria:
  ✓ BER @ 25 dB  < 0.05   (LMMSE baseline: ~0.13)
  ✓ mean(v_x) @ 25 dB > 0.05  (LMMSE baseline: ~0.00 overconfident)

Usage:
    cd OTFS-channel-estimation
    python afdm_sp_refactored/verify_oamp.py --ckpt afdm_sp_refactored/outputs_n512 --frames 100
"""
import argparse
import math
import pathlib
import pickle
import sys

import numpy as np
import torch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_refactored.run_sp_unfolding import AFDMSystem


# ──────────────────────────────────────────────────────────────────────────
def _sync_l_max_cap(sys_obj, ckpt_dir):
    """Auto-detect l_max_cap from saved global_stats (matches training config)."""
    stats_path = pathlib.Path(ckpt_dir) / 'global_stats.pkl'
    if stats_path.exists():
        with open(stats_path, 'rb') as f:
            stats = pickle.load(f)
        sys_obj.global_std_X = stats.get('std_X', 1.0)
        sys_obj.global_std_y = stats.get('std_y', 1.0)
        # Keep l_max_cap already set on sys_obj (set by make_system_n512)
    return sys_obj


def _make_system():
    sys_obj = AFDMSystem(N=16, M=32, rho=0.5)
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    new_lmax = max(new_lmax, 15)
    sys_obj.l_max_cap   = new_lmax
    sys_obj.k_max_cap   = 2
    K_factor            = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max   = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)
    sys_obj.P_paths, sys_obj.use_frac_doppler = 5, True
    sys_obj.k_leak, sys_obj.frac_prune_rel_thres = 2, 0.01
    return sys_obj


def ber_qpsk(x_true, x_hat):
    ei = float(np.mean((np.real(x_true) > 0) != (np.real(x_hat) > 0)))
    eq = float(np.mean((np.imag(x_true) > 0) != (np.imag(x_hat) > 0)))
    return 0.5 * (ei + eq)


def main():
    parser = argparse.ArgumentParser(
        description='Verify OAMP-Net vs LMMSE E2E detector')
    parser.add_argument('--ckpt', type=str,
                        default='afdm_sp_refactored/outputs_n512',
                        help='Checkpoint directory containing oamp_e2e_model.pt '
                             'and e2e_model.pt')
    parser.add_argument('--frames', type=int, default=100,
                        help='Test frames per SNR point  (default: 100)')
    parser.add_argument('--snr', nargs='+', type=int,
                        default=[5, 10, 15, 20, 25],
                        help='SNR list in dB  (default: 5 10 15 20 25)')
    args = parser.parse_args()

    ckpt_dir = pathlib.Path(args.ckpt)
    oamp_ckpt  = ckpt_dir / 'oamp_e2e_model.pt'
    e2e_ckpt   = ckpt_dir / 'e2e_model.pt'
    ce_ckpt    = ckpt_dir / 'dnn_ce_model.pt'

    if not oamp_ckpt.exists():
        print(f"ERROR: {oamp_ckpt} not found.\n"
              f"Run: python -m afdm_sp_refactored.train_n512 --oamp-only")
        sys.exit(1)

    # ── Build system ──────────────────────────────────────────────────────
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

    # ── Load OAMP model ───────────────────────────────────────────────────
    from afdm_sp_refactored.afdm_models import E2EOAMPModel
    ce_oamp = sys_obj.build_dnn_model_full(input_dim)
    oamp_model, _ = sys_obj.build_e2e_oamp_model(input_dim, data_pos,
                                                   ce_backbone=ce_oamp,
                                                   num_oamp_layers=4)
    oamp_model.load_state_dict(
        torch.load(str(oamp_ckpt), map_location='cpu'))
    oamp_model.eval().to(device)
    print(f"  OAMP model loaded from {oamp_ckpt}")

    # ── Load LMMSE E2E baseline ────────────────────────────────────────────
    has_lmmse = e2e_ckpt.exists() and ce_ckpt.exists()
    if has_lmmse:
        ce_lm = sys_obj.build_dnn_model_full(input_dim)
        ce_lm.load_state_dict(torch.load(str(ce_ckpt), map_location='cpu'))
        e2e_lm, _ = sys_obj.build_e2e_model(input_dim, data_pos, ce_backbone=ce_lm)
        e2e_lm.load_state_dict(torch.load(str(e2e_ckpt), map_location='cpu'))
        e2e_lm.eval().to(device)
        print(f"  LMMSE E2E baseline loaded from {e2e_ckpt}")
    else:
        print("  (LMMSE baseline not found — will show OAMP results only)")

    # ── Evaluation loop ───────────────────────────────────────────────────
    rho  = sys_obj.rho
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
    print(f"\n  Evaluating {len(args.snr)} SNR points × {args.frames} frames each")

    SNR_LIST = args.snr
    results = {}

    print("\n" + "═" * 78)
    print("  OAMP-Net Verification    (vs LMMSE E2E baseline)")
    print("═" * 78)
    hdr = (f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {'OAMP_BER':>12}  "
           f"{'LMMSE_vx':>11}  {'OAMP_vx':>11}  Status")
    print(hdr)
    print("─" * len(hdr))

    for snr_db in SNR_LIST:
        sigma_w = 10 ** (-snr_db / 20.0)
        sw2     = sigma_w ** 2

        feat_list, y_list, xp_list, x_true_list = [], [], [], []
        for _ in range(args.frames):
            max_speed    = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(['EPA', 'EVA'])
            _, H_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full    = x_data_sc + x_p_tpl

            s      = sys_obj.afdm_modulation(x_full)
            r, _   = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feats = sys_obj.extract_dnn_features(y_daft, pilot_pos, pilot_syms,
                                                  guard_pos)
            feat_list.append((feats / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate([y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate([x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)   # (N,) complex

        Xf = torch.from_numpy(np.vstack(feat_list)).to(device)
        Yr = torch.from_numpy(np.vstack(y_list)).to(device)
        Xp = torch.from_numpy(np.vstack(xp_list)).to(device)
        Sw = torch.full((len(feat_list), 1), sw2, dtype=torch.float32, device=device)

        with torch.no_grad():
            out_oamp = oamp_model(Xf, Yr, Xp, Sw)

        xh_oamp = out_oamp['detection'].cpu().numpy()   # (F, 2N)
        vx_oamp = float(out_oamp['v_x'].mean().cpu())

        oamp_bers = []
        for fi, x_d in enumerate(x_true_list):
            xh = xh_oamp[fi]
            xh_c = xh[:N] + 1j * xh[N:]
            xh_c = xh_c[:len(x_d)]
            oamp_bers.append(ber_qpsk(x_d, xh_c))
        mean_oamp_ber = float(np.mean(oamp_bers))

        if has_lmmse:
            with torch.no_grad():
                out_lm = e2e_lm(Xf, Yr, Xp, Sw)
            xh_lm = out_lm['detection'].cpu().numpy()
            vx_lm = float(out_lm['v_x'].mean().cpu())
            lmmse_bers = []
            for fi, x_d in enumerate(x_true_list):
                xh = xh_lm[fi]
                xh_c = (xh[:N] + 1j * xh[N:])[:len(x_d)]
                lmmse_bers.append(ber_qpsk(x_d, xh_c))
            mean_lmmse_ber = float(np.mean(lmmse_bers))
        else:
            mean_lmmse_ber = float('nan')
            vx_lm = float('nan')

        oamp_better = (not np.isnan(mean_lmmse_ber)
                       and mean_oamp_ber < mean_lmmse_ber)
        status = "✓ better" if oamp_better else "─"

        results[snr_db] = {'ber_oamp': mean_oamp_ber, 'ber_lmmse': mean_lmmse_ber,
                            'vx_oamp': vx_oamp, 'vx_lmmse': vx_lm}
        print(f"  {snr_db:>8}  {mean_lmmse_ber:12.4e}  {mean_oamp_ber:12.4e}  "
              f"{vx_lm:11.5f}  {vx_oamp:11.5f}  {status}")

    print("═" * 78)

    # ── Acceptance verdict ────────────────────────────────────────────────
    ber_25 = results.get(25, {}).get('ber_oamp', 1.0)
    vx_25  = results.get(25, {}).get('vx_oamp', 0.0)
    ok_ber = ber_25 < 0.05
    ok_vx  = vx_25  > 0.05

    print()
    print(f"  验收标准 1 — BER @ 25dB = {ber_25:.4e}  "
          f"({'✓' if ok_ber else '✗'} target < 0.05)")
    print(f"  验收标准 2 — v_x @ 25dB = {vx_25:.5f}   "
          f"({'✓' if ok_vx else '✗'} target > 0.05, 拒绝过度自信)")
    print()
    if ok_ber and ok_vx:
        print("  ✓ 验收通过：OAMP-Net 成功打破高 SNR Error Floor")
    elif ok_ber:
        print("  △ BER 已达标，但 v_x 仍偏低 (尝试增加 num_oamp_layers)")
    elif ok_vx:
        print("  △ v_x 达标，BER 尚未突破 (尝试增加 Phase B epoch 数)")
    else:
        print("  ✗ 验收未通过 — 建议检查: "
              "(1)增加 num_oamp_layers  "
              "(2)扩大 Phase A epochs  "
              "(3)确认 CE backbone 已正确载入")


if __name__ == '__main__':
    main()
