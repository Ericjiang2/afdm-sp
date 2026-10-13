"""Shared GK15/G7 numerical core; no files, reference data or I/O callbacks.

The event iterator exposes paid panel evidence to a caller, but never inspects
caller-added metadata. The receiver adapter retains scalar refinement traces
and the final DopplerFactor; failures retain all partial panel state.
"""
import time

import numpy as np
from scipy.special import logsumexp

from .continuous import (ContinuousIntegrator, CoreFailure, DopplerFactor,
                         DROP_TOLERANCE, SUPPORT, count, finite, raise_with_evidence)

INITIAL_PANELS = 16
MAX_BISECTIONS = 26
TOLERANCE = 1e-6
RULE_TOLERANCE = 1e-13


def validated_rule():
    """The standard QUADPACK qk15 table, checked once inside the admitted stage."""
    positive = np.array([.991455371120812639206854697526329,
                         .949107912342758524526189684047851,
                         .864864423359769072789712788640926,
                         .741531185599394439863864773280788,
                         .586087235467691130294144838258730,
                         .405845151377397166906606412076961,
                         .207784955007898467600689403773245])
    half_weights = np.array([.022935322010529224963732008058970,
                             .063092092629978553290700663189204,
                             .104790010322250183839876322541518,
                             .140653259715525918745189590510238,
                             .169004726639267902826583426598550,
                             .190350578064785409913256402421014,
                             .204432940075298892414161999234649])
    nodes = np.concatenate((-positive, [0.], positive[::-1]))
    kronrod = np.concatenate((half_weights, [.209482141084727828012999174891714],
                              half_weights[::-1]))
    gauss_indices = np.array([1, 3, 5, 7, 9, 11, 13])
    gauss = np.array([.129484966168869693270611432679082,
                      .279705391489276667901467771423780,
                      .381830050505118944950369775488975,
                      .417959183673469387755102040816327,
                      .381830050505118944950369775488975,
                      .279705391489276667901467771423780,
                      .129484966168869693270611432679082])
    if (np.any(kronrod <= 0) or np.any(gauss <= 0) or np.any(np.diff(nodes) <= 0) or
            not np.array_equal(nodes, -nodes[::-1]) or
            not np.array_equal(kronrod, kronrod[::-1]) or not np.array_equal(gauss, gauss[::-1]) or
            nodes[7] != 0. or np.any(abs(nodes) >= 1)):
        raise RuntimeError('fixed GK15/G7 positivity/symmetry invariant failed')
    checks = []
    for name, points, weights, degree in (('G7', nodes[gauss_indices], gauss, 13),
                                         ('K15', nodes, kronrod, 22)):
        for power in range(degree+1):
            actual = float(weights@(points**power))
            expected = 0. if power % 2 else 2./(power+1)
            error = abs(actual-expected)
            checks.append(dict(rule=name, degree=power, actual=actual, expected=expected,
                               absolute_error=error, passed=error <= RULE_TOLERANCE))
    if not all(row['passed'] for row in checks):
        error = RuntimeError('fixed GK15/G7 polynomial validation failed')
        error.evidence = checks
        raise error
    return dict(nodes=nodes, kronrod=kronrod, gauss=gauss, gauss_indices=gauss_indices,
                validation=checks, tolerance=RULE_TOLERANCE)


def log_nonnegative(value):
    finite(value, 'nonnegative log argument')
    if value < 0:
        raise FloatingPointError('negative log argument')
    return float(np.log(value)) if value else -np.inf


def log_positive_difference(log_a, log_b):
    """log(max(exp(a)-exp(b), 0)); -inf denotes an exact numeric zero."""
    finite([log_a, log_b], 'log difference arguments')
    if log_a <= log_b:
        return -np.inf
    return float(log_a+np.log(-np.expm1(log_b-log_a)))


def scaled_exp(log_terms, shift):
    finite(log_terms, 'discrete log terms')
    finite(shift, 'discrete shift')
    with np.errstate(under='ignore'):
        values = np.exp(log_terms-shift)
    finite(values, 'scaled discrete terms')
    omitted = values == 0
    size = int(np.count_nonzero(omitted))
    upper = float(np.log(size)+np.max(log_terms[omitted])) if size else None
    return values, dict(nodes=size, unshifted_log_mass_upper_bound=upper,
                        scope='floating-point underflow in discrete rule; no continuous tail claim')


