"""generate_teacher_labels.py — Generate per-frame soft teacher labels from
the classical Joint OMP+MP baseline receiver for Step-2 distillation training.

For each SNR point, simulates AFDM-SP frames and runs
`joint_omp_mp_iterative` with `return_soft=True` to obtain per-symbol
Bayesian posteriors (mean + variance).  These are saved alongside the
standard E2E training data as "oracle soft targets" for training a
noise-aware demapper.

Output NPZ fields (per batch)
------------------------------
X_features      : (F, input_dim)  float32 — DNN CE features (normalised)
y_received      : (F, 2*N)        float32 — [Re(y); Im(y)]
x_pilot_frames  : (F, 2*N)        float32 — [Re(x_p); Im(x_p)]
x_data_true     : (F, 2*N)        float32 — true scaled data symbols [Re; Im]
bits_true        : (F, 2*N)        float32 — Gray-coded ground-truth bits
sigma_w2         : (F, 1)          float32 — per-frame noise variance
snr_db           : (F, 1)          float32 — per-frame SNR label in dB
data_positions   : (N_d,)          int     — data-symbol indices in [0, N)
--- teacher labels (all at data scale sqrt(1-rho)) ---
mu_x_teacher     : (F, 2*N_d)      float32 — [Re(mu_post); Im(mu_post)] data symbols
var_x_teacher    : (F, 2*N_d)      float32 — [var_post_r; var_post_i] ≈ var_post/2 each
llr_teacher      : (F, 2*N_d)      float32 — approximate LLR = 2*mu / var_per_comp
H_teacher        : (F, 2*N*N)      float32 — [Re(H); Im(H)] stacked (optional, see --save-H)
support_teacher_iter : (F, T, Q)   float32 — dense support mask per outer iteration
seed_teacher_iter    : (F, T, Q)   float32 — pre-expansion seed mask per outer iteration
gain_teacher_iter    : (F, T, 2*Q) float32 — dense complex gains [Re; Im] per outer iteration
mu_x_teacher_iter    : (F, T, 2*N_d) float32 — per-iteration soft symbol means
var_x_teacher_iter   : (F, T, 2*N_d) float32 — per-iteration component variances
llr_teacher_iter     : (F, T, 2*N_d) float32 — per-iteration approximate LLRs
sigma_teacher_iter   : (F, T, 1)   float32 — effective residual variance per iteration
residual_teacher_iter: (F, T, 1)   float32 — residual norm per iteration
iter_used_teacher    : (F, 1)      int32   — actual number of outer iterations used
early_stop_teacher   : (F, 1)      float32 — 1 if early stop triggered, else 0

Usage
-----
    python -m afdm_sp_joint_unrolled.generate_teacher_labels \\
        --out-dir teacher_data/ \\
        --snr-list 5 10 15 20 \\
        --frames-per-snr 1000 \\
        --mp-mode bp \\
        [--save-H]
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

# ── project imports ────────────────────────────────────────────────────────────
_HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

from afdm_sp_joint_unrolled.run_sp_unfolding import AFDMSystem
from afdm_sp_joint_unrolled.afdm_baselines import joint_omp_mp_iterative

QPSK = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2)


# ──────────────────────────────────────────────────────────────────────────────
#  Core generation
# ──────────────────────────────────────────────────────────────────────────────

def generate_for_snr(
        sys_obj: AFDMSystem,
        snr_db: float,
        n_frames: int,
        mp_mode: str = 'bp',
        save_H: bool = False,
        n_outer: int = 5,
        pic_iter: int = 15,
        pic_damp: float = 0.5,
) -> dict:
    """Generate ``n_frames`` at ``snr_db`` and return dict of arrays."""
    N   = sys_obj.N_total
    rho = sys_obj.rho
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    N_d = len(data_pos)

    # Constellation at data power used by the baseline receiver
    const_data = np.sqrt(1.0 - rho) * QPSK

    # Grid dimensions (for DNN features)
    K_factor, k_max, L_max, W, pad_size = sys_obj._get_2d_grid_params()
    input_dim = L_max * W * 2 + 4
    q_atoms = (sys_obj.l_max_cap + 1) * (2 * sys_obj.k_max_cap + 1)

    # Pre-allocate (fill frame by frame)
    X_feats       = np.empty((n_frames, input_dim),    dtype=np.float32)
    y_recv        = np.empty((n_frames, 2 * N),         dtype=np.float32)
    x_pilots      = np.empty((n_frames, 2 * N),         dtype=np.float32)
    x_data_true   = np.empty((n_frames, 2 * N),         dtype=np.float32)
    bits_true      = np.empty((n_frames, 2 * N),         dtype=np.float32)
    sigma_list     = np.empty((n_frames, 1),             dtype=np.float32)
    snr_db_list    = np.full((n_frames, 1), np.float32(snr_db), dtype=np.float32)
    mu_teacher     = np.empty((n_frames, 2 * N_d),       dtype=np.float32)
    var_teacher    = np.empty((n_frames, 2 * N_d),       dtype=np.float32)
    llr_teacher    = np.empty((n_frames, 2 * N_d),       dtype=np.float32)
    support_teacher_iter = np.empty((n_frames, n_outer, q_atoms), dtype=np.float32)
    seed_teacher_iter = np.empty((n_frames, n_outer, q_atoms), dtype=np.float32)
    gain_teacher_iter = np.empty((n_frames, n_outer, 2 * q_atoms), dtype=np.float32)
    mu_teacher_iter = np.empty((n_frames, n_outer, 2 * N_d), dtype=np.float32)
    var_teacher_iter = np.empty((n_frames, n_outer, 2 * N_d), dtype=np.float32)
    llr_teacher_iter = np.empty((n_frames, n_outer, 2 * N_d), dtype=np.float32)
    sigma_teacher_iter = np.empty((n_frames, n_outer, 1), dtype=np.float32)
    residual_teacher_iter = np.empty((n_frames, n_outer, 1), dtype=np.float32)
    iter_used_teacher = np.empty((n_frames, 1), dtype=np.int32)
    early_stop_teacher = np.empty((n_frames, 1), dtype=np.float32)
    if save_H:
        H_teacher  = np.empty((n_frames, 2 * N * N),    dtype=np.float32)

    std_X = float(sys_obj.global_std_X) if sys_obj.global_std_X else 1.0

    m0 = sys_obj._m0
    for i in range(n_frames):
        # ── Simulate one frame ──────────────────────────────────────────
        H_eff, H_time, _ = sys_obj.generate_channel_matrix(30.0, 'EVA')
        data_sym   = QPSK[np.random.randint(0, 4, N)]       # (N,) complex
        x_data_sc  = np.sqrt(1.0 - rho) * data_sym
        x_p_only   = np.zeros(N, dtype=complex)
        x_p_only[pilot_pos] = pilot_syms
        x_full     = x_data_sc + x_p_only

        s      = sys_obj.afdm_modulation(x_full)
        r, sw2 = sys_obj.add_awgn(H_time @ s, snr_db)
        y_daft = sys_obj.afdm_demodulation(r)

        # ── DNN features ────────────────────────────────────────────────
        feats = sys_obj.extract_dnn_features(y_daft, pilot_pos, pilot_syms, guard_pos)

        # Gray-coded bits
        bits_b0 = (np.real(data_sym) < 0).astype(np.float32)
        bits_b1 = (np.imag(data_sym) < 0).astype(np.float32)

        # ── Joint OMP+MP with soft return ────────────────────────────────
        x_pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
        x_soft, H_hat, mu_soft, var_soft, trajectory = joint_omp_mp_iterative(
            y_daft, x_pilot_scaled, N,
            sys_obj.c1, sys_obj.c2,
            sys_obj.l_max_cap, sys_obj.k_max_cap,
            sw2, const_data,
            n_paths=getattr(sys_obj, '_OMP_N_PATHS', 5),
            n_outer_iter=n_outer,
            rho=rho,
            pic_iter=pic_iter,
            pic_damp=pic_damp,
            mp_mode=mp_mode,
            return_soft=True,
            data_pos=data_pos,
            return_trajectory=True,
        )

        # ── Extract data-symbol teacher labels ────────────────────────────
        # mu_soft: (N,) complex   var_soft: (N,) float
        mu_d    = mu_soft[data_pos]     # (N_d,) complex
        var_d   = var_soft[data_pos]    # (N_d,) float  (per-symbol total var)

        # Split into per-component (real & imag) — for QPSK they're equal
        var_cmp = var_d / 2.0           # per-component variance

        # Store
        mu_teacher[i]  = np.concatenate([np.real(mu_d), np.imag(mu_d)])
        var_teacher[i] = np.concatenate([var_cmp, var_cmp])
        # LLR approximation: 2 * mean / var_per_component
        llr_r = 2.0 * np.real(mu_d) / np.maximum(var_cmp, 1e-10)
        llr_i = 2.0 * np.imag(mu_d) / np.maximum(var_cmp, 1e-10)
        llr_teacher[i] = np.concatenate([llr_r, llr_i])

        stages = trajectory["stages"]
        used = max(1, int(trajectory["iters_used"]))
        iter_used_teacher[i, 0] = used
        early_stop_teacher[i, 0] = 1.0 if trajectory["stopped_early"] else 0.0
        for t in range(n_outer):
            stage = stages[min(t, used - 1)]
            support_teacher_iter[i, t] = stage["support_mask"]
            seed_teacher_iter[i, t] = stage["seed_mask"]
            gain_c = stage["gain_dense"].astype(np.complex64)
            gain_teacher_iter[i, t] = np.concatenate([np.real(gain_c), np.imag(gain_c)]).astype(np.float32)
            mu_teacher_iter[i, t] = stage["mu_x"]
            var_teacher_iter[i, t] = stage["var_x"]
            llr_teacher_iter[i, t] = stage["llr_x"]
            sigma_teacher_iter[i, t, 0] = np.float32(stage["sigma2_eff"])
            residual_teacher_iter[i, t, 0] = np.float32(stage["residual_norm"])

        # ── Standard training data ────────────────────────────────────────
        X_feats[i]      = (feats / std_X).astype(np.float32)
        y_recv[i]       = np.concatenate([np.real(y_daft), np.imag(y_daft)]).astype(np.float32)
        x_pilots[i]     = np.concatenate([np.real(x_p_only), np.imag(x_p_only)]).astype(np.float32)
        x_data_true[i]  = np.concatenate([np.real(x_data_sc), np.imag(x_data_sc)]).astype(np.float32)
        bits_true[i]    = np.concatenate([bits_b0, bits_b1])
        sigma_list[i]   = np.float32(sw2)

        if save_H:
            H_teacher[i] = np.concatenate([np.real(H_hat).ravel(),
                                            np.imag(H_hat).ravel()]).astype(np.float32)

    out = dict(
        X_features    = X_feats,
        y_received    = y_recv,
        x_pilot_frames = x_pilots,
        x_data_true   = x_data_true,
        bits_true     = bits_true,
        sigma_w2      = sigma_list,
        snr_db        = snr_db_list,
        data_positions = data_pos.astype(np.int32),
        mu_x_teacher  = mu_teacher,
        var_x_teacher  = var_teacher,
        llr_teacher   = llr_teacher,
        support_teacher_iter = support_teacher_iter,
        seed_teacher_iter = seed_teacher_iter,
        gain_teacher_iter = gain_teacher_iter,
        mu_x_teacher_iter = mu_teacher_iter,
        var_x_teacher_iter = var_teacher_iter,
        llr_teacher_iter = llr_teacher_iter,
        sigma_teacher_iter = sigma_teacher_iter,
        residual_teacher_iter = residual_teacher_iter,
        iter_used_teacher = iter_used_teacher,
        early_stop_teacher = early_stop_teacher,
    )
    if save_H:
        out['H_teacher'] = H_teacher
    return out


# ──────────────────────────────────────────────────────────────────────────────
#  Entry point
# ──────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out-dir', type=str, default='teacher_labels',
                   help='Output directory for NPZ files. Default: teacher_labels/')
    p.add_argument('--snr-list', type=float, nargs='+', default=[5, 10, 15, 20],
                   help='SNR values in dB. Default: 5 10 15 20')
    p.add_argument('--frames-per-snr', type=int, default=1000,
                   help='Number of frames per SNR point. Default: 1000')
    p.add_argument('--mp-mode', choices=['bp', 'pic'], default='bp',
                   help='MP detector mode. Default: bp')
    p.add_argument('--n-outer', type=int, default=5,
                   help='Number of outer CE+detection iterations. Default: 5')
    p.add_argument('--rho', type=float, default=0.5, help='Pilot power ratio. Default: 0.5')
    p.add_argument('--save-H', action='store_true',
                   help='Also save (N×N) channel matrices (large!). Default: off')
    p.add_argument('--seed', type=int, default=42, help='NumPy random seed. Default: 42')
    return p


def main():
    args = _build_parser().parse_args()

    np.random.seed(args.seed)
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sys_obj = AFDMSystem(N=16, M=32, rho=args.rho)
    # global_std_X defaults to 1.0 when not set (features not normalised by stats)
    # To reproduce training normalisation, load stats:
    stats_path = pathlib.Path(__file__).parent / 'outputs_n512' / 'global_stats.pkl'
    if stats_path.exists():
        import pickle
        with open(stats_path, 'rb') as f:
            stats = pickle.load(f)
        sys_obj.global_std_X = stats['std_X']
        sys_obj.global_std_y = stats['std_y']
        print(f"  Loaded global stats from {stats_path}")
    else:
        print(f"  global_stats.pkl not found at {stats_path}  — features stored unnormalised.")

    print(f"\n  Generating teacher labels")
    print(f"  SNRs      : {args.snr_list}")
    print(f"  Frames/SNR: {args.frames_per_snr}")
    print(f"  MP mode   : {args.mp_mode}")
    print(f"  Out dir   : {out_dir}\n")

    all_batches: list[dict] = []

    for snr_db in args.snr_list:
        t0 = time.time()
        print(f"  Processing SNR={snr_db}dB ...", flush=True)
        batch = generate_for_snr(
            sys_obj,
            snr_db       = snr_db,
            n_frames     = args.frames_per_snr,
            mp_mode      = args.mp_mode,
            save_H       = args.save_H,
            n_outer      = args.n_outer,
        )
        elapsed = time.time() - t0

        # Quick sanity: teacher variance should be positive
        assert np.all(batch['var_x_teacher'] >= 0), "negative teacher variance!"

        # Save per-SNR file
        fname = out_dir / f'teacher_snr{int(snr_db):02d}dB.npz'
        np.savez_compressed(str(fname), **batch)
        print(f"  SNR={snr_db}dB  saved → {fname}  ({elapsed:.1f}s)", flush=True)

        # Diagnostics
        mu_p = batch['mu_x_teacher'][:, :sys_obj.N_total]   # real part for data symbols
        vx_p = batch['var_x_teacher'][:, :sys_obj.N_total]
        print(f"    mu_teacher mean/std : {float(np.mean(mu_p)):.4f} / {float(np.std(mu_p)):.4f}")
        print(f"    var_teacher mean    : {float(np.mean(vx_p)):.6f}  "
              f"(approx NMSE floor = {float(np.mean(vx_p)):.4e})", flush=True)

        all_batches.append(batch)

    # ── Concatenate all SNR batches into a single training file ────────────
    combined = {k: np.concatenate([b[k] for b in all_batches], axis=0)
                for k in all_batches[0].keys() if k != 'data_positions'}
    combined['data_positions'] = all_batches[0]['data_positions']

    combined_path = out_dir / 'teacher_all_snr_traj.npz'
    np.savez_compressed(str(combined_path), **combined)
    print(f"\n  Combined dataset → {combined_path}")
    print(f"  Total frames : {combined['X_features'].shape[0]}")
    print(f"\n  DONE ✓")


if __name__ == '__main__':
    main()
