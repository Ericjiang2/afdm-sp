"""
run_classical_baselines_python.py

Run LS+MMSE, OMP+MMSE, OMP+MP, and Joint OMP-MP classical baselines on the
canonical Python UWA configuration (P_paths=10, fixed-noise, ZC pilot). Also
records channel-estimation NMSE and joint-receiver iteration-convergence BER
history. All outputs are per-SNR mean/std across frames, dumped to JSON for
paper-figure generation.

The pipeline mirrors matlab/AFDM_UWA_acoustic.m but runs entirely in Python so
the paper figures are reproducible from the current Python code base.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from afdm_sp_joint_unrolled.afdm_baselines import (
    construct_sensing_matrix,
    construct_sensing_matrix_matlab,
    extract_delay_doppler_from_h,
    joint_omp_mp_iterative,
    mp_detect_bp,
    mp_detect_pic,
    omp_sparse,
    reconstruct_H_from_omp,
    reconstruct_H_from_omp_matlab,
)
from afdm_sp_joint_unrolled.verify_oamp import _make_system, _sync_l_max_cap
from afdm_sp_joint_unrolled.prepare_teacher_sparse import AFDMSystem


def _make_system_variable_N(n_total: int, rho: float = 0.5):
    """
    Build an AFDMSystem with a non-default frame length (256 / 128).

    The caps l_max_cap and k_max_cap are rescaled so that the delay-Doppler
    dictionary δ_max = k_max + (2 k_max + 1) · l_max stays well inside N.
    UWA delay support at f_s = 8 kHz and τ_spread = 10 ms would call for
    l_max ≈ 80 samples, but the exponential-decay channel concentrates
    >99 % of its energy inside ≈ 25 delay bins, so l_max_cap ≈ N/10
    retains the full diversity while keeping δ_max ≪ N.

    ``rho`` is the SP pilot/data power split (default 0.5 — canonical).
    Step 3 ablation E sweeps rho ∈ {0.3..0.7}.
    """
    if n_total % 32 == 0:
        N_d, M_d = n_total // 32, 32
    elif n_total % 16 == 0:
        N_d, M_d = n_total // 16, 16
    else:
        N_d, M_d = 1, n_total
    sys_obj = AFDMSystem(N=N_d, M=M_d, rho=float(rho))
    # Rescale the dictionary caps.  Keep δ_max ≤ 0.5·N so OMP stays well-posed.
    new_lmax = max(int(n_total // 10), 12)          # 256→25, 128→12
    sys_obj.l_max_cap = new_lmax
    # k_max_cap is the integer-Doppler HALF-WIDTH. MATLAB computes it as
    # ceil(N · D_max) where D_max = v_max · fc / (c_sound · fs). Fixing it at 2
    # over-dimensions the OMP dictionary for short frames (e.g. at N=128 with
    # v_max ≈ 2.5 m/s the physical |k| ≤ 1, so k_max=2 adds a whole ring of
    # spurious columns that OMP can still pick up under noise — that is the
    # leading cause of the huge Pact and the BER blow-up we observed at N=128).
    v_max_ms = float(getattr(sys_obj, "v_mean", 2.0)) + 3.0 * float(getattr(sys_obj, "v_std", 0.5))
    d_max_norm = v_max_ms * float(sys_obj.fc) / (float(sys_obj.c_sound) * float(sys_obj.fs))
    sys_obj.k_max_cap = max(int(np.ceil(sys_obj.N_total * d_max_norm)), 1)
    K_factor = 2 * sys_obj.k_max_cap + 1
    sys_obj.delta_max = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
    sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
    sys_obj.max_delay_idx_bar_supported = (
        int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1)
    sys_obj.use_frac_doppler = True
    sys_obj.k_leak = 2
    sys_obj.frac_prune_rel_thres = 0.01
    # Rebuild DAFT matrices — chirp params c1, c2 depend on N_total.
    sys_obj._set_chirp_parameters(sys_obj.k_max_cap)
    sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()
    # Rebuild ZC pilot for the new N_total.
    _r = 7
    _n = np.arange(sys_obj.N_total)
    sys_obj._zc_seq = np.exp(-1j * np.pi * _r * _n**2 / sys_obj.N_total)
    sys_obj._W_match = sys_obj._build_zc_correlation_matrix()
    print(f"[_make_system_variable_N] N_total={sys_obj.N_total}  l_max={sys_obj.l_max_cap}  "
          f"k_max={sys_obj.k_max_cap}  δ_max={sys_obj.delta_max}  "
          f"< N: {sys_obj.delta_max < sys_obj.N_total}  "
          f"c1={sys_obj.c1:.6f}  c2={sys_obj.c2:.2e}")
    return sys_obj


QPSK = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2)


def _bits_of_symbol(s: np.ndarray, n_data: int) -> np.ndarray:
    """QPSK gray demod: bit_real = real<0, bit_imag = imag<0."""
    b = np.zeros(2 * n_data, dtype=np.float32)
    b[:n_data] = (s.real < 0).astype(np.float32)
    b[n_data:] = (s.imag < 0).astype(np.float32)
    return b


def _ber(bits_pred: np.ndarray, bits_true: np.ndarray) -> float:
    return float(np.mean(bits_pred != bits_true))


def _nmse(H_est: np.ndarray, H_true: np.ndarray) -> float:
    num = np.linalg.norm(H_est - H_true, 'fro') ** 2
    den = np.linalg.norm(H_true, 'fro') ** 2 + 1e-30
    return float(num / den)


def _mmse_equalize(H: np.ndarray, y: np.ndarray, sigma2: float, P_d: float) -> np.ndarray:
    """MMSE equalization: W = (H^H H + sigma2/P_d I)^{-1} H^H."""
    N = H.shape[0]
    HtH = H.conj().T @ H
    reg = (sigma2 / P_d) * np.eye(N)
    W = np.linalg.solve(HtH + reg, H.conj().T)
    return W @ y


def _ls_channel_estimate(y: np.ndarray, Phi_scaled: np.ndarray, lam: float) -> np.ndarray:
    """Ridge-regularised LS channel estimate h = (Phi^H Phi + lam I)^{-1} Phi^H y."""
    Q = Phi_scaled.shape[1]
    AhA = Phi_scaled.conj().T @ Phi_scaled
    Ahy = Phi_scaled.conj().T @ y
    h = np.linalg.solve(AhA + lam * np.eye(Q), Ahy)
    return h


def _reconstruct_H_full(sys_obj, h_sparse: np.ndarray, convention: str = "python"):
    if convention == "matlab":
        return reconstruct_H_from_omp_matlab(
            sys_obj.N_total, h_sparse, sys_obj.k_max_cap, sys_obj.l_max_cap, sys_obj.c1,
            threshold=0.0,
        )
    return reconstruct_H_from_omp(
        sys_obj.N_total, h_sparse, sys_obj.k_max_cap, sys_obj.l_max_cap,
        sys_obj.c1, sys_obj.c2, threshold=0.0,
    )


def _joint_trajectory_ber(trajectory, bits_true, data_pos, n_data):
    """Return per-outer-iteration BER given trajectory["stages"]."""
    stages = trajectory["stages"]
    rows = []
    for t, stage in enumerate(stages):
        mu_x = stage["mu_x"]
        n_bits = mu_x.size // 2
        mu_complex = mu_x[:n_bits] + 1j * mu_x[n_bits:]
        bits_pred = np.zeros(2 * n_bits, dtype=np.float32)
        bits_pred[:n_bits] = (mu_complex.real < 0).astype(np.float32)
        bits_pred[n_bits:] = (mu_complex.imag < 0).astype(np.float32)
        rows.append(_ber(bits_pred, bits_true[:2 * n_bits]))
    return rows


def _run_one_frame(
    sys_obj,
    snr_db: int,
    pilot_scaled: np.ndarray,
    data_pos: np.ndarray,
    data_pos_len: int,
    sparsity_omp: int,
    n_outer_iter_joint: int,
    pic_iter: int,
    rng: np.random.Generator,
    sparsity_mode: str = "fixed",
) -> Dict:
    """Run all classical baselines on a freshly generated channel + frame."""
    N = sys_obj.N_total
    rho = float(sys_obj.rho)
    P_d = 1.0 - rho

    # --- Ground-truth channel + data + y ---------------------------------- #
    H_eff_true, _, _ = sys_obj.generate_channel_matrix()
    # After Dirichlet expansion the channel may have >P_paths virtual taps.
    # MATLAB ls_extract_count = P_actual; we mirror that here when requested.
    p_actual = int(getattr(sys_obj, "_P_actual", sys_obj.P_paths))
    sparsity_effective = int(p_actual) if sparsity_mode == "p_actual" else int(sparsity_omp)
    # Lower-bound sparsity at P_paths (OMP needs enough room for the physical
    # paths even when Dirichlet pruning shrinks virtual count below P_paths).
    sparsity_effective = max(sparsity_effective, int(sys_obj.P_paths))

    # Data & pilot symbols
    data_idx = rng.integers(0, 4, size=data_pos_len)
    data_qam = QPSK[data_idx]
    # Bits (QPSK Gray): real_bit = (real<0), imag_bit = (imag<0)
    bits_true = np.zeros(2 * data_pos_len, dtype=np.float32)
    bits_true[:data_pos_len] = (data_qam.real < 0).astype(np.float32)
    bits_true[data_pos_len:] = (data_qam.imag < 0).astype(np.float32)

    # Construct SP frame at data positions only (other positions = 0)
    x_data_full = np.zeros(N, dtype=complex)
    x_data_full[data_pos] = data_qam
    x_data_scaled = np.sqrt(P_d) * x_data_full  # data at sqrt(P_d)
    x_sp = pilot_scaled + x_data_scaled

    # Receive
    y_daft = H_eff_true @ x_sp

    # AWGN: use 'fixed' reference (matching Round 8)
    noise = (rng.standard_normal(N) + 1j * rng.standard_normal(N)) / np.sqrt(2.0)
    sigma2 = 1.0 / (10 ** (snr_db / 10.0))  # fixed-noise convention (pilot+data signal power = 1)
    y_daft = y_daft + np.sqrt(sigma2) * noise

    # --- Sensing matrix (pilot-based) ------------------------------------- #
    convention = getattr(sys_obj, 'baseline_phase_convention', 'python')
    if convention == 'matlab':
        Phi = construct_sensing_matrix_matlab(
            N, pilot_scaled, sys_obj.c1,
            sys_obj.l_max_cap, sys_obj.k_max_cap,
        )
    else:
        Phi = construct_sensing_matrix(
            N, pilot_scaled, sys_obj.c1, sys_obj.c2,
            sys_obj.l_max_cap, sys_obj.k_max_cap,
        )  # already scaled by pilot amplitude through x_pilot_scaled

    # Diagnostic bookkeeping for this frame: the actual virtual-tap count and
    # the OMP sparsity we decided to use.
    diag = {"p_actual": int(p_actual), "sparsity_effective": int(sparsity_effective)}

    # ==================================================================== #
    # 1. LS + MMSE                                                         #
    # ==================================================================== #
    # Tikhonov factor must account for *both* thermal noise and the
    # superimposed-data interference seen by the pilot-only sensing matrix.
    # MATLAB ridge = 1e-2·σ²·N_data; with SP ρ=0.5 the data term injects
    # additional P_d = 1-ρ of interference, so the effective noise floor is
    # σ² + P_d. Ignoring P_d under-regularises LS at high SNR and floods the
    # channel estimate with data-interference leakage (visible as ~12% BER
    # floor for LS+MMSE / OMP+MMSE in the old numbers).
    lam = 1e-2 * (sigma2 + P_d) * N
    h_ls_full = _ls_channel_estimate(y_daft, Phi, lam)
    # Extract top-P_effective taps (MATLAB AFDM_UWA_acoustic.m uses P_actual
    # after Dirichlet expansion; we mirror that).
    delays_ls, dopplers_ls, gains_ls = extract_delay_doppler_from_h(
        h_ls_full, sparsity_effective, sys_obj.l_max_cap, sys_obj.k_max_cap,
    )
    # Rebuild a sparse Q-vector and reconstruct H
    K = 2 * sys_obj.k_max_cap + 1
    h_ls = np.zeros((sys_obj.l_max_cap + 1) * K, dtype=complex)
    for (l_p, k_p, g) in zip(delays_ls, dopplers_ls, gains_ls):
        h_ls[int(l_p) * K + (int(k_p) + sys_obj.k_max_cap)] = g
    H_ls = _reconstruct_H_full(sys_obj, h_ls, convention=convention)
    y_data_ls = y_daft - H_ls @ pilot_scaled
    x_eq_ls = _mmse_equalize(H_ls, y_data_ls, sigma2, P_d) / np.sqrt(P_d)
    ber_ls_mmse = _ber(_bits_of_symbol(x_eq_ls[data_pos], data_pos_len), bits_true)
    nmse_ls = _nmse(H_ls, H_eff_true)

    # ==================================================================== #
    # 2. OMP + MMSE                                                         #
    # ==================================================================== #
    h_omp, _ = omp_sparse(y_daft, Phi, sparsity_effective)
    H_omp = _reconstruct_H_full(sys_obj, h_omp, convention=convention)
    y_data_omp = y_daft - H_omp @ pilot_scaled
    x_eq_omp_mmse = _mmse_equalize(H_omp, y_data_omp, sigma2, P_d) / np.sqrt(P_d)
    ber_omp_mmse = _ber(_bits_of_symbol(x_eq_omp_mmse[data_pos], data_pos_len), bits_true)
    nmse_omp = _nmse(H_omp, H_eff_true)

    # ==================================================================== #
    # 3. OMP + MP (BP)                                                      #
    # ==================================================================== #
    const_data = np.sqrt(P_d) * QPSK
    x_mp = mp_detect_bp(
        y_data_omp, H_omp, sigma2, const_data,
        n_iter=pic_iter, threshold=1e-4, damp=0.5,
    )
    x_mp_norm = x_mp / np.sqrt(P_d)
    ber_omp_mp = _ber(_bits_of_symbol(x_mp_norm[data_pos], data_pos_len), bits_true)

    # ==================================================================== #
    # 4. Joint OMP-MP (iterative)                                           #
    # ==================================================================== #
    x_soft, H_joint, traj = joint_omp_mp_iterative(
        y_daft, pilot_scaled, N,
        sys_obj.c1, sys_obj.c2,
        sys_obj.l_max_cap, sys_obj.k_max_cap,
        sigma2, const_data,
        n_paths=sparsity_effective,
        n_outer_iter=n_outer_iter_joint,
        rho=rho,
        pic_iter=pic_iter,
        pic_damp=0.5,
        mp_mode='bp',
        phase_convention=convention,
        return_soft=False,
        return_trajectory=True,
        data_pos=data_pos,
    )
    # joint_omp_mp_iterative returns (x_soft, H_hat, trajectory)
    x_soft_norm = x_soft / np.sqrt(P_d)
    ber_joint = _ber(_bits_of_symbol(x_soft_norm[data_pos], data_pos_len), bits_true)
    nmse_joint = _nmse(H_joint, H_eff_true)
    joint_iter_ber = _joint_trajectory_ber(traj, bits_true, data_pos, data_pos_len)

    # ==================================================================== #
    # 5. Perfect CSI + MMSE (lower bound)                                   #
    # ==================================================================== #
    y_data_perfect = y_daft - H_eff_true @ pilot_scaled
    x_eq_pcsi = _mmse_equalize(H_eff_true, y_data_perfect, sigma2, P_d) / np.sqrt(P_d)
    ber_pcsi = _ber(_bits_of_symbol(x_eq_pcsi[data_pos], data_pos_len), bits_true)

    return {
        "ber": {
            "perfect_csi_mmse": ber_pcsi,
            "ls_mmse": ber_ls_mmse,
            "omp_mmse": ber_omp_mmse,
            "omp_mp": ber_omp_mp,
            "joint_omp_mp": ber_joint,
        },
        "nmse": {
            "ls": nmse_ls,
            "omp": nmse_omp,
            "joint": nmse_joint,
        },
        "joint_iter_ber": joint_iter_ber,
        "diag": diag,
    }


def main():
    parser = argparse.ArgumentParser()
    here = pathlib.Path(__file__).parent
    parser.add_argument("--out-dir", type=str,
                        default=str(here / "outputs_classical_baselines_python"))
    parser.add_argument("--snr-list", nargs="+", type=int,
                        default=[5, 10, 15, 20, 25])
    parser.add_argument("--frames-per-snr", type=int, default=100,
                        help="Monte-Carlo frames per SNR. Old runs used 15 which "
                             "gave ~8 errors at BER=1e-3 (too noisy). 100 frames "
                             "× 2·512 bits ≈ 1e5 bits → ~100 errors at BER=1e-3.")
    parser.add_argument("--min-error-bits", type=int, default=200,
                        help="Adaptive early-stop once at least this many error "
                             "bits have accumulated (per SNR, based on joint receiver).")
    parser.add_argument("--min-frames", type=int, default=20,
                        help="Minimum frames per SNR before early-stop is allowed.")
    parser.add_argument("--seed", type=int, default=7777)
    parser.add_argument("--sparsity-omp", type=int, default=10)
    # User directive: keep the Python joint receiver at T=5 outer iterations
    # (the iteration-convergence curve is informative up to T=5; we want the
    # extra two passes to see whether the 25 dB floor continues to drop past
    # T=3). Inner BP iterations match MATLAB at 20.
    parser.add_argument("--n-outer-iter-joint", type=int, default=5)
    parser.add_argument("--pic-iter", type=int, default=20)
    parser.add_argument("--sparsity-mode", type=str, default="p_actual",
                        choices=["fixed", "p_actual"],
                        help="'fixed' uses --sparsity-omp; 'p_actual' uses the "
                             "dynamic virtual-tap count produced by the Dirichlet "
                             "expansion (mirrors MATLAB ls_extract_count = P_actual).")
    parser.add_argument("--n-total", type=int, default=0,
                        help="Override AFDM frame length N_total. 0 = default (=512). "
                             "Set 256 or 128 to test shorter frames; l_max_cap and "
                             "k_max_cap are auto-rescaled so δ_max stays well inside N.")
    parser.add_argument("--convention", type=str, default="python",
                        choices=["python", "matlab"],
                        help="Phase/index convention used for the entire pipeline: "
                             "channel matrix construction, OMP sensing matrix and the "
                             "joint-receiver H reconstruction. MATLAB convention uses "
                             "c2 = 0 and +c1·l² phase (mirrors AFDM_UWA_acoustic.m).")
    args = parser.parse_args()

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sys_obj = _make_system_variable_N(args.n_total) if args.n_total else _make_system()
    if not args.n_total:
        sys_obj = _sync_l_max_cap(sys_obj, here / "outputs_joint_unrolled")
    # Canonical Python UWA config: P_paths = 10 (user directive, matches MATLAB AFDM_UWA_acoustic.m)
    sys_obj.P_paths = 10

    # Apply convention end-to-end. MATLAB convention uses c2 = 0 and +c1·l² phase;
    # Python convention uses c2 ≠ 0 and -c1·l² phase. Both are internally consistent
    # but the OMP dictionary has different coherence / numerical behaviour.
    sys_obj.gen_h_daft_convention = args.convention
    sys_obj.baseline_phase_convention = args.convention
    if args.convention == "matlab":
        sys_obj.c2 = 0.0
        sys_obj._A, sys_obj._A_H = sys_obj.build_daft_matrix()  # rebuild with c2=0
        print(f"[convention=matlab] c1={sys_obj.c1:.6f}  c2={sys_obj.c2:.6f} (zeroed)")
    else:
        print(f"[convention=python] c1={sys_obj.c1:.6f}  c2={sys_obj.c2:.2e}")

    # Canonical pilot template (constant across frames, ZC sequence)
    rho = float(sys_obj.rho)
    pilot_scaled = np.sqrt(rho) * sys_obj._zc_seq
    _, pilot_pos, pilot_syms, guard_pos, data_pos = sys_obj.generate_pilot_frame()
    data_pos = np.asarray(data_pos, dtype=np.int64)
    data_pos_len = int(len(data_pos))

    print(f"[config] N_total={sys_obj.N_total}  P_paths={sys_obj.P_paths}  rho={rho:.2f}  "
          f"l_max={sys_obj.l_max_cap}  k_max={sys_obj.k_max_cap}  n_data={data_pos_len}")

    rng_master = np.random.default_rng(args.seed)

    results_per_frame = []
    start_t = time.time()
    for snr in args.snr_list:
        err_bits_joint = 0
        frames_done_this_snr = 0
        for fi in range(args.frames_per_snr):
            # Per-frame RNG for channel + noise reproducibility
            seed_fi = int(rng_master.integers(0, 2 ** 31))
            rng = np.random.default_rng(seed_fi)
            np.random.seed(seed_fi)  # legacy global state for channel generation
            row = _run_one_frame(
                sys_obj,
                snr_db=snr,
                pilot_scaled=pilot_scaled,
                data_pos=data_pos,
                data_pos_len=data_pos_len,
                sparsity_omp=args.sparsity_omp,
                n_outer_iter_joint=args.n_outer_iter_joint,
                pic_iter=args.pic_iter,
                rng=rng,
                sparsity_mode=args.sparsity_mode,
            )
            row["snr_db"] = int(snr)
            row["frame_idx"] = int(fi)
            results_per_frame.append(row)
            frames_done_this_snr += 1
            err_bits_joint += int(round(row["ber"]["joint_omp_mp"] * (2 * data_pos_len)))
            elapsed = time.time() - start_t
            total = len(args.snr_list) * args.frames_per_snr
            done = len(results_per_frame)
            eta = elapsed * (total - done) / max(done, 1)
            print(f"[snr={snr:>2} dB fi={fi:>2}/{args.frames_per_snr}] "
                  f"ber_pcsi={row['ber']['perfect_csi_mmse']:.3e} "
                  f"ber_lsmmse={row['ber']['ls_mmse']:.3e} "
                  f"ber_ompmmse={row['ber']['omp_mmse']:.3e} "
                  f"ber_ompmp={row['ber']['omp_mp']:.3e} "
                  f"ber_joint={row['ber']['joint_omp_mp']:.3e} "
                  f"Pact={row['diag']['p_actual']:>2} "
                  f"[{elapsed:.1f}s elapsed, {eta:.1f}s eta]", flush=True)
            # Adaptive early stop: once we have enough errors on the joint
            # receiver (the slowest-to-accumulate at high SNR) the BER is
            # statistically reliable; further frames are compute waste.
            if (frames_done_this_snr >= args.min_frames
                    and err_bits_joint >= args.min_error_bits):
                print(f"  [adaptive stop] SNR={snr}dB after {frames_done_this_snr} "
                      f"frames, {err_bits_joint} joint error bits "
                      f"(>= --min-error-bits {args.min_error_bits}).", flush=True)
                break

    # --- Aggregate ------------------------------------------------------- #
    methods_ber = ["perfect_csi_mmse", "ls_mmse", "omp_mmse", "omp_mp", "joint_omp_mp"]
    methods_nmse = ["ls", "omp", "joint"]

    agg_ber = {m: {} for m in methods_ber}
    agg_nmse = {m: {} for m in methods_nmse}
    agg_iter_ber = {}
    for snr in args.snr_list:
        rows = [r for r in results_per_frame if r["snr_db"] == snr]
        for m in methods_ber:
            vals = [r["ber"][m] for r in rows]
            agg_ber[m][int(snr)] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "n": len(vals),
            }
        for m in methods_nmse:
            vals = [r["nmse"][m] for r in rows]
            agg_nmse[m][int(snr)] = {
                "mean": float(np.mean(vals)),
                "std": float(np.std(vals)),
                "n": len(vals),
            }
        # Joint iteration history — pad with last value to handle early-stop
        max_iters = max(len(r["joint_iter_ber"]) for r in rows)
        padded = []
        for r in rows:
            arr = list(r["joint_iter_ber"])
            if len(arr) < max_iters:
                arr = arr + [arr[-1]] * (max_iters - len(arr))
            padded.append(arr)
        iter_bers = np.asarray(padded, dtype=np.float64)
        agg_iter_ber[int(snr)] = {
            "iter_mean": iter_bers.mean(axis=0).tolist(),
            "iter_std": iter_bers.std(axis=0).tolist(),
            "n": iter_bers.shape[0],
        }

    summary = {
        "config": {
            "N_total": int(sys_obj.N_total),
            "P_paths": int(sys_obj.P_paths),
            "rho": rho,
            "l_max_cap": int(sys_obj.l_max_cap),
            "k_max_cap": int(sys_obj.k_max_cap),
            "snr_list": args.snr_list,
            "frames_per_snr_cap": int(args.frames_per_snr),
            "min_error_bits": int(args.min_error_bits),
            "min_frames": int(args.min_frames),
            "sparsity_omp": int(args.sparsity_omp),
            "n_outer_iter_joint": int(args.n_outer_iter_joint),
            "pic_iter": int(args.pic_iter),
            "ls_reg_includes_data_interference": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "per_snr_ber": agg_ber,
        "per_snr_nmse": agg_nmse,
        "per_snr_joint_iter_ber": agg_iter_ber,
    }
    out_json = out_dir / "classical_baselines_python_results.json"
    out_json.write_text(json.dumps(summary, indent=2, default=float))
    print(f"\nWrote {out_json}")

    # Markdown summary.
    md = ["# Classical Baselines — Python (UWA P_paths=10)", ""]
    md.append(f"- frames/SNR cap: {args.frames_per_snr}  |  "
              f"adaptive early-stop: {args.min_error_bits} joint-err bits, "
              f"min {args.min_frames} frames  |  sparsity_omp: {args.sparsity_omp}  |  "
              f"n_outer_iter_joint: {args.n_outer_iter_joint}  |  pic_iter: {args.pic_iter}  |  "
              f"LS λ includes P_data: True")
    md.append("")
    md.append("## BER vs SNR (mean ± std)")
    md.append("| SNR | PerfectCSI+MMSE | LS+MMSE | OMP+MMSE | OMP+MP | Joint OMP-MP |")
    md.append("|---:|---:|---:|---:|---:|---:|")
    for snr in args.snr_list:
        row = [f"{snr} dB"]
        for m in methods_ber:
            r = agg_ber[m][int(snr)]
            row.append(f"{r['mean']:.3e} ± {r['std']:.2e}")
        md.append("| " + " | ".join(row) + " |")
    md.append("")
    md.append("## Channel-estimation NMSE (dB, mean)")
    md.append("| SNR | LS | OMP | Joint |")
    md.append("|---:|---:|---:|---:|")
    for snr in args.snr_list:
        r_ls = agg_nmse["ls"][int(snr)]["mean"]
        r_omp = agg_nmse["omp"][int(snr)]["mean"]
        r_joint = agg_nmse["joint"][int(snr)]["mean"]
        md.append(f"| {snr} dB | {10*np.log10(r_ls+1e-30):.2f} | "
                  f"{10*np.log10(r_omp+1e-30):.2f} | "
                  f"{10*np.log10(r_joint+1e-30):.2f} |")
    md.append("")
    md.append("## Joint OMP-MP iteration-convergence BER")
    md.append("| SNR | iter 1 | iter 2 | iter 3 | iter 4 | iter 5 |")
    md.append("|---:|---:|---:|---:|---:|---:|")
    for snr in args.snr_list:
        mi = agg_iter_ber[int(snr)]["iter_mean"]
        md.append(f"| {snr} dB | " + " | ".join(f"{v:.3e}" for v in mi) + " |")
    (out_dir / "classical_baselines_python_results.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
