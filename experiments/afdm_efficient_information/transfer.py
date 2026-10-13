"""Legal-input transfer diagnostics; no production inference or new training."""
from itertools import product
import json
import math
from pathlib import Path
import resource
import sys
import time

import numpy as np

from experiments.afdm_efficient_information import features
from experiments.afdm_efficient_information.prior_likelihood import (
    ActualPrior, angular_density, daft,
)
from experiments.afdm_efficient_information.score import ScoreRegressor
from experiments.afdm_shared_channel_20261004.production_prior import normalize_gain
from experiments.sp_afdm_frozen_20260920.src.physical import daft as frozen_daft

INPUTS = ('uniform', 'pilot', 'biased', 'repetition')
BIASED_PROBABILITIES = np.array([.55, .15, .20, .10])


def input_states(n, kind):
    """All legal words and their actual mass; no uniform-outside substitution."""
    if not isinstance(n, int) or not 4 <= n <= 6 or kind not in INPUTS:
        raise ValueError('legal input enumeration requires N=4..6 and a known law')
    states = np.array(list(product(range(4), repeat=n)), dtype=int)
    if kind == 'pilot':
        states = states[states[:, 0] == 0]
    elif kind == 'repetition':
        if n % 2:
            raise ValueError('pair repetition requires even N')
        states = states[np.all(states[:, ::2] == states[:, 1::2], axis=1)]
    mass = (np.prod(BIASED_PROBABILITIES[states], axis=1) if kind == 'biased'
            else np.full(len(states), 1/len(states)))
    return np.exp(1j*(np.pi/4+np.pi/2*states)), mass


def draw_inputs(n, count, kind, rng):
    if kind not in INPUTS or n < 4 or count < 1:
        raise ValueError('positive count, N>=4 and known input law required')
    if kind == 'biased':
        labels = rng.choice(4, size=(count, n), p=BIASED_PROBABILITIES)
    else:
        labels = rng.integers(0, 4, (count, n))
    if kind == 'pilot':
        labels[:, 0] = 0
    elif kind == 'repetition':
        if n % 2:
            raise ValueError('pair repetition requires even N')
        labels[:, 1::2] = labels[:, ::2]
    return np.exp(1j*(np.pi/4+np.pi/2*labels))


def inverse_daft(y):
    """Public unitary IDAFT, with the same chirps as prior_likelihood.daft."""
    y = np.asarray(y, complex)
    if y.ndim != 2 or not np.isfinite(y).all():
        raise ValueError('finite DAFT observation rows required')
    n = y.shape[1]
    return frozen_daft(y.T, 2.5/n, .1/n**2, inverse=True).T


def forward_daft(y):
    y = np.asarray(y, complex)
    if y.ndim != 2 or not np.isfinite(y).all():
        raise ValueError('finite time observation rows required')
    n = y.shape[1]
    return frozen_daft(y.T, 2.5/n, .1/n**2).T


class InputPrior(ActualPrior):
    """Actual G0/G1 likelihood with exhaustive legal input and CP1 integration.

    Only the input mixture is changed. The frozen geometric pushforward, latent
    PDP law, positive CP1 rule and analytic global-phase integration are reused.
    Uniform words enumerate all global QPSK phases, independently checking the
    orbit reduction in ActualPrior. This adapter intentionally exposes no score.
    """
    def __init__(self, *args, input_kind='uniform', **kwargs):
        super().__init__(*args, **kwargs)
        words, self.input_mass = input_states(self.n, input_kind)
        self.input_time = words @ daft(self.n).conj()
        self.input_kind = input_kind
        self.cost['component_constructions'] = 0
        self.cost['support_eigh_calls'] = 0
        self.cost['normalization_eigvalsh_calls'] = 0

    def branch(self, theta):
        result = super().branch(theta)
        self.cost['support_eigh_calls'] += 1
        return result

    def _components(self, theta, step=None):
        if step is not None:
            raise ValueError('transfer reference implements density, not score differentiation')
        theta = self._validate(theta)
        key = tuple(theta)
        if key in self._cache:
            return self._cache[key]
        branch = self.branch(theta)
        geo, latent = branch['geometry'], branch['pdp']
        if self.model == 'g0' and branch['platform']:
            atom = int(branch['active'][0]) % (2*self.system.k_max_cap+1)-self.system.k_max_cap
            response = np.exp(2j*np.pi*atom*np.arange(self.n)/self.n)[None, :]
            mass = np.ones(1)
            error = 0.
        else:
            gains = normalize_gain(self.nodes, geo['gram'])
            self.cost['normalization_eigvalsh_calls'] += 1
            response = gains @ geo[self.model].T
            mass = self.weights*angular_density(self.nodes, latent['pdp'], latent['weights'])
            error = abs(float(mass.sum())-1)
            mass = mass/mass.sum()
        means = (np.exp(theta[2]/2)*response[:, None, :]*self.input_time).reshape(-1, self.n)
        result = dict(means=means, logweights=np.log(np.outer(mass, self.input_mass).ravel()),
                      derivatives=None, quadrature_mass_error=error, branch=branch)
        self.cost['response_evaluations'] += len(means)
        self.cost['component_constructions'] += 1
        self._cache[key] = result
        return result


