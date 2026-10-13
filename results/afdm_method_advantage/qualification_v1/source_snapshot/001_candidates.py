"""Observed-only bounded candidate acquisition; fixed-support gain profile scoring.

No decoder/truth inputs, no performance claim. Dynamic geometry search changes
which valid codewords get an expensive physical score, not just list ordering.
"""
import heapq
import importlib.util
import itertools
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'geometry'))
from profile_geometry import ProfileGeometry, channel_jacobian, realify
SPEC = importlib.util.spec_from_file_location('acquisition_ldpc', ROOT / 'experiments/sp_afdm_frozen_20260920/upstream/spafdm_receiver_handoff/afdm_sp_joint_unrolled/e1_ldpc.py')
ldpc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ldpc)


def binary_matrix(h):
    h = np.asarray(h)
    if h.ndim != 2 or not np.isfinite(h).all() or not np.isin(h, (0, 1)).all():
        raise ValueError('H must be a finite binary parity matrix')
    return h.astype(np.uint8)


def reliable_basis(h, llr):
    """Eliminate least reliable parity positions; encode reliable free bits.

    Reuses frozen GF(2) RREF. Unlike fixed-generator bit flips, this depends on
    the actual observation reliability permutation (ties by original bit index).
    """
    h = binary_matrix(h)
    llr = np.asarray(llr, float)
    if llr.shape != (h.shape[1],) or not np.isfinite(llr).all():
        raise ValueError('finite llr of length H.shape[1] required')
    order = np.lexsort((np.arange(len(llr)), np.abs(llr)))
    reduced, pivot, free, rank = ldpc._gf2_rref(h[:, order])
    free_original = order[free]
    g = np.zeros((len(llr), len(free)), dtype=np.uint8)
    g[free_original, np.arange(len(free))] = 1
    g[order[pivot], :] = reduced[:, free]
    info = (llr[free_original] < 0).astype(np.uint8)
    anchor = (g @ info) & 1
    if np.any((h @ anchor) & 1):
        raise ArithmeticError('reliable encoder produced illegal anchor')
    return dict(anchor=anchor, generator=g, free=free_original, rank=rank, permutation=order)


def symbols(word, scale):
    w = np.asarray(word)
    if w.ndim != 1 or len(w)%2 or not np.isin(w, (0, 1)).all() or not np.isfinite(scale) or scale <= 0:
        raise ValueError('even binary I-then-Q word and positive scale required')
    return ldpc.qpsk_map(w, scale=scale)


class PhysicalScore:
    """Exact least-squares gain profile at FIXED delay/Doppler, not global CE.

    gain_precision>=0 penalizes distance to receiver-provided channel gains.
    This is a shared working regularizer, not an independent posterior prior.
    known_channel=True disables fitting, yielding ordinary known-channel NLL.
    """
    def __init__(self, channel, y, pilot, sigma2, scale, gain_precision=0., known_channel=False):
        self.channel = channel
        self.y = np.asarray(y, complex)
        self.pilot = np.asarray(pilot, complex)
        if self.y.shape != (channel.n,) or self.pilot.shape != (channel.n,) or not np.isfinite(self.y).all() or not np.isfinite(self.pilot).all():
            raise ValueError('observed y/pilot dimensions or finiteness invalid')
        if not np.isfinite(sigma2) or sigma2 <= 0 or not np.isfinite(gain_precision) or gain_precision < 0:
            raise ValueError('sigma2 positive, gain_precision nonnegative required')
        self.sigma2, self.scale = sigma2, scale
        self.gain_precision, self.known_channel = gain_precision, known_channel
        self.calls = 0
        self.seconds = 0.

    def __call__(self, word):
        start = time.perf_counter()
        x = self.pilot + symbols(word, self.scale)
        if self.known_channel:
            gain = self.channel.gains.copy()
            residual = self.channel.apply(x)-self.y
        else:
            physical_a = self.channel.regressors(x)
            a = physical_a / np.sqrt(self.sigma2)
            b = self.y / np.sqrt(self.sigma2)
            if self.gain_precision:
                a = np.vstack((a, np.sqrt(self.gain_precision)*np.eye(self.channel.p)))
                b = np.r_[b, np.sqrt(self.gain_precision)*self.channel.gains]
            gain = np.linalg.lstsq(a, b, rcond=None)[0]
            residual = physical_a @ gain-self.y
        value = float(np.vdot(residual, residual).real/self.sigma2)
        if not self.known_channel:
            value += self.gain_precision*float(np.sum(abs(gain-self.channel.gains)**2))
        if not np.isfinite(value):
            raise FloatingPointError('nonfinite physical candidate score')
        self.calls += 1
        self.seconds += time.perf_counter()-start
        return value, gain


