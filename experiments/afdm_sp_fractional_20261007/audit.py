"""Independent saved-array recomposition; never regenerate a physical geometry.

Small-N checks start from saved dense unit operators. N1024 checks start from
saved sufficient statistics and cannot revalidate unsaved basis actions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

from experiments.afdm_phase_information_20261006.protocol import committed_project_sources
from experiments.afdm_shared_channel_20261004.common import dump
from . import protocol, thread_binding

CASES = ((8, [0, 3]), (16, [1, 15]), (1024, [0, 9]))
ATTEMPT_SHA256 = '329f39b59b0fe48dfdfaa4f3870deb29320d457ede16a95f77d54b673b787e56'
MATH_HEAD = 'ad3b3fa2d0d301e6e4267b51286206db26bb748c'
ROUND = 1e-10
KEYS = ('quadratic', 'gram_diagonal', 'gram_matvec', 'mean_adjoint',
        'gain_gram', 'gain_matched', 'conditional_scores')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def array_digest(value):
    value = np.ascontiguousarray(value)
    header = str(value.dtype).encode() + json.dumps(list(value.shape)).encode()
    return hashlib.sha256(header + value.tobytes()).hexdigest()


def load_arrays(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), f'duplicate NPZ entry: {path}')
        require(sum(x.file_size for x in archive.infolist()) <= 64 * 1024**2,
                f'NPZ exceeds admitted uncompressed size: {path}')
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    for name, value in arrays.items():
        require(value.dtype.kind in 'biufc' and np.isfinite(value).all(), f'invalid array: {name}')
    return arrays


class Checks:
    def __init__(self):
        self.rows = []

    def fact(self, name, passed, **details):
        self.rows.append(dict(check=name, passed=bool(passed), **details))

    def compare(self, name, actual, expected, tolerance):
        actual, expected = np.asarray(actual), np.asarray(expected)
        require(actual.shape == expected.shape, f'{name}: incompatible shapes')
        finite = bool(np.isfinite(actual).all() and np.isfinite(expected).all())
        error = float(np.linalg.norm(actual - expected) / max(1., float(np.linalg.norm(expected)))) if finite else None
        self.rows.append(dict(check=name, normalized_error=error, tolerance=tolerance,
                              passed=finite and error <= tolerance))
        return error


def source_inventory():
    module = protocol.adapter()
    # Bind the original physical source as provenance without importing it.
    physical = protocol.ROOT / 'experiments/sp_afdm_frozen_20260920/src/physical.py'
    return sorted(set(module.project_sources()) | set(protocol.PACKAGE.glob('*.py')) | {physical})


def input_files(source):
    require(source.is_absolute() and source.is_dir(), 'absolute saved attempt directory required')
    paths = sorted(path for path in source.rglob('*') if path.is_file())
    require(paths and all(not path.is_symlink() for path in source.rglob('*')), 'symlink or empty input tree')
    require(sum(path.stat().st_size for path in paths) <= 16 * 1024**2, 'saved attempt exceeds input budget')
    return paths


def validate_provenance(source, files):
    require(digest(source / 'attempt.json') == ATTEMPT_SHA256, 'original attempt SHA256 differs')
    attempt = read_json(source / 'attempt.json')
    require(attempt['status'] == 'complete' and attempt['exit_code'] == 0, 'original stage not complete')
    issued = attempt['artifact_sha256']
    roots = [key[:-len('registration.json')] for key in issued if key.endswith('/registration.json')]
    require(len(roots) == 1, 'ambiguous original artifact root')
    original_root = roots[0]
    bound = {}
    for name, expected in issued.items():
        require(name.startswith(original_root), 'artifact manifest spans multiple attempts')
        relative = Path(name[len(original_root):])
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe artifact manifest path')
        path = source / relative
        require(path.is_file() and digest(path) == expected, f'artifact SHA256 mismatch: {relative}')
        bound[str(relative)] = expected
    require({str(path.relative_to(source)) for path in files} == set(bound) | {'attempt.json'},
            'saved attempt file inventory differs from immutable manifest')
    registration = read_json(source / 'registration.json')
    config = registration['config']
    require(registration['stage'] == 'MATH-01' and registration['git_head'] == MATH_HEAD, 'wrong original stage/HEAD')
    require(config == registration['_config'], 'original effective config mismatch')
    require(config['cases'] == [dict(N=n, delays=delays) for n, delays in CASES], 'case inventory differs')
    require(config['new_geometry_probes'] == 3 and config['new_observations'] == 0 and
            config['receiver_calls'] == config['decoder_calls'] == 0 and config['seed'] == 'none',
            'original scientific work contract differs')
    require(config['small_normalized_tolerance'] == 1e-10 and config['large_normalized_tolerance'] == 1e-9
            and config['hermitian_psd_roundoff'] == ROUND, 'original thresholds differ')
    require(attempt['wall_seconds'] <= 180 and attempt['peak_rss_bytes'] <= 1024**3 and
            attempt['total_task_output_bytes'] <= 16 * 1024**2, 'original resource limit failed')
    require(attempt['reserved_wall_seconds'] == registration['wall_cap_seconds'] == 180
            and attempt['reserved_new_observations'] == 0, 'original reservation differs')
    identity = read_json(source / 'committed_project_sources.json')
    python_hashes = {key: value for key, value in registration['source_sha256'].items() if key.endswith('.py')}
    require(identity['head'] == MATH_HEAD and identity['project_python_sha256'] == python_hashes,
            'original committed source inventory mismatch')
    require(len(python_hashes) == 15, 'original source count differs')
    for index, (original, expected) in enumerate(sorted(registration['source_sha256'].items())):
        snapshot = source / 'source_snapshot' / f'{index:03d}_{Path(original).name}'
        require(snapshot.is_file() and digest(snapshot) == expected, 'source snapshot ordering/hash mismatch')
    result = read_json(source / 'verification.json')
    require(result == read_json(source / 'results.json'), 'original summary copies differ')
    require(result['geometry_probes'] == 3 and result['new_observations'] == 0 and
            result['receiver_calls'] == result['decoder_calls'] == 0 and result['seed'] == 'none'
            and result['mathematical_checks_pass'], 'original result accounting/status differs')
    require([row['N'] for row in result['cases']] == [n for n, _ in CASES], 'missing or reordered case')
    require(len(result['validation_controls']) == 9 and all(row['passed'] for row in result['validation_controls']),
            'original boundary controls incomplete; audit does not rerun them')
    return config, result, dict(original_attempt_sha256=ATTEMPT_SHA256, original_root=original_root,
                                bound_artifacts=len(bound), original_resources=attempt)


def recombine(arrays, config, checks, tolerance):
    """Vectorized second-moment grid, distinct from the generator's at_pair loop."""
    a = arrays
    weights = a['doppler_weights']
    indices = a['reference_prior_node_indices'].astype(int)
    points = a['reference_points']
    responses = a['reference_mean_responses']
    own = a['reference_variance_trace_self']
    cross_variance = a['reference_variance_trace_cross']
    mean, covariance = a['gain_mean'], a['gain_covariance']
    second = covariance + np.outer(mean, mean.conj())
    y = a['y']
    matched = responses.conj() @ y
    norms = np.sum(abs(responses)**2, axis=-1) + own
    cross = responses[0].conj() @ responses[1].T + cross_variance
    energy = (np.vdot(y, y).real
              - 2 * np.real(mean[0].conjugate() * matched[0, :, None]
                            + mean[1].conjugate() * matched[1, None, :])
              + second[0, 0] * norms[0, :, None] + second[1, 1] * norms[1, None, :]
              + 2 * np.real(second[1, 0] * cross))
    selection = np.ix_(indices[0], indices[1])
    joint = np.outer(weights[0], weights[1])
    pair_energy = energy[selection]
    gamma = np.diag([weights[i] @ norms[i, indices[i]] for i in range(2)]).astype(complex)
    gamma[0, 1] = np.sum(joint * cross[selection])
    gamma[1, 0] = gamma[0, 1].conjugate()
    gain_matched = np.array([weights[i] @ matched[i, indices[i]] for i in range(2)])
    evaluation = np.array([np.searchsorted(points[i], a['evaluation_nodes']) for i in range(2)])
    for i in range(2):
        checks.compare(f'conditional_node_membership_{i}', points[i, evaluation[i]], a['evaluation_nodes'], 0.)
    conditional = -np.array([energy[np.ix_(evaluation[0], indices[1])] @ weights[1],
                             weights[0] @ energy[np.ix_(indices[0], evaluation[1])]]) / config['noise_variance']
    diagonal = np.einsum('ij,ijk->k', joint, a['reference_pair_diagonal'])
    source_trace = (second[0, 0] * own[0, indices[0]][:, None]
                    + second[1, 1] * own[1, indices[1]][None, :]
                    + 2 * np.real(second[1, 0] * cross_variance[selection]))
    checks.compare('pair_variance_trace_from_diagonal', a['reference_pair_diagonal'] @ a['data_variance'],
                   source_trace, tolerance)
    checks.compare('pair_quadratic_recomposition', pair_energy, a['reference_pair_quadratic'], tolerance)
    return dict(quadratic=np.sum(joint * pair_energy), gain_gram=gamma, gain_matched=gain_matched,
                conditional_scores=conditional, gram_diagonal=diagonal, all_node_quadratic=energy)


