"""Controlled MATLAB-match baseline runner for AFDM SP UWA.

This script is for step-by-step ablations against MATLAB `AFDM_UWA_acoustic.m`.
It keeps `N=100` for speed, but flips the highest-suspicion differences:
  1. random QPSK pilot instead of ZC
  2. MATLAB `GEN_H_DAFT` / sensing convention (`+c1*l^2`, `c2=0`)
  3. `P_paths=5` test-mode channel
  4. OMP sparsity = `P_actual`
  5. full BP detector instead of PIC

N_total can be set via `N_total` param:
  - N=100  (10x10)  : default, fast
  - N=256  (16x16)  : closer to MATLAB (c1 ≈ MATLAB/4), controlled-variable test
  - N=1024 (32x32)  : matches MATLAB N exactly (slow)
"""
import math
import numpy as np
import pathlib
import sys

_HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

from afdm_sp_joint_unrolled.run_sp_unfolding import AFDMSystem
from afdm_sp_joint_unrolled.afdm_baselines import mp_detect_bp


QPSK = np.array([1 + 1j, 1 - 1j, -1 + 1j, -1 - 1j], dtype=complex) / np.sqrt(2)
SNR_LIST = [5, 10, 15, 20]
FRAMES_BY_SNR = {5: 10, 10: 10, 15: 10, 20: 50}
N_OUTER = 5
NUM_ITER_MP = 20
THRESHOLD_MP = 1e-4


# ---------------------------------------------------------------------------
# l_max_cap formula: max delay in DAFT bins = l_phys_max * N * delta_f / fs
# For P=5 UWA paths, tau_mean=0.8ms: max physical sample delay ≈ 32-50 samples.
# Use l_phys_safe=50 (conservative) to cover 99%+ of realizations.
# Precomputed: ceil(50 * N * 15 / 8000 / 5) * 5
# N=100  → 50*1500/8000 = 9.4  → l_max_cap=15  (default; formula gives 15)
# N=256  → 50*3840/8000 = 24.0 → l_max_cap=25  Q=130 N/Q=2.0x
# N=1024 → 50*15360/8000 = 96  → l_max_cap=100 Q=505 N/Q=2.0x
# (Can override with l_max_cap_override= for tighter or looser control)
# ---------------------------------------------------------------------------


def _make_system(n_total: int, rho: float, l_max_cap_override: int = None) -> AFDMSystem:
    """Create AFDMSystem with side=sqrt(N_total) and fix l_max_cap accordingly.

    For each N_total the delay resolution is 1/(N*delta_f) seconds/bin.
    l_max_cap must cover the maximum expected physical delay expressed in DAFT bins:
      l_max_cap = round_up(max_physical_samples * Ts / delay_resolution)
               = round_up(max_physical_samples * Ts * N * delta_f)
    For UWA with P=5 paths, tau_mean=0.8ms, fs=8kHz:
      max physical samples ≈ 5 * 0.8ms/0.125ms = 32 samples
      N=100  → l_max_cap = round_up(32 * 0.125ms * 1500) = 6  (dict uses auto-default 15, fine)
      N=256  → l_max_cap = round_up(32 * 0.125ms * 3840) = 15 (overshoots but OK)
      N=1024 → l_max_cap = round_up(32 * 0.125ms * 15360) = 62 → use 80 for margin
    """
    side = int(round(math.sqrt(n_total)))
    assert side * side == n_total, f"N_total={n_total} must be a perfect square"
    sys_obj = AFDMSystem(N=side, M=side, rho=rho)
    if n_total != 100 or l_max_cap_override is not None:
        # Compute l_max_cap in DAFT bins to cover max_physical_delay
        if l_max_cap_override is not None:
            new_lmax = l_max_cap_override
        else:
            # l_DAFT_max = ceil(l_phys_max * N * delta_f / fs)
            # = max physical delay expressed in DAFT bins
            # (inverse of: delay_seconds / delay_resolution
            #   = l_phys * Ts / (1/(N*delta_f)) = l_phys * N * delta_f / fs)
            l_phys_safe = 50
            delta_f = sys_obj.delta_f
            fs = sys_obj.fs
            new_lmax = int(math.ceil(l_phys_safe * n_total * delta_f / fs / 5.0)) * 5
            new_lmax = max(new_lmax, 15)  # never less than 15 for backward compat
        sys_obj.l_max_cap = new_lmax
        sys_obj.k_max_cap = sys_obj.k_max_default   # k_max stays 2
        K_factor = 2 * sys_obj.k_max_cap + 1
        sys_obj.delta_max = sys_obj.k_max_cap + K_factor * sys_obj.l_max_cap
        sys_obj.max_delay_supported_s = sys_obj.l_max_cap * sys_obj.delay_resolution
        sys_obj.max_delay_idx_bar_supported = (
            int(np.floor(sys_obj.max_delay_supported_s / sys_obj.Ts)) + 1
        )
        Q = (2 * sys_obj.k_max_cap + 1) * (sys_obj.l_max_cap + 1)
        print(f"  [N={n_total}] l_max_cap={sys_obj.l_max_cap}, "
              f"Q={Q}, N/Q={n_total/Q:.2f}x, "
              f"max_phys_delay_supported={sys_obj.max_delay_idx_bar_supported-1} samples, "
              f"delta_max={sys_obj.delta_max} ({'OK' if sys_obj.delta_max < n_total else 'FAIL'}), "
              f"c1={sys_obj.c1:.6f}")
    return sys_obj