def evaluate_panel(factor, rule, times, bound, left, right, panel, cache, counts):
    n = len(times)
    start, cpu = time.perf_counter(), time.process_time()
    before = dict(counts)
    panel.update(status='started', left=left, right=right)
    count(counts, 'panels_started')
    if counts['panels_started'] > 68:
        raise RuntimeError('panel evaluation reservation exceeded')
    center, radius = (left+right)/2, (right-left)/2
    nodes = center+radius*rule['nodes']
    weights = radius*rule['kronrod']/6.
    gauss_weights = radius*rule['gauss']/6.
    panel.update(nodes=nodes, prior_weights=weights, gauss_prior_weights=gauss_weights)
    count(counts, 'phase_entries_started', 15*n)
    phase = np.exp(1j*nodes[:, None]*times)
    finite(phase, 'panel phase')
    count(counts, 'phase_entries_completed', 15*n)
    count(counts, 'density_nodes_started', 15)
    count(counts, 'fourier_contraction_terms', 15*(n-1))
    g = (2/factor['sigma2'])*np.real(phase[:, 1:]@factor['coefficients'][1:])
    finite(g, 'panel Fourier density')
    count(counts, 'density_nodes_completed', 15)
    panel['reduced_log_kernel'] = g
    count(counts, 'center_derivatives_started')
    count(counts, 'center_phase_cache_entries_reused', n-1)
    count(counts, 'derivative_contraction_terms', n-1)
    derivative = float((2/factor['sigma2'])*np.real(np.sum(
        1j*times[1:]*factor['coefficients'][1:]*phase[7, 1:])))
    finite(derivative, 'panel center derivative')
    count(counts, 'center_derivatives_completed')
    count(counts, 'envelope_panels')
    extent = abs(derivative)*radius+.5*bound*radius**2
    lower, upper = float(g[7]-extent), float(g[7]+extent)
    finite([lower, upper], 'panel envelope')
    shift = float(np.max(g))
    k_logs = np.log(weights)+g
    g_logs = np.log(gauss_weights)+g[rule['gauss_indices']]
    k_values, k_underflow = scaled_exp(k_logs, shift)
    g_values, g_underflow = scaled_exp(g_logs, shift)
    a_k, a_g = float(k_values.sum()), float(g_values.sum())
    if a_k <= 0:
        raise FloatingPointError('nonpositive Kronrod panel mass')
    count(counts, 'characteristic_contraction_terms', (15+7)*n)
    count(counts, 'gauss_density_nodes_reused', 7)
    b_k = k_values@phase
    b_g = g_values@phase[rule['gauss_indices']]
    finite([b_k, b_g], 'panel Fourier integrals')
    panel.update(center=center, radius=radius, center_derivative=derivative,
                 envelope_lower_log_kernel=lower, envelope_upper_log_kernel=upper,
                 log_L=lower+float(np.log((right-left)/6.)),
                 log_U=upper+float(np.log((right-left)/6.)),
                 local_shift=shift, K_log_terms=k_logs, G_log_terms=g_logs,
                 K_scaled_mass=a_k, G_scaled_mass=a_g, K_scaled_fourier=b_k, G_scaled_fourier=b_g,
                 log_A_K=shift+log_nonnegative(a_k), log_A_G=shift+log_nonnegative(a_g),
                 log_e_A=shift+log_nonnegative(abs(a_k-a_g)),
                 log_e_B=shift+log_nonnegative(float(np.max(abs(b_k-b_g)))),
                 K_underflow=k_underflow, G_underflow=g_underflow,
                 status='completed', wall_seconds=time.perf_counter()-start,
                 cpu_seconds=time.process_time()-cpu)
    cache[panel['id']] = phase
    count(counts, 'panels_completed')
    panel['work_counts'] = {key: value-before.get(key, 0) for key, value in counts.items()
                            if value != before.get(key, 0)}


