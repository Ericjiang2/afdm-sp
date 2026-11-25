#!/usr/bin/env python3
"""Re-score finite rate-1/2 profiles on saved C1 EXIT curves and build one forest code."""
import argparse
from collections import Counter
from itertools import combinations
import json
from math import comb
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'ideas/l2'), str(ROOT)]
from l2_exit_schedule import DEC_ITERS, ROUNDS, outer as scalar_outer
import l2_exit_tunnel as exit_model
from afdm_sp_joint_unrolled.budgeted_support_diagnostics import array_hash
from afdm_sp_joint_unrolled.e1_ldpc import _edge_structs, _gf2_rref, decode_llr, encode
from codes import girth

N, M = 2048, 1024
MAX_DEGREES = (6, 8, 12, 20, 30)
COARSE = 16
SEED = 20261125
TARGET = 1 - 1e-4


def curves():
    phi = json.loads(exit_model.PHI.read_text())['Phi']
    x_a, y_a = exit_model.transfer(phi, '6.5', 'L28')
    x_b, y_b = exit_model.transfer(phi, '8', 'L28')
    grid = np.union1d(x_a, x_b)
    a, b = np.interp(grid, x_a, y_a), np.interp(grid, x_b, y_b)
    if np.any(b < a):
        raise ValueError('saved curves do not support a monotone SNR threshold search')
    return grid, a, b


def outer_many(counts, degrees, snr, curve):
    """Batched form of the original reset-and-decode schedule."""
    grid, at65, at8 = curve
    snr = np.broadcast_to(snr, len(counts))
    y = at65 + ((snr[:, None] - 6.5) / 1.5) * (at8 - at65)
    y = np.maximum.accumulate(np.clip(y, 0, 1), axis=1)
    edges = counts @ degrees
    dc, remainder = np.divmod(edges, M)
    check_low = (M - remainder) * dc / edges
    check_high = 1 - check_low
    lv = counts / N
    le = counts * degrees / edges[:, None]
    rounds = np.zeros(len(counts), dtype=int)
    ia = np.zeros(len(counts))
    ic = np.zeros(len(counts))
    rows = np.arange(len(counts))
    for step in range(1, ROUNDS + 1):
        index = np.clip(np.searchsorted(grid, ia, side='right') - 1, 0, len(grid) - 2)
        frac = (ia - grid[index]) / (grid[index + 1] - grid[index])
        channel = y[rows, index] + frac * (y[rows, index + 1] - y[rows, index])
        s_ch2 = np.where(channel > 0, exit_model.Jinv(channel) ** 2, 0)
        value = np.zeros(len(counts))
        active = rounds == 0
        for _ in range(DEC_ITERS):
            s_c2 = np.where(value > 0, exit_model.Jinv(value) ** 2, 0)
            iev = np.sum(le * exit_model.J(np.sqrt((degrees - 1) * s_c2[:, None] + s_ch2[:, None])), axis=1)
            s_ext = exit_model.Jinv(1 - iev)
            new = (1 - check_low * exit_model.J(np.sqrt(dc - 1) * s_ext)
                   - check_high * exit_model.J(np.sqrt(dc) * s_ext))
            converged = new - value < 1e-9
            value = np.where(active, new, value)
            active &= ~converged
            if not active.any():
                break
        ic = np.where(rounds == 0, value, ic)
        s_c2 = np.where(ic > 0, exit_model.Jinv(ic) ** 2, 0)
        ia = np.sum(lv * exit_model.J(np.sqrt(degrees * s_c2[:, None])), axis=1)
        rounds[(rounds == 0) & (ic > TARGET)] = step
        if np.all(rounds):
            break
    return rounds, ic, ia


def thresholds(counts, degrees, curve):
    low, high = np.full(len(counts), 5.), np.full(len(counts), 8.)
    opens_high = outer_many(counts, degrees, high, curve)[0] > 0
    opens_low = outer_many(counts, degrees, low, curve)[0] > 0
    for _ in range(9):
        mid = (low + high) / 2
        opens = outer_many(counts, degrees, mid, curve)[0] > 0
        high = np.where(opens, mid, high)
        low = np.where(opens, low, mid)
    high[~opens_high] = np.inf
    high[opens_low] = -np.inf
    return high


