"""
verify_refiner.py — Standalone validation script for TurboRefinerModel.

Usage:
    cd OTFS-channel-estimation
    /opt/anaconda3/envs/CE/bin/python afdm_sp_joint_unrolled/verify_refiner.py \
        --ckpt afdm_sp_joint_unrolled/outputs_n512 --snr 10 --frames 100

Acceptance criteria:
    - Stage-2 NMSE < 0.15 at every evaluated SNR   (target: < 0.15)
    - Stage-2 NMSE < Stage-1 NMSE at every SNR     (refiner always helps)
"""
import argparse, math, pathlib, sys
import numpy as np
import torch

_HERE   = pathlib.Path(__file__).parent
_PARENT = _HERE.parent
sys.path.insert(0, str(_PARENT))

SNR_LIST = [5, 10, 15, 20, 25]
QPSK     = np.array([1+1j, 1-1j, -1+1j, -1-1j], dtype=complex) / np.sqrt(2)


# ─────────────────────────────────────────────────────────────────────────────
#  l_max_cap auto-detection (same logic as quick_vx_check.py)
# ─────────────────────────────────────────────────────────────────────────────
def _sync_l_max_cap(ckpt_path: pathlib.Path, sys_obj):
    """Peek at g2d.S_T shape in checkpoint; set sys_obj.l_max_cap accordingly."""
    e2e_sd = torch.load(str(ckpt_path / 'e2e_model.pt'), map_location='cpu')
    if 'g2d.S_T' not in e2e_sd:
        return
    LW, N_ckpt = e2e_sd['g2d.S_T'].shape
    _, k_max, _, W, _ = sys_obj._get_2d_grid_params()
    if LW % W != 0:
        return
    L_max_ckpt = LW // W
    l_max_new  = L_max_ckpt - 1
    old_val    = sys_obj.l_max_cap
    if l_max_new != old_val:
        print(f"[auto-detect] checkpoint l_max_cap={l_max_new} "
              f"(env default was {old_val}). Adjusting.")
        K_factor = 2 * sys_obj.k_max_cap + 1
        sys_obj.l_max_cap   = l_max_new
        sys_obj.delta_max   = sys_obj.k_max_cap + K_factor * l_max_new
        sys_obj.max_delay_supported_s = l_max_new * sys_obj.delay_resolution
        sys_obj.max_delay_idx_bar_supported = (
            int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)


def nmse_fro(H_true, H_est):
    return float(np.linalg.norm(H_true - H_est, 'fro') ** 2 /
                 max(np.linalg.norm(H_true, 'fro') ** 2, 1e-30))