def aggregate(active, counts):
    """Combine local shifts in log space; never exponentiate an envelope score."""
    count(counts, 'global_aggregations')
    count(counts, 'scalar_panel_accumulations', 5*len(active))
    log_a = float(logsumexp([p['log_A_K'] for p in active]))
    log_ea = float(logsumexp([p['log_e_A'] for p in active]))
    log_eb = float(logsumexp([p['log_e_B'] for p in active]))
    log_l = float(logsumexp([p['log_L'] for p in active]))
    log_u = float(logsumexp([p['log_U'] for p in active]))
    finite([log_a, log_l, log_u], 'global mass/envelopes')
    log_mass = np.concatenate([p['K_log_terms'] for p in active])-log_a
    count(counts, 'tail_nodes_examined', int(log_mass.size))
    keep = log_mass > np.log(DROP_TOLERANCE/log_mass.size)
    if not np.any(keep):
        raise FloatingPointError('global tail rule retained no nodes')
    dropped = int(np.count_nonzero(~keep))
    tail_bound = dropped*DROP_TOLERANCE/log_mass.size
    tail_phi = 2*tail_bound
    if log_ea >= log_a:
        logz_estimate, phi_log_estimate = np.inf, np.inf
        denominator_valid = False
    else:
        # -expm1 remains accurate even when E_A/A is close to one.
        log_remaining = float(np.log(-np.expm1(log_ea-log_a)))
        logz_estimate = -log_remaining
        phi_log_estimate = float(np.logaddexp(
            np.logaddexp(log_ea, log_eb)-log_a-log_remaining, log_nonnegative(tail_phi)))
        denominator_valid = True
    if np.isnan(logz_estimate) or np.isnan(phi_log_estimate):
        raise FloatingPointError('NaN embedded error estimate')
    scores = []
    for panel in active:
        risk = log_positive_difference(panel['log_U'], panel['log_A_K'])-log_l
        score = max(panel['log_e_A']-log_a, panel['log_e_B']-log_a, risk)
        if np.isnan(score):
            raise FloatingPointError('NaN adaptive priority')
        scores.append(dict(panel_id=panel['id'], left=panel['left'], log_priority=float(score),
                           log_mass_difference=panel['log_e_A']-log_a,
                           log_fourier_difference=panel['log_e_B']-log_a, log_envelope_risk=float(risk)))
    estimated = denominator_valid and logz_estimate <= TOLERANCE and phi_log_estimate <= np.log(TOLERANCE)
    return dict(active_panel_ids=[p['id'] for p in active], active_panels=len(active),
                active_nodes=int(log_mass.size), centered_log_normalizer=log_a,
                log_E_A=log_ea, log_E_B=log_eb, log_L=log_l, log_U=log_u,
                logZ_error_estimate=float(logz_estimate), phi_error_estimate_log=float(phi_log_estimate),
                denominator_valid=denominator_valid, estimated_complete=bool(estimated),
                dropped_nodes=dropped, tail_mass_bound=tail_bound, tail_phi_bound=tail_phi,
                scores=scores, envelope_log_width=log_u-log_l,
                envelope_risk='unclosed; ordinary floating-point bounds without outward rounding',
                certified_continuous_error=False), log_mass, keep


def final_output(active, cache, state, log_mass, keep, factor, counts):
    n = len(factor['coefficients'])
    nodes = np.concatenate([p['nodes'] for p in active])
    base_weights = np.concatenate([p['prior_weights'] for p in active])
    reduced = np.concatenate([p['reduced_log_kernel'] for p in active])
    finite([nodes, base_weights, reduced, log_mass], 'final discrete rule')
    if np.any(base_weights <= 0) or abs(float(base_weights.sum())-1.) > 1e-13:
        raise FloatingPointError('invalid full-support positive base weights')
    full_mass, underflow = scaled_exp(log_mass, 0.)
    if abs(float(full_mass.sum())-1.) > 1e-10:
        raise FloatingPointError('invalid untrimmed normalized mass')
    probabilities = np.exp(log_mass[keep]-logsumexp(log_mass[keep]))
    if np.any(probabilities <= 0) or abs(float(probabilities.sum())-1.) > 1e-10:
        raise FloatingPointError('invalid final positive probabilities')
    dropped = int(np.count_nonzero(~keep))
    dropped_log = float(logsumexp(log_mass[~keep])) if dropped else None
    if dropped and dropped_log > np.log(DROP_TOLERANCE):
        raise FloatingPointError('final discrete tail exceeds frozen tolerance')
    with np.errstate(under='ignore'):
        dropped_mass = float(np.exp(dropped_log)) if dropped else 0.
    phi = np.zeros(n, complex)
    node_offset, probability_offset = 0, 0
    for panel in active:
        retained = keep[node_offset:node_offset+15]
        size = int(retained.sum())
        if size:
            count(counts, 'final_phase_cache_entries_reused', size*n)
            count(counts, 'final_characteristic_contraction_terms', size*n)
            phi += probabilities[probability_offset:probability_offset+size]@cache[panel['id']][retained]
        node_offset += 15
        probability_offset += size
    finite(phi, 'final characteristic moments')
    if abs(phi[0]-1) > 1e-10 or np.max(abs(phi)) > 1+1e-10:
        raise FloatingPointError('final characteristic invariant failed')
    constant = float(2*factor['coefficients'][0].real/factor['sigma2'])
    logz = state['centered_log_normalizer']+constant
    finite([constant, logz], 'final log normalizer')
    for array in (nodes, base_weights, reduced, log_mass, keep, probabilities, phi):
        array.setflags(write=False)
    return dict(nodes=nodes, prior_weights=base_weights, reduced_log_kernel=reduced,
                log_masses=log_mass, retained_mask=keep, retained_probabilities=probabilities, phi=phi,
                constant=constant, centered_log_normalizer=state['centered_log_normalizer'],
                log_normalizer=logz, dropped_nodes=dropped, dropped_log_mass=dropped_log,
                dropped_mass=dropped_mass, dropped_mass_bound=state['tail_mass_bound'],
                moment_tail_bound=state['tail_phi_bound'], untrimmed_underflow=underflow,
                positive_weight_and_normalization_checks=True, certified_continuous_error=False)


