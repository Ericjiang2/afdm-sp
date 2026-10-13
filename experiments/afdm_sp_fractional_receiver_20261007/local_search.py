"""One registered bounded search shared by the two five-sweep point arms."""
import numpy as np
import scipy.optimize

from . import continuous

RADIUS = .75
XATOL = 1e-4
MAXITER = 32
SCORE_CAP = 35
SWEEPS = 5


def configuration():
    return dict(radius=RADIUS, support=[-3., 3.], xatol=XATOL, maxiter=MAXITER,
                explicit_scores=3, bounded_searches=1, search_scores_per_coordinate_cap=SCORE_CAP,
                collapsed_winner_full_evaluations=1, collapsed_total_evaluations_per_coordinate_cap=36,
                selection_order=['previous', 'lower', 'upper', 'bounded_result'],
                ties='strict improvement only; previous retained on equal scores', retries=0)


def maximize(score, previous, counts):
    """Return a selected point and all calls; an optimizer endpoint is never rescored."""
    trace = dict(previous=previous, calls=[], candidates=[], status='started')
    try:
        if not np.isfinite(previous) or not -3 <= previous <= 3:
            raise ValueError('local search center outside working support')
        lower, upper = max(-3., previous-RADIUS), min(3., previous+RADIUS)
        trace['bounds'] = [lower, upper]
        continuous.count(counts, 'local_coordinate_searches')

        def evaluate(value, origin):
            value = float(value)
            if not np.isfinite(value) or not lower <= value <= upper:
                raise continuous.CoreFailure('local search candidate outside frozen window', trace)
            if len(trace['calls']) >= SCORE_CAP:
                raise continuous.CoreFailure('local search score cap exceeded', trace)
            row = dict(value=value, origin=origin, status='started')
            trace['calls'].append(row)
            continuous.count(counts, 'local_scores_started')
            potential = float(score(value))
            continuous.finite(potential, 'local coordinate score')
            row.update(score=potential, status='completed')
            continuous.count(counts, 'local_scores_completed')
            return potential

        for name, value in (('previous', previous), ('lower', lower), ('upper', upper)):
            trace['candidates'].append(dict(origin=name, value=float(value), score=evaluate(value, name)))
        continuous.count(counts, 'local_bounded_minimizations')
        result = scipy.optimize.minimize_scalar(lambda value: -evaluate(value, 'bounded'),
            bounds=(lower, upper), method='bounded', options=dict(xatol=XATOL, maxiter=MAXITER))
        trace['optimizer'] = dict(success=bool(result.success), x=float(result.x), fun=float(result.fun),
                                  nfev=int(result.nfev), message=str(result.message))
        internal = [row for row in trace['calls'] if row['origin'] == 'bounded']
        if (not result.success or not np.isfinite([result.x, result.fun]).all() or
                not lower <= result.x <= upper or not 1 <= result.nfev <= MAXITER or
                result.nfev != len(internal)):
            raise continuous.CoreFailure('bounded local optimization failed its contract', trace)
        matching = [row for row in internal if row['value'] == result.x and row['score'] == -result.fun]
        if not matching:
            raise continuous.CoreFailure('optimizer endpoint has no matching recorded score', trace)
        trace['candidates'].append(dict(origin='bounded_result', value=float(result.x), score=-float(result.fun)))
        winner = trace['candidates'][0]
        for candidate in trace['candidates'][1:]:
            if candidate['score'] > winner['score']:
                winner = candidate
        trace.update(status='completed', selected=winner['value'], selected_score=winner['score'],
                     actual_scores=len(trace['calls']))
        continuous.count(counts, 'local_coordinate_searches_completed')
        return winner['value'], trace
    except Exception as error:
        continuous.raise_with_evidence(error, 'local search failed: ', dict(trace=trace, counts=dict(counts)))


class LocalPointOptimizer:
    """Original Fourier conditional potential, using only the registered local search."""

    def __init__(self, n, counts):
        self.n, self.counts = n, counts
        self.time = 2*np.pi*np.arange(n)/n

    def update(self, coefficients, sigma2, previous):
        coefficients = np.asarray(coefficients, complex)
        if coefficients.shape != (self.n,) or not np.isfinite(coefficients).all():
            raise ValueError('finite Fourier coefficient vector required')
        if not np.isfinite(sigma2) or sigma2 <= 0:
            raise ValueError('positive finite noise required')

        def score(value):
            continuous.count(self.counts, 'local_point_phase_entries', self.n-1)
            continuous.count(self.counts, 'local_point_fourier_terms', self.n-1)
            return float((2/sigma2)*np.real(np.exp(1j*value*self.time[1:])@coefficients[1:]))

        value, trace = maximize(score, previous, self.counts)
        trace.update(coefficients=coefficients.copy(), constant=float(2*coefficients[0].real/sigma2),
                     reduced_coordinate_potential=trace['selected_score'])
        return continuous.point_factor(value, self.n, self.counts), trace