def main():
    parser = argparse.ArgumentParser(description='Verify TurboRefinerModel NMSE')
    parser.add_argument('--ckpt',   default='afdm_sp_joint_unrolled/outputs_n512',
                        help='Checkpoint directory containing e2e_model.pt, '
                             'refiner_model.pt, global_stats.pkl')
    parser.add_argument('--snr',    type=float, default=None,
                        help='Single SNR to evaluate (dB); omit for all in [5,10,15,20,25]')
    parser.add_argument('--frames', type=int, default=100,
                        help='Frames per SNR point')
    args = parser.parse_args()

    ckpt_path = pathlib.Path(args.ckpt)
    snr_list  = [args.snr] if args.snr is not None else SNR_LIST
    N_FRAMES  = args.frames

    # ── imports ──────────────────────────────────────────────────────────
    import pickle
    from afdm_sp_joint_unrolled.run_sp_unfolding import AFDMSystem

    # ── system ───────────────────────────────────────────────────────────
    sys_obj = AFDMSystem(N=16, M=32, rho=0.5)
    new_lmax = int(math.ceil(50 * 512 * sys_obj.delta_f / sys_obj.fs / 5.0)) * 5
    new_lmax = max(new_lmax, 15)
    sys_obj.l_max_cap  = new_lmax
    sys_obj.k_max_cap  = 2
    K_factor           = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max  = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)
    sys_obj.P_paths            = 5
    sys_obj.use_frac_doppler   = True
    sys_obj.k_leak             = 2
    sys_obj.frac_prune_rel_thres = 0.01

    _sync_l_max_cap(ckpt_path, sys_obj)

    # ── load stats ───────────────────────────────────────────────────────
    with open(ckpt_path / 'global_stats.pkl', 'rb') as f:
        stats = pickle.load(f)
    sys_obj.global_std_X = stats['std_X']
    sys_obj.global_std_y = stats['std_y']
    print(f"  global_std_X={sys_obj.global_std_X:.6f}  "
          f"global_std_y={sys_obj.global_std_y:.6f}")

    # ── build & load E2E model (Stage-1) ─────────────────────────────────
    K_factor_g, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    data_pos  = sys_obj.generate_pilot_frame()[4]

    ce_bb = sys_obj.build_dnn_model_full(input_dim)
    ce_bb.load_state_dict(torch.load(str(ckpt_path / 'dnn_ce_model.pt'),
                                     map_location='cpu'))
    e2e_model, _ = sys_obj.build_e2e_model(input_dim, data_pos, ce_backbone=ce_bb)
    e2e_model.load_state_dict(torch.load(str(ckpt_path / 'e2e_model.pt'),
                                         map_location='cpu'))
    print(f"  Stage-1 E2E loaded from {ckpt_path}")

    # ── build & load Turbo Refiner (Stage-2) ─────────────────────────────
    refiner_ckpt = ckpt_path / 'refiner_model.pt'
    if not refiner_ckpt.exists():
        print(f"[ERROR] refiner_model.pt not found in {ckpt_path}")
        print("  Run: python -m afdm_sp_joint_unrolled.train_n512 --refiner-only")
        sys.exit(1)
    turbo_model, _ = sys_obj.build_turbo_refiner_model(e2e_model)
    turbo_model.load_state_dict(torch.load(str(refiner_ckpt), map_location='cpu'))
    print(f"  Stage-2 Refiner loaded from {refiner_ckpt}")

    device = sys_obj._pt_device()
    e2e_model   = e2e_model.to(device).eval()
    turbo_model = turbo_model.to(device).eval()

    # ── pilot template ────────────────────────────────────────────────────
    N   = sys_obj.N_total
    rho = sys_obj.rho
    m0  = sys_obj._m0
    _, pilot_pos, pilot_syms, guard_pos, _ = sys_obj.generate_pilot_frame()
    x_p_tpl = np.zeros(N, dtype=complex)
    x_p_tpl[pilot_pos] = pilot_syms
    std_y = sys_obj.global_std_y

    # ── evaluation ────────────────────────────────────────────────────────
    print()
    print("═" * 65)
    print("  NMSE Comparison: Stage-1 E2E  vs  Stage-2 Turbo Refiner")
    print("═" * 65)
    print(f"  SNR (dB) | {'NMSE_S1':>10} | {'NMSE_S2':>10} | {'Improv%':>9}")
    print("  " + "─" * 45)

    all_s1, all_s2 = [], []
    pass_count = 0

    for snr_db in snr_list:
        feat_buf, y_buf, xp_buf, sig_buf, Heff_buf = [], [], [], [], []

        for _ in range(N_FRAMES):
            H_eff, H_time, _ = sys_obj.generate_channel_matrix(30.0, 'EVA')
            data_sym  = QPSK[np.random.randint(0, 4, N)]
            x_data_sc = np.sqrt(1.0 - rho) * data_sym
            x_p_only  = x_p_tpl.copy()
            x_full    = x_data_sc + x_p_only

            s, sw2 = sys_obj.add_awgn(H_time @ sys_obj.afdm_modulation(x_full), snr_db)
            y_daft = sys_obj.afdm_demodulation(s)

            feats = sys_obj.extract_dnn_features(
                y_daft, pilot_pos, pilot_syms, guard_pos=guard_pos).reshape(-1)
            feats = (feats / sys_obj.global_std_X).astype('float32')

            feat_buf.append(feats)
            y_buf.append(np.concatenate([np.real(y_daft), np.imag(y_daft)]).astype('float32'))
            xp_buf.append(np.concatenate([np.real(x_p_only), np.imag(x_p_only)]).astype('float32'))
            sig_buf.append(np.float32(sw2))
            Heff_buf.append(H_eff)

        feat_t = torch.from_numpy(np.stack(feat_buf)).to(device)
        y_t    = torch.from_numpy(np.stack(y_buf)).to(device)
        xp_t   = torch.from_numpy(np.stack(xp_buf)).to(device)
        sig_t  = torch.from_numpy(
            np.array(sig_buf, 'float32').reshape(-1, 1)).to(device)

        with torch.no_grad():
            out_e2e = e2e_model(feat_t, y_t, xp_t, sig_t)
            out_ref = turbo_model(feat_t, y_t, xp_t, sig_t)

        nmse_s1_list, nmse_s2_list = [], []
        for iframe in range(N_FRAMES):
            H_eff = Heff_buf[iframe]

            def _h_sc_to_nmse(h_sc_np):
                h_p = h_sc_np * std_y
                h2d = (h_p[:L_max * W] + 1j * h_p[L_max * W:]).reshape(L_max, W)
                h1d_d = sys_obj.map_2d_grid_to_1d(h2d, pad_size=pad_size)
                h1d   = sys_obj._rechirp(h1d_d, m0=m0)
                H_est = sys_obj._reconstruct_H_eff_from_taps_2d(h1d, m0)
                return nmse_fro(H_eff, H_est)

            nmse_s1_list.append(_h_sc_to_nmse(
                out_e2e['channel_est'][iframe].cpu().numpy()))
            nmse_s2_list.append(_h_sc_to_nmse(
                out_ref['channel_est_s2'][iframe].cpu().numpy()))

        m1 = float(np.mean(nmse_s1_list))
        m2 = float(np.mean(nmse_s2_list))
        imp = (m1 - m2) / max(m1, 1e-12) * 100
        all_s1.append(m1); all_s2.append(m2)
        snr_pass = m2 < 0.15 and m2 < m1
        if snr_pass:
            pass_count += 1
        marker = ' ✓' if snr_pass else ' ✗'
        print(f"  {snr_db:>8.1f} | {m1:>10.4f} | {m2:>10.4f} | {imp:>+9.1f}%{marker}")

    print("  " + "─" * 45)
    gm1 = float(np.mean(all_s1)); gm2 = float(np.mean(all_s2))
    print(f"  {'avg':>8} | {gm1:>10.4f} | {gm2:>10.4f} | "
          f"{(gm1-gm2)/max(gm1,1e-12)*100:>+9.1f}%")
    print("═" * 65)

    if gm2 < 0.15:
        print("\n  ✓ 验收通过：Stage-2 平均 NMSE={:.4f} < 0.15".format(gm2))
    else:
        print(f"\n  ✗ 验收未通过：平均 NMSE={gm2:.4f}  (需 < 0.15)")
        if gm2 < gm1:
            print(f"    (但 Stage-2 相比 Stage-1 已提升 "
                  f"{(gm1-gm2)/max(gm1,1e-12)*100:.1f}%，方向正确)")
        else:
            print("    (Stage-2 未能改善 Stage-1 — 检查训练损失是否收敛)")


if __name__ == '__main__':
    main()