def candidate_events(factor, rule, partial):
    """Run the frozen refinement; yields never provide inputs to its decisions."""
    start, cpu = time.perf_counter(), time.process_time()
    coefficients = np.asarray(factor['coefficients'])
    if coefficients.ndim != 1 or len(coefficients) < 2 or not np.isfinite(coefficients).all():
        raise ValueError('finite Fourier coefficient vector required')
    if not np.isfinite(factor['sigma2']) or factor['sigma2'] <= 0:
        raise ValueError('positive finite noise variance required')
    n = len(coefficients)
    counts, panels, trace = partial['counts'], partial['panels'], partial['trace']
    if counts or panels or trace:
        raise ValueError('adaptive run requires fresh per-integral state')
    cache, active = {}, []
    times = 2*np.pi*np.arange(n)/n
    count(counts, 'B2_evaluations')
    count(counts, 'B2_bound_terms', n-1)
    bound = float((2/factor['sigma2'])*np.sum(abs(factor['coefficients'][1:])*times[1:]**2))
    finite(bound, 'global B2 envelope bound')
    partial['B2'] = bound

    def add_panel(left, right, parent):
        panel = dict(id=len(panels), parent=parent, left=left, right=right)
        panels.append(panel)
        yield 'panel_started', panel
        evaluate_panel(factor, rule, times, bound, left, right, panel, cache, counts)
        yield 'panel_completed', panel
        return panel

    edges = np.linspace(*SUPPORT, INITIAL_PANELS+1)
    for left, right in zip(edges[:-1], edges[1:]):
        panel = yield from add_panel(float(left), float(right), None)
        active.append(panel)
    for iteration in range(MAX_BISECTIONS+1):
        if (active[0]['left'] != SUPPORT[0] or active[-1]['right'] != SUPPORT[1] or
                any(a['right'] != b['left'] for a, b in zip(active[:-1], active[1:]))):
            raise RuntimeError('adaptive panels no longer partition the full support')
        state, log_mass, keep = aggregate(active, counts)
        state.update(bisections=iteration, density_nodes=counts['density_nodes_completed'],
                     center_derivatives=counts['center_derivatives_completed'])
        trace.append(state)
        if state['estimated_complete'] or iteration == MAX_BISECTIONS:
            partial['output'] = final_output(active, cache, state, log_mass, keep, factor, counts)
            partial['status'] = 'candidate_completed' if state['estimated_complete'] else 'budget_failure'
            break
        selected = max(range(len(active)), key=lambda i: state['scores'][i]['log_priority'])
        parent = active[selected]
        state['selected_panel_id'] = parent['id']
        state['selected_left'] = parent['left']
        yield 'iteration', state
        count(counts, 'bisections_started')
        midpoint = (parent['left']+parent['right'])/2
        left_child = yield from add_panel(parent['left'], midpoint, parent['id'])
        right_child = yield from add_panel(midpoint, parent['right'], parent['id'])
        active[selected:selected+1] = [left_child, right_child]
        del cache[parent['id']]
        count(counts, 'retired_parent_phase_entries', 15*n)
        count(counts, 'bisections_completed')
    expected_panels = INITIAL_PANELS+2*counts.get('bisections_completed', 0)
    if (counts['panels_completed'] != expected_panels or counts['density_nodes_completed'] != 15*expected_panels or
            counts['center_derivatives_completed'] != expected_panels or expected_panels > 68):
        raise RuntimeError('candidate cost ledger differs from the fixed refinement scheme')
    partial.update(quadrature_wall_seconds=time.perf_counter()-start,
                   quadrature_cpu_seconds=time.process_time()-cpu,
                   final_active_nodes=15*len(active), retired_parent_nodes=15*(len(panels)-len(active)))
    yield 'finished', partial


