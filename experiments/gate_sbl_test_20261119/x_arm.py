"""Phase 1 MIXED8 arms built on the frozen exchange and decoder."""

import hashlib
import json
from pathlib import Path
import sys
import time
from types import FunctionType, SimpleNamespace

import numpy as np
from scipy.optimize import linear_sum_assignment

from s_arm import block_census, gate_projector

EXPERIMENTS = Path(__file__).resolve().parents[1]
SOURCE = EXPERIMENTS / 'doublet_conflict_20261119'
sys.path.insert(0, str(SOURCE))
import mixed8_receiver as frozen  # noqa: E402

ARCHIVE_FRAMES = range(1000, 1020)
ARMS = ('F0', 'CD', 'G-ex')
cstate = frozen.cstate


def canonical_bytes(record):
    return json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def resolution(truth, atoms):
    """Match two distinct fitted atoms to the true 0.35-bin pair."""
    delays, dopplers = np.asarray(truth['l_i']), np.asarray(truth['k_real'])
    candidates = [(int(delay), pair) for delay in np.unique(delays)
                  if len(pair := np.sort(dopplers[delays == delay])) == 2
                  and np.isclose(np.ptp(pair), .35, rtol=0., atol=1e-12)]
    [(delay, true_pair)] = candidates
    fitted = np.unique([nu for ell, nu in atoms if ell == delay])
    matched, errors = None, None
    if len(fitted) >= 2:
        costs = abs(true_pair[:, None] - fitted)
        refs, picks = linear_sum_assignment(costs)
        matched = fitted[picks].tolist()
        errors = costs[refs, picks].tolist()
    return dict(true_delay=delay, true_dopplers=true_pair.tolist(), distinct_atoms=len(fitted),
                assigned_dopplers=matched, assignment_errors=errors,
                resolved=errors is not None and max(errors) <= .10)


