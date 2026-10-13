"""Test: give detector the oracle H_eff_true and see if BER drops.

If yes -> detector is fine, channel estimation residual is the issue.
If no -> detector itself can't handle this geometry.
"""
import pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from afdm_sp_joint_unrolled.qing_baseline.qing_sp_afdm import (
    QPSK_CONST, build_theta_list, qing_pilot, mp_bp_detect, _qpsk_hard_detect,
)

N = 512
alpha_max, l_max, P = 2, 1, 3
M = 15
c1 = (2 * alpha_max + 1) / (2 * N)
c2 = 1.0 / (4.0 * N)
N0 = 1.0
snr_p_db, snr_d_db = 50.0, 21.0
sigma_p_sq = N0 * 10 ** (snr_p_db / 10)
sigma_d_sq = N0 * 10 ** (snr_d_db / 10)

x_p, _ = qing_pilot(N, alpha_max, l_max, M=M, sigma_p=np.sqrt(sigma_p_sq))
theta_list = build_theta_list(N, alpha_max, l_max, c1, c2)

scaled_const = QPSK_CONST * np.sqrt(sigma_d_sq)

results = {'mp_oracle': 0, 'mp_oracle_bits': 0,
           'ls_oracle': 0, 'ls_oracle_bits': 0,
           'mp_estimated': 0, 'mp_estimated_bits': 0}

rng = np.random.default_rng(42)
for f in range(50):
    rng_f = np.random.default_rng(int(rng.integers(0, 2**31)))
    ch = rng_f.choice(10, size=P, replace=False)
    h_true = np.zeros(10, dtype=complex)
    h_true[ch] = (rng_f.standard_normal(P) + 1j * rng_f.standard_normal(P)) / np.sqrt(2 * P)
    H_eff_true = sum(h_t * Theta for h_t, Theta in zip(h_true, theta_list))
    di = rng_f.integers(0, 4, N)
    x_d = QPSK_CONST[di] * np.sqrt(sigma_d_sq)
    nz = np.sqrt(N0) * (rng_f.standard_normal(N) + 1j * rng_f.standard_normal(N)) / np.sqrt(2)
    y = H_eff_true @ (x_p + x_d) + nz
    sigma_w_eff_sq = 1.0 * sigma_d_sq + N0  # what the receiver uses
    sigma_true = N0  # true residual noise after exact pilot cancellation

    # Oracle: detector with H_eff_true and ORACLE residual y - H_eff_true @ x_p
    y_d_oracle = y - H_eff_true @ x_p
    # Pass TRUE noise variance to detector, not the conservative receiver one.
    x_d_mp_oracle = mp_bp_detect(y_d_oracle, H_eff_true, sigma_true, constellation=scaled_const)
    x_d_ls_oracle = _qpsk_hard_detect(y_d_oracle, H_eff_true, sigma_true)

    # Slice LS to the scaled constellation:
    diffs = np.abs(x_d_ls_oracle[:, None] - scaled_const[None, :])
    x_d_ls_oracle = scaled_const[np.argmin(diffs, axis=1)]

    # bit count
    def bits_diff(a, b):
        return int((np.sign(a.real) != np.sign(b.real)).sum() +
                   (np.sign(a.imag) != np.sign(b.imag)).sum())

    results['mp_oracle'] += bits_diff(x_d, x_d_mp_oracle)
    results['mp_oracle_bits'] += 2 * N
    results['ls_oracle'] += bits_diff(x_d, x_d_ls_oracle)
    results['ls_oracle_bits'] += 2 * N

print(f'MP-BP w/ oracle H: BER = {results["mp_oracle"] / results["mp_oracle_bits"]:.3e} '
      f'({results["mp_oracle"]}/{results["mp_oracle_bits"]})')
print(f'LS    w/ oracle H: BER = {results["ls_oracle"] / results["ls_oracle_bits"]:.3e} '
      f'({results["ls_oracle"]}/{results["ls_oracle_bits"]})')

# Diagnostic: SINR at receive symbol
print(f'\n||H_eff_true x_d||^2 / ||noise||^2 = ({np.linalg.norm(H_eff_true @ x_d)**2:.2e} / {np.linalg.norm(nz)**2:.2e}) = {np.linalg.norm(H_eff_true @ x_d)**2 / np.linalg.norm(nz)**2:.2e}')