def dense_recompute(a, checks, tolerance):
    """Use saved physical unit matrices only; no Channel or structured kernels."""
    unit = a['reference_dense_operators']
    n = len(a['y'])
    require(n in (8, 16) and unit.shape == (2, 10, n, n), 'dense reference only admitted at N8/N16')
    x, variance = a['pilot'] + a['data_mean'], a['data_variance']
    responses = unit @ x
    own = np.einsum('iqnk,iqnk,k->iq', unit.conj(), unit, variance)
    cross = np.einsum('qnk,rnk,k->qr', unit[0].conj(), unit[1], variance)
    checks.compare('dense_elementary_mean_responses', responses, a['reference_mean_responses'], tolerance)
    checks.compare('dense_elementary_variance_self', own, a['reference_variance_trace_self'], tolerance)
    checks.compare('dense_elementary_variance_cross', cross, a['reference_variance_trace_cross'], tolerance)
    nodes, weights = a['reference_prior_node_indices'].astype(int), a['doppler_weights']
    mean = a['gain_mean']
    second = a['gain_covariance'] + np.outer(mean, mean.conj())
    gram = np.zeros((n, n), complex)
    mean_operator = np.zeros((n, n), complex)
    for u, first in enumerate(nodes[0]):
        for v, last in enumerate(nodes[1]):
            matrices = (unit[0, first], unit[1, last])
            pair = sum(second[j, i] * matrices[i].conj().T @ matrices[j]
                       for i in range(2) for j in range(2))
            probability = weights[0, u] * weights[1, v]
            checks.compare(f'dense_pair_diagonal_{u}_{v}', np.diag(pair), a['reference_pair_diagonal'][u, v], tolerance)
            gram += probability * pair
            mean_operator += probability * (mean[0] * matrices[0] + mean[1] * matrices[1])
    checks.compare('dense_expected_gram', gram, a['reference_dense_gram'], tolerance)
    checks.compare('dense_expected_gram_hermitian', gram, gram.conj().T, ROUND)
    checks.fact('dense_expected_gram_psd', np.linalg.eigvalsh((gram + gram.conj().T) / 2).min()
                >= -ROUND * max(1., float(np.linalg.norm(gram))))
    selected = unit[0, nodes[0]]
    pd = float(abs(a['qpsk'][0])**2)
    exact = pd * np.einsum('q,qnk,qmk->nm', weights[0], selected, selected.conj())
    averaged = np.einsum('q,qnk->nk', weights[0], selected)
    wrong = pd * averaged @ averaged.conj().T
    checks.compare('dense_isotropic_covariance', exact, pd * np.eye(n), tolerance)
    checks.compare('dense_saved_isotropic_covariance', exact, a['reference_exact_isotropic_covariance'], tolerance)
    checks.compare('dense_independent_copy_covariance', wrong, a['reference_independent_copy_covariance'], tolerance)
    checks.compare('dense_tangent_saved_matrix_action', a['reference_tangent_covariance'] @ a['probe'],
                   a['reference_tangent_action'], tolerance)
    for name, matrix in [('exact_isotropic', exact), ('independent_copy', wrong),
                         ('tangent', a['reference_tangent_covariance'])]:
        checks.compare(f'dense_{name}_trace', np.trace(matrix), a[f'reference_{name}_trace'], tolerance)
    return dict(gram_matvec=gram @ a['probe'], gram_diagonal=np.diag(gram),
                mean_adjoint=mean_operator.conj().T @ a['y'], dense_gram=gram)


