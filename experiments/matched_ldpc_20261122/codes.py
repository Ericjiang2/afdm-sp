"""Construct and qualify the two finite irregular LDPC codes."""
from collections import Counter, deque

import numpy as np


PROFILES = {
    'matched': ({2: 1377, 3: 620, 30: 51}, {6: 1024}, 20261122),
    'awgn': ({2: 768, 3: 1024, 12: 256}, {7: 512, 8: 512}, 20261222),
}


def peg_matrix(variable_counts, check_counts, rng):
    """Capacity-constrained PEG, with shortest paths on the partial graph."""
    degrees = rng.permutation(np.repeat(list(variable_counts), list(variable_counts.values())))
    caps = rng.permutation(np.repeat(list(check_counts), list(check_counts.values())))
    by_check = [set() for _ in caps]
    by_var = [set() for _ in degrees]
    fill = np.zeros_like(caps)
    available = set(range(len(caps)))
    tie_order = rng.permutation(len(caps))
    for v in np.argsort(-degrees, kind='stable'):
        chosen = by_var[v]
        for _ in range(degrees[v]):
            unvisited = available - chosen
            frontier = chosen
            seen_checks = set(chosen)
            seen_vars = {v}
            farthest = set(unvisited)
            while frontier and unvisited:
                newly_seen_vars = set().union(*(by_check[c] for c in frontier)) - seen_vars
                seen_vars.update(newly_seen_vars)
                frontier = set().union(*(by_var[u] for u in newly_seen_vars)) - seen_checks
                seen_checks.update(frontier)
                unvisited.difference_update(frontier)
                if unvisited:
                    farthest = set(unvisited)
            if not farthest:
                # A saturated neighborhood: discard this structural attempt.
                return None
            indices = np.fromiter(farthest, dtype=int)
            relative_load = fill[indices] / caps[indices]
            least_loaded = indices[relative_load == relative_load.min()]
            check = int(least_loaded[np.argmin(tie_order[least_loaded])])
            chosen.add(check)
            by_check[check].add(v)
            fill[check] += 1
            if fill[check] == caps[check]:
                available.remove(check)
    if not np.array_equal(fill, caps):
        raise ValueError('PEG failed to exhaust the registered check capacities')
    H = np.zeros((len(caps), len(degrees)), dtype=np.uint8)
    for v, neighbors in enumerate(by_var):
        H[list(neighbors), v] = 1
    return H


def build_irregular_code(arm):
    from afdm_sp_joint_unrolled.e1_ldpc import _edge_structs, _gf2_rref

    variable_counts, check_counts, base_seed = PROFILES[arm]
    for seed in range(base_seed, base_seed + 32):
        H = peg_matrix(variable_counts, check_counts, np.random.default_rng(seed))
        if H is None:
            continue
        reduced, pivots, free, rank = _gf2_rref(H)
        if rank != 1024:
            continue
        G = np.zeros((2048, 1024), dtype=np.uint8)
        G[free, np.arange(1024)] = 1
        G[pivots] = reduced[:, free]
        chk, var, row_ptr = _edge_structs(H)
        return dict(H=H, G=G, n=2048, k=1024, pivot_cols=pivots, free_cols=free,
                    chk=chk, var=var, row_ptr=row_ptr, seed=seed)
    raise ValueError(f'{arm}: no full-rank code in the registered seed range')


def girth(H):
    """Shortest cycle length in the bipartite graph."""
    rows, columns = H.shape
    checks, variables = np.nonzero(H)
    graph = [[] for _ in range(rows + columns)]
    for check, var in zip(checks.tolist(), variables.tolist()):
        graph[check].append(rows + var)
        graph[rows + var].append(check)
    best = rows + columns + 1
    for root in range(rows):
        distance = [-1] * len(graph)
        parent = [-1] * len(graph)
        distance[root] = 0
        queue = deque([root])
        while queue:
            vertex = queue.popleft()
            if 2 * distance[vertex] >= best:
                break
            for neighbor in graph[vertex]:
                if distance[neighbor] < 0:
                    distance[neighbor] = distance[vertex] + 1
                    parent[neighbor] = vertex
                    queue.append(neighbor)
                elif neighbor != parent[vertex]:
                    best = min(best, distance[vertex] + distance[neighbor] + 1)
        if best == 4:
            break
    if best > len(graph):
        raise ValueError('unexpected acyclic LDPC graph')
    return best


def qualify(arm, code, decoder, array_hash):
    from afdm_sp_joint_unrolled.e1_ldpc import _gf2_rref, encode, extract_info

    H = code['H']
    variable_counts = dict(Counter(H.sum(axis=0).tolist()))
    check_counts = dict(Counter(H.sum(axis=1).tolist()))
    expected = PROFILES[arm][:2] if arm != 'regular' else ({3: 2048}, {2: 3, 6: 1023})
    if (variable_counts, check_counts) != expected or _gf2_rref(H)[3] != 1024:
        raise ValueError(f'{arm}: incorrect code dimensions or degrees')
    rng = np.random.default_rng(20261124)
    for _ in range(8):
        bits = rng.integers(0, 2, size=1024, dtype=np.uint8)
        word = encode(code, bits)
        if (H @ word % 2).any() or not np.array_equal(extract_info(code, word), bits):
            raise ValueError(f'{arm}: invalid encoded word')
        decoded = decoder(code, 20 * (1 - 2 * word.astype(float)), maxiter=50)
        if not decoded['decode_ok'] or not np.array_equal(decoded['decoded'], word):
            raise ValueError(f'{arm}: noiseless decoding failed')
    edges = sum(degree * count for degree, count in variable_counts.items())
    return dict(n=code['n'], k=code['k'], rank=1024, seed=code['seed'], girth=girth(H),
                variable_counts=variable_counts, check_counts=check_counts,
                variable_edge_weights={d: d * c / edges for d, c in variable_counts.items()},
                check_edge_weights={d: d * c / edges for d, c in check_counts.items()},
                check_sha256=array_hash(H), generator_sha256=array_hash(code['G']),
                noiseless_words=8)