class _GateGeometry(cstate._SpectralGeometry):
    """Replace the frozen U projector at its existing construction points."""

    def __init__(self, cd, x, v, c1, c2, ridge, check_scores=False):
        super().__init__(cd, cstate.TAU, float(v.sum()), len(v), check_scores, 'U')
        self.xt = cd.daft(x, c1, c2, inverse=True)
        self.c1, self.c2, self.ridge = c1, c2, ridge
        self.pass_blocks = []
        self.refit_blocks = []

    def _block(self, columns, dopplers):
        from physical import dkernel

        if len(dopplers) == 1:
            return np.zeros((1, 1), dtype=complex), 0
        kernel = dkernel(dopplers[None, :] - dopplers[:, None], self.n)
        return gate_projector(columns.conj().T @ columns, (kernel + kernel.conj().T) * .5,
                              self.total, self.ridge)

    def _support(self, delays, dopplers, columns, *, census=False):
        projector = np.zeros((len(delays), len(delays)), dtype=complex)
        blocks = []
        for delay in np.unique(delays):
            slots = np.flatnonzero(delays == delay)
            block, rank = self._block(columns[:, slots], dopplers[slots])
            projector[np.ix_(slots, slots)] = block
            if census:
                low, low_rank = cstate.block_projector(dopplers[slots], self.n, self.tau)
                blocks.append(dict(delay=int(delay), **block_census(block, rank, low, int(low_rank))))
        return projector, blocks

    def _support_paths(self, paths, *, census=False):
        delays = np.array([p.delay for p in paths])
        dopplers = np.array([p.doppler for p in paths])
        columns = self.cd._responses(self.xt, paths, self.c1, self.c2)
        return self._support(delays, dopplers, columns, census=census)

    def start_pass(self, current):
        self.fixed, blocks = self._support_paths(current, census=True)
        self.pass_blocks.append(blocks)

    def variance(self, v, delays, dopplers, c1):
        gamma = self.base_variance(v, delays, dopplers, c1)
        if self.fixed is not None:
            return cstate._replace_spectrum(gamma, self.fixed, self.total, self.arm)
        paths = [self.cd.Path(delay, nu) for delay, nu in zip(delays, dopplers, strict=True)]
        projector, blocks = self._support_paths(paths, census=True)
        self.refit_blocks.append(blocks)
        return cstate._replace_spectrum(gamma, projector, self.total, self.arm)

    def trial_projectors(self, columns, delays, dopplers, slot, trial_delays, trial_dopplers,
                         candidates):
        keep = np.flatnonzero(np.arange(len(delays)) != slot)
        common = np.zeros((len(delays), len(delays)), dtype=complex)
        common[np.ix_(keep, keep)], _ = self._support(delays[keep], dopplers[keep], columns[:, keep])
        projectors = np.broadcast_to(common, (len(trial_delays), *common.shape)).copy()
        for delay in np.unique(delays[keep]):
            members = keep[delays[keep] == delay]
            slots = np.sort(np.r_[slot, members])
            pos = np.searchsorted(slots, slot)
            block_columns = columns[:, slots].copy()
            block_dopplers = dopplers[slots].copy()
            for row in np.flatnonzero(trial_delays == delay):
                block_columns[:, pos] = candidates[:, row]
                block_dopplers[pos] = trial_dopplers[row]
                projectors[row][np.ix_(slots, slots)], _ = self._block(block_columns, block_dopplers)
        return projectors

    def direct_scores(self, Y, xt, v, current, B, Q, b, c1, c2, ridge, delays, dopplers,
                      chunk_size, energy, tolerance, counts, gamma_mode):
        # The frozen scorer constructs and caches the exact mean-waveform bank
        # before asking for projectors. Bind only that projector callback.
        chunks = {(delays[start], dopplers[start]): (start, min(start + chunk_size, len(delays)))
                  for start in range(0, len(delays), chunk_size)}

        def project(graph_delays, graph_dopplers, slot, trial_delays, trial_dopplers, n, tau):
            _, responses, _, _ = self.response_cache[chunks[trial_delays[0], trial_dopplers[0]]]
            return self.trial_projectors(B, graph_delays, graph_dopplers, slot,
                                         trial_delays, trial_dopplers, responses)

        base = cstate._SpectralGeometry.direct_scores
        bound = FunctionType(base.__code__, dict(base.__globals__, _trial_projectors=project))
        return bound(self, Y, xt, v, current, B, Q, b, c1, c2, ridge, delays, dopplers,
                     chunk_size, energy, tolerance, counts, gamma_mode)

    def cd_noop(self, result, entering_paths, chunk_size):
        """Prove the gate is a no-op at every accepted CD path and legal trial."""
        projector, blocks = self._support_paths(entering_paths, census=True)
        if np.any(projector):
            return False
        self.refit_blocks.append(blocks)
        for step in result.global_trace:
            current = [self.cd.Path(**p) for p in step['entering_paths']]
            delays = np.array([p.delay for p in current])
            dopplers = np.array([p.doppler for p in current])
            columns = self.cd._responses(self.xt, current, self.c1, self.c2)
            trial_delays, trial_dopplers = step['candidate_delays'], step['candidate_dopplers']
            valid = step['valid']
            for start in range(0, len(trial_delays), chunk_size):
                indices = slice(start, start + chunk_size)
                group_delays, group_dopplers = trial_delays[indices], trial_dopplers[indices]
                group = [self.cd.Path(int(d), float(nu))
                         for d, nu in zip(group_delays, group_dopplers, strict=True)]
                candidates = self.cd._responses(self.xt, group, self.c1, self.c2)
                for slot in range(len(current)):
                    projectors = self.trial_projectors(columns, delays, dopplers, slot,
                                                       group_delays, group_dopplers, candidates)
                    active = np.any(projectors != 0, axis=(1, 2))
                    legal = valid[slot, indices]
                    if np.any(active & legal):
                        return False
                    self.census['scored_trials'] += len(group)
                    self.census['valid_trials'] += int(np.count_nonzero(legal))
                    self.census['nonempty_scored_trials'] += int(np.count_nonzero(active))
            if step['accepted'] is not None:
                current[step['accepted']['slot']] = self.cd.Path(**step['accepted']['new'])
                projector, blocks = self._support_paths(current, census=True)
                if np.any(projector):
                    return False
                self.refit_blocks.append(blocks)
        current = ([self.cd.Path(**p) for p in result.local_trace[0]['local_phase_entering_paths']]
                   if result.local_trace else result.paths)
        for trial in result.local_trace:
            if trial['slot'] == 0:
                self.start_pass(current)
                if np.any(self.fixed):
                    return False
            current[trial['slot']] = self.cd.Path(**trial['endpoint'])
        self.start_pass(result.paths)
        return not bool(np.any(self.fixed))


def gated_route(full, cd, *, substitute_low=False, cd_result=None, check_scores=False):
    """The shared exchange loop, with either the gate or the frozen low projector."""
    census = cstate._empty_census()

    def reopen(Y, x, v, paths, *, strategy, **kwargs):
        if kwargs['gamma_mode'] != 'full':
            raise ValueError('G-ex requires the closed-form co-delay covariance')
        total = float(v.sum())
        if not total:
            return (cd_result if cd_result is not None
                    else cd.reopen_geometry(Y, x, v, paths, strategy=strategy, **kwargs))
        if substitute_low:
            engine = cstate._SpectralGeometry(cd, cstate.TAU, total, len(v), check_scores, 'U')
        else:
            engine = _GateGeometry(cd, x, v, kwargs['c1'], kwargs['c2'], kwargs['ridge'], check_scores)
            if cd_result is not None and engine.cd_noop(cd_result, paths, kwargs['chunk_size']):
                census.update(engine.census, local_pass_blocks=engine.pass_blocks[:-1],
                              final_blocks=engine.pass_blocks[-1], active_refits=0,
                              refit_blocks=engine.refit_blocks, used_cd_noop=True)
                return cd_result
            engine.census = cstate._empty_census()
            engine.census.update(passes_checked=0, max_pass_increase=0.)
            engine.pass_blocks.clear()
            engine.refit_blocks.clear()
            engine.fixed = None
        scope = dict(cd.reopen_geometry.__globals__, _start_pass=engine.start_pass,
                     _check_pass=engine.check_pass, _system=engine.system,
                     _direct_scores=engine.direct_scores)
        exec(cstate._pass_code(full.reopen_geometry), scope)
        result = scope['reopen_geometry'](Y, x, v, paths, strategy='direct', **kwargs)
        census.update(engine.census)
        if not substitute_low:
            census.update(local_pass_blocks=engine.pass_blocks[:-1], final_blocks=engine.pass_blocks[-1],
                          active_refits=sum(any(b['gate_rank'] for b in blocks) for blocks in engine.refit_blocks),
                          refit_blocks=engine.refit_blocks, used_cd_noop=False)
        return result

    return SimpleNamespace(Path=cd.Path, reopen_geometry=reopen, census=census)