def screen(counts, d_max, curve):
    degrees = np.array([2, 3, d_max])
    threshold = thresholds(counts, degrees, curve)
    r65, ic65, _ = outer_many(counts, degrees, 6.5, curve)
    r8, ic8, _ = outer_many(counts, degrees, 8., curve)
    priority = np.lexsort((-ic8, -ic65, np.where(r65, r65, ROUNDS + 1), threshold))
    return priority, threshold, r65, r8


def finite_ensemble(counts, degrees):
    edges = counts * degrees
    return exit_model.ensemble(dict(zip(degrees, edges / edges.sum())), edges.sum() / M)


def describe(counts, d_max, curve, ensemble=None):
    degrees = np.array([2, 3, d_max])
    ensemble = finite_ensemble(counts, degrees) if ensemble is None else ensemble
    assert abs(ensemble['rate'] - .5) < 1e-12
    grid, y65, y8 = curve

    def evaluate(snr):
        y = np.maximum.accumulate(np.clip(y65 + (y8-y65) * (snr-6.5)/1.5, 0, 1))
        return scalar_outer(ensemble, grid, y)

    low, high = 5., 8.
    if evaluate(low)[0] is not None:
        threshold = dict(snr_db=low, censor='left', extrapolated=True)
    elif evaluate(high)[0] is None:
        threshold = dict(snr_db=high, censor='right', extrapolated=False)
    else:
        for _ in range(14):
            mid = (low + high) / 2
            if evaluate(mid)[0] is None:
                low = mid
            else:
                high = mid
        threshold = dict(snr_db=high, censor=None, extrapolated=high < 6.5)
    return dict(variable_counts={int(d): int(c) for d, c in zip(degrees, counts) if c},
                startup_10round=threshold,
                at_6p5=dict(zip(('rounds', 'detector_prior_trajectory'), evaluate(6.5))),
                at_8=dict(zip(('rounds', 'detector_prior_trajectory'), evaluate(8.))))