def ber_qpsk(x_true, x_det):
    err_i = float(np.mean((np.real(x_true) > 0) != (np.real(x_det) > 0)))
    err_q = float(np.mean((np.imag(x_true) > 0) != (np.imag(x_det) > 0)))
    return 0.5 * (err_i + err_q)


def nmse(H_true, H_est):
    return float(np.linalg.norm(H_true - H_est, 'fro') ** 2 / max(np.linalg.norm(H_true, 'fro') ** 2, 1e-30))


def hard_qpsk(x_scaled, rho):
    const = np.sqrt(1.0 - rho) * QPSK
    return np.array([const[np.argmin(np.abs(v - const))] for v in x_scaled], dtype=complex)


def run_case(name, *, random_pilot, matlab_phase, full_bp, p_actual_sparsity,
             n_total=100, n_frames_override=None, snr_list=None, l_max_cap_override=None):
    print("=" * 88)
    print(f"Case: {name}  [N_total={n_total}]")
    print(f"  random_pilot={random_pilot}, matlab_phase={matlab_phase}, full_bp={full_bp}, p_actual={p_actual_sparsity}")
    print("=" * 88)

    sys_obj = _make_system(n_total, rho=0.5, l_max_cap_override=l_max_cap_override)
    sys_obj.P_paths = 5
    sys_obj.sp_pilot_kind = 'random-qpsk' if random_pilot else 'zc'
    sys_obj.gen_h_daft_convention = 'matlab' if matlab_phase else 'python'
    sys_obj.baseline_phase_convention = 'matlab' if matlab_phase else 'python'
    sys_obj.baseline_mp_detector = 'bp' if full_bp else 'pic'
    sys_obj.omp_sparsity_mode = 'p_actual' if p_actual_sparsity else 'p_paths'

    _snr_list = snr_list if snr_list is not None else SNR_LIST
    for snr_db in _snr_list:
        n_frames = n_frames_override if n_frames_override is not None else FRAMES_BY_SNR.get(snr_db, 10)
        ber_perfect = []
        ber_ls = []
        ber_omp_mp = []
        ber_joint = []
        mse_ls = []
        mse_omp = []
        mse_joint = []
        first_diag = None

        for iframe in range(n_frames):
            _, pilot_pos, pilot_syms, _, data_pos = sys_obj.generate_pilot_frame()
            x_p_only = np.zeros(sys_obj.N_total, dtype=complex)
            x_p_only[pilot_pos] = pilot_syms

            H_eff, _, ch = sys_obj.generate_channel_matrix()

            data_unit = QPSK[np.random.randint(0, 4, sys_obj.N_total)]
            x_data = np.sqrt(1.0 - sys_obj.rho) * data_unit
            x_full = x_data + x_p_only

            y_clean = H_eff @ x_full
            noise = np.sqrt((10.0 ** (-snr_db / 10.0)) / 2.0) * (
                np.random.randn(sys_obj.N_total) + 1j * np.random.randn(sys_obj.N_total)
            )
            y = y_clean + noise
            sigma2 = float(10.0 ** (-snr_db / 10.0))

            P_data = 1.0 - sys_obj.rho
            y_data_true = y - H_eff @ x_p_only
            H_d_true = H_eff[:, data_pos]
            reg = (sigma2 / max(P_data, 1e-12)) * np.eye(len(data_pos))
            xh_perfect = np.linalg.solve(H_d_true.conj().T @ H_d_true + reg, H_d_true.conj().T @ y_data_true)

            H_ls = sys_obj.dictionary_ls_estimate(y, sigma2, x_p_only)
            xh_ls = sys_obj._lmmse_detect_np(H_ls, y, x_p_only, data_pos, sigma2)

            if full_bp:
                xh_omp_mp, H_omp = sys_obj.omp_mp_detect(y, x_p_only, sigma2, num_iter=NUM_ITER_MP, threshold=THRESHOLD_MP)
            else:
                xh_omp_mp, H_omp = sys_obj.omp_lmmse_detect(y, x_p_only, data_pos, sigma2)

            xh_joint, H_joint = sys_obj.joint_iterative_detect(y, x_p_only, data_pos, sigma2, n_outer=N_OUTER)
            if full_bp:
                xh_joint = hard_qpsk(xh_joint, sys_obj.rho)

            x_ref = x_data[data_pos]
            ber_perfect.append(ber_qpsk(x_ref, xh_perfect))
            ber_ls.append(ber_qpsk(x_ref, xh_ls))
            ber_omp_mp.append(ber_qpsk(x_ref, xh_omp_mp))
            ber_joint.append(ber_qpsk(x_ref, xh_joint))
            mse_ls.append(nmse(H_eff, H_ls))
            mse_omp.append(nmse(H_eff, H_omp))
            mse_joint.append(nmse(H_eff, H_joint))

            if iframe == 0:
                k_real_str = np.array2string(np.round(ch['k_real'], 4), precision=4, separator=' ')
                kappa_str = np.array2string(np.round(ch['k_real'] - np.round(ch['k_real']), 4), precision=4, separator=' ')
                l_uniq = sorted(set(int(x) for x in ch['l_exp']))
                K = 2*sys_obj.k_max_cap + 1
                Q = K * (sys_obj.l_max_cap + 1)
                first_diag = (
                    f"[Frac-Doppler] P_paths={sys_obj.P_paths} -> P_actual={ch['P_actual']} "
                    f"(K_LEAK={sys_obj.k_leak}, thres={sys_obj.frac_prune_rel_thres})\n"
                    f"  k_real={k_real_str}  kappa={kappa_str}\n"
                    f"  l_exp unique (DAFT bins)={l_uniq}  "
                    f"Q={Q}  N/Q={sys_obj.N_total/Q:.2f}x"
                )

        if first_diag:
            print(first_diag)
        print(
            f"SNR={snr_db:2d}dB | Frames={n_frames:4d} | Perfect: {np.mean(ber_perfect):.4e} | "
            f"LS+MMSE: {np.mean(ber_ls):.4e} | OMP+MP: {np.mean(ber_omp_mp):.4e} | "
            f"Joint: {np.mean(ber_joint):.4e} | MSE_LS: {10*np.log10(max(np.mean(mse_ls),1e-20)):.2f} dB | "
            f"MSE_OMP: {10*np.log10(max(np.mean(mse_omp),1e-20)):.2f} dB | "
            f"MSE_Joint: {10*np.log10(max(np.mean(mse_joint),1e-20)):.2f} dB"
        )
    print()