def acquire(h, llr, channel, y, pilot, sigma2, *, scale, mode='geometry', list_size=16,
            branching=12, max_depth=3, gain_precision=0., nuisance_precision=0.1,
            known_channel=False):
    """Return legal candidates, selection, trajectories and actual call/timing counts.

    osd: bounded weight-ordered OSD-style patterns on least reliable information
    positions; not exhaustive OSD at a named order unless all patterns fit.
    geometry: best-first dynamic neighborhood, at most branching children per
    expanded node, fixed anchor Jacobian for acquisition only. Physical scoring
    of popped nodes is exactly the same scorer as osd. Prefix-safe list sizes.
    No hidden wall timeout: caller must bound list_size/branching/depth and charge
    returned total seconds as part of the complete receiver wrapper.
    """
    start = time.perf_counter()
    if mode not in ('osd', 'geometry') or any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in (list_size, branching, max_depth)):
        raise ValueError('invalid acquisition mode or integer budget')
    if not np.isfinite(nuisance_precision) or nuisance_precision < 0:
        raise ValueError('nuisance_precision must be nonnegative')
    h = binary_matrix(h)
    if h.shape[1] != 2*channel.n:
        raise ValueError('H columns must match I-then-Q 2N bits')
    basis_start = time.perf_counter()
    basis = reliable_basis(h, llr)
    basis_seconds = time.perf_counter()-basis_start
    anchor, g, free = basis['anchor'], basis['generator'], basis['free']
    moves = np.lexsort((free, np.abs(np.asarray(llr)[free])))[:branching]
    def word_for(pattern):
        out = anchor.copy()
        for pos in pattern:
            out ^= g[:, pos]
        return out
    physical = PhysicalScore(channel, y, pilot, sigma2, scale, gain_precision, known_channel)
    init_start = time.perf_counter()
    geometry = None
    if mode == 'geometry':
        x0 = np.asarray(pilot)+symbols(anchor, scale)
        j = np.zeros((2*channel.n, 1)) if known_channel else channel_jacobian(channel, x0)
        geometry = ProfileGeometry(j, sigma2/2, nuisance_precision*np.eye(j.shape[1]))
    geometry_init_seconds = time.perf_counter()-init_start
    prescreen_calls, prescreen_seconds = 0, 0.
    previews = []
    def priority(pattern, word):
        nonlocal prescreen_calls, prescreen_seconds
        t = time.perf_counter()
        r = realify(channel.apply(np.asarray(pilot)+symbols(word, scale))-np.asarray(y))
        val = float(.5*geometry.value(r))
        prescreen_calls += 1
        prescreen_seconds += time.perf_counter()-t
        previews.append(dict(pattern=list(pattern), surrogate=val))
        return val
    candidates, gains, scores, patterns = [], [], [], []
    if mode == 'osd':
        # Lazy per-weight combinations: no full codebook/pool enumeration.
        iterator = itertools.chain.from_iterable(itertools.combinations(moves.tolist(), weight) for weight in range(min(max_depth, len(moves))+1))
        work = ((tuple(p), word_for(p)) for p in iterator)
    else:
        heap = [(priority((), anchor), (), anchor)]
        seen = {()}
        def dynamic():
            while heap:
                _, pattern, word = heapq.heappop(heap)
                yield pattern, word
                if len(pattern) >= max_depth:
                    continue
                for pos in moves:
                    if int(pos) in pattern:
                        continue
                    child = tuple(sorted((*pattern, int(pos))))
                    if child in seen:
                        continue
                    seen.add(child)
                    w = word_for(child)
                    heapq.heappush(heap, (priority(child, w), child, w))
        work = dynamic()
    for pattern, word in work:
        score, gain = physical(word)
        candidates.append(word)
        patterns.append(list(pattern))
        gains.append(gain)
        scores.append(score)
        if len(candidates) >= list_size:
            break
    winner = min(range(len(scores)), key=lambda i: (scores[i], patterns[i]))
    elapsed = time.perf_counter()-start
    return dict(decoded=candidates[winner].copy(), gains=gains[winner].copy(), candidates=np.asarray(candidates), scores=np.asarray(scores), selected=winner,
                patterns=patterns, previews=previews, anchor=anchor, free=free, moves=moves,
                counts=dict(physical_scores=physical.calls, geometry_prescreens=prescreen_calls, unique_candidates=len(candidates), channel_apply_calls=prescreen_calls+(physical.calls if known_channel else 0), regressor_calls=physical.calls if not known_channel else 0, jacobian_regressor_calls=2 if mode == 'geometry' and not known_channel else 0),
                timing=dict(total_seconds=elapsed, basis_seconds=basis_seconds, geometry_init_seconds=geometry_init_seconds, prescreen_seconds=prescreen_seconds, physical_score_seconds=physical.seconds),
                scope='fixed-support fixed-Doppler exact gain-profile scoring; acquisition surrogate is local; no truth consumed', mode=mode)
