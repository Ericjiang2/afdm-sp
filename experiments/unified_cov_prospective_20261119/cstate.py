"""Stage 3 continuation with trial-support spectral covariance."""

import importlib.util
import inspect
from functools import lru_cache
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np

from projector import block_projector, low_projector

STAGE3 = Path(__file__).resolve().parents[1] / 'cstate_codelay_sbl_stage3_20261118'
sys.path.insert(0, str(STAGE3))
spec = importlib.util.spec_from_file_location('stage3_codelay_run', STAGE3 / 'run.py')
stage3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage3)
SPECTRAL_ARMS = ('U', 'C-hi', 'C-lo')
ARMS = ('F0', 'A2', 'CD', *SPECTRAL_ARMS)
TAU = .5


def context():
    return stage3.context()


def _empty_census():
    return dict(scored_trials=0, nonempty_scored_trials=0, valid_trials=0, nonempty_trials=0,
                checked_trials=0, max_relative_score_error=0.)


def _trial_projectors(delays, dopplers, slot, candidate_delays, candidate_dopplers, n, tau):
    """Rebuild each changed co-delay block, retaining disjoint unchanged blocks."""
    keep = np.flatnonzero(np.arange(len(delays)) != slot)
    common = np.zeros((len(delays), len(delays)), dtype=complex)
    common[np.ix_(keep, keep)] = low_projector(delays[keep], dopplers[keep], n, tau)
    shape = (len(candidate_delays), *common.shape)
    projectors = np.broadcast_to(common, shape).copy()
    for delay in np.unique(delays[keep]):
        rows = np.flatnonzero(candidate_delays == delay)
        if not len(rows):
            continue
        members = keep[delays[keep] == delay]
        # Match the per-support slot order used by _system at the threshold.
        slots = np.sort(np.r_[slot, members])
        block_dopplers = np.broadcast_to(dopplers[slots], (len(rows), len(slots))).copy()
        block_dopplers[:, np.searchsorted(slots, slot)] = candidate_dopplers[rows]
        projectors[np.ix_(rows, slots, slots)], _ = block_projector(block_dopplers, n, tau)
    return projectors


def _replace_spectrum(gamma, projector, total, arm):
    if arm == 'U':
        return gamma + total * projector
    if arm == 'C-hi':
        high = np.eye(gamma.shape[-1]) - projector
        return high @ gamma @ high + total * projector
    if arm == 'C-lo':
        return projector @ gamma @ projector + total * (np.eye(gamma.shape[-1]) - projector)
    raise ValueError(f'Unknown spectral covariance {arm}')


def _reference_arm(arm, tau, total):
    if arm in SPECTRAL_ARMS and (not tau or not total):
        return 'A2' if arm == 'C-lo' else 'CD'
    return arm


def support_covariance(full, cd, v, delays, dopplers, c1, *, arm, tau=TAU):
    """Actual covariance selected by the arm on a fresh support."""
    system, mode = _support_system(full, cd, v, arm, tau)
    gamma = system.__globals__['projected_variance'](v, delays, dopplers, c1)
    return np.diag(np.diag(gamma)) if mode == 'diag' else gamma


# Copy E-1 geometry_validation_variant.py::reopen_geometry to bind a new projector before each pass and check descent on that objective; the frozen interface lacks those callbacks.
@lru_cache(maxsize=1)
def _pass_code(reference):
    source = inspect.getsource(reference)
    guard = ('    if value > initial_value + 1e-8 * (1 + abs(initial_value)):\n'
             '        raise AssertionError("frozen geometry objective increased")\n')
    begins = '    for pass_index in range(local_passes):\n'
    final = '    clock.enter("geometry_finalization")\n'
    if any(source.count(marker) != 1 for marker in (begins, final, guard)):
        raise ValueError('Reviewed E-1 pass boundaries do not match')
    source = source.replace(begins, begins +
                            '        _start_pass(current)\n'
                            '        B, Q, b, h, value, gamma = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)\n'
                            '        counts["joint_gain_solves"] += 1\n'
                            '        pass_start = value\n')
    source = source.replace(final,
                            '        *_, pass_end, _ = _system(Y, xt, v, current, c1, c2, ridge, gamma_mode)\n'
                            '        counts["joint_gain_solves"] += 1\n'
                            '        _check_pass(pass_start, value, pass_end)\n'
                            + final + '    _start_pass(current)\n')
    # The across-pass objectives differ. The original coordinate guards stay,
    # and pass endpoints are checked anew under their own fixed objective.
    source = source.replace(guard, '')
    return compile(source, inspect.getsourcefile(reference), 'exec')