def main():
    cases = [
        ('baseline_control', False, False, False, False),
        ('random_pilot_only', True, False, False, False),
        ('p_actual_only', False, False, False, True),
        ('full_bp_only', False, False, True, False),
        ('matlab_phase_only', False, True, False, False),
        ('all_suspects', True, True, True, True),
    ]
    for name, random_pilot, matlab_phase, full_bp, p_actual_sparsity in cases:
        np.random.seed(1)
        run_case(
            name,
            random_pilot=random_pilot,
            matlab_phase=matlab_phase,
            full_bp=full_bp,
            p_actual_sparsity=p_actual_sparsity,
        )


def main_n_sweep():
    """Controlled-variable N sweep: compare N=100 vs N=256.

    Hypothesis: larger N → smaller c1 → better delay-Doppler separation
    → lower BER floor, especially for Joint iterative receiver.
    MATLAB uses N=1024 (c1≈0.0024); Python N=100 has c1=0.0250 (10× worse).
    N=256 gives c1≈0.0098 (~4× better than N=100, still 4× worse than MATLAB).
    """
    # The "best" Python combination identified in ablation:
    #   matlab_phase=True, full_bp=True, p_actual=False, random_pilot=False
    best_kwargs = dict(random_pilot=False, matlab_phase=True, full_bp=True, p_actual_sparsity=False)
    # Also baseline (no changes) for fair comparison
    base_kwargs = dict(random_pilot=False, matlab_phase=False, full_bp=False, p_actual_sparsity=False)

    # N=100 and N=256 baselines (already run; included for comparison reference)
    for n_total in [100, 256]:
        np.random.seed(1)
        run_case(f'baseline_N{n_total}', n_total=n_total,
                 n_frames_override=20, snr_list=[5, 10, 15, 20],
                 **base_kwargs)

    # --------------------------------------------------------------------------
    # N=1024 test — matches MATLAB's N exactly.
    # Root-cause analysis shows:
    #   N=100: delay_resolution=667µs (5.33 physical samples/DAFT bin)
    #           → P=5 physical paths often alias into 3-4 unique DAFT bins
    #           → k_real≈0.16-0.29 (all fractional, P_actual≈20 >> N/Q≈1.25x)
    #   N=1024: delay_resolution=65µs (0.52 physical samples/DAFT bin)
    #           → 5 physical paths → 5 unique DAFT bins (no aliasing!)
    #           → k_real≈1-2.5 (integer+fractional mix, P_actual≈8-12, N/Q≈4x)
    # l_max_cap=80 ensures max physical delay ≤ 42 samples (≈5.25ms) is covered,
    # giving Q=(2*2+1)*(80+1)=405, N/Q=1024/405≈2.5x (well overdetermined).
    # --------------------------------------------------------------------------
    for n_total in [1024]:
        np.random.seed(1)
        run_case(f'baseline_N{n_total}', n_total=n_total,
                 n_frames_override=10, snr_list=[10, 15, 20],
                 l_max_cap_override=80, **base_kwargs)

    for n_total in [100, 256]:
        np.random.seed(1)
        run_case(f'best_combo_N{n_total}', n_total=n_total,
                 n_frames_override=20, snr_list=[5, 10, 15, 20],
                 **best_kwargs)

    for n_total in [1024]:
        np.random.seed(1)
        run_case(f'best_combo_N{n_total}', n_total=n_total,
                 n_frames_override=10, snr_list=[10, 15, 20],
                 l_max_cap_override=80, **best_kwargs)


if __name__ == '__main__':
    main_n_sweep()