def audit_case(source, n, delays, config, original):
    saved = read_json(source / f'n{n}_checks.json')
    require(saved == original and saved['N'] == n and saved['delays'] == delays, 'case JSON copies differ')
    require(saved['factor_combinations'] == 9 and saved['conditional_other_factor_evaluations'] == 42
            and saved['conditional_score_nodes'] == 14 and saved['dense_reference'] == (n <= 16), 'case coverage differs')
    started = read_json(source / f'n{n}_started.json')
    require(started['N'] == n and started['delays'] == delays, 'case start marker mismatch')
    require(saved['arrays_file'] == f'n{n}_arrays.npz' and saved['inputs_file'] == f'n{n}_inputs.npz', 'unexpected raw filenames')
    require(digest(source / saved['arrays_file']) == saved['arrays_sha256'] and
            digest(source / saved['inputs_file']) == saved['inputs_sha256'], 'case file SHA256 mismatch')
    a, inputs = load_arrays(source / saved['arrays_file']), load_arrays(source / saved['inputs_file'])
    require(set(a) == set(saved['array_sha256']), 'array inventory differs')
    for key, value in a.items():
        require(array_digest(value) == saved['array_sha256'][key], f'array SHA256 mismatch: {key}')
    for key, value in inputs.items():
        require(key in a and np.array_equal(value, a[key]), f'input copy differs: {key}')
    require(a['y'].shape == (n,) and a['reference_mean_responses'].shape == (2, 10, n)
            and a['reference_variance_trace_self'].shape == (2, 10)
            and a['reference_variance_trace_cross'].shape == (10, 10)
            and a['reference_pair_diagonal'].shape == (3, 3, n), 'raw sufficient statistic shape differs')
    require(n != 1024 or all(value.ndim < 2 or value.shape[-2:] != (n, n) for value in a.values()),
            'N1024 saved a forbidden dense matrix')
    checks, tolerance = Checks(), 1e-10 if n <= 16 else 1e-9
    checks.compare('delays', a['delays'], delays, 0.)
    checks.compare('registered_nodes', a['doppler_nodes'], config['doppler_nodes'], 0.)
    checks.compare('registered_weights', a['doppler_weights'], np.tile(config['weights'], (2, 1)), 0.)
    checks.compare('registered_score_nodes', a['evaluation_nodes'], config['evaluation_nodes'], 0.)
    checks.compare('registered_c1', a['c1'], 5.3 / (2 * n), 0.)
    checks.compare('registered_c2', a['c2'], (np.sqrt(2) - 1) / (2 * n * n), 0.)
    mean_parts, covariance_parts = np.asarray(config['gain_mean']), np.asarray(config['gain_covariance'])
    checks.compare('registered_gain_mean', a['gain_mean'], mean_parts[:, 0] + 1j * mean_parts[:, 1], 0.)
    checks.compare('registered_gain_covariance', a['gain_covariance'],
                   covariance_parts[:, :, 0] + 1j * covariance_parts[:, :, 1], 0.)
    covariance = a['gain_covariance']
    checks.compare('gain_covariance_hermitian', covariance, covariance.conj().T, ROUND)
    checks.fact('gain_covariance_psd', np.linalg.eigvalsh((covariance + covariance.conj().T) / 2).min()
                >= -ROUND * max(1., float(np.linalg.norm(covariance))))
    for i in range(2):
        indices = a['reference_prior_node_indices'][i].astype(int)
        checks.compare(f'prior_node_membership_{i}', a['reference_points'][i, indices], a['doppler_nodes'][i], 0.)
    probabilities, alphabet = a['probabilities'], a['qpsk']
    require(probabilities.shape == (n, 4) and alphabet.shape == (4,), 'QPSK factor shapes differ')
    checks.fact('positive_probabilities', np.all(probabilities > 0))
    checks.compare('normalized_probabilities', probabilities.sum(axis=1), np.ones(n), 1e-14)
    mu = probabilities @ alphabet
    variance = probabilities @ abs(alphabet)**2 - abs(mu)**2
    checks.compare('symbol_mean_from_probabilities', mu, a['data_mean'], tolerance)
    checks.compare('symbol_variance_from_probabilities', variance, a['data_variance'], tolerance)
    checks.fact('positive_nonuniform_variance', variance.min() > 0 and np.ptp(variance) > 0)
    checks.compare('source_variance_fft', np.fft.fft(variance) / n, a['source_variance_fft'], tolerance)
    checks.compare('unit_path_frobenius_norms', a['reference_unit_norm_sums'], np.full((2, 10), n), tolerance)
    checks.compare('unit_path_variance_trace', a['reference_variance_trace_self'], np.full((2, 10), variance.sum()), tolerance)
    time_axis = 2 * np.pi * np.arange(n) / n
    phi = np.einsum('iq,iqn->in', a['doppler_weights'], np.exp(1j * a['doppler_nodes'][:, :, None] * time_axis))
    checks.compare('characteristic_moments', phi, a['characteristic_moments'], tolerance)
    recomputed = recombine(a, config, checks, tolerance)
    if n <= 16:
        recomputed.update(dense_recompute(a, checks, tolerance))
    for key in KEYS:
        left, right = a[f'structured_{key}'], a[f'reference_{key}']
        if key == 'conditional_scores':
            left, right = left - left[:, :1], right - right[:, :1]
        checks.compare(f'saved_comparison_{key}', left, right, tolerance)
        if key in recomputed:
            independent = recomputed[key]
            if key == 'conditional_scores':
                independent = independent - independent[:, :1]
            checks.compare(f'independent_recomposition_{key}', independent, right, tolerance)
            checks.compare(f'independent_vs_structured_{key}', independent, left, tolerance)
    score = (2 / config['noise_variance']) * np.real(
        a['coordinate_coefficients'] @ np.exp(1j * time_axis[:, None] * a['evaluation_nodes']))
    checks.compare('coefficient_scores_up_to_constant', score - score[:, :1],
                   recomputed['conditional_scores'] - recomputed['conditional_scores'][:, :1], tolerance)
    pd = float(abs(alphabet[0])**2)
    checks.compare('constant_symbol_energy', abs(alphabet)**2, np.full(4, pd), tolerance)
    checks.compare('QPSK_alphabet', alphabet, np.sqrt(pd / 2) * np.array([1+1j, 1-1j, -1+1j, -1-1j]), tolerance)
    centered = a['doppler_nodes'][0] - a['doppler_weights'][0] @ a['doppler_nodes'][0]
    checks.compare('saved_centered_offsets', centered, a['reference_residual_dopplers'], tolerance)
    variance_nu = a['doppler_weights'][0] @ centered**2
    traces = dict(exact_isotropic_trace=pd * n, independent_copy_trace=pd * np.sum(abs(phi[0])**2),
                  tangent_trace=pd * np.sum(1 + variance_nu * time_axis**2))
    for key, value in traces.items():
        checks.compare(f'negative_control_{key}', value, a[f'reference_{key}'], tolerance)
    checks.fact('negative_control_defect_signs', traces['exact_isotropic_trace'] > traces['independent_copy_trace']
                and traces['tangent_trace'] > traces['exact_isotropic_trace'])
    comparisons = {key: (a[f'structured_{key}'], a[f'reference_{key}']) for key in KEYS}
    comparisons['conditional_scores'] = tuple(value - value[:, :1] for value in comparisons['conditional_scores'])
    comparisons.update(gain_gram_hermitian=(a['structured_gain_gram'], a['structured_gain_gram'].conj().T),
                       gram_hermitian_probe=(np.vdot(a['second_probe'], a['structured_gram_matvec']),
                                              np.vdot(a['gram_second_probe'], a['probe'])),
                       single_path_isotropic_action=(a['reference_exact_isotropic_action'], pd * a['probe']),
                       single_path_isotropic_trace=(a['reference_exact_isotropic_trace'], pd * n),
                       independent_copy_predicted_action=(a['reference_independent_copy_action'], a['predicted_wrong_action']),
                       independent_copy_predicted_trace=(a['reference_independent_copy_trace'], traces['independent_copy_trace']),
                       tangent_predicted_action=(a['reference_tangent_action'], a['predicted_tangent_action']),
                       tangent_predicted_trace=(a['reference_tangent_trace'], traces['tangent_trace']))
    if n <= 16:
        comparisons.update(dense_gram_diagonal=(a['structured_gram_diagonal'], np.diag(a['reference_dense_gram'])),
                           dense_gram_hermitian=(a['reference_dense_gram'], a['reference_dense_gram'].conj().T),
                           single_path_full_isotropic_covariance=(a['reference_exact_isotropic_covariance'], pd * np.eye(n)))
    reported = {row['check']: row for row in saved['checks']}
    require(len(reported) == len(saved['checks']) == (23 if n <= 16 else 19), 'original check completeness differs')
    require({key for key, row in reported.items() if 'normalized_error' in row} == set(comparisons),
            'original normalized comparison inventory differs')
    for key, (left, right) in comparisons.items():
        row = reported[key]
        allowed = ROUND if key in ('gain_gram_hermitian', 'gram_hermitian_probe', 'dense_gram_hermitian') else tolerance
        require(row['tolerance'] == allowed, 'saved tolerance differs')
        error = checks.compare(f'recompute_reported_error_{key}', left, right, allowed)
        checks.fact(f'reported_error_value_{key}', error is not None and row['normalized_error'] is not None
                    and abs(error - row['normalized_error']) <= 1e-14)
    gamma = a['structured_gain_gram']
    checks.fact('gain_gram_psd', np.linalg.eigvalsh((gamma + gamma.conj().T) / 2).min()
                >= -ROUND * max(1., float(np.linalg.norm(gamma))))
    energy = np.vdot(a['probe'], a['structured_gram_matvec'])
    checks.fact('gram_psd_probe', energy.real >= -ROUND * max(1., abs(energy)))
    checks.fact('original_flags_all_pass', saved['passed'] and all(row['passed'] for row in saved['checks']))
    return recomputed, dict(N=n, checks=checks.rows, passed=all(row['passed'] for row in checks.rows),
                            coverage='saved dense matrices' if n <= 16 else 'saved sufficient statistics only',
                            unsaved_basis_actions_revalidated=False, original_checks=len(reported))