def low_weight_spectrum(matrix):
    packed = [int.from_bytes(row, 'little') for row in np.packbits(matrix.T, axis=1)]
    multiplicity = Counter(packed)
    assert not multiplicity[0]
    weight2 = sum(comb(count, 2) for count in multiplicity.values())
    pairs = Counter()
    triples = collisions = 0
    for a, b in combinations(packed, 2):
        syndrome = a ^ b
        triples += multiplicity[syndrome]
        collisions += pairs[syndrome]
        pairs[syndrome] += 1
    disjoint = collisions - (len(packed) - 2) * weight2
    assert triples % 3 == disjoint % 3 == 0
    return [0, weight2, triples // 3, disjoint // 3]


def build_matrix(counts, d_max, rng):
    degrees = rng.permutation(np.repeat([2, 3, d_max], counts))
    floor, high = divmod(int(degrees.sum()), M)
    caps = rng.permutation(np.repeat([floor, floor + 1], [M - high, high]))
    H = np.zeros((M, N), dtype=np.uint8)
    paths = np.array_split(rng.permutation(M), M - counts[0])
    degree2 = np.flatnonzero(degrees == 2)
    starts = np.concatenate([path[:-1] for path in paths])
    ends = np.concatenate([path[1:] for path in paths])
    H[starts, degree2] = H[ends, degree2] = 1
    residual = caps - H.sum(axis=1).astype(int)
    remaining = np.flatnonzero(degrees > 2)
    for col in remaining[np.argsort(-degrees[remaining], kind='stable')]:
        order = rng.permutation(M)
        chosen = order[np.argsort(-residual[order], kind='stable')[:degrees[col]]]
        if np.any(residual[chosen] == 0):
            raise ValueError('residual check capacities cannot realize profile')
        H[chosen, col] = 1
        residual[chosen] -= 1
    if not np.array_equal(H.sum(axis=0), degrees) or not np.array_equal(H.sum(axis=1), caps):
        raise ValueError('finite matrix degree mismatch')
    return H


def construct(counts, d_max, code_out):
    for seed in range(SEED, SEED + 16):
        H = build_matrix(counts, d_max, np.random.default_rng(seed))
        reduced, pivots, free, rank = _gf2_rref(H)
        if rank == M:
            break
    else:
        raise ValueError('no full-rank matrix in the registered structural seed sequence')
    parent = list(range(M))

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for col in H[:, H.sum(axis=0) == 2].T:
        a, b = (root(i) for i in np.flatnonzero(col))
        if a == b:
            raise ValueError('degree-2 cycle in resulting matrix')
        parent[b] = a
    components = len({root(i) for i in range(M)})
    assert components == M - counts[0]
    G = np.zeros((N, N - rank), dtype=np.uint8)
    G[free, np.arange(N - rank)] = 1
    G[pivots] = reduced[:, free]
    chk, var, row_ptr = _edge_structs(H)
    code = dict(H=H, G=G, chk=chk, var=var, row_ptr=row_ptr, k=N - rank)
    rng = np.random.default_rng(seed)
    for _ in range(8):
        word = encode(code, rng.integers(0, 2, size=N - rank, dtype=np.uint8))
        decoded, ok = decode_llr(code, 20 * (1 - 2 * word.astype(float)))
        assert not (H @ word % 2).any() and ok and np.array_equal(word, decoded)
    weights = low_weight_spectrum(H)
    with code_out.open('xb') as handle:
        np.savez_compressed(handle, H=H, G=G, free_cols=free, pivot_cols=pivots)
    return dict(seed=seed, rank=rank, n=N, k=N-rank, check_sha256=array_hash(H),
                check_counts=dict(Counter(H.sum(axis=1).tolist())), girth=girth(H),
                degree2_components=components, degree2_cycle_rank=0,
                codewords_weight_1_to_4=weights, noiseless_words=8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--code-out', type=Path, required=True)
    args = parser.parse_args()
    curve = curves()
    hexact = np.array([1377, 620, 51])
    baseline = describe(np.array([0, N, 0]), 30, curve)
    historical = describe(hexact, 30, curve, exit_model.ensemble({2:.45, 3:.30, 30:.25}, 6.))
    realized = describe(hexact, 30, curve)
    assert baseline['at_6p5']['rounds'] is None and historical['at_6p5']['rounds'] == 5
    for counts, expected in [(np.array([0, N, 0]), baseline), (hexact, realized)]:
        rounds, _, _ = outer_many(counts[None], np.array([2, 3, 30]), 6.5, curve)
        assert (int(rounds[0]) or None) == expected['at_6p5']['rounds']
    coarse = np.array([(n2, n3, N-n2-n3)
                       for n2 in [*range(0, M-1, COARSE), M-1]
                       for n3 in [*range(1, N-n2, COARSE), N-n2]])
    out = dict(_argv=sys.argv, _config=dict(family=list(MAX_DEGREES), n=N, m=M, max_n2=M-1,
               coarse_node_stride=COARSE, refine_radius=COARSE, coarse_centers_per_family=3,
               curve=str(exit_model.PHI.relative_to(ROOT)), rounds=ROUNDS, decoder_iterations=DEC_ITERS,
               check_information_target=TARGET, threshold_search_db=[5.,8.], construction_seed=SEED),
               regular=baseline, original_matching_ensemble=historical, original_matching_integer=realized,
               by_family={})
    choices = []
    for d_max in MAX_DEGREES:
        order, _, r65, _ = screen(coarse, d_max, curve)
        neighborhood = {(int(n2), int(n3), int(N-n2-n3))
                        for a, b, _ in coarse[order[:3]]
                        for n2 in range(max(0, a-COARSE), min(M-1, a+COARSE)+1)
                        for n3 in range(max(1, b-COARSE), min(N-n2, b+COARSE)+1)}
        refined = np.unique(np.vstack((coarse[order[:3]], sorted(neighborhood))), axis=0)
        best, _, fine65, _ = screen(refined, d_max, curve)
        counts = refined[best[0]]
        reading = describe(counts, d_max, curve)
        assert reading['at_6p5']['rounds'] == (int(fine65[best[0]]) or None)
        out['by_family'][d_max] = dict(coarse_profiles=len(coarse), fine_profiles=len(refined),
                                      coarse_open_at_6p5=int(np.count_nonzero(r65)),
                                      fine_open_at_6p5=int(np.count_nonzero(fine65)), **reading)
        choices.append((reading['startup_10round']['snr_db'], d_max, counts))
        print(f'D={d_max} {counts.tolist()} {reading["startup_10round"]}', flush=True)
    _, d_max, counts = min(choices, key=lambda choice: choice[:2])
    out['selected_family'] = d_max
    selected = out['by_family'][d_max]['startup_10round']
    if selected['snr_db'] < baseline['startup_10round']['snr_db']:
        out['constructed'] = construct(counts, d_max, args.code_out)
    with args.out.open('x') as handle:
        json.dump(out, handle, indent=2, allow_nan=False)
        handle.write('\n')


if __name__ == '__main__':
    main()
