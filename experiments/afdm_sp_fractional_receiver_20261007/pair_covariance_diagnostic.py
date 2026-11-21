"""PAIR-COVARIANCE-MATH-01: admitted mathematics on the sealed MATH inputs.

Import preparation never evaluates a fixture. No receiver, decoder, generator,
new observation or random stream is called by the admitted diagnostic.
"""
import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np

from experiments.afdm_shared_channel_20261004.common import dump
from experiments.afdm_sp_fractional_20261007.moments import (
    PathMoments, ROUNDOFF, coordinate_log_density)
from . import collapsed_diagnostic as saved, protocol, runtime
from .continuous import count, finite

SOURCE_ATTEMPT = saved.SOURCE_ATTEMPT
SIZES = (8, 16, 1024)
CASE_NAMES = ('saved_diagonal', 'saved_complex', 'saved_boundary', 'point_complex',
              'single_complex', 'same_delay_complex', 'integer_chirp_complex')
REFERENCE_NAMES = ('saved_diagonal', 'saved_complex', 'saved_boundary',
                   'same_delay_complex', 'integer_chirp_complex')
SOURCE_CONTROLS = (
    'missing_pair_indices', 'missing_pair_covariance', 'float_pair_indices',
    'bool_pair_indices', 'wrong_pair_index_shape', 'repeated_endpoint', 'self_pair',
    'out_of_range_pair', 'negative_pair_index', 'nonfinite_pair_covariance',
    'wrong_pair_covariance_shape', 'non_psd_pair', 'zero_variance_nonzero_covariance',
    'foreign_owner', 'stale_geometry', 'stale_phi', 'input_mutation', 'immutable_arrays')
QUERY_CONTROLS = ('wrong_query_shape', 'float_query_indices', 'bool_query_indices',
                  'out_of_range_query')
SIGMA2 = .7
MAX_FILE_BYTES = 10_000_000


def configuration():
    return dict(seed='none', new_observations=0, independent_blocks=0, receiver_calls=0,
                receiver_boundary_rejection_calls=0, receiver_payload_executions=0,
                decoder_calls=0, backend_fixture_calls=0, new_geometry_probes=6,
                diagnostic='disjoint_pair_covariance_and_finite_Gram_entries',
                source_attempt=str(SOURCE_ATTEMPT), source_input_files=10,
                data_moments='original sealed MATH Pd=.55; boundary fixture is generic PSD, not QPSK posterior',
                cases=[dict(n=n, name=name, p=1 if name == 'single_complex' else 2)
                       for n in SIZES for name in CASE_NAMES],
                covariance_references=[dict(n=n, name=name) for n in SIZES for name in REFERENCE_NAMES],
                covariance_reference_count=15, derived_geometry_count=6,
                pair_indices='(N-1,0),(1,N/2),(N-2,2)',
                pair_rho=[[.3, .2], [0., -.4], [-.25, .15]],
                boundary=dict(pairs=[[0, 1], [2, 3]], variance_overrides={'0': .25, '1': .25, '2': 0., '3': .25},
                              covariance=[[.25, 0.], [0., 0.]]),
                point_nodes='first saved node per path', single_path='first saved path and gain marginal',
                same_delay='both paths use the second saved delay', integer_chirp='c1=5/(2*N)',
                gram_queries='(0,0),(N-1,N-1),(0,N-1),(N-1,0),(1,N/2),(N/2,1),'
                             '(N-2,2),(2,N-2),(0,N-1),(N/2+1,0),(0,N/2+1),(N/2-1,N/2+1)',
                gram_query_entries=252, gram_query_replay_entries=252, empty_query_calls=21,
                gram_reference_unique_symbols=8, gram_reference_path_nodes=105,
                source_ref_channel_calls=10506, source_ref_small_basis_calls=240,
                source_ref_sparse_factor_calls=10236, source_ref_mean_calls=30,
                source_ref_inverse_daft_calls=10506, source_ref_sparse_factor_columns=5118,
                gram_ref_channel_calls=1120, total_reference_channel_calls=11626,
                reference_observation_inverse_daft_calls=21,
                reference_residual_evaluations=840, reference_current_evaluations=147,
                reference_conditional_evaluations=693,
                source_controls=list(SOURCE_CONTROLS), query_controls=list(QUERY_CONTROLS),
                zero_variance_counterexample=dict(variance=[0., 1.], covariance=[0., 1e-6],
                    rule='exact zero variance requires exactly zero covariance before determinant tolerance'),
                default_empty_source_comparisons=3, production_path_moment_builds=21,
                production_source_preparations=24, production_source_pair_ifft_vectors=48,
                production_gram_query_fft_vectors=18,
                tolerance=dict(n8=1e-10, n16=1e-10, n1024=1e-9, hermitian_psd=ROUNDOFF),
                normalized_error='norm(actual-reference)/max(1,norm(reference))',
                noise_variance=SIGMA2, source_reference='actual Channel(nu=0) then inverse DAFT',
                large_reference='one sparse Cholesky column with at most two nonzeros; never an N-by-N array',
                gram_reference='actual Channel basis columns; full small G and only twelve large-N entries',
                wall_cap_seconds=120, cpu_cap_seconds=120, whole_process_timeout_seconds=150,
                termination_grace_seconds=10, max_process_memory_bytes=4*1024**3,
                output_limit_bytes=128*1024**2, per_file_limit_bytes=MAX_FILE_BYTES,
                scope='deterministic mathematical qualification only; no receiver benefit, speed or novelty claim')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _compare(name, actual, expected, tolerance, *, exact=False):
    row = saved._check(name, actual, expected, tolerance)
    actual, expected = np.asarray(actual), np.asarray(expected)
    row['byte_equal'] = bool(actual.dtype == expected.dtype and actual.shape == expected.shape and
                             actual.tobytes(order='C') == expected.tobytes(order='C'))
    row['exact_required'] = exact
    row['passed'] = row['passed'] and (not exact or row['byte_equal'])
    return row


def _boolean(name, passed, **details):
    return dict(name=name, passed=bool(passed), **details)