class _SpectralGeometry:
    def __init__(self, cd, tau, total, n, check_scores, arm, response_cache=None):
        self.cd = cd
        self.tau = tau
        self.total = total
        self.n = n
        self.check_scores = check_scores
        self.arm = arm
        self.response_cache = {} if response_cache is None else response_cache
        self.fixed = None
        self.census = _empty_census()
        self.census.update(passes_checked=0, max_pass_increase=0.)
        base_system = cd._system
        self.base_variance = base_system.__globals__['projected_variance']
        self.system = FunctionType(base_system.__code__,
                                   dict(base_system.__globals__, projected_variance=self.variance),
                                   base_system.__name__, base_system.__defaults__)

    def start_pass(self, current):
        self.fixed = low_projector([p.delay for p in current], [p.doppler for p in current],
                                   self.n, self.tau)

    def check_pass(self, start, recorded, refit):
        self.census['passes_checked'] += 1
        self.census['max_pass_increase'] = max(self.census['max_pass_increase'], refit - start)
        if refit > start or not np.isclose(refit, recorded, rtol=1e-12, atol=1e-12):
            raise AssertionError(f'{self.arm} fixed-projector pass objective: {start}, {recorded}, {refit}')

    def variance(self, v, delays, dopplers, c1):
        gamma = self.base_variance(v, delays, dopplers, c1)
        p = self.fixed if self.fixed is not None else low_projector(delays, dopplers, self.n, self.tau)
        return _replace_spectrum(gamma, p, self.total, self.arm)

    def direct_scores(self, Y, xt, v, current, B, Q, b, c1, c2, ridge,
                      delays, dopplers, chunk_size, energy, tolerance, counts, gamma_mode):
        """Use full trial normal equations, sharing the data Gram and bank products."""
        P, C = len(current), len(delays)
        scores = np.empty((P, C))
        valid = np.empty((P, C), dtype=bool)
        graph_delays = np.asarray([p.delay for p in current])
        graph_dopplers = np.asarray([p.doppler for p in current])
        base_gram = B.conj().T @ B
        base_gamma = self.base_variance(v, graph_delays, graph_dopplers, c1)
        base_gram += ridge * np.eye(P)
        base_gram = (base_gram + base_gram.conj().T) * .5
        y_energy = float(np.vdot(Y, Y).real)
        base_cd = (self.total, self.n)
        for first in range(0, C, chunk_size):
            last = min(first + chunk_size, C)
            chunk = (first, last)
            if chunk not in self.response_cache:
                # Bank responses depend on the shared observation and moments,
                # which are fixed for this key across slots, edits and arms.
                group = [self.cd.Path(int(delay), float(nu))
                         for delay, nu in zip(delays[first:last], dopplers[first:last])]
                responses = self.cd._responses(xt, group, c1, c2)
                self.response_cache[chunk] = (group, responses, responses.conj().T @ Y,
                                              np.sum(abs(responses) ** 2, axis=0))
            group, responses, candidate_b, candidate_energy = self.response_cache[chunk]
            cross = B.conj().T @ responses
            gamma_cross = self.cd._gamma_cross(current, group, base_cd, c1, gamma_mode)
            diagonal = candidate_energy + ridge
            mask = self.cd._valid(current, group, tolerance)
            valid[:, first:last] = mask
            for slot in range(P):
                projectors = _trial_projectors(graph_delays, graph_dopplers, slot, delays[first:last],
                                               dopplers[first:last], self.n, self.tau)
                matrices = np.broadcast_to(base_gram, (len(group), P, P)).copy()
                matrices[:, :, slot] = cross.T
                matrices[:, slot, :] = cross.T.conj()
                matrices[:, slot, slot] = diagonal
                gamma = np.broadcast_to(base_gamma, matrices.shape).copy()
                gamma[:, :, slot] = gamma_cross.T
                gamma[:, slot, :] = gamma_cross.T.conj()
                gamma[:, slot, slot] = self.total
                matrices += _replace_spectrum(gamma, projectors, self.total, self.arm)
                matrices = (matrices + matrices.swapaxes(-1, -2).conj()) * .5
                rhs = np.broadcast_to(b, (len(group), P)).copy()
                rhs[:, slot] = candidate_b
                gains = np.linalg.solve(matrices, rhs[..., None])[..., 0]
                values = y_energy - np.einsum('ij,ij->i', rhs.conj(), gains).real
                if not np.isfinite(values).all():
                    raise FloatingPointError('nonfinite unified trial score')
                scores[slot, first:last] = values
                active = np.any(projectors != 0, axis=(1, 2))
                self.census['scored_trials'] += len(group)
                self.census['nonempty_scored_trials'] += int(np.count_nonzero(active))
                self.census['valid_trials'] += int(np.count_nonzero(mask[slot]))
                self.census['nonempty_trials'] += int(np.count_nonzero(active & mask[slot]))
                counts['joint_gain_solves'] += len(group)
                if self.check_scores:
                    for j, candidate in enumerate(group):
                        trial = current.copy()
                        trial[slot] = candidate
                        *_, expected, _ = self.system(Y, xt, v, trial, c1, c2, ridge, gamma_mode)
                        error = float(abs(values[j] - expected) / abs(expected)) if expected else float(abs(values[j]))
                        self.census['checked_trials'] += 1
                        self.census['max_relative_score_error'] = max(self.census['max_relative_score_error'], error)
                        if error > 1e-10:
                            raise AssertionError(f'unified trial score discrepancy {error:.3g} at {slot}, {candidate}')
            counts['global_candidate_columns'] += len(group)
            counts['global_slot_tests'] += P * len(group)
            counts['global_duplicate_rejections'] += int(np.count_nonzero(~mask))
        return scores, valid


