"""
verify_turbo.py — Stand-alone BER verification for Stage-4 JointTurboReceiver.

Loads turbo_receiver_model.pt (and optionally oamp_e2e_model.pt + e2e_model.pt)
from outputs_n512/ and runs a 3-model BER comparison over SNR_EVAL_LIST.
Does NOT require any training — inference only.

Usage (server):
    python -m afdm_sp_joint_unrolled.verify_turbo
    # or
    python afdm_sp_joint_unrolled/verify_turbo.py
"""

from __future__ import annotations

import pathlib
import pickle
import sys
import os

import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── project imports ────────────────────────────────────────────────────────────
from .train_n512 import (
    make_system_n512, _gpu_info, ber_qpsk,
    SNR_EVAL_LIST, N_TEST_FRAMES, SEED, SAVE_DIR,
)

# ──────────────────────────────────────────────────────────────────────────────

def main():
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    save_dir = pathlib.Path(os.environ.get('AFDM_TURBO_SAVE_DIR', SAVE_DIR))
    n_test_frames = int(os.environ.get('AFDM_TURBO_VERIFY_FRAMES', str(N_TEST_FRAMES)))
    detector_type = os.environ.get('AFDM_TURBO_DETECTOR', 'oamp').strip().lower()
    if detector_type not in {'oamp', 'ep'}:
        raise ValueError(f"Unsupported AFDM_TURBO_DETECTOR={detector_type!r}")
    detector_label = detector_type.upper()
    turbo_ckpt_name = (
        'turbo_receiver_model.pt'
        if detector_type == 'oamp'
        else f'turbo_receiver_{detector_type}.pt')
    detector_ckpt_name = f'{detector_type}_e2e_model.pt'
    out_pkl_name = (
        'turbo_verify_results.pkl'
        if detector_type == 'oamp'
        else f'turbo_verify_results_{detector_type}.pkl')
    out_png_name = (
        'turbo_ber_comparison.png'
        if detector_type == 'oamp'
        else f'turbo_ber_comparison_{detector_type}.png')
    sys_obj  = make_system_n512(rho=0.5)
    _gpu_info()
    print(f"  verify save_dir={save_dir}")
    print(f"  verify frames={n_test_frames}")
    print(f"  verify detector={detector_type}")

    # ── load global stats ──────────────────────────────────────────────────────
    stats_path = save_dir / 'global_stats.pkl'
    if not stats_path.exists():
        raise FileNotFoundError(
            f"Cannot find {stats_path}. Run main() first to generate checkpoints.")
    with open(stats_path, 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]
    device    = sys_obj._pt_device()

    # ── load JointTurboReceiver ────────────────────────────────────────────────
    turbo_ckpt = save_dir / turbo_ckpt_name
    if not turbo_ckpt.exists():
        raise FileNotFoundError(
            f"Cannot find {turbo_ckpt}. Run --turbo-only first.")

    turbo_model, _ = sys_obj.build_turbo_receiver(
        input_dim, data_pos,
        num_outer_iters=3, num_oamp_layers=4,
        detector_type=detector_type, device=device)
    turbo_model.load_state_dict(
        torch.load(str(turbo_ckpt), map_location=device))
    turbo_model.eval()
    n_params_turbo = sum(p.numel() for p in turbo_model.parameters())
    print(f"  JointTurboReceiver loaded: {turbo_ckpt}  "
          f"({n_params_turbo:,} params)")

    # ── optionally load detector baseline ─────────────────────────────────────
    detector_model_ref = None
    detector_ckpt = save_dir / detector_ckpt_name
    if detector_ckpt.exists():
        ce_backbone2 = sys_obj.build_dnn_model_full(input_dim)
        if detector_type == 'ep':
            detector_model_ref, _ = sys_obj.build_e2e_ep_model(
                input_dim, data_pos, ce_backbone=ce_backbone2,
                num_ep_layers=4, device=device)
        else:
            detector_model_ref, _ = sys_obj.build_e2e_oamp_model(
                input_dim, data_pos, ce_backbone=ce_backbone2,
                num_oamp_layers=4, device=device)
        detector_model_ref.load_state_dict(
            torch.load(str(detector_ckpt), map_location=device))
        detector_model_ref.eval()
        print(f"  {detector_label}-Net reference loaded: {detector_ckpt}")
    else:
        print(f"  ({detector_ckpt_name} not found — skipping {detector_label} baseline)")

    # ── optionally load LMMSE E2E ──────────────────────────────────────────────
    lmmse_model_ref = None
    e2e_ckpt = save_dir / 'e2e_model.pt'
    ckpt_ce  = save_dir / 'dnn_ce_model.pt'
    if e2e_ckpt.exists() and ckpt_ce.exists():
        ce_e2e = sys_obj.build_dnn_model_full(input_dim)
        ce_e2e.load_state_dict(torch.load(str(ckpt_ce), map_location=device))
        lmmse_model_ref, _ = sys_obj.build_e2e_model(
            input_dim, data_pos, ce_backbone=ce_e2e)
        lmmse_model_ref.load_state_dict(
            torch.load(str(e2e_ckpt), map_location=device))
        lmmse_model_ref.eval()
        lmmse_model_ref = lmmse_model_ref.to(device)
        print(f"  LMMSE E2E reference loaded: {e2e_ckpt}")
    else:
        print("  (e2e_model.pt not found — skipping LMMSE baseline)")

    # ── BER evaluation loop ────────────────────────────────────────────────────
    QPSK = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)
    N    = sys_obj.N_total
    rho  = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(N, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms

    print("\n" + "═" * 72)
    print(f"  BER Comparison: LMMSE E2E  |  {detector_label}-Net  |  JointTurboReceiver")
    print("═" * 72)
    hdr = (f"{'SNR(dB)':>8}  {'LMMSE_BER':>12}  {detector_label + '_BER':>12}  "
           f"{'Turbo_BER':>12}  {'Turbo_vx':>12}")
    print(hdr)
    print("─" * len(hdr))

    rows = []
    snrs         = SNR_EVAL_LIST
    all_turbo    = []
    all_detector = []
    all_lmmse    = []

    for snr_db in snrs:
        sigma_w      = 10 ** (-snr_db / 20.0)
        sigma_w2_val = sigma_w ** 2

        feat_list = []; y_list = []; xp_list = []; x_true_list = []
        for _ in range(n_test_frames):
            max_speed    = np.random.uniform(5, sys_obj.max_speed_kmh)
            channel_type = np.random.choice(['EPA', 'EVA'])
            _, H_time, _ = sys_obj.generate_channel_matrix(max_speed, channel_type)

            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_full    = x_data_sc + x_p_tpl

            s      = sys_obj.afdm_modulation(x_full)
            r, _   = sys_obj.add_awgn(H_time @ s, snr_db)
            y_daft = sys_obj.afdm_demodulation(r)

            feats  = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos)
            feat_list.append((feats / sys_obj.global_std_X).astype(np.float32))
            y_list.append(np.concatenate(
                [y_daft.real, y_daft.imag]).astype(np.float32))
            xp_list.append(np.concatenate(
                [x_p_tpl.real, x_p_tpl.imag]).astype(np.float32))
            x_true_list.append(x_data_sc)

        Xf = torch.from_numpy(np.stack(feat_list)).to(device)
        Yr = torch.from_numpy(np.stack(y_list)).to(device)
        Xp = torch.from_numpy(np.stack(xp_list)).to(device)
        Sw = torch.full((n_test_frames, 1), sigma_w2_val,
                        dtype=torch.float32, device=device)

        # Turbo
        with torch.no_grad():
            out_turbo = turbo_model(Xf, Yr, Xp, Sw)
        x_hat_t  = out_turbo['final_detection'].cpu().numpy()
        vx_turbo = float(out_turbo['final_vx'].mean().cpu().item())
        turbo_bers = []
        for fi in range(n_test_frames):
            xh   = x_hat_t[fi]
            xh_c = xh[:N] + 1j * xh[N:]
            turbo_bers.append(ber_qpsk(x_true_list[fi], xh_c))
        ber_turbo = float(np.mean(turbo_bers))

        # Detector baseline
        ber_detector = float('nan')
        if detector_model_ref is not None:
            with torch.no_grad():
                out_oa = detector_model_ref(Xf, Yr, Xp, Sw)
            x_hat_o  = out_oa['detection'].cpu().numpy()
            detector_bers = []
            for fi in range(n_test_frames):
                xh   = x_hat_o[fi]
                xh_c = xh[:N] + 1j * xh[N:]
                detector_bers.append(ber_qpsk(x_true_list[fi], xh_c))
            ber_detector = float(np.mean(detector_bers))

        # LMMSE
        ber_lmmse = float('nan')
        if lmmse_model_ref is not None:
            with torch.no_grad():
                out_lm = lmmse_model_ref(Xf, Yr, Xp, Sw)
            x_hat_l  = out_lm['detection'].cpu().numpy()
            lmmse_bers = []
            for fi in range(n_test_frames):
                xh   = x_hat_l[fi]
                xh_c = xh[:N] + 1j * xh[N:]
                lmmse_bers.append(ber_qpsk(x_true_list[fi], xh_c))
            ber_lmmse = float(np.mean(lmmse_bers))

        all_turbo.append(ber_turbo)
        all_detector.append(ber_detector)
        all_lmmse.append(ber_lmmse)
        rows.append({'snr': snr_db, 'ber_turbo': ber_turbo,
                     'ber_detector': ber_detector, 'ber_lmmse': ber_lmmse,
                     'vx_turbo': vx_turbo})
        print(f"  {snr_db:>8}  {ber_lmmse:12.4e}  {ber_detector:12.4e}  "
              f"{ber_turbo:12.4e}  {vx_turbo:12.5f}")

    # ── summary ────────────────────────────────────────────────────────────────
    print("═" * 72)
    print(f"  {'avg':>8}  {np.nanmean(all_lmmse):12.4e}  "
          f"{np.nanmean(all_detector):12.4e}  {np.nanmean(all_turbo):12.4e}")

    ber_25 = next((r['ber_turbo'] for r in rows if r['snr'] == 25), 1.0)
    ok_ber = ber_25 < 0.01
    print()
    print(f"  BER @ 25dB = {ber_25:.4e}  ({'✓' if ok_ber else '✗'} target < 0.01)")
    print("  ✓ 验收通过：JointTurboReceiver 达到目标 BER" if ok_ber
          else "  ✗ 验收未通过，检查权重或增加训练轮次")

    # ── save results ───────────────────────────────────────────────────────────
    out_pkl = save_dir / out_pkl_name
    with open(out_pkl, 'wb') as f:
        pickle.dump({'snr': snrs, 'rows': rows,
                     'all_turbo': all_turbo, 'all_detector': all_detector,
                     'all_lmmse': all_lmmse}, f)
    print(f"\n  数值结果 → {out_pkl}")

    # ── BER plot ───────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(snrs, all_lmmse, 'r--o', label='LMMSE E2E',    markersize=5)
    ax.semilogy(snrs, all_detector, 'b-^', label=f'{detector_label}-Net', markersize=5)
    ax.semilogy(snrs, all_turbo, 'g-s',  label='JointTurbo T=3', markersize=5,
                linewidth=2)
    ax.set_xlabel('SNR (dB)')
    ax.set_ylabel('BER')
    ax.set_title(f'AFDM BER Comparison: LMMSE / {detector_label}-Net / JointTurboReceiver')
    ax.legend()
    ax.grid(True, which='both', alpha=0.4)
    out_png = save_dir / out_png_name
    fig.savefig(str(out_png), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  BER plot    → {out_png}")
    print("\n  VERIFY TURBO DONE ✓")


if __name__ == '__main__':
    main()
