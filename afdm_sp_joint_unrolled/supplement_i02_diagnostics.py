"""Offline cancellation diagnostics; actual data/truth never enter the receiver."""
import numpy as np

from .budgeted_support_diagnostics import array_hash


def cancellation_diagnostics(snapshot, transformed, mode):
    s = snapshot
    sigma = float(s['sigma2_terminal'])
    n = len(s['y'])
    H = np.asarray(s['H'], dtype=np.complex128)
    z = s['y'] - H @ s['pilot']
    if mode is None:
        B = np.zeros((n, 0), complex)
        output = dict(z=z, H=H, sigma_out=sigma)
    else:
        B = transformed['B']
        output = transformed
    diagonal = np.sum(np.abs(B)**2, axis=1)
    rank = int(np.linalg.matrix_rank(B)) if B.size else 0
    whiten_error = 0.
    if mode in (None, 'scalar'):
        def apply(value):
            return value.copy()
        minimum = sigma + float(np.mean(diagonal))
    elif mode == 'diagonal':
        scales = np.sqrt(sigma / (sigma + diagonal))
        def apply(value):
            return scales * value if value.ndim == 1 else scales[:, None] * value
        minimum = sigma + float(diagonal.min())
        whiten_error = float(np.linalg.norm(scales**2 * (sigma + diagonal) - sigma)
                             / (sigma * np.sqrt(n)))
    elif mode == 'lowrank':
        U, singular, _ = np.linalg.svd(B, full_matrices=False)
        scales = 1 / np.sqrt(1 + singular**2 / sigma)
        def apply(value):
            projected = U.conj().T @ value
            correction = ((scales - 1) * projected if value.ndim == 1 else
                          (scales - 1)[:, None] * projected)
            return value + U @ correction
        WB = apply(B)
        # Form only the deviation from sigma*I. No N-cubed dense eigensolve.
        delta = sigma * (U * (scales**2 - 1)) @ U.conj().T + WB @ WB.conj().T
        whiten_error = float(np.linalg.norm(delta) / (sigma * np.sqrt(n)))
        minimum = sigma if rank < n else sigma + float(singular[-1]**2)
    else:
        raise ValueError('unknown cancellation diagnostics mode')
    expected_h, expected_z = apply(H), apply(z)
    h_error = float(np.linalg.norm(output['H'] - expected_h) / max(1., np.linalg.norm(H)))
    z_error = float(np.linalg.norm(output['z'] - expected_z) / max(1., np.linalg.norm(z)))
    expected_sigma = sigma + float(np.mean(diagonal)) if mode == 'scalar' else sigma
    if (max(h_error, z_error, whiten_error) > 1e-10
            or abs(float(output['sigma_out']) - expected_sigma) > 1e-12):
        raise AssertionError('cancellation covariance/observation/channel update identity failed')
    terms = dict(pilot_channel_error=apply((s['Htrue'] - H) @ s['pilot']),
                 data_channel_error=apply((s['Htrue'] - H) @ s['data']),
                 thermal_noise=apply(np.sqrt(s['sigma2_thermal']) * s['noise']))
    residual = output['z'] - output['H'] @ s['data']
    closure = float(np.linalg.norm(residual - sum(terms.values())) /
                    max(1., np.linalg.norm(s['y'])))
    energies = {k: float(np.vdot(v, v).real / n) for k, v in terms.items()}
    names = list(terms)
    cross = {f'{a}:{b}': float(2 * np.vdot(terms[a], terms[b]).real / n)
             for i, a in enumerate(names) for b in names[i+1:]}
    energy = float(np.vdot(residual, residual).real / n)
    energy_error = energy - sum(energies.values()) - sum(cross.values())
    if closure > 1e-10 or abs(energy_error) > 1e-10 * max(1., energy):
        raise AssertionError('transformed pilot/data/noise cross-term closure failed')
    mean = np.mean(residual)
    normalized = np.abs(residual)**2 / output['sigma_out']
    result = dict(truth_access='offline_only',
        working_covariance=dict(model='working approximation, not estimator posterior',
            mode=mode or 'baseline', rank_B=rank, K=B.shape[1], N=n,
            minimum_eigenvalue=minimum, positive_definite=bool(minimum > 0),
            trace_BBH=float(diagonal.sum()), sigma_base=sigma,
            sigma_out=float(output['sigma_out']), whitening_relative_error=whiten_error,
            H_update_relative_error=h_error, z_update_relative_error=z_error,
            H_input_sha256=array_hash(s['H']), H_cov_sha256=array_hash(output['H']),
            z_cov_sha256=array_hash(output['z']), B_sha256=array_hash(B),
            power_scaling='pilot and data already scaled; no extra rho or (1-rho)'),
        residual=dict(energies=energies, cross_terms=cross, residual_mean_square=energy,
            relative_vector_closure=closure, energy_closure=energy_error,
            mean_real=float(mean.real), mean_imag=float(mean.imag),
            mean_squared_magnitude=float(abs(mean)**2),
            centered_mean_square=float(np.mean(np.abs(residual - mean)**2)),
            normalized_mean_square=float(normalized.mean()),
            normalized_energy_quantiles=np.quantile(normalized, [.5, .9, .99]).tolist(),
            normalized_energy_over_one=float(np.mean(normalized > 1)),
            normalized_energy_over_three=float(np.mean(normalized > 3)),
            scope='per-frame descriptive calibration of actual post-cancellation residual; no iid-row inference'))
    arrays = dict(residual=residual, z_cov=output['z'], B=B, **terms)
    return result, arrays