def as_factor(coefficients, sigma2, partial):
    """Convert a completed rule to the original continuous-factor semantics."""
    if partial['status'] != 'candidate_completed':
        raise CoreFailure('adaptive integration exhausted 1020 cumulative density nodes',
                          dict(status=partial['status'], counts=partial['counts']))
    result = partial['output']
    if result['dropped_mass'] > result['dropped_mass_bound']*(1+1e-10):
        raise CoreFailure('adaptive receiver tail exceeds declared mass bound',
                          dict(dropped_mass=result['dropped_mass'], mass_bound=result['dropped_mass_bound']))
    keep, probabilities = result['retained_mask'], result['retained_probabilities']
    expected = float(probabilities@result['reduced_log_kernel'][keep])
    density = dict(kind='fourier', coefficients=coefficients.copy(), sigma2=float(sigma2),
                   support=SUPPORT, base_density='uniform[-3,3]', quadrature='adaptive',
                   log_normalizer=result['log_normalizer'],
                   centered_log_normalizer=result['centered_log_normalizer'], constant=result['constant'],
                   expected_log_kernel=expected+result['constant'],
                   kl_to_uniform=expected-result['centered_log_normalizer'],
                   resolution_agreement=True, resolution_criterion='embedded GK15/G7 empirical estimate',
                   certified_continuous_error=False, B2=partial['B2'],
                   adaptive_counts=dict(partial['counts']),
                   panel_boundaries=[{key: panel[key] for key in ('id', 'parent', 'left', 'right')}
                                     for panel in partial['panels']],
                   final_discrete_tail={key: result[key] for key in
                       ('dropped_nodes', 'dropped_log_mass', 'dropped_mass', 'dropped_mass_bound',
                        'moment_tail_bound', 'untrimmed_underflow')},
                   quadrature_wall_seconds=partial['quadrature_wall_seconds'],
                   quadrature_cpu_seconds=partial['quadrature_cpu_seconds'])
    finite([density['log_normalizer'], density['expected_log_kernel'], density['kl_to_uniform']],
           'adaptive factor normalizer/expectation/KL')
    # Keep the original receiver's tighter characteristic check as well as the
    # saved diagnostic checks; never relax a receiving boundary invariant.
    if abs(result['phi'][0]-1) > 1e-12 or np.max(abs(result['phi'])) > 1+1e-12:
        raise CoreFailure('invalid adaptive receiver characteristic moments', dict(phi=result['phi']))
    return DopplerFactor(result['nodes'][keep].copy(), probabilities, result['phi'], density, partial['trace'])


class AdaptiveIntegrator(ContinuousIntegrator):
    """Only Fourier updates differ; inherited initialization remains fixed GL."""

    def __init__(self, n, counts):
        super().__init__(n, counts)
        start, cpu = time.perf_counter(), time.process_time()
        count(counts, 'adaptive_rule_validations_started')
        self.rule = validated_rule()
        count(counts, 'adaptive_rule_validations_completed')
        self.rule_validation = dict(checks=self.rule['validation'],
                                    wall_seconds=time.perf_counter()-start,
                                    cpu_seconds=time.process_time()-cpu)

    def from_coefficients(self, coefficients, sigma2):
        partial = dict(status='started', counts={}, panels=[], trace=[], certified_continuous_error=False)
        try:
            coefficients = np.asarray(coefficients, complex)
            if coefficients.shape != (self.n,):
                raise ValueError('Fourier coefficient dimension differs from receiver N')
            factor = dict(coefficients=coefficients.copy(), sigma2=float(sigma2))
            partial['input'] = factor
            count(self.counts, 'continuous_integrals')
            with np.errstate(over='raise', invalid='raise', divide='raise', under='ignore'):
                for _ in candidate_events(factor, self.rule, partial):
                    pass
                count(self.counts, 'adaptive_factor_exports_started')
                result = as_factor(factor['coefficients'], factor['sigma2'], partial)
                count(self.counts, 'adaptive_factor_expectation_terms', len(result.weights))
                count(self.counts, 'adaptive_factor_exports_completed')
                return result
        except Exception as error:
            raise_with_evidence(error, 'adaptive continuous integration failed: ',
                                dict(partial=partial, cause_type=type(error).__name__))
        finally:
            for key, amount in partial['counts'].items():
                count(self.counts, 'adaptive_'+key, amount)