def _psd_checks(name, matrices):
    matrices = np.asarray(matrices)
    adjoint = matrices.swapaxes(-1, -2).conj()
    checks = [_compare(name+'_Hermitian', matrices, adjoint, ROUNDOFF)]
    # Symmetrization is only for measuring eigenvalues, never a repaired input.
    eigenvalues = np.linalg.eigvalsh((matrices+adjoint)/2)
    scales = np.maximum(1., np.linalg.norm(matrices, axis=(-2, -1)))
    finite(eigenvalues, name+' eigenvalues')
    checks.append(_boolean(name+'_PSD', np.all(eigenvalues[..., 0] >= -ROUNDOFF*scales),
                           minimum_eigenvalue=float(eigenvalues.min()),
                           maximum_tolerance=float(ROUNDOFF*np.max(scales))))
    return checks, eigenvalues


def _save_npz(rt, output, name, payload, role, partial, guard):
    start, cpu = time.perf_counter(), time.process_time()
    entry = dict(file=name, kind='npz', status='started')
    partial['serialization'].append(entry)
    guard.check()
    digest = runtime.save_new(rt, output/name, payload, dict(role=role))
    size = (output/name).stat().st_size
    entry.update(status='completed', sha256=digest, bytes=size,
                 seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
    _require(size < MAX_FILE_BYTES, 'diagnostic artifact exceeds the per-file size contract')
    guard.check(files=True, threads=True)
    return dict(file=name, sha256=digest, bytes=size)


def _save_json(output, name, payload, partial, guard):
    start, cpu = time.perf_counter(), time.process_time()
    entry = dict(file=name, kind='json', status='started')
    partial['serialization'].append(entry)
    dump(output/name, payload)
    entry.update(status='completed', bytes=(output/name).stat().st_size,
                 seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
    _require(entry['bytes'] < MAX_FILE_BYTES, 'diagnostic JSON exceeds the per-file size contract')
    guard.check(files=True)


def _spec(data, name):
    _require(name in CASE_NAMES, 'unregistered pair covariance case')
    n, inputs, arrays = data['n'], data['inputs'], data['arrays']
    p = 1 if name == 'single_complex' else 2
    variance = inputs['data_variance'].copy()
    pairs = np.empty((0, 2), int)
    covariance = np.empty(0, complex)
    if name == 'saved_boundary':
        pairs = np.array([[0, 1], [2, 3]])
        variance[:4] = [.25, .25, 0., .25]
        covariance = np.array([.25, 0.], complex)
    elif name != 'saved_diagonal':
        pairs = np.array([[n-1, 0], [1, n//2], [n-2, 2]])
        covariance = np.array([.3+.2j, -.4j, -.25+.15j])
        covariance *= np.sqrt(variance[pairs[:, 0]]*variance[pairs[:, 1]])
    delays = arrays['delays'][:p].copy()
    if name == 'same_delay_complex':
        delays[:] = arrays['delays'][1]
    nodes, weights = arrays['doppler_nodes'][:p].copy(), arrays['doppler_weights'][:p].copy()
    if name == 'point_complex':
        nodes, weights = nodes[:, :1], np.ones((p, 1))
    return dict(n=n, name=name, p=p, c1=5/(2*n) if name == 'integer_chirp_complex' else float(arrays['c1']),
                c2=float(arrays['c2']), delays=delays, nodes=nodes, weights=weights,
                gain_mean=arrays['gain_mean'][:p].copy(), gain_covariance=arrays['gain_covariance'][:p, :p].copy(),
                variance=variance, pair_indices=pairs, pair_covariance=covariance)


def _queries(n):
    return np.array([[0, 0], [n-1, n-1], [0, n-1], [n-1, 0], [1, n//2], [n//2, 1],
                     [n-2, 2], [2, n-2], [0, n-1], [n//2+1, 0], [0, n//2+1], [n//2-1, n//2+1]])


def _channel(rt, spec, path, doppler, counts, role):
    count(counts, role+'_channel_constructions')
    return rt.physical.Channel(spec['n'], spec['c1'], spec['c2'], spec['delays'][path:path+1],
                               [doppler], [1.+0j])


def _source_action(rt, channel, value, spec, counts, kind, guard):
    count(counts, kind)
    count(counts, 'source_ref_channel_calls')
    count(counts, 'total_reference_channel_calls')
    acted = channel.apply(value)
    count(counts, 'source_ref_inverse_daft_calls')
    result = rt.physical.daft(acted, spec['c1'], spec['c2'], inverse=True)
    guard.check()
    return result


def _sparse_factors(spec):
    """Yield independent columns of C=L L^H, each with at most two nonzeros."""
    variance = spec['variance']
    paired = set()
    for (u, v), covariance in zip(spec['pair_indices'], spec['pair_covariance']):
        u, v = int(u), int(v)
        paired.update((u, v))
        if variance[u] == 0:
            _require(covariance == 0, 'zero-variance reference block has nonzero covariance')
            if variance[v] > 0:
                yield [v], [np.sqrt(variance[v])]
            continue
        root = np.sqrt(variance[u])
        lower = covariance.conjugate()/root
        yield ([u, v], [root, lower]) if lower != 0 else ([u], [root])
        remainder = variance[v]-abs(lower)**2
        _require(remainder >= 0, 'negative sparse Cholesky remainder; no clipping is allowed')
        if remainder > 0:
            yield [v], [np.sqrt(remainder)]
    for index, variance_i in enumerate(variance):
        if index not in paired and variance_i > 0:
            yield [index], [np.sqrt(variance_i)]


def source_reference(rt, data, spec, result, counts, guard):
    n = spec['n']
    channels = [_channel(rt, spec, i, 0., counts, 'source_ref') for i in range(2)]
    covariance_time = np.zeros((2, 2, n), complex)
    mean_time = np.full((2, n), np.nan+1j*np.nan)
    result.update(spec=spec, covariance_time=covariance_time, mean_time=mean_time, checks=[])
    mean = data['inputs']['pilot']+data['inputs']['data_mean']
    for i, channel in enumerate(channels):
        mean_time[i] = _source_action(rt, channel, mean, spec, counts, 'source_ref_mean_calls', guard)
        result['mean_paths_completed'] = i+1
    if n <= 16:
        operators = np.full((2, n, n), np.nan+1j*np.nan)
        covariance = np.diag(spec['variance'].astype(complex))
        for (u, v), value in zip(spec['pair_indices'], spec['pair_covariance']):
            covariance[u, v], covariance[v, u] = value, value.conjugate()
        result.update(dense_source_operators=operators, dense_data_covariance=covariance)
        basis = np.zeros(n, complex)
        for index in range(n):
            basis[index] = 1.
            result['basis_index_started'] = index
            for i, channel in enumerate(channels):
                operators[i, :, index] = _source_action(
                    rt, channel, basis, spec, counts, 'source_ref_small_basis_calls', guard)
            basis[index] = 0.
            result['basis_columns_completed'] = index+1
        for i in range(2):
            for j in range(2):
                covariance_time[i, j] = np.sum((operators[i]@covariance)*operators[j].conj(), axis=1)
        checks, eigenvalues = _psd_checks('reference_data_covariance', covariance)
        result['checks'].extend(checks)
        result['data_covariance_eigenvalues'] = eigenvalues
        count(counts, 'source_ref_dense_covariances')
        count(counts, 'source_ref_dense_operator_matrices', 2)
    else:
        column = np.zeros(n, complex)
        factors, trace = 0, 0.
        for indices, values in _sparse_factors(spec):
            guard.check()
            _require(1 <= len(indices) <= 2, 'sparse factor has more than two nonzeros')
            column[indices] = values
            result['last_factor_indices'] = np.asarray(indices)
            result['last_factor_values'] = np.asarray(values)
            response = np.array([_source_action(rt, channel, column, spec, counts,
                                 'source_ref_sparse_factor_calls', guard) for channel in channels])
            result['last_factor_responses'] = response
            covariance_time += response[:, None, :]*response[None, :, :].conj()
            trace += float(np.sum(abs(np.asarray(values))**2))
            column[indices] = 0.
            factors += 1
            result['factor_columns_completed'] = factors
            count(counts, 'source_ref_sparse_factor_columns')
        expected_factors = n-2 if spec['name'] == 'saved_boundary' else n
        result['checks'].extend([
            _boolean('sparse_factor_count', factors == expected_factors, actual=factors, expected=expected_factors),
            _compare('sparse_factor_trace', trace, spec['variance'].sum(), 1e-9)])
        result['factor_trace'] = trace
    finite(covariance_time, 'physical source covariance')
    finite(mean_time, 'physical source mean')
    checks, eigenvalues = _psd_checks('reference_time_covariance', covariance_time.transpose(2, 0, 1))
    result['checks'].extend(checks)
    result['time_covariance_eigenvalues'] = eigenvalues
    result['checks'].append(_compare('reference_covariance_trace',
        covariance_time[np.arange(2), np.arange(2)].sum(axis=1),
        np.full(2, spec['variance'].sum()), 1e-9 if n == 1024 else 1e-10))
    result['status'] = 'completed'
    result['passed'] = all(row['passed'] for row in result['checks'])
    count(counts, 'covariance_references_completed')
    if spec['name'] in ('same_delay_complex', 'integer_chirp_complex'):
        count(counts, 'derived_geometries_completed')
    guard.check()


def _residual_at(spec, source_cross, mean_time, time_y, dopplers, counts, guard):
    """Direct time-domain R/f at one joint node; no production moment calls."""
    count(counts, 'reference_residual_evaluations')
    guard.check()
    phase = np.exp(2j*np.pi*np.asarray(dopplers)[:, None]*np.arange(spec['n'])/spec['n'])
    responses = phase*mean_time
    cross = source_cross*phase[:, None, :]*phase[None, :, :].conj()
    gram = cross.sum(axis=2).T
    matched = responses.conj()@time_y
    second = spec['gain_covariance']+np.outer(spec['gain_mean'], spec['gain_mean'].conj())
    residual = (np.vdot(time_y, time_y)-2*np.vdot(spec['gain_mean'], matched).real+
                np.sum(second.T*gram))
    finite(gram, 'reference residual Gram')
    finite(matched, 'reference residual matched vector')
    finite(residual, 'reference residual')
    _require(abs(residual.imag) <= ROUNDOFF*max(1., abs(residual)), 'nonreal physical residual reference')
    count(counts, 'reference_residual_evaluations_completed')
    return dict(dopplers=np.asarray(dopplers), gram=gram, matched=matched, quadratic=float(residual.real),
                quadratic_complex=np.asarray(residual))


def residual_reference(rt, data, spec, source_ref, result, counts, guard):
    p, n = spec['p'], spec['n']
    mean_time = source_ref['mean_time'][:p]
    covariance_time = source_ref['covariance_time'][:p, :p]
    source_cross = covariance_time+mean_time[:, None, :]*mean_time[None, :, :].conj()
    count(counts, 'reference_observation_inverse_daft_calls')
    time_y = rt.physical.daft(data['inputs']['y'], spec['c1'], spec['c2'], inverse=True)
    result.update(mean_time=mean_time, covariance_time=covariance_time, source_cross=source_cross,
                  time_y=time_y, evaluations=[], gram=np.zeros((p, p), complex),
                  matched=np.zeros(p, complex), quadratic=0.)
    nodes, weights = spec['nodes'], spec['weights']
    for indices in itertools.product(range(nodes.shape[1]), repeat=p):
        probability = float(np.prod([weights[i, index] for i, index in enumerate(indices)]))
        dopplers = [nodes[i, index] for i, index in enumerate(indices)]
        value = _residual_at(spec, source_cross, mean_time, time_y, dopplers, counts, guard)
        value.update(role='current', indices=list(indices), probability=probability)
        result['evaluations'].append(value)
        result['gram'] += probability*value['gram']
        result['matched'] += probability*value['matched']
        result['quadratic'] += probability*value['quadratic']
        count(counts, 'reference_current_evaluations')
    evaluation_nodes = data['arrays']['evaluation_nodes']
    scores = np.zeros((p, len(evaluation_nodes)))
    result['conditional_scores'] = scores
    for coordinate in range(p):
        others = [i for i in range(p) if i != coordinate]
        for evaluation_index, evaluation_node in enumerate(evaluation_nodes):
            for indices in itertools.product(range(nodes.shape[1]), repeat=len(others)):
                probability = float(np.prod([weights[i, index] for i, index in zip(others, indices)]))
                dopplers = np.empty(p)
                dopplers[coordinate] = evaluation_node
                for i, index in zip(others, indices):
                    dopplers[i] = nodes[i, index]
                value = _residual_at(spec, source_cross, mean_time, time_y, dopplers, counts, guard)
                value.update(role='conditional', coordinate=coordinate, evaluation_index=evaluation_index,
                             other_indices=list(indices), probability=probability)
                result['evaluations'].append(value)
                scores[coordinate, evaluation_index] -= probability*value['quadratic']/SIGMA2
                count(counts, 'reference_conditional_evaluations')
    coefficients = spec['gain_mean'][:, None]*mean_time*time_y.conj()
    second = spec['gain_covariance']+np.outer(spec['gain_mean'], spec['gain_mean'].conj())
    # Average each other-path phase explicitly; the independent conditional
    # residual enumeration above also checks the complete Fourier potential.
    time_axis = 2*np.pi*np.arange(n)/n
    for i in range(p):
        for j in range(p):
            if i == j:
                continue
            for node, weight in zip(nodes[j], weights[j]):
                coefficients[i] -= weight*second[i, j]*source_cross[i, j]*np.exp(-1j*time_axis*node)
                count(counts, 'reference_coefficient_path_node_terms', n)
    result.update(coordinate_coefficients=coefficients, status='completed')
    guard.check()


def gram_reference(rt, data, spec, queries, result, counts, guard):
    n, p = spec['n'], spec['p']
    symbols = np.arange(n) if n <= 16 else np.unique(queries)
    _require(len(np.unique(queries)) == 8, 'the fixed query union must contain eight symbols')
    nodes, weights = spec['nodes'], spec['weights']
    columns = np.full((p, nodes.shape[1], n, len(symbols)), np.nan+1j*np.nan)
    result.update(symbols=symbols, columns=columns, entries=np.zeros(len(queries), complex))
    basis = np.zeros(n, complex)
    for i in range(p):
        for node_index, node in enumerate(nodes[i]):
            channel = _channel(rt, spec, i, node, counts, 'gram_ref')
            count(counts, 'gram_ref_path_nodes')
            for symbol_index, symbol in enumerate(symbols):
                result['column_started'] = dict(path=i, node=node_index, symbol=int(symbol))
                basis[symbol] = 1.
                count(counts, 'gram_ref_channel_calls')
                count(counts, 'total_reference_channel_calls')
                columns[i, node_index, :, symbol_index] = channel.apply(basis)
                basis[symbol] = 0.
                count(counts, 'gram_ref_columns_completed')
                guard.check()
    second = spec['gain_covariance']+np.outer(spec['gain_mean'], spec['gain_mean'].conj())
    positions = {int(symbol): index for index, symbol in enumerate(symbols)}
    if n <= 16:
        result['dense_gram'] = np.zeros((n, n), complex)
    for indices in itertools.product(range(nodes.shape[1]), repeat=p):
        probability = float(np.prod([weights[i, index] for i, index in enumerate(indices)]))
        for i in range(p):
            for j in range(p):
                left, right = columns[i, indices[i]], columns[j, indices[j]]
                weight = probability*second[j, i]
                if n <= 16:
                    result['dense_gram'] += weight*(left.conj().T@right)
                    count(counts, 'gram_ref_column_inner_products', n*n)
                else:
                    for query_index, (u, v) in enumerate(queries):
                        result['entries'][query_index] += weight*np.vdot(left[:, positions[int(u)]],
                                                                         right[:, positions[int(v)]])
                        count(counts, 'gram_ref_column_inner_products')
        count(counts, 'gram_ref_joint_combinations')
        guard.check()
    if n <= 16:
        result['entries'] = result['dense_gram'][queries[:, 0], queries[:, 1]]
        checks, eigenvalues = _psd_checks('reference_dense_Gram', result['dense_gram'])
        result.update(checks=checks, eigenvalues=eigenvalues)
    else:
        result['checks'] = []
    finite(result['entries'], 'physical Gram entry reference')
    result['status'] = 'completed'


def _operator(spec, ledger):
    count(ledger['counts'], 'path_moment_builds_started')
    op = PathMoments(spec['n'], spec['c1'], spec['c2'], spec['delays'], spec['nodes'], spec['weights'],
                     spec['gain_mean'], spec['gain_covariance'])
    ledger['path_work'].append(op.work_counts)
    count(ledger['counts'], 'path_moment_builds_completed')
    return op


def _source(op, data, spec, ledger, *, empty=False, arguments=None):
    count(ledger['counts'], 'source_preparations')
    if arguments is not None:
        return op.prepare_source(**arguments)
    kwargs = {}
    if empty:
        kwargs = dict(pair_indices=np.empty((0, 2), int), pair_covariance=np.empty(0, complex))
    elif len(spec['pair_indices']):
        kwargs = dict(pair_indices=spec['pair_indices'], pair_covariance=spec['pair_covariance'])
    return op.prepare_source(data['inputs']['pilot'], data['inputs']['data_mean'], spec['variance'], **kwargs)


def source_metrics(op, source, data, ledger, result, *, data_operators=False):
    y, evaluation_nodes = data['inputs']['y'], data['arrays']['evaluation_nodes']
    cross = np.full((op.p, op.p, op.n), np.nan+1j*np.nan)
    result.update(mean=source.mean, variance=source.variance, pair_indices=source.pair_indices,
                  pair_covariance=source.pair_covariance, responses=source.responses,
                  variance_fft=source.variance_fft, energy=np.asarray(source.energy), source_cross=cross)
    for i in range(op.p):
        for j in range(op.p):
            cross[i, j] = op._cross_source(source, i, j)
            count(ledger['counts'], 'source_kernel_queries')
    result['covariance_time'] = cross-source.responses[:, None, :]*source.responses[None, :, :].conj()
    coefficients = op.coordinate_coefficients(y, source)
    result['coordinate_coefficients'] = coefficients
    count(ledger['counts'], 'coordinate_coefficients_calls')
    scores = np.array([coordinate_log_density(row, evaluation_nodes, SIGMA2, np.zeros(len(evaluation_nodes)))
                       for row in coefficients])
    gram, matched = op.gain_statistics(y, source)
    count(ledger['counts'], 'gain_statistics_calls')
    quadratic = np.asarray(op.expected_quadratic(y, source))
    count(ledger['counts'], 'expected_quadratic_calls')
    result.update(gram=gram, matched=matched, quadratic=quadratic, conditional_scores=scores)
    if data_operators:
        result.update(gram_matvec=op.gram_matvec(data['inputs']['probe']), gram_diagonal=op.gram_diagonal(),
                      mean_adjoint=op.mean_adjoint(y))
    return result


def run_case(rt, data, spec, source_ref, result, reference_counts, guard):
    n, p = spec['n'], spec['p']
    tolerance = 1e-9 if n == 1024 else 1e-10
    result.update(spec=spec, source_reference_artifact=source_ref['artifact'],
                  inputs={key: data['inputs'][key] for key in ('pilot', 'data_mean', 'y', 'probe')},
                  evaluation_nodes=data['arrays']['evaluation_nodes'], checks=[], actual={},
                  residual_reference={}, gram_reference={})
    checks = result['checks']
    op = _operator(spec, result)
    source = _source(op, data, spec, result)
    before = dict(op.work_counts)
    empty_query = op.gram_entries(np.empty((0, 2), int))
    result['empty_query'] = dict(values=empty_query, before=before, after=dict(op.work_counts))
    checks.append(_boolean('empty_query_builds_no_Z', empty_query.shape == (0,) and
        op.work_counts.get('gram_query_fft_vectors', 0) == before.get('gram_query_fft_vectors', 0) and
        op.work_counts['ordinary_fft_vectors'] == before['ordinary_fft_vectors']))
    count(result['counts'], 'empty_query_calls')
    actual = source_metrics(op, source, data, result, result['actual'],
                            data_operators=spec['name'] == 'saved_diagonal')
    if spec['name'] == 'saved_diagonal':
        empty_source = _source(op, data, spec, result, empty=True)
        result['explicit_empty_source'] = {}
        empty_metrics = source_metrics(op, empty_source, data, result, result['explicit_empty_source'],
                                       data_operators=True)
        for key in actual:
            checks.append(_compare('default_empty_'+key, empty_metrics[key], actual[key], 0., exact=True))
        count(result['counts'], 'default_empty_source_comparisons')
        sealed_names = dict(responses='source_responses', variance_fft='source_variance_fft',
                            coordinate_coefficients='coordinate_coefficients', quadratic='structured_quadratic',
                            gram='structured_gain_gram', matched='structured_gain_matched',
                            gram_matvec='structured_gram_matvec', gram_diagonal='structured_gram_diagonal',
                            mean_adjoint='structured_mean_adjoint', conditional_scores='structured_conditional_scores')
        result['sealed_reference_arrays'] = {key: data['arrays'][name] for key, name in sealed_names.items()}
        for key, reference in result['sealed_reference_arrays'].items():
            checks.append(_compare('sealed_MATH_'+key, actual[key], reference, tolerance))
    residual_reference(rt, data, spec, source_ref, result['residual_reference'], reference_counts, guard)
    reference = result['residual_reference']
    for key, reference_key in (('responses', 'mean_time'), ('source_cross', 'source_cross'),
                               ('covariance_time', 'covariance_time'), ('gram', 'gram'), ('matched', 'matched'),
                               ('quadratic', 'quadratic'), ('coordinate_coefficients', 'coordinate_coefficients')):
        checks.append(_compare(key, actual[key], reference[reference_key], tolerance))
    checks.append(_compare('conditional_scores_up_to_constant',
        actual['conditional_scores']-actual['conditional_scores'][:, :1],
        reference['conditional_scores']-reference['conditional_scores'][:, :1], tolerance))
    checks.append(_compare('covariance_trace', actual['covariance_time'][np.arange(p), np.arange(p)].sum(axis=1),
                           np.full(p, spec['variance'].sum()), tolerance))
    energy = float(np.vdot(data['inputs']['pilot']+data['inputs']['data_mean'],
                           data['inputs']['pilot']+data['inputs']['data_mean']).real+spec['variance'].sum())
    checks.append(_compare('source_energy', actual['energy'], energy, tolerance))
    checks.append(_compare('regressor_self_trace', np.diag(actual['gram']), np.full(p, energy), tolerance))
    time_checks, time_eigenvalues = _psd_checks('actual_time_covariance', actual['covariance_time'].transpose(2, 0, 1))
    gram_checks, gram_eigenvalues = _psd_checks('actual_gain_Gram', actual['gram'])
    ref_checks, ref_eigenvalues = _psd_checks('reference_gain_Gram', reference['gram'])
    checks.extend(time_checks+gram_checks+ref_checks)
    result.update(time_covariance_eigenvalues=time_eigenvalues, gain_gram_eigenvalues=gram_eigenvalues,
                  reference_gain_gram_eigenvalues=ref_eigenvalues)
    canonical_pairs = np.sort(spec['pair_indices'], axis=1)
    canonical_covariance = spec['pair_covariance'].copy()
    reverse = spec['pair_indices'][:, 0] > spec['pair_indices'][:, 1]
    canonical_covariance[reverse] = canonical_covariance[reverse].conj()
    checks.extend([_compare('canonical_pairs', source.pair_indices, canonical_pairs, 0., exact=True),
                   _compare('canonical_covariance', source.pair_covariance, canonical_covariance, 0., exact=True)])
    queries = _queries(n)
    result['queries'] = queries
    gram_reference(rt, data, spec, queries, result['gram_reference'], reference_counts, guard)
    before = dict(op.work_counts)
    entries = op.gram_entries(queries)
    after = dict(op.work_counts)
    replay = op.gram_entries(queries)
    result['query_actual'] = dict(entries=entries, replay=replay, before=before,
                                  after=after, after_replay=dict(op.work_counts))
    count(result['counts'], 'first_query_entries', len(queries))
    count(result['counts'], 'replay_query_entries', len(queries))
    checks.extend(result['gram_reference']['checks'])
    checks.extend([
        _compare('finite_Gram_entries', entries, result['gram_reference']['entries'], tolerance),
        _compare('Gram_query_replay', replay, entries, 0., exact=True),
        _boolean('Gram_first_query_FFT_count',
                 after.get('gram_query_fft_vectors', 0)-before.get('gram_query_fft_vectors', 0) == p*(p-1)//2),
        _boolean('Gram_replay_no_new_FFT',
                 op.work_counts.get('gram_query_fft_vectors', 0) == after.get('gram_query_fft_vectors', 0) and
                 op.work_counts['ordinary_fft_vectors'] == after['ordinary_fft_vectors']),
        _compare('Gram_query_Hermitian', entries[[2, 4, 6, 9]], entries[[3, 5, 7, 10]].conj(), ROUNDOFF),
        _compare('Gram_repeated_query', entries[8], entries[2], 0., exact=True),
        _compare('Gram_real_diagonal', entries[:2].imag, np.zeros(2), ROUNDOFF)])
    result.update(status='completed', passed=all(row['passed'] for row in checks))
    guard.check()


def _expect_value_error(row, operation, fragment):
    row['expected_error'] = dict(type='ValueError', message_contains=fragment)
    try:
        value = operation()
    except ValueError as error:
        row.update(actual_error=dict(type=type(error).__name__, message=str(error)),
                   passed=fragment in str(error))
    except Exception as error:
        row.update(actual_error=dict(type=type(error).__name__, message=str(error)), passed=False)
        raise
    else:
        row.update(actual_error=None, unexpected_return_type=type(value).__name__, passed=False)


def _source_arrays(source):
    return {name: getattr(source, name).copy() for name in
            ('mean', 'variance', 'responses', 'variance_fft', 'pair_indices', 'pair_covariance')}


def _arguments(data, spec):
    return dict(pilot=data['inputs']['pilot'].copy(), data_mean=data['inputs']['data_mean'].copy(),
                data_variance=spec['variance'].copy(), pair_indices=spec['pair_indices'].copy(),
                pair_covariance=spec['pair_covariance'].copy())


def source_control(data, name, row):
    spec = _spec(data, 'saved_complex')
    op = _operator(spec, row)
    arguments = _arguments(data, spec)
    if name in SOURCE_CONTROLS[:13]:
        arguments.update(pair_indices=np.array([[0, 1]]), pair_covariance=np.array([.01j]))
        fragment = 'integer indices'
        if name == 'missing_pair_indices':
            arguments.pop('pair_indices')
            fragment = 'supplied together'
        elif name == 'missing_pair_covariance':
            arguments.pop('pair_covariance')
            fragment = 'supplied together'
        elif name == 'float_pair_indices':
            arguments['pair_indices'] = np.array([[0., 1.]])
        elif name == 'bool_pair_indices':
            arguments['pair_indices'] = np.array([[False, True]])
        elif name == 'wrong_pair_index_shape':
            arguments['pair_indices'] = np.array([0, 1])
            fragment = 'shape'
        elif name == 'repeated_endpoint':
            arguments.update(pair_indices=np.array([[0, 1], [1, 2]]), pair_covariance=np.array([.01j, .02j]))
            fragment = 'disjoint endpoints'
        elif name == 'self_pair':
            arguments['pair_indices'] = np.array([[1, 1]])
            fragment = 'endpoints must differ'
        elif name == 'out_of_range_pair':
            arguments['pair_indices'] = np.array([[0, data['n']]])
            fragment = 'outside [0,N)'
        elif name == 'negative_pair_index':
            arguments['pair_indices'] = np.array([[-1, 1]])
            fragment = 'outside [0,N)'
        elif name == 'nonfinite_pair_covariance':
            arguments['pair_covariance'] = np.array([np.nan+1j])
            fragment = 'finite values'
        elif name == 'wrong_pair_covariance_shape':
            arguments['pair_covariance'] = np.array([[.01j]])
            fragment = 'expected length'
        elif name == 'non_psd_pair':
            variance = arguments['data_variance']
            arguments['pair_covariance'] = np.array([2*np.sqrt(variance[0]*variance[1])])
            fragment = 'PSD'
        elif name == 'zero_variance_nonzero_covariance':
            arguments['data_variance'][:2] = [0., 1.]
            arguments['pair_covariance'] = np.array([1e-6j])
            fragment = 'zero AF data variance requires zero pair covariance'
            row['counterexample'] = dict(old_normalized_determinant_left=1e-12,
                old_normalized_determinant_right=ROUNDOFF,
                exact_support_rule='variance zero implies covariance exactly zero')
        row['arguments'] = arguments
        _expect_value_error(row, lambda: _source(op, data, spec, row, arguments=arguments), fragment)
        return
    row['arguments_before'] = {key: value.copy() for key, value in arguments.items()}
    source = _source(op, data, spec, row, arguments=arguments)
    row['source_before'] = _source_arrays(source)
    if name == 'foreign_owner':
        other = _operator(spec, row)
        _expect_value_error(row, lambda: other.expected_quadratic(data['inputs']['y'], source), 'another path model')
    elif name == 'stale_geometry':
        op.c1 += 1/(data['n']**2)
        row['replaced_c1'] = op.c1
        _expect_value_error(row, lambda: op.expected_quadratic(data['inputs']['y'], source), 'geometry')
    elif name == 'stale_phi':
        op.phi = op.phi.copy()
        row['replacement_phi'] = op.phi
        _expect_value_error(row, lambda: op.expected_quadratic(data['inputs']['y'], source), 'characteristic')
    elif name == 'input_mutation':
        before_cross = op._cross_source(source, 0, 1).copy()
        arguments['pilot'][0] += 1+.5j
        arguments['data_mean'][1] -= .7j
        arguments['data_variance'][:] = 0.
        arguments['pair_indices'][:] = 0
        arguments['pair_covariance'][:] = 0.
        after = _source_arrays(source)
        checks = [_compare('protected_'+key, after[key], value, 0., exact=True)
                  for key, value in row['source_before'].items()]
        after_cross = op._cross_source(source, 0, 1)
        checks.append(_compare('protected_cached_cross', after_cross, before_cross, 0., exact=True))
        row.update(arguments_after=arguments, source_after=after, before_cross=before_cross,
                   after_cross=after_cross, checks=checks, passed=all(check['passed'] for check in checks))
    elif name == 'immutable_arrays':
        targets = [('source.'+key, getattr(source, key)) for key in row['source_before']]
        targets.extend([('model.delays', op.delays), ('model.phi', op.phi)])
        attempts = []
        row['attempts'] = attempts
        for label, array in targets:
            for operation_name in ('direct_write', 'enable_write'):
                attempt = dict(array=label, operation=operation_name)
                attempts.append(attempt)

                def operation(value=array, kind=operation_name):
                    if kind == 'enable_write':
                        value.setflags(write=True)
                    else:
                        value.flat[0] = 0

                _expect_value_error(attempt, operation, 'WRITEABLE' if operation_name == 'enable_write' else 'read-only')
        row['passed'] = all(attempt['passed'] for attempt in attempts)
    else:
        raise ValueError('unregistered source control')


def query_control(data, name, row):
    op = _operator(_spec(data, 'saved_complex'), row)
    if name == 'wrong_query_shape':
        query, fragment = np.array([0, 1]), 'shape'
    elif name == 'float_query_indices':
        query, fragment = np.array([[0., 1.]]), 'integer indices'
    elif name == 'bool_query_indices':
        query, fragment = np.array([[False, True]]), 'integer indices'
    elif name == 'out_of_range_query':
        query, fragment = np.array([[0, data['n']]]), 'outside [0,N)'
    else:
        raise ValueError('unregistered query control')
    row['query'] = query
    before = dict(op.work_counts)
    _expect_value_error(row, lambda: op.gram_entries(query), fragment)
    row['work_before'] = before
    row['work_after'] = dict(op.work_counts)
    row['no_query_fft'] = op.work_counts.get('gram_query_fft_vectors', 0) == before.get('gram_query_fft_vectors', 0)
    row['passed'] = row['passed'] and row['no_query_fft']


def run_controls(data, result, guard):
    _require(data['n'] == 8, 'controls must reuse the saved N8 input')
    result.update(source=[], query=[], counts={})
    for name in SOURCE_CONTROLS:
        row = dict(name=name, status='started', counts={}, path_work=[])
        result['source'].append(row)
        source_control(data, name, row)
        row['status'] = 'completed'
        count(result['counts'], 'source_controls_completed')
        guard.check()
    for name in QUERY_CONTROLS:
        row = dict(name=name, status='started', counts={}, path_work=[])
        result['query'].append(row)
        query_control(data, name, row)
        row['status'] = 'completed'
        count(result['counts'], 'query_controls_completed')
        guard.check()
    result.update(status='completed', passed=all(row['passed'] for row in result['source']+result['query']))


def _add_counts(target, source):
    for key, value in source.items():
        count(target, key, value)


def _no_dense_large_arrays(value, n):
    if isinstance(value, np.ndarray):
        _require(value.ndim < 2 or value.shape[-2:] != (n, n), 'N1024 evidence contains a dense N-by-N array')
    elif isinstance(value, dict):
        for item in value.values():
            _no_dense_large_arrays(item, n)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_dense_large_arrays(item, n)


def _allocation_checks(partial, controls):
    expected = dict(covariance_references_completed=15, derived_geometries_completed=6,
                    source_ref_small_basis_calls=240, source_ref_sparse_factor_calls=10236,
                    source_ref_mean_calls=30, source_ref_channel_calls=10506,
                    source_ref_inverse_daft_calls=10506, source_ref_sparse_factor_columns=5118,
                    gram_ref_path_nodes=105, gram_ref_channel_calls=1120,
                    gram_ref_columns_completed=1120, total_reference_channel_calls=11626,
                    reference_observation_inverse_daft_calls=21, reference_residual_evaluations=840,
                    reference_residual_evaluations_completed=840,
                    reference_current_evaluations=147, reference_conditional_evaluations=693)
    checks = [_boolean('allocation_'+key, partial['reference_counts'].get(key, 0) == value,
                        actual=partial['reference_counts'].get(key, 0), expected=value)
              for key, value in expected.items()]
    expected_production = dict(path_moment_builds_completed=21, source_preparations=24,
                               empty_query_calls=21, first_query_entries=252, replay_query_entries=252,
                               default_empty_source_comparisons=3)
    checks.extend(_boolean('allocation_production_'+key, partial['production_counts'].get(key, 0) == value,
                           actual=partial['production_counts'].get(key, 0), expected=value)
                  for key, value in expected_production.items())
    for key, value in (('source_pair_ifft_vectors', 48), ('gram_query_fft_vectors', 18)):
        checks.append(_boolean('allocation_'+key, partial['path_work_totals'].get(key, 0) == value,
                               actual=partial['path_work_totals'].get(key, 0), expected=value))
    checks.extend([
        _boolean('allocation_case_order', [(row['n'], row['name']) for row in partial['cases']] ==
                 [(n, name) for n in SIZES for name in CASE_NAMES]),
        _boolean('allocation_reference_order', [(row['n'], row['name']) for row in partial['references']] ==
                 [(n, name) for n in SIZES for name in REFERENCE_NAMES]),
        _boolean('allocation_source_controls', [row['name'] for row in controls['source']] == list(SOURCE_CONTROLS)),
        _boolean('allocation_query_controls', [row['name'] for row in controls['query']] == list(QUERY_CONTROLS)),
        _boolean('allocation_observed_Channel_calls',
                 partial['mathematical_operations'].get('channel_apply_calls', 0) == 11626,
                 actual=partial['mathematical_operations'].get('channel_apply_calls', 0), expected=11626),
        _boolean('no_reference_adjoint_regressor_or_LDPC_calls',
                 all(value == 0 for key, value in partial['mathematical_operations'].items()
                     if key in ('channel_adjoint_calls', 'channel_regressors_calls') or key.startswith('forbidden_')))])
    return checks


def calculate(rt, output, guard, source):
    output = Path(output)
    partial = dict(status='started', references=[], cases=[], reference_counts={}, production_counts={},
                   path_work_totals={}, serialization=[], active=None)
    try:
        data_sets, hashes = saved.load_inputs(source, guard)
        _require(len(hashes) == 10 and [data['n'] for data in data_sets] == list(SIZES),
                 'original MATH input allocation differs')
        _save_json(output, 'input_identity.json', dict(source=str(source), sha256=hashes), partial, guard)
        partial['input_sha256'] = hashes
        with runtime.observe_operations(rt, guard.check) as operations:
            partial['mathematical_operations'] = operations
            for data in data_sets:
                n = data['n']
                _require(data['arrays']['doppler_nodes'].shape == (2, 3) and
                         data['arrays']['doppler_weights'].shape == (2, 3) and
                         data['arrays']['evaluation_nodes'].shape == (7,), 'saved Doppler law allocation differs')
                references = {}
                for name in REFERENCE_NAMES:
                    guard.check()
                    spec = _spec(data, name)
                    result = dict(n=n, name=name, status='started')
                    partial['active'] = result
                    _save_json(output, f'n{n}_{name}_reference_started.json',
                               dict(n=n, name=name, role='source_reference'), partial, guard)
                    before = dict(partial['reference_counts'])
                    source_reference(rt, data, spec, result, partial['reference_counts'], guard)
                    result['reference_counts'] = {key: value-before.get(key, 0)
                                                  for key, value in partial['reference_counts'].items()}
                    if n == 1024:
                        _no_dense_large_arrays(result, n)
                    artifact = _save_npz(rt, output, f'n{n}_{name}_reference.npz', result,
                                         'pair_covariance_source_reference', partial, guard)
                    result['artifact'] = artifact
                    references[name] = result
                    partial['references'].append(dict(n=n, name=name, passed=result['passed'],
                        checks=result['checks'], reference_counts=result['reference_counts'], artifact=artifact))
                for name in CASE_NAMES:
                    guard.check()
                    spec = _spec(data, name)
                    reference_name = 'saved_complex' if name in ('point_complex', 'single_complex') else name
                    result = dict(n=n, name=name, p=spec['p'], status='started', counts={}, path_work=[])
                    partial['active'] = result
                    _save_json(output, f'n{n}_{name}_case_started.json',
                               dict(n=n, name=name, p=spec['p'], role='pair_covariance_case'), partial, guard)
                    before = dict(partial['reference_counts'])
                    run_case(rt, data, spec, references[reference_name], result, partial['reference_counts'], guard)
                    result['reference_counts'] = {key: value-before.get(key, 0)
                                                  for key, value in partial['reference_counts'].items()}
                    if n == 1024:
                        _no_dense_large_arrays(result, n)
                    artifact = _save_npz(rt, output, f'n{n}_{name}_case.npz', result,
                                         'pair_covariance_case', partial, guard)
                    _add_counts(partial['production_counts'], result['counts'])
                    for ledger in result['path_work']:
                        _add_counts(partial['path_work_totals'], ledger)
                    partial['cases'].append(dict(n=n, name=name, p=spec['p'], passed=result['passed'],
                        checks=result['checks'], counts=result['counts'], path_work=result['path_work'],
                        reference_counts=result['reference_counts'], artifact=artifact))
            controls = dict(status='started')
            partial['active'] = controls
            run_controls(data_sets[0], controls, guard)
            controls_artifact = _save_npz(rt, output, 'pair_covariance_controls.npz', controls,
                                          'pair_covariance_boundary_controls', partial, guard)
        partial['active'] = None
        allocation = _allocation_checks(partial, controls)
        control_rows = []
        for row in controls['source']+controls['query']:
            control_rows.append({key: row[key] for key in
                ('name', 'status', 'passed', 'expected_error', 'actual_error', 'checks', 'attempts', 'no_query_fft')
                if key in row})
        all_checks = allocation+[check for row in partial['references']+partial['cases'] for check in row['checks']]
        passed = all(check['passed'] for check in all_checks) and controls['passed']
        maximum_error = max((check['normalized_error'] for check in all_checks if 'normalized_error' in check), default=0.)
        summary = dict(status='completed' if passed else 'failed_contract', passed=passed,
                       cases=partial['cases'], references=partial['references'], controls=control_rows,
                       controls_artifact=controls_artifact, allocation_checks=allocation,
                       reference_counts=partial['reference_counts'], production_counts=partial['production_counts'],
                       path_work_totals=partial['path_work_totals'],
                       mathematical_operations=partial['mathematical_operations'],
                       maximum_normalized_error=maximum_error, input_sha256=hashes,
                       new_observations=0, receiver_calls=0, decoder_calls=0, backend_fixture_calls=0,
                       serialized_arrays='per-reference and per-case NPZ; no aggregate array artifact',
                       serialization_ledger='serialization_ledger.json',
                       scope='saved-fixture mathematics; no receiver, performance, cost advantage or novelty result')
        partial.update(status=summary['status'], passed=passed, controls_artifact=controls_artifact)
        _save_json(output, 'pair_covariance_summary.json', summary, partial, guard)
        # This ledger records every diagnostic data save above. Its own bytes
        # and the recorder's closing files are bound by the attempt manifest.
        dump(output/'serialization_ledger.json', dict(saves=partial['serialization'],
            self_and_recorder_files='sizes and hashes are in the immutable attempt manifest'))
        guard.check(files=True, threads=True)
        if not passed:
            raise AssertionError('pair covariance mathematical contract failed; no automatic retry')
        return summary
    except Exception as error:
        if isinstance(error, OSError) and not isinstance(error, TimeoutError):
            raise
        runtime.save_new(rt, output/'pair_covariance_failure.npz',
                         dict(partial=partial, error_type=type(error).__name__, error=str(error),
                              evidence=getattr(error, 'evidence', {})), dict(role='pair_covariance_failure'))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-root', type=Path)
    parser.add_argument('--source-attempt', type=Path, default=SOURCE_ATTEMPT)
    parser.add_argument('--stage', default='PAIR-COVARIANCE-MATH-01')
    parser.add_argument('--print-imports', action='store_true')
    parser.add_argument('--print-config', action='store_true')
    args = parser.parse_args()
    rt = runtime.preload()
    if args.print_imports:
        print(json.dumps(protocol.import_inventory(), indent=2))
        return
    if args.print_config:
        print(json.dumps(configuration(), indent=2))
        return
    if args.artifact_root is None or not args.artifact_root.is_absolute():
        parser.error('absolute admitted --artifact-root required')
    source = args.source_attempt.resolve()

    def run(output, guard):
        return calculate(rt, output, guard, source)

    protocol.run(args.stage, 'engineering', configuration(), run,
                 artifact_root=args.artifact_root, rt=rt, extra_sources=saved.input_paths(source), wall_cap_seconds=120)


if __name__ == '__main__':
    main()