def _diagnostics(ctx, decoded, record, truth, delays):
    return dict(decoded=record['info_errors'] == 0, fer=int(record['info_errors'] > 0),
                syndrome=int(ctx.hd.syndrome_weight(ctx, decoded['decoded'])),
                co_delay_pairs=cstate._pairs(delays), beta=None, iterations=None, converged=None,
                resolution_035=resolution(truth, record['atoms']))


# Source: frozen mixed8_receiver.one; bind G-ex and retain diagnostics because the frozen arm dispatch cannot receive a new route.
def one(ctx, full, cd, frame, *, gate):
    if type(frame) is not int or frame not in ARCHIVE_FRAMES or gate not in ('actual', 'low'):
        raise ValueError('Phase 1 MIXED8 replay is limited to frames 1000–1019 for G2 or G5')
    start = time.process_time()
    screen = frozen.screen
    e2 = screen.e2
    snr = frozen.MAIN_SNR_DB
    msg = e2.ch.cluster_message(ctx, screen.SEED, screen.RHO, frame)
    raw, diag = screen.physical_frame(ctx, frame, frozen.SCENARIO, msg)
    obs, truth, closure = frozen._observe(ctx, raw, diag, snr)
    n = len(obs['y'])
    stamp = time.process_time()
    decoded, arrays, syndrome, _ = e2.e1d.f0_state(ctx, obs)
    delays, dopplers = arrays['r1_delays'], arrays['r1_dopplers']
    if not 0 < len(delays) <= screen.SLOTS:
        raise AssertionError(f'F0 exceeded the {screen.SLOTS}-slot capacity: {len(delays)}')
    f0 = frozen._record(ctx, decoded, truth, delays, dopplers, n)
    diagnostics = {'F0': _diagnostics(ctx, decoded, f0, truth, delays)}
    rows = {'F0': f0}
    cpu = {'F0': time.process_time() - stamp}
    census = cstate._empty_census()
    if gate == 'actual':
        census.update(local_pass_blocks=[], final_blocks=[], refit_blocks=[], active_refits=0, used_cd_noop=False)
    cd_result = None
    for arm in ARMS[1:]:
        stamp = time.process_time()
        if syndrome:
            route = (gated_route(full, cd, substitute_low=gate == 'low', cd_result=cd_result)
                     if arm == 'G-ex' else cd)
            branch = e2.e1d.run_branch(ctx, route, obs, arrays, 'A1')
            result = branch['result']
            fitted_delays, fitted_dopplers = [p.delay for p in result.paths], [p.doppler for p in result.paths]
            rows[arm] = frozen._record(ctx, branch['decoder'], truth, fitted_delays, fitted_dopplers, n,
                                       result=result)
            diagnostics[arm] = _diagnostics(ctx, branch['decoder'], rows[arm], truth, fitted_delays)
            if arm == 'CD':
                cd_result = result
            else:
                census.update(route.census)
        else:
            rows[arm] = f0
            diagnostics[arm] = diagnostics['F0']
        cpu[arm] = time.process_time() - stamp

    fingerprints = {arm: hashlib.sha256(canonical_bytes(dict(record=rows[arm], **diagnostics[arm]))).hexdigest()
                    for arm in ('CD', 'G-ex')}
    row = dict(scenario=frozen.SCENARIO, frame=frame, snr_db=snr, syndrome=int(syndrome),
               closure=closure, entering_slots=len(delays),
               info_sha=ctx.array_hash(raw['info']), noise_sha=ctx.array_hash(raw['noise']),
               doublet_separations=[float(np.ptp(truth['k_real'][truth['l_i'] == delay]))
                                    for delay in (6, 22)],
               inputs=cstate.stage3.input_record(raw, obs),
               truth=cstate.stage3.truth_record(obs, truth), arms=rows, arm_diagnostics=diagnostics,
               gate_census=census, output_fingerprints=fingerprints, arm_cpu_seconds=cpu)
    return dict(row, cpu_seconds=time.process_time() - start)
