"""One admitted deterministic verification stage; never an observation sampler."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from experiments.sp_afdm_frozen_20260920.src.physical import Channel, daft
from . import protocol, thread_binding
from .moments import PathMoments, ROUNDOFF, coordinate_log_density

# Every input law, analytic array and tolerance is fixed before source admission.
CASES = ((8, (0, 3)), (16, (1, 15)), (1024, (0, 9)))
DOPPLER_NODES = ((-.25, .05, .30), (.41, .62, .88))
WEIGHTS = (.2, .5, .3)
EVALUATION_NODES = (-.70, -.37, 0., .19, .52, .75, 1.10)
NOISE_VARIANCE = .7
DATA_POWER = .55
GAIN_MEAN = (.65+.25j, -.35+.45j)
GAIN_COVARIANCE = ((.31, .07+.09j), (.07-.09j, .23))


def configuration():
    return dict(seed='none', new_observations=0, new_geometry_probes=3,
                receiver_calls=0, decoder_calls=0, new_confirmation_stream=False,
                cases=[dict(N=n, delays=list(delays)) for n, delays in CASES],
                c1='5.3/(2*N)', c2='(sqrt(2)-1)/(2*N**2)',
                doppler_nodes=DOPPLER_NODES, weights=WEIGHTS, evaluation_nodes=EVALUATION_NODES,
                small_normalized_tolerance=1e-10, large_normalized_tolerance=1e-9,
                hermitian_psd_roundoff=ROUNDOFF, noise_variance=NOISE_VARIANCE,
                gain_mean=[[z.real, z.imag] for z in GAIN_MEAN],
                gain_covariance=[[[complex(z).real, complex(z).imag] for z in row] for row in GAIN_COVARIANCE],
                deterministic_AF_arrays='fixed_inputs(N): explicit QPSK probabilities, pilot and algebraic test vector',
                model='independent path-Doppler factors; AF QPSK moments; full complex gain covariance',
                coordinate_score='likelihood log potential up to one additive constant; no prior fitted',
                negative_controls='single-path isotropic covariance: independent-copy loss and random-tangent inflation',
                reference='actual Channel basis action at N8/N16; streamed basis action at N1024, never dense there')


def fixed_inputs(n):
    k = np.arange(n)
    angle = 2*np.pi*k/n
    raw_probabilities = np.column_stack((1.4+.2*np.cos(angle), .9+.15*np.sin(2*angle+.1),
                                        1.1+.1*np.cos(3*angle+.2), .8+.12*np.sin(angle+.4)))
    probabilities = raw_probabilities/raw_probabilities.sum(axis=1, keepdims=True)
    qpsk = np.sqrt(DATA_POWER/2)*np.array([1+1j, 1-1j, -1+1j, -1-1j])
    mean = probabilities@qpsk
    variance = probabilities@(abs(qpsk)**2)-abs(mean)**2
    pilot = np.sqrt(.2)*np.exp(1j*(angle+.13*np.sin(angle)))
    y = .6*np.cos(.17*k)+.2*np.sin(.13*k)+1j*(.3*np.sin(.23*k)-.4*np.cos(.11*k))
    probe = (.3+.1*np.sin(angle))*np.exp(.7j*angle)+.2*np.exp(-1.3j*angle)
    second_probe = (.2+.03*k/n)*np.exp(-.4j*angle)
    return dict(probabilities=probabilities, qpsk=qpsk, pilot=pilot, data_mean=mean,
                data_variance=variance, y=y, probe=probe, second_probe=second_probe)


class ReferenceActions:
    """Count actual frozen physical calls, including each internal DAFT pair."""

    def __init__(self):
        self.counts = dict(channel_apply=0, channel_adjoint=0, channel_derivative=0,
                           channel_transform_vectors=0, explicit_daft_vectors=0,
                           streamed_basis_columns=0, dense_operator_matrices=0)

    def apply(self, channel, value):
        self.counts['channel_apply'] += 1
        self.counts['channel_transform_vectors'] += 2
        return channel.apply(value)

    def adjoint(self, channel, value):
        self.counts['channel_adjoint'] += 1
        self.counts['channel_transform_vectors'] += 2
        return channel.adjoint(value)

    def derivative(self, channel, value):
        self.counts['channel_derivative'] += 1
        self.counts['channel_transform_vectors'] += 2
        return channel.regressors(value, derivative=True)[:, 0]

    def transform(self, value, c1, c2, *, inverse=False):
        self.counts['explicit_daft_vectors'] += 1
        return daft(value, c1, c2, inverse=inverse)


def reference(n, delays, c1, c2, inputs):
    """Enumerate all fixed factors; stream columns once for all score nodes.

    The union includes the seven conditional-score nodes. Reusing each basis
    response avoids recomputing the same unit path for every pair combination.
    Only N8/N16 retain dense unit operators. N1024 stores O(N*P*Q) responses.
    """
    actions = ReferenceActions()
    points = [np.unique(np.r_[nodes, EVALUATION_NODES]) for nodes in DOPPLER_NODES]
    original_indices = [np.searchsorted(points[i], DOPPLER_NODES[i]) for i in range(2)]
    evaluation_indices = [np.searchsorted(points[i], EVALUATION_NODES) for i in range(2)]
    channels = [[Channel(n, c1, c2, [delays[i]], [value], [1.]) for value in points[i]] for i in range(2)]
    q = len(points[0])
    if len(points[1]) != q:
        raise ValueError('frozen reference requires equal union lengths')
    weights = np.array(WEIGHTS)
    gain_mean, gain_cov = np.array(GAIN_MEAN), np.array(GAIN_COVARIANCE)
    second = gain_cov+np.outer(gain_mean, gain_mean.conj())
    x = inputs['pilot']+inputs['data_mean']
    mean_responses = np.array([[actions.apply(channel, x) for channel in row] for row in channels])
    trace_self = np.zeros((2, q))
    trace_cross = np.zeros((q, q), complex)
    diagonal_by_pair = np.empty((3, 3, n), complex)
    norm_by_node = np.zeros((2, q))
    wrong_trace = tangent_trace = 0.
    center = float(np.dot(weights, DOPPLER_NODES[0]))
    residuals = np.array(DOPPLER_NODES[0])-center
    central_channel = Channel(n, c1, c2, [delays[0]], [center], [1.])
    dense = n <= 16
    operators = np.empty((2, q, n, n), complex) if dense else None
    tangent_operator = np.empty((n, n), complex) if dense else None
    derivative_operator = np.empty((n, n), complex) if dense else None
    if dense:
        actions.counts['dense_operator_matrices'] = 2*q+2
    basis = np.zeros(n, complex)
    for k in range(n):
        basis[k] = 1.
        responses = np.array([[actions.apply(channel, basis) for channel in row] for row in channels])
        norms = np.sum(abs(responses)**2, axis=2)
        cross = responses[0].conj()@responses[1].T
        norm_by_node += norms
        trace_self += inputs['data_variance'][k]*norms
        trace_cross += inputs['data_variance'][k]*cross
        for a, b in itertools.product(range(3), repeat=2):
            i, j = original_indices[0][a], original_indices[1][b]
            diagonal_by_pair[a, b, k] = (second[0, 0]*norms[0, i]+second[1, 1]*norms[1, j]+
                                          2*np.real(second[1, 0]*cross[i, j]))
        averaged = weights@responses[0, original_indices[0]]
        wrong_trace += float(np.vdot(averaged, averaged).real)
        central = actions.apply(central_channel, basis)
        derivative = actions.derivative(central_channel, basis)
        tangent_trace += sum(float(w*np.vdot(central+delta*derivative, central+delta*derivative).real)
                             for w, delta in zip(weights, residuals))
        if dense:
            operators[:, :, :, k] = responses
            tangent_operator[:, k], derivative_operator[:, k] = central, derivative
        actions.counts['streamed_basis_columns'] += 1
        basis[k] = 0.

    def at_pair(i, j):
        regressors = np.column_stack((mean_responses[0, i], mean_responses[1, j]))
        gamma = regressors.conj().T@regressors
        gamma[0, 0] += trace_self[0, i]
        gamma[1, 1] += trace_self[1, j]
        gamma[0, 1] += trace_cross[i, j]
        gamma[1, 0] += trace_cross[i, j].conjugate()
        matched = regressors.conj().T@inputs['y']
        value = (np.vdot(inputs['y'], inputs['y'])-
                 2*np.vdot(inputs['y'], regressors@gain_mean).real+np.sum(second.T*gamma))
        return value, gamma, matched

    quadratic = 0j
    gram_diagonal = np.zeros(n, complex)
    gram_matvec = np.zeros(n, complex)
    mean_adjoint = np.zeros(n, complex)
    gain_gram = np.zeros((2, 2), complex)
    gain_matched = np.zeros(2, complex)
    gram_dense = np.zeros((n, n), complex) if dense else None
    pair_values = np.empty((3, 3), complex)
    for a, b in itertools.product(range(3), repeat=2):
        i, j = original_indices[0][a], original_indices[1][b]
        probability = weights[a]*weights[b]
        value, gamma, matched = at_pair(i, j)
        pair_values[a, b] = value
        quadratic += probability*value
        gram_diagonal += probability*diagonal_by_pair[a, b]
        gain_gram += probability*gamma
        gain_matched += probability*matched
        selected = (channels[0][i], channels[1][j])
        if dense:
            unit = (operators[0, i], operators[1, j])
            gram = sum(second[v, u]*unit[u].conj().T@unit[v] for u in range(2) for v in range(2))
            gram_dense += probability*gram
            gram_matvec += probability*(gram@inputs['probe'])
            mean_adjoint += probability*sum(gain_mean[u].conjugate()*unit[u].conj().T@inputs['y'] for u in range(2))
        else:
            # Mean channel and full covariance use independent actual actions.
            channel = Channel(n, c1, c2, delays, [points[0][i], points[1][j]], gain_mean)
            acted = actions.apply(channel, inputs['probe'])
            value = actions.adjoint(channel, acted)
            unit_acted = [actions.apply(c, inputs['probe']) for c in selected]
            for u in range(2):
                for v in range(2):
                    value += gain_cov[v, u]*actions.adjoint(selected[u], unit_acted[v])
            gram_matvec += probability*value
            mean_adjoint += probability*actions.adjoint(channel, inputs['y'])

    conditional = np.empty((2, len(EVALUATION_NODES)), complex)
    for path in range(2):
        for u_index, point_index in enumerate(evaluation_indices[path]):
            value = 0j
            for other in range(3):
                pair = (point_index, original_indices[1][other]) if path == 0 else (original_indices[0][other], point_index)
                value += weights[other]*at_pair(*pair)[0]
            conditional[path, u_index] = -value/NOISE_VARIANCE

    stored = dict(points=np.array(points), prior_node_indices=np.array(original_indices),
                  mean_responses=mean_responses, variance_trace_self=trace_self,
                  variance_trace_cross=trace_cross, unit_norm_sums=norm_by_node,
                  pair_diagonal=diagonal_by_pair, pair_quadratic=pair_values,
                  quadratic=np.array(quadratic), gram_diagonal=gram_diagonal,
                  gram_matvec=gram_matvec, mean_adjoint=mean_adjoint,
                  gain_gram=gain_gram, gain_matched=gain_matched, conditional_scores=conditional)
    # Independent single-path covariance controls use the same draw on both
    # sides; these are separate data-only diagnostic quantities, not receivers.
    selected = [channels[0][idx] for idx in original_indices[0]]
    if dense:
        unit = operators[0, original_indices[0]]
        exact_cov = DATA_POWER*sum(w*u@u.conj().T for w, u in zip(weights, unit))
        averaged = np.einsum('q,qij->ij', weights, unit)
        wrong_cov = DATA_POWER*averaged@averaged.conj().T
        tangent_cov = DATA_POWER*sum(w*(tangent_operator+d*derivative_operator)@
                                     (tangent_operator+d*derivative_operator).conj().T
                                     for w, d in zip(weights, residuals))
        exact_action, wrong_action, tangent_action = (cov@inputs['probe'] for cov in (exact_cov, wrong_cov, tangent_cov))
        stored.update(dense_operators=operators, dense_gram=gram_dense, exact_isotropic_covariance=exact_cov,
                      independent_copy_covariance=wrong_cov, tangent_covariance=tangent_cov)
    else:
        exact_action = DATA_POWER*sum(w*actions.apply(c, actions.adjoint(c, inputs['probe'])) for w, c in zip(weights, selected))
        average_adjoint = sum(w*actions.adjoint(c, inputs['probe']) for w, c in zip(weights, selected))
        wrong_action = DATA_POWER*sum(w*actions.apply(c, average_adjoint) for w, c in zip(weights, selected))
        time_y = actions.transform(inputs['probe'], c1, c2, inverse=True)
        derivative_adjoint_input = actions.transform(-1j*(2*np.pi*np.arange(n)/n)*time_y, c1, c2)
        central_adjoint = actions.adjoint(central_channel, inputs['probe'])
        derivative_adjoint = actions.adjoint(central_channel, derivative_adjoint_input)
        tangent_action = np.zeros(n, complex)
        for w, delta in zip(weights, residuals):
            vector = central_adjoint+delta*derivative_adjoint
            tangent_action += DATA_POWER*w*(actions.apply(central_channel, vector)+
                                            delta*actions.derivative(central_channel, vector))
    stored.update(exact_isotropic_action=exact_action, independent_copy_action=wrong_action,
                  tangent_action=tangent_action,
                  exact_isotropic_trace=np.array(DATA_POWER*np.dot(weights, norm_by_node[0, original_indices[0]])),
                  independent_copy_trace=np.array(DATA_POWER*wrong_trace),
                  tangent_trace=np.array(DATA_POWER*tangent_trace), residual_dopplers=residuals)
    return stored, actions.counts


def record_error(checks, name, actual, expected, tolerance):
    actual, expected = np.asarray(actual), np.asarray(expected)
    if actual.shape != expected.shape:
        raise ValueError(f'{name}: incompatible comparison shapes')
    finite = bool(np.isfinite(actual).all() and np.isfinite(expected).all())
    error = float(np.linalg.norm(actual-expected)/max(1., float(np.linalg.norm(expected)))) if finite else None
    checks.append(dict(check=name, normalized_error=error, tolerance=tolerance,
                       passed=finite and error <= tolerance))


def verify_case(n, delays, inputs):
    started = time.perf_counter()
    c1, c2 = 5.3/(2*n), (np.sqrt(2)-1)/(2*n*n)
    weights = np.tile(WEIGHTS, (2, 1))
    model = PathMoments(n, c1, c2, np.array(delays), DOPPLER_NODES, weights, GAIN_MEAN, GAIN_COVARIANCE)
    source = model.prepare_source(inputs['pilot'], inputs['data_mean'], inputs['data_variance'])
    coefficients = model.coordinate_coefficients(inputs['y'], source)
    scores = np.array([coordinate_log_density(row, EVALUATION_NODES, NOISE_VARIANCE,
                                             np.zeros(len(EVALUATION_NODES))) for row in coefficients])
    gamma, matched = model.gain_statistics(inputs['y'], source)
    structured = dict(quadratic=np.array(model.expected_quadratic(inputs['y'], source)),
                      gram_diagonal=model.gram_diagonal(), gram_matvec=model.gram_matvec(inputs['probe']),
                      mean_adjoint=model.mean_adjoint(inputs['y']), gain_gram=gamma,
                      gain_matched=matched, conditional_scores=scores)
    independent, counts = reference(n, delays, c1, c2, inputs)
    tolerance = 1e-10 if n <= 16 else 1e-9
    checks = [dict(check='positive_nonuniform_AF_QPSK_variance',
                   minimum_variance=float(inputs['data_variance'].min()),
                   variance_range=float(np.ptp(inputs['data_variance'])),
                   passed=bool(inputs['data_variance'].min() > 0 and np.ptp(inputs['data_variance']) > 0 and
                               np.all(inputs['probabilities'] > 0) and
                               np.allclose(inputs['probabilities'].sum(axis=1), 1., atol=1e-14, rtol=0)))]
    for key in structured:
        left, right = structured[key], independent[key]
        if key == 'conditional_scores':
            left, right = left-left[:, :1], right-right[:, :1]
        record_error(checks, key, left, right, tolerance)
    record_error(checks, 'gain_gram_hermitian', gamma, gamma.conj().T, ROUNDOFF)
    eigenvalues = np.linalg.eigvalsh((gamma+gamma.conj().T)/2)
    checks.append(dict(check='gain_gram_psd', smallest_eigenvalue=float(eigenvalues[0]),
                       tolerance=ROUNDOFF*max(1., float(np.linalg.norm(gamma))),
                       passed=bool(eigenvalues[0] >= -ROUNDOFF*max(1., float(np.linalg.norm(gamma))))))
    second_acted = model.gram_matvec(inputs['second_probe'])
    record_error(checks, 'gram_hermitian_probe', np.vdot(inputs['second_probe'], structured['gram_matvec']),
                 np.vdot(second_acted, inputs['probe']), ROUNDOFF)
    probe_energy = np.vdot(inputs['probe'], structured['gram_matvec'])
    checks.append(dict(check='gram_psd_probe', real_energy=float(probe_energy.real),
                       imaginary_energy=float(probe_energy.imag),
                       passed=bool(probe_energy.real >= -ROUNDOFF*max(1., abs(probe_energy)))))
    if n <= 16:
        gram = independent['dense_gram']
        record_error(checks, 'dense_gram_diagonal', structured['gram_diagonal'], np.diag(gram), tolerance)
        record_error(checks, 'dense_gram_hermitian', gram, gram.conj().T, ROUNDOFF)
        eig = np.linalg.eigvalsh((gram+gram.conj().T)/2)
        checks.append(dict(check='dense_gram_psd', smallest_eigenvalue=float(eig[0]),
                           passed=bool(eig[0] >= -ROUNDOFF*max(1., float(np.linalg.norm(gram))))))

    time_axis = 2*np.pi*np.arange(n)/n
    phi = np.array(WEIGHTS)@np.exp(1j*np.array(DOPPLER_NODES[0])[:, None]*time_axis)
    residual_variance = float(np.dot(WEIGHTS, independent['residual_dopplers']**2))
    probe_time = daft(inputs['probe'], c1, c2, inverse=True)
    predicted_wrong_action = daft(DATA_POWER*abs(phi)**2*probe_time, c1, c2)
    predicted_tangent_action = daft(DATA_POWER*(1+residual_variance*time_axis**2)*probe_time, c1, c2)
    record_error(checks, 'single_path_isotropic_action', independent['exact_isotropic_action'], DATA_POWER*inputs['probe'], tolerance)
    record_error(checks, 'single_path_isotropic_trace', independent['exact_isotropic_trace'], DATA_POWER*n, tolerance)
    record_error(checks, 'independent_copy_predicted_action', independent['independent_copy_action'], predicted_wrong_action, tolerance)
    record_error(checks, 'independent_copy_predicted_trace', independent['independent_copy_trace'], DATA_POWER*np.sum(abs(phi)**2), tolerance)
    record_error(checks, 'tangent_predicted_action', independent['tangent_action'], predicted_tangent_action, tolerance)
    record_error(checks, 'tangent_predicted_trace', independent['tangent_trace'], DATA_POWER*np.sum(1+residual_variance*time_axis**2), tolerance)
    loss = float(DATA_POWER*n-independent['independent_copy_trace'])
    inflation = float(independent['tangent_trace']-DATA_POWER*n)
    checks.append(dict(check='negative_controls_nonzero_with_predicted_sign', independent_copy_trace_loss=loss,
                       tangent_trace_inflation=inflation, passed=bool(loss > tolerance and inflation > tolerance)))
    if n <= 16:
        identity = np.eye(n)*DATA_POWER
        record_error(checks, 'single_path_full_isotropic_covariance', independent['exact_isotropic_covariance'], identity, tolerance)

    arrays = {**inputs, 'delays': np.array(delays), 'c1': np.array(c1), 'c2': np.array(c2),
              'doppler_nodes': np.array(DOPPLER_NODES), 'doppler_weights': weights,
              'gain_mean': np.array(GAIN_MEAN), 'gain_covariance': np.array(GAIN_COVARIANCE),
              'evaluation_nodes': np.array(EVALUATION_NODES), 'source_responses': source.responses,
              'source_variance_fft': source.variance_fft, 'characteristic_moments': model.phi,
              'coordinate_coefficients': coefficients, 'gram_second_probe': second_acted,
              'predicted_wrong_action': predicted_wrong_action, 'predicted_tangent_action': predicted_tangent_action}
    arrays.update({f'structured_{key}': value for key, value in structured.items()})
    arrays.update({f'reference_{key}': value for key, value in independent.items()})
    if n == 1024 and any(value.ndim >= 2 and value.shape[-2:] == (n, n) for value in arrays.values()):
        raise RuntimeError('N1024 reference must not retain a dense operator')
    report = dict(N=n, delays=list(delays), checks=checks, passed=all(row['passed'] for row in checks),
                  reference_counts=counts, factor_combinations=9, conditional_other_factor_evaluations=42,
                  conditional_score_nodes=14, dense_reference=n <= 16,
                  structured_transform_counts=dict(model.work_counts),
                  auxiliary_control_transform_vectors=3,
                  elapsed_seconds=time.perf_counter()-started)
    return arrays, report


def validation_controls():
    inputs = fixed_inputs(8)
    base = dict(n=8, c1=5.3/16, c2=(np.sqrt(2)-1)/128, delays=np.array([0, 3]),
                doppler_nodes=DOPPLER_NODES, weights=np.tile(WEIGHTS, (2, 1)),
                gain_mean=GAIN_MEAN, gain_cov=GAIN_COVARIANCE)
    invalid = dict(noninteger_delay={'delays': np.array([0., 3.])},
                   invalid_weight={'weights': [[0., .7, .3], WEIGHTS]},
                   unnormalized_weight={'weights': [[.2, .5, .4], WEIGHTS]},
                   nonhermitian_covariance={'gain_cov': [[.31, .07+.09j], [.07+.09j, .23]]},
                   indefinite_covariance={'gain_cov': [[.1, .4j], [-.4j, .1]]},
                   nonfinite_gain={'gain_mean': [np.nan, 1.]},
                   node_shape={'doppler_nodes': [[.1, .2], [.3, .4]]})
    rows = []
    for name, change in invalid.items():
        try:
            PathMoments(**dict(base, **change))
        except ValueError as error:
            rows.append(dict(check=name, passed=True, expected_error=str(error)))
        else:
            rows.append(dict(check=name, passed=False, expected_error=None))
    model = PathMoments(**base)
    for name, variance in (('negative_data_variance', -np.ones(8)), ('wrong_data_variance_shape', np.ones(7))):
        try:
            model.prepare_source(inputs['pilot'], inputs['data_mean'], variance)
        except ValueError as error:
            rows.append(dict(check=name, passed=True, expected_error=str(error)))
        else:
            rows.append(dict(check=name, passed=False, expected_error=None))
    return rows


def array_hash(value):
    value = np.ascontiguousarray(value)
    h = hashlib.sha256(str(value.dtype).encode()+json.dumps(list(value.shape)).encode()+value.tobytes())
    return h.hexdigest()


def calculate(output):
    output = Path(output)
    reports = []
    for n, delays in CASES:
        # Persist a start marker before any numerical work; failures retain the
        # marker and all earlier complete cases under the immutable recorder.
        dump(output/f'n{n}_started.json', dict(N=n, delays=list(delays), geometry_probe=len(reports)+1))
        inputs = fixed_inputs(n)
        input_path = output/f'n{n}_inputs.npz'
        with input_path.open('xb') as handle:
            np.savez_compressed(handle, **inputs)
        arrays, report = verify_case(n, delays, inputs)
        path = output/f'n{n}_arrays.npz'
        with path.open('xb') as handle:
            np.savez_compressed(handle, **arrays)
        report.update(array_sha256={key: array_hash(value) for key, value in arrays.items()},
                      arrays_file=path.name, arrays_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      inputs_file=input_path.name, inputs_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest())
        dump(output/f'n{n}_checks.json', report)
        reports.append(report)
    controls = validation_controls()
    result = dict(geometry_probes=len(reports), new_observations=0, receiver_calls=0, decoder_calls=0,
                  seed='none', cases=reports, validation_controls=controls,
                  mathematical_checks_pass=all(row['passed'] for row in reports+controls),
                  scope='Deterministic mathematical verification only; no receiver, prior selection, performance or novelty claim.')
    dump(output/'verification.json', result)
    if not result['mathematical_checks_pass']:
        raise AssertionError('frozen mathematical verification failed; all completed checks retained')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--stage', default='MATH-01')
    parser.add_argument('--print-imports', action='store_true')
    args = parser.parse_args()
    # Access lazy function objects, but perform no numerical verification before
    # the shared recorder binds source, thread pools and resource reservations.
    _ = np.linalg.eigvalsh, np.fft.fft, np.savez_compressed, thread_binding.blas_binding
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.artifact_root is None or not args.artifact_root.is_absolute():
        parser.error('--artifact-root must be an absolute admitted output path')
    protocol.run(args.stage, configuration(), calculate, artifact_root=args.artifact_root.resolve())


if __name__ == '__main__':
    main()
