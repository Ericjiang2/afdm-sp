"""Offline A-01 diagnostics; truth never supplies a deployable fit or decoder."""
import numpy as np

from .budgeted_support_diagnostics import array_hash, physical_cluster_weights
from .direction_logging import confidence_groups
from .direction_structure import _svd


def _inverse_and_rank(matrix):
    u, s, vh, rank, threshold = _svd(matrix)
    inverse = ((vh[:rank].conj().T / s[:rank]) @ u[:, :rank].conj().T
               if rank else np.zeros((matrix.shape[1], matrix.shape[0]), complex))
    return inverse, u[:, :rank], dict(rank=rank, singular_values=s.tolist(),
        threshold=float(threshold),
        condition_number=float(s[0] / s[-1]) if rank == matrix.shape[1] and rank else None,
        identifiable_condition_number=float(s[0] / s[rank-1]) if rank else None)


def fixed_design_diagnostics(A, W, Wtrue, truth, fitted, constraint, sigma2, *, soft_lambda):
    """Thermal variance of a fixed linear map; selection variability is excluded."""
    if constraint not in ('none', 'soft', 'hard'):
        raise ValueError('unknown A-01 constraint')
    n, k = A.shape
    _, basis, bmeta = _inverse_and_rank(W)
    _, true_basis, tmeta = _inverse_and_rank(Wtrue)
    if constraint == 'hard':
        inverse, _, response = _inverse_and_rank(A @ W)
        linear = W @ inverse
    elif constraint == 'soft' and W.size and soft_lambda > 0:
        penalty = np.eye(k) - basis @ basis.conj().T
        augmented = np.vstack((A, np.sqrt(soft_lambda) * penalty))
        inverse, _, response = _inverse_and_rank(augmented)
        linear = inverse[:, :n]
    else:
        linear, _, response = _inverse_and_rank(A)
    angular_singular = np.linalg.svd(true_basis.conj().T @ basis, compute_uv=False)
    projection = basis @ (basis.conj().T @ truth)
    return dict(scope='fixed-design thermal-noise proxy; adaptive selection held fixed',
        basis_rank=bmeta['rank'], true_basis_rank=tmeta['rank'],
        basis_singular_values=bmeta['singular_values'],
        basis_rank_threshold=bmeta['threshold'], basis_slots=W.shape[1],
        true_basis_slots=Wtrue.shape[1],
        overlap_rows=int(np.count_nonzero(np.count_nonzero(Wtrue, axis=1) > 1)),
        response_rank=response['rank'], response_columns=(W.shape[1] if constraint == 'hard' else k),
        response_singular_values=response['singular_values'],
        response_rank_threshold=response['threshold'],
        response_condition_number=response['condition_number'],
        response_identifiable_condition_number=response['identifiable_condition_number'],
        principal_angles_radians=np.arccos(np.clip(angular_singular, 0, 1)).tolist(),
        unmatched_true_dimensions=max(0, tmeta['rank'] - bmeta['rank']),
        unmatched_estimated_dimensions=max(0, bmeta['rank'] - tmeta['rank']),
        template_projection_bias_squared=float(np.linalg.norm(truth - projection)**2),
        fixed_map_bias_squared=float(np.linalg.norm(linear @ (A @ truth) - truth)**2),
        thermal_variance_trace_proxy=float(sigma2 * np.linalg.norm(linear, 'fro')**2),
        coefficient_squared_error=float(np.linalg.norm(fitted - truth)**2),
        coefficient_truth_energy=float(np.linalg.norm(truth)**2))


def fit_diagnostics(prepared, fitted, system):
    s, ids = prepared['snapshot'], fitted['atom_ids']
    truth = np.array([prepared['truth_coefficients'].get(int(i), 0j) for i in ids])
    Wtrue = physical_cluster_weights(system, prepared['geometry'])[ids]
    details = fitted['diagnostics']
    result = fixed_design_diagnostics(fitted['A'], fitted['basis'], Wtrue, truth,
        fitted['coefficients'], fitted['spec']['constraint'], float(s['sigma2_thermal']),
        soft_lambda=details.get('soft_lambda', 0.))
    H, Htrue = fitted['H'], s['Htrue']
    residual = s['y'] - fitted['A'] @ fitted['coefficients']
    pilot_error = (Htrue - H) @ s['pilot']
    data_error = (Htrue - H) @ s['data']
    result.update(channel_nmse=float(np.linalg.norm(H - Htrue)**2 / np.linalg.norm(Htrue)**2),
        fit_residual_squared=float(np.linalg.norm(residual)**2),
        residual_ledger=fitted['residual'], A_sha256=array_hash(fitted['A']),
        H_sha256=array_hash(H), truth_access_level=fitted['truth_access_level'],
        interpretation='template bias and fixed-design variance are conditional diagnostics, not unique causes')
    arrays = dict(coefficients=fitted['coefficients'], atom_ids=ids, basis=fitted['basis'],
        true_basis=Wtrue, truth_coefficients=truth, fit_residual=residual,
        pilot_channel_error=pilot_error, data_channel_error=data_error)
    return result, arrays


def terminal_diagnostics(result, snapshot):
    llr = np.asarray(result['llr'])
    truth = np.asarray(snapshot['coded'])
    confidence = confidence_groups(llr, truth)
    signed = (1 - 2 * truth.astype(float)) * llr
    p_one = np.exp(-np.logaddexp(0., llr))
    return dict(confidence=confidence, nll=float(np.mean(np.logaddexp(0., -signed))),
        brier=float(np.mean((p_one - truth)**2)),
        raw_coded_errors=int(np.count_nonzero((llr < 0) != truth)),
        decoded_codeword_errors=int(np.count_nonzero(result['decoded'] != truth)),
        coded_bits=len(truth), info_bits=len(snapshot['info']),
        llr_scope='actual final clipped detector LLR; offline truth scoring only')