def calculate(source, files, output):
    dump(output / 'audit_started.json', dict(source_attempt=str(source), new_observations=0, geometry_probes=0))
    config, original, provenance = validate_provenance(source, files)
    dump(output / 'provenance.json', provenance)
    reports = []
    for index, (n, delays) in enumerate(CASES):
        arrays, report = audit_case(source, n, delays, config, original['cases'][index])
        with (output / f'n{n}_recomputed.npz').open('xb') as handle:
            np.savez_compressed(handle, **arrays)
        dump(output / f'n{n}_audit.json', report)
        reports.append(report)
    result = dict(cases=reports, audit_pass=all(row['passed'] for row in reports), new_observations=0,
                  geometry_probes=0, receiver_calls=0, decoder_calls=0, seed='none',
                  scope='Saved-array audit only; N1024 unsaved basis actions and physical generation are not revalidated.')
    dump(output / 'audit.json', result)
    if not result['audit_pass']:
        raise AssertionError('saved-array audit failed; all completed checks retained')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-attempt', type=Path)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--stage', default='AUDIT-01')
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    _ = np.linalg.eigvalsh, np.fft.fft, np.savez_compressed, thread_binding.blas_binding
    forbidden = ('experiments.afdm_sp_fractional_20261007.verify',
                 'experiments.afdm_sp_fractional_20261007.moments',
                 'experiments.sp_afdm_frozen_20260920.src.physical')
    require(not any(name in sys.modules for name in forbidden), 'audit must not import mathematical execution kernels')
    sources = source_inventory()
    if args.print_imports:
        print(json.dumps(dict(all_paths=[str(path.relative_to(protocol.ROOT)) for path in sources],
                              bound_but_not_imported='physical.py; original verify/moments/test files'), indent=2))
        return
    if args.source_attempt is None or args.artifact_root is None:
        parser.error('--source-attempt and --artifact-root are required')
    require(args.source_attempt.is_absolute() and args.artifact_root.is_absolute(), 'absolute audit paths required')
    source, artifact = args.source_attempt.resolve(), args.artifact_root.resolve()
    require(not artifact.is_relative_to(source) and not source.is_relative_to(artifact), 'audit output and source must be disjoint')
    files = input_files(source)
    identity = committed_project_sources(sources)
    config = dict(seed='none', new_observations=0, new_geometry_probes=0, receiver_calls=0, decoder_calls=0,
                  new_confirmation_stream=False, source_attempt=str(source), source_attempt_sha256=ATTEMPT_SHA256,
                  saved_cases=3, independent_audit='saved arrays only; no physical regeneration')

    def checked(output):
        dump(output / 'committed_project_sources.json', identity)
        return calculate(source, files, output)

    protocol.adapter().run(args.stage, config, [*sources, *files], checked,
                           artifact_root=artifact, wall_seconds=60)


if __name__ == '__main__':
    main()