def unified_route(full, cd, tau=TAU, *, arm='U', check_scores=False, response_cache=None):
    def reopen(Y, x, v, paths, *, strategy, **kwargs):
        total = float(v.sum())
        reference = _reference_arm(arm, tau, total)
        if reference == 'A2':
            return full.reopen_geometry(Y, x, v, paths, strategy=strategy, **dict(kwargs, gamma_mode='diag'))
        if reference == 'CD':
            return cd.reopen_geometry(Y, x, v, paths, strategy=strategy, **kwargs)
        if kwargs['gamma_mode'] != 'full':
            raise ValueError('Spectral CSTATE requires the CODELAY reference covariance')
        engine = _SpectralGeometry(cd, tau, total, len(v), check_scores, arm, response_cache)
        scope = dict(cd.reopen_geometry.__globals__, _start_pass=engine.start_pass, _check_pass=engine.check_pass,
                     _system=engine.system, _direct_scores=engine.direct_scores)
        exec(_pass_code(full.reopen_geometry), scope)
        result = scope['reopen_geometry'](Y, x, v, paths, strategy='direct', **kwargs)
        result.diagnostics['projector_census'] = engine.census
        return result

    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen)


def _pairs(delays):
    _, counts = np.unique(delays, return_counts=True)
    return int(np.sum(counts * (counts - 1) // 2))


def _decision(result):
    """Compact identity of proposed and accepted exchange actions in order."""
    def action(record, path):
        return None if record is None else [record['slot'], record[path]]

    return [[action(step['selected'], 'replacement'), action(step['accepted'], 'new')]
            for step in result.global_trace]


def _geometry_record(result):
    first_edit = None
    if result.edits:
        first = result.edits[0]
        entering = result.global_trace[0]['entering_paths']
        other_delays = {p['delay'] for i, p in enumerate(entering) if i != first['slot']}
        first_edit = 'existing_delay' if first['new']['delay'] in other_delays else 'new_delay'
    return dict(atom_count=len(result.paths), co_delay_pairs=_pairs([p.delay for p in result.paths]),
                first_edit_type=first_edit, decision=_decision(result),
                state=dict(paths=[[p.delay, p.doppler] for p in result.paths],
                           gains_sha=stage3.digest(result.gains), gamma_sha=stage3.digest(result.diagnostics['gamma']),
                           objective=result.objective_after))


def _true_codelay(truth):
    delays = np.asarray(truth['l_i'])
    dopplers = np.asarray(truth['k_real'])
    same = delays[:, None] == delays[None, :]
    close = abs(dopplers[:, None] - dopplers[None, :]) < .5
    return bool(np.any(np.triu(same & close, k=1)))


def _support_system(full, cd, v, arm, tau):
    total = float(v.sum())
    reference = _reference_arm(arm, tau, total)
    if reference == 'A2':
        return full._system, 'diag'
    if reference == 'CD':
        return cd._system, 'full'
    return _SpectralGeometry(cd, tau, total, len(v), False, arm).system, 'full'


def admission_readout(full, cd, Y, x, v, traces, *, c1, c2, ridge, tau=TAU):
    """Compare a fixed A2-selected candidate and each arm's best new delay."""
    a2 = traces['A2']
    selected = a2['selected']
    if selected is None:
        return None
    slot = selected['slot']
    target = selected['replacement']
    paths = [cd.Path(p['delay'], p['doppler']) for p in a2['entering_paths']]
    retained = paths[:slot] + paths[slot + 1:]
    target_paths = paths.copy()
    target_paths[slot] = cd.Path(target['delay'], target['doppler'])
    joined = np.asarray([p.doppler for p in target_paths if p.delay == target['delay']])
    if len(joined) == 1 or not block_projector(joined, len(v), tau)[1]:
        return None
    delays, dopplers = a2['candidate_delays'], a2['candidate_dopplers']
    absent = ~np.isin(delays, [p.delay for p in paths])
    competitors = np.flatnonzero(absent & a2['valid'][slot])
    if not len(competitors):
        raise AssertionError('A2-selected admission unit has no legal new-delay candidate')
    target_index, = np.flatnonzero((delays == target['delay']) & (dopplers == target['doppler']))
    if not a2['valid'][slot, target_index]:
        raise AssertionError('A2 selected an illegal admission candidate')

    xt = full.daft(x, c1, c2, inverse=True)
    by_arm = {}
    for arm in ARMS[1:]:
        system, mode = _support_system(full, cd, v, arm, tau)
        *_, anchor, _ = system(Y, xt, v, retained, c1, c2, ridge, mode)
        if arm in traces:
            step = traces[arm]
            if (step['entering_paths'] != a2['entering_paths']
                    or not np.array_equal(step['valid'][slot], a2['valid'][slot])
                    or not np.array_equal(step['candidate_delays'], delays)
                    or not np.array_equal(step['candidate_dopplers'], dopplers)):
                raise AssertionError('V5-adm arms must score the same saved first-exchange support and bank')
            cost = step['scores'][slot]
            phantom_cost = cost[target_index]
            best = competitors[np.argmin(cost[competitors])]
            new_cost = cost[best]
        else:
            # A leverage run can omit an end-to-end arm. Score only its needed
            # supports here, with the same exact covariance and fixed slot.
            def objective(index):
                trial = paths.copy()
                trial[slot] = cd.Path(int(delays[index]), float(dopplers[index]))
                *_, value, _ = system(Y, xt, v, trial, c1, c2, ridge, mode)
                return value

            phantom_cost = objective(target_index)
            new_cost, best = min((objective(index), index) for index in competitors)
        phantom_gain, new_gain = float(anchor - phantom_cost), float(anchor - new_cost)
        by_arm[arm] = dict(phantom_gain=phantom_gain, new_delay_gain=new_gain,
                          new_delay=dict(delay=int(delays[best]), doppler=float(dopplers[best])),
                          preference=bool(phantom_gain > new_gain))
    return dict(slot=slot, phantom=target, entering_paths=a2['entering_paths'], by_arm=by_arm)


def one(ctx, full, cd, base, s, rho, snr, frame, *, tau=TAU, check_scores=False,
        arms=ARMS, admission=False):
    if admission and 'A2' not in arms:
        raise ValueError('V5-adm requires an A2 first-exchange trace')
    raw, obs, truth = stage3.observed(ctx, base, rho, snr)
    t0 = time.process_time()
    dec, arrays, syndrome, _ = stage3.e1.f0_state(ctx, obs)
    f0_seconds = time.process_time() - t0
    f0 = stage3.decoded(ctx, dec, truth)
    r1_delays = arrays['r1_delays']
    original = dict(**f0, atom_count=len(r1_delays), co_delay_pairs=_pairs(r1_delays),
                    first_edit_type=None, decision=[], state=None)
    rows = {'F0': dict(original, seconds=f0_seconds)}
    censuses = {}
    traces = {}
    response_cache = {}
    admission_state = None
    for name in arms:
        if name == 'F0':
            continue
        if not syndrome:
            rows[name] = dict(original, seconds=0.)
            continue
        kernel = (unified_route(full, cd, tau, arm=name, check_scores=check_scores, response_cache=response_cache)
                  if name in SPECTRAL_ARMS else {'A2': full, 'CD': cd}[name])
        stamp = time.process_time()
        br = stage3.e1.run_branch(ctx, kernel, obs, arrays, 'A2' if name == 'A2' else 'A1')
        seconds = time.process_time() - stamp
        result = br['result']
        rows[name] = dict(**stage3.decoded(ctx, br['decoder'], truth),
                          **_geometry_record(result), seconds=seconds)
        if name in SPECTRAL_ARMS:
            if 'projector_census' in result.diagnostics:
                censuses[name] = result.diagnostics['projector_census']
            else:
                censuses[name] = dict(_empty_census(),
                    scored_trials=sum(step['slot_tests'] for step in result.global_trace),
                    valid_trials=sum(step['valid_slot_tests'] for step in result.global_trace))
        if admission:
            traces[name] = result.global_trace[0]
            if name == 'A2':
                admission_state = br['ce_mu'], br['ce_variance']
    row = dict(scenario=s, rho_permille=rho, snr_centi_db=snr, frame=frame, syndrome=syndrome,
               truth=stage3.truth_record(obs, truth), inputs=stage3.input_record(raw, obs), arms=rows)
    decisions_differ = 'U' in rows and 'CD' in rows and rows['U']['decision'] != rows['CD']['decision']
    row['census'] = dict(censuses.get('U', _empty_census()), decisions_differ=decisions_differ,
                         true_close_codelay=_true_codelay(truth) if decisions_differ else None,
                         by_arm=censuses)
    if admission:
        stamp = time.process_time()
        row['admission'] = None
        if admission_state is not None and f0['errors'] > 0:
            mu, v = admission_state
            c1, c2 = ctx.system.c1, ctx.system.c2
            Y = full.daft(obs['y'], c1, c2, inverse=True)
            row['admission'] = admission_readout(full, cd, Y, obs['pilot'] + mu, v, traces,
                                                  c1=c1, c2=c2, ridge=float(obs['sigma2']), tau=tau)
        row['admission_seconds'] = time.process_time() - stamp
    return row


def synthetic_gate(full, cd):
    n, tau = 32, TAU
    v = np.linspace(.05, .4, n)
    delays = np.array([0, 0, 2, 2, 4])
    dopplers = np.array([0., 0., -.25, .25, 1.])
    p = low_projector(delays, dopplers, n, tau)
    np.testing.assert_allclose(p @ p, p, rtol=0, atol=1e-12)
    covariances = {arm: support_covariance(full, cd, v, delays, dopplers, .02, arm=arm)
                   for arm in ARMS[1:]}
    cd_gamma = covariances['CD']
    scalar = v.sum() * np.eye(len(delays))
    np.testing.assert_allclose(covariances['C-hi'] + covariances['C-lo'], cd_gamma + scalar,
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(covariances['U'] - covariances['C-hi'], p @ cd_gamma @ p,
                               rtol=0, atol=1e-12)
    equal = np.array([.5, .5, 0., 0., 0.])
    np.testing.assert_allclose(covariances['U'] @ equal, cd_gamma @ equal, rtol=0, atol=1e-12)
    rng = np.random.default_rng(14907)
    Y = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    x = rng.standard_normal(n) + 1j * rng.standard_normal(n)
    initial = [cd.Path(int(d), float(nu)) for d, nu in zip(delays, [0., .225, -.25, .25, 1.])]
    opts = dict(strategy='compact', c1=.02, c2=.01, ridge=.1, max_delay=4,
                max_edits=2, local_passes=2, gamma_mode='full')
    live = {'A2': full.reopen_geometry(Y, x, v, initial, **dict(opts, gamma_mode='diag')),
            'CD': cd.reopen_geometry(Y, x, v, initial, **opts)}
    shifted = dopplers.copy()
    shifted[3] = 1.2
    assert not np.allclose(low_projector(delays, shifted, n, tau), p)
    checks = {}
    response_cache = {}
    for arm in SPECTRAL_ARMS:
        gamma = covariances[arm]
        np.testing.assert_allclose(gamma, gamma.conj().T, rtol=0, atol=1e-12)
        assert np.linalg.eigvalsh(gamma).min() >= -1e-12
        np.testing.assert_allclose(gamma[-1], cd_gamma[-1], rtol=0, atol=1e-12)
        route = unified_route(full, cd, arm=arm, check_scores=True, response_cache=response_cache)
        new = route.reopen_geometry(Y, x, v, initial, **opts)
        live[arm] = new
        for variance, cutoff in ((v, 0.), (np.zeros(n), tau)):
            ref = (full.reopen_geometry(Y, x, variance, initial, **dict(opts, gamma_mode='diag'))
                   if arm == 'C-lo' else cd.reopen_geometry(Y, x, variance, initial, **opts))
            reduced = unified_route(full, cd, cutoff, arm=arm).reopen_geometry(Y, x, variance, initial, **opts)
            assert _geometry_record(ref) == _geometry_record(reduced)
            for a, b in zip(ref.global_trace, reduced.global_trace, strict=True):
                np.testing.assert_array_equal(a['scores'], b['scores'])
                np.testing.assert_array_equal(a['valid'], b['valid'])
        engine = _SpectralGeometry(cd, tau, float(v.sum()), n, False, arm)
        engine.start_pass([cd.Path(int(d), float(nu)) for d, nu in zip(delays, dopplers)])
        moved_base = engine.base_variance(v, delays, shifted, .02)
        expected = _replace_spectrum(moved_base, p, float(v.sum()), arm)
        np.testing.assert_allclose(engine.variance(v, delays, shifted, .02), expected, rtol=0, atol=1e-12)
        final_gamma = support_covariance(full, cd, v, [p.delay for p in new.paths],
                                         [p.doppler for p in new.paths], opts['c1'], arm=arm)
        np.testing.assert_array_equal(new.diagnostics['gamma'], final_gamma)
        result = new.diagnostics['projector_census']
        assert result['checked_trials'] > 0 and result['nonempty_trials'] > 0
        assert result['passes_checked'] == opts['local_passes']
        checks[arm] = dict(min_eigenvalue=float(np.linalg.eigvalsh(gamma).min()), **result)

    traces = {arm: result.global_trace[0] for arm, result in live.items()}
    # Select a legal projector-active saved candidate explicitly so the test
    # covers the diagnostic without depending on a random A2 winner.
    traces['A2'] = dict(traces['A2'], selected=dict(slot=4, replacement=dict(delay=0, doppler=.25)))
    compare_opts = {k: opts[k] for k in ('c1', 'c2', 'ridge')}
    logged = admission_readout(full, cd, Y, x, v, traces, **compare_opts)
    recomputed = admission_readout(full, cd, Y, x, v, {k: trace for k, trace in traces.items() if k != 'U'}, **compare_opts)
    assert logged['slot'] == 4 and all(data['new_delay']['delay'] not in (0, 2, 4)
                                        for data in logged['by_arm'].values())
    for field in ('phantom_gain', 'new_delay_gain'):
        np.testing.assert_allclose(logged['by_arm']['U'][field], recomputed['by_arm']['U'][field],
                                   rtol=0, atol=1e-12)
    assert logged['by_arm']['U']['preference'] == recomputed['by_arm']['U']['preference']
    return dict(pass_=True, **checks['U'], by_arm=checks, admission_replay=True)