def sample_observations(n, theta, count, seed, *, input_kind='uniform',
                        generator='g0', gain_prior='marginal'):
    """Independent exact continuous latent samples; return raw for offline audit.

    Gaussian is an explicitly distinct CN(0,I/2), untruncated G1 control. Other
    gains use the frozen G0 normalization and the stated actual PDP slice.
    """
    gaussian = gain_prior == 'gaussian' if isinstance(gain_prior, str) else False
    if gaussian and generator != 'g1':
        raise ValueError('Gaussian control must use the declared untruncated G1 response')
    prior = ActualPrior(n=n, model=generator, pdp='equal' if gaussian else gain_prior)
    theta = prior._validate(theta)
    if not isinstance(count, int) or count <= 0:
        raise ValueError('positive integer independent observation count required')
    branch = prior.branch(theta)
    rng = np.random.default_rng(seed)
    latent = branch['pdp']
    index = rng.choice(len(latent['weights']), count, p=latent['weights'])
    gaussian_base = (rng.standard_normal((count, 2))+1j*rng.standard_normal((count, 2)))/np.sqrt(2)
    gain = (gaussian_base/np.sqrt(2) if gaussian else
            normalize_gain(gaussian_base*np.sqrt(latent['pdp'][index]), branch['geometry']['gram']))
    response = gain @ branch['geometry'][generator].T
    words = draw_inputs(n, count, input_kind, rng)
    time_input = inverse_daft(words)
    noise = (rng.standard_normal((count, n))+1j*rng.standard_normal((count, n)))/np.sqrt(2)
    y = np.exp(theta[2]/2)*response*time_input+np.exp(theta[3]/2)*noise
    raw = dict(y_time=y, symbols=words, noise_base=noise, gain_gaussian_base=gaussian_base,
               latent_index=index, latent_pdp=latent['pdp'][index], gain=gain,
               gram=branch['geometry']['gram'], response_atoms=branch['geometry'][generator],
               time_input=time_input, theta=np.asarray(theta), seed=np.asarray(seed))
    # Explicit counts for this source path, including validation decompositions.
    counts = dict(new_independent_observations=count, response_atom_entries=2*n,
                  gain_response_complex_products=2*n*count, input_inverse_fft_rows=count,
                  matrix_eigvalsh_calls=1 if gaussian else 2, matrix_eigh_calls=1,
                  exact_likelihood_nodes=0, pilot_symbols_per_word=int(input_kind == 'pilot'),
                  independent_input_symbols_per_word=n//2 if input_kind == 'repetition' else n-int(input_kind == 'pilot'))
    return raw, branch, counts


def anchored_features(y):
    """The same N4 polynomial map on four public relative-time anchors only."""
    y = np.asarray(y, complex)
    if y.ndim != 2 or y.shape[1] < 4 or y.shape[1] % 4 or not np.isfinite(y).all():
        raise ValueError('finite observation rows and N divisible by four required')
    anchors = np.arange(4)*y.shape[1]//4
    value, cost = features.observed_features(y[:, anchors])
    cost.update(anchors=anchors.tolist(), discarded_observation_coordinates=y.shape[1]-4,
                learned_weight_transfer='same N4 feature map, no per-N refit')
    return value, cost


def restore_regressor(path):
    with np.load(path, allow_pickle=False) as saved:
        required = ('mean', 'scale', 'active', 'score_mean', 'score_scale', 'coefficients',
                    'ridge', 'rank', 'singular_values')
        state = {name: saved[name].copy() for name in required}
    model = ScoreRegressor(float(state['ridge']))
    for name, value in state.items():
        setattr(model, name, value)
    return model


def rejection_threshold(scores, alpha=.05):
    scores = np.asarray(scores, float)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all() or not 0 < alpha < 1:
        raise ValueError('finite nonempty calibration scores and alpha in (0,1) required')
    # Strict exceedance with the finite-sample rank correction; ties conservative.
    index = math.ceil((len(scores)+1)*(1-alpha))-1
    if index >= len(scores):
        raise ValueError('calibration count insufficient for requested alpha')
    return float(np.sort(scores)[index])


def binomial_interval(successes, count, z=1.959963984540054):
    if not isinstance(count, int) or count <= 0 or not 0 <= successes <= count:
        raise ValueError('binomial count and successes disagree')
    fraction = successes/count
    denominator = 1+z*z/count
    center = (fraction+z*z/(2*count))/denominator
    radius = z*np.sqrt(fraction*(1-fraction)/count+z*z/(4*count**2))/denominator
    return dict(count=count, successes=int(successes), fraction=float(fraction),
                wilson95=[float(max(0, center-radius)), float(min(1, center+radius))])


def phase_diagnostics(y):
    """Independent dense reconstruction; exact identities, not learned accuracy."""
    y = np.asarray(y, complex)
    z, anchor = features.canonical_phase(y)
    dense = y[:, :, None]*y[:, None, :].conj()
    reconstruction = z[:, :, None]*z[:, None, :].conj()
    angle = np.arange(len(y))*.37+.123
    rotated, _ = features.canonical_phase(y*np.exp(1j*angle[:, None]))
    # In ties rotation may change which equal maximum wins; z itself remains the
    # same only if the tie choice is numerically stable. rrH is always invariant.
    return dict(max_dense_reconstruction_error=float(np.max(abs(dense-reconstruction))),
                max_rotation_representation_error=float(np.max(abs(z-rotated))),
                dense_output_bytes=dense.nbytes, canonical_output_bytes=z.nbytes+anchor.nbytes,
                canonical_complex_scalings=y.size, dense_complex_products=len(y)*y.shape[1]**2)


class Costs:
    """Measured complete callable costs; raw generation and reference work separate."""
    def __init__(self):
        self.rows = []

    def measure(self, category, key, function, *args, operations=None, **kwargs):
        started, cpu = time.perf_counter(), time.process_time()
        status, error = 'complete', None
        try:
            return function(*args, **kwargs)
        except BaseException as caught:
            status, error = 'failed', repr(caught)
            raise
        finally:
            peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            self.rows.append(dict(category=category, key=key, status=status, error=error,
                                  wall_seconds=time.perf_counter()-started,
                                  cpu_seconds=time.process_time()-cpu,
                                  peak_rss_bytes=int(peak if sys.platform == 'darwin' else 1024*peak),
                                  peak_scope='whole-process cumulative high-water',
                                  operations=operations if operations is not None else {}))


def amortization(one_time, reference_per_item, candidate_per_item, quality_equivalent):
    if not np.isfinite([one_time, reference_per_item, candidate_per_item]).all() or min(one_time, reference_per_item, candidate_per_item) < 0:
        raise ValueError('finite nonnegative costs required')
    if not quality_equivalent:
        return dict(status='no equal-quality advantage established', break_even_items=None)
    saving = reference_per_item-candidate_per_item
    if saving <= 0:
        return dict(status='no measured cost advantage', break_even_items=None)
    return dict(status='same-object measured amortization', break_even_items=math.ceil(one_time/saving),
                saved_seconds_per_item=saving)


def stage_cost_inventory(root):
    """Read all registrations, including failed/missing attempts, with no defaults."""
    rows = []
    for path in sorted(Path(root).glob('*/registration.json')):
        registration = json.loads(path.read_text())
        attempt_path = path.with_name('attempt.json')
        attempt = json.loads(attempt_path.read_text()) if attempt_path.exists() else None
        rows.append(dict(stage=registration['stage'], reserved_wall_seconds=registration['wall_cap_seconds'],
                         reserved_observations=registration['config']['new_observations'],
                         status=attempt['status'] if attempt else 'running_or_interrupted_without_attempt',
                         actual_wall_seconds=attempt['wall_seconds'] if attempt else None,
                         actual_cpu_seconds=attempt['cpu_seconds'] if attempt else None,
                         peak_rss_bytes=attempt.get('peak_rss_bytes') if attempt else None))
    return dict(stages=rows, total_reserved_wall_seconds=sum(r['reserved_wall_seconds'] for r in rows),
                total_reserved_observations=sum(r['reserved_observations'] for r in rows),
                recorded_actual_wall_seconds=sum(r['actual_wall_seconds'] for r in rows if r['actual_wall_seconds'] is not None),
                recorded_actual_cpu_seconds=sum(r['actual_cpu_seconds'] for r in rows if r['actual_cpu_seconds'] is not None),
                missing_attempts=[r['stage'] for r in rows if r['actual_wall_seconds'] is None])
